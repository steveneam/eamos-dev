from __future__ import annotations

from typing import NoReturn, Protocol

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, status
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import RATE_LIMIT_WORKBENCH, enforce_rate_limit
from app.schemas.workflow import ProcessingDisclosureV1, WorkflowContextV1, WorkflowRunV1
from app.schemas.workbench import (
    AlignReferenceRequest,
    AlignReferenceResponse,
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
from app.services.workflow import ProductWorkflowService
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
    def resolve_align_reference(
        self,
        payload: AlignReferenceRequest,
    ) -> AlignReferenceResponse: ...
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


@router.get("/workbench/trace-disclosure", response_model=ProcessingDisclosureV1)
def trace_processing_disclosure(
    _principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> ProcessingDisclosureV1:
    return _trace_processing_disclosure()


@router.post("/workbench/workspaces", response_model=WorkflowRunV1)
def create_workbench_workspace(
    payload: WorkflowContextV1,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> WorkflowRunV1:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH, subject=principal.user_id)
    return _workflow_service(request).create_run(
        kind="workbench",
        user_id=principal.user_id,
        owner_provider=principal.provider,
        status="draft",
        context=payload,
        done=0,
        total=0,
    )


@router.get("/workbench/workspaces/{workspace_id}", response_model=WorkflowRunV1)
def get_workbench_workspace(
    workspace_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> WorkflowRunV1:
    run = _workflow_service(request).get_run(
        run_id=workspace_id,
        user_id=principal.user_id,
        owner_provider=principal.provider,
    )
    if run is None or run.kind != "workbench":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workbench workspace not found.",
        )
    return run


@router.delete("/workbench/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workbench_workspace(
    workspace_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> Response:
    workflow = _workflow_service(request)
    record = workflow.get_record(
        run_id=workspace_id,
        user_id=principal.user_id,
        owner_provider=principal.provider,
    )
    if record is None or record.kind != "workbench" or not workflow.delete_run(
        run_id=workspace_id,
        user_id=principal.user_id,
        owner_provider=principal.provider,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workbench workspace not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.post("/align/reference", response_model=AlignReferenceResponse)
def resolve_align_reference(
    payload: AlignReferenceRequest,
    request: Request,
) -> AlignReferenceResponse:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH)
    try:
        return _workbench_service(request).resolve_align_reference(payload)
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)


@router.post("/align/trace", response_model=AlignTraceResponse)
def analyze_trace(
    payload: AlignTraceRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> AlignTraceResponse:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH, subject=principal.user_id)
    try:
        return _workbench_service(request).analyze_trace(payload)
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)


@router.post("/crispr/tide", response_model=CrisprTideResponse)
async def analyze_crispr_tide(
    request: Request,
    cut_site_index: int = Query(..., ge=1),
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> CrisprTideResponse:
    enforce_rate_limit(request, RATE_LIMIT_WORKBENCH, subject=principal.user_id)
    form = await request.form()
    control_file = form.get("control_file")
    edited_file = form.get("edited_file")
    if not isinstance(control_file, StarletteUploadFile) or not isinstance(
        edited_file, StarletteUploadFile
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multipart upload requires control_file and edited_file trace files.",
        )
    try:
        control_bytes = await _read_trace_upload(control_file)
        edited_bytes = await _read_trace_upload(edited_file)
    finally:
        await control_file.close()
        await edited_file.close()
    try:
        return _workbench_service(request).analyze_crispr_tide(
            control_bytes=control_bytes,
            edited_bytes=edited_bytes,
            cut_site_index=cut_site_index,
        )
    except WorkbenchDesignError as exc:
        _raise_workbench_error(exc)


def _workflow_service(request: Request) -> ProductWorkflowService:
    service = getattr(request.app.state, "product_workflow_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow persistence is unavailable.",
        )
    return service


def _trace_processing_disclosure() -> ProcessingDisclosureV1:
    return ProcessingDisclosureV1(
        execution="eamos_backend",
        provider_id="eamos_trace_processor",
        provider_label="Eamos trace processor",
        input_classes=["trace"],
        raw_input_persisted=False,
        retention="request_lifetime",
        expires_at=None,
        user_deletable=True,
        consent_required=False,
        warnings=[],
    )
