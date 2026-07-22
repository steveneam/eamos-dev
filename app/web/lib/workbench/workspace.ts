import type {
  SelectionOrientationV1,
  SequenceBasisV1,
  WorkbenchTool,
  WorkbenchViewV1,
} from '@/lib/backend'
import type { LocusEditV1 } from './design-context'

export const WORKBENCH_WORKSPACE_SCHEMA = 'workbench_browser_workspace.v1' as const
export const WORKBENCH_WORKSPACE_TTL_MS = 48 * 60 * 60 * 1_000
const WORKSPACE_KEY = 'eamos.workbench.workspace.v1'
const MAX_EDITS = 500
const MAX_SERIALIZED_BYTES = 96_000
const RESULT_TOOLS = ['primer', 'crispr', 'align'] as const

export type WorkbenchResultTool = (typeof RESULT_TOOLS)[number]

export interface WorkbenchDerivedResultV1 {
  schema_version: 'workbench_derived_result.v1'
  tool: WorkbenchResultTool
  context_digest: string | null
  result_digest: string
  recorded_at: string
  title: string
  /** Bounded, non-sequence metrics only. Raw reads, traces, and pasted input
   * are intentionally excluded from browser-session persistence. */
  metrics: Record<string, string | number | boolean | null>
}

export interface WorkbenchWorkspaceSelectionV1 {
  genomicStart: number
  genomicEnd: number
  orientation: SelectionOrientationV1
  sequenceBasis: SequenceBasisV1
  baseAllele: 'reference' | 'variant'
  editRevision: number
}

export interface WorkbenchBrowserWorkspaceV1 {
  schema_version: typeof WORKBENCH_WORKSPACE_SCHEMA
  scope: 'browser_session'
  identity: string
  created_at: string
  updated_at: string
  expires_at: string
  active_tool: Exclude<WorkbenchTool, 'compare'>
  view: WorkbenchViewV1
  selection: WorkbenchWorkspaceSelectionV1 | null
  edits: LocusEditV1[]
  result_digests: Partial<Record<WorkbenchResultTool, string>>
  derived_results: Partial<Record<WorkbenchResultTool, WorkbenchDerivedResultV1>>
}

export function workbenchIdentity(
  gene: string,
  cdna: string,
  transcript?: string | null,
): string {
  return [gene.trim().toUpperCase(), cdna.replace(/\s+/g, ''), transcript?.trim() ?? ''].join('|')
}

export function createWorkbenchWorkspace(
  identity: string,
  now = new Date(),
): WorkbenchBrowserWorkspaceV1 {
  return {
    schema_version: WORKBENCH_WORKSPACE_SCHEMA,
    scope: 'browser_session',
    identity,
    created_at: now.toISOString(),
    updated_at: now.toISOString(),
    expires_at: new Date(now.getTime() + WORKBENCH_WORKSPACE_TTL_MS).toISOString(),
    active_tool: 'viewer',
    view: 'window',
    selection: null,
    edits: [],
    result_digests: {},
    derived_results: {},
  }
}

function safeTool(value: unknown): WorkbenchBrowserWorkspaceV1['active_tool'] | null {
  return value === 'viewer' || value === 'primer' || value === 'crispr' || value === 'align'
    ? value
    : null
}

function safeOrientation(value: unknown): SelectionOrientationV1 | null {
  return value === 'genomic_forward' || value === 'genomic_reverse' || value === 'transcript'
    ? value
    : null
}

function safeBasis(value: unknown): SequenceBasisV1 | null {
  return value === 'reference' || value === 'variant' || value === 'edited' ? value : null
}

function safeSelection(
  value: unknown,
  edits: LocusEditV1[],
): WorkbenchWorkspaceSelectionV1 | null {
  if (!value || typeof value !== 'object') return null
  const input = value as Record<string, unknown>
  const genomicStart = Number(input.genomicStart)
  const genomicEnd = Number(input.genomicEnd)
  const editRevision = Number(input.editRevision)
  const orientation = safeOrientation(input.orientation)
  const sequenceBasis = safeBasis(input.sequenceBasis)
  const baseAllele = input.baseAllele === 'reference' || input.baseAllele === 'variant'
    ? input.baseAllele
    : null
  if (
    !Number.isSafeInteger(genomicStart) ||
    !Number.isSafeInteger(genomicEnd) ||
    genomicStart < 1 ||
    genomicEnd < 1 ||
    genomicStart > genomicEnd ||
    !Number.isSafeInteger(editRevision) ||
    editRevision < 0 ||
    !orientation ||
    !sequenceBasis ||
    !baseAllele ||
    (sequenceBasis === 'edited' && (editRevision < 1 || edits.length === 0)) ||
    (sequenceBasis !== 'edited' && (editRevision !== 0 || edits.length > 0)) ||
    (sequenceBasis !== 'edited' && sequenceBasis !== baseAllele)
  ) {
    return null
  }
  return { genomicStart, genomicEnd, orientation, sequenceBasis, baseAllele, editRevision }
}

function safeEdits(value: unknown): LocusEditV1[] {
  if (!Array.isArray(value) || value.length > MAX_EDITS) return []
  const byPosition = new Map<number, LocusEditV1>()
  for (const item of value) {
    if (!item || typeof item !== 'object') continue
    const input = item as Record<string, unknown>
    const genomicPosition = Number(input.genomicPosition)
    const kind = input.kind
    const alt = typeof input.alt === 'string' ? input.alt.replace(/\s+/g, '').toUpperCase() : ''
    if (
      !Number.isSafeInteger(genomicPosition) ||
      genomicPosition < 1 ||
      (kind !== 'sub' && kind !== 'del' && kind !== 'ins') ||
      (kind === 'sub' && (alt.length !== 1 || !/^[ACGTN]$/.test(alt))) ||
      (kind === 'ins' && (!alt || alt.length > 1_000 || !/^[ACGTN]+$/.test(alt))) ||
      (kind === 'del' && alt.length > 0)
    ) {
      continue
    }
    byPosition.set(genomicPosition, { genomicPosition, kind, alt })
  }
  return Array.from(byPosition.values()).sort(
    (left, right) => left.genomicPosition - right.genomicPosition,
  )
}

function safeDigests(value: unknown): WorkbenchBrowserWorkspaceV1['result_digests'] {
  if (!value || typeof value !== 'object') return {}
  const input = value as Record<string, unknown>
  const result: WorkbenchBrowserWorkspaceV1['result_digests'] = {}
  for (const tool of RESULT_TOOLS) {
    const digest = input[tool]
    if (typeof digest === 'string' && /^[0-9a-f]{64}$/.test(digest)) result[tool] = digest
  }
  return result
}

function safeDerivedResults(
  value: unknown,
  digests: WorkbenchBrowserWorkspaceV1['result_digests'],
  earliest = Number.NEGATIVE_INFINITY,
  latest = Number.POSITIVE_INFINITY,
): WorkbenchBrowserWorkspaceV1['derived_results'] {
  if (!value || typeof value !== 'object') return {}
  const input = value as Record<string, unknown>
  const result: WorkbenchBrowserWorkspaceV1['derived_results'] = {}
  for (const tool of RESULT_TOOLS) {
    const raw = input[tool]
    if (!raw || typeof raw !== 'object') continue
    const item = raw as Record<string, unknown>
    const resultDigest = typeof item.result_digest === 'string'
      ? item.result_digest.toLowerCase()
      : ''
    const contextDigest = item.context_digest == null
      ? null
      : typeof item.context_digest === 'string'
        ? item.context_digest.toLowerCase()
        : ''
    const recordedAt = typeof item.recorded_at === 'string'
      ? new Date(item.recorded_at)
      : new Date(NaN)
    const title = typeof item.title === 'string'
      ? item.title.replace(/[\u0000-\u001f\u007f]+/g, ' ').trim().slice(0, 160)
      : ''
    if (
      item.schema_version !== 'workbench_derived_result.v1' ||
      item.tool !== tool ||
      !/^[0-9a-f]{64}$/.test(resultDigest) ||
      digests[tool] !== resultDigest ||
      (contextDigest !== null && !/^[0-9a-f]{64}$/.test(contextDigest)) ||
      !Number.isFinite(recordedAt.getTime()) ||
      recordedAt.getTime() < earliest ||
      recordedAt.getTime() > latest ||
      !title ||
      !item.metrics ||
      typeof item.metrics !== 'object' ||
      Array.isArray(item.metrics)
    ) {
      continue
    }
    const metrics: WorkbenchDerivedResultV1['metrics'] = {}
    for (const [key, rawMetric] of Object.entries(item.metrics as Record<string, unknown>).slice(0, 16)) {
      if (!/^[a-z][a-z0-9_]{0,39}$/.test(key)) continue
      if (/sequence|trace|blob|raw_input|file_content|ab1/i.test(key)) continue
      if (typeof rawMetric === 'string') {
        metrics[key] = rawMetric.replace(/[\u0000-\u001f\u007f]+/g, ' ').trim().slice(0, 200)
      } else if (typeof rawMetric === 'number' && Number.isFinite(rawMetric)) {
        metrics[key] = rawMetric
      } else if (typeof rawMetric === 'boolean' || rawMetric === null) {
        metrics[key] = rawMetric
      }
    }
    result[tool] = {
      schema_version: 'workbench_derived_result.v1',
      tool,
      context_digest: contextDigest,
      result_digest: resultDigest,
      recorded_at: recordedAt.toISOString(),
      title,
      metrics,
    }
  }
  return result
}

export function parseWorkbenchWorkspace(
  raw: string,
  expectedIdentity: string,
  now = new Date(),
): WorkbenchBrowserWorkspaceV1 | null {
  if (!raw || raw.length > MAX_SERIALIZED_BYTES) return null
  let input: unknown
  try {
    input = JSON.parse(raw)
  } catch {
    return null
  }
  if (!input || typeof input !== 'object') return null
  const value = input as Record<string, unknown>
  const tool = safeTool(value.active_tool)
  const view = value.view === 'window' || value.view === 'locus' ? value.view : null
  const expiresAt = typeof value.expires_at === 'string' ? Date.parse(value.expires_at) : NaN
  const createdAt = typeof value.created_at === 'string' ? Date.parse(value.created_at) : NaN
  const updatedAt = typeof value.updated_at === 'string' ? Date.parse(value.updated_at) : NaN
  const edits = safeEdits(value.edits)
  const resultDigests = safeDigests(value.result_digests)
  if (
    value.schema_version !== WORKBENCH_WORKSPACE_SCHEMA ||
    value.scope !== 'browser_session' ||
    value.identity !== expectedIdentity ||
    !tool ||
    !view ||
    !Number.isFinite(expiresAt) ||
    expiresAt <= now.getTime() ||
    !Number.isFinite(createdAt) ||
    !Number.isFinite(updatedAt) ||
    createdAt > updatedAt ||
    updatedAt > expiresAt ||
    expiresAt - updatedAt > WORKBENCH_WORKSPACE_TTL_MS
  ) {
    return null
  }
  return {
    schema_version: WORKBENCH_WORKSPACE_SCHEMA,
    scope: 'browser_session',
    identity: expectedIdentity,
    created_at: new Date(createdAt).toISOString(),
    updated_at: new Date(updatedAt).toISOString(),
    expires_at: new Date(expiresAt).toISOString(),
    active_tool: tool,
    view,
    selection: safeSelection(value.selection, edits),
    edits,
    result_digests: resultDigests,
    derived_results: safeDerivedResults(value.derived_results, resultDigests, createdAt, updatedAt),
  }
}

export function readWorkbenchWorkspace(
  identity: string,
  storage: Pick<Storage, 'getItem' | 'removeItem'> = window.sessionStorage,
  now = new Date(),
): WorkbenchBrowserWorkspaceV1 | null {
  let raw: string | null
  try {
    raw = storage.getItem(WORKSPACE_KEY)
  } catch {
    return null
  }
  if (!raw) return null
  const parsed = parseWorkbenchWorkspace(raw, identity, now)
  if (!parsed) {
    try {
      storage.removeItem(WORKSPACE_KEY)
    } catch {
      // Storage can be disabled; invalid state is still ignored safely.
    }
  }
  return parsed
}

export function writeWorkbenchWorkspace(
  workspace: WorkbenchBrowserWorkspaceV1,
  storage: Pick<Storage, 'setItem'> = window.sessionStorage,
  now = new Date(),
): WorkbenchBrowserWorkspaceV1 {
  const edits = safeEdits(workspace.edits)
  const createdAt = Date.parse(workspace.created_at)
  const safeCreatedAt = Number.isFinite(createdAt) && createdAt <= now.getTime()
    ? createdAt
    : now.getTime()
  const next: WorkbenchBrowserWorkspaceV1 = {
    ...workspace,
    scope: 'browser_session',
    created_at: new Date(safeCreatedAt).toISOString(),
    updated_at: now.toISOString(),
    expires_at: new Date(now.getTime() + WORKBENCH_WORKSPACE_TTL_MS).toISOString(),
    selection: safeSelection(workspace.selection, edits),
    edits,
    result_digests: safeDigests(workspace.result_digests),
    derived_results: {},
  }
  next.derived_results = safeDerivedResults(
    workspace.derived_results,
    next.result_digests,
    safeCreatedAt,
    now.getTime(),
  )
  const serialized = JSON.stringify(next)
  if (serialized.length > MAX_SERIALIZED_BYTES) throw new Error('Workspace exceeds browser-session limit.')
  storage.setItem(WORKSPACE_KEY, serialized)
  return next
}

export function clearWorkbenchWorkspace(
  storage: Pick<Storage, 'removeItem'> = window.sessionStorage,
): void {
  try {
    storage.removeItem(WORKSPACE_KEY)
  } catch {
    // A disabled storage backend is already equivalent to a cleared session.
  }
}

export function workspaceExpiryLabel(expiresAt: string, now = new Date()): string {
  const remainingMinutes = Math.max(0, Math.ceil((Date.parse(expiresAt) - now.getTime()) / 60_000))
  if (remainingMinutes >= 60) return `${Math.ceil(remainingMinutes / 60)}h`
  return `${remainingMinutes}m`
}
