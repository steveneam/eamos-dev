from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

EvidenceCode = Literal["PS3", "BS3", "PS3_Supporting", "BS3_Supporting", "Other"]
CollectionMethod = Literal["in vivo", "in vitro"]
FunctionalEffect = Literal[
    "functionally abnormal",
    "function uncertain",
    "functionally normal",
]
PubMedValidationStatus = Literal["validated", "unchecked", "not_found"]
ClinvarPayloadStatus = Literal["ready_for_clinvar_dry_run", "draft_needs_curator_fields"]
EvidenceLedgerStatus = Literal["recorded"]

_HGVS_ACCESSION_RE = re.compile(
    r"^(?:"
    r"(?:N[CMGRT]_|LRG_)[A-Za-z0-9_.]+"
    r"(?:\([A-Za-z0-9_.-]+\))?"
    r":"
    r"(?:[cgmnpr]\.|[A-Za-z0-9_.-]+:)"
    r".+"
    r"|"
    r"[A-Z][A-Z0-9-]{1,15}:c\..+"
    r")$",
    flags=re.IGNORECASE,
)


class EvidenceSubmissionRequest(BaseModel):
    variant_hgvs: str = Field(min_length=4, max_length=255)
    submitted_pmid: str = Field(min_length=6, max_length=16)
    curator_notes: str | None = Field(default=None, max_length=4000)
    condition_name: str | None = Field(default=None, max_length=255)
    assay_type: str | None = Field(default=None, max_length=128)
    collection_method: CollectionMethod = "in vitro"
    functional_effect: FunctionalEffect = "function uncertain"
    functional_consequence: list[str] = Field(default_factory=list, max_length=8)
    method: str | None = Field(default=None, max_length=1000)
    result: str | None = Field(default=None, max_length=512)
    evidence_codes: list[EvidenceCode] = Field(default_factory=list, max_length=8)

    @field_validator(
        "variant_hgvs",
        "submitted_pmid",
        "curator_notes",
        "condition_name",
        "assay_type",
        "method",
        "result",
        mode="before",
    )
    @classmethod
    def _strip_optional_text(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("variant_hgvs")
    @classmethod
    def _validate_hgvs(cls, value: str) -> str:
        if not _HGVS_ACCESSION_RE.match(value):
            raise ValueError(
                "variant_hgvs must be accession-qualified HGVS, e.g. "
                "NM_000492.4:c.199C>T or NC_000007.14:g.117559590G>A."
            )
        return value

    @field_validator("submitted_pmid")
    @classmethod
    def _normalize_pmid(cls, value: str) -> str:
        normalized = value.removeprefix("PMID:").removeprefix("pmid:").strip()
        if not re.fullmatch(r"\d{6,9}", normalized):
            raise ValueError("submitted_pmid must be a 6-9 digit PubMed identifier.")
        return normalized

    @field_validator("functional_consequence", mode="before")
    @classmethod
    def _strip_functional_consequence(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]


class PubMedValidation(BaseModel):
    pmid: str
    status: PubMedValidationStatus
    title: str | None = None
    journal: str | None = None
    publication_date: str | None = None
    source_url: str
    warnings: list[str] = Field(default_factory=list)


class ClinvarSubmissionDraft(BaseModel):
    tracking_id: str
    payload_schema_version: str = "clinvar_submission_api_2026_02_no_classification"
    payload_status: ClinvarPayloadStatus
    missing_required_fields: list[str] = Field(default_factory=list)
    payload: dict[str, Any]


class EvidenceSubmissionResponse(BaseModel):
    submission_id: str
    user_id: str
    variant_hgvs: str
    submitted_pmid: str
    curator_notes: str | None = None
    pubmed: PubMedValidation
    clinvar_tracking_id: str
    clinvar_payload: ClinvarSubmissionDraft
    ledger_status: EvidenceLedgerStatus = "recorded"
    created_at: datetime
    warnings: list[str] = Field(default_factory=list)
