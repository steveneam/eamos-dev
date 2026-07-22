from __future__ import annotations

import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.capabilities import CapabilityExecutionDisclosureV2
from app.schemas.source_disclosure import SourceDisclosure
from app.schemas.workflow import (
    WorkbenchDesignContextV1,
    WorkbenchDesignContextV2,
    WorkbenchResultBindingV2,
)

PrimerMode = Literal["sanger", "qpcr", "arms"]
SecondaryStructureRisk = Literal["low", "moderate", "high", "not_assessed"]
PrimerTemplateStrand = Literal["Plus", "Minus"]
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


class _WorkbenchResponseV2Envelope(BaseModel):
    """Atomic V2 response binding; legacy responses omit the whole envelope."""

    execution_disclosure: CapabilityExecutionDisclosureV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    verified_context: WorkbenchDesignContextV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    context_binding: WorkbenchResultBindingV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def _validate_v2_response_envelope(self):
        envelope = (
            self.execution_disclosure,
            self.verified_context,
            self.context_binding,
        )
        present = sum(value is not None for value in envelope)
        if present not in {0, len(envelope)}:
            raise ValueError(
                "Workbench V2 response fields must be supplied together or omitted together"
            )
        if (
            self.verified_context is not None
            and self.context_binding is not None
            and self.context_binding.result_context_digest != self.verified_context.context_digest
        ):
            raise ValueError("result context binding must match the verified context digest")
        return self


class WorkbenchQuery(BaseModel):
    gene: str = Field(min_length=1, max_length=WORKBENCH_GENE_MAX_LENGTH)
    cdna: str = Field(min_length=1, max_length=WORKBENCH_CDNA_MAX_LENGTH)
    design_context: WorkbenchDesignContextV1 | None = None
    design_context_v2: WorkbenchDesignContextV2 | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @field_validator("gene", "cdna", mode="before")
    @classmethod
    def _strip_query_text(cls, value):
        return _strip_text(value)

    @model_validator(mode="after")
    def _validate_design_context(self):
        if self.design_context is not None and self.design_context_v2 is not None:
            raise ValueError("Provide only one Workbench design-context version")
        context = self.design_context_v2 or self.design_context
        if context is None:
            return self
        variant = context.variant
        if self.gene.upper() != variant.gene or self.cdna != variant.cdna:
            raise ValueError("query gene and cdna must match the design-context variant")
        transcript = getattr(self, "transcript", None)
        if transcript is not None and transcript != variant.transcript:
            raise ValueError("query transcript must match the design-context variant")
        return self


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
    self_any_forward: float | None = None
    self_any_reverse: float | None = None
    self_end_forward: float | None = None
    self_end_reverse: float | None = None
    hairpin_tm_forward: float | None = None
    hairpin_tm_reverse: float | None = None
    pair_compl_end: float | None = None
    forward_strand: PrimerTemplateStrand | None = None
    reverse_strand: PrimerTemplateStrand | None = None
    forward_template_start: int | None = None
    forward_template_stop: int | None = None
    reverse_template_start: int | None = None
    reverse_template_stop: int | None = None
    genomic_chromosome: str | None = None
    genome_build: str | None = None
    forward_genomic_start: int | None = None
    forward_genomic_stop: int | None = None
    reverse_genomic_start: int | None = None
    reverse_genomic_stop: int | None = None
    amplicon_template_start: int | None = None
    amplicon_template_end: int | None = None
    amplicon_genomic_start: int | None = None
    amplicon_genomic_end: int | None = None
    notes: str = ""
    recommended: bool = False


class PrimerResponse(_WorkbenchResponseV2Envelope):
    mode: PrimerMode
    pairs: list[PrimerPair] = Field(default_factory=list)
    source_disclosure: SourceDisclosure | None = None


CasEnzyme = Literal["SpCas9", "SaCas9", "Cas12a"]
CrisprScoreFamilyV2 = Literal["on_target", "off_target", "enumeration"]
CrisprScoreDirectionV2 = Literal["higher_is_better", "lower_is_better", "descriptive"]


class _WorkbenchV2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_default=True)


class CrisprVerifiedLocusV2(_WorkbenchV2Model):
    genome_build: Literal["GRCh38"]
    chromosome: str = Field(min_length=1, max_length=32)
    protospacer_start: int = Field(ge=1)
    protospacer_end: int = Field(ge=1)
    pam_start: int = Field(ge=1)
    pam_end: int = Field(ge=1)
    cut_position: int = Field(ge=1)
    strand: Literal["+", "-"]

    @model_validator(mode="after")
    def _validate_locus(self):
        if self.protospacer_start > self.protospacer_end or self.pam_start > self.pam_end:
            raise ValueError("CRISPR locus intervals must be ordered")
        locus_start = min(self.protospacer_start, self.pam_start)
        locus_end = max(self.protospacer_end, self.pam_end)
        if not locus_start <= self.cut_position <= locus_end:
            raise ValueError("cut_position must lie inside the verified guide/PAM locus")
        return self


def build_crispr_guide_identity_digest_v2(
    *,
    guide: str,
    pam: str,
    enzyme: CasEnzyme,
    locus: CrisprVerifiedLocusV2,
    context_digest: str,
) -> str:
    payload = {
        "context_digest": context_digest,
        "enzyme": enzyme,
        "genome_build": locus.genome_build,
        "guide": guide,
        "locus": locus.model_dump(mode="json"),
        "pam": pam,
        "schema_version": "crispr_guide_identity.v2",
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class CrisprGuideIdentityV2(_WorkbenchV2Model):
    schema_version: Literal["crispr_guide_identity.v2"] = "crispr_guide_identity.v2"
    guide_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )
    guide: str = Field(min_length=20, max_length=20, pattern=r"^[ACGT]{20}$")
    pam: str = Field(min_length=2, max_length=8, pattern=r"^[ACGTN]+$")
    enzyme: CasEnzyme
    locus: CrisprVerifiedLocusV2
    context_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("guide", "pam", mode="before")
    @classmethod
    def _normalize_sequences(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("context_digest", "identity_sha256", mode="before")
    @classmethod
    def _normalize_digests(cls, value):
        return value.lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _validate_identity(self):
        if self.locus.protospacer_end - self.locus.protospacer_start + 1 != len(self.guide):
            raise ValueError("protospacer interval length must match the guide length")
        if self.locus.pam_end - self.locus.pam_start + 1 != len(self.pam):
            raise ValueError("PAM interval length must match the PAM length")
        expected = build_crispr_guide_identity_digest_v2(
            guide=self.guide,
            pam=self.pam,
            enzyme=self.enzyme,
            locus=self.locus,
            context_digest=self.context_digest,
        )
        if self.identity_sha256 != expected:
            raise ValueError("identity_sha256 must bind guide, PAM, locus, enzyme, and context")
        return self


class CrisprScoreV2(_WorkbenchV2Model):
    score_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )
    family: CrisprScoreFamilyV2
    algorithm_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )
    algorithm_version: str = Field(min_length=1, max_length=128)
    value: float = Field(allow_inf_nan=False)
    scale_min: float = Field(allow_inf_nan=False)
    scale_max: float = Field(allow_inf_nan=False)
    direction: CrisprScoreDirectionV2
    context_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    guide_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_disclosure: CapabilityExecutionDisclosureV2

    @field_validator("context_digest", "guide_identity_sha256", mode="before")
    @classmethod
    def _normalize_score_digests(cls, value):
        return value.lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _validate_scale(self):
        if self.scale_min >= self.scale_max:
            raise ValueError("score scale_min must be less than scale_max")
        if not self.scale_min <= self.value <= self.scale_max:
            raise ValueError("score value must lie inside its declared scale")
        if self.execution_disclosure.execution not in {
            "eamos_local",
            "mounted_artifact",
            "external_provider",
        }:
            raise ValueError("value-bearing CRISPR scores require executed capability output")
        if self.execution_disclosure.algorithm_id != self.algorithm_id:
            raise ValueError("score algorithm_id must match its execution disclosure")
        if self.execution_disclosure.algorithm_version != self.algorithm_version:
            raise ValueError("score algorithm_version must match its execution disclosure")
        return self


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
    # V1 aggregate scores remain during migration. Remove them after every
    # consumer reads the algorithm-explicit ``scores`` collection.
    identity: CrisprGuideIdentityV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    scores: list[CrisprScoreV2] = Field(
        default_factory=list, max_length=32, exclude_if=lambda value: not value
    )
    execution_disclosure: CapabilityExecutionDisclosureV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def _validate_v2_scores(self):
        if self.scores and self.identity is None:
            raise ValueError("algorithm-explicit scores require a verified guide identity")
        if self.identity is not None and (
            self.guide != self.identity.guide
            or self.pam != self.identity.pam
            or self.strand != self.identity.locus.strand
        ):
            raise ValueError("guide row must match its verified guide identity")
        if self.identity is not None and any(
            score.context_digest != self.identity.context_digest
            or score.guide_identity_sha256 != self.identity.identity_sha256
            for score in self.scores
        ):
            raise ValueError("guide scores must bind to the exact guide identity")
        return self


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
    variant_genomic: str | None = None
    intron_mask: list[bool]
    strand: Literal["+", "-"]
    orientation: SsodnOrientation
    protocol: SsodnProtocol
    template_source: str
    genome_build: str


class CrisprResponse(_WorkbenchResponseV2Envelope):
    cas: CasEnzyme
    guides: list[CrisprGuide] = Field(default_factory=list)
    ssodn: HdrSsodn | None = None
    source_disclosure: SourceDisclosure | None = None


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


class CrisprSsodnResponse(_WorkbenchResponseV2Envelope):
    genome_build: str
    ssodn: CrisprSsodnDesign
    warnings: list[str] = Field(default_factory=list)
    source_disclosure: SourceDisclosure | None = None


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
    design_context: WorkbenchDesignContextV1 | None = None
    design_context_v2: WorkbenchDesignContextV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    guide_identity: CrisprGuideIdentityV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

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

    @model_validator(mode="after")
    def _validate_v2_identity(self):
        if self.design_context is not None and self.design_context_v2 is not None:
            raise ValueError("Provide only one Workbench design-context version")
        if self.guide_identity is None:
            return self
        if self.design_context_v2 is None:
            raise ValueError("guide_identity requires design_context_v2")
        if self.guide != self.guide_identity.guide or self.pam != self.guide_identity.pam:
            raise ValueError("guide and PAM must match guide_identity")
        if self.enzyme != self.guide_identity.enzyme:
            raise ValueError("enzyme must match guide_identity")
        if self.genome_build != self.guide_identity.locus.genome_build:
            raise ValueError("genome_build must match guide_identity")
        if self.design_context_v2.context_digest != self.guide_identity.context_digest:
            raise ValueError("guide_identity must be bound to design_context_v2")
        return self


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
    scores: list[CrisprScoreV2] = Field(
        default_factory=list, max_length=32, exclude_if=lambda value: not value
    )


class CrisprOffTargetResponse(_WorkbenchResponseV2Envelope):
    genome_build: str
    sites: list[CrisprOffTargetSite] = Field(default_factory=list)
    source_disclosure: SourceDisclosure | None = None
    guide_identity: CrisprGuideIdentityV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def _validate_score_contexts(self):
        scores = [score for site in self.sites for score in site.scores]
        if scores and self.guide_identity is None:
            raise ValueError("off-target scores require a verified guide identity")
        if self.guide_identity is not None and any(
            score.context_digest != self.guide_identity.context_digest
            or score.guide_identity_sha256 != self.guide_identity.identity_sha256
            for score in scores
        ):
            raise ValueError("off-target scores must bind to the exact guide identity")
        return self


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
    design_context: WorkbenchDesignContextV1 | None = None
    design_context_v2: WorkbenchDesignContextV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
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
        if self.design_context is not None and self.design_context_v2 is not None:
            raise ValueError("Provide only one Workbench design-context version")
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


class CrisprScreeningPrimerResponse(_WorkbenchResponseV2Envelope):
    mode: PrimerMode
    primers: list[ScreeningPrimer] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_disclosure: SourceDisclosure | None = None


class CrisprTideSpectrumBin(BaseModel):
    size: int = Field(ge=-50, le=50)
    observed: float = Field(ge=0.0, le=1.0)
    predicted: float | None = Field(default=None, ge=0.0, le=1.0)


class CrisprTideResponse(_WorkbenchResponseV2Envelope):
    source_backed: bool = True
    analysis_kind: Literal["tide", "descriptive_trace_comparison"] = "tide"
    provider_label: str = "Eamos observed-only TIDE-style analyzer"
    source_disclosure: SourceDisclosure | None = None
    cut_site_index: int = Field(ge=1)
    editing_efficiency: float = Field(ge=0.0, le=1.0)
    r_squared: float = Field(ge=0.0, le=1.0)
    spectrum: list[CrisprTideSpectrumBin] = Field(default_factory=list)
    predicted_available: bool = False
    notes: str
    warnings: list[str] = Field(default_factory=list)


class AlignRequest(WorkbenchQuery):
    user_sequence: str | None = Field(default=None, max_length=WORKBENCH_USER_SEQUENCE_MAX_LENGTH)
    ab1_blob_base64: str | None = Field(default=None, max_length=WORKBENCH_AB1_BLOB_MAX_LENGTH)

    @field_validator("user_sequence", "ab1_blob_base64", mode="before")
    @classmethod
    def _strip_optional_text(cls, value):
        return _strip_text(value)


class AlignReferenceRequest(WorkbenchQuery):
    transcript: str | None = Field(default=None, max_length=128)
    species: Literal["human", "mouse"] = "human"

    @field_validator("transcript", mode="before")
    @classmethod
    def _strip_reference_text(cls, value):
        return _strip_text(value)


class AlignTraceRequest(BaseModel):
    ab1_blob_base64: str = Field(min_length=1, max_length=WORKBENCH_AB1_BLOB_MAX_LENGTH)
    design_context_v2: WorkbenchDesignContextV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

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


class AlignTraceResponse(_WorkbenchResponseV2Envelope):
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
    source_disclosure: SourceDisclosure | None = None


class AlignResponse(_WorkbenchResponseV2Envelope):
    reference: str
    sanger_read: str
    match_line: str
    mismatch_positions: list[int] = Field(default_factory=list)
    target_position: int
    trace_channels: list[TraceChannel] = Field(default_factory=list)
    base_calls: list[str] = Field(default_factory=list)
    q_scores: list[int] = Field(default_factory=list)
    source_disclosure: SourceDisclosure | None = None


class AlignReferenceResponse(_WorkbenchResponseV2Envelope):
    gene: str
    cdna: str
    transcript: str | None = None
    transcript_hgvs: str
    genome_build: str
    genomic_hg38: str | None = None
    strand: str
    reference: str
    target_position: int
    reference_base: str | None = None
    alternate_base: str | None = None
    source: str
    warnings: list[str] = Field(default_factory=list)
    source_disclosure: SourceDisclosure | None = None
