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
})
