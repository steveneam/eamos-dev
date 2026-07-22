import { describe, expect, it } from 'vitest'
import type {
  CanonicalVariantRefV1,
  GeneViewerResponse,
  SelectionRangeV1,
} from '@/lib/backend'
import {
  buildWorkbenchDesignContext,
  buildWorkbenchContextDigest,
  canonicalJson,
  parseGenomicIdentity,
  selectedLocusSequence,
  selectionRangeFromViewer,
  sha256Hex,
} from './design-context'

const variant: CanonicalVariantRefV1 = {
  schema_version: 'canonical_variant_ref.v1',
  gene: 'RPE65',
  cdna: 'c.260A>G',
  transcript: 'NM_000329.3',
  protein_hgvs: 'p.Asp87Gly',
  genomic_hg38: 'NC_000001.11:g.68444869T>C',
  variant_key: '1-68444869-T-C',
  species: 'human',
  genome_build: 'GRCh38',
  resolution_status: 'resolved',
  source_support: ['variantvalidator', 'clinvar'],
  warnings: [],
}

const selection: SelectionRangeV1 = {
  schema_version: 'selection_range.v1',
  variant_key: '1-68444869-T-C',
  transcript: 'NM_000329.3',
  genome_build: 'GRCh38',
  chrom: 'chr1',
  genomic_start: 68_444_849,
  genomic_end: 68_444_889,
  strand: '+',
  orientation: 'transcript',
  sequence_basis: 'variant',
  edit_revision: 0,
  sequence_sha256: 'a'.repeat(64),
  cdna_start: 240,
  cdna_end: 280,
  cds_start: 240,
  cds_end: 280,
  protein_start: 80,
  protein_end: 94,
  overlaps: ['cds', 'exon'],
}

const reverseViewer = {
  identity: {
    gene: 'RPE65',
    resolved_transcript: 'NM_000329.3',
    requested_transcript: null,
    transcript_aliases: [],
    species: 'human',
    genome_build: 'GRCh38',
  },
  locus: { chrom: '1', gene_start: 100, gene_end: 104, strand: '-' },
  queried_variant: {
    hgvs_c: 'c.3G>A',
    hgvs_p: 'p.Gly1Asp',
    cds_pos: 3,
    genomic_hg38: '1-102-C-T',
    ref: 'G',
    alt: 'A',
    classification: 'vus',
  },
  full_locus: {
    basis: 'genomic_locus',
    locus: {
      chrom: '1',
      start: 100,
      end: 104,
      strand: '-',
      genome_build: 'GRCh38',
      sequence: 'AACGT',
      coordinate_system: 'genomic',
    },
    transcript_projection: {
      transcript: 'NM_000329.3',
      strand: '-',
      intervals: [
        {
          id: 'exon-1',
          kind: 'exon',
          label: 'Exon 1',
          genomic_start: 100,
          genomic_end: 104,
          strand: '-',
          exon_number: 1,
          cdna_start: 1,
          cdna_end: 5,
          cds_start: 1,
          cds_end: 5,
          protein_start: 1,
          protein_end: 2,
        },
        {
          id: 'cds-1',
          kind: 'cds',
          label: 'CDS',
          genomic_start: 100,
          genomic_end: 104,
          strand: '-',
          cdna_start: 1,
          cdna_end: 5,
          cds_start: 1,
          cds_end: 5,
          protein_start: 1,
          protein_end: 2,
        },
      ],
      coordinate_map: [
        {
          genomic_start: 100,
          genomic_end: 104,
          cdna_start: 1,
          cdna_end: 5,
          cds_start: 1,
          cds_end: 5,
          protein_start: 1,
          protein_end: 2,
        },
      ],
      codon_starts: [],
    },
    feature_intervals: [],
    rendering_hints: {
      orientation: 'transcript',
      row_coordinate_policy: 'transcript',
      bases_per_row_min: 1,
      bases_per_row_max: 120,
      base_color_scheme: 'nucleotide',
      amino_acid_color_scheme: 'biochemical',
    },
  },
  provenance: {
    sources: [{ name: 'variantvalidator' }],
    warnings: [],
  },
  } as unknown as GeneViewerResponse

const splitExonViewer = structuredClone(reverseViewer)
splitExonViewer.locus = { chrom: '1', gene_start: 100, gene_end: 105, strand: '+' }
splitExonViewer.full_locus!.locus = {
  ...splitExonViewer.full_locus!.locus,
  strand: '+',
  end: 105,
  sequence: 'AACGTT',
}
splitExonViewer.full_locus!.transcript_projection.strand = '+'
splitExonViewer.full_locus!.transcript_projection.coordinate_map = [
  {
    genomic_start: 100,
    genomic_end: 102,
    cdna_start: 1,
    cdna_end: 3,
    cds_start: 1,
    cds_end: 3,
    protein_start: 1,
    protein_end: 99,
  },
  {
    genomic_start: 103,
    genomic_end: 105,
    cdna_start: 4,
    cdna_end: 6,
    cds_start: 4,
    cds_end: 6,
    protein_start: 99,
    protein_end: 99,
  },
]

describe('Workbench design context', () => {
  it('matches the frozen Python canonical digest bytes', async () => {
    await expect(buildWorkbenchContextDigest(variant, selection)).resolves.toBe(
      '9efb20d9b43b2f9dcc8955d18a8d485e4f6bde905235fdb059dd7a4f24145038',
    )
  })

  it('sorts object keys recursively while preserving array order and unicode', () => {
    expect(canonicalJson({ z: ['β', { y: 2, a: 1 }], a: true })).toBe(
      '{"a":true,"z":["β",{"a":1,"y":2}]}',
    )
  })

  it('derives a stable genomic variant key and fails closed on prose', () => {
    expect(parseGenomicIdentity('chr1-68444869-T-C')).toEqual({
      chrom: 'chr1',
      position: 68_444_869,
      ref: 'T',
      alt: 'C',
      variantKey: '1-68444869-T-C',
    })
    expect(parseGenomicIdentity('NC_000001.11:g.68444869T>C', 'chr1')?.variantKey).toBe(
      '1-68444869-T-C',
    )
    expect(parseGenomicIdentity('not resolved', 'chr1')).toBeNull()
  })

  it('maps reverse-strand transcript orientation separately from genomic order', async () => {
    const draft = {
      genomicStart: 100,
      genomicEnd: 101,
      orientation: 'transcript' as const,
      sequenceBasis: 'reference' as const,
      baseAllele: 'reference' as const,
      editRevision: 0,
      edits: [],
    }
    expect(selectedLocusSequence(reverseViewer, draft)).toBe('TT')
    const range = await selectionRangeFromViewer(reverseViewer, {
      ...variant,
      cdna: 'c.3G>A',
      genomic_hg38: '1-102-C-T',
      variant_key: '1-102-C-T',
    }, draft)
    expect(range).toMatchObject({
      genomic_start: 100,
      genomic_end: 101,
      orientation: 'transcript',
      strand: '-',
      cdna_start: 4,
      cdna_end: 5,
      cds_start: 4,
      cds_end: 5,
      overlaps: ['cds', 'exon'],
    })
    await expect(sha256Hex('TT')).resolves.toBe(range?.sequence_sha256)
  })

  it('derives exact protein bounds from CDS bases on both strands', async () => {
    const forwardSingleBase = await selectionRangeFromViewer(splitExonViewer, variant, {
      genomicStart: 100,
      genomicEnd: 100,
      orientation: 'genomic_forward',
      sequenceBasis: 'reference',
      baseAllele: 'reference',
      editRevision: 0,
      edits: [],
    })
    expect(forwardSingleBase).toMatchObject({
      cds_start: 1,
      cds_end: 1,
      protein_start: 1,
      protein_end: 1,
    })

    const forwardCodon = await selectionRangeFromViewer(splitExonViewer, variant, {
      genomicStart: 100,
      genomicEnd: 102,
      orientation: 'genomic_forward',
      sequenceBasis: 'reference',
      baseAllele: 'reference',
      editRevision: 0,
      edits: [],
    })
    expect(forwardCodon).toMatchObject({
      cds_start: 1,
      cds_end: 3,
      protein_start: 1,
      protein_end: 1,
    })

    const acrossExonBoundary = await selectionRangeFromViewer(splitExonViewer, variant, {
      genomicStart: 102,
      genomicEnd: 103,
      orientation: 'genomic_forward',
      sequenceBasis: 'reference',
      baseAllele: 'reference',
      editRevision: 0,
      edits: [],
    })
    expect(acrossExonBoundary).toMatchObject({
      cds_start: 3,
      cds_end: 4,
      protein_start: 1,
      protein_end: 2,
    })

    const reverseSingleBase = await selectionRangeFromViewer(reverseViewer, {
      ...variant,
      cdna: 'c.3G>A',
      genomic_hg38: '1-102-C-T',
      variant_key: '1-102-C-T',
    }, {
      genomicStart: 104,
      genomicEnd: 104,
      orientation: 'transcript',
      sequenceBasis: 'reference',
      baseAllele: 'reference',
      editRevision: 0,
      edits: [],
    })
    expect(reverseSingleBase).toMatchObject({
      cds_start: 1,
      cds_end: 1,
      protein_start: 1,
      protein_end: 1,
    })
  })

  it('builds a complete resolved design context and binds an edited revision', async () => {
    const context = await buildWorkbenchDesignContext(reverseViewer, {
      genomicStart: 102,
      genomicEnd: 103,
      orientation: 'genomic_forward',
      sequenceBasis: 'edited',
      baseAllele: 'reference',
      editRevision: 1,
      edits: [{ genomicPosition: 103, kind: 'sub', alt: 'A' }],
    })
    expect(context).toMatchObject({
      schema_version: 'workbench_design_context.v1',
      variant: { variant_key: '1-102-C-T', resolution_status: 'resolved' },
      selection: {
        genomic_start: 102,
        genomic_end: 103,
        sequence_basis: 'edited',
        edit_revision: 1,
      },
    })
    expect(context?.context_digest).toMatch(/^[0-9a-f]{64}$/)
  })

  it('fails closed for empty overlap, invalid revision, and unsupported variant basis', async () => {
    const noOverlap = structuredClone(reverseViewer)
    noOverlap.full_locus!.transcript_projection.intervals = []
    await expect(buildWorkbenchDesignContext(noOverlap, {
      genomicStart: 100,
      genomicEnd: 101,
      orientation: 'genomic_forward',
      sequenceBasis: 'reference',
      baseAllele: 'reference',
      editRevision: 0,
      edits: [],
    })).resolves.toBeNull()

    await expect(buildWorkbenchDesignContext(reverseViewer, {
      genomicStart: 100,
      genomicEnd: 101,
      orientation: 'genomic_forward',
      sequenceBasis: 'edited',
      baseAllele: 'reference',
      editRevision: 0,
      edits: [{ genomicPosition: 100, kind: 'sub', alt: 'T' }],
    })).resolves.toBeNull()

    const indel = structuredClone(reverseViewer)
    indel.queried_variant.genomic_hg38 = '1-102-C-CT'
    expect(selectedLocusSequence(indel, {
      genomicStart: 102,
      genomicEnd: 102,
      orientation: 'genomic_forward',
      sequenceBasis: 'variant',
      baseAllele: 'variant',
      editRevision: 0,
      edits: [],
    })).toBeNull()
  })
})
