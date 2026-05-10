from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DraftPayload(BaseModel):
    ai_clinical_summary: str
    expanded_evidence: str
    clinical_integration: str
    recommendations: str
    limitations: str


class ClinicianReviewPayload(BaseModel):
    reviewer_name: str | None = None
    review_note: str


class RunDropPayload(BaseModel):
    review_note: str | None = None


class ReportDraftUpdatePayload(BaseModel):
    patient_context: str | None = None
    clinical_phenotype: str | None = None
    ai_clinical_summary: str | None = None
    expanded_evidence: str | None = None
    acmg_classification: str | None = None
    clinical_integration: str | None = None
    expected_symptoms: str | None = None
    recommendations: str | None = None
    therapeutic_landscape: str | None = None
    limitations: str | None = None
    review_note: str | None = None


class ReviewResult(BaseModel):
    run_id: str
    review_status: Literal["reviewed"] = "reviewed"
    review_note: str
    reviewed_at: datetime


class ApproveResult(BaseModel):
    run_id: str
    review_status: Literal["approved"] = "approved"
    review_note: str | None = None
    reviewed_at: datetime | None = None
    download_path: str


class DropResult(BaseModel):
    run_id: str
    review_status: Literal["dropped"] = "dropped"
    review_note: str | None = None
    reviewed_at: datetime | None = None
