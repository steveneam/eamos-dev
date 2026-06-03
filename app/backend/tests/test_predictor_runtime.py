from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import md5
from pathlib import Path

from app.core.config import Settings
from app.data_sources import (
    DEFAULT_SOURCE_RECORDS,
    DataSourceRegistry,
    SourceAssetMaterializationRecord,
)
from app.services.predictor_runtime import (
    ALPHAMISSENSE_ASSET_ROLE,
    ALPHAMISSENSE_SOURCE_ID,
    PredictorRuntimeStatus,
    build_alphamissense_runtime_plan,
    inspect_alphamissense_runtime_asset,
)


def test_alphamissense_runtime_plan_records_source_md5_and_bucket_limit() -> None:
    settings = Settings(jwt_secret="test-secret")

    plan = build_alphamissense_runtime_plan(settings, bucket_file_size_limit=1234)

    assert plan.source_id == ALPHAMISSENSE_SOURCE_ID
    assert plan.asset_role == ALPHAMISSENSE_ASSET_ROLE
    assert plan.path == (
        settings.backend_root
        / "data"
        / "bio_assets"
        / "predictors"
        / "alphamissense"
        / "AlphaMissense_hg38.tsv.gz"
    )
    assert plan.index_path == Path(f"{plan.path}.tbi")
    assert plan.manifest_path.name == "AlphaMissense_hg38.tsv.gz.manifest.json"
    assert plan.expected_md5 == "9fd167735f16a1b87da6eb3e4c25fcb5"
    assert plan.bucket_file_size_limit == 1234
    assert plan.reader_requires_local_path is True


def test_alphamissense_preflight_reports_missing_file(tmp_path: Path) -> None:
    settings = Settings(
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_path=tmp_path / "missing.tsv.gz",
    )

    inspection = inspect_alphamissense_runtime_asset(settings)

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MISSING_SOURCE_FILE
    assert inspection.actual_size_bytes is None


def test_alphamissense_preflight_reports_missing_index_before_manifest(
    tmp_path: Path,
) -> None:
    asset = tmp_path / "AlphaMissense_hg38.tsv.gz"
    asset.write_bytes(b"tiny")
    settings = Settings(jwt_secret="test-secret", alphamissense_hg38_runtime_asset_path=asset)

    inspection = inspect_alphamissense_runtime_asset(settings)

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MISSING_INDEX
    assert inspection.actual_size_bytes == len(b"tiny")


def test_alphamissense_preflight_reports_missing_manifest(tmp_path: Path) -> None:
    asset = tmp_path / "AlphaMissense_hg38.tsv.gz"
    asset.write_bytes(b"tiny")
    Path(f"{asset}.tbi").write_bytes(b"index")
    settings = Settings(jwt_secret="test-secret", alphamissense_hg38_runtime_asset_path=asset)

    inspection = inspect_alphamissense_runtime_asset(settings)

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MISSING_MANIFEST


def test_alphamissense_preflight_reports_ready_and_checksum_match(
    tmp_path: Path,
) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    settings = Settings(jwt_secret="test-secret", alphamissense_hg38_runtime_asset_path=asset)

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
        verify_checksum=True,
    )

    assert inspection.ready is True
    assert inspection.status is PredictorRuntimeStatus.READY
    assert inspection.actual_size_bytes == len(payload)
    assert inspection.actual_md5 == _md5(payload)


def test_alphamissense_preflight_reports_checksum_mismatch(tmp_path: Path) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    settings = Settings(jwt_secret="test-secret", alphamissense_hg38_runtime_asset_path=asset)

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload, expected_md5="0" * 32),
        verify_checksum=True,
    )

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.CHECKSUM_MISMATCH
    assert inspection.actual_md5 == _md5(payload)


def test_alphamissense_object_mode_requires_materialization_metadata(
    tmp_path: Path,
) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    settings = Settings(
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_mode="object_storage_local_cache",
        alphamissense_hg38_runtime_asset_path=asset,
        alphamissense_hg38_runtime_asset_object_uri=(
            "supabase://eamos-source-assets/google_deepmind_alphamissense_hg38/"
            "md5-test/AlphaMissense_hg38.tsv.gz"
        ),
    )

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
    )

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MATERIALIZATION_STORE_UNAVAILABLE
    assert inspection.materialization_status == "metadata_store_unavailable"


def test_alphamissense_materialization_rejects_public_metadata(
    tmp_path: Path,
) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    object_path = "google_deepmind_alphamissense_hg38/md5-test/AlphaMissense_hg38.tsv.gz"
    settings = Settings(
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_path=asset,
        alphamissense_hg38_runtime_asset_object_uri=f"supabase://eamos-source-assets/{object_path}",
    )
    record = replace(
        _materialization_record(payload, asset, object_path),
        public_access_allowed=True,
    )

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
        materialization_store=FakeMaterializationStore(record),
    )

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MATERIALIZATION_PUBLIC_ACCESS_BLOCKED
    assert inspection.materialization_status == "materialization_public_access_blocked"


def test_alphamissense_materialization_rejects_size_mismatch(
    tmp_path: Path,
) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    object_path = "google_deepmind_alphamissense_hg38/md5-test/AlphaMissense_hg38.tsv.gz"
    settings = Settings(
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_path=asset,
        alphamissense_hg38_runtime_asset_object_uri=f"supabase://eamos-source-assets/{object_path}",
    )
    record = replace(
        _materialization_record(payload, asset, object_path),
        byte_size=len(payload) + 1,
    )

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
        materialization_store=FakeMaterializationStore(record),
    )

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MATERIALIZATION_SIZE_MISMATCH
    assert inspection.materialization_status == "materialization_size_mismatch"


def test_alphamissense_materialization_reports_ready_without_sensitive_checksum(
    tmp_path: Path,
) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    object_path = "google_deepmind_alphamissense_hg38/md5-test/AlphaMissense_hg38.tsv.gz"
    settings = Settings(
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_path=asset,
        alphamissense_hg38_runtime_asset_object_uri=f"supabase://eamos-source-assets/{object_path}",
    )

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
        materialization_store=FakeMaterializationStore(
            _materialization_record(payload, asset, object_path)
        ),
        verify_checksum=True,
    )

    assert inspection.ready is True
    assert inspection.status is PredictorRuntimeStatus.READY
    assert inspection.materialization_status == "ready"
    assert inspection.bucket_file_size_limit == 50 * 1024 * 1024 * 1024


class FakeMaterializationStore:
    def __init__(self, record: SourceAssetMaterializationRecord | None) -> None:
        self.record = record

    def get_source_asset_materialization(self, **kwargs) -> SourceAssetMaterializationRecord | None:
        return self.record


def _write_materialized_asset(tmp_path: Path, payload: bytes) -> Path:
    asset = tmp_path / "AlphaMissense_hg38.tsv.gz"
    asset.write_bytes(payload)
    Path(f"{asset}.tbi").write_bytes(b"index")
    asset.with_suffix(asset.suffix + ".manifest.json").write_text(
        '{"md5":"%s","sha256":"%s"}' % (_md5(payload), "a" * 64),
        encoding="utf-8",
    )
    return asset


def _tiny_registry(payload: bytes, *, expected_md5: str | None = None) -> DataSourceRegistry:
    checksum = expected_md5 or _md5(payload)
    return DataSourceRegistry(
        [
            (
                replace(
                    record,
                    checksum_plan=f"Verify Zenodo MD5 {checksum} for fixture",
                )
                if record.source_id == ALPHAMISSENSE_SOURCE_ID
                else record
            )
            for record in DEFAULT_SOURCE_RECORDS
        ]
    )


def _materialization_record(
    payload: bytes,
    asset_path: Path,
    object_path: str,
) -> SourceAssetMaterializationRecord:
    return SourceAssetMaterializationRecord(
        source_id=ALPHAMISSENSE_SOURCE_ID,
        asset_role=ALPHAMISSENSE_ASSET_ROLE,
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
        verified_at=datetime(2026, 6, 3, tzinfo=timezone.utc),
        fail_closed_reason=None,
        metadata={"fixture": True},
        warnings=[],
    )


def _md5(payload: bytes) -> str:
    return md5(payload).hexdigest()
