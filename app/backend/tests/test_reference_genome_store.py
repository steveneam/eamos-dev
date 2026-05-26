from __future__ import annotations

import re

import pytest

from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, LOCAL_HG38_2BIT_SOURCE_ID
from app.services.reference_genome import ReferenceGenomeStore, ReferenceGenomeStoreError


def test_fixture_store_metadata_reuses_registry_source_shape() -> None:
    store = ReferenceGenomeStore()
    metadata = store.metadata()
    source_record = DEFAULT_DATA_SOURCE_REGISTRY.get(LOCAL_HG38_2BIT_SOURCE_ID)

    assert metadata.source_id == LOCAL_HG38_2BIT_SOURCE_ID
    assert metadata.source_url == source_record.source_url
    assert metadata.source_version == "hg38_fixture_reference_v1"
    assert metadata.genome_build == "GRCh38"
    assert metadata.relative_path == "app/backend/app/fixtures/reference_genome/hg38_tiny.json"
    assert metadata.path.name == "hg38_tiny.json"
    assert metadata.reader == "fixture_json"
    assert metadata.checksum_algorithm == "sha256"
    assert re.fullmatch(r"[0-9a-f]{64}", metadata.checksum)
    assert metadata.source_local_path == source_record.current_local_path
    assert metadata.source_local_md5 == source_record.current_local_md5
    assert metadata.source_local_size_bytes == source_record.actual_size_bytes_local
    assert metadata.path.stat().st_size < 5_000


def test_get_sequence_returns_1_based_inclusive_fixture_windows() -> None:
    store = ReferenceGenomeStore()

    window = store.get_sequence("chr1", 5, 12)

    assert window.requested_chrom == "chr1"
    assert window.chrom == "1"
    assert window.start == 5
    assert window.end == 12
    assert window.zero_based_start == 4
    assert window.zero_based_end_exclusive == 12
    assert window.sequence == "ACGTACGT"
    assert window.length == 8
    assert window.genome_build == "GRCh38"
    assert window.source_id == LOCAL_HG38_2BIT_SOURCE_ID


def test_chromosome_aliases_resolve_when_present_in_fixture_metadata() -> None:
    store = ReferenceGenomeStore()

    assert store.get_sequence("1", 1, 4).sequence == "ACGT"
    assert store.get_sequence("chr1", 1, 4).sequence == "ACGT"
    assert store.get_sequence("NC_000001.11", 1, 4).sequence == "ACGT"
    assert store.get_sequence("chrM", 1, 4).sequence == "GATT"
    assert store.get_sequence("MT", 1, 4).sequence == "GATT"


def test_validate_reference_base_reports_match_and_mismatch() -> None:
    store = ReferenceGenomeStore()

    match = store.validate_reference_base("NC_000001.11", 8, "t")
    mismatch = store.validate_reference_base("1", 8, "G")

    assert match.matches is True
    assert match.chrom == "1"
    assert match.observed_base == "T"
    assert match.expected_base == "T"
    assert match.reason == "reference_base_match"

    assert mismatch.matches is False
    assert mismatch.observed_base == "T"
    assert mismatch.expected_base == "G"
    assert mismatch.reason == "reference_base_mismatch"


def test_validate_reference_base_rejects_invalid_expected_base_without_reading_window() -> None:
    store = ReferenceGenomeStore()

    result = store.validate_reference_base("chr1", 8, "TT")

    assert result.matches is False
    assert result.chrom == "1"
    assert result.observed_base is None
    assert result.reason == "invalid_expected_base"


def test_unknown_chromosome_returns_structured_error() -> None:
    store = ReferenceGenomeStore()

    with pytest.raises(ReferenceGenomeStoreError) as exc_info:
        store.get_sequence("chr7", 1, 4)

    assert exc_info.value.code == "unknown_chromosome"
    assert exc_info.value.details == {"requested_chrom": "chr7"}


def test_out_of_bounds_window_returns_structured_error() -> None:
    store = ReferenceGenomeStore()

    with pytest.raises(ReferenceGenomeStoreError) as exc_info:
        store.get_sequence("1", 30, 33)

    assert exc_info.value.code == "out_of_bounds"
    assert exc_info.value.details == {
        "chrom": "1",
        "start": 30,
        "end": 33,
        "chromosome_length": 32,
    }


@pytest.mark.parametrize(("start", "end"), [(0, 2), (10, 9)])
def test_invalid_coordinates_return_structured_error(start: int, end: int) -> None:
    store = ReferenceGenomeStore()

    with pytest.raises(ReferenceGenomeStoreError) as exc_info:
        store.get_sequence("1", start, end)

    assert exc_info.value.code == "invalid_coordinates"
    assert exc_info.value.details == {"chrom": "1", "start": start, "end": end}


def test_unsupported_build_returns_structured_error() -> None:
    store = ReferenceGenomeStore()

    with pytest.raises(ReferenceGenomeStoreError) as exc_info:
        store.get_sequence("1", 1, 4, build="GRCh37")

    assert exc_info.value.code == "unsupported_build"
    assert exc_info.value.details == {
        "requested_build": "GRCh37",
        "available_build": "GRCh38",
    }
