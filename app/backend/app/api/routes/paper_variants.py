from __future__ import annotations

import asyncio
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile as StarletteUploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import RATE_LIMIT_CHAT, enforce_rate_limit
from app.schemas.paper_variants import (
    PaperVariantsExtractRequest,
    PaperVariantsExtractResponse,
    PaperVariantsPdfMeta,
    PaperVariantsResult,
)
from app.schemas.workflow import ProcessingDisclosureV1, WorkflowRunV1
from app.services.paper_extract.document import PaperInputDocument, pdf_document, text_document
from app.services.paper_variants import PaperDocumentRunResult, PaperVariantsService
from app.services.pdf_text import PdfTextLimits, extract_pdf_text
from app.services.workflow import ProductWorkflowService, ProductWorkflowStateError

router = APIRouter(prefix="/api/v1/paper-variants", tags=["paper-variants"])

_PDF_MAGIC = b"%PDF-"
_ALLOWED_PDF_CONTENT_TYPES = {
    "",
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
}
_T = TypeVar("_T")
_CONSENT_HEADER = "X-Eamos-Processing-Consent"
_UPLOAD_CHUNK_BYTES = 64 * 1024
_MULTIPART_OVERHEAD_BYTES = 1024 * 1024
_MAX_JSON_BODY_BYTES = 4_100_000


@router.get("/disclosure", response_model=ProcessingDisclosureV1)
def paper_processing_disclosure(
    request: Request,
    input_class: Literal["paper_text", "pdf"] = Query(default="paper_text"),
    _principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> ProcessingDisclosureV1:
    return _processing_disclosure(request.app.state.settings, input_class=input_class)


@router.post("/extract", response_model=PaperVariantsExtractResponse)
async def extract_paper_variants(
    request: Request,
    response: Response,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> PaperVariantsExtractResponse:
    enforce_rate_limit(request, RATE_LIMIT_CHAT, subject=principal.user_id)

    settings = request.app.state.settings
    input_class = _request_input_class(request)
    disclosure = _processing_disclosure(settings, input_class=input_class)
    if disclosure.consent_required and request.headers.get(_CONSENT_HEADER, "").lower() != "true":
        raise HTTPException(
            status_code=428,
            detail="Explicit processing consent is required before sending publication input.",
        )
    paper_document, pdf_meta = await _paper_text_from_request(request)
    workflow = _workflow_service(request)
    run = workflow.create_run(
        kind="paper",
        user_id=principal.user_id,
        owner_provider=principal.provider,
        status="running",
        done=0,
        total=1,
        processing_disclosure=disclosure,
        source_disclosures=[_paper_source_disclosure(settings)],
    )
    response.headers["X-Workflow-Run-Id"] = run.run_id
    try:
        service = PaperVariantsService(settings)
        result = await _run_with_deadline(
            request,
            lambda: service.extract(paper_document, validate=True),
            timeout_attr="paper_variants_extract_timeout_seconds",
            timeout_detail="Paper variant extraction timed out.",
            bounded=True,
        )
        document_run = service.last_document_run
        if document_run is None:
            raise RuntimeError("paper_document_extraction_missing")
        extraction_response = _response(
            result=result,
            pdf_meta=pdf_meta,
            document_run=document_run,
        )
        run_status = "completed"
        if result.warnings and result.variants:
            run_status = "partial"
        elif result.warnings and not result.variants:
            run_status = "failed"
        workflow.update_run(
            run_id=run.run_id,
            user_id=principal.user_id,
            owner_provider=principal.provider,
            status=run_status,
            done=1 if run_status in {"completed", "partial"} else 0,
            total=1,
            warnings=result.warnings,
            result_payload=_sanitized_paper_result(extraction_response),
        )
        return extraction_response
    except asyncio.CancelledError:
        # An aborted browser fetch cancels the ASGI task while the threadpool
        # extractor may still be winding down. Keep the durable lifecycle
        # truthful and terminal; the repository guard prevents any late
        # non-cancelled update from overwriting this state.
        try:
            workflow.cancel_run(
                run_id=run.run_id,
                user_id=principal.user_id,
                owner_provider=principal.provider,
            )
        except ProductWorkflowStateError:
            # A response completed at the same instant as the disconnect.
            # Preserve that terminal state rather than manufacturing a cancel.
            pass
        raise
    except Exception as exc:
        workflow.update_run(
            run_id=run.run_id,
            user_id=principal.user_id,
            owner_provider=principal.provider,
            status="failed",
            done=0,
            total=1,
            warnings=[f"paper_extraction_failed:{type(exc).__name__}"],
        )
        raise


@router.get("/runs", response_model=list[WorkflowRunV1])
def list_paper_runs(
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
            kind="paper",
            limit=limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    if next_cursor:
        response.headers["X-Next-Cursor"] = next_cursor
    response.headers["X-Total-Count"] = str(total)
    return runs


@router.get("/runs/{run_id}", response_model=WorkflowRunV1)
def get_paper_run(
    run_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> WorkflowRunV1:
    run = _workflow_service(request).get_run(
        run_id=run_id,
        user_id=principal.user_id,
        owner_provider=principal.provider,
    )
    if run is None or run.kind != "paper":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper run not found.")
    return run


@router.get("/runs/{run_id}/result", response_model=PaperVariantsExtractResponse)
def get_paper_run_result(
    run_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> PaperVariantsExtractResponse:
    record = _workflow_service(request).get_record(
        run_id=run_id,
        user_id=principal.user_id,
        owner_provider=principal.provider,
    )
    if record is None or record.kind != "paper" or record.result_payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper run result not found.",
        )
    return PaperVariantsExtractResponse.model_validate(record.result_payload)


@router.post("/runs/{run_id}/cancel", response_model=WorkflowRunV1)
def cancel_paper_run(
    run_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> WorkflowRunV1:
    workflow = _workflow_service(request)
    record = workflow.get_record(
        run_id=run_id,
        user_id=principal.user_id,
        owner_provider=principal.provider,
    )
    if record is None or record.kind != "paper":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper run not found.")
    try:
        run = workflow.cancel_run(
            run_id=run_id,
            user_id=principal.user_id,
            owner_provider=principal.provider,
        )
    except ProductWorkflowStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None or run.kind != "paper":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper run not found.")
    return run


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper_run(
    run_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> Response:
    workflow = _workflow_service(request)
    record = workflow.get_record(
        run_id=run_id,
        user_id=principal.user_id,
        owner_provider=principal.provider,
    )
    if (
        record is None
        or record.kind != "paper"
        or not workflow.delete_run(
            run_id=run_id,
            user_id=principal.user_id,
            owner_provider=principal.provider,
        )
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper run not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _paper_text_from_request(
    request: Request,
) -> tuple[PaperInputDocument, PaperVariantsPdfMeta | None]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type == "application/json":
        return await _text_from_json(request), None
    if content_type == "multipart/form-data":
        return await _text_from_pdf_upload(request)
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Use application/json with text or multipart/form-data with a PDF file.",
    )


async def _text_from_json(request: Request) -> PaperInputDocument:
    try:
        raw_payload = await _read_json_body_bounded(request)
    except HTTPException:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be valid JSON.",
        ) from exc
    try:
        payload = PaperVariantsExtractRequest.model_validate(raw_payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[
                {key: value for key, value in error.items() if key != "input"}
                for error in exc.errors(include_context=False)
            ],
        ) from exc
    document = text_document(payload.text)
    if document.pages[0].quality == "garbled":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "paper_text_ambiguous",
                "requirement": "clean_selectable_text_or_human_review",
            },
        )
    return document


async def _read_json_body_bounded(request: Request) -> Any:
    declared_length = _declared_content_length(request)
    if declared_length is not None and declared_length > _MAX_JSON_BODY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="JSON body exceeds configured size limit.",
        )
    payload = bytearray()
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > _MAX_JSON_BODY_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="JSON body exceeds configured size limit.",
            )
        payload.extend(chunk)
    return json.loads(payload)


async def _text_from_pdf_upload(
    request: Request,
) -> tuple[PaperInputDocument, PaperVariantsPdfMeta]:
    size_limit = int(request.app.state.settings.max_upload_mb * 1024 * 1024)
    declared_length = _declared_content_length(request)
    if declared_length is not None and declared_length > size_limit + _MULTIPART_OVERHEAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Uploaded file exceeds configured size limit.",
        )
    try:
        form = await request.form(
            max_files=1,
            max_fields=2,
            max_part_size=_UPLOAD_CHUNK_BYTES,
        )
    except StarletteHTTPException as exc:
        if exc.status_code != status.HTTP_400_BAD_REQUEST:
            raise
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed multipart upload.",
        ) from exc
    upload = form.get("file") or form.get("pdf")
    if not isinstance(upload, StarletteUploadFile):
        await form.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multipart upload must include a PDF file field named 'file' or 'pdf'.",
        )

    temp_path: Path | None = None
    try:
        _validate_pdf_upload_metadata(upload)
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            dir=request.app.state.settings.upload_dir,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            size_bytes, source_sha256 = await _copy_upload_bounded(
                upload,
                handle,
                size_limit=size_limit,
            )
        extracted = await _run_with_deadline(
            request,
            lambda: extract_pdf_text(
                temp_path,
                engine=request.app.state.settings.pdf_text_engine,
                limits=PdfTextLimits(max_file_bytes=size_limit),
            ),
            timeout_attr="paper_variants_pdf_timeout_seconds",
            timeout_detail="PDF text extraction timed out.",
            bounded=True,
        )
        _validate_pdf_extraction(extracted)
        document = pdf_document(
            extracted,
            size_bytes=size_bytes,
            sha256=source_sha256,
        )
    finally:
        await form.close()
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    pdf_meta = PaperVariantsPdfMeta(
        page_count=int(extracted.get("page_count", 0) or 0),
        engine=str(extracted.get("engine") or request.app.state.settings.pdf_text_engine),
        warnings=list(extracted.get("warnings", [])),
    )
    return document, pdf_meta


def _declared_content_length(request: Request) -> int | None:
    value = request.headers.get("content-length")
    if value is None:
        return None
    try:
        declared = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Content-Length header.",
        ) from exc
    if declared < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Content-Length header.",
        )
    return declared


def _validate_pdf_upload_metadata(upload: StarletteUploadFile) -> None:
    filename = upload.filename or "paper.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF uploads are supported.",
        )
    content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in _ALLOWED_PDF_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF uploads are supported.",
        )


async def _copy_upload_bounded(
    upload: StarletteUploadFile,
    handle,
    *,
    size_limit: int,
) -> tuple[int, str]:
    total = 0
    digest = hashlib.sha256()
    prefix = b""
    while True:
        chunk = await upload.read(_UPLOAD_CHUNK_BYTES)
        if not chunk:
            break
        if not prefix:
            prefix = chunk[: len(_PDF_MAGIC)]
        total += len(chunk)
        if total > size_limit:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Uploaded file exceeds configured size limit.",
            )
        digest.update(chunk)
        handle.write(chunk)
    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if prefix != _PDF_MAGIC:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Uploaded file is not a valid PDF.",
        )
    return total, digest.hexdigest()


def _validate_pdf_extraction(extracted: dict[str, Any]) -> None:
    warnings = [str(item) for item in extracted.get("warnings", ())]
    page_count = int(extracted.get("page_count") or 0)
    pages = list(extracted.get("pages") or ())
    fatal_prefixes = (
        "pdf_engine_prohibited:",
        "pdf_engine_unavailable:",
        "unsupported_pdf_engine:",
        "pdf_parse_failed:",
        "pdf_page_parse_failed:",
        "pdf_page_limit_exceeded",
        "pdf_object_limit_exceeded",
        "pdf_stream_limit_exceeded:",
        "pdf_image_count_limit_exceeded:",
        "pdf_character_limit_exceeded:",
        "pdf_encrypted",
        "pdf_has_no_pages",
    )
    fatal = next((item for item in warnings if item.startswith(fatal_prefixes)), None)
    if fatal or page_count < 1 or len(pages) != page_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "paper_pdf_unavailable",
                "requirement": fatal or "complete_page_preserving_extraction",
            },
        )
    quality = {str(page.get("quality")) for page in pages}
    if quality and quality <= {"empty", "image_only"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "ocr_required",
                "requirement": "local_ocr_or_selectable_text",
            },
        )
    if quality and quality <= {"garbled", "empty", "image_only"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "paper_text_ambiguous",
                "requirement": "local_ocr_or_human_review",
            },
        )


def _response(
    *,
    result: PaperVariantsResult,
    pdf_meta: PaperVariantsPdfMeta | None,
    document_run: PaperDocumentRunResult,
) -> PaperVariantsExtractResponse:
    extraction = document_run.document_extraction
    validated_count = sum(resolution.status == "resolved" for resolution in extraction.resolutions)
    return PaperVariantsExtractResponse(
        generated_at=datetime.now(timezone.utc),
        llm_provider="eamos_deterministic",
        pdf=pdf_meta,
        source_metadata=document_run.source_metadata,
        candidate_count=len(extraction.mentions),
        validated_count=validated_count,
        variants=result.variants,
        warnings=result.warnings,
        provenance=result.provenance,
        document_extraction=extraction,
        execution_disclosure=extraction.execution_disclosure,
    )


async def _run_with_deadline(
    request: Request,
    func: Callable[[], _T],
    *,
    timeout_attr: str,
    timeout_detail: str,
    bounded: bool = False,
) -> _T:
    timeout_seconds = _positive_float(
        getattr(request.app.state.settings, timeout_attr, None),
        default=10.0,
    )
    try:
        if bounded:
            semaphore = _paper_semaphore(request)
            async with semaphore:
                return await asyncio.wait_for(run_in_threadpool(func), timeout=timeout_seconds)
        return await asyncio.wait_for(run_in_threadpool(func), timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=timeout_detail,
        ) from exc


def _positive_float(value, *, default: float) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return default
    return coerced if coerced > 0 else default


def _request_input_class(request: Request) -> Literal["paper_text", "pdf"]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type == "application/json":
        return "paper_text"
    if content_type == "multipart/form-data":
        return "pdf"
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Use application/json with text or multipart/form-data with a PDF file.",
    )


def _processing_disclosure(
    settings: Any,
    *,
    input_class: Literal["paper_text", "pdf"],
) -> ProcessingDisclosureV1:
    provider = str(getattr(settings, "llm_provider", "mock") or "mock").lower()
    if provider == "gateway":
        return ProcessingDisclosureV1(
            execution="external_provider",
            provider_id="vercel_ai_gateway",
            provider_label="Vercel AI Gateway",
            input_classes=[input_class],
            raw_input_persisted=False,
            retention="none",
            expires_at=None,
            user_deletable=True,
            consent_required=True,
            warnings=[
                "Publication input leaves Eamos for extraction; provider retention is governed by the configured gateway account."
            ],
        )
    return ProcessingDisclosureV1(
        execution="eamos_backend",
        provider_id="eamos_deterministic_extractor",
        provider_label="Eamos deterministic extractor",
        input_classes=[input_class],
        raw_input_persisted=False,
        retention="request_lifetime",
        expires_at=None,
        user_deletable=True,
        consent_required=False,
        warnings=[],
    )


def _paper_source_disclosure(_settings: Any) -> dict[str, Any]:
    return {
        "source_status": "local_provider",
        "provider_id": "eamos_deterministic_extractor",
        "provider_label": "Eamos deterministic paper extractor",
        "source_version": "paper-variants-v2",
        "cache_status": None,
        "warnings": [],
        "requirements": [],
    }


def _sanitized_paper_result(response: PaperVariantsExtractResponse) -> dict[str, Any]:
    payload = response.model_dump(mode="json")
    for variant in payload.get("variants", []):
        variant.pop("evidence_quote", None)
    return payload


def _workflow_service(request: Request) -> ProductWorkflowService:
    service = getattr(request.app.state, "product_workflow_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow persistence is unavailable.",
        )
    return service


def _paper_semaphore(request: Request) -> asyncio.Semaphore:
    semaphore = getattr(request.app.state, "paper_variants_semaphore", None)
    if semaphore is None:
        limit = max(
            1,
            min(
                8,
                int(getattr(request.app.state.settings, "paper_variants_max_concurrency", 2)),
            ),
        )
        semaphore = asyncio.Semaphore(limit)
        request.app.state.paper_variants_semaphore = semaphore
    return semaphore
