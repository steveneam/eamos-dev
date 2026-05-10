from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    completed = "completed"
    degraded = "degraded"
    blocked = "blocked"


class ReviewStatus(str, Enum):
    pending_review = "pending_review"
    reviewed = "reviewed"
    approved = "approved"
    dropped = "dropped"


class RunRequest(BaseModel):
    patient_id: str = Field(min_length=1)
    report_ids: list[str] = Field(min_length=1)


class EvidenceSourceSummary(BaseModel):
    source: str
    status: str
    request_identity: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class VariantSummaryRow(BaseModel):
    gene: str | None = None
    transcript_hgvs: str | None = None
    protein_change: str | None = None
    genomic_hg38: str | None = None
    variation_type: str | None = None
    consequence: str | None = None


class PubMedArticle(BaseModel):
    pmid: str
    title: str
    authors: str
    journal: str
    year: str
    url: str
    abstract: str | None = None


class ReportPayload(BaseModel):
    patient_id: str
    case_label: str | None = None
    report_title: str | None = None
    source_filenames: list[str] = Field(default_factory=list)
    patient_context: str | None = None
    clinical_phenotype: str | None = None
    ai_clinical_summary: str | None = None
    variant_summary_rows: list[VariantSummaryRow] = Field(default_factory=list)
    expanded_evidence: str | None = None
    acmg_classification: str | None = None
    clinical_integration: str | None = None
    expected_symptoms: str | None = None
    recommendations: str | None = None
    limitations: str | None = None
    variant_decoder: str | None = None
    therapeutic_landscape: str | None = None
    pubmed_articles: list[PubMedArticle] = Field(default_factory=list)


class RunResponse(BaseModel):
    run_id: str
    patient_id: str
    report_ids: list[str]
    run_status: RunStatus
    review_status: ReviewStatus
    report_payload: ReportPayload
    evidence: list[EvidenceSourceSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    review_note: str | None = None
    reviewed_at: datetime | None = None
    approved_pdf_path: str | None = None
