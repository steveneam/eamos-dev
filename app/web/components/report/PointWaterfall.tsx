// A2 — Point Waterfall (matches the vault point-waterfall.svg). Two clear parts:
//   1. one diverging bar per TRIGGERED criterion — bar SIZE = its applied points
//      (variable strength), pathogenic to the right of zero, benign to the left,
//      labelled with code · strength and the signed points; and
//   2. a separate "cumulative net → tier" axis where the summed net lands among
//      the Tavtigian tier bands.
// Applied strength + signed points come straight from the engine (never a fixed
// code→points map). Renders the same data as a real <table> for screen readers.

import type { EamosComputedClassification, EamosComputedCriterion } from '@/lib/backend'
import { gaugeBands, netBoundaries, POINTS_FORMULA_STAMP, tierTokens } from '@/lib/acmg/points'
import { ScaleTrack } from './ScoreScale'

const STRENGTH_LABEL: Record<string, string> = {
  very_strong: 'Very Strong',
  strong: 'Strong',
  moderate: 'Moderate',
  supporting: 'Supporting',
}
const TIER_SHORT: Record<string, string> = {
  Pathogenic: 'P',
  'Likely Pathogenic': 'LP',
  VUS: 'VUS',
  'Likely Benign': 'LB',
  Benign: 'B',
}

// Strength-graded muted fill off the --cls-* ramp: stronger evidence → denser fill.
const STRENGTH_MIX: Record<string, number> = { very_strong: 72, strong: 58, moderate: 44, supporting: 30 }
function barFill(c: EamosComputedCriterion): string {
  const ink = c.direction === 'pathogenic' ? 'var(--cls-path-text)' : 'var(--cls-ben-text)'
  const m = c.applied_strength ? STRENGTH_MIX[c.applied_strength] ?? 30 : 30
  return `color-mix(in oklab, ${ink} ${m}%, var(--bg))`
}
function codeLabel(c: EamosComputedCriterion): string {
  const s = c.applied_strength ? STRENGTH_LABEL[c.applied_strength] : null
  return s ? `${c.code} · ${s}` : c.code
}
function signed(n: number): string {
  return `${n >= 0 ? '+' : ''}${n}`
}

function tierContext(net: number, tier: string): string {
  if (net >= 10) return `Pathogenic — ${net - 10} above the +10 line`
  if (net >= 6) return `${10 - net} below the Pathogenic line (+10)`
  if (net >= 0) return `${6 - net} below the Likely-Pathogenic line (+6)`
  return `${tier} — benign-leaning evidence`
}

export function PointWaterfall({
  computed,
  mock = false,
}: {
  computed: EamosComputedClassification
  mock?: boolean
}) {
  const steps = computed.per_criterion
    .filter((c) => c.triggered && c.points !== 0)
    .sort((a, b) => b.points - a.points) // pathogenic (largest) first, then benign
  const net = computed.net_points
  const maxAbs = Math.max(1, ...steps.map((s) => Math.abs(s.points)))

  // Net→tier axis domain.
  const b = netBoundaries(computed.benign_cut)
  const domMin = Math.min(-8, Math.floor(net) - 1)
  const domMax = Math.max(12, Math.ceil(net) + 1)
  const span = domMax - domMin
  const xNet = (n: number) => ((n - domMin) / span) * 100
  const axisBands = gaugeBands(computed.benign_cut, domMin, domMax).map((bd) => ({
    frac: (bd.to - bd.from) / span,
    color: tierTokens(bd.tier).band,
    title: `${bd.tier}`,
  }))
  const axisTierBands = gaugeBands(computed.benign_cut, domMin, domMax)
  const netTicks = [b.likelyBenign - 1, 0, b.likelyPathogenic, b.pathogenic].filter((t) => t > domMin && t < domMax)

  return (
    <figure
      role="img"
      aria-label={`Point waterfall: ${steps.length} triggered ACMG criteria sum to a net of ${signed(net)} points → ${computed.tier}.`}
      style={{ margin: 0 }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 2 }}>
        <span className="eamos-kicker">Point waterfall</span>
        {mock && (
          <span className="eamos-mock" title="Illustrative — applied points are not yet wired to live engine output for this variant.">
            illustrative
          </span>
        )}
      </div>
      <p style={{ margin: '0 0 10px', fontSize: 10.5, color: 'var(--ink-4)', lineHeight: 1.4 }}>
        Each bar = the points that criterion applied (strength varies per variant). Pathogenic right, benign left.
      </p>

      {steps.length === 0 ? (
        <p style={{ fontSize: 12, color: 'var(--ink-4)', margin: '4px 0' }}>No criteria triggered.</p>
      ) : (
        <>
          {/* benign ← 0 → pathogenic header over the plot column */}
          <div aria-hidden style={{ display: 'grid', gridTemplateColumns: 'minmax(110px, 1fr) minmax(120px, 1.3fr) 30px', gap: 8, fontSize: 9, color: 'var(--ink-4)', marginBottom: 3 }}>
            <span />
            <span style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: 0 }}>benign ←</span>
              <span style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)' }}>0</span>
              <span style={{ position: 'absolute', right: 0 }}>→ pathogenic</span>
            </span>
            <span />
          </div>

          {/* diverging bars */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }} aria-hidden>
            {steps.map((c) => {
              const w = (Math.abs(c.points) / maxAbs) * 50 // % of half-width
              const path = c.direction === 'pathogenic'
              return (
                <div key={c.code} style={{ display: 'grid', gridTemplateColumns: 'minmax(110px, 1fr) minmax(120px, 1.3fr) 30px', gap: 8, alignItems: 'center' }}>
                  <span style={{ fontSize: 10.5, color: 'var(--ink-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={typeof c.evidence_value === 'string' ? c.evidence_value : undefined}>
                    {codeLabel(c)}
                  </span>
                  <span style={{ position: 'relative', height: 15, background: 'var(--bg-soft)', borderRadius: 3 }}>
                    {/* center zero line */}
                    <span style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, background: 'var(--ink-5)' }} />
                    <span
                      style={{
                        position: 'absolute',
                        top: 2,
                        bottom: 2,
                        left: path ? '50%' : `${50 - w}%`,
                        width: `${w}%`,
                        minWidth: 2,
                        background: barFill(c),
                        borderRadius: 2,
                      }}
                    />
                  </span>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, textAlign: 'right', color: path ? tierTokens('Pathogenic').ink : tierTokens('Benign').ink }}>
                    {signed(c.points)}
                  </span>
                </div>
              )
            })}
          </div>

          {/* cumulative net → tier axis */}
          <div style={{ marginTop: 14 }}>
            <div className="eamos-kicker" style={{ marginBottom: 6 }}>Cumulative net → tier</div>
            <div style={{ position: 'relative', height: 13, marginBottom: 2 }} aria-hidden>
              {axisTierBands.map((bd) => (
                <span
                  key={bd.tier}
                  style={{ position: 'absolute', left: `${xNet((bd.from + bd.to) / 2)}%`, transform: 'translateX(-50%)', fontSize: 9, fontWeight: 600, color: tierTokens(bd.tier).ink }}
                >
                  {TIER_SHORT[bd.tier]}
                </span>
              ))}
            </div>
            <ScaleTrack bands={axisBands} height={14} radius={4} separators pin={{ pos: xNet(net) / 100, muted: mock }} />
            <div style={{ position: 'relative', height: 14, marginTop: 2 }} aria-hidden>
              {netTicks.map((t) => (
                <span key={t} style={{ position: 'absolute', left: `${xNet(t)}%`, transform: 'translateX(-50%)', fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--ink-4)' }}>
                  {signed(t)}
                </span>
              ))}
            </div>
            <p style={{ margin: '6px 0 0', fontSize: 11, color: tierTokens(computed.tier).ink }}>
              net <strong>{signed(net)}</strong> → {computed.tier}
              <span style={{ color: 'var(--ink-4)', fontWeight: 400 }}> · {tierContext(net, computed.tier)}</span>
            </p>
          </div>
        </>
      )}

      <table className="sr-only">
        <caption>EAMOS point waterfall — applied ACMG/AMP points per triggered criterion</caption>
        <thead>
          <tr>
            <th scope="col">Criterion</th>
            <th scope="col">Direction</th>
            <th scope="col">Applied strength</th>
            <th scope="col">Points</th>
          </tr>
        </thead>
        <tbody>
          {steps.map((c) => (
            <tr key={c.code}>
              <td>{c.code}</td>
              <td>{c.direction}</td>
              <td>{c.applied_strength ? STRENGTH_LABEL[c.applied_strength] : '—'}</td>
              <td>{signed(c.points)}</td>
            </tr>
          ))}
          <tr>
            <th scope="row">Net</th>
            <td colSpan={2}>{computed.tier}</td>
            <td>{signed(net)}</td>
          </tr>
        </tbody>
      </table>

      <p style={{ margin: '8px 0 0', fontSize: 9.5, color: 'var(--ink-5)' }}>{POINTS_FORMULA_STAMP}</p>
    </figure>
  )
}
