from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.capabilities import CapabilityExecutionDisclosureV2
from app.schemas.lookup import SearchInputCandidate, SearchInputSourceInputs
from app.schemas.workflow import CanonicalVariantRefV1

VariantLevel = Literal[
    "cdna",
    "genomic",
    "rna",
    "mitochondrial",
    "protein",
    "rsid",
    "legacy",
    "unknown",
]
VariantContext = Literal[
    "clinical_allele",
    "case_or_proband",
    "family_segregation",
    "experimental_construct",
    "engineered_rescue",
    "comparator_or_background",
    "bibliography_only",
    "ambiguous",
    "unknown",
]
PaperDocumentRoleV2 = Literal["main", "supplement"]
PaperDocumentKindV2 = Literal["pdf", "text", "csv", "xlsx"]
PaperExtractionQualityV2 = Literal["good", "degraded", "garbled", "image_only", "empty"]
PaperExtractionLayerV2 = Literal["l1_structured", "l2_recovery", "l3_inventory"]
PaperResolutionStatusV2 = Literal["resolved", "ambiguous", "unresolved", "excluded"]
PaperAdjudicationRecommendationV2 = Literal["confirm", "reject", "needs_review"]
PaperBoundedText = Annotated[str, Field(min_length=1, max_length=512)]
PaperShortText = Annotated[str, Field(min_length=1, max_length=160)]
PaperOpaqueId = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$"),
]


class _PaperV2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_default=True)


class PaperDocumentUploadV2(_PaperV2Model):
    """Request-only owner-bound handle. This type is never nested in an output."""

    document_id: PaperOpaqueId
    role: PaperDocumentRoleV2
    kind: PaperDocumentKindV2
    upload_ref: str = Field(
        min_length=1,
        max_length=256,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )
    filename: str = Field(
        min_length=1,
        max_length=180,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    media_type: str = Field(min_length=3, max_length=128)
    size_bytes: int = Field(ge=1, le=50_000_000)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("sha256", mode="before")
    @classmethod
    def _normalize_sha256(cls, value):
        return value.lower() if isinstance(value, str) else value


class PaperBibliographicMetadataV2(_PaperV2Model):
    title: PaperBoundedText | None = None
    authors: list[PaperShortText] = Field(default_factory=list, max_length=128)
    year: int | None = Field(default=None, ge=1400, le=3000)
    journal: PaperShortText | None = None
    doi: PaperShortText | None = None
    pmid: PaperOpaqueId | None = None
    provenance: list[PaperBoundedText] = Field(default_factory=list, max_length=32)


class PaperDocumentMetadataV2(_PaperV2Model):
    """Safe durable/output metadata: deliberately contains no upload handle or raw text."""

    document_id: PaperOpaqueId
    role: PaperDocumentRoleV2
    kind: PaperDocumentKindV2
    filename: str = Field(
        min_length=1,
        max_length=180,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    media_type: str = Field(min_length=3, max_length=128)
    size_bytes: int = Field(ge=1, le=50_000_000)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    page_count: int | None = Field(default=None, ge=1, le=100_000)
    extraction_engine: PaperOpaqueId
    extraction_engine_version: PaperShortText
    bibliographic_metadata: PaperBibliographicMetadataV2 | None = None
    warnings: list[PaperBoundedText] = Field(default_factory=list, max_length=32)

    @field_validator("sha256", mode="before")
    @classmethod
    def _normalize_sha256(cls, value):
        return value.lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _validate_document_metadata(self):
        if self.kind == "pdf" and self.page_count is None:
            raise ValueError("PDF metadata requires page_count")
        if self.kind != "pdf" and self.page_count is not None:
            raise ValueError("page_count is reserved for PDF documents")
        return self


class PaperDocumentBundleV2(_PaperV2Model):
    schema_version: Literal["paper_document_bundle.v2"] = "paper_document_bundle.v2"
    bundle_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )
    documents: list[PaperDocumentMetadataV2] = Field(min_length=1, max_length=32)
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("input_digest", mode="before")
    @classmethod
    def _normalize_digest(cls, value):
        return value.lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _validate_bundle(self):
        ids = [document.document_id for document in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("document_id values must be unique")
        if sum(document.role == "main" for document in self.documents) != 1:
            raise ValueError("document bundles require exactly one main document")
        return self


class PaperDocumentBundleRequestV2(_PaperV2Model):
    """Owner-bound upload refs only; ownership is resolved from the principal."""

    schema_version: Literal["paper_document_bundle_request.v2"] = "paper_document_bundle_request.v2"
    bundle_id: PaperOpaqueId
    documents: list[PaperDocumentUploadV2] = Field(min_length=1, max_length=32)
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    consent_to_external_processing: bool = False

    @model_validator(mode="after")
    def _validate_request_bundle(self):
        ids = [document.document_id for document in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("document_id values must be unique")
        if sum(document.role == "main" for document in self.documents) != 1:
            raise ValueError("document bundles require exactly one main document")
        return self


class PaperPageExtractionQualityV2(_PaperV2Model):
    document_id: PaperOpaqueId
    page_number: int = Field(ge=1, le=100_000)
    quality: PaperExtractionQualityV2
    extracted_character_count: int = Field(ge=0, le=5_000_000)
    replacement_character_ratio: float = Field(ge=0.0, le=1.0)
    warnings: list[PaperBoundedText] = Field(default_factory=list, max_length=32)


class PaperEvidenceSpanV2(_PaperV2Model):
    document_id: PaperOpaqueId
    page_number: int = Field(ge=1, le=100_000)
    section: PaperShortText
    start_character: int = Field(ge=0, le=5_000_000)
    end_character: int = Field(ge=1, le=5_000_000)
    exact_text: str = Field(min_length=1, max_length=256)
    bounded_quote: str = Field(min_length=1, max_length=400)

    @model_validator(mode="after")
    def _validate_span(self):
        if self.start_character >= self.end_character:
            raise ValueError("evidence span must use an ordered half-open interval")
        if self.end_character - self.start_character != len(self.exact_text):
            raise ValueError("evidence span length must match exact_text")
        if self.exact_text not in self.bounded_quote:
            raise ValueError("bounded_quote must contain exact_text")
        return self


class PaperVariantMentionV2(_PaperV2Model):
    mention_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )
    notation_type: VariantLevel
    biological_context: VariantContext
    extraction_layer: PaperExtractionLayerV2
    confidence: float = Field(ge=0.0, le=1.0)
    span: PaperEvidenceSpanV2
    gene_evidence: list[PaperShortText] = Field(default_factory=list, max_length=16)
    transcript_evidence: list[PaperShortText] = Field(default_factory=list, max_length=16)
    warnings: list[PaperBoundedText] = Field(default_factory=list, max_length=32)


class PaperMentionResolutionV2(_PaperV2Model):
    mention_id: PaperOpaqueId
    status: PaperResolutionStatusV2
    canonical_variant: CanonicalVariantRefV1 | None = None
    candidate_ids: list[PaperOpaqueId] = Field(default_factory=list, max_length=32)
    execution_disclosure: CapabilityExecutionDisclosureV2
    warnings: list[PaperBoundedText] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def _validate_resolution(self):
        if len(self.candidate_ids) != len(set(self.candidate_ids)):
            raise ValueError("candidate_ids must be deduplicated")
        if self.status == "resolved":
            if (
                self.canonical_variant is None
                or self.canonical_variant.resolution_status != "resolved"
            ):
                raise ValueError("resolved mentions require a resolved canonical variant")
            if len(self.candidate_ids) != 1:
                raise ValueError("resolved mentions require exactly one proven candidate")
            if not self.canonical_variant.source_support:
                raise ValueError("resolved mentions require source-backed canonical support")
            if self.execution_disclosure.execution not in {
                "eamos_local",
                "mounted_artifact",
                "external_provider",
            }:
                raise ValueError("resolved mentions require executed resolution")
            if (
                self.execution_disclosure.source_status != "source_backed"
                or not self.execution_disclosure.source_record_ids
            ):
                raise ValueError("resolved mentions require source-backed resolution records")
        elif self.canonical_variant is not None:
            raise ValueError("only resolved mentions may carry a canonical variant")
        if self.status == "excluded" and not self.warnings:
            raise ValueError("excluded mentions require a reason")
        return self


class PaperAiAdjudicationV2(_PaperV2Model):
    mention_id: PaperOpaqueId
    deterministic_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    recommendation: PaperAdjudicationRecommendationV2
    reason: PaperBoundedText
    advisory_only: Literal[True] = True
    execution_disclosure: CapabilityExecutionDisclosureV2


class PaperDocumentExtractionV2(_PaperV2Model):
    schema_version: Literal["paper_document_extraction.v2"] = "paper_document_extraction.v2"
    bundle: PaperDocumentBundleV2
    deterministic_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    page_quality: list[PaperPageExtractionQualityV2] = Field(
        default_factory=list, max_length=100_000
    )
    mentions: list[PaperVariantMentionV2] = Field(default_factory=list, max_length=10_000)
    resolutions: list[PaperMentionResolutionV2] = Field(default_factory=list, max_length=10_000)
    ai_adjudications: list[PaperAiAdjudicationV2] = Field(default_factory=list, max_length=10_000)
    execution_disclosure: CapabilityExecutionDisclosureV2
    warnings: list[PaperBoundedText] = Field(default_factory=list, max_length=64)

    @field_validator("deterministic_digest", mode="before")
    @classmethod
    def _normalize_deterministic_digest(cls, value):
        return value.lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _validate_evidence_graph(self):
        document_by_id = {document.document_id: document for document in self.bundle.documents}
        page_keys = [(quality.document_id, quality.page_number) for quality in self.page_quality]
        if len(page_keys) != len(set(page_keys)):
            raise ValueError("page quality must contain one state per document page")
        if any(document_id not in document_by_id for document_id, _page in page_keys):
            raise ValueError("page quality must reference a document in the bundle")
        for document in self.bundle.documents:
            document_pages = {
                page for document_id, page in page_keys if document_id == document.document_id
            }
            if document.kind == "pdf":
                assert document.page_count is not None
                if document_pages != set(range(1, document.page_count + 1)):
                    raise ValueError("every PDF page requires one extraction-quality state")
            elif document_pages:
                raise ValueError("page extraction quality is reserved for PDF documents")
        mention_ids = [mention.mention_id for mention in self.mentions]
        if len(mention_ids) != len(set(mention_ids)):
            raise ValueError("mention_id values must be unique")
        mention_set = set(mention_ids)
        for mention in self.mentions:
            document = document_by_id.get(mention.span.document_id)
            if document is None:
                raise ValueError("mention spans must reference a document in the bundle")
            if document.kind != "pdf" or document.page_count is None:
                if mention.span.page_number != 1:
                    raise ValueError("non-PDF mention spans use logical page 1")
            elif mention.span.page_number > document.page_count:
                raise ValueError("mention page_number exceeds the document page count")
        resolution_ids = [resolution.mention_id for resolution in self.resolutions]
        if len(resolution_ids) != len(set(resolution_ids)):
            raise ValueError("each mention may have at most one resolution")
        if set(resolution_ids) != mention_set:
            raise ValueError("resolutions must reference deterministic mentions")
        mention_by_id = {mention.mention_id: mention for mention in self.mentions}
        for resolution in self.resolutions:
            mention = mention_by_id[resolution.mention_id]
            if (
                mention.biological_context == "bibliography_only"
                and resolution.status != "excluded"
            ):
                raise ValueError("bibliography-only mentions must remain excluded")
        for advisory in self.ai_adjudications:
            if advisory.mention_id not in mention_set:
                raise ValueError("AI adjudications must reference deterministic mentions")
            if advisory.deterministic_digest != self.deterministic_digest:
                raise ValueError("AI adjudications must bind the deterministic evidence digest")
        if self.execution_disclosure.execution not in {"eamos_local", "mounted_artifact"}:
            raise ValueError("L1-L3 document extraction must be deterministic local execution")
        return self


class PaperVariantCandidate(BaseModel):
    """One variant mention extracted from publication text (pre-resolution)."""

    gene: str | None = Field(default=None, max_length=64)
    transcript_hgvs: str | None = Field(default=None, max_length=256)
    protein_change: str | None = Field(default=None, max_length=128)
    protein_hgvs: str | None = Field(default=None, max_length=128)
    level: VariantLevel = "unknown"
    context: VariantContext = "unknown"
    evidence_quote: str | None = Field(default=None, max_length=400)

    @field_validator(
        "gene",
        "transcript_hgvs",
        "protein_change",
        "protein_hgvs",
        "evidence_quote",
        mode="before",
    )
    @classmethod
    def _strip_optional(cls, value):
        if value is None or not isinstance(value, str):
            return value
        return value.strip() or None


class PaperVariantsExtraction(BaseModel):
    """Raw structured-extraction output (the model's JSON object)."""

    variants: list[PaperVariantCandidate] = Field(default_factory=list)


class ValidatedPaperVariant(BaseModel):
    """A candidate after the resolution/validation gate."""

    gene: str | None = None
    transcript_hgvs: str | None = None
    protein_change: str | None = None
    protein_hgvs: str | None = None
    level: VariantLevel = "unknown"
    context: VariantContext = "unknown"
    evidence_quote: str | None = None
    validated: bool = False
    validation_status: str = "missing"
    variant_id: str | None = None
    genomic_hgvs: str | None = None
    resolved_candidate_id: str | None = None
    source_support: list[str] = Field(default_factory=list)
    source_inputs: SearchInputSourceInputs | None = None
    candidates: list[SearchInputCandidate] = Field(default_factory=list)
    resolver_warnings: list[str] = Field(default_factory=list)
    resolver_provenance: list[str] = Field(default_factory=list)


class PaperVariantsResult(BaseModel):
    variants: list[ValidatedPaperVariant] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)


class PaperVariantsExtractRequest(BaseModel):
    """JSON request for the paper front-door endpoint."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=1_000_000)

    @field_validator("text")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text must not be blank")
        return stripped


class PaperVariantsPdfMeta(BaseModel):
    page_count: int = 0
    engine: str
    warnings: list[str] = Field(default_factory=list)


class PaperSourceMetadata(BaseModel):
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: str | None = None
    journal: str | None = None
    doi: str | None = None
    pmid: str | None = None


class PaperVariantsGuardrails(BaseModel):
    patient_data: Literal["not_used"] = "not_used"
    raw_paper_text_in_output: Literal["blocked"] = "blocked"
    secrets_in_output: Literal["blocked"] = "blocked"


class PaperVariantsExtractResponse(PaperVariantsResult):
    """HTTP front-door response: sanitized result plus CLI-style metadata."""

    mode: Literal["paper_variants_extract"] = "paper_variants_extract"
    generated_at: datetime
    # Compatibility field for V1 clients. Remove after clients read the
    # algorithm/provider identity from execution_disclosure.
    llm_provider: str
    pdf: PaperVariantsPdfMeta | None = None
    source_metadata: PaperSourceMetadata | None = None
    guardrails: PaperVariantsGuardrails = Field(default_factory=PaperVariantsGuardrails)
    candidate_count: int
    validated_count: int
    document_extraction: PaperDocumentExtractionV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    execution_disclosure: CapabilityExecutionDisclosureV2 | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def _validate_v2_output_binding(self):
        if (self.document_extraction is None) != (self.execution_disclosure is None):
            raise ValueError(
                "document extraction and execution disclosure must be supplied together"
            )
        if self.document_extraction is None:
            return self
        if self.execution_disclosure != self.document_extraction.execution_disclosure:
            raise ValueError("response execution disclosure must match document extraction")
        if self.candidate_count != len(self.document_extraction.mentions):
            raise ValueError("candidate_count must match deterministic mention count")
        resolved_count = sum(
            resolution.status == "resolved" for resolution in self.document_extraction.resolutions
        )
        if self.validated_count != resolved_count:
            raise ValueError("validated_count must match resolved mention count")
        return self
