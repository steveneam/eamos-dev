from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import RATE_LIMIT_LIBRARY, enforce_rate_limit
from app.repos.variant_library_repo import (
    DEFAULT_LIBRARY_FOLDER_LIMIT,
    DEFAULT_LIBRARY_VARIANT_LIMIT,
    MAX_LIBRARY_FOLDER_LIMIT,
    MAX_LIBRARY_VARIANT_LIMIT,
)
from app.schemas.variant_library import (
    CreateFolderRequest,
    Folder,
    LibraryReplaceRequest,
    LibraryStore,
    MoveVariantRequest,
    PopularVariantsResponse,
    RenameFolderRequest,
    SavedVariant,
    SaveVariantsRequest,
    SaveVariantsResponse,
    VariantViewResponse,
)

router = APIRouter(prefix="/api/v1/library", tags=["variant-library"])


@router.get("", response_model=LibraryStore)
def get_library(
    request: Request,
    limit: int = Query(
        default=DEFAULT_LIBRARY_VARIANT_LIMIT,
        ge=1,
        le=MAX_LIBRARY_VARIANT_LIMIT,
    ),
    offset: int = Query(default=0, ge=0),
    folder_limit: int = Query(
        default=DEFAULT_LIBRARY_FOLDER_LIMIT,
        ge=1,
        le=MAX_LIBRARY_FOLDER_LIMIT,
    ),
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> LibraryStore:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY, subject=principal.user_id)
    return _service(request).get_library(
        principal,
        variant_limit=limit,
        variant_offset=offset,
        folder_limit=folder_limit,
    )


@router.put("", response_model=LibraryStore)
def replace_library(
    payload: LibraryReplaceRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> LibraryStore:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY, subject=principal.user_id)
    return _service(request).replace_library(payload, principal)


@router.get("/popular", response_model=PopularVariantsResponse)
def popular_variants(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
) -> PopularVariantsResponse:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY)
    return PopularVariantsResponse(variants=_service(request).popular(limit=limit))


@router.post("/views/{query_id:path}", response_model=VariantViewResponse)
def record_variant_view(
    query_id: str,
    request: Request,
) -> VariantViewResponse:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY)
    return VariantViewResponse(variant=_service(request).record_view(_validated_view_query_id(query_id)))


@router.get("/views/{query_id:path}", response_model=VariantViewResponse)
def get_variant_view(
    query_id: str,
    request: Request,
) -> VariantViewResponse:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY)
    return VariantViewResponse(variant=_service(request).get_view(_validated_view_query_id(query_id)))


@router.post("/variants", response_model=SavedVariant, status_code=status.HTTP_201_CREATED)
def save_variant(
    payload: SavedVariant,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> SavedVariant:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY, subject=principal.user_id)
    return _service(request).save_variant(payload, principal)


@router.post("/variants/bulk", response_model=SaveVariantsResponse)
def save_variants(
    payload: SaveVariantsRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> SaveVariantsResponse:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY, subject=principal.user_id)
    added, variants, library = _service(request).save_variants(payload.variants, principal)
    return SaveVariantsResponse(added=added, variants=variants, library=library)


@router.patch("/variants/{variant_id:path}/folder", response_model=SavedVariant)
def move_variant(
    variant_id: str,
    payload: MoveVariantRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> SavedVariant:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY, subject=principal.user_id)
    return _service(request).move_variant(variant_id, payload.folderId, principal)


@router.delete("/variants/{variant_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def remove_variant(
    variant_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> Response:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY, subject=principal.user_id)
    _service(request).remove_variant(variant_id, principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/folders", response_model=list[Folder])
def list_folders(
    request: Request,
    limit: int = Query(
        default=DEFAULT_LIBRARY_FOLDER_LIMIT,
        ge=1,
        le=MAX_LIBRARY_FOLDER_LIMIT,
    ),
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> list[Folder]:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY, subject=principal.user_id)
    return _service(request).get_library(principal, folder_limit=limit).folders


@router.post("/folders", response_model=Folder, status_code=status.HTTP_201_CREATED)
def create_folder(
    payload: CreateFolderRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> Folder:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY, subject=principal.user_id)
    return _service(request).create_folder(payload.name, principal)


@router.patch("/folders/{folder_id}", response_model=Folder)
def rename_folder(
    folder_id: str,
    payload: RenameFolderRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> Folder:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY, subject=principal.user_id)
    return _service(request).rename_folder(folder_id, payload.name, principal)


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_folder(
    folder_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> Response:
    enforce_rate_limit(request, RATE_LIMIT_LIBRARY, subject=principal.user_id)
    _service(request).remove_folder(folder_id, principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _service(request: Request):
    service = getattr(request.app.state, "variant_library_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Variant library service is unavailable.",
        )
    return service


def _validated_view_query_id(query_id: str) -> str:
    normalized = query_id.strip()
    if not normalized or len(normalized) > 512:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="View query id must be between 1 and 512 characters.",
        )
    return normalized
