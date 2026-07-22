from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.capabilities import CapabilityExecutionDisclosureV2

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
PanelLaunchPostureV2 = Literal["ready", "gated", "unavailable"]
PanelIntervalScopeV2 = Literal["whole_gene", "mane_exon_splice", "capture_bed"]


class _PanelV2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_default=True)


class PanelSourceSnapshotV2(_PanelV2Model):
    schema_version: Literal["panel_source_snapshot.v2"] = "panel_source_snapshot.v2"
    snapshot_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )
    source: PanelSource
    version: str = Field(min_length=1, max_length=128)
    release: str = Field(min_length=1, max_length=128)
    retrieved_at: datetime
    launch_posture: PanelLaunchPostureV2
    licence_id: str = Field(min_length=1, max_length=128)
    provenance_url: AnyHttpUrl | None = None
    artifact_manifest_id: str | None = Field(default=None, min_length=1, max_length=128)
    artifact_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    execution_disclosure: CapabilityExecutionDisclosureV2

    @field_validator("retrieved_at")
    @classmethod
    def _normalize_retrieved_at(cls, value: datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at requires a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _validate_snapshot(self):
        if (self.artifact_manifest_id is None) != (self.artifact_sha256 is None):
            raise ValueError("panel artifact manifest and digest must be supplied together")
        disclosure = self.execution_disclosure
        if (
            self.artifact_manifest_id != disclosure.artifact_manifest_id
            or self.artifact_sha256 != disclosure.artifact_sha256
        ):
            raise ValueError("panel artifact identity must match its execution disclosure")
        if self.launch_posture == "ready":
            if disclosure.execution not in {"eamos_local", "mounted_artifact"}:
                raise ValueError("ready panel snapshots require executed local material")
            if disclosure.source_status != "source_backed":
                raise ValueError("ready panel snapshots require source-backed material")
            if self.artifact_manifest_id is None or self.artifact_sha256 is None:
                raise ValueError("ready panel snapshots require an immutable artifact identity")
        if self.launch_posture != "ready" and self.execution_disclosure.execution != "unavailable":
            raise ValueError("gated or unavailable panel snapshots must fail closed")
        return self


class _PanelSnapshotBinding(BaseModel):
    source: PanelSource
    version: str = Field(min_length=1, max_length=128)
    provenance_url: AnyHttpUrl | None = None
    source_snapshot_v2: PanelSourceSnapshotV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def _validate_snapshot_binding(self):
        snapshot = self.source_snapshot_v2
        if snapshot is None:
            return self
        if self.source != snapshot.source or self.version != snapshot.version:
            raise ValueError("panel source and version must match the source snapshot")
        top_url = str(self.provenance_url) if self.provenance_url is not None else None
        snapshot_url = str(snapshot.provenance_url) if snapshot.provenance_url is not None else None
        if top_url != snapshot_url:
            raise ValueError("panel provenance_url must match the source snapshot")
        return self


class PanelIntervalProvenanceV2(_PanelV2Model):
    scope: PanelIntervalScopeV2
    genome_build: Literal["GRCh38"]
    interval_release: str = Field(min_length=1, max_length=128)
    interval_manifest_id: str = Field(min_length=1, max_length=128)
    interval_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    splice_flank_bases: int | None = Field(default=None, ge=0, le=1000)

    @model_validator(mode="after")
    def _validate_splice_flank(self):
        if self.scope == "mane_exon_splice" and self.splice_flank_bases is None:
            raise ValueError("MANE exon/splice intervals require a splice flank")
        if self.scope != "mane_exon_splice" and self.splice_flank_bases is not None:
            raise ValueError("splice_flank_bases applies only to MANE exon/splice scope")
        return self


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
    interval_provenance_v2: PanelIntervalProvenanceV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

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


class PanelSummary(_PanelSnapshotBinding):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    slug: str = Field(min_length=1, max_length=128)
    gene_count: int = Field(ge=0)
    intervals_ref: Literal["hg38"] = "hg38"
    warnings: list[str] = Field(default_factory=list)


class Panel(_PanelSnapshotBinding):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    slug: str = Field(min_length=1, max_length=128)
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
