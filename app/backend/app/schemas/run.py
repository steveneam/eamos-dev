from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.gene_viewer import ViewerSegment, ViewerSequences, ViewerWindow


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
FunctionalEvidenceSourceTag = Literal["clingen", "clinvar", "pubmed"]
FunctionalEvidenceCode = Literal["PS3", "BS3"]
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


class PublicationLiterature(BaseModel):
    total_count: int
    shown_count: int
    offset: int = 0
    limit: int = 5
    sort: Literal["publication_date_desc"] = "publication_date_desc"
    variant_terms: list[str] = Field(default_factory=list)
    source_breakdown: PublicationSourceBreakdown = Field(default_factory=PublicationSourceBreakdown)
    publication_timeline: PublicationTimeline = Field(default_factory=PublicationTimeline)
    articles: list[PubMedArticle] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FunctionalEvidenceSourceBreakdown(BaseModel):
    clingen: int = 0
    clinvar: int = 0
    pubmed: int = 0


class FunctionalEvidenceDisplayMetrics(BaseModel):
    primary_label: str = "No Functional Data Available"
    acmg_badge_text: str = "None"
    study_count_badge_text: str = "0 Unique"
    ui_color_theme: str = "neutral_slate_state"


class FunctionalStudy(BaseModel):
    id: str
    pmid: str | None = None
    url: str | None = None
    citation: str | None = None
    source_tags: list[FunctionalEvidenceSourceTag] = Field(default_factory=list)
    evidence_codes: list[FunctionalEvidenceCode] = Field(default_factory=list)
    asserted_codes: list[str] = Field(default_factory=list)
    snippet: str | None = None


class FunctionalEvidenceSummary(BaseModel):
    total_count: int
    source_breakdown: FunctionalEvidenceSourceBreakdown = Field(
        default_factory=FunctionalEvidenceSourceBreakdown
    )
    evidence_codes: list[FunctionalEvidenceCode] = Field(default_factory=list)
    source_asserted_codes: list[str] = Field(default_factory=list)
    display_metrics: FunctionalEvidenceDisplayMetrics = Field(
        default_factory=FunctionalEvidenceDisplayMetrics
    )
    studies: list[FunctionalStudy] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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


class AssociatedCondition(BaseModel):
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


SourceStatus = Literal[
    "live",
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
EvidenceAssertionLevel = Literal["source_asserted", "eamos_hint", "not_assessed"]


class SourceProvenance(BaseModel):
    source: str
    status: SourceStatus
    query: dict[str, str] = Field(default_factory=dict)
    source_url: str | None = None
    retrieved_at: datetime | None = None
    version: str | None = None
    warnings: list[str] = Field(default_factory=list)


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
    inheritance: str | None = None
    penetrance: str | None = None
    gene_disease_validity: str | None = None
    mechanism: str | None = None
    provenance: list[SourceProvenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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
    provenance: list[SourceProvenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ComputationalPredictorRow(BaseModel):
    name: str
    score: str | float | None = None
    threshold: str | float | None = None
    interpretation: str | None = None
    source: str
    version: str | None = None
    calibrated_label: str | None = None
    calibration_bucket: RampVerdict | None = None
    calibration_method: str | None = None
    calibration_version: str | None = None
    source_url: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ComputationalDeepDiveSection(BaseModel):
    predictors: list[ComputationalPredictorRow] = Field(default_factory=list)
    spliceai_max_delta: float | None = None
    spliceai_consequence: str | None = None
    conservation: list[ComputationalPredictorRow] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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


class TherapiesTrialsSection(BaseModel):
    trial_rows: list[TrialMatch] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)


class PopulationFrequencyVisualScale(BaseModel):
    basis: Literal["allele_frequency", "popmax_frequency"] = "allele_frequency"
    min_value: float = 0.0
    max_value: float | None = None
    max_group_id: str | None = None
    warnings: list[str] = Field(default_factory=list)


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
    dataset: str = ""
    genome_build: str = "GRCh38"
    variant_id: str = ""
    sequencing_type: PopulationSequencingType = "unknown"
    visual_scale: PopulationFrequencyVisualScale | None = None
    visual_groups: list[PopulationFrequencyVisualGroup] = Field(default_factory=list)
    age_histograms: list[PopulationAgeHistogramView] = Field(default_factory=list)
    source_rows: list[PopulationFrequencySourceRow] = Field(default_factory=list)
    source_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)


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
    render_hints: GeneContextRenderHints = Field(default_factory=GeneContextRenderHints)
    workbench_link: GeneContextWorkbenchLink | None = None
    provenance: list[SourceProvenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class VariantReportProfile(BaseModel):
    extraction_plan: ReportExtractionPlan | None = None
    header: VariantReportHeader | None = None
    interpretation_summary: InterpretationSummary | None = None
    disease_mechanism: DiseaseMechanismSection | None = None
    gene_context_snapshot: GeneContextSnapshot | None = None
    population_frequency: PopulationFrequencyReportSection | None = None
    molecular_context: MolecularContextSection | None = None
    computational_deep_dive: ComputationalDeepDiveSection | None = None
    acmg_worksheet: AcmgWorksheetLedger | None = None
    therapies_trials: TherapiesTrialsSection | None = None
    provenance: list[SourceProvenance] = Field(default_factory=list)


class ReportPayload(BaseModel):
    patient_id: str
    case_label: str | None = None
    report_title: str | None = None
    source_filenames: list[str] = Field(default_factory=list)
    patient_context: str | None = None
    clinical_phenotype: str | None = None
    ai_clinical_summary: str | None = None
    variant_summary_rows: list[VariantSummaryRow] = Field(default_factory=list)
    expanded_evidence: str | None = None
    acmg_classification: str | None = None
    clinical_integration: str | None = None
    expected_symptoms: str | None = None
    recommendations: str | None = None
    limitations: str | None = None
    variant_decoder: str | None = None
    therapeutic_landscape: str | None = None
    pubmed_articles: list[PubMedArticle] = Field(default_factory=list)
    ai_generated_sections: list[str] = Field(default_factory=list)
    locus_context: LocusContext | None = None
    in_silico_predictions: InSilicoPredictions | None = None
    acmg_criteria_scaffold: AcmgCriteriaScaffold | None = None
    curated_variants_distribution: CuratedVariantsDistribution | None = None
    associated_conditions: list[AssociatedCondition] = Field(default_factory=list)
    publications_callout: PublicationsCallout | None = None
    publications_literature: PublicationLiterature | None = None
    functional_evidence: FunctionalEvidenceSummary | None = None
    population_frequency_detail: PopulationFrequencyDetail | None = None
    call_cards: VariantReportCallCards | None = None
    report_profile: VariantReportProfile | None = None


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
