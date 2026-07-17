from __future__ import annotations

import json
from hashlib import md5, sha256
from pathlib import Path

import pytest

from app.services.esm1b_assembly import (
    ESM1B_LICENSE_GATE,
    ESM1B_REGENERATED_SCORE_METHOD,
    ESM1B_REGENERATED_SCORE_WARNING,
    Esm1bManeCodonContext,
    Esm1bAssemblyError,
    Esm1bScoreRow,
    assemble_esm1b_mane_fixture_snv_table,
    esm1b_genomic_snv_rows,
    load_esm1b_codon_contexts_from_jsonl,
    load_esm1b_score_rows_from_csv,
    materialize_regenerated_esm1b_runtime_asset,
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
    assert {row.acmg_band for row in rows} == {"PP3 Moderate"}
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
    assert rows[0].acmg_band == "PP3 3 points"


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
        "chr1\t100\tG\tA\t-12.2000\tPP3 Moderate\tP00001-1\tNM_000001.1\tV1M\n"
        "chr1\t300\tC\tT\t-14.0000\tPP3 3 points\tP00002-1\tNM_000002.1\tV1M\n"
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
    assert payload["internal_fixture_only"] is False
    assert payload["public_serialization_allowed"] is True
    assert payload["license_gate"] == ESM1B_LICENSE_GATE
    assert payload["warnings"] == [
        "fixture rows are synthetic",
        "esm1b_license_gate_metadata",
        ESM1B_LICENSE_GATE,
    ]


def test_assemble_esm1b_mane_fixture_snv_table_supports_clean_mit_regeneration() -> None:
    result = assemble_esm1b_mane_fixture_snv_table(
        score_rows=(
            Esm1bScoreRow(
                mutation_name="V1M",
                esm1b_llr=-14.0,
                uniprot_isoform="P00001-1",
            ),
        ),
        codon_contexts=(
            Esm1bManeCodonContext(
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
        license_gate=None,
        warnings=(ESM1B_REGENERATED_SCORE_WARNING,),
        score_generation_method=ESM1B_REGENERATED_SCORE_METHOD,
        model_name="esm1b_t33_650M_UR50S",
        model_source_license="MIT",
        scoring_code_license="MIT",
    )

    payload = result.manifest_payload()
    assert payload["license_gate"] is None
    assert payload["score_generation_method"] == "mit_model_regeneration"
    assert payload["model_source_license"] == "MIT"
    assert payload["scoring_code_license"] == "MIT"
    assert payload["warnings"] == [ESM1B_REGENERATED_SCORE_WARNING]


def test_materialize_regenerated_esm1b_runtime_asset_writes_clean_manifest(
    tmp_path: Path,
) -> None:
    score_csv = tmp_path / "scores.csv"
    score_csv.write_text("seq_id,mut_name,esm_score\nP00001-1,V1M,-14.0\n", encoding="utf-8")
    contexts_jsonl = tmp_path / "contexts.jsonl"
    contexts_jsonl.write_text(
        json.dumps(
            {
                "uniprot_isoform": "P00001-1",
                "protein_position": 1,
                "chrom": "chr1",
                "ref_codon": "GTG",
                "codon_positions": [100, 101, 102],
                "strand": "+",
                "mane_tx": "NM_000001.1",
                "gene": "TST",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    target = tmp_path / "esm1b_hg38.tsv.gz"

    result = materialize_regenerated_esm1b_runtime_asset(
        score_rows=load_esm1b_score_rows_from_csv(score_csv),
        codon_contexts=load_esm1b_codon_contexts_from_jsonl(contexts_jsonl),
        target_path=target,
        score_source_checksum=sha256(score_csv.read_bytes()).hexdigest(),
        mane_version="MANE Select v1.4",
        grch38_reference_checksum="b" * 64,
        bgzip_tabix_writer=_fake_bgzip_tabix_writer,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert result.launch_gate is None
    assert manifest["license_gate"] is None
    assert manifest["launch_gate"] is None
    assert manifest["commercial_use_allowed"] is True
    assert manifest["precomputed_huggingface_score_zip_used"] is False
    assert manifest["score_generation_method"] == ESM1B_REGENERATED_SCORE_METHOD
    assert manifest["model_source_license"] == "MIT"
    assert manifest["scoring_code_license"] == "MIT"
    assert manifest["row_count"] == 1
    assert manifest["input_score_row_count"] == 1
    assert manifest["md5"] == md5(target.read_bytes()).hexdigest()
    assert result.to_sanitized_dict()["local_path_values_emitted"] is False


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


def _fake_bgzip_tabix_writer(tsv: str, target_path: Path) -> Path:
    target_path.write_text(tsv, encoding="utf-8")
    index_path = Path(f"{target_path}.tbi")
    index_path.write_text("fake-index", encoding="utf-8")
    return index_path


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


def test_assemble_esm1b_mane_fixture_snv_table_honors_explicit_row_limit() -> None:
    with pytest.raises(Esm1bAssemblyError, match="configured limit"):
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
