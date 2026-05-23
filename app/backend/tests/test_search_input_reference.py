from __future__ import annotations

from app.services.search_input_reference import default_search_input_reference


def test_search_input_reference_maps_gene_alias_without_assigning_variant() -> None:
    reference = default_search_input_reference()

    hint = reference.match_gene_hint("frameshift in the cystic fibrosis gene")

    assert hint is not None
    assert hint.gene == "CFTR"
    assert hint.phrase == "cystic fibrosis gene"
    assert "curated search-input lexicon" in hint.assumption


def test_search_input_reference_normalizes_amino_acid_names_and_codes() -> None:
    reference = default_search_input_reference()

    assert reference.amino_acid("leucine").three_letter == "Leu"
    assert reference.amino_acid("L").three_letter == "Leu"
    assert reference.amino_acid("Leu").one_letter == "L"


def test_search_input_reference_maps_consequence_terms_as_hints_only() -> None:
    reference = default_search_input_reference()

    consequence = reference.consequence("a frame shift starting at leucine 441")

    assert consequence is not None
    assert consequence.suffix == "fs"
    assert consequence.variant_class == "frameshift"


def test_search_input_reference_keeps_ambiguous_disease_terms_as_choices() -> None:
    reference = default_search_input_reference()

    hint = reference.match_disease_gene_hint("retinal dystrophy gene variant")

    assert hint is not None
    assert hint.is_ambiguous is True
    assert hint.genes == ("ABCA4", "RPE65", "RPGRIP1", "USH2A")
    assert "multiple possible genes" in hint.assumption


def test_search_input_reference_normalizes_chromosome_ui_aliases() -> None:
    reference = default_search_input_reference()

    assert reference.normalize_chromosome("chr17") == "17"
    assert reference.normalize_chromosome("chromosome X") == "X"
    assert reference.normalize_chromosome("chrMT") == "M"


def test_search_input_reference_exposes_transcript_alias_hints() -> None:
    reference = default_search_input_reference()

    hint = reference.transcript_hint("RPE65", "use the RPE65 MANE transcript")

    assert hint is not None
    assert hint.transcript == "NM_000329.3"
    assert "RPE65 transcript NM_000329.3" in hint.assumption


def test_search_input_reference_exposes_display_vocabularies_as_non_source_hints() -> None:
    reference = default_search_input_reference()

    clinvar = reference.clinical_significance("VUS")
    acmg = reference.acmg_criterion("ps3")

    assert clinvar is not None
    assert clinvar.display == "Uncertain significance"
    assert clinvar.group == "clinvar_significance"
    assert acmg is not None
    assert acmg.display == "PS3"
    assert acmg.group == "pathogenic_strong"
