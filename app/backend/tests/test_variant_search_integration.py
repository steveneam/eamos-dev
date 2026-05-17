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
    assert payload["report_payload"]["publications_callout"]["total_count"] == 816
    assert all(
        article["url"] == f"https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/"
        for article in payload["report_payload"]["pubmed_articles"]
    )
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
