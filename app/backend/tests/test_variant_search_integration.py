from __future__ import annotations


def test_lookup_fixture_mode_resolves_grch38_and_litvar_publications(client) -> None:
    response = client.post(
        "/api/v1/lookup",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    assert response.status_code == 200
    payload = response.json()
    row = payload["report_payload"]["variant_summary_rows"][0]
    assert row["genomic_hg38"] == "1-68444869-T-C"
    literature = payload["report_payload"]["publications_literature"]
    assert literature["total_count"] == 3
    assert literature["shown_count"] == 3
    assert payload["report_payload"]["publications_callout"]["total_count"] == 3
    functional = payload["report_payload"]["functional_evidence"]
    assert functional["total_count"] == 1
    assert functional["source_breakdown"] == {"clingen": 0, "clinvar": 0, "pubmed": 1}
    assert [study["pmid"] for study in functional["studies"]] == ["35901234"]
    assert all(
        article["url"] == f"https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/"
        for article in payload["report_payload"]["pubmed_articles"]
    )
    assert [article["pmid"] for article in payload["report_payload"]["pubmed_articles"]] == [
        "38191234",
        "37042101",
        "35901234",
    ]
    assert payload["report_payload"]["pubmed_articles"][0]["snippets"][0]["matched_terms"]
    assert [item["source"] for item in payload["evidence"]] == [
        "vep",
        "variant_validator",
        "gnomad",
        "spliceai",
        "clinvar",
        "pubmed",
        "litvar2",
    ]


def test_lookup_unparseable_query_uses_frozen_warning_code(client) -> None:
    response = client.post(
        "/api/v1/lookup",
        json={"gene": "RPE65", "cdna": "???not-a-variant???"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "input_unparseable:unknown" in payload["warnings"]
    assert "could not parse" in payload["report_payload"]["limitations"]


def test_lookup_rejects_blank_query_fields(client) -> None:
    response = client.post(
        "/api/v1/lookup",
        json={"gene": "  ", "cdna": "  "},
    )

    assert response.status_code == 422


def test_lookup_publications_endpoint_pages_deduped_ep_vlex_rows(client) -> None:
    response = client.post(
        "/api/v1/lookup/publications",
        json={"gene": "RPE65", "cdna": "c.260A>G", "limit": 2, "offset": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 3
    assert payload["shown_count"] == 2
    assert payload["offset"] == 1
    assert payload["limit"] == 2
    assert [article["pmid"] for article in payload["articles"]] == ["37042101", "35901234"]
    assert all(
        article["url"] == f"https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/"
        for article in payload["articles"]
    )


def test_lookup_publications_endpoint_enforces_bounded_limit(client) -> None:
    response = client.post(
        "/api/v1/lookup/publications",
        json={"gene": "RPE65", "cdna": "c.260A>G", "limit": 51},
    )

    assert response.status_code == 422
