from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Any, Mapping

from app.core.config import Settings
from app.services.source_storage_uploads import (
    S3_MULTIPART_CHUNK_BYTES,
    S3_MULTIPART_MAX_CONCURRENCY,
    _build_s3_client,
)

RUNTIME_TREE_MANIFEST_SCHEMA_VERSION = "eamos.runtime_tree_manifest.v1"
DEFAULT_MINIMUM_FREE_AFTER_BYTES = 8 * 1024**3
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class RuntimeTreeMaterializationError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.details = dict(details or {})


@dataclass(frozen=True)
class RuntimeTreeManifestItem:
    item_id: str
    source_id: str
    asset_id: str
    role: str
    landing_set: str
    object_path: str
    destination_relpath: PurePosixPath
    byte_size: int
    sha256: str
    license_status: str
    approval_status: str
    launch_gate: str | None

    def sanitized_report(self, *, status: str, downloaded: bool) -> dict[str, object]:
        ready_statuses = {"ready", "verified_existing", "source_preflight_ready"}
        return {
            "item_id": self.item_id,
            "source_id": self.source_id,
            "asset_id": self.asset_id,
            "role": self.role,
            "landing_set": self.landing_set,
            "byte_size": self.byte_size,
            "license_status": self.license_status,
            "approval_status": self.approval_status,
            "launch_gate": self.launch_gate,
            "status": status,
            "ready": status in ready_statuses,
            "downloaded": downloaded,
            "source_size_verified": True,
            "sha256_verified": status in {"ready", "verified_existing"},
            "local_path_values_emitted": False,
            "object_path_values_emitted": False,
        }


@dataclass(frozen=True)
class RuntimeTreeExcludedObject:
    object_path: str
    byte_size: int
    sha256: str
    disposition: str


@dataclass(frozen=True)
class RuntimeTreeManifest:
    manifest_id: str
    bucket_id: str
    reference_tree_manifest_sha256: str
    item_count: int
    total_bytes: int
    source_object_count: int
    source_total_bytes: int
    items: tuple[RuntimeTreeManifestItem, ...]
    excluded_source_objects: tuple[RuntimeTreeExcludedObject, ...]


def load_runtime_tree_manifest(path: Path) -> RuntimeTreeManifest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeTreeMaterializationError("manifest_unreadable") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeTreeMaterializationError("manifest_invalid_json") from exc
    if not isinstance(payload, dict):
        raise RuntimeTreeMaterializationError("manifest_invalid_shape")
    if payload.get("schema_version") != RUNTIME_TREE_MANIFEST_SCHEMA_VERSION:
        raise RuntimeTreeMaterializationError("manifest_schema_unsupported")

    items_payload = payload.get("items")
    excluded_payload = payload.get("excluded_source_objects")
    if not isinstance(items_payload, list) or not isinstance(excluded_payload, list):
        raise RuntimeTreeMaterializationError("manifest_inventory_invalid")
    items = tuple(_parse_item(raw) for raw in items_payload)
    excluded = tuple(_parse_excluded(raw) for raw in excluded_payload)

    item_count = _required_positive_int(payload, "item_count")
    total_bytes = _required_positive_int(payload, "total_bytes")
    source_object_count = _required_positive_int(payload, "source_object_count")
    source_total_bytes = _required_positive_int(payload, "source_total_bytes")
    if item_count != len(items) or total_bytes != sum(item.byte_size for item in items):
        raise RuntimeTreeMaterializationError("manifest_landing_totals_mismatch")
    if source_object_count != len(items) + len(excluded):
        raise RuntimeTreeMaterializationError("manifest_source_count_mismatch")
    if source_total_bytes != total_bytes + sum(item.byte_size for item in excluded):
        raise RuntimeTreeMaterializationError("manifest_source_bytes_mismatch")

    item_ids = [item.item_id for item in items]
    destination_paths = [item.destination_relpath.as_posix() for item in items]
    object_paths = [item.object_path for item in items]
    excluded_paths = [item.object_path for item in excluded]
    if len(set(item_ids)) != len(item_ids):
        raise RuntimeTreeMaterializationError("manifest_item_ids_duplicate")
    if len(set(destination_paths)) != len(destination_paths):
        raise RuntimeTreeMaterializationError("manifest_destinations_duplicate")
    if len(set(object_paths + excluded_paths)) != len(object_paths) + len(excluded_paths):
        raise RuntimeTreeMaterializationError("manifest_source_paths_duplicate")
    canonical_tree_manifest = "".join(
        f"{item.sha256}  {item.byte_size}  {item.destination_relpath.as_posix()}\n"
        for item in sorted(items, key=lambda item: item.destination_relpath.as_posix())
    )
    reference_tree_manifest_sha256 = _required_sha256(payload, "reference_tree_manifest_sha256")
    if (
        sha256(canonical_tree_manifest.encode("utf-8")).hexdigest()
        != reference_tree_manifest_sha256
    ):
        raise RuntimeTreeMaterializationError("manifest_reference_tree_hash_mismatch")

    return RuntimeTreeManifest(
        manifest_id=_required_text(payload, "manifest_id"),
        bucket_id=_required_text(payload, "bucket_id"),
        reference_tree_manifest_sha256=reference_tree_manifest_sha256,
        item_count=item_count,
        total_bytes=total_bytes,
        source_object_count=source_object_count,
        source_total_bytes=source_total_bytes,
        items=items,
        excluded_source_objects=excluded,
    )


def materialize_runtime_tree(
    settings: Settings,
    *,
    manifest_path: Path,
    target_root: Path,
    resume: bool = False,
    preflight_only: bool = False,
    minimum_free_after_bytes: int = DEFAULT_MINIMUM_FREE_AFTER_BYTES,
    s3_client: Any | None = None,
    s3_client_factory: Any | None = None,
) -> dict[str, object]:
    if minimum_free_after_bytes < 0:
        raise RuntimeTreeMaterializationError("minimum_free_after_bytes_invalid")
    manifest = load_runtime_tree_manifest(manifest_path)
    root = _resolve_target_root(target_root)
    existing_item_ids = _inspect_target(root, manifest.items, resume=resume)
    missing_items = tuple(item for item in manifest.items if item.item_id not in existing_item_ids)
    missing_bytes = sum(item.byte_size for item in missing_items)
    free_before = shutil.disk_usage(root).free
    if free_before - missing_bytes < minimum_free_after_bytes:
        raise RuntimeTreeMaterializationError(
            "insufficient_free_space",
            details={
                "free_bytes": free_before,
                "missing_bytes": missing_bytes,
                "minimum_free_after_bytes": minimum_free_after_bytes,
            },
        )

    client = _resolve_s3_client(
        settings,
        s3_client=s3_client,
        s3_client_factory=s3_client_factory,
    )
    _preflight_source_objects(client, manifest)

    if preflight_only:
        return _report(
            manifest,
            status="preflight_ready",
            preflight_only=True,
            free_before=free_before,
            minimum_free_after_bytes=minimum_free_after_bytes,
            missing_bytes=missing_bytes,
            item_reports=tuple(
                item.sanitized_report(status="source_preflight_ready", downloaded=False)
                for item in manifest.items
            ),
        )

    item_reports: list[dict[str, object]] = []
    for item in manifest.items:
        if item.item_id in existing_item_ids:
            item_reports.append(item.sanitized_report(status="verified_existing", downloaded=False))
            continue
        _download_and_commit_item(client, manifest.bucket_id, root, item)
        item_reports.append(item.sanitized_report(status="ready", downloaded=True))

    _assert_complete_tree(root, manifest.items)
    return _report(
        manifest,
        status="ready",
        preflight_only=False,
        free_before=free_before,
        minimum_free_after_bytes=minimum_free_after_bytes,
        missing_bytes=missing_bytes,
        item_reports=tuple(item_reports),
    )


def _parse_item(raw: object) -> RuntimeTreeManifestItem:
    if not isinstance(raw, dict):
        raise RuntimeTreeMaterializationError("manifest_item_invalid")
    destination = _required_relative_path(raw, "destination_relpath")
    return RuntimeTreeManifestItem(
        item_id=_required_text(raw, "item_id"),
        source_id=_required_text(raw, "source_id"),
        asset_id=_required_text(raw, "asset_id"),
        role=_required_text(raw, "role"),
        landing_set=_required_text(raw, "landing_set"),
        object_path=_required_object_path(raw, "object_path"),
        destination_relpath=destination,
        byte_size=_required_positive_int(raw, "byte_size"),
        sha256=_required_sha256(raw, "sha256"),
        license_status=_required_text(raw, "license_status"),
        approval_status=_required_text(raw, "approval_status"),
        launch_gate=_optional_text(raw.get("launch_gate")),
    )


def _parse_excluded(raw: object) -> RuntimeTreeExcludedObject:
    if not isinstance(raw, dict):
        raise RuntimeTreeMaterializationError("manifest_excluded_item_invalid")
    return RuntimeTreeExcludedObject(
        object_path=_required_object_path(raw, "object_path"),
        byte_size=_required_positive_int(raw, "byte_size"),
        sha256=_required_sha256(raw, "sha256"),
        disposition=_required_text(raw, "disposition"),
    )


def _resolve_target_root(path: Path) -> Path:
    if path.is_symlink():
        raise RuntimeTreeMaterializationError("target_root_symlink_blocked")
    try:
        root = path.resolve(strict=True)
    except OSError as exc:
        raise RuntimeTreeMaterializationError("target_root_missing") from exc
    if not root.is_dir():
        raise RuntimeTreeMaterializationError("target_root_not_directory")
    return root


def _inspect_target(
    root: Path,
    items: tuple[RuntimeTreeManifestItem, ...],
    *,
    resume: bool,
) -> set[str]:
    if not resume:
        try:
            if next(root.iterdir(), None) is not None:
                raise RuntimeTreeMaterializationError("target_root_not_empty")
        except OSError as exc:
            raise RuntimeTreeMaterializationError("target_root_unreadable") from exc
        return set()

    items_by_relpath = {item.destination_relpath.as_posix(): item for item in items}
    allowed_directories = {
        parent.as_posix()
        for item in items
        for parent in item.destination_relpath.parents
        if parent.as_posix() != "."
    }
    existing_item_ids: set[str] = set()
    try:
        paths = sorted(root.rglob("*"), key=lambda path: path.as_posix())
    except OSError as exc:
        raise RuntimeTreeMaterializationError("target_root_unreadable") from exc
    for path in paths:
        relpath = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise RuntimeTreeMaterializationError("target_symlink_blocked")
        if path.is_dir():
            if relpath not in allowed_directories:
                raise RuntimeTreeMaterializationError("target_unexpected_path")
            continue
        item = items_by_relpath.get(relpath)
        if item is None or not path.is_file():
            raise RuntimeTreeMaterializationError("target_unexpected_path")
        if not _file_matches(path, byte_size=item.byte_size, expected_sha256=item.sha256):
            raise RuntimeTreeMaterializationError(
                "existing_file_mismatch", details={"item_id": item.item_id}
            )
        existing_item_ids.add(item.item_id)
    return existing_item_ids


def _resolve_s3_client(
    settings: Settings,
    *,
    s3_client: Any | None,
    s3_client_factory: Any | None,
) -> Any:
    if s3_client is not None:
        return s3_client
    if s3_client_factory is not None:
        return s3_client_factory()
    required = (
        settings.supabase_storage_s3_endpoint_url,
        settings.supabase_storage_s3_access_key_id,
        settings.supabase_storage_s3_secret_access_key,
    )
    if not all(required):
        raise RuntimeTreeMaterializationError("s3_credentials_missing")
    try:
        return _build_s3_client(
            endpoint_url=settings.supabase_storage_s3_endpoint_url,
            region=settings.supabase_storage_s3_region,
            access_key_id=settings.supabase_storage_s3_access_key_id,
            secret_access_key=settings.supabase_storage_s3_secret_access_key,
        )
    except Exception as exc:
        raise RuntimeTreeMaterializationError("s3_client_initialization_failed") from exc


def _preflight_source_objects(client: Any, manifest: RuntimeTreeManifest) -> None:
    for item in manifest.items:
        try:
            response = client.head_object(Bucket=manifest.bucket_id, Key=item.object_path)
        except Exception as exc:
            code = _s3_error_code(exc)
            status = (
                "source_object_missing"
                if code in {"404", "NoSuchKey", "NotFound"}
                else "source_head_failed"
            )
            raise RuntimeTreeMaterializationError(
                status, details={"item_id": item.item_id}
            ) from None
        size = response.get("ContentLength")
        if not isinstance(size, int) or size != item.byte_size:
            raise RuntimeTreeMaterializationError(
                "source_size_mismatch", details={"item_id": item.item_id}
            )


def _download_and_commit_item(
    client: Any,
    bucket_id: str,
    root: Path,
    item: RuntimeTreeManifestItem,
) -> None:
    destination = root.joinpath(*item.destination_relpath.parts)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.parent.resolve().is_relative_to(root):
        raise RuntimeTreeMaterializationError(
            "destination_outside_root", details={"item_id": item.item_id}
        )
    if destination.exists() or destination.is_symlink():
        raise RuntimeTreeMaterializationError(
            "destination_already_exists", details={"item_id": item.item_id}
        )

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            config = _s3_transfer_config()
            kwargs = {"Config": config} if config is not None else {}
            client.download_fileobj(bucket_id, item.object_path, temp_file, **kwargs)
            temp_file.flush()
            os.fsync(temp_file.fileno())
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise RuntimeTreeMaterializationError(
            "source_download_failed", details={"item_id": item.item_id}
        ) from None

    if temp_path is None or not _file_matches(
        temp_path, byte_size=item.byte_size, expected_sha256=item.sha256
    ):
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise RuntimeTreeMaterializationError(
            "download_identity_mismatch", details={"item_id": item.item_id}
        )
    try:
        temp_path.chmod(0o600)
        os.link(temp_path, destination, follow_symlinks=False)
    except FileExistsError:
        temp_path.unlink(missing_ok=True)
        raise RuntimeTreeMaterializationError(
            "destination_already_exists", details={"item_id": item.item_id}
        ) from None
    except OSError:
        temp_path.unlink(missing_ok=True)
        raise RuntimeTreeMaterializationError(
            "destination_commit_failed", details={"item_id": item.item_id}
        ) from None
    temp_path.unlink()


def _assert_complete_tree(root: Path, items: tuple[RuntimeTreeManifestItem, ...]) -> None:
    expected = {item.destination_relpath.as_posix(): item for item in items}
    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise RuntimeTreeMaterializationError("target_symlink_blocked")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != set(expected):
        raise RuntimeTreeMaterializationError("final_tree_shape_mismatch")
    for relpath, item in expected.items():
        path = root.joinpath(*PurePosixPath(relpath).parts)
        if not path.is_file() or path.stat().st_size != item.byte_size:
            raise RuntimeTreeMaterializationError(
                "final_tree_size_mismatch", details={"item_id": item.item_id}
            )


def _report(
    manifest: RuntimeTreeManifest,
    *,
    status: str,
    preflight_only: bool,
    free_before: int,
    minimum_free_after_bytes: int,
    missing_bytes: int,
    item_reports: tuple[dict[str, object], ...],
) -> dict[str, object]:
    return {
        "mode": "eamos_runtime_tree_materialize",
        "ready": True,
        "status": status,
        "preflight_only": preflight_only,
        "manifest_id": manifest.manifest_id,
        "reference_tree_manifest_sha256": manifest.reference_tree_manifest_sha256,
        "counts": {
            "source_object_count": manifest.source_object_count,
            "landing_item_count": manifest.item_count,
            "excluded_source_object_count": len(manifest.excluded_source_objects),
            "ready_item_count": manifest.item_count,
            "materialized_item_count": 0 if preflight_only else manifest.item_count,
        },
        "bytes": {
            "source_total_bytes": manifest.source_total_bytes,
            "landing_total_bytes": manifest.total_bytes,
            "excluded_source_bytes": manifest.source_total_bytes - manifest.total_bytes,
            "missing_before_bytes": missing_bytes,
            "free_before_bytes": free_before,
            "minimum_free_after_bytes": minimum_free_after_bytes,
            "projected_free_after_bytes": free_before - missing_bytes,
        },
        "items": list(item_reports),
        "local_path_values_emitted": False,
        "object_path_values_emitted": False,
        "secret_values_emitted": False,
    }


def _file_matches(path: Path, *, byte_size: int, expected_sha256: str) -> bool:
    try:
        if not path.is_file() or path.stat().st_size != byte_size:
            return False
        digest = sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest() == expected_sha256
    except OSError:
        return False


def _s3_transfer_config() -> Any | None:
    try:
        from boto3.s3.transfer import TransferConfig
    except ImportError:  # pragma: no cover - deployment image installs boto3
        return None
    return TransferConfig(
        multipart_threshold=S3_MULTIPART_CHUNK_BYTES,
        multipart_chunksize=S3_MULTIPART_CHUNK_BYTES,
        max_concurrency=S3_MULTIPART_MAX_CONCURRENCY,
    )


def _s3_error_code(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return None
    error = response.get("Error")
    if not isinstance(error, dict):
        return None
    code = error.get("Code")
    return str(code) if code is not None else None


def _required_text(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if isinstance(value, str) and value.strip() and "\n" not in value:
        return value.strip()
    raise RuntimeTreeMaterializationError("manifest_required_field_invalid", details={"field": key})


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() and "\n" not in value:
        return value.strip()
    raise RuntimeTreeMaterializationError("manifest_optional_field_invalid")


def _required_positive_int(raw: Mapping[str, object], key: str) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RuntimeTreeMaterializationError(
            "manifest_positive_integer_invalid", details={"field": key}
        )
    return value


def _required_sha256(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if isinstance(value, str) and _SHA256.fullmatch(value.lower()):
        return value.lower()
    raise RuntimeTreeMaterializationError("manifest_sha256_invalid", details={"field": key})


def _required_object_path(raw: Mapping[str, object], key: str) -> str:
    value = _required_text(raw, key)
    path = PurePosixPath(value)
    if value.startswith("/") or "\\" in value or ".." in path.parts:
        raise RuntimeTreeMaterializationError("manifest_object_path_invalid")
    return value


def _required_relative_path(raw: Mapping[str, object], key: str) -> PurePosixPath:
    value = _required_text(raw, key)
    path = PurePosixPath(value)
    if value.startswith("/") or "\\" in value or path.as_posix() in {"", "."} or ".." in path.parts:
        raise RuntimeTreeMaterializationError("manifest_destination_path_invalid")
    return path
