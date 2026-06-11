from __future__ import annotations

from typing import NoReturn, Protocol

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status

from app.core.rate_limit import RATE_LIMIT_WORKBENCH, enforce_rate_limit
from app.schemas.workbench import (
    AlignRequest,
    AlignResponse,
    AlignTraceRequest,
    AlignTraceResponse,
    CrisprOffTargetRequest,
    CrisprOffTargetResponse,
    CrisprRequest,
    CrisprResponse,
    CrisprScreeningPrimerRequest,
    CrisprScreeningPrimerResponse,
    CrisprSsodnRequest,
    CrisprSsodnResponse,
    CrisprTideResponse,
    PrimerRequest,
    PrimerResponse,
)
from app.services.trace_parser import TRACE_MAX_DECODED_BYTES
from app.services.workbench_design import (
    WORKBENCH_SERVICE_UNAVAILABLE,
    WorkbenchDesignError,
)

router = APIRouter(prefix="/api/v1", tags=["workbench"])


class WorkbenchService(Protocol):
    def design_primers(self, payload: PrimerRequest) -> PrimerResponse: ...
    def design_guides(self, payload: CrisprRequest) -> CrisprResponse: ...
    def enumerate_crispr_offtargets(
        self,
        payload: CrisprOffTargetRequest,
    ) -> CrisprOffTargetResponse: ...
    def design_crispr_screening_primers(
        self,
        payload: CrisprScreeningPrimerRequest,
    ) -> CrisprScreeningPrimerResponse: ...
    def design_crispr_ssodn(self, payload: CrisprSsodnRequest) -> CrisprSsodnResponse: ...
    def align(self, payload: AlignRequest) -> AlignResponse: ...
    def analyze_trace(self, payload: AlignTraceRequest) -> AlignTraceResponse: ...
    def analyze_crispr_tide(
        self,
        *,
        control_bytes: bytes,
        edited_bytes: bytes,
        cut_site_index: int,
    ) -> CrisprTideResponse: ...


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


async def _read_trace_upload(file: UploadFile) -> bytes:
    return await file.read(TRACE_MAX_DECODED_BYTES + 1)


@router.post("/primer", response_model=PrimerResponse)
def design_primers(payload: PrimerRequest, request: Request) -> PrimerResponse:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH)
    try:
        return _workbench_service(request).design_primers(payload)
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)


@router.post("/crispr", response_model=CrisprResponse)
def design_guides(payload: CrisprRequest, request: Request) -> CrisprResponse:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH)
    try:
        return _workbench_service(request).design_guides(payload)
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)


@router.post("/crispr/offtargets", response_model=CrisprOffTargetResponse)
def enumerate_crispr_offtargets(
    payload: CrisprOffTargetRequest,
    request: Request,
) -> CrisprOffTargetResponse:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH)
    try:
        return _workbench_service(request).enumerate_crispr_offtargets(payload)
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)


@router.post("/crispr/screening-primers", response_model=CrisprScreeningPrimerResponse)
def design_crispr_screening_primers(
    payload: CrisprScreeningPrimerRequest,
    request: Request,
) -> CrisprScreeningPrimerResponse:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH)
    try:
        return _workbench_service(request).design_crispr_screening_primers(payload)
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)


@router.post("/crispr/ssodn", response_model=CrisprSsodnResponse)
def design_crispr_ssodn(
    payload: CrisprSsodnRequest,
    request: Request,
) -> CrisprSsodnResponse:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH)
    try:
        return _workbench_service(request).design_crispr_ssodn(payload)
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)


@router.post("/align", response_model=AlignResponse)
def align(payload: AlignRequest, request: Request) -> AlignResponse:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH)
    try:
        return _workbench_service(request).align(payload)
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)


@router.post("/align/trace", response_model=AlignTraceResponse)
def analyze_trace(payload: AlignTraceRequest, request: Request) -> AlignTraceResponse:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH)
    try:
        return _workbench_service(request).analyze_trace(payload)
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)


@router.post("/crispr/tide", response_model=CrisprTideResponse)
async def analyze_crispr_tide(
    request: Request,
    cut_site_index: int = Query(..., ge=1),
    control_file: UploadFile = File(...),
    edited_file: UploadFile = File(...),
) -> CrisprTideResponse:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH)
    control_bytes = await _read_trace_upload(control_file)
    edited_bytes = await _read_trace_upload(edited_file)
    try:
        return _workbench_service(request).analyze_crispr_tide(
            control_bytes=control_bytes,
            edited_bytes=edited_bytes,
            cut_site_index=cut_site_index,
        )
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)
