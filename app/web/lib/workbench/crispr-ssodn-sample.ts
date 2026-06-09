import type { CrisprSsodnResponse } from '../backend'

/**
 * Offline fallback for the ssODN lab-donor surface (CRISPR Design tab).
 *
 * PUBLIC / DE-IDENTIFIED illustrative fixture only — RPE65 c.260A>G
 * (p.Asp87Gly), a 120-nt corrective HDR donor. The exonic portion is public
 * GRCh38 RPE65 exon-4 coding sequence; the upstream arm is synthetic intron-3
 * filler (rendered lowercase via `intron_mask`). The real, lab-ordered donors
 * come from the backend `/api/v1/crispr/ssodn` route at runtime — this mock
 * only renders the surface when no backend is reachable, and is surfaced as
 * `.eamos-mock` (illustrative) in the UI.
 *
 * Per docs/crispr-ssodn/spec.md the internal CMRI workbook and its sequences
 * are NEVER committed — nothing here is derived from that workbook.
 */
const INTRON_LEN = 31
const OLIGO =
  // 0–30  synthetic intron-3 3′ end (ends in the AG splice acceptor)
  'TTGCTCTTTGTTTCCTTTCCCTTGCCCCCAG' +
  // 31–98  public RPE65 exon-4 coding c.232–299 (GAC = Asp87 WT codon at the centre)
  'TATCGGGAACCTGTGGACAAGACAGTCGACATTCGGTGCTACATTCAAGAGAACAACGAACGGGGCAG' +
  // 99–119  public RPE65 exon-4 coding c.300–320
  'TCTTATCAGTGTGGCCTACGA'

export const CRISPR_SSODN_SAMPLE: CrisprSsodnResponse = {
  genome_build: 'GRCh38',
  ssodn: {
    // Legacy 3-arm fields (kept for contract completeness; the lab-donor surface
    // renders the orderable string below, not these arms).
    reference_arm: 'GACAAGACAGTCGACATTCGGTGCTACATT',
    variant_arm: 'GACAAGACAGTCGGCATTCGGTGCTACATT',
    repair_template: 'GACAAGACAGTCGACATTCGGTGCTACATT',
    edits_encoded: ['c.260A>G'],
    arm_lengths: { left: 59, right: 60 },
    estimated_hdr_efficiency: 0.42,
    // Lab-order donor.
    oligo_sequence: OLIGO,
    oligo_length: OLIGO.length,
    oligo_name: 'ss oligo for c.260A>G; p.Asp87Gly; GAC > GGC',
    variant_offset: 59,
    intron_mask: Array.from({ length: OLIGO.length }, (_, i) => i < INTRON_LEN),
    strand: '-',
    orientation: 'sense',
    protocol: 'lab_genomic',
    template_source: 'mock_public_rpe65',
    genome_build: 'GRCh38',
  },
  warnings: ['crispr_ssodn_mock_genomic_window'],
}
