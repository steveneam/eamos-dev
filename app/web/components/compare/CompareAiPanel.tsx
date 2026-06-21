import { AskEamos } from '@/components/aistack/AskEamos'
import { IconSparkle } from '@/components/icons/Icon'
import { streamBatchChat, type BatchChatScope } from '@/lib/chat'

/**
 * Ask-Eamos rail surface for the Batch cohort — the same chrome /report, /workbench
 * and /paper use (sparkle strip + chat shell, work-rail.css `.wr-ai-*`), cohort-
 * flavoured. Scoped to *this cohort's* bounded summary: the chat surfaces the
 * actionable variants, summarises the classification mix, and flags panel genes
 * with no hits, never re-annotating and never seeing the raw VCF (spec §5.5b). Gated
 * coming-soon (NEXT_PUBLIC_AI_CHAT_ENABLED) exactly like the others, so this is the
 * consistent Scope ⇄ Ask Eamos rail-head toggle target, ready to light up when the
 * gateway is enabled.
 */
const AI_CHAT_ENABLED = process.env.NEXT_PUBLIC_AI_CHAT_ENABLED === 'true'

const COHORT_SUGGESTIONS = [
  'Which variants are most actionable?',
  'Summarise the pathogenic findings',
  'Which panel genes had no variants?',
  'Group these by gene and significance',
]

export function CompareAiPanel({ batch }: { batch: BatchChatScope | null }) {
  const count = batch?.variant_count ?? 0
  const sources = batch?.sources ?? []
  const ctx =
    count > 0
      ? `${count} variant${count === 1 ? '' : 's'}${
          sources.length === 1
            ? ` · ${sources[0]}`
            : sources.length > 1
              ? ` · ${sources.length} sources`
              : ''
        }`
      : undefined
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
        // Scoped to this cohort's bounded summary only — no cohort loaded means no
        // sender (the shell stays its coming-soon/idle state).
        stream={
          batch
            ? (question, history, signal) => streamBatchChat(batch, question, history, signal)
            : undefined
        }
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
