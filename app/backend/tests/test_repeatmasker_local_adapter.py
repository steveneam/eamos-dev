from __future__ import annotations

import re

from app.services.repeatmasker_local import REPEATMASKER_SOURCE_ID, RepeatMaskerLocalStore


def test_store_provenance_records_repeatmasker_fixture_and_conversion_strategy() -> None:
    provenance = RepeatMaskerLocalStore().provenance()

    assert provenance.source_id == REPEATMASKER_SOURCE_ID
    assert provenance.source_version == "UCSC hg38 rmsk table dump 2022-10-18"
    assert (
        provenance.relative_path
        == "app/backend/app/fixtures/data_sources/repeatmasker_tiny.rmsk.txt"
    )
    assert provenance.checksum_algorithm == "sha256"
    assert re.fullmatch(r"[0-9a-f]{64}", provenance.checksum)
    assert provenance.conversion_strategy == "deterministic_rmsk_text_to_indexed_interval_table"
    assert provenance.source_format == "ucsc_rmsk_txt_rows"


def test_tiny_fixture_returns_repeat_overlaps_and_no_hit_windows() -> None:
    store = RepeatMaskerLocalStore()

    overlaps = store.query_window(chrom="NC_000001.11", start=101, end=120)
    no_hit = store.query_window(chrom="chr1", start=131, end=149)

    assert overlaps.available is True
    assert len(overlaps.repeats) == 1
    assert overlaps.repeats[0].chrom == "1"
    assert overlaps.repeats[0].start == 101
    assert overlaps.repeats[0].end == 130
    assert overlaps.repeats[0].name == "AluY"
    assert overlaps.repeats[0].repeat_class == "SINE"
    assert overlaps.repeats[0].repeat_family == "Alu"
    assert overlaps.repeats[0].strand == "+"
    assert overlaps.repeats[0].provenance.source_id == REPEATMASKER_SOURCE_ID
    assert no_hit.available is True
    assert no_hit.repeats == ()


def test_unknown_contig_and_invalid_window_fail_closed() -> None:
    store = RepeatMaskerLocalStore()

    unknown = store.query_window(chrom="chr7", start=101, end=120)
    invalid = store.query_window(chrom="chr1", start=120, end=101)

    assert unknown.available is False
    assert unknown.unavailable_reason == "contig_not_found"
    assert unknown.warnings == ("repeatmasker_local_contig_not_found",)
    assert invalid.available is False
    assert invalid.unavailable_reason == "invalid_coordinates"
    assert invalid.warnings == ("repeatmasker_local_invalid_coordinates",)
