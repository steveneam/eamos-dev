/* ───────────────────────────────────────────────────────────────────────
   Gene viewer adapter — backend `GeneViewerResponse` → renderer
   `GeneWindowData` (GV-005).

   Hybrid strategy (user-approved 2026-05-19): the backend payload is
   authoritative for everything it carries — window, queried variant,
   sequences, windowed segments, in-window ClinVar, protein features,
   restriction sites, oligo features, summary numbers. Transcript
   architecture can come from the backend projection when requested; older
   fixture/scaffold fallbacks remain explicit via `geneViewerScaffoldWarnings()`.

   Pure + side-effect free so it is unit-testable without a DOM.
─────────────────────────────────────────────────────────────────────── */

import type {
  AlleleMode,
  ClinvarVariant as BackendClinvarVariant,
  GeneViewerResponse,
  ProteinProductEffect as BackendProteinProductEffect,
  VariantClassification,
  ViewerTranscriptProjection,
} from '../backend'
import type { Base } from './codon-table'
import {
  canonicalizeProteinArchitectureFeature,
  normalizeProteinArchitectureLane,
  selectPrimaryProteinArchitectureFeatures,
  type ProteinArchitectureFeature,
} from '../protein-architecture'
import {
  clinClassFromText,
  type ClinClass,
  type ClinvarVariant,
  type DomainInfo,
  type GeneWindowData,
  type ProteinFeatures,
  type ProteinProductEffect,
  type WindowSegment,
} from './gene-window'
import { RPE65_V2 } from './sample-rpe65-v2'

/** ClinVar classification → the 5-tier renderer class. `unknown` has no
 *  renderer tier; it collapses to `vus` for display (documented mapping). */
const CLASS_MAP: Record<VariantClassification, ClinClass> = {
  pathogenic: 'p',
  likely_pathogenic: 'lp',
  vus: 'vus',
  likely_benign: 'lb',
  benign: 'b',
  unknown: 'vus',
}

function toClinClass(c: VariantClassification): ClinClass {
  return CLASS_MAP[c] ?? 'vus'
}

function toBase(ch: string): Base {
  const u = ch.toUpperCase()
  return u === 'A' || u === 'T' || u === 'C' || u === 'G' ? (u as Base) : 'A'
}

/** Replace one character of `seq` at `idx` (no-op if out of range). */
function spliceBase(seq: string, idx: number, alt: string): string {
  if (idx < 0 || idx >= seq.length) return seq
  return seq.slice(0, idx) + alt + seq.slice(idx + 1)
}

function mapClinvar(
  v: BackendClinvarVariant,
  queriedHgvsC: string,
  queriedClassification: ClinClass,
): ClinvarVariant {
  const queried = v.queried || v.hgvs_c === queriedHgvsC
  return {
    cdsPos: v.cds_pos,
    hgvsC: v.hgvs_c,
    hgvsP: v.hgvs_p ?? '',
    cls: queried ? queriedClassification : toClinClass(v.classification),
    cv: v.clinvar_id ?? '',
    queried,
    splice: v.splice,
  }
}

function mapProteinProduct(
  product: BackendProteinProductEffect | null | undefined,
  alleleMode: AlleleMode,
): ProteinProductEffect | null {
  if (!product || product.allele_mode !== alleleMode) return null
  return {
    alleleMode: product.allele_mode,
    consequence: product.consequence,
    label: product.label,
    description: product.description,
    referenceProteinLength: product.reference_protein_length ?? null,
    effectiveProteinLength: product.effective_protein_length ?? null,
    truncatesProtein: product.truncates_protein,
    stopCodon: product.stop_codon ?? null,
    affectedAaStart: product.affected_aa_start ?? null,
    lostAaCount: product.lost_aa_count,
    nmdRisk: product.nmd_risk ?? null,
    exonEffects: product.exon_effects.map((effect) => ({
      exonNumber: effect.exon_number,
      cdsStart: effect.cds_start,
      cdsEnd: effect.cds_end,
      state: effect.state,
      affectedCdsStart: effect.affected_cds_start ?? null,
      affectedCdsEnd: effect.affected_cds_end ?? null,
      lostCdsBases: effect.lost_cds_bases,
    })),
  }
}

function annotateExons(
  exons: GeneWindowData['exons'],
  product: ProteinProductEffect | null,
): GeneWindowData['exons'] {
  if (!product || product.alleleMode !== 'variant') return exons
  const effectByExon = new Map(product.exonEffects.map((effect) => [effect.exonNumber, effect]))
  return exons.map((exon) => {
    const effect = effectByExon.get(exon.num)
    if (!effect) return exon
    return {
      ...exon,
      proteinState: effect.state,
      affectedCdsStart: effect.affectedCdsStart,
      affectedCdsEnd: effect.affectedCdsEnd,
      lostCdsBases: effect.lostCdsBases,
    }
  })
}

function clipRange(
  aaStart: number,
  aaEnd: number,
  limit: number,
): { aaStart: number; aaEnd: number } | null {
  const boundedLimit = Math.max(1, limit)
  const start = Math.max(1, Math.min(aaStart, aaEnd))
  const end = Math.min(boundedLimit, Math.max(aaStart, aaEnd))
  return end >= start ? { aaStart: start, aaEnd: end } : null
}

function mapDomain(
  d: {
    aa_start: number
    aa_end: number
    label: string
    short_label?: string | null
    source?: string | null
    accession?: string | null
    source_accession?: string | null
    broadBackbone?: boolean
  },
  limit: number,
): DomainInfo | null {
  const clipped = clipRange(d.aa_start, d.aa_end, limit)
  if (!clipped) return null
  return {
    aaStart: clipped.aaStart,
    aaEnd: clipped.aaEnd,
    label: d.label,
    shortLabel: d.short_label ?? undefined,
    source: d.source ?? undefined,
    accession: d.accession ?? d.source_accession ?? undefined,
    broadBackbone: d.broadBackbone,
  }
}

function mapProteinDomainBars(
  pf: GeneViewerResponse['tracks']['protein_features'],
  limit: number,
): DomainInfo[] {
  const hasSpecificProteinFeatures =
    Boolean(pf.signal_peptide) ||
    pf.transmembrane.length > 0 ||
    pf.active_sites.length > 0 ||
    pf.membrane_binding.length > 0 ||
    pf.palmitoylation.length > 0
  const trackFeatures = pf.domain_track?.features ?? []
  const architectureFeatures = [
    ...trackFeatures.map((feature): ProteinArchitectureFeature => ({
        start: feature.aa_start,
        end: Math.max(feature.aa_start, feature.aa_end),
        label: feature.label,
        short: feature.short_label ?? feature.label,
        kind: feature.kind,
        lane: normalizeProteinArchitectureLane(feature.lane, feature.kind),
        description: feature.description,
        source: feature.source,
        accession: feature.accession ?? feature.source_accession,
        score: feature.score,
        eValue: feature.e_value,
      })),
    ...pf.domains
      .map((d) => mapDomain(d, limit))
      .filter((d): d is DomainInfo => Boolean(d))
      .map((domain): ProteinArchitectureFeature => ({
        start: domain.aaStart,
        end: domain.aaEnd,
        label: domain.label,
        short: domain.shortLabel ?? domain.label,
        kind: 'domain',
        lane: 'domains',
        source: domain.source ?? 'viewer protein_features',
        accession: domain.accession,
      })),
  ].map(canonicalizeProteinArchitectureFeature)

  if (architectureFeatures.length > 0) {
    return selectPrimaryProteinArchitectureFeatures(architectureFeatures)
      .filter((feature) => feature.lane === 'domains')
      .filter((feature) => !(feature.broadBackbone && hasSpecificProteinFeatures))
      .map((feature) =>
        mapDomain(
          {
            aa_start: feature.start,
            aa_end: feature.end,
            label: feature.label,
            short_label: feature.short,
            source: feature.source,
            accession: feature.accession,
            broadBackbone: feature.broadBackbone,
          },
          limit,
        ),
      )
      .filter((d): d is DomainInfo => Boolean(d))
  }

  return []
}

function mapRangeFeature(
  r: { aa_start: number; aa_end: number; label: string },
  limit: number,
): { aaStart: number; aaEnd: number; label: string } | null {
  const clipped = clipRange(r.aa_start, r.aa_end, limit)
  return clipped ? { ...clipped, label: r.label } : null
}

function mapProteinFeatures(
  pf: GeneViewerResponse['tracks']['protein_features'],
  limit: number,
  domains = mapProteinDomainBars(pf, limit),
): ProteinFeatures {
  return {
    signalPeptide: pf.signal_peptide
      ? clipRange(pf.signal_peptide.aa_start, pf.signal_peptide.aa_end, limit)
      : null,
    transmembrane: pf.transmembrane
      .map((r) => mapRangeFeature(r, limit))
      .filter((r): r is NonNullable<typeof r> => Boolean(r)),
    domains,
    activeSites: pf.active_sites
      .filter((a) => a.aa <= limit)
      .map((a) => ({
        aa: a.aa,
        residue: a.residue,
        label: a.label,
      })),
    membraneBinding: pf.membrane_binding
      .map((r) => mapRangeFeature(r, limit))
      .filter((r): r is NonNullable<typeof r> => Boolean(r)),
    palmitoylation: pf.palmitoylation
      .filter((p) => p.aa <= limit)
      .map((p) => ({
        aa: p.aa,
        residue: p.residue,
        label: p.label,
      })),
  }
}

/**
 * Map a backend `GeneViewerResponse` into the renderer `GeneWindowData`.
 *
 * @param resp     backend payload (live or `GENE_VIEWER_SAMPLE` fallback).
 * @param alleleMode  which sequence basis to render.
 * @param options.scaffold whole-gene exon/intron/conservation source. Defaults to `RPE65_V2`.
 * @param options.architecture use `transcript` to render exon/intron structure from
 * metadata projection while keeping `windowSegments` sequence-bounded.
 */
interface AdaptGeneViewerOptions {
  scaffold?: GeneWindowData
  architecture?: 'window' | 'transcript'
  queriedVariantClassification?: string | null
}

export function adaptGeneViewer(
  resp: GeneViewerResponse,
  alleleMode: AlleleMode = resp.sequences.allele_mode,
  options: AdaptGeneViewerOptions = {},
): GeneWindowData {
  const scaffold = options.scaffold ?? RPE65_V2
  const { identity, locus, summary, queried_variant: qv, tracks } = resp
  const reverse = locus.strand === '-'
  const qvCds = qv.cds_pos
  const canUseSampleScaffold =
    identity.gene === scaffold.gene &&
    identity.resolved_transcript === scaffold.transcript

  const applied = alleleMode === 'variant' ? resp.sequences.applied_variant : null
  let cumulativeOffset = 0
  const windowSegments: WindowSegment[] = resp.segments.map((seg) => {
    const segmentOffset = cumulativeOffset
    const segmentLength =
      seg.kind === 'exon'
        ? seg.sequence.length
        : seg.five_prime_sequence.length + seg.three_prime_sequence.length
    cumulativeOffset += segmentLength
    if (seg.kind === 'exon') {
      const cdsStart = seg.cds_start ?? 0
      const cdsEnd = seg.cds_end ?? 0
      let seq = seg.sequence
      if (applied?.segment_id === seg.id) {
        const localOffset = applied.sequence_offset - segmentOffset
        if (localOffset >= 0 && localOffset <= seq.length) {
          seq =
            seq.slice(0, localOffset) +
            applied.alt +
            seq.slice(localOffset + applied.ref.length)
        }
      } else if (alleleMode === 'variant' && qvCds >= cdsStart && qvCds <= cdsEnd) {
        seq = spliceBase(seq, qvCds - cdsStart, toBase(qv.alt))
      }
      return {
        kind: 'exon',
        exonNum: seg.exon_number ?? 0,
        cdsStart,
        cdsEnd,
        seq,
      }
    }
    return {
      kind: 'intron',
      intronNum: seg.intron_number ?? 0,
      totalLen:
        seg.omitted_bp +
        seg.five_prime_sequence.length +
        seg.three_prime_sequence.length,
      fiveSeq: seg.five_prime_sequence,
      threeSeq: seg.three_prime_sequence,
    }
  })

  const exonVariantCount: Record<number, number> = {}
  tracks.exon_density.forEach((e) => {
    exonVariantCount[e.exon_number] = e.variant_count
  })

  const pf = tracks.protein_features
  const rawProteinLength =
    summary.protein_length ?? (canUseSampleScaffold ? scaffold.proteinLength : 0)
  const proteinProduct = mapProteinProduct(tracks.protein_product, alleleMode)
  const proteinLength =
    alleleMode === 'variant' && proteinProduct?.truncatesProtein
      ? (proteinProduct.effectiveProteinLength ?? rawProteinLength)
      : rawProteinLength
  const featureLimit = Math.max(1, proteinLength || rawProteinLength || 1)
  const transcriptProjection = transcriptProjectionForArchitecture(resp, options.architecture)
  const projectionExons = (transcriptProjection
    ?.intervals
    .filter(
      (interval) =>
        interval.kind === 'exon' && interval.cds_start != null && interval.cds_end != null,
    )
    .map((interval) => ({
      num: interval.exon_number ?? 0,
      cdsStart: interval.cds_start ?? 0,
      cdsEnd: interval.cds_end ?? 0,
      genomicLen: Math.abs(interval.genomic_end - interval.genomic_start) + 1,
    })) ?? [])
  const projectionIntrons = (transcriptProjection
    ?.intervals
    .filter((interval) => interval.kind === 'intron')
    .map((interval) => ({
      num: interval.intron_number ?? 0,
      lenBp: Math.abs(interval.genomic_end - interval.genomic_start) + 1,
    })) ?? [])
  const usesTranscriptProjection = projectionExons.length > 0
  const rawExons = usesTranscriptProjection
    ? projectionExons
    : canUseSampleScaffold
      ? scaffold.exons
      : windowSegments
          .filter((seg): seg is Extract<WindowSegment, { kind: 'exon' }> => seg.kind === 'exon')
          .map((seg) => ({
            num: seg.exonNum,
            cdsStart: seg.cdsStart,
            cdsEnd: seg.cdsEnd,
            genomicLen: seg.cdsEnd - seg.cdsStart + 1,
          }))
  const exons = annotateExons(rawExons, proteinProduct)
  const introns = projectionIntrons?.length
    ? projectionIntrons
    : canUseSampleScaffold
      ? scaffold.introns
      : windowSegments
          .filter((seg): seg is Extract<WindowSegment, { kind: 'intron' }> => seg.kind === 'intron')
          .map((seg) => ({
            num: seg.intronNum,
            lenBp: seg.totalLen,
          }))

  const proteinDomains = mapProteinDomainBars(pf, featureLimit)
  const proteinFeatures = mapProteinFeatures(pf, featureLimit, proteinDomains)
  const queriedClassification =
    clinClassFromText(options.queriedVariantClassification) ?? toClinClass(qv.classification)

  return {
    gene: identity.gene,
    transcript: identity.resolved_transcript,
    ensg: identity.ensembl_gene_id ?? '',
    chrom: locus.chrom,
    nativeStrand: reverse ? 'reverse' : 'forward',

    geneLength: summary.gene_length ?? (canUseSampleScaffold ? scaffold.geneLength : 0),
    totalExons: summary.total_exons,
    cdsLength: summary.cds_length ?? (canUseSampleScaffold ? scaffold.cdsLength : 0),
    proteinLength,
    utr5Length: summary.utr5_length ?? (canUseSampleScaffold ? scaffold.utr5Length : 0),
    utr3Length: summary.utr3_length ?? (canUseSampleScaffold ? scaffold.utr3Length : 0),
    mrnaLength: summary.mrna_length ?? (canUseSampleScaffold ? scaffold.mrnaLength : 0),
    architectureScope: usesTranscriptProjection || canUseSampleScaffold ? 'transcript' : 'window',

    exons,
    introns,

    windowSegments,

    queriedVariant: {
      cdsPos: qv.cds_pos,
      refBase: toBase(qv.ref),
      altBase: toBase(qv.alt),
      codonNumber: qv.codon_number ?? 0,
      codonOffset: qv.codon_offset ?? 0,
      aaRef: qv.aa_ref ?? '',
      aaAlt: qv.aa_alt ?? '',
      hgvsP: qv.hgvs_p ?? '',
      hgvsC: qv.hgvs_c,
      classification: queriedClassification,
    },

    clinvar: tracks.clinvar_variants.map((variant) =>
      mapClinvar(variant, qv.hgvs_c, queriedClassification),
    ),
    exonVariantCount,

    domains: proteinDomains,

    proteinFeatures,
    proteinProduct,

    genomicCoords: {
      chrom: locus.chrom,
      start: locus.gene_start ?? scaffold.genomicCoords.start,
      end: locus.gene_end ?? scaffold.genomicCoords.end,
      strand: reverse ? '-' : '+',
    },

    conservation:
      tracks.conservation_values.length > 0
        ? tracks.conservation_values
        : canUseSampleScaffold
          ? scaffold.conservation
          : [],

    restriction: tracks.restriction_sites.map((r) => ({
      name: r.name,
      site: r.site,
      flatPos: r.flat_pos,
    })),

    features: tracks.features
      .filter((f) => f.type === 'oligo')
      .map((f) => ({
        type: 'oligo' as const,
        cdsStart: f.cds_start,
        cdsEnd: f.cds_end,
        label: f.label,
      })),
  }
}

function transcriptProjectionForArchitecture(
  resp: GeneViewerResponse,
  mode: AdaptGeneViewerOptions['architecture'],
): ViewerTranscriptProjection | null {
  if (mode !== 'transcript') return null
  return resp.transcript_projection ?? resp.full_locus?.transcript_projection ?? null
}

/**
 * Honest provenance for the adapted viewer: the backend payload's own
 * warnings plus synthetic warnings naming any field the adapter had to
 * fill from the sample scaffold.
 */
export function geneViewerScaffoldWarnings(
  resp: GeneViewerResponse,
): string[] {
  const warnings = [...resp.provenance.warnings]
  const usesSampleScaffold =
    resp.identity.gene === RPE65_V2.gene &&
    resp.identity.resolved_transcript === RPE65_V2.transcript
  const hasTranscriptProjection = Boolean(
    resp.transcript_projection?.intervals.some((interval) => interval.kind === 'exon') ||
      resp.full_locus?.transcript_projection.intervals.some((interval) => interval.kind === 'exon'),
  )
  warnings.push(
    hasTranscriptProjection
      ? 'exon_intron_table_from_transcript_projection'
      : usesSampleScaffold
      ? 'exon_intron_table_from_sample_scaffold'
      : 'exon_intron_table_window_only',
  )
  if (resp.tracks.conservation_values.length === 0) {
    warnings.push(
      usesSampleScaffold ? 'conservation_from_sample_scaffold' : 'conservation_unavailable',
    )
  }
  return warnings
}
