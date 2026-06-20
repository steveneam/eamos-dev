from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from enum import Enum
import json
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
from app.services.esm1b_assembly import (
    ESM1B_LICENSE_GATE,
    ESM1B_REGENERATION_REQUIRED_GATE,
)

ALPHAMISSENSE_SOURCE_ID = "google_deepmind_alphamissense_hg38"
ALPHAMISSENSE_ASSET_ROLE = "predictor_tabix_tsv"
ESM1B_SOURCE_ID = "esm1b_hg38_assembled_scores"
ESM1B_ASSET_ROLE = "predictor_tabix_tsv"
CI_SPLICEAI_SOURCE_ID = "ci_spliceai_model"
CI_SPLICEAI_MODEL_ASSET_ROLE = "keras_model"
CI_SPLICEAI_REFERENCE_ASSET_ROLE = "reference_bundle"
CI_SPLICEAI_SCORE_CACHE_ASSET_ROLE = "score_cache"
CI_SPLICEAI_LAUNCH_GATE = "ci_spliceai_launch_filter_metadata"
CAPICE_SOURCE_ID = "capice_model"
CAPICE_MODEL_ASSET_ROLE = "xgboost_model"
CAPICE_FEATURE_CACHE_SOURCE_ID = "illumina_spliceai_precomputed_hg38"
CAPICE_FEATURE_CACHE_ASSET_ROLE = "spliceai_feature_cache"
CAPICE_LAUNCH_GATE = "capice_launch_filter_metadata"
REVEL_SOURCE_ID = "zenodo_revel_scores"
REVEL_SCORE_CACHE_ASSET_ROLE = "predictor_score_cache"
REVEL_LAUNCH_GATE = "revel_launch_filter_metadata"
PRIMATEAI3D_SOURCE_ID = "illumina_primateai3d_scores"
PRIMATEAI3D_SCORE_CACHE_ASSET_ROLE = "predictor_score_cache"
PRIMATEAI3D_LAUNCH_GATE = "primateai3d_launch_filter_metadata"


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
    display_name: str
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
    launch_gate: str | None = None

    @property
    def ready(self) -> bool:
        return self.status is PredictorRuntimeStatus.READY


@dataclass(frozen=True)
class AdminPredictorComponentInspection:
    source_id: str
    asset_role: str
    label: str
    status: str
    ready: bool
    actual_size_bytes: int | None
    reader_requires_local_path: bool = True
    manifest_status: str = "not_checked"
    manifest_expected_size_bytes: int | None = None
    manifest_checksums_present: bool = False
    launch_gate: str | None = None

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "asset_role": self.asset_role,
            "label": self.label,
            "status": self.status,
            "ready": self.ready,
            "actual_size_bytes": self.actual_size_bytes,
            "reader_requires_local_path": self.reader_requires_local_path,
            "manifest_status": self.manifest_status,
            "manifest_expected_size_bytes": self.manifest_expected_size_bytes,
            "manifest_checksums_present": self.manifest_checksums_present,
            "launch_gate": self.launch_gate,
        }


@dataclass(frozen=True)
class AdminPredictorRuntimeInspection:
    source_id: str
    status: str
    available: bool
    launch_gate: str
    status_notes: tuple[str, ...]
    components: tuple[AdminPredictorComponentInspection, ...]
    runtime_wired: bool = True
    public_serialization_allowed: bool = True

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "available": self.available,
            "runtime_wired": self.runtime_wired,
            "public_serialization_allowed": self.public_serialization_allowed,
            "launch_gate": self.launch_gate,
            "status_notes": list(self.status_notes),
            "components": [component.to_sanitized_dict() for component in self.components],
        }


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
        display_name=record.display_name,
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


def build_esm1b_runtime_plan(
    settings: Settings,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    *,
    bucket_file_size_limit: int = DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
) -> PredictorRuntimePlan:
    record = registry.get(ESM1B_SOURCE_ID)
    path = _resolve_backend_path(settings, settings.esm1b_hg38_runtime_asset_path)
    return PredictorRuntimePlan(
        source_id=record.source_id,
        asset_role=ESM1B_ASSET_ROLE,
        display_name=record.display_name,
        mode=settings.esm1b_hg38_runtime_asset_mode.strip().lower(),
        path=path,
        index_path=Path(f"{path}.tbi"),
        manifest_path=path.with_suffix(path.suffix + ".manifest.json"),
        source_url=record.source_url,
        object_uri=settings.esm1b_hg38_runtime_asset_object_uri,
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


def inspect_esm1b_runtime_asset(
    settings: Settings,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    *,
    verify_checksum: bool = False,
    require_manifest: bool = True,
    materialization_store: SourceAssetMaterializationStore | None = None,
    environment: str | None = None,
    bucket_file_size_limit: int = DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
) -> PredictorRuntimeInspection:
    plan = build_esm1b_runtime_plan(
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
        return replace(base, launch_gate=ESM1B_REGENERATION_REQUIRED_GATE)
    base = replace(base, launch_gate=_esm1b_launch_gate_from_manifest(plan.manifest_path))
    if materialization_store is None:
        if plan.mode == RuntimeAssetMode.OBJECT_STORAGE_LOCAL_CACHE.value:
            return _inspection(
                plan,
                PredictorRuntimeStatus.MATERIALIZATION_STORE_UNAVAILABLE,
                f"{plan.display_name} object-storage mode requires materialization metadata",
                actual_size_bytes=base.actual_size_bytes,
                actual_md5=base.actual_md5,
                materialization_status="metadata_store_unavailable",
                launch_gate=base.launch_gate,
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
            launch_gate=base.launch_gate,
        )

    return _inspection(
        plan,
        PredictorRuntimeStatus.READY,
        f"{plan.display_name} runtime asset is ready",
        actual_size_bytes=base.actual_size_bytes,
        actual_md5=base.actual_md5,
        materialization_status="ready",
        launch_gate=base.launch_gate,
    )


def inspect_ci_spliceai_runtime_assets(settings: Settings) -> AdminPredictorRuntimeInspection:
    """Inspect CI-SpliceAI admin-lane artifacts without exposing local paths."""

    model = _inspect_admin_component(
        artifact_id="ci_spliceai",
        component_id="model",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_keras_model",
        asset_role=CI_SPLICEAI_MODEL_ASSET_ROLE,
        label="CI-SpliceAI model",
        path=_resolve_backend_path(settings, settings.ci_spliceai_model_path),
        missing_status="model_artifact_missing",
        path_not_file_status="model_artifact_path_not_file",
        manifest_status_prefix="model",
        expected_launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    )
    reference = _inspect_admin_component(
        artifact_id="ci_spliceai",
        component_id="reference_bundle",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_reference_bundle",
        asset_role=CI_SPLICEAI_REFERENCE_ASSET_ROLE,
        label="CI-SpliceAI reference bundle",
        path=_resolve_backend_path(settings, settings.ci_spliceai_reference_path),
        missing_status="reference_artifact_missing",
        path_not_file_status="reference_artifact_path_not_file",
        manifest_status_prefix="reference",
        expected_launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    )
    score_cache = _inspect_admin_component(
        artifact_id="ci_spliceai",
        component_id="score_cache",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_hg38_score_cache_vcf_gz",
        asset_role=CI_SPLICEAI_SCORE_CACHE_ASSET_ROLE,
        label="CI-SpliceAI score cache",
        path=_resolve_backend_path(settings, settings.ci_spliceai_score_cache_path),
        missing_status="score_cache_missing",
        path_not_file_status="score_cache_path_not_file",
        indexed=True,
        missing_index_status="score_cache_index_missing",
        index_not_file_status="score_cache_index_path_not_file",
        manifest_status_prefix="score_cache",
        expected_launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    )
    components = (model, reference, score_cache)
    status = _ci_spliceai_status(model, reference, score_cache)
    return AdminPredictorRuntimeInspection(
        source_id=CI_SPLICEAI_SOURCE_ID,
        status=status,
        available=status == "ready",
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
        status_notes=_ci_spliceai_status_notes(components),
        components=components,
    )


def inspect_capice_runtime_assets(settings: Settings) -> AdminPredictorRuntimeInspection:
    """Inspect CAPICE admin-lane artifacts without exposing local paths."""

    model = _inspect_admin_component(
        artifact_id="capice",
        component_id="model",
        source_id=CAPICE_SOURCE_ID,
        asset_id="capice_xgboost_model",
        asset_role=CAPICE_MODEL_ASSET_ROLE,
        label="CAPICE model",
        path=_resolve_backend_path(settings, settings.capice_model_path),
        missing_status="model_artifact_missing",
        path_not_file_status="model_artifact_path_not_file",
        manifest_status_prefix="model",
        expected_launch_gate=CAPICE_LAUNCH_GATE,
    )
    feature_cache = _inspect_admin_component(
        artifact_id="capice",
        component_id="feature_cache",
        source_id=CAPICE_FEATURE_CACHE_SOURCE_ID,
        asset_id="capice_hg38_feature_cache_tsv_gz",
        asset_role=CAPICE_FEATURE_CACHE_ASSET_ROLE,
        label="CAPICE SpliceAI-derived feature cache",
        path=_resolve_backend_path(settings, settings.capice_feature_cache_path),
        missing_status="feature_cache_missing",
        path_not_file_status="feature_cache_path_not_file",
        indexed=True,
        missing_index_status="feature_cache_index_missing",
        index_not_file_status="feature_cache_index_path_not_file",
        manifest_status_prefix="feature_cache",
        expected_launch_gate=CAPICE_LAUNCH_GATE,
    )
    components = (model, feature_cache)
    status = _capice_status(model, feature_cache)
    return AdminPredictorRuntimeInspection(
        source_id=CAPICE_SOURCE_ID,
        status=status,
        available=status == "ready",
        launch_gate=CAPICE_LAUNCH_GATE,
        status_notes=_capice_status_notes(components),
        components=components,
    )


def inspect_revel_runtime_assets(settings: Settings) -> AdminPredictorRuntimeInspection:
    """Inspect the REVEL coordinate-keyed score cache without exposing paths."""

    score_cache = _inspect_admin_component(
        artifact_id="revel",
        component_id="score_cache",
        source_id=REVEL_SOURCE_ID,
        asset_id="revel_hg38_score_cache_tsv_gz",
        asset_role=REVEL_SCORE_CACHE_ASSET_ROLE,
        label="REVEL score cache",
        path=_resolve_backend_path(settings, settings.revel_score_cache_path),
        missing_status="score_cache_missing",
        path_not_file_status="score_cache_path_not_file",
        indexed=True,
        missing_index_status="score_cache_index_missing",
        index_not_file_status="score_cache_index_path_not_file",
        manifest_status_prefix="score_cache",
        expected_launch_gate=REVEL_LAUNCH_GATE,
    )
    return _single_cache_admin_inspection(
        source_id=REVEL_SOURCE_ID,
        launch_gate=REVEL_LAUNCH_GATE,
        component=score_cache,
    )


def inspect_primateai3d_runtime_assets(settings: Settings) -> AdminPredictorRuntimeInspection:
    """Inspect the PrimateAI-3D coordinate-keyed score cache without exposing paths."""

    score_cache = _inspect_admin_component(
        artifact_id="primateai3d",
        component_id="score_cache",
        source_id=PRIMATEAI3D_SOURCE_ID,
        asset_id="primateai3d_hg38_score_cache_tsv_gz",
        asset_role=PRIMATEAI3D_SCORE_CACHE_ASSET_ROLE,
        label="PrimateAI-3D score cache",
        path=_resolve_backend_path(settings, settings.primateai3d_score_cache_path),
        missing_status="score_cache_missing",
        path_not_file_status="score_cache_path_not_file",
        indexed=True,
        missing_index_status="score_cache_index_missing",
        index_not_file_status="score_cache_index_path_not_file",
        manifest_status_prefix="score_cache",
        expected_launch_gate=PRIMATEAI3D_LAUNCH_GATE,
    )
    return _single_cache_admin_inspection(
        source_id=PRIMATEAI3D_SOURCE_ID,
        launch_gate=PRIMATEAI3D_LAUNCH_GATE,
        component=score_cache,
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
            f"unsupported {plan.display_name} runtime asset mode: {plan.mode}",
        )
    if plan.mode not in set(plan.supported_modes):
        return _inspection(
            plan,
            PredictorRuntimeStatus.CONFIG_ERROR,
            f"registry does not support {plan.display_name} runtime asset mode: {plan.mode}",
        )
    if plan.mode == RuntimeAssetMode.OBJECT_STORAGE_LOCAL_CACHE.value and not plan.object_uri:
        return _inspection(
            plan,
            PredictorRuntimeStatus.CONFIG_ERROR,
            f"object_storage_local_cache mode requires an object URI for {plan.display_name}",
        )
    if plan.reader_requires_local_path and not plan.path:
        return _inspection(
            plan,
            PredictorRuntimeStatus.CONFIG_ERROR,
            f"{plan.display_name} reader requires a configured local filesystem path",
        )

    if not plan.path.exists():
        return _inspection(
            plan,
            PredictorRuntimeStatus.MISSING_SOURCE_FILE,
            f"{plan.display_name} source TSV is missing",
        )
    if not plan.path.is_file():
        return _inspection(
            plan,
            PredictorRuntimeStatus.SOURCE_PATH_NOT_FILE,
            f"{plan.display_name} runtime asset path is not a file",
        )
    actual_size = plan.path.stat().st_size

    if not plan.index_path.exists():
        return _inspection(
            plan,
            PredictorRuntimeStatus.MISSING_INDEX,
            f"{plan.display_name} tabix index is missing",
            actual_size_bytes=actual_size,
        )
    if not plan.index_path.is_file():
        return _inspection(
            plan,
            PredictorRuntimeStatus.INDEX_PATH_NOT_FILE,
            f"{plan.display_name} tabix index path is not a file",
            actual_size_bytes=actual_size,
        )

    if require_manifest and not plan.manifest_path.is_file():
        return _inspection(
            plan,
            PredictorRuntimeStatus.MISSING_MANIFEST,
            f"{plan.display_name} checksum manifest is missing",
            actual_size_bytes=actual_size,
        )

    actual_md5 = compute_md5(plan.path) if verify_checksum else None
    if actual_md5 is not None and plan.expected_md5 and actual_md5.lower() != plan.expected_md5:
        return _inspection(
            plan,
            PredictorRuntimeStatus.CHECKSUM_MISMATCH,
            f"{plan.display_name} source TSV checksum does not match registry metadata",
            actual_size_bytes=actual_size,
            actual_md5=actual_md5,
        )

    return _inspection(
        plan,
        PredictorRuntimeStatus.READY,
        f"{plan.display_name} runtime asset is ready",
        actual_size_bytes=actual_size,
        actual_md5=actual_md5,
    )


def _inspect_admin_component(
    *,
    artifact_id: str,
    component_id: str,
    source_id: str,
    asset_id: str,
    asset_role: str,
    label: str,
    path: Path,
    missing_status: str,
    path_not_file_status: str,
    manifest_status_prefix: str,
    expected_launch_gate: str,
    indexed: bool = False,
    missing_index_status: str | None = None,
    index_not_file_status: str | None = None,
) -> AdminPredictorComponentInspection:
    if not path.exists():
        return AdminPredictorComponentInspection(
            source_id=source_id,
            asset_role=asset_role,
            label=label,
            status=missing_status,
            ready=False,
            actual_size_bytes=None,
        )
    if not path.is_file():
        return AdminPredictorComponentInspection(
            source_id=source_id,
            asset_role=asset_role,
            label=label,
            status=path_not_file_status,
            ready=False,
            actual_size_bytes=None,
        )
    actual_size = path.stat().st_size
    if indexed:
        index_path = Path(f"{path}.tbi")
        if not index_path.exists():
            return AdminPredictorComponentInspection(
                source_id=source_id,
                asset_role=asset_role,
                label=label,
                status=missing_index_status or "index_missing",
                ready=False,
                actual_size_bytes=actual_size,
            )
        if not index_path.is_file():
            return AdminPredictorComponentInspection(
                source_id=source_id,
                asset_role=asset_role,
                label=label,
                status=index_not_file_status or "index_path_not_file",
                ready=False,
                actual_size_bytes=actual_size,
            )
    manifest = _inspect_admin_component_manifest(
        artifact_id=artifact_id,
        component_id=component_id,
        source_id=source_id,
        asset_id=asset_id,
        asset_role=asset_role,
        path=path,
        actual_size=actual_size,
        expected_launch_gate=expected_launch_gate,
    )
    if manifest["status"] != "ready":
        return AdminPredictorComponentInspection(
            source_id=source_id,
            asset_role=asset_role,
            label=label,
            status=f"{manifest_status_prefix}_{manifest['status']}",
            ready=False,
            actual_size_bytes=actual_size,
            manifest_status=str(manifest["status"]),
            manifest_expected_size_bytes=manifest["expected_size"],
            manifest_checksums_present=bool(manifest["checksums_present"]),
            launch_gate=manifest["launch_gate"],
        )
    return AdminPredictorComponentInspection(
        source_id=source_id,
        asset_role=asset_role,
        label=label,
        status="ready",
        ready=True,
        actual_size_bytes=actual_size,
        manifest_status="ready",
        manifest_expected_size_bytes=manifest["expected_size"],
        manifest_checksums_present=bool(manifest["checksums_present"]),
        launch_gate=manifest["launch_gate"],
    )


def _inspect_admin_component_manifest(
    *,
    artifact_id: str,
    component_id: str,
    source_id: str,
    asset_id: str,
    asset_role: str,
    path: Path,
    actual_size: int,
    expected_launch_gate: str,
) -> dict[str, object]:
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    if not manifest_path.is_file():
        return _admin_manifest_result("manifest_missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _admin_manifest_result("manifest_invalid_json")
    if not isinstance(manifest, dict):
        return _admin_manifest_result("manifest_invalid_json")

    if manifest.get("artifact_id") not in (None, artifact_id):
        return _admin_manifest_result("manifest_artifact_mismatch")
    if manifest.get("component_id") not in (None, component_id):
        return _admin_manifest_result("manifest_component_mismatch")
    if manifest.get("source_id") not in (None, source_id):
        return _admin_manifest_result("manifest_source_mismatch")
    if manifest.get("asset_id") not in (None, asset_id):
        return _admin_manifest_result("manifest_asset_mismatch")
    if manifest.get("role") not in (None, asset_role):
        return _admin_manifest_result("manifest_role_mismatch")

    expected_size = manifest.get("byte_size")
    if not isinstance(expected_size, int) or expected_size <= 0:
        return _admin_manifest_result("manifest_size_missing")
    if expected_size != actual_size:
        return _admin_manifest_result("manifest_size_mismatch", expected_size=expected_size)

    checksums = manifest.get("checksums") if isinstance(manifest.get("checksums"), dict) else {}
    md5_value = _optional_text(manifest.get("md5") or checksums.get("md5"))
    sha256_value = _optional_text(manifest.get("sha256") or checksums.get("sha256"))
    checksums_present = bool(_looks_like_md5(md5_value) or _looks_like_sha256(sha256_value))
    if not checksums_present:
        return _admin_manifest_result(
            "manifest_checksum_missing",
            expected_size=expected_size,
        )

    launch_gate = manifest.get("launch_gate")
    if not isinstance(launch_gate, str) or not launch_gate.strip():
        return _admin_manifest_result(
            "manifest_launch_gate_missing",
            expected_size=expected_size,
            checksums_present=checksums_present,
        )
    launch_gate = launch_gate.strip()
    if launch_gate != expected_launch_gate:
        return _admin_manifest_result(
            "manifest_launch_gate_mismatch",
            expected_size=expected_size,
            checksums_present=checksums_present,
            launch_gate=launch_gate,
        )

    storage_contract = manifest.get("storage_contract")
    if not _admin_storage_contract_is_safe(storage_contract):
        return _admin_manifest_result(
            "manifest_storage_contract_unsafe",
            expected_size=expected_size,
            checksums_present=checksums_present,
            launch_gate=launch_gate,
        )

    return _admin_manifest_result(
        "ready",
        expected_size=expected_size,
        checksums_present=checksums_present,
        launch_gate=launch_gate,
    )


def _admin_manifest_result(
    status: str,
    *,
    expected_size: int | None = None,
    checksums_present: bool = False,
    launch_gate: str | None = None,
) -> dict[str, object]:
    return {
        "status": status,
        "expected_size": expected_size,
        "checksums_present": checksums_present,
        "launch_gate": launch_gate,
    }


def _admin_storage_contract_is_safe(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        value.get("bucket_policy") == "private"
        and value.get("frontend_direct_access_allowed") is False
        and value.get("signed_urls_created") is False
        and value.get("startup_download_allowed") is False
        and value.get("request_time_materialization_allowed") is False
        and value.get("runtime_sync_required") is True
    )


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _looks_like_md5(value: str | None) -> bool:
    return value is not None and re.fullmatch(r"[0-9a-fA-F]{32}", value) is not None


def _looks_like_sha256(value: str | None) -> bool:
    return value is not None and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def _ci_spliceai_status(
    model: AdminPredictorComponentInspection,
    reference: AdminPredictorComponentInspection,
    score_cache: AdminPredictorComponentInspection,
) -> str:
    if not score_cache.ready:
        return score_cache.status
    if not model.ready:
        return model.status
    if not reference.ready:
        return reference.status
    return "ready"


def _ci_spliceai_status_notes(
    components: tuple[AdminPredictorComponentInspection, ...],
) -> tuple[str, ...]:
    notes: list[str] = []
    for component in components:
        if component.ready:
            continue
        if component.asset_role in {CI_SPLICEAI_MODEL_ASSET_ROLE, CI_SPLICEAI_REFERENCE_ASSET_ROLE}:
            notes.append("model_reference_materialization_required")
        elif component.asset_role == CI_SPLICEAI_SCORE_CACHE_ASSET_ROLE:
            notes.append("score_cache_materialization_required")
    return tuple(dict.fromkeys(notes))


def _capice_status(
    model: AdminPredictorComponentInspection,
    feature_cache: AdminPredictorComponentInspection,
) -> str:
    if not model.ready:
        return model.status
    if not feature_cache.ready:
        return feature_cache.status
    return "ready"


def _capice_status_notes(
    components: tuple[AdminPredictorComponentInspection, ...],
) -> tuple[str, ...]:
    notes: list[str] = []
    for component in components:
        if component.ready:
            continue
        if component.asset_role == CAPICE_MODEL_ASSET_ROLE:
            notes.append("capice_model_materialization_required")
        elif component.asset_role == CAPICE_FEATURE_CACHE_ASSET_ROLE:
            notes.append("spliceai_feature_cache_materialization_required")
    return tuple(dict.fromkeys(notes))


def _single_cache_admin_inspection(
    *,
    source_id: str,
    launch_gate: str,
    component: AdminPredictorComponentInspection,
) -> AdminPredictorRuntimeInspection:
    return AdminPredictorRuntimeInspection(
        source_id=source_id,
        status="ready" if component.ready else component.status,
        available=component.ready,
        launch_gate=launch_gate,
        status_notes=() if component.ready else ("score_cache_materialization_required",),
        components=(component,),
    )


def _validate_materialization_record(
    settings: Settings,
    plan: PredictorRuntimePlan,
    materialization_store: SourceAssetMaterializationStore,
    *,
    environment: str | None,
) -> SourceAssetMaterializationRecord:
    bucket_id, object_path = _parse_supabase_object_uri(plan.object_uri)
    try:
        record = materialization_store.get_source_asset_materialization(
            source_id=plan.source_id,
            asset_role=plan.asset_role,
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
            f"{plan.display_name} materialization metadata is unavailable",
            {"source_id": plan.source_id, "asset_role": plan.asset_role},
        ) from exc
    if record is None:
        raise SourceAssetMaterializationError(
            "materialization_metadata_missing",
            f"no {plan.display_name} materialization metadata is available",
            {"source_id": plan.source_id, "asset_role": plan.asset_role},
        )
    if record.source_id != plan.source_id or record.asset_role != plan.asset_role:
        raise SourceAssetMaterializationError(
            "materialization_source_mismatch",
            f"{plan.display_name} materialization metadata is for the wrong source asset",
            {"source_id": plan.source_id},
        )
    if record.public_access_allowed or record.frontend_direct_access_allowed:
        raise SourceAssetMaterializationError(
            "materialization_public_access_blocked",
            f"{plan.display_name} materialization metadata allows public or frontend access",
            {"source_id": plan.source_id},
        )
    if record.upload_status != "verified":
        raise SourceAssetMaterializationError(
            "materialization_upload_not_verified",
            f"{plan.display_name} source object is not verified",
            {"source_id": plan.source_id, "upload_status": record.upload_status},
        )
    if record.approval_status != "approved":
        raise SourceAssetMaterializationError(
            "materialization_not_approved",
            f"{plan.display_name} source object is not approved for backend use",
            {"source_id": plan.source_id, "approval_status": record.approval_status},
        )
    if record.materialization_status != "ready":
        raise SourceAssetMaterializationError(
            "materialization_not_ready",
            f"{plan.display_name} materialization is not ready",
            {
                "source_id": plan.source_id,
                "materialization_status": record.materialization_status,
            },
        )
    if record.fail_closed_reason is not None:
        raise SourceAssetMaterializationError(
            "materialization_fail_closed",
            f"{plan.display_name} materialization has a fail-closed reason",
            {"source_id": plan.source_id},
        )
    if record.byte_size is None or record.byte_size <= 0:
        raise SourceAssetMaterializationError(
            "materialization_size_missing",
            f"ready {plan.display_name} materialization is missing byte_size",
            {"source_id": plan.source_id},
        )
    if record.byte_size != plan.path.stat().st_size:
        raise SourceAssetMaterializationError(
            "materialization_size_mismatch",
            f"{plan.display_name} materialization size does not match local cache bytes",
            {"source_id": plan.source_id},
        )
    if record.verified_at is None:
        raise SourceAssetMaterializationError(
            "materialization_verified_at_missing",
            f"ready {plan.display_name} materialization is missing verified_at",
            {"source_id": plan.source_id},
        )
    if record.checksum_algorithm is None or record.checksum_value is None:
        raise SourceAssetMaterializationError(
            "materialization_checksum_missing",
            f"ready {plan.display_name} materialization is missing checksum metadata",
            {"source_id": plan.source_id},
        )
    if (record.checksum_algorithm or "").lower() != "md5":
        raise SourceAssetMaterializationError(
            "materialization_checksum_algorithm_mismatch",
            f"{plan.display_name} materialization checksum must use md5",
            {"source_id": plan.source_id},
        )
    if plan.expected_md5 and (record.checksum_value or "").lower() != plan.expected_md5:
        raise SourceAssetMaterializationError(
            "materialization_checksum_mismatch",
            f"{plan.display_name} materialization checksum does not match registry metadata",
            {"source_id": plan.source_id},
        )
    materialized_path = _resolve_materialization_path(settings, record.local_cache_path)
    if materialized_path.resolve() != plan.path.resolve():
        raise SourceAssetMaterializationError(
            "materialization_path_mismatch",
            f"{plan.display_name} materialization path does not match configured runtime path",
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
    launch_gate: str | None = None,
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
        launch_gate=launch_gate,
    )


def _esm1b_launch_gate_from_manifest(manifest_path: Path) -> str | None:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ESM1B_LICENSE_GATE

    for key in ("license_gate", "launch_gate"):
        if key not in manifest:
            continue
        value = manifest.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None
    return ESM1B_LICENSE_GATE


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
    "materialization_metadata_unavailable": PredictorRuntimeStatus.MATERIALIZATION_STORE_UNAVAILABLE,
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
