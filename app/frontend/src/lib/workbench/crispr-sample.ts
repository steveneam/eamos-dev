/* ───────────────────────────────────────────────────────────────────────
   Mock-first CRISPR design sample.

   A byte-faithful transcription of the backend fixture
   `app/backend/app/fixtures/workbench/crispr_rpe65.json` (the data the
   live `POST /api/v1/crispr` endpoint already serves). `designGuides` in
   `lib/api.ts` falls back to this when the backend is unreachable, so the
   Workbench CRISPR tool renders offline (dev / pixel-check) exactly as it
   will against the real endpoint. The shape is the shared `CrisprResponse`
   contract — no contract drift; `test_frontend_contract.py` stays canary.
─────────────────────────────────────────────────────────────────────── */

import type { CrisprResponse } from '@/lib/backend'

export const CRISPR_SAMPLE: CrisprResponse = {
  cas: 'SpCas9',
  guides: [
    {
      index: 1,
      cut_position: 26,
      strand: '+',
      guide: 'GGACAAGACAGTCGCCATTC',
      pam: 'GGT',
      on_target_score: 78.4,
      off_target_score: 16.2,
      gc_percent: 60,
      notes: 'Cuts 2 bp upstream of variant; lowest off-target.',
    },
    {
      index: 2,
      cut_position: 31,
      strand: '+',
      guide: 'CAAGACAGTCGCCATTCGGT',
      pam: 'GCT',
      on_target_score: 74.1,
      off_target_score: 19.8,
      gc_percent: 60,
      notes: 'Cuts 3 bp downstream; comparable on-target score.',
    },
    {
      index: 3,
      cut_position: 24,
      strand: '-',
      guide: 'GAATGGCGACTGTCTTGTCC',
      pam: 'CCC',
      on_target_score: 71.0,
      off_target_score: 24.3,
      gc_percent: 55,
      notes: 'Reverse strand; viable backup if forward strands fail synthesis.',
    },
  ],
  ssodn: {
    reference_arm: 'TGGACAAGACAGTCGCCATTCGGTGCCTACATTCAAGAGAACAACGAA',
    variant_arm: 'TGGACAAGACAGTCGCCATTCGGTGCCTGCATTCAAGAGAACAACGAA',
    repair_template: 'TGGACAAGACAGTCGCCATTCGGTGCTTACATTCAAGAGAACAACGAA',
    edits_encoded: ['c.260G>A corrective edit', 'silent PAM-blocking edit'],
    arm_lengths: { left: 60, right: 60 },
    estimated_hdr_efficiency: 0.15,
  },
}
