import type {
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
  PublicationLiterature,
} from './backend'
import type { AlignApiResponseShape } from './workbench/alignment-pairwise'
import { GENE_VIEWER_SAMPLE } from './workbench/gene-viewer-sample'
import { PRIMER_SAMPLE } from './workbench/primer-sample'
import { CRISPR_SAMPLE } from './workbench/crispr-sample'
import { CRISPR_SSODN_SAMPLE } from './workbench/crispr-ssodn-sample'
import {
  OFFTARGET_SAMPLE,
  mockScreeningPrimers,
} from './workbench/crispr-offtarget-sample'
import { ALIGN_SAMPLE } from './workbench/align-sample'
import { CRISPR_TIDE_SAMPLE, type CrisprTideResult } from './workbench/crispr-tide-sample'

// Variant Evidence Report → FastAPI. Same-origin by default (empty base):
// next.config.ts rewrites `/api/*` to the FastAPI dev server, so no CORS.
// Set NEXT_PUBLIC_API_BASE_URL to an absolute origin to call a remote backend.
//
// Scope note: this carries the lookup + Workbench tool calls
// (primer/crispr/tide/viewer). The Vite app's /runs auth helpers stay in the
// Vite app and are intentionally omitted here.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Request failed with status ${response.status}`)
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
    if (attempt > 0) await new Promise((resolve) => setTimeout(resolve, 600))
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/lookup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: init.signal,
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

/**
 * Gene viewer payload for the Workbench sequence viewer. Calls
 * `POST /api/v1/viewer`; if the backend is unreachable it resolves with the
 * bundled `GENE_VIEWER_SAMPLE` for the default RPE65 request (mock-first).
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
    if (err instanceof TypeError && isDefaultGeneViewerPayload(payload)) {
      return GENE_VIEWER_SAMPLE
    }
    throw err
  }
}

function isDefaultGeneViewerPayload(payload: GeneViewerRequest): boolean {
  const gene = payload.gene.trim().toUpperCase()
  const cdna = payload.cdna.replace(/\s+/g, '')
  const transcript = payload.transcript?.trim()
  return (
    gene === GENE_VIEWER_SAMPLE.identity.gene &&
    cdna === GENE_VIEWER_SAMPLE.queried_variant.hgvs_c &&
    (!transcript || transcript === GENE_VIEWER_SAMPLE.identity.resolved_transcript)
  )
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
): Promise<LookupInitialSummaryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/lookup/summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return parseResponse<LookupInitialSummaryResponse>(response)
}

export async function fetchLookupSections(
  payload: LookupSectionFetchRequest,
  init: { signal?: AbortSignal } = {},
): Promise<LookupSectionFetchResponse> {
  let lastError: unknown
  for (let attempt = 0; attempt < 2; attempt += 1) {
    if (attempt > 0) await new Promise((resolve) => setTimeout(resolve, 600))
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/lookup/sections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: init.signal,
      })
      if (response.status >= 500 && attempt === 0) {
        const body = await response.text()
        lastError = new Error(body || `Request failed with status ${response.status}`)
        continue
      }
      return parseResponse<LookupSectionFetchResponse>(response)
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

export async function alignSequences(payload: {
  gene: string
  cdna: string
  user_sequence: string | null
  ab1_blob_base64: string | null
}): Promise<AlignApiResponseShape> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/align`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return await parseResponse<AlignApiResponseShape>(response)
  } catch (err) {
    if (err instanceof TypeError) return ALIGN_SAMPLE // backend down → mock
    throw err
  }
}

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

// The lab-order ssODN donor is a dedicated route (docs/crispr-ssodn/spec.md).
// It may not be deployed everywhere yet, so 404 (route absent) falls back to the
// bundled public sample the same as a TypeError (backend down). Real lab-accurate
// donors come from the live route; the sample renders the surface offline.
export async function designSsodn(
  payload: CrisprSsodnRequest,
): Promise<CrisprSsodnResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/crispr/ssodn`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (response.status === 404) return CRISPR_SSODN_SAMPLE // route not deployed → mock
    return await parseResponse<CrisprSsodnResponse>(response)
  } catch (err) {
    if (err instanceof TypeError) return CRISPR_SSODN_SAMPLE // backend down → mock
    throw err
  }
}

// The CRISPR off-target endpoints are new + backend-gated (mock-first per
// docs/crispr-offtarget-screening/spec.md). Until Codex's route is deployed the
// backend answers 404, so we treat 404 (route absent) the same as a TypeError
// (backend down): fall back to the bundled sample so the surface renders and
// self-heals once the endpoint lands. Real errors (400/422/500) still surface.
export async function enumerateOffTargets(
  payload: CrisprOffTargetRequest,
): Promise<CrisprOffTargetResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/crispr/offtargets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (response.status === 404) return OFFTARGET_SAMPLE // endpoint not deployed → mock
    return await parseResponse<CrisprOffTargetResponse>(response)
  } catch (err) {
    if (err instanceof TypeError) return OFFTARGET_SAMPLE // backend down → mock
    throw err
  }
}

export async function designScreeningPrimers(
  payload: CrisprScreeningPrimerRequest,
): Promise<CrisprScreeningPrimerResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/crispr/screening-primers`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
    )
    if (response.status === 404) return mockScreeningPrimers(payload) // endpoint not deployed → mock
    return await parseResponse<CrisprScreeningPrimerResponse>(response)
  } catch (err) {
    if (err instanceof TypeError) return mockScreeningPrimers(payload) // backend down → mock
    throw err
  }
}

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
    if (response.status === 404) return CRISPR_TIDE_SAMPLE // route absent -> sample
    return await parseResponse<CrisprTideResult>(response)
  } catch (err) {
    if (err instanceof TypeError) return CRISPR_TIDE_SAMPLE // backend down -> sample
    throw err
  }
}
