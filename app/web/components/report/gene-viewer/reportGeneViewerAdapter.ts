import { normalizeProteinArchitectureLane } from '@/lib/protein-architecture'
import { clinClassFromText, type GeneWindowData } from '@/lib/workbench/gene-window'
import type { GeneContextSnapshot } from '@/lib/backend'

function snapshotRangeLength(
  start: number | null | undefined,
  end: number | null | undefined,
): number {
  if (typeof start === 'number' && typeof end === 'number') return Math.abs(end - start) + 1
  return 0
}

function snapshotBase(
  value: string | null | undefined,
): GeneWindowData['queriedVariant']['refBase'] {
  const base = value?.trim().toUpperCase()[0]
  return (base === 'A' || base === 'T' || base === 'C' || base === 'G' ? base : 'A') as GeneWindowData['queriedVariant']['refBase']
}

export function adaptGeneContextSnapshot(
  snapshot: GeneContextSnapshot,
  markerClassification: string | null | undefined,
): GeneWindowData {
  const codingExons = snapshot.exons
    .filter((exon) => typeof exon.cds_start === 'number' && typeof exon.cds_end === 'number')
    .map((exon) => ({
      num: exon.number,
      cdsStart: exon.cds_start ?? 0,
      cdsEnd: exon.cds_end ?? 0,
      genomicLen:
        exon.genomic_length ??
        snapshotRangeLength(exon.genomic_start, exon.genomic_end) ??
        Math.max(1, (exon.cds_end ?? 0) - (exon.cds_start ?? 0) + 1),
    }))
  const cdsLength =
    snapshot.cds_length ??
    codingExons.reduce((sum, exon) => sum + Math.max(0, exon.cdsEnd - exon.cdsStart + 1), 0)
  const proteinTrack = snapshot.protein_domain_track
  const proteinLength =
    snapshot.protein_length ?? proteinTrack?.protein_length ?? Math.max(1, Math.ceil(cdsLength / 3))
  const variant = snapshot.variant
  const cdsPos = variant?.cds_pos ?? codingExons[0]?.cdsStart ?? 1
  const genomicStart = snapshot.gene_start ?? 0
  const genomicEnd = snapshot.gene_end ?? genomicStart
  const windowSegments: GeneWindowData['windowSegments'] = snapshot.zoom_segments.map((segment) => {
    if (segment.kind === 'exon') {
      return {
        kind: 'exon',
        exonNum: segment.exon_number ?? 0,
        cdsStart: segment.cds_start ?? 0,
        cdsEnd: segment.cds_end ?? 0,
        seq: segment.sequence,
      }
    }
    return {
      kind: 'intron',
      intronNum: segment.intron_number ?? 0,
      totalLen:
        segment.omitted_bp +
        segment.five_prime_sequence.length +
        segment.three_prime_sequence.length,
      fiveSeq: segment.five_prime_sequence,
      threeSeq: segment.three_prime_sequence,
    }
  })
  const domainFeatures = proteinTrack?.features
    .filter((feature) => feature.aa_start > 0 && feature.aa_end >= feature.aa_start)
    .filter((feature) => normalizeProteinArchitectureLane(feature.lane, feature.kind) === 'domains')
    .map((feature) => ({
      aaStart: feature.aa_start,
      aaEnd: feature.aa_end,
      label: feature.label,
      shortLabel: feature.short_label ?? undefined,
      source: feature.source ?? undefined,
      accession: feature.accession ?? feature.source_accession ?? undefined,
      broadBackbone: false,
    })) ?? []

  return {
    gene: snapshot.gene,
    transcript: snapshot.transcript ?? '',
    ensg: snapshot.ensembl_gene_id ?? '',
    chrom: snapshot.chromosome ?? '',
    nativeStrand: snapshot.strand === '-' ? 'reverse' : 'forward',
    geneLength: snapshot.gene_length ?? snapshotRangeLength(snapshot.gene_start, snapshot.gene_end),
    totalExons: snapshot.exons.length,
    cdsLength,
    proteinLength,
    utr5Length: 0,
    utr3Length: 0,
    mrnaLength:
      Math.max(
        0,
        ...snapshot.exons.map((exon) => exon.transcript_end ?? 0),
        ...snapshot.introns.map((intron) => intron.transcript_end ?? 0),
      ) || cdsLength,
    architectureScope: 'transcript',
    exons: codingExons,
    introns: snapshot.introns.map((intron) => ({
      num: intron.number,
      lenBp:
        intron.length_bp ??
        snapshotRangeLength(intron.genomic_start, intron.genomic_end) ??
        1,
    })),
    windowSegments,
    queriedVariant: {
      cdsPos,
      refBase: snapshotBase(variant?.ref),
      altBase: snapshotBase(variant?.alt),
      codonNumber: variant?.codon_number ?? Math.max(1, Math.ceil(cdsPos / 3)),
      codonOffset: variant?.codon_offset ?? ((cdsPos - 1) % 3),
      aaRef: variant?.aa_ref ?? '',
      aaAlt: variant?.aa_alt ?? '',
      hgvsP: variant?.hgvs_p ?? '',
      hgvsC: variant?.hgvs_c ?? snapshot.workbench_link?.cdna ?? '',
      classification: clinClassFromText(markerClassification) ?? 'vus',
    },
    clinvar: [],
    exonVariantCount: {},
    domains: domainFeatures,
    proteinFeatures: {
      signalPeptide: null,
      transmembrane: [],
      domains: domainFeatures,
      activeSites: [],
      membraneBinding: [],
      palmitoylation: [],
    },
    proteinProduct: null,
    genomicCoords: {
      chrom: snapshot.chromosome ?? '',
      start: genomicStart,
      end: genomicEnd,
      strand: snapshot.strand === '-' ? '-' : '+',
    },
    conservation: [],
    restriction: [],
    features: [],
  }
}
