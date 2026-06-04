from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.schemas.batch import (
    BatchCreateRequest,
    BatchCreateResponse,
    BatchJob,
    BatchJobQuery,
    BatchUploadResponse,
)
from app.services.batch import BatchService

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])


@router.post("/uploads", response_model=BatchUploadResponse)
async def upload_batch_file(
    request: Request,
    file: UploadFile = File(...),
) -> BatchUploadResponse:
    payload = await file.read()
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded VCF file is empty.",
        )
    upload_ref = _service(request).store_upload(payload, filename=file.filename)
    return BatchUploadResponse(upload_ref=upload_ref)


@router.post("", response_model=BatchCreateResponse)
def create_batch_job(payload: BatchCreateRequest, request: Request) -> BatchCreateResponse:
    try:
        return _service(request).create_job(payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload ref '{exc.args[0]}' was not found.",
        ) from exc


@router.get("/{job_id}", response_model=BatchJob)
def get_batch_job(
    job_id: str,
    request: Request,
    limit: int = 100,
    cursor: str | None = None,
) -> BatchJob:
    query = BatchJobQuery(limit=limit, cursor=cursor)
    job = _service(request).get_job(job_id, limit=query.limit, cursor=query.cursor)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job '{job_id}' was not found.",
        )
    return job


def _service(request: Request) -> BatchService:
    service = getattr(request.app.state, "batch_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Batch service is unavailable.",
        )
    return service
