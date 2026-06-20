import { AskEamos } from '@/components/aistack/AskEamos'
import { IconSparkle } from '@/components/icons/Icon'
import { streamPaperChat, type PaperChatScope } from '@/lib/chat'

/**
 * Ask-Eamos rail surface for Paper → Variants — the same chrome /report and
 * /compare use (sparkle strip + chat shell, work-rail.css `.wr-ai-*`), paper-
 * flavoured. Scoped to *this run's* resolved candidates: the chat adjudicates
 * "is this mention a real reported allele in this paper" (spec §8), never a
 * free-floating assistant. Gated coming-soon (NEXT_PUBLIC_AI_CHAT_ENABLED) exactly
 * like the others, so this is the consistent Library ⇄ Ask Eamos rail-head toggle
 * target, ready to light up when the gateway is enabled.
 */
const AI_CHAT_ENABLED = process.env.NEXT_PUBLIC_AI_CHAT_ENABLED === 'true'

const PAPER_SUGGESTIONS = [
  'Which mentions resolved to a clinical allele?',
  'Summarise the variants found in this paper',
  'Which are experimental constructs, not patient alleles?',
  'What sources back each candidate?',
]

export function PaperAiPanel({ paper }: { paper: PaperChatScope | null }) {
  const count = paper?.candidates.length ?? 0
  const sources = paper?.source_count ?? 0
  const ctx =
    count > 0
      ? `${count} candidate${count === 1 ? '' : 's'}${sources > 0 ? ` · ${sources} paper${sources === 1 ? '' : 's'}` : ''}`
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
        // Scoped to this run's resolved candidates only — no paper extracted yet
        // means no sender (the shell stays its coming-soon/idle state).
        stream={
          paper
            ? (question, history, signal) => streamPaperChat(paper, question, history, signal)
            : undefined
        }
        suggestions={PAPER_SUGGESTIONS}
        intro={
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.6, color: 'var(--ink-2)' }}>
            Ask about the extracted variants — I’ll be able to flag which mentions resolved to a
            clinical allele, which stayed experimental, and what evidence each candidate rests on, all
            grounded in the source-backed resolution.
          </p>
        }
      />
    </div>
  )
}
