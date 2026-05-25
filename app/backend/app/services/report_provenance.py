from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.schemas.run import EvidenceSourceSummary, SourceProvenance, SourceStatus


def provenance_from_evidence(
    evidence: list[EvidenceSourceSummary],
    *,
    retrieved_at: datetime | None = None,
) -> list[SourceProvenance]:
    default_timestamp = retrieved_at or datetime.now(timezone.utc)
    return [
        SourceProvenance(
            source=item.source,
            status=normalize_source_status(item.status),
            query=_string_query_identity(item.request_identity),
            source_url=item.source_url,
            retrieved_at=_parse_timestamp(item.fetched_at) or default_timestamp,
            version=item.source_version,
            warnings=list(item.warnings),
        )
        for item in evidence
    ]


def provenance_for_source(
    source: str,
    *,
    status: str,
    query: dict[str, Any] | None = None,
    source_url: str | None = None,
    version: str | None = None,
    warnings: list[str] | None = None,
) -> SourceProvenance:
    return SourceProvenance(
        source=source,
        status=normalize_source_status(status),
        query=_string_query_identity(query or {}),
        source_url=source_url,
        version=version,
        retrieved_at=datetime.now(timezone.utc),
        warnings=list(warnings or []),
    )


def normalize_source_status(status: str | None) -> SourceStatus:
    normalized = (status or "").strip().lower()
    if normalized in {
        "live",
        "cache",
        "stale",
        "fixture",
        "fallback",
        "missing",
        "live_stub",
        "error",
        "failed",
    }:
        return normalized  # type: ignore[return-value]
    if normalized in {"degraded", "stub", "unavailable"}:
        return "fallback"
    if normalized in {"timeout"}:
        return "error"
    if not normalized:
        return "missing"
    return "fallback"


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _string_query_identity(identity: dict[str, Any]) -> dict[str, str]:
    query: dict[str, str] = {}
    for key, value in identity.items():
        if value is None:
            continue
        if isinstance(value, str):
            text = value.strip()
        elif isinstance(value, bool | int | float):
            text = str(value)
        else:
            continue
        if text:
            query[str(key)] = text
    return query
