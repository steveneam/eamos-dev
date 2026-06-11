import type { ReportPayload } from '@/lib/backend'

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

/**
 * Streams the Ask-Eamos variant chat (docs/ai-gateway/plan.md): posts the report
 * payload + question (+ prior turns) to the variant-lookup chat endpoint, which
 * grounds the answer in an evidence-only bounded context and streams tokens back
 * as text/plain. Yields decoded token chunks as they arrive.
 */
export async function* streamReportChat(
  payload: ReportPayload,
  question: string,
  history: ReportChatTurn[] = [],
  signal?: AbortSignal,
): AsyncGenerator<string> {
  const res = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, variant_context: payload, history }),
    signal,
  })

  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`Chat request failed: ${res.status}${body ? ` — ${body}` : ''}`)
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
