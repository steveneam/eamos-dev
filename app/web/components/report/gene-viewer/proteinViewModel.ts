import type { CSSProperties } from 'react'

import type { ProteinDomainTrack, ProteinDomainTrackFeature } from '@/lib/backend'
import {
  canonicalizeProteinArchitectureFeature,
  normalizeProteinArchitectureLane,
  proteinArchitectureFeatureLength,
  proteinArchitectureLaneRank,
  selectPrimaryProteinArchitectureFeatures,
  type ProteinArchitectureFeature,
  type ProteinArchitectureLaneId,
} from '@/lib/protein-architecture'
import type { GeneWindowData } from '@/lib/workbench/gene-window'

import { clamp } from './geneViewerPresentation'

export interface ProteinFeatureRender extends ProteinArchitectureFeature {
  start: number
  end: number
  label: string
  short: string
  kind: string
  lane: ProteinLaneId
  description?: string | null
  source?: string | null
  accession?: string | null
  score?: number | null
  eValue?: number | null
  architecturePriority?: number
  broadBackbone?: boolean
}

interface PackedProteinFeature extends ProteinFeatureRender {
  legendKey: string
  row: number
  x: number
  width: number
}

export type ProteinLaneId = ProteinArchitectureLaneId

interface ProteinLaneDef {
  id: ProteinLaneId
  label: string
}

export const PROTEIN_W = 920
export const PROTEIN_LEFT = 42
export const PROTEIN_RIGHT = 34
export const PROTEIN_MAX_W = 5600
export const PROTEIN_MARKER_Y = 28
export const PROTEIN_LANE_TOP = 64
export const PROTEIN_LANE_H = 34
export const PROTEIN_LANE_GAP = 24
export const PROTEIN_HEAT_H = 12
export const HEAT_MAX_BINS = 800

const PROTEIN_LANES: ProteinLaneDef[] = [
  { id: 'topology', label: 'Topology' },
  { id: 'domains', label: 'Domains / regions' },
  { id: 'motifs', label: 'Motifs' },
  { id: 'sites', label: 'Sites' },
  { id: 'other', label: 'Other' },
]

export const DEFAULT_VISIBLE_PROTEIN_LANES = new Set<ProteinLaneId>(
  PROTEIN_LANES.map((lane) => lane.id),
)

export function featuresFromTrack(features: ProteinDomainTrackFeature[]): ProteinFeatureRender[] {
  return features
    .map((feature) => ({
      start: feature.aa_start,
      end: Math.max(feature.aa_start, feature.aa_end),
      label: feature.label,
      short: feature.short_label ?? shortLabel(feature.label),
      kind: feature.kind,
      lane: normalizeProteinLane(feature.lane, feature.kind),
      description: feature.description,
      source: feature.source,
      accession: feature.accession ?? feature.source_accession,
      score: feature.score,
      eValue: feature.e_value,
    }))
    .map(canonicalProteinFeature)
    .sort((a, b) => laneRank(a.lane) - laneRank(b.lane) || a.start - b.start || a.end - b.end)
}

export function featuresFromViewer(data: GeneWindowData): ProteinFeatureRender[] {
  return [
    ...(data.proteinFeatures.signalPeptide
      ? [
          {
            start: data.proteinFeatures.signalPeptide.aaStart,
            end: data.proteinFeatures.signalPeptide.aaEnd,
            label: 'Signal peptide',
            short: 'SP',
            kind: 'signal_peptide',
            lane: 'topology' as const,
            source: 'viewer protein_features',
            architecturePriority: 88,
          },
        ]
      : []),
    ...data.proteinFeatures.domains
      .map((feature) => ({
        start: feature.aaStart,
        end: feature.aaEnd,
        label: feature.label,
        short: feature.shortLabel ?? shortLabel(feature.label),
        kind: 'domain',
        lane: 'domains' as const,
        source: feature.source ?? 'viewer protein_features',
        accession: feature.accession,
        broadBackbone: feature.broadBackbone,
        architecturePriority: feature.broadBackbone ? 50 : 54,
      }))
      .map(canonicalProteinFeature),
    ...data.proteinFeatures.transmembrane.map((feature) => ({
      start: feature.aaStart,
      end: feature.aaEnd,
      label: feature.label,
      short: shortLabel(feature.label),
      kind: 'transmembrane',
      lane: 'topology' as const,
      source: 'viewer protein_features',
      architecturePriority: 88,
    })),
    ...data.proteinFeatures.membraneBinding.map((feature) => ({
      start: feature.aaStart,
      end: feature.aaEnd,
      label: feature.label,
      short: shortLabel(feature.label),
      kind: 'region',
      lane: 'motifs' as const,
      source: 'viewer protein_features',
      architecturePriority: 82,
    })),
    ...data.proteinFeatures.activeSites.map((feature) => ({
      start: feature.aa,
      end: feature.aa,
      label: feature.label,
      short: feature.residue ? `${feature.residue}${feature.aa}` : `aa ${feature.aa}`,
      kind: 'site',
      lane: 'sites' as const,
      source: 'viewer protein_features',
      architecturePriority: 75,
    })),
    ...data.proteinFeatures.palmitoylation.map((feature) => ({
      start: feature.aa,
      end: feature.aa,
      label: feature.label,
      short: feature.residue ? `${feature.residue}${feature.aa}` : `aa ${feature.aa}`,
      kind: 'site',
      lane: 'sites' as const,
      source: 'viewer protein_features',
      architecturePriority: 75,
    })),
  ]
    .map(canonicalProteinFeature)
    .sort((a, b) => laneRank(a.lane) - laneRank(b.lane) || a.start - b.start || a.end - b.end)
}

function shortLabel(label: string): string {
  return label.length > 34 ? `${label.slice(0, 31)}...` : label
}

interface ProteinScaleTick {
  aa: number
  major: boolean
  terminal: boolean
}

export function proteinScaleTicks(length: number): ProteinScaleTick[] {
  const clampedLength = Math.max(1, Math.round(length))
  const ticks = new Map<number, ProteinScaleTick>()
  const setTick = (aa: number, major: boolean, terminal = false) => {
    const clampedAa = clamp(Math.round(aa), 1, clampedLength)
    const existing = ticks.get(clampedAa)
    ticks.set(clampedAa, {
      aa: clampedAa,
      major: major || existing?.major === true,
      terminal: terminal || existing?.terminal === true,
    })
  }

  setTick(1, true)
  for (let aa = 100; aa < clampedLength; aa += 100) {
    setTick(aa, aa % 200 === 0)
  }
  setTick(clampedLength, true, true)

  return Array.from(ticks.values()).sort((a, b) => a.aa - b.aa)
}

export function proteinCanvasWidth(proteinLength: number, featureCount: number): number {
  const lengthWidth = PROTEIN_LEFT + PROTEIN_RIGHT + proteinLength * 0.95
  const densityWidth = PROTEIN_LEFT + PROTEIN_RIGHT + featureCount * 42
  return Math.round(Math.min(PROTEIN_MAX_W, Math.max(PROTEIN_W, lengthWidth, densityWidth)))
}

export function proteinArchitectureFeatures(
  features: ProteinFeatureRender[],
): ProteinFeatureRender[] {
  return selectPrimaryProteinArchitectureFeatures(features)
}

function canonicalProteinFeature(feature: ProteinFeatureRender): ProteinFeatureRender {
  return canonicalizeProteinArchitectureFeature(feature)
}

function featureLength(feature: ProteinFeatureRender): number {
  return proteinArchitectureFeatureLength(feature)
}

export function packProteinFeatures(
  features: ProteinFeatureRender[],
  lanes: ProteinLaneDef[],
  xFor: (aa: number) => number,
): { packedFeatures: PackedProteinFeature[] } {
  const laneFeatures = new Map<ProteinLaneId, PackedProteinFeature[]>()

  lanes.forEach((lane) => {
    const rowFeatures =
      lanes.length === 1 ? features : features.filter((feature) => feature.lane === lane.id)
    const packed = rowFeatures
      .sort((a, b) => a.start - b.start || b.end - a.end)
      .map((feature) => {
        const x = xFor(feature.start)
        return {
          ...feature,
          legendKey: featureLegendKey(feature),
          row: 0,
          x,
          width: Math.max(3, xFor(feature.end) - x),
        }
      })
    laneFeatures.set(lane.id, packed)
  })

  return { packedFeatures: lanes.flatMap((lane) => laneFeatures.get(lane.id) ?? []) }
}

export function proteinLanesFor(features: ProteinFeatureRender[]): ProteinLaneDef[] {
  return PROTEIN_LANES.filter((lane) => features.some((feature) => feature.lane === lane.id))
}

function normalizeProteinLane(lane: string | null | undefined, kind: string): ProteinLaneId {
  return normalizeProteinArchitectureLane(lane, kind)
}

function laneRank(lane: ProteinLaneId): number {
  return proteinArchitectureLaneRank(lane)
}

function laneColor(lane: ProteinLaneId): { fill: string; stroke: string; text: string } {
  if (lane === 'topology') {
    return { fill: 'rgba(191, 116, 58, 0.18)', stroke: 'rgba(155, 87, 34, 0.58)', text: 'var(--ink-2)' }
  }
  if (lane === 'motifs') {
    return { fill: 'rgba(136, 104, 190, 0.16)', stroke: 'rgba(111, 82, 164, 0.52)', text: 'var(--ink-2)' }
  }
  if (lane === 'sites') {
    return { fill: 'rgba(216, 179, 82, 0.24)', stroke: 'rgba(172, 132, 34, 0.58)', text: 'var(--ink-2)' }
  }
  if (lane === 'other') {
    return { fill: 'rgba(92, 107, 122, 0.13)', stroke: 'rgba(92, 107, 122, 0.42)', text: 'var(--ink-2)' }
  }
  return { fill: 'var(--teal-tint)', stroke: 'var(--teal-bdr)', text: 'var(--teal-deep)' }
}

export function featureColor(
  feature: ProteinFeatureRender,
): { fill: string; stroke: string; text: string } {
  if (feature.broadBackbone || feature.kind === 'family') {
    return {
      fill: 'rgba(92, 107, 122, 0.12)',
      stroke: 'rgba(92, 107, 122, 0.44)',
      text: 'var(--ink-2)',
    }
  }
  const featureText = `${feature.short} ${feature.label} ${feature.description ?? ''}`.toLowerCase()
  if (feature.lane === 'motifs' && /membrane|amphipathic/.test(featureText)) {
    return {
      fill: 'rgba(80, 129, 185, 0.22)',
      stroke: 'rgba(80, 129, 185, 0.72)',
      text: 'var(--ink)',
    }
  }
  if (feature.lane === 'sites' && /palmit/.test(featureText)) {
    return {
      fill: 'var(--base-C, #4a9d8f)',
      stroke: 'rgba(37, 119, 104, 0.92)',
      text: 'var(--bg)',
    }
  }
  if (feature.lane === 'sites' && /iron|active|metal/.test(featureText)) {
    return { fill: '#BA7517', stroke: 'rgba(105, 71, 22, 0.95)', text: 'var(--bg)' }
  }
  if (feature.lane === 'domains') return domainPaletteColor(feature)
  if (feature.kind === 'coiled_coil') {
    return { fill: 'rgba(47, 125, 121, 0.13)', stroke: 'rgba(47, 125, 121, 0.48)', text: 'var(--teal-deep)' }
  }
  if (feature.kind === 'low_complexity' || feature.kind === 'repeat') {
    return { fill: 'rgba(121, 137, 153, 0.14)', stroke: 'rgba(92, 107, 122, 0.4)', text: 'var(--ink-2)' }
  }
  return laneColor(feature.lane)
}

function domainPaletteColor(
  feature: Pick<ProteinFeatureRender, 'short' | 'label'>,
): { fill: string; stroke: string; text: string } {
  const palette = [
    ['rgba(44, 123, 182, 0.18)', 'rgba(44, 123, 182, 0.58)', 'rgb(22, 78, 121)'],
    ['rgba(86, 160, 103, 0.18)', 'rgba(72, 137, 87, 0.58)', 'rgb(39, 96, 55)'],
    ['rgba(196, 118, 62, 0.18)', 'rgba(173, 93, 42, 0.58)', 'rgb(123, 66, 29)'],
    ['rgba(129, 102, 181, 0.18)', 'rgba(111, 82, 164, 0.58)', 'rgb(78, 56, 125)'],
    ['rgba(196, 87, 112, 0.16)', 'rgba(174, 66, 93, 0.56)', 'rgb(125, 45, 65)'],
    ['rgba(37, 151, 143, 0.16)', 'rgba(26, 126, 120, 0.56)', 'rgb(20, 92, 88)'],
    ['rgba(184, 143, 50, 0.18)', 'rgba(158, 118, 31, 0.58)', 'rgb(113, 83, 20)'],
    ['rgba(89, 111, 173, 0.17)', 'rgba(70, 91, 151, 0.55)', 'rgb(50, 66, 112)'],
    ['rgba(159, 104, 70, 0.17)', 'rgba(138, 82, 49, 0.55)', 'rgb(96, 58, 37)'],
    ['rgba(90, 138, 156, 0.16)', 'rgba(70, 116, 135, 0.54)', 'rgb(47, 83, 98)'],
  ] as const
  const key = domainPaletteKey(feature)
  const [fill, stroke, text] = palette[hashString(key) % palette.length]
  return { fill, stroke, text }
}

function domainPaletteKey(feature: Pick<ProteinFeatureRender, 'short' | 'label'>): string {
  const short = feature.short.trim().toLowerCase()
  if (short && short.length <= 18 && !short.endsWith('...')) return short
  return feature.label.trim().toLowerCase()
}

function hashString(value: string): number {
  let hash = 0
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0
  }
  return hash
}

export function labelForFeatureWidth(
  feature: ProteinFeatureRender,
  width: number,
): string | null {
  if (isPointProteinFeature(feature) || width < 28) return null
  const maxChars = Math.max(3, Math.floor(width / 6.4))
  if (feature.short.length <= maxChars) return feature.short
  if (maxChars <= 5) return feature.short.slice(0, maxChars)
  return `${feature.short.slice(0, maxChars - 3)}...`
}

export function isPointProteinFeature(feature: ProteinFeatureRender): boolean {
  return feature.start === feature.end || feature.kind === 'site' || (feature.kind === 'motif' && featureLength(feature) <= 5)
}

export function proteinFeaturePatternId(
  feature: Pick<ProteinFeatureRender, 'lane' | 'kind'>,
): string | null {
  if (feature.kind === 'family') return 'protein-pattern-other'
  return null
}

export function categorySwatchStyle(
  lane: ProteinLaneId,
  color: { fill: string; stroke: string; text: string },
): CSSProperties {
  return {
    width: 13,
    height: 8,
    borderRadius: 2,
    border: `0.5px solid ${color.stroke}`,
    display: 'inline-block',
    flex: '0 0 auto',
    ...categorySwatchBackgroundStyle(lane, color),
  }
}

function categorySwatchBackgroundStyle(
  lane: ProteinLaneId,
  color: { fill: string; stroke: string; text: string },
): CSSProperties {
  if (lane === 'domains') {
    return {
      background:
        'linear-gradient(90deg, rgba(44, 123, 182, 0.28) 0 20%, rgba(86, 160, 103, 0.28) 20% 40%, rgba(196, 118, 62, 0.28) 40% 60%, rgba(129, 102, 181, 0.28) 60% 80%, rgba(196, 87, 112, 0.24) 80% 100%)',
    }
  }
  if (lane === 'topology') {
    return {
      backgroundColor: color.fill,
      backgroundImage: `repeating-linear-gradient(135deg, transparent 0 4px, ${color.stroke} 4px 5px, transparent 5px 9px)`,
    }
  }
  if (lane === 'motifs') {
    return {
      backgroundColor: color.fill,
      backgroundImage: `repeating-linear-gradient(90deg, transparent 0 4px, ${color.stroke} 4px 5px, transparent 5px 8px)`,
    }
  }
  if (lane === 'sites') {
    return {
      backgroundColor: color.fill,
      backgroundImage: `radial-gradient(circle at 2px 2px, ${color.stroke} 1.1px, transparent 1.4px)`,
      backgroundSize: '6px 6px',
    }
  }
  if (lane === 'other') {
    return {
      backgroundColor: color.fill,
      backgroundImage: `repeating-linear-gradient(0deg, transparent 0 4px, ${color.stroke} 4px 5px, transparent 5px 8px)`,
    }
  }
  return { background: color.fill }
}

export function featureCategoryLegendItems(features: ProteinFeatureRender[]): Array<{
  lane: ProteinLaneId
  label: string
  color: { fill: string; stroke: string; text: string }
}> {
  const categories: Array<{ lane: ProteinLaneId; label: string }> = [
    { lane: 'topology', label: 'Topology' },
    { lane: 'domains', label: 'Domains / regions' },
    { lane: 'motifs', label: 'Motifs' },
    { lane: 'sites', label: 'Sites' },
    { lane: 'other', label: 'Other' },
  ]
  return categories
    .filter((category) => features.some((feature) => feature.lane === category.lane))
    .map((category) => ({
      lane: category.lane,
      label: category.label,
      color: laneColor(category.lane),
    }))
}

export function featureLegendItems(features: ProteinFeatureRender[]): Array<{
  key: string
  short: string
  kindLabel: string
  description: string | null
  coordLabel: string
  ranges: Array<{ start: number; end: number }>
  count: number
  title: string
  color: { fill: string; stroke: string; text: string }
}> {
  const groups = new Map<
    string,
    {
      short: string
      kindLabel: string
      description: string | null
      features: ProteinFeatureRender[]
    }
  >()

  features.forEach((feature) => {
    const description = feature.description || (feature.label !== feature.short ? feature.label : null)
    const key = featureLegendKey(feature)
    const existing = groups.get(key)
    if (existing) {
      existing.features.push(feature)
      return
    }
    groups.set(key, {
      short: feature.short,
      kindLabel: feature.broadBackbone
        ? 'family / backbone'
        : `architecture / ${feature.kind}`.replace(/_/g, ' '),
      description,
      features: [feature],
    })
  })

  return Array.from(groups.entries()).map(([key, group]) => {
    const sorted = group.features.sort((a, b) => a.start - b.start || a.end - b.end)
    const min = Math.min(...sorted.map((feature) => feature.start))
    const max = Math.max(...sorted.map((feature) => feature.end))
    const coords = sorted
      .slice(0, 5)
      .map((feature) => `aa ${feature.start}${feature.start === feature.end ? '' : `-${feature.end}`}`)
      .join(', ')
    const overflow = sorted.length > 5 ? `, +${sorted.length - 5} more` : ''
    return {
      key,
      short: group.short,
      kindLabel: group.kindLabel,
      description: group.description,
      coordLabel: sorted.length === 1 ? coords : `${sorted.length}x | aa ${min}-${max}`,
      ranges: sorted.map((feature) => ({ start: feature.start, end: feature.end })),
      count: sorted.length,
      title: sorted.map(featureTitle).join('\n') + overflow,
      color: featureColor(sorted[0]),
    }
  })
}

function featureLegendKey(
  feature: Pick<ProteinFeatureRender, 'lane' | 'kind' | 'short' | 'label' | 'description'>,
): string {
  const description = feature.description || (feature.label !== feature.short ? feature.label : null)
  return [feature.lane, feature.kind, feature.short, description ?? ''].join('|')
}

export function alphaColor(score: number): string {
  if (score < 0.2) return 'var(--cls-ben-dot)'
  if (score < 0.4) return 'var(--cls-lben-dot)'
  if (score < 0.6) return 'var(--cls-vus-dot)'
  if (score < 0.8) return 'var(--cls-lpath-dot)'
  return 'var(--cls-path-dot)'
}

export function featureTitle(feature: ProteinFeatureRender): string {
  return [
    feature.label,
    `aa ${feature.start}-${feature.end}`,
    feature.source,
    feature.accession,
  ]
    .filter(Boolean)
    .join(' | ')
}

export function proteinSourceLabel(
  track: ProteinDomainTrack | null,
  hasFallbackFeatures: boolean,
): string {
  if (!track) {
    return hasFallbackFeatures
      ? 'Viewer protein_features'
      : 'No protein architecture features returned'
  }
  if (track.status !== 'available' && track.status !== 'cache_hit' && track.status !== 'partial') {
    return track.fail_closed_reason
      ? `Protein architecture unavailable: ${track.fail_closed_reason}`
      : `Protein architecture unavailable: ${track.status}`
  }
  const sources = Array.from(new Set(track.features.map((feature) => feature.source).filter(Boolean)))
  const hasUniprot = sources.some((source) => /uniprot/i.test(source))
  const hasPfam = sources.some((source) => /pfam|hmmer/i.test(source))
  const sourceSummary = [
    hasUniprot ? 'UniProtKB/Swiss-Prot features' : null,
    hasPfam ? (hasUniprot ? 'Pfam family support' : 'Pfam/HMMER family hits') : null,
    ...sources.filter((source) => !/uniprot|pfam|hmmer/i.test(source)),
  ].filter(Boolean)
  const release = track.pfam_release ?? track.uniprot_release ?? track.hmmer_release
  const status = track.status === 'partial' ? 'Source-backed partial' : 'Source-backed'
  return [status, sourceSummary.slice(0, 3).join(' + '), release].filter(Boolean).join(' | ')
}
