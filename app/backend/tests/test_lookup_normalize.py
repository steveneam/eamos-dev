from __future__ import annotations

from app.services.sequence_context import (
    genomic_variant_id_to_refseq_hgvs,
    normalize_variant_query,
    parse_genomic_variant_id,
)


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


def test_normalize_accepts_spaced_genomic_vcf_input() -> None:
    _, hgvs, _, kind = normalize_variant_query("", "6 31740453 G T", None)

    assert hgvs == "6-31740453-G-T"
    assert kind == "genomic"
    assert parse_genomic_variant_id(hgvs) == "6-31740453-G-T"


def test_normalize_accepts_colon_genomic_substitution_input() -> None:
    _, hgvs, _, kind = normalize_variant_query("", "8:140300616 T>G", None)

    assert hgvs == "8-140300616-T-G"
    assert kind == "genomic"
    assert parse_genomic_variant_id(hgvs) == "8-140300616-T-G"


def test_genomic_variant_id_to_refseq_hgvs_handles_simple_indels() -> None:
    assert (
        genomic_variant_id_to_refseq_hgvs("1-1042601-A-AGAGAG")
        == "NC_000001.11:g.1042601_1042602insGAGAG"
    )
    assert (
        genomic_variant_id_to_refseq_hgvs("1-1042466-GGGC-G")
        == "NC_000001.11:g.1042467_1042469delGGC"
    )


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
