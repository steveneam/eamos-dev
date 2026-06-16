from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from app.core.config import Settings
from app.services.source_imports import DEFAULT_SOURCE_ASSET_BUCKET
from app.services.source_storage_uploads import (
    DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
    SourceStorageUploadMode,
)
from app.services.tier2_predictor_artifacts import (
    TIER2_PREDICTOR_ARTIFACT_IDS,
    build_tier2_predictor_artifact_upload_items,
    execute_tier2_predictor_artifact_uploads,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or upload complete Tier 2 predictor runtime artifact sets "
            "(ESM1b, CI-SpliceAI, CAPICE) to private Supabase Storage. This "
            "does not download upstream predictors, mutate Supabase metadata "
            "rows, create signed URLs, seed Render disk, or flip providers."
        )
    )
    parser.add_argument(
        "--artifact",
        action="append",
        choices=TIER2_PREDICTOR_ARTIFACT_IDS,
        help="Tier 2 predictor artifact set to upload; may be repeated. Defaults to all.",
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
        help="private Storage upload transport.",
    )
    parser.add_argument("--bucket", default=DEFAULT_SOURCE_ASSET_BUCKET)
    parser.add_argument(
        "--bucket-file-size-limit",
        type=int,
        default=DEFAULT_SOURCE_ASSET_BUCKET_FILE_SIZE_LIMIT,
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)

    settings = Settings(jwt_secret="tier2-predictor-artifact-upload-local")
    artifact_ids = tuple(args.artifact) if args.artifact else TIER2_PREDICTOR_ARTIFACT_IDS
    with tempfile.TemporaryDirectory(prefix="eamos-tier2-predictor-manifests-") as temp_dir:
        items = build_tier2_predictor_artifact_upload_items(
            settings,
            artifact_ids=artifact_ids,
            bucket_id=args.bucket,
            manifest_staging_root=Path(temp_dir),
            bucket_file_size_limit=args.bucket_file_size_limit,
        )
        result = execute_tier2_predictor_artifact_uploads(
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
        "mode": "eamos_tier2_predictor_artifact_upload",
        "status": status,
        "upload_performed": bool(args.upload and result.uploaded_count > 0),
        "upload_mode": args.upload_mode,
        "bucket": args.bucket,
        "supabase_url_configured": bool(settings.supabase_url),
        "storage_write_key_configured": bool(settings.supabase_service_role_key),
        "s3_endpoint_configured": bool(settings.supabase_storage_s3_endpoint_url),
        "s3_access_key_id_configured": bool(settings.supabase_storage_s3_access_key_id),
        "s3_secret_access_key_configured": bool(settings.supabase_storage_s3_secret_access_key),
        "guardrails": {
            "private_bucket_required": True,
            "complete_artifact_set_required": True,
            "public_bucket": "blocked",
            "frontend_direct_access": "blocked",
            "signed_urls": "not_created",
            "supabase_metadata_mutation": "not_used",
            "render_env_or_deploy_mutation": "not_used",
            "render_disk_seeding": "not_used",
            "provider_flip": "not_used",
            "startup_download": "not_used",
            "restricted_predictor_unlocks": "not_used",
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
        },
        "result": result.to_sanitized_dict(),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 2 if args.upload and status != "uploaded" else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
