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

// ─── Eamos computed ACMG classification (points-engine advisory) ───
// Mirror of app/backend/app/schemas/run.py EamosComputedClassification + its
// sub-types. The seam the report's ACMG visuals (lib/acmg/points.ts + the SVG
// instruments) read: net_points to tier/model_posterior. Backend-led; null until the
// points engine materializes.
export type EamosComputedTier =
  | 'Pathogenic'
  | 'Likely Pathogenic'
  | 'VUS'
  | 'Likely Benign'
  | 'Benign'
export type EamosComputedDirection = 'pathogenic' | 'benign'
export type EamosComputedStrength = 'very_strong' | 'strong' | 'moderate' | 'supporting'
export type EamosComputedBenignCut = 'tavtigian_2020' | 'acgs_panel'
export type EamosComputedClassificationBasis =
  | 'bayesian_points'
  | 'ba1_standalone_override'
  | 'legacy_conflict_cap'

export interface EamosComputedPolicyDiff {
  field: string
  general_value: string
  overlay_value: string
}

export interface EamosComputedVersionPin {
  framework: string
  ruleset_id: string
  ruleset_version: string
  conflict_policy_id: string
  pvs1_revision: string
  pp3_calibration: string
  vcep_id?: string | null
  population_policy_id: string
  population_policy_version: string
  cspec_overlay_id?: string | null
  cspec_overlay_version?: string | null
  population_policy_diff: EamosComputedPolicyDiff[]
}

export interface EamosComputedConflict {
  is_conflicting: boolean
  reason?: string | null
}

export interface EamosComputedCriterion {
  code: string
  direction: EamosComputedDirection
  triggered: boolean
  applied_strength?: EamosComputedStrength | null
  points: number
  evidence_value?: string | number | null
  threshold?: string | number | null
  source_db?: string | null
  source_version?: string | null
  source_url?: string | null
  svi_reference?: string | null
  policy_id?: string | null
  policy_version?: string | null
  policy_source_url?: string | null
  cspec_overlay_id?: string | null
  cspec_overlay_version?: string | null
  functional_assay_oddspath?: number | null
  functional_assay_confidence_interval_lower?: number | null
  functional_assay_confidence_interval_upper?: number | null
}

export interface AcmgCaseContextLimitation {
  code: string
  status: 'not_scored'
  reason: 'missing_case_context'
  missing_inputs: string[]
  applies_when: string[]
  message: string
}

export interface EamosComputedClassification {
  acmg_version_pin: EamosComputedVersionPin
  net_points: number
  sum_pathogenic: number
  sum_benign: number
  tier: EamosComputedTier
  classification_basis: EamosComputedClassificationBasis
  conflict: EamosComputedConflict
  ba1_override: boolean
  aggregate_evidence_likelihood_ratio: number | null
  prior_odds: number | null
  posterior_odds: number | null
  model_posterior: number | null
  /** Read-only compatibility for captured pre-Phase-6 fixtures. */
  posterior?: number
  benign_cut: EamosComputedBenignCut
  per_criterion: EamosComputedCriterion[]
  limitations?: AcmgCaseContextLimitation[]
  warnings?: string[]
}

export interface ReportPayload {
  patient_id: string
  report_generated_at?: string | null
  report_data_currency?: ReportDataCurrency | null
  source_versions?: Record<string, string>
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
  eamos_computed_classification?: EamosComputedClassification | null
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

export type SearchMetadataValue = string | number | boolean | null

export type SearchDocType =
  | 'report'
  | 'run'
  | 'library_variant'
  | 'popular_variant'
  | 'publication'
  | 'trial'
  | 'report_section'
  | 'gene'
  | 'condition'
  | 'gene_disease'
  | 'source'

export type SearchVisibilityScope = 'public' | 'private' | 'internal'

export type SearchMatchType =
  | 'exact_run_id'
  | 'exact_report_id'
  | 'exact_patient_id'
  | 'exact_variant'
  | 'full_text'

export interface SearchHit {
  source_key: string
  doc_type: SearchDocType
  visibility_scope: SearchVisibilityScope
  run_id?: string | null
  report_id?: string | null
  patient_id?: string | null
  title: string
  subtitle?: string | null
  snippet?: string | null
  target_href?: string | null
  metadata: Record<string, SearchMetadataValue>
  match_type: SearchMatchType
  score: number
  run_status?: string | null
  review_status?: string | null
  extraction_status?: string | null
  updated_at?: string | null
}

export interface SearchResponse {
  query: string
  results: SearchHit[]
}

export interface SearchCitation {
  run_id?: string | null
  report_id?: string | null
  title?: string | null
}

export interface SearchAnswerRequest {
  query: string
  limit?: number
  doc_type?: SearchDocType | null
  run_status?: string | null
  review_status?: string | null
}

export interface SearchAnswerResponse {
  query: string
  answer: string
  grounded: boolean
  citations: SearchCitation[]
  results: SearchHit[]
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
  execution_state_v2?: ReportExecutionStateV2 | null
}

// ─── Shared live-product execution/source disclosure ───

export type CapabilityExecutionV2 =
  | 'eamos_local'
  | 'mounted_artifact'
  | 'external_provider'
  | 'fixture'
  | 'unavailable'
export type CapabilitySourceStatusV2 =
  | 'source_backed'
  | 'not_required'
  | 'not_found'
  | 'not_applicable'
  | 'unavailable'
  | 'fixture'
export type CapabilityApplicabilityV2 = 'applicable' | 'not_applicable' | 'unknown'
export type CapabilityValidationStatusV2 =
  | 'validated'
  | 'fixture_only'
  | 'unvalidated'
  | 'failed'
  | 'not_applicable'
export type CapabilityRetentionV2 = 'none' | 'request_lifetime' | 'ttl' | 'account_saved'

export interface CapabilityExecutionDisclosureV2 {
  schema_version?: 'capability_execution.v2'
  capability_id: string
  claim: string
  execution: CapabilityExecutionV2
  algorithm_id?: string | null
  algorithm_version?: string | null
  provider_id?: string | null
  provider_version?: string | null
  input_scope: string
  source_status: CapabilitySourceStatusV2
  source_record_ids?: string[]
  source_release?: string | null
  materialized_at?: string | null
  artifact_manifest_id?: string | null
  artifact_sha256?: string | null
  applicability: CapabilityApplicabilityV2
  validation_status: CapabilityValidationStatusV2
  validation_matrix_id?: string | null
  retention: CapabilityRetentionV2
  retention_expires_at?: string | null
  consent_required: boolean
  warnings?: string[]
  requirements?: string[]
}

// ─── Paper → Variants contract (POST /api/v1/paper-variants/extract) ───
// Mirror of app/backend/app/schemas/paper_variants.py (VariantLevel,
// VariantContext, ValidatedPaperVariant, PaperVariantsResult) plus the CLI-style
// response envelope from app/backend/app/cli/eamos_paper_variants.py (pdf meta +
// guardrails + counts). Reuses SearchInputCandidate / SearchInputSourceInputs
// above — the candidates[] a paper variant carries are the SAME type the search
// interpretation panel renders, so the FE shares one <CandidateCard>.
//
// Backend-led + NOT built yet: the HTTP route is CLI-only today, so
// lib/paperVariants.ts renders the .eamos-mock fixture until Codex ships it, then
// swaps to live with no shape change. Confirm the exact envelope with Codex
// before the live cutover.
export type VariantLevel =
  | 'cdna'
  | 'genomic'
  | 'rna'
  | 'mitochondrial'
  | 'protein'
  | 'rsid'
  | 'legacy'
  | 'unknown'
export type VariantContext =
  | 'clinical_allele'
  | 'case_or_proband'
  | 'family_segregation'
  | 'experimental_construct'
  | 'engineered_rescue'
  | 'comparator_or_background'
  | 'bibliography_only'
  | 'ambiguous'
  | 'unknown'
export type PaperDocumentRoleV2 = 'main' | 'supplement'
export type PaperDocumentKindV2 = 'pdf' | 'text' | 'csv' | 'xlsx'
export type PaperExtractionQualityV2 = 'good' | 'degraded' | 'garbled' | 'image_only' | 'empty'
export type PaperExtractionLayerV2 = 'l1_structured' | 'l2_recovery' | 'l3_inventory'
export type PaperResolutionStatusV2 = 'resolved' | 'ambiguous' | 'unresolved' | 'excluded'
export type PaperAdjudicationRecommendationV2 = 'confirm' | 'reject' | 'needs_review'

export interface PaperDocumentUploadV2 {
  document_id: string
  role: PaperDocumentRoleV2
  kind: PaperDocumentKindV2
  upload_ref: string
  filename: string
  media_type: string
  size_bytes: number
  sha256: string
}

export interface PaperBibliographicMetadataV2 {
  title?: string | null
  authors?: string[]
  year?: number | null
  journal?: string | null
  doi?: string | null
  pmid?: string | null
  provenance?: string[]
}

export interface PaperDocumentMetadataV2 {
  document_id: string
  role: PaperDocumentRoleV2
  kind: PaperDocumentKindV2
  filename: string
  media_type: string
  size_bytes: number
  sha256: string
  page_count?: number | null
  extraction_engine: string
  extraction_engine_version: string
  bibliographic_metadata?: PaperBibliographicMetadataV2 | null
  warnings?: string[]
}

export interface PaperDocumentBundleV2 {
  schema_version?: 'paper_document_bundle.v2'
  bundle_id: string
  documents: PaperDocumentMetadataV2[]
  input_digest: string
}

export interface PaperDocumentBundleRequestV2 {
  schema_version?: 'paper_document_bundle_request.v2'
  bundle_id: string
  documents: PaperDocumentUploadV2[]
  input_digest: string
  consent_to_external_processing?: boolean
}

export interface PaperPageExtractionQualityV2 {
  document_id: string
  page_number: number
  quality: PaperExtractionQualityV2
  extracted_character_count: number
  replacement_character_ratio: number
  warnings?: string[]
}

export interface PaperEvidenceSpanV2 {
  document_id: string
  page_number: number
  section: string
  start_character: number
  end_character: number
  exact_text: string
  bounded_quote: string
}

export interface PaperVariantMentionV2 {
  mention_id: string
  notation_type: VariantLevel
  biological_context: VariantContext
  extraction_layer: PaperExtractionLayerV2
  confidence: number
  span: PaperEvidenceSpanV2
  gene_evidence?: string[]
  transcript_evidence?: string[]
  warnings?: string[]
}

export interface PaperMentionResolutionV2 {
  mention_id: string
  status: PaperResolutionStatusV2
  canonical_variant?: CanonicalVariantRefV1 | null
  candidate_ids?: string[]
  execution_disclosure: CapabilityExecutionDisclosureV2
  warnings?: string[]
}

export interface PaperAiAdjudicationV2 {
  mention_id: string
  deterministic_digest: string
  recommendation: PaperAdjudicationRecommendationV2
  reason: string
  advisory_only?: true
  execution_disclosure: CapabilityExecutionDisclosureV2
}

export interface PaperDocumentExtractionV2 {
  schema_version?: 'paper_document_extraction.v2'
  bundle: PaperDocumentBundleV2
  deterministic_digest: string
  page_quality?: PaperPageExtractionQualityV2[]
  mentions?: PaperVariantMentionV2[]
  resolutions?: PaperMentionResolutionV2[]
  ai_adjudications?: PaperAiAdjudicationV2[]
  execution_disclosure: CapabilityExecutionDisclosureV2
  warnings?: string[]
}

export interface ValidatedPaperVariant {
  gene: string | null
  transcript_hgvs: string | null
  protein_change: string | null
  protein_hgvs: string | null
  level: VariantLevel
  context: VariantContext
  evidence_quote: string | null
  /** Fail-closed gate result: true ONLY for a single high-confidence,
   *  source-backed candidate with coordinates populated. */
  validated: boolean
  /** Resolver outcome string from the backend: 'resolved' | 'candidates' |
   *  'protein_only_unresolved' | 'experimental_construct' | 'missing' |
   *  'not_validated' | 'resolver_failed:<Type>'. */
  validation_status: string
  variant_id: string | null
  genomic_hgvs: string | null
  resolved_candidate_id: string | null
  source_support: string[]
  source_inputs: SearchInputSourceInputs | null
  /** Same type the search panel renders → reused via <CandidateCard>. */
  candidates: SearchInputCandidate[]
  resolver_warnings: string[]
  resolver_provenance: string[]
}

export interface PaperVariantsResult {
  variants: ValidatedPaperVariant[]
  warnings: string[]
  provenance: string[]
}

export interface PaperPdfMeta {
  page_count: number
  engine: string
  warnings: string[]
}

// Bibliographic metadata for the source paper, so the By-paper view can title a
// group by "Authors · Year — Title" instead of the filename. Backend-led and
// optional: the regex mock returns null (it can't know the title); Codex would
// populate this from PDF metadata / first-page parse / the gateway extraction.
export interface PaperSourceMetadata {
  title: string | null
  authors: string[]
  year: string | null
  journal: string | null
  doi: string | null
  pmid: string | null
}

export interface PaperVariantsGuardrails {
  patient_data: string
  raw_paper_text_in_output: string
  secrets_in_output: string
}

// The HTTP envelope mirrors the eamos_paper_variants CLI report dict: the
// PaperVariantsResult fields (variants/warnings/provenance) flattened to the top
// level alongside pdf meta + guardrails + counts.
export interface PaperVariantsResponse {
  mode: string
  generated_at: string
  llm_provider: string
  pdf: PaperPdfMeta | null
  source_metadata: PaperSourceMetadata | null
  guardrails: PaperVariantsGuardrails
  candidate_count: number
  validated_count: number
  variants: ValidatedPaperVariant[]
  warnings: string[]
  provenance: string[]
  document_extraction?: PaperDocumentExtractionV2 | null
  execution_disclosure?: CapabilityExecutionDisclosureV2 | null
}

export type ReportSectionIdV2 =
  | 'header'
  | 'interpretation_summary'
  | 'disease_mechanism'
  | 'gene_context_snapshot'
  | 'population_frequency'
  | 'molecular_context'
  | 'computational_deep_dive'
  | 'acmg_worksheet'
  | 'expert_panel'
  | 'publications'
  | 'therapies_trials'
  | 'provenance'
export type ReportSectionStateV2 =
  | 'ready'
  | 'empty'
  | 'partial'
  | 'unavailable'
  | 'not_applicable'
  | 'stale'
  | 'failed'
export type ReportMatchLevelV2 =
  | 'exact_allele'
  | 'transcript'
  | 'protein'
  | 'gene'
  | 'gene_disease'
  | 'condition'
  | 'discovery_only'
  | 'not_applicable'
export type ReportPredictorStateV2 =
  | 'executed'
  | 'unavailable'
  | 'not_applicable'
  | 'failed'
  | 'stale'
export type ReportCoverageV2 = 'partial' | 'complete'

export interface ReportSectionExecutionV2 {
  section_id: ReportSectionIdV2
  state: ReportSectionStateV2
  match_level: ReportMatchLevelV2
  source_snapshot_id: string
  execution_disclosures?: CapabilityExecutionDisclosureV2[]
  stale_on_failure?: boolean
  warnings?: string[]
}

export interface ReportPredictorExecutionV2 {
  predictor_id: string
  applicability: CapabilityApplicabilityV2
  state: ReportPredictorStateV2
  source_snapshot_id: string
  calibration_id?: string | null
  execution_disclosure: CapabilityExecutionDisclosureV2
  stale_on_failure?: boolean
  warnings?: string[]
}

export interface ReportExecutionStateV2 {
  schema_version?: 'report_execution_state.v2'
  coverage: ReportCoverageV2
  canonical_variant: CanonicalVariantRefV1
  source_snapshot_id: string
  sections?: ReportSectionExecutionV2[]
  predictors?: ReportPredictorExecutionV2[]
}

// ─── M11 lookup section-fetch contract ───
// Mirror of app/backend/app/schemas/lookup.py (LookupSection*, LookupSummaryTile,
// LookupInitialSummaryResponse, LookupSectionFetchRequest/Response).
// Backend-led: FE does not reshape payloads. `payload` on LookupSectionEnvelope
// is intentionally Record<string, unknown> | null — consumers type-narrow per
// section_id at the read site against the existing ReportPayload sub-types
// (PublicationLiterature shape for 'publications', TherapiesTrialsSection for
// 'therapies_trials', ComputationalDeepDive for 'computational_deep_dive',
// AcmgWorksheet + {narrative, source_scope} for 'clingen_vcep').
export type LookupSectionId =
  | 'publications'
  | 'therapies_trials'
  | 'computational_deep_dive'
  | 'clingen_vcep'

export type LookupSectionStatus =
  | 'ready'
  | 'available'
  | 'empty'
  | 'missing'
  | 'partial'
  | 'hydrating'
  | 'stale'
  | 'failed'
  | 'unsupported'

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
  execution_state_v2?: ReportExecutionStateV2 | null
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

// Per-asset data-currency / freshness. Mirrors the backend Phase 0.1 freshness
// block (local-evidence-freshness plan, Task 0.1) consumed by DataCurrencyLine.
// Optional throughout: when absent, the FE derives currency from the real
// per-source `fetched_at` on evidence rows instead.
export interface SourceFreshness {
  source: string
  label?: string | null
  materialized_at?: string | null
  upstream_released_at?: string | null
  tier?: 'volatile' | 'static' | null
  status?: 'fresh' | 'stale' | 'overdue' | 'unknown' | null
  staleness_days?: number | null
  source_version?: string | null
}

export interface ReportDataCurrency {
  sources: SourceFreshness[]
  generated_at?: string | null
}

export interface LookupSectionEnvelope {
  section_id: LookupSectionId
  status: LookupSectionStatus
  payload?: Record<string, unknown> | null
  freshness: LookupSectionFreshness
  warnings: string[]
  execution_state_v2?: ReportSectionExecutionV2 | null
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
  source_status?: string | null
  source_id?: string | null
  source_version?: string | null
  source_url?: string | null
  public_serialization_allowed?: boolean | null
  launch_gate?: string | null
  license_gate?: string | null
  query_cell?: string | null
  query_variant_id?: string | null
  query_accession?: string | null
  query_classification?: string | null
  warnings?: string[]
}

export type EvidenceLevel = 'definitive' | 'strong' | 'moderate' | 'limited'
export type InheritancePattern = 'AR' | 'AD' | 'XL' | 'MT'

export interface AssociatedCondition {
  source_id?: string | null
  source_record_id?: string | null
  source_version?: string | null
  source_url?: string | null
  retrieved_at?: string | null
  origin_kind: SourceOriginKind
  match_level?: string | null
  record_license?: string | null
  terms_version_or_hash?: string | null
  license_gate?: string | null
  launch_gate?: string | null
  public_serialization_allowed?: boolean | null
  export_allowed?: boolean | null
  cache_allowed?: boolean | null
  attribution?: string | null
  policy_version?: string | null
  decision_reason?: string | null
  decision_at?: string | null
  policy_decisions: SourcePolicyDecision[]
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
  mavedb: number
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

export interface FunctionalMeasurementValue {
  column: string
  source_value: string
  parsed_value: string
  description?: string | null
  details?: string | null
}

export interface FunctionalStudy {
  source_id?: string | null
  source_record_id?: string | null
  source_version?: string | null
  source_url?: string | null
  retrieved_at?: string | null
  origin_kind: SourceOriginKind
  match_level?: string | null
  record_license?: string | null
  terms_version_or_hash?: string | null
  license_gate?: string | null
  launch_gate?: string | null
  public_serialization_allowed?: boolean | null
  export_allowed?: boolean | null
  cache_allowed?: boolean | null
  attribution?: string | null
  policy_version?: string | null
  decision_reason?: string | null
  decision_at?: string | null
  policy_decisions: SourcePolicyDecision[]
  id: string
  pmid?: string | null
  url?: string | null
  citation?: string | null
  source_accession?: string | null
  source_tags: string[]
  evidence_codes: string[]
  asserted_codes: string[]
  functional_score?: string | null
  functional_score_label?: string | null
  raw_score?: string | null
  score_unit?: string | null
  score_column?: string | null
  score_direction?: string | null
  score_set_urn?: string | null
  variant_urn?: string | null
  experiment_urn?: string | null
  experiment_set_urn?: string | null
  target_accession?: string | null
  target_kind?: string | null
  target_assembly?: string | null
  target_sequence_checksum?: string | null
  target_identity?: string | null
  mave_hgvs_nt?: string | null
  mave_hgvs_splice?: string | null
  mave_hgvs_pro?: string | null
  score_column_description?: string | null
  score_column_details?: string | null
  uncertainty_values: FunctionalMeasurementValue[]
  assay_context?: string | null
  method_text?: string | null
  linked_doi_identifiers: string[]
  linked_publication_identifiers: string[]
  archive_release_doi?: string | null
  archive_sha256?: string | null
  archive_checksum_algorithm?: string | null
  archive_checksum_value?: string | null
  archive_checksum_verified?: boolean | null
  local_logical_checksum_verified?: boolean | null
  data_usage_policy_decision?: string | null
  match_requested_identity?: string | null
  match_matched_identity?: string | null
  calibration_status?: string | null
  deprecated: boolean
  superseded_by?: string | null
  provenance: SourceProvenance[]
  snippet?: string | null
}

export interface FunctionalAssayConfusionMatrix {
  pathogenic_abnormal: number
  pathogenic_normal: number
  benign_abnormal: number
  benign_normal: number
}

export interface FunctionalAssayValidation {
  validation_id: string
  validation_version: string
  validation_policy_id: string
  validation_policy_version: string
  status: ComputationalStandardStatus
  gene_id: string
  disease_id: string
  disease_mechanism: string
  assay_name: string
  assay_relevance: string
  pathogenic_truth_variant_ids: string[]
  benign_truth_variant_ids: string[]
  evaluation_variant_ids: string[]
  truth_set_independence_basis: string
  truth_evaluation_overlap_rejected: boolean
  circularity_reviewed: boolean
  confusion_matrix: FunctionalAssayConfusionMatrix
  pseudocount_policy: 'brnich_2020_one_discordant_control'
  pseudocount: number
  direction: EamosComputedDirection
  functional_assay_oddspath: number
  confidence_interval_lower: number
  confidence_interval_upper: number
  maximum_supported_strength: EamosComputedStrength
  curator: string
  validation_date: string
  source_url: string
  source_version: string
}

export interface FunctionalEvidenceAssertionCandidate {
  assertion_id: string
  code: 'PS3' | 'BS3'
  applied_strength: EamosComputedStrength
  variant_id: string
  gene_id: string
  disease_id: string
  source_id: string
  source_record_id: string
  source_version: string
  source_url: string
  selected_for_counting: boolean
  selection_rationale?: string | null
  validation: FunctionalAssayValidation
}

export interface FunctionalEvidenceSummary {
  total_count: number
  source_breakdown: FunctionalEvidenceSourceBreakdown
  evidence_codes: string[]
  source_asserted_codes: string[]
  assertion_candidates: FunctionalEvidenceAssertionCandidate[]
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
  unavailable_reason?: string | null
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
  | 'local'
  | 'missing'
  | 'live_stub'
  | 'error'
  | 'failed'
export type ReportMatchLevel = 'variant_level' | 'gene_level' | 'disease_level' | 'unavailable'
export type ReportSectionSignalStatus = 'ready' | 'limited' | 'empty' | 'error' | 'loading'
export type ReportSectionRelevance =
  | 'exact_variant'
  | 'equivalent_allele'
  | 'protein_region'
  | 'transcript_locus'
  | 'gene_disease'
  | 'disease_discovery'
  | 'gene_discovery'
  | 'summary'
export type ReportSectionSourceStrength =
  | 'expert_panel'
  | 'curated'
  | 'primary_db'
  | 'literature'
  | 'eamos_computed'
  | 'source_mixed'
  | 'inferred'
  | 'unavailable'
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

export type SourceOriginKind = 'direct' | 'cross_reference' | 'derived'
export type SourcePolicyOutcome = 'allowed' | 'denied'
export type SourcePolicyAction =
  | 'acquire'
  | 'cache'
  | 'normalize'
  | 'public_serialize'
  | 'product_export'
  | 'log'
  | 'analyze'
  | 'backup'
  | 'stage'
  | 'restore'
  | 'raw_debug'

export interface SourcePolicyDecision {
  action: SourcePolicyAction
  field: string
  outcome: SourcePolicyOutcome
  reason: string
  decided_at: string
}

export interface SourceFactPolicyEnvelope {
  source_id?: string | null
  source_record_id?: string | null
  source_version?: string | null
  source_url?: string | null
  retrieved_at?: string | null
  origin_kind: SourceOriginKind
  match_level?: string | null
  record_license?: string | null
  terms_version_or_hash?: string | null
  license_gate?: string | null
  launch_gate?: string | null
  public_serialization_allowed?: boolean | null
  export_allowed?: boolean | null
  cache_allowed?: boolean | null
  attribution?: string | null
  policy_version?: string | null
  decision_reason?: string | null
  decision_at?: string | null
  policy_decisions: SourcePolicyDecision[]
}

export interface OmimCrossReference {
  source_id?: string | null
  source_record_id?: string | null
  source_version?: string | null
  source_url?: string | null
  retrieved_at?: string | null
  origin_kind: 'cross_reference'
  match_level?: string | null
  record_license?: string | null
  terms_version_or_hash?: string | null
  license_gate?: string | null
  launch_gate?: string | null
  public_serialization_allowed?: boolean | null
  export_allowed?: boolean | null
  cache_allowed?: boolean | null
  attribution?: string | null
  policy_version?: string | null
  decision_reason?: string | null
  decision_at?: string | null
  policy_decisions: SourcePolicyDecision[]
  identifier_namespace: 'OMIM'
  identifier: string
  entry_type: 'gene' | 'phenotype'
  external_link_provider: 'omim_web'
  external_url: string
  evidence_role: 'identifier_only'
}

export interface LovdInstallationSource {
  source_id: 'lovd_global_variome_shared_fixture'
  installation_id: 'global_variome_shared_lovd'
  display_name: 'Global Variome shared LOVD'
  base_url: 'https://databases.lovd.nl/shared'
  live_access_enabled: false
  maximum_requests_per_second: number
  minimum_negative_cache_ttl_seconds: number
  positive_cache_policy: 'not_approved'
  record_license_mode: 'record_level_required'
  installation_permission_is_record_license: false
}

export interface LovdBasicObservation {
  source_id: 'lovd_global_variome_shared_fixture'
  source_record_id: string
  source_version: 'LOVD 3 basic API synthetic schema fixture v1'
  source_url: string
  retrieved_at?: string | null
  origin_kind: 'derived'
  match_level: 'exact_normalized_hgvs'
  record_license: 'CC-BY-4.0'
  terms_version_or_hash: 'lovd-doc-review-2026-07-17'
  license_gate: 'synthetic_fixture_record_license_example'
  launch_gate: 'live_access_disabled_pending_written_permission'
  public_serialization_allowed: true
  export_allowed: false
  cache_allowed: false
  attribution: 'Global Variome shared LOVD (synthetic fixture)'
  policy_version: 'lovd-fixture-policy-v1'
  decision_reason?: string | null
  decision_at?: string | null
  policy_decisions: SourcePolicyDecision[]
  installation: LovdInstallationSource
  presence: true
  genome_build: 'GRCh37' | 'GRCh38'
  transcript_accession: string
  hgvs_c: string
  source_edited_at: string
  evidence_role: 'presence_only'
}

export interface LovdBasicRecordsSection {
  installation: LovdInstallationSource
  status: 'matched' | 'not_found' | 'ambiguous' | 'denied'
  observations: LovdBasicObservation[]
  live_request_performed: false
  warnings: string[]
}

export interface SourceProvenance {
  source_id?: string | null
  source_record_id?: string | null
  source_version?: string | null
  source_url?: string | null
  retrieved_at?: string | null
  origin_kind: SourceOriginKind
  match_level?: string | null
  record_license?: string | null
  terms_version_or_hash?: string | null
  license_gate?: string | null
  launch_gate?: string | null
  public_serialization_allowed?: boolean | null
  export_allowed?: boolean | null
  cache_allowed?: boolean | null
  attribution?: string | null
  policy_version?: string | null
  decision_reason?: string | null
  decision_at?: string | null
  policy_decisions: SourcePolicyDecision[]
  source: string
  status: SourceStatus
  query: Record<string, string>
  version?: string | null
  storage_kind?: string | null
  warnings: string[]
}

export interface EvidenceIdentityMatch {
  tier:
    | 'assertion_id'
    | 'caid'
    | 'clinvar_variation_id'
    | 'vrs'
    | 'spdi'
    | 'genomic_hgvs'
    | 'transcript_hgvs'
    | 'candidate_text'
  source_field: string
  requested: string
  matched: string
  normalized_requested: string
  normalized_matched: string
  auto_attach_allowed: boolean
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
  identity_match?: EvidenceIdentityMatch | null
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
  dbsnp_rsid?: string | null
  ensembl_gene_id?: string | null
  ensembl_transcript?: string | null
  transcript_aliases: string[]
  mane_select?: boolean | null
  view_count?: number | null
  updated_at?: string | null
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
  omim_cross_references: OmimCrossReference[]
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

export type ComputationalStandardStatus = 'published' | 'draft' | 'shadow' | 'withdrawn'
export type ComputationalEvidenceFamily = 'PP3_BP4' | 'SPLICE' | 'other'
export type ComputationalApplicability =
  | 'applicable'
  | 'not_applicable'
  | 'unavailable'
  | 'not_assessed'
export type ComputationalCountedStatus =
  | 'counted'
  | 'context_only'
  | 'separate_mechanism'
  | 'rejected'

export interface ComputationalAlternate {
  predictor_id: string
  raw_score?: string | null
  calibration_normalized_score?: string | null
  score_unit?: string | null
  calibration_id?: string | null
  calibration_version?: string | null
  evidence_code?: 'PP3' | 'BP4' | null
  calibration_points?: string | null
  counted_status: ComputationalCountedStatus
  non_counted_reason?: string | null
  tool_version?: string | null
  model_version?: string | null
  data_version?: string | null
  source_version?: string | null
  source_url?: string | null
}

export interface ComputationalEvidenceDecision {
  ruleset_id: string
  ruleset_version: string
  standard_label: string
  standard_status: ComputationalStandardStatus
  application_id: string
  gene_id?: string | null
  disease_id?: string | null
  transcript_id?: string | null
  protein_id?: string | null
  normalized_variant_id?: string | null
  variant_scope: string
  mechanism_applicability: string
  evidence_family: ComputationalEvidenceFamily
  selected_predictor_id?: string | null
  selection_policy: string
  selection_rationale: string
  declared_fallback_policy: string
  applicability: ComputationalApplicability
  raw_score?: string | null
  calibration_normalized_score?: string | null
  score_unit?: string | null
  score_native_precision?: string | null
  score_quantization_rule?: string | null
  evidence_code?: 'PP3' | 'BP4' | null
  calibration_points?: string | null
  evidence_points: string
  evidence_label: string
  calibration_id?: string | null
  calibration_version?: string | null
  calibration_profile_checksum?: string | null
  interval_lower?: string | null
  interval_lower_inclusive?: boolean | null
  interval_upper?: string | null
  interval_upper_inclusive?: boolean | null
  dependency_group: string
  counted_status: ComputationalCountedStatus
  non_counted_reason?: string | null
  tool_version?: string | null
  model_version?: string | null
  data_version?: string | null
  source_version?: string | null
  source_url?: string | null
  source_retrieved_at?: string | null
  source_checksum?: string | null
  alternates: ComputationalAlternate[]
  warnings: string[]
}

export interface ComputationalPredictorRow {
  name: string
  score?: string | number | null
  threshold?: string | number | null
  interpretation?: string | null
  source: string
  source_id?: string | null
  version?: string | null
  calibrated_label?: string | null
  calibration_bucket?: RampVerdict | null
  calibration_method?: string | null
  calibration_version?: string | null
  calibration_id?: string | null
  calibration_profile_checksum?: string | null
  calibration_normalized_score?: string | null
  score_unit?: string | null
  score_native_precision?: string | null
  score_quantization_rule?: string | null
  evidence_code?: 'PP3' | 'BP4' | 'SPLICE' | null
  evidence_points?: string | null
  interval_lower?: string | null
  interval_lower_inclusive?: boolean | null
  interval_upper?: string | null
  interval_upper_inclusive?: boolean | null
  source_url?: string | null
  public_serialization_allowed?: boolean | null
  launch_gate?: string | null
  warnings: string[]
}

export interface ComputationalDeepDiveSection {
  predictors: ComputationalPredictorRow[]
  selection_accounting?: string | null
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
  matched_query_id?: string | null
  evidence_field?: string | null
  evidence_snippet?: string | null
  last_update_posted_at?: string | null
  fetched_at?: string | null
}

export interface ClinicalTrialQueryExecution {
  query_id?: string | null
  lane?: string | null
  query_term?: string | null
  params: Record<string, string>
  source_url?: string | null
  registry_source_url?: string | null
  registry_source_release?: string | null
  status?: string | null
  result_count: number
  warnings: string[]
}

export interface TherapiesTrialsSection {
  trial_rows: TrialMatch[]
  query_executions: ClinicalTrialQueryExecution[]
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
  unavailable_reason?: string | null
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
  transcript_aliases: string[]
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

export interface ReportSectionSignal {
  section_id: string
  label: string
  priority: number
  confidence: number
  relevance: ReportSectionRelevance
  source_strength: ReportSectionSourceStrength
  status: ReportSectionSignalStatus
  default_open: boolean
  headline?: string | null
  data_notes: string[]
  source_refs: string[]
}

export interface VariantReportProfile {
  extraction_plan?: ReportExtractionPlan | null
  header?: VariantReportHeader | null
  interpretation_summary?: InterpretationSummary | null
  disease_mechanism?: DiseaseMechanismSection | null
  gene_context_snapshot?: GeneContextSnapshot | null
  population_frequency?: PopulationFrequencyReportSection | null
  molecular_context?: MolecularContextSection | null
  computational_decision?: ComputationalEvidenceDecision | null
  computational_deep_dive?: ComputationalDeepDiveSection | null
  acmg_worksheet?: AcmgWorksheetLedger | null
  expert_panel?: ExpertPanelSection | null
  therapies_trials?: TherapiesTrialsSection | null
  lovd_basic_records?: LovdBasicRecordsSection | null
  section_signals: ReportSectionSignal[]
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

export interface PaperCandidateContext {
  gene?: string | null
  hgvs?: string | null
  level?: string
  context?: string
  validation_status?: string
  validated?: boolean
  evidence_quote?: string | null
  source_support?: string[]
  papers?: string[]
}

export interface PaperContext {
  candidates: PaperCandidateContext[]
  source_count: number
  sources?: string[]
}

export interface BatchVariantContext {
  gene?: string | null
  variant?: string | null
  clinical_significance?: string | null
  acmg_classification?: string | null
  classification?: string | null
  gnomad_af?: number | null
}

export interface BatchContext {
  variant_count: number
  annotated: boolean
  sources?: string[]
  panels?: string[]
  filters?: string[]
  classification_counts?: Record<string, number>
  panel_missing_genes?: string[]
  variants: BatchVariantContext[]
}

export interface ChatRequest {
  question: string
  // Optional: report-less surfaces (Workbench, Paper → Variants, Batch cohort)
  // ground the chat in `workbench` / `paper` / `batch` instead. The backend
  // requires at least one scoped context.
  variant_context?: ReportPayload
  history?: ChatMessage[]
  workbench?: WorkbenchContext | null
  paper?: PaperContext | null
  batch?: BatchContext | null
}

export interface ChatResponse {
  answer: string
}

// ─────────────────────────────────────────────────────────────
// Workbench engine endpoints — mirrors app/backend/app/schemas/workbench.py
// (Stubbed responses for v2; real engines deferred to M-002.)
// ─────────────────────────────────────────────────────────────

export type PrimerMode = 'sanger' | 'qpcr' | 'arms'
export type SecondaryStructureRisk = 'low' | 'moderate' | 'high' | 'not_assessed'
export type PrimerTemplateStrand = 'Plus' | 'Minus'
export type SsodnProtocol = 'lab_genomic' | 'guide_pam_block'
export type SsodnOrientation = 'sense' | 'antisense'
export type SsodnStrandRequest = 'auto' | '+' | '-'
export type HdrEfficiencyStatus = 'executed' | 'not_assessed' | 'unavailable'

export interface PrimerRequest {
  gene: string
  cdna: string
  design_context?: WorkbenchDesignContextV1 | null
  design_context_v2?: WorkbenchDesignContextV2 | null
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
  secondary_structure_risk?: SecondaryStructureRisk
  secondary_structure_notes?: string
  self_any_forward?: number | null
  self_any_reverse?: number | null
  self_end_forward?: number | null
  self_end_reverse?: number | null
  hairpin_tm_forward?: number | null
  hairpin_tm_reverse?: number | null
  pair_compl_end?: number | null
  forward_strand?: PrimerTemplateStrand | null
  reverse_strand?: PrimerTemplateStrand | null
  forward_template_start?: number | null
  forward_template_stop?: number | null
  reverse_template_start?: number | null
  reverse_template_stop?: number | null
  genomic_chromosome?: string | null
  genome_build?: string | null
  forward_genomic_start?: number | null
  forward_genomic_stop?: number | null
  reverse_genomic_start?: number | null
  reverse_genomic_stop?: number | null
  amplicon_template_start?: number | null
  amplicon_template_end?: number | null
  amplicon_genomic_start?: number | null
  amplicon_genomic_end?: number | null
  notes?: string
  recommended?: boolean
}

export type WorkbenchSourceStatus =
  | 'source_backed'
  | 'local_provider'
  | 'fallback'
  | 'fixture'
  | 'gated'
  | 'unavailable'

export interface SourceDisclosure {
  source_status: WorkbenchSourceStatus
  provider_id: string
  provider_label: string
  source_version?: string | null
  cache_status?: string | null
  warnings: string[]
  requirements: string[]
}

export interface WorkbenchV2ResponseEnvelope {
  execution_disclosure?: CapabilityExecutionDisclosureV2 | null
  verified_context?: WorkbenchDesignContextV2 | null
  context_binding?: WorkbenchResultBindingV2 | null
}

export interface PrimerResponse extends WorkbenchV2ResponseEnvelope {
  mode: PrimerMode
  pairs: PrimerPair[]
  source_disclosure?: SourceDisclosure | null
}

export type CasEnzyme = 'SpCas9' | 'SaCas9' | 'Cas12a'
export type CrisprScoreFamilyV2 = 'on_target' | 'off_target' | 'enumeration'
export type CrisprScoreDirectionV2 = 'higher_is_better' | 'lower_is_better' | 'descriptive'

export interface CrisprVerifiedLocusV2 {
  genome_build: 'GRCh38'
  chromosome: string
  protospacer_start: number
  protospacer_end: number
  pam_start: number
  pam_end: number
  cut_position: number
  strand: '+' | '-'
}

export interface CrisprGuideIdentityV2 {
  schema_version?: 'crispr_guide_identity.v2'
  guide_id: string
  guide: string
  pam: string
  enzyme: CasEnzyme
  locus: CrisprVerifiedLocusV2
  context_digest: string
  identity_sha256: string
}

export interface CrisprScoreV2 {
  score_id: string
  family: CrisprScoreFamilyV2
  algorithm_id: string
  algorithm_version: string
  value: number
  scale_min: number
  scale_max: number
  direction: CrisprScoreDirectionV2
  context_digest: string
  guide_identity_sha256: string
  execution_disclosure: CapabilityExecutionDisclosureV2
}

export interface CrisprRequest {
  gene: string
  cdna: string
  design_context?: WorkbenchDesignContextV1 | null
  design_context_v2?: WorkbenchDesignContextV2 | null
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
  identity?: CrisprGuideIdentityV2 | null
  scores?: CrisprScoreV2[]
  execution_disclosure?: CapabilityExecutionDisclosureV2 | null
}

export interface HdrSsodn {
  reference_arm: string
  variant_arm: string
  repair_template: string
  edits_encoded: string[]
  arm_lengths: Record<string, number>
  estimated_hdr_efficiency: number
}

export interface CrisprResponse extends WorkbenchV2ResponseEnvelope {
  cas: CasEnzyme
  guides: CrisprGuide[]
  ssodn?: HdrSsodn | null
  source_disclosure?: SourceDisclosure | null
}

export interface CrisprSsodnRequest {
  gene: string
  cdna: string
  design_context?: WorkbenchDesignContextV1 | null
  design_context_v2?: WorkbenchDesignContextV2 | null
  transcript?: string | null
  protein_change?: string | null
  species?: 'human' | 'mouse'
  genome_build?: string
  oligo_length?: number
  variant_offset?: number | null
  strand?: SsodnStrandRequest
  orientation?: SsodnOrientation
  protocol?: SsodnProtocol
  guide_sequence?: string | null
  pam_sequence?: string | null
  pam_blocking_enabled?: boolean
}

export interface CrisprSsodnDesign {
  reference_arm: string
  variant_arm: string
  repair_template: string
  edits_encoded: string[]
  arm_lengths: Record<string, number>
  estimated_hdr_efficiency?: number | null
  hdr_efficiency_status: HdrEfficiencyStatus
  hdr_efficiency_disclosure: CapabilityExecutionDisclosureV2
  oligo_sequence: string
  oligo_length: number
  oligo_name: string
  variant_offset: number
  variant_genomic?: string | null
  intron_mask: boolean[]
  strand: '+' | '-'
  orientation: SsodnOrientation
  protocol: SsodnProtocol
  template_source: string
  genome_build: string
}

export interface CrisprSsodnResponse extends WorkbenchV2ResponseEnvelope {
  genome_build: string
  ssodn: CrisprSsodnDesign
  warnings: string[]
  source_disclosure?: SourceDisclosure | null
}

export interface CrisprOffTargetLocus {
  chromosome: string
  position: number
  strand?: '+' | '-'
}

export interface CrisprOffTargetRequest {
  guide: string
  pam?: string
  enzyme?: CasEnzyme
  genome_build?: string
  max_mismatches?: number
  on_target_locus?: CrisprOffTargetLocus | null
  design_context?: WorkbenchDesignContextV1 | null
  design_context_v2?: WorkbenchDesignContextV2 | null
  guide_identity?: CrisprGuideIdentityV2 | null
}

export interface CrisprOffTargetSite {
  sequence: string
  pam: string
  score: number
  mismatches: number
  gene?: string | null
  gene_id?: string | null
  biotype?: string | null
  chromosome: string
  strand: '+' | '-'
  position: number
  on_target: boolean
  scores?: CrisprScoreV2[]
}

export interface CrisprOffTargetResponse extends WorkbenchV2ResponseEnvelope {
  genome_build: string
  sites: CrisprOffTargetSite[]
  source_disclosure?: SourceDisclosure | null
  guide_identity?: CrisprGuideIdentityV2 | null
}

export interface CrisprScreeningRegion {
  chromosome: string
  start: number
  end: number
  genome_build?: string
  strand?: '+' | '-'
}

export interface CrisprScreeningPrimerTarget {
  site_index: number
  point?: string | null
  chromosome?: string | null
  position?: number | null
  strand?: '+' | '-'
  region?: CrisprScreeningRegion | null
  template_sequence?: string | null
  target_offset?: number | null
  sequence?: string | null
  pam?: string | null
}

export interface CrisprScreeningPrimerRequest {
  sites: CrisprScreeningPrimerTarget[]
  design_context?: WorkbenchDesignContextV1 | null
  design_context_v2?: WorkbenchDesignContextV2 | null
  genome_build?: string
  flank_bp?: number
  naming_prefix?: string
  mode?: PrimerMode
  tm_min?: number
  tm_max?: number
  product_size_min?: number
  product_size_max?: number
  avoid_snps?: boolean
}

export interface ScreeningPrimer {
  site_index: number
  point: string
  region: string
  name_forward: string
  name_reverse: string
  forward: string
  reverse: string
  tm_forward: number
  tm_reverse: number
  gc_forward: number
  gc_reverse: number
  product_size: number
  specificity_hits: number
  other_products: string
  secondary_structure_risk?: SecondaryStructureRisk
  secondary_structure_notes?: string
  recommended?: boolean
  notes?: string
  template_source: string
}

export interface CrisprScreeningPrimerResponse extends WorkbenchV2ResponseEnvelope {
  mode: PrimerMode
  primers: ScreeningPrimer[]
  warnings: string[]
  source_disclosure?: SourceDisclosure | null
}

export interface CrisprTideSpectrumBin {
  size: number
  observed: number
  predicted?: number | null
}

export interface CrisprTraceDifferenceBin {
  size: number
  observed_fraction: number
}

export interface CrisprTideResponse extends WorkbenchV2ResponseEnvelope {
  source_backed: boolean
  analysis_kind: 'tide' | 'descriptive_trace_comparison'
  provider_label: string
  analysis_disclosure: CapabilityExecutionDisclosureV2
  source_disclosure?: SourceDisclosure | null
  cut_site_index: number
  editing_efficiency: number | null
  r_squared: number | null
  spectrum: CrisprTideSpectrumBin[]
  comparison_window_start: number | null
  comparison_window_end: number | null
  consensus_difference_fraction: number | null
  sequence_identity: number | null
  differences: CrisprTraceDifferenceBin[]
  predicted_available?: boolean
  notes: string
  warnings: string[]
}

export interface AlignRequest {
  gene: string
  cdna: string
  design_context?: WorkbenchDesignContextV1 | null
  design_context_v2?: WorkbenchDesignContextV2 | null
  user_sequence?: string | null
  ab1_blob_base64?: string | null
}

export interface AlignReferenceRequest {
  gene: string
  cdna: string
  design_context?: WorkbenchDesignContextV1 | null
  design_context_v2?: WorkbenchDesignContextV2 | null
  transcript?: string | null
  species?: 'human' | 'mouse'
}

export interface AlignTraceRequest {
  ab1_blob_base64: string
  design_context_v2?: WorkbenchDesignContextV2 | null
}

export interface TraceChannel {
  base: 'A' | 'T' | 'C' | 'G'
  values: number[]
}

export interface AlignTraceTrimRange {
  start: number
  end: number
  method: string
  q_cutoff: number
}

export interface AlignTraceHetCall {
  index: number
  called_base: 'A' | 'T' | 'C' | 'G'
  secondary_base: 'A' | 'T' | 'C' | 'G'
  main_ratio: number
  flank_ratio: number
  avg_q: number
  primary_signal: number
  secondary_signal: number
}

export interface AlignTraceResponse extends WorkbenchV2ResponseEnvelope {
  sequence: string
  base_calls: string[]
  q_scores: number[]
  base_confidence: number[]
  peak_locations: number[]
  trace_channels: TraceChannel[]
  sample_count: number
  trim: AlignTraceTrimRange
  het: AlignTraceHetCall[]
  noise_floor: number
  warnings: string[]
  source_disclosure?: SourceDisclosure | null
}

export interface AlignResponse extends WorkbenchV2ResponseEnvelope {
  reference: string
  sanger_read: string
  match_line: string
  mismatch_positions: number[]
  target_position: number
  trace_channels: TraceChannel[]
  base_calls: string[]
  q_scores: number[]
  source_disclosure?: SourceDisclosure | null
}

export interface AlignReferenceResponse extends WorkbenchV2ResponseEnvelope {
  gene: string
  cdna: string
  transcript?: string | null
  transcript_hgvs: string
  genome_build: string
  genomic_hg38?: string | null
  strand: string
  reference: string
  target_position: number
  reference_base?: string | null
  alternate_base?: string | null
  source: string
  warnings: string[]
  source_disclosure?: SourceDisclosure | null
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
  | 'alphamissense'
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

export interface ProteinAlphaMissenseResidue {
  aa: number
  mean_score?: number | null
  max_score?: number | null
  scored_variant_count: number
}

export interface ProteinAlphaMissenseHeatmap {
  status: 'available' | 'unavailable' | 'partial'
  fail_closed_reason?: string | null
  protein_length?: number | null
  aa_start: number
  aa_end?: number | null
  source_id: string
  source_release?: string | null
  calibrated_method?: string | null
  queried_aa?: number | null
  queried_score?: number | null
  queried_calibrated_label?: string | null
  residues: ProteinAlphaMissenseResidue[]
  warnings: string[]
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
  alphamissense_heatmap?: ProteinAlphaMissenseHeatmap | null
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
  transcript_projection?: ViewerTranscriptProjection | null
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
export type PanelLaunchPostureV2 = 'ready' | 'gated' | 'unavailable'
export type PanelIntervalScopeV2 = 'whole_gene' | 'mane_exon_splice' | 'capture_bed'

export interface PanelIntervalProvenanceV2 {
  scope: PanelIntervalScopeV2
  genome_build: 'GRCh38'
  interval_release: string
  interval_manifest_id: string
  interval_sha256: string
  splice_flank_bases?: number | null
}

export interface PanelSourceSnapshotV2 {
  schema_version?: 'panel_source_snapshot.v2'
  snapshot_id: string
  source: PanelSource
  version: string
  release: string
  retrieved_at: string
  launch_posture: PanelLaunchPostureV2
  licence_id: string
  provenance_url?: string | null
  artifact_manifest_id?: string | null
  artifact_sha256?: string | null
  execution_disclosure: CapabilityExecutionDisclosureV2
}

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
  interval_provenance_v2?: PanelIntervalProvenanceV2 | null
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
  source_snapshot_v2?: PanelSourceSnapshotV2 | null
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
  source_snapshot_v2?: PanelSourceSnapshotV2 | null
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
export type BatchInputFormatV2 = 'vcf' | 'vcf_gz' | 'bcf'
export type BatchAnalysisScopeV2 = 'wes' | 'targeted_panel'
export type BatchCohortModelV2 = 'single' | 'proband' | 'small_family'
export type BatchNormalizationStatusV2 =
  | 'normalized'
  | 'reference_mismatch'
  | 'unsupported'
  | 'failed'
export type BatchFilterStageV2 = 'pre_annotation' | 'post_annotation'
export type BatchFilterOutcomeV2 = 'included' | 'excluded' | 'deferred'
export type BatchFilterReasonV2 =
  | 'pass_filter'
  | 'quality'
  | 'region'
  | 'gene_scope'
  | 'capture_scope'
  | 'genotype'
  | 'depth'
  | 'duplicate'
  | 'consequence'
  | 'population_frequency'
  | 'classification'
  | 'evidence_state'
  | 'annotation_cap'
  | 'source_unavailable'
export type BatchIntervalScopeV2 = 'whole_gene' | 'mane_exon_splice' | 'capture_bed'
export type BatchFieldNameV2 =
  | 'gene'
  | 'hgvs_c'
  | 'hgvs_p'
  | 'clinvar_verdict'
  | 'gnomad_af'
  | 'predictor_ensemble'
  | 'acmg_classification'
export type BatchFieldValueStatusV2 = 'executed' | 'unavailable' | 'not_applicable'
export type BatchExportFormatV2 = 'tsv' | 'csv' | 'jsonl' | 'vcf'
export type BatchExportStateV2 = 'queued' | 'running' | 'ready' | 'failed' | 'expired'

export interface BatchInputEnvelopeV2 {
  schema_version?: 'batch_input_envelope.v2'
  format: BatchInputFormatV2
  analysis_scope: BatchAnalysisScopeV2
  cohort_model: BatchCohortModelV2
  genome_build: 'GRCh38'
  source_sha256: string
  compressed_bytes: number
  decompressed_bytes: number
  raw_record_count: number
  sample_count: number
  post_filter_variant_cap: number
  accepted_variant_classes: ('snv' | 'short_indel')[]
  warnings?: string[]
}

export interface BatchAlleleV2 {
  genome_build: 'GRCh38'
  chromosome: string
  position: number
  reference: string
  alternate: string
}

export interface BatchAlleleIdentityV2 {
  original: BatchAlleleV2
  normalized?: BatchAlleleV2 | null
  status: BatchNormalizationStatusV2
  source_record_index: number
  normalization_algorithm_id: string
  normalization_algorithm_version: string
  reference_manifest_id: string
  reference_sha256: string
  warnings?: string[]
}

export interface BatchSourceSnapshotV2 {
  schema_version?: 'batch_source_snapshot.v2'
  snapshot_id: string
  created_at: string
  genome_build: 'GRCh38'
  reference_release: string
  capabilities: CapabilityExecutionDisclosureV2[]
}

export interface BatchFilterPlanV2 {
  pass_only?: boolean
  minimum_quality?: number | null
  regions?: string[]
  interval_scope: BatchIntervalScopeV2
  interval_snapshot_id: string
  panel_snapshot_id?: string | null
  max_population_af?: number | null
  consequence_terms?: string[]
  classifications?: string[]
  require_evidence_sources?: string[]
}

export interface BatchFilterDispositionV2 {
  stage: BatchFilterStageV2
  outcome: BatchFilterOutcomeV2
  reason: BatchFilterReasonV2
  detail: string
  source_snapshot_id: string
}

export interface BatchSampleProvenanceV2 {
  sample_key: string
  source_sample_index: number
  genotype: string
  phased: boolean
  depth?: number | null
  genotype_quality?: number | null
}

export interface BatchFieldExecutionV2 {
  field_name: BatchFieldNameV2
  value_status: BatchFieldValueStatusV2
  execution_disclosure: CapabilityExecutionDisclosureV2
}

export interface BatchPagingV2 {
  snapshot_id: string
  limit: number
  next_cursor?: string | null
  total: number
  has_more: boolean
}

export interface BatchExportV2 {
  export_id: string
  format: BatchExportFormatV2
  state: BatchExportStateV2
  source_snapshot_id: string
  row_count: number
  sha256?: string | null
  expires_at?: string | null
}

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
  expires_at?: string | null
  single_use?: boolean | null
  input_envelope_v2?: BatchInputEnvelopeV2 | null
}

export interface BatchCreateRequest {
  variants?: ParsedVariant[] | null
  upload_ref?: string | null
  filters?: BatchFilters
  filter_plan_v2?: BatchFilterPlanV2 | null
}

export interface BatchCreateResponse {
  job_id: string
  n_input: number
  n_to_lookup: number
  est_seconds: number
  input_envelope_v2?: BatchInputEnvelopeV2 | null
  source_snapshot_v2?: BatchSourceSnapshotV2 | null
}

export interface BatchPage {
  limit: number
  next_cursor?: string | null
  total: number
  paging_v2?: BatchPagingV2 | null
}

export interface BatchJobQuery {
  limit?: number
  cursor?: string | null
  source_snapshot_id?: string | null
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
  allele_identity_v2?: BatchAlleleIdentityV2 | null
  source_snapshot_id?: string | null
  filter_dispositions_v2?: BatchFilterDispositionV2[]
  sample_provenance_v2?: BatchSampleProvenanceV2[]
  field_executions_v2?: BatchFieldExecutionV2[]
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
  input_envelope_v2?: BatchInputEnvelopeV2 | null
  source_snapshot_v2?: BatchSourceSnapshotV2 | null
  filter_dispositions_v2?: BatchFilterDispositionV2[]
  exports_v2?: BatchExportV2[]
}

// ---------------------------------------------------------------------------
// Product Workflow V1 — frozen cross-surface contract.
// Backend source: app/backend/app/schemas/workflow.py. These interfaces keep
// nullable fields explicit; absence and null are not interchangeable here.
// ---------------------------------------------------------------------------

export type VariantResolutionStatusV1 = 'resolved' | 'ambiguous' | 'unresolved'
export type WorkflowOriginSurfaceV1 =
  | 'report'
  | 'paper'
  | 'batch'
  | 'workbench'
  | 'library'
  | 'search'
export type WorkflowActiveToolV1 = 'viewer' | 'primer' | 'crispr' | 'align'
export type SelectionStrandV1 = '+' | '-'
export type SelectionOrientationV1 = 'genomic_forward' | 'genomic_reverse' | 'transcript'
export type SequenceBasisV1 = 'reference' | 'variant' | 'edited'
export type SelectionOverlapV1 = 'utr5' | 'utr3' | 'cds' | 'exon' | 'intron'
export type ProcessingExecutionV1 = 'browser' | 'eamos_backend' | 'external_provider'
export type ProcessingInputClassV1 =
  | 'variant_id'
  | 'sequence'
  | 'vcf'
  | 'paper_text'
  | 'pdf'
  | 'trace'
  | 'notes'
export type ProcessingRetentionV1 = 'none' | 'request_lifetime' | 'ttl' | 'account_saved'
export type WorkflowRunKindV1 = 'batch' | 'paper' | 'workbench'
export type WorkflowRunStatusV1 =
  | 'draft'
  | 'queued'
  | 'running'
  | 'completed'
  | 'partial'
  | 'failed'
  | 'cancelled'
  | 'expired'
export type WorkflowOwnerScopeV1 = 'account' | 'anonymous_session'
export type WorkflowArtifactKindV1 =
  | 'report_tsv'
  | 'report_html'
  | 'batch_tsv'
  | 'paper_tsv'
  | 'fasta'
  | 'primer_tsv'
  | 'primer_fasta'
  | 'guide_tsv'
  | 'ssodn_txt'
  | 'alignment_tsv'
  | 'workspace_json'
export type WorkflowArtifactDownloadStateV1 = 'client_generated' | 'ready' | 'expired'
export type RelatedVariantRelationshipV1 =
  | 'nearby'
  | 'same_gene'
  | 'same_class'
  | 'same_condition'
export type ConsequenceBucketV1 = 'lof' | 'missense' | 'noncoding' | 'synonymous'
export type WorkbenchViewV1 = 'window' | 'locus'
export type CompareViewV1 = 'cohort' | 'compare'
export type WorkflowAsyncStateV1 =
  | 'idle'
  | 'validating'
  | 'auth_required'
  | 'consent_required'
  | 'queued'
  | 'running'
  | 'completed'
  | 'partial'
  | 'empty'
  | 'failed'
  | 'cancelled'
  | 'expired'
  | 'stale'

export interface CanonicalVariantRefV1 {
  schema_version: 'canonical_variant_ref.v1'
  gene: string
  cdna: string
  transcript: string | null
  protein_hgvs: string | null
  genomic_hg38: string | null
  variant_key: string
  species: 'human'
  genome_build: 'GRCh38'
  resolution_status: VariantResolutionStatusV1
  source_support: string[]
  warnings: string[]
}

export interface SelectionRangeV1 {
  schema_version: 'selection_range.v1'
  variant_key: string
  transcript: string
  genome_build: 'GRCh38'
  chrom: string
  genomic_start: number
  genomic_end: number
  strand: SelectionStrandV1
  orientation: SelectionOrientationV1
  sequence_basis: SequenceBasisV1
  edit_revision: number
  sequence_sha256: string
  cdna_start: number | null
  cdna_end: number | null
  cds_start: number | null
  cds_end: number | null
  protein_start: number | null
  protein_end: number | null
  overlaps: SelectionOverlapV1[]
}

export interface WorkflowContextV1 {
  schema_version: 'workflow_context.v1'
  context_id: string | null
  variant: CanonicalVariantRefV1 | null
  origin_surface: WorkflowOriginSurfaceV1
  return_to: string | null
  batch_run_id: string | null
  paper_run_id: string | null
  workspace_id: string | null
  active_tool: WorkflowActiveToolV1 | null
  selection: SelectionRangeV1 | null
  created_at: string
  expires_at: string | null
}

export interface WorkbenchDesignContextV1 {
  schema_version: 'workbench_design_context.v1'
  variant: CanonicalVariantRefV1
  selection: SelectionRangeV1
  context_digest: string
}

export type WorkbenchEditOperationV2 = 'substitution' | 'deletion' | 'insertion' | 'delins'
export type WorkbenchContextOriginV2 = 'native_v2' | 'workbench_design_context.v1'
export type WorkbenchResultStateV2 = 'current' | 'stale'

export interface WorkbenchReferenceBasisV2 {
  schema_version?: 'workbench_reference_basis.v2'
  transcript: string
  genome_build: 'GRCh38'
  chrom: string
  genomic_start: number
  genomic_end: number
  strand: SelectionStrandV1
  orientation: SelectionOrientationV1
  source_id: string
  source_release: string
  source_record_id: string
  sequence_length: number
  sequence_sha256: string
}

export interface WorkbenchSparseEditV2 {
  edit_id: string
  operation: WorkbenchEditOperationV2
  start_offset: number
  end_offset: number
  reference_bases: string
  alternate_bases: string
}

export interface WorkbenchDesignContextV2 {
  schema_version?: 'workbench_design_context.v2'
  variant: CanonicalVariantRefV1
  reference: WorkbenchReferenceBasisV2
  selection: SelectionRangeV1
  edits?: WorkbenchSparseEditV2[]
  revision: number
  compatibility_origin?: WorkbenchContextOriginV2
  legacy_context_digest?: string | null
  context_digest: string
}

export interface WorkbenchResultBindingV2 {
  result_context_digest: string
  current_context_digest: string
  state: WorkbenchResultStateV2
  stale_reason?: string | null
}

export interface ProcessingDisclosureV1 {
  execution: ProcessingExecutionV1
  provider_id: string
  provider_label: string
  input_classes: ProcessingInputClassV1[]
  raw_input_persisted: boolean
  retention: ProcessingRetentionV1
  expires_at: string | null
  user_deletable: boolean
  consent_required: boolean
  warnings: string[]
}

export interface WorkflowArtifactV1 {
  artifact_id: string
  kind: WorkflowArtifactKindV1
  filename: string
  media_type: string
  generated_at: string
  source_run_id: string | null
  context_digest: string
  sha256: string
  download_state: WorkflowArtifactDownloadStateV1
}

export interface WorkflowRunV1 {
  schema_version: 'workflow_run.v1'
  run_id: string
  kind: WorkflowRunKindV1
  status: WorkflowRunStatusV1
  owner_scope: WorkflowOwnerScopeV1
  context: WorkflowContextV1
  done: number
  total: number
  created_at: string
  updated_at: string
  expires_at: string | null
  warnings: string[]
  source_disclosures: SourceDisclosure[]
  processing_disclosure: ProcessingDisclosureV1 | null
  artifacts: WorkflowArtifactV1[]
}

export interface RelatedVariantItemV1 {
  variant: CanonicalVariantRefV1
  relationship: RelatedVariantRelationshipV1
  distance_bp: number | null
  classification: ClassificationTier | null
  evidence_axis_summary: VariantReportCallCards | null
  source_disclosure: SourceDisclosure
  report_href: string
}

export interface RelatedVariantGroupV1 {
  items: RelatedVariantItemV1[]
  warnings: string[]
}

export interface CuratedVariantPageV1 {
  gene: string
  classification_filter: ClassificationTier | null
  consequence_filter: ConsequenceBucketV1 | null
  items: CanonicalVariantRefV1[]
  next_cursor: string | null
  total: number
  source_disclosure: SourceDisclosure
  warnings: string[]
}

const WORKFLOW_OPAQUE_ID_V1 = /^[A-Za-z0-9][A-Za-z0-9._~-]{0,127}$/

function assertWorkflowOpaqueIdV1(value: string, field: string): string {
  if (!WORKFLOW_OPAQUE_ID_V1.test(value)) throw new Error(`${field} must be an opaque identifier`)
  return value
}

function workflowHrefV1(path: string, entries: Array<[string, string]>): string {
  const query = entries
    .map(([key, value]) => `${workflowQueryPartV1(key)}=${workflowQueryPartV1(value)}`)
    .join('&')
  return `${path}?${query}`
}

function workflowQueryPartV1(value: string): string {
  // Match Python urllib.parse.urlencode/quote_plus so backend- and browser-built
  // canonical hrefs are byte-identical as well as semantically equivalent.
  return encodeURIComponent(value)
    .replace(/%20/g, '+')
    .replace(/[!'()*]/g, (char) => `%${char.charCodeAt(0).toString(16).toUpperCase()}`)
}

export function buildReportHrefV1(
  variant: CanonicalVariantRefV1,
  fromSurface?: WorkflowOriginSurfaceV1,
): string {
  const entries: Array<[string, string]> = [
    ['gene', variant.gene],
    ['cdna', variant.cdna],
  ]
  if (variant.transcript) entries.push(['transcript', variant.transcript])
  if (fromSurface) entries.push(['from', fromSurface])
  return workflowHrefV1('/report', entries)
}

export function buildWorkbenchHrefV1(
  variant: CanonicalVariantRefV1,
  options: {
    tool?: WorkflowActiveToolV1
    view?: WorkbenchViewV1
    contextId?: string
  } = {},
): string {
  if (
    options.tool &&
    ['primer', 'crispr', 'align'].includes(options.tool) &&
    variant.resolution_status !== 'resolved'
  ) {
    throw new Error('molecular-design tools require a resolved canonical variant')
  }
  const entries: Array<[string, string]> = [
    ['gene', variant.gene],
    ['cdna', variant.cdna],
  ]
  if (variant.transcript) entries.push(['transcript', variant.transcript])
  if (options.tool) entries.push(['tool', options.tool])
  if (options.view) entries.push(['view', options.view])
  if (options.contextId) {
    entries.push(['context_id', assertWorkflowOpaqueIdV1(options.contextId, 'context_id')])
  }
  return workflowHrefV1('/workbench', entries)
}

export function buildCompareHrefV1(options: {
  runId?: string
  contextId?: string
  view?: CompareViewV1
}): string {
  if (!options.runId && !options.contextId) throw new Error('runId or contextId is required')
  const entries: Array<[string, string]> = []
  if (options.runId) entries.push(['run_id', assertWorkflowOpaqueIdV1(options.runId, 'run_id')])
  if (options.contextId) {
    entries.push(['context_id', assertWorkflowOpaqueIdV1(options.contextId, 'context_id')])
  }
  if (options.view) entries.push(['view', options.view])
  return workflowHrefV1('/compare', entries)
}

export function buildPaperHrefV1(options: { runId?: string; contextId?: string }): string {
  if (!options.runId && !options.contextId) throw new Error('runId or contextId is required')
  const entries: Array<[string, string]> = []
  if (options.runId) entries.push(['run_id', assertWorkflowOpaqueIdV1(options.runId, 'run_id')])
  if (options.contextId) {
    entries.push(['context_id', assertWorkflowOpaqueIdV1(options.contextId, 'context_id')])
  }
  return workflowHrefV1('/paper', entries)
}
