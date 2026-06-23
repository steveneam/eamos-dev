from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.schemas.run import (
    EamosComputedBenignCut,
    EamosComputedClassification,
    EamosComputedConflict,
    EamosComputedCriterion,
    EamosComputedDirection,
    EamosComputedStrength,
    EamosComputedTier,
    EamosComputedVersionPin,
    ReportPayload,
)
from app.services.pvs1_nmd import Pvs1NmdInput, assess_pvs1_nmd

ACMG_FRAMEWORK = "Richards-2015 + Tavtigian-2020 points"
PVS1_REVISION = "Abou-Tayoun-2018"
PP3_CALIBRATION = "Pejaver-2022"
POSTERIOR_PRIOR = 0.10
ODDS_PATH_BASE = 2.08
PM2_POPMAX_THRESHOLD = 0.0001
BS1_POPMAX_THRESHOLD = 0.01
BA1_POPMAX_THRESHOLD = 0.05
PM2_MIN_ALLELE_NUMBER = 1000

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
_MUTUALLY_EXCLUSIVE_CODES: tuple[frozenset[str], ...] = (
    frozenset({"PM2", "BA1"}),
    frozenset({"PM2", "BS1"}),
    frozenset({"PP3", "BP4"}),
    frozenset({"PS3", "BS3"}),
)
_DEPRECATED_TRIGGER_CODES = frozenset({"PP5", "BP6"})
_STRENGTH_POINTS: dict[EamosComputedStrength, int] = {
    "very_strong": 8,
    "strong": 4,
    "moderate": 2,
    "supporting": 1,
}
_DIRECTION_SIGN: dict[EamosComputedDirection, Literal[1, -1]] = {
    "pathogenic": 1,
    "benign": -1,
}


@dataclass(frozen=True)
class AcmgCriterionApplication:
    code: str
    applied_strength: EamosComputedStrength | None = None
    evidence_value: str | int | float | None = None
    threshold: str | int | float | None = None
    source_db: str | None = None
    source_version: str | None = None
    svi_reference: str | None = None


def posterior_from_net(net_points: int) -> float:
    odds_path = ODDS_PATH_BASE**net_points
    return (odds_path * POSTERIOR_PRIOR) / ((odds_path - 1) * POSTERIOR_PRIOR + 1)


def tier_from_net(
    net_points: int,
    benign_cut: EamosComputedBenignCut = "tavtigian_2020",
) -> EamosComputedTier:
    if net_points >= 10:
        return "Pathogenic"
    if net_points >= 6:
        return "Likely Pathogenic"
    if net_points >= 0:
        return "VUS"
    benign_threshold = -6 if benign_cut == "acgs_panel" else -7
    if net_points <= benign_threshold:
        return "Benign"
    return "Likely Benign"


def points_for_strength(
    direction: EamosComputedDirection,
    applied_strength: EamosComputedStrength,
) -> int:
    return _DIRECTION_SIGN[direction] * _STRENGTH_POINTS[applied_strength]


def compute_acmg_points(
    applications: list[AcmgCriterionApplication],
    *,
    benign_cut: EamosComputedBenignCut = "tavtigian_2020",
    conflict_reason: str | None = None,
    vcep_id: str | None = None,
    warnings: list[str] | None = None,
) -> EamosComputedClassification:
    normalized = [_normalize_application(application) for application in applications]
    _reject_deprecated_triggers(normalized)
    _reject_duplicate_codes(normalized)
    _reject_mutually_exclusive_codes(normalized)

    rows_by_code = _triggered_rows_by_code(normalized)
    sum_pathogenic = sum(row.points for row in rows_by_code.values() if row.points > 0)
    sum_benign = sum(abs(row.points) for row in rows_by_code.values() if row.points < 0)
    net_points = sum_pathogenic - sum_benign
    ba1_override = rows_by_code.get("BA1", _not_assessed_row("BA1")).triggered
    conflict = EamosComputedConflict(
        is_conflicting=conflict_reason is not None,
        reason=conflict_reason,
    )

    tier = tier_from_net(net_points, benign_cut)
    if conflict.is_conflicting:
        tier = "VUS"
    if ba1_override:
        tier = "Benign"

    return EamosComputedClassification(
        acmg_version_pin=EamosComputedVersionPin(
            framework=ACMG_FRAMEWORK,
            pvs1_revision=PVS1_REVISION,
            pp3_calibration=PP3_CALIBRATION,
            vcep_id=vcep_id,
        ),
        net_points=net_points,
        sum_pathogenic=sum_pathogenic,
        sum_benign=sum_benign,
        tier=tier,
        conflict=conflict,
        ba1_override=ba1_override,
        posterior=posterior_from_net(net_points),
        benign_cut=benign_cut,
        per_criterion=[rows_by_code.get(code, _not_assessed_row(code)) for code in ALL_ACMG_CODES],
        warnings=_dedupe_text(warnings or []),
    )


def compute_report_acmg_classification(
    payload: ReportPayload,
    evidence_map: dict[str, dict],
    evidence_statuses: dict[str, str] | None = None,
) -> EamosComputedClassification:
    applications = _applications_from_report(payload, evidence_map, evidence_statuses or {})
    return compute_acmg_points(
        applications,
        warnings=_case_context_limit_warnings(payload, evidence_map, applications),
    )


def _applications_from_report(
    payload: ReportPayload,
    evidence_map: dict[str, dict],
    evidence_statuses: dict[str, str],
) -> list[AcmgCriterionApplication]:
    applications: dict[str, AcmgCriterionApplication] = {}

    for application in _source_asserted_acmg_applications(payload, evidence_map):
        _put_application(applications, application)

    for application in _functional_evidence_applications(payload):
        _put_application(applications, application)

    for application in _population_frequency_applications(payload):
        _put_application(applications, application)

    computational = _computational_application(payload, evidence_map)
    if computational is not None:
        _put_application(applications, computational)

    pvs1 = _pvs1_application(payload, evidence_statuses)
    if pvs1 is not None:
        _put_application(applications, pvs1)

    return list(applications.values())


def _case_context_limit_warnings(
    payload: ReportPayload,
    evidence_map: dict[str, dict],
    applications: list[AcmgCriterionApplication],
) -> list[str]:
    triggered_codes = {application.code for application in applications}
    warnings: list[str] = []
    if "PM3" not in triggered_codes and _has_recessive_gene_disease(evidence_map):
        warnings.append("acmg_case_context_not_scored:PM3_phase_in_trans_required")
    if "PP4" not in triggered_codes and _has_gene_disease_context(evidence_map):
        warnings.append("acmg_case_context_not_scored:PP4_phenotype_specificity_required")
    return warnings


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
        points = 0
        if application.code != "BA1":
            if application.applied_strength is None:
                raise ValueError(f"{application.code} requires applied_strength")
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
            svi_reference=application.svi_reference,
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
        application = _application_from_code_strength(
            code=row.get("code"),
            strength=row.get("strength"),
            source_db=row.get("source"),
            source_version=_first_text(row.get("evidence_refs")),
            svi_reference=_first_pmid(row.get("evidence_refs")),
        )
        if application is not None:
            applications.append(application)
    return applications


def _functional_evidence_applications(payload: ReportPayload) -> list[AcmgCriterionApplication]:
    functional = payload.functional_evidence
    if functional is None:
        return []

    applications: list[AcmgCriterionApplication] = []
    for value in functional.source_asserted_codes:
        application = _application_from_code_strength(
            code=value,
            source_db="Functional evidence",
            source_version=functional.display_metrics.verdict_source,
            svi_reference=None,
        )
        if application is not None:
            applications.append(application)
    return applications


def _population_frequency_applications(payload: ReportPayload) -> list[AcmgCriterionApplication]:
    population = payload.population_frequency_detail
    if population is None:
        return []

    frequency = _population_frequency_value(population)
    if frequency is None:
        return []

    source_db = population.source or "gnomAD"
    source_version = population.dataset or None
    if frequency >= BA1_POPMAX_THRESHOLD:
        return [
            AcmgCriterionApplication(
                "BA1",
                evidence_value=frequency,
                threshold=f">={BA1_POPMAX_THRESHOLD:g}",
                source_db=source_db,
                source_version=source_version,
                svi_reference="ACMG/AMP BA1 stand-alone frequency criterion",
            )
        ]
    if frequency >= BS1_POPMAX_THRESHOLD:
        return [
            AcmgCriterionApplication(
                "BS1",
                "strong",
                evidence_value=frequency,
                threshold=f">={BS1_POPMAX_THRESHOLD:g}",
                source_db=source_db,
                source_version=source_version,
            )
        ]

    allele_number = population.allele_number
    homozygote_count = population.homozygote_count
    if (
        frequency < PM2_POPMAX_THRESHOLD
        and (allele_number is None or allele_number >= PM2_MIN_ALLELE_NUMBER)
        and (homozygote_count is None or homozygote_count == 0)
    ):
        return [
            AcmgCriterionApplication(
                "PM2",
                "supporting",
                evidence_value=frequency,
                threshold=f"<{PM2_POPMAX_THRESHOLD:g}",
                source_db=source_db,
                source_version=source_version,
                svi_reference="ClinGen SVI PM2_supporting frequency guardrail",
            )
        ]
    return []


def _computational_application(
    payload: ReportPayload,
    evidence_map: dict[str, dict],
) -> AcmgCriterionApplication | None:
    rows = _computational_rows(payload, evidence_map)
    pp3 = _best_computational_row(rows, "PP3")
    bp4 = _best_computational_row(rows, "BP4")
    if pp3 is not None and bp4 is not None:
        return None
    if pp3 is not None:
        return pp3
    return bp4


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


def _population_frequency_value(population) -> float | None:
    values = [
        _optional_float(population.popmax_frequency),
        _optional_float(population.allele_frequency),
    ]
    values.extend(
        _optional_float(group.allele_frequency) for group in population.genetic_ancestry_groups
    )
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _computational_rows(
    payload: ReportPayload,
    evidence_map: dict[str, dict],
) -> list[dict]:
    rows: list[dict] = []
    if payload.report_profile is not None and payload.report_profile.computational_deep_dive:
        section = payload.report_profile.computational_deep_dive
        rows.extend(row.model_dump(mode="json") for row in section.predictors)

    computational = evidence_map.get("computational_annotations")
    if isinstance(computational, dict):
        rows.extend(_list_of_dicts(computational.get("predictors")))
    return rows


def _best_computational_row(
    rows: list[dict],
    code: str,
) -> AcmgCriterionApplication | None:
    candidates: list[tuple[int, AcmgCriterionApplication]] = []
    for row in rows:
        code_strength = _computational_code_strength(row)
        if code_strength is None:
            continue
        row_code, strength = code_strength
        if row_code != code:
            continue
        direction = _direction_for_code(code)
        application = AcmgCriterionApplication(
            code,
            strength,
            evidence_value=row.get("score"),
            threshold=row.get("threshold"),
            source_db=_optional_text(row.get("name")) or _optional_text(row.get("source")),
            source_version=_optional_text(row.get("version"))
            or _optional_text(row.get("calibration_version")),
            svi_reference=_optional_text(row.get("calibration_version")),
        )
        candidates.append((abs(points_for_strength(direction, strength)), application))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _computational_code_strength(row: dict) -> tuple[str, EamosComputedStrength] | None:
    label = _optional_text(row.get("calibrated_label")) or _optional_text(row.get("acmg_band"))
    if not label:
        return None
    explicit_code = _normalize_code_label(label)
    if explicit_code in {"PP3", "BP4"}:
        strength = _normalize_applied_strength(label) or _default_strength_for_code(explicit_code)
        return (explicit_code, strength) if strength is not None else None

    method = (_optional_text(row.get("calibration_method")) or "").lower()
    if "pp3/bp4" not in method:
        return None
    lowered = label.lower()
    if "damaging" in lowered:
        code = "PP3"
    elif "benign" in lowered:
        code = "BP4"
    else:
        return None
    strength = _normalize_applied_strength(label) or _default_strength_for_code(code)
    return (code, strength) if strength is not None else None


def _normalize_code_label(value: str) -> str | None:
    match = value.strip().upper().replace("-", "_").split("_", 1)
    code = match[0]
    return code if code in _ALL_CODE_SET else None


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
    return AcmgCriterionApplication(
        code=code,
        applied_strength=strength,
        evidence_value=application.evidence_value,
        threshold=application.threshold,
        source_db=application.source_db,
        source_version=application.source_version,
        svi_reference=application.svi_reference,
    )


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


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
