import {
  CLASS_ORDER,
  SBS_CLASSES,
  type CohortSummary as CohortSummaryData,
  type SbsClass,
  type VariantClass,
} from '@/lib/batch-summary'

/**
 * Cohort-at-a-glance panel for the batch results dashboard (spec §5.5b). A
 * headline classification distribution (P/LP/VUS/LB/B) plus the cohort's
 * variant-type, 6-class substitution spectrum, per-gene hit counts, and — when
 * a panel is active — panel coverage. The classification bar reads as all-grey
 * "Unclassified" until the lookup engine annotates the cohort; the variant-shape
 * cards populate from the parsed coordinates immediately.
 */

const CLASS_META: Record<VariantClass, { label: string; short: string; color: string }> = {
  // red → amber → warm-grey → light-teal → teal class ramp (matches the report).
  P: { label: 'Pathogenic', short: 'P', color: 'var(--err)' },
  LP: { label: 'Likely pathogenic', short: 'LP', color: 'var(--warn)' },
  VUS: { label: 'Uncertain (VUS)', short: 'VUS', color: '#a89f93' },
  LB: { label: 'Likely benign', short: 'LB', color: '#7bba9e' },
  B: { label: 'Benign', short: 'B', color: 'var(--teal-deep)' },
  unclassified: { label: 'Unclassified', short: '—', color: 'var(--line-2)' },
}

// Canonical COSMIC SBS-6 substitution palette — recognised by anyone reading a
// mutational spectrum (the black C>G muted slightly for the warm-white theme).
const SBS_COLOR: Record<SbsClass, string> = {
  'C>A': '#2ebaed',
  'C>G': '#2a2a2a',
  'C>T': '#d8352a',
  'T>A': '#b5b0a8',
  'T>C': '#9fcb57',
  'T>G': '#e6b8b5',
}

const CARD: React.CSSProperties = {
  background: 'var(--bg)',
  border: '0.5px solid var(--line)',
  borderRadius: 12,
  padding: '13px 15px',
}

const CAP: React.CSSProperties = {
  fontSize: 10.5,
  fontWeight: 600,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
  color: 'var(--ink-4)',
  margin: 0,
}

export function CohortSummary({
  summary,
  panelLabel,
}: {
  summary: CohortSummaryData
  panelLabel?: string
}) {
  const { total, classDist, classified, geneCounts, typeCounts, subSpectrum, subTotal, indelLengths, panel } =
    summary
  const indelMin = indelLengths.length ? Math.min(...indelLengths) : 0
  const indelMax = indelLengths.length ? Math.max(...indelLengths) : 0
  const indelRange = indelMin === indelMax ? `${indelMax} bp` : `${indelMin}–${indelMax} bp`

  return (
    <section
      aria-label="Cohort summary"
      style={{
        background: 'var(--bg-soft)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '16px 18px',
        marginBottom: 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12 }}>
        <h2 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 14, margin: 0, color: 'var(--ink)' }}>
          Cohort summary
        </h2>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-4)' }}>
          {total} variant{total === 1 ? '' : 's'}
        </span>
      </div>

      {/* Headline: classification distribution */}
      <div style={{ marginTop: 12 }}>
        <p style={{ ...CAP, marginBottom: 7 }}>Classification</p>
        <StackedBar classDist={classDist} total={total} />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 14px', marginTop: 9 }}>
          {CLASS_ORDER.filter((c) => classDist[c] > 0).map((c) => (
            <LegendChip key={c} cls={c} n={classDist[c]} />
          ))}
        </div>
        {classified === 0 && (
          <p style={{ fontSize: 11.5, lineHeight: 1.5, color: 'var(--ink-4)', margin: '8px 0 0' }}>
            Classifications populate once the lookup engine annotates the cohort — the variant-shape
            summaries below are computed from the parsed coordinates now.
          </p>
        )}
      </div>

      {/* Variant-shape grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
          gap: 12,
          marginTop: 14,
        }}
      >
        {/* Variant types */}
        <div style={CARD}>
          <p style={CAP}>Variant types</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginTop: 9 }}>
            <TypePill label="SNV" n={typeCounts.snv} />
            <TypePill label="Ins" n={typeCounts.ins} />
            <TypePill label="Del" n={typeCounts.del} />
            {typeCounts.mnv > 0 && <TypePill label="MNV" n={typeCounts.mnv} />}
          </div>
          {indelLengths.length > 0 && (
            <p style={{ fontSize: 11, color: 'var(--ink-4)', margin: '9px 0 0', fontFamily: 'var(--mono)' }}>
              {indelLengths.length} indel{indelLengths.length === 1 ? '' : 's'} · {indelRange}
            </p>
          )}
        </div>

        {/* Base-change spectrum (strand-collapsed 6-class single-base changes) */}
        <div style={CARD}>
          <p style={CAP}>Base changes</p>
          {subTotal > 0 ? (
            <SubSpectrum spectrum={subSpectrum} />
          ) : (
            <p style={{ fontSize: 11.5, color: 'var(--ink-4)', margin: '12px 0 0' }}>No single-base changes.</p>
          )}
        </div>

        {/* Panel coverage */}
        {panel && (
          <div style={CARD}>
            <p style={CAP}>Panel coverage</p>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 9 }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 18, fontWeight: 600, color: 'var(--ink)' }}>
                {panel.hit}
              </span>
              <span style={{ fontSize: 12, color: 'var(--ink-4)' }}>/ {panel.total} genes hit</span>
            </div>
            <div
              style={{
                position: 'relative',
                height: 6,
                borderRadius: 3,
                background: 'var(--line)',
                overflow: 'hidden',
                marginTop: 8,
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  width: `${panel.total ? (panel.hit / panel.total) * 100 : 0}%`,
                  background: 'var(--teal-deep)',
                  borderRadius: 3,
                }}
              />
            </div>
            <p style={{ fontSize: 10.5, color: 'var(--ink-5)', margin: '7px 0 0' }}>
              {panelLabel ? `${panelLabel} · ` : ''}
              {panel.total - panel.hit} not represented
            </p>
          </div>
        )}
      </div>

      {/* Per-gene counts */}
      {geneCounts.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <p style={CAP}>Genes</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
            {geneCounts.slice(0, 12).map((g) => (
              <span
                key={g.gene}
                style={{
                  display: 'inline-flex',
                  alignItems: 'baseline',
                  gap: 5,
                  padding: '3px 9px',
                  borderRadius: 7,
                  border: '0.5px solid var(--line-2)',
                  background: 'var(--bg)',
                  fontSize: 12,
                }}
              >
                <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{g.gene}</span>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--ink-4)' }}>×{g.n}</span>
              </span>
            ))}
            {geneCounts.length > 12 && (
              <span style={{ alignSelf: 'center', fontSize: 11.5, color: 'var(--ink-4)' }}>
                +{geneCounts.length - 12} more
              </span>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

function StackedBar({ classDist, total }: { classDist: Record<VariantClass, number>; total: number }) {
  return (
    <div
      role="img"
      aria-label={CLASS_ORDER.filter((c) => classDist[c] > 0)
        .map((c) => `${classDist[c]} ${CLASS_META[c].label}`)
        .join(', ')}
      style={{
        display: 'flex',
        height: 13,
        borderRadius: 7,
        overflow: 'hidden',
        background: 'var(--line)',
        gap: 1.5,
      }}
    >
      {total === 0
        ? null
        : CLASS_ORDER.filter((c) => classDist[c] > 0).map((c) => (
            <div
              key={c}
              title={`${CLASS_META[c].label}: ${classDist[c]}`}
              style={{
                flex: `${classDist[c]} 0 0`,
                minWidth: 3,
                background: CLASS_META[c].color,
              }}
            />
          ))}
    </div>
  )
}

function LegendChip({ cls, n }: { cls: VariantClass; n: number }) {
  const meta = CLASS_META[cls]
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11.5, color: 'var(--ink-3)' }}>
      <span aria-hidden style={{ width: 8, height: 8, borderRadius: 2, background: meta.color, flexShrink: 0 }} />
      <span style={{ fontWeight: 600, color: 'var(--ink-2)' }}>{meta.short === '—' ? 'Unclassified' : meta.short}</span>
      <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink-4)' }}>{n}</span>
    </span>
  )
}

function TypePill({ label, n }: { label: string; n: number }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'baseline',
        gap: 5,
        padding: '4px 10px',
        borderRadius: 8,
        border: '0.5px solid var(--line-2)',
        background: 'var(--bg-soft)',
      }}
    >
      <span style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>{n}</span>
    </span>
  )
}

function SubSpectrum({ spectrum }: { spectrum: Record<SbsClass, number> }) {
  const max = Math.max(1, ...SBS_CLASSES.map((c) => spectrum[c]))
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, marginTop: 10, height: 56 }}>
      {SBS_CLASSES.map((c) => {
        const n = spectrum[c]
        return (
          <div key={c} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--ink-3)', height: 12 }}>
              {n > 0 ? n : ''}
            </span>
            <div
              title={`${c}: ${n}`}
              style={{
                width: '100%',
                height: Math.max(2, (n / max) * 30),
                background: SBS_COLOR[c],
                borderRadius: '2px 2px 0 0',
                opacity: n > 0 ? 1 : 0.25,
              }}
            />
            <span style={{ fontFamily: 'var(--mono)', fontSize: 8.5, color: 'var(--ink-4)', whiteSpace: 'nowrap' }}>{c}</span>
          </div>
        )
      })}
    </div>
  )
}
