from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Protocol

from app.core.config import Settings
from app.data_sources.local_inventory import LOCAL_HG38_2BIT_SOURCE_ID, compute_md5
from app.data_sources.registry import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry


class RuntimeAssetMode(str, Enum):
    LOCAL_PATH = "local_path"
    OBJECT_STORAGE_LOCAL_CACHE = "object_storage_local_cache"
    MOUNTED_VOLUME = "mounted_volume"


class RuntimeAssetStatus(str, Enum):
    READY = "ready"
    MISSING = "missing"
    NOT_FILE = "not_file"
    SIZE_MISMATCH = "size_mismatch"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    CONFIG_ERROR = "config_error"


class SourceAssetMaterializationError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


@dataclass(frozen=True)
class RuntimeAssetPlan:
    source_id: str
    mode: str
    path: Path
    source_url: str | None
    object_uri: str | None
    expected_size_bytes: int
    expected_md5: str
    reader_requires_local_path: bool
    supported_modes: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeAssetInspection:
    source_id: str
    mode: str
    status: RuntimeAssetStatus
    path: Path
    expected_size_bytes: int
    actual_size_bytes: int | None
    expected_md5: str
    actual_md5: str | None
    object_uri: str | None
    reader_requires_local_path: bool
    message: str

    @property
    def ready(self) -> bool:
        return self.status is RuntimeAssetStatus.READY


@dataclass(frozen=True)
class SourceAssetMaterializationRecord:
    source_id: str
    asset_role: str
    bucket_id: str
    object_path: str
    upload_status: str
    approval_status: str
    public_access_allowed: bool
    frontend_direct_access_allowed: bool
    environment: str
    backend_runtime: str
    local_cache_path: str
    materialization_status: str
    byte_size: int | None
    checksum_algorithm: str | None
    checksum_value: str | None
    verified_at: datetime | None
    fail_closed_reason: str | None
    metadata: dict[str, object]
    warnings: list[str]


@dataclass(frozen=True)
class ResolvedRuntimeAsset:
    source_id: str
    asset_role: str
    path: Path
    bucket_id: str
    object_path: str
    environment: str
    backend_runtime: str
    byte_size: int
    checksum_algorithm: str
    checksum_value: str
    verified_at: datetime
    inspection: RuntimeAssetInspection


class SourceAssetMaterializationStore(Protocol):
    def get_source_asset_materialization(
        self,
        *,
        source_id: str,
        asset_role: str,
        bucket_id: str | None = None,
        object_path: str | None = None,
        environment: str | None = None,
        local_cache_path: str | None = None,
    ) -> SourceAssetMaterializationRecord | None: ...


HG38_MATERIALIZATION_FAILURE_BOUNDARIES: dict[str, str] = {
    "metadata_and_local_cache_resolution": "fail_closed",
    "lookup_sequence_context_runtime": "fail_open",
    "health_and_preflight_probe": "sanitized_status_no_exception",
}


def build_hg38_runtime_asset_plan(
    settings: Settings,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
) -> RuntimeAssetPlan:
    record = registry.get(LOCAL_HG38_2BIT_SOURCE_ID)
    expected_size = record.actual_size_bytes_local
    expected_md5 = record.current_local_md5
    if expected_size is None or expected_size <= 0:
        raise ValueError(f"{record.source_id}: actual_size_bytes_local is required")
    if not expected_md5:
        raise ValueError(f"{record.source_id}: current_local_md5 is required")

    return RuntimeAssetPlan(
        source_id=record.source_id,
        mode=settings.hg38_2bit_runtime_asset_mode.strip().lower(),
        path=_resolve_backend_path(settings, settings.hg38_2bit_runtime_asset_path),
        source_url=record.source_url,
        object_uri=settings.hg38_2bit_runtime_asset_object_uri,
        expected_size_bytes=expected_size,
        expected_md5=expected_md5.lower(),
        reader_requires_local_path=record.reader_requires_local_path,
        supported_modes=record.runtime_delivery_modes,
    )


def inspect_hg38_runtime_asset(
    settings: Settings,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    *,
    verify_checksum: bool = False,
) -> RuntimeAssetInspection:
    plan = build_hg38_runtime_asset_plan(settings, registry=registry)

    if plan.mode not in _supported_mode_values():
        return _inspection(
            plan,
            RuntimeAssetStatus.CONFIG_ERROR,
            f"unsupported hg38.2bit runtime asset mode: {plan.mode}",
        )
    if plan.mode not in set(plan.supported_modes):
        return _inspection(
            plan,
            RuntimeAssetStatus.CONFIG_ERROR,
            f"registry does not support hg38.2bit runtime asset mode: {plan.mode}",
        )
    if plan.mode == RuntimeAssetMode.OBJECT_STORAGE_LOCAL_CACHE.value and not plan.object_uri:
        return _inspection(
            plan,
            RuntimeAssetStatus.CONFIG_ERROR,
            "object_storage_local_cache mode requires an object URI for the source asset",
        )
    if plan.reader_requires_local_path and not plan.path:
        return _inspection(
            plan,
            RuntimeAssetStatus.CONFIG_ERROR,
            "hg38.2bit reader requires a configured local filesystem path",
        )

    if not plan.path.exists():
        return _inspection(plan, RuntimeAssetStatus.MISSING, "hg38.2bit asset is missing")
    if not plan.path.is_file():
        return _inspection(
            plan,
            RuntimeAssetStatus.NOT_FILE,
            "hg38.2bit runtime asset path is not a file",
        )

    actual_size = plan.path.stat().st_size
    if actual_size != plan.expected_size_bytes:
        return _inspection(
            plan,
            RuntimeAssetStatus.SIZE_MISMATCH,
            "hg38.2bit runtime asset size does not match registry metadata",
            actual_size_bytes=actual_size,
        )

    actual_md5 = compute_md5(plan.path) if verify_checksum else None
    if actual_md5 is not None and actual_md5.lower() != plan.expected_md5:
        return _inspection(
            plan,
            RuntimeAssetStatus.CHECKSUM_MISMATCH,
            "hg38.2bit runtime asset checksum does not match registry metadata",
            actual_size_bytes=actual_size,
            actual_md5=actual_md5,
        )

    return _inspection(
        plan,
        RuntimeAssetStatus.READY,
        "hg38.2bit runtime asset is ready",
        actual_size_bytes=actual_size,
        actual_md5=actual_md5,
    )


def resolve_hg38_materialized_runtime_asset(
    settings: Settings,
    materialization_store: SourceAssetMaterializationStore | None,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    *,
    verify_checksum: bool = False,
    environment: str | None = None,
) -> ResolvedRuntimeAsset:
    """Resolve a verified private Storage materialization to a local reader path.

    This is deliberately a metadata/local-cache reader only. It does not download
    from Storage, create signed URLs, or make browser-readable paths.
    """

    plan = build_hg38_runtime_asset_plan(settings, registry=registry)
    if materialization_store is None:
        raise SourceAssetMaterializationError(
            "materialization_store_unavailable",
            "source asset materialization store is not configured",
            {"source_id": plan.source_id},
        )

    bucket_id, object_path = _parse_supabase_object_uri(plan.object_uri)
    try:
        record = materialization_store.get_source_asset_materialization(
            source_id=plan.source_id,
            asset_role="reference_genome_2bit",
            bucket_id=bucket_id,
            object_path=object_path,
            environment=environment,
            local_cache_path=str(plan.path),
        )
    except SourceAssetMaterializationError:
        raise
    except Exception as exc:
        raise SourceAssetMaterializationError(
            "materialization_metadata_unavailable",
            "source asset materialization metadata is unavailable",
            {"source_id": plan.source_id, "asset_role": "reference_genome_2bit"},
        ) from exc
    if record is None:
        raise SourceAssetMaterializationError(
            "materialization_metadata_missing",
            "no source asset materialization metadata is available",
            {"source_id": plan.source_id, "asset_role": "reference_genome_2bit"},
        )
    _validate_hg38_materialization_record(record, plan)

    materialized_path = _resolve_materialization_path(settings, record.local_cache_path)
    if materialized_path.resolve() != plan.path.resolve():
        raise SourceAssetMaterializationError(
            "materialization_path_mismatch",
            "source asset materialization path does not match configured runtime path",
            {"source_id": plan.source_id},
        )

    inspection = inspect_hg38_runtime_asset(
        settings,
        registry=registry,
        verify_checksum=verify_checksum,
    )
    if not inspection.ready:
        raise SourceAssetMaterializationError(
            f"runtime_asset_{inspection.status.value}",
            inspection.message,
            {"source_id": plan.source_id, "status": inspection.status.value},
        )

    if record.verified_at is None:
        raise SourceAssetMaterializationError(
            "materialization_verified_at_missing",
            "ready source asset materialization is missing verified_at",
            {"source_id": plan.source_id},
        )
    if record.byte_size is None:
        raise SourceAssetMaterializationError(
            "materialization_size_missing",
            "ready source asset materialization is missing byte_size",
            {"source_id": plan.source_id},
        )
    if record.checksum_algorithm is None or record.checksum_value is None:
        raise SourceAssetMaterializationError(
            "materialization_checksum_missing",
            "ready source asset materialization is missing checksum metadata",
            {"source_id": plan.source_id},
        )

    return ResolvedRuntimeAsset(
        source_id=record.source_id,
        asset_role=record.asset_role,
        path=materialized_path,
        bucket_id=record.bucket_id,
        object_path=record.object_path,
        environment=record.environment,
        backend_runtime=record.backend_runtime,
        byte_size=record.byte_size,
        checksum_algorithm=record.checksum_algorithm,
        checksum_value=record.checksum_value.lower(),
        verified_at=record.verified_at,
        inspection=inspection,
    )


def probe_hg38_materialization_status(
    settings: Settings,
    materialization_store: SourceAssetMaterializationStore | None,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    *,
    verify_checksum: bool = False,
    environment: str | None = None,
) -> dict[str, object]:
    """Return a sanitized materialization readiness probe for health/preflight.

    The underlying resolver stays fail-closed because direct local-source reads
    must not proceed with uncertain metadata. This probe and the sequence-context
    caller are non-throwing so operational checks and lookups do not 500 when a
    private Storage materialization is absent or misconfigured.
    """

    metadata: dict[str, object] = {
        "enabled": materialization_store is not None,
        "probe_performed": materialization_store is not None,
        "ready": False,
        "status": "materialization_store_unavailable",
        "failure_boundaries": dict(HG38_MATERIALIZATION_FAILURE_BOUNDARIES),
    }
    if materialization_store is None:
        return metadata

    try:
        resolved = resolve_hg38_materialized_runtime_asset(
            settings,
            materialization_store,
            registry=registry,
            verify_checksum=verify_checksum,
            environment=environment,
        )
    except SourceAssetMaterializationError as exc:
        metadata.update({"ready": False, "status": exc.code})
    except Exception:
        metadata.update({"ready": False, "status": "materialization_probe_failed"})
    else:
        metadata.update(
            {
                "ready": True,
                "status": "ready",
                "environment": resolved.environment,
                "backend_runtime": resolved.backend_runtime,
                "byte_size": resolved.byte_size,
                "checksum_algorithm": resolved.checksum_algorithm,
                "public_access_allowed": False,
                "frontend_direct_access_allowed": False,
            }
        )
    return metadata


def _inspection(
    plan: RuntimeAssetPlan,
    status: RuntimeAssetStatus,
    message: str,
    *,
    actual_size_bytes: int | None = None,
    actual_md5: str | None = None,
) -> RuntimeAssetInspection:
    return RuntimeAssetInspection(
        source_id=plan.source_id,
        mode=plan.mode,
        status=status,
        path=plan.path,
        expected_size_bytes=plan.expected_size_bytes,
        actual_size_bytes=actual_size_bytes,
        expected_md5=plan.expected_md5,
        actual_md5=actual_md5.lower() if actual_md5 else None,
        object_uri=plan.object_uri,
        reader_requires_local_path=plan.reader_requires_local_path,
        message=message,
    )


def _resolve_backend_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _resolve_materialization_path(settings: Settings, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    parts = tuple(path.parts)
    if len(parts) >= 2 and parts[:2] == ("app", "backend"):
        return settings.backend_root / Path(*parts[2:])
    return settings.backend_root / path


def _parse_supabase_object_uri(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    prefix = "supabase://"
    if not value.startswith(prefix):
        raise SourceAssetMaterializationError(
            "invalid_source_asset_object_uri",
            "source asset object URI must use supabase://bucket/object-path",
        )
    remainder = value[len(prefix) :]
    bucket_id, separator, object_path = remainder.partition("/")
    if not bucket_id or not separator or not object_path:
        raise SourceAssetMaterializationError(
            "invalid_source_asset_object_uri",
            "source asset object URI must include bucket and object path",
        )
    return bucket_id, object_path


def _validate_hg38_materialization_record(
    record: SourceAssetMaterializationRecord,
    plan: RuntimeAssetPlan,
) -> None:
    if record.source_id != plan.source_id or record.asset_role != "reference_genome_2bit":
        raise SourceAssetMaterializationError(
            "materialization_source_mismatch",
            "source asset materialization metadata is for the wrong source asset",
            {"source_id": plan.source_id},
        )
    if record.public_access_allowed or record.frontend_direct_access_allowed:
        raise SourceAssetMaterializationError(
            "materialization_public_access_blocked",
            "source asset materialization metadata allows public or frontend access",
            {"source_id": plan.source_id},
        )
    if record.upload_status != "verified":
        raise SourceAssetMaterializationError(
            "materialization_upload_not_verified",
            "source asset object is not verified",
            {"source_id": plan.source_id, "upload_status": record.upload_status},
        )
    if record.approval_status != "approved":
        raise SourceAssetMaterializationError(
            "materialization_not_approved",
            "source asset object is not approved for backend use",
            {"source_id": plan.source_id, "approval_status": record.approval_status},
        )
    if record.materialization_status != "ready":
        raise SourceAssetMaterializationError(
            "materialization_not_ready",
            "source asset materialization is not ready",
            {
                "source_id": plan.source_id,
                "materialization_status": record.materialization_status,
                "fail_closed_reason": record.fail_closed_reason,
            },
        )
    if record.fail_closed_reason is not None:
        raise SourceAssetMaterializationError(
            "materialization_fail_closed",
            "source asset materialization has a fail-closed reason",
            {"source_id": plan.source_id},
        )
    if record.byte_size != plan.expected_size_bytes:
        raise SourceAssetMaterializationError(
            "materialization_size_mismatch",
            "source asset materialization size does not match registry metadata",
            {"source_id": plan.source_id},
        )
    if (record.checksum_algorithm or "").lower() != "md5":
        raise SourceAssetMaterializationError(
            "materialization_checksum_algorithm_mismatch",
            "source asset materialization checksum algorithm is not md5",
            {"source_id": plan.source_id},
        )
    if (record.checksum_value or "").lower() != plan.expected_md5:
        raise SourceAssetMaterializationError(
            "materialization_checksum_mismatch",
            "source asset materialization checksum does not match registry metadata",
            {"source_id": plan.source_id},
        )


def _supported_mode_values() -> set[str]:
    return {mode.value for mode in RuntimeAssetMode}
