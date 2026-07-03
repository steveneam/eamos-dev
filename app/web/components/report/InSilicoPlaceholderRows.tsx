/**
 * InSilicoPlaceholderRows — stable skeleton/shimmer rows for the report's §2
 * in-silico predictor table (`CalibratedInSilicoTable`).
 *
 * The backend variant lookup takes ~9s (see ReportLoadingState). Without a
 * placeholder, this table pops from nothing to a full panel mid-load and
 * shifts the page layout with it. Rendering rows that mirror
 * CalibratedInSilicoTable's column layout up front lets the table reserve its
 * footprint immediately, so predictor data simply resolves in place once it
 * lands instead of causing a layout jump.
 *
 * Pure component, no hooks — reduced motion is handled entirely in CSS via
 * `prefers-reduced-motion`, matching the pattern in ReportLoadingState.
 */

interface InSilicoPlaceholderRowsProps {
  /** How many skeleton rows to render. Ignored when `labels` is supplied. */
  rows?: number
  /** Predictor names to anchor the left column (dimmed, real text) while the rest of the row shimmers. */
  labels?: string[]
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
  padding: '10px 12px',
  borderBottom: '0.5px solid var(--line)',
  verticalAlign: 'top',
}

function ShimmerBar({
  width = '100%',
  height = 12,
  radius = 4,
  style,
}: {
  width?: number | string
  height?: number
  radius?: number
  style?: React.CSSProperties
}) {
  return (
    <div
      aria-hidden="true"
      className="eamos-insilico-shimmer"
      style={{ width, height, borderRadius: radius, ...style }}
    />
  )
}

function PlaceholderRow({ label, isLast }: { label: string | null; isLast: boolean }) {
  const cell: React.CSSProperties = { ...BODY_CELL, borderBottom: isLast ? 'none' : BODY_CELL.borderBottom }
  return (
    <tr>
      <td style={cell}>
        {label ? (
          <span style={{ fontWeight: 600, color: 'var(--ink-4)' }}>{label}</span>
        ) : (
          <ShimmerBar width={130} height={13} />
        )}
      </td>
      <td style={cell}>
        <ShimmerBar width={54} height={11} />
      </td>
      <td style={cell}>
        <ShimmerBar width={86} height={18} radius={999} />
      </td>
      <td style={{ ...cell, textAlign: 'right' }}>
        <ShimmerBar width={38} height={11} style={{ marginLeft: 'auto' }} />
      </td>
      <td style={cell}>
        <ShimmerBar width="100%" height={10} radius={5} />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
          <ShimmerBar width={26} height={9} />
          <ShimmerBar width={26} height={9} />
        </div>
      </td>
    </tr>
  )
}

export function InSilicoPlaceholderRows({ rows = 6, labels }: InSilicoPlaceholderRowsProps) {
  const count = labels && labels.length > 0 ? labels.length : rows
  const items: (string | null)[] = Array.from({ length: count }, (_, i) => labels?.[i] ?? null)

  return (
    <div role="status" aria-busy="true" aria-label="Loading in-silico predictor scores" style={{ marginBottom: 18 }}>
      <div className="eamos-kicker" style={{ marginBottom: 6, opacity: 0.6 }}>
        In-silico predictions
      </div>
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
            {items.map((label, i) => (
              <PlaceholderRow key={label ?? i} label={label} isLast={i === items.length - 1} />
            ))}
          </tbody>
        </table>
      </div>

      <style>{`
        .eamos-insilico-shimmer {
          background: linear-gradient(90deg, var(--bg-soft2) 25%, var(--line) 37%, var(--bg-soft2) 63%);
          background-size: 400% 100%;
        }
        @media (prefers-reduced-motion: no-preference) {
          .eamos-insilico-shimmer {
            animation: eamos-insilico-shimmer-move 1.6s ease-in-out infinite;
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .eamos-insilico-shimmer {
            background: var(--bg-soft2);
          }
        }
        @keyframes eamos-insilico-shimmer-move {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  )
}
