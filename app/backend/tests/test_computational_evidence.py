from __future__ import annotations

from decimal import Decimal

from app.schemas.run import (
    AcmgCriteriaScaffold,
    AcmgCriterion,
    ComputationalDeepDiveSection,
    ComputationalPredictorRow,
    DiseaseMechanismSection,
    ReportPayload,
    VariantSummaryRow,
)
from app.services.computational_evidence import build_computational_evidence_decision


def _payload(*, consequence: str = "missense_variant") -> ReportPayload:
    return ReportPayload(
        patient_id="test",
        variant_summary_rows=[
            VariantSummaryRow(
                gene="RPE65",
                transcript_hgvs="NM_000329.3:c.260A>G",
                genomic_hg38="1-68444869-T-C",
                consequence=consequence,
            )
        ],
    )


def _deep_dive(*rows: tuple[str, str]) -> ComputationalDeepDiveSection:
    return ComputationalDeepDiveSection(
        predictors=[
            ComputationalPredictorRow(
                name=name,
                score=score,
                source=name,
                version=f"{name}-test-v1",
                public_serialization_allowed=True,
            )
            for name, score in rows
        ]
    )


def _mechanism_context() -> tuple[DiseaseMechanismSection, dict[str, dict]]:
    section = DiseaseMechanismSection(
        primary_condition="RPE65-related retinal dystrophy",
        disease_ids=["MONDO:0018998"],
        gene_disease_validity="Definitive",
        mechanism="missense loss of function",
    )
    evidence_map = {
        "gene_disease": {
            "approved_symbol": "RPE65",
            "disease_ids": ["MONDO:0018998"],
            "missense_mechanism_applicable": True,
            "missense_mechanism_policy_version": "rpe65-profile-v1",
        }
    }
    return section, evidence_map


def test_revel_is_preselected_and_extreme_alternate_cannot_replace_it() -> None:
    mechanism, evidence_map = _mechanism_context()
    decision = build_computational_evidence_decision(
        payload=_payload(),
        evidence_map=evidence_map,
        disease_mechanism=mechanism,
        deep_dive=_deep_dive(("AlphaMissense", "0.999"), ("REVEL", "0.822")),
    )

    assert decision.selected_predictor_id == "revel"
    assert decision.calibration_id == "revel_pejaver_2022_capped"
    assert decision.evidence_code == "PP3"
    assert decision.calibration_points == Decimal("2")
    assert decision.evidence_points == Decimal("2")
    assert decision.evidence_label == "REVEL PP3 Moderate"
    assert decision.counted_status == "counted"
    assert decision.alternates[0].predictor_id == "alphamissense"
    assert decision.alternates[0].calibration_points == Decimal("4")
    assert decision.alternates[0].counted_status == "context_only"


def test_missing_revel_does_not_promote_an_alternate() -> None:
    mechanism, evidence_map = _mechanism_context()
    decision = build_computational_evidence_decision(
        payload=_payload(),
        evidence_map=evidence_map,
        disease_mechanism=mechanism,
        deep_dive=_deep_dive(("AlphaMissense", "0.999")),
    )

    assert decision.applicability == "unavailable"
    assert decision.selected_predictor_id == "revel"
    assert decision.evidence_points == Decimal("0")
    assert decision.evidence_label == "REVEL unavailable"
    assert decision.non_counted_reason == "selected_predictor_score_unavailable"


def test_alternate_without_explicit_public_policy_is_not_redisclosed() -> None:
    mechanism, evidence_map = _mechanism_context()
    deep_dive = _deep_dive(("REVEL", "0.822"), ("AlphaMissense", "0.999"))
    deep_dive.predictors[1].public_serialization_allowed = None
    decision = build_computational_evidence_decision(
        payload=_payload(),
        evidence_map=evidence_map,
        disease_mechanism=mechanism,
        deep_dive=deep_dive,
    )

    assert decision.selected_predictor_id == "revel"
    assert decision.evidence_points == Decimal("2")
    assert decision.alternates == []


def test_revel_is_context_only_without_versioned_missense_mechanism() -> None:
    mechanism = DiseaseMechanismSection(
        disease_ids=["MONDO:0018998"],
        gene_disease_validity="Definitive",
        mechanism="loss of function",
    )
    decision = build_computational_evidence_decision(
        payload=_payload(),
        evidence_map={"gene_disease": {"approved_symbol": "RPE65"}},
        disease_mechanism=mechanism,
        deep_dive=_deep_dive(("REVEL", "0.95")),
    )

    assert decision.applicability == "not_applicable"
    assert decision.calibration_points == Decimal("4")
    assert decision.evidence_points == Decimal("0")
    assert decision.counted_status == "context_only"
    assert decision.non_counted_reason == "missense_disease_mechanism_not_established"


def test_non_missense_variant_never_forces_revel() -> None:
    mechanism, evidence_map = _mechanism_context()
    decision = build_computational_evidence_decision(
        payload=_payload(consequence="splice_donor_variant"),
        evidence_map=evidence_map,
        disease_mechanism=mechanism,
        deep_dive=_deep_dive(("REVEL", "0.95"), ("SpliceAI", "0.80")),
    )

    assert decision.selected_predictor_id is None
    assert decision.evidence_family == "SPLICE"
    assert decision.applicability == "not_assessed"
    assert decision.counted_status == "separate_mechanism"


def test_pp3_pm1_dependency_caps_combined_pathogenic_points_at_four() -> None:
    mechanism, evidence_map = _mechanism_context()
    evidence_map["clinical_consensus"] = {
        "acmg_worksheet": {
            "criteria": [
                {
                    "code": "PM1",
                    "state": "met",
                    "strength": "Supporting",
                    "assertion_level": "source_asserted",
                }
            ]
        }
    }
    decision = build_computational_evidence_decision(
        payload=_payload(),
        evidence_map=evidence_map,
        disease_mechanism=mechanism,
        deep_dive=_deep_dive(("REVEL", "0.95")),
    )

    assert decision.calibration_points == Decimal("4")
    assert decision.evidence_points == Decimal("3")
    assert decision.warnings == ["pp3_points_capped_by_pm1_dependency_group"]


def test_unscored_scaffold_pm1_does_not_reduce_computational_evidence() -> None:
    mechanism, evidence_map = _mechanism_context()
    payload = _payload()
    payload.acmg_criteria_scaffold = AcmgCriteriaScaffold(
        criteria=[AcmgCriterion(code="PM1", verdict="met")]
    )
    decision = build_computational_evidence_decision(
        payload=payload,
        evidence_map=evidence_map,
        disease_mechanism=mechanism,
        deep_dive=_deep_dive(("REVEL", "0.95")),
    )

    assert decision.evidence_points == Decimal("4")
    assert decision.warnings == []


def test_decision_json_uses_canonical_decimal_strings() -> None:
    mechanism, evidence_map = _mechanism_context()
    decision = build_computational_evidence_decision(
        payload=_payload(),
        evidence_map=evidence_map,
        disease_mechanism=mechanism,
        deep_dive=_deep_dive(("REVEL", "0.8224")),
    )

    encoded = decision.model_dump(mode="json")
    assert encoded["raw_score"] == "0.8224"
    assert encoded["calibration_normalized_score"] == "0.822"
    assert encoded["evidence_points"] == "2"
    assert encoded["interval_lower"] == "0.773"


def test_source_policy_denial_prevents_selected_score_from_counting() -> None:
    mechanism, evidence_map = _mechanism_context()
    deep_dive = _deep_dive(("REVEL", "0.95"))
    deep_dive.predictors[0].public_serialization_allowed = False
    decision = build_computational_evidence_decision(
        payload=_payload(),
        evidence_map=evidence_map,
        disease_mechanism=mechanism,
        deep_dive=deep_dive,
    )

    assert decision.applicability == "unavailable"
    assert decision.raw_score is None
    assert decision.calibration_id is None
    assert decision.evidence_points == Decimal("0")
    assert decision.non_counted_reason == "source_policy_public_serialization_denied"


def test_missing_source_policy_decision_fails_closed_without_score_disclosure() -> None:
    mechanism, evidence_map = _mechanism_context()
    deep_dive = _deep_dive(("REVEL", "0.95"))
    deep_dive.predictors[0].public_serialization_allowed = None
    decision = build_computational_evidence_decision(
        payload=_payload(),
        evidence_map=evidence_map,
        disease_mechanism=mechanism,
        deep_dive=deep_dive,
    )

    assert decision.applicability == "unavailable"
    assert decision.raw_score is None
    assert decision.source_url is None
    assert decision.evidence_points == Decimal("0")
    assert decision.non_counted_reason == "source_policy_public_serialization_denied"
