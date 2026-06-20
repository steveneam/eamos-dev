from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import Settings
from app.repos.supabase_local_model_cache_repo import (
    SupabaseLocalModelCacheError,
    build_supabase_local_model_cache_store,
)
from app.services.materialization_orchestrator import (
    MaterializationOrchestratorError,
    materialize_all_from_manifest,
)
from app.services.source_storage_uploads import SourceStorageUploadMode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize all pinned runtime assets from a manifest. The command is "
            "idempotent, verifies size/checksum before replacing runtime files, and "
            "reconciles private Supabase source_asset_materializations when configured."
        )
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--download-mode",
        choices=[mode.value for mode in SourceStorageUploadMode],
        default=SourceStorageUploadMode.S3_MULTIPART.value,
        help="private Storage download transport.",
    )
    parser.add_argument("--force", action="store_true", help="replace existing verified assets")
    parser.add_argument(
        "--no-reconcile-supabase",
        action="store_true",
        help="skip private Supabase source object/materialization reconciliation",
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    settings = Settings(jwt_secret="materialize-all-local")
    store = None
    if not args.no_reconcile_supabase:
        store = build_supabase_local_model_cache_store(settings)

    try:
        report = materialize_all_from_manifest(
            settings,
            manifest_path=args.manifest,
            force=args.force,
            download_mode=args.download_mode,
            reconcile_supabase=not args.no_reconcile_supabase,
            materialization_store=store,
        )
    except MaterializationOrchestratorError as exc:
        report = {
            "mode": "eamos_materialize_all",
            "ready": False,
            "status": "failed",
            "code": exc.code,
            "message": str(exc),
            "details": exc.details,
            "guardrails": _guardrails(),
        }
        print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
        return 2
    except SupabaseLocalModelCacheError as exc:
        report = {
            "mode": "eamos_materialize_all",
            "ready": False,
            "status": "failed",
            "code": "supabase_metadata_reconciliation_failed",
            "message": str(exc),
            "details": {},
            "guardrails": _guardrails(),
        }
        print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
        return 2

    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if report["ready"] or not args.require_ready else 2


def _guardrails() -> dict[str, str]:
    return {
        "startup_download": "not_used",
        "request_time_materialization": "not_used",
        "public_storage_fallback": "blocked",
        "signed_urls": "not_created",
        "frontend_direct_access": "blocked",
        "local_evidence_enabled_flip": "not_used",
        "provider_flip": "not_used",
        "render_env_or_deploy_mutation": "not_used",
        "secrets_in_output": "blocked",
        "local_paths_in_output": "blocked",
        "object_uri_values_in_output": "blocked",
    }


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
