from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import quote

import httpx

from app.data_sources.source_manifest import POST_REFERENCE_DAY1_SOURCE_IDS
from app.services.source_downloads import (
    DEFAULT_LARGE_STAGING_ROOT,
    DEFAULT_SMALL_STAGING_ROOT,
    build_source_download_items,
)
from app.services.source_imports import DEFAULT_SOURCE_ASSET_BUCKET

DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT = 50 * 1024 * 1024 * 1024
S3_CONNECT_TIMEOUT_SECONDS = 120
S3_READ_TIMEOUT_SECONDS = 300
S3_RETRY_ATTEMPTS = 10
S3_MULTIPART_CHUNK_BYTES = 128 * 1024 * 1024
S3_MULTIPART_MAX_CONCURRENCY = 3


class SourceStorageUploadStatus(str, Enum):
    PLANNED = "planned"
    MISSING_LOCAL_FILE = "missing_local_file"
    MISSING_MANIFEST = "missing_manifest"
    EXCEEDS_BUCKET_LIMIT = "exceeds_bucket_limit"
    CREDENTIALS_MISSING = "credentials_missing"
    UPLOADED = "uploaded"
    FAILED = "failed"


class SourceStorageUploadMode(str, Enum):
    REST = "rest"
    S3_MULTIPART = "s3_multipart"


@dataclass(frozen=True)
class SourceStorageUploadItem:
    source_id: str
    asset_id: str
    role: str
    bucket_id: str
    object_path: str
    manifest_object_path: str
    local_path: Path
    manifest_path: Path
    content_type: str
    byte_size: int | None
    md5: str | None
    sha256: str | None
    status: SourceStorageUploadStatus
    message: str | None = None


@dataclass(frozen=True)
class SourceStorageUploadResult:
    items: tuple[SourceStorageUploadItem, ...]
    uploaded_count: int
    planned_count: int
    blocked_count: int
    failed_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "items": [
                asdict(item)
                | {
                    "local_path": str(item.local_path),
                    "manifest_path": str(item.manifest_path),
                    "status": item.status.value,
                }
                for item in self.items
            ],
            "uploaded_count": self.uploaded_count,
            "planned_count": self.planned_count,
            "blocked_count": self.blocked_count,
            "failed_count": self.failed_count,
        }


def build_source_storage_upload_items(
    *,
    source_ids: Iterable[str] = POST_REFERENCE_DAY1_SOURCE_IDS,
    bucket_id: str = DEFAULT_SOURCE_ASSET_BUCKET,
    small_staging_root: Path = DEFAULT_SMALL_STAGING_ROOT,
    large_staging_root: Path = DEFAULT_LARGE_STAGING_ROOT,
    bucket_file_size_limit: int = DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
) -> tuple[SourceStorageUploadItem, ...]:
    items: list[SourceStorageUploadItem] = []
    for download in build_source_download_items(
        source_ids=source_ids,
        small_staging_root=small_staging_root,
        large_staging_root=large_staging_root,
        include_large=True,
    ):
        local_path = download.destination
        manifest_path = local_path.with_suffix(local_path.suffix + ".manifest.json")
        manifest = _load_manifest(manifest_path) if manifest_path.is_file() else {}
        sha256_value = _optional_manifest_string(manifest, "sha256")
        md5_value = _optional_manifest_string(manifest, "md5")
        byte_size = local_path.stat().st_size if local_path.is_file() else None
        object_path = _object_path(
            source_id=download.source_id,
            asset_id=download.asset_id,
            sha256_value=sha256_value,
            file_name=local_path.name,
        )
        status, message = _planned_status(
            local_path=local_path,
            manifest_path=manifest_path,
            byte_size=byte_size,
            bucket_file_size_limit=bucket_file_size_limit,
        )
        items.append(
            SourceStorageUploadItem(
                source_id=download.source_id,
                asset_id=download.asset_id,
                role=download.role,
                bucket_id=bucket_id,
                object_path=object_path,
                manifest_object_path=f"{object_path}.manifest.json",
                local_path=local_path,
                manifest_path=manifest_path,
                content_type="application/octet-stream",
                byte_size=byte_size,
                md5=md5_value,
                sha256=sha256_value,
                status=status,
                message=message,
            )
        )
    return tuple(items)


def execute_source_storage_uploads(
    items: Iterable[SourceStorageUploadItem],
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
) -> SourceStorageUploadResult:
    resolved_upload_mode = SourceStorageUploadMode(upload_mode)
    owns_client = client is None and resolved_upload_mode is SourceStorageUploadMode.REST
    if client is None and resolved_upload_mode is SourceStorageUploadMode.REST:
        client = httpx.Client(timeout=None)
    try:
        resolved = tuple(
            _execute_item(
                item,
                upload=upload,
                upload_mode=resolved_upload_mode,
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
            for item in items
        )
    finally:
        if owns_client and client is not None:
            client.close()

    blocked_statuses = {
        SourceStorageUploadStatus.MISSING_LOCAL_FILE,
        SourceStorageUploadStatus.MISSING_MANIFEST,
        SourceStorageUploadStatus.EXCEEDS_BUCKET_LIMIT,
        SourceStorageUploadStatus.CREDENTIALS_MISSING,
    }
    return SourceStorageUploadResult(
        items=resolved,
        uploaded_count=sum(
            1 for item in resolved if item.status is SourceStorageUploadStatus.UPLOADED
        ),
        planned_count=sum(
            1 for item in resolved if item.status is SourceStorageUploadStatus.PLANNED
        ),
        blocked_count=sum(1 for item in resolved if item.status in blocked_statuses),
        failed_count=sum(1 for item in resolved if item.status is SourceStorageUploadStatus.FAILED),
    )


def _execute_item(
    item: SourceStorageUploadItem,
    *,
    upload: bool,
    upload_mode: SourceStorageUploadMode,
    supabase_url: str | None,
    service_role_key: str | None,
    client: httpx.Client | None,
    s3_endpoint_url: str | None,
    s3_region: str | None,
    s3_access_key_id: str | None,
    s3_secret_access_key: str | None,
    s3_client: Any | None,
    s3_client_factory: Callable[[], Any] | None,
) -> SourceStorageUploadItem:
    if item.status is not SourceStorageUploadStatus.PLANNED:
        return item
    if not upload:
        return item
    if upload_mode is SourceStorageUploadMode.S3_MULTIPART:
        return _execute_s3_item(
            item,
            s3_endpoint_url=s3_endpoint_url,
            s3_region=s3_region,
            s3_access_key_id=s3_access_key_id,
            s3_secret_access_key=s3_secret_access_key,
            s3_client=s3_client,
            s3_client_factory=s3_client_factory,
        )
    if not supabase_url or not service_role_key or client is None:
        return _replace_item(
            item,
            status=SourceStorageUploadStatus.CREDENTIALS_MISSING,
            message="storage upload requires Supabase URL and service-role key",
        )
    asset_uploaded = _upload_file(
        client=client,
        supabase_url=supabase_url,
        service_role_key=service_role_key,
        bucket_id=item.bucket_id,
        object_path=item.object_path,
        path=item.local_path,
        content_type=item.content_type,
    )
    manifest_uploaded = _upload_file(
        client=client,
        supabase_url=supabase_url,
        service_role_key=service_role_key,
        bucket_id=item.bucket_id,
        object_path=item.manifest_object_path,
        path=item.manifest_path,
        content_type=item.content_type,
    )
    if not asset_uploaded or not manifest_uploaded:
        return _replace_item(
            item,
            status=SourceStorageUploadStatus.FAILED,
            message="private storage upload failed",
        )
    return _replace_item(
        item,
        status=SourceStorageUploadStatus.UPLOADED,
        message="asset and checksum manifest uploaded to private storage",
    )


def _execute_s3_item(
    item: SourceStorageUploadItem,
    *,
    s3_endpoint_url: str | None,
    s3_region: str | None,
    s3_access_key_id: str | None,
    s3_secret_access_key: str | None,
    s3_client: Any | None,
    s3_client_factory: Callable[[], Any] | None,
) -> SourceStorageUploadItem:
    has_injected_client = s3_client is not None or s3_client_factory is not None
    if not has_injected_client and (
        not s3_endpoint_url or not s3_access_key_id or not s3_secret_access_key
    ):
        return _replace_item(
            item,
            status=SourceStorageUploadStatus.CREDENTIALS_MISSING,
            message="S3 multipart upload requires endpoint URL, access key id, and secret key",
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
        _upload_file_s3(
            client=resolved_client,
            bucket_id=item.bucket_id,
            object_path=item.object_path,
            path=item.local_path,
            content_type=item.content_type,
        )
        _upload_file_s3(
            client=resolved_client,
            bucket_id=item.bucket_id,
            object_path=item.manifest_object_path,
            path=item.manifest_path,
            content_type=item.content_type,
        )
    except Exception as exc:  # pragma: no cover - exercised through injected client failures
        return _replace_item(
            item,
            status=SourceStorageUploadStatus.FAILED,
            message=f"private S3 multipart upload failed: {exc}",
        )
    return _replace_item(
        item,
        status=SourceStorageUploadStatus.UPLOADED,
        message="asset and checksum manifest uploaded to private storage through S3 multipart",
    )


def _upload_file(
    *,
    client: httpx.Client,
    supabase_url: str,
    service_role_key: str,
    bucket_id: str,
    object_path: str,
    path: Path,
    content_type: str,
) -> bool:
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": content_type,
        "cache-control": "31536000",
        "x-upsert": "false",
    }
    with path.open("rb") as file:
        response = client.post(
            _storage_object_url(supabase_url, bucket_id, object_path),
            headers=headers,
            content=file,
        )
    return response.status_code in {200, 201}


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
        raise RuntimeError("boto3 is required for s3_multipart source storage uploads") from exc
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


def _upload_file_s3(
    *,
    client: Any,
    bucket_id: str,
    object_path: str,
    path: Path,
    content_type: str,
) -> None:
    from boto3.s3.transfer import TransferConfig

    client.upload_file(
        str(path),
        bucket_id,
        object_path,
        ExtraArgs={"ContentType": content_type, "CacheControl": "31536000"},
        Config=TransferConfig(
            multipart_threshold=S3_MULTIPART_CHUNK_BYTES,
            multipart_chunksize=S3_MULTIPART_CHUNK_BYTES,
            max_concurrency=S3_MULTIPART_MAX_CONCURRENCY,
        ),
    )


def _planned_status(
    *,
    local_path: Path,
    manifest_path: Path,
    byte_size: int | None,
    bucket_file_size_limit: int,
) -> tuple[SourceStorageUploadStatus, str | None]:
    if not local_path.is_file():
        return (SourceStorageUploadStatus.MISSING_LOCAL_FILE, "downloaded asset is not present")
    if not manifest_path.is_file():
        return (
            SourceStorageUploadStatus.MISSING_MANIFEST,
            "download checksum manifest is not present",
        )
    if byte_size is not None and byte_size > bucket_file_size_limit:
        return (
            SourceStorageUploadStatus.EXCEEDS_BUCKET_LIMIT,
            "asset exceeds current private bucket file-size limit",
        )
    return (SourceStorageUploadStatus.PLANNED, "eligible for private storage upload")


def _replace_item(
    item: SourceStorageUploadItem,
    *,
    status: SourceStorageUploadStatus,
    message: str | None,
) -> SourceStorageUploadItem:
    return SourceStorageUploadItem(
        source_id=item.source_id,
        asset_id=item.asset_id,
        role=item.role,
        bucket_id=item.bucket_id,
        object_path=item.object_path,
        manifest_object_path=item.manifest_object_path,
        local_path=item.local_path,
        manifest_path=item.manifest_path,
        content_type=item.content_type,
        byte_size=item.byte_size,
        md5=item.md5,
        sha256=item.sha256,
        status=status,
        message=message,
    )


def _load_manifest(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _optional_manifest_string(manifest: dict[str, object], key: str) -> str | None:
    value = manifest.get(key)
    return value if isinstance(value, str) and value else None


def _object_path(
    *,
    source_id: str,
    asset_id: str,
    sha256_value: str | None,
    file_name: str,
) -> str:
    checksum_segment = f"sha256-{sha256_value}" if sha256_value else "sha256-unverified"
    return f"{source_id}/{asset_id}/{checksum_segment}/{file_name}"


def _storage_object_url(supabase_url: str, bucket_id: str, object_path: str) -> str:
    encoded_path = "/".join(quote(part, safe="") for part in object_path.split("/"))
    return (
        f"{supabase_url.rstrip('/')}/storage/v1/object/{quote(bucket_id, safe='')}/{encoded_path}"
    )
