from fastapi import APIRouter, Request

from app.core.db import ping_database

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
