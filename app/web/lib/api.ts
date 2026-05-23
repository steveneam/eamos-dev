import type { LookupRequest, LookupResponse } from './backend'

// Variant Evidence Report → FastAPI. Same-origin by default (empty base):
// next.config.ts rewrites `/api/*` to the FastAPI dev server, so no CORS.
// Set NEXT_PUBLIC_API_BASE_URL to an absolute origin to call a remote backend.
//
// Scope note: this is the lookup subset only. The Vite app's api.ts also held
// the /runs auth helpers and Workbench tool calls (primer/crispr/tide/viewer);
// those surfaces stay in the Vite app and are intentionally omitted here.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Request failed with status ${response.status}`)
  }

  return (await response.json()) as T
}

export async function variantLookup(payload: LookupRequest): Promise<LookupResponse> {
  // One retry with backoff on transient failure only: network errors
  // (fetch throws TypeError) and 5xx. 4xx is a terminal client error — never
  // retried (it would just fail identically).
  let lastError: unknown
  for (let attempt = 0; attempt < 2; attempt++) {
    if (attempt > 0) await new Promise((resolve) => setTimeout(resolve, 600))
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/lookup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (response.status >= 500 && attempt === 0) {
        lastError = new Error(`Request failed with status ${response.status}`)
        continue
      }
      return parseResponse<LookupResponse>(response)
    } catch (err) {
      if (err instanceof TypeError && attempt === 0) {
        lastError = err
        continue
      }
      throw err
    }
  }
  throw lastError
}
