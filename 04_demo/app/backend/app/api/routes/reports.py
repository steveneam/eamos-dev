from fastapi import APIRouter, File, Form, Request, UploadFile, status

from app.schemas.report import ReportKind, ReportUploadResponse

router = APIRouter(prefix='/api/v1/reports', tags=['reports'])


@router.post('/upload', response_model=ReportUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_report(request: Request, file: UploadFile = File(...), report_kind: ReportKind = Form(default='test')) -> ReportUploadResponse:
    return await request.app.state.intake_service.ingest_upload(file, report_kind=report_kind)
