from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.esm1b_assembly import load_esm1b_codon_contexts_from_jsonl
from app.services.esm1b_mane_contexts import (
    Esm1bManeContextError,
    iter_esm1b_mane_protein_contexts,
    write_esm1b_mane_context_artifacts,
)
from app.services.reference_genome import ReferenceWindow


def test_iter_esm1b_mane_protein_contexts_builds_plus_and_minus_cds(
    tmp_path: Path,
) -> None:
    gff = _write_tiny_mane_gff(tmp_path)
    store = _FakeReferenceStore({"1": "ATGGTTTAA", "2": "TTAAACCAT"})

    proteins = {
        protein.gene: protein
        for protein in iter_esm1b_mane_protein_contexts(
            mane_gff_path=gff,
            reference_store=store,
        )
    }

    plus = proteins["POS"]
    assert plus.sequence_id == "NP_POS.1"
    assert plus.protein_sequence == "MV"
    assert [
        (context.protein_position, context.ref_codon, context.codon_positions)
        for context in plus.contexts
    ] == [
        (1, "ATG", (1, 2, 3)),
        (2, "GTT", (4, 5, 6)),
    ]

    minus = proteins["NEG"]
    assert minus.sequence_id == "NP_NEG.1"
    assert minus.protein_sequence == "MV"
    assert [
        (context.protein_position, context.ref_codon, context.codon_positions)
        for context in minus.contexts
    ] == [
        (1, "ATG", (9, 8, 7)),
        (2, "GTT", (6, 5, 4)),
    ]


def test_write_esm1b_mane_context_artifacts_emits_materializer_jsonl_and_manifest(
    tmp_path: Path,
) -> None:
    gff = _write_tiny_mane_gff(tmp_path)
    reference = tmp_path / "hg38.2bit"
    reference.write_bytes(b"synthetic-reference")
    store = _FakeReferenceStore({"1": "ATGGTTTAA"})
    context_path = tmp_path / "esm1b-mane-codon-contexts.jsonl"
    fasta_path = tmp_path / "esm1b-mane-proteins.fasta"
    manifest_path = tmp_path / "esm1b-mane-codon-contexts.manifest.json"

    result = write_esm1b_mane_context_artifacts(
        mane_gff_path=gff,
        reference_path=reference,
        reference_store=store,
        context_path=context_path,
        protein_fasta_path=fasta_path,
        manifest_path=manifest_path,
        sequence_id_field="protein_id",
        mane_version="MANE Select v1.5",
        genes=("POS",),
        reference_sha256="b" * 64,
        primary_chromosomes_only=True,
        skipped_patch_gene_count=0,
        fixture_only=True,
    )

    contexts = load_esm1b_codon_contexts_from_jsonl(context_path)
    assert [(context.uniprot_isoform, context.protein_position) for context in contexts] == [
        ("NP_POS.1", 1),
        ("NP_POS.1", 2),
    ]
    assert {context.protein_sequence_id for context in contexts} == {"NP_POS.1"}
    assert {context.protein_sequence_id_namespace for context in contexts} == {"refseq"}
    assert {context.refseq_protein_id for context in contexts} == {"NP_POS.1"}
    assert {context.ensembl_protein_id for context in contexts} == {"ENSPPOS"}
    assert {context.uniprot_isoform_id for context in contexts} == {None}
    assert fasta_path.read_text(encoding="utf-8").splitlines()[:2] == [
        ">NP_POS.1 gene=POS mane_tx=NM_POS.1 sequence_id_field=protein_id "
        "protein_id=NP_POS.1 ensembl_protein_id=ENSPPOS",
        "MV",
    ]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["protein_count"] == 1
    assert manifest["manifest_schema_version"] == "2"
    assert manifest["context_count"] == 2
    assert manifest["reference_sha256"] == "b" * 64
    assert manifest["precomputed_huggingface_score_zip_used"] is False
    assert manifest["patch_contig_policy"] == "exclude_with_explicit_ledger"
    assert manifest["skipped_patch_gene_count"] == 0
    assert manifest["fixture_only"] is True
    assert manifest["storage_upload"] == "not_used"
    assert result.to_sanitized_dict()["local_path_values_emitted"] is False


def test_iter_esm1b_mane_protein_contexts_can_skip_invalid_cds_length(
    tmp_path: Path,
) -> None:
    gff = tmp_path / "invalid-cds.gff"
    gff.write_text(
        "\n".join(
            [
                "##gff-version 3",
                (
                    "chr1\tBestRefSeq\tmRNA\t1\t4\t.\t+\t.\t"
                    "ID=rna-NM_BAD.1;gene=BAD;tag=MANE Select;transcript_id=NM_BAD.1"
                ),
                (
                    "chr1\tBestRefSeq\tCDS\t1\t4\t.\t+\t0\t"
                    "ID=cds-NP_BAD.1;Parent=rna-NM_BAD.1;"
                    "Dbxref=Ensembl:ENSPBAD;protein_id=NP_BAD.1;gene=BAD;tag=MANE Select"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    store = _FakeReferenceStore({"1": "ATGG"})

    with pytest.raises(Esm1bManeContextError, match="not divisible by 3"):
        tuple(iter_esm1b_mane_protein_contexts(mane_gff_path=gff, reference_store=store))

    skipped = tuple(
        iter_esm1b_mane_protein_contexts(
            mane_gff_path=gff,
            reference_store=store,
            invalid_cds_policy="skip",
        )
    )
    assert skipped == ()


def _write_tiny_mane_gff(tmp_path: Path) -> Path:
    path = tmp_path / "tiny-mane.gff"
    path.write_text(
        "\n".join(
            [
                "##gff-version 3",
                (
                    "chr1\tBestRefSeq\tmRNA\t1\t9\t.\t+\t.\t"
                    "ID=rna-NM_POS.1;gene=POS;tag=MANE Select;transcript_id=NM_POS.1"
                ),
                (
                    "chr1\tBestRefSeq\tCDS\t1\t9\t.\t+\t0\t"
                    "ID=cds-NP_POS.1;Parent=rna-NM_POS.1;"
                    "Dbxref=Ensembl:ENSPPOS;protein_id=NP_POS.1;gene=POS;tag=MANE Select"
                ),
                (
                    "chr2\tBestRefSeq\tmRNA\t1\t9\t.\t-\t.\t"
                    "ID=rna-NM_NEG.1;gene=NEG;tag=MANE Select;transcript_id=NM_NEG.1"
                ),
                (
                    "chr2\tBestRefSeq\tCDS\t1\t9\t.\t-\t0\t"
                    "ID=cds-NP_NEG.1;Parent=rna-NM_NEG.1;"
                    "Dbxref=Ensembl:ENSPNEG;protein_id=NP_NEG.1;gene=NEG;tag=MANE Select"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


class _FakeReferenceStore:
    def __init__(self, sequences: dict[str, str]) -> None:
        self._sequences = {chrom: sequence.upper() for chrom, sequence in sequences.items()}

    def get_sequence(
        self,
        chrom: str,
        start: int,
        end: int,
        build: str | None = None,
    ) -> ReferenceWindow:
        sequence = self._sequences[chrom][start - 1 : end]
        return ReferenceWindow(
            requested_chrom=chrom,
            chrom=chrom,
            start=start,
            end=end,
            zero_based_start=start - 1,
            zero_based_end_exclusive=end,
            sequence=sequence,
            genome_build=build or "GRCh38",
            source_id="test",
        )

    def close(self) -> None:
        return None
