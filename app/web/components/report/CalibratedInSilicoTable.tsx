import type { ComputationalPredictorRow } from '@/lib/backend'
import { ClassificationBadge } from '@/components/ui/ClassificationBadge'

interface CalibratedInSilicoTableProps {
  predictors?: ComputationalPredictorRow[] | null
}

const MOCK_TIP =
  'Preview row — this engine is not yet wired to live data. Scores populate once the data source is connected.'

type PredictorCategory = 'Missense' | 'Splice' | 'Genome-wide' | 'Other'

interface CatalogEntry {
  name: string
  category: PredictorCategory
  acmg: string
  tier: 'Free' | 'Pro'
  /** What the engine emits — shown as a caption on placeholder rows + in the name tooltip. */
  metric: string
}

// The full §2 in-silico panel (per the report IA canvas). Each row renders live
// data when the backend supplies it, else a labelled "needs live data"
// placeholder so the complete predictor surface is visible before wiring. Tier
// tags are informational only — everything is shown in full on this account; the
// free/Pro gate (blur) is a pre-launch task, not active here.
const PREDICTOR_CATALOG: CatalogEntry[] = [
  // Missense — predict the effect of an amino-acid substitution.
  { name: 'AlphaMissense', category: 'Missense', acmg: 'PP3 / BP4', tier: 'Free', metric: 'Calibrated missense pathogenicity (0–1) + class' },
  { name: 'ESM1b', category: 'Missense', acmg: 'PP3 / BP4', tier: 'Free', metric: 'Protein-LLM variant-effect (log-likelihood)' },
  { name: 'REVEL', category: 'Missense', acmg: 'PP3 / BP4', tier: 'Pro', metric: 'Ensemble missense score (0–1)' },
  { name: 'PrimateAI-3D', category: 'Missense', acmg: 'PP3 / BP4', tier: 'Pro', metric: 'Missense pathogenicity from 3D structure + primate variation' },
  { name: 'MetaLR', category: 'Missense', acmg: 'PP3 / BP4', tier: 'Pro', metric: 'Logistic-regression missense meta-score' },
  // Splice — predict disruption or creation of splice sites.
  { name: 'CI-SpliceAI', category: 'Splice', acmg: 'PVS1 / PP3 / BP4', tier: 'Free', metric: 'Δ acceptor/donor gain+loss · max-Δ' },
  { name: 'SpliceAI', category: 'Splice', acmg: 'PVS1 / PP3 / BP4', tier: 'Pro', metric: 'Δ score per junction · max-Δ' },
  // Genome-wide — cross-class deleteriousness over coding + non-coding variants.
  { name: 'CADD', category: 'Genome-wide', acmg: 'PP3 / BP4', tier: 'Pro', metric: 'PHRED-scaled deleteriousness (coding + non-coding)' },
  { name: 'GPN-MSA', category: 'Genome-wide', acmg: 'PP3 / BP4', tier: 'Free', metric: 'Genomic-LLM log-likelihood (genome-wide)' },
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
  'GPN-MSA': 'Alignment-based genome-wide DNA language model — rates how damaging a change is from cross-species conservation, across coding and non-coding regions.',
  CADD: 'Combined Annotation Dependent Depletion — genome-wide deleteriousness across coding & non-coding variants (60+ annotations), PHRED-scaled.',
}

function normalizeName(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]/g, '')
}

// Map a live predictor name onto its catalog slot. Exact match, else the catalog
// entry whose name is a prefix of the live name (longest wins) so "CADD PHRED" →
// CADD and "PrimateAI-3D" → PrimateAI without CI-SpliceAI colliding with SpliceAI.
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

function formatScore(value: ComputationalPredictorRow['score']): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '—'
    return Math.abs(value) >= 10 ? value.toFixed(1) : value.toFixed(2)
  }
  return String(value)
}

function formatThreshold(value: ComputationalPredictorRow['threshold']): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '—'
    return Math.abs(value) >= 10 ? value.toFixed(1) : value.toFixed(2)
  }
  return String(value)
}

function displayName(name: string): string {
  return name === 'SpliceAI' ? 'SpliceAI Δ' : name
}

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

function TierTag({ tier }: { tier: 'Free' | 'Pro' }) {
  const isPro = tier === 'Pro'
  return (
    <span
      title={
        isPro
          ? 'Premium engine — shown in full on this account; gated on the free tier at launch.'
          : 'Included on the free tier.'
      }
      style={{
        fontSize: 9.5,
        fontWeight: 700,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        padding: '0.5px 5px',
        borderRadius: 999,
        border: `0.5px solid ${isPro ? 'var(--warn-bdr)' : 'var(--teal-bdr)'}`,
        background: isPro ? 'var(--warn-tint)' : 'var(--teal-tint)',
        color: isPro ? 'var(--warn-text)' : 'var(--teal-deep)',
        whiteSpace: 'nowrap',
      }}
    >
      {tier}
    </span>
  )
}

interface RowData {
  key: string
  category: PredictorCategory
  name: string
  tier: 'Free' | 'Pro' | null
  acmg: string | null
  metric: string | null
  tip: string | null
  live: ComputationalPredictorRow | null
}

function PredictorRow({ rd, isLast }: { rd: RowData; isLast: boolean }) {
  const live = rd.live
  const bucket = live?.calibration_bucket ?? null
  const calibratedLabel = live?.calibrated_label ?? null
  const cell: React.CSSProperties = {
    ...BODY_CELL,
    borderBottom: isLast ? 'none' : BODY_CELL.borderBottom,
  }

  // Sub-caption: the precise engine variant ("PrimateAI-3D" under the "PrimateAI"
  // slot) or the source label; placeholder rows show what the engine emits.
  let subCaption: string | null = null
  if (live) {
    if (normalizeName(live.name) !== normalizeName(rd.name)) subCaption = live.name
    else if (live.source && live.source !== live.name) subCaption = live.source
  } else {
    subCaption = rd.metric
  }

  return (
    <tr>
      <td style={cell}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span
            style={{ fontWeight: 600, color: 'var(--ink-1)', cursor: rd.tip ? 'help' : undefined }}
            title={rd.tip ?? undefined}
          >
            {displayName(rd.name)}
          </span>
          {rd.tier && <TierTag tier={rd.tier} />}
        </div>
        {subCaption && (
          <div style={{ fontSize: 10.5, color: 'var(--ink-4)', marginTop: 2 }}>{subCaption}</div>
        )}
      </td>
      <td style={{ ...cell, whiteSpace: 'nowrap' }}>
        {rd.acmg ? (
          <span
            title={`Contributes to ACMG criterion ${rd.acmg}`}
            style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-3)', cursor: 'help' }}
          >
            {rd.acmg}
          </span>
        ) : (
          <span style={{ color: 'var(--ink-5)' }}>—</span>
        )}
      </td>
      <td style={cell}>
        {live && bucket ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
            <ClassificationBadge classification={bucket} />
            {calibratedLabel && (
              <span style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>{calibratedLabel}</span>
            )}
            {live.calibration_method && (
              <span style={{ fontSize: 10.5, color: 'var(--ink-4)' }}>{live.calibration_method}</span>
            )}
          </div>
        ) : live ? (
          <span style={{ fontSize: 11.5, color: 'var(--ink-4)', fontStyle: 'italic' }}>
            No published calibration
          </span>
        ) : (
          <span className="eamos-mock" title={MOCK_TIP}>
            Needs live data
          </span>
        )}
      </td>
      <td style={{ ...cell, fontFamily: 'var(--mono)', textAlign: 'right' }}>
        {live ? formatScore(live.score) : '—'}
      </td>
      <td style={{ ...cell, fontFamily: 'var(--mono)', textAlign: 'right', color: 'var(--ink-3)' }}>
        {live ? formatThreshold(live.threshold) : '—'}
      </td>
      <td style={{ ...cell, fontSize: 11, color: 'var(--ink-4)' }}>{live?.version ?? '—'}</td>
    </tr>
  )
}

export function CalibratedInSilicoTable({ predictors }: CalibratedInSilicoTableProps) {
  // AlphaMissense re-enabled in §2 (Steven 2026-06-08) — no longer filtered out.
  const live = predictors ?? []

  // Assign each live predictor to its catalog slot (exact or prefix/alias match,
  // so "CADD PHRED" → CADD and "PrimateAI-3D" → PrimateAI inherit the slot's
  // tier/ACMG); unmatched or duplicate live rows fall to "Other engines".
  const liveForEntry = new Map<string, ComputationalPredictorRow>()
  const others: ComputationalPredictorRow[] = []
  for (const row of live) {
    const entry = matchEntry(row.name)
    if (entry && !liveForEntry.has(entry.name)) {
      liveForEntry.set(entry.name, row)
    } else {
      others.push(row)
    }
  }

  const ordered: RowData[] = PREDICTOR_CATALOG.map((entry) => ({
    key: entry.name,
    category: entry.category,
    name: entry.name,
    tier: entry.tier,
    acmg: entry.acmg,
    metric: entry.metric,
    tip: ENGINE_TIP[entry.name] ?? null,
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
        The full predictor panel, grouped by what each engine scores. Rows marked{' '}
        <span className="eamos-mock" title={MOCK_TIP} style={{ verticalAlign: 'middle' }}>
          Needs live data
        </span>{' '}
        are part of the planned panel but not yet wired to a live source ({liveCount} of {sorted.length}{' '}
        engines live).
      </p>

      <div
        style={{
          border: '0.5px solid var(--line)',
          borderRadius: 'var(--r-md)',
          overflowX: 'auto',
          WebkitOverflowScrolling: 'touch',
        }}
      >
        <table
          style={{
            width: '100%',
            minWidth: 640,
            borderCollapse: 'collapse',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          <thead>
            <tr>
              <th style={HEADER_CELL}>Engine</th>
              <th style={{ ...HEADER_CELL, fontFamily: 'var(--mono)' }}>→ ACMG</th>
              <th style={HEADER_CELL}>Calibrated label</th>
              <th style={{ ...HEADER_CELL, fontFamily: 'var(--mono)', textAlign: 'right' }}>Raw score</th>
              <th style={{ ...HEADER_CELL, fontFamily: 'var(--mono)', textAlign: 'right' }}>Threshold</th>
              <th style={HEADER_CELL}>Version</th>
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
                      <td colSpan={6} style={groupHeaderStyle(lastGroup !== null)}>
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
