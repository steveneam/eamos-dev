from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import socket
from typing import Any

from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.repos.supabase_local_model_cache_repo import (
    SupabaseLocalModelCacheError,
    build_supabase_local_model_cache_store,
)
from app.services.source_imports import (
    DBSNP_PHYLOP_EXISTING_OBJECTS_ID,
    EXISTING_OBJECT_SET_SOURCE_IDS,
    HG38_STORAGE_PILOT_ID,
    SourceImportError,
    apply_clinical_source_import_bundle,
    apply_existing_source_asset_metadata_registration,
    apply_storage_pilot_registration,
    build_clinical_source_import_bundle,
    build_clinical_release_source_import_bundle,
    build_existing_source_asset_metadata_registration,
    build_storage_pilot_registration,
    clinical_bundle_report,
    existing_source_asset_metadata_report,
    storage_pilot_report,
)
from app.services.source_storage_uploads import (
    S3_CONNECT_TIMEOUT_SECONDS,
    S3_READ_TIMEOUT_SECONDS,
    S3_RETRY_ATTEMPTS,
    build_source_storage_upload_items,
)

SUPABASE_TCP_PREFLIGHT_TIMEOUT_SECONDS = 8.0


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
        "--clinical-release-files",
        action="store_true",
        help=(
            "plan/apply release-scale staged MONDO/HPO/ClinGen/GenCC files from "
            "app/backend/data/source_assets by default"
        ),
    )
    parser.add_argument(
        "--clinical-source-asset-root",
        type=Path,
        default=None,
        help="override the staged clinical source asset root for --clinical-release-files",
    )
    parser.add_argument("--mondo-source-version", default=None)
    parser.add_argument("--hpo-source-version", default=None)
    parser.add_argument("--clingen-source-version", default=None)
    parser.add_argument("--gencc-source-version", default=None)
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
        "--existing-object-set",
        choices=("none", DBSNP_PHYLOP_EXISTING_OBJECTS_ID),
        default="none",
        help=(
            "plan/apply existing private Storage object metadata. Use dbsnp_phylop "
            "for the M2 dbSNP + phyloP reconciliation."
        ),
    )
    parser.add_argument(
        "--storage-heads-verified",
        action="store_true",
        help=(
            "mark existing object rows as verified after an explicit private Storage "
            "head-object proof for every planned object and manifest."
        ),
    )
    parser.add_argument(
        "--verify-storage-heads",
        action="store_true",
        help=(
            "use configured Supabase S3 credentials to head-object every existing "
            "object and manifest before marking rows verified."
        ),
    )
    parser.add_argument(
        "--environment",
        default="sg-render",
        help="target runtime environment label for materialization metadata.",
    )
    parser.add_argument(
        "--backend-runtime",
        default="render_backend",
        help="backend runtime label for materialization metadata.",
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
    parser.add_argument(
        "--skip-supabase-tcp-check",
        action="store_true",
        help=(
            "skip the fast TCP reachability preflight before --apply-supabase; "
            "the SQLAlchemy smoke test still runs unless --skip-supabase-smoke is also set"
        ),
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)

    include_clinical = (
        args.clinical_release_files or args.clinical_fixtures or not args.skip_clinical_fixtures
    )
    clinical_source_version_overrides = {
        source_id: version
        for source_id, version in (
            ("mondo_disease_ontology", args.mondo_source_version),
            ("human_phenotype_ontology", args.hpo_source_version),
            ("clingen_gene_validity", args.clingen_source_version),
            ("gencc_download", args.gencc_source_version),
        )
        if version
    }

    try:
        report = build_source_import_report(
            include_clinical=include_clinical,
            clinical_release_files=args.clinical_release_files,
            clinical_source_asset_root=args.clinical_source_asset_root,
            clinical_source_version_overrides=clinical_source_version_overrides or None,
            storage_pilot_id=None if args.storage_pilot == "none" else args.storage_pilot,
            existing_object_set_id=(
                None if args.existing_object_set == "none" else args.existing_object_set
            ),
            storage_heads_verified=args.storage_heads_verified,
            verify_storage_heads=args.verify_storage_heads,
            environment=args.environment,
            backend_runtime=args.backend_runtime,
            apply_supabase=args.apply_supabase,
            skip_supabase_smoke=args.skip_supabase_smoke,
            check_supabase_tcp=not args.skip_supabase_tcp_check,
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
    clinical_release_files: bool = False,
    clinical_source_asset_root: Path | None = None,
    clinical_source_version_overrides: dict[str, str] | None = None,
    storage_pilot_id: str | None = HG38_STORAGE_PILOT_ID,
    existing_object_set_id: str | None = None,
    storage_heads_verified: bool = False,
    verify_storage_heads: bool = False,
    environment: str = "sg-render",
    backend_runtime: str = "render_backend",
    apply_supabase: bool = False,
    skip_supabase_smoke: bool = False,
    check_supabase_tcp: bool = True,
) -> dict[str, Any]:
    store = None
    settings = None
    if apply_supabase or verify_storage_heads:
        settings = Settings(jwt_secret="source-import-local")
    if apply_supabase:
        if check_supabase_tcp:
            _check_supabase_database_tcp_reachable(settings)
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
        if clinical_release_files:
            release_kwargs: dict[str, Any] = {
                "source_version_overrides": clinical_source_version_overrides,
            }
            if clinical_source_asset_root is not None:
                release_kwargs["source_asset_root"] = clinical_source_asset_root
            clinical_bundle = build_clinical_release_source_import_bundle(**release_kwargs)
        else:
            clinical_bundle = build_clinical_source_import_bundle(
                source_version_overrides=clinical_source_version_overrides,
            )
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

    if existing_object_set_id is not None:
        upload_items = build_source_storage_upload_items(
            source_ids=EXISTING_OBJECT_SET_SOURCE_IDS[existing_object_set_id],
        )
        resolved_storage_heads_verified = storage_heads_verified
        if verify_storage_heads:
            resolved_storage_heads_verified = _verify_existing_storage_heads(
                settings,
                upload_items,
            )
        registration = build_existing_source_asset_metadata_registration(
            metadata_set_id=existing_object_set_id,
            upload_items=upload_items,
            environment=environment,
            backend_runtime=backend_runtime,
            storage_heads_verified=resolved_storage_heads_verified,
        )
        metadata_report = existing_source_asset_metadata_report(registration)
        if store is not None:
            metadata_report["apply_result"] = asdict(
                apply_existing_source_asset_metadata_registration(store, registration)
            )
        report["existing_object_metadata"] = metadata_report

    return report


def _check_supabase_database_tcp_reachable(
    settings: Settings | None,
    *,
    timeout_seconds: float = SUPABASE_TCP_PREFLIGHT_TIMEOUT_SECONDS,
) -> None:
    if settings is None or not settings.supabase_local_model_cache_database_url:
        raise SourceImportError(
            "supabase_import_not_configured",
            (
                "Supabase import apply requires SUPABASE_LOCAL_MODEL_CACHE_ENABLED=true "
                "and SUPABASE_LOCAL_MODEL_CACHE_DATABASE_URL"
            ),
        )
    try:
        parsed_url = make_url(settings.supabase_local_model_cache_database_url)
    except Exception as exc:
        raise SourceImportError(
            "supabase_import_database_url_invalid",
            "Supabase import apply could not parse the configured private DB URL",
            {"error_type": type(exc).__name__},
        ) from exc

    host = parsed_url.host
    port = parsed_url.port or 5432
    if not host:
        raise SourceImportError(
            "supabase_import_database_url_invalid",
            "Supabase import apply requires a TCP Postgres host in the private DB URL",
            {"port": port},
        )

    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return
    except OSError as exc:
        raise SourceImportError(
            "supabase_import_database_unreachable",
            (
                "Supabase import apply could not open a TCP connection to the configured "
                "Postgres host before parsing/applying release files"
            ),
            {
                "host": host,
                "port": port,
                "timeout_seconds": timeout_seconds,
                "error_type": type(exc).__name__,
            },
        ) from exc


def _verify_existing_storage_heads(settings: Settings | None, upload_items) -> bool:
    if settings is None:
        raise SourceImportError(
            "supabase_s3_settings_unavailable",
            "S3 head verification requires settings",
        )
    if (
        not settings.supabase_storage_s3_endpoint_url
        or not settings.supabase_storage_s3_access_key_id
        or not settings.supabase_storage_s3_secret_access_key
    ):
        raise SourceImportError(
            "supabase_s3_credentials_missing",
            "S3 head verification requires Supabase S3 endpoint and credentials",
        )
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:  # pragma: no cover - depends on deployment environment
        raise SourceImportError(
            "boto3_unavailable",
            "S3 head verification requires boto3",
        ) from exc
    client = boto3.client(
        "s3",
        endpoint_url=settings.supabase_storage_s3_endpoint_url,
        region_name=settings.supabase_storage_s3_region or "auto",
        aws_access_key_id=settings.supabase_storage_s3_access_key_id,
        aws_secret_access_key=settings.supabase_storage_s3_secret_access_key,
        config=Config(
            s3={"addressing_style": "path"},
            connect_timeout=S3_CONNECT_TIMEOUT_SECONDS,
            read_timeout=S3_READ_TIMEOUT_SECONDS,
            retries={"max_attempts": S3_RETRY_ATTEMPTS, "mode": "standard"},
            tcp_keepalive=True,
        ),
    )
    failures: list[dict[str, object]] = []
    for item in upload_items:
        failures.extend(_head_item(client, item))
    if failures:
        raise SourceImportError(
            "existing_storage_head_verification_failed",
            "one or more existing private Storage objects failed head-object verification",
            {"failures": failures},
        )
    return True


def _head_item(client, item) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    for key, expected_size, kind in (
        (item.object_path, item.byte_size, "asset"),
        (item.manifest_object_path, None, "manifest"),
    ):
        try:
            response = client.head_object(Bucket=item.bucket_id, Key=key)
        except Exception as exc:
            failures.append(
                {
                    "source_id": item.source_id,
                    "asset_id": item.asset_id,
                    "kind": kind,
                    "status": "missing_or_unreadable",
                    "error_code": _s3_error_code(exc),
                }
            )
            continue
        content_length = response.get("ContentLength")
        if expected_size is not None and content_length != expected_size:
            failures.append(
                {
                    "source_id": item.source_id,
                    "asset_id": item.asset_id,
                    "kind": kind,
                    "status": "size_mismatch",
                    "expected_size": expected_size,
                    "actual_size": content_length,
                }
            )
    return failures


def _s3_error_code(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error")
        if isinstance(error, dict):
            code = error.get("Code")
            return str(code) if code is not None else None
    return None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
