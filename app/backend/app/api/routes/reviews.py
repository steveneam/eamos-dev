from fastapi import APIRouter, Request

from app.schemas.draft import ClinicianReviewPayload, ReviewResult

router = APIRouter(tags=['reviews'])


@router.post('/api/v1/reports/{report_id}/review', response_model=ReviewResult)
def review_report(report_id: str, payload: ClinicianReviewPayload, request: Request) -> ReviewResult:
    return request.app.state.recommendation_service.apply_review(report_id, payload)


@router.post('/api/v1/runs/{run_id}/review', response_model=ReviewResult)
def review_run(run_id: str, payload: ClinicianReviewPayload, request: Request) -> ReviewResult:
    return request.app.state.recommendation_service.apply_review_to_run(run_id, payload)
