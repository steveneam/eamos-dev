from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.local_evidence_runtime_assets import inspect_local_evidence_runtime_assets
from app.services.local_evidence_runtime_seed import (
    local_evidence_runtime_seed_definition_for_role,
    local_evidence_runtime_seed_roles,
    materialize_local_evidence_runtime_asset,
)
from app.services.source_storage_uploads import SourceStorageUploadMode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Seed one local-evidence runtime asset through an explicit off-startup "
            "operator action. Output is sanitized and never includes local paths, "
            "Storage object paths/URIs, signed URLs, or secrets."
        )
    )
    parser.add_argument("--role", choices=local_evidence_runtime_seed_roles(), required=True)
    parser.add_argument("--source-artifact", type=Path)
    parser.add_argument("--source-object-uri")
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--expected-size-bytes", type=int)
    parser.add_argument("--expected-md5")
    parser.add_argument("--expected-sha256")
    parser.add_argument(
        "--download-mode",
        choices=[mode.value for mode in SourceStorageUploadMode],
        default=SourceStorageUploadMode.REST.value,
        help=(
            "private Storage download transport. Use s3_multipart for large "
            "Supabase S3-compatible runtime seeds."
        ),
    )
    parser.add_argument("--force", action="store_true", help="replace an existing asset")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    definition = local_evidence_runtime_seed_definition_for_role(args.role)
    settings_kwargs: dict[str, Any] = {"jwt_secret": "local-evidence-runtime-seed-local"}
    if args.destination is not None:
        settings_kwargs[definition.path_setting] = args.destination
    settings = Settings(**settings_kwargs)

    result = materialize_local_evidence_runtime_asset(
        settings,
        role=args.role,
        source_artifact_path=args.source_artifact,
        source_object_uri=args.source_object_uri,
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
    runtime_probe = inspect_local_evidence_runtime_assets(settings)
    report = {
        "mode": "eamos_local_evidence_runtime_seed",
        "ready": result.ready,
        "status": result.status,
        "role": args.role,
        "download_mode": args.download_mode,
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
            "frontend_direct_access": "blocked",
            "supabase_metadata_mutation": "not_used",
            "render_env_or_deploy_mutation": "not_used",
            "provider_flip": "not_used",
            "local_evidence_enabled_flip": "not_used",
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
            "object_uri_values_in_output": "blocked",
        },
        "materialization": result.to_sanitized_dict(),
        "local_evidence_runtime_assets": runtime_probe,
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if result.ready or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
