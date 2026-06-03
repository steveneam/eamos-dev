from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PanelSource = Literal["panelapp-au", "panelapp-gel", "clingen-gencc", "custom"]
PanelConfidence = Literal["green", "amber", "red"]
PanelValidity = Literal[
    "definitive",
    "strong",
    "moderate",
    "limited",
    "disputed",
    "refuted",
    "animal_model_only",
    "no_known_disease_relationship",
]
PanelMinimumValidity = Literal["definitive", "strong"]


class PanelGene(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    hgnc_id: str | None = Field(default=None, max_length=32)
    confidence: PanelConfidence | None = None
    moi: str | None = Field(default=None, max_length=64)
    disease: str | None = Field(default=None, max_length=256)
    mondo_id: str | None = Field(default=None, max_length=32)
    validity: PanelValidity | None = None
    provenance: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("symbol", mode="before")
    @classmethod
    def _normalize_symbol(cls, value):
        if not isinstance(value, str):
            return value
        stripped = value.strip().upper()
        return stripped or None

    @field_validator("hgnc_id", "moi", "disease", "mondo_id", mode="before")
    @classmethod
    def _strip_optional_text(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class PanelSummary(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    slug: str = Field(min_length=1, max_length=128)
    source: PanelSource
    version: str = Field(min_length=1, max_length=128)
    provenance_url: str | None = Field(default=None, max_length=512)
    gene_count: int = Field(ge=0)
    intervals_ref: Literal["hg38"] = "hg38"
    warnings: list[str] = Field(default_factory=list)


class Panel(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    slug: str = Field(min_length=1, max_length=128)
    source: PanelSource
    version: str = Field(min_length=1, max_length=128)
    provenance_url: str | None = Field(default=None, max_length=512)
    genes: list[PanelGene] = Field(default_factory=list)
    intervals_ref: Literal["hg38"] = "hg38"
    warnings: list[str] = Field(default_factory=list)


class PanelListResponse(BaseModel):
    panels: list[PanelSummary] = Field(default_factory=list)


class PanelResolveRequest(BaseModel):
    disease_mondo: str | None = Field(default=None, max_length=32)
    symbols: list[str] | None = Field(default=None, min_length=1, max_length=1000)
    upload_ref: str | None = Field(default=None, max_length=256)
    min_validity: PanelMinimumValidity = "strong"

    @field_validator("disease_mondo", "upload_ref", mode="before")
    @classmethod
    def _strip_optional_text(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("symbols", mode="before")
    @classmethod
    def _normalize_symbols(cls, value):
        if value is None:
            return value
        if not isinstance(value, list):
            return value
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                normalized.append(item)
                continue
            symbol = item.strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            normalized.append(symbol)
        return normalized

    @model_validator(mode="after")
    def _validate_resolution_source(self):
        source_count = sum(
            bool(item)
            for item in (
                self.disease_mondo,
                self.symbols,
                self.upload_ref,
            )
        )
        if source_count != 1:
            raise ValueError("Provide exactly one of disease_mondo, symbols, or upload_ref.")
        return self
