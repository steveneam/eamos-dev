from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SearchDocType = Literal["report", "run"]
SearchMatchType = Literal[
    "exact_run_id",
    "exact_report_id",
    "exact_patient_id",
    "exact_variant",
    "full_text",
]


class SearchHit(BaseModel):
    doc_type: SearchDocType
    run_id: str | None = None
    report_id: str | None = None
    patient_id: str | None = None
    title: str
    snippet: str | None = None
    match_type: SearchMatchType
    score: float = 0.0
    run_status: str | None = None
    review_status: str | None = None
    extraction_status: str | None = None
    updated_at: datetime | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchHit] = Field(default_factory=list)


class SearchRequestFilters(BaseModel):
    doc_type: SearchDocType | None = None
    run_status: str | None = None
    review_status: str | None = None


class SearchCitation(BaseModel):
    run_id: str | None = None
    report_id: str | None = None
    title: str | None = None


class SearchAnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    doc_type: SearchDocType | None = None
    run_status: str | None = None
    review_status: str | None = None


class SearchAnswerDraft(BaseModel):
    answer: str
    grounded: bool = True
    citations: list[SearchCitation] = Field(default_factory=list)


class SearchAnswerResponse(BaseModel):
    query: str
    answer: str
    grounded: bool = True
    citations: list[SearchCitation] = Field(default_factory=list)
    results: list[SearchHit] = Field(default_factory=list)


class SearchVariantWrite(BaseModel):
    gene_symbol: str | None = None
    gene_symbol_norm: str | None = None
    transcript_hgvs: str | None = None
    transcript_hgvs_norm: str | None = None
    protein_change: str | None = None
    protein_change_norm: str | None = None
    consequence: str | None = None


class SearchDocumentWrite(BaseModel):
    source_key: str
    doc_type: SearchDocType
    run_id: str | None = None
    report_id: str | None = None
    patient_id: str | None = None
    filename: str | None = None
    report_kind: str | None = None
    extraction_status: str | None = None
    run_status: str | None = None
    review_status: str | None = None
    case_label: str | None = None
    report_title: str | None = None
    summary_text: str = ""
    evidence_text: str = ""
    review_note: str = ""
    raw_extracted_text: str = ""
    identifier_text: str = ""
    search_text: str = ""
    variants: list[SearchVariantWrite] = Field(default_factory=list)
