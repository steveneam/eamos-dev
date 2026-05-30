from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.data_sources.protein_assets import PROTEIN_ANNOTATION_ASSETS, ProteinAssetSpec
from app.services.protein_annotation import resolve_protein_runtime_path


@dataclass(frozen=True)
class PfamMaterializationResult:
    ready: bool
    status: str
    source_object_configured: bool
    bucket_id: str | None
    destination_present: bool
    downloaded: bool
    byte_size: int | None
    expected_size_bytes: int
    md5_verified: bool
    sha256_verified: bool
    warnings: tuple[str, ...] = ()


def materialize_pfam_hmm_gz_from_private_storage(
    settings: Settings,
    *,
    source_object_uri: str | None = None,
    force: bool = False,
    http_client: httpx.Client | None = None,
    expected_size_bytes: int | None = None,
    expected_md5: str | None = None,
    expected_sha256: str | None = None,
) -> PfamMaterializationResult:
    """Materialize the staged Pfam-A.hmm.gz asset from private Supabase Storage.

    This is a backend-only asset materialization helper. It never creates a
    bucket, never returns signed URLs, and intentionally keeps local filesystem
    paths and service-role credentials out of its result.
    """

    asset = _pfam_asset()
    expected_size = expected_size_bytes or asset.expected_size_bytes
    expected_md5_value = (expected_md5 or asset.expected_md5).lower()
    expected_sha256_value = (expected_sha256 or asset.expected_sha256).lower()
    destination = resolve_protein_runtime_path(
        settings,
        settings.protein_annotation_pfam_hmm_gz_path,
    )

    existing = _inspect_destination(
        destination,
        expected_size=expected_size,
        expected_md5=expected_md5_value,
        expected_sha256=expected_sha256_value,
    )
    if existing.ready and not force:
        return existing
    if destination.exists() and not force:
        return PfamMaterializationResult(
            ready=False,
            status=f"existing_pfam_hmm_gz_{existing.status}",
            source_object_configured=bool(
                source_object_uri or settings.protein_annotation_pfam_hmm_gz_object_uri
            ),
            bucket_id=None,
            destination_present=True,
            downloaded=False,
            byte_size=destination.stat().st_size if destination.is_file() else None,
            expected_size_bytes=expected_size,
            md5_verified=False,
            sha256_verified=False,
            warnings=("existing_private_pfam_asset_failed_verification",),
        )

    resolved_uri = source_object_uri or settings.protein_annotation_pfam_hmm_gz_object_uri
    if not resolved_uri:
        return _result(
            "source_object_uri_missing",
            expected_size=expected_size,
            source_object_configured=False,
        )
    try:
        bucket_id, object_path = _parse_supabase_object_uri(resolved_uri)
    except ValueError:
        return _result(
            "source_object_uri_invalid",
            expected_size=expected_size,
            source_object_configured=True,
        )

    if not settings.supabase_url or not settings.supabase_service_role_key:
        return _result(
            "supabase_storage_credentials_missing",
            expected_size=expected_size,
            source_object_configured=True,
            bucket_id=bucket_id,
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    client_owner = http_client is None
    client = http_client or httpx.Client(
        timeout=settings.protein_annotation_pfam_materialize_timeout_seconds
    )
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
            byte_size, md5_value, sha256_value = _download_to_file(
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
            expected_size=expected_size,
            source_object_configured=True,
            bucket_id=bucket_id,
            warnings=exc.warnings,
        )
    finally:
        if client_owner:
            client.close()

    temp_path = Path(temp_name)
    if byte_size != expected_size:
        temp_path.unlink(missing_ok=True)
        return _result(
            "size_mismatch",
            expected_size=expected_size,
            source_object_configured=True,
            bucket_id=bucket_id,
            downloaded=True,
            byte_size=byte_size,
            warnings=("downloaded_pfam_asset_rejected",),
        )
    if md5_value.lower() != expected_md5_value:
        temp_path.unlink(missing_ok=True)
        return _result(
            "md5_mismatch",
            expected_size=expected_size,
            source_object_configured=True,
            bucket_id=bucket_id,
            downloaded=True,
            byte_size=byte_size,
            warnings=("downloaded_pfam_asset_rejected",),
        )
    if sha256_value.lower() != expected_sha256_value:
        temp_path.unlink(missing_ok=True)
        return _result(
            "sha256_mismatch",
            expected_size=expected_size,
            source_object_configured=True,
            bucket_id=bucket_id,
            downloaded=True,
            byte_size=byte_size,
            md5_verified=True,
            warnings=("downloaded_pfam_asset_rejected",),
        )

    temp_path.replace(destination)
    return PfamMaterializationResult(
        ready=True,
        status="ready",
        source_object_configured=True,
        bucket_id=bucket_id,
        destination_present=True,
        downloaded=True,
        byte_size=byte_size,
        expected_size_bytes=expected_size,
        md5_verified=True,
        sha256_verified=True,
    )


class _StorageDownloadError(RuntimeError):
    def __init__(self, status: str, warnings: tuple[str, ...] = ()) -> None:
        super().__init__(status)
        self.status = status
        self.warnings = warnings


def _download_to_file(
    client: httpx.Client,
    *,
    settings: Settings,
    bucket_id: str,
    object_path: str,
    destination,
) -> tuple[int, str, str]:
    md5_digest = hashlib.md5()
    sha256_digest = hashlib.sha256()
    byte_size = 0
    headers = {
        "apikey": settings.supabase_service_role_key or "",
        "Authorization": f"Bearer {settings.supabase_service_role_key or ''}",
    }
    url = _storage_object_url(settings.supabase_url or "", bucket_id, object_path)
    try:
        with client.stream("GET", url, headers=headers) as response:
            if response.status_code == 404:
                raise _StorageDownloadError("source_object_missing")
            if response.status_code < 200 or response.status_code >= 300:
                raise _StorageDownloadError("storage_download_failed")
            for chunk in response.iter_bytes():
                if not chunk:
                    continue
                destination.write(chunk)
                byte_size += len(chunk)
                md5_digest.update(chunk)
                sha256_digest.update(chunk)
    except httpx.HTTPError:
        raise _StorageDownloadError(
            "storage_download_failed",
            ("private_storage_download_failed_no_public_fallback",),
        ) from None
    return byte_size, md5_digest.hexdigest(), sha256_digest.hexdigest()


def _inspect_destination(
    destination: Path,
    *,
    expected_size: int,
    expected_md5: str,
    expected_sha256: str,
) -> PfamMaterializationResult:
    if not destination.exists():
        return _result("missing", expected_size=expected_size)
    if not destination.is_file():
        return _result("not_file", expected_size=expected_size, byte_size=None)
    byte_size = destination.stat().st_size
    if byte_size != expected_size:
        return _result("size_mismatch", expected_size=expected_size, byte_size=byte_size)
    md5_value, sha256_value = _hash_file(destination)
    if md5_value.lower() != expected_md5:
        return _result("md5_mismatch", expected_size=expected_size, byte_size=byte_size)
    if sha256_value.lower() != expected_sha256:
        return _result(
            "sha256_mismatch",
            expected_size=expected_size,
            byte_size=byte_size,
            md5_verified=True,
        )
    return PfamMaterializationResult(
        ready=True,
        status="ready",
        source_object_configured=False,
        bucket_id=None,
        destination_present=True,
        downloaded=False,
        byte_size=byte_size,
        expected_size_bytes=expected_size,
        md5_verified=True,
        sha256_verified=True,
    )


def _hash_file(path: Path) -> tuple[str, str]:
    md5_digest = hashlib.md5()
    sha256_digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            md5_digest.update(chunk)
            sha256_digest.update(chunk)
    return md5_digest.hexdigest(), sha256_digest.hexdigest()


def _storage_object_url(supabase_url: str, bucket_id: str, object_path: str) -> str:
    encoded_path = "/".join(quote(part, safe="") for part in object_path.split("/"))
    return (
        f"{supabase_url.rstrip('/')}/storage/v1/object/{quote(bucket_id, safe='')}/{encoded_path}"
    )


def _parse_supabase_object_uri(value: str) -> tuple[str, str]:
    prefix = "supabase://"
    if not value.startswith(prefix):
        raise ValueError("source object URI must use supabase://bucket/object-path")
    remainder = value[len(prefix) :]
    bucket_id, separator, object_path = remainder.partition("/")
    if not bucket_id or not separator or not object_path:
        raise ValueError("source object URI must include bucket and object path")
    return bucket_id, object_path


def _pfam_asset() -> ProteinAssetSpec:
    return next(asset for asset in PROTEIN_ANNOTATION_ASSETS if asset.asset_id == "pfam_a_hmm_gz")


def _result(
    status: str,
    *,
    expected_size: int,
    source_object_configured: bool = False,
    bucket_id: str | None = None,
    destination_present: bool = False,
    downloaded: bool = False,
    byte_size: int | None = None,
    md5_verified: bool = False,
    sha256_verified: bool = False,
    warnings: tuple[str, ...] = (),
) -> PfamMaterializationResult:
    return PfamMaterializationResult(
        ready=status == "ready",
        status=status,
        source_object_configured=source_object_configured,
        bucket_id=bucket_id,
        destination_present=destination_present,
        downloaded=downloaded,
        byte_size=byte_size,
        expected_size_bytes=expected_size,
        md5_verified=md5_verified,
        sha256_verified=sha256_verified,
        warnings=warnings,
    )
