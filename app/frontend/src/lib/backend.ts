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
}

export interface EvidenceSourceSummary {
  source: string
  status: string
  request_identity: Record<string, unknown>
  summary: Record<string, unknown>
  warnings: string[]
  source_url?: string | null
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

export interface LookupRequest {
  gene: string
  cdna: string
  transcript?: string | null
  protein_change?: string | null
  species: 'human' | 'mouse'
}

export interface LookupResponse {
  query: string
  species: string
  report_payload: ReportPayload
  evidence: EvidenceSourceSummary[]
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
export type ViewerWindowKind = 'around_variant' | 'cds_range'
export type ViewerSegmentKind = 'exon' | 'intron'
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
  cds_start?: number | null
  cds_end?: number | null
  cds_flank_bp: number
  intron_flank_bp: number
  display_cds_start: number
  display_cds_end: number
  total_display_bases: number
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

export interface ProteinFeatures {
  signal_peptide?: ProteinRangeFeature | null
  transmembrane: ProteinRangeFeature[]
  domains: ProteinDomain[]
  active_sites: ProteinActiveSite[]
  membrane_binding: ProteinRangeFeature[]
  palmitoylation: ProteinPointFeature[]
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

export interface GeneViewerResponse {
  identity: ViewerIdentity
  locus: ViewerLocus
  summary: ViewerSummary
  window: ViewerWindow
  segments: ViewerSegment[]
  queried_variant: QueriedVariant
  sequences: ViewerSequences
  tracks: ViewerTracks
  provenance: ViewerProvenance
}
