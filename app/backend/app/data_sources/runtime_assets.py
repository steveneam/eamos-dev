from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

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


def _supported_mode_values() -> set[str]:
    return {mode.value for mode in RuntimeAssetMode}
