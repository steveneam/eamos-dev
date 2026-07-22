from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.source_disclosure import SourceDisclosure
from app.schemas.workflow import ProcessingDisclosureV1

CapabilityExecutionV2 = Literal[
    "eamos_local",
    "mounted_artifact",
    "external_provider",
    "fixture",
    "unavailable",
]
CapabilitySourceStatusV2 = Literal[
    "source_backed",
    "not_required",
    "not_found",
    "not_applicable",
    "unavailable",
    "fixture",
]
CapabilityApplicabilityV2 = Literal["applicable", "not_applicable", "unknown"]
CapabilityValidationStatusV2 = Literal[
    "validated",
    "fixture_only",
    "unvalidated",
    "failed",
    "not_applicable",
]
CapabilityRetentionV2 = Literal["none", "request_lifetime", "ttl", "account_saved"]

BoundedText = Annotated[str, Field(min_length=1, max_length=512)]
OpaqueCapabilityId = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$"),
]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class _CapabilityContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_default=True,
    )


class CapabilityExecutionDisclosureV2(_CapabilityContractModel):
    """One canonical truth statement for an executed or unavailable capability.

    The contract deliberately contains identifiers, digests, and bounded messages,
    never raw sequence, VCF rows/genotypes, trace bytes, document text, or notes.
    """

    schema_version: Literal["capability_execution.v2"] = "capability_execution.v2"
    capability_id: OpaqueCapabilityId
    claim: BoundedText
    execution: CapabilityExecutionV2
    algorithm_id: OpaqueCapabilityId | None = None
    algorithm_version: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    provider_id: OpaqueCapabilityId | None = None
    provider_version: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    input_scope: Annotated[str, Field(min_length=1, max_length=128)]
    source_status: CapabilitySourceStatusV2
    source_record_ids: list[OpaqueCapabilityId] = Field(default_factory=list, max_length=128)
    source_release: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    materialized_at: datetime | None = None
    artifact_manifest_id: OpaqueCapabilityId | None = None
    artifact_sha256: Sha256Hex | None = None
    applicability: CapabilityApplicabilityV2
    validation_status: CapabilityValidationStatusV2
    validation_matrix_id: OpaqueCapabilityId | None = None
    retention: CapabilityRetentionV2
    retention_expires_at: datetime | None = None
    consent_required: bool
    warnings: list[BoundedText] = Field(default_factory=list, max_length=64)
    requirements: list[BoundedText] = Field(default_factory=list, max_length=64)

    @field_validator("artifact_sha256", mode="before")
    @classmethod
    def _normalize_sha256(cls, value):
        return value.lower() if isinstance(value, str) else value

    @field_validator("materialized_at", "retention_expires_at")
    @classmethod
    def _normalize_timestamps(cls, value: datetime | None, info):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{info.field_name} requires a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _validate_truth_posture(self):
        if len(self.source_record_ids) != len(set(self.source_record_ids)):
            raise ValueError("source_record_ids must be deduplicated")
        if self.execution in {"eamos_local", "mounted_artifact"} and self.algorithm_id is None:
            raise ValueError("local and mounted execution require algorithm_id")
        if self.execution == "external_provider":
            if self.provider_id is None:
                raise ValueError("external_provider execution requires provider_id")
            if not self.consent_required:
                raise ValueError("external_provider execution requires explicit consent")
        elif self.consent_required:
            raise ValueError("consent_required is reserved for external_provider execution")
        if self.execution == "mounted_artifact" and (
            self.artifact_manifest_id is None or self.artifact_sha256 is None
        ):
            raise ValueError("mounted_artifact execution requires an immutable artifact identity")
        if self.execution == "fixture" and self.source_status != "fixture":
            raise ValueError("fixture execution requires fixture source_status")
        if self.source_status == "fixture" and self.execution != "fixture":
            raise ValueError("fixture source_status is reserved for fixture execution")
        if self.execution == "unavailable" and self.source_status not in {
            "not_found",
            "not_applicable",
            "unavailable",
        }:
            raise ValueError("unavailable execution requires a non-success source_status")
        if self.execution == "unavailable":
            if self.validation_status == "validated":
                raise ValueError("unavailable capabilities cannot claim validated execution")
            if self.applicability != "not_applicable" and not self.requirements:
                raise ValueError(
                    "applicable unavailable capabilities require a concrete requirement"
                )
        if self.execution == "fixture" and self.validation_status != "fixture_only":
            raise ValueError("fixture execution requires fixture_only validation")
        if self.applicability == "not_applicable":
            if self.execution != "unavailable" or self.source_status != "not_applicable":
                raise ValueError("not_applicable capabilities must use the unavailable truth state")
            if self.validation_status != "not_applicable":
                raise ValueError("not_applicable capabilities require not_applicable validation")
        if self.retention == "ttl" and self.retention_expires_at is None:
            raise ValueError("ttl retention requires retention_expires_at")
        if self.retention != "ttl" and self.retention_expires_at is not None:
            raise ValueError("retention_expires_at is valid only for ttl retention")
        return self

    @classmethod
    def from_legacy(
        cls,
        *,
        capability_id: str,
        claim: str,
        algorithm_id: str,
        algorithm_version: str | None,
        input_scope: str,
        source: SourceDisclosure,
        processing: ProcessingDisclosureV1,
        validation_status: CapabilityValidationStatusV2 = "unvalidated",
        validation_matrix_id: str | None = None,
    ) -> "CapabilityExecutionDisclosureV2":
        """Compatibility shim for V1 disclosure producers.

        Remove after all four live-product surfaces emit V2 directly. Ambiguous
        legacy fallback/gated states intentionally bridge to ``unavailable`` so
        the migration cannot upgrade a weak legacy status into executed output.
        """

        execution_by_v1 = {
            "browser": "eamos_local",
            "eamos_backend": "eamos_local",
            "external_provider": "external_provider",
        }
        source_status_by_v1 = {
            "source_backed": "source_backed",
            "local_provider": "not_required",
            "fallback": "unavailable",
            "fixture": "fixture",
            "gated": "unavailable",
            "unavailable": "unavailable",
        }
        execution: CapabilityExecutionV2 = execution_by_v1[processing.execution]
        source_status: CapabilitySourceStatusV2 = source_status_by_v1[source.source_status]
        warnings = [*source.warnings, *processing.warnings]
        requirements = list(source.requirements)
        if source.source_status in {"fallback", "gated", "unavailable"}:
            execution = "unavailable"
            warnings.append(f"legacy_source_status:{source.source_status}")
            if not requirements:
                requirements.append(f"replace_legacy_{source.source_status}_path")
        elif source.source_status == "fixture":
            execution = "fixture"
            validation_status = "fixture_only"

        return cls(
            capability_id=capability_id,
            claim=claim,
            execution=execution,
            algorithm_id=algorithm_id,
            algorithm_version=algorithm_version,
            provider_id=source.provider_id,
            provider_version=source.source_version,
            input_scope=input_scope,
            source_status=source_status,
            source_release=source.source_version,
            applicability="applicable",
            validation_status=validation_status,
            validation_matrix_id=validation_matrix_id,
            retention=processing.retention,
            retention_expires_at=processing.expires_at,
            consent_required=(
                processing.consent_required if execution == "external_provider" else False
            ),
            warnings=warnings,
            requirements=requirements,
        )
