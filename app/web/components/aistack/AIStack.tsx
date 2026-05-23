import { EvidenceSummary } from './EvidenceSummary'
import { AskEamos } from './AskEamos'
import type { ReportPayload } from '@/lib/backend'

interface AIStackProps {
  payload: ReportPayload
  runId: string | null
  contextLabel?: string
}

export function AIStack({ payload, runId, contextLabel }: AIStackProps) {
  return (
    <div className="mb-4">
      <EvidenceSummary payload={payload} />
      <AskEamos runId={runId} contextLabel={contextLabel} />
    </div>
  )
}
