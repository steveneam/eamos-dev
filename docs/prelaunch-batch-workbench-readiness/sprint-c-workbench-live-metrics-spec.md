# Sprint C Workbench Live Metrics Spec

## What

Make Workbench tool outputs honest and gene/variant agnostic for launch: primer design, CRISPR guide design, ssODN design, off-target enumeration, off-target screening-primer design, TIDE-style outcome analysis, and alignment must either run through a live local/backend provider for the requested input or visibly identify themselves as fixture, fallback, gated, or unavailable.

## Context

Sprint B proved Batch and panel launch posture. Sprint C raises the bar for Workbench: the UI cannot imply that RPE65 fixtures or de-identified demo rows are general live results. Existing Workbench code has a mixed posture:

- Primer and CRISPR guide design have real-mode service paths through `SequenceContextService`.
- ssODN has local MANE/hg38 handling for supported inputs and sequence-context fallback for generic inputs.
- Off-target enumeration is source-backed only when the local SpCas9 GRCh38 SQLite index is configured and ready; otherwise auto mode returns a labelled mock fallback.
- Screening-primer design is source-backed only when a selected site can be mapped to a real region/window or includes a template sequence.
- TIDE analysis is a live local observed-only analyzer from uploaded traces; it is not a Lindel predictor and does not run the NKI/TIDE NNLS decomposition solver.
- Alignment has backend real-mode providers, but the browser Align workspace historically used a viewer-derived reference and client-side read alignment without a visible backend source line.

## Requirements

1. Every Workbench response that can be rendered as a result must carry `source_disclosure` when the backend can identify provenance.
2. The frontend must render source status consistently: `source_backed`, `local_provider`, `fallback`, `fixture`, `gated`, or `unavailable`.
3. Non-default gene/variant requests must not silently receive RPE65 fixture payloads.
4. Primer metrics must run through the live Primer3/local provider path when Workbench live design is enabled, and must disclose local provider caveats for specificity/SNP masking.
5. CRISPR guide metrics must run through the configured CRISPR provider for the requested sequence context, and must not label platform-gated scores as available.
6. Off-target enumeration must be source-backed only with the indexed SQLite provider; auto-mode fallback must be labelled fallback.
7. Screening-primer output must disclose whether primers were designed against real reference windows/templates or mock windows.
8. TIDE output must disclose observed-only local-provider status and must keep predicted/Lindel series hidden unless numeric predicted values are returned.
9. Alignment must use the Workbench live-design flag for backend `/align`, resolve browser references through `/align/reference`, and show reference provenance in the Align panel.
10. Tests must include at least one non-RPE65 synthetic sequence-context path to prove the work is not fixture-bound.

## Design

The backend owns the truth contract with `SourceDisclosure` on Workbench schemas. Service boundaries populate disclosure from the provider actually used. Frontend code consumes that shape through `lib/workbench/source-disclosure.ts`, which centralizes labels and caveats.

For Align, the browser workspace keeps the current multi-read client-side workflow because it supports drag/drop AB1 files, pasted reads, orientation switching, quality trimming, mismatch navigation, and chromatogram rendering. The reference, however, is resolved through `/api/v1/align/reference`; fixture reference fallback is allowed only for the default RPE65 demo, and non-default backend failures remain unavailable instead of substituting the RPE65 fixture.

## Decisions

- Choice: Treat local deterministic/Primer3/Sanger/TIDE providers as `local_provider`, not `source_backed`.
  - Why: They are live computations but not external source-backed datasets.
  - Reversible: Yes, individual providers can be promoted to `source_backed` when they use a ready immutable source/index.

- Choice: Do not claim full off-target source-backed readiness without the GRCh38 SpCas9 SQLite index.
  - Why: Whole-genome off-target enumeration cannot be made honest from a single sequence window.
  - Reversible: Yes, once the index artifact is configured and preflight-ready.

- Choice: Keep TIDE as observed-only for launch.
  - Why: It produces live trace-derived metrics without bundling or implying a validated TIDE/Lindel prediction solver.
  - Reversible: Yes, a future solver can add predicted bins and update disclosure.

## Invariants

- Fixture and fallback results must remain visually labelled.
- Workbench live mode must not depend on the global `use_real_apis` flag.
- Existing fixture-mode tests must keep passing when `workbench_live_design_enabled=false`.
- Backend and frontend Workbench contracts must stay field-name aligned.

## Error Behavior

- Missing sequence context returns a 422 Workbench design error with warnings.
- Forced source-backed providers with missing required artifacts fail closed rather than falling back silently.
- Auto off-target mode may fall back, but must disclose fallback status.
- Non-default alignment reference fallback must not return the RPE65 fixture.

## Testing Strategy

- Backend: `tests/test_workbench_api.py`, `tests/test_frontend_contract.py`, and focused preflight CLI tests.
- Frontend: `npx tsc --noEmit`, lint, and browser proof on `/workbench` across desktop and narrow viewport.
- Browser proof: verify source chips for Primer, CRISPR design, off-targets, ssODN, TIDE, and Align reference.

## Out of Scope

- Downloading or building the full off-target index artifact.
- Enabling Vercel/Render env flips or provider flips.
- Adding Lindel/NKI TIDE decomposition.
- Replacing the current Align multi-read browser interaction model.
