// Derives the four Evidence-Fingerprint axes (rarity · predictors · conservation
// · constraint) from whatever the report already has, mocking only what is not
// yet threaded to the summary. Each axis is 0 (benign) → 1 (pathogenic); axes
// without a real source are flagged `mock` so the fingerprint never passes a
// placeholder off as live data. Kept out of the component so the component stays
// a pure renderer.

import type { EamosComputedClassification, EamosComputedTier } from '@/lib/backend'
import type { FingerprintAxis } from '@/components/report/EvidenceFingerprint'

const clamp01 = (n: number) => Math.max(0, Math.min(1, n))

// Where an axis is only illustrative (conservation / constraint, not yet wired),
// lean it to match the advisory tier so the mock fingerprint agrees in direction
// with the verdict rather than always pointing pathogenic.
const TIER_LEAN: Record<EamosComputedTier, number> = {
  Pathogenic: 0.82,
  'Likely Pathogenic': 0.72,
  VUS: 0.5,
  'Likely Benign': 0.3,
  Benign: 0.18,
}

const STRENGTH_OFFSET: Record<string, number> = {
  supporting: 0.12,
  moderate: 0.26,
  strong: 0.38,
  very_strong: 0.46,
}

// gnomAD allele frequency → benign↔pathogenic on a log scale: ≥5% (BA1) sits at
// the benign end, ultra-rare/absent (PM2) near the pathogenic end.
function rarityAxis(af: number | null | undefined): FingerprintAxis {
  if (af == null) return { key: 'rarity', label: 'Rarity', value: null, detail: 'gnomAD allele frequency (no data)' }
  const hi = Math.log10(0.05) // benign end
  const lo = Math.log10(1e-6) // pathogenic end
  const safe = Math.max(af, 1e-7)
  const v = clamp01((hi - Math.log10(safe)) / (hi - lo))
  return { key: 'rarity', label: 'Rarity', value: v, detail: `gnomAD popmax AF ${af.toExponential(1)}` }
}

// In-silico predictors via the engine's PP3 (pathogenic) / BP4 (benign) row.
function predictorAxis(computed: EamosComputedClassification | null, mock: boolean): FingerprintAxis {
  const pp3 = computed?.per_criterion.find((c) => c.code === 'PP3' && c.triggered)
  const bp4 = computed?.per_criterion.find((c) => c.code === 'BP4' && c.triggered)
  const active = pp3 ?? bp4
  if (!active) return { key: 'predictors', label: 'Predictors', value: null, detail: 'no calibrated predictor call', mock }
  const off = active.applied_strength ? STRENGTH_OFFSET[active.applied_strength] ?? 0.12 : 0.12
  const v = active.direction === 'pathogenic' ? 0.5 + off : 0.5 - off
  return {
    key: 'predictors',
    label: 'Predictors',
    value: clamp01(v),
    detail: typeof active.evidence_value === 'string' ? active.evidence_value : `${active.code} ${active.applied_strength ?? ''}`,
    mock,
  }
}

export function deriveFingerprintAxes(
  populationAf: number | null | undefined,
  computed: EamosComputedClassification | null,
  computedIsMock: boolean,
): FingerprintAxis[] {
  // Conservation + constraint are not yet threaded to the summary; show an
  // illustrative value flagged `mock` (replaced by GERP/phyloP + gnomAD LOEUF when
  // wired). Lean them to the advisory tier so the mock agrees with the verdict.
  // Spec §10 Q5.
  const lean = computed ? TIER_LEAN[computed.tier] : 0.5
  return [
    rarityAxis(populationAf),
    predictorAxis(computed, computedIsMock),
    { key: 'conservation', label: 'Conservation', value: clamp01(lean + 0.04), detail: 'illustrative — GERP / phyloP not yet wired', mock: true },
    { key: 'constraint', label: 'Constraint', value: clamp01(lean - 0.06), detail: 'illustrative — gnomAD LOEUF not yet wired', mock: true },
  ]
}
