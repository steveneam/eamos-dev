from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import RATE_LIMIT_BATCH_JOB, RATE_LIMIT_BATCH_UPLOAD, enforce_rate_limit
from app.schemas.batch import (
    BATCH_MAX_VARIANTS,
    BatchCreateRequest,
    BatchCreateResponse,
    BatchJob,
    BatchJobQuery,
    BatchUploadResponse,
)
from app.schemas.workflow import WorkflowRunV1
from app.services.batch import BatchService
from app.services.workflow import ProductWorkflowService, ProductWorkflowStateError
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
            owner_user_id=principal.user_id,
            owner_provider=principal.provider,
            max_decompressed_bytes=size_limit,
            max_variants=BATCH_MAX_VARIANTS,
        )
    except VcfIngestLimitError as exc:
        status_code = (
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if exc.code
            in {
                "vcf_decompressed_size_limit_exceeded",
                "vcf_variant_count_limit_exceeded",
            }
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc
    return BatchUploadResponse(upload_ref=upload_ref)


@router.post("", response_model=BatchCreateResponse)
def create_batch_job(
    payload: BatchCreateRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> BatchCreateResponse:
    enforce_rate_limit(request, RATE_LIMIT_BATCH_JOB, subject=principal.user_id)
    try:
        return _service(request).create_job(
            payload,
            owner_user_id=principal.user_id,
            owner_provider=principal.provider,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload ref '{exc.args[0]}' was not found.",
        ) from exc


@router.get("/runs", response_model=list[WorkflowRunV1])
def list_batch_runs(
    request: Request,
    response: Response,
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=512),
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> list[WorkflowRunV1]:
    try:
        runs, next_cursor, total = _workflow_service(request).list_runs(
            user_id=principal.user_id,
            owner_provider=principal.provider,
            kind="batch",
            limit=limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if next_cursor:
        response.headers["X-Next-Cursor"] = next_cursor
    response.headers["X-Total-Count"] = str(total)
    return runs


@router.get("/{job_id}", response_model=BatchJob)
def get_batch_job(
    job_id: str,
    request: Request,
    limit: int = 100,
    cursor: str | None = None,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> BatchJob:
    query = BatchJobQuery(limit=limit, cursor=cursor)
    try:
        job = _service(request).get_job(
            job_id,
            limit=query.limit,
            cursor=query.cursor,
            owner_user_id=principal.user_id,
            owner_provider=principal.provider,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job '{job_id}' was not found.",
        )
    return job


@router.post("/{job_id}/cancel", response_model=WorkflowRunV1)
def cancel_batch_job(
    job_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> WorkflowRunV1:
    try:
        run = _service(request).cancel_job(
            job_id,
            owner_user_id=principal.user_id,
            owner_provider=principal.provider,
        )
    except ProductWorkflowStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job '{job_id}' was not found.",
        )
    return run


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch_job(
    job_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> Response:
    if not _service(request).delete_job(
        job_id,
        owner_user_id=principal.user_id,
        owner_provider=principal.provider,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job '{job_id}' was not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{job_id}/export")
def export_batch_job(
    job_id: str,
    request: Request,
    format: Literal["tsv", "manifest"] = Query(default="tsv"),
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
):
    workflow = _workflow_service(request)
    record = workflow.get_record(
        run_id=job_id,
        user_id=principal.user_id,
        owner_provider=principal.provider,
    )
    if record is None or record.kind != "batch":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job '{job_id}' was not found.",
        )
    safe_job_id = record.run_id
    if format == "manifest":
        body = {
            "schema_version": "workflow_manifest.v1",
            "run": ProductWorkflowService._as_contract(record).model_dump(mode="json"),
            "result_count": record.total,
            "generated_at": datetime.now(UTC).isoformat(),
            "raw_input_included": False,
        }
        return JSONResponse(
            content=body,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_job_id}-manifest.json"'
            },
        )
    return StreamingResponse(
        _batch_tsv_rows(
            workflow,
            run_id=record.run_id,
            user_id=principal.user_id,
            owner_provider=principal.provider,
        ),
        media_type="text/tab-separated-values; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_job_id}.tsv"'},
    )


def _service(request: Request) -> BatchService:
    service = getattr(request.app.state, "batch_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Batch service is unavailable.",
        )
    service.bind_lookup_service(getattr(request.app.state, "lookup_service", None))
    return service


def _workflow_service(request: Request) -> ProductWorkflowService:
    service = getattr(request.app.state, "product_workflow_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow persistence is unavailable.",
        )
    return service


def _batch_tsv_rows(
    workflow: ProductWorkflowService,
    *,
    run_id: str,
    user_id: str,
    owner_provider: str,
):
    columns = (
        "variant_key",
        "state",
        "gene",
        "hgvs_c",
        "hgvs_p",
        "clinvar_verdict",
        "gnomad_af",
        "acmg_classification",
        "report_href",
        "warnings",
    )
    yield _tsv_line(columns)
    cursor: str | None = None
    exported = 0
    while exported < BATCH_MAX_VARIANTS:
        page = workflow.page_items(
            run_id=run_id,
            user_id=user_id,
            owner_provider=owner_provider,
            limit=min(500, BATCH_MAX_VARIANTS - exported),
            cursor=cursor,
        )
        if page is None:
            return
        items, cursor, _total = page
        for item in items:
            values = [item.get(column) for column in columns]
            values[-1] = ";".join(str(value) for value in (values[-1] or []))
            yield _tsv_line(values)
        exported += len(items)
        if not cursor or not items:
            return


def _tsv_line(values) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")
    writer.writerow([_safe_tsv_cell(value) for value in values])
    return buffer.getvalue()


def _safe_tsv_cell(value) -> str | int | float:
    if value is None:
        return ""
    if not isinstance(value, str):
        return value
    if value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{value}"
    return value


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
