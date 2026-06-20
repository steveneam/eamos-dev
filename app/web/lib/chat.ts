import { createClient } from '@/utils/supabase/client'
import type { ReportPayload, WorkbenchTool } from '@/lib/backend'

// next.config rewrites same-origin `/api/*` to the FastAPI backend (no CORS).
// Set NEXT_PUBLIC_API_BASE_URL to an absolute origin to call a remote backend.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''

export interface ChatChunk {
  text: string
}

export interface ReportChatTurn {
  role: 'user' | 'assistant'
  content: string
}

/** The Workbench scope a report-less chat is grounded in — the active tool and
 *  (optionally) the current selection. Mirrors the backend `WorkbenchContext`;
 *  `scratchpad` is server-defaulted so callers only send what they have. */
export interface WorkbenchChatScope {
  active_tool: WorkbenchTool
  selected_primer_pair?: number | null
  selected_guide?: number | null
}

/**
 * Shared transport for every Ask-Eamos surface: posts a scoped chat body to the
 * gateway endpoint and streams text/plain tokens back. Ask-Eamos requires login
 * (docs/ai-gateway/pre-launch-security.md) — the endpoint reaches the paid
 * gateway, so we attach the Supabase bearer token and the backend derives the
 * user from the JWT and rate-limits per user. Yields decoded chunks as they
 * arrive. The `body` carries the surface's scoped context (report or workbench).
 */
async function* postChatStream(
  body: Record<string, unknown>,
  signInMessage: string,
  signal?: AbortSignal,
): AsyncGenerator<string> {
  const { data, error: sessionError } = await createClient().auth.getSession()
  const accessToken = data.session?.access_token
  if (sessionError || !accessToken) {
    throw new Error(signInMessage)
  }

  const res = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
    signal,
  })

  if (res.status === 401) {
    throw new Error('Your session expired — sign in again to ask Eamos.')
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Chat request failed: ${res.status}${text ? ` — ${text}` : ''}`)
  }

  if (!res.body) throw new Error('No response body')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      if (chunk) yield chunk
    }
  } finally {
    reader.releaseLock()
  }
}

/**
 * Streams the Ask-Eamos variant chat (docs/ai-gateway/plan.md): grounds the
 * answer in the full report payload as an evidence-only bounded context. Used by
 * the /report (and /compare) rail.
 */
export function streamReportChat(
  payload: ReportPayload,
  question: string,
  history: ReportChatTurn[] = [],
  signal?: AbortSignal,
): AsyncGenerator<string> {
  return postChatStream(
    { question, variant_context: payload, history },
    'Sign in to ask Eamos about this variant.',
    signal,
  )
}

/**
 * Streams the Workbench-scoped Ask-Eamos chat: no report payload, grounded in
 * the active tool's context only (docs/ai-gateway/plan.md). Selecting the tool
 * IS the context boundary — keeps the prompt window tight and the assistant
 * honest about what it can see.
 */
export function streamWorkbenchChat(
  workbench: WorkbenchChatScope,
  question: string,
  history: ReportChatTurn[] = [],
  signal?: AbortSignal,
): AsyncGenerator<string> {
  return postChatStream({ question, workbench, history }, 'Sign in to ask Eamos.', signal)
}

/** One resolved Paper → Variants candidate, bounded for the chat scope. Mirrors
 *  the backend `PaperCandidateContext`: identity, resolution status, a short
 *  evidence quote, and which papers mentioned it — never the full paper body. */
export interface PaperCandidateScope {
  gene?: string | null
  hgvs?: string | null
  level?: string
  context?: string
  validation_status?: string
  validated?: boolean
  evidence_quote?: string | null
  source_support?: string[]
  papers?: string[]
}

/** The Paper → Variants scope a report-less chat is grounded in — this run's
 *  resolved candidates plus their source provenance. Mirrors the backend
 *  `PaperContext`. */
export interface PaperChatScope {
  candidates: PaperCandidateScope[]
  source_count: number
  sources?: string[]
}

/**
 * Streams the Paper-scoped Ask-Eamos chat (docs/ai-gateway-paper-variants/spec.md
 * §8): no report payload, grounded only in this paper's resolved candidates + their
 * evidence quotes + source provenance. The chat adjudicates "is this mention a real
 * reported allele in this paper", it doesn't re-extract.
 */
export function streamPaperChat(
  paper: PaperChatScope,
  question: string,
  history: ReportChatTurn[] = [],
  signal?: AbortSignal,
): AsyncGenerator<string> {
  return postChatStream({ question, paper, history }, 'Sign in to ask Eamos.', signal)
}
