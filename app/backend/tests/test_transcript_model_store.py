from __future__ import annotations

import re

from app.services.transcript_model import (
    GENCODE_SOURCE_ID,
    MANE_SOURCE_ID,
    TranscriptModelStore,
)


def test_store_provenance_records_mane_gencode_fixture_metadata() -> None:
    store = TranscriptModelStore()
    provenance = store.provenance()

    assert provenance.fixture_version == "2026-05-27-mane-gencode-tiny-v1"
    assert provenance.source_ids == (MANE_SOURCE_ID, GENCODE_SOURCE_ID)
    assert [source.source_id for source in provenance.sources] == [
        MANE_SOURCE_ID,
        GENCODE_SOURCE_ID,
    ]
    assert provenance.relative_path == (
        "app/backend/app/fixtures/transcript_models/mane_gencode_tiny.json"
    )
    assert provenance.checksum_algorithm == "sha256"
    assert re.fullmatch(r"[0-9a-f]{64}", provenance.checksum)


def test_rpe65_resolves_to_mane_select_refseq_and_ensembl_transcripts() -> None:
    lookup = TranscriptModelStore().lookup("rpe65", "ENST00000262340")

    assert lookup.available is True
    model = lookup.model
    assert model is not None
    assert model.gene == "RPE65"
    assert model.refseq_transcript == "NM_000329.3"
    assert model.ensembl_transcript == "ENST00000262340.6"
    assert "MANE Select" in model.transcript_aliases
    assert model.ensembl_gene_id == "ENSG00000116745"
    assert model.chrom == "1"
    assert model.strand == "-"
    assert model.genome_build == "GRCh38"
    assert model.transcript_span == (68428820, 68449958)
    assert model.coding_length == 1602
    assert model.protein_length == 533
    assert model.provenance.source_ids == (MANE_SOURCE_ID, GENCODE_SOURCE_ID)


def test_reverse_strand_exons_are_in_transcript_order_with_descending_genomics() -> None:
    lookup = TranscriptModelStore().lookup("RPE65", "NM_000329.3")
    assert lookup.model is not None

    exons = lookup.model.exons

    assert [exon.number for exon in exons] == [3, 4, 5]
    assert [exon.cds_start for exon in exons] == [89, 232, 325]
    assert [exon.genomic_start for exon in exons] == [68446200, 68444805, 68443000]
    assert exons[1].cds_start <= 260 <= exons[1].cds_end
    assert exons[1].genomic_start <= 68444869 <= exons[1].genomic_end


def test_non_rpe65_control_resolves_by_ensembl_alias_and_preserves_plus_strand_order() -> None:
    lookup = TranscriptModelStore().lookup("CFTR", "ENST00000003084")

    assert lookup.available is True
    model = lookup.model
    assert model is not None
    assert model.refseq_transcript == "NM_000492.4"
    assert model.ensembl_transcript == "ENST00000003084.11"
    assert model.strand == "+"
    assert [exon.number for exon in model.exons] == [1, 2, 3, 4]
    assert [exon.genomic_start for exon in model.exons] == [
        117480095,
        117504253,
        117509034,
        117530899,
    ]
    assert model.coding_length == 489


def test_missing_gene_and_transcript_return_structured_unavailable_state() -> None:
    store = TranscriptModelStore()

    missing_gene = store.lookup("NOTAGENE")
    missing_transcript = store.lookup("RPE65", "NM_MISSING.1")

    assert missing_gene.available is False
    assert missing_gene.model is None
    assert missing_gene.unavailable_reason == "gene_not_found"
    assert missing_gene.warnings == ("transcript_model_gene_not_found",)

    assert missing_transcript.available is False
    assert missing_transcript.model is None
    assert missing_transcript.unavailable_reason == "transcript_not_found"
    assert missing_transcript.warnings == ("transcript_model_transcript_not_found",)
