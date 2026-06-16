from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import md5, sha256
import json
from pathlib import Path
from typing import Any, Callable, Iterable

import httpx

from app.core.config import Settings
from app.services.predictor_runtime import (
    CAPICE_FEATURE_CACHE_ASSET_ROLE,
    CAPICE_FEATURE_CACHE_SOURCE_ID,
    CAPICE_LAUNCH_GATE,
    CAPICE_MODEL_ASSET_ROLE,
    CAPICE_SOURCE_ID,
    CI_SPLICEAI_LAUNCH_GATE,
    CI_SPLICEAI_MODEL_ASSET_ROLE,
    CI_SPLICEAI_REFERENCE_ASSET_ROLE,
    CI_SPLICEAI_SCORE_CACHE_ASSET_ROLE,
    CI_SPLICEAI_SOURCE_ID,
    ESM1B_ASSET_ROLE,
    ESM1B_SOURCE_ID,
)
from app.services.source_imports import DEFAULT_SOURCE_ASSET_BUCKET
from app.services.source_storage_uploads import (
    DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
    SourceStorageUploadItem,
    SourceStorageUploadMode,
    SourceStorageUploadStatus,
    execute_source_storage_uploads,
)

TIER2_PREDICTOR_ARTIFACT_IDS = (
    "esm1b_hg38_scores",
    "ci_spliceai",
    "capice",
)


class Tier2PredictorArtifactStatus(str, Enum):
    PLANNED = "planned"
    MISSING_LOCAL_FILE = "missing_local_file"
    LOCAL_PATH_NOT_FILE = "local_path_not_file"
    EXCEEDS_BUCKET_LIMIT = "exceeds_bucket_limit"
    BLOCKED_INCOMPLETE_ARTIFACT_SET = "blocked_incomplete_artifact_set"
    CREDENTIALS_MISSING = "credentials_missing"
    UPLOADED = "uploaded"
    FAILED = "failed"


@dataclass(frozen=True)
class Tier2PredictorArtifactFileDefinition:
    artifact_id: str
    component_id: str
    source_id: str
    asset_id: str
    role: str
    path_setting: str
    launch_gate: str | None
    path_suffix: str = ""
    content_type: str = "application/octet-stream"


@dataclass(frozen=True)
class Tier2PredictorArtifactUploadItem:
    artifact_id: str
    component_id: str
    source_id: str
    asset_id: str
    role: str
    bucket_id: str
    object_path: str
    manifest_object_path: str
    content_type: str
    byte_size: int | None
    md5: str | None
    sha256: str | None
    launch_gate: str | None
    status: Tier2PredictorArtifactStatus
    message: str | None = None
    local_path: Path | None = None
    manifest_path: Path | None = None

    @property
    def source_object_uri(self) -> str | None:
        if self.status in {
            Tier2PredictorArtifactStatus.MISSING_LOCAL_FILE,
            Tier2PredictorArtifactStatus.LOCAL_PATH_NOT_FILE,
        }:
            return None
        return f"supabase://{self.bucket_id}/{self.object_path}"

    def to_source_upload_item(self) -> SourceStorageUploadItem | None:
        if (
            self.status is not Tier2PredictorArtifactStatus.PLANNED
            or self.local_path is None
            or self.manifest_path is None
        ):
            return None
        return SourceStorageUploadItem(
            source_id=self.source_id,
            asset_id=self.asset_id,
            role=self.role,
            bucket_id=self.bucket_id,
            object_path=self.object_path,
            manifest_object_path=self.manifest_object_path,
            local_path=self.local_path,
            manifest_path=self.manifest_path,
            content_type=self.content_type,
            byte_size=self.byte_size,
            md5=self.md5,
            sha256=self.sha256,
            status=SourceStorageUploadStatus.PLANNED,
            message=self.message,
        )

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "component_id": self.component_id,
            "source_id": self.source_id,
            "asset_id": self.asset_id,
            "role": self.role,
            "bucket_id": self.bucket_id,
            "object_path": self.object_path,
            "manifest_object_path": self.manifest_object_path,
            "source_object_uri": self.source_object_uri,
            "content_type": self.content_type,
            "byte_size": self.byte_size,
            "md5": self.md5,
            "sha256": self.sha256,
            "launch_gate": self.launch_gate,
            "status": self.status.value,
            "message": self.message,
            "local_path_values_emitted": False,
            "secret_values_emitted": False,
        }


@dataclass(frozen=True)
class Tier2PredictorArtifactUploadResult:
    items: tuple[Tier2PredictorArtifactUploadItem, ...]
    uploaded_count: int
    planned_count: int
    blocked_count: int
    failed_count: int

    def to_sanitized_dict(self) -> dict[str, object]:
        status_counts = Counter(item.status.value for item in self.items)
        return {
            "items": [item.to_sanitized_dict() for item in self.items],
            "uploaded_count": self.uploaded_count,
            "planned_count": self.planned_count,
            "blocked_count": self.blocked_count,
            "failed_count": self.failed_count,
            "status_counts": dict(sorted(status_counts.items())),
        }


TIER2_PREDICTOR_ARTIFACT_FILES: tuple[Tier2PredictorArtifactFileDefinition, ...] = (
    Tier2PredictorArtifactFileDefinition(
        artifact_id="esm1b_hg38_scores",
        component_id="score_cache",
        source_id=ESM1B_SOURCE_ID,
        asset_id="esm1b_hg38_tsv_gz",
        role=ESM1B_ASSET_ROLE,
        path_setting="esm1b_hg38_runtime_asset_path",
        launch_gate="esm1b_score_file_terms_unconfirmed",
    ),
    Tier2PredictorArtifactFileDefinition(
        artifact_id="esm1b_hg38_scores",
        component_id="score_cache_index",
        source_id=ESM1B_SOURCE_ID,
        asset_id="esm1b_hg38_tsv_gz_tbi",
        role="predictor_tabix_index",
        path_setting="esm1b_hg38_runtime_asset_path",
        path_suffix=".tbi",
        launch_gate="esm1b_score_file_terms_unconfirmed",
    ),
    Tier2PredictorArtifactFileDefinition(
        artifact_id="ci_spliceai",
        component_id="model",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_keras_model",
        role=CI_SPLICEAI_MODEL_ASSET_ROLE,
        path_setting="ci_spliceai_model_path",
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    ),
    Tier2PredictorArtifactFileDefinition(
        artifact_id="ci_spliceai",
        component_id="reference_bundle",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_reference_bundle",
        role=CI_SPLICEAI_REFERENCE_ASSET_ROLE,
        path_setting="ci_spliceai_reference_path",
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
        content_type="application/json",
    ),
    Tier2PredictorArtifactFileDefinition(
        artifact_id="ci_spliceai",
        component_id="score_cache",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_hg38_score_cache_vcf_gz",
        role=CI_SPLICEAI_SCORE_CACHE_ASSET_ROLE,
        path_setting="ci_spliceai_score_cache_path",
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    ),
    Tier2PredictorArtifactFileDefinition(
        artifact_id="ci_spliceai",
        component_id="score_cache_index",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_hg38_score_cache_vcf_gz_tbi",
        role="score_cache_tabix_index",
        path_setting="ci_spliceai_score_cache_path",
        path_suffix=".tbi",
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    ),
    Tier2PredictorArtifactFileDefinition(
        artifact_id="capice",
        component_id="model",
        source_id=CAPICE_SOURCE_ID,
        asset_id="capice_xgboost_model",
        role=CAPICE_MODEL_ASSET_ROLE,
        path_setting="capice_model_path",
        launch_gate=CAPICE_LAUNCH_GATE,
        content_type="application/json",
    ),
    Tier2PredictorArtifactFileDefinition(
        artifact_id="capice",
        component_id="feature_cache",
        source_id=CAPICE_FEATURE_CACHE_SOURCE_ID,
        asset_id="capice_hg38_feature_cache_tsv_gz",
        role=CAPICE_FEATURE_CACHE_ASSET_ROLE,
        path_setting="capice_feature_cache_path",
        launch_gate=CAPICE_LAUNCH_GATE,
    ),
    Tier2PredictorArtifactFileDefinition(
        artifact_id="capice",
        component_id="feature_cache_index",
        source_id=CAPICE_FEATURE_CACHE_SOURCE_ID,
        asset_id="capice_hg38_feature_cache_tsv_gz_tbi",
        role="spliceai_feature_cache_tabix_index",
        path_setting="capice_feature_cache_path",
        path_suffix=".tbi",
        launch_gate=CAPICE_LAUNCH_GATE,
    ),
)


def build_tier2_predictor_artifact_upload_items(
    settings: Settings,
    *,
    artifact_ids: Iterable[str] = TIER2_PREDICTOR_ARTIFACT_IDS,
    bucket_id: str = DEFAULT_SOURCE_ASSET_BUCKET,
    manifest_staging_root: Path,
    bucket_file_size_limit: int = DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
) -> tuple[Tier2PredictorArtifactUploadItem, ...]:
    manifest_staging_root.mkdir(parents=True, exist_ok=True)
    requested = tuple(artifact_ids)
    unknown = sorted(set(requested) - set(TIER2_PREDICTOR_ARTIFACT_IDS))
    if unknown:
        raise ValueError(f"unsupported Tier 2 predictor artifact: {', '.join(unknown)}")

    items: list[Tier2PredictorArtifactUploadItem] = []
    for artifact_id in requested:
        group = tuple(
            definition
            for definition in TIER2_PREDICTOR_ARTIFACT_FILES
            if definition.artifact_id == artifact_id
        )
        group_items = tuple(
            _build_upload_item(
                definition,
                settings=settings,
                bucket_id=bucket_id,
                manifest_staging_root=manifest_staging_root,
                bucket_file_size_limit=bucket_file_size_limit,
            )
            for definition in group
        )
        items.extend(_block_incomplete_group(group_items))
    return tuple(items)


def execute_tier2_predictor_artifact_uploads(
    items: Iterable[Tier2PredictorArtifactUploadItem],
    *,
    upload: bool = False,
    upload_mode: SourceStorageUploadMode | str = SourceStorageUploadMode.REST,
    supabase_url: str | None = None,
    service_role_key: str | None = None,
    client: httpx.Client | None = None,
    s3_endpoint_url: str | None = None,
    s3_region: str | None = None,
    s3_access_key_id: str | None = None,
    s3_secret_access_key: str | None = None,
    s3_client: Any | None = None,
    s3_client_factory: Callable[[], Any] | None = None,
) -> Tier2PredictorArtifactUploadResult:
    item_tuple = tuple(items)
    source_items = tuple(
        source_item
        for source_item in (item.to_source_upload_item() for item in item_tuple)
        if source_item is not None
    )
    if source_items:
        upload_result = execute_source_storage_uploads(
            source_items,
            upload=upload,
            upload_mode=upload_mode,
            supabase_url=supabase_url,
            service_role_key=service_role_key,
            client=client,
            s3_endpoint_url=s3_endpoint_url,
            s3_region=s3_region,
            s3_access_key_id=s3_access_key_id,
            s3_secret_access_key=s3_secret_access_key,
            s3_client=s3_client,
            s3_client_factory=s3_client_factory,
        )
        resolved = _merge_upload_statuses(item_tuple, upload_result.items)
    else:
        resolved = item_tuple
    blocked_statuses = {
        Tier2PredictorArtifactStatus.MISSING_LOCAL_FILE,
        Tier2PredictorArtifactStatus.LOCAL_PATH_NOT_FILE,
        Tier2PredictorArtifactStatus.EXCEEDS_BUCKET_LIMIT,
        Tier2PredictorArtifactStatus.BLOCKED_INCOMPLETE_ARTIFACT_SET,
        Tier2PredictorArtifactStatus.CREDENTIALS_MISSING,
    }
    return Tier2PredictorArtifactUploadResult(
        items=resolved,
        uploaded_count=sum(
            1 for item in resolved if item.status is Tier2PredictorArtifactStatus.UPLOADED
        ),
        planned_count=sum(
            1 for item in resolved if item.status is Tier2PredictorArtifactStatus.PLANNED
        ),
        blocked_count=sum(1 for item in resolved if item.status in blocked_statuses),
        failed_count=sum(
            1 for item in resolved if item.status is Tier2PredictorArtifactStatus.FAILED
        ),
    )


def _build_upload_item(
    definition: Tier2PredictorArtifactFileDefinition,
    *,
    settings: Settings,
    bucket_id: str,
    manifest_staging_root: Path,
    bucket_file_size_limit: int,
) -> Tier2PredictorArtifactUploadItem:
    local_path = _component_path(settings, definition)
    object_path = _object_path(
        definition=definition,
        local_path=local_path,
        sha256_value=None,
    )
    if not local_path.exists():
        return _upload_item(
            definition,
            bucket_id=bucket_id,
            object_path=object_path,
            manifest_object_path=f"{object_path}.manifest.json",
            status=Tier2PredictorArtifactStatus.MISSING_LOCAL_FILE,
            message="Tier 2 predictor artifact component is not present",
            local_path=local_path,
        )
    if not local_path.is_file():
        return _upload_item(
            definition,
            bucket_id=bucket_id,
            object_path=object_path,
            manifest_object_path=f"{object_path}.manifest.json",
            status=Tier2PredictorArtifactStatus.LOCAL_PATH_NOT_FILE,
            message="Tier 2 predictor artifact component path is not a file",
            local_path=local_path,
        )
    byte_size = local_path.stat().st_size
    md5_value, sha256_value = _hash_file(local_path)
    object_path = _object_path(
        definition=definition,
        local_path=local_path,
        sha256_value=sha256_value,
    )
    if byte_size > bucket_file_size_limit:
        return _upload_item(
            definition,
            bucket_id=bucket_id,
            object_path=object_path,
            manifest_object_path=f"{object_path}.manifest.json",
            byte_size=byte_size,
            md5_value=md5_value,
            sha256_value=sha256_value,
            status=Tier2PredictorArtifactStatus.EXCEEDS_BUCKET_LIMIT,
            message="Tier 2 predictor artifact exceeds current private bucket file-size limit",
            local_path=local_path,
        )

    manifest_path = (
        manifest_staging_root / f"{definition.artifact_id}.{definition.component_id}.manifest.json"
    )
    manifest_path.write_text(
        json.dumps(
            _manifest_payload(
                definition,
                local_path=local_path,
                byte_size=byte_size,
                md5_value=md5_value,
                sha256_value=sha256_value,
            ),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return _upload_item(
        definition,
        bucket_id=bucket_id,
        object_path=object_path,
        manifest_object_path=f"{object_path}.manifest.json",
        byte_size=byte_size,
        md5_value=md5_value,
        sha256_value=sha256_value,
        status=Tier2PredictorArtifactStatus.PLANNED,
        message="eligible for private Storage upload",
        local_path=local_path,
        manifest_path=manifest_path,
    )


def _block_incomplete_group(
    items: tuple[Tier2PredictorArtifactUploadItem, ...],
) -> tuple[Tier2PredictorArtifactUploadItem, ...]:
    blockers = tuple(
        item.component_id
        for item in items
        if item.status is not Tier2PredictorArtifactStatus.PLANNED
    )
    if not blockers:
        return items
    message = "Tier 2 predictor artifact set is incomplete: " + ", ".join(blockers)
    return tuple(
        (
            _replace_item(
                item,
                status=Tier2PredictorArtifactStatus.BLOCKED_INCOMPLETE_ARTIFACT_SET,
                message=message,
            )
            if item.status is Tier2PredictorArtifactStatus.PLANNED
            else item
        )
        for item in items
    )


def _merge_upload_statuses(
    original: tuple[Tier2PredictorArtifactUploadItem, ...],
    source_items: tuple[SourceStorageUploadItem, ...],
) -> tuple[Tier2PredictorArtifactUploadItem, ...]:
    by_object = {item.object_path: item for item in source_items}
    updated: list[Tier2PredictorArtifactUploadItem] = []
    for item in original:
        replacement = by_object.get(item.object_path)
        if replacement is None:
            updated.append(item)
            continue
        updated.append(
            _replace_item(
                item,
                status=_tier2_status_from_source_storage(replacement.status),
                message=_sanitize_upload_message(
                    replacement.message,
                    status=replacement.status,
                    local_path=item.local_path,
                    manifest_path=item.manifest_path,
                ),
            )
        )
    return tuple(updated)


def _manifest_payload(
    definition: Tier2PredictorArtifactFileDefinition,
    *,
    local_path: Path,
    byte_size: int,
    md5_value: str,
    sha256_value: str,
) -> dict[str, Any]:
    return {
        "artifact_id": definition.artifact_id,
        "component_id": definition.component_id,
        "source_id": definition.source_id,
        "asset_id": definition.asset_id,
        "role": definition.role,
        "tier": "tier_2_predictor_cache",
        "file_name": local_path.name,
        "content_type": definition.content_type,
        "byte_size": byte_size,
        "md5": md5_value,
        "sha256": sha256_value,
        "checksums": {"md5": md5_value, "sha256": sha256_value},
        "launch_gate": definition.launch_gate,
        "storage_contract": {
            "bucket_policy": "private",
            "frontend_direct_access_allowed": False,
            "signed_urls_created": False,
            "startup_download_allowed": False,
            "request_time_materialization_allowed": False,
            "runtime_sync_required": True,
            "supabase_metadata_registration_required": True,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _component_path(
    settings: Settings,
    definition: Tier2PredictorArtifactFileDefinition,
) -> Path:
    path = getattr(settings, definition.path_setting)
    resolved = path if path.is_absolute() else settings.backend_root / path
    return Path(f"{resolved}{definition.path_suffix}") if definition.path_suffix else resolved


def _object_path(
    *,
    definition: Tier2PredictorArtifactFileDefinition,
    local_path: Path,
    sha256_value: str | None,
) -> str:
    checksum_segment = f"sha256-{sha256_value}" if sha256_value else "sha256-unverified"
    return (
        f"predictors/{definition.source_id}/{definition.asset_id}/"
        f"{checksum_segment}/{local_path.name}"
    )


def _upload_item(
    definition: Tier2PredictorArtifactFileDefinition,
    *,
    bucket_id: str,
    object_path: str,
    manifest_object_path: str,
    status: Tier2PredictorArtifactStatus,
    message: str | None,
    byte_size: int | None = None,
    md5_value: str | None = None,
    sha256_value: str | None = None,
    local_path: Path | None = None,
    manifest_path: Path | None = None,
) -> Tier2PredictorArtifactUploadItem:
    return Tier2PredictorArtifactUploadItem(
        artifact_id=definition.artifact_id,
        component_id=definition.component_id,
        source_id=definition.source_id,
        asset_id=definition.asset_id,
        role=definition.role,
        bucket_id=bucket_id,
        object_path=object_path,
        manifest_object_path=manifest_object_path,
        content_type=definition.content_type,
        byte_size=byte_size,
        md5=md5_value,
        sha256=sha256_value,
        launch_gate=definition.launch_gate,
        status=status,
        message=message,
        local_path=local_path,
        manifest_path=manifest_path,
    )


def _replace_item(
    item: Tier2PredictorArtifactUploadItem,
    *,
    status: Tier2PredictorArtifactStatus,
    message: str | None,
) -> Tier2PredictorArtifactUploadItem:
    return Tier2PredictorArtifactUploadItem(
        artifact_id=item.artifact_id,
        component_id=item.component_id,
        source_id=item.source_id,
        asset_id=item.asset_id,
        role=item.role,
        bucket_id=item.bucket_id,
        object_path=item.object_path,
        manifest_object_path=item.manifest_object_path,
        content_type=item.content_type,
        byte_size=item.byte_size,
        md5=item.md5,
        sha256=item.sha256,
        launch_gate=item.launch_gate,
        status=status,
        message=message,
        local_path=item.local_path,
        manifest_path=item.manifest_path,
    )


def _hash_file(path: Path) -> tuple[str, str]:
    md5_digest = md5(usedforsecurity=False)
    sha256_digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8 * 1024 * 1024), b""):
            md5_digest.update(chunk)
            sha256_digest.update(chunk)
    return md5_digest.hexdigest(), sha256_digest.hexdigest()


def _tier2_status_from_source_storage(
    status: SourceStorageUploadStatus,
) -> Tier2PredictorArtifactStatus:
    mapping = {
        SourceStorageUploadStatus.PLANNED: Tier2PredictorArtifactStatus.PLANNED,
        SourceStorageUploadStatus.MISSING_LOCAL_FILE: (
            Tier2PredictorArtifactStatus.MISSING_LOCAL_FILE
        ),
        SourceStorageUploadStatus.MISSING_MANIFEST: (
            Tier2PredictorArtifactStatus.BLOCKED_INCOMPLETE_ARTIFACT_SET
        ),
        SourceStorageUploadStatus.EXCEEDS_BUCKET_LIMIT: (
            Tier2PredictorArtifactStatus.EXCEEDS_BUCKET_LIMIT
        ),
        SourceStorageUploadStatus.CREDENTIALS_MISSING: (
            Tier2PredictorArtifactStatus.CREDENTIALS_MISSING
        ),
        SourceStorageUploadStatus.UPLOADED: Tier2PredictorArtifactStatus.UPLOADED,
        SourceStorageUploadStatus.FAILED: Tier2PredictorArtifactStatus.FAILED,
    }
    return mapping[status]


def _sanitize_upload_message(
    message: str | None,
    *,
    status: SourceStorageUploadStatus,
    local_path: Path | None,
    manifest_path: Path | None,
) -> str | None:
    if message is None or status is not SourceStorageUploadStatus.FAILED:
        return message
    local_values = tuple(str(path) for path in (local_path, manifest_path) if path is not None)
    if any(value and value in message for value in local_values):
        if message.startswith("private S3 multipart upload failed"):
            return "private S3 multipart upload failed"
        return "private storage upload failed"
    return message
