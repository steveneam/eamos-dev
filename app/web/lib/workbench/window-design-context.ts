import type {
  GeneViewerResponse,
  SelectionOrientationV1,
} from '@/lib/backend'
import {
  buildFlatWindow,
  type FlatBase,
  type GeneWindowData,
} from './gene-window'
import type { DesignSelectionDraft, LocusEditV1 } from './design-context'

export interface WindowDesignEdit {
  flatIndex: number
  kind: 'sub' | 'del' | 'ins'
  alt: string
}

export interface WindowDesignState {
  selection: { start: number; end: number } | null
  edits: WindowDesignEdit[]
  editRevision: number
}

function complement(sequence: string): string {
  const bases: Record<string, string> = { A: 'T', C: 'G', G: 'C', T: 'A', N: 'N' }
  return sequence
    .toUpperCase()
    .split('')
    .map((base) => bases[base] ?? 'N')
    .join('')
}

function reverseComplement(sequence: string): string {
  return complement(sequence).split('').reverse().join('')
}

export function genomicPositionForFlatBase(
  response: GeneViewerResponse,
  base: FlatBase | undefined,
): number | null {
  const projection = response.full_locus?.transcript_projection
  if (!projection || !base || base.kind === 'intron-gap' || projection.strand === 'unknown') {
    return null
  }
  const reverse = projection.strand === '-'
  if (base.kind === 'exon') {
    const range = projection.coordinate_map.find((item) => {
      if (item.cds_start == null || item.cds_end == null) return false
      const low = Math.min(item.cds_start, item.cds_end)
      const high = Math.max(item.cds_start, item.cds_end)
      return base.cdsPos >= low && base.cdsPos <= high
    })
    if (!range || range.cds_start == null || range.cds_end == null) return null
    const cdsLow = Math.min(range.cds_start, range.cds_end)
    const genomicLow = Math.min(range.genomic_start, range.genomic_end)
    const genomicHigh = Math.max(range.genomic_start, range.genomic_end)
    return reverse
      ? genomicHigh - (base.cdsPos - cdsLow)
      : genomicLow + (base.cdsPos - cdsLow)
  }

  const intron = projection.intervals.find(
    (item) => item.kind === 'intron' && item.intron_number === base.intronNum,
  )
  if (!intron) return null
  const genomicLow = Math.min(intron.genomic_start, intron.genomic_end)
  const genomicHigh = Math.max(intron.genomic_start, intron.genomic_end)
  if (base.intronEnd === '5prime') {
    const delta = Math.max(0, base.intronOffset - 1)
    return reverse ? genomicHigh - delta : genomicLow + delta
  }
  const delta = Math.max(0, Math.abs(base.intronOffset) - 1)
  return reverse ? genomicLow + delta : genomicHigh - delta
}

export function designDraftFromWindow(
  response: GeneViewerResponse,
  data: GeneWindowData,
  state: WindowDesignState,
  baseAllele: 'reference' | 'variant',
  orientation: SelectionOrientationV1,
): DesignSelectionDraft | null {
  if (!state.selection) return null
  const flat = buildFlatWindow(data)
  const lowIndex = Math.min(state.selection.start, state.selection.end)
  const highIndex = Math.max(state.selection.start, state.selection.end)
  const start = genomicPositionForFlatBase(response, flat[lowIndex])
  const end = genomicPositionForFlatBase(response, flat[highIndex])
  if (start == null || end == null || state.edits.length > 500) return null
  const reverse = response.full_locus?.transcript_projection.strand === '-'
  const edits: LocusEditV1[] = []
  for (const edit of state.edits) {
    const genomicPosition = genomicPositionForFlatBase(response, flat[edit.flatIndex])
    if (genomicPosition == null) return null
    const inputAlt = edit.alt.replace(/\s+/g, '').toUpperCase()
    const alt = reverse
      ? edit.kind === 'ins'
        ? reverseComplement(inputAlt)
        : complement(inputAlt)
      : inputAlt
    edits.push({ genomicPosition, kind: edit.kind, alt: edit.kind === 'del' ? '' : alt })
  }
  edits.sort((left, right) => left.genomicPosition - right.genomicPosition)
  return {
    genomicStart: Math.min(start, end),
    genomicEnd: Math.max(start, end),
    orientation,
    sequenceBasis: edits.length > 0 ? 'edited' : baseAllele,
    baseAllele,
    editRevision: edits.length > 0 ? Math.max(1, state.editRevision) : 0,
    edits,
  }
}

export function windowStateFromDesignDraft(
  response: GeneViewerResponse,
  data: GeneWindowData,
  draft: DesignSelectionDraft | null,
): WindowDesignState | null {
  if (!draft) return null
  const flat = buildFlatWindow(data)
  const genomicToFlat = new Map<number, number>()
  for (const base of flat) {
    const genomic = genomicPositionForFlatBase(response, base)
    if (genomic != null) genomicToFlat.set(genomic, base.flatPos)
  }
  const selectionStart = genomicToFlat.get(draft.genomicStart)
  const selectionEnd = genomicToFlat.get(draft.genomicEnd)
  if (selectionStart == null || selectionEnd == null) return null
  const reverse = response.full_locus?.transcript_projection.strand === '-'
  const edits: WindowDesignEdit[] = []
  for (const edit of draft.edits) {
    const flatIndex = genomicToFlat.get(edit.genomicPosition)
    if (flatIndex == null) return null
    const alt = reverse
      ? edit.kind === 'ins'
        ? reverseComplement(edit.alt)
        : complement(edit.alt)
      : edit.alt
    edits.push({ flatIndex, kind: edit.kind, alt: edit.kind === 'del' ? '' : alt })
  }
  edits.sort((left, right) => left.flatIndex - right.flatIndex)
  return {
    selection: { start: selectionStart, end: selectionEnd },
    edits,
    editRevision: edits.length > 0 ? Math.max(1, draft.editRevision) : 0,
  }
}
