from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.schemas.report import (
    ExtractedCase,
    ExtractionIssue,
    ExtractionStatus,
    ReportKind,
    ReportUploadResponse,
    UploadedReport,
)


class IntakeService:
    def __init__(
        self,
        settings,
        reports_repo,
        report_pdf_tool,
        extraction_chain,
        search_index_service=None,
    ) -> None:
        self.settings = settings
        self.reports_repo = reports_repo
        self.report_pdf_tool = report_pdf_tool
        self.extraction_chain = extraction_chain
        self.search_index_service = search_index_service

    async def ingest_upload(
        self,
        upload: UploadFile,
        report_kind: ReportKind = "test",
    ) -> ReportUploadResponse:
        filename = upload.filename or "report.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only PDF uploads are supported.",
            )

        content = await upload.read()
        size_limit = self.settings.max_upload_mb * 1024 * 1024
        if len(content) > size_limit:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Uploaded file exceeds configured size limit.",
            )

        report_id = f"report_{uuid4().hex[:12]}"
        file_path = self.settings.upload_dir / f"{report_id}.pdf"
        file_path.write_bytes(content)

        pdf_result = self.report_pdf_tool.extract(file_path)
        extracted_case, extraction_status, warnings = self._build_extracted_case(
            filename=filename,
            report_kind=report_kind,
            report_text=pdf_result.get("text", ""),
            pdf_warnings=list(pdf_result.get("warnings", [])),
        )

        report = UploadedReport(
            report_id=report_id,
            filename=filename,
            content_type=upload.content_type or "application/pdf",
            size_bytes=len(content),
            created_at=datetime.now(timezone.utc),
            report_kind=report_kind,
            source_pdf_path=str(file_path),
            extraction_status=extraction_status,
            extracted_case=extracted_case,
            raw_extracted_text=pdf_result.get("text") or None,
            extraction_warnings=warnings,
        )
        self.reports_repo.save(report)
        if self.search_index_service is not None:
            self.search_index_service.index_report(report)
        return ReportUploadResponse(report=report)

    def _build_extracted_case(
        self,
        filename: str,
        report_kind: ReportKind,
        report_text: str,
        pdf_warnings: list[str],
    ) -> tuple[ExtractedCase, ExtractionStatus, list[str]]:
        warnings = list(pdf_warnings)
        if self.extraction_chain is None:
            if report_kind == "patient":
                issue_message = (
                    "Patient report extraction unavailable without configured parser or AI model."
                )
                extracted_case = ExtractedCase(
                    case_label="patient-upload",
                    report_title=filename,
                    summary=issue_message,
                    issues=[
                        ExtractionIssue(
                            code="patient_extraction_unavailable",
                            message=issue_message,
                            severity="error",
                        )
                    ],
                )
                warnings.append("patient_extraction_unavailable")
                return extracted_case, "blocked", warnings

            extracted_case = ExtractedCase.model_validate_json(
                (self.settings.fixtures_root / "reports" / "ravi_extracted.json").read_text()
            )
            return extracted_case, ("degraded" if warnings else "completed"), warnings

        extracted_payload = self.extraction_chain.invoke(
            {
                "filename": filename,
                "report_text": report_text,
            }
        )
        extracted_case = ExtractedCase.model_validate(extracted_payload)
        return extracted_case, ("degraded" if warnings else "completed"), warnings
