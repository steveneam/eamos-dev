# Search results and answer hardening spec

Status: Implemented sequentially locally on 2026-07-04; contract freeze
`f7ef561` is pushed, while the A/B/C implementation remains uncommitted pending
review/commit approval.
Created: 2026-07-04 by Codex

## What

Add the first authenticated index-backed search results surface to `app/web`
and harden `/api/v1/search/answer` with grounded fake-chain tests. Preserve the
existing structured variant report path and keep search answers disabled unless
explicitly configured.

## Context

Backend search is implemented through `app/backend/app/api/routes/search.py`,
`app/backend/app/services/search.py`, `app/backend/app/services/search_index.py`,
and `app/backend/app/services/search_answer.py`. Current local coverage lives in
`app/backend/tests/test_search_api_local.py`.

The active frontend search bar is `app/web/components/landing/EamosSearch.tsx`.
Submit owners in landing and report currently call `reportHrefForQuery()` from
`app/web/lib/variant-search.ts`, which sends free text to `/report?q=...`.
There is no `app/web/lib/search/**`, no `/search` route, and no Next proxy for
`GET /api/v1/search`.

## Requirements

1. Structured variant inputs keep routing to `/report?gene=...&cdna=...`.
2. Free-text/entity inputs route to `/search?q=...`.
3. `/search` requires the backend-authenticated search endpoint; unauthenticated
   responses render a sign-in-required state for now.
4. Search results show doc type, title, subtitle/snippet, provenance-ish
   metadata when available, and a route action from `target_href`.
5. The UI handles loading, empty, 401, 429, 5xx/proxy failure, and malformed
   query states without mock/sample fallback.
6. Frontend search code lives under feature folders:
   `app/web/lib/search/**`, `app/web/components/search/**`, and
   `app/web/app/search/**`.
7. The backend search response types are mirrored into both current
   `backend.ts` files before lanes fork and covered by contract tests.
8. `SearchAnswerService` has local fake-chain tests proving:
   disabled answers return stable 503;
   unconfigured model returns stable 503 when enabled;
   grounded answers return only citations tied to returned hits;
   invalid model citations are dropped.
9. CI runs web typecheck and backend asset-bound tests self-skip on clean
   runners instead of being workflow-deselected.

## Design

### Contract freeze

Add TypeScript exports for the current backend search schemas:

- `SearchDocType`
- `SearchVisibilityScope`
- `SearchMatchType`
- `SearchMetadataValue`
- `SearchHit`
- `SearchResponse`
- `SearchAnswerRequest`
- `SearchCitation`
- `SearchAnswerResponse`

Mirror them in `app/web/lib/backend.ts` and
`app/frontend/src/lib/backend.ts` while the byte-identical mirror guard remains.
Extend `test_frontend_contract.py` for these fields if the existing parameter
list does not cover them. Completed locally on 2026-07-04 with no backend
behavior change.

Implementation update, 2026-07-04: after the parallel lane flow was canceled,
Codex implemented the CI ratchets, answer hardening, and frontend search
results surface sequentially in the main checkout. The original worktrees are
parked with partial uncommitted diffs and are not active lanes.

### Frontend

Create `app/web/lib/search/api.ts` with a typed `searchEamos()` helper. It
should call `/api/v1/search?q=...&limit=...`, preserve backend error status, and
return `SearchResponse`.

Create a Next proxy at `app/web/app/api/v1/search/route.ts` only if direct
same-origin rewrites are not enough for local/prod parity. The proxy forwards
auth headers and query parameters to the backend target and returns upstream
status and content type.

Create `app/web/app/search/page.tsx` and `SearchResultsClient` under
`app/web/components/search/**`. Use existing layout/nav components and avoid a
marketing page; the first screen is the usable results surface.

Update landing and report submit handlers to use a small routing helper:

- `structuredVariantFromText(raw)` truthy -> `reportHrefForQuery(raw)`.
- otherwise -> `/search?q=<raw>`.

### Backend answer hardening

Keep the answer endpoint disabled by default. Add fake-chain unit/API tests in
local backend tests. Tighten service behavior only as needed by the tests; no
provider or real model access.

## Decisions

### D1: Require auth for search results now

Choice: render sign-in-required for unauthenticated search responses.

Alternatives: public-only search for public rows, or anonymous proxy search.

Why: backend currently requires auth and Steven chose auth-required for now.

Reversible: yes, after backend explicitly supports public search scope.

### D2: Preserve variant report routing

Choice: structured variant queries keep using `/report`.

Why: report lookup is mature and product-critical; Task 7 is additive.

Reversible: partly, after search ranking and routing are trusted.

### D3: Contract freeze before lanes

Choice: mirror Search types before frontend/backend lanes fork.

Why: it avoids parallel lanes editing the same contract file and gives the UI a
stable target.

Reversible: no for the sprint. If the contract changes, re-plan.

## Invariants

- No source downloads, provider calls, startup backfill, Supabase mutation,
  env/provider flips, or Render deploy from lanes.
- Search result UI does not fabricate snippets or provenance.
- Private rows remain backend-filtered by owner.
- `app/frontend` remains frozen historical product code; any touch is contract
  mirror only while the existing canary requires it.
- CI gate should be at least as strict as Vercel's deploy typecheck.

## Error Behavior

- Missing/empty `q`: render an empty prompt state or redirect to `/`.
- 401: sign-in-required state with the query preserved.
- 429: rate-limited state with retry guidance from `Retry-After` when present.
- 5xx/502: backend unavailable state; no sample fallback.
- Empty results: honest empty state with the query shown.
- External `target_href`: render as an HTTPS link only when backend supplied an
  allowed URL. Internal paths must start with `/`.

## Testing Strategy

Backend:

- `cd app/backend; python -m pytest tests/test_search_api_local.py tests/test_search_api.py tests/test_rate_limits.py -q`
- Focused answer tests with a fake answer chain.
- Contract tests for mirrored Search response fields.

Frontend:

- `cd app/web; npm run lint`
- `cd app/web; npx tsc --noEmit -p tsconfig.json`
- Browser verification for structured variant submit, free-text submit,
  unauthenticated state, empty state, and mobile results layout.

Operations:

- `git diff --check`
- `python -m graphify update .` with long timeout after code changes.

## Out of Scope

- Public anonymous search.
- Search autocomplete/typeahead.
- AI answer UI.
- New backend search entity types.
- Provider/source refresh or materialization.
- Supabase migrations.
