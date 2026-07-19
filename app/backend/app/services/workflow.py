from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import UTC, datetime
import re
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.logging import get_logger
from app.core.ownership import OwnerIdentity
from app.repos.product_workflow_repo import (
    ProductWorkflowRepository,
    ProductWorkflowRunRecord,
)
from app.rules.base import DecisionInput
from app.services.lookup_service import GENE_THERAPY_MAP
from app.services.variant_decoder import decode_variant
from app.tools.base import ToolResult
from app.schemas.report import ExtractedCase, ExtractedVariant
from app.schemas.workflow import (
    ProcessingDisclosureV1,
    WorkflowContextV1,
    WorkflowRunV1,
)
from app.schemas.run import (
    EvidenceSourceSummary,
    PubMedArticle,
    ReportPayload,
    RunRequest,
    RunResponse,
    RunStatus,
    VariantSummaryRow,
)

logger = get_logger(__name__)


class ProductWorkflowStateError(RuntimeError):
    pass


class ProductWorkflowService:
    """Durable, owner-scoped lifecycle for product workflow surfaces."""

    def __init__(self, repo: ProductWorkflowRepository) -> None:
        self.repo = repo
        self._expiry_sweep_lock = Lock()
        self._last_expiry_sweep = 0.0

    def create_run(
        self,
        *,
        kind: str,
        user_id: str,
        owner_provider: str,
        status: str = "draft",
        done: int = 0,
        total: int = 0,
        warnings: list[str] | None = None,
        source_disclosures: list[dict[str, Any]] | None = None,
        processing_disclosure: ProcessingDisclosureV1 | dict[str, Any] | None = None,
        context: WorkflowContextV1 | dict[str, Any] | None = None,
        result_payload: dict[str, Any] | None = None,
        items: list[dict[str, Any]] | None = None,
        run_id: str | None = None,
        n_input: int | None = None,
        n_to_lookup: int | None = None,
        n_after_filters: int | None = None,
        est_seconds: float | None = None,
    ) -> WorkflowRunV1:
        self._purge_expired()
        if kind not in {"batch", "paper", "workbench"}:
            raise ValueError("Unsupported workflow kind.")
        now = datetime.now(UTC)
        resolved_run_id = run_id or f"{kind}-{uuid4().hex[:16]}"
        resolved_context = self._context(
            kind=kind,
            run_id=resolved_run_id,
            now=now,
            context=context,
        )
        processing_model = (
            processing_disclosure
            if isinstance(processing_disclosure, ProcessingDisclosureV1)
            else (
                ProcessingDisclosureV1.model_validate(processing_disclosure)
                if processing_disclosure is not None
                else None
            )
        )
        processing_payload = _model_json(processing_model)
        expiry_candidates = [
            value
            for value in (
                resolved_context.expires_at,
                processing_model.expires_at if processing_model is not None else None,
            )
            if value is not None
        ]
        record = ProductWorkflowRunRecord(
            run_id=resolved_run_id,
            user_id=user_id,
            owner_provider=owner_provider,
            kind=kind,
            status=status,
            owner_scope="account",
            context=resolved_context.model_dump(mode="json"),
            done=done,
            total=total,
            warnings=list(dict.fromkeys(warnings or [])),
            source_disclosures=list(source_disclosures or []),
            processing_disclosure=processing_payload,
            artifacts=[],
            result_payload=result_payload,
            created_at=now,
            updated_at=now,
            expires_at=min(expiry_candidates) if expiry_candidates else None,
            n_input=n_input,
            n_to_lookup=n_to_lookup,
            n_after_filters=n_after_filters,
            est_seconds=est_seconds,
        )
        contract = self._as_contract(record)
        self.repo.create_run(record)
        try:
            if items is not None:
                self.repo.replace_items(
                    run_id=resolved_run_id,
                    user_id=user_id,
                    owner_provider=owner_provider,
                    items=items,
                )
        except Exception:
            self.repo.delete_run(
                run_id=resolved_run_id,
                user_id=user_id,
                owner_provider=owner_provider,
            )
            raise
        return contract

    def get_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
    ) -> WorkflowRunV1 | None:
        record = self.get_record(
            run_id=run_id,
            user_id=user_id,
            owner_provider=owner_provider,
        )
        return self._as_contract(record) if record is not None else None

    def get_record(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
    ) -> ProductWorkflowRunRecord | None:
        self._purge_expired()
        return self.repo.get_run(
            run_id=run_id,
            user_id=user_id,
            owner_provider=owner_provider,
        )

    def list_runs(
        self,
        *,
        user_id: str,
        owner_provider: str,
        kind: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[WorkflowRunV1], str | None, int]:
        self._purge_expired()
        records, next_cursor, total = self.repo.list_runs(
            user_id=user_id,
            owner_provider=owner_provider,
            kind=kind,
            limit=limit,
            cursor=cursor,
        )
        return [self._as_contract(record) for record in records], next_cursor, total

    def update_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
        status: str | None = None,
        done: int | None = None,
        total: int | None = None,
        warnings: list[str] | None = None,
        source_disclosures: list[dict[str, Any]] | None = None,
        processing_disclosure: ProcessingDisclosureV1 | dict[str, Any] | None = None,
        result_payload: dict[str, Any] | None = None,
        items: list[dict[str, Any]] | None = None,
    ) -> WorkflowRunV1 | None:
        changes: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        for key, value in (
            ("status", status),
            ("done", done),
            ("total", total),
            ("warnings", warnings),
            ("source_disclosures", source_disclosures),
            ("result_payload", result_payload),
        ):
            if value is not None:
                changes[key] = value
        if processing_disclosure is not None:
            changes["processing_disclosure"] = _model_json(processing_disclosure)
        record = self.repo.update_run(
            run_id=run_id,
            user_id=user_id,
            owner_provider=owner_provider,
            changes=changes,
        )
        if record is None:
            return None
        if items is not None:
            self.repo.replace_items(
                run_id=run_id,
                user_id=user_id,
                owner_provider=owner_provider,
                items=items,
            )
        return self._as_contract(record)

    def update_batch_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
        status: str,
        done: int,
        total: int,
        warnings: list[str],
        items: list[dict[str, Any]],
    ) -> WorkflowRunV1 | None:
        return self.update_run(
            run_id=run_id,
            user_id=user_id,
            owner_provider=owner_provider,
            status=status,
            done=done,
            total=total,
            warnings=warnings,
            items=items,
        )

    def cancel_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
    ) -> WorkflowRunV1 | None:
        record = self.get_record(
            run_id=run_id,
            user_id=user_id,
            owner_provider=owner_provider,
        )
        if record is None:
            return None
        if record.status in {"completed", "failed", "cancelled", "expired"}:
            if record.status == "cancelled":
                return self._as_contract(record)
            raise ProductWorkflowStateError(
                f"A {record.status} workflow run cannot be cancelled."
            )
        updated = self.repo.update_run(
            run_id=run_id,
            user_id=user_id,
            owner_provider=owner_provider,
            changes={"status": "cancelled", "updated_at": datetime.now(UTC)},
        )
        return self._as_contract(updated) if updated is not None else None

    def delete_run(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
    ) -> bool:
        return self.repo.delete_run(
            run_id=run_id,
            user_id=user_id,
            owner_provider=owner_provider,
        )

    def page_items(
        self,
        *,
        run_id: str,
        user_id: str,
        owner_provider: str,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[dict[str, Any]], str | None, int] | None:
        if self.get_record(
            run_id=run_id,
            user_id=user_id,
            owner_provider=owner_provider,
        ) is None:
            return None
        return self.repo.page_items(
            run_id=run_id,
            user_id=user_id,
            owner_provider=owner_provider,
            limit=limit,
            cursor=cursor,
        )

    @staticmethod
    def _as_contract(record: ProductWorkflowRunRecord) -> WorkflowRunV1:
        return WorkflowRunV1.model_validate(
            {
                "schema_version": "workflow_run.v1",
                "run_id": record.run_id,
                "kind": record.kind,
                "status": record.status,
                "owner_scope": record.owner_scope,
                "context": record.context,
                "done": record.done,
                "total": record.total,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
                "expires_at": record.expires_at,
                "warnings": record.warnings,
                "source_disclosures": record.source_disclosures,
                "processing_disclosure": record.processing_disclosure,
                "artifacts": record.artifacts,
            }
        )

    @staticmethod
    def _context(
        *,
        kind: str,
        run_id: str,
        now: datetime,
        context: WorkflowContextV1 | dict[str, Any] | None,
    ) -> WorkflowContextV1:
        if context is not None:
            validated = (
                context
                if isinstance(context, WorkflowContextV1)
                else WorkflowContextV1.model_validate(context)
            )
            updates: dict[str, Any] = {}
            if validated.context_id is None:
                updates["context_id"] = run_id
            if kind == "workbench" and validated.workspace_id is None:
                updates["workspace_id"] = run_id
            return validated.model_copy(update=updates)
        if kind == "batch":
            return_to = f"/compare?run_id={run_id}&view=cohort"
            origin_surface = "batch"
        elif kind == "paper":
            return_to = f"/paper?run_id={run_id}"
            origin_surface = "paper"
        else:
            return_to = f"/workbench?context_id={run_id}"
            origin_surface = "workbench"
        return WorkflowContextV1(
            schema_version="workflow_context.v1",
            context_id=run_id,
            variant=None,
            origin_surface=origin_surface,
            return_to=return_to,
            batch_run_id=run_id if kind == "batch" else None,
            paper_run_id=run_id if kind == "paper" else None,
            workspace_id=run_id if kind == "workbench" else None,
            active_tool=None,
            selection=None,
            created_at=now,
            expires_at=None,
        )

    def _purge_expired(self) -> None:
        now_monotonic = time.monotonic()
        if now_monotonic - self._last_expiry_sweep < 60.0:
            return
        with self._expiry_sweep_lock:
            now_monotonic = time.monotonic()
            if now_monotonic - self._last_expiry_sweep < 60.0:
                return
            self.repo.delete_expired(now=datetime.now(UTC))
            self._last_expiry_sweep = now_monotonic


def _model_json(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


class WorkflowService:
    def __init__(
        self,
        reports_repo,
        run_repo,
        tool_registry,
        rule_engine,
        draft_render_service=None,
        settings=None,
        search_index_service=None,
    ) -> None:
        self.settings = settings
        self.reports_repo = reports_repo
        self.run_repo = run_repo
        self.tool_registry = tool_registry
        self.rule_engine = rule_engine
        self.draft_render_service = draft_render_service
        self.search_index_service = search_index_service
        self._executor = ThreadPoolExecutor(
            max_workers=_positive_int(
                getattr(settings, "workflow_worker_max_workers", 5),
                default=5,
            ),
            thread_name_prefix="eamos-workflow",
        )

    def create_run(
        self,
        payload: RunRequest,
        *,
        owner: OwnerIdentity | None = None,
    ) -> RunResponse:
        if not payload.report_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one report_id is required.",
            )

        reports = []
        missing = []
        for report_id in payload.report_ids:
            report = (
                self.reports_repo.get_for_owner(report_id, owner=owner)
                if owner is not None
                else self.reports_repo.get(report_id)
            )
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

        evidence, evidence_map, evidence_statuses, warnings = self._collect_evidence(
            primary_variant
        )

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
            owner=owner,
        )

        response = RunResponse(
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
        self._index_run(
            response,
            reports,
            owner_user_id=owner.user_id if owner is not None else None,
        )
        return response

    def _index_run(self, run: RunResponse, reports, *, owner_user_id: str | None) -> None:
        if self.search_index_service is None:
            return
        try:
            self.search_index_service.index_run(run, reports=reports, owner_user_id=owner_user_id)
        except Exception:
            logger.exception("Search indexing failed for run %s", run.run_id)

    def _collect_evidence(self, primary_variant) -> tuple[
        list[EvidenceSourceSummary],
        dict[str, dict],
        dict[str, str],
        list[str],
    ]:
        tool_names = ("vep", "spliceai", "clinvar", "gnomad", "pubmed")
        timeout_seconds = _positive_float(
            getattr(self.settings, "workflow_tool_timeout_seconds", 10.0),
            default=10.0,
        )
        futures = {
            name: self._executor.submit(
                self.tool_registry[name].get_evidence,
                variant=primary_variant,
            )
            for name in tool_names
        }
        deadline = time.monotonic() + timeout_seconds
        results: dict[str, ToolResult] = {}
        for name, future in futures.items():
            remaining = max(0.001, deadline - time.monotonic())
            try:
                result = future.result(timeout=remaining)
            except FutureTimeoutError:
                future.cancel()
                result = _degraded_tool_result(
                    name,
                    warning=f"{name}_evidence_timeout:{timeout_seconds:g}s",
                )
            except Exception as exc:
                result = _degraded_tool_result(
                    name,
                    warning=f"{name}_evidence_failed:{type(exc).__name__}",
                )
            results[name] = result

        evidence: list[EvidenceSourceSummary] = []
        evidence_map: dict[str, dict] = {}
        evidence_statuses: dict[str, str] = {}
        warnings: list[str] = []
        for name in tool_names:
            result = results[name]
            summary = EvidenceSourceSummary(
                source=result.source,
                status=result.status,
                request_identity=result.request_identity,
                summary=result.summary,
                warnings=result.warnings,
                source_url=result.source_url,
                fetched_at=result.fetched_at,
                source_version=result.source_version,
                cache_status=result.cache_status,
            )
            evidence.append(summary)
            evidence_map[name] = result.summary
            evidence_statuses[name] = result.status
            warnings.extend(result.warnings)
        return evidence, evidence_map, evidence_statuses, warnings

    def get_run(self, run_id: str, *, owner: OwnerIdentity) -> RunResponse:
        run = self.run_repo.get_run_for_owner(run_id, owner=owner)
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

        draft_payload, draft_warnings = self._render_draft_with_deadline(
            case_title=case_title,
            patient_context=patient_context,
            clinical_phenotype=clinical_findings,
            variant_summary="; ".join(variant_descriptions),
            decision=decision,
            evidence_statuses=evidence_statuses,
            warnings=[*warnings, *decision.warnings],
            base_payload=base_payload,
        )
        if draft_payload is None:
            return base_payload, draft_warnings
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

    def _render_draft_with_deadline(self, **kwargs):
        timeout_seconds = _positive_float(
            getattr(self.settings, "workflow_draft_timeout_seconds", 10.0),
            default=10.0,
        )
        future = self._executor.submit(self.draft_render_service.render, **kwargs)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            future.cancel()
            return None, [f"llm_draft_fallback:TimeoutError:{timeout_seconds:g}s"]


def _degraded_tool_result(source: str, *, warning: str) -> ToolResult:
    return ToolResult(
        source=source,
        status="degraded",
        request_identity={},
        summary={},
        warnings=[warning],
    )


def _positive_int(value, *, default: int) -> int:
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return default
    return coerced if coerced > 0 else default


def _positive_float(value, *, default: float) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return default
    return coerced if coerced > 0 else default
