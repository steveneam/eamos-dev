from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import httpx

from app.core.config import Settings
from app.services.generated_source_artifacts import materialize_generated_source_artifact
from app.services.local_evidence_runtime_seed import materialize_local_evidence_runtime_asset
from app.services.source_storage_uploads import SourceStorageUploadMode


class MaterializationOrchestratorError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


@dataclass(frozen=True)
class MaterializationManifestItem:
    item_id: str
    kind: str
    source_id: str
    asset_id: str
    role: str
    bucket_id: str | None
    object_path: str | None
    source_object_uri: str | None
    destination_path: Path | None
    env_var: str | None
    byte_size: int | None
    md5: str | None
    sha256: str | None
    artifact_id: str | None = None
    source_artifact_path: Path | None = None
    manifest_destination_path: Path | None = None
    manifest_env_var: str | None = None
    content_type: str = "application/octet-stream"
    object_version: str | None = None
    license_status: str = "public_allowed_after_terms_review"
    approval_status: str = "approved"
    materialization_required: bool = True
    metadata: dict[str, Any] | None = None


def materialize_all_from_manifest(
    settings: Settings,
    *,
    manifest_path: Path,
    force: bool = False,
    download_mode: SourceStorageUploadMode | str = SourceStorageUploadMode.S3_MULTIPART,
    reconcile_supabase: bool = True,
    materialization_store: Any | None = None,
    max_items: int | None = None,
    http_client: httpx.Client | None = None,
    s3_client: Any | None = None,
    s3_client_factory: Any | None = None,
) -> dict[str, object]:
    manifest = _load_manifest(manifest_path)
    items = tuple(_parse_item(raw) for raw in _manifest_items(manifest))
    if max_items is not None and len(items) > max_items:
        raise MaterializationOrchestratorError(
            "manifest_item_limit_exceeded",
            "materialization manifest contains more items than this trigger allows",
            {"item_count": len(items), "max_items": max_items},
        )

    resolved_download_mode = SourceStorageUploadMode(download_mode)
    item_reports = [
        _materialize_item(
            settings,
            item,
            force=force,
            download_mode=resolved_download_mode,
            reconcile_supabase=reconcile_supabase,
            materialization_store=materialization_store,
            http_client=http_client,
            s3_client=s3_client,
            s3_client_factory=s3_client_factory,
        )
        for item in items
    ]
    ready_count = sum(1 for item in item_reports if item["ready"] is True)
    failed_count = sum(1 for item in item_reports if item["ready"] is not True)
    return {
        "mode": "eamos_materialize_all",
        "ready": failed_count == 0,
        "status": "ready" if failed_count == 0 else "incomplete",
        "download_mode": resolved_download_mode.value,
        "manifest_schema": str(manifest.get("schema_version") or "unknown"),
        "manifest_id": str(manifest.get("manifest_id") or manifest_path.name),
        "environment": str(manifest.get("environment") or "unknown"),
        "backend_runtime": str(manifest.get("backend_runtime") or "unknown"),
        "counts": {
            "item_count": len(item_reports),
            "ready_count": ready_count,
            "failed_count": failed_count,
            "metadata_reconciled_count": sum(
                1
                for item in item_reports
                if item["metadata_reconciliation"]["status"] == "reconciled"
            ),
        },
        "guardrails": {
            "startup_download": "not_used",
            "request_time_materialization": "not_used",
            "public_storage_fallback": "blocked",
            "signed_urls": "not_created",
            "frontend_direct_access": "blocked",
            "local_evidence_enabled_flip": "not_used",
            "provider_flip": "not_used",
            "render_env_or_deploy_mutation": "not_used",
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
            "object_uri_values_in_output": "blocked",
        },
        "items": item_reports,
        "local_path_values_emitted": False,
        "object_uri_values_emitted": False,
        "secret_values_emitted": False,
    }


def _materialize_item(
    settings: Settings,
    item: MaterializationManifestItem,
    *,
    force: bool,
    download_mode: SourceStorageUploadMode,
    reconcile_supabase: bool,
    materialization_store: Any | None,
    http_client: httpx.Client | None,
    s3_client: Any | None,
    s3_client_factory: Any | None,
) -> dict[str, object]:
    if item.kind == "generated_source_artifact":
        if not item.artifact_id:
            result = None
            status = "artifact_id_missing"
        else:
            result = materialize_generated_source_artifact(
                settings,
                artifact_id=item.artifact_id,
                source_artifact_path=item.source_artifact_path,
                source_object_uri=item.source_object_uri,
                destination_path=item.destination_path,
                manifest_destination_path=item.manifest_destination_path,
                force=force,
                http_client=http_client,
                expected_size_bytes=item.byte_size,
                expected_md5=item.md5,
                expected_sha256=item.sha256,
                download_mode=download_mode,
                s3_endpoint_url=settings.supabase_storage_s3_endpoint_url,
                s3_region=settings.supabase_storage_s3_region,
                s3_access_key_id=settings.supabase_storage_s3_access_key_id,
                s3_secret_access_key=settings.supabase_storage_s3_secret_access_key,
                s3_client=s3_client,
                s3_client_factory=s3_client_factory,
            )
            status = result.status
    elif item.kind == "local_evidence_runtime_asset":
        result = materialize_local_evidence_runtime_asset(
            settings,
            role=item.role,
            source_artifact_path=item.source_artifact_path,
            source_object_uri=item.source_object_uri,
            destination_path=item.destination_path,
            force=force,
            expected_size_bytes=item.byte_size,
            expected_md5=item.md5,
            expected_sha256=item.sha256,
            download_mode=download_mode,
            http_client=http_client,
            s3_endpoint_url=settings.supabase_storage_s3_endpoint_url,
            s3_region=settings.supabase_storage_s3_region,
            s3_access_key_id=settings.supabase_storage_s3_access_key_id,
            s3_secret_access_key=settings.supabase_storage_s3_secret_access_key,
            s3_client=s3_client,
            s3_client_factory=s3_client_factory,
        )
        status = result.status
    else:
        result = None
        status = "unsupported_manifest_item_kind"

    ready = bool(getattr(result, "ready", False)) if result is not None else False
    metadata_status = _reconcile_materialization_metadata(
        item,
        result=result,
        ready=ready,
        reconcile_supabase=reconcile_supabase,
        materialization_store=materialization_store,
    )
    return {
        "item_id": item.item_id,
        "kind": item.kind,
        "source_id": item.source_id,
        "asset_id": item.asset_id,
        "role": item.role,
        "env_var": item.env_var,
        "ready": ready,
        "status": status,
        "downloaded": bool(getattr(result, "downloaded", False)),
        "copied": bool(getattr(result, "copied", False)),
        "destination_present": bool(getattr(result, "destination_present", False)),
        "byte_size": getattr(result, "byte_size", None),
        "expected_size_bytes": item.byte_size,
        "md5_verified": bool(getattr(result, "md5_verified", False)),
        "sha256_verified": bool(getattr(result, "sha256_verified", False)),
        "warnings": list(getattr(result, "warnings", ()) if result is not None else ()),
        "metadata_reconciliation": metadata_status,
        "local_path_values_emitted": False,
        "object_uri_values_emitted": False,
        "secret_values_emitted": False,
    }


def _reconcile_materialization_metadata(
    item: MaterializationManifestItem,
    *,
    result: Any | None,
    ready: bool,
    reconcile_supabase: bool,
    materialization_store: Any | None,
) -> dict[str, object]:
    if not reconcile_supabase:
        return {"status": "skipped_disabled"}
    if materialization_store is None:
        return {"status": "skipped_store_unavailable"}
    if not ready:
        return {"status": "skipped_not_ready"}
    if not item.object_path or not item.bucket_id:
        return {"status": "skipped_source_object_unconfigured"}
    if item.destination_path is None:
        return {"status": "skipped_destination_unconfigured"}
    try:
        source_asset_object_id = materialization_store.upsert_source_asset_object(
            source_version_id=None,
            source_id=item.source_id,
            asset_role=item.role,
            bucket_id=item.bucket_id,
            object_path=item.object_path,
            object_version=item.object_version,
            content_type=item.content_type,
            byte_size=item.byte_size,
            checksum_algorithm="sha256" if item.sha256 else "md5",
            checksum_value=item.sha256 or item.md5,
            upload_status="verified",
            approval_status=item.approval_status,
            license_status=item.license_status,
            materialization_required=item.materialization_required,
            metadata={
                "manifest_item_id": item.item_id,
                "manifest_kind": item.kind,
                "asset_id": item.asset_id,
                "storage_upload_performed_by_this_run": False,
                "frontend_direct_access_allowed": False,
                "public_access_allowed": False,
                **(item.metadata or {}),
            },
            warnings=[],
        )
        materialization_store.upsert_source_asset_materialization(
            source_asset_object_id=source_asset_object_id,
            environment="sg-render",
            backend_runtime="render_backend",
            local_cache_path=str(item.destination_path),
            materialization_status="ready",
            byte_size=getattr(result, "byte_size", item.byte_size),
            checksum_algorithm="sha256" if item.sha256 else "md5",
            checksum_value=item.sha256 or item.md5,
            ready_marker="verified_runtime_file",
            verified_at=datetime.now(timezone.utc).isoformat(),
            fail_closed_reason=None,
            metadata={
                "manifest_item_id": item.item_id,
                "asset_id": item.asset_id,
                "asset_role": item.role,
                "render_disk_seed_performed": True,
                "materialized_by": "eamos_materialize_all",
                "downloaded": bool(getattr(result, "downloaded", False)),
                "copied": bool(getattr(result, "copied", False)),
            },
            warnings=[],
        )
    except Exception as exc:
        return {"status": "failed", "error_type": type(exc).__name__}
    return {"status": "reconciled"}


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise MaterializationOrchestratorError(
            "manifest_unreadable",
            "materialization manifest could not be read",
            {"error_type": type(exc).__name__},
        ) from exc
    except json.JSONDecodeError as exc:
        raise MaterializationOrchestratorError(
            "manifest_invalid_json",
            "materialization manifest is not valid JSON",
            {"error_type": type(exc).__name__},
        ) from exc
    if not isinstance(payload, dict):
        raise MaterializationOrchestratorError(
            "manifest_invalid_shape",
            "materialization manifest must be a JSON object",
        )
    return payload


def _manifest_items(manifest: dict[str, Any]) -> Iterable[dict[str, Any]]:
    items = manifest.get("items")
    if not isinstance(items, list):
        raise MaterializationOrchestratorError(
            "manifest_items_invalid",
            "materialization manifest requires an items array",
        )
    for raw in items:
        if not isinstance(raw, dict):
            raise MaterializationOrchestratorError(
                "manifest_item_invalid",
                "materialization manifest items must be objects",
            )
        yield raw


def _parse_item(raw: dict[str, Any]) -> MaterializationManifestItem:
    source_object_uri = _optional_text(raw.get("source_object_uri"))
    bucket_id = _optional_text(raw.get("bucket_id"))
    object_path = _optional_text(raw.get("object_path"))
    if source_object_uri and (not bucket_id or not object_path):
        parsed_bucket, parsed_path = _parse_supabase_uri(source_object_uri)
        bucket_id = bucket_id or parsed_bucket
        object_path = object_path or parsed_path
    return MaterializationManifestItem(
        item_id=_required_text(raw, "item_id"),
        kind=_required_text(raw, "kind"),
        source_id=_required_text(raw, "source_id"),
        asset_id=_required_text(raw, "asset_id"),
        role=_required_text(raw, "role"),
        bucket_id=bucket_id,
        object_path=object_path,
        source_object_uri=source_object_uri,
        destination_path=_optional_path(raw.get("destination_path")),
        env_var=_optional_text(raw.get("env_var")),
        byte_size=_optional_positive_int(raw.get("byte_size")),
        md5=_optional_text(raw.get("md5")),
        sha256=_optional_text(raw.get("sha256")),
        artifact_id=_optional_text(raw.get("artifact_id")),
        source_artifact_path=_optional_path(raw.get("source_artifact_path")),
        manifest_destination_path=_optional_path(raw.get("manifest_destination_path")),
        manifest_env_var=_optional_text(raw.get("manifest_env_var")),
        content_type=_optional_text(raw.get("content_type")) or "application/octet-stream",
        object_version=_optional_text(raw.get("object_version")),
        license_status=_optional_text(raw.get("license_status"))
        or "public_allowed_after_terms_review",
        approval_status=_optional_text(raw.get("approval_status")) or "approved",
        materialization_required=bool(raw.get("materialization_required", True)),
        metadata=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else None,
    )


def _parse_supabase_uri(uri: str) -> tuple[str | None, str | None]:
    if not uri.startswith("supabase://"):
        return None, None
    remainder = uri[len("supabase://") :]
    bucket, separator, object_path = remainder.partition("/")
    if not separator or not bucket or not object_path:
        return None, None
    return bucket, object_path


def _required_text(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise MaterializationOrchestratorError(
        "manifest_required_field_missing",
        "materialization manifest item is missing a required field",
        {"field": key},
    )


def _optional_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _optional_path(value: Any) -> Path | None:
    text = _optional_text(value)
    return Path(text) if text else None


def _optional_positive_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        return None
    return resolved if resolved > 0 else None
