# Message to Selom

Last updated: 2026-06-25 18:37 +1000 - Codex.

Selom, Steven asked Codex to pause feature work and capture the Eamos architecture
consistency plan before continuing. The work is committed and pushed on
`origin/main`:

- `1a80f45 feat(report): cache lazy lookup sections`
- `98e35fc docs(architecture): capture consistency gate`

Docs to review:

- `docs/architecture-consistency-gate/plan.md`
- `docs/architecture-consistency-gate/inventory.md`
- `docs/architecture-consistency-gate/session-prompts.md`
- `docs/data-architecture-duckdb-parquet/adr.md`
- `docs/data-architecture-duckdb-parquet/plan.md`
- `docs/report-performance-optimization/plan.md`
- `memory/eamos-architecture-consistency-gate.md`

Core plan:

1. Task A - Convert the static architecture inventory into an actionable
   checklist with owner, pass/fail evidence, route/table/UI/cache surface, and
   missing gates.
2. Task B - Build the frontend report section registry and stable skeletons so
   report sections, nav, exports, lazy fetch, and browser preflight all use one
   shared section contract.
3. Task C - Clean the cache boundary so new report/source state lives in
   `source_result_cache` and `report_section_cache`, with `variant_cache`
   treated as compatibility only.
4. Task D - Keep DuckDB/Parquet in the analytical lane. Start with tiny fixture
   artifact layout, manifest, checksum/row-count validation, and read-only
   health/preflight. No real corpus or multi-GB materialization yet.
5. Task E - Add measured performance/memory proof and test hygiene. This now
   explicitly includes splitting/marking slow legacy cache integration cases so
   normal feature commits have fast named contract gates.
6. Task F - Supabase production readiness: RLS, grants, advisors, FK/composite
   indexes, private storage policies, and sanitized health proof. No remote
   mutation without Steven approval.

Important boundaries:

- Single-coordinate lookup stays on prepared report cache, tabix, SQLite, and
  local indexes unless a benchmark-backed ADR changes that.
- DuckDB/Parquet is for batch, region/cohort/freshness analytics, release
  validation, and building compact serving artifacts.
- PubMed/PMC should use layered corpus architecture: upstream objects/manifests,
  Parquet release layers, compact SQLite/FTS/vector runtime stores, and
  report/source caches. Do not put huge article blobs in Supabase Postgres.
- Supabase Postgres owns metadata, user/app state, cache tables, RLS, and
  operational records; private object storage owns large immutable artifacts.

Please review the architecture gate and apply the reusable components/patterns
to Selom where they fit: section registries with stable skeletons, explicit
cache/source boundaries, analytical-lane separation, performance proof, and
fast-vs-slow test gates.
