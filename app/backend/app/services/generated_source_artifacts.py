from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import md5, sha256
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterable
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.services.ai_gateway.retrieval import (
    LITERATURE_EMBEDDING_SOURCE_ID,
    SCHEMA_VERSION as LITERATURE_EMBEDDING_SCHEMA_VERSION,
    LiteratureEmbeddingStore,
)
from app.services.clingen_local import CLINGEN_LOCAL_SOURCE_ID, ClinGenLocalStore
from app.services.pubmed_local import PUBMED_LOCAL_SOURCE_ID, PubMedLocalStore
from app.services.source_imports import DEFAULT_SOURCE_ASSET_BUCKET
from app.services.source_storage_uploads import (
    DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
    REST_UPLOAD_TIMEOUT,
    S3_CONNECT_TIMEOUT_SECONDS,
    S3_MULTIPART_CHUNK_BYTES,
    S3_MULTIPART_MAX_CONCURRENCY,
    S3_READ_TIMEOUT_SECONDS,
    S3_RETRY_ATTEMPTS,
    SourceStorageUploadItem,
    SourceStorageUploadMode,
    SourceStorageUploadResult,
    SourceStorageUploadStatus,
    execute_source_storage_uploads,
)

GENERATED_SOURCE_ARTIFACT_IDS = (
    "clingen_local",
    "pubmed_local",
    "literature_embeddings",
)


@dataclass(frozen=True)
class GeneratedSourceArtifactDefinition:
    artifact_id: str
    source_id: str
    asset_id: str
    role: str
    sqlite_setting: str
    manifest_setting: str
    schema_version: str
    launch_gate: str
    content_type: str = "application/octet-stream"


@dataclass(frozen=True)
class GeneratedSourceArtifactIdentity:
    artifact_id: str
    source_id: str
    asset_id: str
    role: str
    schema_version: str | None
    source_version: str | None
    byte_size: int
    md5: str
    sha256: str
    inspection_status: str
    inspection: dict[str, Any]

    def manifest_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "source_id": self.source_id,
            "asset_id": self.asset_id,
            "role": self.role,
            "schema_version": self.schema_version,
            "source_version": self.source_version,
            "byte_size": self.byte_size,
            "md5": self.md5,
            "sha256": self.sha256,
            "checksums": {"md5": self.md5, "sha256": self.sha256},
            "inspection_status": self.inspection_status,
            "inspection": self.inspection,
            "storage_contract": {
                "bucket_policy": "private",
                "frontend_direct_access_allowed": False,
                "signed_urls_created": False,
                "startup_download_allowed": False,
                "request_time_materialization_allowed": False,
                "runtime_sync_required": True,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


@dataclass(frozen=True)
class GeneratedSourceArtifactUploadItem:
    artifact_id: str
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
    schema_version: str | None
    source_version: str | None
    status: SourceStorageUploadStatus
    message: str | None = None
    local_path: Path | None = None
    manifest_path: Path | None = None

    @property
    def source_object_uri(self) -> str | None:
        if self.status is SourceStorageUploadStatus.MISSING_LOCAL_FILE:
            return None
        return f"supabase://{self.bucket_id}/{self.object_path}"

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
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
            "schema_version": self.schema_version,
            "source_version": self.source_version,
            "status": self.status.value,
            "message": self.message,
            "local_path_values_emitted": False,
            "secret_values_emitted": False,
        }

    def to_source_upload_item(self) -> SourceStorageUploadItem | None:
        if self.local_path is None or self.manifest_path is None:
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
            status=self.status,
            message=self.message,
        )


@dataclass(frozen=True)
class GeneratedSourceArtifactUploadResult:
    items: tuple[GeneratedSourceArtifactUploadItem, ...]
    uploaded_count: int
    planned_count: int
    blocked_count: int
    failed_count: int

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "items": [item.to_sanitized_dict() for item in self.items],
            "uploaded_count": self.uploaded_count,
            "planned_count": self.planned_count,
            "blocked_count": self.blocked_count,
            "failed_count": self.failed_count,
        }


@dataclass(frozen=True)
class GeneratedSourceArtifactMaterializationResult:
    ready: bool
    status: str
    artifact_id: str
    source_id: str
    source_kind: str
    source_configured: bool
    bucket_id: str | None = None
    destination_present: bool = False
    downloaded: bool = False
    copied: bool = False
    byte_size: int | None = None
    expected_size_bytes: int | None = None
    md5_verified: bool = False
    sha256_verified: bool = False
    schema_validated: bool = False
    checksum_computed: bool = False
    manifest_written: bool = False
    warnings: tuple[str, ...] = ()

    def to_sanitized_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["local_path_values_emitted"] = False
        payload["object_uri_values_emitted"] = False
        payload["secret_values_emitted"] = False
        return payload


@dataclass(frozen=True)
class _ExpectedIdentity:
    status: str
    manifest_payload: dict[str, Any] | None = None
    expected_size_bytes: int | None = None
    expected_md5: str | None = None
    expected_sha256: str | None = None
    warnings: tuple[str, ...] = ()


class _StorageDownloadError(RuntimeError):
    def __init__(self, status: str, warnings: tuple[str, ...] = ()) -> None:
        super().__init__(status)
        self.status = status
        self.warnings = warnings


GENERATED_SOURCE_ARTIFACTS: dict[str, GeneratedSourceArtifactDefinition] = {
    "clingen_local": GeneratedSourceArtifactDefinition(
        artifact_id="clingen_local",
        source_id=CLINGEN_LOCAL_SOURCE_ID,
        asset_id="clingen_local_sqlite",
        role="generated_sqlite_runtime_store",
        sqlite_setting="clingen_local_sqlite_path",
        manifest_setting="clingen_local_manifest_path",
        schema_version="eamos.clingen_local.v1",
        launch_gate="clingen_local_materialization",
    ),
    "pubmed_local": GeneratedSourceArtifactDefinition(
        artifact_id="pubmed_local",
        source_id=PUBMED_LOCAL_SOURCE_ID,
        asset_id="pubmed_local_sqlite",
        role="generated_sqlite_runtime_store",
        sqlite_setting="pubmed_local_sqlite_path",
        manifest_setting="pubmed_local_manifest_path",
        schema_version="eamos.pubmed_local.v4",
        launch_gate="pubmed_local_materialization",
    ),
    "literature_embeddings": GeneratedSourceArtifactDefinition(
        artifact_id="literature_embeddings",
        source_id=LITERATURE_EMBEDDING_SOURCE_ID,
        asset_id="literature_embeddings_sqlite",
        role="generated_sqlite_runtime_store",
        sqlite_setting="rag_sqlite_path",
        manifest_setting="rag_manifest_path",
        schema_version=LITERATURE_EMBEDDING_SCHEMA_VERSION,
        launch_gate="literature_rag_materialization",
    ),
}


def build_generated_source_artifact_upload_items(
    settings: Settings,
    *,
    artifact_ids: Iterable[str] = GENERATED_SOURCE_ARTIFACT_IDS,
    bucket_id: str = DEFAULT_SOURCE_ASSET_BUCKET,
    manifest_staging_root: Path,
    bucket_file_size_limit: int = DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
) -> tuple[GeneratedSourceArtifactUploadItem, ...]:
    manifest_staging_root.mkdir(parents=True, exist_ok=True)
    items: list[GeneratedSourceArtifactUploadItem] = []
    for artifact_id in artifact_ids:
        definition = _definition_for(artifact_id)
        local_path = _resolve_backend_path(settings, getattr(settings, definition.sqlite_setting))
        items.append(
            _build_upload_item(
                definition,
                bucket_id=bucket_id,
                local_path=local_path,
                manifest_staging_root=manifest_staging_root,
                bucket_file_size_limit=bucket_file_size_limit,
            )
        )
    return tuple(items)


def execute_generated_source_artifact_uploads(
    items: Iterable[GeneratedSourceArtifactUploadItem],
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
    s3_client_factory: Any | None = None,
) -> GeneratedSourceArtifactUploadResult:
    item_tuple = tuple(items)
    upload_items = tuple(item.to_source_upload_item() for item in item_tuple)
    source_items = tuple(item for item in upload_items if item is not None)
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
        updated = _merge_upload_statuses(item_tuple, upload_result)
    else:
        updated = item_tuple
    blocked_statuses = {
        SourceStorageUploadStatus.MISSING_LOCAL_FILE,
        SourceStorageUploadStatus.MISSING_MANIFEST,
        SourceStorageUploadStatus.EXCEEDS_BUCKET_LIMIT,
        SourceStorageUploadStatus.CREDENTIALS_MISSING,
    }
    return GeneratedSourceArtifactUploadResult(
        items=updated,
        uploaded_count=sum(
            1 for item in updated if item.status is SourceStorageUploadStatus.UPLOADED
        ),
        planned_count=sum(
            1 for item in updated if item.status is SourceStorageUploadStatus.PLANNED
        ),
        blocked_count=sum(1 for item in updated if item.status in blocked_statuses),
        failed_count=sum(1 for item in updated if item.status is SourceStorageUploadStatus.FAILED),
    )


def materialize_generated_source_artifact(
    settings: Settings,
    *,
    artifact_id: str,
    source_artifact_path: Path | None = None,
    source_object_uri: str | None = None,
    destination_path: Path | None = None,
    manifest_destination_path: Path | None = None,
    force: bool = False,
    http_client: httpx.Client | None = None,
    expected_size_bytes: int | None = None,
    expected_md5: str | None = None,
    expected_sha256: str | None = None,
    download_mode: SourceStorageUploadMode | str = SourceStorageUploadMode.REST,
    s3_endpoint_url: str | None = None,
    s3_region: str | None = None,
    s3_access_key_id: str | None = None,
    s3_secret_access_key: str | None = None,
    s3_client: Any | None = None,
    s3_client_factory: Any | None = None,
) -> GeneratedSourceArtifactMaterializationResult:
    definition = _definition_for(artifact_id)
    destination = _resolve_backend_path(
        settings, destination_path or getattr(settings, definition.sqlite_setting)
    )
    manifest_destination = _resolve_backend_path(
        settings, manifest_destination_path or getattr(settings, definition.manifest_setting)
    )
    if source_artifact_path is not None and source_object_uri:
        return _materialization_result(
            definition,
            "multiple_sources_configured",
            source_kind="mixed",
            source_configured=True,
            warnings=("provide_local_artifact_or_storage_object_not_both",),
        )

    existing = _inspect_candidate(
        definition,
        destination,
        manifest_path=manifest_destination,
        expected_size=expected_size_bytes,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )
    if existing.ready and not force:
        return existing
    if destination.exists() and not force:
        return _materialization_result(
            definition,
            f"existing_generated_artifact_{existing.status}",
            source_kind=_source_kind(source_artifact_path, source_object_uri),
            source_configured=bool(source_artifact_path or source_object_uri),
            destination_present=True,
            byte_size=existing.byte_size,
            expected_size_bytes=expected_size_bytes,
            warnings=("existing_generated_artifact_failed_verification",),
        )

    if source_artifact_path is not None:
        return _materialize_from_local_path(
            settings,
            definition,
            source_artifact_path=source_artifact_path,
            destination=destination,
            manifest_destination=manifest_destination,
            expected_size_bytes=expected_size_bytes,
            expected_md5=expected_md5,
            expected_sha256=expected_sha256,
        )
    if source_object_uri:
        return _materialize_from_private_storage(
            settings,
            definition,
            source_object_uri=source_object_uri,
            destination=destination,
            manifest_destination=manifest_destination,
            http_client=http_client,
            expected_size_bytes=expected_size_bytes,
            expected_md5=expected_md5,
            expected_sha256=expected_sha256,
            download_mode=download_mode,
            s3_endpoint_url=s3_endpoint_url,
            s3_region=s3_region,
            s3_access_key_id=s3_access_key_id,
            s3_secret_access_key=s3_secret_access_key,
            s3_client=s3_client,
            s3_client_factory=s3_client_factory,
        )
    return _materialization_result(
        definition,
        "source_unconfigured",
        source_kind="none",
        source_configured=False,
    )


def _build_upload_item(
    definition: GeneratedSourceArtifactDefinition,
    *,
    bucket_id: str,
    local_path: Path,
    manifest_staging_root: Path,
    bucket_file_size_limit: int,
) -> GeneratedSourceArtifactUploadItem:
    if not local_path.is_file():
        return _upload_item(
            definition,
            bucket_id=bucket_id,
            object_path=_placeholder_object_path(definition, local_path),
            manifest_object_path=f"{_placeholder_object_path(definition, local_path)}.manifest.json",
            status=SourceStorageUploadStatus.MISSING_LOCAL_FILE,
            message="generated SQLite artifact is not present",
            local_path=local_path,
        )
    identity = _identity_from_artifact_file(definition, local_path)
    if identity.status != "ready":
        return _upload_item(
            definition,
            bucket_id=bucket_id,
            object_path=_placeholder_object_path(definition, local_path),
            manifest_object_path=f"{_placeholder_object_path(definition, local_path)}.manifest.json",
            byte_size=identity.expected_size_bytes,
            md5=identity.expected_md5,
            sha256=identity.expected_sha256,
            status=SourceStorageUploadStatus.FAILED,
            message=f"generated artifact readiness failed: {identity.status}",
            local_path=local_path,
        )
    if (
        identity.expected_size_bytes is not None
        and identity.expected_size_bytes > bucket_file_size_limit
    ):
        object_path = _object_path(
            definition=definition,
            local_path=local_path,
            sha256_value=identity.expected_sha256,
        )
        return _upload_item(
            definition,
            bucket_id=bucket_id,
            object_path=object_path,
            manifest_object_path=f"{object_path}.manifest.json",
            byte_size=identity.expected_size_bytes,
            md5=identity.expected_md5,
            sha256=identity.expected_sha256,
            schema_version=_manifest_string(identity.manifest_payload, "schema_version"),
            source_version=_manifest_string(identity.manifest_payload, "source_version"),
            status=SourceStorageUploadStatus.EXCEEDS_BUCKET_LIMIT,
            message="generated artifact exceeds current private bucket file-size limit",
            local_path=local_path,
        )
    object_path = _object_path(
        definition=definition,
        local_path=local_path,
        sha256_value=identity.expected_sha256,
    )
    manifest_path = manifest_staging_root / f"{definition.artifact_id}.manifest.json"
    manifest_path.write_text(
        json.dumps(identity.manifest_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return _upload_item(
        definition,
        bucket_id=bucket_id,
        object_path=object_path,
        manifest_object_path=f"{object_path}.manifest.json",
        byte_size=identity.expected_size_bytes,
        md5=identity.expected_md5,
        sha256=identity.expected_sha256,
        schema_version=_manifest_string(identity.manifest_payload, "schema_version"),
        source_version=_manifest_string(identity.manifest_payload, "source_version"),
        status=SourceStorageUploadStatus.PLANNED,
        message="eligible for private Storage upload",
        local_path=local_path,
        manifest_path=manifest_path,
    )


def _materialize_from_local_path(
    settings: Settings,
    definition: GeneratedSourceArtifactDefinition,
    *,
    source_artifact_path: Path,
    destination: Path,
    manifest_destination: Path,
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> GeneratedSourceArtifactMaterializationResult:
    source = _resolve_operator_path(source_artifact_path)
    if not source.exists():
        return _materialization_result(
            definition,
            "source_artifact_missing",
            source_kind="local_file",
            source_configured=True,
        )
    if not source.is_file():
        return _materialization_result(
            definition,
            "source_artifact_not_file",
            source_kind="local_file",
            source_configured=True,
        )
    identity = _identity_from_explicit_args_or_artifact(
        definition,
        source,
        expected_size_bytes=expected_size_bytes,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )
    if identity.status != "ready":
        return _materialization_result(
            definition,
            identity.status,
            source_kind="local_file",
            source_configured=True,
            expected_size_bytes=identity.expected_size_bytes,
            warnings=identity.warnings,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            with source.open("rb") as source_file:
                shutil.copyfileobj(source_file, temp_file, length=8 * 1024 * 1024)
    except OSError:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        return _materialization_result(
            definition,
            "local_artifact_copy_failed",
            source_kind="local_file",
            source_configured=True,
            warnings=("generated_artifact_destination_not_modified",),
        )
    return _verify_and_replace(
        definition,
        temp_path=Path(temp_name),
        destination=destination,
        manifest_destination=manifest_destination,
        manifest_payload=identity.manifest_payload,
        source_kind="local_file",
        copied=True,
        expected_size=identity.expected_size_bytes,
        expected_md5=identity.expected_md5,
        expected_sha256=identity.expected_sha256,
        warnings=identity.warnings,
    )


def _materialize_from_private_storage(
    settings: Settings,
    definition: GeneratedSourceArtifactDefinition,
    *,
    source_object_uri: str,
    destination: Path,
    manifest_destination: Path,
    http_client: httpx.Client | None,
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
    download_mode: SourceStorageUploadMode | str,
    s3_endpoint_url: str | None,
    s3_region: str | None,
    s3_access_key_id: str | None,
    s3_secret_access_key: str | None,
    s3_client: Any | None,
    s3_client_factory: Any | None,
) -> GeneratedSourceArtifactMaterializationResult:
    try:
        bucket_id, object_path = _parse_supabase_object_uri(source_object_uri)
    except ValueError:
        return _materialization_result(
            definition,
            "source_object_uri_invalid",
            source_kind="supabase_private_storage",
            source_configured=True,
        )
    resolved_download_mode = SourceStorageUploadMode(download_mode)
    if resolved_download_mode is SourceStorageUploadMode.S3_MULTIPART:
        return _materialize_from_private_storage_s3(
            definition,
            bucket_id=bucket_id,
            object_path=object_path,
            destination=destination,
            manifest_destination=manifest_destination,
            expected_size_bytes=expected_size_bytes,
            expected_md5=expected_md5,
            expected_sha256=expected_sha256,
            s3_endpoint_url=s3_endpoint_url,
            s3_region=s3_region,
            s3_access_key_id=s3_access_key_id,
            s3_secret_access_key=s3_secret_access_key,
            s3_client=s3_client,
            s3_client_factory=s3_client_factory,
        )

    if not settings.supabase_url or not settings.supabase_service_role_key:
        return _materialization_result(
            definition,
            "supabase_storage_credentials_missing",
            source_kind="supabase_private_storage",
            source_configured=True,
            bucket_id=bucket_id,
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=REST_UPLOAD_TIMEOUT)
    try:
        identity = _identity_from_storage_manifest_or_args(
            client,
            settings=settings,
            bucket_id=bucket_id,
            object_path=object_path,
            definition=definition,
            expected_size_bytes=expected_size_bytes,
            expected_md5=expected_md5,
            expected_sha256=expected_sha256,
        )
        if identity.status != "ready":
            return _materialization_result(
                definition,
                identity.status,
                source_kind="supabase_private_storage",
                source_configured=True,
                bucket_id=bucket_id,
                expected_size_bytes=identity.expected_size_bytes,
                warnings=identity.warnings,
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_name = temp_file.name
                _download_storage_object(
                    client,
                    settings=settings,
                    bucket_id=bucket_id,
                    object_path=object_path,
                    destination=temp_file,
                )
        except _StorageDownloadError as exc:
            if temp_name is not None:
                Path(temp_name).unlink(missing_ok=True)
            return _materialization_result(
                definition,
                exc.status,
                source_kind="supabase_private_storage",
                source_configured=True,
                bucket_id=bucket_id,
                expected_size_bytes=identity.expected_size_bytes,
                warnings=exc.warnings,
            )
    finally:
        if owns_client:
            client.close()

    return _verify_and_replace(
        definition,
        temp_path=Path(temp_name),
        destination=destination,
        manifest_destination=manifest_destination,
        manifest_payload=identity.manifest_payload,
        source_kind="supabase_private_storage",
        bucket_id=bucket_id,
        downloaded=True,
        expected_size=identity.expected_size_bytes,
        expected_md5=identity.expected_md5,
        expected_sha256=identity.expected_sha256,
        warnings=identity.warnings,
    )


def _materialize_from_private_storage_s3(
    definition: GeneratedSourceArtifactDefinition,
    *,
    bucket_id: str,
    object_path: str,
    destination: Path,
    manifest_destination: Path,
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
    s3_endpoint_url: str | None,
    s3_region: str | None,
    s3_access_key_id: str | None,
    s3_secret_access_key: str | None,
    s3_client: Any | None,
    s3_client_factory: Any | None,
) -> GeneratedSourceArtifactMaterializationResult:
    has_injected_client = s3_client is not None or s3_client_factory is not None
    if not has_injected_client and (
        not s3_endpoint_url or not s3_access_key_id or not s3_secret_access_key
    ):
        return _materialization_result(
            definition,
            "supabase_storage_s3_credentials_missing",
            source_kind="supabase_private_storage_s3",
            source_configured=True,
            bucket_id=bucket_id,
        )
    try:
        resolved_client = s3_client
        if resolved_client is None:
            resolved_client = (
                s3_client_factory()
                if s3_client_factory is not None
                else _build_s3_client(
                    endpoint_url=s3_endpoint_url,
                    region=s3_region,
                    access_key_id=s3_access_key_id,
                    secret_access_key=s3_secret_access_key,
                )
            )
    except Exception:
        return _materialization_result(
            definition,
            "supabase_storage_s3_client_unavailable",
            source_kind="supabase_private_storage_s3",
            source_configured=True,
            bucket_id=bucket_id,
        )

    identity = _identity_from_storage_manifest_or_args_s3(
        resolved_client,
        bucket_id=bucket_id,
        object_path=object_path,
        definition=definition,
        expected_size_bytes=expected_size_bytes,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )
    if identity.status != "ready":
        return _materialization_result(
            definition,
            identity.status,
            source_kind="supabase_private_storage_s3",
            source_configured=True,
            bucket_id=bucket_id,
            expected_size_bytes=identity.expected_size_bytes,
            warnings=identity.warnings,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            _download_storage_object_s3(
                resolved_client,
                bucket_id=bucket_id,
                object_path=object_path,
                destination=temp_file,
            )
    except _StorageDownloadError as exc:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        return _materialization_result(
            definition,
            exc.status,
            source_kind="supabase_private_storage_s3",
            source_configured=True,
            bucket_id=bucket_id,
            expected_size_bytes=identity.expected_size_bytes,
            warnings=exc.warnings,
        )

    return _verify_and_replace(
        definition,
        temp_path=Path(temp_name),
        destination=destination,
        manifest_destination=manifest_destination,
        manifest_payload=identity.manifest_payload,
        source_kind="supabase_private_storage_s3",
        bucket_id=bucket_id,
        downloaded=True,
        expected_size=identity.expected_size_bytes,
        expected_md5=identity.expected_md5,
        expected_sha256=identity.expected_sha256,
        warnings=identity.warnings,
    )


def _verify_and_replace(
    definition: GeneratedSourceArtifactDefinition,
    *,
    temp_path: Path,
    destination: Path,
    manifest_destination: Path,
    manifest_payload: dict[str, Any] | None,
    source_kind: str,
    bucket_id: str | None = None,
    downloaded: bool = False,
    copied: bool = False,
    expected_size: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
    warnings: tuple[str, ...] = (),
) -> GeneratedSourceArtifactMaterializationResult:
    candidate = _inspect_candidate(
        definition,
        temp_path,
        manifest_path=None,
        expected_size=expected_size,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )
    if not candidate.ready:
        temp_path.unlink(missing_ok=True)
        return _materialization_result(
            definition,
            candidate.status,
            source_kind=source_kind,
            source_configured=True,
            bucket_id=bucket_id,
            downloaded=downloaded,
            copied=copied,
            byte_size=candidate.byte_size,
            expected_size_bytes=expected_size,
            md5_verified=candidate.md5_verified,
            sha256_verified=candidate.sha256_verified,
            schema_validated=candidate.schema_validated,
            checksum_computed=candidate.checksum_computed,
            warnings=warnings + ("generated_artifact_destination_not_modified",),
        )
    temp_path.replace(destination)
    manifest_destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_destination.write_text(
        json.dumps(
            manifest_payload
            or _identity_from_artifact_file(definition, destination).manifest_payload,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    final = _inspect_candidate(
        definition,
        destination,
        manifest_path=manifest_destination,
        expected_size=expected_size,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )
    if not final.ready:
        return _materialization_result(
            definition,
            f"runtime_probe_{final.status}",
            source_kind=source_kind,
            source_configured=True,
            bucket_id=bucket_id,
            destination_present=True,
            downloaded=downloaded,
            copied=copied,
            byte_size=final.byte_size,
            expected_size_bytes=expected_size,
            md5_verified=final.md5_verified,
            sha256_verified=final.sha256_verified,
            schema_validated=final.schema_validated,
            checksum_computed=final.checksum_computed,
            manifest_written=True,
            warnings=warnings,
        )
    return _materialization_result(
        definition,
        "ready",
        source_kind=source_kind,
        source_configured=True,
        bucket_id=bucket_id,
        destination_present=True,
        downloaded=downloaded,
        copied=copied,
        byte_size=final.byte_size,
        expected_size_bytes=expected_size,
        md5_verified=final.md5_verified,
        sha256_verified=final.sha256_verified,
        schema_validated=True,
        checksum_computed=True,
        manifest_written=True,
        warnings=warnings,
    )


def _inspect_candidate(
    definition: GeneratedSourceArtifactDefinition,
    path: Path,
    *,
    manifest_path: Path | None,
    expected_size: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> GeneratedSourceArtifactMaterializationResult:
    if not path.exists():
        return _materialization_result(
            definition, "missing", source_kind="existing", source_configured=False
        )
    if not path.is_file():
        return _materialization_result(
            definition,
            "not_file",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
        )
    byte_size = path.stat().st_size
    if expected_size is not None and byte_size != expected_size:
        return _materialization_result(
            definition,
            "size_mismatch",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
        )
    md5_value, sha256_value = _hash_file(path)
    normalized_md5 = _normalize_md5(expected_md5)
    normalized_sha256 = _normalize_sha256(expected_sha256)
    if normalized_md5 and md5_value != normalized_md5:
        return _materialization_result(
            definition,
            "md5_mismatch",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
            checksum_computed=True,
        )
    if normalized_sha256 and sha256_value != normalized_sha256:
        return _materialization_result(
            definition,
            "sha256_mismatch",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
            md5_verified=bool(normalized_md5),
            checksum_computed=True,
        )
    inspection = _inspect_artifact_file(definition, path, manifest_path=manifest_path)
    if not bool(inspection.get("ready")):
        return _materialization_result(
            definition,
            f"schema_validation_failed:{inspection.get('status', 'unknown')}",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
            md5_verified=bool(normalized_md5),
            sha256_verified=bool(normalized_sha256),
            checksum_computed=True,
        )
    return _materialization_result(
        definition,
        "ready",
        source_kind="existing",
        source_configured=False,
        destination_present=True,
        byte_size=byte_size,
        expected_size_bytes=expected_size,
        md5_verified=bool(normalized_md5),
        sha256_verified=bool(normalized_sha256),
        schema_validated=True,
        checksum_computed=True,
    )


def _identity_from_artifact_file(
    definition: GeneratedSourceArtifactDefinition, path: Path
) -> _ExpectedIdentity:
    byte_size = path.stat().st_size if path.is_file() else None
    if byte_size is None:
        return _ExpectedIdentity(status="source_artifact_missing")
    inspection = _inspect_artifact_file(definition, path, manifest_path=None)
    if not bool(inspection.get("ready")):
        return _ExpectedIdentity(
            status=f"schema_validation_failed:{inspection.get('status', 'unknown')}",
            expected_size_bytes=byte_size,
        )
    md5_value, sha256_value = _hash_file(path)
    identity = GeneratedSourceArtifactIdentity(
        artifact_id=definition.artifact_id,
        source_id=definition.source_id,
        asset_id=definition.asset_id,
        role=definition.role,
        schema_version=str(inspection.get("schema_version") or definition.schema_version),
        source_version=_optional_text(inspection.get("source_version")),
        byte_size=byte_size,
        md5=md5_value,
        sha256=sha256_value,
        inspection_status=str(inspection.get("status") or "ready"),
        inspection=inspection,
    )
    return _ExpectedIdentity(
        status="ready",
        manifest_payload=identity.manifest_payload(),
        expected_size_bytes=identity.byte_size,
        expected_md5=identity.md5,
        expected_sha256=identity.sha256,
    )


def _identity_from_explicit_args_or_artifact(
    definition: GeneratedSourceArtifactDefinition,
    path: Path,
    *,
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> _ExpectedIdentity:
    if expected_size_bytes is not None or expected_md5 is not None or expected_sha256 is not None:
        return _identity_from_explicit_args(
            definition,
            path,
            expected_size_bytes=expected_size_bytes,
            expected_md5=expected_md5,
            expected_sha256=expected_sha256,
        )
    return _identity_from_artifact_file(definition, path)


def _identity_from_explicit_args(
    definition: GeneratedSourceArtifactDefinition,
    path: Path,
    *,
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> _ExpectedIdentity:
    normalized_md5 = _normalize_md5(expected_md5)
    normalized_sha256 = _normalize_sha256(expected_sha256)
    if expected_size_bytes is not None and expected_size_bytes <= 0:
        return _ExpectedIdentity(status="expected_identity_invalid")
    if expected_md5 is not None and normalized_md5 is None:
        return _ExpectedIdentity(status="expected_identity_invalid")
    if expected_sha256 is not None and normalized_sha256 is None:
        return _ExpectedIdentity(status="expected_identity_invalid")
    generated = _identity_from_artifact_file(definition, path)
    if generated.status != "ready":
        return generated
    payload = dict(generated.manifest_payload or {})
    if expected_size_bytes is not None:
        payload["byte_size"] = expected_size_bytes
    checksums = dict(payload.get("checksums") if isinstance(payload.get("checksums"), dict) else {})
    if normalized_md5 is not None:
        payload["md5"] = normalized_md5
        checksums["md5"] = normalized_md5
    if normalized_sha256 is not None:
        payload["sha256"] = normalized_sha256
        checksums["sha256"] = normalized_sha256
    payload["checksums"] = checksums
    return _ExpectedIdentity(
        status="ready",
        manifest_payload=payload,
        expected_size_bytes=expected_size_bytes,
        expected_md5=normalized_md5,
        expected_sha256=normalized_sha256,
    )


def _identity_from_storage_manifest_or_args(
    client: httpx.Client,
    *,
    settings: Settings,
    bucket_id: str,
    object_path: str,
    definition: GeneratedSourceArtifactDefinition,
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> _ExpectedIdentity:
    if expected_size_bytes is not None or expected_md5 is not None or expected_sha256 is not None:
        explicit = _identity_from_manifest(
            definition,
            {
                "byte_size": expected_size_bytes,
                "md5": expected_md5,
                "sha256": expected_sha256,
                "checksums": {"md5": expected_md5, "sha256": expected_sha256},
            },
        )
        if explicit.status == "ready":
            return explicit
    try:
        response = client.get(
            _storage_object_url(
                settings.supabase_url or "", bucket_id, f"{object_path}.manifest.json"
            ),
            headers=_storage_headers(settings),
        )
    except httpx.HTTPError:
        return _ExpectedIdentity(
            status="manifest_download_failed",
            warnings=("private_storage_manifest_download_failed",),
        )
    if response.status_code == 404:
        return _ExpectedIdentity(status="manifest_missing")
    if response.status_code < 200 or response.status_code >= 300:
        return _ExpectedIdentity(status="manifest_download_failed")
    try:
        manifest = response.json()
    except json.JSONDecodeError:
        return _ExpectedIdentity(status="manifest_invalid_json")
    if not isinstance(manifest, dict):
        return _ExpectedIdentity(status="manifest_invalid_json")
    return _identity_from_manifest(definition, manifest)


def _identity_from_storage_manifest_or_args_s3(
    client: Any,
    *,
    bucket_id: str,
    object_path: str,
    definition: GeneratedSourceArtifactDefinition,
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> _ExpectedIdentity:
    if expected_size_bytes is not None or expected_md5 is not None or expected_sha256 is not None:
        explicit = _identity_from_manifest(
            definition,
            {
                "byte_size": expected_size_bytes,
                "md5": expected_md5,
                "sha256": expected_sha256,
                "checksums": {"md5": expected_md5, "sha256": expected_sha256},
            },
        )
        if explicit.status == "ready":
            return explicit
    try:
        response = client.get_object(Bucket=bucket_id, Key=f"{object_path}.manifest.json")
        body = response.get("Body")
        content = body.read() if hasattr(body, "read") else body
    except Exception as exc:
        if _s3_error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
            return _ExpectedIdentity(status="manifest_missing")
        return _ExpectedIdentity(
            status="manifest_download_failed",
            warnings=("private_storage_manifest_download_failed",),
        )
    try:
        manifest = json.loads(
            content.decode("utf-8") if isinstance(content, bytes) else str(content)
        )
    except json.JSONDecodeError:
        return _ExpectedIdentity(status="manifest_invalid_json")
    if not isinstance(manifest, dict):
        return _ExpectedIdentity(status="manifest_invalid_json")
    return _identity_from_manifest(definition, manifest)


def _identity_from_manifest(
    definition: GeneratedSourceArtifactDefinition,
    manifest: dict[str, Any],
) -> _ExpectedIdentity:
    if manifest.get("source_id") not in (None, definition.source_id):
        return _ExpectedIdentity(status="manifest_source_mismatch")
    if manifest.get("asset_id") not in (None, definition.asset_id):
        return _ExpectedIdentity(status="manifest_asset_mismatch")
    checksums = manifest.get("checksums") if isinstance(manifest.get("checksums"), dict) else {}
    expected_size = _optional_positive_int(manifest.get("byte_size"))
    expected_md5 = _normalize_md5(_optional_text(manifest.get("md5") or checksums.get("md5")))
    expected_sha256 = _normalize_sha256(
        _optional_text(manifest.get("sha256") or checksums.get("sha256"))
    )
    if expected_size is None or not (expected_md5 or expected_sha256):
        return _ExpectedIdentity(
            status="manifest_identity_incomplete",
            expected_size_bytes=expected_size,
        )
    return _ExpectedIdentity(
        status="ready",
        manifest_payload=manifest,
        expected_size_bytes=expected_size,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )


def _inspect_artifact_file(
    definition: GeneratedSourceArtifactDefinition,
    path: Path,
    *,
    manifest_path: Path | None,
) -> dict[str, Any]:
    if definition.artifact_id == "clingen_local":
        return ClinGenLocalStore(path, manifest_path=manifest_path).inspect().to_sanitized_dict()
    if definition.artifact_id == "pubmed_local":
        return PubMedLocalStore(path, manifest_path=manifest_path).inspect().to_sanitized_dict()
    if definition.artifact_id == "literature_embeddings":
        return (
            LiteratureEmbeddingStore(path, manifest_path=manifest_path)
            .inspect()
            .to_sanitized_dict()
        )
    raise ValueError(f"unsupported generated artifact: {definition.artifact_id}")


def _download_storage_object(
    client: httpx.Client,
    *,
    settings: Settings,
    bucket_id: str,
    object_path: str,
    destination,
) -> None:
    try:
        with client.stream(
            "GET",
            _storage_object_url(settings.supabase_url or "", bucket_id, object_path),
            headers=_storage_headers(settings),
        ) as response:
            if response.status_code == 404:
                raise _StorageDownloadError("source_object_missing")
            if response.status_code < 200 or response.status_code >= 300:
                raise _StorageDownloadError("source_object_download_failed")
            for chunk in response.iter_bytes():
                if chunk:
                    destination.write(chunk)
    except httpx.HTTPError:
        raise _StorageDownloadError(
            "source_object_download_failed",
            ("private_storage_download_failed_no_public_fallback",),
        ) from None


def _download_storage_object_s3(
    client: Any,
    *,
    bucket_id: str,
    object_path: str,
    destination,
) -> None:
    config = _s3_transfer_config()
    config_kwargs = {"Config": config} if config is not None else {}
    try:
        client.download_fileobj(
            bucket_id,
            object_path,
            destination,
            **config_kwargs,
        )
    except Exception as exc:
        if _s3_error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
            raise _StorageDownloadError("source_object_missing") from None
        raise _StorageDownloadError(
            "source_object_download_failed",
            ("private_storage_download_failed_no_public_fallback",),
        ) from None


def _build_s3_client(
    *,
    endpoint_url: str | None,
    region: str | None,
    access_key_id: str | None,
    secret_access_key: str | None,
) -> Any:
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:  # pragma: no cover - depends on deployment environment
        raise RuntimeError("boto3 is required for s3 generated artifact sync") from exc
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region or "auto",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=Config(
            s3={"addressing_style": "path"},
            connect_timeout=S3_CONNECT_TIMEOUT_SECONDS,
            read_timeout=S3_READ_TIMEOUT_SECONDS,
            retries={"max_attempts": S3_RETRY_ATTEMPTS, "mode": "standard"},
            tcp_keepalive=True,
        ),
    )


def _s3_transfer_config() -> Any | None:
    try:
        from boto3.s3.transfer import TransferConfig
    except ImportError:  # pragma: no cover - real S3 client construction checks boto3 separately
        return None

    return TransferConfig(
        multipart_threshold=S3_MULTIPART_CHUNK_BYTES,
        multipart_chunksize=S3_MULTIPART_CHUNK_BYTES,
        max_concurrency=S3_MULTIPART_MAX_CONCURRENCY,
    )


def _s3_error_code(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error")
        if isinstance(error, dict):
            code = error.get("Code")
            return str(code) if code is not None else None
    return None


def _merge_upload_statuses(
    original: tuple[GeneratedSourceArtifactUploadItem, ...],
    result: SourceStorageUploadResult,
) -> tuple[GeneratedSourceArtifactUploadItem, ...]:
    by_object = {item.object_path: item for item in result.items}
    updated: list[GeneratedSourceArtifactUploadItem] = []
    for item in original:
        replacement = by_object.get(item.object_path)
        if replacement is None:
            updated.append(item)
            continue
        updated.append(
            _upload_item(
                _definition_for(item.artifact_id),
                bucket_id=item.bucket_id,
                object_path=item.object_path,
                manifest_object_path=item.manifest_object_path,
                content_type=item.content_type,
                byte_size=item.byte_size,
                md5=item.md5,
                sha256=item.sha256,
                schema_version=item.schema_version,
                source_version=item.source_version,
                status=replacement.status,
                message=_sanitize_upload_message(
                    replacement.message,
                    status=replacement.status,
                    local_path=item.local_path,
                    manifest_path=item.manifest_path,
                ),
                local_path=item.local_path,
                manifest_path=item.manifest_path,
            )
        )
    return tuple(updated)


def _sanitize_upload_message(
    message: str | None,
    *,
    status: SourceStorageUploadStatus,
    local_path: Path | None,
    manifest_path: Path | None,
) -> str | None:
    if message is None:
        return None
    if status is not SourceStorageUploadStatus.FAILED:
        return message
    local_values = tuple(str(path) for path in (local_path, manifest_path) if path is not None)
    if any(value and value in message for value in local_values):
        if message.startswith("private S3 multipart upload failed"):
            return "private S3 multipart upload failed"
        if message.startswith("private storage upload failed"):
            return "private storage upload failed"
        return "private storage upload failed"
    return message


def _upload_item(
    definition: GeneratedSourceArtifactDefinition,
    *,
    bucket_id: str,
    object_path: str,
    manifest_object_path: str,
    content_type: str | None = None,
    byte_size: int | None = None,
    md5: str | None = None,
    sha256: str | None = None,
    schema_version: str | None = None,
    source_version: str | None = None,
    status: SourceStorageUploadStatus,
    message: str | None,
    local_path: Path | None = None,
    manifest_path: Path | None = None,
) -> GeneratedSourceArtifactUploadItem:
    return GeneratedSourceArtifactUploadItem(
        artifact_id=definition.artifact_id,
        source_id=definition.source_id,
        asset_id=definition.asset_id,
        role=definition.role,
        bucket_id=bucket_id,
        object_path=object_path,
        manifest_object_path=manifest_object_path,
        content_type=content_type or definition.content_type,
        byte_size=byte_size,
        md5=md5,
        sha256=sha256,
        schema_version=schema_version,
        source_version=source_version,
        status=status,
        message=message,
        local_path=local_path,
        manifest_path=manifest_path,
    )


def _materialization_result(
    definition: GeneratedSourceArtifactDefinition,
    status: str,
    *,
    source_kind: str,
    source_configured: bool,
    bucket_id: str | None = None,
    destination_present: bool = False,
    downloaded: bool = False,
    copied: bool = False,
    byte_size: int | None = None,
    expected_size_bytes: int | None = None,
    md5_verified: bool = False,
    sha256_verified: bool = False,
    schema_validated: bool = False,
    checksum_computed: bool = False,
    manifest_written: bool = False,
    warnings: tuple[str, ...] = (),
) -> GeneratedSourceArtifactMaterializationResult:
    return GeneratedSourceArtifactMaterializationResult(
        ready=status == "ready",
        status=status,
        artifact_id=definition.artifact_id,
        source_id=definition.source_id,
        source_kind=source_kind,
        source_configured=source_configured,
        bucket_id=bucket_id,
        destination_present=destination_present,
        downloaded=downloaded,
        copied=copied,
        byte_size=byte_size,
        expected_size_bytes=expected_size_bytes,
        md5_verified=md5_verified,
        sha256_verified=sha256_verified,
        schema_validated=schema_validated,
        checksum_computed=checksum_computed,
        manifest_written=manifest_written,
        warnings=warnings,
    )


def _object_path(
    *,
    definition: GeneratedSourceArtifactDefinition,
    local_path: Path,
    sha256_value: str | None,
) -> str:
    checksum_segment = f"sha256-{sha256_value}" if sha256_value else "sha256-unverified"
    return (
        f"generated/{definition.source_id}/{definition.asset_id}/"
        f"{checksum_segment}/{local_path.name}"
    )


def _placeholder_object_path(
    definition: GeneratedSourceArtifactDefinition,
    local_path: Path,
) -> str:
    return _object_path(definition=definition, local_path=local_path, sha256_value=None)


def _hash_file(path: Path) -> tuple[str, str]:
    md5_digest = md5(usedforsecurity=False)
    sha256_digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8 * 1024 * 1024), b""):
            md5_digest.update(chunk)
            sha256_digest.update(chunk)
    return md5_digest.hexdigest(), sha256_digest.hexdigest()


def _parse_supabase_object_uri(value: str) -> tuple[str, str]:
    prefix = "supabase://"
    if not value.startswith(prefix):
        raise ValueError("source object URI must use supabase://bucket/object-path")
    remainder = value[len(prefix) :]
    bucket_id, separator, object_path = remainder.partition("/")
    if not bucket_id or not separator or not object_path:
        raise ValueError("source object URI must include bucket and object path")
    return bucket_id, object_path


def _storage_object_url(supabase_url: str, bucket_id: str, object_path: str) -> str:
    encoded_path = "/".join(quote(part, safe="") for part in object_path.split("/"))
    return (
        f"{supabase_url.rstrip('/')}/storage/v1/object/"
        f"{quote(bucket_id, safe='')}/{encoded_path}"
    )


def _storage_headers(settings: Settings) -> dict[str, str]:
    service_role_key = settings.supabase_service_role_key or ""
    return {"apikey": service_role_key, "Authorization": f"Bearer {service_role_key}"}


def _definition_for(artifact_id: str) -> GeneratedSourceArtifactDefinition:
    try:
        return GENERATED_SOURCE_ARTIFACTS[artifact_id]
    except KeyError:
        raise ValueError(f"unsupported generated artifact: {artifact_id}") from None


def _source_kind(source_artifact_path: Path | None, source_object_uri: str | None) -> str:
    if source_artifact_path is not None:
        return "local_file"
    if source_object_uri:
        return "supabase_private_storage"
    return "none"


def _resolve_backend_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _resolve_operator_path(path: Path) -> Path:
    return path if path.is_absolute() else Path.cwd() / path


def _optional_positive_int(value: object) -> int | None:
    return value if isinstance(value, int) and value > 0 else None


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _manifest_string(manifest: dict[str, Any] | None, key: str) -> str | None:
    if manifest is None:
        return None
    return _optional_text(manifest.get(key))


def _normalize_md5(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized if len(normalized) == 32 else None


def _normalize_sha256(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized if len(normalized) == 64 else None
