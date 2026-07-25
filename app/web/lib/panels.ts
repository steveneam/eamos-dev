import type { Panel, PanelResolveRequest, PanelSummary } from './backend'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''

export type PanelRequestErrorCode = 'not_found' | 'validation' | 'unavailable' | 'request_failed'

/**
 * Safe, presentation-ready failure from the panel API boundary. Response bodies
 * are deliberately not copied into this error: a gene panel drives which
 * variants a run reports on, so a failure must surface as an explicit
 * unavailable state rather than as text that could read like panel content.
 */
export class PanelRequestError extends Error {
  readonly code: PanelRequestErrorCode
  readonly status?: number

  constructor(message: string, options: { code: PanelRequestErrorCode; status?: number }) {
    super(message)
    this.name = 'PanelRequestError'
    this.code = options.code
    this.status = options.status
    Object.setPrototypeOf(this, PanelRequestError.prototype)
  }
}

function panelErrorForStatus(status: number): PanelRequestError {
  if (status === 404) return new PanelRequestError('That gene panel was not found.', { code: 'not_found', status })
  if (status === 422) {
    return new PanelRequestError('That panel request was not valid.', { code: 'validation', status })
  }
  if (status === 503) {
    return new PanelRequestError('The panel service is unavailable.', { code: 'unavailable', status })
  }
  return new PanelRequestError('The panel request failed.', { code: 'request_failed', status })
}

/** Wraps transport failures so a dropped connection cannot be mistaken for an
 *  empty or successful catalogue. */
async function requestPanels<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init)
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new PanelRequestError('The panel service could not be reached.', { code: 'unavailable' })
  }
  if (!response.ok) throw panelErrorForStatus(response.status)
  return (await response.json()) as T
}

export async function getPanels(): Promise<PanelSummary[]> {
  const data = await requestPanels<{ panels: PanelSummary[] }>('/api/v1/panels')
  return data.panels
}

export async function getPanel(slug: string): Promise<Panel> {
  return requestPanels<Panel>(`/api/v1/panels/${encodeURIComponent(slug)}`)
}

export async function resolvePanel(input: PanelResolveRequest): Promise<Panel> {
  return requestPanels<Panel>('/api/v1/panels/resolve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}
