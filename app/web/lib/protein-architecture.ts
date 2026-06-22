export type ProteinArchitectureLaneId = 'topology' | 'domains' | 'motifs' | 'sites' | 'other'

export interface ProteinArchitectureFeature {
  start: number
  end: number
  label: string
  short: string
  kind: string
  lane: ProteinArchitectureLaneId
  description?: string | null
  source?: string | null
  accession?: string | null
  score?: number | null
  eValue?: number | null
  architecturePriority?: number
  broadBackbone?: boolean
}

export const TEMP_SUPPRESS_PFAM_HMMER_ARCHITECTURE = true

export const PROTEIN_ARCHITECTURE_LANE_ORDER: ProteinArchitectureLaneId[] = [
  'topology',
  'domains',
  'motifs',
  'sites',
  'other',
]

export function isPfamHmmerProteinFeature(feature: {
  source?: string | null
  accession?: string | null
  source_accession?: string | null
}): boolean {
  return /pfam|hmmer/i.test(`${feature.source ?? ''} ${feature.accession ?? ''} ${feature.source_accession ?? ''}`)
}

export function shouldSuppressPfamHmmerArchitecture<T extends {
  source?: string | null
  accession?: string | null
  source_accession?: string | null
}>(features: T[]): boolean {
  return TEMP_SUPPRESS_PFAM_HMMER_ARCHITECTURE && features.some((feature) => !isPfamHmmerProteinFeature(feature))
}

export function normalizeProteinArchitectureLane(
  lane: string | null | undefined,
  kind: string,
): ProteinArchitectureLaneId {
  const normalized = lane?.toLowerCase()
  if (normalized === 'topology' || normalized === 'domains' || normalized === 'motifs' || normalized === 'sites') {
    return normalized
  }
  if (normalized === 'other') return 'other'
  if (kind === 'signal_peptide' || kind === 'transmembrane' || kind === 'topological_domain') return 'topology'
  if (kind === 'site') return 'sites'
  if (kind === 'motif' || kind === 'region' || kind === 'coiled_coil' || kind === 'low_complexity') return 'motifs'
  if (kind === 'domain' || kind === 'repeat' || kind === 'family') return 'domains'
  return 'other'
}

export function proteinArchitectureLaneRank(lane: ProteinArchitectureLaneId): number {
  const index = PROTEIN_ARCHITECTURE_LANE_ORDER.indexOf(lane)
  return index === -1 ? PROTEIN_ARCHITECTURE_LANE_ORDER.length : index
}

export function proteinArchitectureFeatureLength(feature: Pick<ProteinArchitectureFeature, 'start' | 'end'>): number {
  return Math.max(1, feature.end - feature.start + 1)
}

export function canonicalizeProteinArchitectureFeature<T extends ProteinArchitectureFeature>(feature: T): T {
  const text = `${feature.short} ${feature.label} ${feature.description ?? ''}`.toLowerCase()
  const accession = `${feature.accession ?? ''}`.toUpperCase()
  const kind = feature.kind.toLowerCase()
  const curatedFeature = !isPfamHmmerProteinFeature(feature)
  const domainLike = feature.lane === 'domains' || kind === 'domain' || kind === 'repeat' || kind === 'family'
  const motifLike = feature.lane === 'motifs' || kind === 'motif' || kind === 'region'
  const siteLike = feature.lane === 'sites' || kind === 'site'
  const withCanonical = (
    short: string,
    label: string,
    description: string,
    architecturePriority: number,
    lane: ProteinArchitectureLaneId = feature.lane,
    extra: Partial<ProteinArchitectureFeature> = {},
  ): T => ({
    ...feature,
    ...extra,
    short,
    label,
    description,
    lane,
    architecturePriority,
  }) as T

  if (
    accession.startsWith('PF03055') ||
    /retinal pigment epithelial membrane protein|rpe65.*carotenoid oxygenase|carotenoid oxygenase/.test(text)
  ) {
    return withCanonical(
      'CarOxy',
      'Carotenoid oxygenase family',
      'Broad Pfam family/backbone annotation, not a precise domain boundary',
      66,
      'domains',
      { kind: 'family', broadBackbone: true },
    )
  }
  if (domainLike && /(brca1 c terminus|brct)/.test(text) && !/serine-rich/.test(text)) {
    return withCanonical('BRCT', 'BRCT domain', 'BRCA1 C-terminal BRCT domain', 98)
  }
  if (domainLike && !/prokaryotic/.test(text) && (/\bring\b|ring finger|ring-type|c3hc4/.test(text))) {
    return withCanonical('RING', 'RING finger domain', 'RING zinc-finger domain', 96)
  }
  if (/(fibronectin|fn3|fn\(iii\)|fn-?iii|fn iii)/.test(text)) {
    return withCanonical('FN3', 'Fibronectin type III domain', 'Fibronectin type III domain', 96)
  }
  if (/(laminin\/attractin egf|laminin egf|laminegf|lamegf|laed)/.test(text)) {
    return withCanonical('LamEGF', 'Laminin EGF-like domain', 'Laminin EGF-like domain', 98)
  }
  if (/(laminin g|lamg)/.test(text)) {
    return withCanonical('LamG', 'Laminin G-like domain', 'Laminin G-like domain', 97)
  }
  if (/(laminin n-terminal|laminin n terminal|lamnt)/.test(text)) {
    return withCanonical('LamNT', 'Laminin N-terminal domain', 'Laminin N-terminal domain', 97)
  }
  if (/(egf|epidermal growth factor|laminin egf|lam-egf)/.test(text)) {
    return withCanonical('EGF', 'EGF-like repeat', 'EGF-like repeat', 92)
  }
  if (/(von willebrand|vwf|vwd|vwc|vwap|vwd)/.test(text)) {
    return withCanonical('vW', 'von Willebrand factor domain', 'von Willebrand factor domain', 90)
  }
  if (/(dynamin family|dynamin-type g|dynamin.*g domain)/.test(text)) {
    return withCanonical('G domain', 'Dynamin G domain', 'Dynamin GTPase domain', 98)
  }
  if (/(dynamin central|middle\/stalk|middle domain|stalk domain)/.test(text)) {
    return withCanonical('Stalk', 'Dynamin stalk domain', 'Dynamin middle/stalk domain', 96)
  }
  if (/(gtpase effector|ged)/.test(text)) {
    return withCanonical('GED', 'GTPase effector domain', 'Dynamin GTPase effector domain', 97)
  }
  if (/(pleckstrin|ph domain)/.test(text)) {
    return withCanonical('PH', 'PH domain', 'Pleckstrin homology domain', 97)
  }
  if (/(proline-rich|prd)/.test(text)) {
    return withCanonical('PRD', 'Proline-rich domain', 'Proline-rich domain', 92)
  }
  if (/(fz domain|frizzled.*cysteine|wnt-binding)/.test(text)) {
    return withCanonical('CRD', 'Frizzled cysteine-rich domain', 'WNT-binding cysteine-rich domain', 97)
  }
  if (/(frizzled\/smoothened|frizzled.*membrane|transmembrane|helical|7tm|seven-transmembrane|smoothened)/.test(text)) {
    return withCanonical('7TM', 'Frizzled/Smoothened membrane region', 'Seven-transmembrane receptor region', 94)
  }
  if (/pdz/.test(text)) {
    return withCanonical('PDZ', 'PDZ-binding motif', 'PDZ-binding motif', 90)
  }
  if (siteLike && /(iron|metal binding|catalytic|active site)/.test(text)) {
    return withCanonical('Fe', feature.label, feature.description ?? feature.label, 88, 'sites')
  }
  if (siteLike && /(palmitoyl|palmitoylation)/.test(text)) {
    return withCanonical('Palm', feature.label, feature.description ?? feature.label, 86, 'sites')
  }
  if (curatedFeature && motifLike && /(membrane|amphipathic)/.test(text)) {
    return withCanonical('Mem', 'Membrane-contact region', 'Membrane-contact region', 84, 'motifs')
  }
  return feature
}

export function selectPrimaryProteinArchitectureFeatures<T extends ProteinArchitectureFeature>(features: T[]): T[] {
  const suppressPfamHmmer = shouldSuppressPfamHmmerArchitecture(features)
  const sourceFiltered = suppressPfamHmmer
    ? features.filter((feature) => !isPfamHmmerProteinFeature(feature))
    : features
  const selectedByLane = new Map<ProteinArchitectureLaneId, T[]>()

  PROTEIN_ARCHITECTURE_LANE_ORDER.forEach((lane) => {
    const selected: T[] = []
    const laneFeatures = sourceFiltered.filter((feature) => feature.lane === lane)
    const hasCanonicalInLane = laneFeatures.some((feature) => architecturePriority(feature) >= 70)
    const candidates = laneFeatures
      .filter((feature) => isPrimaryArchitectureFeature(feature, hasCanonicalInLane))
      .sort((a, b) => {
        const priorityDelta = architecturePriority(b) - architecturePriority(a)
        if (priorityDelta !== 0) return priorityDelta
        const confidenceDelta = featureConfidence(b) - featureConfidence(a)
        if (confidenceDelta !== 0) return confidenceDelta
        const lengthDelta = proteinArchitectureFeatureLength(b) - proteinArchitectureFeatureLength(a)
        if (lengthDelta !== 0) return lengthDelta
        return a.start - b.start
      })

    candidates.forEach((candidate) => {
      const overlapsSelected = selected.some((kept) => significantOverlap(candidate, kept))
      if (!overlapsSelected) selected.push(candidate)
    })

    selectedByLane.set(
      lane,
      selected.sort((a, b) => a.start - b.start || a.end - b.end),
    )
  })

  const selected = PROTEIN_ARCHITECTURE_LANE_ORDER.flatMap((lane) => selectedByLane.get(lane) ?? [])
  const hasSpecificAnnotations = selected.some((feature) => !feature.broadBackbone)
  return hasSpecificAnnotations
    ? selected.filter((feature) => !feature.broadBackbone)
    : selected
}

function architecturePriority(feature: ProteinArchitectureFeature): number {
  if (feature.architecturePriority != null) return feature.architecturePriority
  if (feature.kind === 'domain' || feature.kind === 'repeat') return 55
  if (feature.kind === 'site') return 65
  if (feature.kind === 'motif' || feature.kind === 'region') return 58
  if (feature.kind === 'transmembrane' || feature.kind === 'signal_peptide') return 60
  return 40
}

function featureConfidence(feature: ProteinArchitectureFeature): number {
  if (feature.eValue != null && feature.eValue > 0) return -Math.log10(feature.eValue)
  return feature.score ?? 0
}

function significantOverlap(a: ProteinArchitectureFeature, b: ProteinArchitectureFeature): boolean {
  const overlap = Math.min(a.end, b.end) - Math.max(a.start, b.start) + 1
  if (overlap <= 0) return false
  const smaller = Math.min(proteinArchitectureFeatureLength(a), proteinArchitectureFeatureLength(b))
  return overlap / smaller >= 0.45
}

function isPrimaryArchitectureFeature(feature: ProteinArchitectureFeature, hasCanonicalInLane: boolean): boolean {
  const text = `${feature.short} ${feature.label} ${feature.description ?? ''}`.toLowerCase()
  if (feature.lane === 'domains' && /prokaryotic.*ring/.test(text)) return false
  if (feature.kind === 'topological_domain') return false
  if (feature.lane !== 'domains') return true
  if (architecturePriority(feature) >= 70) return true
  if (hasCanonicalInLane) return false
  const source = feature.source?.toLowerCase() ?? ''
  if (!source.includes('hmmer')) return true
  return (feature.score ?? 0) >= 45 && (feature.eValue ?? Number.POSITIVE_INFINITY) <= 1e-8
}
