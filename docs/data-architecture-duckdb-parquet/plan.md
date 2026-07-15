# DuckDB/Parquet Analytical Lane Plan

Last updated: 2026-06-25 23:59 +1000 - Codex.
Status: Phase 0 local adapter slice and Phase 1 manifest/preflight contract
implemented locally; materialization remains operator-gated.

## Goal

Adopt the vault Forj data-architecture standard in EAMOS without moving
single-coordinate report lookup off the existing prepared cache, tabix, SQLite,
and local-index adapters.

## Guardrails

- No standing Spark, MotherDuck, managed-Supabase `pg_duckdb`, or request-path
  `httpfs`.
- Do not push the bulk genomic reference corpus into Supabase Postgres.
- Do not replace tabix/SQLite point lookups with DuckDB unless a later
  benchmark proves equal or better latency, memory, and rollback behavior.
- No Render env mutation, Supabase mutation, deploy, or multi-GB materialization
  without Steven's explicit approval.

## Phase 0 - Embedded Analytical Adapter

Status: Implemented locally.

Deliverables:

- `duckdb` backend dependency.
- `DUCKDB_ANALYTICAL_*` settings with Render-aware `/var/data` defaults.
- Read-only `DuckDbAnalyticalAdapter`, lazy per-worker connection, cursor per
  query, memory limit `1500MB`, threads `2`, and temp spills on local disk.
- Sanitized provider-cache health under `source_assets.duckdb_analytical`.
- Tests for disabled health, enabled missing artifact, and read-only open
  wiring.

Verify:

- `python -m pytest tests/test_duckdb_analytical.py tests/test_health_api.py -q`
- `python -m py_compile app/services/duckdb_analytical.py`
- Ruff, Black check, `git diff --check`, and backend structural boundary tests.

## Phase 1 - Artifact Contract And Preflight

Status: Implemented locally for manifest/checksum/row-count preflight. No real
corpus build or serving-path dependency.

Tasks:

- Define the local artifact layout:
  `data/bio_assets/analytical/{bronze,silver,gold}/<release>/chrom=<chrom>/`.
- Define release manifest fields: source IDs, source versions, input checksums,
  output checksums, row counts, schema versions, build command, and build host.
- Add a read-only CLI preflight that validates an existing release without
  building multi-GB outputs.
- Extend provider-cache health with sanitized release identity and row-count
  summaries when artifacts exist.

Acceptance:

- A missing release fails closed with sanitized health.
- A tiny fixture release can be validated in tests without `duckdb` network or
  large assets.
- `python -m app.cli.eamos_duckdb_analytical_preflight --manifest-path ...`
  verifies manifest layout, output checksums, and row-count totals without
  opening a DuckDB database or materializing data.
- No request route depends on DuckDB.

## Phase 2 - Silver Materialization

Status: Operator-gated.

Tasks:

- Materialize dbSNP, ClinVar, and predictor source tables to
  chrom-partitioned, position-sorted, zstd Parquet.
- Use DuckDB as primary engine, Polars streaming where memory shape requires it,
  and Snakemake for reproducible rebuilds.
- Pin source versions and checksums before every build.
- Emit manifests before an atomic `current` pointer/symlink swap.

Acceptance:

- Rebuild is deterministic for the same inputs.
- Output validates on a tiny fixture and a bounded representative slice.
- Full-size builds are not run from web startup/deploy.

## Phase 3 - Gold Materialized Join

Status: Planned beside tabix/SQLite, not replacing them.

Tasks:

- Build coordinate-sorted Gold joins across dbSNP, ClinVar, and predictor
  outputs.
- Benchmark Gold analytical reads against tabix/SQLite/report cache for:
  single-coordinate lookup, 1k-variant VCF batch, region aggregation, and report
  freshness scans.
- Feed report/source cache artifact generation only where Gold wins or greatly
  simplifies build reproducibility.

Acceptance:

- Benchmark results document which engine owns each workload.
- Point-lookup adapters remain the default until a separate decision changes
  that boundary.

## Phase 4 - Runtime Enablement

Status: Future operator action.

Tasks:

- Seed release artifacts onto the Render persistent disk.
- Verify checksums and provider-cache health on the running service.
- Flip `DUCKDB_ANALYTICAL_ENABLED=true` only after local health is green.
- Run read-only live health/audit checks; do not enable lookup-path usage.

Acceptance:

- Health reports ready, release identity, read-only access, and no local paths.
- No startup downloads, request-time materialization, or remote object reads.
