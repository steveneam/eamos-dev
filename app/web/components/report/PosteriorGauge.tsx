// A3 — Point-model posterior gauge (matches the vault posterior-gauge.svg). The axis is
// LINEAR IN NET POINTS — points are linear in log-odds — with the five tier
// bands by net width and the posterior probability labelled under each tier
// divider (the "compress near 1.0" honesty lives in the labels: +6→0.90,
// +10→0.99, not in invisible slivers). The marker sits at the net score; the big
// readout is the model posterior. Reuses the shared ScaleTrack primitive.
//
// The engine is authoritative: we render `computed.net_points` (marker) and
// `computed.model_posterior` / `computed.tier` (readout) verbatim; points.ts only
// supplies band geometry. BA1 has no point-model posterior and gets a distinct
// not-applicable treatment.

import type { EamosComputedClassification } from '@/lib/backend'
import {
  gaugeBands,
  gaugeBoundaries,
  modelPosteriorFromComputed,
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
  if (computed.ba1_override) return 'BA1 is a stand-alone benign override. The net point total is retained only for audit.'
  if (computed.conflict.is_conflicting)
    return `Conflicting evidence. Advisory capped to VUS${computed.conflict.reason ? ` (${computed.conflict.reason})` : ''}.`
  if (tierByNet(computed.net_points, computed.benign_cut) !== computed.tier) {
    return 'Engine tier differs from the net-implied tier (overlay or override applied).'
  }
  return null
}

export function PosteriorGauge({
  computed,
  variant = 'gauge',
}: {
  computed: EamosComputedClassification
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
  const p = modelPosteriorFromComputed(computed)
  const note = overrideNote(computed)
  const netLabel = `${net >= 0 ? '+' : ''}${net}`
  if (p === null) {
    const status = computed.ba1_override ? 'not applicable because BA1 applies' : 'unavailable'
    const ariaLabel = `Model posterior ${status}. EAMOS-computed advisory tier ${computed.tier}, net ${netLabel} points retained for audit.`
    const dataTable = (
      <table className="sr-only">
        <caption>EAMOS-computed classification basis</caption>
        <tbody>
          <tr>
            <th scope="row">Model posterior</th>
            <td>Not applicable</td>
          </tr>
          <tr>
            <th scope="row">Classification basis</th>
            <td>{computed.classification_basis}</td>
          </tr>
          <tr>
            <th scope="row">Advisory tier</th>
            <td>{computed.tier}</td>
          </tr>
          <tr>
            <th scope="row">Audit net points</th>
            <td>{netLabel}</td>
          </tr>
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
          <span style={{ fontSize: 11, fontWeight: 700, color: tokens.ink }}>
            {computed.ba1_override ? 'BA1' : 'N/A'}
          </span>
          <span style={{ fontSize: 10, color: 'var(--ink-4)' }}>model posterior N/A</span>
          {dataTable}
        </span>
      )
    }

    return (
      <figure role="img" aria-label={ariaLabel} style={{ margin: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontFamily: 'var(--display)', fontSize: 24, fontWeight: 400, color: tokens.ink }}>
            N/A
          </span>
          <span style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>
            model posterior not applicable · <strong style={{ color: tokens.ink }}>{computed.tier}</strong> · audit net {netLabel}
          </span>
        </div>
        <p role="note" style={{ margin: '8px 0 0', fontSize: 10.5, lineHeight: 1.45, color: 'var(--warn-text)' }}>
          {note ?? 'No point-model posterior was supplied.'}
        </p>
        {dataTable}
      </figure>
    )
  }

  const ariaLabel = `Model posterior probability of pathogenicity ${pct(p)}. EAMOS-computed advisory tier ${computed.tier}, net ${netLabel} points on the Tavtigian-2020 scale.`

  const dataTable = (
    <table className="sr-only">
      <caption>EAMOS-computed point-model posterior probability of pathogenicity</caption>
      <tbody>
        <tr>
          <th scope="row">Model posterior</th>
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
            <td>model posterior {fmtPost(b.modelPosterior)}</td>
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
          <ScaleTrack bands={scaleBands} height={6} radius={3} pin={{ pos: xNet(net) / 100 }} />
        </span>
        <span style={{ fontSize: 10, color: 'var(--ink-4)' }}>model posterior</span>
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
            model posterior · <span style={{ color: tokens.ink, fontWeight: 600 }}>{computed.tier}</span> · net {netLabel}
          </span>
        </div>
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

      <ScaleTrack bands={scaleBands} height={16} radius={5} separators pin={{ pos: xNet(net) / 100 }} />

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
            {fmtPost(b.modelPosterior)}
          </span>
        ))}
      </div>

      <div aria-hidden style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: 'var(--ink-5)', marginTop: 1 }}>
        <span>← benign</span>
        <span>net {netLabel} → model posterior {pct(p)}</span>
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
