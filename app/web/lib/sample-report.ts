import type { LookupResponse } from './backend'
import rpe65Sample from './rpe65-sample.json'

// Offline demo fixture for `/report` (bare) and `?demo=1`.
//
// Captured verbatim from a live RPE65 c.260A>G lookup on eamos-dev (2026-05-24)
// so the offline demo mirrors real backend output exactly — same VUS call,
// gnomAD "variant not found" state, call cards, and section ordering. The old
// hand-curated sample drifted from reality (it showed Likely Pathogenic with
// populated gnomAD), which is why it was replaced with a real snapshot.
//
// To refresh: run the lookup, save the /api/v1/lookup response body, and replace
// rpe65-sample.json.
export const RPE65_SAMPLE = rpe65Sample as unknown as LookupResponse
