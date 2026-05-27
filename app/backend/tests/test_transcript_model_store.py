from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.services.transcript_model import (
    GENCODE_SOURCE_ID,
    MANE_SOURCE_ID,
    TranscriptModelStoreError,
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


def test_coordinate_map_identifies_reverse_strand_exon_and_cds_position() -> None:
    location = TranscriptModelStore().map_coordinate(
        gene="RPE65",
        transcript="NM_000329.3",
        chrom="NC_000001.11",
        position=68444869,
    )

    assert location.available is True
    assert location.location is not None
    assert location.location.gene == "RPE65"
    assert location.location.transcript == "NM_000329.3"
    assert location.location.chrom == "1"
    assert location.location.strand == "-"
    assert location.location.region == "exon"
    assert location.location.exon_number == 4
    assert location.location.cds_position == 260
    assert location.location.intron_between_exons is None
    assert location.location.provenance.source_ids == (MANE_SOURCE_ID, GENCODE_SOURCE_ID)


def test_coordinate_map_handles_exon_boundaries_on_both_strands() -> None:
    store = TranscriptModelStore()

    rpe65_genomic_high = store.map_coordinate(
        gene="RPE65",
        chrom="1",
        position=68444897,
    )
    rpe65_genomic_low = store.map_coordinate(
        gene="RPE65",
        chrom="1",
        position=68444805,
    )
    cftr_start = store.map_coordinate(gene="CFTR", chrom="7", position=117504253)
    cftr_end = store.map_coordinate(gene="CFTR", chrom="7", position=117504363)

    assert rpe65_genomic_high.location is not None
    assert rpe65_genomic_high.location.cds_position == 232
    assert rpe65_genomic_low.location is not None
    assert rpe65_genomic_low.location.cds_position == 324
    assert cftr_start.location is not None
    assert cftr_start.location.cds_position == 54
    assert cftr_end.location is not None
    assert cftr_end.location.cds_position == 164


def test_coordinate_map_identifies_introns_in_transcript_order() -> None:
    rpe65 = TranscriptModelStore().map_coordinate(
        gene="RPE65",
        chrom="chr1",
        position=68444920,
    )
    cftr = TranscriptModelStore().map_coordinate(
        gene="CFTR",
        transcript="ENST00000003084",
        chrom="7",
        position=117504500,
    )

    assert rpe65.available is True
    assert rpe65.location is not None
    assert rpe65.location.region == "intron"
    assert rpe65.location.intron_between_exons == (3, 4)
    assert rpe65.location.distance_to_nearest_exon == 23
    assert rpe65.location.cds_position is None

    assert cftr.available is True
    assert cftr.location is not None
    assert cftr.location.region == "intron"
    assert cftr.location.intron_between_exons == (2, 3)
    assert cftr.location.distance_to_nearest_exon == 137


def test_coordinate_map_fails_closed_for_mismatch_outside_and_invalid_states() -> None:
    store = TranscriptModelStore()

    chrom_mismatch = store.map_coordinate(gene="RPE65", chrom="chr7", position=68444869)
    outside = store.map_coordinate(gene="RPE65", chrom="1", position=68460000)
    invalid = store.map_coordinate(gene="RPE65", chrom="1", position=0)
    missing_gene = store.map_coordinate(gene="NOTAGENE", chrom="1", position=68444869)

    assert chrom_mismatch.available is False
    assert chrom_mismatch.unavailable_reason == "chromosome_mismatch"
    assert chrom_mismatch.warnings == ("transcript_model_chromosome_mismatch",)
    assert outside.available is False
    assert outside.unavailable_reason == "coordinate_outside_transcript"
    assert outside.warnings == ("transcript_model_coordinate_outside_transcript",)
    assert invalid.available is False
    assert invalid.unavailable_reason == "invalid_coordinates"
    assert invalid.warnings == ("transcript_model_invalid_coordinates",)
    assert missing_gene.available is False
    assert missing_gene.unavailable_reason == "gene_not_found"
    assert missing_gene.warnings == ("transcript_model_gene_not_found",)


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


def test_malformed_transcript_fixture_rejects_invalid_strand(tmp_path: Path) -> None:
    fixture_path = tmp_path / "bad_transcript_model.json"
    _write_transcript_fixture(
        fixture_path,
        [
            {
                "gene": "RPE65",
                "refseq_transcript": "NM_000329.3",
                "ensembl_transcript": "ENST00000262340.6",
                "transcript_aliases": ["NM_000329.3", "MANE Select"],
                "chrom": "1",
                "strand": "?",
                "exons": [
                    {
                        "number": 1,
                        "cds_start": 1,
                        "cds_end": 3,
                        "genomic_start": 100,
                        "genomic_end": 102,
                    }
                ],
            }
        ],
    )

    with pytest.raises(TranscriptModelStoreError) as exc_info:
        TranscriptModelStore(fixture_path)

    assert exc_info.value.code == "invalid_strand"
    assert exc_info.value.details == {"gene": "RPE65", "strand": "?"}


def _write_transcript_fixture(path: Path, transcripts: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "fixture_version": "test",
                    "genome_build": "GRCh38",
                    "source_ids": [MANE_SOURCE_ID, GENCODE_SOURCE_ID],
                },
                "transcripts": transcripts,
            }
        ),
        encoding="utf-8",
    )
