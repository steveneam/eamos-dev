from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.services.local_evidence_runtime_assets import (
    LOCAL_EVIDENCE_RUNTIME_SOURCE_SPECS,
    LocalEvidenceRuntimeAssetRole,
    LocalEvidenceRuntimeSourceSpec,
)
from app.services.source_storage_uploads import (
    S3_CONNECT_TIMEOUT_SECONDS,
    S3_MULTIPART_CHUNK_BYTES,
    S3_MULTIPART_MAX_CONCURRENCY,
    S3_READ_TIMEOUT_SECONDS,
    S3_RETRY_ATTEMPTS,
    SourceStorageUploadMode,
)


@dataclass(frozen=True)
class LocalEvidenceRuntimeSeedDefinition:
    item_id: str
    source_id: str
    adapter: str
    role: str
    path_setting: str
    expected_format: str


@dataclass(frozen=True)
class LocalEvidenceRuntimeSeedResult:
    ready: bool
    status: str
    item_id: str
    source_id: str
    role: str
    path_setting: str
    expected_format: str
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
    checksum_computed: bool = False
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
    expected_size_bytes: int | None = None
    expected_md5: str | None = None
    expected_sha256: str | None = None
    warnings: tuple[str, ...] = ()


class _StorageDownloadError(RuntimeError):
    def __init__(self, status: str, warnings: tuple[str, ...] = ()) -> None:
        super().__init__(status)
        self.status = status
        self.warnings = warnings


def local_evidence_runtime_seed_roles() -> tuple[str, ...]:
    return tuple(definition.role for definition in _seed_definitions())


def local_evidence_runtime_seed_definition_for_role(
    role: str,
) -> LocalEvidenceRuntimeSeedDefinition:
    for definition in _seed_definitions():
        if definition.role == role:
            return definition
    raise ValueError(f"unsupported local evidence runtime role: {role}")


def materialize_local_evidence_runtime_asset(
    settings: Settings,
    *,
    role: str,
    source_artifact_path: Path | None = None,
    source_object_uri: str | None = None,
    destination_path: Path | None = None,
    force: bool = False,
    expected_size_bytes: int | None = None,
    expected_md5: str | None = None,
    expected_sha256: str | None = None,
    download_mode: SourceStorageUploadMode | str = SourceStorageUploadMode.REST,
    http_client: httpx.Client | None = None,
    s3_endpoint_url: str | None = None,
    s3_region: str | None = None,
    s3_access_key_id: str | None = None,
    s3_secret_access_key: str | None = None,
    s3_client: Any | None = None,
    s3_client_factory: Any | None = None,
) -> LocalEvidenceRuntimeSeedResult:
    """Seed one local-evidence runtime asset through an explicit off-startup action.

    This is intended for Render Shell or another approved operator context. It
    writes through a temp file, verifies size/checksum identity, and never
    returns local paths, Storage object paths/URIs, or secrets.
    """

    definition = local_evidence_runtime_seed_definition_for_role(role)
    destination = _resolve_backend_path(
        settings,
        destination_path or Path(getattr(settings, definition.path_setting)),
    )
    if source_artifact_path is not None and source_object_uri:
        return _result(
            definition,
            "multiple_sources_configured",
            source_kind="mixed",
            source_configured=True,
            warnings=("provide_local_artifact_or_storage_object_not_both",),
        )

    resolved_download_mode = SourceStorageUploadMode(download_mode)
    identity, bucket_id = _resolve_identity(
        settings,
        definition=definition,
        source_artifact_path=source_artifact_path,
        source_object_uri=source_object_uri,
        expected_size_bytes=expected_size_bytes,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
        download_mode=resolved_download_mode,
        http_client=http_client,
        s3_endpoint_url=s3_endpoint_url,
        s3_region=s3_region,
        s3_access_key_id=s3_access_key_id,
        s3_secret_access_key=s3_secret_access_key,
        s3_client=s3_client,
        s3_client_factory=s3_client_factory,
    )
    source_kind = _source_kind(source_artifact_path, source_object_uri, resolved_download_mode)
    source_configured = bool(source_artifact_path or source_object_uri)
    if identity.status == "source_unconfigured":
        return _result(
            definition,
            "source_unconfigured",
            source_kind="none",
            source_configured=False,
        )
    if identity.status != "ready":
        return _result(
            definition,
            identity.status,
            source_kind=source_kind,
            source_configured=source_configured,
            bucket_id=bucket_id,
            expected_size_bytes=identity.expected_size_bytes,
            warnings=identity.warnings,
        )

    existing = _inspect_candidate(
        definition,
        destination,
        expected_size=identity.expected_size_bytes,
        expected_md5=identity.expected_md5,
        expected_sha256=identity.expected_sha256,
    )
    if existing.ready and not force:
        return existing
    if destination.exists() and not force:
        return _result(
            definition,
            f"existing_runtime_asset_{existing.status}",
            source_kind=source_kind,
            source_configured=source_configured,
            bucket_id=bucket_id,
            destination_present=True,
            byte_size=existing.byte_size,
            expected_size_bytes=identity.expected_size_bytes,
            warnings=("existing_runtime_asset_failed_verification",),
        )
    if source_artifact_path is not None:
        return _materialize_from_local_path(
            settings,
            definition=definition,
            source_artifact_path=source_artifact_path,
            destination=destination,
            identity=identity,
        )
    if source_object_uri:
        return _materialize_from_private_storage(
            settings,
            definition=definition,
            source_object_uri=source_object_uri,
            destination=destination,
            identity=identity,
            download_mode=resolved_download_mode,
            http_client=http_client,
            s3_endpoint_url=s3_endpoint_url,
            s3_region=s3_region,
            s3_access_key_id=s3_access_key_id,
            s3_secret_access_key=s3_secret_access_key,
            s3_client=s3_client,
            s3_client_factory=s3_client_factory,
        )
    return existing


def _seed_definitions() -> tuple[LocalEvidenceRuntimeSeedDefinition, ...]:
    definitions: list[LocalEvidenceRuntimeSeedDefinition] = []
    for source_spec in LOCAL_EVIDENCE_RUNTIME_SOURCE_SPECS:
        for role in source_spec.roles:
            definitions.append(_definition_from_spec(source_spec, role))
    return tuple(definitions)


def _definition_from_spec(
    source_spec: LocalEvidenceRuntimeSourceSpec,
    role: LocalEvidenceRuntimeAssetRole,
) -> LocalEvidenceRuntimeSeedDefinition:
    return LocalEvidenceRuntimeSeedDefinition(
        item_id=source_spec.item_id,
        source_id=source_spec.source_id,
        adapter=source_spec.adapter,
        role=role.role,
        path_setting=role.path_setting,
        expected_format=role.expected_format,
    )


def _resolve_identity(
    settings: Settings,
    *,
    definition: LocalEvidenceRuntimeSeedDefinition,
    source_artifact_path: Path | None,
    source_object_uri: str | None,
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
    download_mode: SourceStorageUploadMode,
    http_client: httpx.Client | None,
    s3_endpoint_url: str | None,
    s3_region: str | None,
    s3_access_key_id: str | None,
    s3_secret_access_key: str | None,
    s3_client: Any | None,
    s3_client_factory: Any | None,
) -> tuple[_ExpectedIdentity, str | None]:
    if _has_explicit_identity(expected_size_bytes, expected_md5, expected_sha256):
        return (
            _identity_from_explicit_args(
                expected_size_bytes=expected_size_bytes,
                expected_md5=expected_md5,
                expected_sha256=expected_sha256,
            ),
            _bucket_id_from_uri(source_object_uri),
        )
    if source_artifact_path is not None:
        source = _resolve_operator_path(source_artifact_path)
        if not source.exists():
            return (_ExpectedIdentity(status="source_artifact_missing"), None)
        if not source.is_file():
            return (_ExpectedIdentity(status="source_artifact_not_file"), None)
        return (_identity_from_local_manifest(definition, source), None)
    if source_object_uri:
        try:
            bucket_id, object_path = _parse_supabase_object_uri(source_object_uri)
        except ValueError:
            return (_ExpectedIdentity(status="source_object_uri_invalid"), None)
        if download_mode is SourceStorageUploadMode.S3_MULTIPART:
            return (
                _identity_from_storage_manifest_s3(
                    definition,
                    bucket_id=bucket_id,
                    object_path=object_path,
                    s3_endpoint_url=s3_endpoint_url,
                    s3_region=s3_region,
                    s3_access_key_id=s3_access_key_id,
                    s3_secret_access_key=s3_secret_access_key,
                    s3_client=s3_client,
                    s3_client_factory=s3_client_factory,
                ),
                bucket_id,
            )
        return (
            _identity_from_storage_manifest_rest(
                definition,
                settings=settings,
                bucket_id=bucket_id,
                object_path=object_path,
                http_client=http_client,
            ),
            bucket_id,
        )
    return (_ExpectedIdentity(status="source_unconfigured"), None)


def _identity_from_local_manifest(
    definition: LocalEvidenceRuntimeSeedDefinition,
    source: Path,
) -> _ExpectedIdentity:
    manifest_path = source.with_suffix(source.suffix + ".manifest.json")
    if not manifest_path.is_file():
        return _ExpectedIdentity(status="manifest_missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _ExpectedIdentity(status="manifest_invalid_json")
    if not isinstance(manifest, dict):
        return _ExpectedIdentity(status="manifest_invalid_json")
    return _identity_from_manifest(definition, manifest)


def _identity_from_storage_manifest_rest(
    definition: LocalEvidenceRuntimeSeedDefinition,
    *,
    settings: Settings,
    bucket_id: str,
    object_path: str,
    http_client: httpx.Client | None,
) -> _ExpectedIdentity:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return _ExpectedIdentity(status="supabase_storage_credentials_missing")
    owns_client = http_client is None
    client = http_client or httpx.Client(
        timeout=settings.local_evidence_runtime_seed_timeout_seconds
    )
    try:
        try:
            response = client.get(
                _storage_object_url(
                    settings.supabase_url or "",
                    bucket_id,
                    f"{object_path}.manifest.json",
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
    finally:
        if owns_client:
            client.close()


def _identity_from_storage_manifest_s3(
    definition: LocalEvidenceRuntimeSeedDefinition,
    *,
    bucket_id: str,
    object_path: str,
    s3_endpoint_url: str | None,
    s3_region: str | None,
    s3_access_key_id: str | None,
    s3_secret_access_key: str | None,
    s3_client: Any | None,
    s3_client_factory: Any | None,
) -> _ExpectedIdentity:
    has_injected_client = s3_client is not None or s3_client_factory is not None
    if not has_injected_client and (
        not s3_endpoint_url or not s3_access_key_id or not s3_secret_access_key
    ):
        return _ExpectedIdentity(status="supabase_storage_s3_credentials_missing")
    try:
        client = (
            s3_client
            if s3_client is not None
            else (
                s3_client_factory()
                if s3_client_factory is not None
                else _build_s3_client(
                    endpoint_url=s3_endpoint_url,
                    region=s3_region,
                    access_key_id=s3_access_key_id,
                    secret_access_key=s3_secret_access_key,
                )
            )
        )
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
    definition: LocalEvidenceRuntimeSeedDefinition,
    manifest: dict[str, Any],
) -> _ExpectedIdentity:
    if manifest.get("source_id") not in (None, definition.source_id):
        return _ExpectedIdentity(status="manifest_source_mismatch")
    if manifest.get("role") not in (None, definition.role):
        return _ExpectedIdentity(status="manifest_role_mismatch")
    checksums = manifest.get("checksums") if isinstance(manifest.get("checksums"), dict) else {}
    expected_size = _optional_positive_int(
        manifest.get("byte_size", manifest.get("actual_size_bytes"))
    )
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
    if expected_size_bytes is None or expected_size_bytes <= 0:
        return _ExpectedIdentity(status="expected_identity_invalid")
    if expected_md5 is not None and normalized_md5 is None:
        return _ExpectedIdentity(status="expected_identity_invalid")
    if expected_sha256 is not None and normalized_sha256 is None:
        return _ExpectedIdentity(status="expected_identity_invalid")
    if not normalized_md5 and not normalized_sha256:
        return _ExpectedIdentity(status="expected_identity_invalid")
    return _ExpectedIdentity(
        status="ready",
        expected_size_bytes=expected_size_bytes,
        expected_md5=normalized_md5,
        expected_sha256=normalized_sha256,
    )


def _materialize_from_local_path(
    settings: Settings,
    *,
    definition: LocalEvidenceRuntimeSeedDefinition,
    source_artifact_path: Path,
    destination: Path,
    identity: _ExpectedIdentity,
) -> LocalEvidenceRuntimeSeedResult:
    source = _resolve_operator_path(source_artifact_path)
    if not source.exists():
        return _result(
            definition,
            "source_artifact_missing",
            source_kind="local_file",
            source_configured=True,
            expected_size_bytes=identity.expected_size_bytes,
        )
    if not source.is_file():
        return _result(
            definition,
            "source_artifact_not_file",
            source_kind="local_file",
            source_configured=True,
            expected_size_bytes=identity.expected_size_bytes,
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
            definition,
            "local_artifact_copy_failed",
            source_kind="local_file",
            source_configured=True,
            expected_size_bytes=identity.expected_size_bytes,
            warnings=("runtime_destination_not_modified",),
        )
    return _verify_and_replace(
        settings,
        definition=definition,
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
    definition: LocalEvidenceRuntimeSeedDefinition,
    source_object_uri: str,
    destination: Path,
    identity: _ExpectedIdentity,
    download_mode: SourceStorageUploadMode,
    http_client: httpx.Client | None,
    s3_endpoint_url: str | None,
    s3_region: str | None,
    s3_access_key_id: str | None,
    s3_secret_access_key: str | None,
    s3_client: Any | None,
    s3_client_factory: Any | None,
) -> LocalEvidenceRuntimeSeedResult:
    try:
        bucket_id, object_path = _parse_supabase_object_uri(source_object_uri)
    except ValueError:
        return _result(
            definition,
            "source_object_uri_invalid",
            source_kind=_source_kind(None, source_object_uri, download_mode),
            source_configured=True,
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
            if download_mode is SourceStorageUploadMode.S3_MULTIPART:
                _download_storage_object_s3(
                    bucket_id=bucket_id,
                    object_path=object_path,
                    destination=temp_file,
                    s3_endpoint_url=s3_endpoint_url,
                    s3_region=s3_region,
                    s3_access_key_id=s3_access_key_id,
                    s3_secret_access_key=s3_secret_access_key,
                    s3_client=s3_client,
                    s3_client_factory=s3_client_factory,
                )
            else:
                _download_storage_object_rest(
                    settings,
                    bucket_id=bucket_id,
                    object_path=object_path,
                    destination=temp_file,
                    http_client=http_client,
                )
    except _StorageDownloadError as exc:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        return _result(
            definition,
            exc.status,
            source_kind=_source_kind(None, source_object_uri, download_mode),
            source_configured=True,
            bucket_id=bucket_id,
            expected_size_bytes=identity.expected_size_bytes,
            warnings=exc.warnings,
        )
    return _verify_and_replace(
        settings,
        definition=definition,
        temp_path=Path(temp_name),
        destination=destination,
        source_kind=_source_kind(None, source_object_uri, download_mode),
        bucket_id=bucket_id,
        downloaded=True,
        expected_size=identity.expected_size_bytes,
        expected_md5=identity.expected_md5,
        expected_sha256=identity.expected_sha256,
        warnings=identity.warnings,
    )


def _download_storage_object_rest(
    settings: Settings,
    *,
    bucket_id: str,
    object_path: str,
    destination,
    http_client: httpx.Client | None,
) -> None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise _StorageDownloadError("supabase_storage_credentials_missing")
    owns_client = http_client is None
    client = http_client or httpx.Client(
        timeout=settings.local_evidence_runtime_seed_timeout_seconds
    )
    try:
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
                for chunk in response.iter_bytes(chunk_size=8 * 1024 * 1024):
                    if chunk:
                        destination.write(chunk)
        except httpx.HTTPError:
            raise _StorageDownloadError(
                "source_object_download_failed",
                ("private_storage_download_failed_no_public_fallback",),
            ) from None
    finally:
        if owns_client:
            client.close()


def _download_storage_object_s3(
    *,
    bucket_id: str,
    object_path: str,
    destination,
    s3_endpoint_url: str | None,
    s3_region: str | None,
    s3_access_key_id: str | None,
    s3_secret_access_key: str | None,
    s3_client: Any | None,
    s3_client_factory: Any | None,
) -> None:
    has_injected_client = s3_client is not None or s3_client_factory is not None
    if not has_injected_client and (
        not s3_endpoint_url or not s3_access_key_id or not s3_secret_access_key
    ):
        raise _StorageDownloadError("supabase_storage_s3_credentials_missing")
    try:
        client = (
            s3_client
            if s3_client is not None
            else (
                s3_client_factory()
                if s3_client_factory is not None
                else _build_s3_client(
                    endpoint_url=s3_endpoint_url,
                    region=s3_region,
                    access_key_id=s3_access_key_id,
                    secret_access_key=s3_secret_access_key,
                )
            )
        )
        config = _s3_transfer_config()
        kwargs = {"Config": config} if config is not None else {}
        client.download_fileobj(bucket_id, object_path, destination, **kwargs)
    except Exception as exc:
        if _s3_error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
            raise _StorageDownloadError("source_object_missing") from None
        raise _StorageDownloadError(
            "source_object_download_failed",
            ("private_storage_download_failed_no_public_fallback",),
        ) from None


def _verify_and_replace(
    _settings: Settings,
    *,
    definition: LocalEvidenceRuntimeSeedDefinition,
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
) -> LocalEvidenceRuntimeSeedResult:
    candidate = _inspect_candidate(
        definition,
        temp_path,
        expected_size=expected_size,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )
    if not candidate.ready:
        temp_path.unlink(missing_ok=True)
        return _result(
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
            checksum_computed=candidate.checksum_computed,
            warnings=warnings + ("runtime_destination_not_modified",),
        )
    temp_path.replace(destination)
    return _result(
        definition,
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
        checksum_computed=True,
        warnings=warnings,
    )


def _inspect_candidate(
    definition: LocalEvidenceRuntimeSeedDefinition,
    path: Path,
    *,
    expected_size: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> LocalEvidenceRuntimeSeedResult:
    if not path.exists():
        return _result(
            definition,
            "missing",
            source_kind="existing",
            source_configured=False,
            expected_size_bytes=expected_size,
        )
    if not path.is_file():
        return _result(
            definition,
            "not_file",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
            expected_size_bytes=expected_size,
        )
    byte_size = path.stat().st_size
    if expected_size is not None and byte_size != expected_size:
        return _result(
            definition,
            "size_mismatch",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
        )

    expected_md5 = _normalize_md5(expected_md5)
    expected_sha256 = _normalize_sha256(expected_sha256)
    md5_value, sha256_value = _hash_file(path)
    if expected_md5 and md5_value.lower() != expected_md5:
        return _result(
            definition,
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
            definition,
            "sha256_mismatch",
            source_kind="existing",
            source_configured=False,
            destination_present=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
            md5_verified=bool(expected_md5),
            checksum_computed=True,
        )
    return _result(
        definition,
        "ready",
        source_kind="existing",
        source_configured=False,
        destination_present=True,
        byte_size=byte_size,
        expected_size_bytes=expected_size,
        md5_verified=bool(expected_md5),
        sha256_verified=bool(expected_sha256),
        checksum_computed=True,
    )


def _hash_file(path: Path) -> tuple[str, str]:
    md5_digest = hashlib.md5()
    sha256_digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8 * 1024 * 1024), b""):
            md5_digest.update(chunk)
            sha256_digest.update(chunk)
    return md5_digest.hexdigest(), sha256_digest.hexdigest()


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
        raise RuntimeError("boto3 is required for s3 local evidence runtime seed") from exc
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


def _parse_supabase_object_uri(value: str) -> tuple[str, str]:
    prefix = "supabase://"
    if not value.startswith(prefix):
        raise ValueError("source object URI must use supabase://bucket/object-path")
    remainder = value[len(prefix) :]
    bucket_id, separator, object_path = remainder.partition("/")
    if not bucket_id or not separator or not object_path:
        raise ValueError("source object URI must include bucket and object path")
    return bucket_id, object_path


def _bucket_id_from_uri(value: str | None) -> str | None:
    if not value:
        return None
    try:
        bucket_id, _ = _parse_supabase_object_uri(value)
    except ValueError:
        return None
    return bucket_id


def _storage_object_url(supabase_url: str, bucket_id: str, object_path: str) -> str:
    encoded_path = "/".join(quote(part, safe="") for part in object_path.split("/"))
    return (
        f"{supabase_url.rstrip('/')}/storage/v1/object/"
        f"{quote(bucket_id, safe='')}/{encoded_path}"
    )


def _storage_headers(settings: Settings) -> dict[str, str]:
    service_role_key = settings.supabase_service_role_key or ""
    return {"apikey": service_role_key, "Authorization": f"Bearer {service_role_key}"}


def _source_kind(
    source_artifact_path: Path | None,
    source_object_uri: str | None,
    download_mode: SourceStorageUploadMode,
) -> str:
    if source_artifact_path is not None:
        return "local_file"
    if source_object_uri and download_mode is SourceStorageUploadMode.S3_MULTIPART:
        return "supabase_private_storage_s3"
    if source_object_uri:
        return "supabase_private_storage_rest"
    return "none"


def _resolve_backend_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _resolve_operator_path(path: Path) -> Path:
    return path if path.is_absolute() else Path.cwd() / path


def _has_explicit_identity(
    expected_size_bytes: int | None,
    expected_md5: str | None,
    expected_sha256: str | None,
) -> bool:
    return (
        expected_size_bytes is not None or expected_md5 is not None or expected_sha256 is not None
    )


def _optional_positive_int(value: object) -> int | None:
    return value if isinstance(value, int) and value > 0 else None


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


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
    definition: LocalEvidenceRuntimeSeedDefinition,
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
    checksum_computed: bool = False,
    warnings: tuple[str, ...] = (),
) -> LocalEvidenceRuntimeSeedResult:
    return LocalEvidenceRuntimeSeedResult(
        ready=status == "ready",
        status=status,
        item_id=definition.item_id,
        source_id=definition.source_id,
        role=definition.role,
        path_setting=definition.path_setting,
        expected_format=definition.expected_format,
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
        checksum_computed=checksum_computed,
        warnings=warnings,
    )
