export interface ChatChunk {
  text: string
}

export async function* streamChat(
  runId: string,
  question: string,
  signal?: AbortSignal,
): AsyncGenerator<string> {
  const res = await fetch(`/api/v1/runs/${runId}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
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

export async function sendChat(
  runId: string,
  question: string,
  signal?: AbortSignal,
): Promise<string> {
  const parts: string[] = []
  for await (const chunk of streamChat(runId, question, signal)) {
    parts.push(chunk)
  }
  return parts.join('')
}
