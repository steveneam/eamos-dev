import type { ComputationalPredictorRow } from '@/lib/backend'
import { ClassificationBadge } from '@/components/ui/ClassificationBadge'
import { TierTag } from '@/components/ui/TierTag'

interface CalibratedInSilicoTableProps {
  predictors?: ComputationalPredictorRow[] | null
}

const MOCK_TIP =
  'Preview row — this engine is not yet wired to live data. Scores populate once the data source is connected.'

type PredictorCategory = 'Missense' | 'Splice' | 'Genome-wide' | 'Other'

// Per-predictor score calibration that drives the evidence thermometer.
// `tiers` (Pejaver 2022 / Bergquist 2024 / Walker 2023) → multi-tier evidence bar;
// `binary` only → two-zone tool-native cutoff; neither → uncalibrated raw-score bar.
interface Calibration {
  range: [number, number]
  higherDamaging: boolean
  /** Caption under the bar; null = uncalibrated (no ACMG mapping exists). */
  source: string | null
  tiers?: Partial<
    Record<'pp3Strong' | 'pp3Moderate' | 'pp3Supporting' | 'bp4Supporting' | 'bp4Moderate' | 'bp4Strong', number>
  >
  /** Single damaging cutoff for tools with no graded calibration. */
  binary?: number
}

interface CatalogEntry {
  name: string
  category: PredictorCategory
  acmg: string
  tier: 'Free' | 'Pro'
  /** What the engine emits — shown as a caption on placeholder rows + in the name tooltip. */
  metric: string
  cal: Calibration
}

// The full §2 in-silico panel (per the report IA canvas). Each row renders live
// data when the backend supplies it, else a labelled "needs live data"
// placeholder so the complete predictor surface is visible before wiring. Tier
// tags are informational only — everything is shown in full on this account; the
// free/Pro gate (blur) is a pre-launch task, not active here. Calibrated cutoffs
// are the ClinGen SVI values (Pejaver 2022 / Bergquist 2024 / Walker 2023);
// uncalibrated tools render a raw-score bar rather than fabricated tiers.
const PREDICTOR_CATALOG: CatalogEntry[] = [
  // Missense — predict the effect of an amino-acid substitution.
  {
    name: 'AlphaMissense', category: 'Missense', acmg: 'PP3 / BP4', tier: 'Free',
    metric: 'Calibrated missense pathogenicity (0–1) + class',
    cal: { range: [0, 1], higherDamaging: true, source: 'Bergquist 2024', tiers: { pp3Strong: 0.99, pp3Moderate: 0.906, pp3Supporting: 0.792, bp4Supporting: 0.169, bp4Moderate: 0.07 } },
  },
  {
    name: 'ESM1b', category: 'Missense', acmg: 'PP3 / BP4', tier: 'Free',
    metric: 'Protein-LLM variant-effect (log-likelihood)',
    cal: { range: [-25, 10], higherDamaging: false, source: 'Bergquist 2024', tiers: { pp3Strong: -14.0, pp3Moderate: -10.7, pp3Supporting: -6.4, bp4Supporting: -3.2, bp4Moderate: 8.8 } },
  },
  {
    name: 'REVEL', category: 'Missense', acmg: 'PP3 / BP4', tier: 'Pro',
    metric: 'Ensemble missense score (0–1)',
    cal: { range: [0, 1], higherDamaging: true, source: 'Pejaver 2022', tiers: { pp3Strong: 0.932, pp3Moderate: 0.773, pp3Supporting: 0.644, bp4Supporting: 0.29, bp4Moderate: 0.183, bp4Strong: 0.016 } },
  },
  {
    name: 'PrimateAI-3D', category: 'Missense', acmg: 'PP3 / BP4', tier: 'Pro',
    metric: 'Missense pathogenicity from 3D structure + primate variation',
    cal: { range: [0, 1], higherDamaging: true, source: null },
  },
  {
    name: 'MetaLR', category: 'Missense', acmg: 'PP3 / BP4', tier: 'Pro',
    metric: 'Logistic-regression missense meta-score',
    cal: { range: [0, 1], higherDamaging: true, source: 'tool-native', binary: 0.5 },
  },
  // Splice — predict disruption or creation of splice sites.
  {
    name: 'CI-SpliceAI', category: 'Splice', acmg: 'PVS1 / PP3 / BP4', tier: 'Free',
    metric: 'Δ acceptor/donor gain+loss · max-Δ',
    cal: { range: [0, 1], higherDamaging: true, source: 'tool-native', binary: 0.19 },
  },
  {
    name: 'SpliceAI', category: 'Splice', acmg: 'PVS1 / PP3 / BP4', tier: 'Pro',
    metric: 'Δ score per junction · max-Δ',
    cal: { range: [0, 1], higherDamaging: true, source: 'ClinGen SVI (Walker 2023)', tiers: { pp3Supporting: 0.2, bp4Supporting: 0.1 } },
  },
  {
    name: 'Pangolin', category: 'Splice', acmg: 'PVS1 / PP3 / BP4', tier: 'Free',
    metric: 'Splice-strength Δ (multi-tissue) · max-Δ',
    // GPL-3.0 code / CC-BY scores — commercially safe, display-only (ADR 0005).
    cal: { range: [0, 1], higherDamaging: true, source: 'tool-native', binary: 0.2 },
  },
  // Genome-wide — cross-class deleteriousness over coding + non-coding variants.
  {
    name: 'CADD', category: 'Genome-wide', acmg: 'PP3 / BP4', tier: 'Pro',
    metric: 'PHRED-scaled deleteriousness (coding + non-coding)',
    cal: { range: [0, 40], higherDamaging: true, source: 'Pejaver 2022', tiers: { pp3Moderate: 28.1, pp3Supporting: 25.3, bp4Supporting: 22.7, bp4Moderate: 17.3, bp4Strong: 0.15 } },
  },
  {
    name: 'GPN-MSA', category: 'Genome-wide', acmg: 'PP3 / BP4', tier: 'Free',
    metric: 'Genomic-LLM log-likelihood (genome-wide)',
    cal: { range: [-15, 5], higherDamaging: false, source: null },
  },
  {
    name: 'CAPICE', category: 'Genome-wide', acmg: 'PP3 / BP4', tier: 'Pro',
    metric: 'ML pathogenicity 0–1, SNV + indel (consequence-agnostic)',
    // LGPL-3.0 code, but v5 consumes SpliceAI input features (CC-BY-NC) → Pro-only
    // per the vault CAPICE build-spec; display-only, no ClinGen calibration.
    cal: { range: [0, 1], higherDamaging: true, source: null },
  },
]

const CATEGORY_ORDER: PredictorCategory[] = ['Missense', 'Splice', 'Genome-wide', 'Other']

const CATEGORY_LABEL: Record<PredictorCategory, string> = {
  Missense: 'Missense predictors',
  Splice: 'Splice predictors',
  'Genome-wide': 'Genome-wide / non-coding',
  Other: 'Other engines',
}

const ENGINE_TIP: Record<string, string> = {
  AlphaMissense: 'Google DeepMind missense pathogenicity predictor, calibrated 0–1 (CC-BY).',
  ESM1b: 'Protein language model scoring variant effect from sequence alone (MIT).',
  REVEL: 'Ensemble of individual missense predictors, scored 0–1.',
  'PrimateAI-3D': 'Illumina 3D-CNN missense model trained on common primate variants + AlphaFold protein structures.',
  MetaLR: 'Logistic-regression missense meta-predictor combining multiple component scores.',
  'CI-SpliceAI': 'Open splice-effect predictor — Δ scores for acceptor/donor gain & loss.',
  SpliceAI: 'Deep-learning splice predictor — Δ scores per splice junction.',
  Pangolin: 'Deep-learning splice-strength predictor (multi-tissue); often paired with SpliceAI.',
  'GPN-MSA': 'Alignment-based genome-wide DNA language model — rates how damaging a change is from cross-species conservation, across coding and non-coding regions.',
  CADD: 'Combined Annotation Dependent Depletion — genome-wide deleteriousness across coding & non-coding variants (60+ annotations), PHRED-scaled.',
}

// ---- Evidence-thermometer tiers ---------------------------------------------

interface TierMeta {
  points: number
  fill: string
  text: string
}
const TIER_META: Record<string, TierMeta> = {
  'Strong benign': { points: -4, fill: 'var(--cls-ben-dot)', text: 'var(--cls-ben-text)' },
  'Moderate benign': { points: -2, fill: 'color-mix(in oklab, var(--cls-ben-dot) 70%, var(--cls-lben-dot))', text: 'var(--cls-ben-text)' },
  'Supporting benign': { points: -1, fill: 'var(--cls-lben-dot)', text: 'var(--cls-lben-text)' },
  Indeterminate: { points: 0, fill: 'var(--cls-na-dot)', text: 'var(--cls-na-text)' },
  'Supporting path': { points: 1, fill: 'var(--cls-lpath-dot)', text: 'var(--cls-lpath-text)' },
  'Moderate path': { points: 2, fill: 'color-mix(in oklab, var(--cls-path-dot) 60%, var(--cls-lpath-dot))', text: 'var(--cls-lpath-text)' },
  'Strong path': { points: 4, fill: 'var(--cls-path-dot)', text: 'var(--cls-path-text)' },
}
const TIER_KEYS = ['bp4Strong', 'bp4Moderate', 'bp4Supporting', 'pp3Supporting', 'pp3Moderate', 'pp3Strong'] as const
const TIER_BELOW: Record<string, string> = {
  bp4Strong: 'Strong benign', bp4Moderate: 'Moderate benign', bp4Supporting: 'Supporting benign',
  pp3Supporting: 'Indeterminate', pp3Moderate: 'Supporting path', pp3Strong: 'Moderate path',
}
const TIER_ABOVE: Record<string, string> = {
  bp4Strong: 'Moderate benign', bp4Moderate: 'Supporting benign', bp4Supporting: 'Indeterminate',
  pp3Supporting: 'Supporting path', pp3Moderate: 'Moderate path', pp3Strong: 'Strong path',
}

function pathoPos(cal: Calibration, score: number): number {
  const [min, max] = cal.range
  const span = max - min || 1
  const t = Math.max(0, Math.min(1, (score - min) / span))
  return cal.higherDamaging ? t : 1 - t
}

interface Segment {
  from: number
  to: number
  tier: string
}
function buildSegments(cal: Calibration): Segment[] {
  const tiers = cal.tiers
  if (!tiers) return []
  const present = TIER_KEYS.filter((k) => tiers[k] != null)
    .map((k) => ({ key: k, pos: pathoPos(cal, tiers[k] as number) }))
    .sort((a, b) => a.pos - b.pos)
  if (!present.length) return []
  const segs: Segment[] = [{ from: 0, to: present[0].pos, tier: TIER_BELOW[present[0].key] }]
  for (let i = 0; i < present.length; i++) {
    segs.push({ from: present[i].pos, to: i + 1 < present.length ? present[i + 1].pos : 1, tier: TIER_ABOVE[present[i].key] })
  }
  return segs
}
function classifyTier(segs: Segment[], pos: number): string | null {
  for (const s of segs) if (pos >= s.from && pos <= s.to) return s.tier
  return segs.length ? segs[segs.length - 1].tier : null
}

function toNum(value: ComputationalPredictorRow['score']): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string' && value.trim() !== '') {
    const n = Number(value)
    return Number.isFinite(n) ? n : null
  }
  return null
}
function formatScore(value: ComputationalPredictorRow['score']): string {
  const n = toNum(value)
  if (n === null) return value == null || value === '' ? '—' : String(value)
  return Math.abs(n) >= 10 ? n.toFixed(1) : n.toFixed(2)
}
function fmtNum(n: number): string {
  return Math.abs(n) >= 10 ? n.toFixed(1) : n.toFixed(n % 1 === 0 ? 0 : 2)
}
function displayName(name: string): string {
  return name === 'SpliceAI' ? 'SpliceAI Δ' : name
}

// ---- Evidence bar -----------------------------------------------------------

/** Convert a benign→pathogenic position (0..1) back to a raw-score value. */
function invScore(cal: Calibration, pos: number): number {
  const [min, max] = cal.range
  const span = max - min
  return cal.higherDamaging ? min + pos * span : max - pos * span
}

function EvidenceBar({ cal, score }: { cal: Calibration | null; score: number | null }) {
  if (!cal) return <span style={{ color: 'var(--ink-5)' }}>—</span>

  const segs = buildSegments(cal)
  const calibrated = segs.length > 0
  const binary = !calibrated && cal.binary != null ? cal.binary : null
  const hasScore = score != null && Number.isFinite(score)
  const scorePos = hasScore ? pathoPos(cal, score as number) : null
  const binPos = binary != null ? pathoPos(cal, binary) : null

  // Axis endpoints in raw-score units (benign end ◀ ▶ pathogenic end) — gives the
  // raw score context. For lower-damaging tools the axis is flipped so the
  // benign (left) end is the higher raw value.
  const leftVal = invScore(cal, 0)
  const rightVal = invScore(cal, 1)

  let captionLeft = ''
  let captionRight = ''
  let rightColor = 'var(--ink-4)'
  let summaryTip = ''
  if (calibrated) {
    captionLeft = cal.source ?? 'calibrated'
    if (hasScore) {
      const tier = classifyTier(segs, scorePos as number)
      const meta = tier ? TIER_META[tier] : null
      captionRight = tier && meta ? `${tier} (${meta.points >= 0 ? '+' : ''}${meta.points})` : ''
      rightColor = meta?.text ?? 'var(--ink-4)'
      summaryTip = `Raw ${formatScore(score)} → ${tier} (${meta && meta.points >= 0 ? '+' : ''}${meta?.points} ACMG pt), calibrated per ${cal.source}.`
    } else {
      captionRight = 'score pending'
      summaryTip = `Calibrated ACMG evidence scale (${cal.source}). Hover a band for its strength. Score not yet wired.`
    }
  } else if (binary != null) {
    captionLeft = `cutoff ${fmtNum(binary)}`
    captionRight = `${cal.source} · display`
    summaryTip = hasScore
      ? `Raw ${formatScore(score)} vs cutoff ${fmtNum(binary)} → ${(score as number) >= binary ? 'damaging' : 'tolerated'} (${cal.source}; binary cutoff, not ClinGen-graded).`
      : `Tool-native cutoff ${fmtNum(binary)} (${cal.source}; not ClinGen-graded). Score not yet wired.`
  } else {
    captionLeft = 'raw score'
    captionRight = 'not ACMG-calibrated'
    summaryTip = `Raw-score scale ${fmtNum(leftVal)} → ${fmtNum(rightVal)}; no published ACMG calibration for this engine.`
  }

  return (
    <div style={{ minWidth: 188, opacity: hasScore ? 1 : 0.82 }} title={summaryTip}>
      {/* track */}
      <div style={{ position: 'relative', height: 10, borderRadius: 5, border: '0.5px solid var(--line)', background: 'var(--bg-soft2)' }}>
        <div style={{ position: 'absolute', inset: 0, borderRadius: 5, overflow: 'hidden', display: 'flex' }}>
          {calibrated &&
            segs.map((s, i) => {
              const a = invScore(cal, s.from)
              const b = invScore(cal, s.to)
              const lo = Math.min(a, b)
              const hi = Math.max(a, b)
              const meta = TIER_META[s.tier]
              return (
                <span
                  key={i}
                  title={`${s.tier} · ${meta.points >= 0 ? '+' : ''}${meta.points} ACMG pt · raw ${fmtNum(lo)}–${fmtNum(hi)}`}
                  style={{ width: `${(s.to - s.from) * 100}%`, background: meta.fill, cursor: 'help' }}
                />
              )
            })}
          {binary != null && binPos != null && (
            <>
              <span
                title={`Tolerated / benign-leaning (score ${cal.higherDamaging ? '≤' : '≥'} ${fmtNum(binary)})`}
                style={{ width: `${binPos * 100}%`, background: TIER_META['Supporting benign'].fill, cursor: 'help' }}
              />
              <span
                title={`Damaging (score ${cal.higherDamaging ? '>' : '<'} ${fmtNum(binary)}) — tool-native cutoff, not ClinGen-calibrated`}
                style={{ flex: 1, background: TIER_META['Supporting path'].fill, cursor: 'help' }}
              />
            </>
          )}
          {!calibrated && binary == null && <span style={{ flex: 1, background: 'var(--bg-soft2)' }} />}
        </div>
        {/* tier boundary ticks (white separators between vivid bands) */}
        {calibrated &&
          segs.slice(1).map((s, i) => (
            <span key={`tick-${i}`} aria-hidden style={{ position: 'absolute', left: `${s.from * 100}%`, top: 0, bottom: 0, width: 1, background: 'var(--bg)', opacity: 0.75 }} />
          ))}
        {/* score pin — dark down-triangle (shape, not colour) */}
        {hasScore && scorePos != null && (
          <span
            aria-hidden
            style={{
              position: 'absolute',
              top: -6,
              left: `${scorePos * 100}%`,
              transform: 'translateX(-50%)',
              width: 0,
              height: 0,
              borderLeft: '4px solid transparent',
              borderRight: '4px solid transparent',
              borderTop: '7px solid var(--ink)',
              filter: 'drop-shadow(0 0 1px var(--bg))',
            }}
          />
        )}
      </div>
      {/* range endpoints (raw-score units): benign end ◀ ▶ pathogenic end */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 2, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--ink-4)' }}>
        <span>{fmtNum(leftVal)}</span>
        <span>{fmtNum(rightVal)}</span>
      </div>
      {/* source (left) + resulting tier / status (right) */}
      <div style={{ marginTop: 2, display: 'flex', justifyContent: 'space-between', gap: 6, fontSize: 10, lineHeight: 1.3 }}>
        <span style={{ color: 'var(--ink-4)', fontFamily: 'var(--mono)' }}>{captionLeft}</span>
        <span style={{ color: rightColor, fontWeight: hasScore && calibrated ? 600 : 400, textAlign: 'right' }}>{captionRight}</span>
      </div>
    </div>
  )
}

// ---- Table primitives -------------------------------------------------------

const HEADER_CELL: React.CSSProperties = {
  fontSize: 10,
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: 'var(--ink-4)',
  textAlign: 'left',
  padding: '8px 12px',
  borderBottom: '0.5px solid var(--line)',
  background: 'var(--bg-soft)',
  whiteSpace: 'nowrap',
}
const BODY_CELL: React.CSSProperties = {
  fontSize: 12.5,
  color: 'var(--ink-2)',
  padding: '10px 12px',
  borderBottom: '0.5px solid var(--line)',
  verticalAlign: 'top',
}
function groupHeaderStyle(notFirst: boolean): React.CSSProperties {
  return {
    fontSize: 10,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: 'var(--ink-3)',
    padding: '7px 12px',
    background: 'var(--bg-soft2)',
    borderTop: notFirst ? '0.5px solid var(--line)' : 'none',
    borderBottom: '0.5px solid var(--line)',
  }
}

interface RowData {
  key: string
  category: PredictorCategory
  name: string
  tier: 'Free' | 'Pro' | null
  acmg: string | null
  metric: string | null
  tip: string | null
  cal: Calibration | null
  live: ComputationalPredictorRow | null
}

function PredictorRow({ rd, isLast }: { rd: RowData; isLast: boolean }) {
  const live = rd.live
  const bucket = live?.calibration_bucket ?? null
  const calibratedLabel = live?.calibrated_label ?? null
  const cell: React.CSSProperties = { ...BODY_CELL, borderBottom: isLast ? 'none' : BODY_CELL.borderBottom }
  // Only ClinGen-calibrated engines (with graded tiers) actually fire an ACMG
  // criterion; everything else is display-only context (ADR 0005).
  const activator = !!(rd.cal?.tiers && Object.keys(rd.cal.tiers).length > 0)

  // Sub-caption: the precise engine variant ("PrimateAI-3D" under the slot) or
  // the source label; placeholder rows show what the engine emits.
  let subCaption: string | null = null
  if (live) {
    if (normalizeName(live.name) !== normalizeName(rd.name)) subCaption = live.name
    else if (live.source && live.source !== live.name) subCaption = live.source
  } else {
    subCaption = rd.metric
  }

  // Version now lives in the engine-name hover (its own column was removed).
  const engineTitle = [rd.tip, live?.version ? `Version: ${live.version}` : null].filter(Boolean).join('  ·  ') || undefined

  return (
    <tr>
      <td style={cell}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 600, color: 'var(--ink)', cursor: engineTitle ? 'help' : undefined }} title={engineTitle}>
            {displayName(rd.name)}
          </span>
          {rd.tier && <TierTag tier={rd.tier} />}
        </div>
        {subCaption && <div style={{ fontSize: 10.5, color: 'var(--ink-4)', marginTop: 2 }}>{subCaption}</div>}
      </td>
      <td style={{ ...cell, whiteSpace: 'nowrap' }}>
        {!rd.acmg ? (
          <span style={{ color: 'var(--ink-5)' }}>—</span>
        ) : activator ? (
          <span title={`ClinGen-calibrated activator for ACMG ${rd.acmg}.`} style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-3)', cursor: 'help' }}>
            {rd.acmg}
          </span>
        ) : (
          <span
            title="Shown for context — not a ClinGen-calibrated ACMG evidence activator."
            style={{ fontSize: 10.5, color: 'var(--ink-5)', borderBottom: '1px dotted var(--ink-5)', cursor: 'help' }}
          >
            display only
          </span>
        )}
      </td>
      <td style={cell}>
        {live && bucket ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
            <ClassificationBadge classification={bucket} />
            {calibratedLabel && <span style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>{calibratedLabel}</span>}
            {live.calibration_method && <span style={{ fontSize: 10.5, color: 'var(--ink-4)' }}>{live.calibration_method}</span>}
          </div>
        ) : live ? (
          <span style={{ fontSize: 11.5, color: 'var(--ink-4)', fontStyle: 'italic' }}>No published calibration</span>
        ) : (
          <span className="eamos-mock" title={MOCK_TIP}>
            Needs live data
          </span>
        )}
      </td>
      <td style={{ ...cell, fontFamily: 'var(--mono)', textAlign: 'right' }}>{live ? formatScore(live.score) : '—'}</td>
      <td style={cell}>
        <EvidenceBar cal={rd.cal} score={live ? toNum(live.score) : null} />
      </td>
    </tr>
  )
}

function normalizeName(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]/g, '')
}

// Map a live predictor name onto its catalog slot. Exact match, else the catalog
// entry whose name is a prefix of the live name (longest wins) so "CADD PHRED" →
// CADD and "PrimateAI-3D" → PrimateAI-3D without CI-SpliceAI colliding with SpliceAI.
function matchEntry(liveName: string): CatalogEntry | null {
  const n = normalizeName(liveName)
  let best: CatalogEntry | null = null
  for (const entry of PREDICTOR_CATALOG) {
    const en = normalizeName(entry.name)
    if (n === en || n.startsWith(en)) {
      if (!best || normalizeName(best.name).length < en.length) best = entry
    }
  }
  return best
}

export function CalibratedInSilicoTable({ predictors }: CalibratedInSilicoTableProps) {
  // AlphaMissense re-enabled in §2 (Steven 2026-06-08) — no longer filtered out.
  const live = predictors ?? []

  // Assign each live predictor to its catalog slot (exact or prefix/alias match);
  // unmatched or duplicate live rows fall to "Other engines".
  const liveForEntry = new Map<string, ComputationalPredictorRow>()
  const others: ComputationalPredictorRow[] = []
  for (const row of live) {
    const entry = matchEntry(row.name)
    if (entry && !liveForEntry.has(entry.name)) liveForEntry.set(entry.name, row)
    else others.push(row)
  }

  const ordered: RowData[] = PREDICTOR_CATALOG.map((entry) => ({
    key: entry.name,
    category: entry.category,
    name: entry.name,
    tier: entry.tier,
    acmg: entry.acmg,
    metric: entry.metric,
    tip: ENGINE_TIP[entry.name] ?? null,
    cal: entry.cal,
    live: liveForEntry.get(entry.name) ?? null,
  }))
  for (const row of others) {
    ordered.push({
      key: `other-${row.name}`,
      category: 'Other',
      name: row.name,
      tier: null,
      acmg: null,
      metric: null,
      tip: ENGINE_TIP[row.name] ?? null,
      cal: null,
      live: row,
    })
  }

  const sorted = CATEGORY_ORDER.flatMap((cat) => ordered.filter((r) => r.category === cat))
  const liveCount = sorted.filter((r) => r.live).length

  return (
    <div style={{ marginBottom: 18 }}>
      <div className="eamos-kicker" style={{ marginBottom: 6 }}>
        In-silico predictions
      </div>
      <p style={{ fontSize: 11.5, color: 'var(--ink-4)', margin: '0 0 10px', lineHeight: 1.5 }}>
        The full predictor panel, grouped by what each engine scores. The bar shows where the raw score sits on each
        engine&apos;s benign↔pathogenic scale (calibrated to ClinGen thresholds where they exist). Rows marked{' '}
        <span className="eamos-mock" title={MOCK_TIP} style={{ verticalAlign: 'middle' }}>
          Needs live data
        </span>{' '}
        are part of the planned panel but not yet wired ({liveCount} of {sorted.length} engines live).
      </p>

      <div style={{ border: '0.5px solid var(--line)', borderRadius: 'var(--r-md)', overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
        <table style={{ width: '100%', minWidth: 720, borderCollapse: 'collapse', fontVariantNumeric: 'tabular-nums' }}>
          <thead>
            <tr>
              <th style={HEADER_CELL}>Engine</th>
              <th style={{ ...HEADER_CELL, fontFamily: 'var(--mono)' }}>→ ACMG</th>
              <th style={HEADER_CELL}>Calibrated label</th>
              <th style={{ ...HEADER_CELL, fontFamily: 'var(--mono)', textAlign: 'right' }}>Raw score</th>
              <th style={HEADER_CELL}>Score vs thresholds</th>
            </tr>
          </thead>
          <tbody>
            {(() => {
              const out: React.ReactNode[] = []
              let lastGroup: PredictorCategory | null = null
              sorted.forEach((rd, i) => {
                if (rd.category !== lastGroup) {
                  out.push(
                    <tr key={`group-${rd.category}`}>
                      <td colSpan={5} style={groupHeaderStyle(lastGroup !== null)}>
                        {CATEGORY_LABEL[rd.category]}
                      </td>
                    </tr>,
                  )
                  lastGroup = rd.category
                }
                out.push(<PredictorRow key={rd.key} rd={rd} isLast={i === sorted.length - 1} />)
              })
              return out
            })()}
          </tbody>
        </table>
      </div>
    </div>
  )
}
