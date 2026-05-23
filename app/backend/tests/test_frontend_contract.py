"""Field-name parity test between Pydantic models and frontend TS interfaces.

Every Pydantic field on the in-scope models must appear as a key on its
matching ``export interface`` in ``app/frontend/src/lib/backend.ts``.

The check is asymmetric:
- TS may carry extra fields the backend does not declare (view-only state).
- Pydantic fields missing from TS fail the test — that's the contract drift
  the rebuilt frontend cannot tolerate (ReportPage / AIStack read these names).

When this test fails: rename the missing fields in ``backend.ts`` to match the
Pydantic models, then commit both sides together.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.schemas.chat import RunChatRequest, RunChatResponse
from app.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    WorkbenchContext,
    WorkbenchEdit,
)
from app.schemas.lookup import (
    LookupResponse,
    SearchInputAiExtraction,
    SearchInputCandidate,
    SearchInputInterpretation,
    SearchInputParseRequest,
    SearchInputParseResponse,
    SearchInputSourceInputs,
)
from app.schemas.gene_viewer import (
    AppliedVariant,
    ClinvarVariant,
    ExonVariantDensity,
    GeneViewerRequest,
    GeneViewerResponse,
    ProteinActiveSite,
    ProteinDomain,
    ProteinFeatures,
    ProteinPointFeature,
    ProteinRangeFeature,
    QueriedVariant,
    RestrictionSite,
    ViewerFeature,
    ViewerIdentity,
    ViewerLocus,
    ViewerProvenance,
    ViewerProvenanceSource,
    ViewerSegment,
    ViewerSequences,
    ViewerSummary,
    ViewerTracks,
    ViewerWindow,
    ViewerWindowRequest,
)
from app.schemas.run import (
    AcmgCriteriaScaffold,
    AcmgCriterion,
    AssociatedCondition,
    CodonCell,
    CuratedVariantsDistribution,
    EvidenceSourceSummary,
    FunctionalEvidenceSourceBreakdown,
    FunctionalEvidenceDisplayMetrics,
    FunctionalEvidenceSummary,
    FunctionalStudy,
    GeneContextRenderHints,
    GeneContextSnapshot,
    GeneContextTranscriptExon,
    GeneContextTranscriptIntron,
    GeneContextVariantProjection,
    GeneContextWorkbenchLink,
    InSilicoPredictions,
    LocusContext,
    NearbyVariant,
    PopulationAgeDistribution,
    PopulationAgeBin,
    PopulationAgeHistogram,
    PopulationAgeHistogramView,
    PopulationFrequencyAncestryGroup,
    PopulationFrequencyDetail,
    PopulationFrequencyReportSection,
    PopulationFrequencySourceRow,
    PopulationFrequencyVisualGroup,
    PopulationFrequencyVisualScale,
    PredictorCard,
    PublicationLiterature,
    PublicationSnippet,
    PublicationSourceBreakdown,
    PublicationsCallout,
    PubMedArticle,
    AcmgWorksheetCriterion,
    AcmgWorksheetLedger,
    ComputationalDeepDiveSection,
    ComputationalPredictorRow,
    DiseaseMechanismSection,
    InterpretationSummary,
    MolecularContextSection,
    ReportCallBadge,
    ReportCallCard,
    ReportCallInteraction,
    ReportExtractionPlan,
    ReportExtractionSectionTarget,
    ReportPayload,
    SourceProvenance,
    TherapiesTrialsSection,
    TrialMatch,
    VariantReportHeader,
    VariantReportCallCards,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.schemas.workbench import (
    AlignRequest,
    AlignResponse,
    CrisprGuide,
    CrisprRequest,
    CrisprResponse,
    HdrSsodn,
    PrimerPair,
    PrimerRequest,
    PrimerResponse,
    TraceChannel,
)

MODEL_TO_TS_INTERFACE: dict[type[BaseModel], str] = {
    LookupResponse: "LookupResponse",
    RunChatRequest: "RunChatRequest",
    RunChatResponse: "RunChatResponse",
    ReportPayload: "ReportPayload",
    EvidenceSourceSummary: "EvidenceSourceSummary",
    VariantSummaryRow: "VariantSummaryRow",
    PubMedArticle: "PubMedArticle",
    LocusContext: "LocusContext",
    NearbyVariant: "NearbyVariant",
    CodonCell: "CodonCell",
    InSilicoPredictions: "InSilicoPredictions",
    PredictorCard: "PredictorCard",
    AcmgCriterion: "AcmgCriterion",
    AcmgCriteriaScaffold: "AcmgCriteriaScaffold",
    CuratedVariantsDistribution: "CuratedVariantsDistribution",
    AssociatedCondition: "AssociatedCondition",
    PublicationsCallout: "PublicationsCallout",
    ChatRequest: "ChatRequest",
    ChatResponse: "ChatResponse",
    ChatMessage: "ChatMessage",
    WorkbenchContext: "WorkbenchContext",
    WorkbenchEdit: "WorkbenchEdit",
    PrimerRequest: "PrimerRequest",
    PrimerResponse: "PrimerResponse",
    PrimerPair: "PrimerPair",
    CrisprRequest: "CrisprRequest",
    CrisprResponse: "CrisprResponse",
    CrisprGuide: "CrisprGuide",
    HdrSsodn: "HdrSsodn",
    AlignRequest: "AlignRequest",
    AlignResponse: "AlignResponse",
    TraceChannel: "TraceChannel",
    ViewerWindowRequest: "ViewerWindowRequest",
    GeneViewerRequest: "GeneViewerRequest",
    ViewerIdentity: "ViewerIdentity",
    ViewerLocus: "ViewerLocus",
    ViewerSummary: "ViewerSummary",
    ViewerWindow: "ViewerWindow",
    ViewerSegment: "ViewerSegment",
    QueriedVariant: "QueriedVariant",
    AppliedVariant: "AppliedVariant",
    ViewerSequences: "ViewerSequences",
    ClinvarVariant: "ClinvarVariant",
    ExonVariantDensity: "ExonVariantDensity",
    ProteinDomain: "ProteinDomain",
    ProteinActiveSite: "ProteinActiveSite",
    ProteinRangeFeature: "ProteinRangeFeature",
    ProteinPointFeature: "ProteinPointFeature",
    ProteinFeatures: "ProteinFeatures",
    RestrictionSite: "RestrictionSite",
    ViewerFeature: "ViewerFeature",
    ViewerTracks: "ViewerTracks",
    ViewerProvenanceSource: "ViewerProvenanceSource",
    ViewerProvenance: "ViewerProvenance",
    GeneViewerResponse: "GeneViewerResponse",
    GeneContextTranscriptExon: "GeneContextTranscriptExon",
    GeneContextTranscriptIntron: "GeneContextTranscriptIntron",
    GeneContextVariantProjection: "GeneContextVariantProjection",
    GeneContextRenderHints: "GeneContextRenderHints",
    GeneContextWorkbenchLink: "GeneContextWorkbenchLink",
    GeneContextSnapshot: "GeneContextSnapshot",
}


BE6_REPORT_V2_FIELDS: dict[type[BaseModel], set[str]] = {
    CodonCell: {"aa_alt", "dna_ref", "dna_alt"},
    NearbyVariant: {"protein_change"},
    LocusContext: {"coords"},
    PredictorCard: {"verdict_label"},
    AcmgCriteriaScaffold: {"intro", "note"},
    CuratedVariantsDistribution: {"row_totals", "subtitle"},
    AssociatedCondition: {"db_tag", "db_tag_bold", "source_list"},
    PublicationsCallout: {"blurb"},
}


EPVLEX_PENDING_FRONTEND_MIRROR_FIELDS: dict[type[BaseModel], set[str]] = {
    PubMedArticle: {
        "pmcid",
        "doi",
        "publication_date",
        "snippets",
        "source_tags",
        "snippet_status",
    },
    ReportPayload: {
        "publications_literature",
        "functional_evidence",
        "population_frequency_detail",
        "call_cards",
        "report_profile",
    },
    LookupResponse: {"search_interpretation"},
}


EPVLEX_BACKEND_MODELS: dict[type[BaseModel], set[str]] = {
    PublicationSnippet: {"section", "text", "matched_terms", "source", "confidence"},
    PublicationSourceBreakdown: {"litvar2", "pubmed", "clinvar", "clingen"},
    PublicationLiterature: {
        "total_count",
        "shown_count",
        "offset",
        "limit",
        "sort",
        "variant_terms",
        "source_breakdown",
        "articles",
        "warnings",
    },
}


FUNCTIONAL_EVIDENCE_BACKEND_MODELS: dict[type[BaseModel], set[str]] = {
    FunctionalEvidenceSourceBreakdown: {"clingen", "clinvar", "pubmed"},
    FunctionalEvidenceDisplayMetrics: {
        "primary_label",
        "acmg_badge_text",
        "study_count_badge_text",
        "ui_color_theme",
    },
    FunctionalStudy: {
        "id",
        "pmid",
        "url",
        "citation",
        "source_tags",
        "evidence_codes",
        "asserted_codes",
        "snippet",
    },
    FunctionalEvidenceSummary: {
        "total_count",
        "source_breakdown",
        "evidence_codes",
        "source_asserted_codes",
        "display_metrics",
        "studies",
        "warnings",
    },
}


REPORT_CALL_CARD_BACKEND_MODELS: dict[type[BaseModel], set[str]] = {
    ReportCallBadge: {"text", "kind"},
    ReportCallInteraction: {
        "action",
        "target_section_id",
        "target_panel_id",
    },
    ReportCallCard: {
        "card_id",
        "title",
        "primary_label",
        "support_badges",
        "ui_color_theme",
        "source_status",
        "provenance",
        "warnings",
        "interaction",
    },
    VariantReportCallCards: {"cards"},
    PopulationFrequencyAncestryGroup: {
        "id",
        "allele_count",
        "allele_number",
        "allele_frequency",
        "homozygote_count",
    },
    PopulationAgeHistogram: {"bin_edges", "bin_freq", "n_smaller", "n_larger"},
    PopulationAgeDistribution: {"het", "hom"},
    PopulationFrequencyDetail: {
        "source",
        "dataset",
        "variant_id",
        "sequencing_type",
        "allele_frequency",
        "allele_count",
        "allele_number",
        "homozygote_count",
        "popmax_frequency",
        "popmax_population",
        "genetic_ancestry_groups",
        "age_distribution",
        "flags",
        "warnings",
        "source_url",
    },
}


SEARCH_INPUT_BACKEND_MODELS: dict[type[BaseModel], set[str]] = {
    SearchInputAiExtraction: {
        "gene",
        "gene_alias",
        "cdna",
        "transcript",
        "protein_change",
        "genomic_hint",
        "variant_class",
        "disease_context",
        "confidence",
        "assumptions",
        "warnings",
    },
    SearchInputSourceInputs: {
        "variant_validator",
        "ensembl_vep",
        "gnomad",
        "spliceai",
        "clinvar",
        "literature_terms",
    },
    SearchInputCandidate: {
        "candidate_id",
        "display_label",
        "gene",
        "cdna",
        "transcript",
        "protein_change",
        "genomic_hg38",
        "genomic_hgvs",
        "match_reason",
        "source_support",
        "source_count",
        "distance",
        "confidence",
        "warnings",
    },
    SearchInputInterpretation: {
        "submitted_text",
        "mode",
        "confidence",
        "gene",
        "cdna",
        "transcript",
        "protein_change",
        "normalized_query",
        "query_kind",
        "genomic_hg38",
        "genomic_hgvs",
        "source_inputs",
        "requires_confirmation",
        "exact_variant_available",
        "auto_selected_candidate_id",
        "candidates",
        "ui_prompt",
        "assumptions",
        "warnings",
        "provenance",
    },
    SearchInputParseRequest: {
        "search_text",
        "species",
        "allow_ai",
        "resolve_coordinates",
    },
    SearchInputParseResponse: {"interpretation"},
}


REPORT_PROFILE_BACKEND_MODELS: dict[type[BaseModel], set[str]] = {
    SourceProvenance: {
        "source",
        "status",
        "query",
        "source_url",
        "retrieved_at",
        "version",
        "warnings",
    },
    ReportExtractionSectionTarget: {
        "section_id",
        "match_level",
        "required_sources",
        "query_terms",
        "warnings",
    },
    ReportExtractionPlan: {
        "submitted_text",
        "mode",
        "canonical_identity",
        "source_query_bundle",
        "section_targets",
        "warnings",
        "provenance",
    },
    VariantReportHeader: {
        "display_name",
        "gene",
        "transcript",
        "cdna",
        "protein_change",
        "genomic_hg38",
        "classification",
        "classification_source",
        "verification_badges",
        "source_urls",
    },
    InterpretationSummary: {
        "mode",
        "text",
        "fact_refs",
        "warnings",
    },
    DiseaseMechanismSection: {
        "primary_condition",
        "disease_ids",
        "inheritance",
        "penetrance",
        "gene_disease_validity",
        "mechanism",
        "provenance",
        "warnings",
    },
    MolecularContextSection: {
        "chromosome",
        "strand",
        "exon",
        "codon_change",
        "protein_position",
        "domain",
        "hotspot_flag",
        "loeuf",
        "clingen_haploinsufficiency",
        "overlapping_cnvs",
        "provenance",
        "warnings",
    },
    ComputationalPredictorRow: {
        "name",
        "score",
        "threshold",
        "interpretation",
        "source",
        "version",
        "source_url",
        "warnings",
    },
    ComputationalDeepDiveSection: {
        "predictors",
        "spliceai_max_delta",
        "spliceai_consequence",
        "conservation",
        "provenance",
        "warnings",
    },
    AcmgWorksheetCriterion: {
        "code",
        "state",
        "strength",
        "assertion_level",
        "rationale",
        "source",
        "evidence_refs",
        "warnings",
    },
    AcmgWorksheetLedger: {
        "classification",
        "classification_source",
        "criteria",
        "synthesis",
        "disclaimer",
    },
    TrialMatch: {
        "nct_id",
        "title",
        "status",
        "phase",
        "conditions",
        "interventions",
        "locations",
        "match_level",
        "matched_terms",
        "source_url",
        "warnings",
    },
    TherapiesTrialsSection: {"trial_rows", "warnings", "provenance"},
    PopulationFrequencyVisualScale: {
        "basis",
        "min_value",
        "max_value",
        "max_group_id",
        "warnings",
    },
    PopulationFrequencyVisualGroup: {
        "id",
        "label",
        "allele_frequency",
        "allele_count",
        "allele_number",
        "homozygote_count",
        "is_popmax",
        "data_state",
        "sort_order",
        "warnings",
    },
    PopulationAgeBin: {
        "label",
        "lower_bound",
        "upper_bound",
        "count",
    },
    PopulationAgeHistogramView: {
        "genotype",
        "scope",
        "group_id",
        "bins",
        "n_smaller",
        "n_larger",
        "warnings",
    },
    PopulationFrequencySourceRow: {
        "group_id",
        "label",
        "allele_frequency",
        "allele_count",
        "allele_number",
        "homozygote_count",
        "is_popmax",
        "warnings",
    },
    PopulationFrequencyReportSection: {
        "section_number",
        "section_id",
        "panel_id",
        "title",
        "detail_ref",
        "source_status",
        "dataset",
        "genome_build",
        "variant_id",
        "sequencing_type",
        "visual_scale",
        "visual_groups",
        "age_histograms",
        "source_rows",
        "source_url",
        "warnings",
        "provenance",
    },
    GeneContextTranscriptExon: {
        "number",
        "cds_start",
        "cds_end",
        "genomic_start",
        "genomic_end",
        "genomic_length",
        "transcript_start",
        "transcript_end",
    },
    GeneContextTranscriptIntron: {
        "number",
        "genomic_start",
        "genomic_end",
        "length_bp",
        "transcript_start",
        "transcript_end",
    },
    GeneContextVariantProjection: {
        "hgvs_c",
        "hgvs_p",
        "cds_pos",
        "genomic_hg38",
        "ref",
        "alt",
        "exon_number",
        "intron_number",
        "membership",
        "transcript_offset",
        "codon_number",
        "codon_offset",
        "aa_ref",
        "aa_alt",
        "warnings",
    },
    GeneContextRenderHints: {
        "overview_mode",
        "min_exon_width_px",
        "max_intron_width_px",
        "zoom_flank_bp",
        "large_gene_compression_applied",
        "warnings",
    },
    GeneContextWorkbenchLink: {"url", "gene", "cdna", "transcript"},
    GeneContextSnapshot: {
        "section_number",
        "section_id",
        "panel_id",
        "title",
        "source_status",
        "gene",
        "transcript",
        "genome_build",
        "chromosome",
        "strand",
        "ensembl_gene_id",
        "gene_start",
        "gene_end",
        "gene_length",
        "cds_length",
        "protein_length",
        "exons",
        "introns",
        "variant",
        "zoom_window",
        "zoom_segments",
        "zoom_sequences",
        "render_hints",
        "workbench_link",
        "provenance",
        "warnings",
    },
    VariantReportProfile: {
        "extraction_plan",
        "header",
        "interpretation_summary",
        "disease_mechanism",
        "gene_context_snapshot",
        "population_frequency",
        "molecular_context",
        "computational_deep_dive",
        "acmg_worksheet",
        "therapies_trials",
        "provenance",
    },
}


def _backend_ts_path() -> Path:
    # tests/ -> backend/ -> app/ -> frontend/src/lib/backend.ts
    return Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "backend.ts"


def _extract_ts_interface_body(source: str, name: str) -> str:
    """Return the body slice between { and the matching } for the named interface."""
    match = re.search(rf"export\s+interface\s+{re.escape(name)}\s*\{{", source)
    if not match:
        raise AssertionError(f"export interface {name} not found in backend.ts")
    start = match.end()
    depth = 1
    i = start
    while i < len(source) and depth > 0:
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise AssertionError(f"unterminated interface {name} in backend.ts")
    return source[start : i - 1]


@pytest.mark.parametrize(
    "model,ts_name",
    list(MODEL_TO_TS_INTERFACE.items()),
    ids=lambda v: v if isinstance(v, str) else v.__name__,
)
def test_pydantic_field_names_present_in_typescript(model, ts_name):
    backend_ts = _backend_ts_path().read_text(encoding="utf-8")
    body = _extract_ts_interface_body(backend_ts, ts_name)

    pydantic_fields = set(model.model_fields.keys())
    missing = {
        field
        for field in pydantic_fields
        if not re.search(rf"^\s*{re.escape(field)}\??\s*:", body, re.MULTILINE)
    }
    missing -= EPVLEX_PENDING_FRONTEND_MIRROR_FIELDS.get(model, set())
    assert not missing, (
        f"{ts_name} (TS) is missing fields present on {model.__name__} "
        f"(Pydantic): {sorted(missing)}"
    )


@pytest.mark.parametrize(
    "model,fields",
    list(BE6_REPORT_V2_FIELDS.items()),
    ids=lambda v: v.__name__ if isinstance(v, type) else ",".join(sorted(v)),
)
def test_be6_report_v2_fields_are_declared_on_pydantic_models(model, fields):
    assert fields <= set(model.model_fields.keys())


@pytest.mark.parametrize(
    "model,fields",
    list(EPVLEX_BACKEND_MODELS.items()),
    ids=lambda v: v.__name__ if isinstance(v, type) else ",".join(sorted(v)),
)
def test_epvlex_backend_models_are_declared(model, fields):
    assert fields <= set(model.model_fields.keys())


@pytest.mark.parametrize(
    "model,fields",
    list(FUNCTIONAL_EVIDENCE_BACKEND_MODELS.items()),
    ids=lambda v: v.__name__ if isinstance(v, type) else ",".join(sorted(v)),
)
def test_functional_evidence_backend_models_are_declared(model, fields):
    assert fields <= set(model.model_fields.keys())


@pytest.mark.parametrize(
    "model,fields",
    list(REPORT_CALL_CARD_BACKEND_MODELS.items()),
    ids=lambda v: v.__name__ if isinstance(v, type) else ",".join(sorted(v)),
)
def test_report_call_card_backend_models_are_declared(model, fields):
    assert fields <= set(model.model_fields.keys())


@pytest.mark.parametrize(
    "model,fields",
    list(SEARCH_INPUT_BACKEND_MODELS.items()),
    ids=lambda v: v.__name__ if isinstance(v, type) else ",".join(sorted(v)),
)
def test_search_input_backend_models_are_declared(model, fields):
    assert fields <= set(model.model_fields.keys())


@pytest.mark.parametrize(
    "model,fields",
    list(REPORT_PROFILE_BACKEND_MODELS.items()),
    ids=lambda v: v.__name__ if isinstance(v, type) else ",".join(sorted(v)),
)
def test_report_profile_backend_models_are_declared(model, fields):
    assert fields <= set(model.model_fields.keys())


def test_epvlex_pending_frontend_mirror_fields_are_declared_on_backend_models():
    for model, fields in EPVLEX_PENDING_FRONTEND_MIRROR_FIELDS.items():
        assert fields <= set(model.model_fields.keys())
