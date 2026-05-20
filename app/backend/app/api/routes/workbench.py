from __future__ import annotations

from typing import NoReturn, Protocol

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.workbench import (
    AlignRequest,
    AlignResponse,
    CrisprRequest,
    CrisprResponse,
    PrimerRequest,
    PrimerResponse,
)
from app.services.workbench_design import (
    WORKBENCH_SERVICE_UNAVAILABLE,
    WorkbenchDesignError,
)

router = APIRouter(prefix="/api/v1", tags=["workbench"])


class WorkbenchService(Protocol):
    def design_primers(self, payload: PrimerRequest) -> PrimerResponse: ...
    def design_guides(self, payload: CrisprRequest) -> CrisprResponse: ...
    def align(self, payload: AlignRequest) -> AlignResponse: ...


def _workbench_service(request: Request) -> WorkbenchService:
    service = getattr(request.app.state, "workbench_design_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": WORKBENCH_SERVICE_UNAVAILABLE,
                "message": "Workbench design service is unavailable.",
                "warnings": [WORKBENCH_SERVICE_UNAVAILABLE],
            },
        )
    return service


def _raise_workbench_error(error: WorkbenchDesignError) -> NoReturn:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.to_http_detail(),
    ) from error


@router.post("/primer", response_model=PrimerResponse)
def design_primers(payload: PrimerRequest, request: Request) -> PrimerResponse:
    try:
        return _workbench_service(request).design_primers(payload)
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)


@router.post("/crispr", response_model=CrisprResponse)
def design_guides(payload: CrisprRequest, request: Request) -> CrisprResponse:
    try:
        return _workbench_service(request).design_guides(payload)
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)


@router.post("/align", response_model=AlignResponse)
def align(payload: AlignRequest, request: Request) -> AlignResponse:
    try:
        return _workbench_service(request).align(payload)
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)
