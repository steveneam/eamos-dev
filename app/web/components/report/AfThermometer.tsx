'use client'
import type { EvidenceSourceSummary } from '@/lib/backend'
import { InfoHint } from '@/components/ui/InfoHint'
import { SourceLink } from '@/components/ui/SourceLink'
import { GNOMAD_AF_BANDS } from './gnomadMapTheme'
import { ScaleTrack } from './ScoreScale'

// Franklin-style allele-frequency "thermometer" (report v3, design §4). A
// threshold bullet bar over the SAME GNOMAD_AF_BANDS cutoffs the world map +
// Population card use, so §3 and the card agree by construction. The numeric AF
// is always visible as text (never colour-position alone — ui-ux-pro-max bullet
// chart, AAA), and absent variants pin to grey, never red.

const AF_CHIP_TIP: Record<string, string> = {
  BA1: 'Allele frequency ≥ 5% in a general population — stand-alone evidence the variant is benign (ACMG BA1).',
  BS1: 'Allele frequency higher than expected for the disease (1–5%) — strong evidence toward benign (ACMG BS1).',
  PM2: 'Absent or extremely rare (< 0.1%) in population databases — supporting evidence toward pathogenic (ACMG PM2).',
}
const INTERMEDIATE_TIP =
  'Uncommon — between the benign and pathogenic frequency thresholds; not decisive on its own.'
const MIS_Z_TIP =
  'Missense Z-score: how depleted the gene is of missense variation vs expectation. Higher = more constrained; Z ≥ 3.1 marks a missense-constrained gene.'
const MIS_OE_TIP =
  'Missense observed/expected ratio: fraction of expected missense variants actually seen. Toward 0 = strong depletion (constrained); ≈ 1 = tolerant.'
const MOCK_TIP =
  'Preview value — not yet wired to live data. This number is illustrative and will update once the data source is connected.'
const CONSTRAINT_TIP =
  'gnomAD gene constraint — how depleted this gene is of variation vs expectation. Low LOEUF / high pLI = the gene poorly tolerates loss-of-function; high missense constraint = it poorly tolerates missense change.'
const LOEUF_TIP =
  "LOEUF — loss-of-function observed/expected upper-bound fraction, gnomAD's primary LoF-constraint metric (the upper end of the 90% CI of the LoF o/e ratio). Lower = less tolerant of loss-of-function; < 0.6 (gnomAD v4) marks a constrained gene."
const PLI_TIP =
  'pLI — probability the gene is intolerant of a single loss-of-function allele. ≥ 0.9 = LoF-intolerant. gnomAD now leads with LOEUF.'
const AF_TIP =
  'Allele frequency — how often this exact variant appears across gnomAD reference-population samples. Common variants are usually benign (BA1/BS1); very rare or absent variants give supporting evidence toward pathogenic (PM2). The bar above places this AF on the ACMG benign↔pathogenic thresholds.'

// gnomAD-style constraint thermometer: a coloured banded scale (red = constrained
// → green = tolerant, low value = constrained for both LOEUF and missense o/e) with
// a value pin and the constrained-threshold tick. Mirrors gnomAD's o/e visual but
// uses the report's shared class-ramp tokens so §3 matches the rest of the page.
interface GaugeBand { upTo: number; color: string; label: string }

const LOEUF_BANDS: GaugeBand[] = [
  { upTo: 0.33, color: 'var(--cls-path-dot)', label: 'Highly constrained' },
  { upTo: 0.66, color: 'var(--cls-lpath-dot)', label: 'Constrained' },
  { upTo: 1.0, color: 'var(--cls-vus-dot)', label: 'Moderately tolerant' },
  { upTo: 1.5, color: 'var(--cls-ben-dot)', label: 'LoF-tolerant' },
]
const MIS_OE_BANDS: GaugeBand[] = [
  { upTo: 0.4, color: 'var(--cls-path-dot)', label: 'Strongly depleted' },
  { upTo: 0.6, color: 'var(--cls-lpath-dot)', label: 'Depleted' },
  { upTo: 0.8, color: 'var(--cls-vus-dot)', label: 'Mild depletion' },
  { upTo: 1.2, color: 'var(--cls-ben-dot)', label: 'Tolerant' },
]

function loeufStatus(l: number): { text: string; color: string } {
  if (l < 0.33) return { text: 'Highly constrained', color: 'var(--cls-path-text)' }
  if (l < 0.6) return { text: 'Constrained', color: 'var(--cls-lpath-text)' }
  if (l < 1.0) return { text: 'Moderately tolerant', color: 'var(--cls-vus-text)' }
  return { text: 'LoF-tolerant', color: 'var(--cls-ben-text)' }
}

function readConstraint(evidence?: EvidenceSourceSummary[]): {
  loeuf: number | null
  pli: number | null
  sourceUrl: string | null
} {
  const row = evidence?.find((e) => e.source?.toLowerCase() === 'molecular_context')
  const c = (row?.summary as Record<string, unknown> | undefined)?.gnomad_constraint as
    | Record<string, unknown>
    | undefined
  const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : null)
  const url = typeof c?.source_url === 'string' && c.source_url ? c.source_url : null
  return { loeuf: num(c?.loeuf), pli: num(c?.pli), sourceUrl: url }
}

function ConstraintGauge({
  label, infoTip, axisMax, bands, value, valueText, badge, badgeTip, threshold, thresholdLabel, status, statusColor, mock,
}: {
  label: string
  infoTip: string
  axisMax: number
  bands: GaugeBand[]
  value: number
  valueText: string
  badge?: string
  badgeTip?: string
  threshold?: number
  thresholdLabel?: string
  status: string
  statusColor: string
  mock?: boolean
}) {
  // Convert the cumulative-`upTo` gauge bands into the shared scale's per-band
  // fractions; the value pin + constrained threshold ride the same primitive §2 uses.
  // Each band carries a hover title (zone meaning + the metric range it covers)
  // so hovering a §3 sector explains it — matching §2's EvidenceBar bands.
  const unit = label.split('·').pop()?.trim() ?? ''
  const scaleBands = bands.map((b, i) => {
    const start = i === 0 ? 0 : bands[i - 1].upTo
    return {
      frac: (b.upTo - start) / axisMax,
      color: b.color,
      title: `${b.label} · ${unit} ${start}–${b.upTo}`,
    }
  })
  return (
    <div style={{ border: '0.5px solid var(--line)', borderRadius: 'var(--r-sm)', background: 'var(--bg)', padding: '8px 10px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, flexWrap: 'wrap', marginBottom: 9 }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--ink-4)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</span>
        <InfoHint tip={infoTip} />
        <span style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 600, color: mock ? 'var(--ink-4)' : 'var(--ink)', marginLeft: 2 }}>{valueText}</span>
        {badge && (
          <span title={badgeTip} style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--ink-4)', border: '0.5px solid var(--line)', borderRadius: 999, padding: '0 6px', cursor: badgeTip ? 'help' : 'default' }}>
            {badge}
          </span>
        )}
        {mock && <span className="eamos-mock" title={MOCK_TIP}>Mock</span>}
        <span style={{ marginLeft: 'auto', fontSize: 10.5, color: statusColor, fontWeight: 600 }}>{status}</span>
      </div>
      <ScaleTrack
        bands={scaleBands}
        threshold={threshold != null ? { pos: threshold / axisMax, title: thresholdLabel } : null}
        pin={{ pos: value / axisMax, muted: mock }}
      />
    </div>
  )
}

function fmtAf(af: number | null): string {
  if (af == null) return 'Not observed'
  if (af === 0) return '0%'
  const pct = af * 100
  if (pct < 0.001) return `${pct.toExponential(2)}%`
  return `${Number(pct.toPrecision(3))}%`
}

export function AfThermometer({ af, evidence }: { af: number | null; evidence?: EvidenceSourceSummary[] }) {
  const observed = af != null && af > 0
  const bandIdx = observed ? GNOMAD_AF_BANDS.findIndex((b) => (af as number) >= b.min) : -1
  const band = bandIdx >= 0 ? GNOMAD_AF_BANDS[bandIdx] : null
  // Each of the 4 bands is an equal segment; the marker sits in its band's
  // centre (precision lives in the always-visible numeric AF text). Absent →
  // pinned to the far rare end.
  const markerPct = observed ? (bandIdx + 0.5) * 25 : 98

  const verdict = !observed
    ? 'Absent · PM2-supporting'
    : band?.acmg === 'BA1'
      ? 'Common · benign (BA1)'
      : band?.acmg === 'BS1'
        ? 'Frequent · benign (BS1)'
        : band?.acmg === 'PM2'
          ? 'Rare · PM2-supporting'
          : 'Uncommon · intermediate'
  const verdictColor = !observed
    ? 'var(--cls-na-text)'
    : band?.acmg === 'BA1' || band?.acmg === 'BS1'
      ? 'var(--cls-ben-text)'
      : band?.acmg === 'PM2'
        ? 'var(--cls-lpath-text)'
        : 'var(--cls-vus-text)'

  return (
    <div
      style={{
        background: 'var(--bg-soft)',
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-md)',
        padding: 'var(--report-subpanel-pad)',
        marginBottom: 14,
      }}
    >
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
        <span aria-hidden style={{ width: 8, height: 8, borderRadius: 999, background: verdictColor }} />
        <span style={{ fontFamily: 'var(--display)', fontSize: 15, fontWeight: 600, color: 'var(--ink)' }}>
          {verdict}
        </span>
      </div>

      {/* Threshold track */}
      <div style={{ position: 'relative', marginTop: 24, marginBottom: 6 }}>
        <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden' }}>
          {GNOMAD_AF_BANDS.map((b) => (
            <span key={b.id} style={{ flex: 1, background: b.color, cursor: 'help' }} title={b.acmg ? AF_CHIP_TIP[b.acmg] : INTERMEDIATE_TIP} />
          ))}
        </div>
        {/* Variant marker — a dark down-pointing pin + haloed line (shape, not
            colour, so it's obvious over any band). ui-ux-pro-max bullet-chart. */}
        <span
          aria-hidden
          style={{
            position: 'absolute',
            top: -13,
            left: `${markerPct}%`,
            transform: 'translateX(-50%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            pointerEvents: 'none',
          }}
        >
          <span
            style={{
              width: 0,
              height: 0,
              borderLeft: '5px solid transparent',
              borderRight: '5px solid transparent',
              borderTop: '7px solid var(--ink)',
            }}
          />
          <span
            style={{
              width: 3,
              height: 16,
              marginTop: -1,
              background: 'var(--ink)',
              borderRadius: 1,
              boxShadow: '0 0 0 1.5px var(--bg)',
            }}
          />
        </span>
      </div>

      {/* Zone labels + ACMG chips */}
      <div style={{ display: 'flex' }}>
        {GNOMAD_AF_BANDS.map((b) => (
          <div key={b.id} style={{ flex: 1, textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--ink-4)' }}>{b.label}</div>
            {b.acmg ? (
              <span
                title={AF_CHIP_TIP[b.acmg]}
                style={{
                  display: 'inline-block',
                  marginTop: 2,
                  fontSize: 9,
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                  color: 'var(--ink-3)',
                  borderBottom: '1px dotted var(--ink-5)',
                  cursor: 'help',
                }}
              >
                {b.acmg}
              </span>
            ) : (
              <span title={INTERMEDIATE_TIP} style={{ display: 'inline-block', marginTop: 2, fontSize: 9, color: 'var(--ink-5)', cursor: 'help' }}>
                interm.
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Allele frequency on its own fixed line — always in the same place,
          never tracking the marker (so there's one place to look). */}
      <div style={{ marginTop: 12 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Allele frequency
        </span>
        <InfoHint tip={AF_TIP} />
        <span style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 500, color: 'var(--ink)', marginLeft: 8 }}>{fmtAf(af)}</span>
        <span style={{ color: 'var(--ink-4)', fontSize: 11, marginLeft: 6 }}>· gnomAD v4 · joint</span>
      </div>

      {/* Gene constraint readout (gnomAD), gnomAD-style coloured thermometers.
          LOEUF + pLI are LIVE from molecular_context; the o/e bar geometry +
          the missense axis are illustrative (tagged) until wired. "LoF Z" was
          dropped — gnomAD has no LoF Z-score; LOEUF is its LoF-constraint metric. */}
      {(() => {
        const { loeuf: realLoeuf, pli: realPli, sourceUrl: constraintSrc } = readConstraint(evidence)
        const loeufMock = realLoeuf == null
        const loeuf = realLoeuf ?? 0.41
        const pli = realPli ?? 0.86
        const ls = loeufStatus(loeuf)
        // Missense axis is gated → illustrative o/e + Z, coherent with the gene's LoF tolerance.
        const misOe = 0.94
        const misZ = 1.86
        const misConstrained = misZ >= 3.1
        return (
          <div style={{ marginTop: 14, paddingTop: 12, borderTop: '0.5px solid var(--line)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 10.5, fontWeight: 600, color: 'var(--ink-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Gene constraint
              </span>
              <InfoHint tip={CONSTRAINT_TIP} />
              {constraintSrc ? (
                <SourceLink href={constraintSrc} fontSize={11} style={{ marginLeft: 'auto' }}>
                  gnomAD v4
                </SourceLink>
              ) : (
                <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--ink-4)' }}>gnomAD v4</span>
              )}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
              <ConstraintGauge
                label="LoF · LOEUF"
                infoTip={LOEUF_TIP}
                axisMax={1.5}
                bands={LOEUF_BANDS}
                value={loeuf}
                valueText={loeuf.toFixed(2)}
                badge={`pLI ${pli.toFixed(2)}`}
                badgeTip={PLI_TIP}
                threshold={0.6}
                thresholdLabel="Constrained threshold (LOEUF < 0.6, gnomAD v4)"
                status={ls.text}
                statusColor={ls.color}
                mock={loeufMock}
              />
              <ConstraintGauge
                label="Missense · o/e"
                infoTip={MIS_OE_TIP}
                axisMax={1.2}
                bands={MIS_OE_BANDS}
                value={misOe}
                valueText={misOe.toFixed(2)}
                badge={`Z ${misZ.toFixed(2)}`}
                badgeTip={MIS_Z_TIP}
                threshold={0.6}
                thresholdLabel="Region of missense constraint (lower o/e)"
                status={misConstrained ? 'Constrained' : 'Not constrained'}
                statusColor={misConstrained ? 'var(--cls-lpath-text)' : 'var(--cls-ben-text)'}
                mock
              />
            </div>
          </div>
        )
      })()}
    </div>
  )
}
