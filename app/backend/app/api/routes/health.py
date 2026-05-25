from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from app.core.db import ping_database
from app.services.crispr_design import (
    CRISPR_PROVIDER_CRISPRSCORE_R,
    CRISPR_PROVIDER_LOCAL_DETERMINISTIC,
)

router = APIRouter(tags=["health"])


# NOTE: This endpoint is intentionally public in dev so the frontend can probe
# mode flags (llm_provider, use_real_apis) without auth. If /healthz is ever
# auth-gated for production, split the mode flags into a separate public
# GET /api/v1/runtime-info behind no auth dependency.
@router.get("/healthz")
def healthz(request: Request) -> dict[str, object]:
    ping_database(request.app.state.db_session_factory)
    settings = request.app.state.settings
    return {
        "status": "ok",
        "database": "ok",
        "llm_provider": settings.llm_provider,
        "use_real_apis": settings.use_real_apis,
    }


@router.get("/api/v1/health/provider-cache")
def provider_cache_health(request: Request) -> dict[str, object]:
    ping_database(request.app.state.db_session_factory)
    settings = request.app.state.settings
    source_cache_repo = getattr(request.app.state, "source_cache_repo", None)
    source_cache: dict[str, Any] = {"enabled": source_cache_repo is not None}
    if source_cache_repo is not None:
        source_cache.update(source_cache_repo.health_summary())

    return {
        "status": "ok",
        "database": "ok",
        "source_cache": source_cache,
        "providers": {
            "crispr": _crispr_provider_health(settings),
        },
    }


def _crispr_provider_health(settings) -> dict[str, object]:
    configured_provider = (settings.crispr_provider or "").strip().lower()
    if not configured_provider:
        configured_provider = CRISPR_PROVIDER_LOCAL_DETERMINISTIC

    local_provider = {
        "available": True,
        "status": "available",
        "score_sources": {
            "on_target": "heuristic",
            "off_target": "local_hsu_mit_in_context",
        },
    }
    crisprscore_provider = _crisprscore_r_health(settings, configured_provider)
    providers = {
        CRISPR_PROVIDER_LOCAL_DETERMINISTIC: local_provider,
        CRISPR_PROVIDER_CRISPRSCORE_R: crisprscore_provider,
    }
    configured_status = providers.get(configured_provider)
    configured_available = (
        bool(configured_status and configured_status["available"])
        if configured_provider in providers
        else False
    )
    return {
        "configured_provider": configured_provider,
        "available": configured_available,
        "status": "available" if configured_available else "unavailable",
        "providers": providers,
        "platform_gated_models": ["DeepHF", "DeepCpf1", "enPAM+GB"],
    }


def _crisprscore_r_health(settings, configured_provider: str) -> dict[str, object]:
    configured = configured_provider == CRISPR_PROVIDER_CRISPRSCORE_R
    checks: dict[str, object] = {
        "rscript": False,
        "jsonlite_package": None,
        "crisprscore_package": None,
        "rule_set3_conda_env_configured": settings.crispr_ruleset3_conda_env is not None,
        "lindel_conda_env_configured": settings.crispr_lindel_conda_env is not None,
    }
    if not configured:
        return {
            "available": False,
            "status": "disabled",
            "checks": checks,
        }

    rscript = _resolve_executable(settings.crispr_rscript_path)
    if rscript is None:
        return {
            "available": False,
            "status": "unavailable",
            "checks": checks,
        }

    checks["rscript"] = True
    package_checks = _probe_crisprscore_r_packages(rscript)
    checks.update(package_checks)
    available = bool(checks["jsonlite_package"] and checks["crisprscore_package"])
    return {
        "available": available,
        "status": "available" if available else "unavailable",
        "checks": checks,
    }


def _resolve_executable(path: str | Path) -> str | None:
    raw_path = str(path)
    resolved = shutil.which(raw_path)
    if resolved:
        return resolved
    candidate = Path(raw_path)
    if candidate.is_file():
        return str(candidate)
    return None


def _probe_crisprscore_r_packages(rscript: str) -> dict[str, bool | None]:
    script = (
        "cat('{\"jsonlite_package\":'); "
        "cat(if (requireNamespace('jsonlite', quietly=TRUE)) 'true' else 'false'); "
        "cat(',\"crisprscore_package\":'); "
        "cat(if (requireNamespace('crisprScore', quietly=TRUE)) 'true' else 'false'); "
        "cat('}')"
    )
    try:
        completed = subprocess.run(
            [rscript, "--vanilla", "-e", script],
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"jsonlite_package": None, "crisprscore_package": None}

    if completed.returncode != 0:
        return {"jsonlite_package": None, "crisprscore_package": None}
    try:
        decoded = json.loads(completed.stdout or "{}")
    except ValueError:
        return {"jsonlite_package": None, "crisprscore_package": None}
    return {
        "jsonlite_package": (
            decoded["jsonlite_package"]
            if isinstance(decoded.get("jsonlite_package"), bool)
            else None
        ),
        "crisprscore_package": (
            decoded["crisprscore_package"]
            if isinstance(decoded.get("crisprscore_package"), bool)
            else None
        ),
    }
