from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import RATE_LIMIT_SEARCH, enforce_rate_limit
from app.schemas.search import (
    SearchAccessContext,
    SearchAnswerRequest,
    SearchAnswerResponse,
    SearchResponse,
)

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    request: Request,
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    doc_type: str | None = None,
    run_status: str | None = None,
    review_status: str | None = None,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> SearchResponse:
    enforce_rate_limit(request, RATE_LIMIT_SEARCH, subject=principal.user_id)
    service = getattr(request.app.state, "search_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is unavailable.",
        )
    return service.search(
        query=q,
        access_context=SearchAccessContext(user_id=principal.user_id),
        limit=limit,
        doc_type=doc_type,
        run_status=run_status,
        review_status=review_status,
    )


@router.post("/answer", response_model=SearchAnswerResponse)
def search_answer(
    payload: SearchAnswerRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> SearchAnswerResponse:
    enforce_rate_limit(request, RATE_LIMIT_SEARCH, subject=principal.user_id)
    service = getattr(request.app.state, "search_answer_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search answer service is unavailable.",
        )
    return service.answer(payload, access_context=SearchAccessContext(user_id=principal.user_id))
