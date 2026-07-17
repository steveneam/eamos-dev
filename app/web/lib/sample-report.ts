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
const rawNegativeControl = rpe65Sample as unknown as LookupResponse

// The captured snapshot predates the fact-policy envelope and contains legacy
// condition labels and case counts. Keep the immutable capture for replay, but
// do not expose those rows until a backend-computed public decision is present.
export const RPE65_NEGATIVE_CONTROL_SAMPLE: LookupResponse = {
  ...rawNegativeControl,
  report_payload: {
    ...rawNegativeControl.report_payload,
    associated_conditions: (rawNegativeControl.report_payload.associated_conditions ?? []).filter(
      (condition) => condition.public_serialization_allowed === true,
    ),
  },
}
