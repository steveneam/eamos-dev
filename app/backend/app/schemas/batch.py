from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.capabilities import CapabilityExecutionDisclosureV2

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
BATCH_MAX_VARIANTS = 5000
BatchInputFormatV2 = Literal["vcf", "vcf_gz", "bcf"]
BatchAnalysisScopeV2 = Literal["wes", "targeted_panel"]
BatchCohortModelV2 = Literal["single", "proband", "small_family"]
BatchNormalizationStatusV2 = Literal[
    "normalized",
    "reference_mismatch",
    "unsupported",
    "failed",
]
BatchFilterStageV2 = Literal["pre_annotation", "post_annotation"]
BatchFilterOutcomeV2 = Literal["included", "excluded", "deferred"]
BatchFilterReasonV2 = Literal[
    "pass_filter",
    "quality",
    "region",
    "gene_scope",
    "capture_scope",
    "genotype",
    "depth",
    "duplicate",
    "consequence",
    "population_frequency",
    "classification",
    "evidence_state",
    "annotation_cap",
    "source_unavailable",
]
BatchIntervalScopeV2 = Literal["whole_gene", "mane_exon_splice", "capture_bed"]
BatchFieldNameV2 = Literal[
    "gene",
    "hgvs_c",
    "hgvs_p",
    "clinvar_verdict",
    "gnomad_af",
    "predictor_ensemble",
    "acmg_classification",
]
BatchFieldValueStatusV2 = Literal["executed", "unavailable", "not_applicable"]
BatchExportFormatV2 = Literal["tsv", "csv", "jsonl", "vcf"]
BatchExportStateV2 = Literal["queued", "running", "ready", "failed", "expired"]
BatchBoundedText = Annotated[str, Field(min_length=1, max_length=512)]
BatchRegionText = Annotated[str, Field(min_length=1, max_length=128)]
BatchFilterTerm = Annotated[str, Field(min_length=1, max_length=128)]
_BATCH_FIELD_NAMES = {
    "gene",
    "hgvs_c",
    "hgvs_p",
    "clinvar_verdict",
    "gnomad_af",
    "predictor_ensemble",
    "acmg_classification",
}
_PRE_ANNOTATION_REASONS = {
    "pass_filter",
    "quality",
    "region",
    "gene_scope",
    "capture_scope",
    "genotype",
    "depth",
    "duplicate",
    "annotation_cap",
    "source_unavailable",
}
_POST_ANNOTATION_REASONS = {
    "consequence",
    "population_frequency",
    "classification",
    "evidence_state",
    "source_unavailable",
}


class _BatchV2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_default=True)


class BatchInputEnvelopeV2(_BatchV2Model):
    schema_version: Literal["batch_input_envelope.v2"] = "batch_input_envelope.v2"
    format: BatchInputFormatV2
    analysis_scope: BatchAnalysisScopeV2
    cohort_model: BatchCohortModelV2
    genome_build: Literal["GRCh38"]
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    compressed_bytes: int = Field(ge=1, le=2_000_000_000)
    decompressed_bytes: int = Field(ge=1, le=10_000_000_000)
    raw_record_count: int = Field(ge=0, le=10_000_000)
    sample_count: int = Field(ge=1, le=16)
    post_filter_variant_cap: int = Field(ge=1, le=100_000)
    accepted_variant_classes: list[Literal["snv", "short_indel"]] = Field(
        min_length=1,
        max_length=2,
    )
    warnings: list[BatchBoundedText] = Field(default_factory=list, max_length=64)

    @field_validator("source_sha256", mode="before")
    @classmethod
    def _normalize_sha256(cls, value):
        return value.lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _validate_envelope(self):
        if self.decompressed_bytes < self.compressed_bytes and self.format == "vcf_gz":
            raise ValueError("decompressed_bytes cannot be smaller than compressed_bytes")
        if len(self.accepted_variant_classes) != len(set(self.accepted_variant_classes)):
            raise ValueError("accepted_variant_classes must be deduplicated")
        return self


class BatchAlleleV2(_BatchV2Model):
    genome_build: Literal["GRCh38"]
    chromosome: str = Field(min_length=1, max_length=32)
    position: int = Field(ge=1)
    reference: str = Field(min_length=1, max_length=2048, pattern=r"^[ACGTN]+$")
    alternate: str = Field(min_length=1, max_length=2048, pattern=r"^[ACGTN]+$")

    @field_validator("reference", "alternate", mode="before")
    @classmethod
    def _normalize_allele(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class BatchAlleleIdentityV2(_BatchV2Model):
    original: BatchAlleleV2
    normalized: BatchAlleleV2 | None = None
    status: BatchNormalizationStatusV2
    source_record_index: int = Field(ge=0)
    normalization_algorithm_id: str = Field(min_length=1, max_length=128)
    normalization_algorithm_version: str = Field(min_length=1, max_length=128)
    reference_manifest_id: str = Field(min_length=1, max_length=128)
    reference_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    warnings: list[BatchBoundedText] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def _validate_normalization(self):
        if (self.status == "normalized") != (self.normalized is not None):
            raise ValueError("only normalized alleles may carry a normalized representation")
        return self


class BatchSourceSnapshotV2(_BatchV2Model):
    schema_version: Literal["batch_source_snapshot.v2"] = "batch_source_snapshot.v2"
    snapshot_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )
    created_at: datetime
    genome_build: Literal["GRCh38"]
    reference_release: str = Field(min_length=1, max_length=128)
    capabilities: list[CapabilityExecutionDisclosureV2] = Field(min_length=1, max_length=128)

    @field_validator("created_at")
    @classmethod
    def _normalize_created_at(cls, value: datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at requires a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _validate_capabilities(self):
        ids = [capability.capability_id for capability in self.capabilities]
        if len(ids) != len(set(ids)):
            raise ValueError("snapshot capability_id values must be unique")
        return self


class BatchFilterPlanV2(_BatchV2Model):
    pass_only: bool = True
    minimum_quality: float | None = Field(
        default=None,
        ge=0.0,
        le=1_000_000.0,
        allow_inf_nan=False,
    )
    regions: list[BatchRegionText] = Field(default_factory=list, max_length=500)
    interval_scope: BatchIntervalScopeV2
    interval_snapshot_id: str = Field(min_length=1, max_length=128)
    panel_snapshot_id: str | None = Field(default=None, min_length=1, max_length=128)
    max_population_af: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    consequence_terms: list[BatchFilterTerm] = Field(default_factory=list, max_length=128)
    classifications: list[BatchFilterTerm] = Field(default_factory=list, max_length=64)
    require_evidence_sources: list[BatchFilterTerm] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def _validate_interval_authority(self):
        if self.interval_scope != "capture_bed" and self.panel_snapshot_id is None:
            raise ValueError("gene interval scopes require a source-backed panel_snapshot_id")
        for field_name in (
            "regions",
            "consequence_terms",
            "classifications",
            "require_evidence_sources",
        ):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must be deduplicated")
        return self


class BatchFilterDispositionV2(_BatchV2Model):
    stage: BatchFilterStageV2
    outcome: BatchFilterOutcomeV2
    reason: BatchFilterReasonV2
    detail: BatchBoundedText
    source_snapshot_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def _validate_filter_truth(self):
        allowed_reasons = (
            _PRE_ANNOTATION_REASONS if self.stage == "pre_annotation" else _POST_ANNOTATION_REASONS
        )
        if self.reason not in allowed_reasons:
            raise ValueError("filter reason must belong to its declared processing stage")
        if (self.outcome == "deferred") != (self.reason == "source_unavailable"):
            raise ValueError("source_unavailable and deferred filter outcome must agree")
        return self


class BatchSampleProvenanceV2(_BatchV2Model):
    """A server-issued sample key, never a patient/sample name from the VCF."""

    sample_key: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )
    source_sample_index: int = Field(ge=0, le=15)
    genotype: str = Field(min_length=1, max_length=32)
    phased: bool
    depth: int | None = Field(default=None, ge=0, le=10_000_000)
    genotype_quality: float | None = Field(
        default=None,
        ge=0.0,
        le=1_000_000.0,
        allow_inf_nan=False,
    )


class BatchFieldExecutionV2(_BatchV2Model):
    field_name: BatchFieldNameV2
    value_status: BatchFieldValueStatusV2
    execution_disclosure: CapabilityExecutionDisclosureV2

    @model_validator(mode="after")
    def _validate_value_status(self):
        expected = {
            "executed": {"eamos_local", "mounted_artifact", "external_provider"},
            "unavailable": {"unavailable"},
            "not_applicable": {"unavailable"},
        }[self.value_status]
        if self.execution_disclosure.execution not in expected:
            raise ValueError("field value_status must agree with execution disclosure")
        if (self.value_status == "not_applicable") != (
            self.execution_disclosure.applicability == "not_applicable"
        ):
            raise ValueError(
                "not_applicable field status must exactly match disclosure applicability"
            )
        return self


class BatchPagingV2(_BatchV2Model):
    snapshot_id: str = Field(min_length=1, max_length=128)
    limit: int = Field(ge=1, le=500)
    next_cursor: str | None = Field(default=None, max_length=512)
    total: int = Field(ge=0)
    has_more: bool

    @model_validator(mode="after")
    def _validate_cursor(self):
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("has_more must agree with next_cursor")
        return self


class BatchExportV2(_BatchV2Model):
    export_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )
    format: BatchExportFormatV2
    state: BatchExportStateV2
    source_snapshot_id: str = Field(min_length=1, max_length=128)
    row_count: int = Field(ge=0)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_export(self):
        if self.state == "ready" and self.sha256 is None:
            raise ValueError("ready exports require a content digest")
        if self.state != "ready" and self.sha256 is not None:
            raise ValueError("only ready exports may carry a content digest")
        if self.expires_at is not None:
            if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
                raise ValueError("expires_at requires a timezone")
            self.expires_at = self.expires_at.astimezone(UTC)
        return self


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
    # Server-issued and owner-bound at the route/service layer; clients never set owner identity.
    expires_at: datetime | None = Field(default=None, exclude_if=lambda value: value is None)
    single_use: bool | None = Field(default=None, exclude_if=lambda value: value is None)
    input_envelope_v2: BatchInputEnvelopeV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def _validate_v2_upload_handle(self):
        if self.input_envelope_v2 is None:
            return self
        if self.expires_at is None:
            raise ValueError("V2 upload responses require expires_at")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("V2 upload expires_at requires a timezone")
        self.expires_at = self.expires_at.astimezone(UTC)
        if self.single_use is not True:
            raise ValueError("V2 upload responses require single_use=true")
        return self


class BatchCreateRequest(BaseModel):
    variants: list[ParsedVariant] | None = Field(
        default=None, min_length=1, max_length=BATCH_MAX_VARIANTS
    )
    upload_ref: str | None = Field(default=None, max_length=256)
    filters: BatchFilters = Field(default_factory=BatchFilters)
    filter_plan_v2: BatchFilterPlanV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

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
    input_envelope_v2: BatchInputEnvelopeV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    source_snapshot_v2: BatchSourceSnapshotV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def _validate_v2_create_binding(self):
        if (self.input_envelope_v2 is None) != (self.source_snapshot_v2 is None):
            raise ValueError("V2 create responses require envelope and snapshot together")
        return self


class BatchPage(BaseModel):
    limit: int = Field(ge=1, le=500)
    next_cursor: str | None = Field(default=None, max_length=512)
    total: int = Field(ge=0)
    paging_v2: BatchPagingV2 | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def _validate_v2_page(self):
        if self.paging_v2 is not None and (
            self.limit != self.paging_v2.limit
            or self.next_cursor != self.paging_v2.next_cursor
            or self.total != self.paging_v2.total
        ):
            raise ValueError("legacy and V2 paging fields must describe the same page")
        return self


class BatchJobQuery(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)
    cursor: str | None = Field(default=None, max_length=512)
    source_snapshot_id: str | None = Field(
        default=None,
        max_length=128,
        exclude_if=lambda value: value is None,
    )

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
    allele_identity_v2: BatchAlleleIdentityV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    source_snapshot_id: str | None = Field(
        default=None,
        max_length=128,
        exclude_if=lambda value: value is None,
    )
    filter_dispositions_v2: list[BatchFilterDispositionV2] = Field(
        default_factory=list,
        max_length=64,
        exclude_if=lambda value: not value,
    )
    sample_provenance_v2: list[BatchSampleProvenanceV2] = Field(
        default_factory=list,
        max_length=16,
        exclude_if=lambda value: not value,
    )
    field_executions_v2: list[BatchFieldExecutionV2] = Field(
        default_factory=list,
        max_length=32,
        exclude_if=lambda value: not value,
    )

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

    @model_validator(mode="after")
    def _validate_v2_result(self):
        v2_in_use = any(
            (
                self.allele_identity_v2 is not None,
                self.source_snapshot_id is not None,
                bool(self.filter_dispositions_v2),
                bool(self.sample_provenance_v2),
                bool(self.field_executions_v2),
            )
        )
        if not v2_in_use:
            return self
        if self.source_snapshot_id is None:
            raise ValueError("V2 result rows require a source_snapshot_id")
        field_names = [execution.field_name for execution in self.field_executions_v2]
        if len(field_names) != len(set(field_names)):
            raise ValueError("field_executions_v2 must contain one state per field")
        if self.state == "completed":
            if self.allele_identity_v2 is None or self.allele_identity_v2.status != "normalized":
                raise ValueError("completed V2 rows require a normalized allele")
            if set(field_names) != _BATCH_FIELD_NAMES:
                raise ValueError("completed V2 rows require one state for every shared field")
        if any(
            disposition.source_snapshot_id != self.source_snapshot_id
            for disposition in self.filter_dispositions_v2
        ):
            raise ValueError("row filter dispositions must match the row source snapshot")
        sample_keys = [sample.sample_key for sample in self.sample_provenance_v2]
        sample_indexes = [sample.source_sample_index for sample in self.sample_provenance_v2]
        if len(sample_keys) != len(set(sample_keys)):
            raise ValueError("sample provenance keys must be unique within a result row")
        if len(sample_indexes) != len(set(sample_indexes)):
            raise ValueError("sample provenance indexes must be unique within a result row")
        values = {
            "gene": self.gene,
            "hgvs_c": self.hgvs_c,
            "hgvs_p": self.hgvs_p,
            "clinvar_verdict": self.clinvar_verdict,
            "gnomad_af": self.gnomad_af,
            "predictor_ensemble": self.predictor_ensemble or None,
            "acmg_classification": self.acmg_classification,
        }
        for field_execution in self.field_executions_v2:
            value_present = values[field_execution.field_name] is not None
            if value_present != (field_execution.value_status == "executed"):
                raise ValueError(
                    f"{field_execution.field_name} value presence must match its execution state"
                )
        return self


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
    input_envelope_v2: BatchInputEnvelopeV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    source_snapshot_v2: BatchSourceSnapshotV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    filter_dispositions_v2: list[BatchFilterDispositionV2] = Field(
        default_factory=list,
        max_length=128,
        exclude_if=lambda value: not value,
    )
    exports_v2: list[BatchExportV2] = Field(
        default_factory=list, max_length=16, exclude_if=lambda value: not value
    )

    @model_validator(mode="after")
    def _validate_v2_snapshot_coherence(self):
        if len(self.results) > self.page.limit or len(self.results) > self.page.total:
            raise ValueError("batch results must remain bounded by the declared page")
        v2_in_use = any(
            (
                self.input_envelope_v2 is not None,
                self.source_snapshot_v2 is not None,
                self.page.paging_v2 is not None,
                bool(self.filter_dispositions_v2),
                bool(self.exports_v2),
                any(
                    result.allele_identity_v2 is not None
                    or result.source_snapshot_id is not None
                    or bool(result.filter_dispositions_v2)
                    or bool(result.sample_provenance_v2)
                    or bool(result.field_executions_v2)
                    for result in self.results
                ),
            )
        )
        if not v2_in_use:
            return self
        if self.input_envelope_v2 is None or self.source_snapshot_v2 is None:
            raise ValueError("V2 jobs require input envelope and source snapshot")
        if self.n_to_lookup > self.input_envelope_v2.post_filter_variant_cap:
            raise ValueError("n_to_lookup cannot exceed the post-filter variant cap")
        snapshot_id = self.source_snapshot_v2.snapshot_id
        if self.page.paging_v2 is None or self.page.paging_v2.snapshot_id != snapshot_id:
            raise ValueError("V2 paging must bind to the job source snapshot")
        for result in self.results:
            if result.source_snapshot_id != snapshot_id:
                raise ValueError("V2 result rows must bind to the job source snapshot")
        if any(
            disposition.source_snapshot_id != snapshot_id
            for disposition in self.filter_dispositions_v2
        ):
            raise ValueError("filter dispositions must bind to the job source snapshot")
        if any(export.source_snapshot_id != snapshot_id for export in self.exports_v2):
            raise ValueError("exports must bind to the job source snapshot")
        return self
