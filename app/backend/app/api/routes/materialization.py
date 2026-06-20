from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import RATE_LIMIT_MATERIALIZATION_ADMIN, enforce_rate_limit
from app.repos.supabase_local_model_cache_repo import SupabaseLocalModelCacheError
from app.services.clinical_source_tables import ClinicalSourceTableError
from app.services.materialization_orchestrator import (
    MaterializationOrchestratorError,
    materialize_all_from_manifest,
)
from app.services.source_imports import (
    SourceImportError,
    apply_clinical_source_import_bundle,
    build_clinical_release_source_import_bundle,
)

router = APIRouter(prefix="/api/v1/admin/materialization", tags=["admin-materialization"])


class MaterializationRunRequest(BaseModel):
    download_mode: Literal["rest", "s3_multipart"] = "s3_multipart"
    force: bool = False
    reconcile_supabase: bool = True
    require_ready: bool = False


class ClinicalReleaseImportRequest(BaseModel):
    run_smoke: bool = True
    mondo_source_version: str | None = Field(default=None, max_length=160)
    hpo_source_version: str | None = Field(default=None, max_length=160)
    clingen_source_version: str | None = Field(default=None, max_length=160)
    gencc_source_version: str | None = Field(default=None, max_length=160)


@router.post("/run")
def run_materialization(
    payload: MaterializationRunRequest,
    request: Request,
    x_eamos_admin_token: str | None = Header(default=None, alias="X-Eamos-Admin-Token"),
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> dict[str, object]:
    settings = request.app.state.settings
    _require_admin_materialization(settings, token=x_eamos_admin_token)
    enforce_rate_limit(request, RATE_LIMIT_MATERIALIZATION_ADMIN, subject=principal.user_id)
    store = (
        getattr(request.app.state, "supabase_local_model_cache_store", None)
        if payload.reconcile_supabase
        else None
    )
    try:
        report = materialize_all_from_manifest(
            settings,
            manifest_path=_resolve_manifest_path(settings),
            force=payload.force,
            download_mode=payload.download_mode,
            reconcile_supabase=payload.reconcile_supabase,
            materialization_store=store,
            max_items=settings.admin_materialization_max_items,
        )
    except MaterializationOrchestratorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "mode": "eamos_materialization_admin_run",
                "status": "failed",
                "code": exc.code,
                "message": str(exc),
                "details": exc.details,
                "local_path_values_emitted": False,
                "object_uri_values_emitted": False,
                "secret_values_emitted": False,
            },
        ) from exc

    if payload.require_ready and report["ready"] is not True:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=report)
    return report


@router.post("/clinical-release/import")
def run_clinical_release_import(
    payload: ClinicalReleaseImportRequest,
    request: Request,
    x_eamos_admin_token: str | None = Header(default=None, alias="X-Eamos-Admin-Token"),
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> dict[str, object]:
    settings = request.app.state.settings
    _require_admin_materialization(settings, token=x_eamos_admin_token)
    enforce_rate_limit(request, RATE_LIMIT_MATERIALIZATION_ADMIN, subject=principal.user_id)
    store = getattr(request.app.state, "supabase_local_model_cache_store", None)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_admin_failure_detail(
                mode="eamos_admin_clinical_release_import",
                code="clinical_release_import_store_unavailable",
                message=(
                    "Clinical release import requires the configured private Supabase store "
                    "inside the running backend process."
                ),
            ),
        )

    source_asset_root = _resolve_clinical_source_asset_root(settings)
    source_version_overrides = {
        source_id: version
        for source_id, version in (
            ("mondo_disease_ontology", payload.mondo_source_version),
            ("human_phenotype_ontology", payload.hpo_source_version),
            ("clingen_gene_validity", payload.clingen_source_version),
            ("gencc_download", payload.gencc_source_version),
        )
        if version
    }
    try:
        bundle = build_clinical_release_source_import_bundle(
            source_asset_root=source_asset_root,
            source_version_overrides=source_version_overrides or None,
        )
        if payload.run_smoke:
            smoke_test = getattr(store, "smoke_test", None)
            if callable(smoke_test):
                smoke_test()
        result = apply_clinical_source_import_bundle(store, bundle)
    except (ClinicalSourceTableError, SourceImportError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_admin_failure_detail(
                mode="eamos_admin_clinical_release_import",
                code=getattr(exc, "code", "clinical_release_import_failed"),
                message=str(exc),
                details=getattr(exc, "details", None),
            ),
        ) from exc
    except SupabaseLocalModelCacheError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_admin_failure_detail(
                mode="eamos_admin_clinical_release_import",
                code="clinical_release_import_supabase_failed",
                message="Supabase clinical release import failed.",
                details={"error_type": type(exc).__name__},
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_admin_failure_detail(
                mode="eamos_admin_clinical_release_import",
                code="clinical_release_import_unexpected_error",
                message="Clinical release import failed.",
                details={"error_type": type(exc).__name__},
            ),
        ) from exc

    return {
        "mode": "eamos_admin_clinical_release_import",
        "status": "applied",
        "ready": True,
        "applied": True,
        "import_scope": "release_files",
        "asset_role": bundle.asset_role,
        "source_version_count": len(result.source_versions),
        "source_versions": [
            {
                "source_id": version.source_id,
                "source_release": version.source_release,
                "license_status": version.license_status,
                "row_count": version.row_count,
            }
            for version in result.source_versions
        ],
        "row_counts": dict(result.row_counts),
        "smoke_test": "used" if payload.run_smoke else "skipped",
        "guardrails": {
            "startup_download": "not_used",
            "render_disk_seed": "not_used",
            "storage_uploads": "not_used",
            "public_storage_fallback": "blocked",
            "frontend_direct_sql": "blocked",
            "local_evidence_enabled_flip": "not_used",
            "provider_flip": "not_used",
            "render_env_or_deploy_mutation": "not_used",
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
            "object_uri_values_in_output": "blocked",
        },
        "apply_result": {
            "applied": result.applied,
            "row_counts": dict(result.row_counts),
        },
        "local_path_values_emitted": False,
        "object_uri_values_emitted": False,
        "secret_values_emitted": False,
    }


def _require_admin_materialization(settings, *, token: str | None) -> None:
    if not getattr(settings, "admin_materialization_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found.",
        )
    expected_hash = getattr(settings, "admin_materialization_token_sha256", None)
    if not expected_hash or not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin materialization is not authorized.",
        )
    actual_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(actual_hash, str(expected_hash).strip().lower()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin materialization is not authorized.",
        )


def _resolve_manifest_path(settings):
    manifest_path = settings.admin_materialization_manifest_path
    return manifest_path if manifest_path.is_absolute() else settings.backend_root / manifest_path


def _resolve_clinical_source_asset_root(settings) -> Path:
    root = settings.admin_materialization_clinical_source_asset_root
    return root if root.is_absolute() else settings.backend_root / root


def _admin_failure_detail(
    *,
    mode: str,
    code: str,
    message: str,
    details: Any | None = None,
) -> dict[str, object]:
    return {
        "mode": mode,
        "status": "failed",
        "code": code,
        "message": message,
        "details": _sanitize_admin_details(details or {}),
        "local_path_values_emitted": False,
        "object_uri_values_emitted": False,
        "secret_values_emitted": False,
    }


def _sanitize_admin_details(details: Any) -> Any:
    if isinstance(details, dict):
        return {
            str(key): _sanitize_admin_detail_value(str(key), value)
            for key, value in details.items()
        }
    return _sanitize_admin_detail_value("", details)


def _sanitize_admin_detail_value(key: str, value: Any) -> Any:
    lowered_key = key.lower()
    if any(token in lowered_key for token in ("path", "uri", "url", "secret", "token", "key")):
        return "[redacted]"
    if isinstance(value, dict):
        return _sanitize_admin_details(value)
    if isinstance(value, (list, tuple)):
        return [_sanitize_admin_detail_value(key, item) for item in value[:20]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str) and _looks_sensitive_detail(value):
            return "[redacted]"
        return value
    return type(value).__name__


def _looks_sensitive_detail(value: str) -> bool:
    lowered = value.lower()
    return (
        "supabase://" in lowered
        or "postgresql://" in lowered
        or "postgresql+psycopg://" in lowered
        or "\\" in value
        or "/var/data/" in lowered
        or "/app/" in lowered
    )
