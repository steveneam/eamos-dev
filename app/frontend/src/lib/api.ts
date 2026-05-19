import type {
  ApproveResult,
  ClinicianReviewPayload,
  CrisprRequest,
  CrisprResponse,
  DropResult,
  GeneViewerRequest,
  GeneViewerResponse,
  LookupRequest,
  LookupResponse,
  PrimerRequest,
  PrimerResponse,
  RunChatRequest,
  RunChatResponse,
  ReportDraftUpdatePayload,
  ReportKind,
  ReportUploadResponse,
  ReviewResult,
  RunRequest,
  RunResponse,
} from './backend'
import { CRISPR_SAMPLE } from './workbench/crispr-sample'
import { GENE_VIEWER_SAMPLE } from './workbench/gene-viewer-sample'
import { PRIMER_SAMPLE } from './workbench/primer-sample'
import {
  CRISPR_TIDE_SAMPLE,
  type CrisprTideResult,
} from './workbench/crispr-tide-sample'

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

// --- Legacy /runs auto demo session --------------------------------------
// The /runs patient-report pipeline (upload, run, review, approve, drop,
// chat, PDF) is auth-gated server-side. Eamos has no login surface, so we
// transparently provision one fixed demo session: log in — bootstrapping
// the demo account via /register the first time it doesn't exist — and
// attach the bearer token to gated calls. Non-gated calls (variant lookup,
// Workbench tools) are deliberately left untouched.
const RUNS_TOKEN_KEY = 'eamos_runs_token'
const DEMO_USERNAME = 'eamos-demo'
const DEMO_PASSWORD = 'eamos-demo-session'

let cachedToken: string | null = null

function getStoredToken(): string | null {
  if (cachedToken) return cachedToken
  try {
    cachedToken = localStorage.getItem(RUNS_TOKEN_KEY)
  } catch {
    cachedToken = null
  }
  return cachedToken
}

function storeToken(token: string) {
  cachedToken = token
  try {
    localStorage.setItem(RUNS_TOKEN_KEY, token)
  } catch {
    /* private mode / storage denied — the in-memory token still works */
  }
}

function clearToken() {
  cachedToken = null
  try {
    localStorage.removeItem(RUNS_TOKEN_KEY)
  } catch {
    /* ignore */
  }
}

async function requestToken(path: string): Promise<string | null> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: DEMO_USERNAME, password: DEMO_PASSWORD }),
  })
  if (!response.ok) return null
  const data = (await response.json()) as { access_token?: string }
  return data.access_token ?? null
}

// Log in to the demo account, bootstrapping it via /register the first time
// (fresh DB). A 409 register race just falls back to a second login.
async function provisionToken(): Promise<string> {
  let token = await requestToken('/api/v1/auth/login')
  if (!token) {
    token =
      (await requestToken('/api/v1/auth/register')) ??
      (await requestToken('/api/v1/auth/login'))
  }
  if (!token) {
    throw new Error(
      'Could not establish a demo session — the Eamos auth service is unavailable.',
    )
  }
  storeToken(token)
  return token
}

async function ensureToken(): Promise<string> {
  return getStoredToken() ?? (await provisionToken())
}

// fetch() with the demo bearer token attached. On a 401 (expired token, or
// the server DB was reset out from under a stored token) it re-provisions
// once and retries so the demo session is self-healing.
async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const withAuth = (t: string): RequestInit => ({
    ...init,
    headers: { ...(init.headers ?? {}), Authorization: `Bearer ${t}` },
  })
  let response = await fetch(`${API_BASE_URL}${path}`, withAuth(await ensureToken()))
  if (response.status === 401) {
    clearToken()
    response = await fetch(`${API_BASE_URL}${path}`, withAuth(await provisionToken()))
  }
  return response
}

export async function uploadReport(file: File, reportKind: ReportKind): Promise<ReportUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('report_kind', reportKind)

  const response = await authedFetch('/api/v1/reports/upload', {
    method: 'POST',
    body: formData,
  })

  return parseResponse<ReportUploadResponse>(response)
}

export async function createRun(payload: RunRequest): Promise<RunResponse> {
  const response = await authedFetch('/api/v1/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  return parseResponse<RunResponse>(response)
}

export async function getRun(runId: string): Promise<RunResponse> {
  const response = await authedFetch(`/api/v1/runs/${runId}`)
  return parseResponse<RunResponse>(response)
}

export async function reviewRun(runId: string, payload: ClinicianReviewPayload): Promise<ReviewResult> {
  const response = await authedFetch(`/api/v1/runs/${runId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  return parseResponse<ReviewResult>(response)
}

export async function approveRun(runId: string): Promise<ApproveResult> {
  const response = await authedFetch(`/api/v1/runs/${runId}/approve`, {
    method: 'POST',
  })

  return parseResponse<ApproveResult>(response)
}

export async function dropRun(runId: string, reviewNote?: string): Promise<DropResult> {
  const response = await authedFetch(`/api/v1/runs/${runId}/drop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ review_note: reviewNote || null }),
  })

  return parseResponse<DropResult>(response)
}

export async function updateRunReportPayload(runId: string, payload: ReportDraftUpdatePayload): Promise<RunResponse> {
  const response = await authedFetch(`/api/v1/runs/${runId}/report-payload`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  return parseResponse<RunResponse>(response)
}

export async function askRunChat(runId: string, payload: RunChatRequest): Promise<RunChatResponse> {
  const response = await authedFetch(`/api/v1/runs/${runId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  return parseResponse<RunChatResponse>(response)
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

/**
 * CRISPR gRNA design. Calls the existing `POST /api/v1/crispr` fixture
 * endpoint; if the backend is unreachable (offline dev / pixel-check) it
 * resolves with the bundled `CRISPR_SAMPLE` so the Workbench tool renders
 * identically with or without a server (mock-first, per
 * plans/crispr-integration.md §5). A reachable backend that errors still
 * surfaces the error — only transport failure falls back.
 */
export async function designGuides(payload: CrisprRequest): Promise<CrisprResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/crispr`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return await parseResponse<CrisprResponse>(response)
  } catch (err) {
    if (err instanceof TypeError) return CRISPR_SAMPLE // backend down → mock
    throw err
  }
}

/**
 * Sanger / qPCR / ARMS primer design. Calls the existing `POST /api/v1/primer`
 * fixture endpoint; if the backend is unreachable (offline dev / pixel-check)
 * it resolves with the bundled `PRIMER_SAMPLE` so the Workbench Primer tool
 * renders identically with or without a server (mock-first, per
 * plans/primer-integration.md §5). A reachable backend that errors still
 * surfaces the error (e.g. ARMS real-mode → structured 422
 * `primer_mode_arms`) — only transport failure falls back.
 */
export async function designPrimers(payload: PrimerRequest): Promise<PrimerResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/primer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return await parseResponse<PrimerResponse>(response)
  } catch (err) {
    if (err instanceof TypeError) return PRIMER_SAMPLE // backend down → mock
    throw err
  }
}

/**
 * Post-CRISPR TIDE editing-outcome analysis. The `POST /api/v1/crispr/tide`
 * endpoint + its contract are a gated Codex milestone
 * (plans/crispr-integration.md §7); until it lands this is mock-first
 * against `CRISPR_TIDE_SAMPLE` — any failure (endpoint absent / offline)
 * resolves with the sample so the Outcomes scaffold is exercisable now.
 */
export async function analyzeTide(
  controlFile: File,
  editedFile: File,
  cutSiteIndex: number,
): Promise<CrisprTideResult> {
  const formData = new FormData()
  formData.append('control_file', controlFile)
  formData.append('edited_file', editedFile)
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/crispr/tide?cut_site_index=${cutSiteIndex}`,
      { method: 'POST', body: formData },
    )
    return await parseResponse<CrisprTideResult>(response)
  } catch {
    return CRISPR_TIDE_SAMPLE // endpoint gated to Codex §7 → mock-first
  }
}

/**
 * Gene viewer payload for the Workbench sequence viewer. Calls the
 * `POST /api/v1/viewer` endpoint (Codex GV-001..GV-008); if the backend is
 * unreachable (offline dev / pixel-check) it resolves with the bundled
 * `GENE_VIEWER_SAMPLE` so the Workbench renders identically with or without
 * a server (mock-first, per plans/gene-viewer/plan.md GV-005/GV-006). A
 * reachable backend that errors still surfaces the error — only transport
 * failure falls back. The adapter (`gene-viewer-adapter.ts`) maps the
 * response into the renderer `GeneWindowData` shape.
 */
export async function getGeneViewer(
  payload: GeneViewerRequest,
): Promise<GeneViewerResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/viewer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return await parseResponse<GeneViewerResponse>(response)
  } catch (err) {
    if (err instanceof TypeError) return GENE_VIEWER_SAMPLE // backend down → mock
    throw err
  }
}

// The run PDF endpoint is auth-gated, so it can't be loaded via a bare
// `<object data=…>` / `<a href=…>` (those can't carry a bearer header).
// Fetch it as a blob with the demo session attached; callers turn it into
// an object URL for preview or download.
export async function fetchRunPdfBlob(runId: string): Promise<Blob> {
  const response = await authedFetch(`/api/v1/runs/${runId}/pdf`)
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `PDF request failed with status ${response.status}`)
  }

  return response.blob()
}

export async function downloadRunPdf(runId: string): Promise<Blob> {
  return fetchRunPdfBlob(runId)
}
