import type { CrisprSsodnResponse } from '../backend'

/**
 * Offline fallback for the ssODN lab-donor surface (CRISPR Design tab).
 *
 * PUBLIC RPE65 reference (GRCh38) only — RPE65 c.260A>G (p.Asp87Gly), a 120-nt
 * donor whose sequence is the genomic minus strand (= transcript sense) around
 * c.260, verified against Ensembl ENST00000262340 (codon 87 = GAT; the donor
 * differs from reference by the single c.260 A>G at offset 61). The 5′ arm
 * crosses the intron-3 / exon-4 boundary, so offsets 0–32 are intronic (rendered
 * lowercase via `intron_mask`) and 33–119 are exon 4. The exact mask + the
 * lab-current donor come from the backend `/api/v1/crispr/ssodn` route at
 * runtime; this bundled sample only renders the surface offline (`.eamos-mock`).
 *
 * Per docs/crispr-ssodn/spec.md the internal CMRI workbook file is NEVER
 * committed — the sequence here is public GRCh38 reference, not the workbook.
 */
const INTRON_LEN = 33
// Donor (orderable, 5′→3′ transcript sense) — carries the c.260A>G edit at offset 61.
const OLIGO =
  'CGGATTGCTCCTGTCTATACTCTTCCCTATGTTTCAATGTCCTTCAGGTTCATCCGCACTGGTGCTTACGTACGGGCAATGACTGAGAAAAGGATCGTCATAACAGAATTTGGCACCTGT'
// Reference (wild-type) — same window with c.260 = A.
const REFERENCE =
  'CGGATTGCTCCTGTCTATACTCTTCCCTATGTTTCAATGTCCTTCAGGTTCATCCGCACTGATGCTTACGTACGGGCAATGACTGAGAAAAGGATCGTCATAACAGAATTTGGCACCTGT'

export const CRISPR_SSODN_SAMPLE: CrisprSsodnResponse = {
  genome_build: 'GRCh38',
  ssodn: {
    // Legacy 3-arm fields (contract completeness; the lab-donor surface renders
    // the orderable string below, not these arms).
    reference_arm: REFERENCE,
    variant_arm: OLIGO,
    repair_template: OLIGO,
    edits_encoded: ['c.260A>G'],
    arm_lengths: { left: 61, right: 58 },
    estimated_hdr_efficiency: 0.42,
    // Lab-order donor.
    oligo_sequence: OLIGO,
    oligo_length: OLIGO.length,
    oligo_name: 'ss oligo for c.260A>G; p.Asp87Gly; GAT > GGT',
    variant_offset: 61,
    intron_mask: Array.from({ length: OLIGO.length }, (_, i) => i < INTRON_LEN),
    strand: '-',
    orientation: 'sense',
    protocol: 'lab_genomic',
    template_source: 'mock_public_rpe65',
    genome_build: 'GRCh38',
  },
  warnings: ['crispr_ssodn_mock_genomic_window'],
  source_disclosure: {
    source_status: 'fallback',
    provider_id: 'crispr_ssodn_mock_window',
    provider_label: 'Mock genomic-window fallback',
    source_version: null,
    cache_status: null,
    warnings: ['crispr_ssodn_mock_genomic_window'],
    requirements: ['resolved_sequence_context'],
  },
}
