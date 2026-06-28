# Prelaunch Batch And Workbench Resume Prompt

Status: active session seed.
Last updated: 2026-06-28 20:29 +1000 by Codex.

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
- Sprint A Batch safety implementation completed locally:
  - Batch create/get now require an authenticated principal.
  - Batch uploads and jobs carry owner metadata.
  - Upload refs and job IDs are scoped to the owner and return 404 on
    cross-owner access.
  - Batch job creation has its own rate-limit scope.
  - Web Batch create/get/upload calls attach the Supabase bearer token.
  - Inline create failures no longer become silent mock completed jobs.
- Current recommendation is:
  - PubMed stays API/cache for launch.
  - DuckDB/Parquet stays disabled analytical infrastructure for launch.
  - Batch launch work starts with safety, auth, owner scoping, and no silent
    mock fallback.
  - Workbench launch work starts with source/fallback disclosure and local
    functional proof.

## Not Done

- No Workbench disclosure code changes have been implemented from this plan.
- No browser verification has been run for this prelaunch plan.
- Full broad Black check is blocked by pre-existing unrelated formatting drift
  in backend files outside this Sprint A slice. Touched backend files pass
  targeted Black.
- No live SG probe, provider flip, deploy, Storage mutation, Supabase metadata
  mutation, raw source download, or runtime sync has been performed.

## Current Next Task

Sprint A is implemented locally.

- Task 0.1 - Record Launch Posture.
- Created `docs/prelaunch-batch-workbench-readiness/launch-posture.md`.
- Task 0.2 - Define Source Disclosure Taxonomy.
  Created `docs/prelaunch-batch-workbench-readiness/source-disclosure-taxonomy.md`.
- Task 1.1 - Add Batch Bearer-token Transport.
  Implemented in `app/web/lib/batch.ts`.
- Task 1.2 - Auth-gate Batch Create And Get.
  Implemented in `app/backend/app/api/routes/batch.py` and
  `app/backend/app/services/batch.py`.
- Task 1.3 - Add Batch Job Rate-limit Scope.
  Implemented in `app/backend/app/core/rate_limit.py`,
  `app/backend/app/core/config.py`, and `app/backend/.env.example`.
- Task 1.4 - Remove Silent Batch Mock Fallback.
  Implemented in `app/web/lib/batch.ts` and
  `app/web/components/compare/CompareClient.tsx`.

Next task:

- Sprint B Task 2.1 - Batch Failure, Expiry, And Empty-state UX.

## Sprint Ledger

| Sprint | Status | Scope | Next action |
| --- | --- | --- | --- |
| Planning | Complete | Design, architecture review, agile plan, resume prompt | Keep docs current as work progresses. |
| Sprint A - Safety And Honesty | Complete locally | Launch posture, source disclosure taxonomy, Batch auth transport, Batch owner scoping, Batch job rate limits, remove silent mock fallback | Commit/push when approved and clean. |
| Sprint B - Batch Functional Launch | Pending | Batch failure/expiry UX, panel launch policy, local browser proof | Start Task 2.1. |
| Sprint C - Workbench Functional Launch | Pending | Shared Workbench source disclosure model, label audit, backend smoke, browser proof | Start after Sprint A or in parallel only if ownership is clear. |
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
- Browser verification has not been run yet; Sprint B includes local browser
  proof.

## Canonical Resume Prompt

```text
Resume Eamos from D:\eamos. Read AGENTS.md, CODEX.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, PROGRESS.md top, then read docs/prelaunch-batch-workbench-readiness/design.md, review.md, plan.md, and resume-prompt.md.

Current state: ClinVar/report generated artifact phase is complete on SG for clinvar_gene_distribution_index; no further deploy, seed, provider flip, runtime script, or live sync is needed for that artifact. PubMed remains API/cache for launch. DuckDB/Parquet remains disabled analytical infrastructure for launch.

Planning state: docs/prelaunch-batch-workbench-readiness/design.md, review.md, plan.md, launch-posture.md, source-disclosure-taxonomy.md, and resume-prompt.md exist. Sprint A Batch safety implementation is complete locally unless newer git status says otherwise.

Sprint ledger:
- Planning: complete.
- Sprint A - Safety And Honesty: complete locally. Task 0.1 launch-posture.md, Task 0.2 source disclosure taxonomy, Task 1.1 Batch bearer-token transport, Task 1.2 Batch create/get auth and owner scoping, Task 1.3 Batch job rate-limit scope, and Task 1.4 remove silent Batch mock fallback are implemented.
- Sprint B - Batch Functional Launch: pending after Sprint A commit/push. Covers Batch failure/expiry UX, panel launch policy, local browser proof, optional SQL persistence only if Steven requires reloadable job history, optional source-backed panel catalog only if Steven makes panel provenance a launch blocker.
- Sprint C - Workbench Functional Launch: pending. Covers shared Workbench source disclosure model, label audit, focused backend smoke, and local browser proof.
- Sprint D - Launch Evidence: pending. Covers PubMed hold note, DuckDB hold note, local asset freshness policy, backend/web test gates, and final launch-readiness note.

Important review findings to preserve:
- app/web/lib/batch.ts previously turned inline create failures into mock completed jobs; Sprint A removes that behavior.
- Batch upload was auth-gated but create/get and in-memory records needed owner scoping; Sprint A adds auth and owner scoping.
- If Batch persistence is required, reuse the existing SQLAlchemy app-db/session/repository pattern. Do not introduce Supabase/queues/DuckDB for first-launch persistence.
- Workbench needs a shared source/fallback disclosure taxonomy before broad browser QA.
- Current panels are warning-labeled local launch panels; build a source-backed generated SQLite panel catalog only if Steven decides it is a launch blocker.

Guardrails: no Vercel command, Render env mutation, provider/flag flip, raw source download, Supabase metadata mutation, Supabase Storage mutation, one-off live runtime script, runtime seed/sync, destructive git, commit, or push unless Steven approves that exact action. Do not edit shared handoff/current/progress files without the edit-lock protocol. After code changes, run python -m graphify update . with at least 360s timeout.

Next action unless Steven redirects: commit/push the scoped Sprint A changes if not already done, then start Sprint B Task 2.1 Batch failure/expiry/empty-state UX.
```
