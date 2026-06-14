from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import md5, sha256
import json
from pathlib import Path

import httpx

from app.core.config import Settings
from app.services.predictor_runtime import inspect_alphamissense_runtime_asset

DEFAULT_SOURCE_URL = (
    "https://zenodo.org/records/10813168/files/AlphaMissense_hg38.tsv.gz?download=1"
)
DEFAULT_TARGET_PATH = Path(
    "/var/data/eamos/bio_assets/predictors/alphamissense/AlphaMissense_hg38.tsv.gz"
)
DEFAULT_EXPECTED_SIZE_BYTES = 642_961_469
DEFAULT_EXPECTED_MD5 = "9fd167735f16a1b87da6eb3e4c25fcb5"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Materialize the AlphaMissense hg38 bgzip/tabix runtime asset."
    )
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--target-path", type=Path, default=DEFAULT_TARGET_PATH)
    parser.add_argument("--expected-size-bytes", type=int, default=DEFAULT_EXPECTED_SIZE_BYTES)
    parser.add_argument("--expected-md5", default=DEFAULT_EXPECTED_MD5)
    parser.add_argument("--force", action="store_true", help="download even when target verifies")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)

    result = materialize_alphamissense(
        source_url=args.source_url,
        target_path=args.target_path,
        expected_size_bytes=args.expected_size_bytes,
        expected_md5=args.expected_md5,
        force=args.force,
    )
    ready = result["preflight"]["ready"] is True
    output = {
        "mode": "eamos_alphamissense_runtime_materialize",
        "status": "ready" if ready else "failed",
        "guardrails": {
            "startup_downloads": "not_used",
            "render_env_or_deploy_mutation": "not_used",
            "supabase_mutation": "not_used",
            "public_bucket": "blocked",
            "frontend_direct_access": "blocked",
            "secrets_in_output": "blocked",
        },
        **result,
    }
    print(json.dumps(output, indent=None if args.compact else 2, sort_keys=True))
    return 0 if ready or not args.require_ready else 2


def materialize_alphamissense(
    *,
    source_url: str,
    target_path: Path,
    expected_size_bytes: int,
    expected_md5: str,
    force: bool,
) -> dict[str, object]:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_ready = _target_matches(
        target_path,
        expected_size_bytes=expected_size_bytes,
        expected_md5=expected_md5,
    )
    downloaded = False
    checksum: dict[str, object] | None = target_ready
    if force or target_ready is None:
        download_path = target_path.with_name(f".{target_path.name}.download.gz")
        if download_path.exists():
            download_path.unlink()
        checksum = _download(
            source_url=source_url,
            download_path=download_path,
            expected_size_bytes=expected_size_bytes,
            expected_md5=expected_md5,
        )
        download_path.replace(target_path)
        downloaded = True

    index_path = _build_tabix_index(target_path)
    manifest_path = _write_manifest(
        target_path=target_path,
        index_path=index_path,
        source_url=source_url,
        checksum=checksum or {},
    )
    preflight = _preflight(target_path)
    return {
        "downloaded": downloaded,
        "target": {
            "file_name": target_path.name,
            "size_bytes": target_path.stat().st_size if target_path.exists() else None,
            "md5_verified": checksum.get("md5_verified") if checksum else False,
            "sha256": checksum.get("sha256") if checksum else None,
        },
        "index": {
            "file_name": index_path.name,
            "exists": index_path.is_file(),
            "size_bytes": index_path.stat().st_size if index_path.is_file() else None,
        },
        "manifest": {
            "file_name": manifest_path.name,
            "exists": manifest_path.is_file(),
        },
        "preflight": preflight,
    }


def _target_matches(
    path: Path,
    *,
    expected_size_bytes: int,
    expected_md5: str,
) -> dict[str, object] | None:
    if not path.is_file():
        return None
    if path.stat().st_size != expected_size_bytes:
        return None
    digest = _hash_file(path)
    if digest["md5"] != expected_md5.lower():
        return None
    return {
        **digest,
        "actual_size_bytes": path.stat().st_size,
        "md5_verified": True,
        "expected_md5": expected_md5.lower(),
    }


def _download(
    *,
    source_url: str,
    download_path: Path,
    expected_size_bytes: int,
    expected_md5: str,
) -> dict[str, object]:
    hash_md5 = md5()
    hash_sha256 = sha256()
    total = 0
    final_url = source_url
    with httpx.Client(
        follow_redirects=True,
        timeout=None,
        headers={"User-Agent": "Eamos-alphamissense-materializer/1.0"},
    ) as client:
        with client.stream("GET", source_url) as response:
            response.raise_for_status()
            final_url = _sanitize_url(str(response.url))
            with download_path.open("wb") as file:
                for chunk in response.iter_bytes(chunk_size=4 * 1024 * 1024):
                    if not chunk:
                        continue
                    file.write(chunk)
                    total += len(chunk)
                    hash_md5.update(chunk)
                    hash_sha256.update(chunk)

    actual_md5 = hash_md5.hexdigest()
    if total != expected_size_bytes:
        download_path.unlink(missing_ok=True)
        raise RuntimeError(f"AlphaMissense size mismatch: {total} != {expected_size_bytes}")
    if actual_md5 != expected_md5.lower():
        download_path.unlink(missing_ok=True)
        raise RuntimeError(f"AlphaMissense MD5 mismatch: {actual_md5} != {expected_md5.lower()}")
    return {
        "actual_size_bytes": total,
        "md5": actual_md5,
        "sha256": hash_sha256.hexdigest(),
        "md5_verified": True,
        "expected_md5": expected_md5.lower(),
        "final_url": final_url,
    }


def _build_tabix_index(target_path: Path) -> Path:
    try:
        import pysam
    except ImportError as exc:
        raise RuntimeError("pysam is required to create AlphaMissense tabix index") from exc
    pysam.tabix_index(
        str(target_path),
        force=True,
        seq_col=0,
        start_col=1,
        end_col=1,
        meta_char="#",
        zerobased=False,
    )
    index_path = Path(f"{target_path}.tbi")
    if not index_path.is_file():
        raise RuntimeError("AlphaMissense tabix index was not created")
    return index_path


def _write_manifest(
    *,
    target_path: Path,
    index_path: Path,
    source_url: str,
    checksum: dict[str, object],
) -> Path:
    manifest_path = target_path.with_suffix(target_path.suffix + ".manifest.json")
    index_digest = _hash_file(index_path)
    manifest = {
        "source_id": "google_deepmind_alphamissense_hg38",
        "asset_role": "predictor_tabix_tsv",
        "source_url": _sanitize_url(source_url),
        "file_name": target_path.name,
        "actual_size_bytes": target_path.stat().st_size,
        "md5": checksum.get("md5"),
        "sha256": checksum.get("sha256"),
        "index_file_name": index_path.name,
        "index_size_bytes": index_path.stat().st_size,
        "index_md5": index_digest["md5"],
        "index_sha256": index_digest["sha256"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "public_access_allowed": False,
        "frontend_direct_access_allowed": False,
        "startup_download_allowed": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def _preflight(target_path: Path) -> dict[str, object]:
    settings = Settings(
        jwt_secret="alphamissense-runtime-materialize",
        alphamissense_hg38_runtime_asset_path=target_path,
    )
    inspection = inspect_alphamissense_runtime_asset(
        settings,
        verify_checksum=True,
        require_manifest=True,
    )
    return _predictor_inspection_summary(inspection)


def _predictor_inspection_summary(inspection: object) -> dict[str, object]:
    return {
        "source_id": getattr(inspection, "source_id"),
        "asset_role": getattr(inspection, "asset_role"),
        "mode": getattr(inspection, "mode"),
        "status": getattr(inspection, "status").value,
        "ready": getattr(inspection, "ready"),
        "actual_size_bytes": getattr(inspection, "actual_size_bytes"),
        "reader_requires_local_path": getattr(inspection, "reader_requires_local_path"),
        "materialization_status": getattr(inspection, "materialization_status"),
    }


def _hash_file(path: Path) -> dict[str, str]:
    hash_md5 = md5()
    hash_sha256 = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(4 * 1024 * 1024), b""):
            hash_md5.update(chunk)
            hash_sha256.update(chunk)
    return {"md5": hash_md5.hexdigest(), "sha256": hash_sha256.hexdigest()}


def _sanitize_url(url: str) -> str:
    return url.split("?", 1)[0]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
