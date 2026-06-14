// A4 — Confidence Channel. A calm, one-line evidence-quality readout beside the
// verdict: how many criteria fired, the strongest applied strength, and which
// calibrations the engine pinned. It answers "how well-supported is this
// advisory?" without re-stating the verdict. Reads only the computed contract.

import type { EamosComputedClassification } from '@/lib/backend'

const STRENGTH_RANK: Record<string, number> = { very_strong: 4, strong: 3, moderate: 2, supporting: 1 }
const STRENGTH_LABEL: Record<string, string> = {
  very_strong: 'Very Strong',
  strong: 'Strong',
  moderate: 'Moderate',
  supporting: 'Supporting',
}

export function ConfidenceChannel({ computed }: { computed: EamosComputedClassification }) {
  const triggered = computed.per_criterion.filter((c) => c.triggered)
  const maxStrength = triggered.reduce<string | null>((best, c) => {
    if (!c.applied_strength) return best
    if (!best || STRENGTH_RANK[c.applied_strength] > STRENGTH_RANK[best]) return c.applied_strength
    return best
  }, null)
  const pin = computed.acmg_version_pin
  const items: string[] = [
    `${triggered.length} criteri${triggered.length === 1 ? 'on' : 'a'} applied`,
    maxStrength ? `max strength ${STRENGTH_LABEL[maxStrength]}` : 'no strength assigned',
    `PVS1 ${pin.pvs1_revision}`,
    `PP3 ${pin.pp3_calibration}`,
  ]
  if (pin.vcep_id) items.push(`VCEP ${pin.vcep_id}`)

  return (
    <p
      style={{
        margin: 0,
        display: 'flex',
        flexWrap: 'wrap',
        gap: 8,
        fontSize: 10.5,
        color: 'var(--ink-4)',
        lineHeight: 1.5,
      }}
    >
      {items.map((it, i) => (
        <span key={it} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          {i > 0 && <span aria-hidden style={{ color: 'var(--ink-5)' }}>·</span>}
          {it}
        </span>
      ))}
    </p>
  )
}
