from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
)
from app.services.paper_variants import PaperVariantsService
from app.services.pdf_text import extract_pdf_text

router = APIRouter(prefix="/api/v1/paper-variants", tags=["paper-variants"])

_PDF_MAGIC = b"%PDF-"
_ALLOWED_PDF_CONTENT_TYPES = {
    "",
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
}
_T = TypeVar("_T")


@router.post("/extract", response_model=PaperVariantsExtractResponse)
async def extract_paper_variants(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> PaperVariantsExtractResponse:
    enforce_rate_limit(request, RATE_LIMIT_CHAT, subject=principal.user_id)

    settings = request.app.state.settings
    paper_text, pdf_meta = await _paper_text_from_request(request)
    result = await _run_with_deadline(
        request,
        lambda: PaperVariantsService(settings).extract(paper_text, validate=True),
        timeout_attr="paper_variants_extract_timeout_seconds",
        timeout_detail="Paper variant extraction timed out.",
    )
    return _response(settings, result=result, pdf_meta=pdf_meta)


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
            detail=exc.errors(include_context=False),
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
) -> PaperVariantsExtractResponse:
    validated_count = sum(1 for variant in result.variants if variant.validated)
    return PaperVariantsExtractResponse(
        generated_at=datetime.now(timezone.utc),
        llm_provider=str(getattr(settings, "llm_provider", "mock")),
        pdf=pdf_meta,
        source_metadata=None,
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
) -> _T:
    timeout_seconds = _positive_float(
        getattr(request.app.state.settings, timeout_attr, None),
        default=10.0,
    )
    try:
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
