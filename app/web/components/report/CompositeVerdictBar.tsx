import type { ComputationalPredictorRow } from '@/lib/backend'
import {
  StackedCountBar,
  type RampVerdict,
  type StackedCountSegment,
} from '@/components/ui/StackedCountBar'

interface CompositeVerdictBarProps {
  predictors?: ComputationalPredictorRow[] | null
}

const RAMP_ORDER: RampVerdict[] = [
  'Pathogenic',
  'Likely pathogenic',
  'VUS',
  'Likely benign',
  'Benign',
]

export function CompositeVerdictBar({ predictors }: CompositeVerdictBarProps) {
  // AM filtered at render per [[project_alphamissense_plan]].
  const visible = (predictors ?? []).filter((p) => p.name !== 'AlphaMissense')
  const totalEngines = visible.length

  const counts: Record<RampVerdict, number> = {
    'Pathogenic': 0,
    'Likely pathogenic': 0,
    'VUS': 0,
    'Likely benign': 0,
    'Benign': 0,
  }
  let calibratedCount = 0
  for (const row of visible) {
    const bucket = row.calibration_bucket
    if (bucket && bucket in counts) {
      counts[bucket] += 1
      calibratedCount += 1
    }
  }

  if (totalEngines === 0) return null

  const segments: StackedCountSegment[] = RAMP_ORDER
    .filter((verdict) => counts[verdict] > 0)
    .map((verdict) => ({ verdict, count: counts[verdict] }))

  const ariaParts = segments.map((s) => `${s.verdict} ${s.count}`).join(', ')
  const ariaLabel =
    calibratedCount === 0
      ? `${totalEngines} engine${totalEngines === 1 ? '' : 's'}, none with published calibration`
      : `Composite calibrated verdict: ${ariaParts}; ${calibratedCount} of ${totalEngines} engines calibrated`

  return (
    <div style={{ marginBottom: 16 }}>
      <StackedCountBar segments={segments} height={14} ariaLabel={ariaLabel} />
      <div
        style={{
          display: 'flex',
          gap: 14,
          marginTop: 5,
          fontFamily: 'var(--mono)',
          fontSize: 10.5,
          color: 'var(--ink-4)',
          alignItems: 'baseline',
        }}
      >
        {segments.map((s) => (
          <span key={s.verdict}>
            {s.verdict} <span style={{ color: 'var(--ink-2)' }}>{s.count}</span>
          </span>
        ))}
        <span style={{ marginLeft: 'auto' }}>
          {calibratedCount} of {totalEngines} engine{totalEngines === 1 ? '' : 's'} calibrated
        </span>
      </div>
    </div>
  )
}
