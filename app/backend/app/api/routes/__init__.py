from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.lookup import router as lookup_router
from app.api.routes.reports import router as reports_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.runs import router as runs_router
from app.api.routes.search import router as search_router
from app.api.routes.workbench import router as workbench_router


def build_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(auth_router)
    router.include_router(chat_router)
    router.include_router(lookup_router)
    router.include_router(reports_router)
    router.include_router(reviews_router)
    router.include_router(runs_router)
    router.include_router(search_router)
    router.include_router(workbench_router)
    router.include_router(health_router)
    return router
