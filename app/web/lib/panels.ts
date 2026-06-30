import type { Panel, PanelResolveRequest, PanelSummary } from './backend'
import { MOCK_PANELS, buildCustomPanel, getMockPanel } from './panels.mock'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''
const OFFLINE_PANEL_WARNING = 'offline fixture panel catalog; backend panel service unavailable'
const OFFLINE_RESOLVE_WARNING = 'offline fixture panel resolver; backend panel service unavailable'

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
    // Offline or route-missing development mode uses bundled fixture panels.
    return MOCK_PANELS.map((panel) => withPanelWarning(panel, OFFLINE_PANEL_WARNING))
  }
}

export async function getPanel(slug: string): Promise<Panel | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/panels/${encodeURIComponent(slug)}`)
    return await parseResponse<Panel>(response)
  } catch {
    const panel = getMockPanel(slug)
    return panel ? withPanelWarning(panel, OFFLINE_PANEL_WARNING) : null
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
    if (draft) return withPanelWarning(draft.panel, OFFLINE_RESOLVE_WARNING)
    return {
      id: 'custom-fallback',
      slug: 'custom-fallback',
      name: query || 'Custom panel',
      source: 'custom',
      version: 'draft',
      intervals_ref: 'hg38',
      genes: [],
      warnings: [OFFLINE_RESOLVE_WARNING, 'offline mock; no genes resolved'],
    }
  }
}

function withPanelWarning<T extends { warnings: string[] }>(panel: T, warning: string): T {
  return {
    ...panel,
    warnings: Array.from(new Set([...(panel.warnings ?? []), warning])),
  }
}
