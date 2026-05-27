// Inline RPE65 IRD VCEP fixture for the M-005 ExpertPanelSection
// (mock-first per CAR #3 — opened 2026-05-28 03:18 +1000).
// Component falls back to this when the real `payload.report_profile.expert_panel`
// field isn't yet emitted by the backend. Swaps out once Codex closes CAR #3.

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

export const EXPERT_PANEL_RPE65_FIXTURE: ExpertPanelData = {
  vcep: {
    id: 'ClinGen:IRD',
    name: 'Inherited Retinal Dystrophies VCEP',
    affiliation_id: '50039',
    last_curated_date: '2023-08-14',
    vcep_url:
      'https://erepo.clinicalgenome.org/evrepo/ui/classifications/CA189146',
  },
  final_classification: 'likely_benign',
  narrative:
    'The Inherited Retinal Dystrophies VCEP classified RPE65 c.260A>G p.(Asp87Gly) as Likely benign for autosomal recessive Leber congenital amaurosis 2 (MIM 204100). The variant is observed at low but non-trivial frequency in gnomAD (NFE: 4 alleles; no homozygotes) and lacks definitive segregation or case-level support. Per ClinGen SVI specifications applied by this VCEP, BS1_Strong + BS2_Supporting + PM2_Supporting + PP3_Moderate offsets yield a Likely benign final call.',
  criteria: [
    {
      code: 'BS1',
      applied_strength: 'BS1_Strong',
      default_strength: 'BS1_Strong',
      state: 'met',
      rationale:
        'Allele frequency in gnomAD v4 exceeds the IRD-specific BS1 threshold (4 alleles / ~251,490 NFE).',
      evidence_refs: ['gnomad_v4'],
    },
    {
      code: 'BS2',
      applied_strength: 'BS2_Supporting',
      default_strength: 'BS2_Strong',
      state: 'met',
      rationale:
        'Observed in a single hemizygous-state individual >50y without LCA phenotype; downgraded from Strong to Supporting per ClinGen IRD VCEP rules.',
      evidence_refs: ['humgen_uk'],
    },
    {
      code: 'PM2',
      applied_strength: 'PM2_Supporting',
      default_strength: 'PM2_Moderate',
      state: 'met',
      rationale:
        'Rare in controls but not absent; downgraded from Moderate to Supporting per ClinGen IRD VCEP specs.',
      evidence_refs: ['gnomad_v4'],
    },
    {
      code: 'PP3',
      applied_strength: 'PP3_Moderate',
      default_strength: 'PP3_Supporting',
      state: 'met',
      rationale:
        'REVEL 0.78 + SpliceAI 0.32 cross-engine support; upgraded from Supporting to Moderate per VCEP-specific computational threshold.',
      evidence_refs: ['revel', 'spliceai'],
    },
  ],
  source_scope:
    'ClinGen Evidence Repository — IRD VCEP curation for RPE65 c.260A>G',
  provenance: {
    source_url:
      'https://erepo.clinicalgenome.org/evrepo/api/classifications/CA189146',
    fetched_at: '2026-05-27T22:14:00Z',
    source_version: 'ClinGen Evidence Repo 2024.06',
    cache_record_id: 'expertpanel:CA189146',
    raw_jsonld_ref: '/source-cache/clingen-evrepo/CA189146.jsonld',
  },
  freshness: 'fresh',
  freshness_reason: 'cache_hit',
}
