import type {
  ApproveResult,
  ClinicianReviewPayload,
  DropResult,
  LookupRequest,
  LookupResponse,
  RunChatRequest,
  RunChatResponse,
  ReportDraftUpdatePayload,
  ReportKind,
  ReportUploadResponse,
  ReviewResult,
  RunRequest,
  RunResponse,
} from './backend'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') || 'http://127.0.0.1:8000'

export function buildRunPdfUrl(runId: string, cacheBust?: number) {
  const suffix = cacheBust ? `?v=${cacheBust}` : ''
  return `${API_BASE_URL}/api/v1/runs/${runId}/pdf${suffix}`
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Request failed with status ${response.status}`)
  }

  return (await response.json()) as T
}

export async function uploadReport(file: File, reportKind: ReportKind): Promise<ReportUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('report_kind', reportKind)

  const response = await fetch(`${API_BASE_URL}/api/v1/reports/upload`, {
    method: 'POST',
    body: formData,
  })

  return parseResponse<ReportUploadResponse>(response)
}

export async function createRun(payload: RunRequest): Promise<RunResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  return parseResponse<RunResponse>(response)
}

export async function getRun(runId: string): Promise<RunResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/runs/${runId}`)
  return parseResponse<RunResponse>(response)
}

export async function reviewRun(runId: string, payload: ClinicianReviewPayload): Promise<ReviewResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/runs/${runId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  return parseResponse<ReviewResult>(response)
}

export async function approveRun(runId: string): Promise<ApproveResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/runs/${runId}/approve`, {
    method: 'POST',
  })

  return parseResponse<ApproveResult>(response)
}

export async function dropRun(runId: string, reviewNote?: string): Promise<DropResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/runs/${runId}/drop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ review_note: reviewNote || null }),
  })

  return parseResponse<DropResult>(response)
}

export async function updateRunReportPayload(runId: string, payload: ReportDraftUpdatePayload): Promise<RunResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/runs/${runId}/report-payload`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  return parseResponse<RunResponse>(response)
}

export async function askRunChat(runId: string, payload: RunChatRequest): Promise<RunChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/runs/${runId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  return parseResponse<RunChatResponse>(response)
}

export async function variantLookup(payload: LookupRequest): Promise<LookupResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/lookup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return parseResponse<LookupResponse>(response)
}

export async function downloadRunPdf(runId: string): Promise<Blob> {
  const response = await fetch(buildRunPdfUrl(runId))
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `PDF request failed with status ${response.status}`)
  }

  return response.blob()
}
