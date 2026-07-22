from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.panels import Panel, PanelListResponse, PanelResolveRequest
from app.services.panels import PanelService

router = APIRouter(prefix="/api/v1/panels", tags=["panels"])


@router.get("", response_model=PanelListResponse)
def list_panels(request: Request) -> PanelListResponse:
    return _service(request).list_panels()


@router.post("/resolve", response_model=Panel)
def resolve_panel(payload: PanelResolveRequest, request: Request) -> Panel:
    return _service(request).resolve(payload)


@router.get("/{slug}", response_model=Panel)
def get_panel(slug: str, request: Request) -> Panel:
    panel = _service(request).get_panel(slug)
    if panel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Panel '{slug}' was not found.",
        )
    return panel


def _service(request: Request) -> PanelService:
    service = getattr(request.app.state, "panel_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Panel service is unavailable.",
        )
    return service
