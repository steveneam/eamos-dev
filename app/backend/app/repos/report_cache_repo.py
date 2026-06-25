from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any

from sqlalchemy import select

from app.core.db import (
    NormalizedVariantRecord,
    ReportSectionCacheRecord,
    ReportShellCacheRecord,
    SectionHydrationStatusRecord,
    SourceResultCacheRecord,
    session_scope,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _stale_after(ttl_days: int) -> datetime:
    return _now() + timedelta(days=ttl_days)


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return {
            "serialization_status": "unavailable",
            "serialization_error_type": type(value).__name__,
        }
    return value


def _dedupe_text(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _identity_id(identity: dict[str, Any]) -> str:
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _source_versions_from_freshness(freshness: dict[str, Any]) -> dict[str, Any]:
    source_version = freshness.get("source_version")
    return {"source_version": source_version} if source_version else {}


class ReportCacheRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def get_report_shell(
        self,
        query_string: str,
        *,
        schema_version: int,
        ttl_days: int,
    ) -> dict[str, Any] | None:
        cutoff = _now() - timedelta(days=ttl_days)
        with session_scope(self.session_factory) as session:
            record = session.execute(
                select(ReportShellCacheRecord).where(
                    ReportShellCacheRecord.query_string == query_string,
                    ReportShellCacheRecord.schema_version == schema_version,
                )
            ).scalar_one_or_none()
            if record is None:
                return None
            if record.stale_after is not None and _as_aware(record.stale_after) <= _now():
                return None
            if record.stale_after is None and _as_aware(record.generated_at) < cutoff:
                return None
            return dict(record.payload_json or {})

    def upsert_report_shell(
        self,
        query_string: str,
        *,
        normalized_identity: dict[str, Any],
        schema_version: int,
        payload: dict[str, Any],
        ttl_days: int,
        freshness: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
        source_versions: dict[str, Any] | None = None,
    ) -> None:
        now = _now()
        identity_id = _identity_id(normalized_identity)
        with session_scope(self.session_factory) as session:
            _upsert_normalized_variant(
                session,
                identity_id=identity_id,
                query_string=query_string,
                normalized_identity=normalized_identity,
                now=now,
            )
            record = session.execute(
                select(ReportShellCacheRecord).where(
                    ReportShellCacheRecord.normalized_variant_id == identity_id,
                    ReportShellCacheRecord.schema_version == schema_version,
                )
            ).scalar_one_or_none()
            if record is None:
                session.add(
                    ReportShellCacheRecord(
                        normalized_variant_id=identity_id,
                        query_string=query_string,
                        schema_version=schema_version,
                        payload_json=dict(payload),
                        freshness_json=dict(freshness or {}),
                        warnings_json=list(warnings or []),
                        source_versions_json=dict(source_versions or {}),
                        generated_at=now,
                        stale_after=_stale_after(ttl_days),
                        created_at=now,
                        updated_at=now,
                    )
                )
                return

            record.query_string = query_string
            record.payload_json = dict(payload)
            record.freshness_json = dict(freshness or {})
            record.warnings_json = list(warnings or [])
            record.source_versions_json = dict(source_versions or {})
            record.generated_at = now
            record.stale_after = _stale_after(ttl_days)
            record.updated_at = now

    def get_report_sections(
        self,
        query_string: str,
        *,
        section_ids: list[str],
        schema_version: int,
        ttl_days: int,
    ) -> dict[str, Any] | None:
        include = _dedupe_text(section_ids)
        if not include:
            return None
        cutoff = _now() - timedelta(days=ttl_days)
        with session_scope(self.session_factory) as session:
            records = (
                session.execute(
                    select(ReportSectionCacheRecord).where(
                        ReportSectionCacheRecord.query_string == query_string,
                        ReportSectionCacheRecord.schema_version == schema_version,
                        ReportSectionCacheRecord.section_id.in_(include),
                    )
                )
                .scalars()
                .all()
            )

            by_section = {record.section_id: record for record in records}
            if any(section_id not in by_section for section_id in include):
                return None

            sections: dict[str, Any] = {}
            species = "human"
            for section_id in include:
                record = by_section[section_id]
                if record.stale_after is not None and _as_aware(record.stale_after) <= _now():
                    return None
                if record.stale_after is None and _as_aware(record.generated_at) < cutoff:
                    return None
                species = record.species or species
                sections[section_id] = {
                    "section_id": section_id,
                    "status": record.status,
                    "payload": record.payload_json,
                    "freshness": dict(record.freshness_json or {}),
                    "warnings": list(record.warnings_json or []),
                }

        return {
            "query": query_string,
            "species": species,
            "sections": sections,
            "warnings": [],
        }

    def upsert_report_sections(
        self,
        query_string: str,
        *,
        normalized_identity: dict[str, Any],
        schema_version: int,
        response_payload: dict[str, Any],
        ttl_days: int,
    ) -> None:
        sections = response_payload.get("sections")
        if not isinstance(sections, dict):
            return

        now = _now()
        identity_id = _identity_id(normalized_identity)
        species = str(
            response_payload.get("species") or normalized_identity.get("species") or "human"
        )
        with session_scope(self.session_factory) as session:
            _upsert_normalized_variant(
                session,
                identity_id=identity_id,
                query_string=query_string,
                normalized_identity=normalized_identity,
                now=now,
            )
            for section_id, envelope in sections.items():
                if not isinstance(envelope, dict):
                    continue
                freshness = dict(envelope.get("freshness") or {})
                record = session.execute(
                    select(ReportSectionCacheRecord).where(
                        ReportSectionCacheRecord.normalized_variant_id == identity_id,
                        ReportSectionCacheRecord.section_id == str(section_id),
                        ReportSectionCacheRecord.schema_version == schema_version,
                    )
                ).scalar_one_or_none()
                values = {
                    "query_string": query_string,
                    "species": species,
                    "section_id": str(section_id),
                    "schema_version": schema_version,
                    "status": str(envelope.get("status") or "missing"),
                    "payload_json": _json_safe(envelope.get("payload")),
                    "freshness_json": freshness,
                    "warnings_json": list(envelope.get("warnings") or []),
                    "source_versions_json": _source_versions_from_freshness(freshness),
                    "generated_at": now,
                    "stale_after": _stale_after(ttl_days),
                    "updated_at": now,
                }
                if record is None:
                    session.add(
                        ReportSectionCacheRecord(
                            normalized_variant_id=identity_id,
                            created_at=now,
                            **values,
                        )
                    )
                    continue
                for key, value in values.items():
                    setattr(record, key, value)

    def upsert_source_result(
        self,
        query_string: str,
        *,
        normalized_identity: dict[str, Any],
        source_id: str,
        schema_version: int,
        status: str,
        payload: dict[str, Any],
        raw: Any,
        warnings: list[str],
        ttl_days: int,
        freshness: dict[str, Any] | None = None,
        source_versions: dict[str, Any] | None = None,
    ) -> None:
        now = _now()
        identity_id = _identity_id(normalized_identity)
        with session_scope(self.session_factory) as session:
            _upsert_normalized_variant(
                session,
                identity_id=identity_id,
                query_string=query_string,
                normalized_identity=normalized_identity,
                now=now,
            )
            record = session.execute(
                select(SourceResultCacheRecord).where(
                    SourceResultCacheRecord.normalized_variant_id == identity_id,
                    SourceResultCacheRecord.source_id == source_id,
                    SourceResultCacheRecord.schema_version == schema_version,
                )
            ).scalar_one_or_none()
            values = {
                "query_string": query_string,
                "source_id": source_id,
                "schema_version": schema_version,
                "status": status,
                "payload_json": dict(payload),
                "raw_json": _json_safe(raw),
                "freshness_json": dict(freshness or {}),
                "warnings_json": list(warnings),
                "source_versions_json": dict(source_versions or {}),
                "generated_at": now,
                "stale_after": _stale_after(ttl_days),
                "updated_at": now,
            }
            if record is None:
                session.add(
                    SourceResultCacheRecord(
                        normalized_variant_id=identity_id,
                        created_at=now,
                        **values,
                    )
                )
                return
            for key, value in values.items():
                setattr(record, key, value)

    def get_source_results(
        self,
        query_string: str,
        *,
        source_ids: list[str],
        schema_version: int,
        ttl_days: int,
    ) -> dict[str, dict[str, Any]]:
        include = _dedupe_text(source_ids)
        if not include:
            return {}
        cutoff = _now() - timedelta(days=ttl_days)
        with session_scope(self.session_factory) as session:
            records = (
                session.execute(
                    select(SourceResultCacheRecord).where(
                        SourceResultCacheRecord.query_string == query_string,
                        SourceResultCacheRecord.schema_version == schema_version,
                        SourceResultCacheRecord.source_id.in_(include),
                    )
                )
                .scalars()
                .all()
            )

            results: dict[str, dict[str, Any]] = {}
            for record in records:
                if record.stale_after is not None and _as_aware(record.stale_after) <= _now():
                    continue
                if record.stale_after is None and _as_aware(record.generated_at) < cutoff:
                    continue
                results[record.source_id] = {
                    "source_id": record.source_id,
                    "status": record.status,
                    "payload": dict(record.payload_json or {}),
                    "raw": record.raw_json,
                    "freshness": dict(record.freshness_json or {}),
                    "warnings": list(record.warnings_json or []),
                    "source_versions": dict(record.source_versions_json or {}),
                }
        return results

    def set_section_hydration_status(
        self,
        query_string: str,
        *,
        normalized_identity: dict[str, Any],
        section_id: str,
        status: str,
        fail_closed_reason: str | None = None,
        warnings: list[str] | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        now = _now()
        identity_id = _identity_id(normalized_identity)
        with session_scope(self.session_factory) as session:
            _upsert_normalized_variant(
                session,
                identity_id=identity_id,
                query_string=query_string,
                normalized_identity=normalized_identity,
                now=now,
            )
            record = session.execute(
                select(SectionHydrationStatusRecord).where(
                    SectionHydrationStatusRecord.normalized_variant_id == identity_id,
                    SectionHydrationStatusRecord.section_id == section_id,
                )
            ).scalar_one_or_none()
            values = {
                "query_string": query_string,
                "section_id": section_id,
                "status": status,
                "fail_closed_reason": fail_closed_reason,
                "warnings_json": list(warnings or []),
                "started_at": started_at,
                "completed_at": completed_at,
                "updated_at": now,
            }
            if record is None:
                session.add(
                    SectionHydrationStatusRecord(
                        normalized_variant_id=identity_id,
                        **values,
                    )
                )
                return
            for key, value in values.items():
                setattr(record, key, value)


def _upsert_normalized_variant(
    session,
    *,
    identity_id: str,
    query_string: str,
    normalized_identity: dict[str, Any],
    now: datetime,
) -> None:
    record = session.execute(
        select(NormalizedVariantRecord).where(
            NormalizedVariantRecord.normalized_variant_id == identity_id
        )
    ).scalar_one_or_none()
    values = {
        "query_string": query_string,
        "species": str(normalized_identity.get("species") or "human"),
        "genome_build": str(normalized_identity.get("genome_build") or "GRCh38"),
        "gene": normalized_identity.get("gene"),
        "cdna": normalized_identity.get("cdna"),
        "transcript": normalized_identity.get("transcript"),
        "protein_change": normalized_identity.get("protein_change"),
        "genomic_hg38": normalized_identity.get("genomic_hg38"),
        "genomic_hgvs": normalized_identity.get("genomic_hgvs"),
        "identity_version": int(normalized_identity.get("identity_version") or 1),
        "normalized_identity": dict(normalized_identity),
        "request_identity": dict(normalized_identity.get("request_identity") or {}),
        "updated_at": now,
    }
    if record is None:
        session.add(
            NormalizedVariantRecord(
                normalized_variant_id=identity_id,
                created_at=now,
                **values,
            )
        )
        return
    for key, value in values.items():
        setattr(record, key, value)
