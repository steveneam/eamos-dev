from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import Settings
from app.data_sources.source_manifest import POST_REFERENCE_DAY1_SOURCE_IDS
from app.services.source_downloads import DEFAULT_LARGE_STAGING_ROOT, DEFAULT_SMALL_STAGING_ROOT
from app.services.source_imports import DEFAULT_SOURCE_ASSET_BUCKET
from app.services.source_storage_uploads import (
    DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
    SourceStorageUploadMode,
    build_source_storage_upload_items,
    execute_source_storage_uploads,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Guarded private Supabase Storage upload for staged source assets."
    )
    parser.add_argument(
        "--source",
        action="append",
        choices=POST_REFERENCE_DAY1_SOURCE_IDS,
        help="source id to upload; may be repeated. Defaults to all post-reference sources.",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="perform private Storage uploads. Without this flag the command prints a plan.",
    )
    parser.add_argument(
        "--upload-mode",
        choices=[mode.value for mode in SourceStorageUploadMode],
        default=SourceStorageUploadMode.REST.value,
        help=(
            "private Storage upload transport. Use s3_multipart for Supabase S3-compatible "
            "multipart transfers after S3 credentials are configured."
        ),
    )
    parser.add_argument(
        "--bucket",
        default=DEFAULT_SOURCE_ASSET_BUCKET,
        help="private Supabase Storage bucket id.",
    )
    parser.add_argument(
        "--small-staging-root",
        type=Path,
        default=DEFAULT_SMALL_STAGING_ROOT,
        help="staging root for non-large assets.",
    )
    parser.add_argument(
        "--large-staging-root",
        type=Path,
        default=DEFAULT_LARGE_STAGING_ROOT,
        help="staging root for large assets.",
    )
    parser.add_argument(
        "--bucket-file-size-limit",
        type=int,
        default=DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
        help="current private bucket per-object limit in bytes.",
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)

    settings = Settings(jwt_secret="source-storage-upload-local")
    source_ids = tuple(args.source) if args.source else POST_REFERENCE_DAY1_SOURCE_IDS
    items = build_source_storage_upload_items(
        source_ids=source_ids,
        bucket_id=args.bucket,
        small_staging_root=args.small_staging_root,
        large_staging_root=args.large_staging_root,
        bucket_file_size_limit=args.bucket_file_size_limit,
    )
    result = execute_source_storage_uploads(
        items,
        upload=args.upload,
        upload_mode=args.upload_mode,
        supabase_url=settings.supabase_url,
        service_role_key=settings.supabase_service_role_key,
        s3_endpoint_url=settings.supabase_storage_s3_endpoint_url,
        s3_region=settings.supabase_storage_s3_region,
        s3_access_key_id=settings.supabase_storage_s3_access_key_id,
        s3_secret_access_key=settings.supabase_storage_s3_secret_access_key,
    )
    status = "planned"
    if args.upload:
        if result.uploaded_count > 0 and result.blocked_count == 0 and result.failed_count == 0:
            status = "uploaded"
        elif result.failed_count > 0:
            status = "failed"
        else:
            status = "blocked"
    report = {
        "mode": "eamos_source_storage_upload",
        "status": status,
        "upload_performed": bool(args.upload and result.uploaded_count > 0),
        "upload_mode": args.upload_mode,
        "supabase_url_configured": bool(settings.supabase_url),
        "service_role_key_configured": bool(settings.supabase_service_role_key),
        "s3_endpoint_configured": bool(settings.supabase_storage_s3_endpoint_url),
        "s3_access_key_id_configured": bool(settings.supabase_storage_s3_access_key_id),
        "s3_secret_access_key_configured": bool(settings.supabase_storage_s3_secret_access_key),
        "bucket": args.bucket,
        "bucket_file_size_limit": args.bucket_file_size_limit,
        "guardrails": {
            "private_bucket_required": True,
            "public_bucket": "blocked",
            "frontend_direct_access": "blocked",
            "signed_urls": "not_created",
            "render_env_or_deploy_mutation": "not_used",
            "restricted_predictor_unlocks": "not_used",
            "secrets_in_output": "blocked",
        },
        "result": result.to_dict(),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 2 if args.upload and status != "uploaded" else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
