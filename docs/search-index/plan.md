# Eamos search index implementation plan

Status: run/report wiring plus Tasks 4-5 implemented; Task 6 workspace/public/source-backed backend breadth mostly implemented; Task 7+ and frontend integration remain open.
Spec: `docs/search-index/spec.md`.
Related repo-structure wave: Wave 2, "Fix or retire Search".

Implementation update, 2026-06-30:

- Task 1 local characterization coverage added in
  `app/backend/tests/test_search_api_local.py`.
- Task 2 normal app wiring is implemented in `create_app()` with
  `SearchRepo`, `SearchService`, `SearchIndexService`, and disabled-by-default
  `SearchAnswerService`.
- Search routes now use explicit `RATE_LIMIT_SEARCH` settings.
- Task 3 first mutation hook is implemented for `WorkflowService.create_run()`.
  Existing upload/review hooks are wired through normal app construction.
- Task 4 private/public access posture is implemented for the current
  run/report index: private rows are owner-filtered server-side, ownerless
  historical private rows are hidden until backfilled, and raw report snippets
  are not exposed outside owner-scoped private hits.
- Task 5 readiness/backfill tooling is implemented: provider-cache health has a
  sanitized search block, and `python -m app.cli.eamos_search_index_backfill`
  is dry-run-first with explicit `--apply` and optional `--owner-user-id`.
- Task 6 first non-run/report workspace slice is implemented: saved
  variant-library rows index as owner-scoped private `library_variant` search
  documents on save, bulk save, whole-library replace, and delete.
- Task 6 public/source-backed slice is implemented for existing run payloads:
  publication and trial evidence rows index as public documents, and
  report-section rows index as owner-scoped private documents. Report-payload
  updates, approve, and drop refresh indexed rows best-effort.
- Still open: richer public metadata/view-count breadth, broader product entity
  coverage beyond the current payload-backed publication/trial/section rows,
  frontend integration, and grounded answer-chain tests.

## Shared decisions before implementation

- Treat the feature as a Search Control Plane, not just a 503 fix.
- Keep structured variant lookup on the existing `/report` path while search
  results mature.
- Use PostgreSQL FTS plus deterministic aliases for the first robust slice.
- Keep SQLite fallback for local tests.
- Do not add external hosted search, vector search, source downloads, startup
  materialization, Supabase mutation, deploy/env mutation, destructive git,
  commits, or pushes during these tasks unless Steven approves that exact
  action.
- Do not expose private report/run raw text in snippets without owner filtering.

## Task 1 - Characterize current search behavior

Status: done for local non-Docker route coverage.

Goal:

Capture the current unwired state with local tests so the first code slice has a
clear failure and does not rely on Docker-gated coverage.

Context:

`app/backend/tests/test_search_api.py` is skipped unless
`HSIL_DOCKER_BASE_URL` is set. Local coverage now lives in
`app/backend/tests/test_search_api_local.py` and asserts standard app wiring,
empty-index results, bounds, rate limits, answer gating, and run-create
indexing.

Relevant files:

- `app/backend/app/api/routes/search.py`
- `app/backend/app/main.py`
- `app/backend/tests/conftest.py`
- `app/backend/tests/test_search_api.py`
- `docs/repo-structure/audit-2026-06-30.md`

Proposed approach:

Add a non-Docker local API test module or split local tests out of
`test_search_api.py`. Prove:

- unauthenticated search is rejected;
- authenticated search no longer returns 503 after wiring;
- empty indexes return `200` with `results: []`;
- configured limit bounds are enforced;
- route-level rate limiting exists.

Acceptance criteria:

- A local pytest run catches missing `app.state.search_service`.
- The Docker-gated integration test remains available but is no longer the only
  search-route coverage.
- The test names make the current product gap obvious.

Source reference:

`docs/search-index/spec.md`, Requirements 1, 3, and 12.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_search_api.py tests/test_rate_limits.py -q
```

Out of scope:

- Building the full generalized entity index.
- Frontend changes.

## Task 2 - Wire existing run/report search services in `create_app()`

Status: done for the existing run/report service path.

Goal:

Make `/api/v1/search` available in normal backend construction for the existing
run/report index path.

Context:

The app already has `SearchRepo`, `SearchService`, `SearchIndexService`, and
`SearchAnswerService`, and `create_app()` now instantiates them. Intake and
recommendation services receive the shared indexer.

Relevant files:

- `app/backend/app/main.py`
- `app/backend/app/repos/search_repo.py`
- `app/backend/app/services/search.py`
- `app/backend/app/services/search_index.py`
- `app/backend/app/services/search_answer.py`
- `app/backend/app/services/intake.py`
- `app/backend/app/services/recommendation.py`
- `app/backend/app/api/routes/search.py`

Proposed approach:

- Instantiate `SearchRepo(db_session_factory)`.
- Instantiate `SearchService(search_repo)`.
- Instantiate `SearchIndexService(search_repo, reports_repo, run_repo)`.
- Instantiate `SearchAnswerService(settings, search_service, answer_chain=...)`
  only with the existing answer-chain pattern; keep answer feature gated.
- Set `app.state.search_service`, `app.state.search_index_service`, and
  `app.state.search_answer_service`.
- Pass `search_index_service` into `IntakeService` and
  `RecommendationService`.
- Add route-level rate limiting to search endpoints using the existing
  `enforce_rate_limit()` pattern and a search scope. If adding a new
  `RATE_LIMIT_SEARCH` setting is too broad for the first slice, use the default
  scope deliberately and record the follow-up.

Acceptance criteria:

- A fresh local test app has all search state entries set.
- Authenticated `GET /api/v1/search?q=anything` returns `200` with an empty list
  before any reports/runs exist.
- `POST /api/v1/search/answer` still returns 503 when disabled/unconfigured.
- Search route abuse is rate-limited.

Source reference:

`docs/search-index/spec.md`, Requirements 1, 2, and 3.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_search_api.py tests/test_rate_limits.py -q
python -m ruff check app tests
python -m black --check --target-version py310 app tests
```

Out of scope:

- Owner scoping and generalized entities.
- UI integration.

## Task 3 - Index runs at creation and after run mutations

Status: partly done. Run creation indexing is implemented and tested; broader
approve/drop/report-payload refresh hooks remain open.

Goal:

Ensure the current run/report index actually contains the entities users expect
to find.

Context:

Report upload has an optional index hook in `IntakeService`, and review updates
have one in `RecommendationService`; both are now wired in normal app startup.
`WorkflowService.create_run()` now indexes after the primary run write succeeds.
Approval/drop/report-payload updates also affect indexed fields or filters and
remain follow-up work.

Relevant files:

- `app/backend/app/services/workflow.py`
- `app/backend/app/services/report_draft.py`
- `app/backend/app/services/final_report.py`
- `app/backend/app/services/recommendation.py`
- `app/backend/app/services/search_index.py`
- `app/backend/app/repos/run_repo.py`
- `app/backend/tests/test_search_api.py`

Proposed approach:

- Add an optional `search_index_service` dependency to `WorkflowService`.
- After `run_repo.create_run()` succeeds, call `index_run(run_response,
  reports=reports)`.
- Add index refresh hooks after report payload update, approve, and drop if
  those fields affect search filters or titles/snippets.
- Keep indexing failures from corrupting the primary write. Decide whether to
  log and continue or return a 500; recommended first-launch behavior is log and
  continue with a health/backfill signal, because failed indexing should not
  lose a clinical run.
- Add tests for run ID search, gene search, review-status filter, and idempotent
  reindex after review/status mutation.

Acceptance criteria:

- Creating a run makes it discoverable by run ID, patient ID where allowed, gene,
  and variant alias.
- Updating review/status changes search filters without duplicate index rows.
- Re-running index on the same run replaces stale variants.

Source reference:

`docs/search-index/spec.md`, Requirements 5, 6, and 10.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_search_api.py tests/test_protein_annotation_service.py -q
```

Out of scope:

- Changing the primary run/report schema ownership model.

## Task 4 - Add explicit private/public access posture

Status: done for the current run/report index surface.

Goal:

Prevent the search feature from becoming a cross-user report-text leak as soon
as private workspace results are exposed in the product UI.

Context:

The current search route requires auth, but existing run/report records do not
show an owner filter in the search repo. Auth alone is not enough in a multi-user
deployment. Search documents may include patient IDs and raw extracted report
text.

Relevant files:

- `app/backend/app/schemas/auth.py`
- `app/backend/app/api/routes/search.py`
- `app/backend/app/repos/search_repo.py`
- `app/backend/app/core/db.py`
- `app/backend/tests/test_search_api.py`
- `app/backend/tests/test_frontend_contract.py`

Proposed approach:

- Define search visibility modes in the schema: `public`, `workspace`, and
  `internal` or equivalent.
- For private run/report rows, add or derive owner/user scope before product UI
  exposure. If the current app cannot infer ownership for historical rows, mark
  those rows as not safe for user-facing private search until backfilled.
- Filter private rows by the authenticated user subject server-side.
- Suppress raw uploaded text snippets unless the hit passed private ownership
  checks.
- Add tests with two authenticated users proving one user cannot search the
  other's private run/report rows.

Acceptance criteria:

- Search repo methods accept an access context and apply it server-side.
- Public/reference rows can be searched without leaking private workspace rows.
- Private raw text snippets require owner-scoped access.
- Tests cover both positive and negative authorization cases.

Source reference:

`docs/search-index/spec.md`, Requirements 7 and 14, Decision D3.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_search_api.py tests/test_rate_limits.py -q
```

Out of scope:

- Full account-role/admin plumbing unrelated to search.
- Reworking all non-search run/report authorization in the same task.

## Task 5 - Add search readiness and backfill tooling

Status: done for run/report index health and explicit DB-row backfill.

Goal:

Make index freshness operationally visible and rebuildable without startup work.

Context:

The repo's backend policy avoids startup materialization and runtime seed/sync.
Search should follow the same model: explicit operator action, health visibility,
no hidden source downloads.

Relevant files:

- `app/backend/app/api/routes/health.py`
- `app/backend/app/services/search_index.py`
- `app/backend/app/repos/search_repo.py`
- `app/backend/app/core/db.py`
- `app/backend/app/cli/`
- `app/backend/tests/test_health_api.py`

Proposed approach:

- Add a search health/readiness helper that reports service wiring, table/index
  readiness, entity counts, last indexed timestamp, and answer feature status.
- Add a CLI command for report/run search backfill from existing local DB rows.
- Add dry-run output before writes.
- Ensure backfill does not fetch sources, materialize assets, mutate Supabase,
  flip providers, or touch deploy/env config.

Acceptance criteria:

- Health/preflight output includes search readiness fields.
- Backfill can rebuild run/report search rows from existing records.
- Backfill is idempotent and exits non-zero on required failures.
- Startup does not run backfill.

Source reference:

`docs/search-index/spec.md`, Requirements 4, 6, and 12.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_health_api.py tests/test_search_api.py -q
python -m compileall -q app
```

Out of scope:

- Downloading or refreshing external source assets.

## Task 6 - Evolve schemas toward product-wide entity search

Status: partially done. Saved variant-library rows now index as owner-scoped
private `library_variant` documents. Public/source-backed entity types,
view-count metadata, publication/trial rows, source-backed report sections,
and a stable frontend-facing richer result shape remain open.

Goal:

Expand beyond run/report search into a reusable indexed entity model for the
product search bar.

Context:

The current schema names `SearchDocType = Literal["report", "run"]`. That is
too narrow for a product search bar that should find genes, variants, source
evidence, publications, trials, and workspace records.

Implementation update, 2026-07-01:

- `SearchDocType` now includes `library_variant`.
- `VariantLibraryService` receives the shared `SearchIndexService` in
  `create_app()` and treats indexing as a logged secondary side effect.
- `SearchIndexService` builds private `library_variant` search documents from
  saved variants with stable hashed source keys, gene/HGVS/protein aliases, and
  owner filtering.
- `SearchRepo` can delete a single indexed document or all indexed documents
  for an owner/doc-type pair so library delete and whole-document replace do
  not leave stale hits.
- Focused API tests cover owner-only saved-variant search, delete cleanup, and
  whole-library replace refresh.

Relevant files:

- `app/backend/app/schemas/search.py`
- `app/backend/app/core/db.py`
- `app/backend/app/repos/search_repo.py`
- `app/backend/app/services/search_index.py`
- `app/backend/app/services/variant_library.py`
- `app/backend/app/main.py`
- `app/backend/tests/test_frontend_contract.py`
- `app/web/lib/backend.ts`

Proposed approach:

- Add new schemas while preserving existing response fields during migration.
- Introduce entity types and alias rows behind the repo boundary.
- Add index builders for source-backed entities already present in existing
  payloads/cache, not fresh source calls.
- Keep exact aliases separate from text body so identifier matches rank higher.
- Add contract tests and update `app/web/lib/backend.ts` only once backend
  schemas are stable.

Acceptance criteria:

- Search can return at least one non-run/report private workspace entity type
  from existing product writes.
- Search can return at least one non-run/report public/source-backed entity type
  from fixture or materialized data. (Still open.)
- Existing run/report search clients still work.
- Exact gene/HGVS/rsID aliases outrank plain-text mentions.
- Frontend contract test covers the new response shape when a richer
  frontend-facing search result contract is introduced.

Source reference:

`docs/search-index/spec.md`, Requirements 8, 9, 10, and 13.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_search_api_local.py tests/test_variant_library_api.py tests/test_frontend_contract.py -q
```

Out of scope:

- pgvector or external hosted search.
- Large source asset policy changes.

## Task 7 - Integrate the live Next search bar

Goal:

Connect `app/web` to index-backed search results without breaking structured
variant report lookup.

Context:

`EamosSearch` currently submits raw text through `reportHrefForQuery()`.
Structured variants go to `/report?gene=...&cdna=...`; free text goes to
`/report?q=...`. There is no frontend search API helper.

Relevant files:

- `app/web/components/landing/EamosSearch.tsx`
- `app/web/lib/variant-search.ts`
- `app/web/lib/api.ts`
- `app/web/components/report/ReportClient.tsx`
- possible new `app/web/lib/search/api.ts`
- possible new search results route/component under `app/web`

Proposed approach:

- Preserve `reportHrefForQuery()` structured-variant behavior.
- Add a typed search API helper under a feature folder.
- Add a search results surface for free-text/entity queries.
- Display title, result type, snippet, provenance/freshness, and route action.
- Do not add sample/mock fallback search results.
- Browser-verify desktop and mobile once UI exists.

Acceptance criteria:

- Structured variant searches still open reports.
- Free-text search opens index-backed results.
- Empty/error/unauthorized/rate-limited states render clearly.
- No `app/frontend` mirror is treated as active product code.

Source reference:

`docs/search-index/spec.md`, Frontend integration section.

Verify:

```powershell
cd app/web
npm run lint
npx tsc --noEmit
```

Browser verification:

- Landing search structured variant.
- Landing search free text.
- Report-page compact search structured variant.
- Mobile viewport for search results.

Out of scope:

- Redesigning the whole landing/report page.

## Task 8 - Grounded AI answer hardening

Goal:

Keep `/api/v1/search/answer` useful but safe: answers cite only returned indexed
hits and cannot invent sources or execute tools.

Context:

`SearchAnswerService` already calls `search_service.search()` first and filters
citations against returned results. The feature is disabled by default through
`settings.search_answer_enabled`.

Relevant files:

- `app/backend/app/services/search_answer.py`
- `app/backend/app/api/routes/search.py`
- `app/backend/app/agents/client.py`
- `app/backend/tests/test_search_api.py`

Proposed approach:

- Add local tests with a fake answer chain.
- Validate that citations not present in the top hits are dropped.
- Add rate limits and, if needed later, per-user AI usage caps consistent with
  chat caps.
- Keep output plain text or sanitized markdown only; do not render model output
  as raw HTML.

Acceptance criteria:

- Disabled/unconfigured answer endpoint returns stable 503.
- Enabled fake-chain test returns grounded answer and valid citations.
- Invalid model citations are excluded.
- Search results are still returned alongside answers.

Source reference:

`docs/search-index/spec.md`, Requirement 14 and Decision D5.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_search_api.py tests/test_rate_limits.py -q
```

Out of scope:

- Giving the answer model database/tool access.

## Task 9 - Update graph/docs/handoff after implementation slices

Goal:

Keep the repo's durable state accurate after each search slice.

Context:

Repo instructions require graphify updates after modifying code. The handoff
files are shared and must use the log edit-lock protocol before edits.

Relevant files:

- `docs/search-index/spec.md`
- `docs/search-index/plan.md`
- `docs/repo-structure/audit-2026-06-30.md`
- `agent_handoff/CURRENT.md`
- `PROGRESS.md`
- `graphify-out/`

Proposed approach:

- After each code slice, update the relevant docs with actual status.
- Run `python -m graphify update .` with at least a 360-second timeout.
- Update `agent_handoff/CURRENT.md` heartbeat and `PROGRESS.md` only at useful
  boundaries, using the edit lock.

Acceptance criteria:

- A session clear can resume from the docs and handoff without relying on chat.
- Graphify AST graph is refreshed after code changes.
- No semantic graph pass is run unless Steven explicitly asks.

Source reference:

`AGENTS.md`, `agent_handoff/README.md`, and `docs/search-index/spec.md`.

Verify:

```powershell
python -m graphify update .
git diff --check -- docs/search-index/spec.md docs/search-index/plan.md
```

Out of scope:

- Commit or push unless Steven approves the exact action.
