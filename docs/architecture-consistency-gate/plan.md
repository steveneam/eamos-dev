# Eamos Architecture Consistency Gate

Last updated: 2026-06-26 00:20 +1000 - Codex.
Status: Draft gate for Steven review. No code, deploy, Supabase mutation, or
multi-GB materialization is implied by this document.

## Goal

Before the next feature slice, verify that Eamos uses one robust architecture
across lookup, analysis, report sections, workbench tools, caches, database
tables, API routes, UI loading states, metrics, and operational artifacts.

The target skeleton is:

```text
user input
  -> search/input resolution
  -> normalized variant identity
  -> source adapter or prepared cache
  -> source_result_cache row with status/freshness/version/provenance
  -> report/analysis section envelope
  -> frontend section registry slot
  -> preflight, health, timing, payload-size, and memory telemetry
```

Any section, page, or metric that cannot be described by this path is either a
legacy compatibility path or an architecture gap.

## Current Read

The current backend direction is sound:

- `/api/v1/lookup`, `/lookup/summary`, `/lookup/sections`, and
  `/lookup/publications` are split at the route layer.
- Local SQL tables now model normalized variants, report shells, section
  envelopes, source results, and hydration status.
- `LookupService.lookup_sections()` has prepared-hit and source-specific
  cold-miss builders for the current report section set.
- The DuckDB/Parquet lane is accepted as an analytical/build lane beside
  prepared cache, tabix, SQLite, and local indexes. It is not a point-lookup
  replacement.

The architecture is not yet production-certified:

- The DuckDB/Parquet Phase 1 manifest/preflight work is local and tiny-fixture
  only; no real corpus materialization has run.
- The frontend still needs one shared report-section registry with stable
  skeleton, empty, partial, stale, failed, and hydrating states.
- Older `variant_cache.publication_data` compatibility storage is still present
  and must not become the long-term home for new report state.
- Task E now has a live read-only evidence pass for ABCA4/RPE65/USH2A timing,
  payloads, desktop preflight, fast test targets, and Render RSS. Production
  closeout still requires a deploy-approved rerun because the deployed backend
  still rejects `therapies_trials` section fetches.

## Gate Matrix

| Area | Required invariant | Current status | Gate before production |
| --- | --- | --- | --- |
| File system | Source, generated artifacts, source assets, scratch files, and docs have clear homes. | Mostly present, but large source assets coexist with source tree paths. | Confirm `.gitignore`/artifact layout; no generated multi-GB files in Git; no runtime writes outside `/var/data` or approved local data dirs. |
| API endpoints | Every expensive route has auth/rate/input bounds and explicit failure states. | Lookup/chat/batch/workbench routes exist; history shows prior OOM-class fixes. | Endpoint inventory with auth, rate limit, max payload, cache path, and failure contract per route. |
| SQL schema | Hot queries have composite indexes and FK indexes; user data has RLS in Supabase; JSON blobs are compatibility only. | Local SQLAlchemy tables have useful unique/index constraints for report caches. | Supabase migration plan with RLS, grants, advisors, FK/composite index checks, and no service-role client exposure. |
| Lookup path | Single-coordinate requests prefer prepared shell/section cache and source-specific local indexes. | Implemented locally for current sections. | Verify p50/p95 and provider-call counts for ABCA4/RPE65/USH2A cold/warm paths. |
| Analysis path | Batch, region, cohort, and freshness scans use analytical artifacts, not point-lookup loops. | DuckDB phase 0 adapter is local and disabled by default. | Add tiny fixture Parquet/DuckDB preflight and benchmark matrix before any real materialization. |
| UI sections | Every report section has a stable slot independent of data arrival. | `LazySection` exists, but registry/stable skeletons are still Task 5. | Implement `REPORT_SECTION_REGISTRY`; preflight asserts required slots before hydration. |
| Metrics | Timing, payload size, memory, cache hit rate, and source freshness are observable. | Lookup timing header and report audit script exist locally. | Make diagnostics opt-in, bounded, sanitized, and covered by audit scripts. |
| Caching | Source-result cache owns provider rows; report-section cache owns renderable envelopes. | Table-backed cache path is now present locally. | Deprecation plan for legacy `variant_cache.publication_data` report blobs. |
| Security | Secrets never reach client bundles; service-role remains server/operator only. | Public env scan shows expected public anon/site flags and backend-only secret placeholders. | Run secret scan, Supabase RLS/advisors for remote schema, and deployment header/CORS checks before launch. |
| Operations | No startup/request-time downloads; no unapproved Supabase/Render mutation. | Existing guardrail is strong and repeated in plans. | Every materialization command has dry-run, checksum, rollback, and sanitized health proof. |

## DuckDB and Parquet Decision

Do not clone or build the DuckDB source repository for Eamos unless we are
patching DuckDB itself. The runtime need is the Python package already added in
the local Task 4 work, plus a small fixture dataset and preflight/benchmark
scripts.

Parquet should save meaningful storage for some Eamos assets, but only when the
workload and lifecycle match:

- Good candidates:
  - ClinVar/dbSNP/predictor Silver tables.
  - Gold analytical joins for batch VCF, region/cohort scans, and freshness
    dashboards.
  - Generated report-section source summaries that are rebuilt in batches.
- Bad candidates:
  - Tiny request-path rows already served from SQLite tables.
  - Single-coordinate hot lookup if tabix/SQLite/local indexes already win.
  - Mutable user/account tables, review state, payments, or auth data.

The storage strategy should be:

```text
Supabase private Storage:
  durable raw inputs, immutable Parquet releases, manifests, checksums

Render persistent disk:
  only the current approved runtime release, compact serving indexes, temp
  DuckDB spill, and rollback-sized previous artifact when justified

Supabase Postgres:
  metadata, app/user records, cache tables that need SQL semantics, not the
  multi-GB genomic corpus
```

## Processing vs Storage Tradeoff

Parquet can reduce durable storage and transfer volume, but it moves cost into
offline materialization:

- Benefits:
  - columnar compression;
  - projection/filter pushdown;
  - chromosome/Hive partition pruning;
  - smaller object-storage footprint than raw expanded CSV/JSON/SQLite in many
    source layouts;
  - easier batch analytics and reproducible rebuilds.
- Costs:
  - build CPU and memory;
  - temporary disk during conversion;
  - schema/version migration work;
  - extra decompression cost at query time;
  - worse repeated join-heavy query performance than loaded DuckDB tables in
    some workloads.

Rule: keep Parquet as the durable analytical/rebuild format; derive compact
serving artifacts from it only where benchmarks show a win.

## PubMed and PMC Corpus Decision

PubMed and PMC should not be treated as one database table or one request-time
asset. They need a tiered literature corpus lane:

```text
NCBI baseline/update source files
  -> immutable Bronze manifests and checksums
  -> normalized Parquet Silver tables by source/year/license/status
  -> Gold literature views for Eamos use cases
  -> runtime SQLite/FTS/vector stores and source-result/report-section cache
```

For PubMed citations:

- keep the annual XML baseline and daily update semantics as the source of
  truth;
- normalize into Parquet for durable rebuilds, freshness scans, license/policy
  audits, and batch literature analytics;
- derive compact SQL/FTS serving tables for PMID lookup, gene/variant term
  search, publication counts, and report publication sections;
- store only metadata or license-permitted abstract text according to the
  existing `abstract_policy` model.

For PMC full text:

- treat PMC OA, commercial-use, non-commercial-only, other-license, author
  manuscript, XML, text, PDF, media, and supplement packages as separate
  source lanes;
- do not persist or redistribute full text unless the article-level license
  permits the intended use;
- use Parquet for article metadata, license policy, PMCID/PMID joins, extracted
  entities, section-level text features, and checksums;
- keep the original large article objects in private/object storage or reference
  them by upstream object identity rather than expanding them into Postgres;
- only build runtime SQL/FTS/vector artifacts from a bounded, license-approved
  subset that Eamos actually serves.

The robust SQL model is not "load PubMed/PMC into Supabase Postgres." It is:

- Supabase Postgres for corpus metadata, release manifests, job status,
  source-version rows, and user-visible cache references;
- Parquet in private object storage for large immutable analytical releases;
- local/runtime SQLite FTS or vector artifacts for fast publication retrieval;
- `source_result_cache` and `report_section_cache` for rendered report outputs.

Good SQL tables for the literature lane:

- `literature_release`;
- `literature_source_file`;
- `literature_article`;
- `literature_article_identifier`;
- `literature_article_license`;
- `literature_article_term`;
- `literature_entity_edge`;
- `literature_section_feature`;
- `literature_retraction_status`;
- `literature_embedding_manifest`;
- `literature_materialization_job`.

Do not put full article XML/text/PDF blobs in Supabase Postgres. For Eamos, SQL
should index and govern the corpus; Parquet/object storage should hold the
large release data; compact generated stores should serve hot lookups.

## Required Benchmark Before Conversion

Use a tiny fixture first, then one bounded representative slice. For each source
candidate, record:

- raw input size;
- compressed Parquet size with `zstd`;
- compact serving artifact size, if generated;
- Supabase upload method required and object count;
- Render disk footprint after seeding only the current runtime subset;
- materialization wall time;
- peak RSS;
- temp disk peak;
- point lookup p50/p95;
- 1k-variant batch p50/p95;
- region/cohort scan time;
- checksum/preflight time;
- rollback path.

Minimum decision table:

| Source | Keep raw? | Parquet Silver? | Gold join? | Serving artifact? | Runtime owner |
| --- | --- | --- | --- | --- | --- |
| ClinVar | durable raw + Parquet | yes | yes, for report scans | SQLite/tabix/index if faster | lookup/report |
| dbSNP | durable raw + Parquet | yes | yes | compact index/tabix for point lookup | lookup/batch |
| AlphaMissense | durable raw + Parquet | yes | maybe | local indexed predictor adapter | report/batch |
| PubMed citations | annual baseline + update files | yes | yes, for term/license/freshness views | SQLite/FTS/vector store | literature/report/RAG |
| PMC full text/OA | upstream objects + license manifests | yes, metadata/features only first | maybe, license-approved subsets | bounded FTS/vector subset | literature/RAG |
| LitVar/PubTator edges | durable edge snapshots | yes | yes, PMID/entity joins | SQLite edge/term indexes | literature/report |
| ClinicalTrials | JSON snapshot + normalized table | maybe | no until needed | source-result/report-section cache | report |

## Gate Tasks

### Task A - Architecture Inventory

Produce a machine-readable inventory of:

- backend routes and their auth/rate/input limits;
- SQLAlchemy tables, indexes, unique constraints, and FK coverage;
- frontend report/workbench section surfaces;
- cache tables and source IDs;
- preflight/health surfaces.

Acceptance: one inventory artifact plus findings for missing limits or missing
state contracts.

### Task B - Section Registry and UI Stability

Implement or review `REPORT_SECTION_REGISTRY` before further report UI growth.

Acceptance: every required report section renders a stable slot on desktop and
mobile before hydration, and `scripts/eamos-report-preflight.mjs` fails when a
required slot disappears.

### Task C - Cache Boundary Cleanup

Make the table-backed report cache the canonical path.

Acceptance: new report sections never write new state only into
`variant_cache.publication_data`; compatibility reads are explicitly marked and
covered by tests.

### Task D - DuckDB/Parquet Phase 1

Status: implemented locally for manifest/preflight proof; no real corpus build.

Add only the artifact contract and tiny fixture preflight:

- layout under `data/bio_assets/analytical/{bronze,silver,gold}/<release>/`;
- manifest schema;
- checksum and row-count validation;
- no request-route dependency;
- no multi-GB build.

Acceptance: disabled/missing/ready health states are sanitized and tests pass
without real assets.

### Task E - Performance and Memory Proof

Status: live read-only evidence captured; production rerun pending deploy.

Run local and, when approved, live read-only audits:

- `scripts/eamos-report-performance-audit.mjs`;
- report preflight with required section slots;
- backend focused tests;
- test-suite timing audit that separates fast contract tests from slow legacy
  integration tests;
- memory watch during ABCA4/RPE65/USH2A reports;
- no `/viewer` duplicate fetch when seeded context is available;
- payload-size ceiling check.

Acceptance: p50/p95 and peak RSS are recorded for cold and warm paths.
Cache/report tests have a fast, named contract target that completes quickly,
while slower legacy integration-style cache cases are marked, split, or moved
behind an explicit slow-test gate so normal feature commits do not depend on a
multi-minute file-level run.

Evidence: `docs/architecture-consistency-gate/task-e-performance-memory-evidence.md`
records live ABCA4/RPE65/USH2A cold/warm p50/p95, payload ceilings, desktop
preflight, no first-paint viewer fetch, fast test timing, and Render peak RSS
of 641.9 MB (31.3% of the 2 GB cap). Remaining gap: live
`/lookup/sections` still returns 422 for `therapies_trials` until the pushed
local contract is deployed and rechecked.

### Task F - Supabase Production Readiness

Before any remote schema/storage change:

- search current Supabase docs/changelog for relevant breaking changes;
- run advisors;
- enforce RLS on exposed schemas;
- keep private source assets in private Storage, not public buckets;
- keep service-role and S3 keys server/operator only;
- use resumable/S3 upload for large objects;
- record rollback object/version.

Acceptance: migration/runbook includes verification SQL and sanitized health
proof. No remote mutation happens without explicit approval.

## Next Recommended Move

Do Task A as a read-only inventory, then Task B if Steven wants frontend
stability first, or Task D if Steven redirects to data architecture. Do not
start multi-GB Parquet conversion until Task D's tiny fixture preflight and
Task E's benchmark harness exist.

## References

- `docs/report-performance-optimization/plan.md`
- `docs/architecture-consistency-gate/task-e-performance-memory-evidence.md`
- `docs/data-architecture-duckdb-parquet/adr.md`
- `docs/data-architecture-duckdb-parquet/plan.md`
- `docs/report-backend-source-cache-readiness/plan.md`
- `docs/report-evidence-framework/plan.md`
- DuckDB Parquet docs: https://duckdb.org/docs/current/data/parquet/overview
- DuckDB file-format performance guide: https://duckdb.org/docs/lts/guides/performance/file_formats
- Supabase Storage pricing: https://supabase.com/docs/guides/storage/pricing
- Supabase upload size restrictions: https://supabase.com/docs/guides/troubleshooting/upload-file-size-restrictions-Y4wQLT
- Render persistent disks: https://render.com/docs/disks
