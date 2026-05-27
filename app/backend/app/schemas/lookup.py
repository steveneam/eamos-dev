from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.run import EvidenceSourceSummary, ReportPayload

SearchInputMode = Literal[
    "structured",
    "deterministic",
    "ai_assisted",
    "auto_resolved",
    "needs_selection",
    "suggestions",
]
SearchInputConfidence = Literal["high", "medium", "low"]
SearchInputVariantClass = Literal[
    "snv",
    "missense",
    "nonsense",
    "frameshift",
    "splice",
    "deletion",
    "insertion",
    "duplication",
    "delins",
    "unknown",
]


class SearchInputAiExtraction(BaseModel):
    gene: str | None = Field(default=None, max_length=64)
    gene_alias: str | None = Field(default=None, max_length=128)
    cdna: str | None = Field(default=None, max_length=256)
    transcript: str | None = Field(default=None, max_length=64)
    protein_change: str | None = Field(default=None, max_length=128)
    genomic_hint: str | None = Field(default=None, max_length=256)
    variant_class: SearchInputVariantClass = "unknown"
    disease_context: str | None = Field(default=None, max_length=256)
    confidence: SearchInputConfidence = "low"
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator(
        "gene",
        "gene_alias",
        "cdna",
        "transcript",
        "protein_change",
        "genomic_hint",
        "disease_context",
        mode="before",
    )
    @classmethod
    def _strip_optional_text(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("gene")
    @classmethod
    def _normalize_gene(cls, value):
        return value.upper() if value else value


class LookupRequest(BaseModel):
    search_text: str | None = Field(default=None, min_length=1, max_length=512)
    query: str | None = Field(default=None, min_length=1, max_length=512)
    gene: str | None = Field(default=None, min_length=1, max_length=64)
    cdna: str | None = Field(default=None, min_length=1, max_length=256)
    transcript: str | None = Field(default=None, max_length=64)
    protein_change: str | None = Field(default=None, max_length=128)
    species: Literal["human", "mouse"] = "human"
    confirmed_interpretation: bool = False
    selected_candidate_id: str | None = Field(default=None, max_length=128)

    @field_validator(
        "search_text",
        "query",
        "gene",
        "cdna",
        "transcript",
        "protein_change",
        "selected_candidate_id",
        mode="before",
    )
    @classmethod
    def _strip_text_fields(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def _validate_input_mode(self):
        if self.search_text and self.query and self.search_text != self.query:
            raise ValueError("search_text and query must match when both are provided.")

        raw_text_present = bool(self.search_text or self.query)
        candidate_present = bool(self.selected_candidate_id)
        structured_present = any((self.gene, self.cdna, self.transcript, self.protein_change))
        if (raw_text_present or candidate_present) and structured_present:
            raise ValueError("Provide either search_text/query or structured fields, not both.")

        if raw_text_present or candidate_present:
            return self

        if not self.gene or not self.cdna:
            raise ValueError("Provide gene and cdna, or provide search_text.")
        return self

    @property
    def raw_search_text(self) -> str | None:
        return self.search_text or self.query


class SearchInputSourceInputs(BaseModel):
    variant_validator: str | None = None
    ensembl_vep: str | None = None
    gnomad: str | None = None
    spliceai: str | None = None
    clinvar: str | None = None
    literature_terms: list[str] = Field(default_factory=list)


class SearchInputCandidate(BaseModel):
    candidate_id: str
    display_label: str
    gene: str
    cdna: str | None = None
    transcript: str | None = None
    protein_change: str | None = None
    genomic_hg38: str | None = None
    genomic_hgvs: str | None = None
    match_reason: str
    source_support: list[str] = Field(default_factory=list)
    source_count: int = 0
    distance: str | None = None
    confidence: SearchInputConfidence = "medium"
    warnings: list[str] = Field(default_factory=list)


class SearchInputInterpretation(BaseModel):
    submitted_text: str
    mode: SearchInputMode
    confidence: SearchInputConfidence
    gene: str | None = None
    cdna: str | None = None
    transcript: str | None = None
    protein_change: str | None = None
    normalized_query: str | None = None
    query_kind: str | None = None
    genomic_hg38: str | None = None
    genomic_hgvs: str | None = None
    source_inputs: SearchInputSourceInputs | None = None
    requires_confirmation: bool = False
    exact_variant_available: bool = True
    auto_selected_candidate_id: str | None = None
    candidates: list[SearchInputCandidate] = Field(default_factory=list)
    ui_prompt: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)


class SearchInputParseRequest(BaseModel):
    search_text: str = Field(min_length=1, max_length=512)
    species: Literal["human", "mouse"] = "human"
    allow_ai: bool = True
    resolve_coordinates: bool = False

    @field_validator("search_text", mode="before")
    @classmethod
    def _strip_search_text(cls, value):
        if not isinstance(value, str):
            return value
        return value.strip()


class SearchInputParseResponse(BaseModel):
    interpretation: SearchInputInterpretation


class LookupResponse(BaseModel):
    query: str
    species: str
    report_payload: ReportPayload
    evidence: list[EvidenceSourceSummary]
    warnings: list[str]
    search_interpretation: SearchInputInterpretation | None = None


LookupSectionId = Literal["publications", "computational_deep_dive", "clingen_vcep"]
LookupSectionStatus = Literal["available", "partial", "missing"]


class LookupSummaryTile(BaseModel):
    tile_id: str
    title: str
    primary_label: str
    support_badges: list[str] = Field(default_factory=list)
    source_status: str
    ui_color_theme: str
    target_section_id: str | None = None
    target_panel_id: str | None = None
    fetch_section_id: LookupSectionId | None = None
    warnings: list[str] = Field(default_factory=list)


class LookupSectionDescriptor(BaseModel):
    section_id: LookupSectionId
    endpoint: str = "/api/v1/lookup/sections"
    include_value: LookupSectionId
    hydration: Literal["expand"] = "expand"


class LookupInitialSummaryResponse(BaseModel):
    query: str
    species: str
    header: dict[str, Any] | None = None
    tiles: list[LookupSummaryTile] = Field(default_factory=list)
    lazy_sections: list[LookupSectionDescriptor] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LookupSectionFetchRequest(LookupRequest):
    include: list[LookupSectionId] = Field(min_length=1, max_length=3)

    @field_validator("include")
    @classmethod
    def _dedupe_include(cls, value: list[LookupSectionId]) -> list[LookupSectionId]:
        seen: set[LookupSectionId] = set()
        result: list[LookupSectionId] = []
        for item in value:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result


class LookupSectionFreshness(BaseModel):
    fetched_at: str | None = None
    source_version: str | None = None
    stale_on_failure: bool = False
    source_status: str | None = None
    source_url: str | None = None


class LookupSectionEnvelope(BaseModel):
    section_id: LookupSectionId
    status: LookupSectionStatus
    payload: dict[str, Any] | None = None
    freshness: LookupSectionFreshness = Field(default_factory=LookupSectionFreshness)
    warnings: list[str] = Field(default_factory=list)


class LookupSectionFetchResponse(BaseModel):
    query: str
    species: str
    sections: dict[LookupSectionId, LookupSectionEnvelope] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


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
