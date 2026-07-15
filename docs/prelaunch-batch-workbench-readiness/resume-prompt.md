# Prelaunch Batch And Workbench Resume Prompt

Status: active session seed.
Last updated: 2026-06-30 14:22 +1000 by Codex.

## Purpose

Use this file to keep Batch and Workbench launch-readiness work persistent across
sessions. A future agent should be able to read this file, know what is already
done, know the next sprint, and avoid reopening completed decisions.

Update this file whenever a sprint task is completed, skipped, or materially
changed.

## Done

- ClinVar/report generated artifact phase is complete on SG for
  `clinvar_gene_distribution_index`.
- No further deploy, seed, provider flip, runtime script, or live sync is needed
  for that ClinVar artifact.
- Design checkpoint created:
  `docs/prelaunch-batch-workbench-readiness/design.md`.
- Architecture review created:
  `docs/prelaunch-batch-workbench-readiness/review.md`.
- Agile bucket plan created:
  `docs/prelaunch-batch-workbench-readiness/plan.md`.
- Launch posture note created:
  `docs/prelaunch-batch-workbench-readiness/launch-posture.md`.
- Source disclosure taxonomy created:
  `docs/prelaunch-batch-workbench-readiness/source-disclosure-taxonomy.md`.
- Sprint A Batch safety implementation is complete and pushed in
  `f7d74c2 feat(batch): require auth for launch jobs`:
  - Batch create/get require an authenticated principal.
  - Batch uploads and jobs carry owner metadata.
  - Upload refs and job IDs are scoped to the owner and return 404 on
    cross-owner access.
  - Batch job creation has its own rate-limit scope.
  - Web Batch create/get/upload calls attach the Supabase bearer token.
  - Inline create failures no longer become silent mock completed jobs.
- Sprint B Task 2.1 Batch failure, expiry, and empty-state UX is implemented
  locally:
  - Web Batch transport throws typed request errors for auth, missing/expired,
    rate-limit, validation, unavailable, and generic request failures.
  - Compare Batch UI shows issue-specific failure cards without fabricating a
    completed mock job.
  - Completed-but-empty runs and scoped-zero-match states have explicit copy.
  - Scope changes after a run show a stale-regenerate notice.
  - Batch warnings from jobs are retained and rendered.
- Sprint B panel launch policy is implemented locally:
  - Current panels remain warning-labeled local launch panels.
  - Panel warnings are surfaced in the preset list and active-scope chip as
    `local launch`, `fixture`, or `warning`.
  - Offline/mock panel fallback warnings are no longer hidden.
- Sprint C Workbench live-metrics disclosure is implemented locally:
  - Backend Workbench responses now carry `source_disclosure` for primer,
    CRISPR guide, ssODN, off-target enumeration, screening-primer, TIDE,
    alignment, trace, and alignment-reference outputs.
  - Workbench fixture/sample payloads identify themselves as `fixture` or
    `fallback`; live local providers identify as `local_provider`, and indexed
    or real reference-backed paths identify as `source_backed`.
  - Workbench UI renders shared source labels across Primer, CRISPR design,
    ssODN, off-targets, screening primers, TIDE outcomes, and Align reference
    provenance.
  - `/api/v1/align` now honors `workbench_live_design_enabled`, and backend
    tests include a non-RPE65 synthetic context path proving the Align service
    is not RPE65-fixture-bound.
  - The Align panel resolves references through `/api/v1/align/reference`,
    keeps the current client-side multi-read alignment UX, and refuses to use
    the RPE65 fixture fallback for non-default queries when the backend is down.
- Sprint C gap spec and plan were added:
  - `docs/prelaunch-batch-workbench-readiness/sprint-c-workbench-live-metrics-spec.md`
  - `docs/prelaunch-batch-workbench-readiness/sprint-c-workbench-live-metrics-plan.md`
- Code release `d5ee212 feat(prelaunch): disclose workbench and batch launch states`
  was pushed to `origin/main` and deployed on SG Render as
  `dep-d91k7d6q1p3s73c493cg` on commit
  `d5ee212f41956ac22be68a27a5626d984513d780`.
- Live backend Workbench smokes passed after deploy:
  - `/healthz` is OK.
  - Provider-cache reports `clinvar_gene_distribution_index.ready=true`.
  - Primer returns `local_provider` / `primer3_template_specificity`.
  - CRISPR guide design returns `local_provider` /
    `local_deterministic_spcas9`.
  - Align reference returns `source_backed` /
    `sequence_context_alignment_reference`.
  - Off-target enumeration returns labelled `fallback` / `mock_cas_offinder`.
- Vercel HTTP checks passed without browser use:
  `/workbench?gene=RPE65&cdna=c.260A%3EG` returned 200, and the Vercel
  provider-cache proxy returned `status=ok`, `database=ok`, and
  `clinvar_gene_distribution_index.ready=true`.
- Local browser proof ran on `http://localhost:3001/compare` after refreshing
  the existing dev server:
  - Signed-out Generate shows `Sign-in required` and keeps the preview table.
  - Retinal panel scope shows `local launch`, stale-regenerate, and
    zero-match empty state.
  - Narrow viewport reported no horizontal overflow.
  - Chrome console/issue stream was clean after the final input-name patch.
- Current recommendation is:
  - PubMed stays API/cache for launch.
  - DuckDB/Parquet stays disabled analytical infrastructure for launch.
  - Batch launch work continues with signed-in/local proof only under an
    approved Supabase Auth test approach or existing approved session.
  - Workbench launch work starts with source/fallback disclosure and local
    functional proof.

## Not Done

- No signed-in browser Batch job run was performed. Creating or mutating a
  Supabase Auth test user/session was treated as external-state mutation and was
  not done without Steven's exact approval.
- No live SG Batch probe, provider flip, deploy, Storage mutation, Supabase
  metadata mutation, raw source download, or runtime sync has been performed.
- Source-backed generated panel catalog is not enabled. Build an offline SQLite
  panel artifact only if Steven makes source-backed panel provenance a launch
  blocker.
- Batch SQL persistence and reloadable job history remain conditional.
- Off-target enumeration is source-backed only when the GRCh38 SpCas9 SQLite
  index is configured and ready; auto/mock mode remains a labelled fallback.
- Off-target screening-primer design is source-backed only for real target
  regions/windows or caller-provided templates; mock-window output remains a
  labelled fallback.
- TIDE is a live local observed-only trace analyzer; it is not a Lindel
  predictor and not the NKI/TIDE NNLS solver.
- Sprint C browser proof has not run yet because Selom was using the browser.
- The combined Batch/Panel/Health sweep failed only on local environment drift:
  `tests/test_health_api.py::test_provider_cache_health_returns_sanitized_empty_aggregates`
  expected missing `clinvar_gene_distribution_index`, but this local workspace
  reports it ready. No Sprint C change touched the health route or test.

## Current Next Task

Sprint C is committed, pushed, and deployed through command-line/live HTTP
verification. Browser verification is pending because Selom was using the
browser.

Next task:

- When the browser is available, run local browser proof on `/workbench`:
  - Primer source line and fixture/local-provider labels.
  - CRISPR design source line and gated advanced-score copy.
  - ssODN source line and fallback/source-backed caveat.
  - Off-target source line and screening-primer fallback/source-backed label.
  - TIDE observed-only source line.
  - Align reference source line after `/align/reference` resolution.
  - Narrow viewport no-overflow and clean console/issues.
- Then run the structural boundary guards after any browser-proof fixes or
  final doc edits.
- Decide whether signed-in Batch browser proof remains deferred or should use
  an existing approved Supabase session / Steven-approved Auth test mutation.

## Sprint Ledger

| Sprint | Status | Scope | Next action |
| --- | --- | --- | --- |
| Planning | Complete | Design, architecture review, agile plan, resume prompt | Keep docs current as work progresses. |
| Sprint A - Safety And Honesty | Complete and pushed | Launch posture, source disclosure taxonomy, Batch auth transport, Batch owner scoping, Batch job rate limits, remove silent mock fallback | Do not redo. |
| Sprint B - Batch Functional Launch | Partly complete locally | Batch failure/expiry UX, panel launch policy, local signed-out browser proof | Resolve signed-in browser proof policy, then close or defer. |
| Sprint C - Workbench Functional Launch | Implemented locally; browser proof pending | Shared Workbench source disclosure model, label audit, backend smoke, build, spec/plan | Run deferred `/workbench` browser proof when browser is free. |
| Sprint D - Launch Evidence | Pending | PubMed hold note, DuckDB hold note, freshness policy, backend/web test gates, final launch-readiness note | Start after B/C verification. |

## Conditional Tracks

Only start these if Steven explicitly decides they are launch requirements:

- Batch SQL persistence:
  - Use existing SQLAlchemy app-db/session/repository pattern.
  - Suggested tables are in `review.md` and `plan.md`.
  - Do not jump to Supabase/queues/DuckDB for launch persistence.
- Source-backed panel catalog:
  - Use an offline generated SQLite artifact plus manifest/preflight.
  - Do not call PanelApp/ClinGen/GenCC/MONDO at request time.
- Benchling-style Workbench polish:
  - Use `docs/workbench-benchling-apply/spec.md`.
  - Treat as frontend polish, not backend readiness.

## Guardrails

Do not run any of these without Steven approving that exact action:

- Vercel command.
- Render env mutation.
- Provider or flag flip.
- Raw source download.
- Supabase metadata mutation.
- Supabase Storage mutation.
- One-off live runtime script.
- Runtime seed/sync.
- Destructive git.
- Commit.
- Push.

Also:

- Do not edit shared handoff/current/progress files unless the edit-lock
  protocol is followed.
- Do not treat dirty pre-existing docs as part of this work.
- Preserve license, provenance, fallback, and launch-gate metadata.
- Keep PubMed API/cache and DuckDB disabled unless a later approved task changes
  that posture.

## Verification Protocol

For docs-only updates:

```powershell
git diff --check -- docs/prelaunch-batch-workbench-readiness
```

For backend Sprint A/B/C code changes:

```powershell
cd app/backend
python -m pytest tests/test_batch_api.py tests/test_workbench_api.py tests/test_panels_api.py tests/test_health_api.py tests/test_workbench_preflight_cli.py -q
python -m ruff check app tests
python -m black --check --target-version py310 app tests
```

For web Sprint A/B/C changes:

```powershell
cd app/web
npx tsc --noEmit
npm run lint
npm run build
```

For browser-facing changes, start local backend/web servers and browser-verify
desktop and mobile flows. Do not use Vercel commands.

## Verification Run

2026-06-28 20:29 +1000 by Codex:

- `cd app/backend; python -m pytest tests/test_batch_api.py -q` passed.
- `cd app/backend; python -m ruff check app tests` passed.
- `cd app/backend; python -m black --check --target-version py310 app\api\routes\batch.py app\core\config.py app\core\rate_limit.py app\services\batch.py tests\test_batch_api.py` passed.
- `cd app/backend; python -m black --check --target-version py310 app tests`
  failed on 10 unrelated pre-existing files outside this Sprint A slice.
- `cd app/web; npx tsc --noEmit` passed.
- `cd app/web; npm run lint` passed.
- `git diff --check -- app\backend app\web docs\prelaunch-batch-workbench-readiness` passed.
- Browser verification had not been run yet.

2026-06-28 21:13 +1000 by Codex:

- `cd app/backend; python -m pytest tests/test_panels_api.py tests/test_batch_api.py -q` passed.
- `cd app/web; npx tsc --noEmit` passed.
- `cd app/web; npm run lint` passed.
- `git diff --check -- app/web/lib/batch.ts app/web/lib/panels.ts app/web/components/compare/CompareClient.tsx app/web/components/compare/ScopeGate.tsx app/web/components/compare/BatchTable.tsx app/web/components/aistack/AskEamos.tsx` passed with line-ending warnings only.
- Local browser verification on `http://localhost:3001/compare` passed for
  signed-out auth-required failure, panel empty-state/stale notice, warning
  labels, and narrow viewport no-overflow. Screenshots were saved under
  `.tmp/batch-sprintb-*final.png`.
- The then-required repository index refresh passed; its oversized visualization
  export was skipped.
- `cd app/web; npm run build` was attempted earlier and timed out; not counted
  as passed.

2026-06-30 14:11 +1000 by Codex:

- `cd app/backend; python -m pytest tests/test_workbench_api.py tests/test_frontend_contract.py -q` passed.
- `cd app/backend; python -m pytest tests/test_workbench_preflight_cli.py tests/test_workbench_render_approval_bundle_cli.py -q` passed.
- `cd app/backend; python -m pytest tests/test_batch_api.py tests/test_batch_panel_schemas.py tests/test_panels_api.py -q` passed.
- `cd app/backend; python -m ruff check app tests` passed.
- `cd app/backend; python -m black --check app/schemas/workbench.py app/services/workbench_design.py app/services/crispr_offtarget_screening.py app/services/crispr_ssodn.py app/services/crispr_tide.py tests/test_workbench_api.py tests/test_frontend_contract.py` passed for touched files.
- `cd app/web; npx tsc --noEmit` passed.
- `cd app/web; npm run lint` passed.
- `cd app/web; npm run build` passed with the longer timeout.
- Focused `git diff --check` passed with line-ending warnings only.
- Combined Batch/Panel/Health sweep rerun with longer timeout failed only on
  `tests/test_health_api.py::test_provider_cache_health_returns_sanitized_empty_aggregates`
  because this local workspace reports
  `source_assets.clinvar_gene_distribution_index.ready=true` while that test
  expects it missing.
- The then-required repository index refresh passed.
- `git commit` created `d5ee212 feat(prelaunch): disclose workbench and batch launch states`.
- `git push origin main` pushed `d5ee212` to GitHub.
- Render deploy hook triggered SG deploy `dep-d91k7d6q1p3s73c493cg`; Render
  API reported it `live` on commit `d5ee212f41956ac22be68a27a5626d984513d780`.
- Live backend and Vercel HTTP smokes passed as listed above.
- Browser verification was deferred at Steven's direction because Selom was
  using the browser.

## Canonical Resume Prompt

```text
Resume Eamos from D:\eamos. Read AGENTS.md, CODEX.md, agent_handoff/README.md, agent_handoff/CURRENT.md, docs/operations/risks-and-guardrails.md, PROGRESS.md top, then read docs/prelaunch-batch-workbench-readiness/design.md, review.md, plan.md, and resume-prompt.md.

Current state: `main == origin/main` at `d5ee212 feat(prelaunch): disclose workbench and batch launch states` unless newer git status says otherwise. SG Render deploy `dep-d91k7d6q1p3s73c493cg` is live on `d5ee212f41956ac22be68a27a5626d984513d780`. ClinVar/report generated artifact phase is complete on SG for `clinvar_gene_distribution_index`; no further deploy, seed, provider flip, runtime script, or live sync is needed for that artifact. PubMed remains API/cache for launch. DuckDB/Parquet remains disabled analytical infrastructure for launch.

Sprint ledger:
- Planning: complete.
- Sprint A - Safety And Honesty: complete and pushed in `f7d74c2`. Task 0.1 launch-posture.md, Task 0.2 source disclosure taxonomy, Task 1.1 Batch bearer-token transport, Task 1.2 Batch create/get auth and owner scoping, Task 1.3 Batch job rate-limit scope, and Task 1.4 remove silent Batch mock fallback are done.
- Sprint B - Batch Functional Launch: partly complete locally. Task 2.1 Batch failure/expiry/auth/empty/stale UX is implemented. Panel launch policy is implemented as visible warning-labeled local launch panels. Local browser proof on `localhost:3001/compare` passed for signed-out auth-required failure, panel zero-match state, warning labels, and narrow viewport no-overflow. Signed-in browser proof is not done because creating/mutating a Supabase Auth test user/session was not approved.
- Sprint C - Workbench Functional Launch: implemented locally through command-line verification; browser proof pending because Selom was using the browser. Backend `SourceDisclosure` is added to Workbench response schemas and fixtures/samples; UI source labels are wired across Primer, CRISPR design, ssODN, off-target enumeration, screening primers, TIDE outcomes, and Align reference provenance. `/api/v1/align` honors `workbench_live_design_enabled` and has a non-RPE65 synthetic context test.
- Sprint D - Launch Evidence: pending. Covers PubMed hold note, DuckDB hold note, local asset freshness policy, backend/web test gates, and final launch-readiness note.

Important review findings to preserve:
- Batch transport now attaches Supabase bearer tokens and throws typed request errors; do not reintroduce silent mock fallback after create failures.
- Batch create/get are auth and owner scoped; backend tests cover cross-owner 404 behavior.
- If Batch persistence is required, reuse the existing SQLAlchemy app-db/session/repository pattern. Do not introduce Supabase/queues/DuckDB for first-launch persistence.
- Current panels are warning-labeled local launch panels; build a source-backed generated SQLite panel catalog only if Steven decides it is a launch blocker.
- Workbench truth to preserve: Primer and CRISPR guide design are live local/provider paths when Workbench live design is enabled; ssODN is source-backed for local MANE/hg38 or resolved sequence-context inputs and labelled fallback for mock windows; off-target enumeration is source-backed only with the GRCh38 SpCas9 SQLite index; screening primers are source-backed only with real windows/templates; TIDE is live observed-only and not Lindel/NKI-TIDE decomposition; Align reference/align backend paths are gene/variant agnostic through sequence context while the browser keeps the multi-read client-side alignment UX.

Verification from the latest Sprint C slice: Workbench API/frontend-contract pytest passed; Workbench preflight/render-approval pytest passed; Batch/Panel pytest passed; Ruff passed; targeted Black on touched backend files passed; web TypeScript passed; web lint passed; web `npm run build` passed; focused diff-check passed; the then-required repository index refresh passed; SG Render deploy and live backend/Vercel HTTP smokes passed. Combined Batch/Panel/Health sweep failed only on local health-test environment drift where `clinvar_gene_distribution_index.ready=true` but the test expects it missing. Browser proof is still pending because Selom was using the browser.

Guardrails: no Vercel command, Render env mutation, provider/flag flip, raw source download, Supabase metadata mutation, Supabase Storage mutation, one-off live runtime script, runtime seed/sync, destructive git, commit, or push unless Steven approves that exact action. Do not edit shared handoff/current/progress files without the edit-lock protocol. After code changes, run the structural boundary guards.

Next action unless Steven redirects: when the browser is free, run local `/workbench` browser proof for source labels across Primer, CRISPR design, ssODN, off-targets, screening primers, TIDE, and Align reference, plus narrow viewport and clean console/issues. Then run the structural boundary guards, refresh this handoff if needed, and decide whether signed-in Batch browser proof remains deferred or should use an approved session/test mutation.
```
