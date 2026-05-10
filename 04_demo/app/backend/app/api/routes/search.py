from fastapi import APIRouter, HTTPException, Query, Request, status

from app.schemas.search import SearchAnswerRequest, SearchAnswerResponse, SearchResponse

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    request: Request,
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    doc_type: str | None = None,
    run_status: str | None = None,
    review_status: str | None = None,
) -> SearchResponse:
    service = getattr(request.app.state, "search_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is unavailable.",
        )
    return service.search(
        query=q,
        limit=limit,
        doc_type=doc_type,
        run_status=run_status,
        review_status=review_status,
    )


@router.post("/answer", response_model=SearchAnswerResponse)
def search_answer(
    payload: SearchAnswerRequest,
    request: Request,
) -> SearchAnswerResponse:
    service = getattr(request.app.state, "search_answer_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search answer service is unavailable.",
        )
    return service.answer(payload)
