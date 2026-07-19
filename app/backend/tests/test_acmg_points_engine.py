from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.schemas.run import (
    ComputationalEvidenceDecision,
    DiseaseMechanismSection,
    FunctionalAssayConfusionMatrix,
    FunctionalAssayValidation,
    FunctionalEvidenceAssertionCandidate,
    FunctionalEvidenceDisplayMetrics,
    FunctionalEvidenceSummary,
    GeneContextSnapshot,
    GeneContextTranscriptExon,
    GeneContextVariantProjection,
    MolecularContextSection,
    PopulationFrequencyDetail,
    ReportPayload,
    VariantReportHeader,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.services.acmg_points_engine import (
    ALL_ACMG_CODES,
    ACMG_FRAMEWORK,
    PP3_CALIBRATION,
    PVS1_REVISION,
    AcmgCriterionApplication,
    compute_acmg_points,
    compute_report_acmg_classification,
    model_posterior_from_net,
    points_for_strength,
    tier_from_net,
)
from app.services.computational_rulesets import active_ruleset


def _rows_by_code(result):
    return {row.code: row for row in result.per_criterion}


@pytest.mark.parametrize(
    ("net_points", "expected_percent"),
    [
        (0, "10.0"),
        (6, "90.0"),
        (9, "98.8"),
        (10, "99.4"),
        (-1, "5.1"),
        (-7, "0.1"),
    ],
)
def test_model_posterior_anchors_match_tavtigian_formula(net_points, expected_percent):
    assert round(model_posterior_from_net(net_points) * 100, 1) == Decimal(expected_percent)


@pytest.mark.parametrize(
    ("net_points", "expected_tier"),
    [
        (10, "Pathogenic"),
        (9, "Likely Pathogenic"),
        (6, "Likely Pathogenic"),
        (5, "VUS"),
        (0, "VUS"),
        (-1, "Likely Benign"),
        (-6, "Likely Benign"),
        (-7, "Benign"),
    ],
)
def test_tavtigian_tier_edges(net_points, expected_tier):
    assert tier_from_net(net_points, "tavtigian_2020") == expected_tier


def test_acgs_panel_uses_only_the_alternate_benign_cut():
    assert tier_from_net(-5, "acgs_panel") == "Likely Benign"
    assert tier_from_net(-6, "acgs_panel") == "Benign"


def test_strength_points_are_applied_per_criterion_direction():
    assert points_for_strength("pathogenic", "very_strong") == 8
    assert points_for_strength("pathogenic", "strong") == 4
    assert points_for_strength("pathogenic", "moderate") == 2
    assert points_for_strength("pathogenic", "supporting") == 1
    assert points_for_strength("benign", "strong") == -4
    assert points_for_strength("benign", "moderate") == -2
    assert points_for_strength("benign", "supporting") == -1


def test_mavedb_only_uncurated_measurements_cannot_activate_ps3_bs3_or_points():
    baseline = compute_report_acmg_classification(ReportPayload(patient_id="baseline"), {}, {})
    with_mavedb = compute_report_acmg_classification(
        ReportPayload(
            patient_id="with-mavedb",
            functional_evidence=FunctionalEvidenceSummary(
                total_count=2,
                evidence_codes=[],
                source_asserted_codes=[],
                display_metrics=FunctionalEvidenceDisplayMetrics(
                    state="uncurated",
                    primary_label="Functional Work Found - Not ACMG-graded",
                    acmg_badge_text="No code asserted",
                    verdict_source="uncurated",
                    study_count_badge_text="2 Unique",
                    ui_color_theme="neutral_slate_state",
                ),
            ),
        ),
        {},
        {},
    )

    assert with_mavedb.net_points == baseline.net_points
    assert with_mavedb.tier == baseline.tier
    rows = _rows_by_code(with_mavedb)
    assert rows["PS3"].triggered is False
    assert rows["PS3"].points == 0
    assert rows["BS3"].triggered is False
    assert rows["BS3"].points == 0


def test_source_asserted_functional_codes_remain_context_without_assay_validation():
    payload = ReportPayload(
        patient_id="functional-context-only",
        functional_evidence=FunctionalEvidenceSummary(
            total_count=1,
            evidence_codes=["PS3"],
            source_asserted_codes=["PS3_Moderate"],
        ),
        report_profile=VariantReportProfile(
            acmg_worksheet={
                "criteria": [
                    {
                        "code": "PS3",
                        "state": "met",
                        "strength": "Moderate",
                        "assertion_level": "source_asserted",
                        "source": "ClinGen CSpec",
                    }
                ]
            }
        ),
    )

    result = compute_report_acmg_classification(payload, {}, {})

    assert _rows_by_code(result)["PS3"].triggered is False
    assert result.net_points == 0
    assert "functional_source_assertions_context_only:assay_validation_missing" in result.warnings


def test_one_selected_validated_functional_assertion_can_contribute_once():
    payload = ReportPayload(
        patient_id="functional-counted",
        variant_summary_rows=[VariantSummaryRow(gene="RPE65")],
        functional_evidence=FunctionalEvidenceSummary(
            total_count=1,
            evidence_codes=["PS3"],
            source_asserted_codes=["PS3_Moderate"],
            assertion_candidates=[_functional_candidate()],
        ),
        report_profile=VariantReportProfile(
            header=VariantReportHeader(display_name="RPE65 query", gene="RPE65"),
            disease_mechanism=DiseaseMechanismSection(disease_ids=["MONDO:0100368"]),
            acmg_worksheet={
                "criteria": [
                    {
                        "code": "PM1",
                        "state": "met",
                        "strength": "Moderate",
                        "assertion_level": "source_asserted",
                        "source": "ClinGen CSpec",
                    }
                ]
            },
        ),
    )

    result = compute_report_acmg_classification(payload, {}, {})
    row = _rows_by_code(result)["PS3"]

    assert result.net_points == 4
    assert row.triggered is True
    assert row.applied_strength == "moderate"
    assert row.source_db == "clingen"
    assert row.policy_id == "clingen_svi_brnich_2020_v1"
    assert row.policy_version == "1.0.0"
    assert row.source_url == "https://cspec.clinicalgenome.org/cspec/ui/svi/doc/GN120"
    assert row.policy_source_url == ("https://cspec.clinicalgenome.org/cspec/ui/svi/doc/GN120")
    assert row.functional_assay_oddspath == Decimal("10")
    assert row.functional_assay_confidence_interval_lower == Decimal("5")
    assert row.functional_assay_confidence_interval_upper == Decimal("15")
    assert result.acmg_version_pin.cspec_overlay_id == "clingen_cspec_gn120_rpe65_v1"


def test_validated_functional_assertion_requires_independent_same_direction_evidence():
    payload = ReportPayload(
        patient_id="functional-dependency",
        variant_summary_rows=[VariantSummaryRow(gene="RPE65")],
        functional_evidence=FunctionalEvidenceSummary(
            total_count=1,
            evidence_codes=["PS3"],
            source_asserted_codes=["PS3_Moderate"],
            assertion_candidates=[_functional_candidate()],
        ),
        report_profile=VariantReportProfile(
            header=VariantReportHeader(display_name="RPE65 query", gene="RPE65"),
            disease_mechanism=DiseaseMechanismSection(disease_ids=["MONDO:0100368"]),
        ),
    )

    result = compute_report_acmg_classification(payload, {}, {})

    assert _rows_by_code(result)["PS3"].triggered is False
    assert result.net_points == 0
    assert (
        "functional_assertion_not_counted:PS3_independent_same_direction_evidence_missing"
        in result.warnings
    )


def test_multiple_selected_functional_assertions_fail_closed_without_stacking():
    candidates = [
        _functional_candidate(assertion_id="GN120:PS3:query-1", variant_id="query-1"),
        _functional_candidate(assertion_id="GN120:PS3:query-2", variant_id="query-2"),
    ]
    payload = ReportPayload(
        patient_id="functional-cardinality",
        variant_summary_rows=[VariantSummaryRow(gene="RPE65")],
        functional_evidence=FunctionalEvidenceSummary(
            total_count=2,
            evidence_codes=["PS3"],
            source_asserted_codes=["PS3_Moderate"],
            assertion_candidates=candidates,
        ),
        report_profile=VariantReportProfile(
            header=VariantReportHeader(display_name="RPE65 query", gene="RPE65"),
            disease_mechanism=DiseaseMechanismSection(disease_ids=["MONDO:0100368"]),
        ),
    )

    result = compute_report_acmg_classification(payload, {}, {})

    assert _rows_by_code(result)["PS3"].triggered is False
    assert result.net_points == 0
    assert "functional_assertion_not_counted:selected_candidate_cardinality" in result.warnings


def test_very_strong_plus_strong_is_pathogenic():
    result = compute_acmg_points(
        [
            AcmgCriterionApplication("PVS1", "very_strong"),
            AcmgCriterionApplication("PS3", "strong"),
        ]
    )

    assert result.sum_pathogenic == 12
    assert result.sum_benign == 0
    assert result.net_points == 12
    assert result.tier == "Pathogenic"
    assert result.ba1_override is False
    rows = _rows_by_code(result)
    assert rows["PVS1"].points == 8
    assert rows["PS3"].points == 4


def test_two_moderate_plus_one_supporting_is_vus():
    result = compute_acmg_points(
        [
            AcmgCriterionApplication("PM2", "moderate"),
            AcmgCriterionApplication("PM3", "moderate"),
            AcmgCriterionApplication("PP3", "supporting"),
        ]
    )

    assert result.sum_pathogenic == 5
    assert result.net_points == 5
    assert result.tier == "VUS"


def test_pvs1_plus_pm2_supporting_is_likely_pathogenic():
    result = compute_acmg_points(
        [
            AcmgCriterionApplication("PVS1", "very_strong"),
            AcmgCriterionApplication("PM2", "supporting"),
        ]
    )

    assert result.sum_pathogenic == 9
    assert result.net_points == 9
    assert result.tier == "Likely Pathogenic"


def test_ba1_hard_override_is_benign_and_not_a_summand():
    result = compute_acmg_points([AcmgCriterionApplication("BA1")])

    assert result.tier == "Benign"
    assert result.ba1_override is True
    assert result.net_points == 0
    assert result.sum_benign == 0
    assert result.classification_basis == "ba1_standalone_override"
    assert result.aggregate_evidence_likelihood_ratio is None
    assert result.prior_odds is None
    assert result.posterior_odds is None
    assert result.model_posterior is None
    row = _rows_by_code(result)["BA1"]
    assert row.triggered is True
    assert row.applied_strength is None
    assert row.points == 0


def test_conflicting_evidence_caps_the_tier_at_vus():
    result = compute_acmg_points(
        [
            AcmgCriterionApplication("PVS1", "very_strong"),
            AcmgCriterionApplication("PS4", "strong"),
        ],
        conflict_reason="curated pathogenic and benign assertions disagree",
    )

    assert result.net_points == 12
    assert result.tier == "VUS"
    assert result.classification_basis == "legacy_conflict_cap"
    assert result.conflict.is_conflicting is True
    assert result.conflict.reason == "curated pathogenic and benign assertions disagree"


@pytest.mark.parametrize(
    "applications",
    [
        [
            AcmgCriterionApplication("PM2", "supporting"),
            AcmgCriterionApplication("BA1"),
        ],
        [
            AcmgCriterionApplication("PP3", "supporting"),
            AcmgCriterionApplication("BP4", "supporting"),
        ],
        [
            AcmgCriterionApplication("PS3", "strong"),
            AcmgCriterionApplication("BS3", "strong"),
        ],
    ],
)
def test_mutually_exclusive_criteria_reject(applications):
    with pytest.raises(ValueError, match="mutually exclusive ACMG criteria co-fired"):
        compute_acmg_points(applications)


def test_deprecated_pp5_bp6_remain_audit_rows_but_cannot_trigger():
    result = compute_acmg_points([])
    rows = _rows_by_code(result)

    assert rows["PP5"].triggered is False
    assert rows["BP6"].triggered is False
    with pytest.raises(ValueError, match="deprecated ACMG criteria cannot be triggered"):
        compute_acmg_points([AcmgCriterionApplication("PP5", "supporting")])


def test_missing_strength_rejects_non_ba1_triggered_criterion():
    with pytest.raises(ValueError, match="PM2 requires applied_strength"):
        compute_acmg_points([AcmgCriterionApplication("PM2")])


def test_duplicate_criteria_reject_to_prevent_double_counting():
    with pytest.raises(ValueError, match="duplicate ACMG criterion applications: PM2"):
        compute_acmg_points(
            [
                AcmgCriterionApplication("PM2", "supporting"),
                AcmgCriterionApplication("PM2_Moderate", "moderate"),
            ]
        )


def test_explicit_three_point_application_stays_decimal_and_canonical_in_json():
    result = compute_acmg_points([AcmgCriterionApplication("PP3", evidence_points=Decimal("3"))])
    row = _rows_by_code(result)["PP3"]

    assert row.applied_strength is None
    assert row.points == Decimal("3")
    assert result.net_points == Decimal("3")
    encoded = result.model_dump(mode="json")
    assert encoded["net_points"] == "3"
    assert next(item for item in encoded["per_criterion"] if item["code"] == "PP3")["points"] == "3"


def test_fractional_application_stays_decimal_and_canonical_in_json():
    result = compute_acmg_points([AcmgCriterionApplication("PP3", evidence_points=Decimal("2.5"))])
    row = _rows_by_code(result)["PP3"]

    assert row.applied_strength is None
    assert row.points == Decimal("2.5")
    assert result.net_points == Decimal("2.5")
    encoded = result.model_dump(mode="json")
    assert encoded["net_points"] == "2.5"
    assert (
        next(item for item in encoded["per_criterion"] if item["code"] == "PP3")["points"] == "2.5"
    )


@pytest.mark.parametrize(
    ("points", "expected"),
    [
        (Decimal("10"), "Pathogenic"),
        (Decimal("9.9999999"), "Likely Pathogenic"),
        (Decimal("6"), "Likely Pathogenic"),
        (Decimal("5.9999999"), "VUS"),
        (Decimal("0"), "VUS"),
        (Decimal("-0.0000001"), "Likely Benign"),
        (Decimal("-6.9999999"), "Likely Benign"),
        (Decimal("-7"), "Benign"),
    ],
)
def test_ruleset_tier_intervals_cover_fractional_boundaries_once(points, expected):
    matching = [tier.label for tier in active_ruleset().tier_definitions if tier.contains(points)]

    assert matching == [expected]
    assert tier_from_net(points) == expected


def test_active_ruleset_pins_the_exact_source_document() -> None:
    ruleset = active_ruleset()

    assert ruleset.document_url.endswith("/PMC8011844/pdf/nihms-1681181.pdf")
    assert ruleset.document_checksum == (
        "sha256:2714eb28dda9188e4567377554ec829c8d62b442f3dfbed7dfb9a4fa763b8a01"
    )
    assert ruleset.functional_validation_policy_id == "clingen_svi_brnich_2020_v1"
    assert ruleset.functional_validation_policy_version == "1.0.0"


def test_pp3_pm1_dependency_cap_is_enforced_again_at_points_boundary():
    result = compute_acmg_points(
        [
            AcmgCriterionApplication("PM1", "supporting"),
            AcmgCriterionApplication("PP3", "strong"),
        ]
    )
    rows = _rows_by_code(result)

    assert rows["PM1"].points == Decimal("1")
    assert rows["PP3"].points == Decimal("3")
    assert rows["PP3"].applied_strength is None
    assert result.sum_pathogenic == Decimal("4")
    assert "pp3_points_capped_by_pm1_dependency_group" in result.warnings


@pytest.mark.parametrize(
    "application",
    [
        AcmgCriterionApplication("PP3", evidence_points=Decimal("-1")),
        AcmgCriterionApplication("BP4", evidence_points=Decimal("1")),
        AcmgCriterionApplication("PP3", evidence_points=Decimal("NaN")),
        AcmgCriterionApplication("PP3", "supporting", evidence_points=Decimal("2")),
    ],
)
def test_explicit_points_fail_closed_on_direction_finiteness_or_strength_drift(application):
    with pytest.raises(ValueError):
        compute_acmg_points([application])


def test_contract_emits_complete_rows_version_pin_and_source_fields():
    result = compute_acmg_points(
        [
            AcmgCriterionApplication(
                "pp3_supporting",
                "supporting",
                evidence_value=0.87,
                threshold=">=0.644",
                source_db="REVEL",
                source_version="Pejaver-2022",
                svi_reference="PMID:36413997",
            )
        ],
        vcep_id="pilot-vcep",
    )
    rows = _rows_by_code(result)

    assert [row.code for row in result.per_criterion] == list(ALL_ACMG_CODES)
    assert result.acmg_version_pin.framework == ACMG_FRAMEWORK
    assert result.acmg_version_pin.ruleset_id == active_ruleset().ruleset_id
    assert result.acmg_version_pin.ruleset_version == active_ruleset().framework_version
    assert result.acmg_version_pin.conflict_policy_id == "eamos_legacy_vus_cap"
    assert result.acmg_version_pin.pvs1_revision == PVS1_REVISION
    assert result.acmg_version_pin.pp3_calibration == PP3_CALIBRATION
    assert result.acmg_version_pin.vcep_id == "pilot-vcep"
    assert result.acmg_version_pin.population_policy_id == "acmg_svi_general_frequency_v1"
    assert result.classification_basis == "bayesian_points"
    assert result.aggregate_evidence_likelihood_ratio is not None
    assert round(result.prior_odds, 6) == Decimal("0.111111")
    assert result.posterior_odds is not None
    assert result.model_posterior is not None
    assert rows["PP3"].triggered is True
    assert rows["PP3"].points == 1
    assert rows["PP3"].evidence_value == 0.87
    assert rows["PP3"].threshold == ">=0.644"
    assert rows["PP3"].source_db == "REVEL"
    assert rows["PP3"].source_version == "Pejaver-2022"
    assert rows["PP3"].svi_reference == "PMID:36413997"
    assert rows["BP4"].triggered is False
    assert rows["BP4"].points == 0


def test_report_adapter_derives_ba1_override_from_high_population_frequency():
    payload = ReportPayload(
        patient_id="lookup_test",
        population_frequency_detail=PopulationFrequencyDetail(
            source="gnomAD",
            dataset="gnomad_r4",
            variant_id="1-1-A-G",
            allele_frequency=0.061,
            allele_count=61,
            allele_number=1000,
        ),
    )

    result = compute_report_acmg_classification(payload, {}, {})
    rows = _rows_by_code(result)

    assert result.tier == "Benign"
    assert result.ba1_override is True
    assert result.net_points == 0
    assert rows["BA1"].triggered is True
    assert rows["BA1"].points == 0
    assert rows["BA1"].policy_id == "acmg_svi_general_frequency_v1"
    assert result.acmg_version_pin.population_policy_id == "acmg_svi_general_frequency_v1"
    assert result.acmg_version_pin.cspec_overlay_id is None
    assert rows["BA1"].source_db == "gnomAD"
    assert rows["PM2"].triggered is False


def test_report_adapter_derives_bs1_but_not_ba1_from_intermediate_frequency():
    payload = ReportPayload(
        patient_id="lookup_test",
        population_frequency_detail=PopulationFrequencyDetail(
            source="gnomAD",
            dataset="gnomad_r4",
            variant_id="1-1-A-G",
            allele_frequency=0.015,
            allele_count=15,
            allele_number=1000,
        ),
    )

    result = compute_report_acmg_classification(payload, {}, {})
    rows = _rows_by_code(result)

    assert result.tier == "Likely Benign"
    assert result.net_points == -4
    assert rows["BS1"].triggered is True
    assert rows["BS1"].applied_strength == "strong"
    assert rows["BA1"].triggered is False


def test_report_adapter_applies_exact_rpe65_cspec_population_overlay():
    payload = ReportPayload(
        patient_id="lookup_test",
        variant_summary_rows=[VariantSummaryRow(gene="RPE65")],
        population_frequency_detail=PopulationFrequencyDetail(
            source="gnomAD",
            dataset="gnomad_r4",
            variant_id="1-1-A-G",
            allele_frequency=0.001,
            popmax_frequency=0.009,
            source_url="https://gnomad.broadinstitute.org/variant/1-1-A-G?dataset=gnomad_r4",
        ),
        report_profile=VariantReportProfile(
            header=VariantReportHeader(display_name="RPE65 query", gene="RPE65"),
            disease_mechanism=DiseaseMechanismSection(disease_ids=["MONDO:0100368"]),
        ),
    )

    result = compute_report_acmg_classification(payload, {}, {})
    row = _rows_by_code(result)["BA1"]

    assert result.tier == "Benign"
    assert row.triggered is True
    assert row.threshold == ">=0.008"
    assert row.policy_id == "clingen_cspec_gn120_rpe65_frequency_v1"
    assert row.cspec_overlay_id == "clingen_cspec_gn120_rpe65_v1"
    assert row.source_url == ("https://gnomad.broadinstitute.org/variant/1-1-A-G?dataset=gnomad_r4")
    assert row.policy_source_url == "https://cspec.clinicalgenome.org/cspec/ui/svi/doc/GN120"
    assert result.acmg_version_pin.population_policy_id == (
        "clingen_cspec_gn120_rpe65_frequency_v1"
    )
    assert result.acmg_version_pin.cspec_overlay_version == "1.0.0"
    assert {
        (item.field, item.general_value, item.overlay_value)
        for item in result.acmg_version_pin.population_policy_diff
    } >= {
        ("ba1_minimum", "0.05", "0.008"),
        ("bs1_minimum", "0.01", "0.0008"),
        ("pm2_maximum", "0.0001", "0.0002"),
    }


def test_report_adapter_requires_popmax_faf_before_applying_exact_cspec_thresholds():
    payload = ReportPayload(
        patient_id="lookup_test",
        variant_summary_rows=[VariantSummaryRow(gene="RPE65")],
        population_frequency_detail=PopulationFrequencyDetail(
            source="gnomAD",
            dataset="gnomad_r4",
            variant_id="1-1-A-G",
            allele_frequency=0.009,
        ),
        report_profile=VariantReportProfile(
            header=VariantReportHeader(display_name="RPE65 query", gene="RPE65"),
            disease_mechanism=DiseaseMechanismSection(disease_ids=["MONDO:0100368"]),
        ),
    )

    result = compute_report_acmg_classification(payload, {}, {})
    rows = _rows_by_code(result)

    assert rows["BA1"].triggered is False
    assert rows["BS1"].triggered is False
    assert rows["PM2"].triggered is False
    assert "population_cspec_not_applied:popmax_faf_missing" in result.warnings


def test_report_adapter_uses_typed_preselected_computational_decision():
    payload = ReportPayload(
        patient_id="lookup_test",
        report_profile=VariantReportProfile(
            computational_decision=ComputationalEvidenceDecision(
                ruleset_id="richards_2015_tavtigian_2020_eamos_v1",
                ruleset_version="eamos-historical-replay-v1",
                standard_label="Richards-2015 + Tavtigian-2020 points",
                standard_status="published",
                application_id="computational:test",
                variant_scope="missense",
                mechanism_applicability="applicable:test-v1",
                evidence_family="PP3_BP4",
                selected_predictor_id="revel",
                selection_policy="eamos_preselected_predictor_policy_v1",
                selection_rationale="REVEL was selected before score evaluation.",
                declared_fallback_policy="none",
                applicability="applicable",
                raw_score=Decimal("0.780"),
                calibration_normalized_score=Decimal("0.780"),
                evidence_code="PP3",
                calibration_points=Decimal("2"),
                evidence_points=Decimal("2"),
                evidence_label="REVEL PP3 Moderate",
                calibration_id="revel_pejaver_2022_capped",
                calibration_version="eamos-revel-capped-v1+PMID:36413997",
                interval_lower=Decimal("0.773"),
                interval_lower_inclusive=True,
                interval_upper=Decimal("0.932"),
                interval_upper_inclusive=False,
                dependency_group="computational_regional_pathogenic_cap_4",
                counted_status="counted",
                source_version="REVEL v1.3",
            )
        ),
    )

    result = compute_report_acmg_classification(payload, {}, {})
    row = _rows_by_code(result)["PP3"]

    assert result.net_points == 2
    assert row.triggered is True
    assert row.applied_strength == "moderate"
    assert row.points == 2
    assert row.source_db == "REVEL"
    assert row.source_version == "REVEL v1.3"
    assert row.svi_reference == "eamos-revel-capped-v1+PMID:36413997"
    assert row.threshold == "[0.773, 0.932)"

    decision = payload.report_profile.computational_decision
    payload.report_profile.computational_decision = decision.model_copy(
        update={"ruleset_version": "unpublished-drift"}
    )
    drifted = compute_report_acmg_classification(payload, {}, {})
    assert _rows_by_code(drifted)["PP3"].triggered is False


def test_report_adapter_never_scores_legacy_predictor_labels_without_a_typed_decision():
    payload = ReportPayload(patient_id="lookup_test")
    evidence_map = {
        "computational_annotations": {
            "predictors": [
                {
                    "name": "AlphaMissense",
                    "score": "0.999",
                    "calibrated_label": "PP3 Strong",
                    "calibration_method": "PP3/BP4",
                },
                {
                    "name": "REVEL",
                    "score": "0.95",
                    "calibrated_label": "PP3 Strong",
                    "calibration_method": "PP3/BP4",
                },
            ]
        }
    }

    result = compute_report_acmg_classification(payload, evidence_map, {})

    assert result.net_points == Decimal("0")
    assert _rows_by_code(result)["PP3"].triggered is False


def test_report_adapter_warns_when_recessive_case_context_criteria_are_not_scored():
    payload = ReportPayload(patient_id="lookup_test")
    evidence_map = {
        "gene_disease": {
            "primary_condition": "ABCA4-related retinopathy",
            "inheritance": "AR",
            "conditions": [
                {
                    "name": "ABCA4-related retinopathy",
                    "inheritance": "AR",
                    "validity": "Definitive",
                }
            ],
        }
    }

    result = compute_report_acmg_classification(payload, evidence_map, {})
    rows = _rows_by_code(result)

    assert rows["PM3"].triggered is False
    assert rows["PP4"].triggered is False
    limitations = {item.code: item for item in result.limitations}
    assert limitations["PM3"].missing_inputs == ["affected_status", "second_allele", "phase"]
    assert limitations["PM3"].applies_when == ["recessive_gene_disease"]
    assert limitations["PM3"].message.startswith("PM3 requires affected case context")
    assert limitations["PP4"].missing_inputs == [
        "phenotype_specificity",
        "test_scope",
        "alternative_cause_exclusion",
    ]
    assert limitations["PP4"].applies_when == ["gene_disease_context"]
    assert limitations["PP4"].message.startswith("PP4 requires phenotype specificity")
    assert "acmg_case_context_not_scored:PM3_phase_in_trans_required" in result.warnings
    assert "acmg_case_context_not_scored:PP4_phenotype_specificity_required" in result.warnings


def test_report_adapter_does_not_emit_pm3_limitation_for_dominant_context():
    payload = ReportPayload(patient_id="lookup_test")
    evidence_map = {
        "gene_disease": {
            "primary_condition": "Dominant retinal dystrophy",
            "inheritance": "AD",
        }
    }

    result = compute_report_acmg_classification(payload, evidence_map, {})

    assert {item.code for item in result.limitations} == {"PP4"}
    assert "acmg_case_context_not_scored:PM3_phase_in_trans_required" not in result.warnings
    assert "acmg_case_context_not_scored:PP4_phenotype_specificity_required" in result.warnings


def test_report_adapter_source_asserted_case_context_suppresses_pm3_pp4_warnings():
    payload = ReportPayload(patient_id="lookup_test")
    evidence_map = {
        "gene_disease": {
            "primary_condition": "ABCA4-related retinopathy",
            "inheritance": "AR",
        },
        "clinical_consensus": {
            "acmg_worksheet": {
                "criteria": [
                    {
                        "code": "PM3",
                        "state": "met",
                        "strength": "Moderate",
                        "assertion_level": "source_asserted",
                        "source": "ABCA4 VCEP case review",
                        "evidence_refs": ["phase:confirmed_in_trans"],
                    },
                    {
                        "code": "PP4",
                        "state": "met",
                        "strength": "Supporting",
                        "assertion_level": "source_asserted",
                        "source": "ABCA4 VCEP case review",
                        "evidence_refs": ["phenotype_score:3-7.5"],
                    },
                ]
            }
        },
    }

    result = compute_report_acmg_classification(payload, evidence_map, {})
    rows = _rows_by_code(result)

    assert result.net_points == 3
    assert rows["PM3"].triggered is True
    assert rows["PP4"].triggered is True
    assert result.limitations == []
    assert "acmg_case_context_not_scored:PM3_phase_in_trans_required" not in result.warnings
    assert "acmg_case_context_not_scored:PP4_phenotype_specificity_required" not in result.warnings


def test_report_adapter_uses_pvs1_only_when_lof_context_supports_nmd():
    payload = ReportPayload(
        patient_id="lookup_test",
        variant_summary_rows=[
            VariantSummaryRow(gene="TEST", consequence="stop_gained"),
        ],
        report_profile=VariantReportProfile(
            header=VariantReportHeader(
                display_name="TEST c.1A>T", gene="TEST", transcript="NM_000000.1"
            ),
            disease_mechanism=DiseaseMechanismSection(mechanism="loss of function"),
            molecular_context=MolecularContextSection(
                clingen_haploinsufficiency="Sufficient Evidence for Haploinsufficiency (3)"
            ),
            gene_context_snapshot=GeneContextSnapshot(
                gene="TEST",
                variant=GeneContextVariantProjection(exon_number=2),
                exons=[
                    GeneContextTranscriptExon(number=1),
                    GeneContextTranscriptExon(number=2),
                    GeneContextTranscriptExon(number=3),
                    GeneContextTranscriptExon(number=4),
                    GeneContextTranscriptExon(number=5),
                ],
            ),
        ),
    )

    result = compute_report_acmg_classification(payload, {}, {"sequence_context": "fixture"})
    row = _rows_by_code(result)["PVS1"]

    assert row.triggered is True
    assert row.applied_strength == "strong"
    assert row.points == 4
    assert row.source_db == "EAMOS PVS1/NMD decision support"
    assert row.source_version == "fixture"


def test_report_adapter_ignores_eamos_hint_rows_but_uses_admissible_source_asserted_rows():
    payload = ReportPayload(patient_id="lookup_test")
    evidence_map = {
        "clinical_consensus": {
            "acmg_worksheet": {
                "criteria": [
                    {
                        "code": "PM1",
                        "state": "met",
                        "strength": "Moderate",
                        "assertion_level": "source_asserted",
                        "source": "ClinVar VCV",
                        "evidence_refs": ["PMID:35901234"],
                    },
                    {
                        "code": "PP3",
                        "state": "met",
                        "strength": "Supporting",
                        "assertion_level": "eamos_hint",
                        "source": "Eamos worksheet scaffold",
                    },
                ]
            }
        }
    }

    result = compute_report_acmg_classification(payload, evidence_map, {})
    rows = _rows_by_code(result)

    assert result.net_points == 2
    assert rows["PM1"].triggered is True
    assert rows["PM1"].source_db == "ClinVar VCV"
    assert rows["PM1"].svi_reference == "PMID:35901234"
    assert rows["PP3"].triggered is False


def test_report_adapter_does_not_count_untyped_source_asserted_population_codes():
    payload = ReportPayload(patient_id="lookup_test")
    evidence_map = {
        "clinical_consensus": {
            "acmg_worksheet": {
                "criteria": [
                    {
                        "code": "PM2",
                        "state": "met",
                        "strength": "Supporting",
                        "assertion_level": "source_asserted",
                        "source": "ClinVar VCV",
                        "evidence_refs": ["PMID:35901234"],
                    }
                ]
            }
        }
    }

    result = compute_report_acmg_classification(payload, evidence_map, {})

    assert _rows_by_code(result)["PM2"].triggered is False
    assert result.net_points == 0


def _functional_candidate(
    *,
    assertion_id: str = "GN120:PS3:query-variant",
    variant_id: str = "query-variant",
) -> FunctionalEvidenceAssertionCandidate:
    validation = FunctionalAssayValidation(
        validation_id="rpe65-isomerohydrolase-calibration",
        validation_version="1.0.0",
        validation_policy_id="clingen_svi_brnich_2020_v1",
        validation_policy_version="1.0.0",
        status="published",
        gene_id="HGNC:10294",
        disease_id="MONDO:0100368",
        disease_mechanism="Biallelic loss of RPE65 isomerohydrolase activity",
        assay_name="RPE65 isomerohydrolase activity",
        assay_relevance="Measures the disease-relevant enzymatic mechanism",
        pathogenic_truth_variant_ids=[f"truth-path-{index}" for index in range(1, 11)],
        benign_truth_variant_ids=[f"truth-benign-{index}" for index in range(1, 11)],
        evaluation_variant_ids=[variant_id],
        truth_set_independence_basis="Truth variants were classified without this assay",
        truth_evaluation_overlap_rejected=True,
        circularity_reviewed=True,
        confusion_matrix=FunctionalAssayConfusionMatrix(
            pathogenic_abnormal=10,
            pathogenic_normal=0,
            benign_abnormal=0,
            benign_normal=10,
        ),
        pseudocount_policy="brnich_2020_one_discordant_control",
        pseudocount=Decimal("1"),
        direction="pathogenic",
        functional_assay_oddspath=Decimal("10"),
        confidence_interval_lower=Decimal("5"),
        confidence_interval_upper=Decimal("15"),
        maximum_supported_strength="moderate",
        curator="ClinGen VCEP curator",
        validation_date=date(2023, 8, 10),
        source_url="https://cspec.clinicalgenome.org/cspec/ui/svi/doc/GN120",
        source_version="RPE65 CSpec 1.0.0",
    )
    return FunctionalEvidenceAssertionCandidate(
        assertion_id=assertion_id,
        code="PS3",
        applied_strength="moderate",
        variant_id=variant_id,
        gene_id="HGNC:10294",
        disease_id="MONDO:0100368",
        source_id="clingen",
        source_record_id="GN120",
        source_version="1.0.0",
        source_url="https://cspec.clinicalgenome.org/cspec/ui/svi/doc/GN120",
        selected_for_counting=True,
        selection_rationale="Best validated disease-mechanism assay",
        validation=validation,
    )
