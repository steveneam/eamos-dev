import { EvidenceSummary } from './EvidenceSummary'
import { AskEamos } from './AskEamos'
import { IconSparkle } from '@/components/icons/Icon'
import type { ReportPayload } from '@/lib/backend'

interface AIStackProps {
  payload: ReportPayload
  runId: string | null
  contextLabel?: string
}

/**
 * The Ask-Eamos rail surface (docs/ai-work-rail/spec.md): a pinned identity strip
 * (sparkle + "Ask Eamos" + the variant context chip), then the chat shell — the
 * deterministic evidence summary opens the thread, the composer is pinned at the
 * bottom (Claude / Grok layout). The chat streams via AskEamos's existing scaffold
 * and lights up when the AI gateway lands. No nested card chrome — the rail is the
 * surface. Styling: work-rail.css `.wr-ai-*` / `.wr-chat-*`.
 */
export function AIStack({ payload, runId, contextLabel }: AIStackProps) {
  return (
    <div className="wr-ai-stack">
      <header className="wr-ai-strip">
        <span className="wr-ai-strip-mark" aria-hidden>
          <IconSparkle size={15} />
        </span>
        <span className="wr-ai-strip-title">Ask Eamos</span>
        {runId === null && <span className="wr-ai-strip-soon">Coming soon</span>}
        {contextLabel && <span className="wr-ai-strip-ctx">{contextLabel}</span>}
      </header>
      <AskEamos runId={runId} intro={<EvidenceSummary payload={payload} />} />
    </div>
  )
}
