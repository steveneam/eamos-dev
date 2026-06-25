from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.rate_limit import RATE_LIMIT_LOOKUP, enforce_rate_limit
from app.schemas.lookup import (
    LookupInitialSummaryResponse,
    LookupRequest,
    LookupResponse,
    LookupSectionFetchRequest,
    LookupSectionFetchResponse,
    PublicationPageRequest,
    SearchInputParseRequest,
    SearchInputParseResponse,
)
from app.schemas.run import PublicationLiterature
from app.services.lookup_timing import LOOKUP_TIMING_HEADER

router = APIRouter(prefix="/api/v1/lookup", tags=["lookup"])

LOOKUP_EAGER_RESPONSE_EXCLUDE = {
    "report_payload": {
        "publications_literature": True,
        "report_profile": {
            "computational_deep_dive": True,
            "expert_panel": True,
            "therapies_trials": True,
        },
    }
}


@router.post("", response_model=LookupResponse)
def variant_lookup(
    payload: LookupRequest,
    request: Request,
    response: Response,
    refresh: bool = False,
    include_lazy_sections: bool = False,
) -> LookupResponse | JSONResponse:
    enforce_rate_limit(request, RATE_LIMIT_LOOKUP, subject=_lookup_subject(payload))
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    lookup_response = service.lookup(payload, refresh=refresh)
    timing_header = _lookup_timing_header(service, lookup_response)
    if timing_header:
        response.headers[LOOKUP_TIMING_HEADER] = timing_header
    if include_lazy_sections:
        return lookup_response
    return JSONResponse(
        content=jsonable_encoder(lookup_response, exclude=LOOKUP_EAGER_RESPONSE_EXCLUDE),
        headers={LOOKUP_TIMING_HEADER: timing_header} if timing_header else None,
    )


@router.post("/summary", response_model=LookupInitialSummaryResponse)
def lookup_summary(
    payload: LookupRequest,
    request: Request,
    response: Response,
    refresh: bool = False,
) -> LookupInitialSummaryResponse:
    enforce_rate_limit(request, RATE_LIMIT_LOOKUP, subject=_lookup_subject(payload))
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    summary = service.lookup_summary(payload, refresh=refresh)
    timing_header = _lookup_timing_header(service, summary)
    if timing_header:
        response.headers[LOOKUP_TIMING_HEADER] = timing_header
    return summary


@router.post("/sections", response_model=LookupSectionFetchResponse)
def lookup_sections(
    payload: LookupSectionFetchRequest,
    request: Request,
    response: Response,
    refresh: bool = False,
) -> LookupSectionFetchResponse:
    enforce_rate_limit(request, RATE_LIMIT_LOOKUP, subject=_lookup_subject(payload))
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    sections = service.lookup_sections(payload, refresh=refresh)
    timing_header = _lookup_timing_header(service, sections)
    if timing_header:
        response.headers[LOOKUP_TIMING_HEADER] = timing_header
    return sections


@router.post("/parse", response_model=SearchInputParseResponse)
def parse_lookup_input(
    payload: SearchInputParseRequest,
    request: Request,
) -> SearchInputParseResponse:
    enforce_rate_limit(request, RATE_LIMIT_LOOKUP, subject=payload.search_text)
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    # Public parse must not let callers force the heavier coordinate-resolution path.
    safe_payload = payload.model_copy(update={"resolve_coordinates": False})
    return service.parse_search_input(safe_payload)


@router.post("/publications", response_model=PublicationLiterature)
def lookup_publications(
    payload: PublicationPageRequest,
    request: Request,
    refresh: bool = False,
) -> PublicationLiterature:
    enforce_rate_limit(
        request,
        RATE_LIMIT_LOOKUP,
        subject=":".join(part for part in (payload.gene, payload.cdna) if part),
    )
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    try:
        if refresh:
            payload = payload.model_copy(update={"refresh": True})
        return service.page_publications(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


def _lookup_subject(payload: LookupRequest) -> str | None:
    if payload.raw_search_text:
        return payload.raw_search_text
    if payload.selected_candidate_id:
        return payload.selected_candidate_id
    return ":".join(
        part
        for part in (payload.gene, payload.cdna, payload.transcript, payload.protein_change)
        if part
    )


def _lookup_timing_header(service, response) -> str | None:
    settings = getattr(service, "settings", None)
    if not bool(getattr(settings, "lookup_timing_diagnostics_enabled", False)):
        return None
    return getattr(response, "lookup_timing_header", None)
