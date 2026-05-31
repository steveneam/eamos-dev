from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import md5
from pathlib import Path

import pytest

from app.core.config import Settings
from app.data_sources import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    DEFAULT_SOURCE_RECORDS,
    DataSourceRegistry,
    RuntimeAssetMode,
    RuntimeAssetStatus,
    SourceAssetMaterializationError,
    SourceAssetMaterializationRecord,
    build_hg38_runtime_asset_plan,
    inspect_hg38_runtime_asset,
    probe_hg38_materialization_status,
    resolve_hg38_materialized_runtime_asset,
)
from app.data_sources.runtime_assets import _resolve_materialization_path
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


def test_hg38_materialized_reader_resolves_verified_private_metadata(
    tmp_path: Path,
) -> None:
    payload = b"small-test-2bit"
    asset_path = tmp_path / "hg38.2bit"
    asset_path.write_bytes(payload)
    settings = Settings(jwt_secret="test-secret", hg38_2bit_runtime_asset_path=asset_path)
    store = FakeMaterializationStore(_materialization_record(payload, asset_path))

    resolved = resolve_hg38_materialized_runtime_asset(
        settings,
        store,
        registry=_tiny_registry(payload),
        verify_checksum=True,
    )

    assert resolved.source_id == "ucsc_hg38_2bit"
    assert resolved.path == asset_path
    assert resolved.bucket_id == "eamos-source-assets"
    assert resolved.byte_size == len(payload)
    assert resolved.checksum_value == _md5(payload)
    assert resolved.inspection.ready is True


def test_hg38_materialized_reader_fails_closed_on_public_metadata(
    tmp_path: Path,
) -> None:
    payload = b"small-test-2bit"
    asset_path = tmp_path / "hg38.2bit"
    asset_path.write_bytes(payload)
    settings = Settings(jwt_secret="test-secret", hg38_2bit_runtime_asset_path=asset_path)
    record = replace(
        _materialization_record(payload, asset_path),
        public_access_allowed=True,
    )

    with pytest.raises(SourceAssetMaterializationError) as exc_info:
        resolve_hg38_materialized_runtime_asset(
            settings,
            FakeMaterializationStore(record),
            registry=_tiny_registry(payload),
        )

    assert exc_info.value.code == "materialization_public_access_blocked"


def test_hg38_materialized_reader_fails_closed_on_checksum_mismatch(
    tmp_path: Path,
) -> None:
    payload = b"small-test-2bit"
    asset_path = tmp_path / "hg38.2bit"
    asset_path.write_bytes(payload)
    settings = Settings(jwt_secret="test-secret", hg38_2bit_runtime_asset_path=asset_path)
    record = replace(
        _materialization_record(payload, asset_path),
        checksum_value="0" * 32,
    )

    with pytest.raises(SourceAssetMaterializationError) as exc_info:
        resolve_hg38_materialized_runtime_asset(
            settings,
            FakeMaterializationStore(record),
            registry=_tiny_registry(payload),
        )

    assert exc_info.value.code == "materialization_checksum_mismatch"


def test_hg38_materialized_reader_filters_configured_object_uri(
    tmp_path: Path,
) -> None:
    payload = b"small-test-2bit"
    asset_path = tmp_path / "hg38.2bit"
    asset_path.write_bytes(payload)
    object_path = "ucsc_hg38_2bit/hg38/md5-test/hg38.2bit"
    settings = Settings(
        jwt_secret="test-secret",
        hg38_2bit_runtime_asset_path=asset_path,
        hg38_2bit_runtime_asset_object_uri=f"supabase://eamos-source-assets/{object_path}",
    )
    store = FakeMaterializationStore(_materialization_record(payload, asset_path, object_path))

    resolve_hg38_materialized_runtime_asset(
        settings,
        store,
        registry=_tiny_registry(payload),
    )

    assert store.calls == [
        {
            "source_id": "ucsc_hg38_2bit",
            "asset_role": "reference_genome_2bit",
            "bucket_id": "eamos-source-assets",
            "object_path": object_path,
            "environment": None,
        }
    ]


def test_hg38_materialization_probe_reports_ready_without_sensitive_paths(
    tmp_path: Path,
) -> None:
    payload = b"small-test-2bit"
    asset_path = tmp_path / "hg38.2bit"
    asset_path.write_bytes(payload)
    settings = Settings(jwt_secret="test-secret", hg38_2bit_runtime_asset_path=asset_path)

    summary = probe_hg38_materialization_status(
        settings,
        FakeMaterializationStore(_materialization_record(payload, asset_path)),
        registry=_tiny_registry(payload),
        verify_checksum=True,
    )

    assert summary["enabled"] is True
    assert summary["probe_performed"] is True
    assert summary["ready"] is True
    assert summary["status"] == "ready"
    assert summary["byte_size"] == len(payload)
    assert summary["checksum_algorithm"] == "md5"
    assert summary["failure_boundaries"] == {
        "health_and_preflight_probe": "sanitized_status_no_exception",
        "lookup_sequence_context_runtime": "fail_open",
        "metadata_and_local_cache_resolution": "fail_closed",
    }
    encoded = str(summary).lower()
    assert str(tmp_path).lower() not in encoded
    assert "ucsc_hg38_2bit/hg38/md5-test/hg38.2bit" not in encoded
    assert _md5(payload) not in encoded


def test_hg38_materialization_probe_catches_unexpected_errors() -> None:
    settings = Settings(jwt_secret="test-secret")

    summary = probe_hg38_materialization_status(settings, ExplodingMaterializationStore())

    assert summary["enabled"] is True
    assert summary["probe_performed"] is True
    assert summary["ready"] is False
    assert summary["status"] == "materialization_probe_failed"


def test_materialization_path_strips_app_backend_prefix_under_shallow_backend_root(
    monkeypatch,
) -> None:
    shallow_root = Path("/app")
    monkeypatch.setattr(Settings, "backend_root", property(lambda self: shallow_root))
    settings = Settings(jwt_secret="test-secret")

    resolved = _resolve_materialization_path(
        settings,
        "app/backend/data/bio_assets/genomes/hg38.2bit",
    )

    assert resolved == shallow_root / "data" / "bio_assets" / "genomes" / "hg38.2bit"


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


class FakeMaterializationStore:
    def __init__(self, record: SourceAssetMaterializationRecord | None) -> None:
        self.record = record
        self.calls: list[dict[str, object]] = []

    def get_source_asset_materialization(
        self,
        *,
        source_id: str,
        asset_role: str,
        bucket_id: str | None = None,
        object_path: str | None = None,
        environment: str | None = None,
    ) -> SourceAssetMaterializationRecord | None:
        self.calls.append(
            {
                "source_id": source_id,
                "asset_role": asset_role,
                "bucket_id": bucket_id,
                "object_path": object_path,
                "environment": environment,
            }
        )
        if self.record is None:
            return None
        if bucket_id is not None and self.record.bucket_id != bucket_id:
            return None
        if object_path is not None and self.record.object_path != object_path:
            return None
        if environment is not None and self.record.environment != environment:
            return None
        return self.record


class ExplodingMaterializationStore:
    def get_source_asset_materialization(self, **kwargs) -> SourceAssetMaterializationRecord:
        raise RuntimeError("database unavailable at postgresql://private.example/path")


def _materialization_record(
    payload: bytes,
    asset_path: Path,
    object_path: str = "ucsc_hg38_2bit/hg38/md5-test/hg38.2bit",
) -> SourceAssetMaterializationRecord:
    return SourceAssetMaterializationRecord(
        source_id="ucsc_hg38_2bit",
        asset_role="reference_genome_2bit",
        bucket_id="eamos-source-assets",
        object_path=object_path,
        upload_status="verified",
        approval_status="approved",
        public_access_allowed=False,
        frontend_direct_access_allowed=False,
        environment="dev-local",
        backend_runtime="render_backend",
        local_cache_path=str(asset_path),
        materialization_status="ready",
        byte_size=len(payload),
        checksum_algorithm="md5",
        checksum_value=_md5(payload),
        verified_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
        fail_closed_reason=None,
        metadata={"fixture": True},
        warnings=[],
    )
