from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.capabilities import CapabilityExecutionDisclosureV2

BoundedIdentifier = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._~:-]*$"),
]
BoundedText = Annotated[str, Field(min_length=1, max_length=512)]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

ComponentKind = Literal["package", "binary", "material", "service", "isolation"]
ComponentStatus = Literal["ready", "unavailable", "disabled", "invalid"]
LaunchPosture = Literal["enabled", "gated", "disabled"]
ProbeStatus = Literal["passed", "failed", "unavailable", "not_run"]
LicensePosture = Literal[
    "permissive",
    "copyleft_review_required",
    "terms_review_required",
    "not_applicable",
]


class _RuntimeModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_default=True,
    )


class RuntimeProbeV1(_RuntimeModel):
    probe_id: BoundedIdentifier
    status: ProbeStatus
    executed: bool
    elapsed_ms: float = Field(ge=0, le=120_000)
    validation_matrix_id: BoundedIdentifier | None = None
    warnings: list[BoundedText] = Field(default_factory=list, max_length=32)
    requirements: list[BoundedText] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def _validate_execution_truth(self):
        if self.executed and self.status == "not_run":
            raise ValueError("an executed probe cannot have not_run status")
        if not self.executed and self.status in {"passed", "failed"}:
            raise ValueError("a non-executed probe cannot claim an execution result")
        if self.status in {"failed", "unavailable"} and not self.requirements:
            raise ValueError("failed and unavailable probes require remediation")
        return self


class RuntimeComponentV1(_RuntimeModel):
    component_id: BoundedIdentifier
    display_name: BoundedText
    kind: ComponentKind
    status: ComponentStatus
    required_at_startup: bool
    launch_posture: LaunchPosture
    installed_version: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    pinned_version: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    license_spdx: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    license_posture: LicensePosture
    sbom_ref: Annotated[str, Field(min_length=1, max_length=256)] | None = None
    notice_ids: list[BoundedIdentifier] = Field(default_factory=list, max_length=32)
    capability_ids: list[BoundedIdentifier] = Field(default_factory=list, max_length=64)
    artifact_manifest_id: BoundedIdentifier | None = None
    artifact_sha256: Sha256Hex | None = None
    probe: RuntimeProbeV1
    warnings: list[BoundedText] = Field(default_factory=list, max_length=32)
    requirements: list[BoundedText] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def _validate_component_truth(self):
        if len(self.capability_ids) != len(set(self.capability_ids)):
            raise ValueError("capability_ids must be deduplicated")
        if len(self.notice_ids) != len(set(self.notice_ids)):
            raise ValueError("notice_ids must be deduplicated")
        if self.status == "ready" and self.probe.status != "passed":
            raise ValueError("ready components require a passed probe")
        if self.status in {"unavailable", "invalid"} and not self.requirements:
            raise ValueError("unavailable and invalid components require remediation")
        if self.kind == "material" and self.status == "ready":
            if self.artifact_manifest_id is None or self.artifact_sha256 is None:
                raise ValueError("ready materials require immutable artifact identity")
        return self


class RuntimeStartupMetricsV1(_RuntimeModel):
    composition_elapsed_ms: float = Field(ge=0, le=120_000)
    process_peak_rss_bytes: int = Field(ge=0)
    container_image_size_bytes: int | None = Field(default=None, ge=0)
    runtime_payload_size_bytes: int | None = Field(default=None, ge=0)
    measurement_scope: Literal["process", "container_build", "deployment"] = "process"
    requirements: list[BoundedText] = Field(default_factory=list, max_length=16)


class RuntimePolicyV1(_RuntimeModel):
    startup_downloads_allowed: Literal[False] = False
    request_time_installs_allowed: Literal[False] = False
    host_binary_autodiscovery_allowed: Literal[False] = False
    raw_paths_emitted: Literal[False] = False
    secret_values_emitted: Literal[False] = False


class RuntimeCapabilityRegistryV1(_RuntimeModel):
    schema_version: Literal["runtime_capability_registry.v1"] = "runtime_capability_registry.v1"
    status: Literal["ready", "degraded"]
    core_services_ready: bool
    startup_metrics: RuntimeStartupMetricsV1
    policy: RuntimePolicyV1 = Field(default_factory=RuntimePolicyV1)
    components: list[RuntimeComponentV1] = Field(min_length=1, max_length=128)
    capabilities: list[CapabilityExecutionDisclosureV2] = Field(
        default_factory=list,
        max_length=128,
    )

    @model_validator(mode="after")
    def _validate_registry(self):
        component_ids = [item.component_id for item in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("runtime component IDs must be unique")
        capability_ids = [item.capability_id for item in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("runtime capability IDs must be unique")
        if self.status == "ready" and any(
            item.status != "ready" for item in self.components if item.required_at_startup
        ):
            raise ValueError("ready registry cannot contain an unavailable required component")
        return self
