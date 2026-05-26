from __future__ import annotations

import os

import pytest

from app.data_sources import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    LOCAL_HG38_2BIT_SOURCE_ID,
    inventory_local_hg38_2bit,
    resolve_local_asset_path,
)

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


def test_rpe65_reference_base_check_is_pending_until_2bit_reader_is_approved() -> None:
    pytest.skip(
        "pending Task 7 2bit reader approval: GRCh38 "
        f"{RPE65_GRCH38_REFERENCE_BASE_CHECK['chrom']}:"
        f"{RPE65_GRCH38_REFERENCE_BASE_CHECK['position']} should be "
        f"{RPE65_GRCH38_REFERENCE_BASE_CHECK['expected_base']} for "
        f"{RPE65_GRCH38_REFERENCE_BASE_CHECK['variant']}"
    )
