// Derives the four Evidence-Fingerprint axes (rarity, predictors, conservation,
// constraint) from source-backed report data. Each axis is 0 (benign) to
// 1 (pathogenic); absent source values stay null.

import type { ComputationalPredictorRow, EamosComputedClassification } from '@/lib/backend'
import type { FingerprintAxis } from '@/components/report/EvidenceFingerprint'

const clamp01 = (n: number) => Math.max(0, Math.min(1, n))

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
function predictorAxis(computed: EamosComputedClassification | null): FingerprintAxis {
  const pp3 = computed?.per_criterion.find((c) => c.code === 'PP3' && c.triggered)
  const bp4 = computed?.per_criterion.find((c) => c.code === 'BP4' && c.triggered)
  const active = pp3 ?? bp4
  if (!active) return { key: 'predictors', label: 'Predictors', value: null, detail: 'no calibrated predictor call' }
  const off = active.applied_strength ? STRENGTH_OFFSET[active.applied_strength] ?? 0.12 : 0.12
  const v = active.direction === 'pathogenic' ? 0.5 + off : 0.5 - off
  return {
    key: 'predictors',
    label: 'Predictors',
    value: clamp01(v),
    detail: typeof active.evidence_value === 'string' ? active.evidence_value : `${active.code} ${active.applied_strength ?? ''}`,
  }
}

function toNumber(value: ComputationalPredictorRow['score']): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function conservationAxis(rows: ComputationalPredictorRow[]): FingerprintAxis {
  const row = rows.find((item) => toNumber(item.score) !== null)
  if (!row) {
    return {
      key: 'conservation',
      label: 'Conservation',
      value: null,
      detail: 'no source-backed conservation score',
    }
  }
  const score = toNumber(row.score) as number
  const normalized =
    row.name.toLowerCase().includes('phylop')
      ? clamp01((score + 3) / 9)
      : row.name.toLowerCase().includes('gerp')
        ? clamp01((score + 2) / 8)
        : clamp01(score)
  return {
    key: 'conservation',
    label: 'Conservation',
    value: normalized,
    detail: `${row.name} ${score.toPrecision(3)}`,
  }
}

function constraintAxis(loeuf: number | null | undefined): FingerprintAxis {
  if (loeuf == null || !Number.isFinite(loeuf)) {
    return {
      key: 'constraint',
      label: 'Constraint',
      value: null,
      detail: 'gnomAD LOEUF unavailable',
    }
  }
  return {
    key: 'constraint',
    label: 'Constraint',
    value: clamp01(1 - loeuf / 1.5),
    detail: `gnomAD LOEUF ${loeuf.toPrecision(3)}`,
  }
}

export function deriveFingerprintAxes(
  populationAf: number | null | undefined,
  computed: EamosComputedClassification | null,
  sources: {
    conservation?: ComputationalPredictorRow[]
    loeuf?: number | null
  } = {},
): FingerprintAxis[] {
  return [
    rarityAxis(populationAf),
    predictorAxis(computed),
    conservationAxis(sources.conservation ?? []),
    constraintAxis(sources.loeuf ?? null),
  ]
}
