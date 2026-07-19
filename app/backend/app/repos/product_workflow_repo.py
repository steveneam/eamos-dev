from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    delete,
    func,
    insert,
    or_,
    select,
    update,
)

from app.core.db import session_scope


class ProductWorkflowRepoError(RuntimeError):
    pass


class UnsafeWorkflowPayloadError(ProductWorkflowRepoError):
    pass


_RUN_UPDATE_FIELDS = frozenset(
    {
        "status",
        "context",
        "done",
        "total",
        "warnings",
        "source_disclosures",
        "processing_disclosure",
        "artifacts",
        "result_payload",
        "updated_at",
        "expires_at",
        "n_input",
        "n_to_lookup",
        "n_after_filters",
        "est_seconds",
    }
)


@dataclass(frozen=True)
class ProductWorkflowRunRecord:
    run_id: str
    user_id: str
    owner_provider: str
    kind: str
    status: str
    owner_scope: str
    context: dict[str, Any]
    done: int
    total: int
    warnings: list[str]
    source_disclosures: list[dict[str, Any]]
    processing_disclosure: dict[str, Any] | None
    artifacts: list[dict[str, Any]]
    result_payload: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    n_input: int | None = None
    n_to_lookup: int | None = None
    n_after_filters: int | None = None
    est_seconds: float | None = None


class ProductWorkflowRepository(Protocol):
    def initialize(self) -> None: ...

    def create_run(self, record: ProductWorkflowRunRecord) -> ProductWorkflowRunRecord: ...

    def get_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
    ) -> ProductWorkflowRunRecord | None: ...

    def list_runs(
        self,
        *,
        user_id: str,
        owner_provider: str,
        kind: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[ProductWorkflowRunRecord], str | None, int]: ...

    def update_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
        changes: dict[str, Any],
    ) -> ProductWorkflowRunRecord | None: ...

    def delete_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
    ) -> bool: ...

    def delete_expired(self, *, now: datetime) -> int: ...

    def replace_items(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
        items: list[dict[str, Any]],
    ) -> None: ...

    def page_items(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[dict[str, Any]], str | None, int]: ...


_metadata = MetaData()
_runs = Table(
    "product_workflow_run",
    _metadata,
    # The local development database also supports non-UUID Eamos user ids.
    # The reviewed Supabase migration narrows this column to auth.users UUIDs.
    Column("run_id", String(128), primary_key=True),
    Column("user_id", String(128), primary_key=True),
    Column("owner_provider", String(32), nullable=False),
    Column("kind", String(16), nullable=False),
    Column("status", String(16), nullable=False),
    Column("owner_scope", String(24), nullable=False),
    Column("context", JSON, nullable=False),
    Column("done", Integer, nullable=False),
    Column("total", Integer, nullable=False),
    Column("warnings", JSON, nullable=False),
    Column("source_disclosures", JSON, nullable=False),
    Column("processing_disclosure", JSON, nullable=True),
    Column("artifacts", JSON, nullable=False),
    Column("result_payload", JSON, nullable=True),
    Column("n_input", Integer, nullable=True),
    Column("n_to_lookup", Integer, nullable=True),
    Column("n_after_filters", Integer, nullable=True),
    Column("est_seconds", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=True),
)
Index(
    "ix_product_workflow_run_owner_kind_updated",
    _runs.c.user_id,
    _runs.c.owner_provider,
    _runs.c.kind,
    _runs.c.updated_at.desc(),
    _runs.c.run_id.desc(),
)
Index(
    "ix_product_workflow_run_expires",
    _runs.c.expires_at,
)
_items = Table(
    "product_workflow_item",
    _metadata,
    Column("run_id", String(128), primary_key=True),
    Column("user_id", String(128), primary_key=True),
    Column("owner_provider", String(32), primary_key=True),
    Column("position", Integer, primary_key=True),
    Column("payload", JSON, nullable=False),
    ForeignKeyConstraint(
        ["run_id", "user_id"],
        ["product_workflow_run.run_id", "product_workflow_run.user_id"],
        ondelete="CASCADE",
    ),
)
Index(
    "ix_product_workflow_item_owner_run_position",
    _items.c.user_id,
    _items.c.owner_provider,
    _items.c.run_id,
    _items.c.position,
)
class ProductWorkflowRepo:
    """Owner-scoped local workflow ledger.

    Only normalized metadata and sanitized result rows are accepted. Raw upload
    bodies are deliberately not represented in this schema.
    """

    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def initialize(self) -> None:
        _metadata.create_all(self.session_factory.kw["bind"])

    def create_run(self, record: ProductWorkflowRunRecord) -> ProductWorkflowRunRecord:
        _assert_safe_record(record)
        values = _record_values(record)
        with session_scope(self.session_factory) as session:
            session.execute(insert(_runs).values(**values))
        return record

    def get_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
    ) -> ProductWorkflowRunRecord | None:
        with session_scope(self.session_factory) as session:
            row = session.execute(
                select(_runs).where(
                    _runs.c.run_id == run_id,
                    _runs.c.user_id == user_id,
                    _runs.c.owner_provider == owner_provider,
                )
            ).mappings().one_or_none()
        return _record_from_mapping(row) if row is not None else None

    def list_runs(
        self,
        *,
        user_id: str,
        owner_provider: str,
        kind: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[ProductWorkflowRunRecord], str | None, int]:
        bounded_limit = max(1, min(100, int(limit)))
        conditions = [
            _runs.c.user_id == user_id,
            _runs.c.owner_provider == owner_provider,
        ]
        if kind is not None:
            conditions.append(_runs.c.kind == kind)
        cursor_value = _decode_run_cursor(cursor) if cursor else None
        if cursor_value is not None:
            cursor_updated_at, cursor_run_id = cursor_value
            conditions.append(
                or_(
                    _runs.c.updated_at < cursor_updated_at,
                    and_(
                        _runs.c.updated_at == cursor_updated_at,
                        _runs.c.run_id < cursor_run_id,
                    ),
                )
            )
        count_conditions = [
            _runs.c.user_id == user_id,
            _runs.c.owner_provider == owner_provider,
        ]
        if kind is not None:
            count_conditions.append(_runs.c.kind == kind)
        with session_scope(self.session_factory) as session:
            total = int(
                session.execute(
                    select(func.count()).select_from(_runs).where(*count_conditions)
                ).scalar_one()
            )
            rows = session.execute(
                select(_runs)
                .where(*conditions)
                .order_by(_runs.c.updated_at.desc(), _runs.c.run_id.desc())
                .limit(bounded_limit + 1)
            ).mappings().all()
        has_more = len(rows) > bounded_limit
        selected = rows[:bounded_limit]
        records = [_record_from_mapping(row) for row in selected]
        next_cursor = None
        if has_more and records:
            last = records[-1]
            next_cursor = _encode_run_cursor(last.updated_at, last.run_id)
        return records, next_cursor, total

    def update_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
        changes: dict[str, Any],
    ) -> ProductWorkflowRunRecord | None:
        unexpected = set(changes) - _RUN_UPDATE_FIELDS
        if unexpected:
            raise ProductWorkflowRepoError(
                f"Unsupported workflow update fields: {sorted(unexpected)}"
            )
        _assert_safe_payload(changes)
        values = dict(changes)
        if "est_seconds" in values and values["est_seconds"] is not None:
            values["est_seconds"] = str(values["est_seconds"])
        with session_scope(self.session_factory) as session:
            conditions = [
                _runs.c.run_id == run_id,
                _runs.c.user_id == user_id,
                _runs.c.owner_provider == owner_provider,
            ]
            if values.get("status") not in {None, "cancelled"}:
                conditions.append(_runs.c.status != "cancelled")
            result = session.execute(update(_runs).where(*conditions).values(**values))
        return self.get_run(
            run_id=run_id,
            user_id=user_id,
            owner_provider=owner_provider,
        )

    def delete_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
    ) -> bool:
        with session_scope(self.session_factory) as session:
            # SQLite foreign-key enforcement varies by runtime, so remove child
            # rows explicitly as well as retaining ON DELETE CASCADE in schema.
            session.execute(
                delete(_items).where(
                    _items.c.run_id == run_id,
                    _items.c.user_id == user_id,
                    _items.c.owner_provider == owner_provider,
                )
            )
            result = session.execute(
                delete(_runs).where(
                    _runs.c.run_id == run_id,
                    _runs.c.user_id == user_id,
                    _runs.c.owner_provider == owner_provider,
                )
            )
            return bool(result.rowcount)

    def delete_expired(self, *, now: datetime) -> int:
        with session_scope(self.session_factory) as session:
            expired = session.execute(
                select(_runs.c.run_id, _runs.c.user_id, _runs.c.owner_provider).where(
                    _runs.c.expires_at.is_not(None),
                    _runs.c.expires_at <= now,
                )
            ).all()
            for run_id, user_id, owner_provider in expired:
                session.execute(
                    delete(_items).where(
                        _items.c.run_id == run_id,
                        _items.c.user_id == user_id,
                        _items.c.owner_provider == owner_provider,
                    )
                )
            result = session.execute(
                delete(_runs).where(
                    _runs.c.expires_at.is_not(None),
                    _runs.c.expires_at <= now,
                )
            )
            return int(result.rowcount or 0)

    def replace_items(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
        items: list[dict[str, Any]],
    ) -> None:
        for item in items:
            _assert_safe_payload(item)
        with session_scope(self.session_factory) as session:
            owner_exists = session.execute(
                select(_runs.c.run_id).where(
                    _runs.c.run_id == run_id,
                    _runs.c.user_id == user_id,
                    _runs.c.owner_provider == owner_provider,
                )
            ).scalar_one_or_none()
            if owner_exists is None:
                raise ProductWorkflowRepoError("workflow run not found")
            session.execute(
                delete(_items).where(
                    _items.c.run_id == run_id,
                    _items.c.user_id == user_id,
                    _items.c.owner_provider == owner_provider,
                )
            )
            if items:
                session.execute(
                    insert(_items),
                    [
                        {
                            "run_id": run_id,
                            "user_id": user_id,
                            "owner_provider": owner_provider,
                            "position": position,
                            "payload": item,
                        }
                        for position, item in enumerate(items)
                    ],
                )

    def page_items(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[dict[str, Any]], str | None, int]:
        bounded_limit = max(1, min(500, int(limit)))
        after_position = _decode_item_cursor(cursor) if cursor else -1
        owner_conditions = (
            _items.c.run_id == run_id,
            _items.c.user_id == user_id,
            _items.c.owner_provider == owner_provider,
        )
        with session_scope(self.session_factory) as session:
            total = int(
                session.execute(
                    select(func.count()).select_from(_items).where(*owner_conditions)
                ).scalar_one()
            )
            rows = session.execute(
                select(_items.c.position, _items.c.payload)
                .where(*owner_conditions, _items.c.position > after_position)
                .order_by(_items.c.position.asc())
                .limit(bounded_limit + 1)
            ).mappings().all()
        has_more = len(rows) > bounded_limit
        selected = rows[:bounded_limit]
        next_cursor = (
            _encode_item_cursor(int(selected[-1]["position"]))
            if has_more and selected
            else None
        )
        return [dict(row["payload"]) for row in selected], next_cursor, total


class SupabaseProductWorkflowRepo:
    """Service-role REST mirror with mandatory owner filters on every operation."""

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

    def initialize(self) -> None:
        # Schema application is a separately approved lead-run checkpoint.
        return None

    def create_run(self, record: ProductWorkflowRunRecord) -> ProductWorkflowRunRecord:
        _assert_safe_record(record)
        response = self._request(
            "POST",
            "product_workflow_run",
            json=_json_ready(_record_values(record)),
            headers={"Prefer": "return=representation"},
        )
        return _record_from_mapping(_single_row(response))

    def get_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
    ) -> ProductWorkflowRunRecord | None:
        response = self._request(
            "GET",
            "product_workflow_run",
            params={
                "select": "*",
                "run_id": f"eq.{run_id}",
                "user_id": f"eq.{user_id}",
                "owner_provider": f"eq.{owner_provider}",
                "limit": "1",
            },
        )
        rows = _rows(response)
        return _record_from_mapping(rows[0]) if rows else None

    def list_runs(
        self,
        *,
        user_id: str,
        owner_provider: str,
        kind: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[ProductWorkflowRunRecord], str | None, int]:
        bounded_limit = max(1, min(100, int(limit)))
        params = {
            "select": "*",
            "user_id": f"eq.{user_id}",
            "owner_provider": f"eq.{owner_provider}",
            "order": "updated_at.desc,run_id.desc",
            "limit": str(bounded_limit + 1),
        }
        if kind is not None:
            params["kind"] = f"eq.{kind}"
        if cursor:
            cursor_updated_at, cursor_run_id = _decode_run_cursor(cursor)
            timestamp = cursor_updated_at.isoformat()
            params["or"] = f"(updated_at.lt.{timestamp},and(updated_at.eq.{timestamp},run_id.lt.{cursor_run_id}))"
        response = self._request(
            "GET",
            "product_workflow_run",
            params=params,
            headers={"Prefer": "count=exact"},
        )
        rows = _rows(response)
        has_more = len(rows) > bounded_limit
        records = [_record_from_mapping(row) for row in rows[:bounded_limit]]
        next_cursor = None
        if has_more and records:
            last = records[-1]
            next_cursor = _encode_run_cursor(last.updated_at, last.run_id)
        if cursor:
            count_params = {
                "select": "run_id",
                "user_id": f"eq.{user_id}",
                "owner_provider": f"eq.{owner_provider}",
                "limit": "1",
            }
            if kind is not None:
                count_params["kind"] = f"eq.{kind}"
            count_response = self._request(
                "GET",
                "product_workflow_run",
                params=count_params,
                headers={"Prefer": "count=exact"},
            )
            total = _content_range_total(count_response.headers.get("content-range"), 0)
        else:
            total = _content_range_total(response.headers.get("content-range"), len(records))
        return records, next_cursor, total

    def update_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
        changes: dict[str, Any],
    ) -> ProductWorkflowRunRecord | None:
        unexpected = set(changes) - _RUN_UPDATE_FIELDS
        if unexpected:
            raise ProductWorkflowRepoError(
                f"Unsupported workflow update fields: {sorted(unexpected)}"
            )
        _assert_safe_payload(changes)
        params = {
            "run_id": f"eq.{run_id}",
            "user_id": f"eq.{user_id}",
            "owner_provider": f"eq.{owner_provider}",
        }
        if changes.get("status") not in {None, "cancelled"}:
            params["status"] = "neq.cancelled"
        response = self._request(
            "PATCH",
            "product_workflow_run",
            params=params,
            json=_json_ready(changes),
            headers={"Prefer": "return=representation"},
        )
        rows = _rows(response)
        if rows:
            return _record_from_mapping(rows[0])
        if changes.get("status") not in {None, "cancelled"}:
            return self.get_run(
                run_id=run_id,
                user_id=user_id,
                owner_provider=owner_provider,
            )
        return None

    def delete_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
    ) -> bool:
        response = self._request(
            "DELETE",
            "product_workflow_run",
            params={
                "run_id": f"eq.{run_id}",
                "user_id": f"eq.{user_id}",
                "owner_provider": f"eq.{owner_provider}",
            },
            headers={"Prefer": "return=representation"},
        )
        return bool(_rows(response))

    def delete_expired(self, *, now: datetime) -> int:
        response = self._request(
            "DELETE",
            "product_workflow_run",
            params={"expires_at": f"lte.{now.astimezone(UTC).isoformat()}"},
            headers={"Prefer": "return=representation"},
        )
        return len(_rows(response))

    def replace_items(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
        items: list[dict[str, Any]],
    ) -> None:
        for item in items:
            _assert_safe_payload(item)
        self._request(
            "DELETE",
            "product_workflow_item",
            params={
                "run_id": f"eq.{run_id}",
                "user_id": f"eq.{user_id}",
                "owner_provider": f"eq.{owner_provider}",
            },
        )
        if not items:
            return
        self._request(
            "POST",
            "product_workflow_item",
            json=[
                {
                    "run_id": run_id,
                    "user_id": user_id,
                    "owner_provider": owner_provider,
                    "position": position,
                    "payload": item,
                }
                for position, item in enumerate(items)
            ],
        )

    def page_items(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[dict[str, Any]], str | None, int]:
        bounded_limit = max(1, min(500, int(limit)))
        after_position = _decode_item_cursor(cursor) if cursor else -1
        response = self._request(
            "GET",
            "product_workflow_item",
            params={
                "select": "position,payload",
                "run_id": f"eq.{run_id}",
                "user_id": f"eq.{user_id}",
                "owner_provider": f"eq.{owner_provider}",
                "position": f"gt.{after_position}",
                "order": "position.asc",
                "limit": str(bounded_limit + 1),
            },
            headers={"Prefer": "count=exact"},
        )
        rows = _rows(response)
        has_more = len(rows) > bounded_limit
        selected = rows[:bounded_limit]
        next_cursor = (
            _encode_item_cursor(int(selected[-1]["position"]))
            if has_more and selected
            else None
        )
        if cursor:
            count_response = self._request(
                "GET",
                "product_workflow_item",
                params={
                    "select": "position",
                    "run_id": f"eq.{run_id}",
                    "user_id": f"eq.{user_id}",
                    "owner_provider": f"eq.{owner_provider}",
                    "limit": "1",
                },
                headers={"Prefer": "count=exact"},
            )
            total = _content_range_total(count_response.headers.get("content-range"), 0)
        else:
            total = _content_range_total(response.headers.get("content-range"), len(selected))
        return [dict(row["payload"]) for row in selected], next_cursor, total

    def _request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        request_headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            **(headers or {}),
        }
        try:
            if self.http_client is None:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.request(
                        method,
                        f"{self.supabase_url}/rest/v1/{table}",
                        params=params,
                        json=json,
                        headers=request_headers,
                    )
            else:
                response = self.http_client.request(
                    method,
                    f"{self.supabase_url}/rest/v1/{table}",
                    params=params,
                    json=json,
                    headers=request_headers,
                )
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            raise ProductWorkflowRepoError(
                f"Supabase workflow operation failed: {type(exc).__name__}"
            ) from exc


_FORBIDDEN_DURABLE_KEYS = frozenset(
    {
        "access_token",
        "authorization",
        "edited_sequence",
        "evidence_quote",
        "notes",
        "paper_text",
        "pdf_bytes",
        "raw",
        "raw_input",
        "raw_text",
        "sequence",
        "token",
        "vcf",
    }
)


def _assert_safe_payload(value: Any) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in _FORBIDDEN_DURABLE_KEYS:
                raise UnsafeWorkflowPayloadError(
                    f"Raw workflow input field '{key}' cannot be persisted."
                )
            _assert_safe_payload(item)
    elif isinstance(value, list):
        for item in value:
            _assert_safe_payload(item)


def _assert_safe_record(record: ProductWorkflowRunRecord) -> None:
    for value in (
        record.context,
        record.source_disclosures,
        record.processing_disclosure,
        record.artifacts,
        record.result_payload,
    ):
        _assert_safe_payload(value)


def _record_values(record: ProductWorkflowRunRecord) -> dict[str, Any]:
    return {
        "run_id": record.run_id,
        "user_id": record.user_id,
        "owner_provider": record.owner_provider,
        "kind": record.kind,
        "status": record.status,
        "owner_scope": record.owner_scope,
        "context": record.context,
        "done": record.done,
        "total": record.total,
        "warnings": record.warnings,
        "source_disclosures": record.source_disclosures,
        "processing_disclosure": record.processing_disclosure,
        "artifacts": record.artifacts,
        "result_payload": record.result_payload,
        "n_input": record.n_input,
        "n_to_lookup": record.n_to_lookup,
        "n_after_filters": record.n_after_filters,
        "est_seconds": str(record.est_seconds) if record.est_seconds is not None else None,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "expires_at": record.expires_at,
    }


def _record_from_mapping(row: Any) -> ProductWorkflowRunRecord:
    values = dict(row)
    return ProductWorkflowRunRecord(
        run_id=str(values["run_id"]),
        user_id=str(values["user_id"]),
        owner_provider=str(values["owner_provider"]),
        kind=str(values["kind"]),
        status=str(values["status"]),
        owner_scope=str(values["owner_scope"]),
        context=dict(values.get("context") or {}),
        done=int(values.get("done") or 0),
        total=int(values.get("total") or 0),
        warnings=list(values.get("warnings") or []),
        source_disclosures=list(values.get("source_disclosures") or []),
        processing_disclosure=(
            dict(values["processing_disclosure"])
            if values.get("processing_disclosure") is not None
            else None
        ),
        artifacts=list(values.get("artifacts") or []),
        result_payload=(
            dict(values["result_payload"])
            if values.get("result_payload") is not None
            else None
        ),
        created_at=_datetime(values["created_at"]),
        updated_at=_datetime(values["updated_at"]),
        expires_at=_datetime(values["expires_at"]) if values.get("expires_at") else None,
        n_input=_optional_int(values.get("n_input")),
        n_to_lookup=_optional_int(values.get("n_to_lookup")),
        n_after_filters=_optional_int(values.get("n_after_filters")),
        est_seconds=(
            float(values["est_seconds"]) if values.get("est_seconds") is not None else None
        ),
    )


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _rows(response: httpx.Response) -> list[dict[str, Any]]:
    try:
        body = response.json()
    except ValueError as exc:
        raise ProductWorkflowRepoError("Workflow repository returned invalid JSON.") from exc
    if body is None:
        return []
    if isinstance(body, list) and all(isinstance(item, dict) for item in body):
        return body
    if isinstance(body, dict):
        return [body]
    raise ProductWorkflowRepoError("Workflow repository returned an invalid row shape.")


def _single_row(response: httpx.Response) -> dict[str, Any]:
    rows = _rows(response)
    if len(rows) != 1:
        raise ProductWorkflowRepoError("Workflow repository did not return one row.")
    return rows[0]


def _datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ProductWorkflowRepoError("Workflow repository returned an invalid timestamp.")
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _encode_run_cursor(updated_at: datetime, run_id: str) -> str:
    payload = json.dumps(
        [updated_at.astimezone(UTC).isoformat(), run_id],
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_run_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        payload = _decode_base64_json(cursor)
        if not isinstance(payload, list) or len(payload) != 2:
            raise ValueError
        updated_at = _datetime(payload[0])
        run_id = str(payload[1])
        if not run_id or len(run_id) > 128:
            raise ValueError
        return updated_at, run_id
    except (TypeError, ValueError, ProductWorkflowRepoError) as exc:
        raise ValueError("Invalid workflow cursor.") from exc


def _encode_item_cursor(position: int) -> str:
    payload = json.dumps([int(position)], separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_item_cursor(cursor: str) -> int:
    try:
        payload = _decode_base64_json(cursor)
        if not isinstance(payload, list) or len(payload) != 1:
            raise ValueError
        position = int(payload[0])
        if position < 0:
            raise ValueError
        return position
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid workflow cursor.") from exc


def _decode_base64_json(value: str) -> Any:
    if not value or len(value) > 512:
        raise ValueError
    padding = "=" * (-len(value) % 4)
    raw = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    if len(raw) > 512:
        raise ValueError
    return json.loads(raw.decode("utf-8"))


def _content_range_total(value: str | None, fallback: int) -> int:
    if value and "/" in value:
        tail = value.rsplit("/", 1)[-1]
        if tail.isdigit():
            return int(tail)
    return fallback
