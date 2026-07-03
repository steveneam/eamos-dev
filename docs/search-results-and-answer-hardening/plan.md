# Search results and answer hardening plan

Status: Implemented sequentially locally on 2026-07-04 after the parallel lane
flow was canceled. Contract freeze `f7ef561` is pushed; A/B/C implementation is
uncommitted in the main checkout pending review/commit approval.
Spec: `docs/search-results-and-answer-hardening/spec.md`
Design: `docs/search-results-and-answer-hardening/design.md`

## Shared decisions before implementation

- Search results require auth for now.
- Structured variant queries keep routing to `/report`.
- Freeze the Search response contract on `main` before lanes fork.
- No lane performs source materialization, provider calls, Supabase mutation,
  env/provider flips, production deploys, or destructive cleanup.
- Lead scope-checks every lane before merge with `git log --name-only`.

## Task 0 - Serial contract freeze

Status: done locally on 2026-07-04; freeze before any lane fork.

Goal:

Create the frozen backend-to-frontend Search response seam before parallel work
starts.

Context:

The backend has Search schemas in `app/backend/app/schemas/search.py`, but the
frontend contract mirrors do not currently expose Search types. The contract
canary still requires `app/web/lib/backend.ts` and
`app/frontend/src/lib/backend.ts` to be byte-identical.

Relevant files:

- `app/backend/app/schemas/search.py`
- `app/web/lib/backend.ts`
- `app/frontend/src/lib/backend.ts`
- `app/backend/tests/test_frontend_contract.py`

Proposed approach:

- Add TypeScript Search types matching the current backend schemas.
- Add or extend contract canary coverage.
- Commit this on `main` before lanes fork.

Acceptance criteria:

- Search response types exist in both frontend mirrors.
- Contract canary passes.
- No backend behavior changes.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_frontend_contract.py -q
```

Out of scope:

- UI wiring.
- Answer behavior changes.

## Task 1 - CI ratchets lane

Status: done locally on 2026-07-04 in the sequential main-checkout pass.

Goal:

Make the merge gate a stronger executable ratchet for parallel lanes.

Context:

The `web` CI job currently lints but does not typecheck. Backend CI deselects two
asset-bound tests by node id because clean runners lack their gitignored assets.

Relevant files:

- `.github/workflows/ci.yml`
- `app/backend/tests/test_pdf_text.py`
- `app/backend/tests/test_source_reader_proofs.py`

Proposed approach:

- Add asset-absent `pytest.skip` or `skipif` behavior to the two tests.
- Remove the two `--deselect` lines from CI.
- Add `npx tsc --noEmit -p tsconfig.json` to the web CI job.
- Optionally bump GitHub Action majors if current major warnings persist.

Acceptance criteria:

- Clean CI runner can execute backend pytest without pinned deselects.
- Web job fails on TypeScript errors before Vercel deploy.
- No unrelated test semantics change.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_pdf_text.py tests/test_source_reader_proofs.py -q
cd ..\web
npx tsc --noEmit -p tsconfig.json
npm run lint
```

## Task 2 - Backend answer hardening lane

Status: done locally on 2026-07-04 in the sequential main-checkout pass.

Goal:

Prove `/api/v1/search/answer` is disabled by default and grounded when enabled
with a fake answer chain.

Context:

`SearchAnswerService` searches first, builds context from returned hits, invokes
an optional chain, and drops citations not tied to returned results. Existing
local tests cover disabled behavior but not enabled fake-chain grounding.

Relevant files:

- `app/backend/app/services/search_answer.py`
- `app/backend/app/api/routes/search.py`
- `app/backend/tests/test_search_api_local.py`
- `app/backend/tests/test_search_api.py`

Proposed approach:

- Add a fake answer chain test fixture.
- Test disabled, enabled-without-chain, enabled-grounded, and invalid-citation
  dropping cases.
- Tighten citation validation only if test evidence shows a gap.

Acceptance criteria:

- Enabled fake-chain response includes only valid citations.
- Invalid citations are dropped.
- Search results are returned alongside the answer.
- No real model/provider/API key required.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_search_api_local.py tests/test_search_api.py tests/test_rate_limits.py -q
```

Out of scope:

- Answer UI.
- Real LLM calls.
- Token budgets or billing controls.

## Task 3 - Frontend search results lane

Status: done locally on 2026-07-04 in the sequential main-checkout pass.
Desktop browser smoke was run; mobile browser verification was skipped because
Steven asked to stop live verification and wrap.

Goal:

Expose index-backed search results in the active Next app while preserving
structured report lookup.

Context:

`EamosSearch` is shared by landing/report surfaces, but submit owners route all
queries through `reportHrefForQuery()`. Backend search requires auth.

Relevant files:

- `app/web/components/landing/EamosSearch.tsx`
- `app/web/components/landing/LandingClient.tsx`
- `app/web/components/report/ReportClient.tsx`
- `app/web/lib/variant-search.ts`
- `app/web/lib/search/**`
- `app/web/components/search/**`
- `app/web/app/search/**`
- optional `app/web/app/api/v1/search/route.ts`

Proposed approach:

- Add a typed search API helper under `app/web/lib/search/`.
- Add a `/search` page/client and focused result components.
- Add route helper logic so structured variants still go to `/report`, while
  free text goes to `/search?q=...`.
- Render sign-in-required, empty, loading, rate-limited, and backend-error
  states without sample fallback.

Acceptance criteria:

- Landing structured variant submit opens `/report?gene=...&cdna=...`.
- Landing free-text submit opens `/search?q=...`.
- Report compact search preserves the same behavior.
- Auth-required state is clear and does not fake results.
- Results display backend `target_href` actions safely.
- Mobile layout does not overlap or truncate key text.

Verify:

```powershell
cd app/web
npm run lint
npx tsc --noEmit -p tsconfig.json
```

Browser verification:

- Landing search structured variant.
- Landing search free text.
- Report-page compact search structured variant.
- `/search` unauthenticated state.
- `/search` mobile viewport.

Out of scope:

- Public anonymous search.
- Autocomplete.
- AI answer UI.

## Task 4 - Lead integration and deploy gate

Status: partially done locally. The lane merge model was canceled before PR/CI
merge; implementation exists as uncommitted main-checkout changes. No deploy has
been run.

Goal:

Merge the lanes safely and verify the integrated behavior.

Context:

Strict branch protection requires each lane after the first to rebase and rerun
CI after prior merges. The lead is the sole merger and pauses for Steven's
approval before each merge.

Relevant files:

- `COORDINATION.md`
- `docs/search-results-and-answer-hardening/*`
- `docs/search-index/plan.md`
- `agent_handoff/CURRENT.md`
- `PROGRESS.md`

Proposed approach:

- Merge Task 1, then Task 2, then Task 3.
- Scope-check each lane before merge.
- Run focused local verification and browser proof after frontend integration.
- Update docs and graphify AST after code changes.
- Deploy from `main` only after Steven approves.

Acceptance criteria:

- CI green for every lane at merge time.
- No lane touches files outside its owned glob except `COORDINATION.md`.
- Search UI and answer tests are both verified.
- Handoff docs contain a fresh resume prompt.

Verify:

```powershell
git diff --check
python -m graphify update .
```
