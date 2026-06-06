from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import delete, func, select, update

from app.core.db import (
    VariantLibraryCollectionRecord,
    VariantLibrarySavedVariantRecord,
    VariantViewCountRecord,
    session_scope,
)


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
    last_viewed: datetime


class VariantLibraryRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def list_variants(self, *, user_id: str) -> list[SavedVariantRecord]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(VariantLibrarySavedVariantRecord)
                .where(VariantLibrarySavedVariantRecord.user_id == user_id)
                .order_by(VariantLibrarySavedVariantRecord.saved_at.desc())
            ).scalars()
            return [_saved_variant_from_record(row) for row in rows]

    def list_folders(self, *, user_id: str) -> list[FolderRecord]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(VariantLibraryCollectionRecord)
                .where(VariantLibraryCollectionRecord.user_id == user_id)
                .order_by(VariantLibraryCollectionRecord.created_at.asc())
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
        saved: list[SavedVariantRecord] = []
        added = 0
        for variant in variants:
            existing = self.get_variant(user_id=user_id, variant_id=variant.id)
            if existing is None:
                added += 1
            saved.append(self.save_variant(user_id=user_id, variant=variant))
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

    def list_variants(self, *, user_id: str) -> list[SavedVariantRecord]:
        rows = self._get_rows(
            "saved_variant",
            params={
                "select": "id,gene,variant,query,raw,saved_at,folder_id,classification,hgvs_full",
                "user_id": f"eq.{user_id}",
                "order": "saved_at.desc",
            },
        )
        return [_saved_variant_from_row(row) for row in rows]

    def list_folders(self, *, user_id: str) -> list[FolderRecord]:
        rows = self._get_rows(
            "collection",
            params={
                "select": "id,name,created_at",
                "user_id": f"eq.{user_id}",
                "order": "created_at.asc",
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
        existing_ids = {
            row.id
            for row in self.list_variants(user_id=user_id)
            if row.id in {v.id for v in variants}
        }
        saved = [self.save_variant(user_id=user_id, variant=variant) for variant in variants]
        return len([variant for variant in variants if variant.id not in existing_ids]), saved

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
        json: dict[str, Any],
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
        json: dict[str, Any] | None = None,
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


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
