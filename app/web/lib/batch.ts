import type {
  BatchCreateRequest,
  BatchCreateResponse,
  BatchJob,
  BatchJobQuery,
  BatchJobStatus,
  BatchResult,
  BatchUploadResponse,
} from './backend'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''
const DEFAULT_BATCH_PAGE_LIMIT = 200
const DEFAULT_BATCH_POLL_INTERVAL_MS = 1000
const DEFAULT_BATCH_MAX_POLLS = 720

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Request failed with status ${response.status}`)
  }
  return (await response.json()) as T
}

export async function createBatch(input: BatchCreateRequest): Promise<BatchCreateResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
    return await parseResponse<BatchCreateResponse>(response)
  } catch {
    if (input.upload_ref) throw new Error('Batch upload job could not be created')
    // Mock-first: any failure → an immediate completed mock job; the
    // client-side table already reflects the scoped cohort.
    const n = input.variants?.length ?? 0
    return {
      job_id: `mock-job-${Date.now()}`,
      n_input: n,
      n_to_lookup: n,
      est_seconds: 0,
    }
  }
}

export async function getBatchJob(jobId: string, opts?: BatchJobQuery): Promise<BatchJob> {
  const params = new URLSearchParams()
  if (opts?.limit != null) params.set('limit', String(opts.limit))
  if (opts?.cursor != null) params.set('cursor', opts.cursor)
  const qs = params.size > 0 ? `?${params.toString()}` : ''
  const response = await fetch(
    `${API_BASE_URL}/api/v1/batch/${encodeURIComponent(jobId)}${qs}`,
  )
  return parseResponse<BatchJob>(response)
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function isTerminalBatchStatus(status: BatchJobStatus): boolean {
  return status === 'completed' || status === 'failed' || status === 'cancelled'
}

export async function pollBatchJob(
  jobId: string,
  opts?: {
    limit?: number
    intervalMs?: number
    maxPolls?: number
    onUpdate?: (job: BatchJob) => void
    shouldContinue?: () => boolean
  },
): Promise<BatchJob> {
  const limit = opts?.limit ?? DEFAULT_BATCH_PAGE_LIMIT
  const intervalMs = opts?.intervalMs ?? DEFAULT_BATCH_POLL_INTERVAL_MS
  const maxPolls = opts?.maxPolls ?? DEFAULT_BATCH_MAX_POLLS
  for (let i = 0; i < maxPolls; i++) {
    if (opts?.shouldContinue && !opts.shouldContinue()) throw new Error('Batch polling was cancelled')
    const job = await getBatchJob(jobId, { limit })
    opts?.onUpdate?.(job)
    if (isTerminalBatchStatus(job.status)) return job
    await sleep(intervalMs)
  }
  throw new Error('Batch lookup is still running')
}

export async function collectBatchResults(
  job: BatchJob,
  opts?: {
    limit?: number
    maxPages?: number
    shouldContinue?: () => boolean
  },
): Promise<BatchResult[]> {
  const limit = opts?.limit ?? DEFAULT_BATCH_PAGE_LIMIT
  const maxPages = opts?.maxPages ?? 50
  const collected = [...job.results]
  let cursor = job.page?.next_cursor ?? null
  for (let guard = 0; cursor && guard < maxPages; guard++) {
    if (opts?.shouldContinue && !opts.shouldContinue()) throw new Error('Batch result collection was cancelled')
    const page = await getBatchJob(job.job_id, { limit, cursor })
    collected.push(...page.results)
    cursor = page.page?.next_cursor ?? null
  }
  return collected
}

export async function uploadBatch(file: File): Promise<BatchUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await fetch(`${API_BASE_URL}/api/v1/batch/uploads`, {
    method: 'POST',
    body: formData,
  })
  return parseResponse<BatchUploadResponse>(response)
}
