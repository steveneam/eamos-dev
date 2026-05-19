/* ───────────────────────────────────────────────────────────────────────
   Mock-first post-CRISPR editing-outcome (TIDE) sample.

   Blueprint 2 is scaffolded on the frontend now; the backend
   `POST /api/v1/crispr/tide` endpoint + its Pydantic/`backend.ts` contract
   are a gated Codex milestone (see plans/crispr-integration.md §7). Per
   Coordination Rule 5 (contract changes are backend-led) the TIDE shape is
   declared **frontend-local here**, not added to `lib/backend.ts`, until
   Codex ships §7 — at which point the canonical type moves into the shared
   contract and this becomes a thin re-export / fixture.

   Shape transcribed from Blueprint 2's reference dashboard response: a TIDE
   (Brinkman 2014) indel-frequency spectrum with an optional AI-predicted
   (SPROUT / inDelphi) series. The real backend will return
   `predicted_available: false` (no ML weights yet) and the FE renders
   observed-only; this sample carries a predicted series so the grouped
   chart design is exercised offline.
─────────────────────────────────────────────────────────────────────── */

/** One indel-size bin. `size` is bp: negative = deletion, positive =
 *  insertion, 0 = unmodified (wild-type). `predicted` is null per bin when
 *  no repair-outcome model is available. */
export interface IndelBin {
  size: number
  observed: number
  predicted: number | null
}

export interface CrisprTideResult {
  /** Cas9 cleavage base index used for the deconvolution (Blueprint 2). */
  cut_site_index: number
  /** Overall editing efficiency = 1 − wild-type fraction (0..1). */
  editing_efficiency: number
  /** NNLS fit quality (R²) of the TIDE deconvolution. */
  r_squared: number
  /** Indel-frequency spectrum, ascending by `size`. */
  spectrum: IndelBin[]
  /** False until a SPROUT/inDelphi repair model is sourced — drives the
   *  observed-only fallback in the UI. */
  predicted_available: boolean
  notes: string
}

export const CRISPR_TIDE_SAMPLE: CrisprTideResult = {
  cut_site_index: 100,
  editing_efficiency: 0.69,
  r_squared: 0.93,
  predicted_available: true,
  notes:
    'TIDE Sanger deconvolution (Brinkman 2014). AI series shown is the Blueprint-2 reference predictor; production runs are observed-only until repair-model weights are sourced.',
  spectrum: [
    { size: -10, observed: 0.004, predicted: 0.006 },
    { size: -9, observed: 0.006, predicted: 0.008 },
    { size: -8, observed: 0.009, predicted: 0.011 },
    { size: -7, observed: 0.012, predicted: 0.015 },
    { size: -6, observed: 0.018, predicted: 0.02 },
    { size: -5, observed: 0.027, predicted: 0.03 },
    { size: -4, observed: 0.041, predicted: 0.038 },
    { size: -3, observed: 0.064, predicted: 0.058 },
    { size: -2, observed: 0.142, predicted: 0.131 },
    { size: -1, observed: 0.271, predicted: 0.255 },
    { size: 0, observed: 0.31, predicted: 0.32 },
    { size: 1, observed: 0.166, predicted: 0.158 },
    { size: 2, observed: 0.031, predicted: 0.029 },
    { size: 3, observed: 0.012, predicted: 0.013 },
    { size: 4, observed: 0.006, predicted: 0.005 },
    { size: 5, observed: 0.003, predicted: 0.004 },
  ],
}
