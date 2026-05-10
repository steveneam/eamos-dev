from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from app.schemas.chat import RunChatRequest, RunChatResponse
from app.schemas.draft import ApproveResult, ClinicianReviewPayload, DropResult, ReportDraftUpdatePayload, ReviewResult, RunDropPayload
from app.schemas.run import RunRequest, RunResponse

router = APIRouter(prefix='/api/v1', tags=['runs'])


@router.post('/runs', response_model=RunResponse)
def create_run(payload: RunRequest, request: Request) -> RunResponse:
    return request.app.state.workflow_service.create_run(payload)


@router.get('/runs/{run_id}', response_model=RunResponse)
def get_run(run_id: str, request: Request) -> RunResponse:
    return request.app.state.workflow_service.get_run(run_id)


@router.post('/runs/{run_id}/review', response_model=ReviewResult)
def review_run(run_id: str, payload: ClinicianReviewPayload, request: Request) -> ReviewResult:
    return request.app.state.recommendation_service.apply_review(run_id, payload)


@router.patch('/runs/{run_id}/report-payload', response_model=RunResponse)
def update_run_report_payload(run_id: str, payload: ReportDraftUpdatePayload, request: Request) -> RunResponse:
    return request.app.state.report_draft_service.update_report_payload(run_id, payload)


@router.post('/runs/{run_id}/chat', response_model=RunChatResponse)
def chat_on_run(run_id: str, payload: RunChatRequest, request: Request) -> RunChatResponse:
    return request.app.state.run_chat_service.answer(run_id, payload)


@router.post('/runs/{run_id}/approve', response_model=ApproveResult)
def approve_run(run_id: str, request: Request) -> ApproveResult:
    return request.app.state.final_report_service.approve(run_id)


@router.post('/runs/{run_id}/drop', response_model=DropResult)
def drop_run(run_id: str, payload: RunDropPayload, request: Request) -> DropResult:
    return request.app.state.final_report_service.drop(run_id, review_note=(payload.review_note or None))


@router.api_route('/runs/{run_id}/pdf', methods=['GET', 'HEAD'])
def get_run_pdf(run_id: str, request: Request) -> FileResponse:
    path = request.app.state.final_report_service.get_pdf(run_id)
    return FileResponse(
        path=path,
        media_type='application/pdf',
        filename=path.name,
        content_disposition_type='inline',
    )
