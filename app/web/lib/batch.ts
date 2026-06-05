import type { BatchCreateRequest, BatchCreateResponse, BatchJob, BatchJobQuery, BatchUploadResponse } from './backend'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''

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

export async function uploadBatch(file: File): Promise<BatchUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await fetch(`${API_BASE_URL}/api/v1/batch/uploads`, {
    method: 'POST',
    body: formData,
  })
  return parseResponse<BatchUploadResponse>(response)
}
