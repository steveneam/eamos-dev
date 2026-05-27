from __future__ import annotations

import os

import pytest

from app.data_sources import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    LOCAL_HG38_2BIT_SOURCE_ID,
    inventory_local_hg38_2bit,
    resolve_local_asset_path,
)
from app.services.reference_genome import TwoBitReferenceGenomeStore
from app.services.sequence_window_model import LocalSequenceWindowBuilder

VERIFY_LOCAL_HG38_2BIT = os.environ.get("EAMOS_VERIFY_LOCAL_HG38_2BIT") == "1"
RPE65_GRCH38_REFERENCE_BASE_CHECK = {
    "chrom": "1",
    "position": 68444869,
    "expected_base": "T",
    "variant": "NM_000329.3:c.260A>G / 1-68444869-T-C",
}

pytestmark = pytest.mark.skipif(
    not VERIFY_LOCAL_HG38_2BIT,
    reason="set EAMOS_VERIFY_LOCAL_HG38_2BIT=1 to verify the ignored local hg38.2bit asset",
)


def test_opt_in_local_hg38_asset_matches_registry_metadata() -> None:
    record = DEFAULT_DATA_SOURCE_REGISTRY.get(LOCAL_HG38_2BIT_SOURCE_ID)
    asset_path = resolve_local_asset_path(record)
    if not asset_path.exists():
        pytest.skip(f"ignored local hg38.2bit asset is absent: {asset_path}")

    inventory = inventory_local_hg38_2bit()

    assert inventory.source_id == LOCAL_HG38_2BIT_SOURCE_ID
    assert inventory.source_url == record.source_url
    assert inventory.relative_path == record.current_local_path
    assert inventory.path == asset_path
    assert inventory.path.name == "hg38.2bit"
    assert inventory.expected_size_bytes == record.actual_size_bytes_local == 835393456
    assert inventory.actual_size_bytes == 835393456
    assert inventory.size_matches is True
    assert inventory.expected_md5 == record.current_local_md5
    assert inventory.expected_md5 == "dcc3ea27079aa6dc3f9deccd7275e0f8"
    assert inventory.actual_md5 == "dcc3ea27079aa6dc3f9deccd7275e0f8"
    assert inventory.md5_matches is True
    assert inventory.md5sum_md5 == "dcc3ea27079aa6dc3f9deccd7275e0f8"
    assert inventory.md5sum_matches is True


def test_twobit_reader_verifies_rpe65_reference_base_from_local_hg38_asset() -> None:
    record = DEFAULT_DATA_SOURCE_REGISTRY.get(LOCAL_HG38_2BIT_SOURCE_ID)
    asset_path = resolve_local_asset_path(record)
    if not asset_path.exists():
        pytest.skip(f"ignored local hg38.2bit asset is absent: {asset_path}")

    with TwoBitReferenceGenomeStore.local_hg38() as store:
        check = store.validate_reference_base(
            RPE65_GRCH38_REFERENCE_BASE_CHECK["chrom"],
            RPE65_GRCH38_REFERENCE_BASE_CHECK["position"],
            RPE65_GRCH38_REFERENCE_BASE_CHECK["expected_base"],
        )

    assert check.matches is True
    assert check.chrom == "1"
    assert check.position == 68444869
    assert check.expected_base == "T"
    assert check.observed_base == "T"
    assert check.reason == "reference_base_match"


def test_local_sequence_window_builder_applies_rpe65_variant_from_hg38_asset() -> None:
    record = DEFAULT_DATA_SOURCE_REGISTRY.get(LOCAL_HG38_2BIT_SOURCE_ID)
    asset_path = resolve_local_asset_path(record)
    if not asset_path.exists():
        pytest.skip(f"ignored local hg38.2bit asset is absent: {asset_path}")

    with TwoBitReferenceGenomeStore.local_hg38() as store:
        context = LocalSequenceWindowBuilder(store, flank_bp=8).build(
            gene="RPE65",
            transcript="NM_000329.3",
            cdna_hgvs="NM_000329.3:c.260A>G",
            genomic_hg38="1-68444869-T-C",
            chrom=RPE65_GRCH38_REFERENCE_BASE_CHECK["chrom"],
            position=RPE65_GRCH38_REFERENCE_BASE_CHECK["position"],
            reference_allele=RPE65_GRCH38_REFERENCE_BASE_CHECK["expected_base"],
            alternate_allele="C",
            strand="-",
        )

    assert context.warnings == ()
    assert context.reference_window is not None
    assert context.reference_window.chrom == "1"
    assert context.reference_window.strand == "-"
    assert context.reference_base_check is not None
    assert context.reference_base_check.matches is True
    assert context.reference_base_check.observed_base == "T"
    assert context.variant_window is not None
    assert context.variant_window.reference_start_offset == 8
    assert context.reference_window.sequence[8] == "T"
    assert context.variant_window.applied_sequence[8] == "C"
    assert context.provenance is not None
    assert context.provenance.reader.startswith("twobitreader==")
