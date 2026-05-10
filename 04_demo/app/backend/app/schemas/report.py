from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ReportKind = Literal["test", "patient"]
ExtractionStatus = Literal["completed", "degraded", "blocked"]


class ExtractionIssue(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"


class ExtractedVariant(BaseModel):
    gene: str
    transcript_hgvs: str
    protein_change: str
    genomic_hg38: str
    variation_type: str
    consequence: str


class ExtractedCase(BaseModel):
    case_label: str
    report_title: str
    patient_context: str | None = None
    clinical_findings: str | None = None
    summary: str
    genome_build: str = "GRCh38"
    variants: list[ExtractedVariant] = Field(default_factory=list)
    issues: list[ExtractionIssue] = Field(default_factory=list)


class UploadedReport(BaseModel):
    report_id: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    report_kind: ReportKind = "test"
    source_pdf_path: str
    extraction_status: ExtractionStatus
    extracted_case: ExtractedCase
    raw_extracted_text: str | None = None
    extraction_warnings: list[str] = Field(default_factory=list)


class ReportUploadResponse(BaseModel):
    report: UploadedReport
