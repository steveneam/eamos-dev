from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PrimerMode = Literal["sanger", "qpcr", "arms"]
WORKBENCH_GENE_MAX_LENGTH = 64
WORKBENCH_CDNA_MAX_LENGTH = 256
WORKBENCH_USER_SEQUENCE_MAX_LENGTH = 10_000
WORKBENCH_AB1_BLOB_MAX_LENGTH = 3_000_000


def _strip_text(value):
    if value is None or not isinstance(value, str):
        return value
    stripped = value.strip()
    return stripped or None


class WorkbenchQuery(BaseModel):
    gene: str = Field(min_length=1, max_length=WORKBENCH_GENE_MAX_LENGTH)
    cdna: str = Field(min_length=1, max_length=WORKBENCH_CDNA_MAX_LENGTH)

    @field_validator("gene", "cdna", mode="before")
    @classmethod
    def _strip_query_text(cls, value):
        return _strip_text(value)


class PrimerRequest(WorkbenchQuery):
    mode: PrimerMode = "sanger"
    tm_min: float = Field(default=58.0, ge=40.0, le=90.0)
    tm_max: float = Field(default=62.0, ge=40.0, le=90.0)
    product_size_min: int = Field(default=300, ge=50, le=2_000)
    product_size_max: int = Field(default=700, ge=50, le=2_000)
    avoid_snps: bool = True

    @model_validator(mode="after")
    def _validate_ranges(self):
        if self.tm_min > self.tm_max:
            raise ValueError("tm_min must be less than or equal to tm_max.")
        if self.product_size_min > self.product_size_max:
            raise ValueError("product_size_min must be less than or equal to product_size_max.")
        return self


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


class CrisprRequest(WorkbenchQuery):
    cas: CasEnzyme = "SpCas9"
    strand_filter: Literal["both", "plus", "minus"] = "both"
    off_target_tolerance: int = Field(default=3, ge=0, le=6)


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


class AlignRequest(WorkbenchQuery):
    user_sequence: str | None = Field(default=None, max_length=WORKBENCH_USER_SEQUENCE_MAX_LENGTH)
    ab1_blob_base64: str | None = Field(default=None, max_length=WORKBENCH_AB1_BLOB_MAX_LENGTH)

    @field_validator("user_sequence", "ab1_blob_base64", mode="before")
    @classmethod
    def _strip_optional_text(cls, value):
        return _strip_text(value)


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
