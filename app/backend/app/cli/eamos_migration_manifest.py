from __future__ import annotations

import argparse
from pathlib import Path
import sys

from app.core.config import Settings
from app.services.migration_asset_manifest import (
    MigrationAssetManifestError,
    build_source_bucket_manifest,
    build_tree_manifest,
    compare_manifest_content,
    format_asset_manifest,
    load_source_checksum_overrides,
    parse_asset_manifest,
)
from app.services.source_storage_uploads import _build_s3_client

DEFAULT_BUCKET_ID = "eamos-source-assets"
DEFAULT_OVERRIDE_PATH = Path(__file__).resolve().parents[1] / "migration-source-overrides.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build and compare read-only source/runtime manifests for the Render-to-syd2 "
            "migration proof."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    source_parser = subparsers.add_parser(
        "source",
        help="list/head private Storage objects and hash only objects up to one MiB",
    )
    source_parser.add_argument("--bucket", default=DEFAULT_BUCKET_ID)
    source_parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDE_PATH)

    tree_parser = subparsers.add_parser("tree", help="hash every regular file below a root")
    tree_parser.add_argument("--root", type=Path, required=True)

    compare_parser = subparsers.add_parser(
        "compare",
        help="fail when any Render/runtime file identity is absent from the source manifest",
    )
    compare_parser.add_argument("--source", type=Path, required=True)
    compare_parser.add_argument("--runtime", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "source":
        return _source_manifest(args.bucket, args.overrides)
    if args.command == "tree":
        return _tree_manifest(args.root)
    return _compare_manifests(args.source, args.runtime)


def _source_manifest(bucket_id: str, override_path: Path) -> int:
    settings = Settings(jwt_secret="migration-manifest-read-only")
    required_settings = (
        settings.supabase_storage_s3_endpoint_url,
        settings.supabase_storage_s3_access_key_id,
        settings.supabase_storage_s3_secret_access_key,
    )
    if not all(required_settings):
        print(
            "ERROR: source manifest requires configured server-side S3 credentials", file=sys.stderr
        )
        return 2
    try:
        overrides = load_source_checksum_overrides(override_path)
        client = _build_s3_client(
            endpoint_url=settings.supabase_storage_s3_endpoint_url,
            region=settings.supabase_storage_s3_region,
            access_key_id=settings.supabase_storage_s3_access_key_id,
            secret_access_key=settings.supabase_storage_s3_secret_access_key,
        )
        result = build_source_bucket_manifest(
            client,
            bucket_id=bucket_id,
            overrides=overrides,
        )
    except Exception as exc:
        print(f"ERROR: source manifest failed ({type(exc).__name__})", file=sys.stderr)
        return 2

    if result.issues:
        for issue in result.issues:
            print(f"ERROR: {issue.code}: {issue.object_path}", file=sys.stderr)
        print(
            f"source_manifest=failed objects={result.object_count} issues={len(result.issues)} "
            "read_only=true",
            file=sys.stderr,
        )
        return 1

    print(format_asset_manifest(result.rows), end="")
    print(
        f"source_manifest=ready objects={result.object_count} bytes={result.object_bytes} "
        f"small_object_bytes_downloaded={result.small_object_bytes_downloaded} "
        "operations=list,head,get-small-objects large_object_downloads=0 mutations=0",
        file=sys.stderr,
    )
    return 0


def _tree_manifest(root: Path) -> int:
    try:
        rows = build_tree_manifest(root)
    except MigrationAssetManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(format_asset_manifest(rows), end="")
    print(f"tree_manifest=ready files={len(rows)} read_only=true", file=sys.stderr)
    return 0


def _compare_manifests(source_path: Path, runtime_path: Path) -> int:
    try:
        source_rows = parse_asset_manifest(source_path.read_text(encoding="utf-8"))
        runtime_rows = parse_asset_manifest(runtime_path.read_text(encoding="utf-8"))
    except (OSError, MigrationAssetManifestError) as exc:
        print(f"ERROR: manifest comparison failed ({type(exc).__name__})", file=sys.stderr)
        return 2

    comparison = compare_manifest_content(source_rows, runtime_rows)
    for row in comparison.render_only:
        print(f"RENDER_ONLY: {row.relpath}  {row.byte_size}  {row.sha256}")
    print(
        f"SUMMARY: matched={comparison.matched_count} "
        f"render_only={len(comparison.render_only)} "
        f"source_identities={comparison.source_identity_count} "
        f"source_only_identities={comparison.source_only_identity_count}"
    )
    return 1 if comparison.render_only else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
