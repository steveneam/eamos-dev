from __future__ import annotations

from collections.abc import Sequence

from app.schemas.report import UploadedReport
from app.schemas.run import RunResponse
from app.schemas.search import SearchDocumentWrite, SearchVariantWrite


class SearchIndexService:
    def __init__(self, search_repo, reports_repo, run_repo) -> None:
        self.search_repo = search_repo
        self.reports_repo = reports_repo
        self.run_repo = run_repo
        self._run_loader = getattr(run_repo, "get_run", None)

    def index_report(self, report: UploadedReport) -> None:
        document = self._build_report_document(report)
        self.search_repo.upsert_document(document)

    def index_run(self, run: RunResponse, reports: list[UploadedReport] | None = None) -> None:
        normalized_run = self._coerce_run(run)
        source_reports = reports or [
            report
            for report_id in normalized_run.report_ids
            if (report := self.reports_repo.get(report_id)) is not None
        ]
        document = self._build_run_document(normalized_run, source_reports)
        self.search_repo.upsert_document(document)

    def refresh_run(self, run_id: str) -> None:
        run = self._run_loader(run_id) if self._run_loader is not None else self.run_repo.get(run_id)
        if run is None:
            return
        self.index_run(run)

    def _coerce_run(self, run: RunResponse) -> RunResponse:
        if isinstance(run, RunResponse):
            return run
        if isinstance(run, dict):
            return RunResponse(**run)
        return RunResponse.model_validate(run)

    def _build_report_document(self, report: UploadedReport) -> SearchDocumentWrite:
        variants = [self._build_variant_write(item) for item in report.extracted_case.variants]
        identifier_parts: list[object | None] = [
            report.report_id,
            report.filename,
            report.extracted_case.case_label,
            report.extracted_case.report_title,
        ]
        for variant in report.extracted_case.variants:
            identifier_parts.extend(
                [variant.gene, variant.transcript_hgvs, variant.protein_change]
            )

        summary_text = self._join_text([
            report.extracted_case.patient_context,
            report.extracted_case.clinical_findings,
            report.extracted_case.summary,
        ])
        raw_extracted_text = (report.raw_extracted_text or "").strip()

        return SearchDocumentWrite(
            source_key=f"report:{report.report_id}",
            doc_type="report",
            report_id=report.report_id,
            filename=report.filename,
            report_kind=report.report_kind,
            extraction_status=report.extraction_status,
            case_label=report.extracted_case.case_label,
            report_title=report.extracted_case.report_title,
            summary_text=summary_text,
            evidence_text="\n".join(report.extraction_warnings),
            raw_extracted_text=raw_extracted_text,
            identifier_text=self._join_text(identifier_parts),
            search_text=self._join_text(
                [
                    *identifier_parts,
                    summary_text,
                    raw_extracted_text,
                    *report.extraction_warnings,
                ]
            ),
            variants=variants,
        )

    def _build_run_document(
        self,
        run: RunResponse,
        reports: list[UploadedReport],
    ) -> SearchDocumentWrite:
        variants = self._collect_variants(reports)
        titles = [report.extracted_case.report_title for report in reports if report.extracted_case.report_title]
        case_labels = [report.extracted_case.case_label for report in reports if report.extracted_case.case_label]
        raw_extracted_text = "\n\n".join(
            report.raw_extracted_text.strip()
            for report in reports
            if report.raw_extracted_text and report.raw_extracted_text.strip()
        )
        summary_text = self._join_text(
            [
                run.report_payload.patient_context,
                run.report_payload.ai_clinical_summary,
                run.report_payload.clinical_phenotype,
                run.report_payload.clinical_integration,
                run.report_payload.recommendations,
                run.report_payload.limitations,
            ]
        )
        evidence_text = self._join_text(
            [
                run.report_payload.expanded_evidence,
                run.report_payload.acmg_classification,
                *run.warnings,
                *[
                    self._join_text(
                        [
                            item.source,
                            item.status,
                            *item.warnings,
                            *(
                                item.summary.values() if getattr(item, "summary", None) else []
                            ),
                        ]
                    )
                    for item in run.evidence
                ],
            ]
        )
        identifier_parts: list[object | None] = [
            run.run_id,
            run.patient_id,
            *run.report_ids,
            *titles,
            *case_labels,
        ]
        for variant in variants:
            identifier_parts.extend(
                [variant.gene_symbol, variant.transcript_hgvs, variant.protein_change]
            )

        return SearchDocumentWrite(
            source_key=f"run:{run.run_id}",
            doc_type="run",
            run_id=run.run_id,
            patient_id=run.patient_id,
            run_status=run.run_status.value,
            review_status=run.review_status.value,
            case_label=case_labels[0] if case_labels else None,
            report_title=titles[0] if titles else None,
            summary_text=summary_text,
            evidence_text=evidence_text,
            review_note=(run.review_note or "").strip(),
            raw_extracted_text=raw_extracted_text,
            identifier_text=self._join_text(identifier_parts),
            search_text=self._join_text(
                [
                    *identifier_parts,
                    summary_text,
                    evidence_text,
                    raw_extracted_text,
                    run.review_note,
                ]
            ),
            variants=variants,
        )

    def _collect_variants(self, reports: list[UploadedReport]) -> list[SearchVariantWrite]:
        seen: set[tuple[str | None, str | None, str | None]] = set()
        rows: list[SearchVariantWrite] = []
        for report in reports:
            for variant in report.extracted_case.variants:
                key = (variant.gene, variant.transcript_hgvs, variant.protein_change)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(self._build_variant_write(variant))
        return rows

    def _build_variant_write(self, variant) -> SearchVariantWrite:
        gene = (variant.gene or "").strip() or None
        transcript_hgvs = (variant.transcript_hgvs or "").strip() or None
        protein_change = (variant.protein_change or "").strip() or None
        return SearchVariantWrite(
            gene_symbol=gene,
            gene_symbol_norm=gene.upper() if gene else None,
            transcript_hgvs=transcript_hgvs,
            transcript_hgvs_norm=self._normalize_identifier(transcript_hgvs),
            protein_change=protein_change,
            protein_change_norm=self._normalize_identifier(protein_change),
            consequence=(variant.consequence or "").strip() or None,
        )

    def _join_text(self, items: Sequence[object | None]) -> str:
        return "\n".join(str(item).strip() for item in items if str(item or "").strip())

    def _normalize_identifier(self, value: str | None) -> str | None:
        if not value:
            return None
        return "".join(value.split()).lower()
