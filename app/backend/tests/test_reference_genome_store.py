from __future__ import annotations

import json
import re
import struct
from pathlib import Path

import pytest

from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, LOCAL_HG38_2BIT_SOURCE_ID
from app.data_sources.local_inventory import compute_md5
import app.services.reference_genome as reference_genome_module
from app.services.reference_genome import (
    ReferenceGenomeStore,
    ReferenceGenomeStoreError,
    TwoBitReferenceGenomeStore,
)


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


def test_fixture_store_rejects_duplicate_canonical_chromosomes(tmp_path: Path) -> None:
    fixture_path = tmp_path / "duplicate_chromosome.json"
    fixture_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "source_id": LOCAL_HG38_2BIT_SOURCE_ID,
                    "genome_build": "GRCh38",
                    "source_version": "test",
                    "reader": "fixture_json",
                },
                "chromosomes": {
                    "1": {"aliases": ["1", "chr1"], "sequence": "ACGT"},
                    "chr1": {"aliases": ["NC_000001.11"], "sequence": "TGCA"},
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ReferenceGenomeStoreError) as exc_info:
        ReferenceGenomeStore(fixture_path)

    assert exc_info.value.code == "duplicate_chromosome_alias"
    assert exc_info.value.details == {"chrom": "chr1", "canonical_chrom": "1"}


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


def test_twobit_store_reads_1_based_inclusive_windows_from_fixture_file(
    tmp_path: Path,
) -> None:
    fixture_path = tmp_path / "tiny.2bit"
    _write_tiny_twobit(fixture_path, {"chr1": "ACGTACGTACGTACGT", "chrM": "GATTACAGATTACAAT"})

    with TwoBitReferenceGenomeStore(
        fixture_path,
        source_version="tiny_twobit_fixture_v1",
        expected_size_bytes=fixture_path.stat().st_size,
        expected_md5=compute_md5(fixture_path),
        verify_checksum=True,
    ) as store:
        metadata = store.metadata()
        window = store.get_sequence("NC_000001.11", 5, 12)
        base = store.validate_reference_base("chr1", 8, "T")

    assert metadata.reader == "twobitreader==3.1.8"
    assert metadata.source_version == "tiny_twobit_fixture_v1"
    assert metadata.checksum_algorithm == "md5"
    assert metadata.checksum == compute_md5(fixture_path)
    assert window.chrom == "1"
    assert window.zero_based_start == 4
    assert window.zero_based_end_exclusive == 12
    assert window.sequence == "ACGTACGT"
    assert base.matches is True
    assert base.observed_base == "T"


def test_twobit_store_rejects_missing_asset(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.2bit"

    with pytest.raises(ReferenceGenomeStoreError) as exc_info:
        TwoBitReferenceGenomeStore(missing_path)

    assert exc_info.value.code == "missing_reference_asset"
    assert exc_info.value.details == {"path": str(missing_path)}


def test_twobit_store_rejects_checksum_mismatch(tmp_path: Path) -> None:
    fixture_path = tmp_path / "tiny.2bit"
    _write_tiny_twobit(fixture_path, {"chr1": "ACGTACGTACGTACGT"})

    with pytest.raises(ReferenceGenomeStoreError) as exc_info:
        TwoBitReferenceGenomeStore(
            fixture_path,
            expected_md5="0" * 32,
            verify_checksum=True,
        )

    assert exc_info.value.code == "reference_asset_checksum_mismatch"
    assert exc_info.value.details["expected_md5"] == "0" * 32
    assert exc_info.value.details["actual_md5"] == compute_md5(fixture_path)


def test_repo_relative_path_tolerates_shallow_docker_layout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module_path = tmp_path / "image" / "app" / "services" / "reference_genome.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text("", encoding="utf-8")
    external_asset = tmp_path / "var" / "data" / "eamos" / "bio_assets" / "hg38.2bit"

    monkeypatch.setattr(reference_genome_module, "__file__", str(module_path))

    assert reference_genome_module._repo_relative_path(external_asset) == str(external_asset)


def test_twobit_store_unknown_chromosome_and_out_of_bounds_fail_closed(
    tmp_path: Path,
) -> None:
    fixture_path = tmp_path / "tiny.2bit"
    _write_tiny_twobit(fixture_path, {"chr1": "ACGTACGTACGTACGT"})

    with TwoBitReferenceGenomeStore(fixture_path) as store:
        with pytest.raises(ReferenceGenomeStoreError) as unknown_exc:
            store.get_sequence("chr7", 1, 4)
        with pytest.raises(ReferenceGenomeStoreError) as bounds_exc:
            store.get_sequence("chr1", 14, 17)

    assert unknown_exc.value.code == "unknown_chromosome"
    assert unknown_exc.value.details == {"requested_chrom": "chr7"}
    assert bounds_exc.value.code == "out_of_bounds"
    assert bounds_exc.value.details == {
        "chrom": "1",
        "start": 14,
        "end": 17,
        "chromosome_length": 16,
    }


def _write_tiny_twobit(path: Path, sequences: dict[str, str]) -> None:
    header_size = 16
    index_size = sum(1 + len(name.encode("ascii")) + 4 for name in sequences)
    offset = header_size + index_size
    records: list[bytes] = []
    index_entries: list[tuple[str, int]] = []

    for name, sequence in sequences.items():
        index_entries.append((name, offset))
        record = _twobit_sequence_record(sequence)
        records.append(record)
        offset += len(record)

    payload = bytearray()
    payload.extend(struct.pack("<LLLL", 0x1A412743, 0, len(sequences), 0))
    for name, record_offset in index_entries:
        encoded_name = name.encode("ascii")
        payload.extend(struct.pack("B", len(encoded_name)))
        payload.extend(encoded_name)
        payload.extend(struct.pack("<L", record_offset))
    for record in records:
        payload.extend(record)

    path.write_bytes(bytes(payload))


def _twobit_sequence_record(sequence: str) -> bytes:
    normalized = sequence.upper()
    if any(base not in {"A", "C", "G", "T"} for base in normalized):
        raise ValueError("tiny 2bit test writer supports only A/C/G/T")

    payload = bytearray()
    payload.extend(struct.pack("<L", len(normalized)))
    payload.extend(struct.pack("<L", 0))
    payload.extend(struct.pack("<L", 0))
    payload.extend(struct.pack("<L", 0))
    payload.extend(_pack_twobit_bases(normalized))
    while len(payload) % 4:
        payload.append(0)
    return bytes(payload)


def _pack_twobit_bases(sequence: str) -> bytes:
    base_to_bits = {"T": 0b00, "C": 0b01, "A": 0b10, "G": 0b11}
    packed = bytearray()
    for index in range(0, len(sequence), 4):
        chunk = sequence[index : index + 4].ljust(4, "T")
        byte = 0
        for base in chunk:
            byte = (byte << 2) | base_to_bits[base]
        packed.append(byte)
    return bytes(packed)
