import { describe, expect, it } from 'vitest'
import type { GeneViewerResponse } from '@/lib/backend'
import { buildFlatWindow, type GeneWindowData } from './gene-window'
import { RPE65_V2 } from './sample-rpe65-v2'
import {
  designDraftFromWindow,
  genomicPositionForFlatBase,
  windowStateFromDesignDraft,
  type WindowDesignState,
} from './window-design-context'

function windowData(strand: 'forward' | 'reverse'): GeneWindowData {
  return {
    ...RPE65_V2,
    nativeStrand: strand,
    genomicCoords: {
      chrom: 'chr1',
      start: 100,
      end: 111,
      strand: strand === 'reverse' ? '-' : '+',
    },
    windowSegments: [
      { kind: 'exon', exonNum: 1, cdsStart: 1, cdsEnd: 3, seq: 'ATG' },
      {
        kind: 'intron',
        intronNum: 1,
        totalLen: 6,
        fiveSeq: 'gt',
        threeSeq: 'ag',
      },
      { kind: 'exon', exonNum: 2, cdsStart: 4, cdsEnd: 6, seq: 'GAA' },
    ],
  }
}

function viewer(strand: '+' | '-'): GeneViewerResponse {
  const reverse = strand === '-'
  return {
    full_locus: {
      transcript_projection: {
        transcript: 'NM_000329.3',
        strand,
        coordinate_map: reverse
          ? [
              { genomic_start: 109, genomic_end: 111, cds_start: 1, cds_end: 3 },
              { genomic_start: 100, genomic_end: 102, cds_start: 4, cds_end: 6 },
            ]
          : [
              { genomic_start: 100, genomic_end: 102, cds_start: 1, cds_end: 3 },
              { genomic_start: 109, genomic_end: 111, cds_start: 4, cds_end: 6 },
            ],
        intervals: [
          {
            id: 'intron-1',
            kind: 'intron',
            label: 'Intron 1',
            intron_number: 1,
            genomic_start: 103,
            genomic_end: 108,
            strand,
          },
        ],
        codon_starts: [],
      },
    },
  } as unknown as GeneViewerResponse
}

function indexFor(
  data: GeneWindowData,
  predicate: (base: ReturnType<typeof buildFlatWindow>[number]) => boolean,
): number {
  return buildFlatWindow(data).findIndex(predicate)
}

describe('window/full-locus design bridge', () => {
  it('maps plus-strand exons and both donor/acceptor intron flanks', () => {
    const data = windowData('forward')
    const response = viewer('+')
    const flat = buildFlatWindow(data)
    expect(genomicPositionForFlatBase(response, flat[indexFor(data, (base) => base.kind === 'exon' && base.cdsPos === 1)])).toBe(100)
    expect(genomicPositionForFlatBase(response, flat[indexFor(data, (base) => base.kind === 'exon' && base.cdsPos === 6)])).toBe(111)
    expect(genomicPositionForFlatBase(response, flat[indexFor(data, (base) => base.kind === 'intron' && base.intronEnd === '5prime' && base.intronOffset === 1)])).toBe(103)
    expect(genomicPositionForFlatBase(response, flat[indexFor(data, (base) => base.kind === 'intron' && base.intronEnd === '3prime' && base.intronOffset === -1)])).toBe(108)
  })

  it('maps reverse-strand exons and transcript donor/acceptor flanks', () => {
    const data = windowData('reverse')
    const response = viewer('-')
    const flat = buildFlatWindow(data)
    expect(genomicPositionForFlatBase(response, flat[indexFor(data, (base) => base.kind === 'exon' && base.cdsPos === 1)])).toBe(111)
    expect(genomicPositionForFlatBase(response, flat[indexFor(data, (base) => base.kind === 'exon' && base.cdsPos === 6)])).toBe(100)
    expect(genomicPositionForFlatBase(response, flat[indexFor(data, (base) => base.kind === 'intron' && base.intronEnd === '5prime' && base.intronOffset === 1)])).toBe(108)
    expect(genomicPositionForFlatBase(response, flat[indexFor(data, (base) => base.kind === 'intron' && base.intronEnd === '3prime' && base.intronOffset === -1)])).toBe(103)
  })

  it('orients reverse-strand substitutions and insertions and round-trips them', () => {
    const data = windowData('reverse')
    const response = viewer('-')
    const exonIndex = indexFor(data, (base) => base.kind === 'exon' && base.cdsPos === 1)
    const state: WindowDesignState = {
      selection: { start: exonIndex, end: exonIndex },
      edits: [
        { flatIndex: exonIndex, kind: 'sub', alt: 'A' },
        { flatIndex: exonIndex + 1, kind: 'ins', alt: 'AG' },
      ],
      editRevision: 2,
    }
    const draft = designDraftFromWindow(response, data, state, 'reference', 'transcript')
    expect(draft).toMatchObject({
      genomicStart: 111,
      genomicEnd: 111,
      sequenceBasis: 'edited',
      editRevision: 2,
      edits: [
        { genomicPosition: 110, kind: 'ins', alt: 'CT' },
        { genomicPosition: 111, kind: 'sub', alt: 'T' },
      ],
    })
    expect(windowStateFromDesignDraft(response, data, draft)).toEqual(state)
  })

  it('fails closed when a full-locus selection or edit is outside the cropped window', () => {
    const data = windowData('forward')
    const response = viewer('+')
    expect(windowStateFromDesignDraft(response, data, {
      genomicStart: 90,
      genomicEnd: 91,
      orientation: 'genomic_forward',
      sequenceBasis: 'reference',
      baseAllele: 'reference',
      editRevision: 0,
      edits: [],
    })).toBeNull()

    expect(windowStateFromDesignDraft(response, data, {
      genomicStart: 100,
      genomicEnd: 101,
      orientation: 'genomic_forward',
      sequenceBasis: 'edited',
      baseAllele: 'reference',
      editRevision: 1,
      edits: [{ genomicPosition: 999, kind: 'sub', alt: 'A' }],
    })).toBeNull()
  })
})
