from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas.run import EvidenceSourceSummary, ReportPayload


class LookupRequest(BaseModel):
    gene: str
    cdna: str
    transcript: str | None = None
    protein_change: str | None = None
    species: Literal["human", "mouse"] = "human"


class LookupResponse(BaseModel):
    query: str
    species: str
    report_payload: ReportPayload
    evidence: list[EvidenceSourceSummary]
    warnings: list[str]
