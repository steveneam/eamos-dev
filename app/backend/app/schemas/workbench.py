from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PrimerMode = Literal["sanger", "qpcr", "arms"]
SecondaryStructureRisk = Literal["low", "moderate", "high", "not_assessed"]
SsodnProtocol = Literal["lab_genomic", "guide_pam_block"]
SsodnOrientation = Literal["sense", "antisense"]
SsodnStrandRequest = Literal["auto", "+", "-"]
WORKBENCH_GENE_MAX_LENGTH = 64
WORKBENCH_CDNA_MAX_LENGTH = 256
WORKBENCH_USER_SEQUENCE_MAX_LENGTH = 10_000
WORKBENCH_AB1_BLOB_MAX_LENGTH = 3_000_000
WORKBENCH_SCREENING_TEMPLATE_MAX_LENGTH = 20_000


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
    secondary_structure_risk: SecondaryStructureRisk = "not_assessed"
    secondary_structure_notes: str = ""
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


class CrisprSsodnDesign(BaseModel):
    reference_arm: str
    variant_arm: str
    repair_template: str
    edits_encoded: list[str] = Field(default_factory=list)
    arm_lengths: dict[str, int] = Field(default_factory=dict)
    estimated_hdr_efficiency: float
    oligo_sequence: str
    oligo_length: int
    oligo_name: str
    variant_offset: int
    intron_mask: list[bool]
    strand: Literal["+", "-"]
    orientation: SsodnOrientation
    protocol: SsodnProtocol
    template_source: str
    genome_build: str


class CrisprResponse(BaseModel):
    cas: CasEnzyme
    guides: list[CrisprGuide] = Field(default_factory=list)
    ssodn: HdrSsodn | None = None


class CrisprSsodnRequest(WorkbenchQuery):
    transcript: str | None = Field(default=None, max_length=128)
    protein_change: str | None = Field(default=None, max_length=128)
    species: Literal["human", "mouse"] = "human"
    genome_build: str = Field(default="GRCh38", min_length=1, max_length=32)
    oligo_length: int = Field(default=120, ge=60, le=200)
    variant_offset: int | None = Field(default=None, ge=0)
    strand: SsodnStrandRequest = "auto"
    orientation: SsodnOrientation = "sense"
    protocol: SsodnProtocol = "lab_genomic"
    guide_sequence: str | None = Field(default=None, max_length=20)
    pam_sequence: str | None = Field(default=None, max_length=8)
    pam_blocking_enabled: bool = False

    @field_validator(
        "transcript",
        "protein_change",
        "genome_build",
        "guide_sequence",
        "pam_sequence",
        mode="before",
    )
    @classmethod
    def _strip_ssodn_text(cls, value):
        return _strip_text(value)

    @field_validator("guide_sequence")
    @classmethod
    def _normalize_guide(cls, value: str | None) -> str | None:
        if value is None:
            return None
        guide = re.sub(r"\s+", "", value).upper()
        if any(base not in {"A", "C", "G", "T"} for base in guide):
            raise ValueError("guide_sequence must contain only A, C, G, and T bases.")
        return guide

    @field_validator("pam_sequence")
    @classmethod
    def _normalize_pam(cls, value: str | None) -> str | None:
        if value is None:
            return None
        pam = re.sub(r"\s+", "", value).upper()
        if any(base not in {"A", "C", "G", "T", "N"} for base in pam):
            raise ValueError("pam_sequence must contain only A, C, G, T, and N bases.")
        return pam

    @model_validator(mode="after")
    def _validate_variant_offset(self):
        if self.variant_offset is not None and self.variant_offset >= self.oligo_length:
            raise ValueError("variant_offset must be less than oligo_length.")
        if self.protocol == "guide_pam_block":
            self.pam_blocking_enabled = True
        return self


class CrisprSsodnResponse(BaseModel):
    genome_build: str
    ssodn: CrisprSsodnDesign
    warnings: list[str] = Field(default_factory=list)


class CrisprOffTargetLocus(BaseModel):
    chromosome: str = Field(min_length=1, max_length=32)
    position: int = Field(ge=1)
    strand: Literal["+", "-"] = "+"

    @field_validator("chromosome", mode="before")
    @classmethod
    def _strip_chromosome(cls, value):
        return _strip_text(value)


class CrisprOffTargetRequest(BaseModel):
    guide: str = Field(min_length=20, max_length=20)
    pam: str = Field(default="NGG", min_length=2, max_length=8)
    enzyme: CasEnzyme = "SpCas9"
    genome_build: str = Field(default="GRCh38", min_length=1, max_length=32)
    max_mismatches: int = Field(default=3, ge=0, le=6)
    on_target_locus: CrisprOffTargetLocus | None = None

    @field_validator("guide", "pam", "genome_build", mode="before")
    @classmethod
    def _strip_request_text(cls, value):
        return _strip_text(value)

    @field_validator("guide")
    @classmethod
    def _validate_guide(cls, value: str) -> str:
        guide = value.upper()
        if any(base not in {"A", "C", "G", "T"} for base in guide):
            raise ValueError("guide must contain only A, C, G, and T bases.")
        return guide

    @field_validator("pam")
    @classmethod
    def _validate_pam(cls, value: str) -> str:
        pam = value.upper()
        if any(base not in {"A", "C", "G", "T", "N"} for base in pam):
            raise ValueError("pam must contain only A, C, G, T, and N bases.")
        return pam


class CrisprOffTargetSite(BaseModel):
    sequence: str
    pam: str
    score: float = Field(ge=0.0, le=1.0)
    mismatches: int = Field(ge=0)
    gene: str | None = None
    gene_id: str | None = None
    biotype: str | None = None
    chromosome: str
    strand: Literal["+", "-"]
    position: int = Field(ge=1)
    on_target: bool


class CrisprOffTargetResponse(BaseModel):
    genome_build: str
    sites: list[CrisprOffTargetSite] = Field(default_factory=list)


class CrisprScreeningRegion(BaseModel):
    chromosome: str = Field(min_length=1, max_length=32)
    start: int = Field(ge=1)
    end: int = Field(ge=1)
    genome_build: str = Field(default="GRCh38", min_length=1, max_length=32)
    strand: Literal["+", "-"] = "+"

    @field_validator("chromosome", "genome_build", mode="before")
    @classmethod
    def _strip_region_text(cls, value):
        return _strip_text(value)

    @model_validator(mode="after")
    def _validate_span(self):
        if self.start > self.end:
            raise ValueError("region start must be less than or equal to end.")
        return self


class CrisprScreeningPrimerTarget(BaseModel):
    site_index: int = Field(ge=1)
    point: str | None = Field(default=None, max_length=64)
    chromosome: str | None = Field(default=None, max_length=32)
    position: int | None = Field(default=None, ge=1)
    strand: Literal["+", "-"] = "+"
    region: CrisprScreeningRegion | None = None
    template_sequence: str | None = Field(
        default=None,
        max_length=WORKBENCH_SCREENING_TEMPLATE_MAX_LENGTH,
    )
    target_offset: int | None = Field(default=None, ge=0)
    sequence: str | None = Field(default=None, min_length=20, max_length=20)
    pam: str | None = Field(default=None, max_length=8)

    @field_validator(
        "point",
        "chromosome",
        "template_sequence",
        "sequence",
        "pam",
        mode="before",
    )
    @classmethod
    def _strip_target_text(cls, value):
        return _strip_text(value)

    @field_validator("template_sequence", "sequence")
    @classmethod
    def _normalize_dna(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = re.sub(r"\s+", "", value).upper()
        if any(base not in {"A", "C", "G", "T", "N"} for base in normalized):
            raise ValueError("DNA sequence must contain only A, C, G, T, and N bases.")
        return normalized

    @field_validator("pam")
    @classmethod
    def _normalize_target_pam(cls, value: str | None) -> str | None:
        if value is None:
            return None
        pam = value.upper()
        if any(base not in {"A", "C", "G", "T", "N"} for base in pam):
            raise ValueError("pam must contain only A, C, G, T, and N bases.")
        return pam


class CrisprScreeningPrimerRequest(BaseModel):
    sites: list[CrisprScreeningPrimerTarget] = Field(min_length=1, max_length=50)
    genome_build: str = Field(default="GRCh38", min_length=1, max_length=32)
    flank_bp: int = Field(default=400, ge=50, le=5_000)
    naming_prefix: str = Field(default="OTS", min_length=1, max_length=64)
    mode: PrimerMode = "sanger"
    tm_min: float = Field(default=58.0, ge=40.0, le=90.0)
    tm_max: float = Field(default=62.0, ge=40.0, le=90.0)
    product_size_min: int = Field(default=300, ge=50, le=2_000)
    product_size_max: int = Field(default=700, ge=50, le=2_000)
    avoid_snps: bool = True

    @field_validator("genome_build", "naming_prefix", mode="before")
    @classmethod
    def _strip_primer_request_text(cls, value):
        return _strip_text(value)

    @model_validator(mode="after")
    def _validate_ranges(self):
        if self.tm_min > self.tm_max:
            raise ValueError("tm_min must be less than or equal to tm_max.")
        if self.product_size_min > self.product_size_max:
            raise ValueError("product_size_min must be less than or equal to product_size_max.")
        return self


class ScreeningPrimer(BaseModel):
    site_index: int
    point: str
    region: str
    name_forward: str
    name_reverse: str
    forward: str
    reverse: str
    tm_forward: float
    tm_reverse: float
    gc_forward: float
    gc_reverse: float
    product_size: int
    specificity_hits: int
    other_products: str
    secondary_structure_risk: SecondaryStructureRisk = "not_assessed"
    secondary_structure_notes: str = ""
    recommended: bool = False
    notes: str = ""
    template_source: str


class CrisprScreeningPrimerResponse(BaseModel):
    mode: PrimerMode
    primers: list[ScreeningPrimer] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AlignRequest(WorkbenchQuery):
    user_sequence: str | None = Field(default=None, max_length=WORKBENCH_USER_SEQUENCE_MAX_LENGTH)
    ab1_blob_base64: str | None = Field(default=None, max_length=WORKBENCH_AB1_BLOB_MAX_LENGTH)

    @field_validator("user_sequence", "ab1_blob_base64", mode="before")
    @classmethod
    def _strip_optional_text(cls, value):
        return _strip_text(value)


class AlignTraceRequest(BaseModel):
    ab1_blob_base64: str = Field(min_length=1, max_length=WORKBENCH_AB1_BLOB_MAX_LENGTH)

    @field_validator("ab1_blob_base64", mode="before")
    @classmethod
    def _strip_blob(cls, value):
        return _strip_text(value)


class TraceChannel(BaseModel):
    base: Literal["A", "T", "C", "G"]
    values: list[float]


class AlignTraceTrimRange(BaseModel):
    start: int
    end: int
    method: str
    q_cutoff: int


class AlignTraceHetCall(BaseModel):
    index: int
    called_base: Literal["A", "T", "C", "G"]
    secondary_base: Literal["A", "T", "C", "G"]
    main_ratio: float
    flank_ratio: float
    avg_q: float
    primary_signal: float
    secondary_signal: float


class AlignTraceResponse(BaseModel):
    sequence: str
    base_calls: list[str] = Field(default_factory=list)
    q_scores: list[int] = Field(default_factory=list)
    base_confidence: list[float] = Field(default_factory=list)
    peak_locations: list[int] = Field(default_factory=list)
    trace_channels: list[TraceChannel] = Field(default_factory=list)
    sample_count: int
    trim: AlignTraceTrimRange
    het: list[AlignTraceHetCall] = Field(default_factory=list)
    noise_floor: float
    warnings: list[str] = Field(default_factory=list)


class AlignResponse(BaseModel):
    reference: str
    sanger_read: str
    match_line: str
    mismatch_positions: list[int] = Field(default_factory=list)
    target_position: int
    trace_channels: list[TraceChannel] = Field(default_factory=list)
    base_calls: list[str] = Field(default_factory=list)
    q_scores: list[int] = Field(default_factory=list)
