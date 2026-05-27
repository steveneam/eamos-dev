import type { ComputationalPredictorRow } from '@/lib/backend'
import { ClassificationBadge } from '@/components/ui/ClassificationBadge'

interface CalibratedInSilicoTableProps {
  predictors?: ComputationalPredictorRow[] | null
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

export function CalibratedInSilicoTable({ predictors }: CalibratedInSilicoTableProps) {
  // AlphaMissense filtered at render per [[project_alphamissense_plan]] —
  // contract may carry calibrated_* for AM, but display stays hidden.
  const rows = (predictors ?? []).filter((p) => p.name !== 'AlphaMissense')

  if (rows.length === 0) {
    return (
      <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: '0 0 18px' }}>
        No in-silico predictions available for this variant.
      </p>
    )
  }

  return (
    <div style={{ marginBottom: 18 }}>
      <div
        style={{
          fontSize: 10.5,
          fontWeight: 700,
          color: 'var(--ink-4)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          marginBottom: 10,
        }}
      >
        In-silico predictions
      </div>

      <div
        style={{
          border: '0.5px solid var(--line)',
          borderRadius: 'var(--r-md)',
          overflow: 'hidden',
        }}
      >
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          <thead>
            <tr>
              <th style={HEADER_CELL}>Engine</th>
              <th style={HEADER_CELL}>Calibrated label</th>
              <th style={{ ...HEADER_CELL, fontFamily: 'var(--mono)', textAlign: 'right' }}>Raw score</th>
              <th style={{ ...HEADER_CELL, fontFamily: 'var(--mono)', textAlign: 'right' }}>Threshold</th>
              <th style={HEADER_CELL}>Version</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const isLast = i === rows.length - 1
              const bucket = row.calibration_bucket ?? null
              const calibratedLabel = row.calibrated_label ?? null

              const cellStyle: React.CSSProperties = {
                ...BODY_CELL,
                borderBottom: isLast ? 'none' : BODY_CELL.borderBottom,
              }

              return (
                <tr key={`${row.name}-${i}`}>
                  <td style={cellStyle}>
                    <div style={{ fontWeight: 600, color: 'var(--ink-1)' }}>{displayName(row.name)}</div>
                    {row.source && row.source !== row.name && (
                      <div style={{ fontSize: 10.5, color: 'var(--ink-4)', marginTop: 2 }}>{row.source}</div>
                    )}
                  </td>
                  <td style={cellStyle}>
                    {bucket ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
                        <ClassificationBadge classification={bucket} />
                        {calibratedLabel && (
                          <span style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>{calibratedLabel}</span>
                        )}
                        {row.calibration_method && (
                          <span style={{ fontSize: 10.5, color: 'var(--ink-4)' }}>{row.calibration_method}</span>
                        )}
                      </div>
                    ) : (
                      <span style={{ fontSize: 11.5, color: 'var(--ink-4)', fontStyle: 'italic' }}>
                        No published calibration
                      </span>
                    )}
                  </td>
                  <td style={{ ...cellStyle, fontFamily: 'var(--mono)', textAlign: 'right' }}>
                    {formatScore(row.score)}
                  </td>
                  <td style={{ ...cellStyle, fontFamily: 'var(--mono)', textAlign: 'right', color: 'var(--ink-3)' }}>
                    {formatThreshold(row.threshold)}
                  </td>
                  <td style={{ ...cellStyle, fontSize: 11, color: 'var(--ink-4)' }}>
                    {row.version ?? '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
