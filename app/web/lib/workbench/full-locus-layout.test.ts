import { describe, expect, it } from 'vitest'
import type { ViewerFullLocus } from '@/lib/backend'
import { buildFullLocusRows, genomicPositionAt } from './full-locus-layout'

const locus: ViewerFullLocus = {
  basis: 'genomic_locus',
  locus: {
    chrom: 'chr1',
    start: 100,
    end: 109,
    strand: '-',
    genome_build: 'GRCh38',
    sequence: 'AACCGGTTAA',
    coordinate_system: 'genomic',
  },
  transcript_projection: {
    transcript: 'NM_TEST.1',
    strand: '-',
    intervals: [
      {
        id: 'utr3',
        kind: 'utr3',
        label: "3' UTR",
        genomic_start: 100,
        genomic_end: 101,
        strand: '-',
      },
      {
        id: 'intron',
        kind: 'intron',
        label: 'Intron 1',
        genomic_start: 102,
        genomic_end: 105,
        strand: '-',
        intron_number: 1,
      },
      {
        id: 'exon',
        kind: 'exon',
        label: 'Exon 2',
        genomic_start: 106,
        genomic_end: 109,
        strand: '-',
        exon_number: 2,
      },
      {
        id: 'utr5',
        kind: 'utr5',
        label: "5' UTR",
        genomic_start: 106,
        genomic_end: 107,
        strand: '-',
      },
      {
        id: 'cds',
        kind: 'cds',
        label: 'CDS',
        genomic_start: 107,
        genomic_end: 109,
        strand: '-',
      },
    ],
    coordinate_map: [],
    codon_starts: [],
  },
  feature_intervals: [
    {
      id: 'query',
      kind: 'queried_variant',
      label: 'query',
      coordinate_system: 'genomic',
      start: 108,
      end: 108,
      strand: '-',
      metadata: { ref: 'A', alt: 'G' },
    },
  ],
  rendering_hints: {
    orientation: 'transcript',
    row_coordinate_policy: 'transcript',
    bases_per_row_min: 2,
    bases_per_row_max: 10,
    base_color_scheme: 'nucleotide',
    amino_acid_color_scheme: 'biochemical',
  },
}

describe('full-locus orientation', () => {
  it('keeps genomic-forward coordinates ascending', () => {
    const rows = buildFullLocusRows(locus, { basesPerRow: 5, orientation: 'genomic_forward' })
    expect(rows.displaySequence).toBe('AACCGGTTAA')
    expect(rows.rows[0]).toMatchObject({ genomicStart: 100, genomicEnd: 104 })
    expect(genomicPositionAt(rows, 8)).toBe(108)
  })

  it('renders reverse-strand transcript orientation as reverse complement', () => {
    const rows = buildFullLocusRows(locus, { basesPerRow: 5, orientation: 'transcript' })
    expect(rows.displaySequence).toBe('TTAACCGGTT')
    expect(rows.rows[0]).toMatchObject({ genomicStart: 109, genomicEnd: 105 })
    expect(genomicPositionAt(rows, 1)).toBe(108)
    expect(rows.variantRowIndex).toBe(0)
    expect(rows.navigationTargets.find((target) => target.id === 'exon')?.rowIndex).toBe(0)
    expect(new Set(rows.navigationTargets.map((target) => target.kind))).toEqual(
      new Set(['utr3', 'intron', 'exon', 'utr5', 'cds']),
    )
  })
})
