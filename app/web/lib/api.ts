import type {
  AlignRequest,
  AlignReferenceRequest,
  AlignReferenceResponse,
  CrisprOffTargetRequest,
  CrisprOffTargetResponse,
  CrisprRequest,
  CrisprResponse,
  CrisprScreeningPrimerRequest,
  CrisprScreeningPrimerResponse,
  CrisprSsodnRequest,
  CrisprSsodnResponse,
  GeneViewerRequest,
  GeneViewerResponse,
  LookupInitialSummaryResponse,
  LookupRequest,
  LookupResponse,
  LookupSectionFetchRequest,
  LookupSectionFetchResponse,
  PrimerRequest,
  PrimerResponse,
  ProcessingDisclosureV1,
  PublicationLiterature,
} from './backend'
import type { AlignApiResponseShape } from './workbench/alignment-pairwise'
import type { CrisprTideResult } from './workbench/crispr-tide-sample'

// Variant Evidence Report → FastAPI. Same-origin by default (empty base):
// next.config.ts rewrites `/api/*` to the FastAPI dev server, so no CORS.
// Set NEXT_PUBLIC_API_BASE_URL to an absolute origin to call a remote backend.
//
// Scope note: this carries the lookup + Workbench tool calls
// (primer/crispr/tide/viewer). The Vite app's /runs auth helpers stay in the
// Vite app and are intentionally omitted here.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''

export class WorkbenchApiError extends Error {
  readonly status: number

  constructor(status: number) {
    const message = status === 400 || status === 422
      ? 'The request was rejected. Check the selected context and constraints.'
      : status === 401
        ? 'Sign in is required for this request.'
        : status === 403
          ? 'This request is not permitted.'
          : status === 404
            ? 'The requested service or record is unavailable.'
            : status === 409
              ? 'The request conflicts with newer state. Refresh and try again.'
              : status === 413
                ? 'The submitted input is too large.'
                : status === 429
                  ? 'Too many requests. Wait briefly and try again.'
                  : status >= 500
                    ? 'The service is temporarily unavailable.'
                    : `Request failed with status ${status}.`
    super(message)
    this.name = 'WorkbenchApiError'
    this.status = status
  }
}

interface ApiRequestOptions {
  signal?: AbortSignal
  accessToken?: string
}

function throwIfAborted(signal?: AbortSignal): void {
  if (!signal?.aborted) return
  throw signal.reason instanceof Error
    ? signal.reason
    : new DOMException('The request was cancelled.', 'AbortError')
}

function rethrowWorkbenchNetworkError(error: unknown, signal?: AbortSignal): never {
  if (error instanceof TypeError) {
    throwIfAborted(signal)
    throw new WorkbenchApiError(503)
  }
  throw error
}

type DisclosedWorkbenchResponse = {
  source_disclosure?: {
    source_status: string
    provider_id: string
    warnings?: string[]
  } | null
}

function requireOperationalWorkbenchResponse<T extends DisclosedWorkbenchResponse>(
  response: T,
  forbiddenProvider?: RegExp,
): T {
  const disclosure = response.source_disclosure
  const operational =
    disclosure?.source_status === 'source_backed' ||
    disclosure?.source_status === 'local_provider'
  const providerRejected = Boolean(
    disclosure && forbiddenProvider?.test(disclosure.provider_id),
  )
  const warningRejected = Boolean(
    disclosure?.warnings?.some((warning) => /fixture|fallback|mock|synthetic/i.test(warning)),
  )
  if (!operational || providerRejected || warningRejected) throw new WorkbenchApiError(503)
  return response
}

function requireSourceBackedViewer(response: GeneViewerResponse): GeneViewerResponse {
  const provenanceTokens = [
    ...response.provenance.sources.map((source) => source.name),
    ...response.provenance.warnings,
  ]
  if (provenanceTokens.some((token) => /fixture|fallback|mock|synthetic/i.test(token))) {
    throw new WorkbenchApiError(503)
  }
  if (response.provenance.sources.length === 0) throw new WorkbenchApiError(503)
  return response
}

function abortableDelay(milliseconds: number, signal?: AbortSignal): Promise<void> {
  throwIfAborted(signal)
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort)
      resolve()
    }, milliseconds)
    const onAbort = () => {
      clearTimeout(timer)
      reject(signal?.reason instanceof Error
        ? signal.reason
        : new DOMException('The request was cancelled.', 'AbortError'))
    }
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    // Backend bodies can contain provider diagnostics or echoed validation
    // input. UI errors expose only a bounded status-derived message.
    await response.body?.cancel().catch(() => undefined)
    throw new WorkbenchApiError(response.status)
  }

  return (await response.json()) as T
}

export async function variantLookup(
  payload: LookupRequest,
  init: { signal?: AbortSignal } = {},
): Promise<LookupResponse> {
  // One retry with backoff on transient failure only: network errors
  // (fetch throws TypeError) and 5xx. 4xx is a terminal client error — never
  // retried (it would just fail identically).
  let lastError: unknown
  for (let attempt = 0; attempt < 2; attempt++) {
    if (attempt > 0) await abortableDelay(600, init.signal)
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/lookup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: init.signal,
      })
      if (response.status >= 500 && attempt === 0) {
        await response.body?.cancel().catch(() => undefined)
        lastError = new WorkbenchApiError(response.status)
        continue
      }
      return parseResponse<LookupResponse>(response)
    } catch (err) {
      if (err instanceof TypeError && attempt === 0) {
        throwIfAborted(init.signal)
        lastError = err
        continue
      }
      throw err
    }
  }
  throw lastError
}

// Mirror of the backend `PublicationPageRequest` (app/backend/app/schemas/lookup.py).
// Local to the api layer because it's a request body the frontend constructs —
// the response shape (PublicationLiterature) is the shared contract type.
// GOTCHA (probed live): omit `transcript` and always send species:'human' —
// including the transcript returns total_count=0 from the live backend.
export interface PublicationPageRequest {
  gene: string
  cdna: string
  transcript?: string | null
  protein_change?: string | null
  species?: 'human' | 'mouse'
  scope?: 'variant' | 'gene'
  limit?: number
  offset?: number
}

/** Gene viewer payload for the Workbench sequence viewer. */
export async function getGeneViewer(
  payload: GeneViewerRequest,
  init: ApiRequestOptions = {},
): Promise<GeneViewerResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/viewer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: init.signal,
    })
    return requireSourceBackedViewer(await parseResponse<GeneViewerResponse>(response))
  } catch (error) {
    rethrowWorkbenchNetworkError(error, init.signal)
  }
}

export async function lookupPublications(
  payload: PublicationPageRequest,
): Promise<PublicationLiterature> {
  const response = await fetch(`${API_BASE_URL}/api/v1/lookup/publications`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return parseResponse<PublicationLiterature>(response)
}

export async function lookupSummary(
  payload: LookupRequest,
  init: ApiRequestOptions = {},
): Promise<LookupInitialSummaryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/lookup/summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: init.signal,
  })
  return parseResponse<LookupInitialSummaryResponse>(response)
}

export async function fetchLookupSections(
  payload: LookupSectionFetchRequest,
  init: { signal?: AbortSignal } = {},
): Promise<LookupSectionFetchResponse> {
  let lastError: unknown
  for (let attempt = 0; attempt < 2; attempt += 1) {
    if (attempt > 0) await abortableDelay(600, init.signal)
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/lookup/sections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: init.signal,
      })
      if (response.status >= 500 && attempt === 0) {
        await response.body?.cancel().catch(() => undefined)
        lastError = new WorkbenchApiError(response.status)
        continue
      }
      return parseResponse<LookupSectionFetchResponse>(response)
    } catch (err) {
      if (err instanceof TypeError && attempt === 0) {
        throwIfAborted(init.signal)
        lastError = err
        continue
      }
      throw err
    }
  }
  throw lastError
}

export async function designPrimers(
  payload: PrimerRequest,
  init: ApiRequestOptions = {},
): Promise<PrimerResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/primer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: init.signal,
    })
    return requireOperationalWorkbenchResponse(await parseResponse<PrimerResponse>(response))
  } catch (error) {
    rethrowWorkbenchNetworkError(error, init.signal)
  }
}

export async function alignSequences(
  payload: AlignRequest,
  init: ApiRequestOptions = {},
): Promise<AlignApiResponseShape> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/align`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: init.signal,
    })
    return requireOperationalWorkbenchResponse(await parseResponse<AlignApiResponseShape>(response))
  } catch (error) {
    rethrowWorkbenchNetworkError(error, init.signal)
  }
}

export async function resolveAlignReference(
  payload: AlignReferenceRequest,
  init: ApiRequestOptions = {},
): Promise<AlignReferenceResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/align/reference`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: init.signal,
    })
    return requireOperationalWorkbenchResponse(await parseResponse<AlignReferenceResponse>(response))
  } catch (error) {
    rethrowWorkbenchNetworkError(error, init.signal)
  }
}

export async function designGuides(
  payload: CrisprRequest,
  init: ApiRequestOptions = {},
): Promise<CrisprResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/crispr`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: init.signal,
    })
    return requireOperationalWorkbenchResponse(
      await parseResponse<CrisprResponse>(response),
      /deterministic|fixture|fallback|mock/i,
    )
  } catch (error) {
    rethrowWorkbenchNetworkError(error, init.signal)
  }
}

// The lab-order ssODN donor is a dedicated route. Missing providers and routes
// fail closed; design output is never replaced with illustrative client data.
export async function designSsodn(
  payload: CrisprSsodnRequest,
  init: ApiRequestOptions = {},
): Promise<CrisprSsodnResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/crispr/ssodn`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: init.signal,
    })
    return requireOperationalWorkbenchResponse(await parseResponse<CrisprSsodnResponse>(response))
  } catch (error) {
    rethrowWorkbenchNetworkError(error, init.signal)
  }
}

// Off-target execution is provider-gated. A missing route/provider is surfaced
// as unavailable and never replaced with deterministic sample hits.
export async function enumerateOffTargets(
  payload: CrisprOffTargetRequest,
  init: ApiRequestOptions = {},
): Promise<CrisprOffTargetResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/crispr/offtargets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: init.signal,
    })
    return requireOperationalWorkbenchResponse(await parseResponse<CrisprOffTargetResponse>(response))
  } catch (error) {
    rethrowWorkbenchNetworkError(error, init.signal)
  }
}

export async function designScreeningPrimers(
  payload: CrisprScreeningPrimerRequest,
  init: ApiRequestOptions = {},
): Promise<CrisprScreeningPrimerResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/crispr/screening-primers`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: init.signal,
      },
    )
    return requireOperationalWorkbenchResponse(
      await parseResponse<CrisprScreeningPrimerResponse>(response),
    )
  } catch (error) {
    rethrowWorkbenchNetworkError(error, init.signal)
  }
}

export async function analyzeTide(
  controlFile: File,
  editedFile: File,
  cutSiteIndex: number,
  init: ApiRequestOptions = {},
): Promise<CrisprTideResult> {
  const formData = new FormData()
  formData.append('control_file', controlFile)
  formData.append('edited_file', editedFile)
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/crispr/tide?cut_site_index=${cutSiteIndex}`,
      {
        method: 'POST',
        body: formData,
        signal: init.signal,
        headers: init.accessToken ? { Authorization: `Bearer ${init.accessToken}` } : undefined,
      },
    )
    return requireOperationalWorkbenchResponse(await parseResponse<CrisprTideResult>(response))
  } catch (error) {
    rethrowWorkbenchNetworkError(error, init.signal)
  }
}

export async function getWorkbenchTraceDisclosure(
  accessToken: string,
  init: ApiRequestOptions = {},
): Promise<ProcessingDisclosureV1> {
  const response = await fetch(`${API_BASE_URL}/api/v1/workbench/trace-disclosure`, {
    method: 'GET',
    signal: init.signal,
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return parseResponse<ProcessingDisclosureV1>(response)
}
