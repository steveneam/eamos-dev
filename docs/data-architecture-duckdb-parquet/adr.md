# ADR: DuckDB/Parquet Analytical Lane Beside Local Point-Lookup Adapters

Status: Accepted locally
Owner: Codex/backend
Date: 2026-06-25

## Context

The vault Forj ADR ratifies a portfolio standard: use DuckDB/Polars/Snakemake
for offline and analytical data work, store durable rebuild artifacts as
chromosome-partitioned, position-sorted, zstd Parquet, and keep
single-coordinate variant lookup on tabix/SQLite/local indexes.

EAMOS already has a local-first report-serving path in progress:

- `ReportCacheRepo` and explicit local SQL tables for prepared report shells,
  section envelopes, source-result rows, normalized variants, and hydration
  status.
- Existing tabix/SQLite/local-file adapters for source-specific point lookups.
- Render persistent disk assumptions under `/var/data`, with no large startup
  downloads and no remote data mutation without operator approval.

This ADR records how EAMOS adopts the portfolio standard without regressing the
current report-cache plan.

## Decision

EAMOS will add DuckDB as an embedded, read-only analytical adapter beside the
existing point-lookup adapters.

The single-coordinate hot path remains:

- prepared report shell/section cache first;
- local SQLite/report cache where appropriate;
- tabix/bigWig/local-index adapters for source point lookups;
- live providers only where a source is not locally materialized or is being
  explicitly refreshed.

DuckDB is for:

- bulk VCF annotation and batch QA;
- region/cohort aggregation;
- report/source freshness analytics;
- building and validating compact serving artifacts;
- reading materialized Gold joins when the workload is scan/report shaped.

DuckDB is not for:

- replacing tabix/SQLite point lookups by default;
- request-time joins over raw source files;
- startup materialization;
- remote `httpfs` reads on the hot path;
- MotherDuck, `pg_duckdb`, or standing Spark.

The embedded adapter opens read-only, per uvicorn worker, with cursors per
query. EAMOS defaults it to disabled until a local artifact exists, with:

- `access_mode=READ_ONLY` / `read_only=True`;
- `memory_limit=1500MB`;
- `threads=2`;
- temp spills on the Render persistent disk.

## Gold Replacement Decision

The materialized dbSNP x ClinVar x predictor Gold table sits beside the
per-adapter tabix/SQLite files for phase 1. It does not replace them.

Rationale:

- The Forj standard explicitly keeps single-coordinate lookup on tabix/SQLite.
- EAMOS's current bottleneck is duplicated section hydration, not evidence that
  DuckDB wins point lookups on the 2 GB Render web box.
- Keeping both paths preserves rollback and failure isolation. A bad Gold
  artifact cannot break source-specific tabix/SQLite fallbacks.
- Gold can still feed generated serving artifacts later, including compact
  SQLite/report-section caches or regenerated tabix-style indexes.

Replacement can be reconsidered only after a benchmark proves equal or better
single-coordinate latency, memory behavior, and operational safety on the
target Render class.

## Storage Layout

Silver and Gold artifacts should use:

- medallion folders: `bronze/`, `silver/`, `gold/`;
- immutable dated release folders;
- chromosome partitions such as `chrom=1/`;
- sorted row groups by coordinate;
- zstd compression;
- manifests with source versions, checksums, row counts, schema versions, and
  build commands;
- atomic `current` pointer/symlink swap after verification.

Plain Parquet is the default. Delta/Iceberg/DuckLake are deferred until EAMOS
needs upserts or time travel. DuckLake is the named fallback if that need
appears later.

## Implementation Phases

Phase 0 is the local code slice:

- add `duckdb` to backend requirements;
- add `DUCKDB_ANALYTICAL_*` settings with Render-aware `/var/data` defaults;
- add `DuckDbAnalyticalAdapter` and sanitized provider-cache health;
- keep the adapter disabled by default and unused by lookup routes.

Phase 1 adds the artifact contract:

- document the Parquet release layout and manifest fields;
- add a preflight/check command that verifies local artifact shape without
  building multi-GB outputs;
- teach health/build-ledger to surface release identity when artifacts exist.

Phase 2 builds Silver:

- materialize dbSNP, ClinVar, and predictor source tables into chrom-partitioned
  Parquet;
- pin source versions and checksums;
- use DuckDB primarily and Polars streaming where memory shape requires it;
- keep Snakemake as the reproducibility envelope for full rebuilds.

Phase 3 builds Gold:

- materialize stable coordinate-sorted joins for report/batch workloads;
- keep coordinate-keyed report/source caches in front of request serving;
- benchmark Gold reads against tabix/SQLite before any serving-path expansion.

Phase 4 is operator gated:

- seed artifacts onto the persistent disk;
- verify checksums and provider-cache health;
- flip analytical enablement only after local health is green;
- no Render, Vercel, or Supabase mutation without Steven's explicit approval.

## Edge Hardening

The vault edge-infrastructure guidance is accepted as a lower-priority security
baseline, not part of this data-slice implementation:

- service-role keys stay server-only;
- Supabase anon/JWT paths stay RLS-bound;
- FastAPI JWT verification remains the server trust boundary;
- rate limits and circuit breakers should degrade rather than 500 when external
  sources fail;
- Supabase should stay Sydney-aligned where possible, with Render fronted by
  Vercel as already planned.

## Consequences

Positive:

- EAMOS gains a commercial-clean analytical engine without moving the point
  lookup hot path.
- Large source rebuilds get deterministic Parquet artifacts and manifests.
- The report-cache work remains the first request-path optimization.

Costs and risks:

- DuckDB adds a backend dependency and a new artifact lifecycle.
- The 2 GB Render instance requires strict memory/thread/temp configuration.
- Full Silver/Gold materialization is a multi-GB operator task and must remain
  approval-gated.

## Verification

Local verification for phase 0 should cover:

- default provider-cache health reports the adapter as disabled and sanitized;
- enabled-but-missing database reports a fail-closed missing-artifact status;
- adapter open uses read-only mode, configured memory/thread/temp settings, and
  per-query cursors.

No live audit, deployment, Supabase migration, Render env mutation, or
multi-GB materialization is implied by this ADR.
