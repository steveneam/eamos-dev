// ClinGen expert-panel (VCEP) type definitions for ExpertPanelSection.
//
// Type-only. The RPE65 fixture that used to live here was removed 2026-05-30:
// the component no longer falls back to a hardcoded panel (it renders null
// when `payload.report_profile.expert_panel` is absent), so sample data can
// never paint onto a non-RPE65 query. Live data comes from the backend
// expert-panel contract (Codex CAR #3).

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

export interface ExpertPanelCriterion {
  code: string
  applied_strength: string
  default_strength: string
  state: 'met' | 'not_met' | 'not_assessed' | 'conflicting'
  rationale?: string | null
  evidence_refs: string[]
}

export interface ExpertPanelVcep {
  id: string
  name: string
  affiliation_id?: string | null
  last_curated_date: string
  vcep_url: string
}

export interface ExpertPanelProvenance {
  source_url: string
  fetched_at: string
  source_version: string
  cache_record_id?: string | null
  raw_jsonld_ref?: string | null
}

export interface ExpertPanelData {
  vcep: ExpertPanelVcep
  final_classification: ExpertPanelClassification
  narrative: string
  criteria: ExpertPanelCriterion[]
  source_scope: string
  provenance: ExpertPanelProvenance
  freshness: ExpertPanelFreshness
  freshness_reason?: ExpertPanelFreshnessReason | null
}
