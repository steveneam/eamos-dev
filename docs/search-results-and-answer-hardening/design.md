# Search results and answer hardening design

Status: Implemented sequentially, reviewed, committed, and pushed on
2026-07-04. Serial contract freeze `f7ef561`; implementation commit `319b9e7`.
Parked Search worktrees/branches were cleaned after explicit approval.
Created: 2026-07-04 by Codex
Related: `docs/search-index/spec.md`, `docs/search-index/plan.md`,
`COORDINATION.md`

## Summary

Search Task 7 should add an index-backed results surface to the active Next app
without breaking structured variant report lookup. Search Task 8 should harden
the disabled-by-default answer endpoint with deterministic fake-chain tests that
prove answers are grounded in returned hits. The safe shape is a small serial
contract-freeze pass followed by parallel lanes: CI ratchets, backend answer
hardening, and frontend search results.

## Context and Scope

Backend search is already wired in normal app startup. It returns public
`gene`, `condition`, `gene_disease`, `source`, `publication`, `trial`, and
`popular_variant` hits, plus owner-filtered private workspace hits. Search
requests require authentication today.

The live frontend still routes every non-empty text query through
`reportHrefForQuery()`. Structured variants route to `/report?gene=...&cdna=...`;
free text routes to `/report?q=...`, where report lookup tries to interpret the
query. There is no index-backed results page or typed search helper in
`app/web`.

This design covers the next workflow only. It does not change search backend
schemas, provider posture, source materialization, Supabase state, auth policy,
or production env flags.

## Goals

- Preserve structured variant report routing.
- Route free-text/entity queries to authenticated index-backed search results.
- Render useful result states: loading, empty, unauthorized, rate-limited,
  upstream error, and normal results.
- Keep result routing driven by backend `target_href` when it is safe.
- Add answer-chain tests proving disabled/unconfigured behavior, valid
  citations, and invalid citation dropping.
- Raise CI confidence so the merge gate catches web type errors and clean-runner
  backend asset absence.

## Non-Goals

- Public unauthenticated search. Steven chose auth-required for now.
- Autocomplete/typeahead inside the search bar.
- AI answer UI.
- External search infrastructure, pgvector, source scans, provider calls,
  startup backfill, Supabase mutation, or env/provider flips.
- Reworking report lookup semantics beyond submit routing.

## Constraints

- `app/web` is the active frontend. `app/frontend` is a frozen historical mirror
  but `test_frontend_contract.py` still requires byte-identical `backend.ts`
  mirrors.
- The backend search contract is backend-led. It must be frozen before frontend
  lanes fork.
- Search endpoints require authentication; the frontend must not assume public
  search.
- The merge gate currently lacks `app/web` typecheck and pins two backend tests
  with `--deselect`.
- Render deploy remains main-only; worktree lanes must not deploy production.

## Proposed Design

First land a serial contract-freeze pass on `main`:

- Mirror the current backend search schema types into `app/web/lib/backend.ts`
  and `app/frontend/src/lib/backend.ts`.
- Add or extend the frontend contract canary so Search response types cannot
  drift.
- Make no backend behavior changes in this freeze pass.

Implementation note, 2026-07-04: the Search response and answer TypeScript
mirror plus contract canary coverage were added as the serial pre-step. Parallel
lanes must treat this seam as frozen.

Implementation note, 2026-07-04: Steven canceled the parallel lane execution
after the spawned-worker trial. Codex completed the CI ratchets, answer
hardening, and frontend search results pass sequentially in the main checkout;
the parked worktrees are no longer active lanes.

Then fork parallel lanes:

- CI ratchets lane: make asset-bound backend tests skip when assets are absent,
  drop workflow `--deselect`, add `tsc --noEmit -p tsconfig.json` to web CI, and
  optionally bump action majors.
- Backend answer lane: add fake-chain tests around `SearchAnswerService` and
  tighten citation validation only if tests show a gap.
- Frontend results lane: add `app/web/lib/search/api.ts`, a same-origin
  `GET /api/v1/search` proxy if needed, a `/search` page, and result components
  under `app/web/components/search/**`. Wire landing/report search submitters so
  structured variants still use `/report`, while free text uses `/search?q=...`.

## Interfaces and Data

Frozen backend-to-frontend shape:

- `SearchDocType`
- `SearchVisibilityScope`
- `SearchMatchType`
- `SearchMetadataValue`
- `SearchHit`
- `SearchResponse`
- `SearchAnswerRequest`
- `SearchCitation`
- `SearchAnswerResponse`

Frontend route behavior:

- Structured variant input -> unchanged `/report?gene=...&cdna=...`.
- Free text/entity input -> `/search?q=<query>`.
- Empty input -> no navigation.
- Unauthenticated search result fetch -> sign-in state with no sample fallback.

## Alternatives Considered

- Keep sending free text to `/report?q=...`: lowest effort, but leaves the
  product search index invisible.
- Replace all search behavior with index results: too risky; structured variant
  lookup is product-critical and already tested.
- Allow public search now: attractive for landing UX, but backend currently
  requires auth and Steven chose auth-required for now.
- Build answer UI in this sprint: premature; first prove the answer endpoint is
  safely grounded.

## Tradeoffs

Auth-required search means anonymous landing users will see a sign-in state
instead of immediate public entity results. That is acceptable for this slice
because it avoids widening backend access posture while search UI matures.

The contract-freeze pass touches both frontend mirrors, including the frozen
Vite mirror, because the current canary requires byte identity. That is a
temporary cost until the contract-source guard is simplified.

## Cross-Cutting Concerns

Security and privacy: private hits remain owner-filtered server-side. The UI
does not display raw private text except through authenticated API results and
does not synthesize snippets.

Reliability: no mock/sample fallback for search results. Network and upstream
errors render explicit states.

Observability: provider-cache health already reports search readiness. This
sprint does not add new telemetry.

Operations: no startup backfill, source refresh, Supabase mutation, provider
flip, or Render deploy from lanes.

## Rollout and Migration

1. Contract-freeze commit on `main`.
2. Fork lanes from frozen `main`.
3. Merge CI ratchets first, then answer tests, then frontend results.
4. Run focused backend tests, web lint/typecheck, browser verification, and
   graphify AST update.
5. Deploy only after main is green and Steven approves the merge/deploy seam.

Backout: revert the frontend route/submit wiring to restore old `/report?q=...`
behavior while leaving backend search and tests intact.

## Open Questions

- Should unauthenticated users see a generic sign-in state, or a dedicated
  "Search requires sign in" page with the original query preserved? Recommended:
  dedicated sign-in state on `/search`, preserving `q`.
- Should result clicks for external `target_href` values open same tab or new
  tab? Recommended: same tab for internal paths, new tab with safe `rel` for
  external HTTPS.

## Decision

Proceed with auth-required frontend search integration and backend answer
hardening after a serial contract freeze. Use Mode B if Steven wants separate
Codex terminals for the frontend/backend/CI lanes; Mode A remains acceptable if
Codex is the only available runtime and keeps lane count to three.
