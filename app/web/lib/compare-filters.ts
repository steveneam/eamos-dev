// Active-filter model for the /compare scope bar (P3, mock-first).
//
// Filters are added as removable chips. Only PANEL filters compute client-side
// today (gene-symbol membership over the browser-parsed rows); Quality(PASS),
// Region, and Allele-frequency are configured here but APPLY SERVER-SIDE once
// Codex's batch engine lands — our parsed rows don't yet carry FILTER/AF/coords.
// Maps to spec §5.2 (filter order panel → PASS → region → AF) + the BatchFilters
// contract in lib/backend.ts.
import type { ParsedVariant } from './variant-file'
import type { Panel } from './backend'
import { getMockPanel } from './panels.mock'

export type FilterKind = 'panel' | 'pass' | 'region' | 'af'

export interface ActiveFilter {
  id: string
  kind: FilterKind
  panelSlug?: string // kind=panel (preset)
  customPanel?: Panel // kind=panel (builder-generated, source=custom)
  region?: string // kind=region
  maxAf?: number // kind=af
}

/** A panel filter resolves to a preset (by slug) or a builder-generated custom panel. */
export function resolveFilterPanel(f: ActiveFilter): Panel | null {
  if (f.customPanel) return f.customPanel
  if (f.panelSlug) return getMockPanel(f.panelSlug)
  return null
}

export const FILTER_META: Record<FilterKind, { label: string; serverSide: boolean }> = {
  panel: { label: 'Gene panel', serverSide: false },
  pass: { label: 'Quality (PASS)', serverSide: true },
  region: { label: 'Region', serverSide: true },
  af: { label: 'Allele frequency', serverSide: true },
}

export const DEFAULT_MAX_AF = 0.05
const SECONDS_PER_VARIANT = 9

let seq = 0
export function makeFilter(kind: FilterKind, init?: Partial<ActiveFilter>): ActiveFilter {
  seq += 1
  const f: ActiveFilter = { id: `${kind}-${Date.now()}-${seq}`, kind, ...init }
  if (kind === 'af' && f.maxAf == null) f.maxAf = DEFAULT_MAX_AF
  return f
}

export interface FilterResult {
  /** Rows to display = surviving the client-side (panel) filters. */
  shown: ParsedVariant[]
  total: number
  /** Genomic rows (no gene symbol) when ≥1 panel is active — need the
   *  server-side interval filter (MANE→hg38 BED); not droppable client-side. */
  intervalPending: number
  /** Resolved panels for the active panel chips. */
  activePanels: Panel[]
  /** Count of configured filters that apply server-side (PASS/region/af). */
  serverSideCount: number
  estSeconds: number
}

/** Apply the active filters. Panel chips union their genes (a row matches if it
 *  is in ANY active panel); non-panel chips are server-side and don't change the
 *  client row set, only the server-side tally. */
export function applyFilters(variants: ParsedVariant[], filters: ActiveFilter[]): FilterResult {
  const activePanels = filters
    .filter((f) => f.kind === 'panel')
    .map(resolveFilterPanel)
    .filter((p): p is Panel => Boolean(p))
  const serverSideCount = filters.filter((f) => f.kind !== 'panel').length

  if (activePanels.length === 0) {
    return {
      shown: variants,
      total: variants.length,
      intervalPending: 0,
      activePanels,
      serverSideCount,
      estSeconds: variants.length * SECONDS_PER_VARIANT,
    }
  }

  const symbols = new Set<string>()
  for (const panel of activePanels) for (const gene of panel.genes) symbols.add(gene.symbol.toUpperCase())

  const shown: ParsedVariant[] = []
  let intervalPending = 0
  for (const v of variants) {
    if (!v.gene) intervalPending += 1
    else if (symbols.has(v.gene.toUpperCase())) shown.push(v)
  }
  return {
    shown,
    total: variants.length,
    intervalPending,
    activePanels,
    serverSideCount,
    estSeconds: shown.length * SECONDS_PER_VARIANT,
  }
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `~${seconds}s`
  if (seconds < 3600) return `~${Math.round(seconds / 60)} min`
  return `~${(seconds / 3600).toFixed(1)} h`
}

/** Short human label for a chip. */
export function filterChipLabel(f: ActiveFilter): string {
  switch (f.kind) {
    case 'panel':
      return resolveFilterPanel(f)?.name ?? 'Panel'
    case 'pass':
      return 'PASS only'
    case 'region':
      return f.region ? `Region: ${f.region}` : 'Region'
    case 'af':
      return `AF ≤ ${f.maxAf ?? DEFAULT_MAX_AF}`
  }
}
