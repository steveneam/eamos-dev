from __future__ import annotations

from dataclasses import replace
from hashlib import md5
from pathlib import Path

from app.core.config import Settings
from app.data_sources import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    DEFAULT_SOURCE_RECORDS,
    DataSourceRegistry,
    RuntimeAssetMode,
    RuntimeAssetStatus,
    build_hg38_runtime_asset_plan,
    inspect_hg38_runtime_asset,
)
from app.services.reference_genome import ReferenceGenomeStore


def test_default_hg38_runtime_asset_plan_uses_backend_local_path() -> None:
    settings = Settings(jwt_secret="test-secret")
    plan = build_hg38_runtime_asset_plan(settings)
    record = DEFAULT_DATA_SOURCE_REGISTRY.get("ucsc_hg38_2bit")

    assert plan.source_id == "ucsc_hg38_2bit"
    assert plan.mode == RuntimeAssetMode.LOCAL_PATH.value
    assert plan.path == settings.backend_root / "data" / "bio_assets" / "genomes" / "hg38.2bit"
    assert plan.source_url == record.source_url
    assert plan.object_uri is None
    assert plan.expected_size_bytes == 835393456
    assert plan.expected_md5 == "dcc3ea27079aa6dc3f9deccd7275e0f8"
    assert plan.reader_requires_local_path is True
    assert set(plan.supported_modes) == {
        RuntimeAssetMode.LOCAL_PATH.value,
        RuntimeAssetMode.OBJECT_STORAGE_LOCAL_CACHE.value,
        RuntimeAssetMode.MOUNTED_VOLUME.value,
    }


def test_missing_hg38_runtime_asset_reports_missing_without_breaking_fixture_store(
    tmp_path: Path,
) -> None:
    settings = Settings(
        jwt_secret="test-secret",
        hg38_2bit_runtime_asset_path=tmp_path / "missing-hg38.2bit",
    )

    inspection = inspect_hg38_runtime_asset(settings, registry=_tiny_registry(b"ACGT"))

    assert inspection.ready is False
    assert inspection.status is RuntimeAssetStatus.MISSING
    assert inspection.actual_size_bytes is None
    assert "missing" in inspection.message
    assert ReferenceGenomeStore().metadata().reader == "fixture_json"


def test_hg38_runtime_asset_reports_ready_for_checksum_matched_local_file(
    tmp_path: Path,
) -> None:
    payload = b"small-test-2bit"
    asset_path = tmp_path / "hg38.2bit"
    asset_path.write_bytes(payload)
    settings = Settings(jwt_secret="test-secret", hg38_2bit_runtime_asset_path=asset_path)

    inspection = inspect_hg38_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
        verify_checksum=True,
    )

    assert inspection.ready is True
    assert inspection.status is RuntimeAssetStatus.READY
    assert inspection.actual_size_bytes == len(payload)
    assert inspection.actual_md5 == _md5(payload)


def test_hg38_runtime_asset_reports_checksum_mismatch(tmp_path: Path) -> None:
    payload = b"small-test-2bit"
    asset_path = tmp_path / "hg38.2bit"
    asset_path.write_bytes(payload)
    settings = Settings(jwt_secret="test-secret", hg38_2bit_runtime_asset_path=asset_path)

    inspection = inspect_hg38_runtime_asset(
        settings,
        registry=_tiny_registry(payload, expected_md5="0" * 32),
        verify_checksum=True,
    )

    assert inspection.ready is False
    assert inspection.status is RuntimeAssetStatus.CHECKSUM_MISMATCH
    assert inspection.actual_size_bytes == len(payload)
    assert inspection.actual_md5 == _md5(payload)


def test_hg38_object_storage_mode_requires_source_uri(tmp_path: Path) -> None:
    payload = b"small-test-2bit"
    asset_path = tmp_path / "hg38.2bit"
    asset_path.write_bytes(payload)
    settings = Settings(
        jwt_secret="test-secret",
        hg38_2bit_runtime_asset_mode=RuntimeAssetMode.OBJECT_STORAGE_LOCAL_CACHE.value,
        hg38_2bit_runtime_asset_path=asset_path,
    )

    inspection = inspect_hg38_runtime_asset(settings, registry=_tiny_registry(payload))

    assert inspection.ready is False
    assert inspection.status is RuntimeAssetStatus.CONFIG_ERROR
    assert "object URI" in inspection.message


def test_hg38_object_storage_mode_reports_cache_ready_when_uri_and_checksum_match(
    tmp_path: Path,
) -> None:
    payload = b"small-test-2bit"
    asset_path = tmp_path / "hg38.2bit"
    asset_path.write_bytes(payload)
    settings = Settings(
        jwt_secret="test-secret",
        hg38_2bit_runtime_asset_mode=RuntimeAssetMode.OBJECT_STORAGE_LOCAL_CACHE.value,
        hg38_2bit_runtime_asset_path=asset_path,
        hg38_2bit_runtime_asset_object_uri="supabase://source-assets/genomes/hg38.2bit",
    )

    inspection = inspect_hg38_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
        verify_checksum=True,
    )

    assert inspection.ready is True
    assert inspection.status is RuntimeAssetStatus.READY
    assert inspection.object_uri == "supabase://source-assets/genomes/hg38.2bit"
    assert inspection.reader_requires_local_path is True


def test_hg38_runtime_asset_reports_size_mismatch_before_checksum(tmp_path: Path) -> None:
    payload = b"small-test-2bit"
    asset_path = tmp_path / "hg38.2bit"
    asset_path.write_bytes(payload)
    settings = Settings(jwt_secret="test-secret", hg38_2bit_runtime_asset_path=asset_path)

    inspection = inspect_hg38_runtime_asset(
        settings,
        registry=_tiny_registry(payload, expected_size=len(payload) + 1),
        verify_checksum=True,
    )

    assert inspection.ready is False
    assert inspection.status is RuntimeAssetStatus.SIZE_MISMATCH
    assert inspection.actual_size_bytes == len(payload)
    assert inspection.actual_md5 is None


def test_hg38_runtime_asset_reports_invalid_mode_as_config_error(tmp_path: Path) -> None:
    settings = Settings(
        jwt_secret="test-secret",
        hg38_2bit_runtime_asset_mode="direct_object_stream",
        hg38_2bit_runtime_asset_path=tmp_path / "hg38.2bit",
    )

    inspection = inspect_hg38_runtime_asset(settings, registry=_tiny_registry(b"ACGT"))

    assert inspection.ready is False
    assert inspection.status is RuntimeAssetStatus.CONFIG_ERROR
    assert "unsupported" in inspection.message


def _tiny_registry(
    payload: bytes,
    *,
    expected_size: int | None = None,
    expected_md5: str | None = None,
) -> DataSourceRegistry:
    return DataSourceRegistry(
        [
            (
                replace(
                    record,
                    actual_size_bytes_local=(
                        len(payload) if expected_size is None else expected_size
                    ),
                    current_local_md5=expected_md5 or _md5(payload),
                )
                if record.source_id == "ucsc_hg38_2bit"
                else record
            )
            for record in DEFAULT_SOURCE_RECORDS
        ]
    )


def _md5(payload: bytes) -> str:
    return md5(payload).hexdigest()
