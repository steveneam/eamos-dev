from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import shutil
import tempfile
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.services.compact_coordinate_index import (
    CompactCoordinateIndex,
    clear_compact_coordinate_index_cache,
)


@dataclass(frozen=True)
class CompactCoordinateIndexMaterializationResult:
    ready: bool
    status: str
    source_kind: str
    source_configured: bool
    bucket_id: str | None
    destination_present: bool
    downloaded: bool
    copied: bool
    byte_size: int | None
    expected_size_bytes: int | None
    md5_verified: bool
    sha256_verified: bool
    schema_validated: bool
    checksum_computed: bool
    variant_count: int
    transcript_count: int
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def materialize_compact_coordinate_index(
    settings: Settings,
    *,
    source_artifact_path: Path | None = None,
    source_object_uri: str | None = None,
    force: bool = False,
    http_client: httpx.Client | None = None,
    expected_size_bytes: int | None = None,
    expected_md5: str | None = None,
    expected_sha256: str | None = None,
) -> CompactCoordinateIndexMaterializationResult:
    """Materialize the immutable compact coordinate index through an explicit action.

    This helper is deliberately not called at app startup. It writes through a
    temp file, validates checksums when identity is provided, validates the
    compact-index schema, and returns only sanitized metadata.
    """

    clear_compact_coordinate_index_cache()
    destination = _resolve_runtime_path(settings, settings.coordinate_resolver_compact_index_path)
    resolved_object_uri = source_object_uri or settings.coordinate_resolver_compact_index_object_uri
    if source_artifact_path is not None and resolved_object_uri:
        return _result(
            "multiple_sources_configured",
            source_kind="mixed",
            source_configured=True,
            warnings=("provide_local_artifact_or_storage_object_not_both",),
        )

    existing = _inspect_candidate(
        destination,
        expected_size=expected_size_bytes,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )
    if existing.ready and not force:
        return existing
    if destination.exists() and not force:
        return _result(
            f"existing_compact_index_{existing.status}",
            source_kind=_source_kind(source_artifact_path, resolved_object_uri),
            source_configured=bool(source_artifact_path or resolved_object_uri),
            destination_present=True,
            byte_size=existing.byte_size,
            expected_size_bytes=expected_size_bytes,
            warnings=("existing_compact_index_failed_verification",),
        )

    if source_artifact_path is not None:
        return _materialize_from_local_path(
            settings,
            source_artifact_path=source_artifact_path,
            destination=destination,
            expected_size_bytes=expected_size_bytes,
            expected_md5=expected_md5,
            expected_sha256=expected_sha256,
        )

    if resolved_object_uri:
        return _materialize_from_private_storage(
            settings,
            source_object_uri=resolved_object_uri,
            destination=destination,
            http_client=http_client,
            expected_size_bytes=expected_size_bytes,
            expected_md5=expected_md5,
            expected_sha256=expected_sha256,
        )

    return _result("source_unconfigured", source_kind="none", source_configured=False)


def _materialize_from_local_path(
    settings: Settings,
    *,
    source_artifact_path: Path,
    destination: Path,
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> CompactCoordinateIndexMaterializationResult:
    source = _resolve_operator_path(source_artifact_path)
    if not source.exists():
        return _result("source_artifact_missing", source_kind="local_file", source_configured=True)
    if not source.is_file():
        return _result("source_artifact_not_file", source_kind="local_file", source_configured=True)

    identity = _identity_from_sidecar_or_args(
        source,
        expected_size_bytes=expected_size_bytes,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )
    if identity.status != "ready":
        return _result(
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
        return _result(
            "local_artifact_copy_failed",
            source_kind="local_file",
            source_configured=True,
            warnings=("compact_index_destination_not_modified",),
        )

    return _verify_and_replace(
        settings,
        temp_path=Path(temp_name),
        destination=destination,
        source_kind="local_file",
        copied=True,
        expected_size=identity.expected_size_bytes,
        expected_md5=identity.expected_md5,
        expected_sha256=identity.expected_sha256,
        warnings=identity.warnings,
    )


def _materialize_from_private_storage(
    settings: Settings,
    *,
    source_object_uri: str,
    destination: Path,
    http_client: httpx.Client | None,
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> CompactCoordinateIndexMaterializationResult:
    try:
        bucket_id, object_path = _parse_supabase_object_uri(source_object_uri)
    except ValueError:
        return _result(
            "source_object_uri_invalid",
            source_kind="supabase_private_storage",
            source_configured=True,
        )

    if not settings.supabase_url or not settings.supabase_service_role_key:
        return _result(
            "supabase_storage_credentials_missing",
            source_kind="supabase_private_storage",
            source_configured=True,
            bucket_id=bucket_id,
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(
        timeout=settings.coordinate_resolver_compact_index_materialize_timeout_seconds
    )
    try:
        identity = _identity_from_storage_manifest_or_args(
            client,
            settings=settings,
            bucket_id=bucket_id,
            object_path=object_path,
            expected_size_bytes=expected_size_bytes,
            expected_md5=expected_md5,
            expected_sha256=expected_sha256,
        )
        if identity.status != "ready":
            return _result(
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
            return _result(
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
        settings,
        temp_path=Path(temp_name),
        destination=destination,
        source_kind="supabase_private_storage",
        bucket_id=bucket_id,
        downloaded=True,
        expected_size=identity.expected_size_bytes,
        expected_md5=identity.expected_md5,
        expected_sha256=identity.expected_sha256,
        warnings=identity.warnings,
    )


@dataclass(frozen=True)
class _ExpectedIdentity:
    status: str
    expected_size_bytes: int | None = None
    expected_md5: str | None = None
    expected_sha256: str | None = None
    warnings: tuple[str, ...] = ()


def _identity_from_sidecar_or_args(
    source: Path,
    *,
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> _ExpectedIdentity:
    if expected_size_bytes or expected_md5 or expected_sha256:
        return _identity_from_explicit_args(
            expected_size_bytes=expected_size_bytes,
            expected_md5=expected_md5,
            expected_sha256=expected_sha256,
        )
    manifest_path = source.with_suffix(source.suffix + ".manifest.json")
    if not manifest_path.is_file():
        return _ExpectedIdentity(
            status="ready",
            warnings=("local_artifact_identity_manifest_missing",),
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _ExpectedIdentity(status="manifest_invalid_json")
    if not isinstance(manifest, dict):
        return _ExpectedIdentity(status="manifest_invalid_json")
    return _identity_from_manifest(manifest)


def _identity_from_storage_manifest_or_args(
    client: httpx.Client,
    *,
    settings: Settings,
    bucket_id: str,
    object_path: str,
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> _ExpectedIdentity:
    if expected_size_bytes and (expected_md5 or expected_sha256):
        return _identity_from_explicit_args(
            expected_size_bytes=expected_size_bytes,
            expected_md5=expected_md5,
            expected_sha256=expected_sha256,
        )
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
    return _identity_from_manifest(manifest)


def _identity_from_manifest(manifest: dict[str, Any]) -> _ExpectedIdentity:
    checksums = manifest.get("checksums") if isinstance(manifest.get("checksums"), dict) else {}
    expected_size = _optional_positive_int(
        manifest.get("byte_size", manifest.get("actual_size_bytes"))
    )
    expected_md5 = _normalize_md5(_optional_string(manifest.get("md5") or checksums.get("md5")))
    expected_sha256 = _normalize_sha256(
        _optional_string(manifest.get("sha256") or checksums.get("sha256"))
    )
    if expected_size is None or not (expected_md5 or expected_sha256):
        return _ExpectedIdentity(
            status="manifest_identity_incomplete",
            expected_size_bytes=expected_size,
        )
    return _ExpectedIdentity(
        status="ready",
        expected_size_bytes=expected_size,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )


def _identity_from_explicit_args(
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
        return _ExpectedIdentity(
            status="expected_identity_invalid",
            expected_size_bytes=expected_size_bytes,
        )
    if expected_sha256 is not None and normalized_sha256 is None:
        return _ExpectedIdentity(
            status="expected_identity_invalid",
            expected_size_bytes=expected_size_bytes,
            expected_md5=normalized_md5,
        )
    return _ExpectedIdentity(
        status="ready",
        expected_size_bytes=expected_size_bytes,
        expected_md5=normalized_md5,
        expected_sha256=normalized_sha256,
    )


def _download_storage_object(
    client: httpx.Client,
    *,
    settings: Settings,
    bucket_id: str,
    object_path: str,
    destination,
) -> None:
    url = _storage_object_url(settings.supabase_url or "", bucket_id, object_path)
    try:
        with client.stream("GET", url, headers=_storage_headers(settings)) as response:
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


def _verify_and_replace(
    settings: Settings,
    *,
    temp_path: Path,
    destination: Path,
    source_kind: str,
    bucket_id: str | None = None,
    downloaded: bool = False,
    copied: bool = False,
    expected_size: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
    warnings: tuple[str, ...] = (),
) -> CompactCoordinateIndexMaterializationResult:
    candidate = _inspect_candidate(
        temp_path,
        expected_size=expected_size,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )
    if not candidate.ready:
        temp_path.unlink(missing_ok=True)
        return _result(
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
            warnings=warnings + ("compact_index_destination_not_modified",),
        )

    temp_path.replace(destination)
    clear_compact_coordinate_index_cache()
    destination_inspection = CompactCoordinateIndex(destination).inspection(verify_checksum=True)
    return _result(
        "ready",
        source_kind=source_kind,
        source_configured=True,
        bucket_id=bucket_id,
        destination_present=True,
        downloaded=downloaded,
        copied=copied,
        byte_size=candidate.byte_size,
        expected_size_bytes=expected_size,
        md5_verified=candidate.md5_verified,
        sha256_verified=candidate.sha256_verified,
        schema_validated=True,
        checksum_computed=True,
        variant_count=destination_inspection.variant_count,
        transcript_count=destination_inspection.transcript_count,
        warnings=warnings,
    )


def _inspect_candidate(
    path: Path,
    *,
    expected_size: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> CompactCoordinateIndexMaterializationResult:
    if not path.exists():
        return _result("missing", source_kind="existing", source_configured=False)
    if not path.is_file():
        return _result(
            "not_file",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
        )
    byte_size = path.stat().st_size
    if expected_size is not None and byte_size != expected_size:
        return _result(
            "size_mismatch",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
            checksum_computed=False,
        )

    md5_value, sha256_value = _hash_file(path)
    expected_md5 = _normalize_md5(expected_md5)
    expected_sha256 = _normalize_sha256(expected_sha256)
    if expected_md5 and md5_value.lower() != expected_md5:
        return _result(
            "md5_mismatch",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
            checksum_computed=True,
        )
    if expected_sha256 and sha256_value.lower() != expected_sha256:
        return _result(
            "sha256_mismatch",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
            md5_verified=bool(expected_md5),
            checksum_computed=True,
        )

    clear_compact_coordinate_index_cache()
    inspection = CompactCoordinateIndex(path).inspection(verify_checksum=True)
    if not inspection.ready:
        return _result(
            "schema_validation_failed",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
            md5_verified=bool(expected_md5),
            sha256_verified=bool(expected_sha256),
            checksum_computed=True,
            warnings=(f"compact_index_reader_status:{inspection.status}",),
        )
    return _result(
        "ready",
        source_kind="existing",
        source_configured=False,
        destination_present=True,
        byte_size=byte_size,
        expected_size_bytes=expected_size,
        md5_verified=bool(expected_md5),
        sha256_verified=bool(expected_sha256),
        schema_validated=True,
        checksum_computed=True,
        variant_count=inspection.variant_count,
        transcript_count=inspection.transcript_count,
    )


def _hash_file(path: Path) -> tuple[str, str]:
    md5_digest = hashlib.md5()
    sha256_digest = hashlib.sha256()
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
    return {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }


def _resolve_runtime_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _resolve_operator_path(path: Path) -> Path:
    return path if path.is_absolute() else Path.cwd() / path


def _source_kind(source_artifact_path: Path | None, source_object_uri: str | None) -> str:
    if source_artifact_path is not None:
        return "local_file"
    if source_object_uri:
        return "supabase_private_storage"
    return "none"


def _optional_positive_int(value: object) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    return None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


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


def _result(
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
    variant_count: int = 0,
    transcript_count: int = 0,
    warnings: tuple[str, ...] = (),
) -> CompactCoordinateIndexMaterializationResult:
    return CompactCoordinateIndexMaterializationResult(
        ready=status == "ready",
        status=status,
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
        variant_count=variant_count,
        transcript_count=transcript_count,
        warnings=warnings,
    )


class _StorageDownloadError(RuntimeError):
    def __init__(self, status: str, warnings: tuple[str, ...] = ()) -> None:
        super().__init__(status)
        self.status = status
        self.warnings = warnings
