import { createClient } from '@/utils/supabase/client'
import type {
  BatchCreateRequest,
  BatchCreateResponse,
  BatchJob,
  BatchJobQuery,
  BatchJobStatus,
  BatchResult,
  BatchUploadResponse,
  WorkflowRunV1,
} from './backend'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''
const DEFAULT_BATCH_PAGE_LIMIT = 200
const DEFAULT_BATCH_POLL_INTERVAL_MS = 1000
const DEFAULT_BATCH_MAX_POLLS = 720
const BATCH_SIGN_IN_MESSAGE = 'Sign in to run Batch variant annotation.'

export type BatchRequestErrorCode =
  | 'auth_required'
  | 'auth_expired'
  | 'not_found'
  | 'rate_limited'
  | 'validation'
  | 'unavailable'
  | 'request_failed'

export class BatchRequestError extends Error {
  readonly status?: number
  readonly code: BatchRequestErrorCode

  constructor(message: string, opts: { status?: number; code: BatchRequestErrorCode }) {
    super(message)
    this.name = 'BatchRequestError'
    this.status = opts.status
    this.code = opts.code
    Object.setPrototypeOf(this, BatchRequestError.prototype)
  }
}

export interface BatchRunPage {
  runs: WorkflowRunV1[]
  nextCursor: string | null
  total: number | null
}

export interface BatchExport {
  filename: string
  mediaType: string
  content: string
}

const OPAQUE_RUN_ID = /^[A-Za-z0-9][A-Za-z0-9._~-]{0,127}$/

async function accessToken(): Promise<string> {
  const { data, error } = await createClient().auth.getSession()
  const token = data.session?.access_token
  if (error || !token) throw new BatchRequestError(BATCH_SIGN_IN_MESSAGE, { code: 'auth_required' })
  return token
}

async function authorizationHeader(): Promise<{ Authorization: string }> {
  return { Authorization: `Bearer ${await accessToken()}` }
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    if (response.status === 401) {
      throw new BatchRequestError('Your session expired. Sign in again to run Batch annotation.', {
        status: response.status,
        code: 'auth_expired',
      })
    }
    throw new BatchRequestError(defaultErrorMessage(response.status), {
      status: response.status,
      code: errorCodeForStatus(response.status),
    })
  }
  return (await response.json()) as T
}

function errorCodeForStatus(status: number): BatchRequestErrorCode {
  if (status === 404) return 'not_found'
  if (status === 429) return 'rate_limited'
  if (status === 422 || status === 400 || status === 413) return 'validation'
  if (status === 503) return 'unavailable'
  return 'request_failed'
}

function defaultErrorMessage(status: number): string {
  if (status === 404) return 'Batch run was not found.'
  if (status === 429) return 'Batch run limit reached. Wait a moment, then try again.'
  if (status === 422 || status === 400 || status === 413) return 'Batch input could not be accepted.'
  if (status === 503) return 'Batch service is unavailable.'
  return 'Batch request failed. Retry in a moment.'
}

export async function createBatch(input: BatchCreateRequest): Promise<BatchCreateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/batch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(await authorizationHeader()),
    },
    body: JSON.stringify(input),
  })
  return await parseResponse<BatchCreateResponse>(response)
}

export async function getBatchJob(jobId: string, opts?: BatchJobQuery): Promise<BatchJob> {
  const params = new URLSearchParams()
  if (opts?.limit != null) params.set('limit', String(opts.limit))
  if (opts?.cursor != null) params.set('cursor', opts.cursor)
  const qs = params.size > 0 ? `?${params.toString()}` : ''
  const response = await fetch(`${API_BASE_URL}/api/v1/batch/${encodeRunId(jobId)}${qs}`, {
    headers: await authorizationHeader(),
  })
  return parseResponse<BatchJob>(response)
}

export async function listBatchRuns(opts: {
  limit?: number
  cursor?: string | null
  signal?: AbortSignal
} = {}): Promise<BatchRunPage> {
  const params = new URLSearchParams({ limit: String(opts.limit ?? 20) })
  if (opts.cursor) params.set('cursor', opts.cursor)
  const response = await fetch(`${API_BASE_URL}/api/v1/batch/runs?${params.toString()}`, {
    headers: await authorizationHeader(),
    signal: opts.signal,
  })
  const runs = await parseResponse<WorkflowRunV1[]>(response)
  const totalHeader = response.headers.get('X-Total-Count')
  const total = totalHeader == null ? null : Number.parseInt(totalHeader, 10)
  return {
    runs,
    nextCursor: response.headers.get('X-Next-Cursor'),
    total: total != null && Number.isFinite(total) ? total : null,
  }
}

export async function cancelBatchRun(runId: string): Promise<WorkflowRunV1> {
  const response = await fetch(`${API_BASE_URL}/api/v1/batch/${encodeRunId(runId)}/cancel`, {
    method: 'POST',
    headers: await authorizationHeader(),
  })
  return parseResponse<WorkflowRunV1>(response)
}

export async function deleteBatchRun(runId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/batch/${encodeRunId(runId)}`, {
    method: 'DELETE',
    headers: await authorizationHeader(),
  })
  if (!response.ok) await parseResponse<unknown>(response)
}

export async function exportBatchRun(
  runId: string,
  format: 'tsv' | 'manifest',
): Promise<BatchExport> {
  const params = new URLSearchParams({ format })
  const response = await fetch(
    `${API_BASE_URL}/api/v1/batch/${encodeRunId(runId)}/export?${params.toString()}`,
    { headers: await authorizationHeader() },
  )
  if (!response.ok) await parseResponse<unknown>(response)
  const fallbackName = format === 'tsv' ? 'eamos-batch.tsv' : 'eamos-batch-manifest.json'
  return {
    filename: safeAttachmentFilename(response.headers.get('Content-Disposition')) ?? fallbackName,
    mediaType: response.headers.get('Content-Type') ?? (format === 'tsv' ? 'text/tab-separated-values' : 'application/json'),
    content: await response.text(),
  }
}

function encodeRunId(runId: string): string {
  const normalized = runId.trim()
  if (!OPAQUE_RUN_ID.test(normalized)) {
    throw new BatchRequestError('This Batch run link is invalid.', { code: 'validation' })
  }
  return encodeURIComponent(normalized)
}

function safeAttachmentFilename(contentDisposition: string | null): string | null {
  if (!contentDisposition) return null
  const match = /filename="?([^";]+)"?/i.exec(contentDisposition)
  if (!match) return null
  const name = match[1].trim().replace(/[^A-Za-z0-9._-]/g, '_')
  return name && name !== '.' && name !== '..' ? name.slice(0, 160) : null
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
    if (opts?.shouldContinue && !opts.shouldContinue()) {
      throw new Error('Batch polling was cancelled')
    }
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
    if (opts?.shouldContinue && !opts.shouldContinue()) {
      throw new Error('Batch result collection was cancelled')
    }
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
    headers: await authorizationHeader(),
    body: formData,
  })
  return parseResponse<BatchUploadResponse>(response)
}
