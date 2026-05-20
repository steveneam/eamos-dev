from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.run import EvidenceSourceSummary, ReportPayload


class LookupRequest(BaseModel):
    gene: str = Field(min_length=1, max_length=64)
    cdna: str = Field(min_length=1, max_length=256)
    transcript: str | None = Field(default=None, max_length=64)
    protein_change: str | None = Field(default=None, max_length=128)
    species: Literal["human", "mouse"] = "human"

    @field_validator("gene", "cdna", "transcript", "protein_change", mode="before")
    @classmethod
    def _strip_text_fields(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class LookupResponse(BaseModel):
    query: str
    species: str
    report_payload: ReportPayload
    evidence: list[EvidenceSourceSummary]
    warnings: list[str]


class PublicationPageRequest(BaseModel):
    gene: str = Field(min_length=1, max_length=64)
    cdna: str = Field(min_length=1, max_length=256)
    transcript: str | None = Field(default=None, max_length=64)
    protein_change: str | None = Field(default=None, max_length=128)
    species: Literal["human", "mouse"] = "human"
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0)

    @field_validator("gene", "cdna", "transcript", "protein_change", mode="before")
    @classmethod
    def _strip_text_fields(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None
