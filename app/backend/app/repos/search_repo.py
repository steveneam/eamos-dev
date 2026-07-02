from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import and_, delete, func, inspect, literal, or_, select

from app.core.db import (
    SearchDocumentRecord,
    SearchVariantRecord,
    _build_search_documents_fts_expression,
    session_scope,
)
from app.schemas.search import SearchAccessContext, SearchDocumentWrite, SearchRequestFilters

SearchRepoMatch = tuple[
    SearchDocumentRecord,
    float,
    Literal["exact_run_id", "exact_report_id", "exact_patient_id", "exact_variant", "full_text"],
]


class SearchRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def upsert_document(self, document: SearchDocumentWrite) -> SearchDocumentRecord:
        with session_scope(self.session_factory) as session:
            record = session.execute(
                select(SearchDocumentRecord).where(
                    SearchDocumentRecord.source_key == document.source_key
                )
            ).scalar_one_or_none()

            record_exists = record is not None
            if record is None:
                record = SearchDocumentRecord(
                    source_key=document.source_key,
                    doc_type=document.doc_type,
                    created_at=datetime.now(timezone.utc),
                )

            record.doc_type = document.doc_type
            if record_exists and document.owner_user_id is None:
                record.visibility_scope = record.visibility_scope or document.visibility_scope
            else:
                record.visibility_scope = document.visibility_scope
                record.owner_user_id = document.owner_user_id
            record.run_id = document.run_id
            record.report_id = document.report_id
            record.patient_id = document.patient_id
            record.filename = document.filename
            record.report_kind = document.report_kind
            record.extraction_status = document.extraction_status
            record.run_status = document.run_status
            record.review_status = document.review_status
            record.case_label = document.case_label
            record.report_title = document.report_title
            record.summary_text = document.summary_text
            record.evidence_text = document.evidence_text
            record.review_note = document.review_note
            record.raw_extracted_text = document.raw_extracted_text
            record.identifier_text = document.identifier_text
            record.search_text = document.search_text
            record.metadata_json = dict(document.metadata)
            record.updated_at = datetime.now(timezone.utc)
            session.add(record)
            session.flush()

            session.execute(
                delete(SearchVariantRecord).where(SearchVariantRecord.document_id == record.doc_id)
            )
            for variant in document.variants:
                session.add(
                    SearchVariantRecord(
                        document_id=record.doc_id,
                        gene_symbol=variant.gene_symbol,
                        gene_symbol_norm=variant.gene_symbol_norm,
                        transcript_hgvs=variant.transcript_hgvs,
                        transcript_hgvs_norm=variant.transcript_hgvs_norm,
                        protein_change=variant.protein_change,
                        protein_change_norm=variant.protein_change_norm,
                        consequence=variant.consequence,
                    )
                )
            return record

    def delete_document(self, *, source_key: str) -> bool:
        with session_scope(self.session_factory) as session:
            record = session.execute(
                select(SearchDocumentRecord).where(SearchDocumentRecord.source_key == source_key)
            ).scalar_one_or_none()
            if record is None:
                return False
            session.execute(
                delete(SearchVariantRecord).where(SearchVariantRecord.document_id == record.doc_id)
            )
            session.delete(record)
            return True

    def delete_owner_documents(self, *, doc_type: str, owner_user_id: str) -> int:
        with session_scope(self.session_factory) as session:
            doc_ids = list(
                session.execute(
                    select(SearchDocumentRecord.doc_id).where(
                        SearchDocumentRecord.doc_type == doc_type,
                        SearchDocumentRecord.owner_user_id == owner_user_id,
                    )
                ).scalars()
            )
            if not doc_ids:
                return 0
            session.execute(
                delete(SearchVariantRecord).where(SearchVariantRecord.document_id.in_(doc_ids))
            )
            result = session.execute(
                delete(SearchDocumentRecord).where(SearchDocumentRecord.doc_id.in_(doc_ids))
            )
            return int(result.rowcount or 0)

    def delete_documents_by_source_key_prefix(self, *, source_key_prefix: str) -> int:
        with session_scope(self.session_factory) as session:
            doc_ids = list(
                session.execute(
                    select(SearchDocumentRecord.doc_id).where(
                        SearchDocumentRecord.source_key.like(f"{source_key_prefix}%")
                    )
                ).scalars()
            )
            if not doc_ids:
                return 0
            session.execute(
                delete(SearchVariantRecord).where(SearchVariantRecord.document_id.in_(doc_ids))
            )
            result = session.execute(
                delete(SearchDocumentRecord).where(SearchDocumentRecord.doc_id.in_(doc_ids))
            )
            return int(result.rowcount or 0)

    def owner_for_source_key(self, *, source_key: str) -> str | None:
        with session_scope(self.session_factory) as session:
            return session.execute(
                select(SearchDocumentRecord.owner_user_id).where(
                    SearchDocumentRecord.source_key == source_key
                )
            ).scalar_one_or_none()

    def search_exact_ids(
        self,
        query: str,
        filters: SearchRequestFilters,
        access_context: SearchAccessContext,
        limit: int,
    ) -> list[SearchRepoMatch]:
        clauses = []
        normalized = query.strip()
        if normalized.startswith("run_"):
            clauses.append(SearchDocumentRecord.run_id == normalized)
        if normalized.startswith("report_"):
            clauses.append(SearchDocumentRecord.report_id == normalized)
        clauses.append(SearchDocumentRecord.patient_id == normalized)

        with session_scope(self.session_factory) as session:
            stmt = select(SearchDocumentRecord)
            stmt = self._apply_access_filter(stmt, access_context)
            stmt = self._apply_filters(stmt, filters)
            stmt = stmt.where(or_(*clauses)).limit(limit)
            records = session.execute(stmt).scalars().all()

        matches: list[SearchRepoMatch] = []
        for record in records:
            if record.run_id == normalized:
                matches.append((record, 1.0, "exact_run_id"))
            elif record.report_id == normalized:
                matches.append((record, 1.0, "exact_report_id"))
            else:
                matches.append((record, 1.0, "exact_patient_id"))
        return matches

    def search_exact_variants(
        self,
        query_norm: str,
        gene_norm: str,
        filters: SearchRequestFilters,
        access_context: SearchAccessContext,
        limit: int,
    ) -> list[SearchRepoMatch]:
        clauses = []
        if gene_norm:
            clauses.append(SearchVariantRecord.gene_symbol_norm == gene_norm)
        if query_norm:
            clauses.append(SearchVariantRecord.transcript_hgvs_norm == query_norm)
            clauses.append(SearchVariantRecord.protein_change_norm == query_norm)
        if not clauses:
            return []

        with session_scope(self.session_factory) as session:
            stmt = select(SearchDocumentRecord).join(
                SearchVariantRecord,
                SearchVariantRecord.document_id == SearchDocumentRecord.doc_id,
            )
            stmt = self._apply_access_filter(stmt, access_context)
            stmt = self._apply_filters(stmt, filters)
            stmt = (
                stmt.where(or_(*clauses))
                .distinct()
                .order_by(
                    SearchDocumentRecord.updated_at.desc(), SearchDocumentRecord.doc_type.asc()
                )
                .limit(limit)
            )
            records = session.execute(stmt).scalars().all()
        return [(record, 0.95, "exact_variant") for record in records]

    def search_full_text(
        self,
        query: str,
        filters: SearchRequestFilters,
        access_context: SearchAccessContext,
        limit: int,
    ) -> list[SearchRepoMatch]:
        with session_scope(self.session_factory) as session:
            stmt = self._apply_access_filter(select(SearchDocumentRecord), access_context)
            stmt = self._apply_filters(stmt, filters)
            dialect_name = session.bind.dialect.name if session.bind is not None else "sqlite"
            if dialect_name == "postgresql":
                fts_expression = _build_search_documents_fts_expression(
                    SearchDocumentRecord.__table__
                )
                ts_query = func.websearch_to_tsquery("english", query)
                rank = func.ts_rank(fts_expression, ts_query).label("score")
                stmt = (
                    select(SearchDocumentRecord, rank)
                    .where(fts_expression.op("@@")(ts_query))
                    .order_by(rank.desc(), SearchDocumentRecord.updated_at.desc())
                    .limit(limit)
                )
                stmt = self._apply_access_filter(stmt, access_context)
                stmt = self._apply_filters(stmt, filters)
                rows = session.execute(stmt).all()
                return [(record, float(score or 0.0), "full_text") for record, score in rows]

            pattern = f"%{query.strip()}%"
            score = literal(0.1).label("score")
            stmt = (
                select(SearchDocumentRecord, score)
                .where(
                    or_(
                        SearchDocumentRecord.identifier_text.ilike(pattern),
                        SearchDocumentRecord.search_text.ilike(pattern),
                    )
                )
                .order_by(SearchDocumentRecord.updated_at.desc())
                .limit(limit)
            )
            stmt = self._apply_access_filter(stmt, access_context)
            stmt = self._apply_filters(stmt, filters)
            rows = session.execute(stmt).all()
            return [(record, float(raw_score or 0.0), "full_text") for record, raw_score in rows]

    def health_summary(self) -> dict[str, object]:
        with session_scope(self.session_factory) as session:
            bind = session.bind
            dialect_name = bind.dialect.name if bind is not None else "sqlite"
            table_names = set(inspect(bind).get_table_names()) if bind is not None else set()
            table_present = "search_documents" in table_names
            if not table_present:
                return {
                    "index_tables_present": False,
                    "postgres_fts_ready": "not_postgres" if dialect_name != "postgresql" else False,
                    "entity_counts": {},
                    "visibility_counts": {},
                    "private_rows_without_owner_count": 0,
                    "last_indexed_at": None,
                }

            entity_counts = {
                str(doc_type): int(count)
                for doc_type, count in session.execute(
                    select(SearchDocumentRecord.doc_type, func.count())
                    .group_by(SearchDocumentRecord.doc_type)
                    .order_by(SearchDocumentRecord.doc_type)
                ).all()
            }
            visibility_counts = {
                str(scope): int(count)
                for scope, count in session.execute(
                    select(SearchDocumentRecord.visibility_scope, func.count())
                    .group_by(SearchDocumentRecord.visibility_scope)
                    .order_by(SearchDocumentRecord.visibility_scope)
                ).all()
            }
            private_rows_without_owner = session.execute(
                select(func.count())
                .select_from(SearchDocumentRecord)
                .where(
                    SearchDocumentRecord.visibility_scope == "private",
                    SearchDocumentRecord.owner_user_id.is_(None),
                )
            ).scalar_one()
            last_indexed_at = session.execute(
                select(func.max(SearchDocumentRecord.updated_at))
            ).scalar_one_or_none()
            postgres_fts_ready: bool | str
            if dialect_name == "postgresql" and bind is not None:
                postgres_fts_ready = any(
                    item["name"] == "ix_search_documents_search_text_fts"
                    for item in inspect(bind).get_indexes("search_documents")
                )
            else:
                postgres_fts_ready = "not_postgres"
            return {
                "index_tables_present": True,
                "postgres_fts_ready": postgres_fts_ready,
                "entity_counts": entity_counts,
                "visibility_counts": visibility_counts,
                "private_rows_without_owner_count": int(private_rows_without_owner or 0),
                "last_indexed_at": last_indexed_at.isoformat() if last_indexed_at else None,
            }

    def _apply_access_filter(self, stmt, access_context: SearchAccessContext):
        clauses = [SearchDocumentRecord.visibility_scope == "public"]
        if access_context.user_id:
            clauses.append(
                and_(
                    SearchDocumentRecord.visibility_scope == "private",
                    SearchDocumentRecord.owner_user_id == access_context.user_id,
                )
            )
        if access_context.include_internal:
            clauses.append(SearchDocumentRecord.visibility_scope == "internal")
        return stmt.where(or_(*clauses))

    def _apply_filters(self, stmt, filters: SearchRequestFilters):
        if filters.doc_type:
            stmt = stmt.where(SearchDocumentRecord.doc_type == filters.doc_type)
        if filters.run_status:
            stmt = stmt.where(SearchDocumentRecord.run_status == filters.run_status)
        if filters.review_status:
            stmt = stmt.where(SearchDocumentRecord.review_status == filters.review_status)
        return stmt
