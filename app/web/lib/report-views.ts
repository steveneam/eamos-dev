export interface VariantViewMetric {
  query_id: string
  view_count: number
  last_viewed?: string | null
}

const SESSION_KEY_PREFIX = 'eamos.report.view.v1:'
const SESSION_TTL_MS = 30 * 60 * 1000
const pending = new Map<string, Promise<VariantViewMetric | null>>()
const pendingReads = new Map<string, Promise<VariantViewMetric | null>>()

interface VariantViewResponse {
  variant?: VariantViewMetric
}

export async function recordReportView(queryId: string): Promise<VariantViewMetric | null> {
  const normalized = normalizeQueryId(queryId)
  if (!normalized) return null

  const cached = readRecentView(normalized)
  if (cached) return cached

  const key = normalized.toLowerCase()
  const existing = pending.get(key)
  if (existing) return existing

  const request = requestReportView(normalized, 'POST').finally(() => {
    pending.delete(key)
  })
  pending.set(key, request)
  return request
}

export async function getReportView(queryId: string): Promise<VariantViewMetric | null> {
  const normalized = normalizeQueryId(queryId)
  if (!normalized) return null

  const cached = readRecentView(normalized)
  if (cached) return cached

  const key = normalized.toLowerCase()
  const existing = pendingReads.get(key)
  if (existing) return existing

  const request = requestReportView(normalized, 'GET').finally(() => {
    pendingReads.delete(key)
  })
  pendingReads.set(key, request)
  return request
}

function normalizeQueryId(queryId: string): string | null {
  const normalized = queryId.trim()
  if (!normalized || normalized.length > 512) return null
  return normalized
}

async function requestReportView(queryId: string, method: 'GET' | 'POST'): Promise<VariantViewMetric | null> {
  try {
    const response = await fetch(`/api/v1/library/views/${encodeURIComponent(queryId)}`, {
      method,
      headers: { accept: 'application/json' },
      cache: 'no-store',
    })
    if (!response.ok) return null
    const body = (await response.json()) as VariantViewResponse
    const metric = body.variant ?? null
    if (metric) writeRecentView(queryId, metric)
    return metric
  } catch {
    return null
  }
}

function readRecentView(queryId: string): VariantViewMetric | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(`${SESSION_KEY_PREFIX}${queryId.toLowerCase()}`)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { savedAt?: unknown; metric?: unknown }
    if (typeof parsed.savedAt !== 'number' || Date.now() - parsed.savedAt > SESSION_TTL_MS) {
      window.sessionStorage.removeItem(`${SESSION_KEY_PREFIX}${queryId.toLowerCase()}`)
      return null
    }
    const metric = parsed.metric as Partial<VariantViewMetric> | null
    if (!metric || typeof metric.query_id !== 'string' || typeof metric.view_count !== 'number') {
      return null
    }
    return {
      query_id: metric.query_id,
      view_count: metric.view_count,
      last_viewed: typeof metric.last_viewed === 'string' ? metric.last_viewed : null,
    }
  } catch {
    return null
  }
}

function writeRecentView(queryId: string, metric: VariantViewMetric): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(
      `${SESSION_KEY_PREFIX}${queryId.toLowerCase()}`,
      JSON.stringify({ savedAt: Date.now(), metric }),
    )
  } catch {
    // Storage failures should never block report rendering.
  }
}
