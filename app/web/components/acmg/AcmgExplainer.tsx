'use client'

// The full interactive ACMG points explainer — the "change the criteria and
// strengths yourself, watch the points and the verdict move" teaching surface
// that lives on the variant-submission page (/account). Productionizes the vault
// `Wiki/assets/acmg-explainer.html`: a criteria panel on the left (toggle codes,
// pick per-application strengths) and, on the right, the live verdict + the same
// Evidence Plane / Point Waterfall / Posterior Gauge the report draws — plus the
// draggable net-points puck for free-form what-if.
//
// It is a TEACHING TOOL, not the classifier. The combine logic is the pure
// lib/acmg/criteria-model.ts (vitest-pinned); the visuals are the report's own
// instruments fed a synthesized classification, so what a submitter learns here
// is exactly what the report shows.

import Link from 'next/link'
import { useMemo, useState } from 'react'
import type { EamosComputedClassification } from '@/lib/backend'
import { posterior, tierByNet, tierTokens } from '@/lib/acmg/points'
import {
  blockedCodes,
  computeCriteria,
  CRITERIA,
  CRITERIA_CATEGORIES,
  initialCriteriaState,
  STRENGTH_LABEL,
  STRENGTH_POINTS,
  type CriteriaResult,
  type CriteriaState,
  type CriteriaStrength,
} from '@/lib/acmg/criteria-model'
import { EvidencePlane } from '@/components/report/EvidencePlane'
import { PointWaterfall } from '@/components/report/PointWaterfall'
import { PosteriorGauge } from '@/components/report/PosteriorGauge'
import { NetPointsPuck } from './NetPointsPuck'

const signed = (n: number) => `${n >= 0 ? '+' : ''}${n}`
const pct = (p: number) => `${(p * 100).toFixed(1)}%`

const TIER_FULL: Record<string, string> = {
  Pathogenic: 'Pathogenic',
  'Likely Pathogenic': 'Likely Pathogenic',
  VUS: 'Uncertain significance (VUS)',
  'Likely Benign': 'Likely Benign',
  Benign: 'Benign',
}

// Build the contract the report instruments consume from a teaching-model result.
function toComputed(
  r: CriteriaResult,
  benignCut: EamosComputedClassification['benign_cut'],
): EamosComputedClassification {
  return {
    acmg_version_pin: {
      framework: 'Richards-2015 + Tavtigian-2020 points',
      pvs1_revision: 'Abou-Tayoun-2018',
      pp3_calibration: 'Pejaver-2022',
      vcep_id: null,
    },
    net_points: r.net,
    sum_pathogenic: r.sumPathogenic,
    sum_benign: r.sumBenign,
    tier: r.tier,
    conflict: { is_conflicting: r.conflict, reason: r.reason || null },
    ba1_override: r.ba1,
    posterior: r.posterior,
    benign_cut: benignCut,
    per_criterion: r.applied.map((a) => ({
      code: a.code,
      direction: a.direction,
      triggered: true,
      applied_strength: a.strength === 'stand_alone' ? null : a.strength,
      points: a.points,
    })),
  }
}

// A hypothetical (drag) result — no per-criterion breakdown, just ΣP/ΣB → net → tier.
function exploreResult(sumP: number, sumB: number, benignCut: 'tavtigian_2020' | 'acgs_panel'): CriteriaResult {
  const net = sumP - sumB
  return {
    sumPathogenic: sumP,
    sumBenign: sumB,
    net,
    tier: tierByNet(net, benignCut),
    conflict: false,
    reason: '',
    ba1: false,
    posterior: posterior(net),
    applied: [],
  }
}

// Has the criteria selection moved off the seed the explainer opened with? Used
// only in the anchored report context — any deviation (toggle, strength, or cut)
// makes the live verdict a what-if, never mistakable for the engine's call.
function criteriaDiffer(current: CriteriaState, seed: CriteriaState): boolean {
  for (const code in current) {
    const c = current[code]
    const s = seed[code]
    if (!s || c.on !== s.on || (c.on && c.strength !== s.strength)) return true
  }
  return false
}

export function AcmgExplainer({
  initialState,
  anchor = null,
}: {
  /** Pre-tick the criteria from a real variant (the engine's per_criterion). */
  initialState?: CriteriaState
  /** The engine's computed call — anchored as the fixed truth + the reset target
   *  (report context). Omitted on the blank /account authoring tool. */
  anchor?: EamosComputedClassification | null
} = {}) {
  const [criteria, setCriteria] = useState<CriteriaState>(() => initialState ?? initialCriteriaState())
  const [benignCut, setBenignCut] = useState<'tavtigian_2020' | 'acgs_panel'>(anchor?.benign_cut ?? 'tavtigian_2020')
  const [mode, setMode] = useState<'criteria' | 'explore'>('criteria')
  const [exP, setExP] = useState(0)
  const [exB, setExB] = useState(0)

  const criteriaResult = computeCriteria(criteria, benignCut)
  const blocked = blockedCodes(criteria)
  const result = mode === 'explore' ? exploreResult(exP, exB, benignCut) : criteriaResult
  const computed = toComputed(result, benignCut)
  const tokens = tierTokens(result.tier)

  // The seed this explainer opened with (the variant's call in report context).
  const seed = useMemo<CriteriaState>(() => initialState ?? initialCriteriaState(), [initialState])
  const criteriaChanged = useMemo(() => criteriaDiffer(criteria, seed), [criteria, seed])
  const cutChanged = anchor ? benignCut !== (anchor.benign_cut ?? 'tavtigian_2020') : false

  const toggleCriterion = (code: string) => {
    setCriteria((prev) => {
      const next = { ...prev }
      const turningOn = !next[code].on
      next[code] = { ...next[code], on: turningOn }
      if (turningOn) {
        // switch off any mutually-exclusive partners
        for (const ex of CRITERIA.find((c) => c.code === code)?.excl ?? []) {
          if (next[ex]?.on) next[ex] = { ...next[ex], on: false }
        }
      }
      return next
    })
    if (mode === 'explore') setMode('criteria')
  }

  const setStrength = (code: string, strength: CriteriaStrength) => {
    setCriteria((prev) => ({ ...prev, [code]: { ...prev[code], strength } }))
    if (mode === 'explore') setMode('criteria')
  }

  const reset = () => {
    setCriteria(initialState ? { ...initialState } : initialCriteriaState())
    setMode('criteria')
  }

  // Dragging the puck (1-D net) or the plane marker (2-D ΣP/ΣB) drops into explore
  // (what-if) mode. The puck maps net → ΣP/ΣB; the plane sets them independently.
  const onPuckChange = (n: number) => {
    if (mode !== 'explore') setMode('explore')
    setExP(Math.max(0, n))
    setExB(Math.max(0, -n))
  }
  const onPlaneChange = (sumP: number, sumB: number) => {
    if (mode !== 'explore') setMode('explore')
    setExP(sumP)
    setExB(sumB)
  }
  const backToCriteria = () => setMode('criteria')

  const exploring = mode === 'explore'
  // In the anchored report context the verdict is a what-if the moment anything
  // deviates from the seed — a puck/plane drag OR a criterion / strength / cut edit.
  const dirty = exploring || (!!anchor && (criteriaChanged || cutChanged))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Engine anchor (report context): the fixed, authoritative computed call. */}
      {anchor && (
        <div
          style={{
            border: `0.5px solid ${tierTokens(anchor.tier).edge}`,
            background: tierTokens(anchor.tier).band,
            borderRadius: 'var(--r-md)',
            padding: '12px 14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', color: tierTokens(anchor.tier).ink }}>
              EAMOS computed · this variant
            </span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '3px 10px',
                borderRadius: 999,
                background: 'var(--bg)',
                border: `0.5px solid ${tierTokens(anchor.tier).edge}`,
                color: tierTokens(anchor.tier).ink,
                fontSize: 12.5,
                fontWeight: 700,
              }}
            >
              <span aria-hidden style={{ width: 7, height: 7, borderRadius: '50%', background: tierTokens(anchor.tier).ink }} />
              {TIER_FULL[anchor.tier]}
            </span>
            <span style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>
              net {signed(anchor.net_points)} · posterior {pct(anchor.posterior)}
            </span>
          </div>
          <p style={{ margin: '8px 0 0', fontSize: 11, lineHeight: 1.5, color: 'var(--ink-4)' }}>
            Advisory — the engine is authoritative. Toggle criteria or drag the puck below to explore{' '}
            <strong style={{ color: 'var(--ink-3)' }}>what-if</strong> scenarios on this variant; changes are a sandbox —
            they don&apos;t change this verdict and aren&apos;t saved. To submit a different classification, use the{' '}
            <Link href="/account#acmg-explainer" style={{ color: 'var(--teal)', fontWeight: 600 }}>
              submission page →
            </Link>
          </p>
        </div>
      )}

      {/* top controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 7, fontSize: 12, color: 'var(--ink-3)', cursor: 'pointer' }}>
          <input type="checkbox" checked={benignCut === 'acgs_panel'} onChange={(e) => setBenignCut(e.target.checked ? 'acgs_panel' : 'tavtigian_2020')} />
          ACGS / CanVIG benign cut <span style={{ color: 'var(--ink-4)' }}>(LB −1..−5 · B ≤ −6)</span>
        </label>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          {exploring && (
            <button type="button" onClick={backToCriteria} style={linkBtn}>
              ← Back to criteria
            </button>
          )}
          <button type="button" onClick={reset} style={anchor ? resetVariantBtn : ghostBtn}>
            {anchor ? 'Reset to this variant' : 'Reset'}
          </button>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(280px,340px)_1fr]">
        {/* ── criteria panel ─────────────────────────────────────────────── */}
        <div
          style={{
            border: '0.5px solid var(--line)',
            borderRadius: 'var(--r-md)',
            background: 'var(--bg-soft)',
            padding: '12px 14px',
            opacity: exploring ? 0.45 : 1,
            pointerEvents: exploring ? 'none' : 'auto',
            filter: exploring ? 'grayscale(0.3)' : undefined,
            transition: 'opacity var(--dur-1) var(--ease-standard)',
            maxHeight: 560,
            overflowY: 'auto',
          }}
          aria-hidden={exploring}
        >
          {CRITERIA_CATEGORIES.map((cat) => (
            <div key={cat} style={{ marginBottom: 10 }}>
              <div className="eamos-kicker" style={{ marginBottom: 4 }}>{cat}</div>
              {CRITERIA.filter((c) => c.category === cat).map((def) => {
                const st = criteria[def.code]
                const isBlocked = blocked.has(def.code) && !st.on
                const dirPath = def.direction === 'pathogenic'
                return (
                  <div
                    key={def.code}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '4px 0',
                      borderBottom: '0.5px solid var(--line)',
                      opacity: isBlocked ? 0.4 : 1,
                    }}
                  >
                    <input
                      type="checkbox"
                      id={`crit-${def.code}`}
                      checked={st.on}
                      disabled={isBlocked}
                      onChange={() => toggleCriterion(def.code)}
                    />
                    <label htmlFor={`crit-${def.code}`} style={{ flex: 1, cursor: isBlocked ? 'not-allowed' : 'pointer', minWidth: 0 }}>
                      <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 11.5, color: dirPath ? 'var(--cls-path-text)' : 'var(--cls-ben-text)' }}>
                        {def.code}
                      </span>{' '}
                      <span style={{ fontSize: 11, color: 'var(--ink-4)' }}>{def.desc}</span>
                    </label>
                    {def.strengths.length > 0 ? (
                      <select
                        aria-label={`${def.code} strength`}
                        value={st.strength}
                        disabled={!st.on}
                        onChange={(e) => setStrength(def.code, e.target.value as CriteriaStrength)}
                        style={{
                          fontFamily: 'var(--mono)',
                          fontSize: 10.5,
                          border: '0.5px solid var(--line-2)',
                          borderRadius: 4,
                          background: 'var(--bg)',
                          color: 'var(--ink-2)',
                          padding: '1px 2px',
                          opacity: st.on ? 1 : 0.4,
                        }}
                      >
                        {def.strengths.map((s) => (
                          <option key={s} value={s}>
                            {STRENGTH_LABEL[s]} ({dirPath ? '+' : '−'}{STRENGTH_POINTS[s]})
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--ink-4)', width: 30, textAlign: 'right' }}>
                        {st.on ? `${dirPath ? '+' : '−'}${STRENGTH_POINTS[st.strength]}` : ''}
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </div>

        {/* ── live verdict + instruments ─────────────────────────────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* verdict header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 7,
                padding: '6px 13px',
                borderRadius: 999,
                border: dirty ? `1px dashed ${tokens.edge}` : `0.5px solid ${tokens.edge}`,
                background: dirty ? 'transparent' : tokens.band,
                color: tokens.ink,
                fontSize: 13.5,
                fontWeight: 700,
              }}
            >
              <span aria-hidden style={{ width: 8, height: 8, borderRadius: '50%', background: tokens.ink }} />
              {TIER_FULL[result.tier]}
              {result.conflict && <span style={{ fontWeight: 400, fontSize: 11 }}>· conflicting</span>}
            </span>
            <span style={{ fontSize: 12.5, color: 'var(--ink-3)' }}>
              {dirty && <span style={{ color: 'var(--ink-4)' }}>what-if · </span>}
              net <strong style={{ fontFamily: 'var(--mono)', color: 'var(--ink)' }}>{signed(result.net)}</strong> · ΣP{' '}
              <strong style={{ fontFamily: 'var(--mono)', color: 'var(--cls-path-text)' }}>+{result.sumPathogenic}</strong> / ΣB{' '}
              <strong style={{ fontFamily: 'var(--mono)', color: 'var(--cls-ben-text)' }}>−{result.sumBenign}</strong> · posterior {pct(result.posterior)}
            </span>
          </div>

          {/* step trace */}
          <StepTrace result={result} exploring={exploring} benignCut={benignCut} />

          {/* draggable net-points puck */}
          <div>
            <div className="eamos-kicker" style={{ marginBottom: 6 }}>
              Net-points line {exploring ? '— drag the puck (what-if)' : '— drag to explore'}
            </div>
            <NetPointsPuck
              net={result.net}
              onChange={onPuckChange}
              benignCut={benignCut}
              label={exploring ? 'Hypothetical net points' : 'Net points'}
            />
          </div>

          <PosteriorGauge computed={computed} />

          <div className="grid gap-5 sm:grid-cols-[minmax(0,260px)_1fr]">
            <EvidencePlane computed={computed} onChange={onPlaneChange} />
            {exploring ? (
              <p role="note" style={{ margin: 0, fontSize: 11.5, lineHeight: 1.5, color: 'var(--ink-4)' }}>
                What-if exploration — a hypothetical ΣP <strong style={{ color: 'var(--ink)' }}>+{result.sumPathogenic}</strong> / ΣB{' '}
                <strong style={{ color: 'var(--ink)' }}>−{result.sumBenign}</strong> → net {signed(result.net)} → {result.tier}.{' '}
                <button type="button" onClick={backToCriteria} style={linkInline}>Back to criteria</button> for the per-criterion
                waterfall (and the BA1 / conflict overrides, which are criteria-level).
              </p>
            ) : (
              <PointWaterfall computed={computed} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function StepTrace({
  result,
  exploring,
  benignCut,
}: {
  result: CriteriaResult
  exploring: boolean
  benignCut: 'tavtigian_2020' | 'acgs_panel'
}) {
  const lines: { text: string; tone?: 'flag' | 'ok' }[] = exploring
    ? [
        { text: `Hypothetical evidence total — ΣP +${result.sumPathogenic} · ΣB −${result.sumBenign} · net ${signed(result.net)}` },
        { text: `tier ${result.tier} · posterior ${pct(result.posterior)}` },
        { text: 'conflict & BA1 overrides are evaluated in Criteria mode', tone: 'flag' },
      ]
    : [
        { text: `Step 1 · sum pathogenic points  ΣP = +${result.sumPathogenic}` },
        { text: `Step 2 · sum benign points      ΣB = −${result.sumBenign}` },
        { text: `Step 3 · net = ΣP − ΣB = ${signed(result.net)}` },
        result.ba1
          ? { text: 'Step 4 · override · BA1 → hard Benign (stops the sum)', tone: 'flag' }
          : result.conflict
            ? { text: `Step 4 · override · ${result.reason}`, tone: 'flag' }
            : { text: 'Step 4 · override · none — net maps directly to tier', tone: 'ok' },
        { text: `Step 5 · tier = ${result.tier}  (${benignCut === 'acgs_panel' ? 'ACGS cut' : 'Tavtigian cut'})` },
        { text: `Step 6 · posterior ≈ ${pct(result.posterior)}` },
      ]

  return (
    <div
      style={{
        fontFamily: 'var(--mono)',
        fontSize: 11,
        lineHeight: 1.7,
        background: 'var(--bg-soft)',
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-md)',
        padding: '10px 12px',
        color: 'var(--ink-2)',
      }}
    >
      {lines.map((l, i) => (
        <div key={i} style={{ color: l.tone === 'flag' ? 'var(--warn-text, var(--warn))' : l.tone === 'ok' ? 'var(--teal-deep)' : 'var(--ink-2)' }}>
          {l.text}
        </div>
      ))}
    </div>
  )
}

const ghostBtn: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: 'var(--ink-2)',
  background: 'var(--bg)',
  border: '0.5px solid var(--line)',
  borderRadius: 'var(--r-md)',
  padding: '4px 12px',
  cursor: 'pointer',
}
// Prominent reset when anchored to a real variant — teal so "return to the real
// call" reads as the safe way back from a what-if exploration.
const resetVariantBtn: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: 'var(--teal-deep)',
  background: 'var(--teal-tint)',
  border: '0.5px solid var(--teal)',
  borderRadius: 'var(--r-md)',
  padding: '4px 12px',
  cursor: 'pointer',
}
const linkBtn: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: 'var(--teal)',
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  padding: '4px 0',
}
const linkInline: React.CSSProperties = {
  color: 'var(--teal)',
  fontWeight: 600,
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  padding: 0,
  textDecoration: 'underline',
  textUnderlineOffset: 3,
}
