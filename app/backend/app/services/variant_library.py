from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.deps import AuthenticatedPrincipal
from app.repos.variant_library_repo import (
    FolderRecord,
    SavedVariantRecord,
    VariantLibraryNotFoundError,
    VariantLibraryRepoError,
    VariantPopularityRecord,
)
from app.schemas.variant_library import (
    Folder,
    LibraryStore,
    SavedVariant,
    VariantPopularity,
)


class VariantLibraryService:
    def __init__(self, repo) -> None:
        self.repo = repo

    def get_library(self, principal: AuthenticatedPrincipal) -> LibraryStore:
        try:
            return LibraryStore(
                variants=[
                    _saved_variant_schema(row)
                    for row in self.repo.list_variants(user_id=principal.user_id)
                ],
                folders=[
                    _folder_schema(row) for row in self.repo.list_folders(user_id=principal.user_id)
                ],
            )
        except VariantLibraryRepoError as exc:
            raise _service_unavailable() from exc

    def save_variant(
        self,
        payload: SavedVariant,
        principal: AuthenticatedPrincipal,
    ) -> SavedVariant:
        try:
            row = self.repo.save_variant(
                user_id=principal.user_id,
                variant=_saved_variant_record(payload),
            )
            return _saved_variant_schema(row)
        except VariantLibraryNotFoundError as exc:
            raise _not_found("Folder not found.") from exc
        except VariantLibraryRepoError as exc:
            raise _service_unavailable() from exc

    def save_variants(
        self,
        variants: list[SavedVariant],
        principal: AuthenticatedPrincipal,
    ) -> tuple[int, list[SavedVariant], LibraryStore]:
        try:
            added, rows = self.repo.save_variants(
                user_id=principal.user_id,
                variants=[_saved_variant_record(variant) for variant in variants],
            )
            library = self.get_library(principal)
            return added, [_saved_variant_schema(row) for row in rows], library
        except VariantLibraryNotFoundError as exc:
            raise _not_found("Folder not found.") from exc
        except VariantLibraryRepoError as exc:
            raise _service_unavailable() from exc

    def remove_variant(self, variant_id: str, principal: AuthenticatedPrincipal) -> None:
        try:
            removed = self.repo.remove_variant(
                user_id=principal.user_id,
                variant_id=_normalize_id(variant_id),
            )
        except VariantLibraryRepoError as exc:
            raise _service_unavailable() from exc
        if not removed:
            raise _not_found("Saved variant not found.")

    def create_folder(self, name: str, principal: AuthenticatedPrincipal) -> Folder:
        try:
            return _folder_schema(self.repo.create_folder(user_id=principal.user_id, name=name))
        except VariantLibraryRepoError as exc:
            raise _service_unavailable() from exc

    def rename_folder(
        self,
        folder_id: str,
        name: str,
        principal: AuthenticatedPrincipal,
    ) -> Folder:
        try:
            return _folder_schema(
                self.repo.rename_folder(
                    user_id=principal.user_id,
                    folder_id=folder_id,
                    name=name,
                )
            )
        except VariantLibraryNotFoundError as exc:
            raise _not_found("Folder not found.") from exc
        except VariantLibraryRepoError as exc:
            raise _service_unavailable() from exc

    def remove_folder(self, folder_id: str, principal: AuthenticatedPrincipal) -> None:
        try:
            removed = self.repo.remove_folder(user_id=principal.user_id, folder_id=folder_id)
        except VariantLibraryRepoError as exc:
            raise _service_unavailable() from exc
        if not removed:
            raise _not_found("Folder not found.")

    def move_variant(
        self,
        variant_id: str,
        folder_id: str | None,
        principal: AuthenticatedPrincipal,
    ) -> SavedVariant:
        try:
            row = self.repo.move_variant(
                user_id=principal.user_id,
                variant_id=_normalize_id(variant_id),
                folder_id=folder_id,
            )
            return _saved_variant_schema(row)
        except VariantLibraryNotFoundError as exc:
            raise _not_found("Saved variant or folder not found.") from exc
        except VariantLibraryRepoError as exc:
            raise _service_unavailable() from exc

    def record_view(self, query_id: str) -> VariantPopularity:
        try:
            return _popularity_schema(self.repo.record_view(query_id=_normalize_id(query_id)))
        except VariantLibraryRepoError as exc:
            raise _service_unavailable() from exc

    def popular(self, *, limit: int) -> list[VariantPopularity]:
        try:
            return [_popularity_schema(row) for row in self.repo.popular(limit=limit)]
        except VariantLibraryRepoError as exc:
            raise _service_unavailable() from exc


def _saved_variant_record(payload: SavedVariant) -> SavedVariantRecord:
    return SavedVariantRecord(
        id=_normalize_id(payload.id),
        gene=payload.gene,
        variant=payload.variant,
        query=payload.query,
        raw=payload.raw,
        saved_at=payload.savedAt,
        folder_id=payload.folderId,
        classification=payload.classification,
        hgvs_full=payload.hgvs_full,
    )


def _saved_variant_schema(row: SavedVariantRecord) -> SavedVariant:
    return SavedVariant(
        id=row.id,
        gene=row.gene,
        variant=row.variant,
        query=row.query,
        raw=row.raw,
        savedAt=row.saved_at,
        folderId=row.folder_id,
        classification=row.classification,
        hgvs_full=row.hgvs_full,
    )


def _folder_schema(row: FolderRecord) -> Folder:
    return Folder(
        id=row.id,
        name=row.name,
        createdAt=_epoch_ms(row.created_at),
    )


def _popularity_schema(row: VariantPopularityRecord) -> VariantPopularity:
    return VariantPopularity(
        query_id=row.query_id,
        view_count=row.view_count,
        last_viewed=row.last_viewed,
    )


def _normalize_id(value: str) -> str:
    return value.strip().lower()


def _epoch_ms(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _service_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Variant library persistence is unavailable.",
    )
