from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation, localcontext
from typing import Literal

from app.schemas.run import (
    AcmgCaseContextLimitation,
    EamosComputedBenignCut,
    EamosComputedClassification,
    EamosComputedConflict,
    EamosComputedCriterion,
    EamosComputedDirection,
    EamosComputedPolicyDiff,
    EamosComputedStrength,
    EamosComputedTier,
    EamosComputedVersionPin,
    ReportPayload,
)
from app.services.acmg_policy_registry import (
    PopulationPolicyResolution,
    resolve_population_policy,
)
from app.services.computational_rulesets import active_ruleset
from app.services.functional_assay_validation import admit_functional_assertion
from app.services.pvs1_nmd import Pvs1NmdInput, assess_pvs1_nmd

ACMG_FRAMEWORK = "Richards-2015 + Tavtigian-2020 points"
PVS1_REVISION = "Abou-Tayoun-2018"
PP3_CALIBRATION = "eamos-revel-capped-v1+PMID:36413997"

ALL_ACMG_CODES: tuple[str, ...] = (
    "PVS1",
    "PS1",
    "PS2",
    "PS3",
    "PS4",
    "PM1",
    "PM2",
    "PM3",
    "PM4",
    "PM5",
    "PM6",
    "PP1",
    "PP2",
    "PP3",
    "PP4",
    "PP5",
    "BA1",
    "BS1",
    "BS2",
    "BS3",
    "BS4",
    "BP1",
    "BP2",
    "BP3",
    "BP4",
    "BP5",
    "BP6",
    "BP7",
)

_ALL_CODE_SET = frozenset(ALL_ACMG_CODES)
_MUTUALLY_EXCLUSIVE_CODES: tuple[frozenset[str], ...] = tuple(
    frozenset({left, right})
    for left, right, relationship in active_ruleset().dependency_and_exclusion_edges
    if relationship == "mutually_exclusive"
)
_FUNCTIONAL_DEPENDENCY_CODES = frozenset(
    left
    for left, _right, relationship in active_ruleset().dependency_and_exclusion_edges
    if relationship == "requires_same_direction_evidence"
)
_DEPRECATED_TRIGGER_CODES = frozenset({"PP5", "BP6"})
_TYPED_ADMISSION_ONLY_CODES = frozenset({"PS3", "BS3", "PM2", "BS1", "BA1"})
_STRENGTH_POINTS: dict[EamosComputedStrength, Decimal] = {
    "very_strong": Decimal("8"),
    "strong": Decimal("4"),
    "moderate": Decimal("2"),
    "supporting": Decimal("1"),
}
_DIRECTION_SIGN: dict[EamosComputedDirection, Literal[1, -1]] = {
    "pathogenic": 1,
    "benign": -1,
}
_PP3_PM1_COMBINED_CAP = Decimal("4")
_PP3_PM1_CAP_WARNING = "pp3_points_capped_by_pm1_dependency_group"


@dataclass(frozen=True)
class AcmgCriterionApplication:
    code: str
    applied_strength: EamosComputedStrength | None = None
    evidence_points: Decimal | str | int | float | None = None
    evidence_value: str | int | float | Decimal | None = None
    threshold: str | int | float | Decimal | None = None
    source_db: str | None = None
    source_version: str | None = None
    source_url: str | None = None
    svi_reference: str | None = None
    policy_id: str | None = None
    policy_version: str | None = None
    policy_source_url: str | None = None
    cspec_overlay_id: str | None = None
    cspec_overlay_version: str | None = None
    functional_assay_oddspath: Decimal | None = None
    functional_assay_confidence_interval_lower: Decimal | None = None
    functional_assay_confidence_interval_upper: Decimal | None = None


@dataclass(frozen=True)
class BayesianModelQuantities:
    aggregate_evidence_likelihood_ratio: Decimal
    prior_odds: Decimal
    posterior_odds: Decimal
    model_posterior: Decimal


def bayesian_model_quantities(
    net_points: Decimal | str | int | float,
) -> BayesianModelQuantities:
    net = _decimal_value(net_points, field_name="net_points")
    ruleset = active_ruleset()
    with localcontext() as context:
        context.prec = 40
        aggregate_likelihood_ratio = ruleset.likelihood_ratio_base_decimal**net
        prior_odds = ruleset.prior_decimal / (Decimal("1") - ruleset.prior_decimal)
        posterior_odds = aggregate_likelihood_ratio * prior_odds
        model_posterior = posterior_odds / (Decimal("1") + posterior_odds)
    return BayesianModelQuantities(
        aggregate_evidence_likelihood_ratio=aggregate_likelihood_ratio.normalize(),
        prior_odds=prior_odds.normalize(),
        posterior_odds=posterior_odds.normalize(),
        model_posterior=model_posterior.normalize(),
    )


def model_posterior_from_net(net_points: Decimal | str | int | float) -> Decimal:
    return bayesian_model_quantities(net_points).model_posterior


def tier_from_net(
    net_points: Decimal | str | int | float,
    benign_cut: EamosComputedBenignCut = "tavtigian_2020",
) -> EamosComputedTier:
    net = _decimal_value(net_points, field_name="net_points")
    if net >= Decimal("10"):
        return "Pathogenic"
    if net >= Decimal("6"):
        return "Likely Pathogenic"
    if net >= Decimal("0"):
        return "VUS"
    benign_threshold = Decimal("-6") if benign_cut == "acgs_panel" else Decimal("-7")
    if net <= benign_threshold:
        return "Benign"
    return "Likely Benign"


def points_for_strength(
    direction: EamosComputedDirection,
    applied_strength: EamosComputedStrength,
) -> Decimal:
    return Decimal(_DIRECTION_SIGN[direction]) * _STRENGTH_POINTS[applied_strength]


def compute_acmg_points(
    applications: list[AcmgCriterionApplication],
    *,
    benign_cut: EamosComputedBenignCut = "tavtigian_2020",
    conflict_reason: str | None = None,
    vcep_id: str | None = None,
    warnings: list[str] | None = None,
    limitations: list[AcmgCaseContextLimitation] | None = None,
    population_resolution: PopulationPolicyResolution | None = None,
) -> EamosComputedClassification:
    ruleset = active_ruleset()
    resolution = population_resolution or resolve_population_policy(gene_symbol=None)
    normalized = [_normalize_application(application) for application in applications]
    _reject_deprecated_triggers(normalized)
    _reject_duplicate_codes(normalized)
    _reject_mutually_exclusive_codes(normalized)
    normalized, functional_dependency_warnings = _enforce_functional_dependencies(normalized)
    normalized, dependency_warnings = _cap_pp3_pm1_dependency(normalized)

    rows_by_code = _triggered_rows_by_code(normalized)
    sum_pathogenic = sum(
        (row.points for row in rows_by_code.values() if row.points > 0),
        Decimal("0"),
    )
    sum_benign = sum(
        (abs(row.points) for row in rows_by_code.values() if row.points < 0),
        Decimal("0"),
    )
    net_points = sum_pathogenic - sum_benign
    ba1_override = rows_by_code.get("BA1", _not_assessed_row("BA1")).triggered
    conflict = EamosComputedConflict(
        is_conflicting=conflict_reason is not None,
        reason=conflict_reason,
    )

    tier = tier_from_net(net_points, benign_cut)
    classification_basis = "bayesian_points"
    if conflict.is_conflicting and ruleset.conflict_resolution_policy == "eamos_legacy_vus_cap":
        tier = "VUS"
        classification_basis = "legacy_conflict_cap"
    if ba1_override:
        tier = "Benign"
        classification_basis = "ba1_standalone_override"

    model_quantities = None if ba1_override else bayesian_model_quantities(net_points)

    limitation_rows = limitations or []
    compatibility_warnings = [
        *[warning for warning in (warnings or [])],
        *functional_dependency_warnings,
        *dependency_warnings,
        *[_warning_for_limitation(limitation) for limitation in limitation_rows],
    ]

    return EamosComputedClassification(
        acmg_version_pin=EamosComputedVersionPin(
            framework=ACMG_FRAMEWORK,
            ruleset_id=ruleset.ruleset_id,
            ruleset_version=ruleset.framework_version,
            conflict_policy_id=ruleset.conflict_resolution_policy,
            pvs1_revision=PVS1_REVISION,
            pp3_calibration=PP3_CALIBRATION,
            vcep_id=vcep_id,
            population_policy_id=resolution.effective_policy.policy_id,
            population_policy_version=resolution.effective_policy.version,
            cspec_overlay_id=resolution.overlay.overlay_id if resolution.overlay else None,
            cspec_overlay_version=resolution.overlay.version if resolution.overlay else None,
            population_policy_diff=[
                EamosComputedPolicyDiff(
                    field=item.field,
                    general_value=item.general_value,
                    overlay_value=item.overlay_value,
                )
                for item in resolution.diff
            ],
        ),
        net_points=net_points,
        sum_pathogenic=sum_pathogenic,
        sum_benign=sum_benign,
        tier=tier,
        classification_basis=classification_basis,
        conflict=conflict,
        ba1_override=ba1_override,
        aggregate_evidence_likelihood_ratio=(
            model_quantities.aggregate_evidence_likelihood_ratio if model_quantities else None
        ),
        prior_odds=model_quantities.prior_odds if model_quantities else None,
        posterior_odds=model_quantities.posterior_odds if model_quantities else None,
        model_posterior=model_quantities.model_posterior if model_quantities else None,
        benign_cut=benign_cut,
        per_criterion=[rows_by_code.get(code, _not_assessed_row(code)) for code in ALL_ACMG_CODES],
        limitations=limitation_rows,
        warnings=_dedupe_text(compatibility_warnings),
    )


def compute_report_acmg_classification(
    payload: ReportPayload,
    evidence_map: dict[str, dict],
    evidence_statuses: dict[str, str] | None = None,
) -> EamosComputedClassification:
    population_resolution = _population_policy_resolution(payload)
    applications, application_warnings = _applications_from_report(
        payload,
        evidence_map,
        evidence_statuses or {},
        population_resolution,
    )
    limitations = _case_context_limitations(payload, evidence_map, applications)
    computational_warnings = (
        list(payload.report_profile.computational_decision.warnings)
        if payload.report_profile is not None
        and payload.report_profile.computational_decision is not None
        else []
    )
    return compute_acmg_points(
        applications,
        warnings=[*computational_warnings, *application_warnings],
        limitations=limitations,
        population_resolution=population_resolution,
    )


def _applications_from_report(
    payload: ReportPayload,
    evidence_map: dict[str, dict],
    evidence_statuses: dict[str, str],
    population_resolution: PopulationPolicyResolution,
) -> tuple[list[AcmgCriterionApplication], list[str]]:
    applications: dict[str, AcmgCriterionApplication] = {}
    warnings: list[str] = []

    for application in _source_asserted_acmg_applications(payload, evidence_map):
        _put_application(applications, application)

    functional_applications, functional_warnings = _functional_evidence_applications(payload)
    warnings.extend(functional_warnings)
    for application in functional_applications:
        _put_application(applications, application)

    population_applications, population_warnings = _population_frequency_applications(
        payload,
        population_resolution,
    )
    warnings.extend(population_warnings)
    for application in population_applications:
        _put_application(applications, application)

    computational = _computational_application(payload, evidence_map)
    if computational is not None:
        _put_application(applications, computational)

    pvs1 = _pvs1_application(payload, evidence_statuses)
    if pvs1 is not None:
        _put_application(applications, pvs1)

    return list(applications.values()), _dedupe_text(warnings)


def _population_policy_resolution(payload: ReportPayload) -> PopulationPolicyResolution:
    profile = payload.report_profile
    header = profile.header if profile is not None else None
    snapshot = profile.gene_context_snapshot if profile is not None else None
    decision = profile.computational_decision if profile is not None else None
    disease = profile.disease_mechanism if profile is not None else None
    row = payload.variant_summary_rows[0] if payload.variant_summary_rows else None
    gene_symbol = (row.gene if row is not None else None) or (
        header.gene if header is not None else None
    )
    gene_ids = _dedupe_optional_text(
        [
            decision.gene_id if decision is not None else None,
            header.ensembl_gene_id if header is not None else None,
            snapshot.ensembl_gene_id if snapshot is not None else None,
        ]
    )
    disease_ids = tuple(disease.disease_ids) if disease is not None else ()
    return resolve_population_policy(
        gene_symbol=gene_symbol,
        gene_ids=gene_ids,
        disease_ids=disease_ids,
    )


def _functional_context_identifiers(
    payload: ReportPayload,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    profile = payload.report_profile
    header = profile.header if profile is not None else None
    snapshot = profile.gene_context_snapshot if profile is not None else None
    decision = profile.computational_decision if profile is not None else None
    row = payload.variant_summary_rows[0] if payload.variant_summary_rows else None
    population_resolution = _population_policy_resolution(payload)
    gene_ids = _dedupe_optional_text(
        [
            row.gene if row is not None else None,
            header.gene if header is not None else None,
            decision.gene_id if decision is not None else None,
            header.ensembl_gene_id if header is not None else None,
            snapshot.ensembl_gene_id if snapshot is not None else None,
            (
                population_resolution.overlay.gene_id
                if population_resolution.overlay is not None
                else None
            ),
        ]
    )
    disease = profile.disease_mechanism if profile is not None else None
    disease_ids = tuple(disease.disease_ids) if disease is not None else ()
    return gene_ids, disease_ids


def _case_context_limitations(
    payload: ReportPayload,
    evidence_map: dict[str, dict],
    applications: list[AcmgCriterionApplication],
) -> list[AcmgCaseContextLimitation]:
    triggered_codes = {application.code for application in applications}
    limitations: list[AcmgCaseContextLimitation] = []
    if "PM3" not in triggered_codes and _has_recessive_gene_disease(evidence_map):
        limitations.append(
            AcmgCaseContextLimitation(
                code="PM3",
                missing_inputs=["affected_status", "second_allele", "phase"],
                applies_when=["recessive_gene_disease"],
                message=(
                    "PM3 requires affected case context, a second disease-causing "
                    "allele, and phase evidence before EAMOS can score it."
                ),
            )
        )
    if "PP4" not in triggered_codes and _has_gene_disease_context(evidence_map):
        limitations.append(
            AcmgCaseContextLimitation(
                code="PP4",
                missing_inputs=[
                    "phenotype_specificity",
                    "test_scope",
                    "alternative_cause_exclusion",
                ],
                applies_when=["gene_disease_context"],
                message=(
                    "PP4 requires phenotype specificity, test scope, and "
                    "alternative-cause review before EAMOS can score it."
                ),
            )
        )
    return limitations


def _warning_for_limitation(limitation: AcmgCaseContextLimitation) -> str:
    if limitation.code == "PM3" and limitation.reason == "missing_case_context":
        return "acmg_case_context_not_scored:PM3_phase_in_trans_required"
    if limitation.code == "PP4" and limitation.reason == "missing_case_context":
        return "acmg_case_context_not_scored:PP4_phenotype_specificity_required"
    return f"acmg_case_context_not_scored:{limitation.code}_{limitation.reason}"


def _has_gene_disease_context(evidence_map: dict[str, dict]) -> bool:
    gene_disease = evidence_map.get("gene_disease")
    if not isinstance(gene_disease, dict):
        return False
    if _optional_text(gene_disease.get("primary_condition")):
        return True
    return bool(_list_of_dicts(gene_disease.get("conditions")))


def _has_recessive_gene_disease(evidence_map: dict[str, dict]) -> bool:
    gene_disease = evidence_map.get("gene_disease")
    if not isinstance(gene_disease, dict):
        return False
    inheritance_values = [_optional_text(gene_disease.get("inheritance"))]
    for condition in _list_of_dicts(gene_disease.get("conditions")):
        inheritance_values.append(_optional_text(condition.get("inheritance")))
    return any(_is_recessive_inheritance(value) for value in inheritance_values)


def _is_recessive_inheritance(value: str | None) -> bool:
    if not value:
        return False
    normalized = " ".join(value.replace("_", " ").replace("-", " ").casefold().split())
    return normalized == "ar" or "autosomal recessive" in normalized


def _triggered_rows_by_code(
    applications: list[AcmgCriterionApplication],
) -> dict[str, EamosComputedCriterion]:
    rows: dict[str, EamosComputedCriterion] = {}
    for application in applications:
        direction = _direction_for_code(application.code)
        points = Decimal("0")
        if application.code != "BA1":
            if application.evidence_points is not None:
                points = _decimal_value(
                    application.evidence_points,
                    field_name=f"{application.code}.evidence_points",
                )
            else:
                if application.applied_strength is None:
                    raise ValueError(
                        f"{application.code} requires applied_strength or evidence_points"
                    )
                points = points_for_strength(direction, application.applied_strength)

        rows[application.code] = EamosComputedCriterion(
            code=application.code,
            direction=direction,
            triggered=True,
            applied_strength=application.applied_strength,
            points=points,
            evidence_value=application.evidence_value,
            threshold=application.threshold,
            source_db=application.source_db,
            source_version=application.source_version,
            source_url=application.source_url,
            svi_reference=application.svi_reference,
            policy_id=application.policy_id,
            policy_version=application.policy_version,
            policy_source_url=application.policy_source_url,
            cspec_overlay_id=application.cspec_overlay_id,
            cspec_overlay_version=application.cspec_overlay_version,
            functional_assay_oddspath=application.functional_assay_oddspath,
            functional_assay_confidence_interval_lower=(
                application.functional_assay_confidence_interval_lower
            ),
            functional_assay_confidence_interval_upper=(
                application.functional_assay_confidence_interval_upper
            ),
        )
    return rows


def _source_asserted_acmg_applications(
    payload: ReportPayload,
    evidence_map: dict[str, dict],
) -> list[AcmgCriterionApplication]:
    worksheet = _clinical_consensus_worksheet(evidence_map)
    if (
        worksheet is None
        and payload.report_profile is not None
        and payload.report_profile.acmg_worksheet is not None
    ):
        worksheet = payload.report_profile.acmg_worksheet.model_dump(mode="json")
    if not isinstance(worksheet, dict):
        return []

    applications: list[AcmgCriterionApplication] = []
    for row in _list_of_dicts(worksheet.get("criteria")):
        if row.get("state") != "met" or row.get("assertion_level") != "source_asserted":
            continue
        code = _optional_text(row.get("code"))
        if code and code.split("_", 1)[0].upper() in _TYPED_ADMISSION_ONLY_CODES:
            # Functional and population assertions remain context until their
            # typed, versioned admission paths accept them below.
            continue
        application = _application_from_code_strength(
            code=code,
            strength=row.get("strength"),
            source_db=row.get("source"),
            source_version=_first_text(row.get("evidence_refs")),
            svi_reference=_first_pmid(row.get("evidence_refs")),
        )
        if application is not None:
            applications.append(application)
    return applications


def _functional_evidence_applications(
    payload: ReportPayload,
) -> tuple[list[AcmgCriterionApplication], list[str]]:
    functional = payload.functional_evidence
    if functional is None:
        return [], []

    warnings: list[str] = []
    if functional.source_asserted_codes and not functional.assertion_candidates:
        warnings.append("functional_source_assertions_context_only:assay_validation_missing")

    selected = [
        candidate
        for candidate in functional.assertion_candidates
        if candidate.selected_for_counting
    ]
    if not selected:
        if functional.assertion_candidates:
            warnings.append("functional_assertions_context_only:none_selected_for_counting")
        return [], warnings
    if len(selected) != 1:
        warnings.append("functional_assertion_not_counted:selected_candidate_cardinality")
        return [], warnings

    candidate = selected[0]
    gene_ids, disease_ids = _functional_context_identifiers(payload)
    admission = admit_functional_assertion(
        candidate,
        gene_ids=gene_ids,
        disease_ids=disease_ids,
    )
    if not admission.admitted:
        warnings.extend(
            f"functional_assertion_not_counted:{reason}" for reason in admission.reasons
        )
        return [], warnings

    return [
        AcmgCriterionApplication(
            code=admission.code,
            applied_strength=admission.applied_strength,
            evidence_value=admission.functional_assay_oddspath,
            threshold=(
                "functional assay OddsPath CI "
                f"[{admission.confidence_interval_lower}, "
                f"{admission.confidence_interval_upper}]"
            ),
            source_db=admission.source_id,
            source_version=admission.source_version,
            source_url=admission.source_url,
            svi_reference=(
                f"{admission.source_record_id}; "
                f"{admission.validation_id}@{admission.validation_version}"
            ),
            policy_id=admission.validation_policy_id,
            policy_version=admission.validation_policy_version,
            policy_source_url=admission.validation_source_url,
            functional_assay_oddspath=admission.functional_assay_oddspath,
            functional_assay_confidence_interval_lower=admission.confidence_interval_lower,
            functional_assay_confidence_interval_upper=admission.confidence_interval_upper,
        )
    ], warnings


def _population_frequency_applications(
    payload: ReportPayload,
    resolution: PopulationPolicyResolution,
) -> tuple[list[AcmgCriterionApplication], list[str]]:
    population = payload.population_frequency_detail
    if population is None:
        return [], []

    frequency, frequency_basis = _population_frequency_value(population)
    if frequency is None:
        return [], []
    policy = resolution.effective_policy
    if (
        frequency_basis != policy.frequency_metric
        and not policy.allow_maximum_observed_frequency_fallback
    ):
        return [], ["population_cspec_not_applied:popmax_faf_missing"]

    overlay = resolution.overlay
    source_db = population.source or "gnomAD"
    source_version = population.dataset or None
    common = {
        "source_db": source_db,
        "source_version": source_version,
        "source_url": population.source_url,
        "svi_reference": policy.source_url,
        "policy_id": policy.policy_id,
        "policy_version": policy.version,
        "policy_source_url": policy.source_url,
        "cspec_overlay_id": overlay.overlay_id if overlay else None,
        "cspec_overlay_version": overlay.version if overlay else None,
    }
    if frequency >= policy.ba1_minimum:
        return [
            AcmgCriterionApplication(
                "BA1",
                evidence_value=frequency,
                threshold=f">={format(policy.ba1_minimum, 'f')}",
                **common,
            )
        ], []
    if frequency >= policy.bs1_minimum:
        return [
            AcmgCriterionApplication(
                "BS1",
                "strong",
                evidence_value=frequency,
                threshold=f">={format(policy.bs1_minimum, 'f')}",
                **common,
            )
        ], []

    allele_number = population.allele_number
    homozygote_count = population.homozygote_count
    pm2_frequency_match = (
        frequency <= policy.pm2_maximum
        if policy.pm2_maximum_inclusive
        else frequency < policy.pm2_maximum
    )
    if (
        pm2_frequency_match
        and (
            policy.pm2_minimum_allele_number is None
            or allele_number is not None
            and allele_number >= policy.pm2_minimum_allele_number
        )
        and (
            policy.pm2_maximum_homozygotes is None
            or homozygote_count is not None
            and homozygote_count <= policy.pm2_maximum_homozygotes
        )
    ):
        comparator = "<=" if policy.pm2_maximum_inclusive else "<"
        return [
            AcmgCriterionApplication(
                "PM2",
                "supporting",
                evidence_value=frequency,
                threshold=f"{comparator}{format(policy.pm2_maximum, 'f')}",
                **common,
            )
        ], []
    return [], []


def _computational_application(
    payload: ReportPayload,
    evidence_map: dict[str, dict],
) -> AcmgCriterionApplication | None:
    del evidence_map
    ruleset = active_ruleset()
    profile = payload.report_profile
    decision = profile.computational_decision if profile is not None else None
    if decision is None:
        return None
    if (
        decision.standard_status != "published"
        or decision.ruleset_id != ruleset.ruleset_id
        or decision.ruleset_version != ruleset.framework_version
        or decision.evidence_family != "PP3_BP4"
        or decision.selected_predictor_id != "revel"
        or decision.declared_fallback_policy != "none"
        or decision.calibration_id != "revel_pejaver_2022_capped"
        or decision.applicability != "applicable"
        or decision.counted_status != "counted"
        or decision.evidence_code not in {"PP3", "BP4"}
        or decision.evidence_points == 0
    ):
        return None
    direction = _direction_for_code(decision.evidence_code)
    if (direction == "pathogenic" and decision.evidence_points < 0) or (
        direction == "benign" and decision.evidence_points > 0
    ):
        return None
    return AcmgCriterionApplication(
        code=decision.evidence_code,
        applied_strength=_strength_for_points(decision.evidence_points),
        evidence_points=decision.evidence_points,
        evidence_value=decision.calibration_normalized_score,
        threshold=_interval_threshold(decision),
        source_db="REVEL",
        source_version=decision.source_version or decision.model_version,
        source_url=decision.source_url,
        svi_reference=decision.calibration_version,
    )


def _pvs1_application(
    payload: ReportPayload,
    evidence_statuses: dict[str, str],
) -> AcmgCriterionApplication | None:
    row = payload.variant_summary_rows[0] if payload.variant_summary_rows else None
    consequence = row.consequence if row is not None else None
    if not consequence:
        return None

    exon_number, exon_count = _pvs1_exon_context(payload)
    critical_region = _lof_relevance_supported(payload)
    assessment = assess_pvs1_nmd(
        Pvs1NmdInput(
            consequence=consequence,
            exon_number=exon_number,
            exon_count=exon_count,
            critical_region=critical_region,
            transcript=(
                payload.report_profile.header.transcript
                if payload.report_profile is not None and payload.report_profile.header is not None
                else None
            ),
        )
    )
    if (
        not assessment.applicable
        or assessment.pvs1_support != "possible"
        or assessment.nmd_predicted is not True
    ):
        return None

    status = evidence_statuses.get("sequence_context") or evidence_statuses.get("vep")
    return AcmgCriterionApplication(
        "PVS1",
        "strong",
        evidence_value=assessment.reason,
        threshold="LoF consequence with NMD and LoF relevance support",
        source_db="EAMOS PVS1/NMD decision support",
        source_version=status,
        svi_reference="Abou-Tayoun-2018",
    )


def _put_application(
    applications: dict[str, AcmgCriterionApplication],
    application: AcmgCriterionApplication,
) -> None:
    try:
        code = _normalize_code(application.code)
    except ValueError:
        return
    if code in applications or code in _DEPRECATED_TRIGGER_CODES:
        return
    if any(code in group and applications.keys() & group for group in _MUTUALLY_EXCLUSIVE_CODES):
        return
    applications[code] = application


def _clinical_consensus_worksheet(evidence_map: dict[str, dict]) -> dict | None:
    consensus = evidence_map.get("clinical_consensus")
    if not isinstance(consensus, dict):
        return None
    worksheet = consensus.get("acmg_worksheet")
    return worksheet if isinstance(worksheet, dict) else None


def _application_from_code_strength(
    *,
    code: object,
    strength: object = None,
    source_db: object = None,
    source_version: object = None,
    svi_reference: object = None,
) -> AcmgCriterionApplication | None:
    text = _optional_text(code)
    if not text:
        return None
    try:
        normalized_code = _normalize_code(text)
    except ValueError:
        return None
    if normalized_code in _DEPRECATED_TRIGGER_CODES:
        return None

    applied_strength = None if normalized_code == "BA1" else _normalize_applied_strength(strength)
    if applied_strength is None and normalized_code != "BA1":
        applied_strength = _default_strength_for_code(normalized_code)
    if applied_strength is None and normalized_code != "BA1":
        return None

    return AcmgCriterionApplication(
        normalized_code,
        applied_strength,
        source_db=_optional_text(source_db),
        source_version=_optional_text(source_version),
        svi_reference=_optional_text(svi_reference),
    )


def _normalize_applied_strength(value: object) -> EamosComputedStrength | None:
    text = _optional_text(value)
    if not text:
        return None
    if "_" in text and text.upper().split("_", 1)[0] in _ALL_CODE_SET:
        text = text.split("_", 1)[1]
    key = " ".join(text.replace("_", " ").replace("-", " ").lower().split())
    aliases: dict[str, EamosComputedStrength] = {
        "very strong": "very_strong",
        "verystrong": "very_strong",
        "strong": "strong",
        "moderate": "moderate",
        "supporting": "supporting",
        "support": "supporting",
    }
    direct = aliases.get(key)
    if direct is not None:
        return direct
    if "very strong" in key or "verystrong" in key:
        return "very_strong"
    if "strong" in key:
        return "strong"
    if "moderate" in key:
        return "moderate"
    if "supporting" in key or "support" in key:
        return "supporting"
    return None


def _default_strength_for_code(code: str) -> EamosComputedStrength | None:
    normalized = _normalize_code(code)
    if normalized == "PVS1":
        return "very_strong"
    if normalized.startswith(("PS", "BS")):
        return "strong"
    if normalized.startswith("PM"):
        return "moderate"
    if normalized.startswith(("PP", "BP")):
        return "supporting"
    return None


def _population_frequency_value(population) -> tuple[Decimal | None, str | None]:
    popmax = _optional_decimal(population.popmax_frequency)
    if popmax is not None:
        return popmax, "popmax_filtering_allele_frequency"

    values = [_optional_decimal(population.allele_frequency)]
    values.extend(
        _optional_decimal(group.allele_frequency) for group in population.genetic_ancestry_groups
    )
    present = [value for value in values if value is not None]
    return (max(present), "maximum_observed_allele_frequency") if present else (None, None)


def _pvs1_exon_context(payload: ReportPayload) -> tuple[int | None, int | None]:
    snapshot = payload.report_profile.gene_context_snapshot if payload.report_profile else None
    variant = snapshot.variant if snapshot is not None else None
    exon_number = variant.exon_number if variant is not None else None
    exon_count = len(snapshot.exons) if snapshot is not None and snapshot.exons else None
    return exon_number, exon_count


def _lof_relevance_supported(payload: ReportPayload) -> bool | None:
    profile = payload.report_profile
    if profile is None:
        return None
    molecular = profile.molecular_context
    if molecular is not None:
        dosage = (molecular.clingen_haploinsufficiency or "").lower()
        if "sufficient evidence" in dosage and "haploinsufficiency" in dosage:
            return True
    disease = profile.disease_mechanism
    if disease is not None:
        mechanism = (disease.mechanism or "").lower()
        if "loss of function" in mechanism or "haploinsufficiency" in mechanism:
            return True
    return None


def _normalize_application(application: AcmgCriterionApplication) -> AcmgCriterionApplication:
    code = _normalize_code(application.code)
    strength = application.applied_strength
    if strength is not None and strength not in _STRENGTH_POINTS:
        raise ValueError(f"unsupported ACMG applied_strength: {strength}")
    evidence_points = (
        _decimal_value(application.evidence_points, field_name=f"{code}.evidence_points")
        if application.evidence_points is not None
        else None
    )
    if code == "BA1":
        if evidence_points not in {None, Decimal("0")}:
            raise ValueError("BA1 is a stand-alone override and cannot carry evidence_points")
        evidence_points = None
    elif evidence_points is not None:
        if evidence_points == 0:
            raise ValueError(f"{code}.evidence_points must be non-zero when triggered")
        direction = _direction_for_code(code)
        if (direction == "pathogenic" and evidence_points < 0) or (
            direction == "benign" and evidence_points > 0
        ):
            raise ValueError(f"{code}.evidence_points has the wrong direction")
        if strength is not None and evidence_points != points_for_strength(direction, strength):
            raise ValueError(f"{code}.evidence_points conflicts with applied_strength")
    return AcmgCriterionApplication(
        code=code,
        applied_strength=strength,
        evidence_points=evidence_points,
        evidence_value=application.evidence_value,
        threshold=application.threshold,
        source_db=application.source_db,
        source_version=application.source_version,
        source_url=application.source_url,
        svi_reference=application.svi_reference,
        policy_id=application.policy_id,
        policy_version=application.policy_version,
        policy_source_url=application.policy_source_url,
        cspec_overlay_id=application.cspec_overlay_id,
        cspec_overlay_version=application.cspec_overlay_version,
        functional_assay_oddspath=application.functional_assay_oddspath,
        functional_assay_confidence_interval_lower=(
            application.functional_assay_confidence_interval_lower
        ),
        functional_assay_confidence_interval_upper=(
            application.functional_assay_confidence_interval_upper
        ),
    )


def _cap_pp3_pm1_dependency(
    applications: list[AcmgCriterionApplication],
) -> tuple[list[AcmgCriterionApplication], list[str]]:
    by_code = {application.code: application for application in applications}
    pp3 = by_code.get("PP3")
    pm1 = by_code.get("PM1")
    if pp3 is None or pm1 is None:
        return applications, []

    pp3_points = _application_points(pp3)
    pm1_points = _application_points(pm1)
    if pp3_points + pm1_points <= _PP3_PM1_COMBINED_CAP:
        return applications, []

    allowed = max(Decimal("0"), _PP3_PM1_COMBINED_CAP - pm1_points)
    adjusted: list[AcmgCriterionApplication] = []
    for application in applications:
        if application.code != "PP3":
            adjusted.append(application)
        elif allowed > 0:
            adjusted.append(
                replace(
                    application,
                    applied_strength=_strength_for_points(allowed),
                    evidence_points=allowed,
                )
            )
    return adjusted, [_PP3_PM1_CAP_WARNING]


def _enforce_functional_dependencies(
    applications: list[AcmgCriterionApplication],
) -> tuple[list[AcmgCriterionApplication], list[str]]:
    retained: list[AcmgCriterionApplication] = []
    warnings: list[str] = []
    for application in applications:
        if application.code not in _FUNCTIONAL_DEPENDENCY_CODES:
            retained.append(application)
            continue
        direction = _direction_for_code(application.code)
        has_independent_support = any(
            candidate.code not in _FUNCTIONAL_DEPENDENCY_CODES
            and _direction_for_code(candidate.code) == direction
            for candidate in applications
        )
        if has_independent_support:
            retained.append(application)
        else:
            warnings.append(
                "functional_assertion_not_counted:"
                f"{application.code}_independent_same_direction_evidence_missing"
            )
    return retained, warnings


def _application_points(application: AcmgCriterionApplication) -> Decimal:
    if application.code == "BA1":
        return Decimal("0")
    if application.evidence_points is not None:
        return _decimal_value(
            application.evidence_points,
            field_name=f"{application.code}.evidence_points",
        )
    if application.applied_strength is None:
        raise ValueError(f"{application.code} requires applied_strength or evidence_points")
    return points_for_strength(_direction_for_code(application.code), application.applied_strength)


def _strength_for_points(points: Decimal) -> EamosComputedStrength | None:
    magnitude = abs(points)
    return next(
        (strength for strength, value in _STRENGTH_POINTS.items() if value == magnitude),
        None,
    )


def _interval_threshold(decision: object) -> str | None:
    lower = getattr(decision, "interval_lower", None)
    upper = getattr(decision, "interval_upper", None)
    if lower is None and upper is None:
        return None
    lower_bracket = "[" if getattr(decision, "interval_lower_inclusive", False) else "("
    upper_bracket = "]" if getattr(decision, "interval_upper_inclusive", False) else ")"
    lower_text = "-inf" if lower is None else format(lower, "f")
    upper_text = "+inf" if upper is None else format(upper, "f")
    return f"{lower_bracket}{lower_text}, {upper_text}{upper_bracket}"


def _normalize_code(code: str) -> str:
    normalized = code.strip().upper()
    if not normalized:
        raise ValueError("ACMG criterion code is required")
    if "_" in normalized:
        normalized = normalized.split("_", 1)[0]
    if normalized not in _ALL_CODE_SET:
        raise ValueError(f"unsupported ACMG criterion code: {code}")
    return normalized


def _reject_duplicate_codes(applications: list[AcmgCriterionApplication]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for application in applications:
        if application.code in seen:
            duplicates.add(application.code)
        seen.add(application.code)
    if duplicates:
        raise ValueError(f"duplicate ACMG criterion applications: {', '.join(sorted(duplicates))}")


def _reject_deprecated_triggers(applications: list[AcmgCriterionApplication]) -> None:
    deprecated = sorted(
        application.code
        for application in applications
        if application.code in _DEPRECATED_TRIGGER_CODES
    )
    if deprecated:
        raise ValueError(f"deprecated ACMG criteria cannot be triggered: {', '.join(deprecated)}")


def _reject_mutually_exclusive_codes(applications: list[AcmgCriterionApplication]) -> None:
    triggered_codes = {application.code for application in applications}
    conflicts: list[str] = []
    for group in _MUTUALLY_EXCLUSIVE_CODES:
        overlap = sorted(triggered_codes & group)
        if len(overlap) > 1:
            conflicts.append("+".join(overlap))
    if conflicts:
        raise ValueError(f"mutually exclusive ACMG criteria co-fired: {', '.join(conflicts)}")


def _not_assessed_row(code: str) -> EamosComputedCriterion:
    return EamosComputedCriterion(
        code=code,
        direction=_direction_for_code(code),
        triggered=False,
        applied_strength=None,
        points=0,
    )


def _direction_for_code(code: str) -> EamosComputedDirection:
    normalized = _normalize_code(code)
    if normalized == "PVS1" or normalized.startswith(("PS", "PM", "PP")):
        return "pathogenic"
    return "benign"


def _list_of_dicts(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _dedupe_text(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _dedupe_optional_text(items: list[object]) -> tuple[str, ...]:
    return tuple(_dedupe_text([text for item in items if (text := _optional_text(item))]))


def _first_text(value: object) -> str | None:
    if isinstance(value, list):
        for item in value:
            text = _optional_text(item)
            if text:
                return text
    return _optional_text(value)


def _first_pmid(value: object) -> str | None:
    text = _first_text(value)
    return text if text and text.upper().startswith("PMID:") else None


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None
    return parsed if parsed.is_finite() else None


def _decimal_value(value: object, *, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a finite decimal")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise ValueError(f"{field_name} must be a finite decimal") from exc
    if not parsed.is_finite():
        raise ValueError(f"{field_name} must be a finite decimal")
    return parsed
