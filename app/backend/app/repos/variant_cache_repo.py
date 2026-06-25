from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from app.core.db import VariantCacheRecord, session_scope


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class VariantCacheRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def get_fresh(self, query_string: str, ttl_days: int) -> dict[str, Any] | None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
        with session_scope(self.session_factory) as session:
            record = session.execute(
                select(VariantCacheRecord).where(VariantCacheRecord.query_string == query_string)
            ).scalar_one_or_none()
            if record is None or _as_aware(record.created_at) < cutoff:
                return None
            return {
                "query_string": record.query_string,
                "litvar_id": record.litvar_id,
                "total_publications": record.total_publications,
                "publication_data": json.loads(record.publication_data or "{}"),
                "strict_genomic_cache": json.loads(record.strict_genomic_cache or "{}"),
                "gene_context_snapshot": json.loads(record.gene_context_snapshot or "{}"),
                "created_at": record.created_at,
            }

    def upsert(
        self,
        query_string: str,
        *,
        litvar_id: str | None,
        total_publications: int | None,
        publication_data: dict[str, Any],
        strict_genomic_cache: dict[str, Any],
        gene_context_snapshot: dict[str, Any] | None = None,
    ) -> None:
        with session_scope(self.session_factory) as session:
            now = datetime.now(timezone.utc)
            values = {
                "query_string": query_string,
                "litvar_id": litvar_id,
                "total_publications": total_publications,
                "publication_data": json.dumps(publication_data),
                "strict_genomic_cache": json.dumps(strict_genomic_cache),
                "gene_context_snapshot": json.dumps(gene_context_snapshot or {}),
                "created_at": now,
            }
            statement = insert(VariantCacheRecord).values(**values)
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=[VariantCacheRecord.query_string],
                    set_={
                        "litvar_id": statement.excluded.litvar_id,
                        "total_publications": statement.excluded.total_publications,
                        "publication_data": statement.excluded.publication_data,
                        "strict_genomic_cache": statement.excluded.strict_genomic_cache,
                        "gene_context_snapshot": statement.excluded.gene_context_snapshot,
                        "created_at": statement.excluded.created_at,
                    },
                )
            )

    def update_gene_context_snapshot(
        self,
        query_string: str,
        *,
        gene_context_snapshot: dict[str, Any],
    ) -> None:
        with session_scope(self.session_factory) as session:
            record = session.execute(
                select(VariantCacheRecord).where(VariantCacheRecord.query_string == query_string)
            ).scalar_one_or_none()
            if record is None:
                return
            record.gene_context_snapshot = json.dumps(gene_context_snapshot)

    def update_report_shell(
        self,
        query_string: str,
        *,
        report_shell: dict[str, Any],
    ) -> None:
        with session_scope(self.session_factory) as session:
            record = session.execute(
                select(VariantCacheRecord).where(VariantCacheRecord.query_string == query_string)
            ).scalar_one_or_none()
            if record is None:
                return
            publication_data = json.loads(record.publication_data or "{}")
            publication_data["report_shell"] = report_shell
            record.publication_data = json.dumps(publication_data)

    def update_report_sections(
        self,
        query_string: str,
        *,
        report_sections: dict[str, Any],
    ) -> None:
        with session_scope(self.session_factory) as session:
            record = session.execute(
                select(VariantCacheRecord).where(VariantCacheRecord.query_string == query_string)
            ).scalar_one_or_none()
            if record is None:
                return
            publication_data = json.loads(record.publication_data or "{}")
            publication_data["report_sections"] = report_sections
            record.publication_data = json.dumps(publication_data)
