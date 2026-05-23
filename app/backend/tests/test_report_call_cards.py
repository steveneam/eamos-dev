from __future__ import annotations

from app.schemas.run import (
    AcmgCriteriaScaffold,
    AcmgCriterion,
    PopulationFrequencyDetail,
    ReportPayload,
)
from app.services.report_call_cards import build_variant_report_call_cards


def _population_card(payload: ReportPayload, evidence_map: dict | None = None) -> dict:
    cards = build_variant_report_call_cards(
        payload,
        evidence_map or {},
        {"gnomad": "fixture"},
    )
    return next(
        card for card in cards.model_dump()["cards"] if card["card_id"] == "population_frequency"
    )


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
