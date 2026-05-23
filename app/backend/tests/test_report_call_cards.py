from __future__ import annotations

from app.schemas.run import (
    AcmgCriteriaScaffold,
    AcmgCriterion,
    FunctionalEvidenceSummary,
    InSilicoPredictions,
    PopulationFrequencyDetail,
    PredictorCard,
    ReportPayload,
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

    card = _population_card(payload, evidence_map)

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
            "predictors": [
                {"name": "REVEL", "score": 0.78, "threshold": 0.5},
                {"name": "CADD PHRED", "score": 23.4, "threshold": 20.0},
                {"name": "MetaLR", "score": 0.62, "threshold": 0.5},
            ],
            "spliceai": {"max_delta": 0.12, "threshold": 0.2},
            "excluded_predictors": ["AlphaMissense"],
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

    assert card["source_status"] == "fixture"
