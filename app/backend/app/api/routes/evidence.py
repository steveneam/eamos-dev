from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import RATE_LIMIT_EVIDENCE, enforce_rate_limit
from app.schemas.evidence import EvidenceSubmissionRequest, EvidenceSubmissionResponse

router = APIRouter(prefix="/api/v1/evidence-submissions", tags=["evidence-submissions"])


@router.post("", response_model=EvidenceSubmissionResponse, status_code=status.HTTP_201_CREATED)
def submit_evidence(
    payload: EvidenceSubmissionRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> EvidenceSubmissionResponse:
    enforce_rate_limit(request, RATE_LIMIT_EVIDENCE, subject=principal.user_id)
    service = getattr(request.app.state, "evidence_submission_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Evidence submission service is unavailable.",
        )
    return service.submit(payload, principal)
