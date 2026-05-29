from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ProteinAnnotationInputType = Literal["auto", "protein", "coding_dna"]
ProteinAnnotationStatus = Literal["available", "cache_hit", "unavailable", "failed", "partial"]
ProteinDomainFeatureKind = Literal[
    "domain",
    "site",
    "motif",
    "repeat",
    "region",
    "family",
    "epitope",
    "coiled_coil",
    "low_complexity",
    "signal_peptide",
    "transmembrane",
    "topological_domain",
]
ProteinVariantMarkerShape = Literal["triangle", "circle", "star", "pin"]


class ProteinAnnotationRequest(BaseModel):
    sequence: str = Field(min_length=1, max_length=30000)
    input_type: ProteinAnnotationInputType = "auto"
    sequence_label: str | None = Field(default=None, max_length=128)
    gene_symbol: str | None = Field(default=None, max_length=32)
    transcript: str | None = Field(default=None, max_length=64)
    protein_accession: str | None = Field(default=None, max_length=64)
    use_cache: bool = True
    allow_run: bool = True

    @field_validator("sequence", mode="before")
    @classmethod
    def _strip_sequence(cls, value):
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator("sequence_label", mode="before")
    @classmethod
    def _strip_label(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("gene_symbol", mode="before")
    @classmethod
    def _strip_gene_symbol(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip().upper()
        return stripped or None

    @field_validator("transcript", "protein_accession", mode="before")
    @classmethod
    def _strip_identifier(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class ProteinTrackProvenance(BaseModel):
    source_id: str
    source_name: str
    source_url: str | None = None
    source_release: str | None = None
    checksum_md5: str | None = None
    checksum_sha256: str | None = None
    license_status: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ProteinDomainTrackFeature(BaseModel):
    feature_id: str
    kind: ProteinDomainFeatureKind
    label: str
    short_label: str | None = None
    aa_start: int = Field(ge=1)
    aa_end: int = Field(ge=1)
    accession: str | None = None
    interpro_accession: str | None = None
    source: str
    source_accession: str | None = None
    source_release: str | None = None
    source_checksum_md5: str | None = None
    source_checksum_sha256: str | None = None
    score: float | None = None
    e_value: float | None = None
    hmm_start: int | None = Field(default=None, ge=1)
    hmm_end: int | None = Field(default=None, ge=1)
    envelope_start: int | None = Field(default=None, ge=1)
    envelope_end: int | None = Field(default=None, ge=1)
    description: str | None = None
    lane: str = "domains"
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_ranges(self):
        if self.aa_end < self.aa_start:
            raise ValueError("aa_end must be greater than or equal to aa_start")
        if (
            self.hmm_start is not None
            and self.hmm_end is not None
            and self.hmm_end < self.hmm_start
        ):
            raise ValueError("hmm_end must be greater than or equal to hmm_start")
        if (
            self.envelope_start is not None
            and self.envelope_end is not None
            and self.envelope_end < self.envelope_start
        ):
            raise ValueError("envelope_end must be greater than or equal to envelope_start")
        return self


class ProteinTrackVariantMarker(BaseModel):
    marker_id: str
    aa_start: int = Field(ge=1)
    aa_end: int = Field(ge=1)
    label: str
    hgvs_c: str | None = None
    hgvs_p: str | None = None
    variant_class: str | None = None
    classification: str | None = None
    marker_shape: ProteinVariantMarkerShape = "triangle"
    is_query: bool = False
    source: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_marker_range(self):
        if self.aa_end < self.aa_start:
            raise ValueError("aa_end must be greater than or equal to aa_start")
        return self


class ProteinDomainTrack(BaseModel):
    status: ProteinAnnotationStatus = "unavailable"
    fail_closed_reason: str | None = None
    sequence_label: str | None = None
    gene_symbol: str | None = None
    transcript: str | None = None
    protein_accession: str | None = None
    protein_sequence_hash: str | None = None
    sequence_hash_algorithm: Literal["sha256"] = "sha256"
    protein_length: int | None = Field(default=None, ge=1)
    translated_from: Literal["protein", "coding_dna", "unknown"] = "unknown"
    cache_key: str | None = None
    cache_status: Literal["cache_hit", "cache_miss", "stored", "not_used"] = "not_used"
    pfam_release: str | None = None
    hmmer_release: str | None = None
    uniprot_release: str | None = None
    features: list[ProteinDomainTrackFeature] = Field(default_factory=list)
    variant_markers: list[ProteinTrackVariantMarker] = Field(default_factory=list)
    provenance: list[ProteinTrackProvenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
