/* Full-locus row layout. Pure, no DOM, no React.

   Input:  ViewerFullLocus straight off the backend.
   Output: row-keyed structure consumed by FullLocusViewer.

   Coordinate convention: row coordinates and feature/codon positions are
   relayed verbatim from the backend payload. The renderer treats
   `locus.sequence` as `sequence.length === locus.end - locus.start` and
   maps any genomic position `p` to a sequence offset by `p - locus.start`.
   Row labels are reported as absolute backend positions so a user can copy
   them straight into a coordinate search. */

import type {
  ViewerFeatureInterval,
  ViewerFullLocus,
  ViewerFullLocusFeatureKind,
  ViewerOrientation,
  ViewerTranscriptIntervalKind,
  ViewerTranscriptProjectionInterval,
  GenomeStrand,
  VariantClassification,
} from '../backend'

export interface FullLocusBand {
  kind: ViewerTranscriptIntervalKind
  colStart: number
  colEnd: number
  label: string
  exonNumber?: number | null
  intronNumber?: number | null
}

export interface FullLocusCodonMark {
  codonNumber: number
  proteinPosition: number
  col: number
  basesInRow: number
}

export interface FullLocusVariantPin {
  col: number
  label: string
  refBase: string | null
  altBase: string | null
  classification: VariantClassification | null
}

export interface FullLocusRow {
  rowIndex: number
  genomicStart: number
  genomicEnd: number
  bases: string
  bands: FullLocusBand[]
  codonMarks: FullLocusCodonMark[]
  variantPin?: FullLocusVariantPin
  clinvarPins: Array<{ col: number; label: string; classification: VariantClassification | null }>
}

export interface FullLocusRows {
  basesPerRow: number
  rowCount: number
  totalBases: number
  variantRowIndex: number | null
  rows: FullLocusRow[]
  orientation: ViewerOrientation
  chrom: string
  strand: GenomeStrand
  genomeBuild: string
  locusStart: number
  locusEnd: number
}

const DEFAULT_BASES_PER_ROW = 60

function clampBasesPerRow(hintMin: number, hintMax: number, requested: number): number {
  const lo = Math.max(1, Math.floor(hintMin || 1))
  const hi = Math.max(lo, Math.floor(hintMax || lo))
  return Math.min(hi, Math.max(lo, Math.floor(requested)))
}

function intervalLabel(interval: ViewerTranscriptProjectionInterval): string {
  if (interval.label) return interval.label
  switch (interval.kind) {
    case 'exon':
      return interval.exon_number != null ? `Exon ${interval.exon_number}` : 'Exon'
    case 'intron':
      return interval.intron_number != null ? `Intron ${interval.intron_number}` : 'Intron'
    case 'utr5':
      return "5' UTR"
    case 'utr3':
      return "3' UTR"
    case 'cds':
      return 'CDS'
    default:
      return interval.kind
  }
}

function featureLabel(feature: ViewerFeatureInterval): string {
  if (feature.label) return feature.label
  return feature.kind
}

function isQueriedVariantFeature(kind: ViewerFullLocusFeatureKind): boolean {
  return kind === 'queried_variant'
}

function isClinvarFeature(kind: ViewerFullLocusFeatureKind): boolean {
  return kind === 'clinvar'
}

function classificationOf(feature: ViewerFeatureInterval): VariantClassification | null {
  return feature.classification ?? null
}

function metadataString(
  feature: ViewerFeatureInterval,
  key: string,
): string | null {
  const value = feature.metadata?.[key]
  return typeof value === 'string' ? value : null
}

export function buildFullLocusRows(
  full: ViewerFullLocus,
  opts: { basesPerRow?: number } = {},
): FullLocusRows {
  const { locus, transcript_projection, feature_intervals, rendering_hints } = full
  const totalBases = locus.sequence.length
  const basesPerRow = clampBasesPerRow(
    rendering_hints.bases_per_row_min,
    rendering_hints.bases_per_row_max,
    opts.basesPerRow ?? DEFAULT_BASES_PER_ROW,
  )
  const rowCount = totalBases === 0 ? 0 : Math.ceil(totalBases / basesPerRow)

  const positionToOffset = (genomicPos: number): number => genomicPos - locus.start
  const offsetToRow = (offset: number): { row: number; col: number } => {
    const row = Math.floor(offset / basesPerRow)
    const col = offset - row * basesPerRow
    return { row, col }
  }

  const rows: FullLocusRow[] = []
  for (let rowIndex = 0; rowIndex < rowCount; rowIndex++) {
    const offsetStart = rowIndex * basesPerRow
    const offsetEnd = Math.min(offsetStart + basesPerRow, totalBases)
    rows.push({
      rowIndex,
      genomicStart: locus.start + offsetStart,
      genomicEnd: locus.start + offsetEnd - 1,
      bases: locus.sequence.slice(offsetStart, offsetEnd),
      bands: [],
      codonMarks: [],
      clinvarPins: [],
    })
  }

  for (const interval of transcript_projection.intervals) {
    const relStart = positionToOffset(interval.genomic_start)
    const relEnd = positionToOffset(interval.genomic_end) + 1
    const clampedStart = Math.max(0, relStart)
    const clampedEnd = Math.min(totalBases, relEnd)
    if (clampedEnd <= clampedStart) continue
    const firstRow = Math.floor(clampedStart / basesPerRow)
    const lastRow = Math.floor((clampedEnd - 1) / basesPerRow)
    const label = intervalLabel(interval)
    for (let row = firstRow; row <= lastRow; row++) {
      const rowOffsetStart = row * basesPerRow
      const rowOffsetEnd = rowOffsetStart + basesPerRow
      const colStart = Math.max(0, clampedStart - rowOffsetStart)
      const colEnd = Math.min(basesPerRow, clampedEnd - rowOffsetStart, rowOffsetEnd - rowOffsetStart)
      if (colEnd <= colStart) continue
      rows[row].bands.push({
        kind: interval.kind,
        colStart,
        colEnd,
        label,
        exonNumber: interval.exon_number ?? null,
        intronNumber: interval.intron_number ?? null,
      })
    }
  }

  for (const codon of transcript_projection.codon_starts) {
    const positions = codon.genomic_positions
    if (!positions || positions.length === 0) continue
    const offsetsByRow = new Map<number, number[]>()
    for (const pos of positions) {
      const offset = positionToOffset(pos)
      if (offset < 0 || offset >= totalBases) continue
      const { row, col } = offsetToRow(offset)
      const cols = offsetsByRow.get(row)
      if (cols) cols.push(col)
      else offsetsByRow.set(row, [col])
    }
    for (const [row, cols] of offsetsByRow) {
      cols.sort((a, b) => a - b)
      rows[row].codonMarks.push({
        codonNumber: codon.codon_number,
        proteinPosition: codon.protein_position,
        col: cols[0],
        basesInRow: cols.length,
      })
    }
  }

  let variantRowIndex: number | null = null

  for (const feature of feature_intervals) {
    if (isQueriedVariantFeature(feature.kind)) {
      const offset = positionToOffset(feature.start)
      if (offset < 0 || offset >= totalBases) continue
      const { row, col } = offsetToRow(offset)
      rows[row].variantPin = {
        col,
        label: featureLabel(feature),
        refBase: metadataString(feature, 'ref'),
        altBase: metadataString(feature, 'alt'),
        classification: classificationOf(feature),
      }
      variantRowIndex = row
    } else if (isClinvarFeature(feature.kind)) {
      const offset = positionToOffset(feature.start)
      if (offset < 0 || offset >= totalBases) continue
      const { row, col } = offsetToRow(offset)
      rows[row].clinvarPins.push({
        col,
        label: featureLabel(feature),
        classification: classificationOf(feature),
      })
    }
  }

  return {
    basesPerRow,
    rowCount,
    totalBases,
    variantRowIndex,
    rows,
    orientation: rendering_hints.orientation,
    chrom: locus.chrom,
    strand: locus.strand,
    genomeBuild: locus.genome_build,
    locusStart: locus.start,
    locusEnd: locus.end,
  }
}
