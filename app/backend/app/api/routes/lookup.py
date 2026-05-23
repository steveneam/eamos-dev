from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.lookup import (
    LookupRequest,
    LookupResponse,
    PublicationPageRequest,
    SearchInputParseRequest,
    SearchInputParseResponse,
)
from app.schemas.run import PublicationLiterature

router = APIRouter(prefix="/api/v1/lookup", tags=["lookup"])


@router.post("", response_model=LookupResponse)
def variant_lookup(
    payload: LookupRequest,
    request: Request,
    refresh: bool = False,
) -> LookupResponse:
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    return service.lookup(payload, refresh=refresh)


@router.post("/parse", response_model=SearchInputParseResponse)
def parse_lookup_input(
    payload: SearchInputParseRequest,
    request: Request,
) -> SearchInputParseResponse:
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    return service.parse_search_input(payload)


@router.post("/publications", response_model=PublicationLiterature)
def lookup_publications(
    payload: PublicationPageRequest,
    request: Request,
) -> PublicationLiterature:
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    try:
        return service.page_publications(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
