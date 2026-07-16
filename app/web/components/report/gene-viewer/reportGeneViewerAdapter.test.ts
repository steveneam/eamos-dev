import { describe, expect, it } from 'vitest'

import type { GeneContextSnapshot, ProteinAlphaMissenseHeatmap } from '@/lib/backend'
import { adaptGeneViewer } from '@/lib/workbench/gene-viewer-adapter'
import { GENE_VIEWER_SAMPLE } from '@/lib/workbench/gene-viewer-sample'

import { adaptGeneContextSnapshot } from './reportGeneViewerAdapter'
import {
  shouldFetchViewerPayload,
  viewerFetchWarning,
} from './useReportGeneViewer'

const SNAPSHOT: GeneContextSnapshot = {
  section_number: 4,
  section_id: 'gene_context',
  panel_id: 'gene_context',
  title: 'Gene context',
  source_status: 'cache',
  gene: 'RPE65',
  transcript: 'NM_000329.3',
  transcript_aliases: ['NM_000329.3'],
  genome_build: 'GRCh38',
  chromosome: 'chr1',
  strand: '-',
  ensembl_gene_id: 'ENSG00000116745',
  gene_start: 100,
  gene_end: 399,
  cds_length: 12,
  protein_length: 4,
  exons: [
    {
      number: 1,
      cds_start: 1,
      cds_end: 6,
      genomic_start: 300,
      genomic_end: 305,
      transcript_start: 1,
      transcript_end: 6,
    },
    {
      number: 2,
      cds_start: 7,
      cds_end: 12,
      genomic_start: 200,
      genomic_end: 205,
      transcript_start: 107,
      transcript_end: 112,
    },
  ],
  introns: [
    {
      number: 1,
      genomic_start: 206,
      genomic_end: 299,
      length_bp: 94,
      transcript_start: 7,
      transcript_end: 106,
    },
  ],
  variant: {
    hgvs_c: 'c.8G>A',
    hgvs_p: 'p.Gly3Asp',
    cds_pos: 8,
    ref: 'n',
    alt: 'g',
    membership: 'exon',
    codon_number: 3,
    codon_offset: 1,
    aa_ref: 'G',
    aa_alt: 'D',
    warnings: [],
  },
  zoom_segments: [
    {
      id: 'exon-1',
      kind: 'exon',
      label: 'Exon 1',
      exon_number: 1,
      cds_start: 1,
      cds_end: 6,
      strand: '-',
      sequence: 'AAACCC',
      five_prime_sequence: '',
      three_prime_sequence: '',
      omitted_bp: 0,
    },
    {
      id: 'intron-1',
      kind: 'intron',
      label: 'Intron 1',
      intron_number: 1,
      strand: '-',
      sequence: '',
      five_prime_sequence: 'GT',
      three_prime_sequence: 'AG',
      omitted_bp: 90,
    },
  ],
  render_hints: {
    overview_mode: 'compressed_introns',
    min_exon_width_px: 14,
    max_intron_width_px: 60,
    zoom_flank_bp: 30,
    large_gene_compression_applied: false,
    warnings: [],
  },
  workbench_link: {
    url: '/workbench?q=RPE65:c.8G>A',
    gene: 'RPE65',
    cdna: 'c.8G>A',
    transcript: 'NM_000329.3',
  },
  provenance: [],
  warnings: [],
}

const AVAILABLE_HEATMAP: ProteinAlphaMissenseHeatmap = {
  status: 'available',
  protein_length: 4,
  aa_start: 1,
  aa_end: 4,
  source_id: 'alphamissense',
  residues: [],
  warnings: [],
}

describe('report gene viewer snapshot adapter', () => {
  it('preserves the report snapshot identity, structure, and marker semantics', () => {
    const adapted = adaptGeneContextSnapshot(SNAPSHOT, 'Likely pathogenic')

    expect(adapted).toMatchObject({
      gene: 'RPE65',
      transcript: 'NM_000329.3',
      nativeStrand: 'reverse',
      geneLength: 300,
      totalExons: 2,
      cdsLength: 12,
      proteinLength: 4,
      mrnaLength: 112,
      architectureScope: 'transcript',
      queriedVariant: {
        cdsPos: 8,
        refBase: 'A',
        altBase: 'G',
        hgvsC: 'c.8G>A',
        hgvsP: 'p.Gly3Asp',
        classification: 'lp',
      },
      genomicCoords: {
        chrom: 'chr1',
        start: 100,
        end: 399,
        strand: '-',
      },
    })
    expect(adapted.exons.map((exon) => [exon.num, exon.cdsStart, exon.cdsEnd])).toEqual([
      [1, 1, 6],
      [2, 7, 12],
    ])
    expect(adapted.introns).toEqual([{ num: 1, lenBp: 94 }])
    expect(adapted.windowSegments).toEqual([
      { kind: 'exon', exonNum: 1, cdsStart: 1, cdsEnd: 6, seq: 'AAACCC' },
      { kind: 'intron', intronNum: 1, totalLen: 94, fiveSeq: 'GT', threeSeq: 'AG' },
    ])
  })
})

describe('report gene viewer controller decisions', () => {
  const seededData = adaptGeneViewer(GENE_VIEWER_SAMPLE, 'variant', {
    architecture: 'transcript',
  })

  it('fetches only when the base payload or an enabled AlphaMissense track is missing', () => {
    expect(
      shouldFetchViewerPayload({
        demo: true,
        includeAlphaMissense: true,
        seededData: null,
        alphaHeatmap: null,
      }),
    ).toBe(false)
    expect(
      shouldFetchViewerPayload({
        demo: false,
        includeAlphaMissense: false,
        seededData: null,
        alphaHeatmap: null,
      }),
    ).toBe(true)
    expect(
      shouldFetchViewerPayload({
        demo: false,
        includeAlphaMissense: false,
        seededData,
        alphaHeatmap: null,
      }),
    ).toBe(false)
    expect(
      shouldFetchViewerPayload({
        demo: false,
        includeAlphaMissense: true,
        seededData,
        alphaHeatmap: null,
      }),
    ).toBe(true)
    expect(
      shouldFetchViewerPayload({
        demo: false,
        includeAlphaMissense: true,
        seededData,
        alphaHeatmap: AVAILABLE_HEATMAP,
      }),
    ).toBe(false)
  })

  it('normalizes live-request errors into a stable provenance warning', () => {
    expect(viewerFetchWarning(new Error('  backend   unavailable  '))).toBe(
      'gene_viewer_live_request_failed:backend unavailable',
    )
  })
})
