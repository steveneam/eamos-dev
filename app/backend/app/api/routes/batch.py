from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import RATE_LIMIT_BATCH_UPLOAD, enforce_rate_limit
from app.schemas.batch import (
    BATCH_MAX_VARIANTS,
    BatchCreateRequest,
    BatchCreateResponse,
    BatchJob,
    BatchJobQuery,
    BatchUploadResponse,
)
from app.services.batch import BatchService
from app.services.vcf_ingest import VcfIngestLimitError

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])
_UPLOAD_READ_CHUNK_BYTES = 1024 * 1024


@router.post("/uploads", response_model=BatchUploadResponse)
async def upload_batch_file(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> BatchUploadResponse:
    enforce_rate_limit(request, RATE_LIMIT_BATCH_UPLOAD, subject=principal.user_id)

    size_limit = _upload_size_limit_bytes(request)
    _reject_oversized_content_length(request, size_limit=size_limit)
    file = await _uploaded_vcf_file(request)
    try:
        payload = await _read_upload_bytes(file, size_limit=size_limit)
    finally:
        await file.close()
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded VCF file is empty.",
        )
    try:
        upload_ref = _service(request).store_upload(
            payload,
            filename=file.filename,
            max_decompressed_bytes=size_limit,
            max_variants=BATCH_MAX_VARIANTS,
        )
    except VcfIngestLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
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


def _upload_size_limit_bytes(request: Request) -> int:
    max_upload_mb = int(getattr(request.app.state.settings, "max_upload_mb", 20) or 20)
    return max(1, max_upload_mb) * 1024 * 1024


def _reject_oversized_content_length(request: Request, *, size_limit: int) -> None:
    header = request.headers.get("content-length")
    if header is None:
        return
    try:
        content_length = int(header)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Content-Length header.",
        ) from exc
    if content_length > size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded VCF file exceeds configured size limit.",
        )


async def _uploaded_vcf_file(request: Request) -> StarletteUploadFile:
    form = await request.form()
    upload = form.get("file") or form.get("vcf")
    if not isinstance(upload, StarletteUploadFile):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multipart upload must include a VCF file field named 'file' or 'vcf'.",
        )
    return upload


async def _read_upload_bytes(upload: StarletteUploadFile, *, size_limit: int) -> bytes:
    chunks: list[bytes] = []
    bytes_seen = 0
    while True:
        chunk = await upload.read(_UPLOAD_READ_CHUNK_BYTES)
        if not chunk:
            break
        bytes_seen += len(chunk)
        if bytes_seen > size_limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploaded VCF file exceeds configured size limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks)
