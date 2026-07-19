from __future__ import annotations

from decimal import Decimal

import pytest

from app.schemas.run import (
    ComputationalEvidenceDecision,
    DiseaseMechanismSection,
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
    points_for_strength,
    posterior_from_net,
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
def test_posterior_anchors_match_tavtigian_formula(net_points, expected_percent):
    assert round(posterior_from_net(net_points) * 100, 1) == Decimal(expected_percent)


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
    assert result.posterior == Decimal("0.1")
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
    assert result.acmg_version_pin.pvs1_revision == PVS1_REVISION
    assert result.acmg_version_pin.pp3_calibration == PP3_CALIBRATION
    assert result.acmg_version_pin.vcep_id == "pilot-vcep"
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


def test_report_adapter_uses_typed_preselected_computational_decision():
    payload = ReportPayload(
        patient_id="lookup_test",
        report_profile=VariantReportProfile(
            computational_decision=ComputationalEvidenceDecision(
                ruleset_id="richards_2015_tavtigian_2020_eamos_v1",
                ruleset_version="eamos-current-v1",
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


def test_report_adapter_ignores_eamos_hint_rows_but_uses_source_asserted_rows():
    payload = ReportPayload(patient_id="lookup_test")
    evidence_map = {
        "clinical_consensus": {
            "acmg_worksheet": {
                "criteria": [
                    {
                        "code": "PM2",
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
    assert rows["PM2"].triggered is True
    assert rows["PM2"].source_db == "ClinVar VCV"
    assert rows["PM2"].svi_reference == "PMID:35901234"
    assert rows["PP3"].triggered is False
