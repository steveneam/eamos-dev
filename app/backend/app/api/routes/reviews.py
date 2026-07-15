from fastapi import APIRouter, Depends, Request

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.schemas.draft import ClinicianReviewPayload, ReviewResult

router = APIRouter(tags=["reviews"])


@router.post("/api/v1/reports/{report_id}/review", response_model=ReviewResult)
def review_report(
    report_id: str,
    payload: ClinicianReviewPayload,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> ReviewResult:
    return request.app.state.recommendation_service.apply_review(
        report_id,
        payload,
        owner=principal.owner,
    )
