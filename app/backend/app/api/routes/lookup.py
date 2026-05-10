from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.lookup import LookupRequest, LookupResponse

router = APIRouter(prefix="/api/v1/lookup", tags=["lookup"])


@router.post("", response_model=LookupResponse)
def variant_lookup(
    payload: LookupRequest,
    request: Request,
) -> LookupResponse:
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    return service.lookup(payload)
