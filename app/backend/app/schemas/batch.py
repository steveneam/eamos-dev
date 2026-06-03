from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

BatchJobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
BatchVariantState = Literal[
    "queued",
    "filtered_pre_lookup",
    "lookup_pending",
    "running",
    "completed",
    "filtered_post_lookup",
    "failed",
]


class ParsedVariant(BaseModel):
    raw: str | None = Field(default=None, max_length=512)
    query: str = Field(min_length=1, max_length=512)
    gene: str | None = Field(default=None, max_length=64)
    variant: str | None = Field(default=None, max_length=256)
    chrom: str | None = Field(default=None, max_length=32)
    pos: int | None = Field(default=None, ge=1)
    ref: str | None = Field(default=None, max_length=2048)
    alt: str | None = Field(default=None, max_length=2048)
    filter: str | None = Field(default=None, max_length=128)
    info_af: float | None = Field(default=None, ge=0, le=1)
    source_index: int | None = Field(default=None, ge=0)
    sample_id: str | None = Field(default=None, max_length=128)
    genotype: str | None = Field(default=None, max_length=64)
    warnings: list[str] = Field(default_factory=list)

    @field_validator(
        "raw",
        "query",
        "gene",
        "variant",
        "chrom",
        "ref",
        "alt",
        "filter",
        "sample_id",
        "genotype",
        mode="before",
    )
    @classmethod
    def _strip_text_fields(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("gene")
    @classmethod
    def _normalize_gene(cls, value):
        return value.upper() if value else value


class BatchFilters(BaseModel):
    panel_slug: str | None = Field(default=None, max_length=128)
    pass_only: bool = True
    regions: list[str] = Field(default_factory=list, max_length=500)
    max_af: float | None = Field(default=None, ge=0, le=1)

    @field_validator("panel_slug", mode="before")
    @classmethod
    def _strip_panel_slug(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("regions", mode="before")
    @classmethod
    def _normalize_regions(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        regions: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                regions.append(item)
                continue
            region = item.strip()
            if not region or region in seen:
                continue
            seen.add(region)
            regions.append(region)
        return regions


class BatchUploadResponse(BaseModel):
    upload_ref: str = Field(min_length=1, max_length=256)


class BatchCreateRequest(BaseModel):
    variants: list[ParsedVariant] | None = Field(default=None, min_length=1, max_length=5000)
    upload_ref: str | None = Field(default=None, max_length=256)
    filters: BatchFilters = Field(default_factory=BatchFilters)

    @field_validator("upload_ref", mode="before")
    @classmethod
    def _strip_upload_ref(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def _validate_variant_source(self):
        if bool(self.variants) == bool(self.upload_ref):
            raise ValueError("Provide exactly one of variants or upload_ref.")
        return self


class BatchCreateResponse(BaseModel):
    job_id: str = Field(min_length=1, max_length=128)
    n_input: int = Field(ge=0)
    n_to_lookup: int = Field(ge=0)
    est_seconds: float = Field(ge=0)


class BatchPage(BaseModel):
    limit: int = Field(ge=1, le=500)
    next_cursor: str | None = Field(default=None, max_length=512)
    total: int = Field(ge=0)


class BatchJobQuery(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)
    cursor: str | None = Field(default=None, max_length=512)

    @field_validator("cursor", mode="before")
    @classmethod
    def _strip_cursor(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class BatchResult(BaseModel):
    variant_key: str = Field(min_length=1, max_length=256)
    state: BatchVariantState = "completed"
    gene: str | None = Field(default=None, max_length=64)
    hgvs_c: str | None = Field(default=None, max_length=256)
    hgvs_p: str | None = Field(default=None, max_length=128)
    clinvar_verdict: str | None = Field(default=None, max_length=128)
    gnomad_af: float | None = Field(default=None, ge=0, le=1)
    predictor_ensemble: dict[str, Any] = Field(default_factory=dict)
    acmg_classification: str | None = Field(default=None, max_length=128)
    report_href: str | None = Field(default=None, max_length=512)
    warnings: list[str] = Field(default_factory=list)

    @field_validator(
        "variant_key",
        "gene",
        "hgvs_c",
        "hgvs_p",
        "clinvar_verdict",
        "acmg_classification",
        "report_href",
        mode="before",
    )
    @classmethod
    def _strip_text_fields(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("gene")
    @classmethod
    def _normalize_gene(cls, value):
        return value.upper() if value else value


class BatchJob(BaseModel):
    job_id: str = Field(min_length=1, max_length=128)
    status: BatchJobStatus
    n_input: int = Field(ge=0)
    n_to_lookup: int = Field(ge=0)
    n_after_filters: int | None = Field(default=None, ge=0)
    est_seconds: float = Field(ge=0)
    done: int = Field(ge=0)
    total: int = Field(ge=0)
    results: list[BatchResult] = Field(default_factory=list)
    page: BatchPage
    warnings: list[str] = Field(default_factory=list)
