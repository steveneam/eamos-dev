from __future__ import annotations

from typing import NoReturn, Protocol

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.gene_viewer import GeneViewerRequest, GeneViewerResponse
from app.services.gene_viewer import (
    GENE_VIEWER_SERVICE_UNAVAILABLE,
    GeneViewerError,
)

router = APIRouter(prefix="/api/v1", tags=["workbench"])


class GeneViewerServiceProtocol(Protocol):
    def build_viewer(self, payload: GeneViewerRequest) -> GeneViewerResponse: ...


def _gene_viewer_service(request: Request) -> GeneViewerServiceProtocol:
    service = getattr(request.app.state, "gene_viewer_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": GENE_VIEWER_SERVICE_UNAVAILABLE,
                "message": "Gene viewer service is unavailable.",
                "warnings": [GENE_VIEWER_SERVICE_UNAVAILABLE],
            },
        )
    return service


def _raise_gene_viewer_error(error: GeneViewerError) -> NoReturn:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.to_http_detail(),
    ) from error


@router.post("/viewer", response_model=GeneViewerResponse)
def build_viewer(payload: GeneViewerRequest, request: Request) -> GeneViewerResponse:
    try:
        return _gene_viewer_service(request).build_viewer(payload)
    except GeneViewerError as exc:
        _raise_gene_viewer_error(exc)
