from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
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
from app.services.lookup_sections import (
    build_lookup_initial_summary,
    build_lookup_section_fetch_response,
)

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
    response = service.lookup(payload, refresh=refresh)
    if include_lazy_sections:
        return response
    return JSONResponse(content=jsonable_encoder(response, exclude=LOOKUP_EAGER_RESPONSE_EXCLUDE))


@router.post("/summary", response_model=LookupInitialSummaryResponse)
def lookup_summary(
    payload: LookupRequest,
    request: Request,
    refresh: bool = False,
) -> LookupInitialSummaryResponse:
    enforce_rate_limit(request, RATE_LIMIT_LOOKUP, subject=_lookup_subject(payload))
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    response = service.lookup(payload, refresh=refresh)
    return build_lookup_initial_summary(response)


@router.post("/sections", response_model=LookupSectionFetchResponse)
def lookup_sections(
    payload: LookupSectionFetchRequest,
    request: Request,
    refresh: bool = False,
) -> LookupSectionFetchResponse:
    enforce_rate_limit(request, RATE_LIMIT_LOOKUP, subject=_lookup_subject(payload))
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    lookup_payload = LookupRequest.model_validate(payload.model_dump(exclude={"include"}))
    response = service.lookup(lookup_payload, refresh=refresh)
    return build_lookup_section_fetch_response(response, payload.include)


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
