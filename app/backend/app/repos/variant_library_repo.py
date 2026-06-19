from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

import httpx
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.sqlite import insert

from app.core.db import (
    UserLibraryRecord,
    VariantLibraryCollectionRecord,
    VariantLibrarySavedVariantRecord,
    VariantViewCountRecord,
    session_scope,
)

DEFAULT_LIBRARY_VARIANT_LIMIT = 500
MAX_LIBRARY_VARIANT_LIMIT = 500
DEFAULT_LIBRARY_FOLDER_LIMIT = 500
MAX_LIBRARY_FOLDER_LIMIT = 500


class VariantLibraryRepoError(RuntimeError):
    pass


class VariantLibraryNotFoundError(VariantLibraryRepoError):
    pass


class VariantLibraryWriteError(VariantLibraryRepoError):
    pass


@dataclass(frozen=True)
class SavedVariantRecord:
    id: str
    gene: str | None
    variant: str | None
    query: str
    raw: str
    saved_at: int
    folder_id: str | None
    classification: str | None
    hgvs_full: str | None


@dataclass(frozen=True)
class FolderRecord:
    id: str
    name: str
    created_at: datetime


@dataclass(frozen=True)
class VariantPopularityRecord:
    query_id: str
    view_count: int
    last_viewed: datetime | None


@dataclass(frozen=True)
class UserLibraryDocumentRecord:
    user_id: str
    variants: list[dict[str, Any]]
    folders: list[dict[str, Any]]
    updated_at: datetime


class VariantLibraryRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def get_document(self, *, user_id: str) -> UserLibraryDocumentRecord | None:
        with session_scope(self.session_factory) as session:
            record = session.get(UserLibraryRecord, user_id)
            return _library_document_from_record(record) if record is not None else None

    def replace_document(
        self,
        *,
        user_id: str,
        variants: list[dict[str, Any]],
        folders: list[dict[str, Any]],
    ) -> UserLibraryDocumentRecord:
        now = datetime.now(timezone.utc)
        with session_scope(self.session_factory) as session:
            record = session.get(UserLibraryRecord, user_id)
            if record is None:
                record = UserLibraryRecord(user_id=user_id)
            record.variants = variants
            record.folders = folders
            record.updated_at = now
            session.add(record)
            session.flush()
            return _library_document_from_record(record)

    def list_variants(
        self,
        *,
        user_id: str,
        limit: int = DEFAULT_LIBRARY_VARIANT_LIMIT,
        offset: int = 0,
    ) -> list[SavedVariantRecord]:
        bounded_limit = _bounded_limit(limit, max_limit=MAX_LIBRARY_VARIANT_LIMIT)
        bounded_offset = max(0, int(offset))
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(VariantLibrarySavedVariantRecord)
                .where(VariantLibrarySavedVariantRecord.user_id == user_id)
                .order_by(VariantLibrarySavedVariantRecord.saved_at.desc())
                .offset(bounded_offset)
                .limit(bounded_limit)
            ).scalars()
            return [_saved_variant_from_record(row) for row in rows]

    def list_folders(
        self,
        *,
        user_id: str,
        limit: int = DEFAULT_LIBRARY_FOLDER_LIMIT,
    ) -> list[FolderRecord]:
        bounded_limit = _bounded_limit(limit, max_limit=MAX_LIBRARY_FOLDER_LIMIT)
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(VariantLibraryCollectionRecord)
                .where(VariantLibraryCollectionRecord.user_id == user_id)
                .order_by(VariantLibraryCollectionRecord.created_at.asc())
                .limit(bounded_limit)
            ).scalars()
            return [_folder_from_record(row) for row in rows]

    def save_variant(self, *, user_id: str, variant: SavedVariantRecord) -> SavedVariantRecord:
        with session_scope(self.session_factory) as session:
            if variant.folder_id is not None and not _folder_exists(
                session,
                user_id=user_id,
                folder_id=variant.folder_id,
            ):
                raise VariantLibraryNotFoundError("folder not found")

            record = session.get(
                VariantLibrarySavedVariantRecord,
                {"id": variant.id, "user_id": user_id},
            )
            if record is None:
                record = VariantLibrarySavedVariantRecord(id=variant.id, user_id=user_id)
            record.gene = variant.gene
            record.variant = variant.variant
            record.query = variant.query
            record.raw = variant.raw
            record.saved_at = variant.saved_at
            record.folder_id = variant.folder_id
            record.classification = variant.classification
            record.hgvs_full = variant.hgvs_full
            session.add(record)
            session.flush()
            return _saved_variant_from_record(record)

    def save_variants(
        self,
        *,
        user_id: str,
        variants: list[SavedVariantRecord],
    ) -> tuple[int, list[SavedVariantRecord]]:
        if not variants:
            return 0, []
        latest_by_id = {variant.id: variant for variant in variants}
        ordered_ids = list(dict.fromkeys(variant.id for variant in variants))
        folder_ids = {variant.folder_id for variant in latest_by_id.values() if variant.folder_id}
        with session_scope(self.session_factory) as session:
            if folder_ids:
                existing_folder_ids = set(
                    session.execute(
                        select(VariantLibraryCollectionRecord.id).where(
                            VariantLibraryCollectionRecord.user_id == user_id,
                            VariantLibraryCollectionRecord.id.in_(folder_ids),
                        )
                    ).scalars()
                )
                if existing_folder_ids != folder_ids:
                    raise VariantLibraryNotFoundError("folder not found")

            existing_ids = set(
                session.execute(
                    select(VariantLibrarySavedVariantRecord.id).where(
                        VariantLibrarySavedVariantRecord.user_id == user_id,
                        VariantLibrarySavedVariantRecord.id.in_(ordered_ids),
                    )
                ).scalars()
            )
            values = [
                _saved_variant_values(user_id=user_id, variant=latest_by_id[variant_id])
                for variant_id in ordered_ids
            ]
            statement = insert(VariantLibrarySavedVariantRecord).values(values)
            update_values = {
                "gene": statement.excluded.gene,
                "variant": statement.excluded.variant,
                "query": statement.excluded.query,
                "raw": statement.excluded.raw,
                "saved_at": statement.excluded.saved_at,
                "folder_id": statement.excluded.folder_id,
                "classification": statement.excluded.classification,
                "hgvs_full": statement.excluded.hgvs_full,
            }
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=["id", "user_id"],
                    set_=update_values,
                )
            )
            saved_rows = session.execute(
                select(VariantLibrarySavedVariantRecord).where(
                    VariantLibrarySavedVariantRecord.user_id == user_id,
                    VariantLibrarySavedVariantRecord.id.in_(ordered_ids),
                )
            ).scalars()
            by_id = {row.id: _saved_variant_from_record(row) for row in saved_rows}
        saved = [by_id[variant.id] for variant in variants]
        added = len([variant_id for variant_id in ordered_ids if variant_id not in existing_ids])
        return added, saved

    def get_variant(self, *, user_id: str, variant_id: str) -> SavedVariantRecord | None:
        with session_scope(self.session_factory) as session:
            record = session.get(
                VariantLibrarySavedVariantRecord,
                {"id": variant_id, "user_id": user_id},
            )
            return _saved_variant_from_record(record) if record is not None else None

    def remove_variant(self, *, user_id: str, variant_id: str) -> bool:
        with session_scope(self.session_factory) as session:
            result = session.execute(
                delete(VariantLibrarySavedVariantRecord).where(
                    VariantLibrarySavedVariantRecord.user_id == user_id,
                    VariantLibrarySavedVariantRecord.id == variant_id,
                )
            )
            return bool(result.rowcount)

    def create_folder(self, *, user_id: str, name: str) -> FolderRecord:
        with session_scope(self.session_factory) as session:
            existing = session.execute(
                select(VariantLibraryCollectionRecord).where(
                    VariantLibraryCollectionRecord.user_id == user_id,
                    func.lower(VariantLibraryCollectionRecord.name) == name.lower(),
                )
            ).scalar_one_or_none()
            if existing is not None:
                return _folder_from_record(existing)

            record = VariantLibraryCollectionRecord(
                id=str(uuid4()),
                user_id=user_id,
                name=name,
            )
            session.add(record)
            session.flush()
            return _folder_from_record(record)

    def rename_folder(self, *, user_id: str, folder_id: str, name: str) -> FolderRecord:
        with session_scope(self.session_factory) as session:
            record = session.get(VariantLibraryCollectionRecord, folder_id)
            if record is None or record.user_id != user_id:
                raise VariantLibraryNotFoundError("folder not found")
            record.name = name
            session.add(record)
            session.flush()
            return _folder_from_record(record)

    def remove_folder(self, *, user_id: str, folder_id: str) -> bool:
        with session_scope(self.session_factory) as session:
            record = session.get(VariantLibraryCollectionRecord, folder_id)
            if record is None or record.user_id != user_id:
                return False
            session.execute(
                update(VariantLibrarySavedVariantRecord)
                .where(
                    VariantLibrarySavedVariantRecord.user_id == user_id,
                    VariantLibrarySavedVariantRecord.folder_id == folder_id,
                )
                .values(folder_id=None)
            )
            session.delete(record)
            return True

    def move_variant(
        self,
        *,
        user_id: str,
        variant_id: str,
        folder_id: str | None,
    ) -> SavedVariantRecord:
        with session_scope(self.session_factory) as session:
            if folder_id is not None and not _folder_exists(
                session,
                user_id=user_id,
                folder_id=folder_id,
            ):
                raise VariantLibraryNotFoundError("folder not found")
            record = session.get(
                VariantLibrarySavedVariantRecord,
                {"id": variant_id, "user_id": user_id},
            )
            if record is None:
                raise VariantLibraryNotFoundError("variant not found")
            record.folder_id = folder_id
            session.add(record)
            session.flush()
            return _saved_variant_from_record(record)

    def record_view(self, *, query_id: str) -> VariantPopularityRecord:
        now = datetime.now(timezone.utc)
        with session_scope(self.session_factory) as session:
            record = session.get(VariantViewCountRecord, query_id)
            if record is None:
                record = VariantViewCountRecord(query_id=query_id, view_count=0)
            record.view_count += 1
            record.last_viewed = now
            session.add(record)
            session.flush()
            return _popularity_from_record(record)

    def get_view(self, *, query_id: str) -> VariantPopularityRecord:
        with session_scope(self.session_factory) as session:
            record = session.get(VariantViewCountRecord, query_id)
            if record is None:
                return VariantPopularityRecord(query_id=query_id, view_count=0, last_viewed=None)
            return _popularity_from_record(record)

    def popular(self, *, limit: int) -> list[VariantPopularityRecord]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(VariantViewCountRecord)
                .order_by(
                    VariantViewCountRecord.view_count.desc(),
                    VariantViewCountRecord.last_viewed.desc(),
                )
                .limit(limit)
            ).scalars()
            return [_popularity_from_record(row) for row in rows]


class SupabaseVariantLibraryRepo:
    def __init__(
        self,
        *,
        supabase_url: str,
        service_role_key: str,
        timeout_seconds: float = 10.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key
        self.timeout_seconds = timeout_seconds
        self.http_client = http_client

    def get_document(self, *, user_id: str) -> UserLibraryDocumentRecord | None:
        rows = self._get_rows(
            "user_library",
            params={
                "select": "user_id,variants,folders,updated_at",
                "user_id": f"eq.{user_id}",
                "limit": "1",
            },
        )
        return _library_document_from_row(rows[0]) if rows else None

    def replace_document(
        self,
        *,
        user_id: str,
        variants: list[dict[str, Any]],
        folders: list[dict[str, Any]],
    ) -> UserLibraryDocumentRecord:
        updated_at = datetime.now(timezone.utc).isoformat()
        rows = self._post_rows(
            "user_library",
            json={
                "user_id": user_id,
                "variants": variants,
                "folders": folders,
                "updated_at": updated_at,
            },
            params={"on_conflict": "user_id"},
            prefer="resolution=merge-duplicates,return=representation",
        )
        if not rows:
            raise VariantLibraryWriteError("user library upsert returned no row")
        return _library_document_from_row(rows[0])

    def list_variants(
        self,
        *,
        user_id: str,
        limit: int = DEFAULT_LIBRARY_VARIANT_LIMIT,
        offset: int = 0,
    ) -> list[SavedVariantRecord]:
        bounded_limit = _bounded_limit(limit, max_limit=MAX_LIBRARY_VARIANT_LIMIT)
        bounded_offset = max(0, int(offset))
        rows = self._get_rows(
            "saved_variant",
            params={
                "select": "id,gene,variant,query,raw,saved_at,folder_id,classification,hgvs_full",
                "user_id": f"eq.{user_id}",
                "order": "saved_at.desc",
                "limit": str(bounded_limit),
                "offset": str(bounded_offset),
            },
        )
        return [_saved_variant_from_row(row) for row in rows]

    def list_folders(
        self,
        *,
        user_id: str,
        limit: int = DEFAULT_LIBRARY_FOLDER_LIMIT,
    ) -> list[FolderRecord]:
        bounded_limit = _bounded_limit(limit, max_limit=MAX_LIBRARY_FOLDER_LIMIT)
        rows = self._get_rows(
            "collection",
            params={
                "select": "id,name,created_at",
                "user_id": f"eq.{user_id}",
                "order": "created_at.asc",
                "limit": str(bounded_limit),
            },
        )
        return [_folder_from_row(row) for row in rows]

    def save_variant(self, *, user_id: str, variant: SavedVariantRecord) -> SavedVariantRecord:
        if variant.folder_id is not None and not self._folder_exists(
            user_id=user_id,
            folder_id=variant.folder_id,
        ):
            raise VariantLibraryNotFoundError("folder not found")
        rows = self._post_rows(
            "saved_variant",
            json={
                "id": variant.id,
                "user_id": user_id,
                "gene": variant.gene,
                "variant": variant.variant,
                "query": variant.query,
                "raw": variant.raw,
                "saved_at": variant.saved_at,
                "folder_id": variant.folder_id,
                "classification": variant.classification,
                "hgvs_full": variant.hgvs_full,
            },
            params={"on_conflict": "id,user_id"},
            prefer="resolution=merge-duplicates,return=representation",
        )
        if not rows:
            raise VariantLibraryWriteError("saved variant upsert returned no row")
        return _saved_variant_from_row(rows[0])

    def save_variants(
        self,
        *,
        user_id: str,
        variants: list[SavedVariantRecord],
    ) -> tuple[int, list[SavedVariantRecord]]:
        if not variants:
            return 0, []
        latest_by_id = {variant.id: variant for variant in variants}
        ordered_ids = list(dict.fromkeys(variant.id for variant in variants))
        folder_ids = {variant.folder_id for variant in latest_by_id.values() if variant.folder_id}
        if folder_ids:
            existing_folder_rows = self._get_rows(
                "collection",
                params={
                    "select": "id",
                    "user_id": f"eq.{user_id}",
                    "id": _postgrest_in_filter(folder_ids),
                    "limit": str(len(folder_ids)),
                },
            )
            if {str(row["id"]) for row in existing_folder_rows} != folder_ids:
                raise VariantLibraryNotFoundError("folder not found")

        existing_rows = self._get_rows(
            "saved_variant",
            params={
                "select": "id",
                "user_id": f"eq.{user_id}",
                "id": _postgrest_in_filter(ordered_ids),
                "limit": str(len(ordered_ids)),
            },
        )
        existing_ids = {str(row["id"]) for row in existing_rows}
        rows = self._post_rows(
            "saved_variant",
            json=[
                _saved_variant_values(user_id=user_id, variant=latest_by_id[variant_id])
                for variant_id in ordered_ids
            ],
            params={"on_conflict": "id,user_id"},
            prefer="resolution=merge-duplicates,return=representation",
        )
        if not rows:
            raise VariantLibraryWriteError("saved variant bulk upsert returned no rows")
        by_id = {_saved_variant_from_row(row).id: _saved_variant_from_row(row) for row in rows}
        saved = [by_id[variant.id] for variant in variants]
        added = len([variant_id for variant_id in ordered_ids if variant_id not in existing_ids])
        return added, saved

    def get_variant(self, *, user_id: str, variant_id: str) -> SavedVariantRecord | None:
        rows = self._get_rows(
            "saved_variant",
            params={
                "select": "id,gene,variant,query,raw,saved_at,folder_id,classification,hgvs_full",
                "user_id": f"eq.{user_id}",
                "id": f"eq.{variant_id}",
                "limit": "1",
            },
        )
        return _saved_variant_from_row(rows[0]) if rows else None

    def remove_variant(self, *, user_id: str, variant_id: str) -> bool:
        rows = self._delete_rows(
            "saved_variant",
            params={
                "user_id": f"eq.{user_id}",
                "id": f"eq.{variant_id}",
            },
        )
        return bool(rows)

    def create_folder(self, *, user_id: str, name: str) -> FolderRecord:
        for folder in self.list_folders(user_id=user_id):
            if folder.name.lower() == name.lower():
                return folder
        rows = self._post_rows(
            "collection",
            json={"user_id": user_id, "name": name},
            prefer="return=representation",
        )
        if not rows:
            raise VariantLibraryWriteError("folder create returned no row")
        return _folder_from_row(rows[0])

    def rename_folder(self, *, user_id: str, folder_id: str, name: str) -> FolderRecord:
        rows = self._patch_rows(
            "collection",
            json={"name": name},
            params={
                "user_id": f"eq.{user_id}",
                "id": f"eq.{folder_id}",
            },
        )
        if not rows:
            raise VariantLibraryNotFoundError("folder not found")
        return _folder_from_row(rows[0])

    def remove_folder(self, *, user_id: str, folder_id: str) -> bool:
        if not self._folder_exists(user_id=user_id, folder_id=folder_id):
            return False
        self._patch_rows(
            "saved_variant",
            json={"folder_id": None},
            params={
                "user_id": f"eq.{user_id}",
                "folder_id": f"eq.{folder_id}",
            },
        )
        rows = self._delete_rows(
            "collection",
            params={
                "user_id": f"eq.{user_id}",
                "id": f"eq.{folder_id}",
            },
        )
        return bool(rows)

    def move_variant(
        self,
        *,
        user_id: str,
        variant_id: str,
        folder_id: str | None,
    ) -> SavedVariantRecord:
        if folder_id is not None and not self._folder_exists(user_id=user_id, folder_id=folder_id):
            raise VariantLibraryNotFoundError("folder not found")
        rows = self._patch_rows(
            "saved_variant",
            json={"folder_id": folder_id},
            params={
                "user_id": f"eq.{user_id}",
                "id": f"eq.{variant_id}",
            },
        )
        if not rows:
            raise VariantLibraryNotFoundError("variant not found")
        return _saved_variant_from_row(rows[0])

    def record_view(self, *, query_id: str) -> VariantPopularityRecord:
        rows = self._post_rows(
            "rpc/increment_variant_view_count",
            json={"p_query_id": query_id},
            prefer="return=representation",
        )
        if not rows:
            raise VariantLibraryWriteError("view counter increment returned no row")
        return _popularity_from_row(rows[0])

    def get_view(self, *, query_id: str) -> VariantPopularityRecord:
        rows = self._get_rows(
            "variant_view_count",
            params={
                "select": "query_id,view_count,last_viewed",
                "query_id": f"eq.{query_id}",
                "limit": "1",
            },
        )
        if not rows:
            return VariantPopularityRecord(query_id=query_id, view_count=0, last_viewed=None)
        return _popularity_from_row(rows[0])

    def popular(self, *, limit: int) -> list[VariantPopularityRecord]:
        rows = self._get_rows(
            "variant_view_count",
            params={
                "select": "query_id,view_count,last_viewed",
                "order": "view_count.desc,last_viewed.desc",
                "limit": str(limit),
            },
        )
        return [_popularity_from_row(row) for row in rows]

    def _folder_exists(self, *, user_id: str, folder_id: str) -> bool:
        rows = self._get_rows(
            "collection",
            params={
                "select": "id",
                "user_id": f"eq.{user_id}",
                "id": f"eq.{folder_id}",
                "limit": "1",
            },
        )
        return bool(rows)

    def _get_rows(self, path: str, *, params: dict[str, str]) -> list[dict[str, Any]]:
        response = self._request("GET", path, params=params)
        return _json_rows(response)

    def _post_rows(
        self,
        path: str,
        *,
        json: Any,
        params: dict[str, str] | None = None,
        prefer: str,
    ) -> list[dict[str, Any]]:
        response = self._request("POST", path, json=json, params=params, prefer=prefer)
        return _json_rows(response)

    def _patch_rows(
        self,
        path: str,
        *,
        json: dict[str, Any],
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        response = self._request(
            "PATCH",
            path,
            json=json,
            params=params,
            prefer="return=representation",
        )
        return _json_rows(response)

    def _delete_rows(self, path: str, *, params: dict[str, str]) -> list[dict[str, Any]]:
        response = self._request(
            "DELETE",
            path,
            params=params,
            prefer="return=representation",
        )
        return _json_rows(response)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: Any = None,
        prefer: str | None = None,
    ) -> httpx.Response:
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }
        if json is not None:
            headers["Content-Type"] = "application/json"
        if prefer:
            headers["Prefer"] = prefer
        url = f"{self.supabase_url}/rest/v1/{path.lstrip('/')}"
        try:
            if self.http_client is None:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.request(
                        method,
                        url,
                        headers=headers,
                        params=params,
                        json=json,
                    )
            else:
                response = self.http_client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json,
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise VariantLibraryWriteError(
                f"Supabase variant library request failed: {type(exc).__name__}"
            ) from exc
        return response


def _folder_exists(session, *, user_id: str, folder_id: str) -> bool:
    record = session.get(VariantLibraryCollectionRecord, folder_id)
    return record is not None and record.user_id == user_id


def _bounded_limit(value: int, *, max_limit: int) -> int:
    return max(1, min(int(value), max_limit))


def _saved_variant_values(*, user_id: str, variant: SavedVariantRecord) -> dict[str, Any]:
    return {
        "id": variant.id,
        "user_id": user_id,
        "gene": variant.gene,
        "variant": variant.variant,
        "query": variant.query,
        "raw": variant.raw,
        "saved_at": variant.saved_at,
        "folder_id": variant.folder_id,
        "classification": variant.classification,
        "hgvs_full": variant.hgvs_full,
    }


def _postgrest_in_filter(values: Iterable[str]) -> str:
    escaped_values = []
    for value in values:
        escaped = str(value).replace('"', '""')
        escaped_values.append(f'"{escaped}"')
    return f"in.({','.join(escaped_values)})"


def _saved_variant_from_record(row: VariantLibrarySavedVariantRecord) -> SavedVariantRecord:
    return SavedVariantRecord(
        id=row.id,
        gene=row.gene,
        variant=row.variant,
        query=row.query,
        raw=row.raw,
        saved_at=row.saved_at,
        folder_id=row.folder_id,
        classification=row.classification,
        hgvs_full=row.hgvs_full,
    )


def _folder_from_record(row: VariantLibraryCollectionRecord) -> FolderRecord:
    return FolderRecord(id=row.id, name=row.name, created_at=row.created_at)


def _popularity_from_record(row: VariantViewCountRecord) -> VariantPopularityRecord:
    return VariantPopularityRecord(
        query_id=row.query_id,
        view_count=row.view_count,
        last_viewed=row.last_viewed,
    )


def _library_document_from_record(row: UserLibraryRecord) -> UserLibraryDocumentRecord:
    return UserLibraryDocumentRecord(
        user_id=row.user_id,
        variants=_list_of_dicts(row.variants),
        folders=_list_of_dicts(row.folders),
        updated_at=_as_utc_datetime(row.updated_at),
    )


def _library_document_from_row(row: dict[str, Any]) -> UserLibraryDocumentRecord:
    return UserLibraryDocumentRecord(
        user_id=str(row["user_id"]),
        variants=_list_of_dicts(row.get("variants")),
        folders=_list_of_dicts(row.get("folders")),
        updated_at=_parse_datetime(row.get("updated_at")),
    )


def _saved_variant_from_row(row: dict[str, Any]) -> SavedVariantRecord:
    return SavedVariantRecord(
        id=str(row["id"]),
        gene=_optional_str(row.get("gene")),
        variant=_optional_str(row.get("variant")),
        query=str(row["query"]),
        raw=str(row.get("raw") or ""),
        saved_at=int(row["saved_at"]),
        folder_id=_optional_str(row.get("folder_id")),
        classification=_optional_str(row.get("classification")),
        hgvs_full=_optional_str(row.get("hgvs_full")),
    )


def _folder_from_row(row: dict[str, Any]) -> FolderRecord:
    return FolderRecord(
        id=str(row["id"]),
        name=str(row["name"]),
        created_at=_parse_datetime(row.get("created_at")),
    )


def _popularity_from_row(row: dict[str, Any]) -> VariantPopularityRecord:
    return VariantPopularityRecord(
        query_id=str(row["query_id"]),
        view_count=int(row["view_count"]),
        last_viewed=_parse_datetime(row.get("last_viewed")),
    )


def _json_rows(response: httpx.Response) -> list[dict[str, Any]]:
    if response.status_code == 204 or not response.content:
        return []
    try:
        body = response.json()
    except ValueError as exc:
        raise VariantLibraryWriteError("Supabase variant library returned invalid JSON") from exc
    if isinstance(body, list):
        return [row for row in body if isinstance(row, dict)]
    if isinstance(body, dict):
        return [body]
    return []


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _as_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]
