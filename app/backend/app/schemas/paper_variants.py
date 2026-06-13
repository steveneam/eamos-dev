from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

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


class PaperVariantsResult(BaseModel):
    variants: list[ValidatedPaperVariant] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)
