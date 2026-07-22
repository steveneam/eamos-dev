from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Annotated, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.run import ClassificationTier, VariantReportCallCards
from app.schemas.source_disclosure import SourceDisclosure

VariantResolutionStatusV1 = Literal["resolved", "ambiguous", "unresolved"]
WorkflowOriginSurfaceV1 = Literal["report", "paper", "batch", "workbench", "library", "search"]
WorkflowActiveToolV1 = Literal["viewer", "primer", "crispr", "align"]
SelectionStrandV1 = Literal["+", "-"]
SelectionOrientationV1 = Literal["genomic_forward", "genomic_reverse", "transcript"]
SequenceBasisV1 = Literal["reference", "variant", "edited"]
SelectionOverlapV1 = Literal["utr5", "utr3", "cds", "exon", "intron"]
ProcessingExecutionV1 = Literal["browser", "eamos_backend", "external_provider"]
ProcessingInputClassV1 = Literal[
    "variant_id", "sequence", "vcf", "paper_text", "pdf", "trace", "notes"
]
ProcessingRetentionV1 = Literal["none", "request_lifetime", "ttl", "account_saved"]
WorkflowRunKindV1 = Literal["batch", "paper", "workbench"]
WorkflowRunStatusV1 = Literal[
    "draft",
    "queued",
    "running",
    "completed",
    "partial",
    "failed",
    "cancelled",
    "expired",
]
WorkflowOwnerScopeV1 = Literal["account", "anonymous_session"]
WorkflowArtifactKindV1 = Literal[
    "report_tsv",
    "report_html",
    "batch_tsv",
    "paper_tsv",
    "fasta",
    "primer_tsv",
    "primer_fasta",
    "guide_tsv",
    "ssodn_txt",
    "alignment_tsv",
    "workspace_json",
]
WorkflowArtifactDownloadStateV1 = Literal["client_generated", "ready", "expired"]
RelatedVariantRelationshipV1 = Literal["nearby", "same_gene", "same_class", "same_condition"]
ConsequenceBucketV1 = Literal["lof", "missense", "noncoding", "synonymous"]
WorkbenchViewV1 = Literal["window", "locus"]
CompareViewV1 = Literal["cohort", "compare"]
WorkflowAsyncStateV1 = Literal[
    "idle",
    "validating",
    "auth_required",
    "consent_required",
    "queued",
    "running",
    "completed",
    "partial",
    "empty",
    "failed",
    "cancelled",
    "expired",
    "stale",
]

OpaqueId = Annotated[
    str,
    Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    ),
]
SafeKey = Annotated[
    str,
    Field(min_length=1, max_length=256, pattern=r"^[^\s\x00-\x1f\x7f]+$"),
]
ShortText = Annotated[str, Field(min_length=1, max_length=256)]
LabelText = Annotated[str, Field(min_length=1, max_length=160)]
WarningText = Annotated[str, Field(min_length=1, max_length=512)]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ContextDigest = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[^\s\x00-\x1f\x7f]+$"),
]

_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._~-]{0,127}$")
_SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,179}$")
_MEDIA_TYPE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*$")
_PRODUCT_QUERY_FIELDS: dict[str, frozenset[str]] = {
    "/report": frozenset({"gene", "cdna", "transcript", "from"}),
    "/workbench": frozenset({"gene", "cdna", "transcript", "tool", "view", "context_id"}),
    "/compare": frozenset({"run_id", "context_id", "view"}),
    "/paper": frozenset({"run_id", "context_id"}),
}
_ORIGIN_SURFACES = frozenset({"report", "paper", "batch", "workbench", "library", "search"})
_WORKBENCH_TOOLS = frozenset({"viewer", "primer", "crispr", "align"})
_WORKBENCH_VIEWS = frozenset({"window", "locus"})
_COMPARE_VIEWS = frozenset({"cohort", "compare"})


class _WorkflowContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_default=True,
    )


def _utc_datetime(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} requires a timezone and must resolve to UTC")
    return value.astimezone(UTC)


def _validate_sha256(value: str) -> str:
    normalized = value.lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError("value must be a 64-character SHA-256 hex digest")
    return normalized


def _validate_opaque_id(value: str, *, field_name: str) -> str:
    if not _OPAQUE_ID_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be an opaque identifier")
    return value


def _validate_product_href(value: str, *, expected_path: str | None = None) -> str:
    if len(value) > 1024 or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("return_to must be a bounded control-free product path")
    if "\\" in value:
        raise ValueError("return_to must use URL path separators")

    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError("return_to must be a fragment-free same-origin product path")
    if expected_path is not None and parsed.path != expected_path:
        raise ValueError(f"href must use the canonical {expected_path} route")
    allowed_fields = _PRODUCT_QUERY_FIELDS.get(parsed.path)
    if allowed_fields is None:
        raise ValueError("return_to must use the frozen product URL grammar")

    try:
        pairs = parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=16)
    except ValueError as exc:
        raise ValueError("return_to query is invalid or too large") from exc
    keys = [key for key, _value in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("return_to query fields must not repeat")
    unexpected = set(keys) - allowed_fields
    if unexpected:
        raise ValueError(f"return_to contains unsupported query fields: {sorted(unexpected)}")

    values = dict(pairs)
    if any(not value for value in values.values()):
        raise ValueError("return_to query values must not be blank")
    if any(
        any(ord(char) < 32 or ord(char) == 127 for char in key_or_value)
        for pair in pairs
        for key_or_value in pair
    ):
        raise ValueError("return_to decoded query fields must be control-free")
    if "from" in values and values["from"] not in _ORIGIN_SURFACES:
        raise ValueError("return_to from value is not a workflow surface")
    if "tool" in values and values["tool"] not in _WORKBENCH_TOOLS:
        raise ValueError("return_to tool value is not supported")
    if parsed.path == "/workbench" and "view" in values and values["view"] not in _WORKBENCH_VIEWS:
        raise ValueError("return_to workbench view is not supported")
    if parsed.path == "/compare" and "view" in values and values["view"] not in _COMPARE_VIEWS:
        raise ValueError("return_to compare view is not supported")
    for id_field in ("run_id", "context_id"):
        if id_field in values:
            _validate_opaque_id(values[id_field], field_name=id_field)
    return value


class CanonicalVariantRefV1(_WorkflowContractModel):
    schema_version: Literal["canonical_variant_ref.v1"]
    gene: Annotated[
        str,
        Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9.-]*$"),
    ]
    cdna: SafeKey
    transcript: ShortText | None
    protein_hgvs: ShortText | None
    genomic_hg38: ShortText | None
    variant_key: SafeKey
    species: Literal["human"]
    genome_build: Literal["GRCh38"]
    resolution_status: VariantResolutionStatusV1
    source_support: list[ShortText] = Field(max_length=64)
    warnings: list[WarningText] = Field(max_length=64)

    @field_validator("gene")
    @classmethod
    def _normalize_gene(cls, value: str) -> str:
        return value.upper()


class SelectionRangeV1(_WorkflowContractModel):
    schema_version: Literal["selection_range.v1"]
    variant_key: SafeKey
    transcript: ShortText
    genome_build: Literal["GRCh38"]
    chrom: Annotated[str, Field(min_length=1, max_length=32)]
    genomic_start: int = Field(ge=1)
    genomic_end: int = Field(ge=1)
    strand: SelectionStrandV1
    orientation: SelectionOrientationV1
    sequence_basis: SequenceBasisV1
    edit_revision: int = Field(ge=0)
    sequence_sha256: Sha256Hex
    cdna_start: int | None
    cdna_end: int | None
    cds_start: int | None
    cds_end: int | None
    protein_start: int | None
    protein_end: int | None
    overlaps: list[SelectionOverlapV1] = Field(min_length=1, max_length=5)

    @field_validator("sequence_sha256", mode="before")
    @classmethod
    def _normalize_sha256(cls, value):
        if not isinstance(value, str):
            return value
        return _validate_sha256(value)

    @model_validator(mode="after")
    def _validate_interval(self):
        if self.genomic_start > self.genomic_end:
            raise ValueError("genomic_start must be less than or equal to genomic_end")
        for start_name, end_name in (
            ("cdna_start", "cdna_end"),
            ("cds_start", "cds_end"),
            ("protein_start", "protein_end"),
        ):
            start = getattr(self, start_name)
            end = getattr(self, end_name)
            if (start is None) != (end is None):
                raise ValueError(f"{start_name} and {end_name} must both be null or both be set")
            if start is not None and end is not None and start > end:
                raise ValueError(f"{start_name} must be less than or equal to {end_name}")
        if self.sequence_basis == "edited" and self.edit_revision == 0:
            raise ValueError("edit_revision must be positive for edited sequence basis")
        if self.sequence_basis != "edited" and self.edit_revision != 0:
            raise ValueError("edit_revision must be zero unless sequence_basis is edited")
        if len(self.overlaps) != len(set(self.overlaps)):
            raise ValueError("overlaps must be deduplicated")
        return self


class WorkflowContextV1(_WorkflowContractModel):
    schema_version: Literal["workflow_context.v1"]
    context_id: OpaqueId | None
    variant: CanonicalVariantRefV1 | None
    origin_surface: WorkflowOriginSurfaceV1
    return_to: Annotated[str, Field(min_length=1, max_length=1024)] | None
    batch_run_id: OpaqueId | None
    paper_run_id: OpaqueId | None
    workspace_id: OpaqueId | None
    active_tool: WorkflowActiveToolV1 | None
    selection: SelectionRangeV1 | None
    created_at: datetime
    expires_at: datetime | None

    @field_validator("return_to")
    @classmethod
    def _validate_return_to(cls, value: str | None) -> str | None:
        return _validate_product_href(value) if value is not None else None

    @field_validator("created_at", "expires_at")
    @classmethod
    def _normalize_timestamps(cls, value: datetime | None, info):
        if value is None:
            return None
        return _utc_datetime(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _validate_context_binding(self):
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        if self.active_tool in {"primer", "crispr", "align"}:
            if self.variant is None or self.variant.resolution_status != "resolved":
                raise ValueError("molecular-design tools require a resolved canonical variant")
        if self.selection is not None:
            if self.variant is None or self.variant.resolution_status != "resolved":
                raise ValueError("selection requires a resolved canonical variant")
            if self.selection.variant_key != self.variant.variant_key:
                raise ValueError("selection variant_key must match the context variant_key")
            if self.selection.genome_build != self.variant.genome_build:
                raise ValueError("selection genome_build must match the context variant")
            if (
                self.variant.transcript is None
                or self.selection.transcript != self.variant.transcript
            ):
                raise ValueError("selection transcript must match the context variant transcript")
        return self


def build_workbench_design_context_digest_v1(
    variant: CanonicalVariantRefV1,
    selection: SelectionRangeV1,
) -> str:
    payload = {
        "schema_version": "workbench_design_context.v1",
        "selection": selection.model_dump(mode="json"),
        "variant": variant.model_dump(mode="json"),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class WorkbenchDesignContextV1(_WorkflowContractModel):
    schema_version: Literal["workbench_design_context.v1"]
    variant: CanonicalVariantRefV1
    selection: SelectionRangeV1
    context_digest: Sha256Hex

    @field_validator("context_digest", mode="before")
    @classmethod
    def _normalize_context_digest(cls, value):
        if not isinstance(value, str):
            return value
        return _validate_sha256(value)

    @model_validator(mode="after")
    def _validate_design_binding(self):
        if self.variant.resolution_status != "resolved":
            raise ValueError("Workbench design context requires a resolved canonical variant")
        if self.selection.variant_key != self.variant.variant_key:
            raise ValueError("selection variant_key must match the design-context variant_key")
        if self.selection.genome_build != self.variant.genome_build:
            raise ValueError("selection genome_build must match the design-context variant")
        if self.variant.transcript is None or self.selection.transcript != self.variant.transcript:
            raise ValueError(
                "selection transcript must match the design-context variant transcript"
            )
        expected_digest = build_workbench_design_context_digest_v1(
            self.variant,
            self.selection,
        )
        if self.context_digest != expected_digest:
            raise ValueError("context_digest must match the canonical variant and selection")
        return self


class ProcessingDisclosureV1(_WorkflowContractModel):
    execution: ProcessingExecutionV1
    provider_id: OpaqueId
    provider_label: LabelText
    input_classes: list[ProcessingInputClassV1] = Field(min_length=1, max_length=7)
    raw_input_persisted: bool
    retention: ProcessingRetentionV1
    expires_at: datetime | None
    user_deletable: bool
    consent_required: bool
    warnings: list[WarningText] = Field(max_length=64)

    @field_validator("expires_at")
    @classmethod
    def _normalize_expiry(cls, value: datetime | None):
        if value is None:
            return None
        return _utc_datetime(value, field_name="expires_at")

    @model_validator(mode="after")
    def _validate_processing_posture(self):
        if len(self.input_classes) != len(set(self.input_classes)):
            raise ValueError("input_classes must be deduplicated")
        if self.execution == "external_provider" and not self.consent_required:
            raise ValueError("consent_required must be true for external_provider execution")
        if self.retention == "ttl" and self.expires_at is None:
            raise ValueError("expires_at is required when retention is ttl")
        if self.retention == "none" and self.raw_input_persisted:
            raise ValueError("raw_input_persisted must be false when retention is none")
        return self


class WorkflowArtifactV1(_WorkflowContractModel):
    artifact_id: OpaqueId
    kind: WorkflowArtifactKindV1
    filename: Annotated[str, Field(min_length=1, max_length=180)]
    media_type: Annotated[str, Field(min_length=3, max_length=128)]
    generated_at: datetime
    source_run_id: OpaqueId | None
    context_digest: ContextDigest
    sha256: Sha256Hex
    download_state: WorkflowArtifactDownloadStateV1

    @field_validator("filename")
    @classmethod
    def _validate_filename(cls, value: str) -> str:
        if not _SAFE_FILENAME_RE.fullmatch(value) or value in {".", ".."}:
            raise ValueError("filename must be a safe basename without path separators")
        return value

    @field_validator("media_type")
    @classmethod
    def _validate_media_type(cls, value: str) -> str:
        if not _MEDIA_TYPE_RE.fullmatch(value):
            raise ValueError("media_type must be a bounded type/subtype value")
        return value.lower()

    @field_validator("sha256", mode="before")
    @classmethod
    def _normalize_sha256(cls, value):
        if not isinstance(value, str):
            return value
        return _validate_sha256(value)

    @field_validator("generated_at")
    @classmethod
    def _normalize_generated_at(cls, value: datetime):
        return _utc_datetime(value, field_name="generated_at")


class WorkflowRunV1(_WorkflowContractModel):
    schema_version: Literal["workflow_run.v1"]
    run_id: OpaqueId
    kind: WorkflowRunKindV1
    status: WorkflowRunStatusV1
    owner_scope: WorkflowOwnerScopeV1
    context: WorkflowContextV1
    done: int = Field(ge=0)
    total: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    warnings: list[WarningText] = Field(max_length=64)
    source_disclosures: list[SourceDisclosure] = Field(max_length=32)
    processing_disclosure: ProcessingDisclosureV1 | None
    artifacts: list[WorkflowArtifactV1] = Field(max_length=64)

    @field_validator("created_at", "updated_at", "expires_at")
    @classmethod
    def _normalize_timestamps(cls, value: datetime | None, info):
        if value is None:
            return None
        return _utc_datetime(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _validate_run_integrity(self):
        if self.done > self.total:
            raise ValueError("done must be less than or equal to total")
        if self.status == "completed" and self.done != self.total:
            raise ValueError("completed runs require done to equal total")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        artifact_ids = [artifact.artifact_id for artifact in self.artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("artifact_id values must be unique within a run")
        for artifact in self.artifacts:
            if artifact.source_run_id is not None and artifact.source_run_id != self.run_id:
                raise ValueError("artifact source_run_id must match run_id")
        return self


class RelatedVariantItemV1(_WorkflowContractModel):
    variant: CanonicalVariantRefV1
    relationship: RelatedVariantRelationshipV1
    distance_bp: int | None
    classification: ClassificationTier | None
    evidence_axis_summary: VariantReportCallCards | None
    source_disclosure: SourceDisclosure
    report_href: Annotated[str, Field(min_length=1, max_length=1024)]

    @field_validator("report_href")
    @classmethod
    def _validate_report_href(cls, value: str) -> str:
        return _validate_product_href(value, expected_path="/report")

    @model_validator(mode="after")
    def _validate_report_target(self):
        query = dict(parse_qsl(urlsplit(self.report_href).query, keep_blank_values=True))
        if query.get("gene") != self.variant.gene or query.get("cdna") != self.variant.cdna:
            raise ValueError("report_href must target the item's canonical gene and cdna")
        if query.get("transcript") != self.variant.transcript:
            raise ValueError("report_href transcript must match the canonical variant")
        return self


class RelatedVariantGroupV1(_WorkflowContractModel):
    items: list[RelatedVariantItemV1] = Field(max_length=500)
    warnings: list[WarningText] = Field(max_length=64)

    @model_validator(mode="after")
    def _validate_deduplicated_items(self):
        keys = [item.variant.variant_key for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("items must be deduplicated by canonical variant_key")
        return self


class CuratedVariantPageV1(_WorkflowContractModel):
    gene: Annotated[
        str,
        Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9.-]*$"),
    ]
    classification_filter: ClassificationTier | None
    consequence_filter: ConsequenceBucketV1 | None
    items: list[CanonicalVariantRefV1] = Field(max_length=500)
    next_cursor: OpaqueId | None
    total: int = Field(ge=0)
    source_disclosure: SourceDisclosure
    warnings: list[WarningText] = Field(max_length=64)

    @field_validator("gene")
    @classmethod
    def _normalize_gene(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def _validate_page(self):
        keys = [item.variant_key for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("items must be deduplicated by canonical variant_key")
        if any(item.gene != self.gene for item in self.items):
            raise ValueError("all curated page items must match the page gene")
        if self.total < len(self.items):
            raise ValueError("total must be at least the number of page items")
        return self


def build_report_href_v1(
    variant: CanonicalVariantRefV1,
    *,
    from_surface: WorkflowOriginSurfaceV1 | None = None,
) -> str:
    params: list[tuple[str, str]] = [("gene", variant.gene), ("cdna", variant.cdna)]
    if variant.transcript is not None:
        params.append(("transcript", variant.transcript))
    if from_surface is not None:
        if from_surface not in _ORIGIN_SURFACES:
            raise ValueError("from_surface is not a workflow surface")
        params.append(("from", from_surface))
    return f"/report?{urlencode(params)}"


def build_workbench_href_v1(
    variant: CanonicalVariantRefV1,
    *,
    tool: WorkflowActiveToolV1 | None = None,
    view: WorkbenchViewV1 | None = None,
    context_id: str | None = None,
) -> str:
    if tool is not None and tool not in _WORKBENCH_TOOLS:
        raise ValueError("tool is not supported")
    if view is not None and view not in _WORKBENCH_VIEWS:
        raise ValueError("view is not supported")
    if tool in {"primer", "crispr", "align"} and variant.resolution_status != "resolved":
        raise ValueError("molecular-design tools require a resolved canonical variant")
    params: list[tuple[str, str]] = [("gene", variant.gene), ("cdna", variant.cdna)]
    if variant.transcript is not None:
        params.append(("transcript", variant.transcript))
    if tool is not None:
        params.append(("tool", tool))
    if view is not None:
        params.append(("view", view))
    if context_id is not None:
        params.append(("context_id", _validate_opaque_id(context_id, field_name="context_id")))
    return f"/workbench?{urlencode(params)}"


def build_compare_href_v1(
    *,
    run_id: str | None = None,
    context_id: str | None = None,
    view: CompareViewV1 | None = None,
) -> str:
    if run_id is None and context_id is None:
        raise ValueError("run_id or context_id is required")
    if view is not None and view not in _COMPARE_VIEWS:
        raise ValueError("view is not supported")
    params: list[tuple[str, str]] = []
    if run_id is not None:
        params.append(("run_id", _validate_opaque_id(run_id, field_name="run_id")))
    if context_id is not None:
        params.append(("context_id", _validate_opaque_id(context_id, field_name="context_id")))
    if view is not None:
        params.append(("view", view))
    return f"/compare?{urlencode(params)}"


def build_paper_href_v1(
    *,
    run_id: str | None = None,
    context_id: str | None = None,
) -> str:
    if run_id is None and context_id is None:
        raise ValueError("run_id or context_id is required")
    params: list[tuple[str, str]] = []
    if run_id is not None:
        params.append(("run_id", _validate_opaque_id(run_id, field_name="run_id")))
    if context_id is not None:
        params.append(("context_id", _validate_opaque_id(context_id, field_name="context_id")))
    return f"/paper?{urlencode(params)}"
