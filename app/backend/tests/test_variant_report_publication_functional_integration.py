from __future__ import annotations

import json
from typing import Any


def _section_targets(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        target["section_id"]: target for target in profile["extraction_plan"]["section_targets"]
    }


def _report_call_card(payload: dict[str, Any], card_id: str) -> dict[str, Any]:
    return next(card for card in payload["call_cards"]["cards"] if card["card_id"] == card_id)


def test_lookup_keeps_publication_inventory_and_functional_count_distinct(
    client,
) -> None:
    response = client.post(
        "/api/v1/lookup",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    assert response.status_code == 200
    payload = response.json()["report_payload"]
    publications = payload["publications_literature"]
    functional = payload["functional_evidence"]
    profile = payload["report_profile"]

    assert publications["total_count"] == 3
    assert publications["limit"] == 5
    assert publications["shown_count"] == min(publications["total_count"], 5)
    assert len(publications["articles"]) == publications["shown_count"]
    assert payload["publications_callout"]["total_count"] == publications["total_count"]

    assert functional["total_count"] == 1
    assert functional["total_count"] != publications["total_count"]
    publication_pmids = {article["pmid"] for article in publications["articles"]}
    functional_pmids = {
        study["pmid"] for study in functional["studies"] if study["pmid"] is not None
    }
    assert functional_pmids == {"35901234"}
    assert functional_pmids < publication_pmids

    targets = _section_targets(profile)
    assert targets["publications"]["match_level"] == "variant_level"
    assert targets["publications"]["required_sources"] == ["pubmed", "litvar2", "clinvar"]
    assert targets["lab_functional"]["match_level"] == "variant_level"
    assert targets["lab_functional"]["required_sources"] == [
        "clingen",
        "clinvar",
        "pubmed",
    ]

    summary = profile["interpretation_summary"]
    assert "publications" in summary["fact_refs"]
    assert "3 publication(s) identified" in summary["text"]

    functional_card = _report_call_card(payload, "lab_functional")
    badge_texts = {badge["text"] for badge in functional_card["support_badges"]}
    assert "1 Unique" in badge_texts
    assert "3 Unique" not in badge_texts


def test_report_profile_references_publication_and_functional_sections_without_rows(
    client,
) -> None:
    response = client.post(
        "/api/v1/lookup",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    assert response.status_code == 200
    payload = response.json()["report_payload"]
    profile = payload["report_profile"]

    assert "publications_literature" not in profile
    assert "functional_evidence" not in profile
    assert "publications" in _section_targets(profile)
    assert "lab_functional" in _section_targets(profile)

    profile_json = json.dumps(profile)
    for article in payload["publications_literature"]["articles"]:
        assert article["title"] not in profile_json
    for study in payload["functional_evidence"]["studies"]:
        if study["snippet"] is not None:
            assert study["snippet"] not in profile_json


def test_publication_expansion_endpoint_paginates_epvlex_inventory(client) -> None:
    response = client.post(
        "/api/v1/lookup/publications",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "transcript": "NM_000329.3",
            "protein_change": "p.Asp87Gly",
            "limit": 1,
            "offset": 1,
        },
    )

    assert response.status_code == 200
    page = response.json()
    assert page["total_count"] == 3
    assert page["shown_count"] == 1
    assert page["limit"] == 1
    assert page["offset"] == 1
    assert [article["pmid"] for article in page["articles"]] == ["37042101"]
    assert page["articles"][0]["url"] == "https://pubmed.ncbi.nlm.nih.gov/37042101/"
