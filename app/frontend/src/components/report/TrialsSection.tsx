import { Card } from '@/components/ui/Card'
import type { ReportPayload } from '@/lib/backend'

interface TrialsSectionProps {
  payload: ReportPayload
  number?: number
}

export function TrialsSection({ payload, number }: TrialsSectionProps) {
  const text = payload.therapeutic_landscape?.trim()
  if (!text) return null

  return (
    <Card number={number} title="Active trials & approved therapies" meta="ClinicalTrials.gov">
      <p
        style={{
          margin: 0,
          fontSize: 13.5,
          lineHeight: 1.65,
          color: 'var(--ink-2)',
        }}
      >
        {text}
      </p>
    </Card>
  )
}
