/*
   Mock-first post-CRISPR editing-outcome sample.

   The frontend Outcomes tab is scaffolded now, while the backend
   POST /api/v1/crispr/tide endpoint, AB1 parsing, and numerical solver are
   still gated work. This type is frontend-local until the backend contract
   lands, matching the existing mock-first workbench pattern.

   This sample is observed-only. It intentionally does not imply that Eamos
   runs a repair-outcome model. A later Cas9 backend integration can expose
   crisprScore's Lindel-derived frameshift probability as a separate score.
*/

/** One indel-size bin. size is bp: negative = deletion, positive = insertion,
 *  0 = unmodified (wild-type). predicted is null when no repair-outcome model
 *  is available. */
export interface IndelBin {
  size: number
  observed: number
  predicted: number | null
}

export interface CrisprTideResult {
  /** Cas9 cleavage base index used for the deconvolution. */
  cut_site_index: number
  /** Overall editing efficiency = 1 - wild-type fraction (0..1). */
  editing_efficiency: number
  /** NNLS fit quality (R2) of the TIDE deconvolution. */
  r_squared: number
  /** Indel-frequency spectrum, ascending by size. */
  spectrum: IndelBin[]
  /** True only when a backend result explicitly includes predicted values. */
  predicted_available: boolean
  notes: string
}

export const CRISPR_TIDE_SAMPLE: CrisprTideResult = {
  cut_site_index: 100,
  editing_efficiency: 0.69,
  r_squared: 0.93,
  predicted_available: false,
  notes:
    'Sample observed-only TIDE spectrum. No repair predictor is run; a later Cas9 integration may add crisprScore Lindel-derived frameshift probability as a separate score.',
  spectrum: [
    { size: -10, observed: 0.004, predicted: null },
    { size: -9, observed: 0.006, predicted: null },
    { size: -8, observed: 0.009, predicted: null },
    { size: -7, observed: 0.012, predicted: null },
    { size: -6, observed: 0.018, predicted: null },
    { size: -5, observed: 0.027, predicted: null },
    { size: -4, observed: 0.041, predicted: null },
    { size: -3, observed: 0.064, predicted: null },
    { size: -2, observed: 0.142, predicted: null },
    { size: -1, observed: 0.271, predicted: null },
    { size: 0, observed: 0.31, predicted: null },
    { size: 1, observed: 0.166, predicted: null },
    { size: 2, observed: 0.031, predicted: null },
    { size: 3, observed: 0.012, predicted: null },
    { size: 4, observed: 0.006, predicted: null },
    { size: 5, observed: 0.003, predicted: null },
  ],
}
