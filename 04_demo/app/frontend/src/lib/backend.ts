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
}

export interface EvidenceSourceSummary {
  source: string
  status: string
  request_identity: Record<string, unknown>
  summary: Record<string, unknown>
  warnings: string[]
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
