# Sprint C Workbench Live Metrics Plan

## Task 1 - Source Disclosure Contract

Goal: Ensure every Workbench backend result can disclose whether it is source-backed, local, fallback, fixture, gated, or unavailable.

Relevant files: `app/backend/app/schemas/workbench.py`, `app/backend/app/services/workbench_design.py`, Workbench fixtures, `app/web/lib/backend.ts`, `app/frontend/src/lib/backend.ts`.

Acceptance criteria: backend Workbench responses include `source_disclosure`; frontend contract canary passes; fixtures explicitly say `fixture` or `fallback`.

Verify: `python -m pytest tests/test_workbench_api.py tests/test_frontend_contract.py -q`.

## Task 2 - Live, Gene-Agnostic Service Paths

Goal: Prove live-mode Primer, CRISPR guide, ssODN, and Align paths use the requested sequence context rather than RPE65 fixtures.

Relevant files: `app/backend/app/services/workbench_design.py`, `app/backend/tests/test_workbench_api.py`.

Acceptance criteria: non-RPE65 synthetic context tests cover Primer, CRISPR, and Align; `/api/v1/align` honors `workbench_live_design_enabled`; fixture mode remains available when explicitly disabled.

Verify: focused Workbench pytest.

## Task 3 - Off-Target and Screening Primer Honesty

Goal: Keep off-target and screening-primer outputs useful while preventing fallback rows from looking source-backed.

Relevant files: `app/backend/app/services/crispr_offtarget_screening.py`, `app/backend/app/services/workbench_design.py`, `app/web/components/workbench/crispr/OffTargetTab.tsx`.

Acceptance criteria: indexed provider responses disclose `source_backed`; auto/mock responses disclose `fallback`; screening primers disclose real reference-window/template vs mock-window provenance.

Verify: Workbench API tests plus browser proof on the off-target tab.

## Task 4 - Frontend Disclosure Audit

Goal: Render consistent source chips and caveats across Primer, CRISPR design, ssODN, off-targets, screening primers, TIDE outcomes, and Align.

Relevant files: `app/web/lib/workbench/source-disclosure.ts`, Workbench panel components, `app/web/components/workbench/workbench.css`.

Acceptance criteria: every rendered result surface shows a truthful source line or existing equivalent; fixture/fallback states are visually distinct and responsive.

Verify: TypeScript, lint, and browser screenshots/console check.

## Task 5 - Release Evidence and Handoff

Goal: Record Sprint C status with exact caveats for anything not fully source-backed.

Relevant files: `PROGRESS.md`, `agent_handoff/CURRENT.md`, `docs/prelaunch-batch-workbench-readiness/resume-prompt.md`.

Acceptance criteria: handoff states which Workbench outputs are live local providers, which are source-backed only with artifacts, and which remain fixture/fallback/gated.

Verify: run the structural boundary guards and complete the final handoff review.
