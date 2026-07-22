from __future__ import annotations

from decimal import Decimal

import pytest

from app.schemas.run import (
    AcmgCriteriaScaffold,
    AcmgCriterion,
    ComputationalAlternate,
    ComputationalEvidenceDecision,
    FunctionalEvidenceDisplayMetrics,
    FunctionalEvidenceSummary,
    InSilicoPredictions,
    PopulationFrequencyDetail,
    PredictorCard,
    ReportPayload,
    VariantReportProfile,
)
from app.services.report_call_cards import build_variant_report_call_cards


def _call_card(
    payload: ReportPayload,
    card_id: str,
    evidence_map: dict | None = None,
    evidence_statuses: dict | None = None,
) -> dict:
    cards = build_variant_report_call_cards(
        payload,
        evidence_map or {},
        evidence_statuses or {"gnomad": "fixture"},
    )
    return next(card for card in cards.model_dump()["cards"] if card["card_id"] == card_id)


def _population_card(payload: ReportPayload, evidence_map: dict | None = None) -> dict:
    return _call_card(payload, "population_frequency", evidence_map)


def _decision(**updates) -> ComputationalEvidenceDecision:
    values = {
        "ruleset_id": "richards_2015_tavtigian_2020_eamos_v1",
        "ruleset_version": "eamos-historical-replay-v1",
        "standard_label": "Richards-2015 + Tavtigian-2020 points",
        "standard_status": "published",
        "application_id": "computational:test",
        "variant_scope": "missense",
        "mechanism_applicability": "applicable:test-v1",
        "evidence_family": "PP3_BP4",
        "selected_predictor_id": "revel",
        "selection_policy": "eamos_preselected_predictor_policy_v1",
        "selection_rationale": "REVEL was selected before score evaluation.",
        "declared_fallback_policy": "none",
        "applicability": "applicable",
        "raw_score": Decimal("0.780"),
        "calibration_normalized_score": Decimal("0.780"),
        "evidence_code": "PP3",
        "calibration_points": Decimal("2"),
        "evidence_points": Decimal("2"),
        "evidence_label": "REVEL PP3 Moderate",
        "calibration_id": "revel_pejaver_2022_capped",
        "calibration_version": "eamos-revel-capped-v1+PMID:36413997",
        "dependency_group": "computational_regional_pathogenic_cap_4",
        "counted_status": "counted",
    }
    values.update(updates)
    return ComputationalEvidenceDecision(**values)


def test_mavedb_only_measurements_keep_lab_call_card_neutral() -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        functional_evidence=FunctionalEvidenceSummary(
            total_count=2,
            display_metrics=FunctionalEvidenceDisplayMetrics(
                state="uncurated",
                primary_label="Functional Work Found - Not ACMG-graded",
                acmg_badge_text="No code asserted",
                verdict_source="uncurated",
                study_count_badge_text="2 Unique",
                ui_color_theme="neutral_slate_state",
            ),
        ),
    )

    card = _call_card(
        payload,
        "lab_functional",
        evidence_statuses={"mavedb": "fixture"},
    )

    assert card["ui_color_theme"] == "neutral_slate_state"
    assert {badge["text"] for badge in card["support_badges"]} == {
        "No code asserted",
        "2 Unique",
    }
    assert not {"PS3", "BS3"}.intersection(badge["text"] for badge in card["support_badges"])


def test_population_card_does_not_infer_acmg_badge_from_raw_frequency_only() -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        population_frequency_detail=PopulationFrequencyDetail(
            dataset="gnomad_r4",
            variant_id="1-123-A-G",
            allele_frequency=0.06,
            allele_count=120,
            allele_number=2000,
            popmax_frequency=0.07,
            popmax_population="nfe",
        ),
    )

    card = _population_card(payload)

    assert {badge["text"] for badge in card["support_badges"]} >= {"None", "AC 120"}
    assert "BA1" not in {badge["text"] for badge in card["support_badges"]}
    assert "BS1" not in {badge["text"] for badge in card["support_badges"]}
    assert card["primary_label"] == "Very Common (7.00% max AF)"


def test_population_card_distinguishes_bs1_frequency_label() -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        population_frequency_detail=PopulationFrequencyDetail(
            dataset="gnomad_r4",
            variant_id="1-123-A-G",
            allele_frequency=0.02,
            allele_count=40,
            allele_number=2000,
            popmax_frequency=0.02,
            popmax_population="nfe",
        ),
    )

    card = _population_card(payload)

    assert card["primary_label"] == "Common (2.00% max AF)"


def test_population_card_no_data_provenance_reflects_source_status() -> None:
    payload = ReportPayload(patient_id="lookup_test")

    fixture_card = _call_card(
        payload,
        "population_frequency",
        evidence_statuses={"gnomad": "fixture"},
    )
    missing_card = _call_card(
        payload,
        "population_frequency",
        evidence_statuses={"gnomad": "missing"},
    )

    assert fixture_card["provenance"] == ["gnomAD fixture"]
    assert missing_card["provenance"] == ["gnomAD unavailable"]
    assert fixture_card["provenance"] != ["gnomAD GraphQL"]


def test_population_card_can_show_explicit_eamos_frequency_hint_badge() -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        population_frequency_detail=PopulationFrequencyDetail(
            dataset="gnomad_r4",
            variant_id="1-123-A-G",
            allele_frequency=0.0,
            allele_count=0,
            allele_number=2000,
        ),
        acmg_criteria_scaffold=AcmgCriteriaScaffold(
            criteria=[
                AcmgCriterion(code="PM2", verdict="met", note="Reviewed rare-frequency hint.")
            ]
        ),
    )

    card = _population_card(payload)

    assert {badge["text"] for badge in card["support_badges"]} >= {"PM2", "AC 0"}


def test_population_card_prefers_source_asserted_frequency_badge() -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        population_frequency_detail=PopulationFrequencyDetail(
            dataset="gnomad_r4",
            variant_id="1-123-A-G",
            allele_frequency=0.0,
            allele_count=0,
            allele_number=2000,
        ),
    )
    evidence_map = {
        "clinical_consensus": {
            "acmg_worksheet": {
                "criteria": [
                    {
                        "code": "PM2",
                        "state": "met",
                        "assertion_level": "source_asserted",
                    }
                ]
            }
        }
    }

    card = _call_card(
        payload,
        "population_frequency",
        evidence_map,
        {"gnomad": "fixture", "clinical_consensus": "fixture"},
    )

    assert {badge["text"] for badge in card["support_badges"]} >= {"PM2", "AC 0"}


def test_computational_card_prefers_source_labeled_annotation_metrics() -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        in_silico_predictions=InSilicoPredictions(
            consensus_note="Legacy fixture values should not win.",
            cards=[
                PredictorCard(
                    name="REVEL",
                    score=0.82,
                    threshold=0.75,
                    verdict="damaging",
                ),
                PredictorCard(
                    name="MetaLR",
                    score=0.78,
                    threshold=0.5,
                    verdict="damaging",
                ),
            ],
        ),
        acmg_criteria_scaffold=AcmgCriteriaScaffold(
            criteria=[AcmgCriterion(code="PP3", verdict="met", note="Source-supported.")]
        ),
    )
    evidence_map = {
        "computational_annotations": {
            # Legacy callers may still send this retired access-policy field.
            # It must not hide a returned predictor from the free catalog.
            "excluded_predictors": ["REVEL", "CADD PHRED", "MetaLR"],
            "predictors": [
                {"name": "REVEL", "score": 0.78, "threshold": 0.5},
                {"name": "CADD PHRED", "score": 23.4, "threshold": 20.0},
                {"name": "MetaLR", "score": 0.62, "threshold": 0.5},
            ],
            "spliceai": {"max_delta": 0.12, "threshold": 0.2},
            "warnings": ["computational_annotations_fixture_snapshot"],
        }
    }

    card = _call_card(
        payload,
        "computational",
        evidence_map,
        {"computational_annotations": "fixture", "spliceai": "fixture", "vep": "fixture"},
    )

    badge_text = [badge["text"] for badge in card["support_badges"]]
    assert card["primary_label"] == "Damaging"
    assert badge_text == ["REVEL: 0.78", "CADD PHRED: 23.4", "PP3"]
    assert "REVEL: 0.82" not in badge_text
    assert "MetaLR: 0.78" not in badge_text
    assert card["source_status"] == "fixture"
    assert card["warnings"] == ["computational_annotations_fixture_snapshot"]


def test_computational_card_does_not_upgrade_fallback_annotations_to_live() -> None:
    payload = ReportPayload(patient_id="lookup_test")
    evidence_map = {
        "computational_annotations": {
            "predictors": [{"name": "REVEL", "score": 0.78, "threshold": 0.5}],
            "warnings": ["computational_annotations_fixture_snapshot"],
        }
    }

    card = _call_card(
        payload,
        "computational",
        evidence_map,
        {"computational_annotations": "fallback", "spliceai": "missing", "vep": "live"},
    )

    assert card["source_status"] == "fallback"
    assert card["warnings"] == ["computational_annotations_fixture_snapshot"]


@pytest.mark.parametrize(
    ("decision", "label", "theme", "badges"),
    [
        (
            _decision(
                raw_score=Decimal("0.950"),
                calibration_normalized_score=Decimal("0.950"),
                calibration_points=Decimal("4"),
                evidence_points=Decimal("4"),
                evidence_label="REVEL PP3 Strong",
            ),
            "REVEL · PP3 Strong",
            "danger_red_state",
            ["Score 0.95", "PP3", "+4 points"],
        ),
        (
            _decision(),
            "REVEL · PP3 Moderate",
            "caution_orange_state",
            ["Score 0.78", "PP3", "+2 points"],
        ),
        (
            _decision(
                raw_score=Decimal("0.500"),
                calibration_normalized_score=Decimal("0.500"),
                evidence_code=None,
                calibration_points=Decimal("0"),
                evidence_points=Decimal("0"),
                evidence_label="REVEL Indeterminate",
                counted_status="context_only",
            ),
            "REVEL · Indeterminate",
            "neutral_slate_state",
            ["Score 0.5", "No PP3/BP4", "0 points"],
        ),
        (
            _decision(
                raw_score=Decimal("0.100"),
                calibration_normalized_score=Decimal("0.100"),
                evidence_code="BP4",
                calibration_points=Decimal("-1"),
                evidence_points=Decimal("-1"),
                evidence_label="REVEL BP4 Supporting",
            ),
            "REVEL · BP4 Supporting",
            "support_green_state",
            ["Score 0.1", "BP4", "-1 point"],
        ),
        (
            _decision(
                raw_score=Decimal("0.010"),
                calibration_normalized_score=Decimal("0.010"),
                evidence_code="BP4",
                calibration_points=Decimal("-2"),
                evidence_points=Decimal("-2"),
                evidence_label="REVEL BP4 Moderate",
            ),
            "REVEL · BP4 Moderate",
            "benign_green_state",
            ["Score 0.01", "BP4", "-2 points"],
        ),
        (
            _decision(
                raw_score=None,
                calibration_normalized_score=None,
                evidence_code=None,
                calibration_points=None,
                evidence_points=Decimal("0"),
                evidence_label="REVEL unavailable",
                calibration_id=None,
                calibration_version=None,
                applicability="unavailable",
                counted_status="rejected",
            ),
            "REVEL unavailable",
            "neutral_slate_state",
            ["Score unavailable", "No PP3/BP4", "0 points"],
        ),
        (
            _decision(
                evidence_points=Decimal("0"),
                evidence_label="REVEL not applicable",
                applicability="not_applicable",
                counted_status="context_only",
            ),
            "REVEL not applicable",
            "neutral_slate_state",
            ["Score 0.78", "PP3", "0 points"],
        ),
    ],
)
def test_computational_card_uses_typed_selected_evidence_decision(
    decision: ComputationalEvidenceDecision,
    label: str,
    theme: str,
    badges: list[str],
) -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        report_profile=VariantReportProfile(computational_decision=decision),
    )

    card = _call_card(
        payload,
        "computational",
        {"computational_annotations": {"warnings": ["fixture_warning"]}},
        {"computational_annotations": "fixture"},
    )

    assert card["primary_label"] == label
    assert card["ui_color_theme"] == theme
    assert [badge["text"] for badge in card["support_badges"]] == badges
    assert card["source_status"] == "fixture"
    assert card["warnings"] == ["fixture_warning"]
    assert card["provenance"] == [
        "REVEL selected by Eamos policy · "
        + (f"{decision.calibration_version} · " if decision.calibration_version else "")
        + "Richards-2015 + Tavtigian-2020 points (eamos-historical-replay-v1)"
    ]


def test_computational_card_theme_ignores_extreme_alternate_scores() -> None:
    decision = _decision(
        raw_score=Decimal("0.500"),
        calibration_normalized_score=Decimal("0.500"),
        evidence_code=None,
        evidence_points=Decimal("0"),
        evidence_label="REVEL Indeterminate",
        counted_status="context_only",
        alternates=[
            ComputationalAlternate(
                predictor_id="alphamissense",
                raw_score=Decimal("0.999"),
                counted_status="context_only",
            )
        ],
    )
    payload = ReportPayload(
        patient_id="lookup_test",
        report_profile=VariantReportProfile(computational_decision=decision),
    )

    card = _call_card(
        payload,
        "computational",
        evidence_statuses={"computational_annotations": "fixture"},
    )

    assert card["primary_label"] == "REVEL · Indeterminate"
    assert card["ui_color_theme"] == "neutral_slate_state"


def test_lab_functional_card_status_includes_clingen_backed_evidence() -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        functional_evidence=FunctionalEvidenceSummary(total_count=1),
    )

    card = _call_card(
        payload,
        "lab_functional",
        evidence_statuses={"clingen": "fixture", "clinvar": "missing", "pubmed": "missing"},
    )

    assert card["source_status"] == "partial"


def test_cached_functional_payload_is_suppressed_when_all_sources_are_weak() -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        functional_evidence=FunctionalEvidenceSummary(
            total_count=2,
            display_metrics=FunctionalEvidenceDisplayMetrics(
                state="uncurated",
                primary_label="Fixture functional finding",
                acmg_badge_text="No code asserted",
                verdict_source="uncurated",
                study_count_badge_text="2 Unique",
                ui_color_theme="neutral_slate_state",
            ),
        ),
    )

    card = _call_card(
        payload,
        "lab_functional",
        evidence_statuses={"clingen": "fallback", "clinvar": "failed", "pubmed": "missing"},
    )

    assert card["primary_label"] == "No Functional Data Available"
    assert {badge["text"] for badge in card["support_badges"]} == {"0 Unique"}
    assert "functional_evidence_sources_unavailable" in card["warnings"]


def test_legacy_predictor_payload_is_suppressed_without_explicit_fixture_status() -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        in_silico_predictions=InSilicoPredictions(
            consensus_note="Fixture values",
            cards=[
                PredictorCard(
                    name="REVEL",
                    score=0.99,
                    threshold=0.75,
                    verdict="damaging",
                )
            ],
        ),
    )

    card = _call_card(
        payload,
        "computational",
        evidence_statuses={"spliceai": "fallback", "vep": "missing"},
    )

    assert card["primary_label"] == "No Computational Data"
    assert "legacy_computational_fixture_payload_suppressed" in card["warnings"]


def test_clinical_consensus_card_does_not_claim_unavailable_sources() -> None:
    payload = ReportPayload(patient_id="lookup_test")

    card = _call_card(
        payload,
        "clinical_consensus",
        evidence_map={
            "clinical_consensus": {"classification": "Pathogenic"},
            "clinvar": {"classification": "Pathogenic"},
        },
        evidence_statuses={"clinical_consensus": "fallback", "clinvar": "failed"},
    )

    assert card["primary_label"] == "Unavailable"
    assert card["provenance"] == ["Clinical consensus sources unavailable"]
