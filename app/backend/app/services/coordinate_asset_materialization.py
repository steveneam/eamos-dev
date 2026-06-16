from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

import httpx

from app.core.config import Settings

COORDINATE_ASSET_DOWNLOAD_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class CoordinateAssetMaterializationItem:
    asset_id: str
    object_path: str
    manifest_object_path: str
    destination_path: str
    ready: bool
    status: str
    downloaded: bool
    byte_size: int | None
    expected_size_bytes: int | None
    md5_verified: bool
    sha256_verified: bool
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CoordinateAssetMaterializationResult:
    ready: bool
    enabled: bool
    source_configured: bool
    bucket_id: str
    items: tuple[CoordinateAssetMaterializationItem, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "enabled": self.enabled,
            "source_configured": self.source_configured,
            "bucket_id": self.bucket_id,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True)
class _CoordinateAssetSpec:
    asset_id: str
    object_path: str
    destination_path: Path

    @property
    def manifest_object_path(self) -> str:
        return f"{self.object_path}.manifest.json"


def materialize_coordinate_resolver_assets(
    settings: Settings,
    *,
    force: bool = False,
    http_client: httpx.Client | None = None,
) -> CoordinateAssetMaterializationResult:
    """Materialize coordinate resolver assets from private Supabase Storage.

    This helper is backend-only. It never creates signed frontend URLs and never
    includes secret values in return data.
    """

    specs = tuple(_coordinate_asset_specs(settings))
    bucket_id = settings.coordinate_resolver_asset_bucket_id
    source_configured = bool(settings.supabase_url and settings.supabase_service_role_key)
    if not source_configured:
        items = tuple(_missing_source_item(spec) for spec in specs)
        return CoordinateAssetMaterializationResult(
            ready=False,
            enabled=settings.coordinate_resolver_asset_materialization_enabled,
            source_configured=False,
            bucket_id=bucket_id,
            items=items,
        )

    owns_client = http_client is None
    client = http_client or httpx.Client(
        timeout=settings.coordinate_resolver_asset_materialization_timeout_seconds
    )
    try:
        items = tuple(
            _materialize_one(
                client,
                settings=settings,
                bucket_id=bucket_id,
                spec=spec,
                force=force,
            )
            for spec in specs
        )
    finally:
        if owns_client:
            client.close()

    return CoordinateAssetMaterializationResult(
        ready=all(item.ready for item in items),
        enabled=settings.coordinate_resolver_asset_materialization_enabled,
        source_configured=True,
        bucket_id=bucket_id,
        items=items,
    )


def _coordinate_asset_specs(settings: Settings) -> Iterable[_CoordinateAssetSpec]:
    hg38_path = (
        settings.coordinate_resolver_hg38_2bit_path
        if settings.coordinate_resolver_hg38_2bit_path is not None
        else settings.hg38_2bit_runtime_asset_path
    )
    return (
        _CoordinateAssetSpec(
            asset_id="mane_refseq_gff",
            object_path=settings.coordinate_resolver_mane_gff_object_path,
            destination_path=_resolve_runtime_path(
                settings,
                settings.coordinate_resolver_mane_gff_path,
            ),
        ),
        _CoordinateAssetSpec(
            asset_id="refseq_grch38_p14_gff",
            object_path=settings.coordinate_resolver_refseq_gff_object_path,
            destination_path=_resolve_runtime_path(
                settings,
                settings.coordinate_resolver_refseq_gff_path,
            ),
        ),
        _CoordinateAssetSpec(
            asset_id="ucsc_hg38_2bit_coordinate_runtime",
            object_path=settings.coordinate_resolver_hg38_2bit_object_path,
            destination_path=_resolve_runtime_path(settings, hg38_path),
        ),
    )


def _materialize_one(
    client: httpx.Client,
    *,
    settings: Settings,
    bucket_id: str,
    spec: _CoordinateAssetSpec,
    force: bool,
) -> CoordinateAssetMaterializationItem:
    try:
        manifest = _download_manifest(client, settings, bucket_id, spec.manifest_object_path)
    except _CoordinateAssetMaterializationError as exc:
        return _item(spec, ready=False, status=exc.status, warnings=exc.warnings)

    expected_size = _manifest_int(manifest, "byte_size")
    checksums = manifest.get("checksums")
    if not isinstance(checksums, dict):
        return _item(
            spec,
            ready=False,
            status="manifest_checksums_missing",
            expected_size_bytes=expected_size,
        )
    expected_md5 = _manifest_string(checksums, "md5")
    expected_sha256 = _manifest_string(checksums, "sha256")
    if expected_size is None or not expected_md5 or not expected_sha256:
        return _item(
            spec,
            ready=False,
            status="manifest_identity_incomplete",
            expected_size_bytes=expected_size,
        )

    existing = _inspect_destination(
        spec,
        spec.destination_path,
        expected_size=expected_size,
        expected_md5=expected_md5,
        expected_sha256=expected_sha256,
    )
    if existing.ready and not force:
        return existing
    if spec.destination_path.exists() and not force:
        return _item(
            spec,
            ready=False,
            status=f"existing_asset_{existing.status}",
            byte_size=existing.byte_size,
            expected_size_bytes=expected_size,
            warnings=("existing_coordinate_asset_failed_verification",),
        )

    spec.destination_path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=spec.destination_path.parent,
            prefix=f".{spec.destination_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            byte_size, md5_value, sha256_value = _download_asset(
                client,
                settings,
                bucket_id,
                spec.object_path,
                temp_file,
            )
    except _CoordinateAssetMaterializationError as exc:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        return _item(
            spec,
            ready=False,
            status=exc.status,
            expected_size_bytes=expected_size,
            warnings=exc.warnings,
        )

    temp_path = Path(temp_name)
    if byte_size != expected_size:
        temp_path.unlink(missing_ok=True)
        return _item(
            spec,
            ready=False,
            status="size_mismatch",
            downloaded=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
        )
    if md5_value.lower() != expected_md5.lower():
        temp_path.unlink(missing_ok=True)
        return _item(
            spec,
            ready=False,
            status="md5_mismatch",
            downloaded=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
        )
    if sha256_value.lower() != expected_sha256.lower():
        temp_path.unlink(missing_ok=True)
        return _item(
            spec,
            ready=False,
            status="sha256_mismatch",
            downloaded=True,
            byte_size=byte_size,
            expected_size_bytes=expected_size,
            md5_verified=True,
        )

    temp_path.replace(spec.destination_path)
    return _item(
        spec,
        ready=True,
        status="ready",
        downloaded=True,
        byte_size=byte_size,
        expected_size_bytes=expected_size,
        md5_verified=True,
        sha256_verified=True,
    )


def _download_manifest(
    client: httpx.Client,
    settings: Settings,
    bucket_id: str,
    object_path: str,
) -> dict[str, Any]:
    try:
        response = client.get(
            _storage_object_url(settings.supabase_url or "", bucket_id, object_path),
            headers=_storage_headers(settings),
        )
    except httpx.HTTPError:
        raise _CoordinateAssetMaterializationError("manifest_download_failed") from None
    if response.status_code == 404:
        raise _CoordinateAssetMaterializationError("manifest_missing")
    if response.status_code < 200 or response.status_code >= 300:
        raise _CoordinateAssetMaterializationError("manifest_download_failed")
    try:
        payload = response.json()
    except json.JSONDecodeError:
        raise _CoordinateAssetMaterializationError("manifest_invalid_json") from None
    if not isinstance(payload, dict):
        raise _CoordinateAssetMaterializationError("manifest_invalid_json")
    return payload


def _download_asset(
    client: httpx.Client,
    settings: Settings,
    bucket_id: str,
    object_path: str,
    destination,
) -> tuple[int, str, str]:
    md5_digest = hashlib.md5()
    sha256_digest = hashlib.sha256()
    byte_size = 0
    url = _storage_object_url(settings.supabase_url or "", bucket_id, object_path)
    try:
        with client.stream("GET", url, headers=_storage_headers(settings)) as response:
            if response.status_code == 404:
                raise _CoordinateAssetMaterializationError("source_object_missing")
            if response.status_code < 200 or response.status_code >= 300:
                raise _CoordinateAssetMaterializationError("source_object_download_failed")
            for chunk in response.iter_bytes(chunk_size=COORDINATE_ASSET_DOWNLOAD_CHUNK_BYTES):
                if not chunk:
                    continue
                destination.write(chunk)
                byte_size += len(chunk)
                md5_digest.update(chunk)
                sha256_digest.update(chunk)
    except httpx.HTTPError:
        raise _CoordinateAssetMaterializationError(
            "source_object_download_failed",
            ("private_storage_download_failed_no_public_fallback",),
        ) from None
    return byte_size, md5_digest.hexdigest(), sha256_digest.hexdigest()


def _inspect_destination(
    spec: _CoordinateAssetSpec,
    path: Path,
    *,
    expected_size: int,
    expected_md5: str,
    expected_sha256: str,
) -> CoordinateAssetMaterializationItem:
    if not path.exists():
        return _item(spec, ready=False, status="missing", expected_size_bytes=expected_size)
    if not path.is_file():
        return _item(spec, ready=False, status="not_file", expected_size_bytes=expected_size)
    byte_size = path.stat().st_size
    if byte_size != expected_size:
        return _item(
            spec,
            ready=False,
            status="size_mismatch",
            byte_size=byte_size,
            expected_size_bytes=expected_size,
        )
    md5_value, sha256_value = _hash_file(path)
    if md5_value.lower() != expected_md5.lower():
        return _item(
            spec,
            ready=False,
            status="md5_mismatch",
            byte_size=byte_size,
            expected_size_bytes=expected_size,
        )
    if sha256_value.lower() != expected_sha256.lower():
        return _item(
            spec,
            ready=False,
            status="sha256_mismatch",
            byte_size=byte_size,
            expected_size_bytes=expected_size,
            md5_verified=True,
        )
    return _item(
        spec,
        ready=True,
        status="ready",
        byte_size=byte_size,
        expected_size_bytes=expected_size,
        md5_verified=True,
        sha256_verified=True,
    )


def _hash_file(path: Path) -> tuple[str, str]:
    md5_digest = hashlib.md5()
    sha256_digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8 * 1024 * 1024), b""):
            md5_digest.update(chunk)
            sha256_digest.update(chunk)
    return md5_digest.hexdigest(), sha256_digest.hexdigest()


def _item(
    spec: _CoordinateAssetSpec,
    *,
    ready: bool,
    status: str,
    downloaded: bool = False,
    byte_size: int | None = None,
    expected_size_bytes: int | None = None,
    md5_verified: bool = False,
    sha256_verified: bool = False,
    warnings: tuple[str, ...] = (),
) -> CoordinateAssetMaterializationItem:
    return CoordinateAssetMaterializationItem(
        asset_id=spec.asset_id,
        object_path=spec.object_path,
        manifest_object_path=spec.manifest_object_path,
        destination_path=str(spec.destination_path),
        ready=ready,
        status=status,
        downloaded=downloaded,
        byte_size=byte_size,
        expected_size_bytes=expected_size_bytes,
        md5_verified=md5_verified,
        sha256_verified=sha256_verified,
        warnings=warnings,
    )


def _missing_source_item(spec: _CoordinateAssetSpec) -> CoordinateAssetMaterializationItem:
    return _item(
        spec,
        ready=False,
        status="supabase_storage_credentials_missing",
        warnings=("private_storage_credentials_required",),
    )


def _resolve_runtime_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


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


def _manifest_int(manifest: dict[str, Any], key: str) -> int | None:
    value = manifest.get(key)
    return value if isinstance(value, int) and value > 0 else None


def _manifest_string(manifest: dict[str, Any], key: str) -> str | None:
    value = manifest.get(key)
    return value if isinstance(value, str) and value else None


class _CoordinateAssetMaterializationError(RuntimeError):
    def __init__(self, status: str, warnings: tuple[str, ...] = ()) -> None:
        super().__init__(status)
        self.status = status
        self.warnings = warnings
