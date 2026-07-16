import type { CSSProperties } from 'react'

import type {
  PopulationFrequencyDatasetCell,
  PopulationFrequencyOverall,
  PopulationFrequencyOverallTotalCell,
  PopulationFrequencySexCell,
  PopulationFrequencyVisualGroup,
} from '@/lib/backend'

import { gnomadMapAnchor } from '../gnomadAncestryMap'
import { GNOMAD_MAP_REGIONS } from '../gnomadMapGeometry.generated'
import {
  GNOMAD_AF_BANDS,
  GNOMAD_MAP_SURFACE,
  type GnomadAfBand,
} from '../gnomadMapTheme'

export function formatInteger(value: number | null | undefined): string {
  return value == null ? 'Not reported' : new Intl.NumberFormat('en-US').format(value)
}

export function formatFrequency(value: number | null | undefined): string {
  if (value == null) return 'Not reported'
  if (value === 0) return '0%'
  const pct = value * 100
  if (pct < 0.001) return `${pct.toExponential(2)}%`
  if (pct < 0.1) return `${pct.toPrecision(2)}%`
  return `${pct.toFixed(2)}%`
}

export function compactLabel(label: string): string {
  return label.replace(' genetic ancestry', '')
}

const WARNING_COPY: Record<string, string> = {
  low_allele_number_cohorts:
    'Some ancestry groups have few sampled alleles (small sample size), so their frequencies are less precise.',
  allele_number_unavailable: 'Allele number (sample size) is not reported for one or more groups.',
  genetic_ancestry_groups_unavailable: 'Per-ancestry-group frequencies are unavailable for this variant.',
  age_distribution_unavailable: 'Age distribution is not available for this variant.',
  age_distribution_scope: 'Age distribution covers all gnomAD release samples, not only this variant’s carriers.',
  per_genetic_ancestry_age_distribution_not_available: 'Age distribution is not broken down by ancestry group.',
  allele_frequency_unavailable: 'Overall allele frequency is unavailable for this variant.',
  population_frequency_detail_unavailable: 'Detailed population frequency data is unavailable.',
  gnomad_source_status: 'gnomAD did not return a live frequency result for this lookup.',
  source_status: 'gnomAD source status is not live for this lookup.',
}

const UNAVAILABLE_REASON_COPY: Record<string, string> = {
  detail_unavailable: 'Detailed gnomAD population frequency data is unavailable.',
  frequency_metrics_unavailable: 'gnomAD returned the variant but did not provide usable frequency metrics.',
  variant_not_found: 'gnomAD has no record for this variant.',
  source_failure: 'gnomAD could not be reached for this lookup.',
  source_unavailable: 'gnomAD is unavailable for this lookup.',
}

export function warningCopy(warning: string): string {
  const key = warning.split(':', 1)[0]
  return WARNING_COPY[warning] ?? WARNING_COPY[key] ?? warning.replace(/_/g, ' ').replace(/:/g, ': ')
}

export function machineText(value: string | null | undefined): string | null {
  if (!value) return null
  return value.replace(/_/g, ' ').replace(/:/g, ': ').trim()
}

export function unavailableReasonCopy(reason: string | null | undefined): string | null {
  if (!reason) return null
  return UNAVAILABLE_REASON_COPY[reason] ?? machineText(reason)
}

export function sourceStatusNeedsDisclosure(status: string | null | undefined): boolean {
  if (!status) return false
  return !['live', 'local', 'cache', 'fixture'].includes(status.toLowerCase())
}

export function uniqueWarnings(warnings: string[]): string[] {
  return Array.from(new Set(warnings.filter(Boolean)))
}

export function groupContext(group: PopulationFrequencyVisualGroup): string {
  return gnomadMapAnchor(group.id).context
}

export function bandForAf(
  value: number | null | undefined,
  dataState?: string,
): GnomadAfBand | null {
  if (dataState === 'zero_observed' || value == null || value <= 0) return null
  return GNOMAD_AF_BANDS.find((band) => value >= band.min) ?? null
}

export function bandFill(value: number | null | undefined, dataState?: string): string {
  return bandForAf(value, dataState)?.color ?? GNOMAD_MAP_SURFACE.noData
}

export const GEOGRAPHIC_GROUP_IDS = new Set<string>(
  GNOMAD_MAP_REGIONS.map((region) => region.group),
)

const OFFMAP_SHORT_DESC: Record<string, string> = {
  remaining: 'Individuals not assigned gnomAD labels',
}

export function offMapOriginCopy(groupId: string): string {
  return (
    OFFMAP_SHORT_DESC[groupId] ??
    gnomadMapAnchor(groupId)
      .context.split(/,?\s*oriented/i)[0]
      .replace(/^gnomAD\s+\w+:\s*/i, '')
      .replace(/[;,]\s*$/, '')
      .trim()
  )
}

export const FOOTER_CHIP_WIDTH = 140
export const FOOTER_CHIP_MIN_HEIGHT = 46
export const FOOTER_CHIP_DESC_STYLE: CSSProperties = {
  marginTop: 2,
  fontSize: 9.2,
  color: 'var(--ink-4)',
  lineHeight: 1.3,
  display: '-webkit-box',
  WebkitLineClamp: 2,
  WebkitBoxOrient: 'vertical',
  overflow: 'hidden',
}

const EMPTY_DATASET_CELL: PopulationFrequencyDatasetCell = {
  allele_frequency: null,
  allele_count: null,
  allele_number: null,
  homozygote_count: null,
}

export function selectDatasetCell(
  base: PopulationFrequencyOverallTotalCell,
  includeExome: boolean,
  includeGenome: boolean,
): PopulationFrequencyDatasetCell {
  if (includeExome && includeGenome) {
    return {
      allele_frequency: base.allele_frequency,
      allele_count: base.allele_count,
      allele_number: base.allele_number,
      homozygote_count: base.homozygote_count,
    }
  }
  if (includeExome) return base.exome ?? EMPTY_DATASET_CELL
  if (includeGenome) return base.genome ?? EMPTY_DATASET_CELL
  return EMPTY_DATASET_CELL
}

export function applyDatasetToGroup(
  group: PopulationFrequencyVisualGroup,
  includeExome: boolean,
  includeGenome: boolean,
): PopulationFrequencyVisualGroup {
  const cell = selectDatasetCell(group, includeExome, includeGenome)
  const observed = cell.allele_frequency != null && cell.allele_frequency > 0
  return {
    ...group,
    allele_frequency: cell.allele_frequency,
    allele_count: cell.allele_count,
    allele_number: cell.allele_number,
    homozygote_count: cell.homozygote_count,
    data_state: observed ? 'observed' : 'zero_observed',
  }
}

export function applyDatasetToOverall(
  overall: PopulationFrequencyOverall | null | undefined,
  includeExome: boolean,
  includeGenome: boolean,
): PopulationFrequencyOverall | null {
  if (!overall) return null
  const total = overall.total
    ? { ...overall.total, ...selectDatasetCell(overall.total, includeExome, includeGenome) }
    : overall.total
  return { ...overall, total }
}

export function buildAncestryFrequencyTsv(
  groups: PopulationFrequencyVisualGroup[],
  overall: PopulationFrequencyOverall | null,
): string {
  const num = (value: number | null | undefined) => (value == null ? '' : String(value))
  const row = (label: string, cell: PopulationFrequencySexCell) =>
    [
      label,
      num(cell.allele_frequency),
      num(cell.allele_count),
      num(cell.allele_number),
      num(cell.homozygote_count),
    ].join('\t')
  const header = [
    'Genetic ancestry group',
    'Allele frequency',
    'Allele count',
    'Allele number',
    'Homozygotes',
  ].join('\t')
  const groupRows = groups.map((group) => row(compactLabel(group.label), group))
  const overallRows: string[] = []
  if (overall?.total) overallRows.push(row('Total', overall.total))
  if (overall?.xx) overallRows.push(row('XX', overall.xx))
  if (overall?.xy) overallRows.push(row('XY', overall.xy))
  return [header, ...groupRows, ...overallRows].join('\n')
}

export function buildReadoutTsv(
  title: string,
  rows: Array<{ label: string; cell: PopulationFrequencySexCell }>,
): string {
  const num = (value: number | null | undefined) => (value == null ? '' : String(value))
  const lines = [
    title,
    ['', 'Allele frequency', 'Allele count', 'Allele number', 'Homozygotes'].join('\t'),
  ]
  rows.forEach((row) =>
    lines.push(
      [
        row.label,
        num(row.cell.allele_frequency),
        num(row.cell.allele_count),
        num(row.cell.allele_number),
        num(row.cell.homozygote_count),
      ].join('\t'),
    ),
  )
  return lines.join('\n')
}

export function hasOverall(overall?: PopulationFrequencyOverall | null): boolean {
  return Boolean(overall && (overall.total || overall.xx || overall.xy))
}
