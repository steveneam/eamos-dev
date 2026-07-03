from __future__ import annotations

from typing import Any, Literal, cast
from urllib.parse import quote

from app.schemas.search import (
    SearchAccessContext,
    SearchDocType,
    SearchHit,
    SearchMatchType,
    SearchRequestFilters,
    SearchResponse,
)

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
        access_context: SearchAccessContext,
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
                normalized, filters, access_context, limit
            ):
                combined[record.source_key] = (record, score, match_type)

        if query_mode in {"variant", "mixed"}:
            for record, score, match_type in self.search_repo.search_exact_variants(
                query_norm, gene_norm, filters, access_context, limit
            ):
                self._merge_match(combined, record, score, match_type)

        for record, score, match_type in self.search_repo.search_full_text(
            normalized, filters, access_context, limit
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
        metadata = self._metadata(record)
        return SearchHit(
            source_key=record.source_key,
            doc_type=cast(SearchDocType, record.doc_type),
            visibility_scope=record.visibility_scope,
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
            subtitle=self._build_subtitle(record, metadata),
            snippet=self._build_snippet(record, query),
            target_href=self._build_target_href(record, metadata),
            metadata=metadata,
            match_type=match_type,
            score=score,
            run_status=record.run_status,
            review_status=record.review_status,
            extraction_status=record.extraction_status,
            updated_at=record.updated_at,
        )

    def _metadata(self, record) -> dict[str, str | int | float | bool | None]:
        raw = getattr(record, "metadata_json", None)
        if not isinstance(raw, dict):
            return {}
        metadata: dict[str, str | int | float | bool | None] = {}
        for key, value in raw.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                metadata[str(key)] = value
            else:
                metadata[str(key)] = str(value)
        return metadata

    def _build_subtitle(
        self,
        record,
        metadata: dict[str, str | int | float | bool | None],
    ) -> str | None:
        if record.doc_type == "popular_variant":
            view_count = metadata.get("view_count")
            if isinstance(view_count, int):
                suffix = "view" if view_count == 1 else "views"
                return f"{view_count} {suffix}"
        if record.doc_type == "publication":
            parts = [
                str(value).strip()
                for value in (metadata.get("journal"), metadata.get("year"), metadata.get("pmid"))
                if str(value or "").strip()
            ]
            return " | ".join(parts) or None
        if record.doc_type == "trial":
            parts = [
                str(value).strip()
                for value in (metadata.get("status"), metadata.get("phase"), metadata.get("nct_id"))
                if str(value or "").strip()
            ]
            return " | ".join(parts) or None
        if record.doc_type == "library_variant":
            classification = metadata.get("classification")
            return str(classification).replace("_", " ") if classification else None
        if record.doc_type == "report_section":
            section_id = metadata.get("section_id")
            return f"Report section: {section_id}" if section_id else None
        if record.doc_type == "gene":
            publication_count = metadata.get("publication_count")
            trial_count = metadata.get("trial_count")
            parts = []
            if isinstance(publication_count, int) and publication_count > 0:
                suffix = "publication" if publication_count == 1 else "publications"
                parts.append(f"{publication_count} {suffix}")
            if isinstance(trial_count, int) and trial_count > 0:
                suffix = "trial" if trial_count == 1 else "trials"
                parts.append(f"{trial_count} {suffix}")
            return " | ".join(parts) or "Source-backed gene"
        if record.doc_type == "condition":
            parts = []
            phenotype_count = metadata.get("hpo_phenotype_count")
            gene_count = metadata.get("gene_count")
            if isinstance(phenotype_count, int) and phenotype_count > 0:
                suffix = "phenotype" if phenotype_count == 1 else "phenotypes"
                parts.append(f"{phenotype_count} HPO {suffix}")
            if isinstance(gene_count, int) and gene_count > 0:
                suffix = "gene" if gene_count == 1 else "genes"
                parts.append(f"{gene_count} {suffix}")
            source_ids = metadata.get("source_ids")
            if isinstance(source_ids, str) and source_ids:
                parts.append(source_ids)
            return " | ".join(parts) or "Clinical source condition"
        if record.doc_type == "gene_disease":
            parts = [
                str(value).strip()
                for value in (
                    metadata.get("clingen_classification"),
                    metadata.get("gencc_assertions"),
                    metadata.get("disease_id"),
                )
                if str(value or "").strip()
            ]
            return " | ".join(parts) or "Gene-disease assertion"
        if record.doc_type == "source":
            parts = [
                str(value).strip()
                for value in (
                    metadata.get("status"),
                    metadata.get("tier"),
                    metadata.get("source_version"),
                )
                if str(value or "").strip()
            ]
            return " | ".join(parts) or None
        return record.case_label or record.filename

    def _build_target_href(
        self,
        record,
        metadata: dict[str, str | int | float | bool | None],
    ) -> str | None:
        target_href = metadata.get("target_href")
        if isinstance(target_href, str) and (
            target_href.startswith("/") or target_href.startswith("https://")
        ):
            return target_href
        if record.doc_type == "publication":
            pmid = metadata.get("pmid") or self._source_key_suffix(record.source_key, "pmid:")
            return f"https://pubmed.ncbi.nlm.nih.gov/{quote(str(pmid))}/" if pmid else None
        if record.doc_type == "trial":
            nct_id = metadata.get("nct_id") or self._source_key_suffix(record.source_key, "trial:")
            return f"https://clinicaltrials.gov/study/{quote(str(nct_id))}" if nct_id else None
        if record.doc_type in {"library_variant", "popular_variant"}:
            report_query = metadata.get("query") or metadata.get("query_id") or record.report_title
            return f"/report?q={quote(str(report_query))}" if report_query else None
        if record.doc_type == "gene":
            gene = metadata.get("gene") or record.report_title
            return f"/report?q={quote(str(gene))}" if gene else None
        return None

    def _source_key_suffix(self, source_key: str, marker: str) -> str | None:
        if marker not in source_key:
            return None
        return source_key.rsplit(marker, 1)[-1].strip() or None

    def _build_snippet(self, record, query: str) -> str | None:
        sources = [
            record.summary_text,
            record.evidence_text,
            record.review_note,
        ]
        if record.visibility_scope == "private" and record.owner_user_id:
            sources.extend([record.raw_extracted_text, record.search_text])
        else:
            sources.append(record.identifier_text)
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
        if (
            query.isascii()
            and query.upper() == query
            and 1 <= len(query) <= 10
            and " " not in query
        ):
            return "mixed"
        return "text"

    def _coerce_doc_type(self, value: str | None) -> SearchDocType | None:
        if value in {
            "run",
            "report",
            "library_variant",
            "popular_variant",
            "publication",
            "trial",
            "report_section",
            "gene",
            "condition",
            "gene_disease",
            "source",
        }:
            return cast(SearchDocType, value)
        return None

    def _coerce_gene_symbol(self, query: str) -> str:
        compact = query.strip()
        if (
            compact.isascii()
            and compact.upper() == compact
            and " " not in compact
            and len(compact) <= 16
        ):
            return compact
        return ""

    def _normalize_identifier(self, value: str) -> str:
        return "".join(value.split()).lower()

    def _timestamp_value(self, record) -> float:
        stamp = record.updated_at or record.created_at
        if stamp is None:
            return 0.0
        return stamp.timestamp()
