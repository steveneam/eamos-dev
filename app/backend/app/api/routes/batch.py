from __future__ import annotations

import csv
from dataclasses import dataclass
from hashlib import sha256
import io
import json
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.datastructures import FormData, UploadFile as StarletteUploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import RATE_LIMIT_BATCH_JOB, RATE_LIMIT_BATCH_UPLOAD, enforce_rate_limit
from app.schemas.batch import (
    BATCH_MAX_VARIANTS,
    BatchCreateRequest,
    BatchCreateResponse,
    BatchExportV2,
    BatchJob,
    BatchJobQuery,
    BatchResult,
    BatchUploadResponse,
)
from app.schemas.workflow import WorkflowRunV1
from app.services.batch import BatchQueueUnavailable, BatchService
from app.services.workflow import ProductWorkflowService, ProductWorkflowStateError
from app.services.vcf_ingest import VcfIngestLimitError

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])
_EXPORT_FORMATS = ("tsv", "csv", "jsonl", "vcf")
_EXPORT_COLUMNS = (
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


@router.post("/uploads", response_model=BatchUploadResponse)
async def upload_batch_file(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> BatchUploadResponse:
    enforce_rate_limit(request, RATE_LIMIT_BATCH_UPLOAD, subject=principal.user_id)

    size_limit = _upload_size_limit_bytes(request)
    _reject_oversized_content_length(request, size_limit=size_limit)
    form, file = await _uploaded_vcf_file(request)
    filename = file.filename
    try:
        await file.seek(0)
        upload_ref = _service(request).store_upload_file(
            file.file,
            filename=filename,
            owner_user_id=principal.user_id,
            owner_provider=principal.provider,
            max_compressed_bytes=size_limit,
            max_decompressed_bytes=min(512 * 1024 * 1024, size_limit * 20),
            post_filter_variant_cap=BATCH_MAX_VARIANTS,
        )
    except VcfIngestLimitError as exc:
        if exc.code == "vcf_intake_time_limit_exceeded":
            status_code = status.HTTP_408_REQUEST_TIMEOUT
        elif exc.code in {
            "vcf_compressed_size_limit_exceeded",
            "vcf_decompressed_size_limit_exceeded",
            "vcf_raw_record_limit_exceeded",
            "vcf_line_size_limit_exceeded",
        }:
            status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        else:
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    finally:
        await form.close()
    try:
        return _service(request).upload_response(
            upload_ref,
            owner_user_id=principal.user_id,
            owner_provider=principal.provider,
        )
    except KeyError as exc:  # pragma: no cover - protected by the same service call
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload receipt expired before it could be returned.",
        ) from exc


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
    except VcfIngestLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except BatchQueueUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
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
    source_snapshot_id: str | None = None,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> BatchJob:
    query = BatchJobQuery(
        limit=limit,
        cursor=cursor,
        source_snapshot_id=source_snapshot_id,
    )
    try:
        job = _service(request).get_job(
            job_id,
            limit=query.limit,
            cursor=query.cursor,
            source_snapshot_id=query.source_snapshot_id,
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
    format: Literal["tsv", "csv", "jsonl", "vcf", "manifest"] = Query(default="tsv"),
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
    if record.status in {"draft", "queued", "running"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Batch export is available only after the job reaches a terminal state.",
        )
    safe_job_id = record.run_id
    runtime_payload = record.result_payload or {}
    source_snapshot = runtime_payload.get("source_snapshot_v2")
    source_snapshot_id = (
        str(source_snapshot.get("snapshot_id"))
        if isinstance(source_snapshot, dict) and source_snapshot.get("snapshot_id")
        else None
    )
    if format == "manifest":
        body = {
            "schema_version": (
                "batch_export_manifest.v2"
                if source_snapshot_id is not None
                else "workflow_manifest.v1"
            ),
            "run": ProductWorkflowService._as_contract(record).model_dump(mode="json"),
            "result_count": record.total,
            "generated_at": datetime.now(UTC).isoformat(),
            "raw_input_included": False,
            "source_snapshot_v2": source_snapshot,
            "exports": (
                [
                    _export_receipt(
                        workflow,
                        run_id=record.run_id,
                        user_id=principal.user_id,
                        owner_provider=principal.provider,
                        export_format=export_format,
                        source_snapshot_id=source_snapshot_id,
                    ).model_dump(mode="json")
                    for export_format in _EXPORT_FORMATS
                ]
                if source_snapshot_id is not None
                else []
            ),
        }
        return JSONResponse(
            content=body,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_job_id}-manifest.json"',
                "Cache-Control": "private, no-store",
            },
        )
    digest, row_count = _measure_export(
        workflow,
        run_id=record.run_id,
        user_id=principal.user_id,
        owner_provider=principal.provider,
        export_format=format,
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_job_id}.{format}"',
        "Cache-Control": "private, no-store",
        "X-Content-SHA256": digest,
        "X-Row-Count": str(row_count),
    }
    if source_snapshot_id is not None:
        headers["X-Source-Snapshot-ID"] = source_snapshot_id
        headers["X-Eamos-Export-ID"] = _export_id(
            run_id=record.run_id,
            export_format=format,
            source_snapshot_id=source_snapshot_id,
            digest=digest,
        )
    return StreamingResponse(
        (
            chunk.payload
            for chunk in _batch_export_chunks(
                workflow,
                run_id=record.run_id,
                user_id=principal.user_id,
                owner_provider=principal.provider,
                export_format=format,
            )
        ),
        media_type={
            "tsv": "text/tab-separated-values; charset=utf-8",
            "csv": "text/csv; charset=utf-8",
            "jsonl": "application/x-ndjson; charset=utf-8",
            "vcf": "text/vcf; charset=utf-8",
        }[format],
        headers=headers,
    )


def _export_receipt(
    workflow: ProductWorkflowService,
    *,
    run_id: str,
    user_id: str,
    owner_provider: str,
    export_format: Literal["tsv", "csv", "jsonl", "vcf"],
    source_snapshot_id: str,
) -> BatchExportV2:
    digest, row_count = _measure_export(
        workflow,
        run_id=run_id,
        user_id=user_id,
        owner_provider=owner_provider,
        export_format=export_format,
    )
    return BatchExportV2(
        export_id=_export_id(
            run_id=run_id,
            export_format=export_format,
            source_snapshot_id=source_snapshot_id,
            digest=digest,
        ),
        format=export_format,
        state="ready",
        source_snapshot_id=source_snapshot_id,
        row_count=row_count,
        sha256=digest,
        expires_at=None,
    )


def _export_id(
    *,
    run_id: str,
    export_format: str,
    source_snapshot_id: str,
    digest: str,
) -> str:
    identity = sha256(
        f"{run_id}\n{export_format}\n{source_snapshot_id}\n{digest}".encode("utf-8")
    ).hexdigest()[:20]
    return f"batch-export-{identity}"


@dataclass(frozen=True)
class _ExportChunk:
    payload: bytes
    is_result_row: bool = False


def _measure_export(
    workflow: ProductWorkflowService,
    *,
    run_id: str,
    user_id: str,
    owner_provider: str,
    export_format: Literal["tsv", "csv", "jsonl", "vcf"],
) -> tuple[str, int]:
    digest = sha256()
    row_count = 0
    for chunk in _batch_export_chunks(
        workflow,
        run_id=run_id,
        user_id=user_id,
        owner_provider=owner_provider,
        export_format=export_format,
    ):
        digest.update(chunk.payload)
        row_count += int(chunk.is_result_row)
    return digest.hexdigest(), row_count


def _batch_export_chunks(
    workflow: ProductWorkflowService,
    *,
    run_id: str,
    user_id: str,
    owner_provider: str,
    export_format: Literal["tsv", "csv", "jsonl", "vcf"],
):
    if export_format in {"tsv", "csv"}:
        delimiter = "\t" if export_format == "tsv" else ","
        yield _ExportChunk(_delimited_line(_EXPORT_COLUMNS, delimiter=delimiter).encode("utf-8"))
    elif export_format == "vcf":
        yield _ExportChunk(
            (
                "##fileformat=VCFv4.2\n"
                "##reference=GRCh38\n"
                "##source=Eamos-Batch-V2\n"
                '##INFO=<ID=EAMOS_STATE,Number=1,Type=String,Description="Eamos row state">\n'
                '##INFO=<ID=GENE,Number=1,Type=String,Description="Canonical gene">\n'
                '##INFO=<ID=HGVSC,Number=1,Type=String,Description="Canonical coding HGVS">\n'
                '##INFO=<ID=HGVSP,Number=1,Type=String,Description="Canonical protein HGVS">\n'
                '##INFO=<ID=CLINVAR,Number=1,Type=String,Description="Direct Report ClinVar value">\n'
                '##INFO=<ID=GNOMAD_AF,Number=1,Type=Float,Description="Direct Report gnomAD AF">\n'
                '##INFO=<ID=ACMG,Number=1,Type=String,Description="Direct Report ACMG value">\n'
                '##INFO=<ID=SOURCE_SNAPSHOT,Number=1,Type=String,Description="Eamos source snapshot">\n'
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
            ).encode("utf-8")
        )
    for item in _iter_batch_results(
        workflow,
        run_id=run_id,
        user_id=user_id,
        owner_provider=owner_provider,
    ):
        if export_format == "jsonl":
            yield _ExportChunk(
                (json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"),
                is_result_row=True,
            )
            continue
        if export_format in {"tsv", "csv"}:
            values = [item.get(column) for column in _EXPORT_COLUMNS]
            values[-1] = ";".join(str(value) for value in (values[-1] or []))
            delimiter = "\t" if export_format == "tsv" else ","
            yield _ExportChunk(
                _delimited_line(values, delimiter=delimiter).encode("utf-8"),
                is_result_row=True,
            )
            continue
        vcf_row = _batch_vcf_row(item)
        if vcf_row is not None:
            yield _ExportChunk(vcf_row.encode("utf-8"), is_result_row=True)


def _iter_batch_results(
    workflow: ProductWorkflowService,
    *,
    run_id: str,
    user_id: str,
    owner_provider: str,
):
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
        items, cursor, total = page
        if total > BATCH_MAX_VARIANTS:
            raise ValueError("Batch export exceeds the validated post-filter result cap.")
        for item in items:
            yield BatchResult.model_validate(item).model_dump(mode="json")
        exported += len(items)
        if not cursor or not items:
            return


def _batch_vcf_row(item: dict) -> str | None:
    identity = item.get("allele_identity_v2") or {}
    allele = identity.get("normalized") or {}
    try:
        chromosome = str(allele["chromosome"])
        position = int(allele["position"])
        reference = str(allele["reference"])
        alternate = str(allele["alternate"])
    except (KeyError, TypeError, ValueError):
        parts = str(item.get("variant_key") or "").split("-", 3)
        if len(parts) != 4:
            return None
        chromosome, position_text, reference, alternate = parts
        try:
            position = int(position_text)
        except ValueError:
            return None
    if not reference or not alternate:
        return None
    info_values = {
        "EAMOS_STATE": item.get("state"),
        "GENE": item.get("gene"),
        "HGVSC": item.get("hgvs_c"),
        "HGVSP": item.get("hgvs_p"),
        "CLINVAR": item.get("clinvar_verdict"),
        "GNOMAD_AF": item.get("gnomad_af"),
        "ACMG": item.get("acmg_classification"),
        "SOURCE_SNAPSHOT": item.get("source_snapshot_id"),
    }
    info = (
        ";".join(
            f"{key}={quote(str(value), safe='._:-')}"
            for key, value in info_values.items()
            if value is not None
        )
        or "."
    )
    return f"{chromosome}\t{position}\t.\t{reference}\t{alternate}\t.\t.\t{info}\n"


def _batch_tsv_rows(
    workflow: ProductWorkflowService,
    *,
    run_id: str,
    user_id: str,
    owner_provider: str,
):
    for chunk in _batch_export_chunks(
        workflow,
        run_id=run_id,
        user_id=user_id,
        owner_provider=owner_provider,
        export_format="tsv",
    ):
        yield chunk.payload.decode("utf-8")


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


def _tsv_line(values) -> str:
    return _delimited_line(values, delimiter="\t")


def _delimited_line(values, *, delimiter: Literal["\t", ","]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
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


async def _uploaded_vcf_file(request: Request) -> tuple[FormData, StarletteUploadFile]:
    try:
        form = await request.form(max_files=1, max_fields=2, max_part_size=64 * 1024)
    except StarletteHTTPException as exc:
        if exc.status_code != status.HTTP_400_BAD_REQUEST:
            raise
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed multipart upload.",
        ) from exc
    upload = form.get("file") or form.get("vcf")
    if not isinstance(upload, StarletteUploadFile):
        await form.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multipart upload must include a VCF file field named 'file' or 'vcf'.",
        )
    return form, upload
