from __future__ import annotations

from typing import Any, Literal, cast

from app.schemas.search import SearchDocType, SearchHit, SearchMatchType, SearchRequestFilters, SearchResponse


QueryMode = Literal["id", "variant", "text", "mixed"]


class SearchService:
    MATCH_PRIORITY: dict[SearchMatchType, int] = {
        "exact_run_id": 0,
        "exact_report_id": 1,
        "exact_patient_id": 2,
        "exact_variant": 3,
        "full_text": 4,
    }

    def __init__(self, search_repo) -> None:
        self.search_repo = search_repo

    def search(
        self,
        query: str,
        limit: int = 10,
        doc_type: str | None = None,
        run_status: str | None = None,
        review_status: str | None = None,
    ) -> SearchResponse:
        normalized = query.strip()
        if not normalized:
            return SearchResponse(query=query, results=[])

        filters = SearchRequestFilters(
            doc_type=self._coerce_doc_type(doc_type),
            run_status=run_status,
            review_status=review_status,
        )
        query_norm = self._normalize_identifier(normalized)
        gene_norm = self._coerce_gene_symbol(normalized)
        query_mode = self._classify_query(normalized)

        combined: dict[str, tuple[Any, float, SearchMatchType]] = {}

        if query_mode in {"id", "mixed"}:
            for record, score, match_type in self.search_repo.search_exact_ids(
                normalized, filters, limit
            ):
                combined[record.source_key] = (record, score, match_type)

        if query_mode in {"variant", "mixed"}:
            for record, score, match_type in self.search_repo.search_exact_variants(
                query_norm, gene_norm, filters, limit
            ):
                self._merge_match(combined, record, score, match_type)

        for record, score, match_type in self.search_repo.search_full_text(
            normalized, filters, limit
        ):
            self._merge_match(combined, record, score, match_type)

        ranked = sorted(
            combined.values(),
            key=lambda item: (
                self.MATCH_PRIORITY[item[2]],
                0 if item[0].doc_type == "run" else 1,
                -float(item[1]),
                -self._timestamp_value(item[0]),
            ),
        )

        results = [
            self._build_hit(record, float(score), match_type, normalized)
            for record, score, match_type in ranked[:limit]
        ]
        return SearchResponse(query=query, results=results)

    def _merge_match(self, combined, record, score: float, match_type: SearchMatchType) -> None:
        existing = combined.get(record.source_key)
        if existing is None:
            combined[record.source_key] = (record, score, match_type)
            return

        existing_priority = self.MATCH_PRIORITY[existing[2]]
        next_priority = self.MATCH_PRIORITY[match_type]
        if next_priority < existing_priority or (
            next_priority == existing_priority and float(score) > float(existing[1])
        ):
            combined[record.source_key] = (record, score, match_type)

    def _build_hit(
        self,
        record,
        score: float,
        match_type: SearchMatchType,
        query: str,
    ) -> SearchHit:
        return SearchHit(
            doc_type=cast(SearchDocType, record.doc_type),
            run_id=record.run_id,
            report_id=record.report_id,
            patient_id=record.patient_id,
            title=(
                record.report_title
                or record.case_label
                or record.filename
                or record.run_id
                or record.report_id
                or "Untitled record"
            ),
            snippet=self._build_snippet(record, query),
            match_type=match_type,
            score=score,
            run_status=record.run_status,
            review_status=record.review_status,
            extraction_status=record.extraction_status,
            updated_at=record.updated_at,
        )

    def _build_snippet(self, record, query: str) -> str | None:
        sources = [
            record.summary_text,
            record.evidence_text,
            record.review_note,
            record.raw_extracted_text,
            record.search_text,
        ]
        needle = query.lower()
        for source in sources:
            text = (source or "").strip()
            if not text:
                continue
            lower = text.lower()
            position = lower.find(needle)
            if position != -1:
                start = max(0, position - 60)
                end = min(len(text), position + max(len(query), 40) + 60)
                snippet = text[start:end].replace("\n", " ").strip()
                if start > 0:
                    snippet = f"…{snippet}"
                if end < len(text):
                    snippet = f"{snippet}…"
                return snippet
        for source in sources:
            text = (source or "").strip()
            if text:
                return text.replace("\n", " ")[:220]
        return None

    def _classify_query(self, query: str) -> QueryMode:
        if query.startswith("run_") or query.startswith("report_"):
            return "id"
        lowered = query.lower()
        if lowered.startswith("p.") or ":c." in lowered or lowered.startswith("nm_"):
            return "variant"
        if query.isascii() and query.upper() == query and 1 <= len(query) <= 10 and " " not in query:
            return "mixed"
        return "text"

    def _coerce_doc_type(self, value: str | None) -> SearchDocType | None:
        if value in {"run", "report"}:
            return cast(SearchDocType, value)
        return None

    def _coerce_gene_symbol(self, query: str) -> str:
        compact = query.strip()
        if compact.isascii() and compact.upper() == compact and " " not in compact and len(compact) <= 16:
            return compact
        return ""

    def _normalize_identifier(self, value: str) -> str:
        return "".join(value.split()).lower()

    def _timestamp_value(self, record) -> float:
        stamp = record.updated_at or record.created_at
        if stamp is None:
            return 0.0
        return stamp.timestamp()
