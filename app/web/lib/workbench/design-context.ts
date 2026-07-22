import type {
  CanonicalVariantRefV1,
  GeneViewerResponse,
  SelectionOrientationV1,
  SelectionOverlapV1,
  SelectionRangeV1,
  SequenceBasisV1,
  ViewerCoordinateMapRange,
  WorkbenchDesignContextV1,
} from '@/lib/backend'

export type LocusEditKind = 'sub' | 'del' | 'ins'

export interface LocusEditV1 {
  genomicPosition: number
  kind: LocusEditKind
  /** Bases in genomic-forward orientation. Insertions occur after the position. */
  alt: string
}

export interface DesignSelectionDraft {
  genomicStart: number
  genomicEnd: number
  orientation: SelectionOrientationV1
  sequenceBasis: SequenceBasisV1
  /** The immutable basis under sparse edits. */
  baseAllele: 'reference' | 'variant'
  editRevision: number
  edits: LocusEditV1[]
}

export interface ParsedGenomicIdentity {
  chrom: string
  position: number
  ref: string
  alt: string
  variantKey: string
}

const DNA_RE = /^[ACGTN]+$/i
const SHA256_RE = /^[0-9a-f]{64}$/
const OVERLAP_ORDER: SelectionOverlapV1[] = ['utr5', 'utr3', 'cds', 'exon', 'intron']

export function normalizeChromosome(value: string): string {
  const clean = value.trim()
  if (!clean) return ''
  return clean.toLowerCase().startsWith('chr') ? `chr${clean.slice(3)}` : `chr${clean}`
}

export function parseGenomicIdentity(
  value: string | null | undefined,
  fallbackChrom?: string | null,
): ParsedGenomicIdentity | null {
  const clean = value?.trim()
  if (!clean) return null

  const compact = clean.replace(/\s+/g, '')
  const dash = /^(?:chr)?([A-Za-z0-9_.]+)-(\d+)-([ACGTN]+)-([ACGTN]+)$/i.exec(compact)
  if (dash) {
    const chrom = normalizeChromosome(dash[1])
    const position = Number(dash[2])
    const ref = dash[3].toUpperCase()
    const alt = dash[4].toUpperCase()
    if (!chrom || !Number.isSafeInteger(position) || position < 1) return null
    return {
      chrom,
      position,
      ref,
      alt,
      variantKey: `${chrom.slice(3)}-${position}-${ref}-${alt}`,
    }
  }

  const hgvs = /^(?:[^:]+:)?g\.(\d+)([ACGTN]+)>([ACGTN]+)$/i.exec(compact)
  if (!hgvs) return null
  const chrom = normalizeChromosome(fallbackChrom ?? '')
  const position = Number(hgvs[1])
  const ref = hgvs[2].toUpperCase()
  const alt = hgvs[3].toUpperCase()
  if (!chrom || !Number.isSafeInteger(position) || position < 1) return null
  return {
    chrom,
    position,
    ref,
    alt,
    variantKey: `${chrom.slice(3)}-${position}-${ref}-${alt}`,
  }
}

/**
 * The viewer contract predates CanonicalVariantRefV1. Until the backend adds a
 * direct field, derive only from its resolved transcript and genomic identity.
 * An incomplete identity fails closed and cannot initiate a design request.
 */
export function canonicalVariantFromViewer(
  response: GeneViewerResponse,
): CanonicalVariantRefV1 | null {
  const gene = response.identity.gene.trim().toUpperCase()
  const transcript = response.identity.resolved_transcript.trim()
  const genomeBuild = response.identity.genome_build.trim()
  const species = response.identity.species.trim().toLowerCase()
  const genomic = parseGenomicIdentity(
    response.queried_variant.genomic_hg38,
    response.full_locus?.locus.chrom ?? response.locus.chrom,
  )
  if (
    !gene ||
    !transcript ||
    genomeBuild !== 'GRCh38' ||
    species !== 'human' ||
    !genomic
  ) {
    return null
  }

  const support = Array.from(
    new Set(
      response.provenance.sources
        .map((source) => source.name.trim())
        .filter(Boolean),
    ),
  )

  return {
    schema_version: 'canonical_variant_ref.v1',
    gene,
    cdna: response.queried_variant.hgvs_c,
    transcript,
    protein_hgvs: response.queried_variant.hgvs_p ?? null,
    genomic_hg38: response.queried_variant.genomic_hg38 ?? null,
    variant_key: genomic.variantKey,
    species: 'human',
    genome_build: 'GRCh38',
    resolution_status: 'resolved',
    source_support: support,
    warnings: [...response.provenance.warnings],
  }
}

function reverseComplement(sequence: string): string {
  const complement: Record<string, string> = {
    A: 'T',
    C: 'G',
    G: 'C',
    T: 'A',
    N: 'N',
  }
  return sequence
    .toUpperCase()
    .split('')
    .reverse()
    .map((base) => complement[base] ?? 'N')
    .join('')
}

function isReverseOrientation(
  response: GeneViewerResponse,
  orientation: SelectionOrientationV1,
): boolean {
  return (
    orientation === 'genomic_reverse' ||
    (orientation === 'transcript' && response.full_locus?.locus.strand === '-')
  )
}

function normalizedEdits(edits: LocusEditV1[]): Map<number, LocusEditV1> | null {
  if (edits.length > 2_000) return null
  const byPosition = new Map<number, LocusEditV1>()
  for (const edit of edits) {
    const alt = edit.alt.replace(/\s+/g, '').toUpperCase()
    if (!Number.isSafeInteger(edit.genomicPosition) || edit.genomicPosition < 1) return null
    if (edit.kind === 'sub' && (alt.length !== 1 || !DNA_RE.test(alt))) return null
    if (edit.kind === 'ins' && (!alt || !DNA_RE.test(alt) || alt.length > 1_000)) return null
    if (edit.kind === 'del') {
      byPosition.set(edit.genomicPosition, { ...edit, alt: '' })
      continue
    }
    byPosition.set(edit.genomicPosition, { ...edit, alt })
  }
  return byPosition
}

export function selectedLocusSequence(
  response: GeneViewerResponse,
  draft: DesignSelectionDraft,
): string | null {
  const full = response.full_locus
  if (!full) return null
  const start = Math.min(draft.genomicStart, draft.genomicEnd)
  const end = Math.max(draft.genomicStart, draft.genomicEnd)
  if (start < full.locus.start || end > full.locus.end || start > end) return null

  if (
    (draft.sequenceBasis === 'edited' && (draft.editRevision < 1 || draft.edits.length === 0)) ||
    (draft.sequenceBasis !== 'edited' && (draft.editRevision !== 0 || draft.edits.length > 0))
  ) {
    return null
  }

  const genomicIdentity = parseGenomicIdentity(
    response.queried_variant.genomic_hg38,
    full.locus.chrom,
  )
  const edits = normalizedEdits(draft.edits)
  if (!edits) return null
  if (
    draft.baseAllele === 'variant' &&
    (!genomicIdentity || genomicIdentity.ref.length !== 1 || genomicIdentity.alt.length !== 1)
  ) {
    return null
  }
  const output: string[] = []
  for (let position = start; position <= end; position += 1) {
    const offset = position - full.locus.start
    let base = full.locus.sequence[offset]?.toUpperCase()
    if (!base || !DNA_RE.test(base)) return null
    if (
      draft.baseAllele === 'variant' &&
      genomicIdentity &&
      genomicIdentity.position === position
    ) {
      if (base !== genomicIdentity.ref) return null
      base = genomicIdentity.alt
    }
    const edit = edits.get(position)
    if (!edit) {
      output.push(base)
    } else if (edit.kind === 'sub') {
      output.push(edit.alt)
    } else if (edit.kind === 'ins') {
      output.push(base, edit.alt)
    }
  }
  const genomicForward = output.join('')
  return isReverseOrientation(response, draft.orientation)
    ? reverseComplement(genomicForward)
    : genomicForward
}

function intersectingBounds(
  range: ViewerCoordinateMapRange,
  selectionStart: number,
  selectionEnd: number,
  projectedStart: number | null | undefined,
  projectedEnd: number | null | undefined,
  strand: '+' | '-' | 'unknown',
): [number, number] | null {
  if (projectedStart == null || projectedEnd == null) return null
  const genomicStart = Math.min(range.genomic_start, range.genomic_end)
  const genomicEnd = Math.max(range.genomic_start, range.genomic_end)
  const hitStart = Math.max(selectionStart, genomicStart)
  const hitEnd = Math.min(selectionEnd, genomicEnd)
  if (hitEnd < hitStart) return null

  const project = (position: number): number => {
    const delta = position - genomicStart
    return strand === '-'
      ? Math.max(projectedStart, projectedEnd) - delta
      : Math.min(projectedStart, projectedEnd) + delta
  }
  const a = project(hitStart)
  const b = project(hitEnd)
  return [Math.min(a, b), Math.max(a, b)]
}

function projectedSelectionBounds(
  response: GeneViewerResponse,
  start: number,
  end: number,
  key: 'cdna' | 'cds',
): [number, number] | null {
  const projection = response.full_locus?.transcript_projection
  if (!projection) return null
  const values: number[] = []
  for (const range of projection.coordinate_map) {
    const bounds = intersectingBounds(
      range,
      start,
      end,
      range[`${key}_start`],
      range[`${key}_end`],
      projection.strand,
    )
    if (bounds) values.push(...bounds)
  }
  return values.length > 0 ? [Math.min(...values), Math.max(...values)] : null
}

/** Protein coordinates are derived from exact CDS nucleotide bounds.
 *
 * The coordinate-map protein fields describe an interval and cannot represent
 * which codon a one-base selection lands in. Deriving from the CDS projection
 * keeps one-base, codon-boundary, exon-boundary, and reverse-strand selections
 * unambiguous.
 */
function proteinBoundsFromCds(cds: [number, number] | null): [number, number] | null {
  if (!cds) return null
  return [Math.ceil(cds[0] / 3), Math.ceil(cds[1] / 3)]
}

function selectionOverlaps(
  response: GeneViewerResponse,
  start: number,
  end: number,
): SelectionOverlapV1[] {
  const intervals = response.full_locus?.transcript_projection.intervals ?? []
  const found = new Set<SelectionOverlapV1>()
  for (const interval of intervals) {
    const intervalStart = Math.min(interval.genomic_start, interval.genomic_end)
    const intervalEnd = Math.max(interval.genomic_start, interval.genomic_end)
    if (intervalEnd < start || intervalStart > end) continue
    found.add(interval.kind)
  }
  return OVERLAP_ORDER.filter((kind) => found.has(kind))
}

export async function selectionRangeFromViewer(
  response: GeneViewerResponse,
  variant: CanonicalVariantRefV1,
  draft: DesignSelectionDraft,
): Promise<SelectionRangeV1 | null> {
  const full = response.full_locus
  if (!full || full.locus.genome_build !== 'GRCh38' || full.locus.strand === 'unknown') {
    return null
  }
  const start = Math.min(draft.genomicStart, draft.genomicEnd)
  const end = Math.max(draft.genomicStart, draft.genomicEnd)
  const sequence = selectedLocusSequence(response, draft)
  if (!sequence) return null

  const cdna = projectedSelectionBounds(response, start, end, 'cdna')
  const cds = projectedSelectionBounds(response, start, end, 'cds')
  const protein = proteinBoundsFromCds(cds)
  const overlaps = selectionOverlaps(response, start, end)
  if (overlaps.length === 0) return null
  if (
    (draft.sequenceBasis === 'edited' && draft.editRevision < 1) ||
    (draft.sequenceBasis !== 'edited' && draft.editRevision !== 0)
  ) {
    return null
  }
  return {
    schema_version: 'selection_range.v1',
    variant_key: variant.variant_key,
    transcript: variant.transcript!,
    genome_build: 'GRCh38',
    chrom: normalizeChromosome(full.locus.chrom),
    genomic_start: start,
    genomic_end: end,
    strand: full.locus.strand,
    orientation: draft.orientation,
    sequence_basis: draft.sequenceBasis,
    edit_revision: Math.max(0, Math.trunc(draft.editRevision)),
    sequence_sha256: await sha256Hex(sequence),
    cdna_start: cdna?.[0] ?? null,
    cdna_end: cdna?.[1] ?? null,
    cds_start: cds?.[0] ?? null,
    cds_end: cds?.[1] ?? null,
    protein_start: protein?.[0] ?? null,
    protein_end: protein?.[1] ?? null,
    overlaps,
  }
}

function sortJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortJsonValue)
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const key of Object.keys(value as Record<string, unknown>).sort()) {
      out[key] = sortJsonValue((value as Record<string, unknown>)[key])
    }
    return out
  }
  return value
}

export function canonicalJson(value: unknown): string {
  return JSON.stringify(sortJsonValue(value))
}

export async function sha256Hex(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value)
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

export async function buildWorkbenchContextDigest(
  variant: CanonicalVariantRefV1,
  selection: SelectionRangeV1,
): Promise<string> {
  return sha256Hex(
    canonicalJson({
      schema_version: 'workbench_design_context.v1',
      variant,
      selection,
    }),
  )
}

export async function buildWorkbenchDesignContext(
  response: GeneViewerResponse,
  draft: DesignSelectionDraft,
): Promise<WorkbenchDesignContextV1 | null> {
  const variant = canonicalVariantFromViewer(response)
  if (!variant) return null
  const selection = await selectionRangeFromViewer(response, variant, draft)
  if (!selection) return null
  const context_digest = await buildWorkbenchContextDigest(variant, selection)
  if (!SHA256_RE.test(context_digest)) return null
  return {
    schema_version: 'workbench_design_context.v1',
    variant,
    selection,
    context_digest,
  }
}

export function isWorkbenchResultStale(
  resultDigest: string | null | undefined,
  currentDigest: string | null | undefined,
): boolean {
  return Boolean(resultDigest && currentDigest && resultDigest !== currentDigest)
}
