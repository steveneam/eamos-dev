import type { CrisprTideResponse, CrisprTideSpectrumBin } from '../backend'

/*
   Mock-first post-CRISPR editing-outcome sample.

   The backend contract is source-led by CrisprTideResponse. The bundled
   sample keeps the Workbench surface usable when the route is absent or the
   backend is offline, and remains clearly marked as frontend fallback data.
*/

/** One indel-size bin. size is bp: negative = deletion, positive = insertion,
 *  0 = unmodified (wild-type). predicted is null when no repair-outcome model
 *  is available. */
export type IndelBin = CrisprTideSpectrumBin

export interface CrisprTideResult
  extends Omit<
    CrisprTideResponse,
    'source_backed' | 'analysis_kind' | 'provider_label' | 'warnings'
  > {
  /** Optional additive backend metadata; absent means frontend sample/fallback. */
  source_backed?: boolean
  analysis_kind?: 'sample' | CrisprTideResponse['analysis_kind'] | 'lindel'
  provider_label?: string
  warnings?: string[]
}

export const CRISPR_TIDE_SAMPLE: CrisprTideResult = {
  source_backed: false,
  analysis_kind: 'sample',
  provider_label: 'Frontend sample/fallback',
  source_disclosure: {
    source_status: 'fallback',
    provider_id: 'frontend_tide_sample',
    provider_label: 'Frontend sample/fallback',
    source_version: null,
    cache_status: null,
    warnings: ['workbench_backend_unavailable'],
    requirements: ['crispr_tide_backend'],
  },
  cut_site_index: 100,
  editing_efficiency: 0.69,
  r_squared: 0.93,
  predicted_available: false,
  notes:
    'Frontend sample/fallback observed-only spectrum. Uploaded traces are not parsed here; a later Cas9 integration may add Lindel-derived frameshift probability as a separate backend score.',
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
