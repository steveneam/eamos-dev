/* ───────────────────────────────────────────────────────────────────────
   Mock-first CRISPR off-target screening sample.

   `OFFTARGET_SAMPLE` is a byte-faithful transcription of the backend fixture
   `app/backend/app/fixtures/workbench/crispr_offtargets_deidentified.json`
   (the data the live `POST /api/v1/crispr/offtargets` endpoint serves in
   mock mode). De-identified: the off-target gene symbols / ENSG IDs and loci
   are synthetic stand-ins shaped from a real CMRI off-target workbook — the
   workbook itself is never committed.

   `mockScreeningPrimers` synthesises a `CrisprScreeningPrimerResponse` for the
   selected sites by reusing the bundled `PRIMER_SAMPLE` pairs, so the FE
   renders the full enumerate → curate → primer → export flow offline exactly
   as it will against the real `POST /api/v1/crispr/screening-primers`. Shapes
   are the shared contract types — no drift; `test_frontend_contract.py` stays
   canary on the backend side.
─────────────────────────────────────────────────────────────────────── */

import type {
  CrisprOffTargetResponse,
  CrisprScreeningPrimerRequest,
  CrisprScreeningPrimerResponse,
  ScreeningPrimer,
} from '@/lib/backend'
import { PRIMER_SAMPLE } from './primer-sample'

export const OFFTARGET_SAMPLE: CrisprOffTargetResponse = {
  genome_build: 'GRCh38',
  sites: [
    {
      sequence: 'GAGTCCGAGCAGAAGAAGAT',
      pam: 'AGG',
      score: 1.0,
      mismatches: 0,
      gene: 'ON_TARGET',
      gene_id: null,
      biotype: 'protein_coding',
      chromosome: 'chr7',
      strand: '+',
      position: 117509080,
      on_target: true,
    },
    {
      sequence: 'GAGTCCGAGCCGAAGAAGAT',
      pam: 'GGG',
      score: 0.555,
      mismatches: 1,
      gene: 'OTSG2',
      gene_id: 'ENSG00000290002',
      biotype: 'protein_coding',
      chromosome: 'chr3',
      strand: '-',
      position: 37004431,
      on_target: false,
    },
    {
      sequence: 'GAGTCCGAGCAGAAGACGAT',
      pam: 'CGG',
      score: 0.385,
      mismatches: 1,
      gene: 'OTSG1',
      gene_id: 'ENSG00000290001',
      biotype: 'protein_coding',
      chromosome: 'chr7',
      strand: '+',
      position: 117509068,
      on_target: false,
    },
    {
      sequence: 'GAGTCCGCGCAGCAGAAGAT',
      pam: 'AGG',
      score: 0.02451,
      mismatches: 2,
      gene: 'OTSG3',
      gene_id: 'ENSG00000290003',
      biotype: 'lncRNA',
      chromosome: 'chr17',
      strand: '-',
      position: 43092673,
      on_target: false,
    },
    {
      sequence: 'GAGTGCGAGCAGAAGAATAT',
      pam: 'TGG',
      score: 0.021651,
      mismatches: 2,
      gene: null,
      gene_id: null,
      biotype: null,
      chromosome: 'chr12',
      strand: '+',
      position: 102912875,
      on_target: false,
    },
  ],
}

/** chrN:start-end region string from a point ± flank (matches backend math). */
function regionLabel(chromosome: string, position: number, flank: number): string {
  return `${chromosome}:${Math.max(1, position - flank)}-${position + flank}`
}

/**
 * Offline fallback for `POST /api/v1/crispr/screening-primers`. Cycles the
 * bundled primer pairs across the requested sites — honest mock numbers, the
 * exact `ScreeningPrimer` contract shape, deterministic per site_index.
 */
export function mockScreeningPrimers(
  payload: CrisprScreeningPrimerRequest,
): CrisprScreeningPrimerResponse {
  const mode = payload.mode ?? 'sanger'
  const flank = payload.flank_bp ?? 400
  const prefix = (payload.naming_prefix ?? 'OTS').replace(/[^A-Za-z0-9_.-]+/g, '_') || 'OTS'
  const pairs = PRIMER_SAMPLE.pairs

  const primers: ScreeningPrimer[] = payload.sites.map((target, i) => {
    const pair = pairs[i % pairs.length]
    const chromosome = target.chromosome ?? target.region?.chromosome ?? 'chr?'
    const position = target.position ?? 0
    const point = target.point ?? `${chromosome}:${position}`
    const region = target.region
      ? `${target.region.chromosome}:${target.region.start}-${target.region.end}`
      : regionLabel(chromosome, position, flank)
    const otherProducts =
      pair.specificity_hits <= 1
        ? 'NONE'
        : `${pair.specificity_hits - 1} other product(s); see notes`
    return {
      site_index: target.site_index,
      point,
      region,
      name_forward: `${prefix}_${target.site_index}_F`,
      name_reverse: `${prefix}_${target.site_index}_R`,
      forward: pair.forward,
      reverse: pair.reverse,
      tm_forward: pair.tm_forward,
      tm_reverse: pair.tm_reverse,
      gc_forward: pair.gc_forward,
      gc_reverse: pair.gc_reverse,
      product_size: pair.product_size,
      specificity_hits: pair.specificity_hits,
      other_products: otherProducts,
      secondary_structure_risk: pair.secondary_structure_risk,
      secondary_structure_notes: pair.secondary_structure_notes,
      recommended: pair.recommended,
      notes: pair.notes,
      template_source: 'mock_screening_window',
    }
  })

  return { mode, primers, warnings: ['crispr_screening_mock_template'] }
}
