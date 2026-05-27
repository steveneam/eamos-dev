/* ───────────────────────────────────────────────────────────────────────
   Mock-first primer design sample.

   A byte-faithful transcription of the backend fixture
   `app/backend/app/fixtures/workbench/primer_rpe65.json` (the data the
   live `POST /api/v1/primer` endpoint already serves). `designPrimers` in
   `lib/api.ts` falls back to this when the backend is unreachable, so the
   Workbench Primer tool renders offline (dev / pixel-check) exactly as it
   will against the real endpoint. The shape is the shared `PrimerResponse`
   contract — no contract drift; `test_frontend_contract.py` stays canary.
   Mirrors `crispr-sample.ts`. Do not diverge from the backend fixture.
─────────────────────────────────────────────────────────────────────── */

import type { PrimerResponse } from '@/lib/backend'

export const PRIMER_SAMPLE: PrimerResponse = {
  mode: 'sanger',
  pairs: [
    {
      index: 1,
      forward: 'GTGGACAAGACAGTCGCCATT',
      reverse: 'GCAACATGCCCTACGCCCACG',
      tm_forward: 60.2,
      tm_reverse: 60.6,
      gc_forward: 52,
      gc_reverse: 65,
      product_size: 487,
      specificity_hits: 1,
      notes: 'Optimal Tm balance; single specific hit; flanks c.260 by 178/309 bp.',
      recommended: true,
    },
    {
      index: 2,
      forward: 'TATCGGGAACCTGTGGACAAG',
      reverse: 'GTCCAGGGCAACATGCCCTAC',
      tm_forward: 58.8,
      tm_reverse: 61.4,
      gc_forward: 52,
      gc_reverse: 62,
      product_size: 412,
      specificity_hits: 1,
      notes: 'Slightly wider Tm spread; useful if pair #1 fails.',
      recommended: false,
    },
    {
      index: 3,
      forward: 'CCCTGTGGACAAGACAGTCGC',
      reverse: 'GTCCTACGCCCACGCAACATG',
      tm_forward: 62.1,
      tm_reverse: 62.5,
      gc_forward: 62,
      gc_reverse: 62,
      product_size: 524,
      specificity_hits: 2,
      notes: 'Tighter Tm but two BLAST hits — risk of pseudogene cross-reactivity.',
      recommended: false,
    },
  ],
}
