from __future__ import annotations

import asyncio
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import RATE_LIMIT_CHAT, enforce_rate_limit
from app.schemas.paper_variants import (
    PaperVariantsExtractRequest,
    PaperVariantsExtractResponse,
    PaperVariantsPdfMeta,
    PaperVariantsResult,
    PaperSourceMetadata,
)
from app.schemas.workflow import ProcessingDisclosureV1, WorkflowRunV1
from app.services.paper_variants import PaperVariantsService
from app.services.pdf_text import extract_pdf_text
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
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_PMID_RE = re.compile(r"\bPMID\s*[:#]?\s*(\d{6,9})\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


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
    paper_text, pdf_meta = await _paper_text_from_request(request)
    source_metadata = _source_metadata(paper_text)
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
        result = await _run_with_deadline(
            request,
            lambda: PaperVariantsService(settings).extract(paper_text, validate=True),
            timeout_attr="paper_variants_extract_timeout_seconds",
            timeout_detail="Paper variant extraction timed out.",
            bounded=True,
        )
        extraction_response = _response(
            settings,
            result=result,
            pdf_meta=pdf_meta,
            source_metadata=source_metadata,
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
    if record is None or record.kind != "paper" or not workflow.delete_run(
        run_id=run_id,
        user_id=principal.user_id,
        owner_provider=principal.provider,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper run not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _paper_text_from_request(
    request: Request,
) -> tuple[str, PaperVariantsPdfMeta | None]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type == "application/json":
        return await _text_from_json(request), None
    if content_type == "multipart/form-data":
        return await _text_from_pdf_upload(request)
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Use application/json with text or multipart/form-data with a PDF file.",
    )


async def _text_from_json(request: Request) -> str:
    try:
        payload = PaperVariantsExtractRequest.model_validate(await request.json())
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {key: value for key, value in error.items() if key != "input"}
                for error in exc.errors(include_context=False)
            ],
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be valid JSON.",
        ) from exc
    return payload.text


async def _text_from_pdf_upload(
    request: Request,
) -> tuple[str, PaperVariantsPdfMeta]:
    form = await request.form()
    upload = form.get("file") or form.get("pdf")
    if not isinstance(upload, StarletteUploadFile):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multipart upload must include a PDF file field named 'file' or 'pdf'.",
        )

    _validate_pdf_upload_metadata(upload)
    content = await upload.read()
    temp_path: Path | None = None
    try:
        _validate_pdf_upload_content(request, content)
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            dir=request.app.state.settings.upload_dir,
            delete=False,
        ) as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        extracted = await _run_with_deadline(
            request,
            lambda: extract_pdf_text(
                temp_path,
                engine=request.app.state.settings.pdf_text_engine,
            ),
            timeout_attr="paper_variants_pdf_timeout_seconds",
            timeout_detail="PDF text extraction timed out.",
        )
    finally:
        await upload.close()
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
    return str(extracted.get("text") or ""), pdf_meta


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


def _validate_pdf_upload_content(request: Request, content: bytes) -> None:
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    size_limit = request.app.state.settings.max_upload_mb * 1024 * 1024
    if len(content) > size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file exceeds configured size limit.",
        )
    if not content.startswith(_PDF_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Uploaded file is not a valid PDF.",
        )


def _response(
    settings: Any,
    *,
    result: PaperVariantsResult,
    pdf_meta: PaperVariantsPdfMeta | None,
    source_metadata: PaperSourceMetadata | None,
) -> PaperVariantsExtractResponse:
    validated_count = sum(1 for variant in result.variants if variant.validated)
    return PaperVariantsExtractResponse(
        generated_at=datetime.now(timezone.utc),
        llm_provider=str(getattr(settings, "llm_provider", "mock")),
        pdf=pdf_meta,
        source_metadata=source_metadata,
        candidate_count=len(result.variants),
        validated_count=validated_count,
        variants=result.variants,
        warnings=result.warnings,
        provenance=result.provenance,
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


def _paper_source_disclosure(settings: Any) -> dict[str, Any]:
    provider = str(getattr(settings, "llm_provider", "mock") or "mock").lower()
    if provider == "gateway":
        return {
            "source_status": "local_provider",
            "provider_id": "vercel_ai_gateway",
            "provider_label": "Vercel AI Gateway extraction",
            "source_version": str(getattr(settings, "ai_gateway_model", "configured-model")),
            "cache_status": None,
            "warnings": [],
            "requirements": [],
        }
    return {
        "source_status": "local_provider",
        "provider_id": "eamos_deterministic_extractor",
        "provider_label": "Eamos deterministic paper extractor",
        "source_version": "paper-variants-v1",
        "cache_status": None,
        "warnings": [],
        "requirements": [],
    }


def _source_metadata(text: str) -> PaperSourceMetadata | None:
    bounded = text[:20_000]
    lines = [line.strip() for line in bounded.splitlines() if line.strip()]
    doi_match = _DOI_RE.search(bounded)
    pmid_match = _PMID_RE.search(bounded)
    year_match = _YEAR_RE.search(bounded)
    title = None
    if (
        len(lines) >= 2
        and 8 <= len(lines[0]) <= 500
        and not re.search(r"\b[cpgrmno]\.", lines[0], flags=re.IGNORECASE)
    ):
        title = lines[0]
    metadata = PaperSourceMetadata(
        title=title,
        year=year_match.group(0) if year_match else None,
        doi=doi_match.group(0).rstrip(".,;)") if doi_match else None,
        pmid=pmid_match.group(1) if pmid_match else None,
    )
    return metadata if any((metadata.title, metadata.year, metadata.doi, metadata.pmid)) else None


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
