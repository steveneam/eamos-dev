from __future__ import annotations

import hashlib
import hmac
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import RATE_LIMIT_MATERIALIZATION_ADMIN, enforce_rate_limit
from app.services.materialization_orchestrator import (
    MaterializationOrchestratorError,
    materialize_all_from_manifest,
)

router = APIRouter(prefix="/api/v1/admin/materialization", tags=["admin-materialization"])


class MaterializationRunRequest(BaseModel):
    download_mode: Literal["rest", "s3_multipart"] = "s3_multipart"
    force: bool = False
    reconcile_supabase: bool = True
    require_ready: bool = False


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
