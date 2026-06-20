import type { ReactNode } from 'react'
import { IconSparkle } from '@/components/icons/Icon'
import type { WorkbenchTool } from '@/lib/backend'
import { AskEamos } from '@/components/aistack/AskEamos'
import { streamWorkbenchChat } from '@/lib/chat'
import { ToolIcon } from './ToolIcon'

/**
 * Tool-scoped Ask-Eamos rail surface for the Workbench. Same chrome /report,
 * /compare and /paper use (sparkle strip + AskEamos shell, work-rail.css
 * `.wr-ai-*`), but the assistant is scoped to the *active tool*: a Primer-only
 * context when Primer is selected, CRISPR-only for CRISPR, and so on. Selecting
 * the tool IS the context boundary — it keeps the prompt window tight (less
 * bloat, lower hallucination) and gives the user one honest mental model: Eamos
 * answers about what you're looking at. A persistent "<tool> expert" scope pill
 * in the pinned strip keeps that state legible while you chat. Gated coming-soon
 * (NEXT_PUBLIC_AI_CHAT_ENABLED) exactly like the other surfaces, ready to light
 * up when the gateway is enabled.
 */
const AI_CHAT_ENABLED = process.env.NEXT_PUBLIC_AI_CHAT_ENABLED === 'true'

interface ToolAi {
  /** The persona the scope pill announces — "Primer expert", etc. */
  persona: string
  intro: string
  suggestions: string[]
}

const TOOL_AI: Record<WorkbenchTool, ToolAi> = {
  viewer: {
    persona: 'Sequence expert',
    intro:
      'Ask about this variant in its sequence context — the codon change, what’s conserved nearby, adjacent ClinVar calls, and how the edit reshapes the protein.',
    suggestions: [
      'Explain this variant’s consequence',
      'What’s conserved around this codon?',
      'Which nearby ClinVar variants matter?',
      'How does this change the protein?',
    ],
  },
  primer: {
    persona: 'Primer expert',
    intro:
      'Ask about this primer design — Tm balance, specificity, product size, and which pair to trust for Sanger or qPCR.',
    suggestions: ['Pick the safest pair', 'Explain specificity', 'Redesign for qPCR', 'Why this amplicon size?'],
  },
  crispr: {
    persona: 'CRISPR expert',
    intro:
      'Ask about this guide + repair design — on-target efficiency, off-target risk, PAM choice, and the HDR / ssODN strategy.',
    suggestions: ['Pick the safest guide', 'Explain off-target risk', 'HDR design rationale', 'Why this PAM-blocking edit?'],
  },
  align: {
    persona: 'Alignment expert',
    intro:
      'Ask about this alignment — mismatches, indels, read orientation, and how the trace supports or refutes the intended edit.',
    suggestions: [
      'Summarise the mismatches',
      'Is this read forward or reverse?',
      'Does the trace support the edit?',
      'Explain the indel pattern',
    ],
  },
  compare: {
    persona: 'Comparator expert',
    intro: 'Ask about the variants being compared — what differs and why it matters.',
    suggestions: ['Which differs most?', 'Summarise the contrast'],
  },
}

export function WorkbenchAiPanel({
  tool,
  gene,
  cdna,
}: {
  tool: WorkbenchTool
  gene: string
  cdna: string
}): ReactNode {
  const cfg = TOOL_AI[tool]
  const ctx = `${gene} · ${cdna}`
  return (
    <div className="wr-ai-stack">
      <header className="wr-ai-strip wb-ai-strip">
        <div className="wb-ai-strip-row">
          <span className="wr-ai-strip-mark" aria-hidden>
            <IconSparkle size={15} />
          </span>
          <span className="wr-ai-strip-title">Ask Eamos</span>
          {!AI_CHAT_ENABLED && <span className="wr-ai-strip-soon">Coming soon</span>}
          <span className="wr-ai-strip-ctx">{ctx}</span>
        </div>
        <div className="wb-ai-strip-row">
          <span
            className="wr-ai-scope"
            title={`Eamos is scoped to the ${cfg.persona.replace(' expert', '')} tool — switch tools to change its context`}
          >
            <span className="wr-ai-scope-ic" aria-hidden>
              <ToolIcon tool={tool} />
            </span>
            {cfg.persona}
          </span>
          <span className="wr-ai-scope-note">context: this tool only</span>
        </div>
      </header>
      <AskEamos
        enabled={AI_CHAT_ENABLED}
        // Scoped to the active tool only — selecting the tool IS the context
        // boundary (no report payload reaches this surface).
        stream={(question, history, signal) =>
          streamWorkbenchChat({ active_tool: tool }, question, history, signal)
        }
        suggestions={cfg.suggestions}
        intro={<p style={{ margin: 0, fontSize: 13, lineHeight: 1.6, color: 'var(--ink-2)' }}>{cfg.intro}</p>}
      />
    </div>
  )
}
