from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.core.db import SourceCacheRecord, session_scope
from app.tools.base import ToolResult


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _iso(value: datetime) -> str:
    return _as_aware(value).isoformat()


@dataclass(frozen=True)
class SourceCachePayload:
    source: str
    cache_key: str
    normalized_identity: dict[str, Any]
    request_identity: dict[str, Any]
    status: str
    source_version: str | None
    summary: dict[str, Any]
    raw: Any
    warnings: list[str] = field(default_factory=list)
    source_url: str | None = None
    fetched_at: datetime | None = None
    expires_at: datetime | None = None

    def to_tool_result(
        self,
        *,
        status: str,
        cache_status: str,
        extra_warnings: list[str] | None = None,
    ) -> ToolResult:
        return ToolResult(
            source=self.source,
            status=status,
            request_identity=dict(self.request_identity),
            summary=dict(self.summary),
            warnings=[*self.warnings, *(extra_warnings or [])],
            raw=self.raw,
            source_url=self.source_url,
            fetched_at=_iso(self.fetched_at) if self.fetched_at is not None else None,
            source_version=self.source_version,
            cache_status=cache_status,
        )


class SourceCacheRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def get_fresh(self, source: str, cache_key: str) -> SourceCachePayload | None:
        now = datetime.now(timezone.utc)
        payload = self.get_any(source, cache_key)
        if payload is None or payload.expires_at is None or _as_aware(payload.expires_at) <= now:
            return None
        return payload

    def get_stale(self, source: str, cache_key: str) -> SourceCachePayload | None:
        payload = self.get_any(source, cache_key)
        if payload is None:
            return None
        now = datetime.now(timezone.utc)
        if payload.expires_at is not None and _as_aware(payload.expires_at) > now:
            return None
        return payload

    def get_any(self, source: str, cache_key: str) -> SourceCachePayload | None:
        with session_scope(self.session_factory) as session:
            record = session.execute(
                select(SourceCacheRecord).where(
                    SourceCacheRecord.source == source,
                    SourceCacheRecord.cache_key == cache_key,
                )
            ).scalar_one_or_none()
            if record is None:
                return None
            return _payload_from_record(record)

    def health_summary(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(
                    SourceCacheRecord.source,
                    SourceCacheRecord.status,
                    SourceCacheRecord.source_version,
                    SourceCacheRecord.fetched_at,
                    SourceCacheRecord.expires_at,
                )
            ).all()

        sources: dict[str, dict[str, Any]] = {}
        latest_fetched_at: datetime | None = None
        oldest_fetched_at: datetime | None = None
        total_rows = 0
        fresh_rows = 0
        stale_rows = 0
        versioned_rows = 0
        for source, status, source_version, fetched_at, expires_at in rows:
            total_rows += 1
            source_summary = sources.setdefault(
                source,
                {
                    "rows": 0,
                    "fresh_rows": 0,
                    "stale_rows": 0,
                    "versioned_rows": 0,
                    "status_counts": {},
                    "oldest_fetched_at": None,
                    "latest_fetched_at": None,
                },
            )
            source_summary["rows"] += 1
            status_counts = source_summary["status_counts"]
            status_counts[status] = status_counts.get(status, 0) + 1

            is_fresh = expires_at is not None and _as_aware(expires_at) > now
            if is_fresh:
                fresh_rows += 1
                source_summary["fresh_rows"] += 1
            else:
                stale_rows += 1
                source_summary["stale_rows"] += 1

            if source_version:
                versioned_rows += 1
                source_summary["versioned_rows"] += 1

            if fetched_at is None:
                continue
            aware_fetched_at = _as_aware(fetched_at)
            if latest_fetched_at is None or aware_fetched_at > latest_fetched_at:
                latest_fetched_at = aware_fetched_at
            if oldest_fetched_at is None or aware_fetched_at < oldest_fetched_at:
                oldest_fetched_at = aware_fetched_at
            current_latest = source_summary["latest_fetched_at"]
            if current_latest is None or aware_fetched_at > current_latest:
                source_summary["latest_fetched_at"] = aware_fetched_at
            current_oldest = source_summary["oldest_fetched_at"]
            if current_oldest is None or aware_fetched_at < current_oldest:
                source_summary["oldest_fetched_at"] = aware_fetched_at

        return {
            "total_rows": total_rows,
            "fresh_rows": fresh_rows,
            "stale_rows": stale_rows,
            "versioned_rows": versioned_rows,
            "oldest_fetched_at": _iso(oldest_fetched_at) if oldest_fetched_at else None,
            "latest_fetched_at": _iso(latest_fetched_at) if latest_fetched_at else None,
            "sources": {
                source: {
                    **summary,
                    "status_counts": dict(sorted(summary["status_counts"].items())),
                    "oldest_fetched_at": (
                        _iso(summary["oldest_fetched_at"]) if summary["oldest_fetched_at"] else None
                    ),
                    "latest_fetched_at": (
                        _iso(summary["latest_fetched_at"]) if summary["latest_fetched_at"] else None
                    ),
                }
                for source, summary in sorted(sources.items())
            },
        }

    def upsert(
        self,
        source: str,
        cache_key: str,
        *,
        normalized_identity: dict[str, Any],
        request_identity: dict[str, Any],
        status: str,
        summary: dict[str, Any],
        raw: Any,
        warnings: list[str],
        source_url: str | None,
        ttl_days: int,
        source_version: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=ttl_days)
        with session_scope(self.session_factory) as session:
            record = session.execute(
                select(SourceCacheRecord).where(
                    SourceCacheRecord.source == source,
                    SourceCacheRecord.cache_key == cache_key,
                )
            ).scalar_one_or_none()
            if record is None:
                session.add(
                    SourceCacheRecord(
                        source=source,
                        cache_key=cache_key,
                        normalized_identity=dict(normalized_identity),
                        request_identity=dict(request_identity),
                        status=status,
                        source_version=source_version,
                        summary=dict(summary),
                        raw=raw,
                        warnings=list(warnings),
                        source_url=source_url,
                        fetched_at=now,
                        expires_at=expires_at,
                        created_at=now,
                        updated_at=now,
                    )
                )
                return

            record.normalized_identity = dict(normalized_identity)
            record.request_identity = dict(request_identity)
            record.status = status
            record.source_version = source_version
            record.summary = dict(summary)
            record.raw = raw
            record.warnings = list(warnings)
            record.source_url = source_url
            record.fetched_at = now
            record.expires_at = expires_at
            record.updated_at = now


def _payload_from_record(record: SourceCacheRecord) -> SourceCachePayload:
    return SourceCachePayload(
        source=record.source,
        cache_key=record.cache_key,
        normalized_identity=dict(record.normalized_identity or {}),
        request_identity=dict(record.request_identity or {}),
        status=record.status,
        source_version=record.source_version,
        summary=dict(record.summary or {}),
        raw=record.raw,
        warnings=list(record.warnings or []),
        source_url=record.source_url,
        fetched_at=record.fetched_at,
        expires_at=record.expires_at,
    )
