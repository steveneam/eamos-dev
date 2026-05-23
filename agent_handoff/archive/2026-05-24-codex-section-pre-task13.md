## Codex — Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule
1/2). Section last edited: 2026-05-23 21:53 +1000 - Codex.

**Latest Codex update (2026-05-23 21:53 +1000 - Codex):** implemented and
verified the user-directed Variant Evidence Report frontend/backend slice for
gnomAD ancestry visualization, age distribution disclosure, ClinicalTrials.gov
rows, and removal of the visible limitations section. This was an explicit
role redirect from the earlier backend-only handoff.

**Implementation completed:**
- Mirrored the additive report contract in both `app/frontend/src/lib/backend.ts`
  and `app/web/lib/backend.ts`, including `TrialMatch`,
  `TherapiesTrialsSection`, report profile sections, call-card interactions,
  and `population_frequency`.
- Added `PopulationFrequencySection` in both Vite and Next 16 report mirrors:
  SimpleMaps `/world.svg` basemap, proprietary EAMOS genetic-ancestry anchor
  layer, relative AF heat scale, hover/focus sidebar rows with exact AF/AN/AC,
  and a tabbed age-distribution view using source age histograms.
- Kept gnomAD wording aligned with the 2023 genetic-ancestry guidance: source
  groups are inferred genetic-similarity groups, not race/ethnicity, patient
  ancestry, or exact geography.
- Removed the visible `LimitationsSection` card from both report mirrors while
  preserving `limitations` as backend/API data for malformed/unresolved flows.
- Reworked the trials card in both mirrors to show structured
  ClinicalTrials.gov rows from `report_profile.therapies_trials.trial_rows`.
- Updated `ClinicalTrialsTool` / lookup orchestration so live lookups can carry
  up to 15 active/not-yet ClinicalTrials.gov rows into the report evidence and
  typed profile; fixture mode keeps a representative RPE65 text summary without
  fabricating structured eligibility rows.
- Refreshed the RPE65 demo data: ClinicalTrials.gov RPE65 sample now shows 13
  active/not-yet rows and 29 total search records; gnomAD sample wording now
  matches AC 2 / AN 125,748 / AF 0.0000159 rather than the older absent wording.
- Fixed stale report UI risks found by subagents: no static RPE65 header stats
  for non-RPE65 variants, no unavailable ClinVar badge, zero AF/age bins render
  as zero rather than fake minimum bars, and mobile report shell no longer
  compresses the nav search.

**Verification:**
- `cd app/backend && python -m pytest tests/test_variant_report_orchestration.py tests/test_clinical_trials_tool.py tests/test_variant_cache.py -q`
  passed.
- `cd app/backend && python -m pytest tests/test_variant_search_integration.py::test_lookup_fixture_mode_resolves_grch38_and_litvar_publications tests/test_variant_report_orchestration.py tests/test_clinical_trials_tool.py -q`
  passed.
- `cd app/backend && python -m ruff check .` passed.
- `cd app/backend && python -m black --check --target-version py310 .` passed.
- `cd app/backend && python -m pytest -q` passed (4 skipped; existing JWT
  short-key warnings only).
- `cd app/frontend && npx tsc -b --pretty false` passed.
- `cd app/web && npx tsc --noEmit --pretty false` passed.
- `cd app/frontend && npm run build` passed (existing Vite chunk-size warning).
- `cd app/web && npm run build` passed on Next.js 16.2.6.
- Browser verification against `http://localhost:3000/report?demo=1` passed on
  desktop and mobile: map SVG present, AF heat legend present, age tab works,
  13 ClinicalTrials.gov links render, limitations text not visible, no page
  overflow, and no uncanceled network/runtime failures.

**Still gated / next:**
- Patient Report Pipeline (`/runs`) remains parked.
- AlphaMissense remains hidden/on hold; no surfacing work was done.
- Future backend/data work remains gated: production gnomAD ETL/warehouse,
  per-hover endpoint, local DuckDB/parquet prototype, and richer exome/genome
  age-distribution source hydration.
- Next server is running on `http://localhost:3000` for user review.

**Clear-safe:** yes; implementation, verification, and handoff are synced.

**Latest resume prompt:**
`# Resume prompt · 2026-05-23 21:53 +1000 · Codex gnomAD ancestry map + trials report slice complete
Eamos. Read CODEX.md, agent_handoff/README.md, agent_handoff/CURRENT.md (Codex section, Locks, Requests), agent_handoff/on_hold/register.md, agent_handoff/RISKS.md, agent_handoff/DECISIONS.md, docs/proprietary/README.md, docs/proprietary/index.json, docs/proprietary/variant-report-orchestration.md, plans/variant-report-layout/{design.md,spec.md,plan.md}, plans/variant-report-data-orchestration/{design.md,spec.md,plan.md}, then git status --short --branch.
Delta: Codex implemented the user-directed report slice across Vite + Next 16: SimpleMaps-backed gnomAD genetic-ancestry AF heat map/sidebar, age-distribution tab, visible limitations card removed, structured ClinicalTrials.gov rows added, RPE65 demo/trials/gnomAD wording refreshed, and mobile report shell fixed.
Verification: full backend pytest passed; ruff passed; black --check --target-version py310 passed; Vite tsc/build passed; Next tsc/build passed; browser verification passed on desktop/mobile at /report?demo=1. Next server is running at http://localhost:3000.
Next: commit/push status should be checked if resuming immediately; future work remains gated for /runs, AlphaMissense, production gnomAD ETL/warehouse, per-hover endpoint, DuckDB/parquet prototype, and richer exome/genome age source hydration.
End clear-safe (Safe-to-clear line + fresh stamped resume prompt).`
