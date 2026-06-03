from __future__ import annotations

from hashlib import sha256

import pytest

from app.services.esm1b_assembly import (
    Esm1bManeCodonContext,
    Esm1bAssemblyError,
    Esm1bScoreRow,
    assemble_esm1b_mane_fixture_snv_table,
    esm1b_genomic_snv_rows,
    parse_esm1b_mutation_name,
    translate_codon,
)


def test_parse_esm1b_mutation_name_accepts_one_letter_missense() -> None:
    substitution = parse_esm1b_mutation_name("V715M")

    assert substitution.wt_residue == "V"
    assert substitution.protein_position == 715
    assert substitution.alt_residue == "M"


@pytest.mark.parametrize("value", ["p.Val715Met", "V0M", "V715V", ""])
def test_parse_esm1b_mutation_name_rejects_non_esm1b_shapes(value: str) -> None:
    with pytest.raises(Esm1bAssemblyError):
        parse_esm1b_mutation_name(value)


def test_translate_codon_uses_standard_dna_code() -> None:
    assert translate_codon("GTG") == "V"
    assert translate_codon("atg") == "M"


def test_esm1b_genomic_snv_rows_emit_single_base_plus_strand_paths() -> None:
    substitution = parse_esm1b_mutation_name("V1L")

    rows = esm1b_genomic_snv_rows(
        chrom="chr1",
        ref_codon="GTG",
        codon_positions=(100, 101, 102),
        strand="+",
        substitution=substitution,
        esm1b_llr=-12.2,
        uniprot_isoform="P00001-1",
        mane_tx="NM_000001.1",
    )

    assert [(row.position, row.ref, row.alt) for row in rows] == [
        (100, "G", "C"),
        (100, "G", "T"),
    ]
    assert {row.acmg_band for row in rows} == {"PP3_Moderate"}
    assert rows[0].to_tsv_fields()[4] == "-12.2000"


def test_esm1b_genomic_snv_rows_reverse_complement_negative_strand_alleles() -> None:
    substitution = parse_esm1b_mutation_name("V1M")

    rows = esm1b_genomic_snv_rows(
        chrom="chr1",
        ref_codon="GTG",
        codon_positions=(300, 299, 298),
        strand="-",
        substitution=substitution,
        esm1b_llr=-14.0,
        uniprot_isoform="P00001-1",
        mane_tx="NM_000001.1",
    )

    assert [(row.position, row.ref, row.alt) for row in rows] == [(300, "C", "T")]
    assert rows[0].acmg_band == "PP3_Strong"


def test_esm1b_genomic_snv_rows_reject_ref_codon_mismatch() -> None:
    substitution = parse_esm1b_mutation_name("V1M")

    with pytest.raises(Esm1bAssemblyError, match="wild-type residue"):
        esm1b_genomic_snv_rows(
            chrom="chr1",
            ref_codon="ATG",
            codon_positions=(100, 101, 102),
            strand="+",
            substitution=substitution,
            esm1b_llr=-7.5,
            uniprot_isoform="P00001-1",
            mane_tx="NM_000001.1",
        )


def test_assemble_esm1b_mane_fixture_snv_table_emits_tsv_and_manifest() -> None:
    result = assemble_esm1b_mane_fixture_snv_table(
        score_rows=(
            Esm1bScoreRow(
                mutation_name="V1M",
                esm1b_llr=-14.0,
                uniprot_isoform="P00002-1",
            ),
            Esm1bScoreRow(
                mutation_name="V1M",
                esm1b_llr=-12.2,
                uniprot_isoform="P00001-1",
            ),
        ),
        codon_contexts=(
            Esm1bManeCodonContext(
                gene="NEG",
                uniprot_isoform="P00002-1",
                protein_position=1,
                chrom="chr1",
                ref_codon="GTG",
                codon_positions=(300, 299, 298),
                strand="-",
                mane_tx="NM_000002.1",
            ),
            Esm1bManeCodonContext(
                gene="POS",
                uniprot_isoform="P00001-1",
                protein_position=1,
                chrom="chr1",
                ref_codon="GTG",
                codon_positions=(100, 101, 102),
                strand="+",
                mane_tx="NM_000001.1",
            ),
        ),
        score_source_checksum="a" * 64,
        mane_version="MANE Select v1.4",
        grch38_reference_checksum="b" * 64,
        code_version="unit-test-code-version",
        warnings=("fixture rows are synthetic",),
    )

    expected_tsv = (
        "chr1\t100\tG\tA\t-12.2000\tPP3_Moderate\tP00001-1\tNM_000001.1\tV1M\n"
        "chr1\t300\tC\tT\t-14.0000\tPP3_Strong\tP00002-1\tNM_000002.1\tV1M\n"
    )
    assert result.tsv == expected_tsv
    assert [row.position for row in result.rows] == [100, 300]

    payload = result.manifest_payload()
    assert payload["source_id"] == "esm1b_hg38_assembled_scores"
    assert payload["score_source_checksum"] == "a" * 64
    assert payload["mane_version"] == "MANE Select v1.4"
    assert payload["grch38_reference_checksum"] == "b" * 64
    assert payload["code_version"] == "unit-test-code-version"
    assert payload["output_checksum"] == sha256(expected_tsv.encode("utf-8")).hexdigest()
    assert payload["row_count"] == 2
    assert payload["input_score_row_count"] == 2
    assert payload["internal_fixture_only"] is True
    assert payload["public_serialization_allowed"] is False
    assert payload["license_gate"] == "esm1b_score_file_terms_unconfirmed"
    assert payload["warnings"] == [
        "fixture rows are synthetic",
        "internal_fixture_only",
        "esm1b_public_serialization_blocked",
        "esm1b_score_file_terms_unconfirmed",
    ]


def test_assemble_esm1b_mane_fixture_snv_table_rejects_ref_codon_mismatch() -> None:
    with pytest.raises(Esm1bAssemblyError, match="wild-type residue"):
        assemble_esm1b_mane_fixture_snv_table(
            score_rows=(
                Esm1bScoreRow(
                    mutation_name="V1M",
                    esm1b_llr=-12.2,
                    uniprot_isoform="P00001-1",
                ),
            ),
            codon_contexts=(
                Esm1bManeCodonContext(
                    uniprot_isoform="P00001-1",
                    protein_position=1,
                    chrom="chr1",
                    ref_codon="ATG",
                    codon_positions=(100, 101, 102),
                    strand="+",
                    mane_tx="NM_000001.1",
                ),
            ),
            score_source_checksum="a" * 64,
            mane_version="MANE Select v1.4",
            grch38_reference_checksum="b" * 64,
        )


def test_assemble_esm1b_mane_fixture_snv_table_requires_explicit_codon_context() -> None:
    with pytest.raises(Esm1bAssemblyError, match="missing MANE codon context"):
        assemble_esm1b_mane_fixture_snv_table(
            score_rows=(
                Esm1bScoreRow(
                    mutation_name="V1M",
                    esm1b_llr=-12.2,
                    uniprot_isoform="P00001-1",
                ),
            ),
            codon_contexts=(),
            score_source_checksum="a" * 64,
            mane_version="MANE Select v1.4",
            grch38_reference_checksum="b" * 64,
        )


def test_assemble_esm1b_mane_fixture_snv_table_is_fixture_sized_only() -> None:
    with pytest.raises(Esm1bAssemblyError, match="fixture-sized only"):
        assemble_esm1b_mane_fixture_snv_table(
            score_rows=(
                Esm1bScoreRow(
                    mutation_name="V1M",
                    esm1b_llr=-12.2,
                    uniprot_isoform="P00001-1",
                ),
                Esm1bScoreRow(
                    mutation_name="V1L",
                    esm1b_llr=-10.8,
                    uniprot_isoform="P00001-1",
                ),
            ),
            codon_contexts=(),
            score_source_checksum="a" * 64,
            mane_version="MANE Select v1.4",
            grch38_reference_checksum="b" * 64,
            max_score_rows=1,
        )
