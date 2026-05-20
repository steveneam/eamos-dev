from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PrimerMode = Literal["sanger", "qpcr", "arms"]


class PrimerRequest(BaseModel):
    gene: str
    cdna: str
    mode: PrimerMode = "sanger"
    tm_min: float = 58.0
    tm_max: float = 62.0
    product_size_min: int = 300
    product_size_max: int = 700
    avoid_snps: bool = True


class PrimerPair(BaseModel):
    index: int
    forward: str
    reverse: str
    tm_forward: float
    tm_reverse: float
    gc_forward: float
    gc_reverse: float
    product_size: int
    specificity_hits: int
    notes: str = ""
    recommended: bool = False


class PrimerResponse(BaseModel):
    mode: PrimerMode
    pairs: list[PrimerPair] = Field(default_factory=list)


CasEnzyme = Literal["SpCas9", "SaCas9", "Cas12a"]


class CrisprRequest(BaseModel):
    gene: str
    cdna: str
    cas: CasEnzyme = "SpCas9"
    strand_filter: Literal["both", "plus", "minus"] = "both"
    off_target_tolerance: int = 3


class CrisprGuide(BaseModel):
    index: int
    cut_position: int
    strand: Literal["+", "-"]
    guide: str
    pam: str
    on_target_score: float
    off_target_score: float
    gc_percent: float
    notes: str = ""


class HdrSsodn(BaseModel):
    reference_arm: str
    variant_arm: str
    repair_template: str
    edits_encoded: list[str] = Field(default_factory=list)
    arm_lengths: dict[str, int] = Field(default_factory=dict)
    estimated_hdr_efficiency: float


class CrisprResponse(BaseModel):
    cas: CasEnzyme
    guides: list[CrisprGuide] = Field(default_factory=list)
    ssodn: HdrSsodn | None = None


class AlignRequest(BaseModel):
    gene: str
    cdna: str
    user_sequence: str | None = None
    ab1_blob_base64: str | None = None


class TraceChannel(BaseModel):
    base: Literal["A", "T", "C", "G"]
    values: list[float]


class AlignResponse(BaseModel):
    reference: str
    sanger_read: str
    match_line: str
    mismatch_positions: list[int] = Field(default_factory=list)
    target_position: int
    trace_channels: list[TraceChannel] = Field(default_factory=list)
    base_calls: list[str] = Field(default_factory=list)
    q_scores: list[int] = Field(default_factory=list)
