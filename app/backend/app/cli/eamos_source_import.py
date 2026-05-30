from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from typing import Any

from app.core.config import Settings
from app.repos.supabase_local_model_cache_repo import (
    SupabaseLocalModelCacheError,
    build_supabase_local_model_cache_store,
)
from app.services.source_imports import (
    HG38_STORAGE_PILOT_ID,
    SourceImportError,
    apply_clinical_source_import_bundle,
    apply_storage_pilot_registration,
    build_clinical_source_import_bundle,
    build_storage_pilot_registration,
    clinical_bundle_report,
    storage_pilot_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Backend-only Eamos source import CLI for Tier 3 fixture rows and "
            "metadata-only private Storage pilots."
        )
    )
    parser.add_argument(
        "--clinical-fixtures",
        action="store_true",
        help="plan/apply the dev fixture import for MONDO/HPO/ClinGen/GenCC private tables",
    )
    parser.add_argument(
        "--skip-clinical-fixtures",
        action="store_true",
        help="only plan/apply the requested storage pilot",
    )
    parser.add_argument(
        "--storage-pilot",
        choices=("none", HG38_STORAGE_PILOT_ID, "clinvar_vcf"),
        default=HG38_STORAGE_PILOT_ID,
        help="plan/apply a metadata-only private Storage pilot; default is hg38.2bit",
    )
    parser.add_argument(
        "--apply-supabase",
        action="store_true",
        help=(
            "write to the configured private Supabase Postgres tables. Requires "
            "SUPABASE_LOCAL_MODEL_CACHE_ENABLED=true and a private DB URL."
        ),
    )
    parser.add_argument(
        "--skip-supabase-smoke",
        action="store_true",
        help="skip the Supabase write/read/delete smoke before applying imports",
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)

    include_clinical = args.clinical_fixtures or not args.skip_clinical_fixtures

    try:
        report = build_source_import_report(
            include_clinical=include_clinical,
            storage_pilot_id=None if args.storage_pilot == "none" else args.storage_pilot,
            apply_supabase=args.apply_supabase,
            skip_supabase_smoke=args.skip_supabase_smoke,
        )
    except SourceImportError as exc:
        print(
            json.dumps(
                {
                    "mode": "eamos_source_import",
                    "status": "failed",
                    "code": exc.code,
                    "message": str(exc),
                    "details": exc.details,
                },
                indent=None if args.compact else 2,
                sort_keys=True,
            )
        )
        return 2
    except SupabaseLocalModelCacheError as exc:
        print(
            json.dumps(
                {
                    "mode": "eamos_source_import",
                    "status": "failed",
                    "code": "supabase_import_failed",
                    "message": str(exc),
                    "details": {},
                },
                indent=None if args.compact else 2,
                sort_keys=True,
            )
        )
        return 2

    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0


def build_source_import_report(
    *,
    include_clinical: bool = True,
    storage_pilot_id: str | None = HG38_STORAGE_PILOT_ID,
    apply_supabase: bool = False,
    skip_supabase_smoke: bool = False,
) -> dict[str, Any]:
    store = None
    if apply_supabase:
        settings = Settings(jwt_secret="source-import-local")
        store = build_supabase_local_model_cache_store(settings)
        if store is None:
            raise SourceImportError(
                "supabase_import_not_configured",
                (
                    "Supabase import apply requires SUPABASE_LOCAL_MODEL_CACHE_ENABLED=true "
                    "and SUPABASE_LOCAL_MODEL_CACHE_DATABASE_URL"
                ),
            )
        if not skip_supabase_smoke:
            store.smoke_test()

    report: dict[str, Any] = {
        "mode": "eamos_source_import",
        "status": "applied" if apply_supabase else "planned",
        "applied": apply_supabase,
        "guardrails": {
            "production_downloads": "not_used",
            "storage_bucket_creation": "not_used",
            "storage_uploads": "not_used",
            "frontend_direct_sql": "blocked",
            "public_bucket": "blocked",
            "browser_roles": "no_grants",
            "secrets_in_output": "blocked",
        },
    }

    if include_clinical:
        clinical_bundle = build_clinical_source_import_bundle()
        clinical_report = clinical_bundle_report(clinical_bundle)
        if store is not None:
            clinical_report["apply_result"] = asdict(
                apply_clinical_source_import_bundle(store, clinical_bundle)
            )
        report["clinical_fixtures"] = clinical_report

    if storage_pilot_id is not None:
        pilot = build_storage_pilot_registration(pilot_id=storage_pilot_id)
        pilot_report = storage_pilot_report(pilot)
        if store is not None:
            pilot_report["apply_result"] = asdict(apply_storage_pilot_registration(store, pilot))
        report["storage_pilot"] = pilot_report

    return report


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
