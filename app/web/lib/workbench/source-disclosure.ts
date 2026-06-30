import type { SourceDisclosure, WorkbenchSourceStatus } from '@/lib/backend'

const STATUS_LABELS: Record<WorkbenchSourceStatus, string> = {
  source_backed: 'Source-backed',
  local_provider: 'Local provider',
  fallback: 'Preview fallback',
  fixture: 'Fixture',
  gated: 'Gated',
  unavailable: 'Unavailable',
}

const FALLBACK_DISCLOSURE: SourceDisclosure = {
  source_status: 'fallback',
  provider_id: 'workbench_unknown_source',
  provider_label: 'Workbench fallback',
  source_version: null,
  cache_status: null,
  warnings: [],
  requirements: [],
}

export interface WorkbenchDisclosureView {
  status: WorkbenchSourceStatus
  statusLabel: string
  providerLabel: string
  cacheStatus: string | null
  warnings: string[]
  requirements: string[]
  operational: boolean
  preview: boolean
  caveat: string
}

export function disclosureView(
  disclosure: SourceDisclosure | null | undefined,
  fallback: Partial<SourceDisclosure> = {},
): WorkbenchDisclosureView {
  const merged: SourceDisclosure = {
    ...FALLBACK_DISCLOSURE,
    ...fallback,
    ...disclosure,
    warnings: disclosure?.warnings ?? fallback.warnings ?? FALLBACK_DISCLOSURE.warnings,
    requirements:
      disclosure?.requirements ?? fallback.requirements ?? FALLBACK_DISCLOSURE.requirements,
  }
  const operational =
    merged.source_status === 'source_backed' || merged.source_status === 'local_provider'
  const preview = merged.source_status === 'fixture' || merged.source_status === 'fallback'
  return {
    status: merged.source_status,
    statusLabel: STATUS_LABELS[merged.source_status],
    providerLabel: merged.provider_label,
    cacheStatus: merged.cache_status ?? null,
    warnings: merged.warnings,
    requirements: merged.requirements,
    operational,
    preview,
    caveat: caveatFor(merged),
  }
}

export function disclosureChipClass(status: WorkbenchSourceStatus): string {
  if (status === 'source_backed') return 'source-backed'
  if (status === 'local_provider') return 'local-provider'
  if (status === 'fixture') return 'fixture'
  if (status === 'fallback') return 'fallback'
  if (status === 'gated') return 'gated'
  return 'unavailable'
}

function caveatFor(disclosure: SourceDisclosure): string {
  switch (disclosure.source_status) {
    case 'source_backed':
      return 'Backed by a resolved source or ready local index.'
    case 'local_provider':
      return 'Computed by the local backend provider for this request.'
    case 'fixture':
      return 'Bundled fixture data, suitable for offline rendering only.'
    case 'fallback':
      return 'Fallback output, not a source-backed solve.'
    case 'gated':
      return 'Provider is implemented but not enabled for launch.'
    case 'unavailable':
      return 'Provider is unavailable for this request.'
  }
}
