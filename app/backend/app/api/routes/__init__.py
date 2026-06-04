from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.batch import router as batch_router
from app.api.routes.chat import router as chat_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.gene_viewer import router as gene_viewer_router
from app.api.routes.health import router as health_router
from app.api.routes.lookup import router as lookup_router
from app.api.routes.panels import router as panels_router
from app.api.routes.payments import router as payments_router
from app.api.routes.protein_annotation import router as protein_annotation_router
from app.api.routes.reports import router as reports_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.runs import router as runs_router
from app.api.routes.search import router as search_router
from app.api.routes.workbench import router as workbench_router


def build_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(auth_router)
    router.include_router(batch_router)
    router.include_router(chat_router)
    router.include_router(evidence_router)
    router.include_router(gene_viewer_router)
    router.include_router(lookup_router)
    router.include_router(panels_router)
    router.include_router(payments_router)
    router.include_router(protein_annotation_router)
    router.include_router(reports_router)
    router.include_router(reviews_router)
    router.include_router(runs_router)
    router.include_router(search_router)
    router.include_router(workbench_router)
    router.include_router(health_router)
    return router
