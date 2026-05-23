/* ───────────────────────────────────────────────────────────────────────
   Gene viewer adapter — backend `GeneViewerResponse` → renderer
   `GeneWindowData` (GV-005).

   Hybrid strategy (user-approved 2026-05-19): the backend payload is
   authoritative for everything it carries — window, queried variant,
   sequences, windowed segments, in-window ClinVar, protein features,
   restriction sites, oligo features, summary numbers. The whole-gene
   exon/intron table and PhyloP conservation are NOT in the contract yet
   (`agent_handoff/CURRENT.md` → Cross-Agent Requests, viewer-payload
   enrichment ask), so those are filled from a `scaffold` (default
   `RPE65_V2`) and honestly reported via `geneViewerScaffoldWarnings()`.

   Pure + side-effect free so it is unit-testable without a DOM.
─────────────────────────────────────────────────────────────────────── */

import type {
  AlleleMode,
  ClinvarVariant as BackendClinvarVariant,
  GeneViewerResponse,
  VariantClassification,
} from '../backend'
import type { Base } from './codon-table'
import type {
  ClinClass,
  ClinvarVariant,
  GeneWindowData,
  WindowSegment,
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

function mapClinvar(v: BackendClinvarVariant): ClinvarVariant {
  return {
    cdsPos: v.cds_pos,
    hgvsC: v.hgvs_c,
    hgvsP: v.hgvs_p ?? '',
    cls: toClinClass(v.classification),
    cv: v.clinvar_id ?? '',
    queried: v.queried,
    splice: v.splice,
  }
}

/**
 * Map a backend `GeneViewerResponse` into the renderer `GeneWindowData`.
 *
 * @param resp     backend payload (live or `GENE_VIEWER_SAMPLE` fallback).
 * @param alleleMode  which sequence basis to render. Defaults to the
 *   payload's own `sequences.allele_mode`. In `variant` mode the queried
 *   SNV is overlaid onto the exon segment that contains it so the displayed
 *   base flips (e.g. RPE65 c.260 A→G) while all variant labels/coordinates
 *   are preserved unchanged.
 * @param scaffold whole-gene exon/intron/conservation source for the fields
 *   the contract does not yet carry. Defaults to `RPE65_V2`.
 */
export function adaptGeneViewer(
  resp: GeneViewerResponse,
  alleleMode: AlleleMode = resp.sequences.allele_mode,
  scaffold: GeneWindowData = RPE65_V2,
): GeneWindowData {
  const { identity, locus, summary, queried_variant: qv, tracks } = resp
  const reverse = locus.strand === '-'
  const qvCds = qv.cds_pos
  const canUseSampleScaffold =
    identity.gene === scaffold.gene &&
    identity.resolved_transcript === scaffold.transcript

  const windowSegments: WindowSegment[] = resp.segments.map((seg) => {
    if (seg.kind === 'exon') {
      const cdsStart = seg.cds_start ?? 0
      const cdsEnd = seg.cds_end ?? 0
      let seq = seg.sequence
      if (
        alleleMode === 'variant' &&
        qvCds >= cdsStart &&
        qvCds <= cdsEnd
      ) {
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
  const exons = canUseSampleScaffold
    ? scaffold.exons
    : windowSegments
        .filter((seg): seg is Extract<WindowSegment, { kind: 'exon' }> => seg.kind === 'exon')
        .map((seg) => ({
          num: seg.exonNum,
          cdsStart: seg.cdsStart,
          cdsEnd: seg.cdsEnd,
          genomicLen: seg.cdsEnd - seg.cdsStart + 1,
        }))
  const introns = canUseSampleScaffold
    ? scaffold.introns
    : windowSegments
        .filter((seg): seg is Extract<WindowSegment, { kind: 'intron' }> => seg.kind === 'intron')
        .map((seg) => ({
          num: seg.intronNum,
          lenBp: seg.totalLen,
        }))

  return {
    gene: identity.gene,
    transcript: identity.resolved_transcript,
    ensg: identity.ensembl_gene_id ?? '',
    chrom: locus.chrom,
    nativeStrand: reverse ? 'reverse' : 'forward',

    geneLength: summary.gene_length ?? (canUseSampleScaffold ? scaffold.geneLength : 0),
    totalExons: summary.total_exons,
    cdsLength: summary.cds_length ?? (canUseSampleScaffold ? scaffold.cdsLength : 0),
    proteinLength: summary.protein_length ?? (canUseSampleScaffold ? scaffold.proteinLength : 0),
    utr5Length: summary.utr5_length ?? (canUseSampleScaffold ? scaffold.utr5Length : 0),
    utr3Length: summary.utr3_length ?? (canUseSampleScaffold ? scaffold.utr3Length : 0),
    mrnaLength: summary.mrna_length ?? (canUseSampleScaffold ? scaffold.mrnaLength : 0),

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
      classification: toClinClass(qv.classification),
    },

    clinvar: tracks.clinvar_variants.map(mapClinvar),
    exonVariantCount,

    domains: pf.domains.map((d) => ({
      aaStart: d.aa_start,
      aaEnd: d.aa_end,
      label: d.label,
      shortLabel: d.short_label ?? undefined,
    })),

    proteinFeatures: {
      signalPeptide: pf.signal_peptide
        ? { aaStart: pf.signal_peptide.aa_start, aaEnd: pf.signal_peptide.aa_end }
        : null,
      transmembrane: pf.transmembrane.map((r) => ({
        aaStart: r.aa_start,
        aaEnd: r.aa_end,
        label: r.label,
      })),
      domains: pf.domains.map((d) => ({
        aaStart: d.aa_start,
        aaEnd: d.aa_end,
        label: d.label,
      })),
      activeSites: pf.active_sites.map((a) => ({
        aa: a.aa,
        residue: a.residue,
        label: a.label,
      })),
      membraneBinding: pf.membrane_binding.map((r) => ({
        aaStart: r.aa_start,
        aaEnd: r.aa_end,
        label: r.label,
      })),
      palmitoylation: pf.palmitoylation.map((p) => ({
        aa: p.aa,
        residue: p.residue,
        label: p.label,
      })),
    },

    genomicCoords: {
      chrom: locus.chrom,
      start: locus.gene_start ?? scaffold.genomicCoords.start,
      end: locus.gene_end ?? scaffold.genomicCoords.end,
      strand: reverse ? '-' : '+',
    },

    // PhyloP conservation is not in the contract yet → sample scaffold when
    // the payload track is empty.
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

/**
 * Honest provenance for the adapted viewer: the backend payload's own
 * warnings plus synthetic warnings naming any field the adapter had to
 * fill from the sample scaffold (so GV-006 can surface it, never implying
 * sample-derived structure is live data). Pure; no scaffold values leak.
 */
export function geneViewerScaffoldWarnings(
  resp: GeneViewerResponse,
): string[] {
  const warnings = [...resp.provenance.warnings]
  const usesSampleScaffold =
    resp.identity.gene === RPE65_V2.gene &&
    resp.identity.resolved_transcript === RPE65_V2.transcript
  warnings.push(
    usesSampleScaffold
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
