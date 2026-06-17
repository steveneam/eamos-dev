import { AskEamos } from '@/components/aistack/AskEamos'
import { IconSparkle } from '@/components/icons/Icon'

/**
 * Ask-Eamos rail surface for Paper → Variants — the same chrome /report and
 * /compare use (sparkle strip + chat shell, work-rail.css `.wr-ai-*`), paper-
 * flavoured. The chat is gated coming-soon (NEXT_PUBLIC_AI_CHAT_ENABLED) exactly
 * like the others, so this is the consistent Library ⇄ Ask Eamos rail-head
 * toggle target, ready to light up when the gateway is enabled.
 */
const AI_CHAT_ENABLED = process.env.NEXT_PUBLIC_AI_CHAT_ENABLED === 'true'

const PAPER_SUGGESTIONS = [
  'Which mentions resolved to a clinical allele?',
  'Summarise the variants found in this paper',
  'Which are experimental constructs, not patient alleles?',
  'What sources back each candidate?',
]

export function PaperAiPanel({ count, sources }: { count: number; sources: number }) {
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
