from __future__ import annotations

import pytest

from app.services.paper_extract.grammar import extract_page_mentions, extract_page_records


def _by_text(text: str):
    return {
        mention.span.exact_text: mention
        for mention in extract_page_mentions(
            document_id="main",
            page_number=1,
            text=text,
        )
    }


def test_typed_grammar_covers_accession_hgvs_rsid_splice_indel_and_legacy() -> None:
    text = (
        "Results\n"
        "The RPE65 proband carried NM_000329.3:c.260A>G and rs121918127. "
        "ABCA4 c.5461-10T>C and BRCA1 c.68_69delAG were clinical alleles. "
        "In a construct, TP53 p.Arg72Pro and legacy R72P were compared."
    )

    mentions = _by_text(text)

    assert mentions["NM_000329.3:c.260A>G"].notation_type == "cdna"
    assert mentions["NM_000329.3:c.260A>G"].transcript_evidence == ["NM_000329.3"]
    assert mentions["NM_000329.3:c.260A>G"].gene_evidence == ["RPE65"]
    assert mentions["rs121918127"].notation_type == "rsid"
    assert mentions["c.5461-10T>C"].notation_type == "cdna"
    assert mentions["c.68_69delAG"].notation_type == "cdna"
    assert mentions["p.Arg72Pro"].notation_type == "protein"
    assert mentions["R72P"].notation_type == "legacy"
    assert mentions["p.Arg72Pro"].biological_context == "experimental_construct"

    for exact, mention in mentions.items():
        assert text[mention.span.start_character : mention.span.end_character] == exact
        assert mention.span.end_character - mention.span.start_character == len(exact)
        assert exact in mention.span.bounded_quote


def test_recovery_layer_preserves_exact_split_surface_and_span() -> None:
    text = "Results\nThe USH2A proband carried c. 2276 G >\nT in exon 13."

    mentions = extract_page_mentions(document_id="main", page_number=1, text=text)

    mention = next(item for item in mentions if "2276" in item.span.exact_text)
    assert mention.extraction_layer == "l2_recovery"
    assert mention.gene_evidence == ["USH2A"]
    assert (
        text[mention.span.start_character : mention.span.end_character] == mention.span.exact_text
    )


def test_references_are_inventoried_but_always_bibliography_only() -> None:
    text = (
        "Results\nRPE65 c.260A>G was found in the proband.\n"
        "References\nSmith et al. reported ABCA4 c.5882G>A in 2019."
    )

    mentions = _by_text(text)

    assert mentions["c.260A>G"].biological_context in {"clinical_allele", "case_or_proband"}
    assert mentions["c.5882G>A"].biological_context == "bibliography_only"
    assert mentions["c.5882G>A"].span.section == "References"


def test_gene_association_does_not_cross_section_or_unbounded_distance() -> None:
    text = "Methods\nRPE65 was measured.\nResults\n" + ("ordinary words " * 30) + "c.260A>G"

    mention = _by_text(text)["c.260A>G"]

    assert mention.gene_evidence == []
    assert mention.extraction_layer == "l3_inventory"


def test_contexts_remain_distinct() -> None:
    cases = {
        "The proband carried RPE65 c.260A>G.": "case_or_proband",
        "The variant RPE65 c.260A>G segregated with disease in the family.": "family_segregation",
        "We engineered rescue variant RPE65 c.260A>G.": "engineered_rescue",
        "Wild-type was compared with RPE65 c.260A>G.": "comparator_or_background",
    }

    for text, expected in cases.items():
        assert _by_text(text)["c.260A>G"].biological_context == expected


@pytest.mark.parametrize(
    ("caption", "expected_section"),
    [
        ("Figure 2. The GENE1 c.2A>G construct was measured.", "Figure caption"),
        ("Table S1. The GENE1 c.3A>G proband result.", "Table caption"),
    ],
)
def test_figure_and_table_caption_lines_have_explicit_sections(
    caption: str,
    expected_section: str,
) -> None:
    surface = "c.2A>G" if "Figure" in caption else "c.3A>G"

    mention = _by_text(f"Results\nBody text.\n{caption}\nMore body.")[surface]

    assert mention.span.section == expected_section


@pytest.mark.parametrize(
    ("surface", "notation_type"),
    [
        ("c.123_124insAT", "cdna"),
        ("c.123dupA", "cdna"),
        ("c.123_124del", "cdna"),
        ("c.123_124delinsGC", "cdna"),
        ("g.101A>G", "genomic"),
        ("n.44delA", "genomic"),
        ("r.55_56insAU", "rna"),
        ("m.73A>G", "mitochondrial"),
        ("p.Gly12ValfsTer5", "protein"),
        ("p.Arg97Profs*23", "protein"),
        ("IVS2+1G>A", "legacy"),
    ],
)
def test_typed_grammar_matrix(surface: str, notation_type: str) -> None:
    text = f"Results\nThe GENE1 proband carried {surface}."

    mentions = _by_text(text)

    assert mentions[surface].notation_type == notation_type


def test_recovery_canonicalizes_prefix_operation_and_bases_without_changing_span() -> None:
    text = "Results\nThe GENE1 proband carried C. 123_124 DELINS at."

    record = extract_page_records(document_id="main", page_number=1, text=text)[0]

    assert record.mention.span.exact_text == "C. 123_124 DELINS at"
    assert record.canonical_notation == "c.123_124delinsAT"


def test_headerless_reference_tail_is_excluded_from_resolution_context() -> None:
    body = "Results\nGENE1 c.1A>G was observed.\n" + ("ordinary discussion text " * 30)
    references = (
        "\n1 Smith et al. GENE2 c.2A>G.\n"
        "2 Jones et al. GENE3 c.3A>G.\n"
        "3 Brown et al. GENE4 c.4A>G."
    )

    mentions = _by_text(body + references)

    assert mentions["c.1A>G"].biological_context != "bibliography_only"
    for surface in ("c.2A>G", "c.3A>G", "c.4A>G"):
        assert mentions[surface].biological_context == "bibliography_only"
        assert mentions[surface].span.section == "References"


@pytest.mark.parametrize(
    "hostile_token",
    [
        "c." + ("1" * 1_000) + "A>G",
        "c.123delins" + ("A" * 1_000),
        "c." + (" " * 1_000) + "123A>G",
        "p.Gly" + ("1" * 1_000) + "Val",
    ],
)
def test_overlong_tokens_cannot_escape_frozen_evidence_bounds(hostile_token: str) -> None:
    text = f"Results\nGENE1 {hostile_token}."

    assert extract_page_mentions(document_id="main", page_number=1, text=text) == []
