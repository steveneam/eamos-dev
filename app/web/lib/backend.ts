export type ReportKind = 'test' | 'patient'

export type ExtractionStatus = 'completed' | 'degraded' | 'blocked'

export type RunStatus = 'completed' | 'degraded' | 'blocked'

export type ReviewStatus = 'pending_review' | 'reviewed' | 'approved' | 'dropped'

export interface ExtractionIssue {
  code: string
  message: string
  severity: 'info' | 'warning' | 'error'
}

export interface ExtractedVariant {
  gene: string
  transcript_hgvs: string
  protein_change: string
  genomic_hg38: string
  variation_type: string
  consequence: string
}

export interface ExtractedCase {
  case_label: string
  report_title: string
  patient_context?: string | null
  clinical_findings?: string | null
  summary: string
  genome_build: string
  variants: ExtractedVariant[]
  issues: ExtractionIssue[]
}

export interface UploadedReport {
  report_id: string
  filename: string
  content_type: string
  size_bytes: number
  created_at: string
  report_kind: ReportKind
  source_pdf_path: string
  extraction_status: ExtractionStatus
  extracted_case: ExtractedCase
  extraction_warnings: string[]
}

export interface ReportUploadResponse {
  report: UploadedReport
}

export interface RunRequest {
  patient_id: string
  report_ids: string[]
}

export interface VariantSummaryRow {
  gene: string | null
  transcript_hgvs: string | null
  protein_change: string | null
  genomic_hg38: string | null
  variation_type: string | null
  consequence: string | null
}

export interface PubMedArticle {
  pmid: string
  title: string
  authors: string
  journal: string
  year: string
  url: string
  abstract?: string | null
  pmcid?: string | null
  doi?: string | null
  publication_date?: string | null
  snippets?: PublicationSnippet[]
  source_tags?: PublicationSourceTag[]
  snippet_status?: string | null
}

export interface ReportPayload {
  patient_id: string
  case_label?: string | null
  report_title?: string | null
  source_filenames?: string[]
  patient_context?: string | null
  clinical_phenotype: string | null
  ai_clinical_summary: string | null
  variant_summary_rows: VariantSummaryRow[]
  expanded_evidence: string | null
  acmg_classification: string | null
  clinical_integration: string | null
  expected_symptoms: string | null
  recommendations: string | null
  limitations: string | null
  variant_decoder?: string | null
  therapeutic_landscape?: string | null
  pubmed_articles?: PubMedArticle[]
  ai_generated_sections?: string[]
  locus_context?: LocusContext | null
  in_silico_predictions?: InSilicoPredictions | null
  acmg_criteria_scaffold?: AcmgCriteriaScaffold | null
  curated_variants_distribution?: CuratedVariantsDistribution | null
  associated_conditions?: AssociatedCondition[]
  publications_callout?: PublicationsCallout | null
  publications_literature?: PublicationLiterature | null
  functional_evidence?: FunctionalEvidenceSummary | null
  population_frequency_detail?: PopulationFrequencyDetail | null
  call_cards?: VariantReportCallCards | null
  report_profile?: VariantReportProfile | null
}

export interface EvidenceSourceSummary {
  source: string
  status: string
  request_identity: Record<string, unknown>
  summary: Record<string, unknown>
  warnings: string[]
  source_url?: string | null
  fetched_at?: string | null
  source_version?: string | null
  cache_status?: string | null
}

export interface RunResponse {
  run_id: string
  patient_id: string
  report_ids: string[]
  run_status: RunStatus
  review_status: ReviewStatus
  report_payload: ReportPayload
  evidence: EvidenceSourceSummary[]
  warnings: string[]
  review_note: string | null
  reviewed_at: string | null
  approved_pdf_path: string | null
}

export interface ClinicianReviewPayload {
  reviewer_name?: string | null
  review_note: string
}

export interface ReportDraftUpdatePayload {
  patient_context?: string | null
  clinical_phenotype?: string | null
  ai_clinical_summary?: string | null
  expanded_evidence?: string | null
  acmg_classification?: string | null
  clinical_integration?: string | null
  expected_symptoms?: string | null
  recommendations?: string | null
  therapeutic_landscape?: string | null
  limitations?: string | null
  review_note?: string | null
}

export interface ReviewResult {
  run_id: string
  review_status: 'reviewed'
  review_note: string
  reviewed_at: string
}

export interface ApproveResult {
  run_id: string
  review_status: 'approved'
  review_note: string | null
  reviewed_at: string | null
  download_path: string
}

export interface DropResult {
  run_id: string
  review_status: 'dropped'
  review_note: string | null
  reviewed_at: string | null
}

export type SearchInputMode =
  | 'structured'
  | 'deterministic'
  | 'ai_assisted'
  | 'auto_resolved'
  | 'needs_selection'
  | 'suggestions'

export type SearchInputConfidence = 'high' | 'medium' | 'low'

export type SearchInputVariantClass =
  | 'snv'
  | 'missense'
  | 'nonsense'
  | 'frameshift'
  | 'splice'
  | 'deletion'
  | 'insertion'
  | 'duplication'
  | 'delins'
  | 'unknown'

export interface SearchInputAiExtraction {
  gene?: string | null
  gene_alias?: string | null
  cdna?: string | null
  transcript?: string | null
  protein_change?: string | null
  genomic_hint?: string | null
  variant_class: SearchInputVariantClass
  disease_context?: string | null
  confidence: SearchInputConfidence
  assumptions: string[]
  warnings: string[]
}

export interface SearchInputSourceInputs {
  variant_validator?: string | null
  ensembl_vep?: string | null
  gnomad?: string | null
  spliceai?: string | null
  clinvar?: string | null
  literature_terms: string[]
}

export interface SearchInputCoordinateResolutionAudit {
  resolver_path: string
  coordinate_resolution_requested: boolean
  used_eamos_local: boolean
  used_variant_validator: boolean
  used_clinvar_for_coordinates: boolean
  used_submitted_genomic: boolean
  used_rsid_candidates: boolean
  canonical_variant_id?: string | null
  genomic_hgvs?: string | null
  local_source?: string | null
  variant_validator_url?: string | null
  clinvar_role?: string | null
  provenance: string[]
  warnings: string[]
}

export interface SearchInputCandidate {
  candidate_id: string
  display_label: string
  gene: string
  cdna?: string | null
  transcript?: string | null
  protein_change?: string | null
  genomic_hg38?: string | null
  genomic_hgvs?: string | null
  match_reason: string
  source_support: string[]
  source_count: number
  distance?: string | null
  confidence: SearchInputConfidence
  warnings: string[]
}

export interface SearchInputInterpretation {
  submitted_text: string
  mode: SearchInputMode
  confidence: SearchInputConfidence
  gene?: string | null
  cdna?: string | null
  transcript?: string | null
  protein_change?: string | null
  normalized_query?: string | null
  query_kind?: string | null
  genomic_hg38?: string | null
  genomic_hgvs?: string | null
  source_inputs?: SearchInputSourceInputs | null
  coordinate_resolution_audit?: SearchInputCoordinateResolutionAudit | null
  requires_confirmation: boolean
  exact_variant_available: boolean
  auto_selected_candidate_id?: string | null
  candidates: SearchInputCandidate[]
  ui_prompt?: string | null
  assumptions: string[]
  warnings: string[]
  provenance: string[]
}

export interface SearchInputParseRequest {
  search_text: string
  species: 'human' | 'mouse'
  allow_ai?: boolean
  resolve_coordinates?: boolean
}

export interface SearchInputParseResponse {
  interpretation: SearchInputInterpretation
}

export interface LookupRequest {
  search_text?: string | null
  query?: string | null
  gene?: string | null
  cdna?: string | null
  transcript?: string | null
  protein_change?: string | null
  species: 'human' | 'mouse'
  confirmed_interpretation?: boolean
  selected_candidate_id?: string | null
}

export interface LookupResponse {
  query: string
  species: string
  report_payload: ReportPayload
  evidence: EvidenceSourceSummary[]
  warnings: string[]
  search_interpretation?: SearchInputInterpretation | null
}

// ─── M11 lookup section-fetch contract ───
// Mirror of app/backend/app/schemas/lookup.py (LookupSection*, LookupSummaryTile,
// LookupInitialSummaryResponse, LookupSectionFetchRequest/Response).
// Backend-led: FE does not reshape payloads. `payload` on LookupSectionEnvelope
// is intentionally Record<string, unknown> | null — consumers type-narrow per
// section_id at the read site against the existing ReportPayload sub-types
// (PublicationLiteratureshape for 'publications', ComputationalDeepDive for
// 'computational_deep_dive', AcmgWorksheet + {narrative, source_scope} for
// 'clingen_vcep').
export type LookupSectionId =
  | 'publications'
  | 'computational_deep_dive'
  | 'clingen_vcep'

export type LookupSectionStatus = 'available' | 'partial' | 'missing'

export interface LookupSummaryTile {
  tile_id: string
  title: string
  primary_label: string
  support_badges: string[]
  source_status: string
  ui_color_theme: string
  target_section_id?: string | null
  target_panel_id?: string | null
  fetch_section_id?: LookupSectionId | null
  warnings: string[]
}

export interface LookupSectionDescriptor {
  section_id: LookupSectionId
  endpoint: string
  include_value: LookupSectionId
  hydration: 'expand'
}

export interface LookupInitialSummaryResponse {
  query: string
  species: string
  header?: Record<string, unknown> | null
  tiles: LookupSummaryTile[]
  lazy_sections: LookupSectionDescriptor[]
  warnings: string[]
}

export interface LookupSectionFetchRequest extends LookupRequest {
  include: LookupSectionId[]
}

export interface LookupSectionFreshness {
  fetched_at?: string | null
  source_version?: string | null
  stale_on_failure: boolean
  source_status?: string | null
  source_url?: string | null
}

export interface LookupSectionEnvelope {
  section_id: LookupSectionId
  status: LookupSectionStatus
  payload?: Record<string, unknown> | null
  freshness: LookupSectionFreshness
  warnings: string[]
}

export interface LookupSectionFetchResponse {
  query: string
  species: string
  sections: Partial<Record<LookupSectionId, LookupSectionEnvelope>>
  warnings: string[]
}

export interface RunChatRequest {
  question: string
}

export interface RunChatCitation {
  title: string
  snippet: string
  source_type: 'run_section' | 'report_extract' | 'evidence'
  section: string | null
}

export interface RunChatResponse {
  question: string
  answer: string
  grounded: boolean
  citations: RunChatCitation[]
}

export interface HealthzResponse {
  status: string
  database: string
  llm_provider: string
  use_real_apis: boolean
}

// ─────────────────────────────────────────────────────────────
// Report v2 modules — mirrors app/backend/app/schemas/run.py
// ─────────────────────────────────────────────────────────────

export type ClassificationTier =
  | 'pathogenic'
  | 'likely_pathogenic'
  | 'vus'
  | 'likely_benign'
  | 'benign'

export type RampVerdict =
  | 'Pathogenic'
  | 'Likely pathogenic'
  | 'VUS'
  | 'Likely benign'
  | 'Benign'

export type AcmgVerdictTier = 'met' | 'not_met' | 'not_assessed'
export type PredictorVerdict = 'damaging' | 'tolerated' | 'uncertain'

export interface NearbyVariant {
  cds_pos: number
  classification: ClassificationTier
  hgvs: string
  clinvar_id?: string | null
  protein_change?: string | null
}

export interface CodonCell {
  codon_number: number
  aa_ref: string
  aa_alt?: string | null
  dna_ref?: string
  dna_alt?: string | null
  is_query?: boolean
}

export interface LocusContext {
  gene: string
  centre_cdna: string
  coords?: string
  nearby_variants: NearbyVariant[]
  codon_strip: CodonCell[]
}

export interface PredictorCard {
  name: 'REVEL' | 'AlphaMissense' | 'MetaLR' | 'SpliceAI'
  score: number
  threshold: number
  verdict: PredictorVerdict
  verdict_label?: string
  source_url?: string | null
}

export interface InSilicoPredictions {
  cards: PredictorCard[]
  consensus_note: string
}

export type AcmgCode =
  | 'PVS1'
  | 'PS1' | 'PS2' | 'PS3' | 'PS4'
  | 'PM1' | 'PM2' | 'PM3' | 'PM4' | 'PM5' | 'PM6'
  | 'PP1' | 'PP2' | 'PP3' | 'PP4' | 'PP5'
  | 'BA1'
  | 'BS1' | 'BS2' | 'BS3' | 'BS4'
  | 'BP1' | 'BP2' | 'BP3' | 'BP4' | 'BP5' | 'BP6' | 'BP7'

export interface AcmgCriterion {
  code: AcmgCode
  verdict: AcmgVerdictTier
  note?: string | null
}

export interface AcmgCriteriaScaffold {
  criteria: AcmgCriterion[]
  intro?: string
  note?: string
  disclaimer: string
}

export interface CuratedVariantsDistribution {
  cells: Record<string, number>
  row_totals?: Record<string, number>
  total: number
  subtitle?: string
  reading: string
}

export type EvidenceLevel = 'definitive' | 'strong' | 'moderate' | 'limited'
export type InheritancePattern = 'AR' | 'AD' | 'XL' | 'MT'

export interface AssociatedCondition {
  name: string
  case_count: number
  evidence_level: EvidenceLevel
  inheritance: InheritancePattern
  source: string
  db_tag?: string
  db_tag_bold?: string | null
  source_list?: string
}

export interface PublicationsCallout {
  total_count: number
  scholar_url: string
  blurb?: string
  ai_summary_prompt: string
  scope_counts?: PublicationScopeCounts | null
}

export type PublicationSourceTag = 'litvar2' | 'pubmed' | 'clinvar' | 'clingen'
export type PublicationScope = 'variant' | 'gene'
export type PublicationCountKind =
  | 'deduped_pmids'
  | 'gene_wide_source_count'
  | 'unavailable'
export type PublicationSnippetConfidence =
  | 'exact_variant'
  | 'variant_alias'
  | 'rsid'
  | 'gene_variant_context'
  | 'reported_no_text'

export interface PublicationSnippet {
  section: string
  text: string
  matched_terms: string[]
  source: string
  confidence: PublicationSnippetConfidence
}

export interface PublicationSourceBreakdown {
  litvar2: number
  pubmed: number
  clinvar: number
  clingen: number
}

export interface PublicationYearCount {
  year: number
  count: number
}

export interface PublicationTimeline {
  publications_by_year: PublicationYearCount[]
  total_with_year: number
  total_without_year: number
}

export interface PublicationScopeCount {
  scope: PublicationScope
  total_count?: number | null
  count_kind: PublicationCountKind
  query?: string | null
  source_status?: string | null
  source_breakdown: PublicationSourceBreakdown
  warnings: string[]
}

export interface PublicationScopeCounts {
  variant: PublicationScopeCount
  gene: PublicationScopeCount
}

export interface PublicationLiterature {
  total_count: number
  shown_count: number
  offset: number
  limit: number
  scope?: PublicationScope
  sort: string
  variant_terms: string[]
  source_breakdown: PublicationSourceBreakdown
  publication_timeline: PublicationTimeline
  scope_counts?: PublicationScopeCounts | null
  articles: PubMedArticle[]
  warnings: string[]
}

export interface FunctionalEvidenceSourceBreakdown {
  clingen: number
  clinvar: number
  pubmed: number
}

export interface FunctionalEvidenceConflictSplit {
  deficit: number
  normal: number
}

export interface FunctionalEvidenceCodeRestsOn {
  cited: number
  total: number
}

export interface FunctionalEvidenceDisplayMetrics {
  state: string
  primary_label: string
  acmg_badge_text: string
  verdict_source: string
  study_count_badge_text: string
  conflict_split?: FunctionalEvidenceConflictSplit | null
  code_rests_on?: FunctionalEvidenceCodeRestsOn | null
  ui_color_theme: string
}

export interface FunctionalStudy {
  id: string
  pmid?: string | null
  url?: string | null
  citation?: string | null
  source_tags: string[]
  evidence_codes: string[]
  asserted_codes: string[]
  snippet?: string | null
}

export interface FunctionalEvidenceSummary {
  total_count: number
  source_breakdown: FunctionalEvidenceSourceBreakdown
  evidence_codes: string[]
  source_asserted_codes: string[]
  display_metrics: FunctionalEvidenceDisplayMetrics
  studies: FunctionalStudy[]
  warnings: string[]
}

export type ReportCallCardId =
  | 'population_frequency'
  | 'computational'
  | 'lab_functional'
  | 'clinical_consensus'
export type ReportCallBadgeKind = 'acmg' | 'metric' | 'source' | 'warning' | 'neutral'
export type PopulationSequencingType = 'joint' | 'exome' | 'genome' | 'unknown'

export interface ReportCallBadge {
  text: string
  kind: ReportCallBadgeKind
}

export interface ReportCallInteraction {
  action: 'none' | 'scroll' | 'scroll_and_expand'
  target_section_id?: string | null
  target_panel_id?: string | null
}

export interface ReportCallCard {
  card_id: ReportCallCardId
  title: string
  primary_label: string
  support_badges: ReportCallBadge[]
  ui_color_theme: string
  source_status: string
  provenance: string[]
  warnings: string[]
  interaction?: ReportCallInteraction | null
}

export interface VariantReportCallCards {
  cards: ReportCallCard[]
}

export interface PopulationFrequencyAncestryGroup {
  id: string
  allele_count?: number | null
  allele_number?: number | null
  allele_frequency?: number | null
  homozygote_count?: number | null
}

export interface PopulationAgeHistogram {
  bin_edges: number[]
  bin_freq: number[]
  n_smaller?: number | null
  n_larger?: number | null
}

export interface PopulationAgeDistribution {
  het?: PopulationAgeHistogram | null
  hom?: PopulationAgeHistogram | null
}

export interface PopulationSequencingAgeDistribution {
  sequencing_type: PopulationSequencingType
  age_distribution: PopulationAgeDistribution
}

export interface PopulationFrequencyDetail {
  source: string
  dataset: string
  variant_id: string
  sequencing_type: PopulationSequencingType
  allele_frequency?: number | null
  allele_count?: number | null
  allele_number?: number | null
  homozygote_count?: number | null
  popmax_frequency?: number | null
  popmax_population?: string | null
  genetic_ancestry_groups: PopulationFrequencyAncestryGroup[]
  age_distribution?: PopulationAgeDistribution | null
  age_distributions: PopulationSequencingAgeDistribution[]
  flags: string[]
  warnings: string[]
  source_url?: string | null
}

export type SourceStatus =
  | 'live'
  | 'cache'
  | 'stale'
  | 'fixture'
  | 'fallback'
  | 'missing'
  | 'live_stub'
  | 'error'
  | 'failed'
export type ReportMatchLevel = 'variant_level' | 'gene_level' | 'disease_level' | 'unavailable'
export type EvidenceAssertionLevel =
  | 'source_asserted'
  | 'vcep_specified'
  | 'eamos_hint'
  | 'not_assessed'
export type ExpertPanelClassification =
  | 'pathogenic'
  | 'likely_pathogenic'
  | 'vus'
  | 'likely_benign'
  | 'benign'
  | 'conflicting'
  | 'not_classified'
export type ExpertPanelFreshness = 'fresh' | 'stale' | 'unknown'
export type ExpertPanelFreshnessReason =
  | 'cache_hit'
  | 'stale_on_failure'
  | 'tile_only'

export interface SourceProvenance {
  source: string
  status: SourceStatus
  query: Record<string, string>
  source_url?: string | null
  retrieved_at?: string | null
  version?: string | null
  warnings: string[]
}

export interface ExpertPanelVcep {
  id: string
  name: string
  affiliation_id?: string | null
  last_curated_date: string
  vcep_url: string
}

export interface ExpertPanelCriterion {
  code: string
  applied_strength: string
  default_strength: string
  state: 'met' | 'not_met' | 'not_assessed' | 'conflicting'
  assertion_level: EvidenceAssertionLevel
  rationale?: string | null
  source?: string | null
  evidence_refs: string[]
  warnings: string[]
}

export interface ExpertPanelProvenance {
  source_url: string
  fetched_at: string
  source_version: string
  cache_record_id?: string | null
  raw_jsonld_ref?: string | null
}

export interface ExpertPanelSection {
  vcep: ExpertPanelVcep
  final_classification: ExpertPanelClassification
  narrative: string
  criteria: ExpertPanelCriterion[]
  source_scope: string
  provenance: ExpertPanelProvenance
  freshness: ExpertPanelFreshness
  freshness_reason?: ExpertPanelFreshnessReason | null
}

export interface ReportExtractionSectionTarget {
  section_id: string
  match_level: ReportMatchLevel
  required_sources: string[]
  query_terms: string[]
  warnings: string[]
}

export interface ReportExtractionPlan {
  submitted_text: string
  mode: string
  canonical_identity: Record<string, string>
  source_query_bundle: Record<string, string | string[] | null>
  section_targets: ReportExtractionSectionTarget[]
  warnings: string[]
  provenance: string[]
}

export interface VariantReportHeader {
  display_name: string
  gene: string
  transcript?: string | null
  cdna?: string | null
  protein_change?: string | null
  genomic_hg38?: string | null
  classification?: string | null
  classification_source?: string | null
  verification_badges: string[]
  source_urls: string[]
}

export interface InterpretationSummary {
  mode: 'deterministic' | 'llm_rewrite' | 'unavailable'
  text: string
  fact_refs: string[]
  warnings: string[]
}

export interface DiseaseMechanismSection {
  primary_condition?: string | null
  disease_ids: string[]
  inheritance?: string | null
  penetrance?: string | null
  gene_disease_validity?: string | null
  mechanism?: string | null
  provenance: SourceProvenance[]
  warnings: string[]
}

export interface MolecularContextSection {
  chromosome?: string | null
  strand?: string | null
  exon?: string | null
  codon_change?: string | null
  protein_position?: string | null
  domain?: string | null
  hotspot_flag?: boolean | null
  loeuf?: number | null
  clingen_haploinsufficiency?: string | null
  overlapping_cnvs: string[]
  protein_domain_track?: ProteinDomainTrack | null
  provenance: SourceProvenance[]
  warnings: string[]
}

export interface ComputationalPredictorRow {
  name: string
  score?: string | number | null
  threshold?: string | number | null
  interpretation?: string | null
  source: string
  version?: string | null
  calibrated_label?: string | null
  calibration_bucket?: RampVerdict | null
  calibration_method?: string | null
  calibration_version?: string | null
  source_url?: string | null
  warnings: string[]
}

export interface ComputationalDeepDiveSection {
  predictors: ComputationalPredictorRow[]
  spliceai_max_delta?: number | null
  spliceai_consequence?: string | null
  conservation: ComputationalPredictorRow[]
  provenance: SourceProvenance[]
  warnings: string[]
}

export interface AcmgWorksheetCriterion {
  code: string
  state: 'met' | 'not_met' | 'not_assessed' | 'conflicting'
  strength?: string | null
  assertion_level: EvidenceAssertionLevel
  rationale?: string | null
  source?: string | null
  evidence_refs: string[]
  warnings: string[]
}

export interface AcmgWorksheetLedger {
  classification?: string | null
  classification_source?: string | null
  criteria: AcmgWorksheetCriterion[]
  synthesis?: string | null
  disclaimer: string
}

export interface TrialMatch {
  nct_id: string
  title: string
  status?: string | null
  phase?: string | null
  conditions: string[]
  interventions: string[]
  locations: string[]
  match_level: ReportMatchLevel
  matched_terms: string[]
  source_url: string
  warnings: string[]
}

export interface TherapiesTrialsSection {
  trial_rows: TrialMatch[]
  warnings: string[]
  provenance: SourceProvenance[]
}

export interface PopulationFrequencyVisualScale {
  basis: 'allele_frequency' | 'popmax_frequency'
  min_value: number
  max_value?: number | null
  max_group_id?: string | null
  warnings: string[]
}

export interface PopulationFrequencyDatasetCell {
  allele_frequency?: number | null
  allele_count?: number | null
  allele_number?: number | null
  homozygote_count?: number | null
}

// Per-group sex split (gnomAD XX/XY). Optional: present only once the backend
// surfaces the sex-disaggregated populations (see Codex contract). Same metric
// shape as the group's own Overall row.
export interface PopulationFrequencySexCell {
  allele_frequency?: number | null
  allele_count?: number | null
  allele_number?: number | null
  homozygote_count?: number | null
}

export interface PopulationFrequencyOverallTotalCell {
  allele_frequency?: number | null
  allele_count?: number | null
  allele_number?: number | null
  homozygote_count?: number | null
  exome?: PopulationFrequencyDatasetCell | null
  genome?: PopulationFrequencyDatasetCell | null
}

// Whole-cohort aggregate (gnomAD's Total row + cohort-wide XX/XY), independent of
// any single ancestry group. Optional until the backend surfaces it.
export interface PopulationFrequencyOverall {
  total?: PopulationFrequencyOverallTotalCell | null
  xx?: PopulationFrequencySexCell | null
  xy?: PopulationFrequencySexCell | null
}

export interface PopulationFrequencyVisualGroup {
  id: string
  label: string
  allele_frequency?: number | null
  allele_count?: number | null
  allele_number?: number | null
  homozygote_count?: number | null
  is_popmax: boolean
  data_state: 'observed' | 'zero_observed' | 'not_reported' | 'filtered'
  sort_order?: number | null
  xx?: PopulationFrequencySexCell | null
  xy?: PopulationFrequencySexCell | null
  exome?: PopulationFrequencyDatasetCell | null
  genome?: PopulationFrequencyDatasetCell | null
  warnings: string[]
}

export interface PopulationAgeBin {
  label: string
  lower_bound?: number | null
  upper_bound?: number | null
  count: number
}

export interface PopulationAgeHistogramView {
  sequencing_type: PopulationSequencingType
  series_kind: 'variant_carriers' | 'all_individuals'
  genotype: 'heterozygous_alternate' | 'homozygous_alternate' | 'combined' | 'not_applicable'
  scope: 'overall_release_samples' | 'genetic_ancestry_group'
  group_id?: string | null
  bins: PopulationAgeBin[]
  n_smaller?: number | null
  n_larger?: number | null
  warnings: string[]
}

export interface PopulationFrequencySourceRow {
  group_id: string
  label: string
  allele_frequency?: number | null
  allele_count?: number | null
  allele_number?: number | null
  homozygote_count?: number | null
  is_popmax: boolean
  warnings: string[]
}

export interface PopulationFrequencyReportSection {
  section_number: number
  section_id: string
  panel_id: string
  title: string
  detail_ref: 'population_frequency_detail'
  source_status: string
  dataset: string
  genome_build: string
  variant_id: string
  sequencing_type: PopulationSequencingType
  visual_scale?: PopulationFrequencyVisualScale | null
  visual_groups: PopulationFrequencyVisualGroup[]
  overall?: PopulationFrequencyOverall | null
  age_histograms: PopulationAgeHistogramView[]
  source_rows: PopulationFrequencySourceRow[]
  source_url?: string | null
  warnings: string[]
  provenance: SourceProvenance[]
}

export type GeneContextVariantMembership = 'exon' | 'intron' | 'outside_transcript' | 'unknown'
export type GeneContextOverviewMode = 'compressed_introns' | 'linear'

export interface GeneContextTranscriptExon {
  number: number
  cds_start?: number | null
  cds_end?: number | null
  genomic_start?: number | null
  genomic_end?: number | null
  genomic_length?: number | null
  transcript_start?: number | null
  transcript_end?: number | null
}

export interface GeneContextTranscriptIntron {
  number: number
  genomic_start?: number | null
  genomic_end?: number | null
  length_bp?: number | null
  transcript_start?: number | null
  transcript_end?: number | null
}

export interface GeneContextVariantProjection {
  hgvs_c?: string | null
  hgvs_p?: string | null
  cds_pos?: number | null
  genomic_hg38?: string | null
  ref?: string | null
  alt?: string | null
  exon_number?: number | null
  intron_number?: number | null
  membership: GeneContextVariantMembership
  transcript_offset?: number | null
  codon_number?: number | null
  codon_offset?: number | null
  aa_ref?: string | null
  aa_alt?: string | null
  warnings: string[]
}

export interface GeneContextRenderHints {
  overview_mode: GeneContextOverviewMode
  min_exon_width_px: number
  max_intron_width_px: number
  zoom_flank_bp: number
  large_gene_compression_applied: boolean
  warnings: string[]
}

export interface GeneContextWorkbenchLink {
  url: string
  gene: string
  cdna: string
  transcript?: string | null
}

export interface GeneContextSnapshot {
  section_number: number
  section_id: string
  panel_id: string
  title: string
  source_status: SourceStatus
  gene: string
  transcript?: string | null
  genome_build: string
  chromosome?: string | null
  strand: GenomeStrand
  ensembl_gene_id?: string | null
  gene_start?: number | null
  gene_end?: number | null
  gene_length?: number | null
  cds_length?: number | null
  protein_length?: number | null
  exons: GeneContextTranscriptExon[]
  introns: GeneContextTranscriptIntron[]
  variant?: GeneContextVariantProjection | null
  zoom_window?: ViewerWindow | null
  zoom_segments: ViewerSegment[]
  zoom_sequences?: ViewerSequences | null
  protein_domain_track?: ProteinDomainTrack | null
  render_hints: GeneContextRenderHints
  workbench_link?: GeneContextWorkbenchLink | null
  provenance: SourceProvenance[]
  warnings: string[]
}

export interface VariantReportProfile {
  extraction_plan?: ReportExtractionPlan | null
  header?: VariantReportHeader | null
  interpretation_summary?: InterpretationSummary | null
  disease_mechanism?: DiseaseMechanismSection | null
  gene_context_snapshot?: GeneContextSnapshot | null
  population_frequency?: PopulationFrequencyReportSection | null
  molecular_context?: MolecularContextSection | null
  computational_deep_dive?: ComputationalDeepDiveSection | null
  acmg_worksheet?: AcmgWorksheetLedger | null
  expert_panel?: ExpertPanelSection | null
  therapies_trials?: TherapiesTrialsSection | null
  provenance: SourceProvenance[]
}

// ─────────────────────────────────────────────────────────────
// Lookup/Workbench-scoped chat — mirrors app/backend/app/schemas/chat.py
// (Existing run-scoped RunChatRequest/Response above unchanged.)
// ─────────────────────────────────────────────────────────────

export type WorkbenchTool = 'viewer' | 'primer' | 'crispr' | 'align' | 'compare'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface WorkbenchEdit {
  position: number
  ref_base: 'A' | 'T' | 'C' | 'G'
  new_base: 'A' | 'T' | 'C' | 'G' | 'del'
  consequence: string
}

export interface WorkbenchContext {
  active_tool: WorkbenchTool
  scratchpad: WorkbenchEdit[]
  selected_primer_pair?: number | null
  selected_guide?: number | null
}

export interface ChatRequest {
  question: string
  variant_context: ReportPayload
  history?: ChatMessage[]
  workbench?: WorkbenchContext | null
}

export interface ChatResponse {
  answer: string
}

// ─────────────────────────────────────────────────────────────
// Workbench engine endpoints — mirrors app/backend/app/schemas/workbench.py
// (Stubbed responses for v2; real engines deferred to M-002.)
// ─────────────────────────────────────────────────────────────

export type PrimerMode = 'sanger' | 'qpcr' | 'arms'

export interface PrimerRequest {
  gene: string
  cdna: string
  mode?: PrimerMode
  tm_min?: number
  tm_max?: number
  product_size_min?: number
  product_size_max?: number
  avoid_snps?: boolean
}

export interface PrimerPair {
  index: number
  forward: string
  reverse: string
  tm_forward: number
  tm_reverse: number
  gc_forward: number
  gc_reverse: number
  product_size: number
  specificity_hits: number
  notes?: string
  recommended?: boolean
}

export interface PrimerResponse {
  mode: PrimerMode
  pairs: PrimerPair[]
}

export type CasEnzyme = 'SpCas9' | 'SaCas9' | 'Cas12a'

export interface CrisprRequest {
  gene: string
  cdna: string
  cas?: CasEnzyme
  strand_filter?: 'both' | 'plus' | 'minus'
  off_target_tolerance?: number
}

export interface CrisprGuide {
  index: number
  cut_position: number
  strand: '+' | '-'
  guide: string
  pam: string
  on_target_score: number
  off_target_score: number
  gc_percent: number
  notes?: string
}

export interface HdrSsodn {
  reference_arm: string
  variant_arm: string
  repair_template: string
  edits_encoded: string[]
  arm_lengths: Record<string, number>
  estimated_hdr_efficiency: number
}

export interface CrisprResponse {
  cas: CasEnzyme
  guides: CrisprGuide[]
  ssodn?: HdrSsodn | null
}

export interface AlignRequest {
  gene: string
  cdna: string
  user_sequence?: string | null
  ab1_blob_base64?: string | null
}

export interface TraceChannel {
  base: 'A' | 'T' | 'C' | 'G'
  values: number[]
}

export interface AlignResponse {
  reference: string
  sanger_read: string
  match_line: string
  mismatch_positions: number[]
  target_position: number
  trace_channels: TraceChannel[]
  base_calls: string[]
  q_scores: number[]
}

// ─── Gene viewer (POST /api/v1/viewer) ──────────────────────────────────
// Mirror of app/backend/app/schemas/gene_viewer.py (Codex-authored = the
// backend-led contract source; this file only mirrors it, never reshapes it).
// snake_case fields match the Pydantic models; lib/workbench/gene-viewer-
// adapter.ts maps this into the camelCase GeneWindowData renderer shape.
// Contract canary: app/backend/tests/test_frontend_contract.py (Codex extends).

export type AlleleMode = 'reference' | 'variant'
export type GenomeStrand = '+' | '-' | 'unknown'
export type ViewerTrack =
  | 'sequence'
  | 'exons'
  | 'clinvar'
  | 'protein_features'
  | 'restriction'
  | 'conservation'
export type ViewerWindowKind = 'around_variant' | 'cds_range' | 'full_gene'
export type ViewerDisplayBasis = 'transcript_window' | 'genomic_locus'
export type ViewerSegmentKind = 'exon' | 'intron'
export type ViewerCoordinateSystem = 'genomic' | 'cdna' | 'cds' | 'protein' | 'row'
export type ViewerTranscriptIntervalKind = 'exon' | 'intron' | 'utr5' | 'utr3' | 'cds'
export type ViewerFullLocusFeatureKind =
  | 'gene'
  | 'transcript'
  | 'exon'
  | 'intron'
  | 'utr5'
  | 'utr3'
  | 'cds'
  | 'queried_variant'
  | 'clinvar'
  | 'restriction_site'
  | 'conservation_bin'
  | 'primer'
  | 'guide'
  | 'custom'
export type ViewerOrientation = 'genomic_forward' | 'genomic_reverse' | 'transcript'
export type ViewerRowCoordinatePolicy = 'genomic' | 'transcript'
export type ViewerBaseColorScheme = 'none' | 'nucleotide'
export type ViewerAminoAcidColorScheme = 'none' | 'biochemical'
export type ProteinConsequenceKind =
  | 'reference'
  | 'synonymous'
  | 'missense'
  | 'stop_gained'
  | 'stop_lost'
  | 'frameshift'
  | 'inframe_deletion'
  | 'inframe_insertion'
  | 'inframe_duplication'
  | 'delins'
  | 'splice'
  | 'unknown'
export type ProteinProductExonState =
  | 'retained'
  | 'contains_variant'
  | 'downstream_truncated'
  | 'not_applicable'
export type VariantClassification =
  | 'pathogenic'
  | 'likely_pathogenic'
  | 'vus'
  | 'likely_benign'
  | 'benign'
  | 'unknown'

export interface ViewerWindowRequest {
  kind?: ViewerWindowKind
  cds_start?: number | null
  cds_end?: number | null
  cds_flank_bp?: number
  intron_flank_bp?: number
}

export interface GeneViewerRequest {
  gene: string
  cdna: string
  transcript?: string | null
  species?: string
  genome_build?: string
  allele_mode?: AlleleMode
  window?: ViewerWindowRequest
  tracks?: ViewerTrack[]
}

export interface ViewerIdentity {
  gene: string
  ensembl_gene_id?: string | null
  requested_transcript?: string | null
  resolved_transcript: string
  transcript_aliases: string[]
  species: string
  genome_build: string
}

export interface ViewerLocus {
  chrom: string
  gene_start?: number | null
  gene_end?: number | null
  strand: GenomeStrand
}

export interface ViewerSummary {
  gene_length?: number | null
  total_exons: number
  cds_length?: number | null
  protein_length?: number | null
  utr5_length?: number | null
  utr3_length?: number | null
  mrna_length?: number | null
}

export interface ViewerWindow {
  kind: ViewerWindowKind
  basis: ViewerDisplayBasis
  cds_start?: number | null
  cds_end?: number | null
  cds_flank_bp: number
  intron_flank_bp: number
  display_cds_start: number
  display_cds_end: number
  total_display_bases: number
  display_genomic_start?: number | null
  display_genomic_end?: number | null
  total_locus_bases?: number | null
}

export interface ViewerSegment {
  id: string
  kind: ViewerSegmentKind
  label: string
  exon_number?: number | null
  intron_number?: number | null
  cds_start?: number | null
  cds_end?: number | null
  genomic_start?: number | null
  genomic_end?: number | null
  strand: GenomeStrand
  sequence: string
  five_prime_sequence: string
  three_prime_sequence: string
  omitted_bp: number
}

export interface QueriedVariant {
  hgvs_c: string
  hgvs_p?: string | null
  cds_pos: number
  genomic_hg38?: string | null
  ref: string
  alt: string
  codon_number?: number | null
  codon_offset?: number | null
  aa_ref?: string | null
  aa_alt?: string | null
  classification: VariantClassification
}

export interface AppliedVariant {
  hgvs_c: string
  cds_pos: number
  segment_id: string
  sequence_offset: number
  ref: string
  alt: string
}

export interface ViewerSequences {
  allele_mode: AlleleMode
  reference_window_sequence: string
  display_window_sequence: string
  applied_variant?: AppliedVariant | null
}

export interface ClinvarVariant {
  cds_pos: number | string
  hgvs_c: string
  hgvs_p?: string | null
  classification: VariantClassification
  clinvar_id?: string | null
  queried: boolean
  splice: boolean
}

export interface ExonVariantDensity {
  exon_number: number
  variant_count: number
}

export interface ProteinDomain {
  aa_start: number
  aa_end: number
  label: string
  short_label?: string | null
}

export interface ProteinActiveSite {
  aa: number
  residue: string
  label: string
}

export interface ProteinRangeFeature {
  aa_start: number
  aa_end: number
  label: string
}

export interface ProteinPointFeature {
  aa: number
  residue: string
  label: string
}

export interface ProteinProductExonEffect {
  exon_number: number
  cds_start: number
  cds_end: number
  state: ProteinProductExonState
  affected_cds_start?: number | null
  affected_cds_end?: number | null
  lost_cds_bases: number
}

export interface ProteinProductEffect {
  allele_mode: AlleleMode
  consequence: ProteinConsequenceKind
  label: string
  description: string
  reference_protein_length?: number | null
  effective_protein_length?: number | null
  truncates_protein: boolean
  stop_codon?: number | null
  affected_aa_start?: number | null
  lost_aa_count: number
  nmd_risk?: string | null
  exon_effects: ProteinProductExonEffect[]
}

export type ProteinAnnotationInputType = 'auto' | 'protein' | 'coding_dna'
export type ProteinAnnotationStatus =
  | 'available'
  | 'cache_hit'
  | 'unavailable'
  | 'failed'
  | 'partial'
export type ProteinDomainFeatureKind =
  | 'domain'
  | 'site'
  | 'motif'
  | 'repeat'
  | 'region'
  | 'family'
  | 'epitope'
  | 'coiled_coil'
  | 'low_complexity'
  | 'signal_peptide'
  | 'transmembrane'
  | 'topological_domain'
export type ProteinVariantMarkerShape = 'triangle' | 'circle' | 'star' | 'pin'

export interface ProteinAnnotationRequest {
  sequence: string
  input_type: ProteinAnnotationInputType
  sequence_label?: string | null
  gene_symbol?: string | null
  transcript?: string | null
  protein_accession?: string | null
  use_cache: boolean
  allow_run: boolean
}

export interface ProteinTrackProvenance {
  source_id: string
  source_name: string
  source_url?: string | null
  source_release?: string | null
  checksum_md5?: string | null
  checksum_sha256?: string | null
  license_status?: string | null
  warnings: string[]
}

export interface ProteinDomainTrackFeature {
  feature_id: string
  kind: ProteinDomainFeatureKind
  label: string
  short_label?: string | null
  aa_start: number
  aa_end: number
  accession?: string | null
  interpro_accession?: string | null
  source: string
  source_accession?: string | null
  source_release?: string | null
  source_checksum_md5?: string | null
  source_checksum_sha256?: string | null
  score?: number | null
  e_value?: number | null
  hmm_start?: number | null
  hmm_end?: number | null
  envelope_start?: number | null
  envelope_end?: number | null
  description?: string | null
  lane: string
  warnings: string[]
}

export interface ProteinTrackVariantMarker {
  marker_id: string
  aa_start: number
  aa_end: number
  label: string
  hgvs_c?: string | null
  hgvs_p?: string | null
  variant_class?: string | null
  classification?: string | null
  marker_shape: ProteinVariantMarkerShape
  is_query: boolean
  source?: string | null
  warnings: string[]
}

export interface ProteinDomainTrack {
  status: ProteinAnnotationStatus
  fail_closed_reason?: string | null
  sequence_label?: string | null
  gene_symbol?: string | null
  transcript?: string | null
  protein_accession?: string | null
  protein_sequence_hash?: string | null
  sequence_hash_algorithm: 'sha256'
  protein_length?: number | null
  translated_from: 'protein' | 'coding_dna' | 'unknown'
  cache_key?: string | null
  cache_status: 'cache_hit' | 'cache_miss' | 'stored' | 'not_used'
  pfam_release?: string | null
  hmmer_release?: string | null
  uniprot_release?: string | null
  features: ProteinDomainTrackFeature[]
  variant_markers: ProteinTrackVariantMarker[]
  provenance: ProteinTrackProvenance[]
  warnings: string[]
}

export interface ProteinFeatures {
  signal_peptide?: ProteinRangeFeature | null
  transmembrane: ProteinRangeFeature[]
  domains: ProteinDomain[]
  active_sites: ProteinActiveSite[]
  membrane_binding: ProteinRangeFeature[]
  palmitoylation: ProteinPointFeature[]
  domain_track?: ProteinDomainTrack | null
}

export interface RestrictionSite {
  name: string
  site: string
  flat_pos: number
}

export interface ViewerFeature {
  type: string
  cds_start: number
  cds_end: number
  label: string
}

export interface ViewerTracks {
  clinvar_variants: ClinvarVariant[]
  exon_density: ExonVariantDensity[]
  protein_features: ProteinFeatures
  protein_product?: ProteinProductEffect | null
  conservation_values: number[]
  restriction_sites: RestrictionSite[]
  features: ViewerFeature[]
}

export interface ViewerProvenanceSource {
  name: string
  identifier?: string | null
  url?: string | null
  version?: string | null
}

export interface ViewerProvenance {
  sources: ViewerProvenanceSource[]
  warnings: string[]
}

export interface ViewerGenomicLocus {
  chrom: string
  start: number
  end: number
  strand: GenomeStrand
  genome_build: string
  sequence: string
  coordinate_system: 'genomic'
}

export interface ViewerCoordinateMapRange {
  genomic_start: number
  genomic_end: number
  cdna_start?: number | null
  cdna_end?: number | null
  cds_start?: number | null
  cds_end?: number | null
  protein_start?: number | null
  protein_end?: number | null
}

export interface ViewerCodonStart {
  codon_number: number
  cds_start: number
  protein_position: number
  genomic_start: number
  genomic_positions: number[]
}

export interface ViewerTranscriptProjectionInterval {
  id: string
  kind: ViewerTranscriptIntervalKind
  label: string
  genomic_start: number
  genomic_end: number
  strand: GenomeStrand
  exon_number?: number | null
  intron_number?: number | null
  cdna_start?: number | null
  cdna_end?: number | null
  cds_start?: number | null
  cds_end?: number | null
  protein_start?: number | null
  protein_end?: number | null
}

export interface ViewerTranscriptProjection {
  transcript: string
  strand: GenomeStrand
  intervals: ViewerTranscriptProjectionInterval[]
  coordinate_map: ViewerCoordinateMapRange[]
  codon_starts: ViewerCodonStart[]
}

export interface ViewerFeatureInterval {
  id: string
  kind: ViewerFullLocusFeatureKind
  label: string
  coordinate_system: ViewerCoordinateSystem
  start: number
  end: number
  strand: GenomeStrand
  source?: string | null
  classification?: VariantClassification | null
  metadata: Record<string, string | number | boolean | null>
}

export interface ViewerRenderingHints {
  orientation: ViewerOrientation
  row_coordinate_policy: ViewerRowCoordinatePolicy
  bases_per_row_min: number
  bases_per_row_max: number
  max_visual_density?: number | null
  base_color_scheme: ViewerBaseColorScheme
  amino_acid_color_scheme: ViewerAminoAcidColorScheme
}

export interface ViewerFullLocus {
  basis: 'genomic_locus'
  locus: ViewerGenomicLocus
  transcript_projection: ViewerTranscriptProjection
  feature_intervals: ViewerFeatureInterval[]
  rendering_hints: ViewerRenderingHints
}

export interface GeneViewerResponse {
  identity: ViewerIdentity
  locus: ViewerLocus
  summary: ViewerSummary
  window: ViewerWindow
  segments: ViewerSegment[]
  queried_variant: QueriedVariant
  sequences: ViewerSequences
  tracks: ViewerTracks
  full_locus?: ViewerFullLocus | null
  provenance: ViewerProvenance
}

// ---------------------------------------------------------------------------
// Batch VCF + gene panels (spec plans/batch-vcf-and-panels).
// Mirrors app/backend/app/schemas/panels.py + batch.py — keep in sync; the
// field-name parity is enforced by tests/test_frontend_contract.py.
// ---------------------------------------------------------------------------

export type PanelSource = 'panelapp-au' | 'panelapp-gel' | 'clingen-gencc' | 'custom'
export type PanelConfidence = 'green' | 'amber' | 'red'
export type PanelValidity =
  | 'definitive'
  | 'strong'
  | 'moderate'
  | 'limited'
  | 'disputed'
  | 'refuted'
  | 'animal_model_only'
  | 'no_known_disease_relationship'
export type PanelMinimumValidity = 'definitive' | 'strong'

export interface PanelGene {
  symbol: string
  hgnc_id?: string | null
  confidence?: PanelConfidence | null
  moi?: string | null
  disease?: string | null
  mondo_id?: string | null
  validity?: PanelValidity | null
  provenance: string[]
  warnings: string[]
}

export interface PanelSummary {
  id: string
  name: string
  slug: string
  source: PanelSource
  version: string
  provenance_url?: string | null
  gene_count: number
  intervals_ref: 'hg38'
  warnings: string[]
}

export interface Panel {
  id: string
  name: string
  slug: string
  source: PanelSource
  version: string
  provenance_url?: string | null
  genes: PanelGene[]
  intervals_ref: 'hg38'
  warnings: string[]
}

export interface PanelListResponse {
  panels: PanelSummary[]
}

export interface PanelResolveRequest {
  disease_mondo?: string | null
  symbols?: string[] | null
  upload_ref?: string | null
  min_validity?: PanelMinimumValidity
}

export type BatchJobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
export type BatchVariantState =
  | 'queued'
  | 'filtered_pre_lookup'
  | 'lookup_pending'
  | 'running'
  | 'completed'
  | 'filtered_post_lookup'
  | 'failed'

export interface ParsedVariant {
  raw?: string | null
  query: string
  gene?: string | null
  variant?: string | null
  chrom?: string | null
  pos?: number | null
  ref?: string | null
  alt?: string | null
  filter?: string | null
  info_af?: number | null
  source_index?: number | null
  sample_id?: string | null
  genotype?: string | null
  warnings: string[]
}

export interface BatchFilters {
  panel_slug?: string | null
  pass_only?: boolean
  regions?: string[]
  max_af?: number | null
}

export interface BatchUploadResponse {
  upload_ref: string
}

export interface BatchCreateRequest {
  variants?: ParsedVariant[] | null
  upload_ref?: string | null
  filters?: BatchFilters
}

export interface BatchCreateResponse {
  job_id: string
  n_input: number
  n_to_lookup: number
  est_seconds: number
}

export interface BatchPage {
  limit: number
  next_cursor?: string | null
  total: number
}

export interface BatchJobQuery {
  limit?: number
  cursor?: string | null
}

export interface BatchResult {
  variant_key: string
  state: BatchVariantState
  gene?: string | null
  hgvs_c?: string | null
  hgvs_p?: string | null
  clinvar_verdict?: string | null
  gnomad_af?: number | null
  predictor_ensemble: Record<string, unknown>
  acmg_classification?: string | null
  report_href?: string | null
  warnings: string[]
}

export interface BatchJob {
  job_id: string
  status: BatchJobStatus
  n_input: number
  n_to_lookup: number
  n_after_filters?: number | null
  est_seconds: number
  done: number
  total: number
  results: BatchResult[]
  page: BatchPage
  warnings: string[]
}
