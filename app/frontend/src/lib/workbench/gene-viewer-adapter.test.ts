import { describe, expect, it } from 'vitest'
import type { GeneViewerResponse, VariantClassification } from '../backend'
import {
  adaptGeneViewer,
  geneViewerScaffoldWarnings,
} from './gene-viewer-adapter'
import { GENE_VIEWER_SAMPLE } from './gene-viewer-sample'
import { RPE65_V2 } from './sample-rpe65-v2'

/** c.260 sits in the exon-4 segment (cds 232–324) at offset 28. */
const EXON4_OFFSET_260 = 260 - 232

const GENERIC_VIEWER_RESPONSE: GeneViewerResponse = {
  ...GENE_VIEWER_SAMPLE,
  identity: {
    gene: 'CFTR',
    ensembl_gene_id: 'ENSG00000001626',
    requested_transcript: null,
    resolved_transcript: 'ENSTGENERIC.1',
    transcript_aliases: ['ENSTGENERIC.1', 'NM_GENERIC.1'],
    species: 'human',
    genome_build: 'GRCh38',
  },
  locus: {
    chrom: 'chr7',
    gene_start: 90,
    gene_end: 210,
    strand: '+',
  },
  summary: {
    gene_length: 121,
    total_exons: 2,
    cds_length: 12,
    protein_length: 4,
    utr5_length: null,
    utr3_length: null,
    mrna_length: 12,
  },
  window: {
    kind: 'cds_range',
    cds_start: 1,
    cds_end: 12,
    cds_flank_bp: 0,
    intron_flank_bp: 0,
    display_cds_start: 1,
    display_cds_end: 12,
    total_display_bases: 12,
  },
  segments: [
    {
      id: 'exon-1:1-6',
      kind: 'exon',
      label: 'Exon 1',
      exon_number: 1,
      intron_number: null,
      cds_start: 1,
      cds_end: 6,
      genomic_start: 100,
      genomic_end: 105,
      strand: '+',
      sequence: 'AAACCC',
      five_prime_sequence: '',
      three_prime_sequence: '',
      omitted_bp: 0,
    },
    {
      id: 'intron-1',
      kind: 'intron',
      label: 'Intron 1',
      exon_number: null,
      intron_number: 1,
      cds_start: null,
      cds_end: null,
      genomic_start: 106,
      genomic_end: 199,
      strand: '+',
      sequence: '',
      five_prime_sequence: '',
      three_prime_sequence: '',
      omitted_bp: 94,
    },
    {
      id: 'exon-2:7-12',
      kind: 'exon',
      label: 'Exon 2',
      exon_number: 2,
      intron_number: null,
      cds_start: 7,
      cds_end: 12,
      genomic_start: 200,
      genomic_end: 205,
      strand: '+',
      sequence: 'GGGTTT',
      five_prime_sequence: '',
      three_prime_sequence: '',
      omitted_bp: 0,
    },
  ],
  queried_variant: {
    hgvs_c: 'c.8G>A',
    hgvs_p: null,
    cds_pos: 8,
    genomic_hg38: '7-200-G-A',
    ref: 'G',
    alt: 'A',
    codon_number: 3,
    codon_offset: 1,
    aa_ref: null,
    aa_alt: null,
    classification: 'unknown',
  },
  sequences: {
    allele_mode: 'reference',
    reference_window_sequence: 'AAACCCGGGTTT',
    display_window_sequence: 'AAACCCGGGTTT',
    applied_variant: null,
  },
  tracks: {
    clinvar_variants: [],
    exon_density: [],
    protein_features: {
      signal_peptide: null,
      transmembrane: [],
      domains: [],
      active_sites: [],
      membrane_binding: [],
      palmitoylation: [],
    },
    conservation_values: [],
    restriction_sites: [],
    features: [],
  },
  provenance: {
    sources: [{ name: 'ensembl_rest', identifier: 'ENSTGENERIC.1' }],
    warnings: ['mocked_generic_source'],
  },
}

function exon4(data: ReturnType<typeof adaptGeneViewer>) {
  const seg = data.windowSegments.find(
    (s) => s.kind === 'exon' && s.exonNum === 4,
  )
  if (!seg || seg.kind !== 'exon') throw new Error('exon-4 segment missing')
  return seg
}

describe('adaptGeneViewer — fixture parity with RPE65_V2 (hybrid)', () => {
  const data = adaptGeneViewer(GENE_VIEWER_SAMPLE)

  it('maps identity / locus', () => {
    expect(data.gene).toBe('RPE65')
    expect(data.transcript).toBe('NM_000329.3')
    expect(data.ensg).toBe('ENSG00000116745')
    expect(data.chrom).toBe('chr1')
    expect(data.nativeStrand).toBe('reverse')
    expect(data.genomicCoords.strand).toBe('-')
  })

  it('maps the summary numbers from the payload', () => {
    expect(data.geneLength).toBe(RPE65_V2.geneLength)
    expect(data.totalExons).toBe(14)
    expect(data.cdsLength).toBe(RPE65_V2.cdsLength)
    expect(data.proteinLength).toBe(RPE65_V2.proteinLength)
    expect(data.mrnaLength).toBe(RPE65_V2.mrnaLength)
  })

  it('fills whole-gene exon/intron/conservation from the sample scaffold', () => {
    expect(data.exons).toEqual(RPE65_V2.exons)
    expect(data.introns).toEqual(RPE65_V2.introns)
    expect(data.conservation).toEqual(RPE65_V2.conservation)
  })

  it('reproduces RPE65_V2 windowSegments in reference mode', () => {
    expect(data.windowSegments).toEqual(RPE65_V2.windowSegments)
  })

  it('reproduces the queried variant metadata', () => {
    expect(data.queriedVariant).toEqual(RPE65_V2.queriedVariant)
  })

  it('maps restriction sites and oligo features faithfully', () => {
    expect(data.restriction).toEqual(RPE65_V2.restriction)
    expect(data.features).toEqual(RPE65_V2.features)
  })

  it('maps protein domains from the backend payload (authoritative)', () => {
    expect(data.domains).toEqual([
      {
        aaStart: 51,
        aaEnd: 468,
        label: 'Carotenoid oxygenase (RPE65 catalytic)',
        shortLabel: 'Carotenoid oxygenase',
      },
    ])
    expect(data.proteinFeatures.activeSites).toHaveLength(4)
    expect(data.proteinFeatures.palmitoylation[0]).toEqual({
      aa: 231,
      residue: 'C',
      label: 'S-palmitoyl cysteine (membrane anchor)',
    })
    expect(data.proteinFeatures.signalPeptide).toBeNull()
  })

  it('maps the window-bounded ClinVar subset (sample-bounded, 5 entries)', () => {
    expect(data.clinvar).toHaveLength(5)
    const queried = data.clinvar.find((v) => v.queried)
    expect(queried).toEqual({
      cdsPos: 260,
      hgvsC: 'c.260A>G',
      hgvsP: 'p.Asp87Gly',
      cls: 'lp',
      cv: 'VCV000099473',
      queried: true,
      splice: false,
    })
    const splice = data.clinvar.find((v) => v.splice)
    expect(splice?.cdsPos).toBe('325-2')
  })

  it('maps exon variant density', () => {
    expect(data.exonVariantCount[4]).toBe(46)
    expect(data.exonVariantCount[14]).toBe(11)
  })
})

describe('adaptGeneViewer — allele mode overlay', () => {
  it('reference mode keeps c.260 as the ref base A', () => {
    const data = adaptGeneViewer(GENE_VIEWER_SAMPLE, 'reference')
    expect(exon4(data).seq[EXON4_OFFSET_260]).toBe('A')
  })

  it('variant mode flips c.260 to the alt base G, labels preserved', () => {
    const data = adaptGeneViewer(GENE_VIEWER_SAMPLE, 'variant')
    const seg = exon4(data)
    expect(seg.seq[EXON4_OFFSET_260]).toBe('G')
    // Only that one base changes.
    const ref = exon4(adaptGeneViewer(GENE_VIEWER_SAMPLE, 'reference')).seq
    expect(seg.seq.length).toBe(ref.length)
    let diffs = 0
    for (let i = 0; i < ref.length; i++) if (seg.seq[i] !== ref[i]) diffs++
    expect(diffs).toBe(1)
    // Variant labels/coordinates are unchanged by the overlay.
    expect(data.queriedVariant.hgvsC).toBe('c.260A>G')
    expect(data.queriedVariant.hgvsP).toBe('p.Asp87Gly')
    expect(data.queriedVariant.refBase).toBe('A')
    expect(data.queriedVariant.altBase).toBe('G')
  })

  it('defaults the allele mode to the payload value', () => {
    // GENE_VIEWER_SAMPLE.sequences.allele_mode === 'reference'
    const data = adaptGeneViewer(GENE_VIEWER_SAMPLE)
    expect(exon4(data).seq[EXON4_OFFSET_260]).toBe('A')
  })
})

describe('adaptGeneViewer — non-RPE65 live payloads', () => {
  it('uses backend window segments without importing the RPE65 scaffold', () => {
    const data = adaptGeneViewer(GENERIC_VIEWER_RESPONSE, 'variant')

    expect(data.gene).toBe('CFTR')
    expect(data.transcript).toBe('ENSTGENERIC.1')
    expect(data.nativeStrand).toBe('forward')
    expect(data.exons).toEqual([
      { num: 1, cdsStart: 1, cdsEnd: 6, genomicLen: 6 },
      { num: 2, cdsStart: 7, cdsEnd: 12, genomicLen: 6 },
    ])
    expect(data.introns).toEqual([{ num: 1, lenBp: 94 }])
    expect(data.conservation).toEqual([])
    expect(data.windowSegments).toEqual([
      { kind: 'exon', exonNum: 1, cdsStart: 1, cdsEnd: 6, seq: 'AAACCC' },
      { kind: 'intron', intronNum: 1, totalLen: 94, fiveSeq: '', threeSeq: '' },
      { kind: 'exon', exonNum: 2, cdsStart: 7, cdsEnd: 12, seq: 'GAGTTT' },
    ])
  })
})

describe('adaptGeneViewer — classification mapping', () => {
  const cases: Array<[VariantClassification, string]> = [
    ['pathogenic', 'p'],
    ['likely_pathogenic', 'lp'],
    ['vus', 'vus'],
    ['likely_benign', 'lb'],
    ['benign', 'b'],
    ['unknown', 'vus'],
  ]
  it.each(cases)('maps %s → %s', (input, expected) => {
    const resp: GeneViewerResponse = {
      ...GENE_VIEWER_SAMPLE,
      queried_variant: {
        ...GENE_VIEWER_SAMPLE.queried_variant,
        classification: input,
      },
    }
    expect(adaptGeneViewer(resp).queriedVariant.classification).toBe(expected)
  })
})

describe('geneViewerScaffoldWarnings', () => {
  it('keeps backend warnings and names the sample-scaffolded fields', () => {
    const w = geneViewerScaffoldWarnings(GENE_VIEWER_SAMPLE)
    expect(w).toContain('offline_fixture_not_live_source_backed')
    expect(w).toContain('clinvar_track_is_sample_bounded')
    expect(w).toContain('exon_intron_table_from_sample_scaffold')
    expect(w).toContain('conservation_from_sample_scaffold')
  })

  it('drops the conservation warning when the payload carries values', () => {
    const resp: GeneViewerResponse = {
      ...GENE_VIEWER_SAMPLE,
      tracks: { ...GENE_VIEWER_SAMPLE.tracks, conservation_values: [0.5, 0.6] },
    }
    const w = geneViewerScaffoldWarnings(resp)
    expect(w).not.toContain('conservation_from_sample_scaffold')
    expect(w).toContain('exon_intron_table_from_sample_scaffold')
  })

  it('does not report sample-scaffolded fields for non-RPE65 payloads', () => {
    const w = geneViewerScaffoldWarnings(GENERIC_VIEWER_RESPONSE)
    expect(w).toContain('mocked_generic_source')
    expect(w).toContain('exon_intron_table_window_only')
    expect(w).toContain('conservation_unavailable')
    expect(w).not.toContain('exon_intron_table_from_sample_scaffold')
    expect(w).not.toContain('conservation_from_sample_scaffold')
  })
})
