from __future__ import annotations

import re
from uuid import uuid4

from fastapi import HTTPException, status

from app.rules.base import DecisionInput
from app.services.lookup_service import GENE_THERAPY_MAP
from app.services.variant_decoder import decode_variant
from app.schemas.report import ExtractedCase, ExtractedVariant
from app.schemas.run import (
    EvidenceSourceSummary,
    PubMedArticle,
    ReportPayload,
    RunRequest,
    RunResponse,
    RunStatus,
    VariantSummaryRow,
)


class WorkflowService:
    def __init__(
        self, reports_repo, run_repo, tool_registry, rule_engine, draft_render_service=None
    ) -> None:
        self.reports_repo = reports_repo
        self.run_repo = run_repo
        self.tool_registry = tool_registry
        self.rule_engine = rule_engine
        self.draft_render_service = draft_render_service

    def create_run(self, payload: RunRequest) -> RunResponse:
        if not payload.report_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one report_id is required.",
            )

        reports = []
        missing = []
        for report_id in payload.report_ids:
            report = self.reports_repo.get(report_id)
            if report is None:
                missing.append(report_id)
            else:
                reports.append(report)

        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Reports not found: {", ".join(missing)}',
            )

        report_statuses = [report.extraction_status for report in reports]

        case_title = self._extract_case_title(reports)
        case_label = self._extract_case_label(reports)
        source_filenames = self._build_source_filenames(reports)
        variant_rows = self._collect_variants(reports)

        # Use the first variant as the primary query target for all evidence tools
        primary_variant = (
            reports[0].extracted_case.variants[0]
            if (reports and getattr(reports[0].extracted_case, "variants", None))
            else None
        )

        evidence = []
        evidence_map = {}
        evidence_statuses = {}
        warnings: list[str] = []
        for name in ("vep", "spliceai", "clinvar", "gnomad", "pubmed"):
            tool = self.tool_registry[name]
            result = tool.get_evidence(variant=primary_variant)
            summary = EvidenceSourceSummary(
                source=result.source,
                status=result.status,
                request_identity=result.request_identity,
                summary=result.summary,
                warnings=result.warnings,
                source_url=result.source_url,
            )
            evidence.append(summary)
            evidence_map[name] = result.summary
            evidence_statuses[name] = result.status
            warnings.extend(result.warnings)

        run_status = self._derive_run_status(report_statuses, evidence_statuses, warnings)
        variant_descriptions = [self._describe_variant(item) for item in variant_rows]
        patient_context = self._build_patient_context(
            patient_id=payload.patient_id,
            reports=reports,
            case_title=case_title,
            case_label=case_label,
            source_filenames=source_filenames,
        )
        clinical_findings = self._build_clinical_findings(
            reports,
            case_label=case_label,
            source_filenames=source_filenames,
        )

        decision_input = DecisionInput(
            case_title=case_title,
            evidence=evidence_map,
            evidence_statuses=evidence_statuses,
            case_label=case_label,
            patient_context=patient_context,
            clinical_findings=clinical_findings,
            variant_summary=variant_descriptions,
        )
        decision = self.rule_engine.evaluate(decision_input)

        report_payload, draft_warnings = self._build_report_payload(
            patient_id=payload.patient_id,
            reports=reports,
            case_title=case_title,
            case_label=case_label,
            source_filenames=source_filenames,
            patient_context=patient_context,
            clinical_findings=clinical_findings,
            variant_rows=variant_rows,
            variant_descriptions=variant_descriptions,
            decision=decision,
            evidence_map=evidence_map,
            evidence_statuses=evidence_statuses,
            warnings=warnings,
            evidence_lines=decision.evidence_lines,
        )
        warnings = [*warnings, *decision.warnings, *draft_warnings]

        run_response = self.run_repo.create_run(
            run_id=f"run_{uuid4().hex[:12]}",
            patient_id=payload.patient_id,
            report_ids=payload.report_ids,
            run_status=run_status,
            report_payload=report_payload,
            evidence=evidence,
            warnings=warnings,
        )

        return RunResponse(
            run_id=run_response.run_id,
            patient_id=run_response.patient_id,
            report_ids=run_response.report_ids,
            run_status=run_response.run_status,
            review_status=run_response.review_status,
            report_payload=report_payload,
            evidence=evidence,
            warnings=warnings,
            review_note=None,
            reviewed_at=None,
            approved_pdf_path=None,
        )

    def get_run(self, run_id: str) -> RunResponse:
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
        return run

    def _derive_run_status(
        self,
        report_statuses: list[str],
        evidence_statuses: dict[str, str],
        warnings: list[str],
    ) -> RunStatus:
        if report_statuses and all(item == "blocked" for item in report_statuses):
            return RunStatus.blocked

        evidence_problem = {
            status.lower() for status in evidence_statuses.values() if isinstance(status, str)
        }
        if evidence_problem & {"fallback", "degraded", "error", "failed"}:
            return RunStatus.degraded
        if warnings:
            return RunStatus.degraded
        if any(item in {"blocked", "degraded"} for item in report_statuses):
            return RunStatus.degraded
        return RunStatus.completed

    def _coerce_extracted_case(self, report) -> ExtractedCase:
        extracted_case = report.extracted_case
        if isinstance(extracted_case, ExtractedCase):
            return extracted_case
        return ExtractedCase.model_validate(extracted_case)

    def _extract_case_title(self, reports) -> str:
        titles = [
            self._coerce_extracted_case(report).report_title
            for report in reports
            if self._coerce_extracted_case(report).report_title
        ]
        if titles:
            return titles[0]
        return "Genomic interpretation report"

    def _extract_case_label(self, reports) -> str | None:
        labels = [
            self._coerce_extracted_case(report).case_label
            for report in reports
            if self._coerce_extracted_case(report).case_label
        ]
        return labels[0] if labels else None

    def _collect_text_blocks(self, reports, *field_names: str) -> list[str]:
        seen: set[str] = set()
        blocks: list[str] = []
        for report in reports:
            extracted = self._coerce_extracted_case(report)
            for field_name in field_names:
                text = (getattr(extracted, field_name, None) or "").strip()
                if text and text not in seen:
                    seen.add(text)
                    blocks.append(text)
        return blocks

    def _build_source_filenames(self, reports) -> list[str]:
        seen: set[str] = set()
        names: list[str] = []
        for report in reports:
            filename = (getattr(report, "filename", "") or "").strip()
            if filename and filename not in seen:
                seen.add(filename)
                names.append(filename)
        return names

    def _sanitize_report_text(
        self,
        text: str | None,
        *,
        case_label: str | None,
        source_filenames: list[str] | None = None,
    ) -> str | None:
        sanitized = (text or "").strip()
        if not sanitized:
            return None

        if case_label:
            escaped_label = re.escape(case_label)
            sanitized = re.sub(
                rf"(?i)\b{escaped_label}\s*\(\s*{escaped_label}(?:-[A-Z0-9]+)*\s*\)",
                "the patient",
                sanitized,
            )
            sanitized = re.sub(
                rf"(?i)\b{escaped_label}(?:-[A-Z0-9]+)*\b",
                "the patient",
                sanitized,
            )

        for filename in source_filenames or []:
            if filename:
                sanitized = re.sub(
                    re.escape(filename), "the uploaded report", sanitized, flags=re.IGNORECASE
                )

        sanitized = re.sub(r"(?i)\bsource report(?:s)?:\s*the uploaded report\.?", "", sanitized)
        sanitized = re.sub(r"(?i)\(\s*the patient\s*\)", "", sanitized)
        sanitized = re.sub(r"\s+\.", ".", sanitized)
        sanitized = re.sub(r"\.\.", ".", sanitized)
        sanitized = re.sub(r"[ \t]{2,}", " ", sanitized)
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
        return sanitized.strip()

    def _first_sentence(self, text: str | None) -> str | None:
        normalized = " ".join((text or "").split())
        if not normalized:
            return None
        for delimiter in (". ", "; "):
            if delimiter in normalized:
                return normalized.split(delimiter, 1)[0].strip() + (
                    "." if delimiter == ". " else ""
                )
        return normalized

    def _describe_variant(self, variant: VariantSummaryRow) -> str:
        base = " ".join(part for part in [variant.gene, variant.transcript_hgvs] if part)
        if variant.protein_change:
            if base:
                base = f"{base} ({variant.protein_change})"
            else:
                base = variant.protein_change
        if variant.consequence or variant.variation_type:
            tail = variant.consequence or variant.variation_type
            base = f"{base}, {tail}" if base else str(tail)
        return base or "a reported genomic variant"

    def _build_patient_context(
        self,
        patient_id: str,
        reports,
        case_title: str,
        case_label: str | None,
        source_filenames: list[str],
    ) -> str | None:
        context_blocks = self._collect_text_blocks(reports, "patient_context")
        summary_blocks = self._collect_text_blocks(reports, "summary")
        safe_case_title = (
            self._sanitize_report_text(
                case_title,
                case_label=case_label,
                source_filenames=source_filenames,
            )
            or case_title
        )
        lead = (
            f"This case (patient ID {patient_id}) is being reviewed through {safe_case_title}."
            if patient_id
            else (
                f"This case is being reviewed through {safe_case_title}."
                if safe_case_title
                else "This case is being reviewed through the uploaded genomic report."
            )
        )

        detail = (
            context_blocks[0] if context_blocks else (summary_blocks[0] if summary_blocks else "")
        )
        detail = self._sanitize_report_text(
            detail,
            case_label=case_label,
            source_filenames=source_filenames,
        )
        if detail:
            detail = detail[0].upper() + detail[1:]
        parts = [lead]
        if detail:
            parts.append(detail)
        composed = " ".join(part.strip() for part in parts if part and part.strip()).strip()
        return composed or None

    def _build_clinical_findings(
        self,
        reports,
        *,
        case_label: str | None,
        source_filenames: list[str],
    ) -> str | None:
        findings = self._collect_text_blocks(reports, "clinical_findings")
        if findings:
            sanitized = [
                self._sanitize_report_text(
                    item, case_label=case_label, source_filenames=source_filenames
                )
                for item in findings
            ]
            return "\n\n".join(item for item in sanitized if item)
        summaries = self._collect_text_blocks(reports, "summary")
        sanitized = [
            self._sanitize_report_text(
                item, case_label=case_label, source_filenames=source_filenames
            )
            for item in summaries
        ]
        return "\n\n".join(item for item in sanitized if item) if sanitized else None

    def _build_classification_snapshot(self, evidence_map: dict[str, dict]) -> str:
        clinvar = evidence_map.get("clinvar", {})
        classification = clinvar.get("classification", "Unavailable")
        review_status = clinvar.get("review_status", "review status unavailable")
        return (
            f"ClinVar currently lists the reported variant as {classification} ({review_status}). "
            "This is a source snapshot only and should not be read as formal ACMG evidence-code assignment or a final laboratory classification."
        )

    def _build_evidence_snapshot(
        self, evidence_lines: list[str], evidence_statuses: dict[str, str], warnings: list[str]
    ) -> str | None:
        lines = list(evidence_lines)
        degraded_sources = [
            name.upper()
            for name, value in evidence_statuses.items()
            if value in {"fallback", "degraded", "error", "failed"}
        ]
        if degraded_sources:
            lines.append(
                f"Source quality note: {', '.join(sorted(degraded_sources))} evidence was not fully live and should be interpreted with caution."
            )
        if warnings:
            lines.append(f"Workflow note: {'; '.join(warnings[:2])}")
        return "\n".join(line for line in lines if line).strip() or None

    def _build_clinical_integration(
        self,
        patient_context: str | None,
        clinical_findings: str | None,
        variant_descriptions: list[str],
        evidence_map: dict[str, dict],
    ) -> str:
        variant_ref = variant_descriptions[0] if variant_descriptions else "the reported variant"
        context_ref = (
            self._first_sentence(clinical_findings)
            or self._first_sentence(patient_context)
            or "the reported patient context"
        )
        classification = evidence_map.get("clinvar", {}).get(
            "classification", "an unresolved classification state"
        )
        return (
            f"{variant_ref} should be interpreted against {context_ref} "
            f"Current external classification remains {classification}, so the molecular finding can support clinician reasoning in this case but should not be treated as a stand-alone explanation or treatment decision without specialist review."
        )

    def _build_recommendations(self, variant_descriptions: list[str], decision) -> str:
        variant_ref = variant_descriptions[0] if variant_descriptions else "the reported variant"
        return (
            f"Confirm phenotype and referral alignment for {variant_ref}. "
            f"{decision.next_step} "
            "Use this draft as clinician support rather than autonomous sign-off."
        )

    def _collect_variants(self, reports) -> list[VariantSummaryRow]:
        rows: list[VariantSummaryRow] = []
        for report in reports:
            extracted = self._coerce_extracted_case(report)
            for variant in extracted.variants:
                if isinstance(variant, ExtractedVariant):
                    rows.append(
                        VariantSummaryRow(
                            gene=variant.gene,
                            transcript_hgvs=variant.transcript_hgvs,
                            protein_change=variant.protein_change,
                            genomic_hg38=variant.genomic_hg38,
                            variation_type=variant.variation_type,
                            consequence=variant.consequence,
                        )
                    )
                else:
                    payload = getattr(variant, "model_dump", lambda: variant)()
                    if isinstance(payload, dict):
                        rows.append(VariantSummaryRow.model_validate(payload))
                    else:
                        rows.append(VariantSummaryRow())
        return rows

    def _build_report_payload(
        self,
        patient_id: str,
        reports,
        case_title: str,
        case_label: str | None,
        source_filenames: list[str],
        patient_context: str | None,
        clinical_findings: str | None,
        variant_rows: list[VariantSummaryRow],
        variant_descriptions: list[str],
        decision,
        evidence_map: dict[str, dict],
        evidence_statuses: dict[str, str],
        warnings: list[str],
        evidence_lines: list[str],
    ) -> tuple[ReportPayload, list[str]]:
        safe_report_title = (
            self._sanitize_report_text(
                case_title,
                case_label=case_label,
                source_filenames=source_filenames,
            )
            or case_title
        )

        primary_row = variant_rows[0] if variant_rows else None
        variant_decoder_text = decode_variant(
            gene=primary_row.gene if primary_row else None,
            transcript_hgvs=primary_row.transcript_hgvs if primary_row else None,
            protein_change=primary_row.protein_change if primary_row else None,
        )

        pubmed_data = evidence_map.get("pubmed", {})
        pubmed_articles_raw = (
            pubmed_data.get("articles", []) if isinstance(pubmed_data, dict) else []
        )
        pubmed_articles: list[PubMedArticle] = []
        for a in pubmed_articles_raw:
            if isinstance(a, dict):
                try:
                    pubmed_articles.append(PubMedArticle(**a))
                except Exception:
                    pass

        gene_name = (primary_row.gene or "").strip().upper() if primary_row else ""
        therapy_text = GENE_THERAPY_MAP.get(gene_name) or (
            f"No approved gene therapy identified for {gene_name}. "
            "Check ClinicalTrials.gov for active trials."
            if gene_name
            else "No gene identified; therapeutic landscape unavailable."
        )
        trials_tool = self.tool_registry.get("clinical_trials")
        if trials_tool is not None:
            trials_text = trials_tool.get_trials_summary(gene_name)
            therapeutic_landscape = f"{therapy_text}\n\n{trials_text}"
        else:
            therapeutic_landscape = therapy_text

        base_payload = ReportPayload(
            patient_id=patient_id,
            case_label=None,
            report_title=safe_report_title,
            source_filenames=source_filenames,
            patient_context=patient_context,
            clinical_phenotype=clinical_findings,
            ai_clinical_summary=decision.recommendation,
            variant_summary_rows=variant_rows,
            expanded_evidence=self._build_evidence_snapshot(
                evidence_lines, evidence_statuses, warnings
            ),
            acmg_classification=self._build_classification_snapshot(evidence_map),
            clinical_integration=self._build_clinical_integration(
                patient_context, clinical_findings, variant_descriptions, evidence_map
            ),
            expected_symptoms=None,
            recommendations=self._build_recommendations(variant_descriptions, decision),
            limitations=decision.uncertainty,
            variant_decoder=variant_decoder_text,
            therapeutic_landscape=therapeutic_landscape,
            pubmed_articles=pubmed_articles,
        )
        if self.draft_render_service is None:
            return base_payload, []

        draft_payload, draft_warnings = self.draft_render_service.render(
            case_title=case_title,
            patient_context=patient_context,
            clinical_phenotype=clinical_findings,
            variant_summary="; ".join(variant_descriptions),
            decision=decision,
            evidence_statuses=evidence_statuses,
            warnings=[*warnings, *decision.warnings],
            base_payload=base_payload,
        )
        base_payload.ai_clinical_summary = draft_payload.ai_clinical_summary
        base_payload.expanded_evidence = draft_payload.expanded_evidence
        base_payload.clinical_integration = draft_payload.clinical_integration
        base_payload.recommendations = draft_payload.recommendations
        base_payload.limitations = draft_payload.limitations
        base_payload.ai_generated_sections = [
            "ai_clinical_summary",
            "expanded_evidence",
            "clinical_integration",
            "recommendations",
        ]
        return base_payload, draft_warnings
