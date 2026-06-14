// Illustrative `.eamos-mock` fixture for the ACMG-viz instruments. The backend
// points engine (acmg_points_engine.py) exists but does not yet POPULATE the
// report payload (Codex's evidence/report-population slice is gated on Steven's
// approval), so `payload.eamos_computed_classification` is null today. The report
// falls back to this fixture and flags every instrument with an `.eamos-mock`
// chip until the live block lands — same mock-first posture as ProteinTrack /
// the §2 in-silico tiles.
//
// The fixture is built to AGREE IN DIRECTION with the report's curated clinical
// verdict (the precedence call), so the illustrative advisory never contradicts
// it on the same page — the engine still produces the real numbers once wired.
// Shape + rules mirror docs/report-acmg-viz/spec.md §3 and Codex's engine
// contract: applied_strength is per-criterion (no fixed code→points map);
// mutually-exclusive pairs never co-fire (PM2/BA1, PM2/BS1, PP3/BP4, PS3/BS3);
// PP5/BP6 are demoted to permanent not-assessed audit rows; untriggered codes are
// still emitted for audit completeness.

import type {
  EamosComputedClassification,
  EamosComputedCriterion,
  EamosComputedTier,
} from '@/lib/backend'
import { posterior } from './points'

type Trig = Pick<EamosComputedCriterion, 'code' | 'direction' | 'applied_strength' | 'points'> &
  Partial<EamosComputedCriterion>

// Per-tier triggered criteria, chosen to be plausible for any variant (no PVS1,
// which is LoF-only) and to sum to a representative net inside the tier band.
const TRIGGERED_BY_TIER: Record<EamosComputedTier, Trig[]> = {
  Pathogenic: [
    { code: 'PS3', direction: 'pathogenic', applied_strength: 'strong', points: 4, evidence_value: 'damaging in a calibrated functional assay', source_db: 'MaveDB' },
    { code: 'PM1', direction: 'pathogenic', applied_strength: 'moderate', points: 2, evidence_value: 'functional domain / hotspot', source_db: 'UniProt' },
    { code: 'PM5', direction: 'pathogenic', applied_strength: 'moderate', points: 2, evidence_value: 'novel change at a known-pathogenic residue', source_db: 'ClinVar' },
    { code: 'PP3', direction: 'pathogenic', applied_strength: 'moderate', points: 2, evidence_value: 'AlphaMissense 0.4365', threshold: '0.170-0.791 -> PP3_Moderate (Bergquist-2025)', source_db: 'AlphaMissense' },
    { code: 'PM2', direction: 'pathogenic', applied_strength: 'supporting', points: 1, evidence_value: 'gnomAD v4 popmax 4e-6', source_db: 'gnomAD v4' },
  ],
  'Likely Pathogenic': [
    { code: 'PM1', direction: 'pathogenic', applied_strength: 'moderate', points: 2, evidence_value: 'Laminin G-like 4 domain', source_db: 'UniProt' },
    { code: 'PP3', direction: 'pathogenic', applied_strength: 'moderate', points: 2, evidence_value: 'AlphaMissense 0.4365', threshold: '0.170-0.791 -> PP3_Moderate (Bergquist-2025)', source_db: 'AlphaMissense' },
    { code: 'PM2', direction: 'pathogenic', applied_strength: 'supporting', points: 1, evidence_value: 'gnomAD v4 popmax 1.2e-5', source_db: 'gnomAD v4' },
    { code: 'PP2', direction: 'pathogenic', applied_strength: 'supporting', points: 1, evidence_value: 'missense-constrained gene', source_db: 'gnomAD constraint' },
  ],
  VUS: [
    { code: 'PM2', direction: 'pathogenic', applied_strength: 'supporting', points: 1, evidence_value: 'gnomAD v4 popmax 3e-5', source_db: 'gnomAD v4' },
    { code: 'PP3', direction: 'pathogenic', applied_strength: 'supporting', points: 1, evidence_value: 'REVEL 0.71 (supporting)', threshold: '≥ 0.644 → Supporting (Pejaver-2022)', source_db: 'REVEL' },
  ],
  'Likely Benign': [
    { code: 'BS1', direction: 'benign', applied_strength: 'strong', points: -4, evidence_value: 'AF greater than expected for the disorder', source_db: 'gnomAD v4' },
    { code: 'BP4', direction: 'benign', applied_strength: 'supporting', points: -1, evidence_value: 'REVEL 0.18 (supporting benign)', threshold: '≤ 0.183 → Supporting (Pejaver-2022)', source_db: 'REVEL' },
  ],
  Benign: [
    { code: 'BS1', direction: 'benign', applied_strength: 'strong', points: -4, evidence_value: 'AF well above disease expectation', source_db: 'gnomAD v4' },
    { code: 'BS2', direction: 'benign', applied_strength: 'strong', points: -4, evidence_value: 'observed in healthy adults', source_db: 'gnomAD v4' },
  ],
}

// Standard not-assessed / untriggered audit rows (completeness). Codes already
// triggered for the chosen tier are dropped so nothing appears twice.
const AUDIT_ROWS: EamosComputedCriterion[] = [
  { code: 'PVS1', direction: 'pathogenic', triggered: false, applied_strength: null, points: 0, evidence_value: 'N/A — not a predicted loss-of-function', source_db: 'NMDetective-B / Abou-Tayoun PVS1' },
  { code: 'PS1', direction: 'pathogenic', triggered: false, applied_strength: null, points: 0, evidence_value: 'not assessed' },
  { code: 'PS3', direction: 'pathogenic', triggered: false, applied_strength: null, points: 0, evidence_value: 'no calibrated functional assay (MaveDB)', source_db: 'MaveDB' },
  { code: 'PM1', direction: 'pathogenic', triggered: false, applied_strength: null, points: 0, evidence_value: 'not assessed' },
  { code: 'PM2', direction: 'pathogenic', triggered: false, applied_strength: null, points: 0, evidence_value: 'not assessed' },
  { code: 'PM5', direction: 'pathogenic', triggered: false, applied_strength: null, points: 0, evidence_value: 'not assessed' },
  { code: 'PP2', direction: 'pathogenic', triggered: false, applied_strength: null, points: 0, evidence_value: 'not assessed' },
  { code: 'PP3', direction: 'pathogenic', triggered: false, applied_strength: null, points: 0, evidence_value: 'mutually exclusive with BP4' },
  { code: 'BA1', direction: 'benign', triggered: false, applied_strength: null, points: 0, evidence_value: 'AF below 5% stand-alone threshold', threshold: '≥ 5%', source_db: 'gnomAD v4' },
  { code: 'BS1', direction: 'benign', triggered: false, applied_strength: null, points: 0, evidence_value: 'not assessed' },
  { code: 'BS2', direction: 'benign', triggered: false, applied_strength: null, points: 0, evidence_value: 'not assessed' },
  { code: 'BP4', direction: 'benign', triggered: false, applied_strength: null, points: 0, evidence_value: 'mutually exclusive with PP3' },
  // PP5/BP6 — demoted (SVI): permanent not-assessed audit rows, cannot trigger.
  { code: 'PP5', direction: 'pathogenic', triggered: false, applied_strength: null, points: 0, evidence_value: 'demoted (not used)' },
  { code: 'BP6', direction: 'benign', triggered: false, applied_strength: null, points: 0, evidence_value: 'demoted (not used)' },
]

// Map a free-form curated classification string to a points tier so the mock
// agrees with the precedence call. Order matters (test "likely …" first).
export function classificationToTier(label: string | null | undefined): EamosComputedTier {
  const l = (label ?? '').toLowerCase()
  if (l.includes('likely pathogenic')) return 'Likely Pathogenic'
  if (l.includes('pathogenic')) return 'Pathogenic'
  if (l.includes('likely benign')) return 'Likely Benign'
  if (l.includes('benign')) return 'Benign'
  return 'VUS'
}

export function mockEamosComputed(tier: EamosComputedTier): EamosComputedClassification {
  const triggered: EamosComputedCriterion[] = TRIGGERED_BY_TIER[tier].map((t) => ({
    triggered: true,
    threshold: null,
    evidence_value: null,
    source_db: null,
    source_version: null,
    svi_reference: null,
    ...t,
  }))
  const triggeredCodes = new Set(triggered.map((c) => c.code))
  const audit = AUDIT_ROWS.filter((c) => !triggeredCodes.has(c.code))
  const per_criterion = [...triggered, ...audit]

  const sum_pathogenic = triggered.filter((c) => c.direction === 'pathogenic').reduce((s, c) => s + c.points, 0)
  const sum_benign = -triggered.filter((c) => c.direction === 'benign').reduce((s, c) => s + c.points, 0)
  const net_points = sum_pathogenic - sum_benign

  return {
    acmg_version_pin: {
      framework: 'Richards-2015 + Tavtigian-2020 points',
      pvs1_revision: 'Abou-Tayoun-2018',
      pp3_calibration: 'Pejaver-2022 / Bergquist-2025',
      vcep_id: null,
    },
    net_points,
    sum_pathogenic,
    sum_benign,
    tier,
    conflict: { is_conflicting: false },
    ba1_override: false,
    posterior: posterior(net_points),
    benign_cut: 'tavtigian_2020',
    per_criterion,
  }
}
