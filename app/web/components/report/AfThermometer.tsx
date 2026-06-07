'use client'
import { GNOMAD_AF_BANDS } from './gnomadMapTheme'

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
const Z_TIP =
  'gnomAD missense constraint Z-score: how depleted the gene is of missense changes versus expectation. Higher = more constrained (Z ≳ 3 is constrained).'
const MOCK_TIP =
  'Preview value — not yet wired to live data. This number is illustrative and will update once the data source is connected.'

function fmtAf(af: number | null): string {
  if (af == null) return 'Not observed'
  if (af === 0) return '0%'
  const pct = af * 100
  if (pct < 0.001) return `${pct.toExponential(2)}%`
  return `${Number(pct.toPrecision(3))}%`
}

export function AfThermometer({ af }: { af: number | null }) {
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
        padding: '14px 18px',
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
            <span key={b.id} style={{ flex: 1, background: b.color }} title={`${b.label}${b.acmg ? ` · ${b.acmg}` : ''}`} />
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
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-4)', textTransform: 'uppercase', letterSpacing: '0.06em', marginRight: 8 }}>
          Allele frequency
        </span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 500, color: 'var(--ink)' }}>{fmtAf(af)}</span>
        <span style={{ color: 'var(--ink-4)', fontSize: 11, marginLeft: 6 }}>· gnomAD v4 · joint</span>
      </div>

      {/* Constraint readout (gene-level). LOEUF / pLI render in Gene & locus;
          the missense Z-score is not yet in the contract → mock + label. */}
      <div style={{ marginTop: 14, paddingTop: 12, borderTop: '0.5px solid var(--line)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <span
          title={Z_TIP}
          style={{ fontSize: 10.5, fontWeight: 600, color: 'var(--ink-4)', textTransform: 'uppercase', letterSpacing: '0.06em', borderBottom: '1px dotted var(--ink-5)', cursor: 'help' }}
        >
          Missense Z
        </span>
        <span className="eamos-mock" title={`Genomic-constraint Z-score. ${MOCK_TIP}`}>
          Z = — · needs live data
        </span>
        <span style={{ fontSize: 11, color: 'var(--ink-4)' }}>
          LOEUF / pLI in <span style={{ fontWeight: 600 }}>Gene &amp; locus</span> below.
        </span>
      </div>
    </div>
  )
}
