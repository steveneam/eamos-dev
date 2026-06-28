from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import Settings
from app.services.generated_source_artifacts import (
    GENERATED_SOURCE_ARTIFACT_IDS,
    materialize_generated_source_artifact,
)
from app.services.source_storage_uploads import SourceStorageUploadMode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sync a generated SQLite artifact from an operator local file or private "
            "Supabase Storage object to the configured runtime path. This is an explicit "
            "off-startup action and validates checksums plus SQLite schema before replacing "
            "the runtime file."
        )
    )
    parser.add_argument("--artifact", choices=GENERATED_SOURCE_ARTIFACT_IDS, required=True)
    parser.add_argument("--source-artifact", type=Path)
    parser.add_argument("--source-object-uri")
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--manifest-destination", type=Path)
    parser.add_argument("--expected-size-bytes", type=int)
    parser.add_argument("--expected-md5")
    parser.add_argument("--expected-sha256")
    parser.add_argument(
        "--download-mode",
        choices=[mode.value for mode in SourceStorageUploadMode],
        default=SourceStorageUploadMode.REST.value,
        help=(
            "private Storage download transport. Use s3_multipart for Supabase "
            "S3-compatible sync when service-role REST credentials are not configured."
        ),
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    settings = Settings(jwt_secret="generated-artifact-sync-local")
    result = materialize_generated_source_artifact(
        settings,
        artifact_id=args.artifact,
        source_artifact_path=args.source_artifact,
        source_object_uri=args.source_object_uri,
        destination_path=args.destination,
        manifest_destination_path=args.manifest_destination,
        force=args.force,
        expected_size_bytes=args.expected_size_bytes,
        expected_md5=args.expected_md5,
        expected_sha256=args.expected_sha256,
        download_mode=args.download_mode,
        s3_endpoint_url=settings.supabase_storage_s3_endpoint_url,
        s3_region=settings.supabase_storage_s3_region,
        s3_access_key_id=settings.supabase_storage_s3_access_key_id,
        s3_secret_access_key=settings.supabase_storage_s3_secret_access_key,
    )
    report = {
        "mode": "eamos_generated_artifact_sync",
        "ready": result.ready,
        "status": result.status,
        "download_mode": args.download_mode,
        "supabase_url_configured": bool(settings.supabase_url),
        "storage_read_key_configured": bool(settings.supabase_service_role_key),
        "s3_endpoint_configured": bool(settings.supabase_storage_s3_endpoint_url),
        "s3_access_key_id_configured": bool(settings.supabase_storage_s3_access_key_id),
        "s3_secret_access_key_configured": bool(settings.supabase_storage_s3_secret_access_key),
        "guardrails": {
            "startup_download": "not_used",
            "request_time_materialization": "not_used",
            "network": (
                (
                    "supabase_private_storage_s3"
                    if args.download_mode == SourceStorageUploadMode.S3_MULTIPART.value
                    else "supabase_private_storage_rest"
                )
                if args.source_object_uri
                else "not_used_for_local_artifact"
            ),
            "public_storage_fallback": "blocked",
            "signed_urls": "not_created",
            "supabase_metadata_mutation": "not_used",
            "render_env_or_deploy_mutation": "not_used",
            "provider_flip": "not_used",
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
            "object_uri_values_in_output": "blocked",
        },
        "materialization": result.to_sanitized_dict(),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if result.ready or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
