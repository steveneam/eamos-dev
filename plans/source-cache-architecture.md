# Source Cache And Local Evidence Architecture

Source: user request on 2026-05-25 to run or plan a local database/webserver
architecture for faster source-backed evidence and Workbench scoring.

Status: Task 0 hero-example source-cache pilot, Task 2 arbitrary gnomAD
read-through, and the additive provider/cache health endpoint were implemented
by Codex on 2026-05-25; existing FastAPI + SQLite/Postgres + `variant_cache` is
runnable today. SpliceAI, ClinVar, ClinGen, and local warehouse slices are still
pending separate identity/version decisions.

## Shared Decisions

- Keep the FastAPI backend as the only application API. The frontend must not
  invent snippets, classifications, CRISPR scores, or source evidence.
- Keep fixture mode deterministic: `USE_REAL_APIS=false` remains the default.
- Use the existing SQLAlchemy database boundary for local SQLite, Docker
  Postgres, and future Supabase/Postgres compatibility.
- Store small, normalized source payloads in SQL. Do not attempt to mirror full
  gnomAD or large annotation datasets into a free-tier hosted database.
- Treat ClinVar, ClinGen, SpliceAI, gnomAD, PubMed/LitVar2, and CRISPR scoring
  as provider-backed caches with source version/provenance and explicit stale
  or fallback status.
- Serve stale-on-failure when a provider fails and a stale source row exists.
  A stale row is better than a fabricated miss, but it must be labeled as
  stale and carry the original fetch timestamp/version.
- Use local file/columnar storage for large public datasets when needed
  (DuckDB/Parquet or provider-native files), with SQL storing pointers,
  metadata, and curated slices.
- Hosted source-cache rows are global shared evidence, not user-owned rows:
  write with a backend service role and keep reads backend-only. Do not expose
  `source_cache` directly to Supabase anon/authenticated clients through RLS.
- Keep CRISPR source-backed scoring optional and deterministic. If R/Bioconductor
  is unavailable or a package is platform-gated, return deterministic fallback
  scores with an honest provider note.
- First implementation target should be the report-capable example variants
  under the landing-page hero search bar. These examples are small, curated,
  frequently clicked, and ideal for proving cache warming, stale-on-failure,
  and freshness display before broad user-query caching.

## Source Status Contract

Canonical source status values for evidence rows:

- `live`: provider call succeeded and returned usable source data.
- `cache`: fresh cache hit; treat as a successful usable state.
- `stale`: stale cache row served because live refresh failed or timed out;
  treat as usable but warning-tinted and clearly time-labeled.
- `fallback`: provider failed and a deterministic/local fallback was used;
  degraded unless a usable cache/stale row is also attached.
- `fixture`: deterministic offline fixture mode.
- `missing`: provider returned a real no-hit or fixture mismatch; not an error
  and not a successful evidence assertion.
- `live_stub`: live mode could not run because required identity, such as
  genomic coordinates, was unavailable.
- `error` / `failed`: provider or adapter failed with no usable cache/fallback.

`cache` and `stale` are success-path states for report rendering and should not
be routed through broad `live_fetch_failed` degraded banners unless there is no
usable cached payload.

When source cache lands, add these optional fields to `EvidenceSourceSummary`
and any source-provenance/call-card models that need freshness display:

- `fetched_at: str | None` - ISO timestamp for the source payload being shown.
- `source_version: str | None` - provider dataset/API/package version when
  available.
- `cache_status: str | None` - cache-layer state when it differs from the
  visible source status, for example `stale_on_failure`.

These are additive backend-led contract changes. Mirror both frontend
`backend.ts` files, extend `test_frontend_contract.py`, and recapture
`app/web/lib/rpe65-sample.json` if `/api/v1/lookup` shape changes.

## Current Runnable Baseline

The backend already supports:

- `DATABASE_URL=sqlite+pysqlite:///./data/app.db` for local development.
- Docker Postgres through `app/backend/docker-compose.yml`.
- `variant_cache` for successful live lookup hydration, including resolved
  coordinates, gnomAD/SpliceAI strict-genomic evidence, PubMed/LitVar2
  publication data, and EP-VLEx/functional publication summaries.
- Supabase write-through for accepted evidence submissions when Supabase env
  vars are configured; local SQL fallback when they are not.

Baseline boot command:

```powershell
cd app/backend
$env:USE_REAL_APIS = "false"
$env:LLM_PROVIDER = "mock"
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/healthz
```

## Task 0 - Hero Example Cache Pilot

Status: Implemented 2026-05-25 by Codex.

**Goal**

Make the landing-page hero example variants load from warmed source-cache rows
before generalizing source-cache behavior to arbitrary user queries.

**Context**

The example chips under the hero search bar are the most visible and
repeatable user path. They should feel instant and source-backed, and they are
small enough to warm safely on a schedule or during deploy. They also make
freshness UI obvious: the report can show `cached` or `stale` with an `as of`
timestamp without the frontend inventing source state.

**Relevant Files**

- `app/web/components/landing/LandingClient.tsx`
- `app/web/lib/variant-search.ts`
- `app/backend/app/services/lookup_service.py`
- new `app/backend/app/repos/source_cache_repo.py`
- new source-cache route/service helpers if needed
- `app/backend/tests/test_source_cache.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_frontend_contract.py`

**Proposed Approach**

Define the canonical hero examples in one backend-visible list, using the same
queries the landing chips route to. Add a cache warm command/service that runs
source-backed lookup for those examples, writes source-level cache rows, and
records `fetched_at`, `source_version`, status, and warnings. The frontend keeps
linking to `/report?gene=...&cdna=...`; it does not create snippets or source
facts. When the report loads, the backend should prefer fresh cache rows for
these examples, serve stale rows on provider failure, and bypass cache on an
explicit refresh.

**Acceptance Criteria**

- DONE: Hero example variants are cache-warmed without changing the chip UI
  contract.
- DONE: First report load for a warmed example can use source-cache rows for
  supported sources and returns status/freshness metadata on
  `EvidenceSourceSummary`.
- DONE: Provider failure with only stale hero-example data returns
  `status="stale"` rather than a blank/missing report section.
- DONE: `?refresh=true` performs a live refresh and rewrites cache rows only on
  successful usable provider results.
- DONE: No non-example arbitrary user query is pre-warmed or read through by
  this pilot.
- DONE: `/api/v1/lookup` shape changed additively; both `backend.ts` mirrors
  and `app/web/lib/rpe65-sample.json` were updated in the same backend-led
  slice.

Implemented files:

- `app/backend/app/core/db.py`
- `app/backend/app/repos/source_cache_repo.py`
- `app/backend/app/services/source_cache.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/cli/warm_source_cache.py`
- `app/backend/app/schemas/run.py`
- `app/frontend/src/lib/backend.ts`
- `app/web/lib/backend.ts`
- `app/web/lib/rpe65-sample.json`
- `app/backend/tests/test_source_cache.py`

**Verify**

```powershell
cd app/backend
python -m pytest tests/test_source_cache.py tests/test_variant_search_integration.py tests/test_frontend_contract.py -q
```

## Task 1 - Normalize Source Cache Rows

**Goal**

Add a general source-cache table/repository for small source responses that are
useful across lookup, report, and Workbench flows.

**Context**

`variant_cache` is lookup-shaped. It is good for whole-report hydration, but
ClinVar/ClinGen/SpliceAI/gNOMAD/CRISPR providers need a source-level cache key,
source version, TTL, status, and raw/normalized payload.

**Relevant Files**

- `app/backend/app/core/db.py`
- `app/backend/app/repos/variant_cache_repo.py`
- new `app/backend/app/repos/source_cache_repo.py`
- `app/backend/app/tools/registry.py`
- `app/backend/tests/test_variant_cache.py`
- new `app/backend/tests/test_source_cache.py`

**Proposed Approach**

Create `source_cache` with fields for source, cache key, normalized identity,
status, source version, summary JSON, raw JSON, warnings JSON, source URL,
created timestamp, and expiry timestamp. Add a repository that supports
get-fresh, upsert, bypass on refresh, and explicit invalidation by source/key.

**Acceptance Criteria**

- Cache rows are keyed by source plus normalized variant/provider identity.
- Normal reads return only fresh rows.
- Provider failure can serve a stale row with explicit `status="stale"`,
  `cache_status="stale_on_failure"`, `fetched_at`, source version, and warnings.
- Cached rows preserve original status and warnings.
- Missing/unresolved lookups are not cached unless explicitly marked as a
  source-level no-hit with a short TTL.
- SQLite and Postgres both initialize the table without migrations in tests.

**Verify**

```powershell
cd app/backend
python -m pytest tests/test_source_cache.py tests/test_variant_cache.py -q
```

## Task 2 - Wire Read-Through Cache For Small Evidence Sources

Status: Partially implemented 2026-05-25 by Codex. Arbitrary resolved-variant
source-cache read-through now starts with gnomAD only, keyed by
`gnomad:<dataset>:<normalized_variant_id>`. ClinVar, ClinGen, and SpliceAI are
deferred to separate identity/version slices.

**Goal**

Reduce live API calls for small, variant-level sources while keeping provenance
honest.

**Context**

gnomAD variant GraphQL responses are the first arbitrary-query source-cache
target because they have a stable provider identity (`variant_id` + `dataset`).
ClinVar, ClinGen, and SpliceAI remain suitable candidates, but they should land
after explicit source identity and source-version decisions. PubMed/LitVar2
already have lookup-level caching but can later reuse the source-cache
repository.

**Relevant Files**

- `app/backend/app/tools/clinvar.py`
- `app/backend/app/tools/clingen.py`
- `app/backend/app/tools/spliceai.py`
- `app/backend/app/tools/gnomad.py`
- `app/backend/app/tools/registry.py`
- `app/backend/app/services/lookup_service.py`

**Proposed Approach**

Wrap selected tools with read-through source cache in live mode. For arbitrary
resolved variants, compute provider-identity cache keys before calling the
provider. For gnomAD this is `gnomad:<dataset>:<normalized_variant_id>`. On a
hit, return `ToolResult(status="cache", ...)` with the cached source status
inside the payload/provenance. On refresh, bypass and rewrite.

**Acceptance Criteria**

- DONE: Repeated live lookup of the same resolved variant avoids duplicate
  arbitrary gnomAD provider calls when a fresh source-cache row exists.
- DONE: Arbitrary gnomAD cache keys use provider identity, not `gene:cdna`.
- DONE: `?refresh=true` bypasses the cache for the existing read-through path.
- DONE: Cache hits are labeled as cache hits and retain source provenance.
- DONE: If live gnomAD returns a failure state and only stale data exists, the
  tool returns the stale row rather than a miss, with source failure warnings
  preserved separately.
- DONE: Arbitrary gnomAD no-hits carrying `gnomad_variant_not_found` are not
  persisted as normal long-TTL live successes.
- DONE: Fixture mode never writes source-cache rows.
- PENDING: ClinVar, ClinGen, and SpliceAI arbitrary read-through.

**Verify**

```powershell
cd app/backend
python -m pytest tests/test_tool_invariants.py tests/test_variant_cache.py tests/test_source_cache.py -q
```

## Task 3 - CRISPR Score Cache And R Adapter Health

**Goal**

Make source-backed CRISPR scores fast after first calculation and explicit when
R/Bioconductor is unavailable.

**Context**

The first provider slice supports a deterministic fallback and an Rscript
adapter boundary. Local source-backed scoring needs package/version detection,
provider health, and cache keys by sequence/PAM/model.

**Relevant Files**

- `app/backend/app/services/crispr_design.py`
- `app/backend/app/services/workbench_design.py`
- `app/backend/tests/test_crispr_design.py`
- `app/backend/tests/test_workbench_api.py`

**Proposed Approach**

Cache per-guide score bundles by provider, package version, spacer, PAM,
sequence context, genome/build, and scoring options. Provider health should
report installed R path, package availability, package versions, and disabled
platform-gated models.

**Acceptance Criteria**

- RuleSet1, RuleSet3, CRISPRscan, CRISPRater, MIT, CFD, and Lindel return
  source-backed values when the installed R stack supports them.
- DeepHF, DeepCpf1, and enPAM+GB remain gated with clear notes on Windows.
- Deterministic fallback remains available and visible in provider notes.
- Cached score bundles are invalidated when provider/package version changes.

**Verify**

```powershell
cd app/backend
python -m pytest tests/test_crispr_design.py tests/test_workbench_api.py -q
```

## Task 4 - Local gnomAD Mini-Store

**Goal**

Prototype local gnomAD access without storing the whole public dataset in a
small hosted database.

**Context**

gnomAD is large. The right architecture is local/columnar data or a dedicated
warehouse for heavy datasets, with SQL used for metadata and curated slices.

**Relevant Files**

- `app/backend/app/tools/gnomad.py`
- proposed `app/backend/app/services/gnomad_local_store.py`
- `app/backend/tests/test_gnomad_tool.py`
- proposed `app/backend/tests/test_gnomad_local_store.py`

**Proposed Approach**

Use a tiny fixture-backed DuckDB/Parquet or CSV prototype first. Normalize
lookup by GRCh38 variant ID, return the existing gnomAD summary shape, and keep
dataset/build/source version in provenance. Later replace the fixture data with
a curated local slice or production warehouse.

**Acceptance Criteria**

- Local store returns the same summary shape as `GnomadTool`.
- Missing variants return no-hit state without fixture bleed.
- Per-group AF/AC/AN, homozygotes, popmax, flags, dataset, and version are
  preserved.
- The public API contract does not change.

**Verify**

```powershell
cd app/backend
python -m pytest tests/test_gnomad_tool.py tests/test_gnomad_local_store.py -q
```

## Task 5 - Deployment Modes

Status: Partially implemented 2026-05-25 by Codex. The additive backend-only
provider/cache health route is available at `GET /api/v1/health/provider-cache`
and `/healthz` remains the stable liveness endpoint.

**Goal**

Make the same architecture usable locally, in Docker, and later with Supabase.

**Context**

Free-tier hosted storage is enough for small normalized cache rows and user
submission ledgers, but not for full public genomic datasets.

**Proposed Approach**

Support three modes:

- Local dev: SQLite plus fixture/default deterministic providers.
- Local source-backed: SQLite or Docker Postgres plus live APIs, R/Bioconductor,
  and optional local gnomAD mini-store.
- Hosted: Supabase/Postgres for auth/submission ledgers and small source-cache
  rows; external object/warehouse/local service for large annotations. The
  `source_cache` table remains service-role/backend-only: no direct anon or
  authenticated client table access.

**Acceptance Criteria**

- Environment variables select providers without frontend contract changes.
- DONE: The backend health endpoint can report database/provider availability.
  The provider/cache route includes sanitized source-cache row aggregates and
  CRISPR provider availability without cache keys, variant identities, raw
  payloads, source URLs, configured paths, or warnings.
- No large dataset is required for the app to boot.
- Source-backed modes degrade to deterministic or missing states rather than
  crashing the report/Workbench.

**Verify**

```powershell
cd app/backend
python -m pytest tests/test_health_api.py tests/test_frontend_contract.py -q
```
