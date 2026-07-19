from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
import re
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from app.schemas.gene_viewer import ViewerSegment, ViewerSequences, ViewerWindow
from app.schemas.protein_annotation import ProteinDomainTrack


class RunStatus(str, Enum):
    completed = "completed"
    degraded = "degraded"
    blocked = "blocked"


class ReviewStatus(str, Enum):
    pending_review = "pending_review"
    reviewed = "reviewed"
    approved = "approved"
    dropped = "dropped"


class RunRequest(BaseModel):
    patient_id: str = Field(min_length=1)
    report_ids: list[str] = Field(min_length=1)


class EvidenceSourceSummary(BaseModel):
    source: str
    status: str
    request_identity: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    source_url: str | None = None
    fetched_at: str | None = None
    source_version: str | None = None
    cache_status: str | None = None


class VariantSummaryRow(BaseModel):
    gene: str | None = None
    transcript_hgvs: str | None = None
    protein_change: str | None = None
    genomic_hg38: str | None = None
    variation_type: str | None = None
    consequence: str | None = None


PublicationTextSection = Literal[
    "title",
    "abstract",
    "body",
    "table",
    "supplement",
    "unknown",
]
PublicationSnippetSource = Literal[
    "pubmed_efetch",
    "pubtator",
    "pmc_bioc",
    "litvar2",
]
PublicationSnippetConfidence = Literal[
    "exact_variant",
    "variant_alias",
    "rsid",
    "gene_variant_context",
    "reported_no_text",
]
PublicationSourceTag = Literal["litvar2", "pubmed", "clinvar", "clingen"]
PublicationScope = Literal["variant", "gene"]
PublicationCountKind = Literal["deduped_pmids", "gene_wide_source_count", "unavailable"]
FunctionalEvidenceSourceTag = Literal["clingen", "clinvar", "pubmed", "mavedb"]
FunctionalEvidenceCode = Literal["PS3", "BS3"]
FunctionalEvidenceState = Literal[
    "strong_deficit",
    "emerging_deficit",
    "normal",
    "conflict",
    "uncurated",
    "none",
]
FunctionalEvidenceVerdictSource = Literal[
    "clingen",
    "clinvar",
    "clingen+clinvar",
    "conflict",
    "uncurated",
    "none",
]
ReportCallCardId = Literal[
    "population_frequency",
    "computational",
    "lab_functional",
    "clinical_consensus",
]
ReportCallBadgeKind = Literal["acmg", "metric", "source", "warning", "neutral"]
PopulationSequencingType = Literal["joint", "exome", "genome", "unknown"]
PopulationAgeSeriesKind = Literal["variant_carriers", "all_individuals"]
RampVerdict = Literal["Pathogenic", "Likely pathogenic", "VUS", "Likely benign", "Benign"]
EamosComputedTier = Literal[
    "Pathogenic",
    "Likely Pathogenic",
    "VUS",
    "Likely Benign",
    "Benign",
]
EamosComputedDirection = Literal["pathogenic", "benign"]
EamosComputedStrength = Literal["very_strong", "strong", "moderate", "supporting"]
EamosComputedBenignCut = Literal["tavtigian_2020", "acgs_panel"]
EamosComputedClassificationBasis = Literal[
    "bayesian_points",
    "ba1_standalone_override",
    "legacy_conflict_cap",
]
AcmgCaseContextLimitationStatus = Literal["not_scored"]
AcmgCaseContextLimitationReason = Literal["missing_case_context"]
SourceOriginKind = Literal["direct", "cross_reference", "derived"]
SourcePolicyOutcome = Literal["allowed", "denied"]
SourcePolicyAction = Literal[
    "acquire",
    "cache",
    "normalize",
    "public_serialize",
    "product_export",
    "log",
    "analyze",
    "backup",
    "stage",
    "restore",
    "raw_debug",
]
ComputationalStandardStatus = Literal["published", "draft", "shadow", "withdrawn"]
ComputationalEvidenceFamily = Literal["PP3_BP4", "SPLICE", "other"]
ComputationalApplicability = Literal[
    "applicable",
    "not_applicable",
    "unavailable",
    "not_assessed",
]
ComputationalCountedStatus = Literal[
    "counted",
    "context_only",
    "separate_mechanism",
    "rejected",
]


class SourcePolicyDecision(BaseModel):
    action: SourcePolicyAction
    field: str
    outcome: SourcePolicyOutcome
    reason: str
    decided_at: datetime


class SourceFactPolicyEnvelope(BaseModel):
    source_id: str | None = None
    source_record_id: str | None = None
    source_version: str | None = None
    source_url: str | None = None
    retrieved_at: datetime | None = None
    origin_kind: SourceOriginKind = "direct"
    match_level: str | None = None
    record_license: str | None = None
    terms_version_or_hash: str | None = None
    license_gate: str | None = None
    launch_gate: str | None = None
    public_serialization_allowed: bool | None = None
    export_allowed: bool | None = None
    cache_allowed: bool | None = None
    attribution: str | None = None
    policy_version: str | None = None
    decision_reason: str | None = None
    decision_at: datetime | None = None
    policy_decisions: list[SourcePolicyDecision] = Field(default_factory=list)

    @model_validator(mode="after")
    def _recompute_permission_projections(self) -> SourceFactPolicyEnvelope:
        if not self.policy_decisions:
            return self
        self.public_serialization_allowed = _policy_projection(
            self.policy_decisions, "public_serialize"
        )
        self.export_allowed = _policy_projection(self.policy_decisions, "product_export")
        self.cache_allowed = _policy_projection(self.policy_decisions, "cache")
        self.decision_at = max(decision.decided_at for decision in self.policy_decisions)
        denied = next(
            (decision for decision in self.policy_decisions if decision.outcome == "denied"),
            None,
        )
        if denied is not None:
            self.decision_reason = f"{denied.action}:{denied.field}:{denied.reason}"
        elif self.decision_reason is None:
            self.decision_reason = "all_recorded_policy_decisions_allowed"
        return self


def _policy_projection(
    decisions: list[SourcePolicyDecision],
    action: SourcePolicyAction,
) -> bool:
    relevant = [decision for decision in decisions if decision.action == action]
    return bool(relevant) and all(decision.outcome == "allowed" for decision in relevant)


def _serialization_policy_action(info: Any) -> str:
    context = getattr(info, "context", None)
    if isinstance(context, dict):
        action = context.get("source_policy_action")
        if isinstance(action, str) and action:
            return action
    return "public_serialize"


def _source_fact_output_allowed(fact: SourceFactPolicyEnvelope, action: str) -> bool:
    if action == "public_serialize":
        if fact.public_serialization_allowed is False:
            return False
        if _protected_source_fact(fact):
            return fact.public_serialization_allowed is True
        return True
    if action == "product_export":
        return fact.export_allowed is True
    if action == "cache":
        return fact.cache_allowed is True
    relevant = [decision for decision in fact.policy_decisions if decision.action == action]
    return bool(relevant) and all(decision.outcome == "allowed" for decision in relevant)


def _protected_source_fact(fact: SourceFactPolicyEnvelope) -> bool:
    source_text = " ".join(
        str(value or "")
        for value in (
            fact.source_id,
            getattr(fact, "source", None),
            getattr(fact, "source_list", None),
            getattr(fact, "identifier_namespace", None),
        )
    ).casefold()
    return any(source in source_text for source in ("omim", "lovd", "mavedb"))


OMIM_CROSS_REFERENCE_SUPPLIER_POLICY: dict[str, tuple[str, frozenset[str]]] = {
    "clingen_gene_validity": ("disease", frozenset({"phenotype"})),
    "gencc_download": ("disease", frozenset({"phenotype"})),
    "human_phenotype_ontology": ("gene_or_disease_links", frozenset({"phenotype"})),
    "mondo_disease_ontology": ("cross_references", frozenset({"phenotype"})),
}


class OmimCrossReference(SourceFactPolicyEnvelope):
    origin_kind: Literal["cross_reference"] = "cross_reference"
    identifier_namespace: Literal["OMIM"] = "OMIM"
    identifier: str
    entry_type: Literal["gene", "phenotype"]
    external_link_provider: Literal["omim_web"] = "omim_web"
    external_url: str
    evidence_role: Literal["identifier_only"] = "identifier_only"

    @model_validator(mode="after")
    def _validate_identifier_link(self) -> OmimCrossReference:
        prefix, separator, accession = self.identifier.partition(":")
        if prefix != "OMIM" or separator != ":" or len(accession) != 6 or not accession.isdigit():
            raise ValueError("OMIM cross-reference must use canonical OMIM:<six digits> syntax")
        if self.external_url != f"https://omim.org/entry/{accession}":
            raise ValueError("OMIM cross-reference URL must use the canonical HTTPS entry origin")
        if not self.source_id or not self.source_record_id:
            raise ValueError("OMIM cross-reference requires its supplying source and record")
        supplier_policy = OMIM_CROSS_REFERENCE_SUPPLIER_POLICY.get(self.source_id)
        if supplier_policy is None:
            raise ValueError("OMIM cross-reference supplier is not approved")
        policy_field, allowed_entry_types = supplier_policy
        if self.entry_type not in allowed_entry_types:
            raise ValueError("OMIM cross-reference entry type is invalid for its supplier")
        public_decisions = [
            decision
            for decision in self.policy_decisions
            if decision.action == "public_serialize" and decision.field == policy_field
        ]
        if (
            not public_decisions
            or any(decision.outcome != "allowed" for decision in public_decisions)
            or self.public_serialization_allowed is not True
            or not self.policy_version
            or not self.terms_version_or_hash
        ):
            raise ValueError("OMIM cross-reference requires recorded supplier permission")
        return self


def _omim_cross_reference_output_allowed(reference: OmimCrossReference, action: str) -> bool:
    relevant = [decision for decision in reference.policy_decisions if decision.action == action]
    return (
        bool(reference.source_id)
        and bool(reference.source_record_id)
        and bool(relevant)
        and all(decision.outcome == "allowed" for decision in relevant)
        and _source_fact_output_allowed(reference, action)
    )


LOVD_FIXTURE_SOURCE_ID = "lovd_global_variome_shared_fixture"
LOVD_INSTALLATION_ID = "global_variome_shared_lovd"
LOVD_INSTALLATION_BASE_URL = "https://databases.lovd.nl/shared"
LOVD_BASIC_RECORD_FIELD = "basic_record"
LOVD_POLICY_DECIDED_AT = datetime(2026, 7, 17, 13, 39, tzinfo=UTC)
LOVD_FIXTURE_POLICY_DECISIONS: dict[str, tuple[str, str]] = {
    "acquire": ("denied", "acquisition_not_approved"),
    "normalize": ("allowed", "allowed_by_source_allowlist"),
    "public_serialize": ("allowed", "allowed_by_source_allowlist"),
    "cache": ("denied", "field_not_allowlisted"),
    "product_export": ("denied", "action_not_allowlisted"),
    "log": ("denied", "action_not_allowlisted"),
    "analyze": ("denied", "action_not_allowlisted"),
    "backup": ("denied", "action_not_allowlisted"),
    "stage": ("denied", "action_not_allowlisted"),
    "restore": ("denied", "action_not_allowlisted"),
    "raw_debug": ("denied", "action_not_allowlisted"),
}
_LOVD_RECORD_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
_LOVD_TRANSCRIPT_RE = re.compile(r"(?:NM|NR)_\d+\.\d+")
_LOVD_CDNA_RE = re.compile(r"c\.[^\s:]{1,120}")


class LovdInstallationSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: Literal["lovd_global_variome_shared_fixture"] = LOVD_FIXTURE_SOURCE_ID
    installation_id: Literal["global_variome_shared_lovd"] = LOVD_INSTALLATION_ID
    display_name: Literal["Global Variome shared LOVD"] = "Global Variome shared LOVD"
    base_url: Literal["https://databases.lovd.nl/shared"] = LOVD_INSTALLATION_BASE_URL
    live_access_enabled: Literal[False] = False
    maximum_requests_per_second: float = Field(default=5.0, gt=0, le=5)
    minimum_negative_cache_ttl_seconds: int = Field(default=14_400, ge=14_400)
    positive_cache_policy: Literal["not_approved"] = "not_approved"
    record_license_mode: Literal["record_level_required"] = "record_level_required"
    installation_permission_is_record_license: Literal[False] = False


class LovdBasicObservation(SourceFactPolicyEnvelope):
    model_config = ConfigDict(extra="forbid")

    source_id: Literal["lovd_global_variome_shared_fixture"] = LOVD_FIXTURE_SOURCE_ID
    source_record_id: str
    source_version: Literal["LOVD 3 basic API synthetic schema fixture v1"] = (
        "LOVD 3 basic API synthetic schema fixture v1"
    )
    source_url: str
    origin_kind: Literal["derived"] = "derived"
    match_level: Literal["exact_normalized_hgvs"] = "exact_normalized_hgvs"
    record_license: Literal["CC-BY-4.0"]
    terms_version_or_hash: Literal["lovd-doc-review-2026-07-17"] = "lovd-doc-review-2026-07-17"
    license_gate: Literal["synthetic_fixture_record_license_example"] = (
        "synthetic_fixture_record_license_example"
    )
    launch_gate: Literal["live_access_disabled_pending_written_permission"] = (
        "live_access_disabled_pending_written_permission"
    )
    public_serialization_allowed: Literal[True] = True
    export_allowed: Literal[False] = False
    cache_allowed: Literal[False] = False
    attribution: Literal["Global Variome shared LOVD (synthetic fixture)"] = (
        "Global Variome shared LOVD (synthetic fixture)"
    )
    policy_version: Literal["lovd-fixture-policy-v1"] = "lovd-fixture-policy-v1"
    installation: LovdInstallationSource = Field(default_factory=LovdInstallationSource)
    presence: Literal[True] = True
    genome_build: Literal["GRCh37", "GRCh38"]
    transcript_accession: str
    hgvs_c: str
    source_edited_at: datetime
    evidence_role: Literal["presence_only"] = "presence_only"

    @model_validator(mode="after")
    def _validate_safe_fixture_observation(self) -> LovdBasicObservation:
        prefix = f"{LOVD_INSTALLATION_ID}:variant:"
        if not self.source_record_id.startswith(prefix):
            raise ValueError("LOVD observation record namespace is invalid")
        record_id = self.source_record_id.removeprefix(prefix)
        if _LOVD_RECORD_ID_RE.fullmatch(record_id) is None:
            raise ValueError("LOVD observation record identifier is invalid")

        parsed = urlsplit(self.source_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "databases.lovd.nl"
            or parsed.port is not None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path != f"/shared/variants/{record_id}"
        ):
            raise ValueError("LOVD observation record URL is outside the reviewed installation")
        if _LOVD_TRANSCRIPT_RE.fullmatch(self.transcript_accession) is None:
            raise ValueError("LOVD observation requires a versioned RefSeq transcript")
        if _LOVD_CDNA_RE.fullmatch(self.hgvs_c) is None:
            raise ValueError("LOVD observation requires canonical coding HGVS")
        if self.source_edited_at.tzinfo is None:
            raise ValueError("LOVD observation source-edited time requires a timezone")

        decisions_by_action = {decision.action: decision for decision in self.policy_decisions}
        if len(decisions_by_action) != len(self.policy_decisions) or set(
            decisions_by_action
        ) != set(LOVD_FIXTURE_POLICY_DECISIONS):
            raise ValueError("LOVD observation policy decision set is incomplete")
        for action, (expected_outcome, expected_reason) in LOVD_FIXTURE_POLICY_DECISIONS.items():
            decision = decisions_by_action[action]
            if (
                decision.field != LOVD_BASIC_RECORD_FIELD
                or decision.outcome != expected_outcome
                or decision.reason != expected_reason
                or decision.decided_at != LOVD_POLICY_DECIDED_AT
            ):
                raise ValueError("LOVD observation policy decision is inconsistent")
        if self.decision_reason != "acquire:basic_record:acquisition_not_approved":
            raise ValueError("LOVD observation decision summary is inconsistent")

        public_decisions = [
            decision
            for decision in self.policy_decisions
            if decision.action == "public_serialize" and decision.field == LOVD_BASIC_RECORD_FIELD
        ]
        cache_decisions = [
            decision
            for decision in self.policy_decisions
            if decision.action == "cache" and decision.field == LOVD_BASIC_RECORD_FIELD
        ]
        export_decisions = [
            decision
            for decision in self.policy_decisions
            if decision.action == "product_export" and decision.field == LOVD_BASIC_RECORD_FIELD
        ]
        if not public_decisions or any(item.outcome != "allowed" for item in public_decisions):
            raise ValueError("LOVD observation requires an allowed serialization decision")
        if not cache_decisions or any(item.outcome != "denied" for item in cache_decisions):
            raise ValueError("LOVD fixture observation caching must remain denied")
        if not export_decisions or any(item.outcome != "denied" for item in export_decisions):
            raise ValueError("LOVD fixture observation export must remain denied")
        if (
            self.public_serialization_allowed is not True
            or self.cache_allowed is not False
            or self.export_allowed is not False
        ):
            raise ValueError("LOVD observation policy projections are inconsistent")
        return self


class LovdBasicRecordsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    installation: LovdInstallationSource = Field(default_factory=LovdInstallationSource)
    status: Literal["matched", "not_found", "ambiguous", "denied"]
    observations: list[LovdBasicObservation] = Field(default_factory=list, max_length=1)
    live_request_performed: Literal[False] = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_result_shape(self) -> LovdBasicRecordsSection:
        if self.status == "matched" and len(self.observations) != 1:
            raise ValueError("matched LOVD fixture result requires exactly one observation")
        if self.status != "matched" and self.observations:
            raise ValueError("non-matching LOVD fixture result cannot expose observations")
        return self


def _lovd_observation_output_allowed(observation: LovdBasicObservation, action: str) -> bool:
    relevant = [
        decision
        for decision in observation.policy_decisions
        if decision.action == action and decision.field == LOVD_BASIC_RECORD_FIELD
    ]
    return (
        bool(relevant)
        and all(decision.outcome == "allowed" for decision in relevant)
        and _source_fact_output_allowed(observation, action)
    )


class ComputationalAlternate(BaseModel):
    predictor_id: str
    raw_score: Decimal | None = None
    calibration_normalized_score: Decimal | None = None
    score_unit: str | None = None
    calibration_id: str | None = None
    calibration_version: str | None = None
    evidence_code: Literal["PP3", "BP4"] | None = None
    calibration_points: Decimal | None = None
    counted_status: ComputationalCountedStatus = "context_only"
    non_counted_reason: str | None = None
    tool_version: str | None = None
    model_version: str | None = None
    data_version: str | None = None
    source_version: str | None = None
    source_url: str | None = None


class ComputationalEvidenceDecision(BaseModel):
    ruleset_id: str
    ruleset_version: str
    standard_label: str
    standard_status: ComputationalStandardStatus
    application_id: str
    gene_id: str | None = None
    disease_id: str | None = None
    transcript_id: str | None = None
    protein_id: str | None = None
    normalized_variant_id: str | None = None
    variant_scope: str
    mechanism_applicability: str
    evidence_family: ComputationalEvidenceFamily
    selected_predictor_id: str | None = None
    selection_policy: str
    selection_rationale: str
    declared_fallback_policy: str
    applicability: ComputationalApplicability
    raw_score: Decimal | None = None
    calibration_normalized_score: Decimal | None = None
    score_unit: str | None = None
    score_native_precision: Decimal | None = None
    score_quantization_rule: str | None = None
    evidence_code: Literal["PP3", "BP4"] | None = None
    calibration_points: Decimal | None = None
    evidence_points: Decimal
    evidence_label: str
    calibration_id: str | None = None
    calibration_version: str | None = None
    calibration_profile_checksum: str | None = None
    interval_lower: Decimal | None = None
    interval_lower_inclusive: bool | None = None
    interval_upper: Decimal | None = None
    interval_upper_inclusive: bool | None = None
    dependency_group: str
    counted_status: ComputationalCountedStatus
    non_counted_reason: str | None = None
    tool_version: str | None = None
    model_version: str | None = None
    data_version: str | None = None
    source_version: str | None = None
    source_url: str | None = None
    source_retrieved_at: datetime | None = None
    source_checksum: str | None = None
    alternates: list[ComputationalAlternate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PublicationSnippet(BaseModel):
    section: PublicationTextSection
    text: str
    matched_terms: list[str] = Field(default_factory=list)
    source: PublicationSnippetSource
    confidence: PublicationSnippetConfidence


class PubMedArticle(BaseModel):
    pmid: str
    title: str
    authors: str
    journal: str
    year: str
    url: str
    abstract: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    publication_date: str | None = None
    snippets: list[PublicationSnippet] = Field(default_factory=list)
    source_tags: list[PublicationSourceTag] = Field(default_factory=list)
    snippet_status: str | None = None


class PublicationSourceBreakdown(BaseModel):
    litvar2: int = 0
    pubmed: int = 0
    clinvar: int = 0
    clingen: int = 0


class PublicationYearCount(BaseModel):
    year: int
    count: int


class PublicationTimeline(BaseModel):
    publications_by_year: list[PublicationYearCount] = Field(default_factory=list)
    total_with_year: int = 0
    total_without_year: int = 0


class PublicationScopeCount(BaseModel):
    scope: PublicationScope
    total_count: int | None = None
    count_kind: PublicationCountKind
    query: str | None = None
    source_status: str | None = None
    source_breakdown: PublicationSourceBreakdown = Field(default_factory=PublicationSourceBreakdown)
    warnings: list[str] = Field(default_factory=list)


class PublicationScopeCounts(BaseModel):
    variant: PublicationScopeCount
    gene: PublicationScopeCount


class PublicationLiterature(BaseModel):
    total_count: int
    shown_count: int
    offset: int = 0
    limit: int = 5
    scope: PublicationScope = "variant"
    sort: Literal["publication_date_desc"] = "publication_date_desc"
    variant_terms: list[str] = Field(default_factory=list)
    source_breakdown: PublicationSourceBreakdown = Field(default_factory=PublicationSourceBreakdown)
    publication_timeline: PublicationTimeline = Field(default_factory=PublicationTimeline)
    scope_counts: PublicationScopeCounts | None = None
    articles: list[PubMedArticle] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FunctionalEvidenceSourceBreakdown(BaseModel):
    clingen: int = 0
    clinvar: int = 0
    pubmed: int = 0
    mavedb: int = 0


class FunctionalEvidenceConflictSplit(BaseModel):
    deficit: int = 0
    normal: int = 0


class FunctionalEvidenceCodeRestsOn(BaseModel):
    cited: int = 0
    total: int = 0


class FunctionalEvidenceDisplayMetrics(BaseModel):
    state: FunctionalEvidenceState = "none"
    primary_label: str = "No Functional Data Available"
    acmg_badge_text: str = "None"
    verdict_source: FunctionalEvidenceVerdictSource = "none"
    study_count_badge_text: str = "0 Unique"
    conflict_split: FunctionalEvidenceConflictSplit | None = None
    code_rests_on: FunctionalEvidenceCodeRestsOn | None = None
    ui_color_theme: str = "neutral_slate_state"


class FunctionalMeasurementValue(BaseModel):
    column: str
    source_value: str
    parsed_value: Decimal
    description: str | None = None
    details: str | None = None


class FunctionalStudy(SourceFactPolicyEnvelope):
    id: str
    pmid: str | None = None
    url: str | None = None
    citation: str | None = None
    source_accession: str | None = None
    source_tags: list[FunctionalEvidenceSourceTag] = Field(default_factory=list)
    evidence_codes: list[FunctionalEvidenceCode] = Field(default_factory=list)
    asserted_codes: list[str] = Field(default_factory=list)
    functional_score: Decimal | None = None
    functional_score_label: str | None = None
    raw_score: str | None = None
    score_unit: str | None = None
    score_column: str | None = None
    score_direction: str | None = None
    score_set_urn: str | None = None
    variant_urn: str | None = None
    experiment_urn: str | None = None
    experiment_set_urn: str | None = None
    target_accession: str | None = None
    target_kind: str | None = None
    target_assembly: str | None = None
    target_sequence_checksum: str | None = None
    target_identity: str | None = None
    mave_hgvs_nt: str | None = None
    mave_hgvs_splice: str | None = None
    mave_hgvs_pro: str | None = None
    score_column_description: str | None = None
    score_column_details: str | None = None
    uncertainty_values: list[FunctionalMeasurementValue] = Field(default_factory=list)
    assay_context: str | None = None
    method_text: str | None = None
    linked_doi_identifiers: list[str] = Field(default_factory=list)
    linked_publication_identifiers: list[str] = Field(default_factory=list)
    archive_release_doi: str | None = None
    archive_sha256: str | None = None
    archive_checksum_algorithm: str | None = None
    archive_checksum_value: str | None = None
    archive_checksum_verified: bool | None = None
    local_logical_checksum_verified: bool | None = None
    data_usage_policy_decision: str | None = None
    match_requested_identity: str | None = None
    match_matched_identity: str | None = None
    calibration_status: str | None = None
    deprecated: bool = False
    superseded_by: str | None = None
    provenance: list[SourceProvenance] = Field(default_factory=list)
    snippet: str | None = None

    @field_serializer("provenance", when_used="json")
    def _serialize_policy_provenance(
        self, provenance: list[SourceProvenance], info: Any
    ) -> list[SourceProvenance]:
        action = _serialization_policy_action(info)
        return [item for item in provenance if _source_fact_output_allowed(item, action)]


class FunctionalAssayConfusionMatrix(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pathogenic_abnormal: int = Field(ge=0)
    pathogenic_normal: int = Field(ge=0)
    benign_abnormal: int = Field(ge=0)
    benign_normal: int = Field(ge=0)


def _normalized_identifier_set(values: list[str]) -> set[str]:
    return {value.strip().casefold() for value in values if value.strip()}


class FunctionalAssayValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    validation_id: str = Field(min_length=1)
    validation_version: str = Field(min_length=1)
    validation_policy_id: str = Field(min_length=1)
    validation_policy_version: str = Field(min_length=1)
    status: ComputationalStandardStatus
    gene_id: str = Field(min_length=1)
    disease_id: str = Field(min_length=1)
    disease_mechanism: str = Field(min_length=1)
    assay_name: str = Field(min_length=1)
    assay_relevance: str = Field(min_length=1)
    pathogenic_truth_variant_ids: list[str] = Field(min_length=1)
    benign_truth_variant_ids: list[str] = Field(min_length=1)
    evaluation_variant_ids: list[str] = Field(default_factory=list)
    truth_set_independence_basis: str = Field(min_length=1)
    truth_evaluation_overlap_rejected: bool
    circularity_reviewed: bool
    confusion_matrix: FunctionalAssayConfusionMatrix
    pseudocount_policy: Literal["brnich_2020_one_discordant_control"]
    pseudocount: Decimal = Field(ge=Decimal("1"), le=Decimal("1"))
    direction: EamosComputedDirection
    functional_assay_oddspath: Decimal = Field(gt=Decimal("0"))
    confidence_interval_lower: Decimal = Field(gt=Decimal("0"))
    confidence_interval_upper: Decimal = Field(gt=Decimal("0"))
    maximum_supported_strength: EamosComputedStrength
    curator: str = Field(min_length=1)
    validation_date: date
    source_url: str = Field(min_length=1)
    source_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_assay_record(self) -> FunctionalAssayValidation:
        pathogenic = _normalized_identifier_set(self.pathogenic_truth_variant_ids)
        benign = _normalized_identifier_set(self.benign_truth_variant_ids)
        evaluation = _normalized_identifier_set(self.evaluation_variant_ids)
        if len(pathogenic) != len(self.pathogenic_truth_variant_ids):
            raise ValueError("pathogenic truth-set variant IDs must be non-empty and unique")
        if len(benign) != len(self.benign_truth_variant_ids):
            raise ValueError("benign truth-set variant IDs must be non-empty and unique")
        if len(evaluation) != len(self.evaluation_variant_ids):
            raise ValueError("evaluation-set variant IDs must be non-empty and unique")
        if pathogenic & benign:
            raise ValueError("pathogenic and benign truth sets must be independent")
        if (
            self.confusion_matrix.pathogenic_abnormal + self.confusion_matrix.pathogenic_normal
            != len(pathogenic)
        ):
            raise ValueError("pathogenic confusion-matrix total must match the truth set")
        if self.confusion_matrix.benign_abnormal + self.confusion_matrix.benign_normal != len(
            benign
        ):
            raise ValueError("benign confusion-matrix total must match the truth set")
        if (pathogenic | benign) & evaluation:
            raise ValueError("truth and evaluation variant sets must not overlap")
        if not self.truth_evaluation_overlap_rejected or not self.circularity_reviewed:
            raise ValueError("truth-set overlap and circularity review must pass")
        if self.confidence_interval_lower > self.functional_assay_oddspath:
            raise ValueError("functional assay OddsPath falls below its confidence interval")
        if self.functional_assay_oddspath > self.confidence_interval_upper:
            raise ValueError("functional assay OddsPath exceeds its confidence interval")
        if urlsplit(self.source_url).scheme != "https":
            raise ValueError("functional assay validation source URL must use HTTPS")
        return self


class FunctionalEvidenceAssertionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_id: str = Field(min_length=1)
    code: FunctionalEvidenceCode
    applied_strength: EamosComputedStrength
    variant_id: str = Field(min_length=1)
    gene_id: str = Field(min_length=1)
    disease_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_record_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    selected_for_counting: bool = False
    selection_rationale: str | None = None
    validation: FunctionalAssayValidation

    @model_validator(mode="after")
    def _validate_assertion_candidate(self) -> FunctionalEvidenceAssertionCandidate:
        if self.selected_for_counting and not (self.selection_rationale or "").strip():
            raise ValueError("selected functional assertion requires a selection rationale")
        if urlsplit(self.source_url).scheme != "https":
            raise ValueError("functional assertion source URL must use HTTPS")
        return self


class FunctionalEvidenceSummary(BaseModel):
    total_count: int
    source_breakdown: FunctionalEvidenceSourceBreakdown = Field(
        default_factory=FunctionalEvidenceSourceBreakdown
    )
    evidence_codes: list[FunctionalEvidenceCode] = Field(default_factory=list)
    source_asserted_codes: list[str] = Field(default_factory=list)
    assertion_candidates: list[FunctionalEvidenceAssertionCandidate] = Field(default_factory=list)
    display_metrics: FunctionalEvidenceDisplayMetrics = Field(
        default_factory=FunctionalEvidenceDisplayMetrics
    )
    studies: list[FunctionalStudy] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_serializer("studies", when_used="json")
    def _serialize_public_studies(
        self,
        studies: list[FunctionalStudy],
        info: Any,
    ) -> list[FunctionalStudy]:
        action = _serialization_policy_action(info)
        return [study for study in studies if _source_fact_output_allowed(study, action)]


class EamosComputedPolicyDiff(BaseModel):
    field: str
    general_value: str
    overlay_value: str


class EamosComputedVersionPin(BaseModel):
    framework: str
    ruleset_id: str
    ruleset_version: str
    conflict_policy_id: str
    pvs1_revision: str
    pp3_calibration: str
    vcep_id: str | None = None
    population_policy_id: str
    population_policy_version: str
    cspec_overlay_id: str | None = None
    cspec_overlay_version: str | None = None
    population_policy_diff: list[EamosComputedPolicyDiff] = Field(default_factory=list)


class EamosComputedConflict(BaseModel):
    is_conflicting: bool
    reason: str | None = None


class EamosComputedCriterion(BaseModel):
    code: str
    direction: EamosComputedDirection
    triggered: bool
    applied_strength: EamosComputedStrength | None = None
    points: Decimal
    evidence_value: str | int | float | Decimal | None = None
    threshold: str | int | float | Decimal | None = None
    source_db: str | None = None
    source_version: str | None = None
    source_url: str | None = None
    svi_reference: str | None = None
    policy_id: str | None = None
    policy_version: str | None = None
    policy_source_url: str | None = None
    cspec_overlay_id: str | None = None
    cspec_overlay_version: str | None = None
    functional_assay_oddspath: Decimal | None = None
    functional_assay_confidence_interval_lower: Decimal | None = None
    functional_assay_confidence_interval_upper: Decimal | None = None


class AcmgCaseContextLimitation(BaseModel):
    code: str
    status: AcmgCaseContextLimitationStatus = "not_scored"
    reason: AcmgCaseContextLimitationReason = "missing_case_context"
    missing_inputs: list[str] = Field(default_factory=list)
    applies_when: list[str] = Field(default_factory=list)
    message: str


class EamosComputedClassification(BaseModel):
    acmg_version_pin: EamosComputedVersionPin
    net_points: Decimal
    sum_pathogenic: Decimal
    sum_benign: Decimal
    tier: EamosComputedTier
    classification_basis: EamosComputedClassificationBasis
    conflict: EamosComputedConflict
    ba1_override: bool
    aggregate_evidence_likelihood_ratio: Decimal | None = Field(default=None, gt=Decimal("0"))
    prior_odds: Decimal | None = Field(default=None, gt=Decimal("0"))
    posterior_odds: Decimal | None = Field(default=None, gt=Decimal("0"))
    model_posterior: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
    )
    benign_cut: EamosComputedBenignCut
    per_criterion: list[EamosComputedCriterion] = Field(default_factory=list)
    limitations: list[AcmgCaseContextLimitation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_classification_basis(self) -> EamosComputedClassification:
        model_values = (
            self.aggregate_evidence_likelihood_ratio,
            self.prior_odds,
            self.posterior_odds,
            self.model_posterior,
        )
        if self.ba1_override:
            if self.classification_basis != "ba1_standalone_override" or self.tier != "Benign":
                raise ValueError("BA1 override requires the benign stand-alone basis")
            if any(value is not None for value in model_values):
                raise ValueError("BA1 override cannot expose Bayesian model quantities")
        else:
            if self.classification_basis == "ba1_standalone_override":
                raise ValueError("BA1 stand-alone basis requires ba1_override")
            if any(value is None for value in model_values):
                raise ValueError(
                    "point-model classifications require all Bayesian model quantities"
                )
        return self


class ReportCallBadge(BaseModel):
    text: str
    kind: ReportCallBadgeKind


class ReportCallInteraction(BaseModel):
    action: Literal["none", "scroll", "scroll_and_expand"] = "none"
    target_section_id: str | None = None
    target_panel_id: str | None = None


class ReportCallCard(BaseModel):
    card_id: ReportCallCardId
    title: str
    primary_label: str
    support_badges: list[ReportCallBadge] = Field(default_factory=list)
    ui_color_theme: str
    source_status: str
    provenance: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    interaction: ReportCallInteraction | None = None


class VariantReportCallCards(BaseModel):
    cards: list[ReportCallCard] = Field(default_factory=list)


class PopulationFrequencyAncestryGroup(BaseModel):
    id: str
    allele_count: int | None = None
    allele_number: int | None = None
    allele_frequency: float | None = None
    homozygote_count: int | None = None


class PopulationAgeHistogram(BaseModel):
    bin_edges: list[float] = Field(default_factory=list)
    bin_freq: list[int] = Field(default_factory=list)
    n_smaller: int | None = None
    n_larger: int | None = None


class PopulationAgeDistribution(BaseModel):
    het: PopulationAgeHistogram | None = None
    hom: PopulationAgeHistogram | None = None


class PopulationSequencingAgeDistribution(BaseModel):
    sequencing_type: PopulationSequencingType
    age_distribution: PopulationAgeDistribution


class PopulationFrequencyDetail(BaseModel):
    source: str = "gnomAD"
    dataset: str = ""
    variant_id: str = ""
    unavailable_reason: str | None = None
    sequencing_type: PopulationSequencingType = "unknown"
    allele_frequency: float | None = None
    allele_count: int | None = None
    allele_number: int | None = None
    homozygote_count: int | None = None
    popmax_frequency: float | None = None
    popmax_population: str | None = None
    genetic_ancestry_groups: list[PopulationFrequencyAncestryGroup] = Field(default_factory=list)
    age_distribution: PopulationAgeDistribution | None = None
    age_distributions: list[PopulationSequencingAgeDistribution] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_url: str | None = None


ClassificationTier = Literal["pathogenic", "likely_pathogenic", "vus", "likely_benign", "benign"]
AcmgVerdict = Literal["met", "not_met", "not_assessed"]
PredictorVerdict = Literal["damaging", "tolerated", "uncertain"]


class NearbyVariant(BaseModel):
    cds_pos: int
    classification: ClassificationTier
    hgvs: str
    clinvar_id: str | None = None
    protein_change: str | None = None


class CodonCell(BaseModel):
    codon_number: int
    aa_ref: str
    aa_alt: str | None = None
    dna_ref: str = ""
    dna_alt: str | None = None
    is_query: bool = False


class LocusContext(BaseModel):
    """Region viewer payload for the report."""

    gene: str
    centre_cdna: str
    coords: str = ""
    nearby_variants: list[NearbyVariant] = Field(default_factory=list)
    codon_strip: list[CodonCell] = Field(default_factory=list)


class PredictorCard(BaseModel):
    """One card in the in-silico prediction grid."""

    name: Literal["REVEL", "AlphaMissense", "MetaLR", "SpliceAI"]
    score: float
    threshold: float
    verdict: PredictorVerdict
    verdict_label: str = ""
    source_url: str | None = None


class InSilicoPredictions(BaseModel):
    cards: list[PredictorCard] = Field(default_factory=list)
    consensus_note: str


class AcmgCriterion(BaseModel):
    code: Literal[
        "PVS1",
        "PS1",
        "PS2",
        "PS3",
        "PS4",
        "PM1",
        "PM2",
        "PM3",
        "PM4",
        "PM5",
        "PM6",
        "PP1",
        "PP2",
        "PP3",
        "PP4",
        "PP5",
        "BA1",
        "BS1",
        "BS2",
        "BS3",
        "BS4",
        "BP1",
        "BP2",
        "BP3",
        "BP4",
        "BP5",
        "BP6",
        "BP7",
    ]
    verdict: AcmgVerdict
    note: str | None = None


class AcmgCriteriaScaffold(BaseModel):
    criteria: list[AcmgCriterion] = Field(default_factory=list)
    intro: str = ""
    note: str = ""
    disclaimer: str = "Supporting evidence, not classification."


class CuratedVariantsDistribution(BaseModel):
    """3 by 4 heat matrix, flattened into keyed cells."""

    cells: dict[str, int] = Field(default_factory=dict)
    row_totals: dict[str, int] = Field(default_factory=dict)
    total: int
    subtitle: str = ""
    reading: str
    source_status: str | None = None
    source_id: str | None = None
    source_version: str | None = None
    source_url: str | None = None
    public_serialization_allowed: bool | None = None
    launch_gate: str | None = None
    license_gate: str | None = None
    query_cell: str | None = None
    query_variant_id: str | None = None
    query_accession: str | None = None
    query_classification: str | None = None
    warnings: list[str] = Field(default_factory=list)


class AssociatedCondition(SourceFactPolicyEnvelope):
    name: str
    case_count: int
    evidence_level: Literal["definitive", "strong", "moderate", "limited"]
    inheritance: Literal["AR", "AD", "XL", "MT"]
    source: str
    db_tag: str = ""
    db_tag_bold: str | None = None
    source_list: str = ""


class PublicationsCallout(BaseModel):
    total_count: int
    scholar_url: str
    blurb: str = ""
    ai_summary_prompt: str
    scope_counts: PublicationScopeCounts | None = None


SourceStatus = Literal[
    "live",
    "local",
    "cache",
    "stale",
    "fixture",
    "fallback",
    "missing",
    "live_stub",
    "error",
    "failed",
]
ReportMatchLevel = Literal["variant_level", "gene_level", "disease_level", "unavailable"]
ReportDataCurrencyTier = Literal["volatile", "static"]
ReportDataCurrencyStatus = Literal["fresh", "stale", "overdue", "unknown"]
ReportSectionSignalStatus = Literal["ready", "limited", "empty", "error", "loading"]
ReportSectionRelevance = Literal[
    "exact_variant",
    "equivalent_allele",
    "protein_region",
    "transcript_locus",
    "gene_disease",
    "disease_discovery",
    "gene_discovery",
    "summary",
]
ReportSectionSourceStrength = Literal[
    "expert_panel",
    "curated",
    "primary_db",
    "literature",
    "eamos_computed",
    "source_mixed",
    "inferred",
    "unavailable",
]
EvidenceAssertionLevel = Literal[
    "source_asserted",
    "vcep_specified",
    "eamos_hint",
    "not_assessed",
]
ExpertPanelClassification = Literal[
    "pathogenic",
    "likely_pathogenic",
    "vus",
    "likely_benign",
    "benign",
    "conflicting",
    "not_classified",
]
ExpertPanelFreshness = Literal["fresh", "stale", "unknown"]
ExpertPanelFreshnessReason = Literal["cache_hit", "stale_on_failure", "tile_only"]


class ReportDataCurrencySource(BaseModel):
    source: str
    label: str | None = None
    materialized_at: str | None = None
    upstream_released_at: str | None = None
    tier: ReportDataCurrencyTier | None = None
    status: ReportDataCurrencyStatus | None = None
    staleness_days: int | None = None
    source_version: str | None = None


class ReportDataCurrency(BaseModel):
    generated_at: str | None = None
    sources: list[ReportDataCurrencySource] = Field(default_factory=list)


class EvidenceIdentityMatch(BaseModel):
    tier: Literal[
        "assertion_id",
        "caid",
        "clinvar_variation_id",
        "vrs",
        "spdi",
        "genomic_hgvs",
        "transcript_hgvs",
        "candidate_text",
    ]
    source_field: str
    requested: str
    matched: str
    normalized_requested: str
    normalized_matched: str
    auto_attach_allowed: bool


class SourceProvenance(SourceFactPolicyEnvelope):
    source: str
    status: SourceStatus
    query: dict[str, str] = Field(default_factory=dict)
    version: str | None = None
    storage_kind: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ExpertPanelVcep(BaseModel):
    id: str
    name: str
    affiliation_id: str | None = None
    last_curated_date: str
    vcep_url: str


class ExpertPanelCriterion(BaseModel):
    code: str
    applied_strength: str
    default_strength: str
    state: Literal["met", "not_met", "not_assessed", "conflicting"]
    assertion_level: EvidenceAssertionLevel = "vcep_specified"
    rationale: str | None = None
    source: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExpertPanelProvenance(BaseModel):
    source_url: str
    fetched_at: str
    source_version: str
    cache_record_id: str | None = None
    raw_jsonld_ref: str | None = None
    identity_match: EvidenceIdentityMatch | None = None


class ExpertPanelSection(BaseModel):
    vcep: ExpertPanelVcep
    final_classification: ExpertPanelClassification
    narrative: str
    criteria: list[ExpertPanelCriterion] = Field(default_factory=list)
    source_scope: str
    provenance: ExpertPanelProvenance
    freshness: ExpertPanelFreshness = "unknown"
    freshness_reason: ExpertPanelFreshnessReason | None = None


class ReportExtractionSectionTarget(BaseModel):
    section_id: Literal[
        "header",
        "population_frequency",
        "rna_splicing",
        "lab_functional",
        "clinical_consensus",
        "interpretation_summary",
        "disease_mechanism",
        "gene_context_snapshot",
        "molecular_context",
        "computational_deep_dive",
        "acmg_worksheet",
        "publications",
        "therapies_trials",
        "provenance",
    ]
    match_level: ReportMatchLevel
    required_sources: list[str] = Field(default_factory=list)
    query_terms: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ReportExtractionPlan(BaseModel):
    submitted_text: str
    mode: str
    canonical_identity: dict[str, str] = Field(default_factory=dict)
    source_query_bundle: dict[str, str | list[str] | None] = Field(default_factory=dict)
    section_targets: list[ReportExtractionSectionTarget] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)


class VariantReportHeader(BaseModel):
    display_name: str
    gene: str
    transcript: str | None = None
    cdna: str | None = None
    protein_change: str | None = None
    genomic_hg38: str | None = None
    dbsnp_rsid: str | None = None
    ensembl_gene_id: str | None = None
    ensembl_transcript: str | None = None
    transcript_aliases: list[str] = Field(default_factory=list)
    mane_select: bool | None = None
    view_count: int | None = None
    updated_at: str | None = None
    classification: str | None = None
    classification_source: str | None = None
    verification_badges: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class InterpretationSummary(BaseModel):
    mode: Literal["deterministic", "llm_rewrite", "unavailable"] = "deterministic"
    text: str
    fact_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DiseaseMechanismSection(BaseModel):
    primary_condition: str | None = None
    disease_ids: list[str] = Field(default_factory=list)
    omim_cross_references: list[OmimCrossReference] = Field(default_factory=list)
    inheritance: str | None = None
    penetrance: str | None = None
    gene_disease_validity: str | None = None
    mechanism: str | None = None
    provenance: list[SourceProvenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_serializer("provenance", when_used="json")
    def _serialize_policy_provenance(
        self, provenance: list[SourceProvenance], info: Any
    ) -> list[SourceProvenance]:
        action = _serialization_policy_action(info)
        return [item for item in provenance if _source_fact_output_allowed(item, action)]

    @field_serializer("omim_cross_references", when_used="json")
    def _serialize_omim_cross_references(
        self,
        references: list[OmimCrossReference],
        info: Any,
    ) -> list[OmimCrossReference]:
        action = _serialization_policy_action(info)
        return [
            reference
            for reference in references
            if _omim_cross_reference_output_allowed(reference, action)
        ]


class MolecularContextSection(BaseModel):
    chromosome: str | None = None
    strand: str | None = None
    exon: str | None = None
    codon_change: str | None = None
    protein_position: str | None = None
    domain: str | None = None
    hotspot_flag: bool | None = None
    loeuf: float | None = None
    clingen_haploinsufficiency: str | None = None
    overlapping_cnvs: list[str] = Field(default_factory=list)
    protein_domain_track: ProteinDomainTrack | None = None
    provenance: list[SourceProvenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_serializer("provenance", when_used="json")
    def _serialize_policy_provenance(
        self, provenance: list[SourceProvenance], info: Any
    ) -> list[SourceProvenance]:
        action = _serialization_policy_action(info)
        return [item for item in provenance if _source_fact_output_allowed(item, action)]


class ComputationalPredictorRow(BaseModel):
    name: str
    score: str | float | None = None
    threshold: str | float | None = None
    interpretation: str | None = None
    source: str
    source_id: str | None = None
    version: str | None = None
    calibrated_label: str | None = None
    calibration_bucket: RampVerdict | None = None
    calibration_method: str | None = None
    calibration_version: str | None = None
    calibration_id: str | None = None
    calibration_profile_checksum: str | None = None
    calibration_normalized_score: Decimal | None = None
    score_unit: str | None = None
    score_native_precision: Decimal | None = None
    score_quantization_rule: str | None = None
    evidence_code: Literal["PP3", "BP4", "SPLICE"] | None = None
    evidence_points: Decimal | None = None
    interval_lower: Decimal | None = None
    interval_lower_inclusive: bool | None = None
    interval_upper: Decimal | None = None
    interval_upper_inclusive: bool | None = None
    source_url: str | None = None
    public_serialization_allowed: bool | None = None
    launch_gate: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ComputationalDeepDiveSection(BaseModel):
    predictors: list[ComputationalPredictorRow] = Field(default_factory=list)
    selection_accounting: str | None = None
    spliceai_max_delta: float | None = None
    spliceai_consequence: str | None = None
    conservation: list[ComputationalPredictorRow] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_serializer("provenance", when_used="json")
    def _serialize_policy_provenance(
        self, provenance: list[SourceProvenance], info: Any
    ) -> list[SourceProvenance]:
        action = _serialization_policy_action(info)
        return [item for item in provenance if _source_fact_output_allowed(item, action)]


class AcmgWorksheetCriterion(BaseModel):
    code: str
    state: Literal["met", "not_met", "not_assessed", "conflicting"]
    strength: str | None = None
    assertion_level: EvidenceAssertionLevel
    rationale: str | None = None
    source: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AcmgWorksheetLedger(BaseModel):
    classification: str | None = None
    classification_source: str | None = None
    criteria: list[AcmgWorksheetCriterion] = Field(default_factory=list)
    synthesis: str | None = None
    disclaimer: str = "Supporting evidence, not a clinical classification."


class TrialMatch(BaseModel):
    nct_id: str
    title: str
    status: str | None = None
    phase: str | None = None
    conditions: list[str] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    match_level: ReportMatchLevel
    matched_terms: list[str] = Field(default_factory=list)
    source_url: str
    warnings: list[str] = Field(default_factory=list)
    matched_query_id: str | None = None
    evidence_field: str | None = None
    evidence_snippet: str | None = None
    last_update_posted_at: str | None = None
    fetched_at: str | None = None


class ClinicalTrialQueryExecution(BaseModel):
    query_id: str | None = None
    lane: str | None = None
    query_term: str | None = None
    params: dict[str, str] = Field(default_factory=dict)
    source_url: str | None = None
    registry_source_url: str | None = None
    registry_source_release: str | None = None
    status: str | None = None
    result_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class TherapiesTrialsSection(BaseModel):
    trial_rows: list[TrialMatch] = Field(default_factory=list)
    query_executions: list[ClinicalTrialQueryExecution] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)

    @field_serializer("provenance", when_used="json")
    def _serialize_policy_provenance(
        self, provenance: list[SourceProvenance], info: Any
    ) -> list[SourceProvenance]:
        action = _serialization_policy_action(info)
        return [item for item in provenance if _source_fact_output_allowed(item, action)]


class PopulationFrequencyVisualScale(BaseModel):
    basis: Literal["allele_frequency", "popmax_frequency"] = "allele_frequency"
    min_value: float = 0.0
    max_value: float | None = None
    max_group_id: str | None = None
    warnings: list[str] = Field(default_factory=list)


class PopulationFrequencyDatasetCell(BaseModel):
    allele_frequency: float | None = None
    allele_count: int | None = None
    allele_number: int | None = None
    homozygote_count: int | None = None


class PopulationFrequencySexCell(PopulationFrequencyDatasetCell):
    pass


class PopulationFrequencyOverallTotalCell(PopulationFrequencyDatasetCell):
    exome: PopulationFrequencyDatasetCell | None = None
    genome: PopulationFrequencyDatasetCell | None = None


class PopulationFrequencyOverall(BaseModel):
    total: PopulationFrequencyOverallTotalCell | None = None
    xx: PopulationFrequencySexCell | None = None
    xy: PopulationFrequencySexCell | None = None


class PopulationFrequencyVisualGroup(BaseModel):
    id: str
    label: str
    allele_frequency: float | None = None
    allele_count: int | None = None
    allele_number: int | None = None
    homozygote_count: int | None = None
    is_popmax: bool = False
    data_state: Literal["observed", "zero_observed", "not_reported", "filtered"] = "observed"
    sort_order: int | None = None
    xx: PopulationFrequencySexCell | None = None
    xy: PopulationFrequencySexCell | None = None
    exome: PopulationFrequencyDatasetCell | None = None
    genome: PopulationFrequencyDatasetCell | None = None
    warnings: list[str] = Field(default_factory=list)


class PopulationAgeBin(BaseModel):
    label: str
    lower_bound: float | None = None
    upper_bound: float | None = None
    count: int


class PopulationAgeHistogramView(BaseModel):
    sequencing_type: PopulationSequencingType = "unknown"
    series_kind: PopulationAgeSeriesKind = "variant_carriers"
    genotype: Literal[
        "heterozygous_alternate",
        "homozygous_alternate",
        "combined",
        "not_applicable",
    ]
    scope: Literal["overall_release_samples", "genetic_ancestry_group"] = "overall_release_samples"
    group_id: str | None = None
    bins: list[PopulationAgeBin] = Field(default_factory=list)
    n_smaller: int | None = None
    n_larger: int | None = None
    warnings: list[str] = Field(default_factory=list)


class PopulationFrequencySourceRow(BaseModel):
    group_id: str
    label: str
    allele_frequency: float | None = None
    allele_count: int | None = None
    allele_number: int | None = None
    homozygote_count: int | None = None
    is_popmax: bool = False
    warnings: list[str] = Field(default_factory=list)


class PopulationFrequencyReportSection(BaseModel):
    section_number: int = 3
    section_id: str = "section-3-population-frequency"
    panel_id: str = "gnomad-expansion"
    title: str = "gnomAD Population Frequency Detail"
    detail_ref: Literal["population_frequency_detail"] = "population_frequency_detail"
    source_status: str = "missing"
    unavailable_reason: str | None = None
    dataset: str = ""
    genome_build: str = "GRCh38"
    variant_id: str = ""
    sequencing_type: PopulationSequencingType = "unknown"
    visual_scale: PopulationFrequencyVisualScale | None = None
    visual_groups: list[PopulationFrequencyVisualGroup] = Field(default_factory=list)
    overall: PopulationFrequencyOverall | None = None
    age_histograms: list[PopulationAgeHistogramView] = Field(default_factory=list)
    source_rows: list[PopulationFrequencySourceRow] = Field(default_factory=list)
    source_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)

    @field_serializer("provenance", when_used="json")
    def _serialize_policy_provenance(
        self, provenance: list[SourceProvenance], info: Any
    ) -> list[SourceProvenance]:
        action = _serialization_policy_action(info)
        return [item for item in provenance if _source_fact_output_allowed(item, action)]


GeneContextVariantMembership = Literal["exon", "intron", "outside_transcript", "unknown"]
GeneContextOverviewMode = Literal["compressed_introns", "linear"]


class GeneContextTranscriptExon(BaseModel):
    number: int
    cds_start: int | None = None
    cds_end: int | None = None
    genomic_start: int | None = None
    genomic_end: int | None = None
    genomic_length: int | None = None
    transcript_start: int | None = None
    transcript_end: int | None = None


class GeneContextTranscriptIntron(BaseModel):
    number: int
    genomic_start: int | None = None
    genomic_end: int | None = None
    length_bp: int | None = None
    transcript_start: int | None = None
    transcript_end: int | None = None


class GeneContextVariantProjection(BaseModel):
    hgvs_c: str | None = None
    hgvs_p: str | None = None
    cds_pos: int | None = None
    genomic_hg38: str | None = None
    ref: str | None = None
    alt: str | None = None
    exon_number: int | None = None
    intron_number: int | None = None
    membership: GeneContextVariantMembership = "unknown"
    transcript_offset: int | None = None
    codon_number: int | None = None
    codon_offset: int | None = None
    aa_ref: str | None = None
    aa_alt: str | None = None
    warnings: list[str] = Field(default_factory=list)


class GeneContextRenderHints(BaseModel):
    overview_mode: GeneContextOverviewMode = "compressed_introns"
    min_exon_width_px: int = 8
    max_intron_width_px: int = 72
    zoom_flank_bp: int = 120
    large_gene_compression_applied: bool = False
    warnings: list[str] = Field(default_factory=list)


class GeneContextWorkbenchLink(BaseModel):
    url: str
    gene: str
    cdna: str
    transcript: str | None = None


class GeneContextSnapshot(BaseModel):
    section_number: int = 2
    section_id: str = "section-2-gene-context"
    panel_id: str = "gene-context-snapshot"
    title: str = "Gene Context Snapshot"
    source_status: SourceStatus = "missing"
    gene: str
    transcript: str | None = None
    transcript_aliases: list[str] = Field(default_factory=list)
    genome_build: str = "GRCh38"
    chromosome: str | None = None
    strand: Literal["+", "-", "unknown"] = "unknown"
    ensembl_gene_id: str | None = None
    gene_start: int | None = None
    gene_end: int | None = None
    gene_length: int | None = None
    cds_length: int | None = None
    protein_length: int | None = None
    exons: list[GeneContextTranscriptExon] = Field(default_factory=list)
    introns: list[GeneContextTranscriptIntron] = Field(default_factory=list)
    variant: GeneContextVariantProjection | None = None
    zoom_window: ViewerWindow | None = None
    zoom_segments: list[ViewerSegment] = Field(default_factory=list)
    zoom_sequences: ViewerSequences | None = None
    protein_domain_track: ProteinDomainTrack | None = None
    render_hints: GeneContextRenderHints = Field(default_factory=GeneContextRenderHints)
    workbench_link: GeneContextWorkbenchLink | None = None
    provenance: list[SourceProvenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_serializer("provenance", when_used="json")
    def _serialize_policy_provenance(
        self, provenance: list[SourceProvenance], info: Any
    ) -> list[SourceProvenance]:
        action = _serialization_policy_action(info)
        return [item for item in provenance if _source_fact_output_allowed(item, action)]


class ReportSectionSignal(BaseModel):
    section_id: str
    label: str
    priority: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    relevance: ReportSectionRelevance
    source_strength: ReportSectionSourceStrength
    status: ReportSectionSignalStatus
    default_open: bool = False
    headline: str | None = None
    data_notes: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class VariantReportProfile(BaseModel):
    extraction_plan: ReportExtractionPlan | None = None
    header: VariantReportHeader | None = None
    interpretation_summary: InterpretationSummary | None = None
    disease_mechanism: DiseaseMechanismSection | None = None
    gene_context_snapshot: GeneContextSnapshot | None = None
    population_frequency: PopulationFrequencyReportSection | None = None
    molecular_context: MolecularContextSection | None = None
    computational_decision: ComputationalEvidenceDecision | None = None
    computational_deep_dive: ComputationalDeepDiveSection | None = None
    acmg_worksheet: AcmgWorksheetLedger | None = None
    expert_panel: ExpertPanelSection | None = None
    therapies_trials: TherapiesTrialsSection | None = None
    lovd_basic_records: LovdBasicRecordsSection | None = None
    section_signals: list[ReportSectionSignal] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)

    @field_serializer("provenance", when_used="json")
    def _serialize_policy_provenance(
        self, provenance: list[SourceProvenance], info: Any
    ) -> list[SourceProvenance]:
        action = _serialization_policy_action(info)
        return [item for item in provenance if _source_fact_output_allowed(item, action)]

    @field_serializer("lovd_basic_records", when_used="json")
    def _serialize_lovd_basic_records(
        self,
        section: LovdBasicRecordsSection | None,
        info: Any,
    ) -> LovdBasicRecordsSection | None:
        if section is None or section.status != "matched":
            return None
        action = _serialization_policy_action(info)
        if all(_lovd_observation_output_allowed(item, action) for item in section.observations):
            return section
        return None


REPORT_SOURCE_FILENAMES_MAX = 32
REPORT_VARIANT_SUMMARY_ROWS_MAX = 100
REPORT_PUBMED_ARTICLES_MAX = 100
REPORT_AI_GENERATED_SECTIONS_MAX = 64
REPORT_ASSOCIATED_CONDITIONS_MAX = 100


class ReportPayload(BaseModel):
    patient_id: str
    report_generated_at: str | None = None
    report_data_currency: ReportDataCurrency | None = None
    source_versions: dict[str, str] = Field(default_factory=dict)
    case_label: str | None = None
    report_title: str | None = None
    source_filenames: list[str] = Field(
        default_factory=list, max_length=REPORT_SOURCE_FILENAMES_MAX
    )
    patient_context: str | None = None
    clinical_phenotype: str | None = None
    ai_clinical_summary: str | None = None
    variant_summary_rows: list[VariantSummaryRow] = Field(
        default_factory=list,
        max_length=REPORT_VARIANT_SUMMARY_ROWS_MAX,
    )
    expanded_evidence: str | None = None
    acmg_classification: str | None = None
    clinical_integration: str | None = None
    expected_symptoms: str | None = None
    recommendations: str | None = None
    limitations: str | None = None
    variant_decoder: str | None = None
    therapeutic_landscape: str | None = None
    pubmed_articles: list[PubMedArticle] = Field(
        default_factory=list,
        max_length=REPORT_PUBMED_ARTICLES_MAX,
    )
    ai_generated_sections: list[str] = Field(
        default_factory=list,
        max_length=REPORT_AI_GENERATED_SECTIONS_MAX,
    )
    locus_context: LocusContext | None = None
    in_silico_predictions: InSilicoPredictions | None = None
    acmg_criteria_scaffold: AcmgCriteriaScaffold | None = None
    curated_variants_distribution: CuratedVariantsDistribution | None = None
    associated_conditions: list[AssociatedCondition] = Field(
        default_factory=list,
        max_length=REPORT_ASSOCIATED_CONDITIONS_MAX,
    )
    publications_callout: PublicationsCallout | None = None
    publications_literature: PublicationLiterature | None = None
    functional_evidence: FunctionalEvidenceSummary | None = None
    population_frequency_detail: PopulationFrequencyDetail | None = None
    call_cards: VariantReportCallCards | None = None
    report_profile: VariantReportProfile | None = None
    eamos_computed_classification: EamosComputedClassification | None = None

    @field_serializer("associated_conditions", when_used="json")
    def _serialize_public_conditions(
        self,
        conditions: list[AssociatedCondition],
        info: Any,
    ) -> list[AssociatedCondition]:
        action = _serialization_policy_action(info)
        return [
            condition for condition in conditions if _source_fact_output_allowed(condition, action)
        ]


class RunResponse(BaseModel):
    run_id: str
    patient_id: str
    report_ids: list[str]
    run_status: RunStatus
    review_status: ReviewStatus
    report_payload: ReportPayload
    evidence: list[EvidenceSourceSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    review_note: str | None = None
    reviewed_at: datetime | None = None
    approved_pdf_path: str | None = None
