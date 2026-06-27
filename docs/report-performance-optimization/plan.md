# Variant Report Performance Optimization Plan

Last updated: 2026-06-27 19:42 +1000 by Codex.

## Implementation Progress

- 2026-06-25: Task 1 started. `ReportGeneViewer` now uses seeded
  `gene_context_snapshot` data for first paint and does not immediately fetch
  `/api/v1/viewer` unless no seed exists or an expanded track needs live viewer
  data.
- 2026-06-25: Trials section rendering now preserves an explicit empty/unavailable
  card when the section envelope exists but no trial rows are available.
- 2026-06-25: `scripts/eamos-report-preflight.mjs` gained `--forbid-viewer` so
  browser preflight can ratchet against accidental duplicate viewer hydration.
- 2026-06-25: Task 2 complete locally. Backend lookup timing diagnostics now
  collect sanitized phase/provider timings and expose them only through the
  opt-in `X-Eamos-Lookup-Timing` header when
  `LOOKUP_TIMING_DIAGNOSTICS_ENABLED=true`; the audit script parses and prints
  the header when present.
- 2026-06-25: Task 3 prepared-hit path started. Full lookups now write a
  versioned `report_shell` into the existing variant cache, and
  `/api/v1/lookup/summary` routes through `LookupService.lookup_summary()` so
  a warm prepared shell returns without re-entering full `lookup()`.
- 2026-06-25: Task 4 prepared-hit path started. Full lookups now write
  versioned lazy section envelopes into the existing variant cache, and
  `/api/v1/lookup/sections` routes through `LookupService.lookup_sections()` so
  warm prepared section fetches can return requested envelopes without
  rebuilding the full lookup. Cache misses still fall back to the full lookup;
  source-specific miss builders remain the next optimization.
- 2026-06-25: Task 4 cold-miss path advanced. Structured human
  `/lookup/sections` misses for `publications` now build only ClinVar, PubMed,
  and LitVar2 publication sources; misses for `therapies_trials` build only the
  ClinicalTrials.gov section. Computational deep dive and ClinGen/VCEP still use
  the full-lookup compatibility fallback until their broader evidence
  dependencies are split safely.
- 2026-06-25: Task 4 direction updated and table slice implemented locally.
  The prepared shell/section proof originally used `variant_cache.publication_data`
  to avoid schema risk; that is now a compatibility fallback, not the target
  architecture. The backend now creates explicit local tables for
  `normalized_variant`, `report_shell_cache`, `report_section_cache`,
  `source_result_cache`, and `section_hydration_status`; `LookupService` reads
  table-backed prepared shells/sections first and writes source-result rows for
  report cacheable provider calls. No Supabase migration, deploy, or remote data
  mutation has been run.
- 2026-06-25: Task 4 cold-miss split completed locally for the current report
  sections. `computational_deep_dive` misses now build only the computational
  source lane, and `clingen_vcep` misses build only ClinVar/ClinGen source
  lanes before assembling the section envelope. Cached `source_result_cache`
  rows are reused before provider calls, and built section envelopes persist
  into `report_section_cache`.
- 2026-06-25: Vault Forj data-architecture standard reviewed and folded into
  EAMOS as the DuckDB/Parquet analytical lane. Phase 0 adds a disabled-by-default
  read-only DuckDB adapter and sanitized health. The ADR resolves the open Gold
  decision: materialized Gold joins sit beside tabix/SQLite first; they do not
  replace point-lookup adapters without later benchmark proof.
- 2026-06-25: Task 5/architecture-gate evidence advanced. The report performance
  audit script now supports repeated cold/warm runs, aggregate p50/p95 latency
  summaries, JSON evidence, and optional payload-size ceilings for lookup
  responses, report payloads, section envelopes, and section payloads.
- 2026-06-25: Task E test-hygiene gate advanced. `tests/test_report_cache_contract.py`
  is now the fast named report-cache contract target, while slower
  integration-style cases in `tests/test_variant_cache.py` are marked `slow`
  and can be excluded with `-m "not slow"`.
- 2026-06-26: Task E live read-only evidence captured after pushing the local
  Task D/E commits. ABCA4/RPE65/USH2A repeated audit recorded cold/warm p50/p95,
  payload ceilings, desktop preflight, no first-paint `/api/v1/viewer` fetch,
  fast test target timings, and Render peak RSS of 641.9 MB (31.3% of the 2 GB
  cap). Evidence is in
  `docs/architecture-consistency-gate/task-e-performance-memory-evidence.md`.
  Production closeout still needs deploy-approved rerun because live
  `/lookup/sections` still rejects `therapies_trials`.
- 2026-06-27: Task E production closeout captured after deploying `a3a7293` to
  Render SG (`dep-d8vpgternols73e040kg`). ABCA4/RPE65/USH2A repeated audit had
  zero payload-threshold violations; `therapies_trials` returned HTTP 200 and
  `available` for all three variants; desktop preflight passed at 1280 px with
  no forbidden first-paint `/api/v1/viewer` request; Render peak RSS was
  639.6 MB (29.8% of the 2 GB cap).
- 2026-06-26: Task 5 local hardening completed. The existing
  `REPORT_SECTION_REGISTRY` now has a deterministic `--validate-registry`
  preflight mode, backend/FE section statuses accept the canonical UI state
  vocabulary, and lazy sections can render empty/partial/stale/failed registry
  states instead of collapsing non-ready envelopes into generic errors.

## Goal

Make `/report` feel immediate and consistent across genes/variants by separating
the first-page report shell from expensive source hydration, removing duplicate
backend work, and giving every report section a stable loading/empty/error
contract.

The current failure mode is architectural, not a single slow provider:

- `/api/v1/lookup`, `/api/v1/lookup/summary`, and `/api/v1/lookup/sections`
  all enter the monolithic `LookupService.lookup()` path.
- `LazySection` fetches can still cost several seconds because the section
  route rebuilds the full lookup before extracting one envelope.
- `ReportGeneViewer` can fire a separate `/api/v1/viewer` request even when the
  lookup response already contains a usable `gene_context_snapshot`.
- Publications, clinical trials, computational predictors, and gene/protein
  viewer data have inconsistent critical-path behavior and inconsistent
  skeleton/empty-state handling.

## Non-Goals

- Do not deploy or mutate Render/Vercel/Supabase state without Steven's explicit
  deployment instruction.
- Do not add account-role/auth plumbing for predictor/report integration.
- Do not make single-gene fixes. Optimizations must be gene/variant agnostic and
  covered at shared orchestration/rendering boundaries.
- Do not move single-coordinate report lookup off the prepared cache,
  tabix/SQLite, or local-index paths. DuckDB/Parquet are the analytical and
  build lane unless a later benchmark and ADR explicitly change that boundary.

## Current Evidence

Latest deployed read-only audit against `https://eamos-dev-sg.onrender.com`
showed:

- ABCA4 `c.5435T>A`: `/lookup` p50/p95 4955/5409 ms; report payload p95
  55,955 bytes.
- RPE65 `c.260A>G`: `/lookup` p50/p95 4013/4162 ms; report payload p95
  73,929 bytes.
- USH2A `c.2276G>T`: `/lookup` p50/p95 6462/6586 ms; report payload p95
  403,744 bytes.
- `therapies_trials` section fetches are HTTP 200 and `available` for all
  three variants.
- Payload ceilings passed: report payload `<=750000` bytes, section envelope
  `<=200000` bytes, and section payload `<=200000` bytes.

The audit helper lives at `scripts/eamos-report-performance-audit.mjs` and can
be run with:

```powershell
npm --prefix app/web run audit:report-performance -- --variant="ABCA4:c.5435T>A" --variant="RPE65:c.260A>G"
```

For gate evidence, use repeat runs and explicit payload ceilings:

```powershell
npm --prefix app/web run audit:report-performance -- --runs=3 --skip-viewer --max-report-payload-bytes=750000 --max-section-envelope-bytes=200000
```

## Storage and Query Strategy

### Request Path

Use a prepared report/section cache as the first request-path optimization.
This can be backed by Postgres/Supabase for durable multi-instance operation or
by the existing local SQLite cache for single-instance Render operation. The
important contract is section-level prepared JSON keyed by normalized variant
identity and source/schema version, not the specific SQL engine.

Implementation note: the first local table-backed slice is now in code. Remote
Postgres/Supabase DDL is still an operator-gated follow-up; local SQLAlchemy
table creation is enough to prove service contracts and keep existing
`variant_cache` rows readable.

Recommended tables:

- `normalized_variant`: canonical gene, transcript/cDNA, protein change,
  genomic coordinate, genome build, and identity/version keys.
- `report_shell_cache`: header, call cards, data-currency summary, required
  section descriptors, and first-paint warnings.
- `report_section_cache`: one row per normalized variant and section id, with
  `status`, `payload_json`, `freshness_json`, `warnings_json`, `schema_version`,
  `source_versions_json`, `generated_at`, and `stale_after`.
- `source_result_cache`: normalized source responses for PubMed, LitVar2,
  ClinicalTrials.gov, ClinGen, gnomAD, VEP/SpliceAI, and predictor artifacts.
- `section_hydration_status`: pending/running/complete/failed state for
  background refresh and UI hydration.

### DuckDB and Parquet

DuckDB/Parquet are now a ratified analytical lane, aligned to the vault Forj
standard and recorded in `docs/data-architecture-duckdb-parquet/adr.md`:

- batch QA over local sources;
- building compact report-section artifacts;
- source freshness/failure dashboards;
- large columnar scans over ClinVar, gnomAD subsets, PubMed/LitVar indexes, and
  predictor artifacts.

They remain outside the single-coordinate hot path. The phase-0 adapter is
disabled by default, opens read-only when enabled, uses `1500MB` memory,
`threads=2`, and spills to the persistent disk. Gold materialized joins sit
beside tabix/SQLite first and can feed future serving artifacts only where
benchmarks prove they help.

## Section State Contract

Every report section should render a stable slot immediately. Backend envelopes
and frontend components should share the same state model:

- `ready`: payload is current and renderable.
- `empty`: source was checked and no relevant data exists.
- `partial`: some sources are available and some are missing/stale.
- `hydrating`: cache miss or refresh is running; show skeleton and retry affordance.
- `stale`: stale payload shown while refresh failed or is pending.
- `failed`: source failed and no usable payload exists.
- `unsupported`: section is not applicable for the variant class.

Frontend should move from ad hoc section checks to a shared
`REPORT_SECTION_REGISTRY` that defines:

- section id and display label;
- critical, eager, lazy, or background load policy;
- skeleton component;
- empty, partial, stale, and failed copy;
- source dependencies;
- export behavior.

## Tasks

### Task 1 - Stop Duplicate Viewer Fetch When Lookup Snapshot Is Usable

Goal: remove the extra `/api/v1/viewer` request from the normal report path
when `report_profile.gene_context_snapshot` already has enough data to render.

Context: `ReportGeneViewer` adapts `geneContextSnapshot` synchronously, then
still fetches `/viewer` unless `initialData` or demo mode short-circuits.

Relevant files:

- `app/web/components/report/ReportGeneViewer.tsx`
- `app/web/components/report/ReportClient.tsx`
- `scripts/eamos-report-performance-audit.mjs`

Proposed approach:

- Treat seeded gene-context snapshot data as the first-class report view.
- Only fetch `/viewer` when no seeded data exists or when an explicitly requested
  track, such as AlphaMissense heatmap, is unavailable in the seeded payload.
- Keep the existing error fallback for variants without seeded data.

Acceptance criteria:

- A report with `gene_context_snapshot` renders the gene/protein view without an
  immediate `/api/v1/viewer` network request.
- Toggling a track that requires live viewer data can still fetch the viewer.
- The visual fallback/error state for variants without seeded data is unchanged.

Verify:

- `npm --prefix app/web run lint`
- Browser/network verification on an ABCA4 or RPE65 report after a local web
  server is available.

### Task 2 - Add Server-Side Timing and Payload Diagnostics

Status: COMPLETE LOCALLY - 2026-06-25 - Codex.

Goal: make backend source latency visible before refactoring the orchestrator.

Context: current live timings identify slow endpoints but not per-source backend
contributors. `LookupService` has `timed_call` helper usage for some sources,
but there is no durable report-level timing contract.

Relevant files:

- `app/backend/app/services/lookup_service.py`
- `app/backend/app/api/routes/lookup.py`
- `scripts/eamos-report-performance-audit.mjs`

Proposed approach:

- Add sanitized per-source timing data behind an environment-gated response
  header or debug field.
- Preserve default public response shape unless the debug gate is enabled.
- Extend the audit script to collect the timing header when present.

Acceptance criteria:

- No default public contract changes.
- Debug-enabled local runs identify slow lookup phases and providers.
- Timing failures never fail the report request.

Verify:

- focused backend tests for debug-off/default behavior;
- `npm --prefix app/web run audit:report-performance -- --skip-viewer` against
  the selected environment.

Evidence:

- Added `lookup_timing.py`, `LOOKUP_TIMING_DIAGNOSTICS_ENABLED`, private
  non-serialized timing slots on lookup response models, and route-level
  `X-Eamos-Lookup-Timing` attachment.
- `LookupService.lookup()` now records major orchestration phases and provider
  timings through the central source wrapper; header data is sanitized and
  bounded.
- `scripts/eamos-report-performance-audit.mjs` now captures and summarizes the
  timing header when present.

### Task 3 - Introduce Prepared Report Shell Contract

Status: STARTED / PREPARED-HIT PATH COMPLETE + PUBLICATIONS/TRIALS COLD-MISS
BUILDERS - 2026-06-25 - Codex.

Goal: make `/lookup/summary` cheap and suitable for first paint.

Context: the summary endpoint currently returns a small response but still
builds a full `LookupResponse`.

Relevant files:

- `app/backend/app/api/routes/lookup.py`
- `app/backend/app/services/lookup_sections.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/schemas/lookup.py`
- `app/backend/tests/test_lookup_section_fetch_contract.py`

Proposed approach:

- Add a `lookup_summary()` service method that resolves identity and reads or
  builds only the shell fields needed for the summary response.
- If no prepared shell exists, return a valid shell with `hydrating` section
  descriptors and schedule/build heavier sections outside first paint.
- Add a test that `/lookup/summary` does not call the full `lookup()` method
  when a prepared shell is available.

Acceptance criteria:

- `/lookup/summary` no longer depends on publications, clinical trials, viewer,
  or full report profile hydration.
- Summary response keeps existing frontend fields.
- Missing shell data degrades to explicit hydrating/missing states, not blank UI.

Verify:

- `pytest app/backend/tests/test_lookup_section_fetch_contract.py`
- live/local audit shows summary latency separated from full lookup latency.

Evidence:

- Full lookups write a versioned `report_shell` into existing variant-cache
  `publication_data` JSON, mirrored through local and Supabase-local-model cache
  repositories.
- `/lookup/summary` now calls `LookupService.lookup_summary()` instead of
  calling `lookup()` in the route. Warm prepared shell hits return the cached
  summary response without provider calls; misses still fall back to full lookup.
- Tests prove the route does not call `lookup()` directly and a warm prepared
  shell does not re-enter provider tools.

### Task 4 - Make `/lookup/sections` a True Section Endpoint

Status: COMPLETE LOCALLY FOR CURRENT SECTIONS - 2026-06-25 - Codex.

Goal: fetch requested section envelopes without rebuilding unrelated sections.

Context: `/lookup/sections` currently calls full lookup and then extracts the
requested envelope.

Relevant files:

- `app/backend/app/api/routes/lookup.py`
- `app/backend/app/services/lookup_sections.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/core/db.py`
- backend repository/cache modules for variant and source cache.

Proposed approach:

- Add a section cache repository and service method keyed by normalized variant
  identity, section id, schema version, and source versions.
- Serve cached section envelopes directly when fresh.
- On miss, build only the requested section if possible; otherwise return
  `hydrating` with explicit warnings.
- Keep multi-section include support and `therapies_trials` compatibility.

Acceptance criteria:

- Fetching `publications` does not build viewer/gene context.
- Fetching `therapies_trials` does not build publications or computational
  deep dive.
- Section envelopes include consistent freshness and warning data.

Verify:

- backend contract tests for each section id;
- audit script confirms single-section calls no longer track full lookup latency.

Evidence:

- Full lookups write versioned lazy section envelopes into table-backed
  `report_section_cache`, with the existing variant-cache `publication_data`
  JSON retained as a compatibility fallback for rows created before the table
  path existed.
- `/lookup/sections` now calls `LookupService.lookup_sections()` instead of
  calling `lookup()` in the route. Warm prepared section hits return only the
  requested envelopes without provider calls.
- Cold structured misses for `publications` now run only the publication source
  path (ClinVar/PubMed/LitVar2) and return the same section envelope shape.
- Cold structured misses for `therapies_trials` now run only the ClinicalTrials
  source path and return the same section envelope shape.
- Cold structured misses for `computational_deep_dive` now use cached
  `computational_annotations` and optional `spliceai` source-result rows when
  present, otherwise building only the computational source lane needed for the
  section.
- Cold structured misses for `clingen_vcep` now use cached or newly built
  ClinVar/ClinGen rows and assemble clinical consensus/VCEP status without
  rebuilding publications, trials, viewer, or unrelated computational sections.
- The local schema now includes the planned report serving tables:
  `normalized_variant`, `report_shell_cache`, `report_section_cache`,
  `source_result_cache`, and `section_hydration_status`. Focused tests prove
  prepared hits still work after removing the legacy JSON prepared payload from
  `variant_cache.publication_data`.
- Focused tests prove computational and ClinGen/VCEP misses do not call the
  full lookup or unrelated source tools, and that their source/section cache
  rows are persisted.

### Task 5 - Frontend Section Registry and Stable Skeletons

Status: COMPLETE LOCALLY FOR DESKTOP SLOT/STATE/PREFLIGHT HARDENING -
2026-06-26 - Codex.

Goal: make every report section appear in a predictable order with consistent
loading, empty, partial, failed, and stale states.

Context: `LazySection` is generic and one-shot, and some sections can disappear
when payloads are empty.

Relevant files:

- `app/web/components/report/ReportClient.tsx`
- `app/web/components/report/LazySection.tsx`
- `app/web/components/report/TrialsSection.tsx`
- `app/web/components/report/PubMedSection.tsx`
- `app/web/components/report/CalibratedInSilicoTable.tsx`
- `app/web/lib/backend.ts`

Proposed approach:

- Add a shared frontend section registry mirroring backend section ids and load
  policies.
- Replace generic fallback copy with section-specific skeletons and empty/error
  states.
- Ensure publications, clinical trials, computational tools, ClinGen/VCEP, and
  gene/protein view always have visible state.

Acceptance criteria:

- No report section silently vanishes because a payload is empty or delayed.
- ABCA4, RPE65, and USH2A reports use the same section order and state model.
- Desktop report layouts keep stable section slots during hydration.
- Mobile/sub-desktop overflow and stability gates are inactive until Steven
  explicitly reactivates them.

Evidence:

- `app/web/lib/report-section-registry.json` is the seven-section desktop
  registry for required slots, anchors, lazy contracts, and empty/partial/
  stale/failed copy.
- `app/web/lib/report-section-registry.ts` normalizes section envelopes into
  stable UI states.
- `LazySection` supports empty and registry-state fallback rendering for
  non-ready section envelopes.
- `scripts/eamos-report-preflight.mjs --validate-registry --json` passes and
  normal preflight includes the same registry validation as a failure gate.

Verify:

- `npm --prefix app/web run lint`
- browser verification at desktop widths only;
- report preflight asserts required section slots before data hydration finishes;
- report performance audit records repeated cold/warm p50/p95 and payload-size
  ceilings for the selected variants.

### Task 6 - Materialize Publications and Clinical Trials

Status: NEXT DATA LANE AFTER TABLE CACHE CONTRACT - 2026-06-25 - Codex.

Goal: remove PubMed/LitVar2 and ClinicalTrials.gov live calls from first paint.

Context: PubMed local DB and literature embeddings were not ready in live cache
health, and clinical trials had only a tiny source-cache footprint.

Relevant files:

- `app/backend/app/services/publication_literature.py`
- `app/backend/app/services/pubmed_local.py`
- `app/backend/app/tools/clinical_trials.py`
- `docs/pubmed-local/`
- `docs/pubmed-corpus-materialization/`

Proposed approach:

- Restore/build local PubMed materialization and report-section summaries.
- Add clinical-trials materialization by gene/disease/variant query lane.
- Put live API refresh behind explicit refresh/background hydration, not first
  paint.

Acceptance criteria:

- Publications section can render variant/gene counts from local materialized
  data.
- Clinical trials section can render empty/available/hydrating states without
  serial live HTTP calls.
- Live refresh failures show stale or unavailable states with provenance.

Verify:

- local provider-cache health;
- audit script for RPE65, ABCA4, and USH2A;
- backend unit tests for no-row vs missing clinical trial payloads.

### Task 7 - DuckDB/Parquet Analytical Build Pipeline

Status: PHASE 0 ADAPTER IMPLEMENTED LOCALLY; MATERIALIZATION PLANNED - 2026-06-25
- Codex.

Goal: implement the ratified analytical lane for bulk, regional, and reporting
workloads while keeping single-coordinate lookup on prepared cache plus
tabix/SQLite/local indexes.

Context: Eamos has large local evidence assets where columnar analytics can
help build compact serving tables.

Relevant files:

- `docs/data-architecture-duckdb-parquet/adr.md`
- `docs/data-architecture-duckdb-parquet/plan.md`
- `app/backend/app/services/duckdb_analytical.py`
- `app/backend/app/api/routes/health.py`
- `app/backend/app/core/config.py`
- `docs/local-first-data-source-strategy/`
- materialization scripts under `scripts/` and `app/backend/`
- source registry/config docs.

Proposed approach:

- Keep the embedded DuckDB adapter disabled by default and expose only sanitized
  health until a local artifact is present.
- Define Silver/Gold Parquet release layout and manifests.
- Materialize dbSNP, ClinVar, and predictor Silver tables to chrom-partitioned,
  position-sorted zstd Parquet through DuckDB/Polars/Snakemake.
- Materialize coordinate-sorted Gold joins beside the existing tabix/SQLite
  adapters.
- Benchmark Gold reads against tabix/SQLite/report cache before any serving-path
  expansion.

Acceptance criteria:

- Provider-cache health reports disabled/missing/ready states without exposing
  local paths.
- Tiny fixture release validates without multi-GB assets.
- Benchmark result documents the winning engine for point lookup, 1k-variant
  batch, region aggregation, and reporting scans.
- Gold joins do not replace tabix/SQLite unless a later ADR changes that
  boundary.

Verify:

- `python -m pytest tests/test_duckdb_analytical.py tests/test_health_api.py -q`
- reproducible benchmark/preflight command and output when Phase 1 lands;
- no lookup route dependency on DuckDB unless separately approved.

### Task 8 - Operator-Gated Deployment and Data Refresh

Goal: leave environment-specific and account-specific actions until last.

Requires Steven-specific approval or environment access:

- Render deploys and environment mutations.
- Vercel project commands.
- Supabase schema migrations or remote data mutations.
- Multi-GB artifact syncs or semantic graphify passes.
- Production PubMed/clinical-trials materialization jobs.

Acceptance criteria:

- All local code/tests/docs are ready before requesting operator action.
- The final deployment checklist names exact commands, expected effects, and
  rollback.
