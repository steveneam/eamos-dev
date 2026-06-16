import { AskEamos } from '@/components/aistack/AskEamos'
import { IconSparkle } from '@/components/icons/Icon'

/**
 * Ask-Eamos rail surface for the Batch cohort — the same chrome /report uses
 * (sparkle strip + chat shell, work-rail.css `.wr-ai-*`), cohort-flavoured. The
 * chat is gated coming-soon (NEXT_PUBLIC_AI_CHAT_ENABLED) exactly like /report,
 * so this is the consistent rail-head toggle target, ready to light up when the
 * gateway is enabled. Mirrors AIStack but with a cohort intro (no report payload).
 */
const AI_CHAT_ENABLED = process.env.NEXT_PUBLIC_AI_CHAT_ENABLED === 'true'

const COHORT_SUGGESTIONS = [
  'Which variants are most actionable?',
  'Summarise the pathogenic findings',
  'Which panel genes had no variants?',
  'Group these by gene and significance',
]

export function CompareAiPanel({ count, source }: { count: number; source?: string }) {
  const ctx = count > 0 ? `${count} variant${count === 1 ? '' : 's'}${source ? ` · ${source}` : ''}` : undefined
  return (
    <div className="wr-ai-stack">
      <header className="wr-ai-strip">
        <span className="wr-ai-strip-mark" aria-hidden>
          <IconSparkle size={15} />
        </span>
        <span className="wr-ai-strip-title">Ask Eamos</span>
        {!AI_CHAT_ENABLED && <span className="wr-ai-strip-soon">Coming soon</span>}
        {ctx && <span className="wr-ai-strip-ctx">{ctx}</span>}
      </header>
      <AskEamos
        enabled={AI_CHAT_ENABLED}
        suggestions={COHORT_SUGGESTIONS}
        intro={
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.6, color: 'var(--ink-2)' }}>
            Ask about this cohort — I’ll be able to surface the actionable variants, summarise the
            classification mix, and flag panel genes with no hits, all grounded in the lookup evidence.
          </p>
        }
      />
    </div>
  )
}
