from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import delete, func, literal, or_, select

from app.core.db import (
    SearchDocumentRecord,
    SearchVariantRecord,
    _build_search_documents_fts_expression,
    session_scope,
)
from app.schemas.search import SearchDocumentWrite, SearchRequestFilters, SearchVariantWrite

SearchRepoMatch = tuple[SearchDocumentRecord, float, Literal["exact_run_id", "exact_report_id", "exact_patient_id", "exact_variant", "full_text"]]


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

            if record is None:
                record = SearchDocumentRecord(
                    source_key=document.source_key,
                    doc_type=document.doc_type,
                    created_at=datetime.now(timezone.utc),
                )

            record.doc_type = document.doc_type
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

    def search_exact_ids(
        self, query: str, filters: SearchRequestFilters, limit: int
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
            stmt = self._apply_filters(stmt, filters)
            stmt = (
                stmt.where(or_(*clauses))
                .distinct()
                .order_by(SearchDocumentRecord.updated_at.desc(), SearchDocumentRecord.doc_type.asc())
                .limit(limit)
            )
            records = session.execute(stmt).scalars().all()
        return [(record, 0.95, "exact_variant") for record in records]

    def search_full_text(
        self, query: str, filters: SearchRequestFilters, limit: int
    ) -> list[SearchRepoMatch]:
        with session_scope(self.session_factory) as session:
            stmt = self._apply_filters(select(SearchDocumentRecord), filters)
            dialect_name = session.bind.dialect.name if session.bind is not None else "sqlite"
            if dialect_name == "postgresql":
                fts_expression = _build_search_documents_fts_expression(SearchDocumentRecord.__table__)
                ts_query = func.websearch_to_tsquery("english", query)
                rank = func.ts_rank(fts_expression, ts_query).label("score")
                stmt = (
                    select(SearchDocumentRecord, rank)
                    .where(fts_expression.op("@@")(ts_query))
                    .order_by(rank.desc(), SearchDocumentRecord.updated_at.desc())
                    .limit(limit)
                )
                stmt = self._apply_filters(stmt, filters)
                rows = session.execute(stmt).all()
                return [
                    (record, float(score or 0.0), "full_text")
                    for record, score in rows
                ]

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
            stmt = self._apply_filters(stmt, filters)
            rows = session.execute(stmt).all()
            return [(record, float(raw_score or 0.0), "full_text") for record, raw_score in rows]

    def _apply_filters(self, stmt, filters: SearchRequestFilters):
        if filters.doc_type:
            stmt = stmt.where(SearchDocumentRecord.doc_type == filters.doc_type)
        if filters.run_status:
            stmt = stmt.where(SearchDocumentRecord.run_status == filters.run_status)
        if filters.review_status:
            stmt = stmt.where(SearchDocumentRecord.review_status == filters.review_status)
        return stmt
