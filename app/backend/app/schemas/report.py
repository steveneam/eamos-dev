from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.capabilities import (
    CapabilityApplicabilityV2,
    CapabilityExecutionDisclosureV2,
)
from app.schemas.workflow import CanonicalVariantRefV1

ReportKind = Literal["test", "patient"]
ExtractionStatus = Literal["completed", "degraded", "blocked"]
ReportSectionIdV2 = Literal[
    "header",
    "interpretation_summary",
    "disease_mechanism",
    "gene_context_snapshot",
    "population_frequency",
    "molecular_context",
    "computational_deep_dive",
    "acmg_worksheet",
    "expert_panel",
    "publications",
    "therapies_trials",
    "provenance",
]
ReportSectionStateV2 = Literal[
    "ready",
    "empty",
    "partial",
    "unavailable",
    "not_applicable",
    "stale",
    "failed",
]
ReportMatchLevelV2 = Literal[
    "exact_allele",
    "transcript",
    "protein",
    "gene",
    "gene_disease",
    "condition",
    "discovery_only",
    "not_applicable",
]
ReportPredictorStateV2 = Literal[
    "executed",
    "unavailable",
    "not_applicable",
    "failed",
    "stale",
]
ReportCoverageV2 = Literal["partial", "complete"]
ReportBoundedText = Annotated[str, Field(min_length=1, max_length=512)]

_EXECUTED_CAPABILITY_STATES = {"eamos_local", "mounted_artifact", "external_provider"}


class _ReportV2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_default=True)


class ReportSectionExecutionV2(_ReportV2Model):
    section_id: ReportSectionIdV2
    state: ReportSectionStateV2
    match_level: ReportMatchLevelV2
    source_snapshot_id: str = Field(min_length=1, max_length=128)
    execution_disclosures: list[CapabilityExecutionDisclosureV2] = Field(
        default_factory=list,
        max_length=128,
    )
    stale_on_failure: bool = False
    warnings: list[ReportBoundedText] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def _validate_section_truth(self):
        capability_ids = [item.capability_id for item in self.execution_disclosures]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("section capability_id values must be unique")
        has_executed = any(
            item.execution in _EXECUTED_CAPABILITY_STATES for item in self.execution_disclosures
        )
        has_applicable_unavailable = any(
            item.applicability == "applicable" and item.execution == "unavailable"
            for item in self.execution_disclosures
        )
        has_failed = any(
            item.applicability == "applicable" and item.validation_status == "failed"
            for item in self.execution_disclosures
        )
        all_not_applicable = bool(self.execution_disclosures) and all(
            item.applicability == "not_applicable" for item in self.execution_disclosures
        )
        if (self.state == "not_applicable") != (self.match_level == "not_applicable"):
            raise ValueError("not_applicable section state and match level must agree")
        if (self.state == "not_applicable") != all_not_applicable:
            raise ValueError(
                "not_applicable section state must exactly match capability applicability"
            )
        if self.state in {"ready", "empty"}:
            if not has_executed:
                raise ValueError("ready and empty report sections require executed lookup evidence")
            if has_applicable_unavailable or has_failed:
                raise ValueError(
                    "ready and empty sections cannot hide applicable unavailable or failed evidence"
                )
        elif self.state == "partial":
            if not has_executed or not (has_applicable_unavailable or has_failed):
                raise ValueError(
                    "partial sections require executed and applicable unavailable or failed evidence"
                )
        elif self.state == "unavailable":
            if has_executed or not has_applicable_unavailable or has_failed:
                raise ValueError(
                    "unavailable sections require non-failed unavailable evidence and no execution"
                )
        elif self.state == "failed":
            if has_executed or not has_failed:
                raise ValueError("failed sections require failed evidence and no execution")
        elif self.state == "stale":
            if not self.stale_on_failure or not has_executed or not self.warnings:
                raise ValueError(
                    "stale sections require prior executed evidence, stale_on_failure, and warning"
                )
        if self.state != "stale" and self.stale_on_failure:
            raise ValueError("stale_on_failure is reserved for stale section state")
        return self


class ReportPredictorExecutionV2(_ReportV2Model):
    predictor_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )
    applicability: CapabilityApplicabilityV2
    state: ReportPredictorStateV2
    source_snapshot_id: str = Field(min_length=1, max_length=128)
    calibration_id: str | None = Field(default=None, min_length=1, max_length=128)
    execution_disclosure: CapabilityExecutionDisclosureV2
    stale_on_failure: bool = False
    warnings: list[ReportBoundedText] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def _validate_predictor_truth(self):
        if self.applicability != self.execution_disclosure.applicability:
            raise ValueError("predictor applicability must match its execution disclosure")
        if (self.state == "not_applicable") != (self.applicability == "not_applicable"):
            raise ValueError(
                "not_applicable predictor state must exactly match predictor applicability"
            )
        if (self.state == "failed") != (self.execution_disclosure.validation_status == "failed"):
            raise ValueError("failed predictor state requires failed validation state")
        if (
            self.state == "executed"
            and self.execution_disclosure.execution not in _EXECUTED_CAPABILITY_STATES
        ):
            raise ValueError("executed predictors require executed disclosure")
        if self.state in {"unavailable", "failed", "not_applicable"} and (
            self.execution_disclosure.execution != "unavailable"
        ):
            raise ValueError("non-executed predictors require unavailable disclosure")
        if self.state == "unavailable" and self.applicability == "not_applicable":
            raise ValueError("unavailable predictors cannot masquerade as not_applicable")
        if self.state == "stale":
            if not self.stale_on_failure:
                raise ValueError("stale predictors must declare stale_on_failure")
            if self.execution_disclosure.execution not in _EXECUTED_CAPABILITY_STATES:
                raise ValueError("stale predictors require previously executed evidence")
            if not self.warnings:
                raise ValueError("stale predictors require a bounded freshness warning")
        elif self.stale_on_failure:
            raise ValueError("stale_on_failure is reserved for stale predictor state")
        return self


class ReportExecutionStateV2(_ReportV2Model):
    schema_version: Literal["report_execution_state.v2"] = "report_execution_state.v2"
    coverage: ReportCoverageV2
    canonical_variant: CanonicalVariantRefV1
    source_snapshot_id: str = Field(min_length=1, max_length=128)
    sections: list[ReportSectionExecutionV2] = Field(default_factory=list, max_length=32)
    predictors: list[ReportPredictorExecutionV2] = Field(default_factory=list, max_length=128)

    @model_validator(mode="after")
    def _validate_unique_states(self):
        if self.canonical_variant.resolution_status != "resolved":
            raise ValueError("actionable report execution state requires a resolved variant")
        if not self.canonical_variant.source_support:
            raise ValueError("report canonical variant requires source-backed support")
        section_ids = [section.section_id for section in self.sections]
        predictor_ids = [predictor.predictor_id for predictor in self.predictors]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("report sections must have one canonical state")
        if len(predictor_ids) != len(set(predictor_ids)):
            raise ValueError("report predictors must have one canonical state")
        all_section_ids = set(get_args(ReportSectionIdV2))
        if self.coverage == "complete" and set(section_ids) != all_section_ids:
            raise ValueError("complete reports require every report section exactly once")
        if self.coverage == "partial" and set(section_ids) == all_section_ids:
            raise ValueError("partial report coverage cannot contain the complete section set")
        if any(section.source_snapshot_id != self.source_snapshot_id for section in self.sections):
            raise ValueError("report section snapshots must match the report snapshot")
        if any(
            predictor.source_snapshot_id != self.source_snapshot_id for predictor in self.predictors
        ):
            raise ValueError("report predictor snapshots must match the report snapshot")
        return self


class ExtractionIssue(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"


class ExtractedVariant(BaseModel):
    gene: str
    transcript_hgvs: str
    protein_change: str
    genomic_hg38: str
    variation_type: str
    consequence: str


class ExtractedCase(BaseModel):
    case_label: str
    report_title: str
    patient_context: str | None = None
    clinical_findings: str | None = None
    summary: str
    genome_build: str = "GRCh38"
    variants: list[ExtractedVariant] = Field(default_factory=list)
    issues: list[ExtractionIssue] = Field(default_factory=list)


class UploadedReport(BaseModel):
    report_id: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    report_kind: ReportKind = "test"
    source_pdf_path: str
    extraction_status: ExtractionStatus
    extracted_case: ExtractedCase
    raw_extracted_text: str | None = None
    extraction_warnings: list[str] = Field(default_factory=list)


class ReportUploadResponse(BaseModel):
    report: UploadedReport
    execution_state_v2: ReportExecutionStateV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
