import type { LookupResponse } from './backend'
import rpe65Sample from './rpe65-sample.json'

// Offline negative-control fixture for explicit `?fixture=rpe65-negative`.
//
// Captured verbatim from a live RPE65 c.260A>G lookup on eamos-dev (2026-05-25)
// so the fixture mirrors real backend output exactly: same VUS call, gnomAD
// "variant not found" state, call cards, and section ordering. The old
// hand-curated sample drifted from reality, which is why it was replaced with a
// real snapshot.
//
// Do not use this as the primary demo/sample report: RPE65 c.260A>G is a
// source-missing control, not a comprehensive live-metric showcase.
//
// To refresh: run the lookup, save the /api/v1/lookup response body, and replace
// rpe65-sample.json.
export const RPE65_NEGATIVE_CONTROL_SAMPLE = rpe65Sample as unknown as LookupResponse
