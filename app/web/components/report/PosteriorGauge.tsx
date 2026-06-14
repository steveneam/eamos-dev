// A3 — Posterior Gauge (matches the vault posterior-gauge.svg). The axis is
// LINEAR IN NET POINTS — points are linear in log-odds — with the five tier
// bands by net width and the posterior probability labelled under each tier
// divider (the "compress near 1.0" honesty lives in the labels: +6→0.90,
// +10→0.99, not in invisible slivers). The marker sits at the net score; the big
// readout is the posterior. Reuses the shared ScaleTrack primitive.
//
// The engine is authoritative: we render `computed.net_points` (marker) and
// `computed.posterior` / `computed.tier` (readout) verbatim; points.ts only
// supplies band geometry. BA1 override / conflict cap (where the net-implied
// tier and the verdict disagree) surface as an honest note.

import type { EamosComputedClassification } from '@/lib/backend'
import {
  gaugeBands,
  gaugeBoundaries,
  POINTS_FORMULA_STAMP,
  tierByNet,
  tierTokens,
} from '@/lib/acmg/points'
import { ScaleTrack } from './ScoreScale'

const TIER_SHORT: Record<string, string> = {
  Pathogenic: 'P',
  'Likely Pathogenic': 'LP',
  VUS: 'VUS',
  'Likely Benign': 'LB',
  Benign: 'B',
}

const pct = (p: number) => `${(p * 100).toFixed(1)}%`
const fmtPost = (p: number) => (p < 0.01 ? p.toFixed(3) : p.toFixed(2))

function overrideNote(computed: EamosComputedClassification): string | null {
  if (computed.ba1_override) return 'BA1 stand-alone benign override — classified Benign regardless of the point total.'
  if (computed.conflict.is_conflicting)
    return `Conflicting evidence — advisory capped to VUS${computed.conflict.reason ? ` (${computed.conflict.reason})` : ''}.`
  if (tierByNet(computed.net_points, computed.benign_cut) !== computed.tier) {
    return 'Engine tier differs from the net-implied tier (overlay or override applied).'
  }
  return null
}

export function PosteriorGauge({
  computed,
  mock = false,
  variant = 'gauge',
}: {
  computed: EamosComputedClassification
  mock?: boolean
  variant?: 'gauge' | 'chip'
}) {
  const net = computed.net_points
  const domMin = Math.min(-10, Math.floor(net) - 2)
  const domMax = Math.max(13, Math.ceil(net) + 2)
  const span = domMax - domMin
  const xNet = (n: number) => ((n - domMin) / span) * 100

  const bands = gaugeBands(computed.benign_cut, domMin, domMax)
  const scaleBands = bands.map((b) => ({
    frac: (b.to - b.from) / span,
    color: tierTokens(b.tier).band,
    title: `${b.tier}: net ${Math.ceil(b.from)}…${Math.floor(b.to)}`,
  }))
  const boundaries = gaugeBoundaries(computed.benign_cut)

  const tokens = tierTokens(computed.tier)
  const p = computed.posterior
  const note = overrideNote(computed)
  const netLabel = `${net >= 0 ? '+' : ''}${net}`
  const ariaLabel = `Posterior probability of pathogenicity ${pct(p)}. EAMOS-computed advisory tier ${computed.tier}, net ${netLabel} points on the Tavtigian-2020 scale.`

  const dataTable = (
    <table className="sr-only">
      <caption>EAMOS-computed posterior probability of pathogenicity</caption>
      <tbody>
        <tr>
          <th scope="row">Posterior</th>
          <td>{pct(p)}</td>
        </tr>
        <tr>
          <th scope="row">Advisory tier</th>
          <td>{computed.tier}</td>
        </tr>
        <tr>
          <th scope="row">Net points</th>
          <td>{netLabel}</td>
        </tr>
        {boundaries.map((b) => (
          <tr key={b.net}>
            <th scope="row">Net {b.net} boundary</th>
            <td>posterior {fmtPost(b.posterior)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )

  if (variant === 'chip') {
    return (
      <span
        role="img"
        aria-label={ariaLabel}
        title={ariaLabel}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          padding: '5px 10px',
          borderRadius: 999,
          border: `0.5px solid ${tokens.edge}`,
          background: tokens.band,
        }}
      >
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.02em', color: tokens.ink }}>{pct(p)}</span>
        <span style={{ width: 72 }}>
          <ScaleTrack bands={scaleBands} height={6} radius={3} pin={{ pos: xNet(net) / 100, muted: mock }} />
        </span>
        <span style={{ fontSize: 10, color: 'var(--ink-4)' }}>posterior</span>
        {dataTable}
      </span>
    )
  }

  return (
    <figure role="img" aria-label={ariaLabel} style={{ margin: 0 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontFamily: 'var(--display)', fontSize: 24, fontWeight: 400, color: tokens.ink, letterSpacing: '-0.01em' }}>
            {pct(p)}
          </span>
          <span style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>
            posterior · <span style={{ color: tokens.ink, fontWeight: 600 }}>{computed.tier}</span> · net {netLabel}
          </span>
        </div>
        {mock && (
          <span className="eamos-mock" title="Illustrative — the EAMOS points engine is not yet wired to live data for this variant.">
            illustrative
          </span>
        )}
      </div>

      {/* Tier labels above their bands. */}
      <div style={{ position: 'relative', height: 14 }} aria-hidden>
        {bands.map((b) => (
          <span
            key={b.tier}
            style={{
              position: 'absolute',
              left: `${xNet((b.from + b.to) / 2)}%`,
              transform: 'translateX(-50%)',
              fontSize: 9.5,
              fontWeight: 600,
              color: tierTokens(b.tier).ink,
              whiteSpace: 'nowrap',
            }}
          >
            {TIER_SHORT[b.tier]}
          </span>
        ))}
      </div>

      <ScaleTrack bands={scaleBands} height={16} radius={5} separators pin={{ pos: xNet(net) / 100, muted: mock }} />

      {/* Posterior value labelled under each tier divider. */}
      <div style={{ position: 'relative', height: 16, marginTop: 3 }} aria-hidden>
        {boundaries.map((b) => (
          <span
            key={b.net}
            style={{
              position: 'absolute',
              left: `${xNet(b.net)}%`,
              transform: 'translateX(-50%)',
              fontFamily: 'var(--mono)',
              fontSize: 9,
              color: 'var(--ink-4)',
            }}
          >
            {fmtPost(b.posterior)}
          </span>
        ))}
      </div>

      <div aria-hidden style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: 'var(--ink-5)', marginTop: 1 }}>
        <span>← benign</span>
        <span>net {netLabel} → posterior {pct(p)}</span>
        <span>pathogenic →</span>
      </div>

      {note && (
        <p role="note" style={{ margin: '8px 0 0', fontSize: 10.5, lineHeight: 1.45, color: 'var(--warn-text)' }}>
          {note}
        </p>
      )}

      <p style={{ margin: '8px 0 0', fontSize: 9.5, color: 'var(--ink-5)' }}>{POINTS_FORMULA_STAMP}</p>
      {dataTable}
    </figure>
  )
}
