import type { Panel, PanelResolveRequest, PanelSummary } from './backend'
import { MOCK_PANELS, getMockPanel, buildCustomPanel } from './panels.mock'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Request failed with status ${response.status}`)
  }
  return (await response.json()) as T
}

export async function getPanels(): Promise<PanelSummary[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/panels`)
    const data = await parseResponse<{ panels: PanelSummary[] }>(response)
    return data.panels
  } catch {
    // Mock-first: any failure (offline → TypeError, or a 404/5xx from a dev
    // server with no backend) degrades to the bundled catalogue.
    return MOCK_PANELS
  }
}

export async function getPanel(slug: string): Promise<Panel | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/panels/${encodeURIComponent(slug)}`)
    return await parseResponse<Panel>(response)
  } catch {
    return getMockPanel(slug)
  }
}

export async function resolvePanel(input: PanelResolveRequest): Promise<Panel> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/panels/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
    return await parseResponse<Panel>(response)
  } catch {
    const query =
      input.disease_mondo ??
      (input.symbols ? input.symbols.join(' ') : null) ??
      input.upload_ref ??
      ''
    const draft = buildCustomPanel(query)
    if (draft) return draft.panel
    return {
      id: 'custom-fallback',
      slug: 'custom-fallback',
      name: query || 'Custom panel',
      source: 'custom',
      version: 'draft',
      intervals_ref: 'hg38',
      genes: [],
      warnings: ['Offline mock — no genes resolved'],
    }
  }
}
