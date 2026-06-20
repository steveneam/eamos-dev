from __future__ import annotations

from datetime import datetime, timezone
from hashlib import md5, sha256
import json
from pathlib import Path
from typing import Any

from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry
from app.services.indexed_sources import REPEATMASKER_COMPACT_INDEX_SCHEMA
from app.services.repeatmasker_local import REPEATMASKER_SOURCE_ID
from app.services.source_imports import DEFAULT_SOURCE_ASSET_BUCKET
from app.services.source_storage_uploads import (
    DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
    SourceStorageUploadItem,
    SourceStorageUploadResult,
    SourceStorageUploadStatus,
)

REPEATMASKER_COMPACT_ARTIFACT_ID = "repeatmasker_compact_interval_index"
REPEATMASKER_COMPACT_ROLE = "repeatmasker_compact_interval_index"
REPEATMASKER_COMPACT_ASSET_ID = "repeatmasker_compact_interval_index"
REPEATMASKER_COMPACT_FILE_NAME = "repeatmasker.interval-index.jsonl"


def build_repeatmasker_compact_upload_item(
    *,
    source_artifact_path: Path,
    manifest_staging_root: Path,
    bucket_id: str = DEFAULT_SOURCE_ASSET_BUCKET,
    bucket_file_size_limit: int = DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
) -> SourceStorageUploadItem:
    manifest_staging_root.mkdir(parents=True, exist_ok=True)
    local_path = source_artifact_path
    placeholder_object_path = _object_path(sha256_value=None, file_name=local_path.name)
    placeholder_manifest_path = manifest_staging_root / "repeatmasker_compact_index.manifest.json"
    if not local_path.is_file():
        return _item(
            bucket_id=bucket_id,
            object_path=placeholder_object_path,
            manifest_object_path=f"{placeholder_object_path}.manifest.json",
            local_path=local_path,
            manifest_path=placeholder_manifest_path,
            status=SourceStorageUploadStatus.MISSING_LOCAL_FILE,
            message="RepeatMasker compact interval index is not present",
        )

    byte_size = local_path.stat().st_size
    if byte_size > bucket_file_size_limit:
        return _item(
            bucket_id=bucket_id,
            object_path=placeholder_object_path,
            manifest_object_path=f"{placeholder_object_path}.manifest.json",
            local_path=local_path,
            manifest_path=placeholder_manifest_path,
            byte_size=byte_size,
            status=SourceStorageUploadStatus.EXCEEDS_BUCKET_LIMIT,
            message="RepeatMasker compact interval index exceeds current private bucket limit",
        )

    header = _read_compact_header(local_path)
    if header.get("schema") != REPEATMASKER_COMPACT_INDEX_SCHEMA:
        return _item(
            bucket_id=bucket_id,
            object_path=placeholder_object_path,
            manifest_object_path=f"{placeholder_object_path}.manifest.json",
            local_path=local_path,
            manifest_path=placeholder_manifest_path,
            byte_size=byte_size,
            status=SourceStorageUploadStatus.FAILED,
            message="RepeatMasker compact interval index header is unsupported",
        )

    md5_value, sha256_value = _hash_file(local_path)
    object_path = _object_path(sha256_value=sha256_value, file_name=local_path.name)
    manifest_path = manifest_staging_root / "repeatmasker_compact_index.manifest.json"
    manifest_path.write_text(
        json.dumps(
            _manifest_payload(
                byte_size=byte_size,
                md5_value=md5_value,
                sha256_value=sha256_value,
                header=header,
                registry=registry,
            ),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return _item(
        bucket_id=bucket_id,
        object_path=object_path,
        manifest_object_path=f"{object_path}.manifest.json",
        local_path=local_path,
        manifest_path=manifest_path,
        byte_size=byte_size,
        md5=md5_value,
        sha256=sha256_value,
        status=SourceStorageUploadStatus.PLANNED,
        message="eligible for private Storage upload",
    )


def repeatmasker_compact_item_to_sanitized_dict(
    item: SourceStorageUploadItem,
) -> dict[str, object]:
    return {
        "artifact_id": REPEATMASKER_COMPACT_ARTIFACT_ID,
        "source_id": item.source_id,
        "asset_id": item.asset_id,
        "role": item.role,
        "bucket_id": item.bucket_id,
        "object_path": item.object_path,
        "manifest_object_path": item.manifest_object_path,
        "source_object_uri": f"supabase://{item.bucket_id}/{item.object_path}",
        "content_type": item.content_type,
        "byte_size": item.byte_size,
        "md5": item.md5,
        "sha256": item.sha256,
        "status": item.status.value,
        "message": _sanitized_message(item.message),
        "local_path_values_emitted": False,
        "secret_values_emitted": False,
    }


def repeatmasker_compact_upload_result_to_sanitized_dict(
    result: SourceStorageUploadResult,
) -> dict[str, object]:
    return {
        "items": [repeatmasker_compact_item_to_sanitized_dict(item) for item in result.items],
        "uploaded_count": result.uploaded_count,
        "planned_count": result.planned_count,
        "blocked_count": result.blocked_count,
        "failed_count": result.failed_count,
    }


def _item(
    *,
    bucket_id: str,
    object_path: str,
    manifest_object_path: str,
    local_path: Path,
    manifest_path: Path,
    status: SourceStorageUploadStatus,
    message: str | None,
    byte_size: int | None = None,
    md5: str | None = None,
    sha256: str | None = None,
) -> SourceStorageUploadItem:
    return SourceStorageUploadItem(
        source_id=REPEATMASKER_SOURCE_ID,
        asset_id=REPEATMASKER_COMPACT_ASSET_ID,
        role=REPEATMASKER_COMPACT_ROLE,
        bucket_id=bucket_id,
        object_path=object_path,
        manifest_object_path=manifest_object_path,
        local_path=local_path,
        manifest_path=manifest_path,
        content_type="application/octet-stream",
        byte_size=byte_size,
        md5=md5,
        sha256=sha256,
        status=status,
        message=message,
    )


def _read_compact_header(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            first_line = handle.readline()
    except OSError:
        return {}
    try:
        payload = json.loads(first_line)
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _manifest_payload(
    *,
    byte_size: int,
    md5_value: str,
    sha256_value: str,
    header: dict[str, Any],
    registry: DataSourceRegistry,
) -> dict[str, Any]:
    record = registry.get(REPEATMASKER_SOURCE_ID)
    source_version = header.get("source_version") or record.source_version
    return {
        "artifact_id": REPEATMASKER_COMPACT_ARTIFACT_ID,
        "source_id": REPEATMASKER_SOURCE_ID,
        "asset_id": REPEATMASKER_COMPACT_ASSET_ID,
        "role": REPEATMASKER_COMPACT_ROLE,
        "schema": REPEATMASKER_COMPACT_INDEX_SCHEMA,
        "source_version": source_version,
        "byte_size": byte_size,
        "md5": md5_value,
        "sha256": sha256_value,
        "checksums": {
            "md5": md5_value,
            "sha256": sha256_value,
        },
        "source_header": {
            key: value for key, value in header.items() if key in {"schema", "source_version"}
        },
        "license_status": record.license_status.value,
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


def _hash_file(path: Path) -> tuple[str, str]:
    md5_digest = md5()
    sha256_digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            md5_digest.update(chunk)
            sha256_digest.update(chunk)
    return md5_digest.hexdigest(), sha256_digest.hexdigest()


def _object_path(*, sha256_value: str | None, file_name: str) -> str:
    checksum_segment = f"sha256-{sha256_value}" if sha256_value else "sha256-unavailable"
    resolved_file_name = file_name or REPEATMASKER_COMPACT_FILE_NAME
    return (
        f"generated/{REPEATMASKER_SOURCE_ID}/{REPEATMASKER_COMPACT_ASSET_ID}/"
        f"{checksum_segment}/{resolved_file_name}"
    )


def _sanitized_message(message: str | None) -> str | None:
    if message is None:
        return None
    if message.startswith("private S3 multipart upload failed"):
        return "private S3 multipart upload failed"
    if message.startswith("private storage upload failed"):
        return "private storage upload failed"
    return message
