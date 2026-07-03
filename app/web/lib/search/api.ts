import { createClient } from '@/utils/supabase/client'
import type { SearchDocType, SearchResponse } from '@/lib/backend'

const SEARCH_SIGN_IN_MESSAGE = 'Sign in to search Eamos.'
const AUTH_SESSION_TIMEOUT_MS = 3_000

export type SearchRequestErrorCode =
  | 'auth_required'
  | 'auth_expired'
  | 'rate_limited'
  | 'validation'
  | 'unavailable'
  | 'network'
  | 'request_failed'

export interface SearchQueryInput {
  query: string
  limit?: number
  docType?: SearchDocType
  runStatus?: string
  reviewStatus?: string
}

export class SearchRequestError extends Error {
  readonly status?: number
  readonly code: SearchRequestErrorCode
  readonly retryAfter?: string | null

  constructor(
    message: string,
    opts: { status?: number; code: SearchRequestErrorCode; retryAfter?: string | null },
  ) {
    super(message)
    this.name = 'SearchRequestError'
    this.status = opts.status
    this.code = opts.code
    this.retryAfter = opts.retryAfter ?? null
    Object.setPrototypeOf(this, SearchRequestError.prototype)
  }
}

async function accessToken(): Promise<string> {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    throw new SearchRequestError(SEARCH_SIGN_IN_MESSAGE, { status: 401, code: 'auth_required' })
  }
  const { data, error } = await withTimeout(
    createClient().auth.getSession(),
    AUTH_SESSION_TIMEOUT_MS,
  )
  const token = data.session?.access_token
  if (error || !token) {
    throw new SearchRequestError(SEARCH_SIGN_IN_MESSAGE, { status: 401, code: 'auth_required' })
  }
  return token
}

function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      reject(new SearchRequestError(SEARCH_SIGN_IN_MESSAGE, { status: 401, code: 'auth_required' }))
    }, timeoutMs)
    promise.then(
      (value) => {
        window.clearTimeout(timeout)
        resolve(value)
      },
      (error: unknown) => {
        window.clearTimeout(timeout)
        reject(error)
      },
    )
  })
}

function responseDetail(body: string): string | null {
  if (!body) return null
  try {
    const parsed = JSON.parse(body) as { detail?: unknown; message?: unknown }
    if (typeof parsed.detail === 'string') return parsed.detail
    if (Array.isArray(parsed.detail)) {
      const first = parsed.detail.find(
        (item): item is { msg: string } =>
          typeof item === 'object' &&
          item !== null &&
          'msg' in item &&
          typeof (item as { msg?: unknown }).msg === 'string',
      )
      return first?.msg ?? null
    }
    if (typeof parsed.message === 'string') return parsed.message
  } catch {
    return body.length <= 240 ? body : null
  }
  return null
}

function errorCodeForStatus(status: number): SearchRequestErrorCode {
  if (status === 401) return 'auth_expired'
  if (status === 429) return 'rate_limited'
  if (status === 400 || status === 422) return 'validation'
  if (status === 502 || status === 503 || status >= 500) return 'unavailable'
  return 'request_failed'
}

function defaultErrorMessage(status: number): string {
  if (status === 401) return 'Your session expired. Sign in again to search Eamos.'
  if (status === 429) return 'Search limit reached. Wait a moment, then try again.'
  if (status === 400 || status === 422) return 'Search query could not be accepted.'
  if (status === 502) return 'Search proxy could not reach the backend.'
  if (status === 503) return 'Search service is unavailable.'
  return `Search request failed with status ${status}`
}

async function parseSearchResponse(response: Response): Promise<SearchResponse> {
  if (!response.ok) {
    const body = await response.text().catch(() => '')
    throw new SearchRequestError(responseDetail(body) ?? defaultErrorMessage(response.status), {
      status: response.status,
      code: errorCodeForStatus(response.status),
      retryAfter: response.headers.get('retry-after'),
    })
  }
  return (await response.json()) as SearchResponse
}

export async function searchEamos(
  input: SearchQueryInput,
  init: { signal?: AbortSignal } = {},
): Promise<SearchResponse> {
  const query = input.query.trim()
  if (!query) return { query: input.query, results: [] }

  const params = new URLSearchParams({ q: query })
  if (input.limit != null) params.set('limit', String(input.limit))
  if (input.docType) params.set('doc_type', input.docType)
  if (input.runStatus) params.set('run_status', input.runStatus)
  if (input.reviewStatus) params.set('review_status', input.reviewStatus)

  try {
    const response = await fetch(`/api/v1/search?${params.toString()}`, {
      headers: {
        accept: 'application/json',
        Authorization: `Bearer ${await accessToken()}`,
      },
      cache: 'no-store',
      signal: init.signal,
    })
    return await parseSearchResponse(response)
  } catch (error) {
    if (error instanceof SearchRequestError) throw error
    if (error instanceof TypeError) {
      throw new SearchRequestError('Search backend could not be reached.', {
        code: 'network',
      })
    }
    throw error
  }
}
