> ARCHIVED 2026-07-15 11:19 UTC by Codex - the stale pause register was
> retired; live founder gates now remain in `RISKS.md`. Original content
> follows verbatim.

---

# On-Hold And Pause Register

Last updated: 2026-06-03 22:54 +1000 - Claude (Tier-3 report visuals parked: AlphaFold 3D + PDBe-Molstar)

This is a pickup aid, not a replacement for `DECISIONS.md`, `RISKS.md`, or the
active plans. Keep the list sorted by priority so resume prompts can point here
instead of restating every hold.

Resume prompts should point to this register for parked holds. It is still
fine for prompts to explicitly name hard gates such as Patient Report Pipeline
(`/runs`) and AlphaMissense, so the no-touch constraints remain visible even
when the detail lives here.

## 1. Cross-Check Attention

### Variant Evidence Report frontend mirror/render backlog

- Added: 2026-05-23 11:45 +1000 - Codex
- Last touched: 2026-05-23 11:57 +1000 - Codex
- Owner/next reviewer: Claude for frontend mirror/render; Codex for backend
  contract clarification.
- Resume condition: Claude returns to Variant Evidence Report frontend work.
- Source of truth: `agent_handoff/CURRENT.md` Cross-Agent Requests,
  `plans/search-bar-ai-input/`, `plans/variant-literature-extraction/`,
  `plans/variant-report-layout/`, and
  `plans/variant-report-data-orchestration/`.
- Notes: mirror/render is pending for raw `search_text` and parse UX,
  EP-VLEx publications, functional evidence, call cards/gnomAD detail, and the
  larger Variant Evidence Report section order.

### Variant Report Data Orchestration plan review

- Added: 2026-05-23 11:45 +1000 - Codex
- Last touched: 2026-05-23 11:45 +1000 - Codex
- Owner/next reviewer: user approval, then Codex implementation.
- Resume condition: user approves implementation of
  `plans/variant-report-data-orchestration/plan.md`.
- Source of truth: `plans/variant-report-data-orchestration/{design.md,spec.md,plan.md}`.
- Notes: plan is acceptable for implementation after tightening the
  `TherapyMatch` first-slice schema choice and adding explicit match-level
  gating tests.

## 2. Active Lane Pauses

### Codex backend next-task queue paused

- Added: 2026-05-26 20:29 +1000 - Codex
- Last touched: 2026-05-26 20:29 +1000 - Codex
- Owner/next reviewer: user, then Codex.
- Resume condition: user finishes/redirects the bigger next-session topic and
  explicitly resumes Codex backend queue work.
- Source of truth: `agent_handoff/CURRENT.md` Codex section,
  `plans/v2-backend.md`, `PROGRESS.md` Sessions 41-42.
- Notes: do not auto-start the previous Codex next tasks on resume. Parked
  queue includes landing/report/workbench checks against
  `project_100_sample_manifest.json`, multi-segment/cross-exon viewer edit
  rendering and source-backed confidence gates, Workbench Reading Room styling
  migration, and SpliceAI source-cache/licensing review.

### Frontend design-overhaul implementation

- Added: 2026-05-23 11:45 +1000 - Codex
- Last touched: 2026-05-23 11:45 +1000 - Codex
- Owner/next reviewer: Claude.
- Resume condition: user approves the rendered reviewable plan and tells Claude
  to implement.
- Source of truth: `plans/v2-design-overhaul/` and Claude's next-session doc.
- Notes: no implementation until approved.

### Frontend Workbench (port/redesign) on hold

- Added: 2026-05-23 12:35 +1000 - Claude
- Last touched: 2026-05-23 12:35 +1000 - Claude
- Owner/next reviewer: Claude.
- Resume condition: user lifts the hold (current focus = landing page + Variant
  Evidence Report only).
- Source of truth: Claude's next-session doc; `plans/v2-frontend.md` (FE-4..FE-6
  Workbench, complete in the Vite app).
- Notes: the Vite Workbench (FE-0..FE-6 done) is parked as-is and is NOT being
  ported to Next.js or redesigned for now. The Next.js migration + new-aesthetic
  effort targets landing + report only.

### Frontend framework migration decision

- Added: 2026-05-23 11:45 +1000 - Codex
- Last touched: 2026-05-23 11:45 +1000 - Codex
- Owner/next reviewer: Claude for frontend migration planning; Codex for API
  contract compatibility.
- Resume condition: user confirms React/Vite to Next.js migration direction.
- Source of truth: future Claude frontend plan update.
- Notes: backend should remain route/client agnostic if Claude preserves the
  API contract surface.

## 3. Workbench And Later Build Queue

### Tier-3 report visuals - AlphaFold 3D structure + PDBe-Molstar viewer

- Added: 2026-06-03 22:54 +1000 - Claude
- Last touched: 2026-06-03 22:54 +1000 - Claude
- Owner/next reviewer: user, then Claude (frontend) once lifted.
- Resume condition: explicit user approval to build the in-report 3D structure view.
- Source of truth: `plans/predictor-visuals-contracts/spec.md`; vault
  `Wiki/product/predictor-visuals-build-spec.md` (Visual 3) and
  `Wiki/syntheses/predictor-build-roadmap.md` (Tier 3).
- Notes: dropped from the active visuals set 2026-06-03 (user). PDBe-Molstar is a
  frontend-only 3D viewer (Mol* wrapper) with NO backend/adapter integration; its sole
  job was rendering an AlphaFold structure, so it parks with AlphaFold. Both are Tier-3
  (the roadmap defers 3D behind the 1-D protein-domain track). Accuracy note: the planned
  path used the AlphaFold DB API (one ~1-5 MB precomputed .cif per UniProt accession,
  cached) - NOT hosting the 1 TB model. Still parked. The other predictor visuals
  (splice-outcome SVG, the §4 Nightingale domain track, the per-gene confidence badge)
  are NOT affected and remain the active FE visuals lane.

### Workbench real-engine follow-ups

- Added: 2026-05-23 11:45 +1000 - Codex
- Last touched: 2026-05-23 11:45 +1000 - Codex
- Owner/next reviewer: Codex for backend engines; Claude for frontend surfaces.
- Resume condition: explicit user approval for a specific M-002 follow-up.
- Source of truth: `agent_handoff/RISKS.md`, `agent_handoff/TASKS.md`,
  `plans/v2-backend.md`, `plans/v2-frontend.md`.
- Notes: includes TIDE/post-edit analytics, DeepHF weights, genome-wide
  Bowtie/BWA off-targets, raw sequence/genomic-region fields, persistence, and
  related Workbench tool hardening.

### Gene Viewer enrichment

- Added: 2026-05-23 11:45 +1000 - Codex
- Last touched: 2026-05-23 11:45 +1000 - Codex
- Owner/next reviewer: Codex for backend schema/data; Claude for frontend
  viewer integration.
- Resume condition: user approves the next gene-viewer backend/frontend slice.
- Source of truth: `plans/gene-viewer/` and `agent_handoff/CURRENT.md`
  Cross-Agent Requests.
- Notes: additive transcript model, conservation hydration, and fuller ClinVar
  support remain future work.

## 4. Parked Holds

### Patient Report Pipeline

- Added: 2026-05-19 14:22 +1000 - Codex decision record; indexed here
  2026-05-23 11:45 +1000 - Codex.
- Last touched: 2026-05-23 11:45 +1000 - Codex
- Scope: `/runs`, `LegacyRunsApp`, PDF upload -> intake -> clinician review.
- Owner/next reviewer: user only.
- Resume condition: explicit user instruction to reopen Patient Report
  Pipeline work.
- Source of truth: `agent_handoff/DECISIONS.md` "2026-05-19: Naming
  Convention + Patient Report Pipeline On Hold".
- Notes: do not extend the shipped auto demo-session auth wiring unless the
  hold is lifted. Prompt shorthand: Patient Report Pipeline (`/runs`) is ON
  HOLD; no upload/review/approve/drop/chat/pdf/PDF-preview expansion until the
  user explicitly reopens this lane.

### AlphaMissense display/integration

- Added: 2026-05-19 14:22 +1000 - Codex decision record; indexed here
  2026-05-23 11:45 +1000 - Codex.
- Last touched: 2026-05-23 11:57 +1000 - Codex
- Owner/next reviewer: user only.
- Resume condition: explicit user instruction to re-enable AlphaMissense.
- Source of truth: `agent_handoff/DECISIONS.md` "2026-05-19: AlphaMissense On
  Hold".
- Notes: assets and contract literals stay; display remains off. Prompt
  shorthand: AlphaMissense is ON HOLD, not cancelled; do not re-enable,
  surface, remove, or refactor its kept assets unless the user explicitly
  approves that lane.

### Mouse/mm39 Workbench support

- Added: 2026-05-23 11:45 +1000 - Codex
- Last touched: 2026-05-23 11:45 +1000 - Codex
- Owner/next reviewer: user direction, then Codex/Claude by lane.
- Resume condition: explicit user approval to begin mouse support work.
- Source of truth: `plans/v2-frontend.md` "Tasks deferred to M-002" and future
  backend plan.
- Notes: current Workbench assumptions remain human/hg38 unless a scoped mouse
  support task is approved.
