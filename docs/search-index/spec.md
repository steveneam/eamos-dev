# Eamos search index spec

Status: run/report wiring plus private search posture and readiness/backfill slice implemented; Task 6 backend breadth now covers private library variants, public publications/trials, and private report sections from existing payloads; frontend integration remains planned.
Created: 2026-06-30 by Codex.
Related structure work: `docs/repo-structure/plan.md`, Wave 2 in
`docs/repo-structure/audit-2026-06-30.md`.

Implementation update, 2026-06-30:

- `create_app()` now constructs `SearchRepo`, `SearchService`,
  `SearchIndexService`, and the disabled-by-default `SearchAnswerService`.
- `GET /api/v1/search` works in ordinary local app construction with empty-index
  `200` responses instead of composition-root `503`s.
- Search routes use an explicit `RATE_LIMIT_SEARCH` scope keyed by IP and
  authenticated user subject.
- Uploaded report indexing, review refresh indexing, and run creation indexing
  are wired through existing services.
- Run/report search documents now carry `visibility_scope` and `owner_user_id`.
  Newly uploaded reports and newly created runs are indexed as private rows
  owned by the authenticated user. Ownerless historical private rows fail
  closed for user-facing search until an explicit backfill assigns ownership.
- Search queries now pass a server-side access context to the repository. Normal
  users can search public rows and their own private rows; internal rows remain
  hidden unless a future internal access context explicitly opts in.
- Provider-cache health exposes sanitized search readiness: service wiring,
  table/index presence, entity/visibility counts, last index timestamp,
  ownerless private row backlog, and answer-chain status.
- `python -m app.cli.eamos_search_index_backfill` provides a dry-run-first
  run/report backfill from existing DB rows. It does not fetch sources, mutate
  Supabase, call providers, or run during startup.
- AI search answers remain gated by `settings.search_answer_enabled` and a
  configured answer chain; no answer chain is configured in normal startup.
- Local non-Docker coverage now lives in
  `app/backend/tests/test_search_api_local.py`.

Implementation update, 2026-07-01:

- Search document schemas now accept `library_variant` in addition to `run` and
  `report`.
- Saved variant-library writes index owner-scoped private search documents for
  individual save, bulk save, and whole-library replace. Deleting a saved
  variant removes its search document.
- Library-variant search uses the existing bounded search tables with stable
  hashed source keys and variant aliases. It does not add migrations, source
  downloads, provider calls, Supabase mutations, startup work, or frontend
  integration.
- Local API coverage proves saved library variants are searchable only by the
  owning user and that replace/delete operations refresh indexed rows.
- Public/source-backed publication and trial rows are indexed from existing run
  report payloads as public search documents. Report-section rows are indexed
  as owner-scoped private documents.
- Report-payload PATCH, approve, and drop flows refresh run/report-section
  search rows after the primary write succeeds, preserving the existing
  best-effort indexing posture.

## What

Build a Search Control Plane for the product search bar: an authenticated,
rate-limited, indexed search service that can find Eamos domain entities without
request-time source scans. The first implementation should make the existing
`/api/v1/search` route honest and useful for indexed runs/reports, then extend
the index to product-wide entities such as variants, genes, publications,
trials, library rows, and source-backed evidence.

## Context

The product is centered on a single search bar, but the current backend has two
separate concepts that do not add up to a robust search index.

Existing run/report search:

- `app/backend/app/api/routes/search.py` mounts `GET /api/v1/search` and
  `POST /api/v1/search/answer`.
- Those routes require auth, but look up `request.app.state.search_service` and
  `request.app.state.search_answer_service`.
- `app/backend/app/main.py` includes the search router through
  `build_api_router()` and constructs `SearchRepo`, `SearchService`,
  `SearchIndexService`, and `SearchAnswerService`.
- `app/backend/app/repos/search_repo.py` supports exact run/report/patient IDs,
  exact variant fields, PostgreSQL full-text search, and a SQLite `LIKE`
  fallback.
- `app/backend/app/services/search_index.py` builds indexed documents from
  uploaded reports and runs.
- `IntakeService`, `RecommendationService`, and `WorkflowService` receive the
  shared `search_index_service` in normal app construction.
- `WorkflowService.create_run()` indexes newly created runs after the primary
  run write succeeds. Indexing failures are logged and do not corrupt the run
  write.
- `app/backend/tests/test_search_api.py` remains Docker-gated, but normal local
  route coverage now exists in `app/backend/tests/test_search_api_local.py`.

Existing search-input resolver:

- `EamosSearchInputResolver` parses gene, cDNA, protein, rsID, and genomic
  inputs for report lookup.
- `build_runtime_coordinate_resolver(settings)` deliberately builds an
  `EamosLocalCoordinateResolver` without raw GFF scan paths.
- `CompactCoordinateIndex` is a real compact coordinate index, but it is not a
  general product search index.
- `POST /api/v1/lookup/parse` forces `resolve_coordinates=False`, which is the
  right public request-path posture.

Existing frontend search:

- `app/web/components/landing/EamosSearch.tsx` is the live Next search bar.
- `app/web/lib/variant-search.ts` routes structured variant-like queries to
  `/report?gene=...&cdna=...` and unparseable/free text to `/report?q=...`.
- `app/web/lib/api.ts` has lookup/workbench helpers but no search API helper.
- There is no same-origin Next route proxy under `app/web/app/api/v1/search`.

The current state is therefore not "no search code"; it is a first wired
run/report search route plus a separate variant resolver. The product still
needs an indexed, source-aware search control plane that composes both and adds
explicit public/private search scope.

## Requirements

1. `GET /api/v1/search` must be wired in normal `create_app()` construction and
   must return either indexed results or an empty result set for a healthy app.
   A healthy app must not return 503 merely because the composition root forgot
   to set search services.
2. `POST /api/v1/search/answer` remains feature-gated by
   `settings.search_answer_enabled` and the configured answer chain. Search
   results must work without AI answers.
3. Search endpoints must require authenticated users and route-level rate
   limiting. Rate limits must use both IP and authenticated user subject when
   the user is available.
4. Search must not perform raw source scans, source downloads, provider calls,
   Supabase mutations, runtime seed/sync work, or startup materialization on the
   request path.
5. The first indexed entity set must include report uploads and runs:
   report upload, run creation, review updates, approval/drop status changes,
   and report-payload updates must either update the index synchronously after
   the primary write succeeds or be covered by an explicit backfill/reindex
   command.
6. Index writes must be idempotent. Reindexing the same source key must update
   the current row and replace stale child rows rather than duplicating results.
7. Product search must distinguish public/source-backed entities from private
   workspace entities. Private report/run results must be access-controlled
   before multi-user launch. Until ownership is explicit on the indexed source,
   snippets must not expose raw uploaded report text to a user who is merely
   authenticated.
8. Search responses must expose enough result metadata for the UI to route and
   explain a hit: result type, title, subtitle or snippet, match type, score,
   target href or source identifiers, status/freshness, and provenance.
9. Variant-like queries must use deterministic normalization first. The search
   service may reuse `SearchInputInterpreter`/`EamosSearchInputResolver` with
   coordinate resolution disabled by default, but must not invoke heavyweight
   coordinate resolution or external lookup sources during ordinary search.
10. Exact matches must outrank full-text matches. Recommended initial priority:
    run/report ID, patient ID if allowed, exact variant identity, gene/entity
    alias, weighted full-text, recency.
11. PostgreSQL must use explicit indexes on frequent filter/join columns and a
    weighted full-text expression/index for text search. SQLite must retain a
    local-test fallback, but production ranking is PostgreSQL FTS.
12. Health/preflight output must make search readiness visible: service wired,
    table/index availability, indexed row counts by entity type, last index
    update timestamp, stale/backfill-needed status, and answer feature status.
13. Search schema changes must preserve frontend contract tests. `app/web` is
    the active frontend contract home; `app/frontend` must not become a second
    active search implementation.
14. AI search answers must be grounded only in returned indexed hits and
    citations must be validated against those hits. LLM output is untrusted and
    must not be rendered as HTML or used to build SQL/tool calls.

## Design

### Search modes

The search service should treat user input as one query with layered
interpreters:

1. **Deterministic identifier mode** for run IDs, report IDs, patient IDs where
   allowed, source IDs, PubMed IDs, trial IDs, and exact library/query IDs.
2. **Variant/entity mode** for gene symbols, HGVS, rsIDs, genomic coordinates,
   and protein changes. This uses normalization and indexed aliases, not live
   source calls.
3. **Full-text mode** for clinical notes, evidence summaries, publication
   titles, trial terms, source labels, and report titles.
4. **Answer mode** only after search results are produced and only when the
   answer feature flag/model are configured.

The resolver and the index are separate responsibilities. Resolver code decides
what a raw query likely means; the search index decides what existing Eamos
entities match it.

### Backend components

Initial package shape can stay compatible with the current files, but the
implementation should move toward a small package as the feature grows:

```text
app/backend/app/services/search/
  __init__.py             # preserves app.services.search.SearchService
  service.py              # query orchestration and ranking
  indexer.py              # source entity -> index documents
  normalizer.py           # identifiers, gene/HGVS aliases, query modes
  answers.py              # grounded answer wrapper
  health.py               # readiness/count summaries

app/backend/app/repos/search_repo.py
app/backend/app/api/routes/search.py
app/backend/app/schemas/search.py
```

Do not fold this package in the same task as large unrelated folder cleanup.
The first slice may keep the current module names to reduce blast radius.

### Index model

Use the existing `search_documents` and `search_variants` rows for the first
run/report slice, then evolve toward a generalized entity index.

Current usable model:

- `search_documents`: source key, doc type, run/report/patient identifiers,
  statuses, title-ish fields, summary/evidence/review/raw/search text, created
  and updated timestamps.
- `search_variants`: child rows for gene symbol, transcript HGVS, protein
  change, and consequence.
- PostgreSQL FTS expression in `app/backend/app/core/db.py` weights identifiers
  above summary/evidence/review/raw text.

Generalized model for the robust product index:

```text
search_entities
  entity_pk
  source_key unique            # e.g. run:..., report:..., variant:...
  entity_type                  # run, report, variant, gene, publication, trial, source
  visibility_scope             # public, private, internal
  owner_user_id nullable       # required for private multi-user workspace rows
  title
  subtitle
  route_path
  identifier_text
  summary_text
  evidence_text
  search_text
  facets json                  # gene, condition, source, statuses, tags
  provenance json              # provider/source/cache/license details
  source_status
  source_version
  license_key nullable
  indexed_at
  source_updated_at

search_entity_aliases
  alias_pk
  entity_pk references search_entities
  alias_type                  # gene, transcript_hgvs, protein, rsid, pmid, trial_id
  alias_value
  alias_norm
  weight
```

PostgreSQL indexes:

- unique btree on `source_key`.
- btree on `entity_type`, `visibility_scope`, `owner_user_id`,
  `source_updated_at`, and `indexed_at`.
- btree on `search_entity_aliases.alias_norm` and
  `search_entity_aliases.entity_pk`.
- GIN FTS index over weighted identifier/title/summary/evidence/search text.
- Consider partial indexes for common filtered subsets once real query patterns
  are known, for example public entities and non-dropped workspace rows.

Do not add external hosted search, Algolia, Meilisearch, pgvector, or trigram
extensions in the first slice. They are future options after the PostgreSQL FTS
baseline has tests and query metrics. If vector search is later required, prefer
a private Postgres/pgvector-backed path with the same provenance and access
controls rather than copying PHI to a third-party search service.

### Index sources

First slice:

- Uploaded reports from `IntakeService.ingest_upload()`.
- Runs from `WorkflowService.create_run()`.
- Review updates from `RecommendationService.apply_review()`.
- Approval/drop/report-payload updates from the services that mutate
  `RunRecord`.
- Backfill CLI or admin command that reads existing run/report rows and rebuilds
  the index without touching source/provider state.

Second slice:

- Variant library saved rows and view metadata.
- Source-backed report sections that already exist in cache payloads.
- Publication/trial rows that are already materialized or returned in lookup
  payloads. The search index should index what Eamos has already fetched or
  materialized, not trigger fresh source queries.

Current implementation note: variant library saved rows are the first completed
piece of this slice. View metadata, source-backed report sections,
publication/trial rows, and public gene/source entities remain open.

Later slices:

- Public gene and disease vocabulary from approved vendored/materialized source
  assets.
- Workbench artifacts only if they are persisted as user-owned objects.
- Paper extraction runs only after ownership and provenance are explicit.

### API shape

Keep the existing route family but evolve the response.

Initial compatible request:

```http
GET /api/v1/search?q=RPE65&limit=10&doc_type=run
```

Proposed richer request fields:

```text
q: required non-empty string
limit: 1..50
cursor: optional opaque cursor for later pagination
entity_type: optional repeatable filter
scope: public | workspace | all, default all allowed by the user
run_status, review_status: existing filters for run/report rows
```

Proposed result fields:

```text
entity_type
source_key
title
subtitle
snippet
target_href
match_type
score
status
freshness
provenance
facets
run_id/report_id/patient_id where allowed
```

The UI should be able to route without re-parsing the query. For example:

- variant hit -> `/report?gene=...&cdna=...`
- run/report hit -> existing run/report route
- publication hit -> paper/source detail route, when available
- gene hit -> `/report?q=GENE` or a future gene page

### Frontend integration

The first UI integration should not replace structured variant lookup. It should
add an index-backed results path for free text and ambiguous queries:

1. Keep `reportHrefForQuery()` for deterministic variant-like inputs.
2. Add `app/web/lib/search/api.ts` or a small helper in `app/web/lib/api.ts`
   only if the structure guard allows it; avoid a flat `search-api.ts` under
   `lib`.
3. Add a same-origin Next route proxy only if needed for deployment parity,
   mirroring the existing lookup proxy pattern.
4. Search bar submit behavior:
   - structured variant -> existing `/report?gene=...&cdna=...`
   - file upload -> existing compare/report path
   - free text -> search results surface, not a fake report
5. Results must show provenance/freshness for source-backed hits and must not
   silently fall back to sample data.

### Health and operations

Add search readiness to health/preflight output:

- `service_wired: true/false`
- `index_tables_present: true/false`
- `postgres_fts_ready: true/false/not_postgres`
- `entity_counts`
- `private_rows_without_owner_count`
- `last_indexed_at`
- `stale_source_count`
- `answer_enabled`
- `answer_model_configured`

Backfill/reindex must be an explicit operator action. It must not run during app
startup and must not download sources or mutate provider settings.

## Decisions

### D1: Start with PostgreSQL FTS, not an external search engine

Choice: use the existing database/search repo path and PostgreSQL full-text
search for the first robust slice.

Alternatives considered:

- External hosted search engine: stronger product search ergonomics, but adds
  PHI/governance, sync, secrets, and cost concerns.
- Vector search first: useful later for semantic evidence retrieval, but not a
  substitute for exact clinical identifiers and provenance.
- Keep SQLite/LIKE only: fine for tests, not robust enough for production.

Why: Eamos already has SQLAlchemy models, a weighted FTS expression, and local
SQLite fallback tests. The smallest safe product improvement is wiring and
hardening that path before adding more infrastructure.

Reversible: yes. A later index adapter can add vector or external search behind
the same schemas and access controls.

### D2: Search is an index over known Eamos entities, not a live-source resolver

Choice: request-time search never scans raw source files, materializes assets,
or calls external providers.

Why: source-backed Eamos flows already have explicit materialization/cache
policies. Search should be fast, bounded, and explainable.

Reversible: no for launch posture. Live source search can be a separate,
explicit tool/action with its own limits and provenance, not the default search
bar path.

### D3: Product search has public and private scopes

Choice: source-backed public/reference entities and private workspace entities
share one control plane but have explicit visibility and ownership fields.

Assumption: run/report records may contain patient-sensitive content. Auth alone
is not sufficient authorization in a multi-user deployment.

Why: the current route is authenticated but not owner-scoped. A robust search
bar must not leak uploaded report text across users.

Reversible: partly. The first local/dev slice can operate under current
single-tenant assumptions, but launch search must include owner filtering before
private entities are exposed to end users.

### D4: Keep structured variant lookup stable while adding search results

Choice: structured variant-like inputs continue to route to the existing report
lookup path. Index-backed search is added for free text, entity discovery, and
workspace results.

Why: the report path is heavily tested and product-critical. Replacing it with
new search behavior would mix two risky changes.

Reversible: yes. The UI can later show autocomplete/results before submit once
the backend ranking is trusted.

### D5: AI answers depend on search, not the other way around

Choice: `search_answer` stays optional and grounded in returned hits.

Why: exact clinical/entity search must work without an LLM. AI output must not
invent citations or trigger tools.

Reversible: no for safety. The answer layer can get better, but it must remain
grounded.

## Invariants

- `app/backend/app/main.py` remains the composition root and does not define
  route handlers.
- Existing `/api/v1/lookup` report behavior remains unchanged for structured
  gene/variant queries.
- `build_runtime_coordinate_resolver(settings)` remains the runtime coordinate
  resolver path and must not re-enable raw GFF scans.
- Search indexing is idempotent and can be rebuilt.
- Request-time search is read-only except for logging/metrics.
- No startup materialization, seed/sync, provider flip, source download, or
  Supabase mutation is introduced by search wiring.
- Private report/run raw text is not exposed in snippets unless owner filtering
  is implemented and tested.
- The active frontend integration is `app/web`; `app/frontend` is not updated
  as a parallel product surface.

## Error behavior

- Empty or whitespace query returns `200` with no results, or `422` if the route
  keeps FastAPI `min_length=1`; choose one behavior and test it.
- Missing search service in app state should be a test failure after wiring. In
  production, it may still return `503` only for genuinely unavailable
  dependencies.
- Database/index unavailable returns `503` with a stable detail string and logs
  the underlying exception server-side.
- Rate limit returns `429` with `Retry-After`.
- Unauthorized search returns `401`.
- AI answer disabled or unconfigured returns `503` from `/answer` without
  affecting `GET /api/v1/search`.
- Backfill failures report the source key and error count, skip/continue when
  safe, and exit non-zero if any required source failed.

## Testing strategy

Backend:

- Non-Docker API tests proving `GET /api/v1/search` is wired in the standard
  `create_app()` fixture.
- Tests for report upload indexing, run creation indexing, review/status
  reindexing, and idempotent rebuild.
- Search repo tests for exact IDs, exact variant aliases, weighted full text,
  filters, SQLite fallback, and PostgreSQL FTS where available.
- Rate-limit tests for `/api/v1/search` and `/api/v1/search/answer`.
- Authorization tests proving private rows are filtered by owner before
  multi-user launch exposure.
- Health/preflight tests for search readiness fields.
- Contract tests for any schema changes mirrored in `app/web/lib/backend.ts`.

Frontend:

- Unit tests for `reportHrefForQuery()` preserving structured variant routing.
- API helper tests for search responses and errors.
- Component tests or Playwright proof for free-text search results once UI work
  starts.
- No mock/sample fallback for search results.

Operational:

- Backfill CLI dry-run test on fixture SQLite DB.
- Focused `python -m graphify update .` after code changes.

## Out of scope

- Deleting or retiring the existing search route.
- Implementing external hosted search infrastructure.
- Adding pgvector/vector ranking in the first slice.
- Running source downloads/materialization, Supabase migrations, provider flips,
  deploy mutations, commits, or pushes.
- Reworking the entire search bar UI before backend search is wired and tested.
- Solving full multi-tenant ownership across all existing Eamos routes. The
  search feature must not make that gap worse; private search launch depends on
  explicit access filtering.
