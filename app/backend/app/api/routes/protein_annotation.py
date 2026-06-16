from __future__ import annotations

from typing import Protocol

from fastapi import APIRouter, HTTPException, Request, status

from app.core.rate_limit import RATE_LIMIT_WORKBENCH, enforce_rate_limit
from app.schemas.protein_annotation import ProteinAnnotationRequest, ProteinDomainTrack

router = APIRouter(prefix="/api/v1", tags=["workbench"])

PROTEIN_ANNOTATION_SERVICE_UNAVAILABLE = "protein_annotation_service_unavailable"


class ProteinAnnotationServiceProtocol(Protocol):
    def annotate(self, request: ProteinAnnotationRequest) -> ProteinDomainTrack: ...


def _protein_annotation_service(request: Request) -> ProteinAnnotationServiceProtocol:
    service = getattr(request.app.state, "protein_annotation_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": PROTEIN_ANNOTATION_SERVICE_UNAVAILABLE,
                "message": "Protein annotation service is unavailable.",
                "warnings": [PROTEIN_ANNOTATION_SERVICE_UNAVAILABLE],
            },
        )
    return service


@router.post("/protein/annotate", response_model=ProteinDomainTrack)
def annotate_protein(payload: ProteinAnnotationRequest, request: Request) -> ProteinDomainTrack:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH)
    cache_only_payload = payload.model_copy(update={"allow_run": False, "use_cache": True})
    return _protein_annotation_service(request).annotate(cache_only_payload)
