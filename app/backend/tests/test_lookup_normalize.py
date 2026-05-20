from __future__ import annotations

from app.services.lookup_service import normalize_variant_query


def test_normalize_strips_gene_prefix_without_lowercasing_hgvs() -> None:
    gene, hgvs, transcript, kind = normalize_variant_query(
        " rpe65 ",
        " RPE65:c.260A>G ",
        None,
    )

    assert gene == "RPE65"
    assert hgvs == "c.260A>G"
    assert transcript is None
    assert kind == "cdna"


def test_normalize_strips_transcript_prefix_and_preserves_accession() -> None:
    gene, hgvs, transcript, kind = normalize_variant_query(
        "RPE65",
        "NM_000329.3:c.260A>G",
        None,
    )

    assert gene == "RPE65"
    assert hgvs == "c.260A>G"
    assert transcript == "NM_000329.3"
    assert kind == "cdna"


def test_normalize_strips_transcript_gene_annotation_and_trailing_protein() -> None:
    gene, hgvs, transcript, kind = normalize_variant_query(
        "RPE65",
        "NM_000329.3(RPE65):c.1301C>T (p.Ala434Val)",
        None,
    )

    assert gene == "RPE65"
    assert hgvs == "c.1301C>T"
    assert transcript == "NM_000329.3"
    assert kind == "cdna"


def test_normalize_collapses_internal_whitespace() -> None:
    _, hgvs, _, kind = normalize_variant_query("RPE65", " c.260 A>G ", None)

    assert hgvs == "c.260A>G"
    assert kind == "cdna"


def test_lookup_gene_prefixed_and_plain_cdna_have_same_transcript_hgvs(client) -> None:
    prefixed = client.post(
        "/api/v1/lookup",
        json={"gene": "RPE65", "cdna": "RPE65:c.260A>G"},
    )
    plain = client.post(
        "/api/v1/lookup",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    assert prefixed.status_code == 200
    assert plain.status_code == 200
    prefixed_hgvs = prefixed.json()["report_payload"]["variant_summary_rows"][0]["transcript_hgvs"]
    plain_hgvs = plain.json()["report_payload"]["variant_summary_rows"][0]["transcript_hgvs"]
    assert prefixed_hgvs == plain_hgvs == "c.260A>G"
