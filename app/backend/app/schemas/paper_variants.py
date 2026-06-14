from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.lookup import SearchInputCandidate, SearchInputSourceInputs

VariantLevel = Literal["cdna", "protein", "genomic", "unknown"]
VariantContext = Literal["clinical_allele", "experimental_construct", "unknown"]


class PaperVariantCandidate(BaseModel):
    """One variant mention extracted from publication text (pre-resolution)."""

    gene: str | None = Field(default=None, max_length=64)
    transcript_hgvs: str | None = Field(default=None, max_length=256)
    protein_change: str | None = Field(default=None, max_length=128)
    protein_hgvs: str | None = Field(default=None, max_length=128)
    level: VariantLevel = "unknown"
    context: VariantContext = "unknown"
    evidence_quote: str | None = Field(default=None, max_length=400)

    @field_validator(
        "gene",
        "transcript_hgvs",
        "protein_change",
        "protein_hgvs",
        "evidence_quote",
        mode="before",
    )
    @classmethod
    def _strip_optional(cls, value):
        if value is None or not isinstance(value, str):
            return value
        return value.strip() or None


class PaperVariantsExtraction(BaseModel):
    """Raw structured-extraction output (the model's JSON object)."""

    variants: list[PaperVariantCandidate] = Field(default_factory=list)


class ValidatedPaperVariant(BaseModel):
    """A candidate after the resolution/validation gate."""

    gene: str | None = None
    transcript_hgvs: str | None = None
    protein_change: str | None = None
    protein_hgvs: str | None = None
    level: VariantLevel = "unknown"
    context: VariantContext = "unknown"
    evidence_quote: str | None = None
    validated: bool = False
    validation_status: str = "missing"
    variant_id: str | None = None
    genomic_hgvs: str | None = None
    resolved_candidate_id: str | None = None
    source_support: list[str] = Field(default_factory=list)
    source_inputs: SearchInputSourceInputs | None = None
    candidates: list[SearchInputCandidate] = Field(default_factory=list)
    resolver_warnings: list[str] = Field(default_factory=list)
    resolver_provenance: list[str] = Field(default_factory=list)


class PaperVariantsResult(BaseModel):
    variants: list[ValidatedPaperVariant] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)


class PaperVariantsExtractRequest(BaseModel):
    """JSON request for the paper front-door endpoint."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=1_000_000)

    @field_validator("text")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text must not be blank")
        return stripped


class PaperVariantsPdfMeta(BaseModel):
    page_count: int = 0
    engine: str
    warnings: list[str] = Field(default_factory=list)


class PaperSourceMetadata(BaseModel):
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: str | None = None
    journal: str | None = None
    doi: str | None = None
    pmid: str | None = None


class PaperVariantsGuardrails(BaseModel):
    patient_data: Literal["not_used"] = "not_used"
    raw_paper_text_in_output: Literal["blocked"] = "blocked"
    secrets_in_output: Literal["blocked"] = "blocked"


class PaperVariantsExtractResponse(PaperVariantsResult):
    """HTTP front-door response: sanitized result plus CLI-style metadata."""

    mode: Literal["paper_variants_extract"] = "paper_variants_extract"
    generated_at: datetime
    llm_provider: str
    pdf: PaperVariantsPdfMeta | None = None
    source_metadata: PaperSourceMetadata | None = None
    guardrails: PaperVariantsGuardrails = Field(default_factory=PaperVariantsGuardrails)
    candidate_count: int
    validated_count: int
