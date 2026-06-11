import { EvidenceSummary } from './EvidenceSummary'
import { AskEamos } from './AskEamos'
import { IconSparkle } from '@/components/icons/Icon'
import type { ReportPayload } from '@/lib/backend'

interface AIStackProps {
  payload: ReportPayload
  contextLabel?: string
}

// Capability flag (docs/ai-gateway/plan.md decision 3): prod stays "coming soon"
// until NEXT_PUBLIC_AI_CHAT_ENABLED is set, so the chat only goes live where verified.
const AI_CHAT_ENABLED = process.env.NEXT_PUBLIC_AI_CHAT_ENABLED === 'true'

/**
 * The Ask-Eamos rail surface (docs/ai-work-rail/spec.md): a pinned identity strip
 * (sparkle + "Ask Eamos" + the variant context chip), then the chat shell — the
 * deterministic evidence summary opens the thread, the composer is pinned at the
 * bottom (Claude / Grok layout). The chat streams via AskEamos and the Vercel AI
 * Gateway broker. Hovering or focusing the sparkle reveals the model provenance.
 * No nested card chrome — the rail is the surface. Styling: work-rail.css `.wr-ai-*`.
 */
export function AIStack({ payload, contextLabel }: AIStackProps) {
  return (
    <div className="wr-ai-stack">
      <header className="wr-ai-strip">
        <ModelProvenance />
        <span className="wr-ai-strip-title">Ask Eamos</span>
        {!AI_CHAT_ENABLED && <span className="wr-ai-strip-soon">Coming soon</span>}
        {contextLabel && <span className="wr-ai-strip-ctx">{contextLabel}</span>}
      </header>
      <AskEamos enabled={AI_CHAT_ENABLED} payload={payload} intro={<EvidenceSummary payload={payload} />} />
    </div>
  )
}

/**
 * The sparkle mark doubles as a provenance affordance: hover or keyboard-focus it
 * to see which model and gateway power the chat. Honest about the routing — Groq
 * is primary, Amazon Bedrock is the automatic failover, both via the Vercel AI
 * Gateway. Pure CSS hover/focus popover, no layout shift.
 */
function ModelProvenance() {
  return (
    <span
      className="wr-ai-prov"
      tabIndex={0}
      role="button"
      aria-label="Model details: Llama 3.3 70B via Vercel AI Gateway, Groq primary with Amazon Bedrock failover"
    >
      <span className="wr-ai-strip-mark" aria-hidden>
        <IconSparkle size={15} />
      </span>
      <span className="wr-ai-prov-pop" role="tooltip">
        <span className="wr-ai-prov-model">Llama 3.3 70B</span>
        <span className="wr-ai-prov-line">via Vercel AI Gateway</span>
        <span className="wr-ai-prov-route">
          <span className="wr-ai-prov-dot" aria-hidden />
          Groq primary
          <span className="wr-ai-prov-sep">·</span>
          Amazon Bedrock failover
        </span>
      </span>
      <style>{`
        .wr-ai-prov {
          position: relative;
          display: inline-flex;
          align-items: center;
          border-radius: var(--r-sm, 6px);
          cursor: help;
          outline: none;
        }
        .wr-ai-prov:focus-visible {
          box-shadow: 0 0 0 3px rgba(29,158,117,0.18);
        }
        .wr-ai-prov-pop {
          position: absolute;
          top: calc(100% + 8px);
          left: -4px;
          z-index: var(--z-popover, 60);
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 200px;
          padding: 10px 12px;
          border: 1px solid var(--line, #e4e4e0);
          border-radius: var(--r-md, 10px);
          background: var(--bg, #fff);
          box-shadow: var(--elev-2, 0 8px 24px rgba(20,20,16,0.12));
          opacity: 0;
          visibility: hidden;
          transform: translateY(-4px);
          transition: opacity 120ms ease, transform 120ms ease, visibility 120ms;
          pointer-events: none;
        }
        .wr-ai-prov:hover .wr-ai-prov-pop,
        .wr-ai-prov:focus-visible .wr-ai-prov-pop,
        .wr-ai-prov:focus-within .wr-ai-prov-pop {
          opacity: 1;
          visibility: visible;
          transform: translateY(0);
        }
        .wr-ai-prov-model {
          font-weight: 600;
          font-size: 12.5px;
          color: var(--ink, #16140f);
          letter-spacing: -0.01em;
        }
        .wr-ai-prov-line {
          font-size: 11.5px;
          color: var(--ink-3, #6b6b62);
        }
        .wr-ai-prov-route {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          margin-top: 3px;
          font-size: 11px;
          color: var(--ink-2, #44443c);
        }
        .wr-ai-prov-dot {
          width: 6px;
          height: 6px;
          border-radius: 999px;
          background: var(--teal, #1d9e75);
        }
        .wr-ai-prov-sep { color: var(--ink-4, #9a9a90); }
      `}</style>
    </span>
  )
}
