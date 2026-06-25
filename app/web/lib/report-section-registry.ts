import registryData from './report-section-registry.json'
import type { LookupSectionId } from '@/lib/backend'

export type ReportSectionId =
  | 'clinical_evidence'
  | 'evidence_by_source'
  | 'population_frequency'
  | 'gene_context'
  | 'associated_conditions'
  | 'publications'
  | 'trials'

export type ReportSectionLoadPolicy = 'eager' | 'lazy' | 'eager_with_lazy_panel'
export type ReportSectionSkeleton = 'card_skeleton' | 'panel_skeleton'

export interface ReportSectionRegistryEntry {
  id: ReportSectionId
  anchorId: string
  label: string
  title: string
  number: number
  meta: string
  loadPolicy: ReportSectionLoadPolicy
  lazySectionId?: LookupSectionId
  eagerPayloadSelector: string
  lazyFetchContract: string | null
  skeleton: ReportSectionSkeleton
  emptyState: string
  partialState: string
  failedState: string
  staleState: string
  requiredSlot: boolean
  preflightRequired: boolean
  navigation: boolean
  export: boolean
  signalIds: string[]
  aliasAnchors?: string[]
}

interface ReportSectionRegistryData {
  schemaVersion: number
  sections: ReportSectionRegistryEntry[]
}

export const REPORT_SECTION_REGISTRY =
  (registryData as ReportSectionRegistryData).sections

export const REPORT_SECTION_BY_ID = Object.fromEntries(
  REPORT_SECTION_REGISTRY.map((section) => [section.id, section]),
) as Record<ReportSectionId, ReportSectionRegistryEntry>

export const REPORT_SECTION_NAV_ITEMS = REPORT_SECTION_REGISTRY
  .filter((section) => section.navigation)
  .map((section) => ({
    id: section.anchorId,
    label: section.label,
  }))

export const REPORT_REQUIRED_SECTION_SLOTS = REPORT_SECTION_REGISTRY
  .filter((section) => section.preflightRequired)
  .map((section) => ({
    id: section.id,
    anchorId: section.anchorId,
    label: section.label,
    title: section.title,
  }))

export const REPORT_LAZY_SECTION_IDS = REPORT_SECTION_REGISTRY
  .map((section) => section.lazySectionId)
  .filter((sectionId): sectionId is LookupSectionId => Boolean(sectionId))

export const REPORT_SIGNAL_ANCHORS = REPORT_SECTION_REGISTRY.reduce<Record<string, string>>(
  (anchors, section) => {
    for (const signalId of section.signalIds) {
      anchors[signalId] = section.anchorId
    }
    return anchors
  },
  {},
)
