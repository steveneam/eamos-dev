# Prelaunch Batch And Workbench Agile Plan

Status: draft for Steven review.
Created: 2026-06-28 by Codex.
Source input:

- `docs/prelaunch-batch-workbench-readiness/design.md`
- `docs/prelaunch-batch-workbench-readiness/review.md`
- `docs/prelaunch-batch-workbench-readiness/resume-prompt.md`
- Current Batch, Workbench, auth, rate-limit, cache, and frontend source.

Session continuity:

- Use `docs/prelaunch-batch-workbench-readiness/resume-prompt.md` as the
  canonical session seed and sprint ledger.
- Update that file whenever a sprint task starts, completes, is skipped, or
  changes scope.

## Shared Decisions

These decisions affect task ordering and should be answered before
implementation starts.

1. Batch access model:
   - Recommended: signed-in users only.
   - Consequence: inline create, upload, and job polling all need bearer-token
     transport and owner checks.

2. Batch persistence:
   - Recommended for launch: owner-aware in-memory jobs with TTL.
   - Add SQL persistence only if reloadable job history is a launch requirement.

3. Panel catalog:
   - Recommended for launch: keep current warning-labeled local launch panels.
   - Build a source-backed panel catalog artifact only if panel provenance is a
     launch blocker.

4. Workbench provider posture:
   - Recommended for launch: mixed source-backed/fallback with honest labels.
   - Do not enable isPcr, indexed CRISPR off-targets, advanced CRISPR R scores,
     PubMed-local, RAG, or DuckDB analytical serving without separate approval.

5. Live SG checks:
   - Recommended: local proof first.
   - Any live SG probe beyond read-only health needs exact Steven approval.

## Bucket 0 - Launch Governance And Source Truth

### Task 0.1 - Record Launch Posture

Goal:

Create one concise launch-readiness note for the current posture so frontend,
backend, and handoff work do not drift.

Context:

The ClinVar generated artifact is complete, PubMed remains API/cache, and
DuckDB remains disabled. Batch and Workbench still need readiness work.

Relevant files:

- `docs/prelaunch-batch-workbench-readiness/design.md`
- `docs/prelaunch-batch-workbench-readiness/review.md`
- `docs/report-backend-source-cache-readiness/plan.md`

Proposed approach:

- Add `docs/prelaunch-batch-workbench-readiness/launch-posture.md`.
- State current provider posture and non-goals.
- Include the exact no-mutation guardrails.
- Link to the design, review, and this plan.

Acceptance criteria:

- The note clearly says ClinVar/report generated artifact is complete.
- The note clearly says PubMed-local, RAG, DuckDB analytical serving, isPcr,
  indexed CRISPR off-targets, and advanced CRISPR scoring are not enabled.
- The note lists required approvals before live/provider mutations.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/design.md`

Verify:

- `git diff --check -- docs/prelaunch-batch-workbench-readiness`

Out of scope:

- Editing shared handoff files.

### Task 0.2 - Define Source Disclosure Taxonomy

Goal:

Define the source/fallback vocabulary Batch and Workbench should use in UI and
API metadata.

Context:

Workbench currently has per-tool metadata, but no single taxonomy. Batch has
row warnings and source limitations but no standardized UI status vocabulary.

Relevant files:

- `app/backend/app/schemas/workbench.py`
- `app/backend/app/schemas/batch.py`
- `app/web/lib/workbench/crispr-disclosure.ts`
- `app/web/components/workbench`
- `app/web/components/compare`

Proposed approach:

- Define these statuses:
  - `source_backed`
  - `local_provider`
  - `fallback`
  - `fixture`
  - `gated`
  - `unavailable`
- Decide display labels:
  - Source-backed
  - Local provider
  - Preview fallback
  - Fixture
  - Gated
  - Unavailable
- Document when each status is valid.

Acceptance criteria:

- Every launch Batch/Workbench surface can map its current state to exactly one
  status.
- The taxonomy does not claim full source-backed status for sample or fallback
  paths.
- The taxonomy can be implemented additively without breaking current API
  contracts.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/review.md`

Verify:

- Document review only for this task.

Out of scope:

- Implementing schema changes.

## Bucket 1 - Batch Perimeter And Auth Consistency

### Task 1.1 - Add Batch Bearer-token Transport

Goal:

Make Batch frontend calls use the same Supabase bearer-token pattern as chat
and library sync.

Context:

`app/web/lib/chat.ts` and `app/web/lib/library-sync.ts` call
`createClient().auth.getSession()` and attach `Authorization: Bearer <token>`.
`app/web/lib/batch.ts` currently does not.

Relevant files:

- `app/web/lib/batch.ts`
- `app/web/lib/chat.ts`
- `app/web/lib/library-sync.ts`
- `app/web/components/compare/CompareClient.tsx`

Proposed approach:

- Add a small local `accessToken()` helper in `app/web/lib/batch.ts`, matching
  `library-sync.ts`.
- Attach the bearer token to `createBatch`, `getBatchJob`, and `uploadBatch`.
- If no token exists, throw an explicit sign-in error.
- Do not silently fall back to mock for auth-related failures.

Acceptance criteria:

- Signed-in users send a bearer token on Batch create, upload, and get.
- Anonymous users see an explicit sign-in-required Batch error.
- TypeScript compiles.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/review.md#1-batch-frontend-mock-fallback-will-hide-real-launch-failures`

Verify:

- `cd app/web; npx tsc --noEmit`
- Browser check `/compare` signed out and signed in.

Out of scope:

- Backend auth enforcement.

### Task 1.2 - Auth-gate Batch Create And Get

Goal:

Make Batch create and polling owner-aware and signed-in for launch.

Context:

Upload is already authenticated. Inline create and get are not. Batch records
do not carry owners.

Relevant files:

- `app/backend/app/api/routes/batch.py`
- `app/backend/app/services/batch.py`
- `app/backend/app/schemas/batch.py`
- `app/backend/tests/test_batch_api.py`

Proposed approach:

- Add `principal: AuthenticatedPrincipal =
  Depends(require_authenticated_principal)` to create and get routes.
- Add owner fields to `StoredUpload` and `StoredBatchJob`.
- Pass `principal.user_id` and `principal.provider` into `BatchService`.
- Reject create when an `upload_ref` belongs to another owner.
- Reject get when a job belongs to another owner.
- Use 404 for unauthorized job/upload lookups to avoid exposing existence.

Acceptance criteria:

- Anonymous create/get requests return 401.
- A signed-in user can create and poll their own job.
- A signed-in user cannot use another user's `upload_ref`.
- A signed-in user cannot poll another user's `job_id`.
- Existing upload auth tests still pass.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/review.md#2-batch-ownership-is-missing-from-the-upload-create-and-get-lifecycle`

Verify:

- `cd app/backend; python -m pytest tests/test_batch_api.py -q`
- `cd app/backend; python -m ruff check app tests`
- `cd app/backend; python -m black --check --target-version py310 app tests`

Out of scope:

- SQL persistence.

### Task 1.3 - Add Batch Job Rate-limit Scope

Goal:

Rate-limit Batch job creation separately from uploads.

Context:

`RATE_LIMIT_BATCH_UPLOAD` exists. Inline create can submit up to 5,000 variants
and should have its own launch budget.

Relevant files:

- `app/backend/app/core/rate_limit.py`
- `app/backend/app/core/config.py`
- `app/backend/app/api/routes/batch.py`
- `app/backend/tests/test_batch_api.py`

Proposed approach:

- Add `RATE_LIMIT_BATCH_JOB`.
- Add `rate_limit_batch_job_max_requests` setting with conservative default.
- Enforce by both IP and authenticated subject on create.

Acceptance criteria:

- Exceeding the create limit returns 429 with `Retry-After`.
- Upload rate limits remain unchanged.
- Rate-limit disabled setting still disables the new scope.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/review.md`

Verify:

- `cd app/backend; python -m pytest tests/test_batch_api.py -q`

Out of scope:

- Paid-tier quota modeling.

### Task 1.4 - Remove Silent Batch Mock Fallback

Goal:

Prevent Batch UI from presenting failed backend work as completed mock work.

Context:

Current `createBatch` catches all failures for inline variants and returns
`mock-job-*`.

Relevant files:

- `app/web/lib/batch.ts`
- `app/web/components/compare/CompareClient.tsx`
- `app/web/components/compare/BatchTable.tsx`

Proposed approach:

- Remove catch-all mock fallback from `createBatch`.
- If a preview/demo mode is still wanted, make it explicit in the UI state and
  label it with the source disclosure taxonomy.
- Surface backend error text in the compare progress/error region.

Acceptance criteria:

- 401/422/429/5xx responses display errors, not mock completed jobs.
- Upload path behavior remains unchanged except for explicit auth errors.
- No source-backed/cohort annotation claim appears for a failed backend run.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/review.md#1-batch-frontend-mock-fallback-will-hide-real-launch-failures`

Verify:

- `cd app/web; npx tsc --noEmit`
- Browser check `/compare` with backend down and with anonymous session.

Out of scope:

- Reworking compare layout.

## Bucket 2 - Batch UX And Functional Completion

### Task 2.1 - Batch Failure, Expiry, And Empty-state UX

Goal:

Make queued, running, failed, cancelled, expired, auth, and zero-result states
clear in the compare surface.

Context:

The backend emits job status and warnings. The frontend has progress state, but
launch QA needs explicit coverage of failure and expiry states.

Relevant files:

- `app/web/components/compare/CompareClient.tsx`
- `app/web/components/compare/BatchTable.tsx`
- `app/web/components/compare/CohortSummary.tsx`
- `app/web/lib/batch.ts`
- `app/backend/app/schemas/batch.py`

Proposed approach:

- Map each backend status to one concise UI message.
- Preserve warnings from the final job.
- Distinguish "no variants after filters" from backend failure.
- Ensure stale results are visibly stale after scope changes.

Acceptance criteria:

- Failed jobs show the backend error state and do not render as successful
  annotations.
- Expired/missing jobs explain that the run needs to be regenerated.
- Zero-result filtered cohorts are not treated as errors.
- Warnings are visible without overwhelming the table.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/design.md#batch-prelaunch-work`

Verify:

- `cd app/web; npx tsc --noEmit`
- Browser checks for normal, empty, failed, and expired/missing job states.

Out of scope:

- Persisted history.

### Task 2.2 - Batch Local Browser Proof

Goal:

Prove Batch works end-to-end locally before any live probe.

Context:

Backend tests cover parsers and service behavior, but launch needs browser proof
of the actual compare flow.

Relevant files:

- `app/web/components/compare`
- `app/web/lib/batch.ts`
- `app/backend/tests/test_batch_api.py`
- `app/backend/tests/test_project_100_mock_vcf_generator.py`

Proposed approach:

- Start local backend and web dev server.
- Use a small hg38 VCF and the Project-100 mock VCF path.
- Verify upload, generate, progress, final rows, cohort summary, TSV export,
  and Ask-Eamos cohort scope.

Acceptance criteria:

- Small VCF flow completes with source-backed row annotations.
- Project-100 mock flow exercises server-side upload path.
- Progress increments and final counts match the job payload.
- No mock fallback label appears for backend-backed rows.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/design.md#batch-design`

Verify:

- `cd app/backend; python -m pytest tests/test_batch_api.py tests/test_project_100_mock_vcf_generator.py -q`
- `cd app/web; npx tsc --noEmit`
- Browser screenshots or notes for desktop and mobile.

Out of scope:

- Live SG probe.

### Task 2.3 - Optional Batch SQL Persistence

Goal:

Add reloadable job history only if Steven decides session-lifetime jobs are not
enough for launch.

Context:

Current jobs are in memory. The existing app DB already uses SQLAlchemy and can
host a local-first Batch repository.

Relevant files:

- `app/backend/app/core/db.py`
- `app/backend/app/services/batch.py`
- `app/backend/app/repos`
- `app/backend/tests/test_batch_api.py`
- `app/backend/tests/test_variant_cache.py`

Proposed approach:

- Add `BatchJobRecord`, `BatchJobResultRecord`, and `BatchUploadRecord`.
- Add `BatchJobRepo` using `session_scope`.
- Add `BATCH_PERSISTENCE_ENABLED=false` default.
- When enabled, write job metadata and result rows as the background worker
  progresses.
- Keep raw VCF bytes out of SQL.

Acceptance criteria:

- With persistence disabled, existing in-memory behavior remains.
- With persistence enabled, completed jobs survive service object recreation.
- Users can list/read only their own jobs.
- Expiry cleanup removes old job/result/upload rows.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/review.md#3-batch-persistence-should-reuse-the-existing-sqlalchemy-app-db-pattern`

Verify:

- `cd app/backend; python -m pytest tests/test_batch_api.py -q`
- Add focused repo tests for persistence enabled/disabled.

Out of scope:

- Supabase/Postgres migrations for Batch history.
- Queue infrastructure.

## Bucket 3 - Panel Catalog And Cohort Filtering

### Task 3.1 - Confirm Launch Panel Policy

Goal:

Decide whether warning-labeled local panels are acceptable for launch.

Context:

`PanelService` currently ships local launch panels and warns that external
sources are pending.

Relevant files:

- `app/backend/app/services/panels.py`
- `app/backend/app/api/routes/panels.py`
- `app/backend/tests/test_panels_api.py`
- `app/web/lib/panels.ts`
- `app/web/lib/panels.mock.ts`

Proposed approach:

- Document the launch panel status in the launch posture note.
- Keep source labels visible in the UI.
- Treat source-backed panel import as a separate artifact lane unless Steven
  makes it a launch blocker.

Acceptance criteria:

- Panel UI/API responses expose local-launch warnings.
- Batch filtered by local panels remains functional.
- Launch docs do not claim PanelApp/ClinGen/GenCC source-backed panels unless
  the artifact exists.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/review.md#5-panel-catalog-is-the-right-intermediate-artifact-if-source-backed-panels-are-needed`

Verify:

- `cd app/backend; python -m pytest tests/test_panels_api.py tests/test_batch_api.py -q`

Out of scope:

- Building source-backed panel artifact.

### Task 3.2 - Optional Source-backed Panel Catalog Artifact

Goal:

Build a local generated panel catalog only if source-backed panels are required
before launch.

Context:

Request-time calls to PanelApp/ClinGen/GenCC/MONDO would violate the local asset
policy. A generated SQLite artifact matches the ClinVar generated-artifact
approach.

Relevant files:

- `app/backend/app/services/panels.py`
- `app/backend/app/schemas/panels.py`
- `app/backend/app/api/routes/panels.py`
- `app/backend/app/core/config.py`
- `app/backend/tests/test_panels_api.py`

Proposed approach:

- Define `panel-catalog.sqlite` schema:
  - `panel_release`
  - `panel`
  - `panel_gene`
  - `panel_disease_map`
  - `panel_gene_source_evidence`
  - `panel_alias`
- Add a read-only adapter and provider-cache readiness probe.
- Add a tiny fixture catalog for tests.
- Keep local launch panels as fallback when artifact is absent.

Acceptance criteria:

- With fixture artifact, `/api/v1/panels` returns source-backed panel metadata.
- With no artifact, existing local launch panels remain available with warnings.
- No request-time external API call occurs.
- Health/preflight output is sanitized.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/review.md#5-panel-catalog-is-the-right-intermediate-artifact-if-source-backed-panels-are-needed`

Verify:

- `cd app/backend; python -m pytest tests/test_panels_api.py tests/test_health_api.py -q`

Out of scope:

- Downloading real panel source payloads.
- Uploading or syncing generated artifacts.

## Bucket 4 - Workbench Source Disclosure Framework

### Task 4.1 - Add Shared Workbench Disclosure Model

Goal:

Make Workbench source and fallback states consistent across Viewer, Primer,
CRISPR, ssODN, Align, and Outcomes.

Context:

Each Workbench tool currently exposes a different source/fallback shape.

Relevant files:

- `app/backend/app/schemas/workbench.py`
- `app/backend/app/services/workbench_design.py`
- `app/web/lib/workbench/crispr-disclosure.ts`
- `app/web/lib/workbench`
- `app/web/components/workbench`

Proposed approach:

- Add an optional Pydantic model such as `SourceDisclosure`.
- Add a matching TypeScript type/helper.
- Thread it through responses additively where practical.
- Keep existing fields for compatibility.

Acceptance criteria:

- Existing API clients remain compatible.
- Each Workbench tool can produce a consistent disclosure status.
- Frontend rendering uses one helper for status label and caveat copy.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/review.md#4-workbench-sourcefallback-disclosure-is-fragmented-across-tools`

Verify:

- `cd app/backend; python -m pytest tests/test_workbench_api.py -q`
- `cd app/web; npx tsc --noEmit`

Out of scope:

- Making every provider source-backed.

### Task 4.2 - Workbench Label Audit

Goal:

Ensure backend-backed Workbench results do not show sample/fallback labels, and
fallback paths remain visibly marked.

Context:

The launch posture allows mixed source-backed/fallback Workbench behavior only
if labels are honest.

Relevant files:

- `app/web/components/workbench/primer/PrimerResultCard.tsx`
- `app/web/components/workbench/crispr`
- `app/web/components/workbench/align`
- `app/web/components/workbench/viewer`
- `app/web/lib/api.ts`
- `app/web/lib/workbench`

Proposed approach:

- Browser-test backend available and backend unavailable modes.
- Replace stale "pending backend" or "mock" labels when live data exists.
- Keep explicit preview/fallback labels for offline samples.

Acceptance criteria:

- Primer3 placement/thermo live fields are not marked illustrative.
- TIDE backend results show TIDE/source-backed, not frontend sample.
- ssODN mock windows are marked fallback, while local context is not.
- CRISPR off-target mock fallback is clear.
- Viewer scaffold warnings remain visible.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/design.md#workbench-prelaunch-work`

Verify:

- `cd app/web; npx tsc --noEmit`
- Browser verification of each Workbench tool at desktop and mobile widths.

Out of scope:

- Provider flips.

## Bucket 5 - Workbench Functional Proof

### Task 5.1 - Focused Workbench Backend Smoke

Goal:

Prove core Workbench routes are functional with current provider posture.

Context:

Routes exist, but launch proof should capture the exact conservative provider
state.

Relevant files:

- `app/backend/app/api/routes/workbench.py`
- `app/backend/app/services/workbench_design.py`
- `app/backend/tests/test_workbench_api.py`
- `app/backend/tests/test_workbench_preflight_cli.py`

Proposed approach:

- Run focused tests for:
  - primer
  - CRISPR design
  - off-target auto fallback
  - forced indexed fail-closed
  - screening primers
  - ssODN
  - align/reference
  - trace
  - TIDE
- Run workbench preflight compact output.

Acceptance criteria:

- Tests pass locally without network/source downloads.
- Preflight reports conservative provider posture without raw path leaks.
- Missing advanced providers are warning-labeled, not fatal.

Source reference:

- `docs/workbench-live-wiring/plan.md`

Verify:

- `cd app/backend; python -m pytest tests/test_workbench_api.py tests/test_workbench_preflight_cli.py -q`
- `cd app/backend; python -m app.cli.eamos_workbench_preflight --compact`

Out of scope:

- Live SG provider mutation.

### Task 5.2 - Workbench Browser Proof

Goal:

Verify the Workbench UI is usable and accurately labeled before launch.

Context:

Backend tests do not prove UX flow or visual disclosure quality.

Relevant files:

- `app/web/app/workbench`
- `app/web/components/workbench`
- `app/web/lib/api.ts`
- `app/web/lib/workbench`

Proposed approach:

- Start local backend and web server.
- Verify viewer, Primer, CRISPR Design, CRISPR Off-targets, CRISPR Outcomes,
  and Align.
- Check desktop and mobile viewports.
- Confirm no overlapping UI and no source/fallback mislabeling.

Acceptance criteria:

- Each tool can complete its launch workflow.
- Fallback/sample paths are marked.
- Backend-backed paths are not marked as preview.
- File upload controls and errors are clear.
- Mobile layout remains usable.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/design.md#workbench-design`

Verify:

- `cd app/web; npx tsc --noEmit`
- Browser screenshots or notes for desktop and mobile.

Out of scope:

- Full Benchling-style polish unless Bucket 6 is selected.

## Bucket 6 - UX Polish And Framework Consistency

### Task 6.1 - Shared Auth Error UX For Gated Tools

Goal:

Make signed-in requirements feel consistent across Ask-Eamos, Batch, Library
sync, and future gated tools.

Context:

Chat and library sync already use Supabase session tokens. Batch should use the
same pattern and UX language.

Relevant files:

- `app/web/lib/chat.ts`
- `app/web/lib/library-sync.ts`
- `app/web/lib/batch.ts`
- `app/web/components/auth`
- `app/web/components/compare`

Proposed approach:

- Reuse plain sign-in-required messages.
- Avoid silent local-only fallbacks for gated backend compute.
- Keep local/offline behavior only where the product explicitly supports it.

Acceptance criteria:

- Anonymous Batch users see a clear sign-in prompt/error.
- Signed-out Ask-Eamos and Batch use consistent language.
- No sensitive backend error text is exposed raw.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/review.md`

Verify:

- Browser signed-out checks for `/compare` and Ask-Eamos.

Out of scope:

- New auth provider work.

### Task 6.2 - Optional Benchling-style Workbench Apply Polish

Goal:

Apply the approved Workbench UX polish only if launch quality requires it.

Context:

`docs/workbench-benchling-apply/spec.md` describes a frontend-only polished
flow. It is not required for backend correctness, but it may improve launch UX.

Relevant files:

- `docs/workbench-benchling-apply/spec.md`
- `app/web/components/workbench`
- `app/web/lib/workbench`

Proposed approach:

- Implement slice by slice:
  - viewer band to Align
  - CRISPR two-table plus overlay
  - Primer table plus overlay
- Browser-verify each slice before the next.

Acceptance criteria:

- Tool transitions are clear.
- Overlays match selected tool state.
- No card-in-card or overlapping text issues.
- Desktop and mobile remain usable.

Source reference:

- `docs/workbench-benchling-apply/spec.md`

Verify:

- `cd app/web; npx tsc --noEmit`
- Browser screenshots for each slice.

Out of scope:

- Backend route changes.

## Bucket 7 - Data Architecture And Freshness Policy

### Task 7.1 - PubMed Launch Hold Note

Goal:

Make the PubMed decision explicit in launch evidence.

Context:

PubMed-local is a data logistics project and should not block launch.

Relevant files:

- `docs/pubmed-corpus-materialization/spec.md`
- `docs/pubmed-local/plan.md`
- `docs/prelaunch-batch-workbench-readiness/launch-posture.md`

Proposed approach:

- Record that launch uses PubMed/LitVar/ClinicalTrials API/cache.
- Record that PubMed-local, RAG, and literature embeddings remain disabled.
- List future options: targeted seed, filtered PubMed, raw mirror.

Acceptance criteria:

- Launch evidence cannot be read as claiming PubMed-local is enabled.
- Future PubMed options are clear and approval-gated.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/design.md#pubmed`

Verify:

- Doc review.

Out of scope:

- Source downloads or Storage mutation.

### Task 7.2 - DuckDB/Parquet Launch Hold Note

Goal:

Keep DuckDB/Parquet separate from launch-critical point lookup.

Context:

Phase 0/1 exist, but no route depends on DuckDB and no Silver/Gold corpus exists.

Relevant files:

- `docs/data-architecture-duckdb-parquet/plan.md`
- `docs/data-architecture-duckdb-parquet/adr.md`
- `app/backend/app/services/duckdb_analytical.py`

Proposed approach:

- Record that DuckDB remains disabled analytical infrastructure.
- Record future workloads where it can help.
- Avoid tying Batch launch to DuckDB.

Acceptance criteria:

- Launch evidence does not claim DuckDB analytical serving.
- Future analytical tasks stay benchmark-gated.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/design.md#duckdb-and-parquet`

Verify:

- Doc review.

Out of scope:

- Building Silver/Gold artifacts.

### Task 7.3 - Local Asset Freshness Policy

Goal:

Define how launch surfaces describe local asset freshness without forcing
immediate materialization work.

Context:

The ClinVar generated artifact is ready, but broader local assets have different
freshness states and update paths.

Relevant files:

- `docs/deployment/materialization-lessons-learned.md`
- `docs/report-backend-source-cache-readiness/plan.md`
- `app/backend/app/api/routes/health.py`
- `app/backend/app/services`

Proposed approach:

- List each launch-visible asset and current freshness/status source.
- Define labels:
  - ready
  - ready_stale_ok
  - API/cache
  - disabled
  - gated
  - unavailable
- Map labels to UI/health language.

Acceptance criteria:

- Each launch-visible local/API source has a freshness label.
- Labels match provider-cache/preflight behavior.
- No materialization work is implied without approval.

Source reference:

- `docs/prelaunch-batch-workbench-readiness/design.md`

Verify:

- Doc review plus provider-cache read-only local check if needed.

Out of scope:

- Live provider/env changes.

## Bucket 8 - Release Evidence And Final QA

### Task 8.1 - Backend Focused Test Gate

Goal:

Run the backend tests that prove Batch and Workbench launch behavior.

Context:

Launch readiness should not rely on broad test suite luck.

Relevant files:

- `app/backend/tests/test_batch_api.py`
- `app/backend/tests/test_workbench_api.py`
- `app/backend/tests/test_panels_api.py`
- `app/backend/tests/test_health_api.py`
- `app/backend/tests/test_workbench_preflight_cli.py`

Proposed approach:

- Run focused backend test groups after implementation buckets.
- Record failures and fixes in the launch evidence note.

Acceptance criteria:

- Focused backend tests pass.
- Health/preflight tests pass for conservative provider posture.

Source reference:

- This plan.

Verify:

- `cd app/backend; python -m pytest tests/test_batch_api.py tests/test_workbench_api.py tests/test_panels_api.py tests/test_health_api.py tests/test_workbench_preflight_cli.py -q`
- `cd app/backend; python -m ruff check app tests`
- `cd app/backend; python -m black --check --target-version py310 app tests`

Out of scope:

- Whole repo exhaustive test suite unless time allows.

### Task 8.2 - Web Focused Test Gate

Goal:

Run web checks for Compare and Workbench after frontend changes.

Context:

Batch and Workbench launch readiness includes UI contracts and labels.

Relevant files:

- `app/web/components/compare`
- `app/web/components/workbench`
- `app/web/lib/batch.ts`
- `app/web/lib/api.ts`
- `app/web/lib/workbench`

Proposed approach:

- Run TypeScript checks.
- Run lint/build if available in package scripts.
- Browser-verify desktop and mobile.

Acceptance criteria:

- TypeScript passes.
- Browser proof shows no overlapping UI, misleading labels, or blocked flows.

Source reference:

- This plan.

Verify:

- `cd app/web; npx tsc --noEmit`
- `cd app/web; npm run lint`
- `cd app/web; npm run build`

Out of scope:

- Vercel commands.

### Task 8.3 - Final Launch Readiness Note

Goal:

Produce the final evidence note for Batch and Workbench before launch.

Context:

The release needs a concise, accurate statement of what is complete, what is
fallback, and what is deferred.

Relevant files:

- `docs/prelaunch-batch-workbench-readiness/launch-readiness.md`
- `docs/prelaunch-batch-workbench-readiness/design.md`
- `docs/prelaunch-batch-workbench-readiness/review.md`
- `docs/prelaunch-batch-workbench-readiness/plan.md`

Proposed approach:

- Summarize implementation decisions.
- Include commands run and browser proof summary.
- List explicit non-enabled providers/features.
- List required approvals for any later live SG/deploy/provider changes.

Acceptance criteria:

- The note is accurate enough to hand off.
- It does not hide fallback paths.
- It distinguishes local verification from live SG verification.

Source reference:

- This plan.

Verify:

- `git diff --check -- docs/prelaunch-batch-workbench-readiness`

Out of scope:

- Committing or pushing.

## Recommended Sprint Order

### Sprint A - Safety And Honesty

1. Task 0.1 - Record Launch Posture
2. Task 0.2 - Define Source Disclosure Taxonomy
3. Task 1.1 - Add Batch Bearer-token Transport
4. Task 1.2 - Auth-gate Batch Create And Get
5. Task 1.3 - Add Batch Job Rate-limit Scope
6. Task 1.4 - Remove Silent Batch Mock Fallback

### Sprint B - Batch Functional Launch

1. Task 2.1 - Batch Failure, Expiry, And Empty-state UX
2. Task 3.1 - Confirm Launch Panel Policy
3. Task 2.2 - Batch Local Browser Proof

Conditional:

- Task 2.3 - Optional Batch SQL Persistence
- Task 3.2 - Optional Source-backed Panel Catalog Artifact

### Sprint C - Workbench Functional Launch

1. Task 4.1 - Add Shared Workbench Disclosure Model
2. Task 4.2 - Workbench Label Audit
3. Task 5.1 - Focused Workbench Backend Smoke
4. Task 5.2 - Workbench Browser Proof

Conditional:

- Task 6.2 - Optional Benchling-style Workbench Apply Polish

### Sprint D - Launch Evidence

1. Task 7.1 - PubMed Launch Hold Note
2. Task 7.2 - DuckDB/Parquet Launch Hold Note
3. Task 7.3 - Local Asset Freshness Policy
4. Task 8.1 - Backend Focused Test Gate
5. Task 8.2 - Web Focused Test Gate
6. Task 8.3 - Final Launch Readiness Note

## Work Not Recommended Before Launch

- Full PubMed-local corpus materialization.
- Literature embeddings/RAG enablement.
- DuckDB Silver/Gold materialization.
- Production CRISPR off-target index build/mount/env flip.
- UCSC isPcr enablement.
- Advanced CRISPR R scoring enablement.
- Supabase Batch history migrations unless cross-device job history becomes a
  launch requirement.
