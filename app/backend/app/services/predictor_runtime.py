from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re

from app.core.config import Settings
from app.data_sources.local_inventory import compute_md5
from app.data_sources.registry import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry
from app.data_sources.runtime_assets import (
    RuntimeAssetMode,
    SourceAssetMaterializationError,
    SourceAssetMaterializationRecord,
    SourceAssetMaterializationStore,
    _parse_supabase_object_uri,
    _resolve_materialization_path,
)
from app.services.source_storage_uploads import DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT

ALPHAMISSENSE_SOURCE_ID = "google_deepmind_alphamissense_hg38"
ALPHAMISSENSE_ASSET_ROLE = "predictor_tabix_tsv"


class PredictorRuntimeStatus(str, Enum):
    READY = "ready"
    MISSING_SOURCE_FILE = "missing_source_file"
    SOURCE_PATH_NOT_FILE = "source_path_not_file"
    MISSING_INDEX = "missing_index"
    INDEX_PATH_NOT_FILE = "index_path_not_file"
    MISSING_MANIFEST = "missing_manifest"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    CONFIG_ERROR = "config_error"
    MATERIALIZATION_STORE_UNAVAILABLE = "materialization_store_unavailable"
    MATERIALIZATION_METADATA_MISSING = "materialization_metadata_missing"
    MATERIALIZATION_PUBLIC_ACCESS_BLOCKED = "materialization_public_access_blocked"
    MATERIALIZATION_UPLOAD_NOT_VERIFIED = "materialization_upload_not_verified"
    MATERIALIZATION_NOT_APPROVED = "materialization_not_approved"
    MATERIALIZATION_NOT_READY = "materialization_not_ready"
    MATERIALIZATION_FAIL_CLOSED = "materialization_fail_closed"
    MATERIALIZATION_VERIFIED_AT_MISSING = "materialization_verified_at_missing"
    MATERIALIZATION_SIZE_MISMATCH = "materialization_size_mismatch"
    MATERIALIZATION_CHECKSUM_MISSING = "materialization_checksum_missing"
    MATERIALIZATION_CHECKSUM_MISMATCH = "materialization_checksum_mismatch"
    MATERIALIZATION_PATH_MISMATCH = "materialization_path_mismatch"


@dataclass(frozen=True)
class PredictorRuntimePlan:
    source_id: str
    asset_role: str
    mode: str
    path: Path
    index_path: Path
    manifest_path: Path
    source_url: str | None
    object_uri: str | None
    expected_md5: str | None
    reader_requires_local_path: bool
    supported_modes: tuple[str, ...]
    bucket_file_size_limit: int


@dataclass(frozen=True)
class PredictorRuntimeInspection:
    source_id: str
    asset_role: str
    mode: str
    status: PredictorRuntimeStatus
    path: Path
    index_path: Path
    manifest_path: Path
    actual_size_bytes: int | None
    expected_md5: str | None
    actual_md5: str | None
    object_uri: str | None
    reader_requires_local_path: bool
    bucket_file_size_limit: int
    materialization_status: str | None
    message: str

    @property
    def ready(self) -> bool:
        return self.status is PredictorRuntimeStatus.READY


def build_alphamissense_runtime_plan(
    settings: Settings,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    *,
    bucket_file_size_limit: int = DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
) -> PredictorRuntimePlan:
    record = registry.get(ALPHAMISSENSE_SOURCE_ID)
    path = _resolve_backend_path(settings, settings.alphamissense_hg38_runtime_asset_path)
    return PredictorRuntimePlan(
        source_id=record.source_id,
        asset_role=ALPHAMISSENSE_ASSET_ROLE,
        mode=settings.alphamissense_hg38_runtime_asset_mode.strip().lower(),
        path=path,
        index_path=Path(f"{path}.tbi"),
        manifest_path=path.with_suffix(path.suffix + ".manifest.json"),
        source_url=record.source_url,
        object_uri=settings.alphamissense_hg38_runtime_asset_object_uri,
        expected_md5=_expected_md5(record.current_local_md5, record.checksum_plan),
        reader_requires_local_path=True,
        supported_modes=record.runtime_delivery_modes,
        bucket_file_size_limit=bucket_file_size_limit,
    )


def inspect_alphamissense_runtime_asset(
    settings: Settings,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    *,
    verify_checksum: bool = False,
    require_manifest: bool = True,
    materialization_store: SourceAssetMaterializationStore | None = None,
    environment: str | None = None,
    bucket_file_size_limit: int = DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
) -> PredictorRuntimeInspection:
    plan = build_alphamissense_runtime_plan(
        settings,
        registry=registry,
        bucket_file_size_limit=bucket_file_size_limit,
    )
    base = _inspect_predictor_local_files(
        plan,
        verify_checksum=verify_checksum,
        require_manifest=require_manifest,
    )
    if not base.ready:
        return base
    if materialization_store is None:
        if plan.mode == RuntimeAssetMode.OBJECT_STORAGE_LOCAL_CACHE.value:
            return _inspection(
                plan,
                PredictorRuntimeStatus.MATERIALIZATION_STORE_UNAVAILABLE,
                "AlphaMissense object-storage mode requires materialization metadata",
                actual_size_bytes=base.actual_size_bytes,
                actual_md5=base.actual_md5,
                materialization_status="metadata_store_unavailable",
            )
        return base

    try:
        _validate_materialization_record(
            settings,
            plan,
            materialization_store,
            environment=environment,
        )
    except SourceAssetMaterializationError as exc:
        status = _MATERIALIZATION_ERROR_STATUS.get(
            exc.code,
            PredictorRuntimeStatus.CONFIG_ERROR,
        )
        return _inspection(
            plan,
            status,
            str(exc),
            actual_size_bytes=base.actual_size_bytes,
            actual_md5=base.actual_md5,
            materialization_status=exc.code,
        )

    return _inspection(
        plan,
        PredictorRuntimeStatus.READY,
        "AlphaMissense runtime asset is ready",
        actual_size_bytes=base.actual_size_bytes,
        actual_md5=base.actual_md5,
        materialization_status="ready",
    )


def _inspect_predictor_local_files(
    plan: PredictorRuntimePlan,
    *,
    verify_checksum: bool,
    require_manifest: bool,
) -> PredictorRuntimeInspection:
    supported_modes = _supported_mode_values()
    if plan.mode not in supported_modes:
        return _inspection(
            plan,
            PredictorRuntimeStatus.CONFIG_ERROR,
            f"unsupported AlphaMissense runtime asset mode: {plan.mode}",
        )
    if plan.mode not in set(plan.supported_modes):
        return _inspection(
            plan,
            PredictorRuntimeStatus.CONFIG_ERROR,
            f"registry does not support AlphaMissense runtime asset mode: {plan.mode}",
        )
    if plan.mode == RuntimeAssetMode.OBJECT_STORAGE_LOCAL_CACHE.value and not plan.object_uri:
        return _inspection(
            plan,
            PredictorRuntimeStatus.CONFIG_ERROR,
            "object_storage_local_cache mode requires an object URI for AlphaMissense",
        )
    if plan.reader_requires_local_path and not plan.path:
        return _inspection(
            plan,
            PredictorRuntimeStatus.CONFIG_ERROR,
            "AlphaMissense reader requires a configured local filesystem path",
        )

    if not plan.path.exists():
        return _inspection(
            plan,
            PredictorRuntimeStatus.MISSING_SOURCE_FILE,
            "AlphaMissense source TSV is missing",
        )
    if not plan.path.is_file():
        return _inspection(
            plan,
            PredictorRuntimeStatus.SOURCE_PATH_NOT_FILE,
            "AlphaMissense runtime asset path is not a file",
        )
    actual_size = plan.path.stat().st_size

    if not plan.index_path.exists():
        return _inspection(
            plan,
            PredictorRuntimeStatus.MISSING_INDEX,
            "AlphaMissense tabix index is missing",
            actual_size_bytes=actual_size,
        )
    if not plan.index_path.is_file():
        return _inspection(
            plan,
            PredictorRuntimeStatus.INDEX_PATH_NOT_FILE,
            "AlphaMissense tabix index path is not a file",
            actual_size_bytes=actual_size,
        )

    if require_manifest and not plan.manifest_path.is_file():
        return _inspection(
            plan,
            PredictorRuntimeStatus.MISSING_MANIFEST,
            "AlphaMissense checksum manifest is missing",
            actual_size_bytes=actual_size,
        )

    actual_md5 = compute_md5(plan.path) if verify_checksum else None
    if actual_md5 is not None and plan.expected_md5 and actual_md5.lower() != plan.expected_md5:
        return _inspection(
            plan,
            PredictorRuntimeStatus.CHECKSUM_MISMATCH,
            "AlphaMissense source TSV checksum does not match registry metadata",
            actual_size_bytes=actual_size,
            actual_md5=actual_md5,
        )

    return _inspection(
        plan,
        PredictorRuntimeStatus.READY,
        "AlphaMissense runtime asset is ready",
        actual_size_bytes=actual_size,
        actual_md5=actual_md5,
    )


def _validate_materialization_record(
    settings: Settings,
    plan: PredictorRuntimePlan,
    materialization_store: SourceAssetMaterializationStore,
    *,
    environment: str | None,
) -> SourceAssetMaterializationRecord:
    bucket_id, object_path = _parse_supabase_object_uri(plan.object_uri)
    record = materialization_store.get_source_asset_materialization(
        source_id=plan.source_id,
        asset_role=plan.asset_role,
        bucket_id=bucket_id,
        object_path=object_path,
        environment=environment,
    )
    if record is None:
        raise SourceAssetMaterializationError(
            "materialization_metadata_missing",
            "no AlphaMissense materialization metadata is available",
            {"source_id": plan.source_id, "asset_role": plan.asset_role},
        )
    if record.source_id != plan.source_id or record.asset_role != plan.asset_role:
        raise SourceAssetMaterializationError(
            "materialization_source_mismatch",
            "AlphaMissense materialization metadata is for the wrong source asset",
            {"source_id": plan.source_id},
        )
    if record.public_access_allowed or record.frontend_direct_access_allowed:
        raise SourceAssetMaterializationError(
            "materialization_public_access_blocked",
            "AlphaMissense materialization metadata allows public or frontend access",
            {"source_id": plan.source_id},
        )
    if record.upload_status != "verified":
        raise SourceAssetMaterializationError(
            "materialization_upload_not_verified",
            "AlphaMissense source object is not verified",
            {"source_id": plan.source_id, "upload_status": record.upload_status},
        )
    if record.approval_status != "approved":
        raise SourceAssetMaterializationError(
            "materialization_not_approved",
            "AlphaMissense source object is not approved for backend use",
            {"source_id": plan.source_id, "approval_status": record.approval_status},
        )
    if record.materialization_status != "ready":
        raise SourceAssetMaterializationError(
            "materialization_not_ready",
            "AlphaMissense materialization is not ready",
            {
                "source_id": plan.source_id,
                "materialization_status": record.materialization_status,
            },
        )
    if record.fail_closed_reason is not None:
        raise SourceAssetMaterializationError(
            "materialization_fail_closed",
            "AlphaMissense materialization has a fail-closed reason",
            {"source_id": plan.source_id},
        )
    if record.byte_size is None or record.byte_size <= 0:
        raise SourceAssetMaterializationError(
            "materialization_size_missing",
            "ready AlphaMissense materialization is missing byte_size",
            {"source_id": plan.source_id},
        )
    if record.byte_size != plan.path.stat().st_size:
        raise SourceAssetMaterializationError(
            "materialization_size_mismatch",
            "AlphaMissense materialization size does not match local cache bytes",
            {"source_id": plan.source_id},
        )
    if record.verified_at is None:
        raise SourceAssetMaterializationError(
            "materialization_verified_at_missing",
            "ready AlphaMissense materialization is missing verified_at",
            {"source_id": plan.source_id},
        )
    if record.checksum_algorithm is None or record.checksum_value is None:
        raise SourceAssetMaterializationError(
            "materialization_checksum_missing",
            "ready AlphaMissense materialization is missing checksum metadata",
            {"source_id": plan.source_id},
        )
    if (record.checksum_algorithm or "").lower() != "md5":
        raise SourceAssetMaterializationError(
            "materialization_checksum_algorithm_mismatch",
            "AlphaMissense materialization checksum must use md5",
            {"source_id": plan.source_id},
        )
    if plan.expected_md5 and (record.checksum_value or "").lower() != plan.expected_md5:
        raise SourceAssetMaterializationError(
            "materialization_checksum_mismatch",
            "AlphaMissense materialization checksum does not match registry metadata",
            {"source_id": plan.source_id},
        )
    materialized_path = _resolve_materialization_path(settings, record.local_cache_path)
    if materialized_path.resolve() != plan.path.resolve():
        raise SourceAssetMaterializationError(
            "materialization_path_mismatch",
            "AlphaMissense materialization path does not match configured runtime path",
            {"source_id": plan.source_id},
        )
    return record


def _inspection(
    plan: PredictorRuntimePlan,
    status: PredictorRuntimeStatus,
    message: str,
    *,
    actual_size_bytes: int | None = None,
    actual_md5: str | None = None,
    materialization_status: str | None = None,
) -> PredictorRuntimeInspection:
    return PredictorRuntimeInspection(
        source_id=plan.source_id,
        asset_role=plan.asset_role,
        mode=plan.mode,
        status=status,
        path=plan.path,
        index_path=plan.index_path,
        manifest_path=plan.manifest_path,
        actual_size_bytes=actual_size_bytes,
        expected_md5=plan.expected_md5,
        actual_md5=actual_md5.lower() if actual_md5 else None,
        object_uri=plan.object_uri,
        reader_requires_local_path=plan.reader_requires_local_path,
        bucket_file_size_limit=plan.bucket_file_size_limit,
        materialization_status=materialization_status,
        message=message,
    )


def _resolve_backend_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _expected_md5(current_local_md5: str | None, checksum_plan: str | None) -> str | None:
    if current_local_md5:
        return current_local_md5.lower()
    if not checksum_plan:
        return None
    match = re.search(r"\b[0-9a-fA-F]{32}\b", checksum_plan)
    return match.group(0).lower() if match is not None else None


def _supported_mode_values() -> set[str]:
    return {mode.value for mode in RuntimeAssetMode}


_MATERIALIZATION_ERROR_STATUS = {
    "materialization_metadata_missing": PredictorRuntimeStatus.MATERIALIZATION_METADATA_MISSING,
    "materialization_public_access_blocked": (
        PredictorRuntimeStatus.MATERIALIZATION_PUBLIC_ACCESS_BLOCKED
    ),
    "materialization_upload_not_verified": (
        PredictorRuntimeStatus.MATERIALIZATION_UPLOAD_NOT_VERIFIED
    ),
    "materialization_not_approved": PredictorRuntimeStatus.MATERIALIZATION_NOT_APPROVED,
    "materialization_not_ready": PredictorRuntimeStatus.MATERIALIZATION_NOT_READY,
    "materialization_fail_closed": PredictorRuntimeStatus.MATERIALIZATION_FAIL_CLOSED,
    "materialization_verified_at_missing": (
        PredictorRuntimeStatus.MATERIALIZATION_VERIFIED_AT_MISSING
    ),
    "materialization_size_mismatch": PredictorRuntimeStatus.MATERIALIZATION_SIZE_MISMATCH,
    "materialization_checksum_missing": PredictorRuntimeStatus.MATERIALIZATION_CHECKSUM_MISSING,
    "materialization_checksum_mismatch": PredictorRuntimeStatus.MATERIALIZATION_CHECKSUM_MISMATCH,
    "materialization_path_mismatch": PredictorRuntimeStatus.MATERIALIZATION_PATH_MISMATCH,
}
