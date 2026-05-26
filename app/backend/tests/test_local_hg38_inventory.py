from __future__ import annotations

import pytest

from app.data_sources import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    LOCAL_HG38_2BIT_SOURCE_ID,
    inventory_local_hg38_2bit,
    resolve_local_asset_path,
)


def test_local_hg38_inventory_matches_registry_metadata() -> None:
    record = DEFAULT_DATA_SOURCE_REGISTRY.get(LOCAL_HG38_2BIT_SOURCE_ID)
    asset_path = resolve_local_asset_path(record)
    if not asset_path.exists():
        pytest.skip(f"ignored local hg38.2bit asset is absent: {asset_path}")

    inventory = inventory_local_hg38_2bit()

    assert inventory.source_id == LOCAL_HG38_2BIT_SOURCE_ID
    assert inventory.source_url == record.source_url
    assert inventory.relative_path == record.current_local_path
    assert inventory.path == asset_path
    assert inventory.expected_size_bytes == 835393456
    assert inventory.actual_size_bytes == 835393456
    assert inventory.size_matches is True
    assert inventory.expected_md5 == "dcc3ea27079aa6dc3f9deccd7275e0f8"
    assert inventory.actual_md5 == "dcc3ea27079aa6dc3f9deccd7275e0f8"
    assert inventory.md5_matches is True
    assert inventory.md5sum_md5 == "dcc3ea27079aa6dc3f9deccd7275e0f8"
    assert inventory.md5sum_matches is True


def test_local_hg38_inventory_resolves_repo_relative_path() -> None:
    record = DEFAULT_DATA_SOURCE_REGISTRY.get(LOCAL_HG38_2BIT_SOURCE_ID)

    path = resolve_local_asset_path(record)

    assert path.is_absolute()
    assert path.name == "hg38.2bit"
    assert path.parts[-6:] == ("app", "backend", "data", "bio_assets", "genomes") + ("hg38.2bit",)
