/* ───────────────────────────────────────────────────────────────────────
   RPE65 sample for the Workbench v2 sequence viewer.
   Ported from `e:\Web tool\Claude Design\Workbench v2\data.js`.

   DATA-COHERENCE FIX (carried forward from FE-5): the source mock's exon-4
   window `seq` had window index 28 = 'C', making codon 87 = "GCC" (Ala),
   contradicting the mock's own annotations and the rest of Eamos where the
   demo variant is c.260A>G p.Asp87Gly (Asp = GAC). Index 28 is 'C'→'A' here
   so codon 87 = "GAC" (Asp); `consequenceAt` then yields the spec-mandated
   p.Asp87Gly. No other base is altered.

   In production these come from NCBI Entrez (gene/transcript), Ensembl REST
   (exon structure), ClinVar, UniProt Proteins API, and PhyloP.
─────────────────────────────────────────────────────────────────────── */

import type { GeneWindowData } from './gene-window'

export const RPE65_V2: GeneWindowData = {
  gene: 'RPE65',
  transcript: 'NM_000329.3',
  ensg: 'ENSG00000116745',
  chrom: 'chr1',
  nativeStrand: 'reverse',

  geneLength: 21139,
  totalExons: 14,
  cdsLength: 1602,
  proteinLength: 533,
  utr5Length: 89,
  utr3Length: 1216,
  mrnaLength: 89 + 1602 + 1216,

  exons: [
    { num: 1, cdsStart: 1, cdsEnd: 24, genomicLen: 113 },
    { num: 2, cdsStart: 25, cdsEnd: 88, genomicLen: 64 },
    { num: 3, cdsStart: 89, cdsEnd: 231, genomicLen: 143 },
    { num: 4, cdsStart: 232, cdsEnd: 324, genomicLen: 93 }, // variant exon (c.260)
    { num: 5, cdsStart: 325, cdsEnd: 432, genomicLen: 108 },
    { num: 6, cdsStart: 433, cdsEnd: 533, genomicLen: 101 },
    { num: 7, cdsStart: 534, cdsEnd: 660, genomicLen: 127 },
    { num: 8, cdsStart: 661, cdsEnd: 770, genomicLen: 110 },
    { num: 9, cdsStart: 771, cdsEnd: 884, genomicLen: 114 },
    { num: 10, cdsStart: 885, cdsEnd: 988, genomicLen: 104 },
    { num: 11, cdsStart: 989, cdsEnd: 1130, genomicLen: 142 },
    { num: 12, cdsStart: 1131, cdsEnd: 1276, genomicLen: 146 },
    { num: 13, cdsStart: 1277, cdsEnd: 1452, genomicLen: 176 },
    { num: 14, cdsStart: 1453, cdsEnd: 1602, genomicLen: 1366 },
  ],
  introns: [
    { num: 1, lenBp: 1812 },
    { num: 2, lenBp: 661 },
    { num: 3, lenBp: 1240 },
    { num: 4, lenBp: 982 },
    { num: 5, lenBp: 753 },
    { num: 6, lenBp: 1504 },
    { num: 7, lenBp: 921 },
    { num: 8, lenBp: 1082 },
    { num: 9, lenBp: 787 },
    { num: 10, lenBp: 1342 },
    { num: 11, lenBp: 1155 },
    { num: 12, lenBp: 984 },
    { num: 13, lenBp: 823 },
  ],

  windowSegments: [
    {
      kind: 'exon',
      exonNum: 3,
      cdsStart: 217,
      cdsEnd: 231,
      seq: 'CCATCCCAACCAATC',
    },
    {
      kind: 'intron',
      intronNum: 3,
      totalLen: 1240,
      fiveSeq: 'gtaagtgcatcgttagctcgtaaggtgact',
      threeSeq: 'tttcttgctctttccccgcttgttccacag',
    },
    {
      // index 28 'C'→'A' (coherence fix; see file header) → codon 87 = GAC (Asp)
      kind: 'exon',
      exonNum: 4,
      cdsStart: 232,
      cdsEnd: 324,
      seq: 'TATCGGGAACCTGTGGACAAGACAGTCGACATTCGGTGCTACATTCAAGAGAACAACGAACGGGGGCAGCTTATCAGTGTGGCCTACGATGCC',
    },
    {
      kind: 'intron',
      intronNum: 4,
      totalLen: 982,
      fiveSeq: 'gtaagcttcgcctaaggtacgttctcaaag',
      threeSeq: 'ttgtcttttcccgctcttcttttgccccag',
    },
    {
      kind: 'exon',
      exonNum: 5,
      cdsStart: 325,
      cdsEnd: 339,
      seq: 'ATGGCCTTCAGTGAA',
    },
  ],

  queriedVariant: {
    cdsPos: 260,
    refBase: 'A',
    altBase: 'G',
    codonNumber: 87,
    codonOffset: 1,
    aaRef: 'D',
    aaAlt: 'G',
    hgvsP: 'p.Asp87Gly',
    hgvsC: 'c.260A>G',
    classification: 'lp',
  },

  clinvar: [
    { cdsPos: 220, hgvsC: 'c.220C>T', hgvsP: 'p.Pro74Ser', cls: 'lb', cv: 'VCV000099177' },
    { cdsPos: 226, hgvsC: 'c.226C>T', hgvsP: 'p.Pro76Ser', cls: 'vus', cv: 'VCV000099186' },
    { cdsPos: 236, hgvsC: 'c.236A>G', hgvsP: 'p.Asn79Ser', cls: 'p', cv: 'VCV000099201' },
    { cdsPos: 241, hgvsC: 'c.241C>T', hgvsP: 'p.Arg81Cys', cls: 'lp', cv: 'VCV000099234' },
    { cdsPos: 247, hgvsC: 'c.247G>A', hgvsP: 'p.Val83Ile', cls: 'p', cv: 'VCV000099244' },
    { cdsPos: 253, hgvsC: 'c.253T>C', hgvsP: 'p.Tyr85His', cls: 'vus', cv: 'VCV000099260' },
    { cdsPos: 257, hgvsC: 'c.257C>G', hgvsP: 'p.Ala86Gly', cls: 'lp', cv: 'VCV000099277' },
    {
      cdsPos: 260,
      hgvsC: 'c.260A>G',
      hgvsP: 'p.Asp87Gly',
      cls: 'lp',
      cv: 'VCV000099473',
      queried: true,
    },
    { cdsPos: 268, hgvsC: 'c.268A>G', hgvsP: 'p.Lys90Glu', cls: 'vus', cv: 'VCV000099501' },
    { cdsPos: 271, hgvsC: 'c.271G>A', hgvsP: 'p.Val91Ile', cls: 'lb', cv: 'VCV000099520' },
    { cdsPos: 277, hgvsC: 'c.277C>T', hgvsP: 'p.Arg93Cys', cls: 'p', cv: 'VCV000099544' },
    { cdsPos: 283, hgvsC: 'c.283G>C', hgvsP: 'p.Glu95Gln', cls: 'vus', cv: 'VCV000099568' },
    { cdsPos: 289, hgvsC: 'c.289G>A', hgvsP: 'p.Glu97Lys', cls: 'lp', cv: 'VCV000099591' },
    { cdsPos: 295, hgvsC: 'c.295G>A', hgvsP: 'p.Gly99Arg', cls: 'vus', cv: 'VCV000099614' },
    { cdsPos: 301, hgvsC: 'c.301C>T', hgvsP: 'p.Leu101Phe', cls: 'p', cv: 'VCV000099632' },
    { cdsPos: 313, hgvsC: 'c.313A>G', hgvsP: 'p.Ile105Val', cls: 'lb', cv: 'VCV000099680' },
    { cdsPos: 322, hgvsC: 'c.322G>A', hgvsP: 'p.Ala108Thr', cls: 'vus', cv: 'VCV000099701' },
    {
      cdsPos: '231+1',
      hgvsC: 'c.231+1G>A',
      hgvsP: 'p.(?)',
      cls: 'p',
      cv: 'VCV000099202',
      splice: true,
    },
    {
      cdsPos: '325-2',
      hgvsC: 'c.325-2A>G',
      hgvsP: 'p.(?)',
      cls: 'p',
      cv: 'VCV000099405',
      splice: true,
    },
  ],

  exonVariantCount: {
    1: 2, 2: 8, 3: 31, 4: 46, 5: 38, 6: 24, 7: 29,
    8: 33, 9: 17, 10: 22, 11: 41, 12: 36, 13: 28, 14: 11,
  },

  domains: [
    {
      aaStart: 51,
      aaEnd: 468,
      label: 'Carotenoid oxygenase (RPE65 catalytic)',
      shortLabel: 'Carotenoid oxygenase',
    },
  ],

  proteinFeatures: {
    signalPeptide: null,
    transmembrane: [],
    domains: [{ aaStart: 51, aaEnd: 468, label: 'Carotenoid oxygenase (catalytic)' }],
    activeSites: [
      { aa: 180, residue: 'H', label: 'Fe²⁺ coordination' },
      { aa: 241, residue: 'H', label: 'Fe²⁺ coordination' },
      { aa: 313, residue: 'H', label: 'Fe²⁺ coordination' },
      { aa: 527, residue: 'H', label: 'Fe²⁺ coordination' },
    ],
    membraneBinding: [
      { aaStart: 110, aaEnd: 127, label: 'Amphipathic helix (membrane contact)' },
      { aaStart: 200, aaEnd: 215, label: 'Amphipathic helix (membrane contact)' },
    ],
    palmitoylation: [
      { aa: 231, residue: 'C', label: 'S-palmitoyl cysteine (membrane anchor)' },
      { aa: 329, residue: 'C', label: 'S-palmitoyl cysteine (membrane anchor)' },
    ],
  },
  proteinProduct: null,

  genomicCoords: { chrom: 'chr1', start: 68428820, end: 68449958, strand: '-' },

  conservation: [
    0.71, 0.8, 0.34, 0.75, 0.83, 0.28, 0.78, 0.85, 0.21, 0.74, 0.81, 0.3, 0.79, 0.83, 0.25,
    0.95, 0.96, 0.22, 0.18, 0.2, 0.21, 0.19, 0.22, 0.18, 0.16, 0.14, 0.15, 0.13, 0.12, 0.14,
    0.13, 0.15, 0.12, 0.18, 0.16, 0.2, 0.21, 0.18, 0.19, 0.22, 0.18, 0.21, 0.18, 0.2, 0.22,
    0.18, 0.21, 0.24, 0.26, 0.3, 0.34, 0.38, 0.4, 0.44, 0.46, 0.5, 0.55, 0.6, 0.62, 0.65,
    0.7, 0.74, 0.78, 0.8, 0.82, 0.86, 0.88, 0.91, 0.92, 0.94, 0.95, 0.96, 0.97, 0.97, 0.98,
    0.62, 0.91, 0.21, 0.78, 0.83, 0.3, 0.88, 0.92, 0.25, 0.81, 0.86, 0.32, 0.79, 0.82, 0.28,
    0.85, 0.89, 0.22, 0.82, 0.91, 0.27, 0.78, 0.8, 0.31, 0.86, 0.87, 0.18, 0.95, 0.98, 0.96,
    0.83, 0.8, 0.21, 0.71, 0.74, 0.2, 0.69, 0.73, 0.22, 0.79, 0.81, 0.28, 0.84, 0.86, 0.3,
    0.77, 0.78, 0.19, 0.82, 0.84, 0.25, 0.76, 0.79, 0.23, 0.8, 0.83, 0.21, 0.74, 0.77, 0.22,
    0.72, 0.75, 0.18, 0.81, 0.83, 0.24, 0.79, 0.82, 0.25, 0.83, 0.85, 0.27, 0.78, 0.8, 0.22,
    0.75, 0.77, 0.2, 0.79, 0.81, 0.26, 0.82, 0.85, 0.29, 0.78, 0.81, 0.24, 0.74, 0.76, 0.21,
    0.72, 0.74, 0.18, 0.96, 0.97, 0.24, 0.2, 0.18, 0.16, 0.2, 0.18, 0.16, 0.15, 0.13, 0.14,
    0.12, 0.14, 0.13, 0.12, 0.15, 0.13, 0.18, 0.16, 0.2, 0.18, 0.21, 0.19, 0.22, 0.18, 0.21,
    0.18, 0.2, 0.22, 0.18, 0.2, 0.24, 0.28, 0.3, 0.32, 0.36, 0.4, 0.44, 0.48, 0.52, 0.58,
    0.62, 0.66, 0.68, 0.72, 0.76, 0.8, 0.82, 0.86, 0.88, 0.9, 0.92, 0.94, 0.95, 0.96, 0.97,
    0.97, 0.98, 0.98, 0.84, 0.92, 0.32, 0.78, 0.81, 0.28, 0.74, 0.78, 0.22, 0.81, 0.83, 0.3,
    0.77, 0.79, 0.24,
  ],

  restriction: [
    { name: 'BsrBI', site: 'CCGCTC', flatPos: 23 },
    { name: 'BamHI', site: 'GGATCC', flatPos: 108 },
    { name: 'EcoRI', site: 'GAATTC', flatPos: 146 },
    { name: 'PmlI', site: 'CACGTG', flatPos: 137 },
  ],

  features: [
    { type: 'oligo', cdsStart: 248, cdsEnd: 272, label: 'ss oligo for c.260A>G correction' },
  ],
}
