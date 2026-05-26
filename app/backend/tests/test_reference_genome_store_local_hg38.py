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
