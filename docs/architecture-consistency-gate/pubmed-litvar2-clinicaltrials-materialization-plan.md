# PubMed, LitVar2, and ClinicalTrials Materialization Plan

Last updated: 2026-06-27 19:22 +1000 - Codex.

Status: planning plus local tiny-fixture, cache-snapshot, and benchmark-contract
gates. No real
PubMed, LitVar2, PubTator, ClinicalTrials, Supabase, Render, or Storage
materialization was run for this task; PMAT-002 and PMAT-003 only exercise
temporary pytest SQLite fixtures from checked-in source fixtures plus generated
edge files, PMAT-004 only exercises local report/source cache rows, and PMAT-005
only benchmarks the checked-in tiny fixture slice.

## Purpose

Define the next operator-gated materialization lane for the literature and
therapies/trials report surfaces without weakening the existing architecture
guardrails:

- no startup, deploy-time, or request-time source downloads;
- no single-coordinate lookup migration away from prepared cache/tabix/SQLite;
- no Supabase Storage/schema mutation without explicit approval;
- no promotion of proof or cache-derived PubMed artifacts to production;
- PubMed citations, PMC full text, LitVar/PubTator edges, and ClinicalTrials
  snapshots remain separate source lanes with separate license/provenance gates.

## Current Local Surfaces

The existing code already provides these building blocks:

- `app/backend/app/cli/eamos_pubmed_local_materialize.py` builds a local
  PubMed SQLite source asset from operator-staged XML, JSONL, PubTator edge
  JSONL, LitVar edge JSONL, and PMC OA license metadata. It explicitly reports
  no network use and no startup/request-time materialization.
- `app/backend/app/services/pubmed_local.py` owns the SQLite schema,
  license-gated abstract persistence, source-file manifests, checksum
  inspection, source-kind import stats, PubMed coverage rows, and read-only
  local search.
- `app/backend/app/cli/eamos_pubmed_litvar_edges.py` converts
  operator-staged LitVar/LitVar2 exports into `pubmed_literature_edge` JSONL
  without network or source DB mutation.
- `app/backend/app/cli/eamos_pubmed_pubtator_edges.py` converts
  operator-staged PubTator flat files into edge JSONL without network or source
  DB mutation.
- `app/backend/app/tools/litvar2.py` remains the live LitVar2 lookup path and
  hydrates bounded PubMed metadata only when live APIs are enabled.
- `app/backend/app/tools/clinical_trials.py` remains the live/fixture
  ClinicalTrials.gov v2 path. It builds variant/gene/disease query lanes,
  filters active/not-yet statuses, and returns discovery rows through the
  therapies/trials report section.
- Health and build-ledger surfaces already expose PubMed-local readiness, and
  source-result/report-section caches already cover report replay behavior.

## Source-Lane Model

Use four distinct lanes:

| Lane | Durable input | Derived artifact | Runtime surface | Gate |
| --- | --- | --- | --- | --- |
| PubMed citations | annual baseline/update XML plus checksum sidecars | `pubmed-local.sqlite` and manifest | PubMed local adapter, publications section, literature RAG seed | corpus scope, license, checksum, benchmark |
| PMC licenses/text | PMC OA license metadata first; full text later only if approved | license overlay and optional licensed text features | abstract policy, RAG eligibility | article-level license approval |
| LitVar/PubTator edges | operator-staged exports or selector files | edge JSONL imported into PubMed-local SQLite | variant PMIDs, snippets, entity joins | seed-match and orphan-edge checks |
| ClinicalTrials | ClinicalTrials.gov v2 JSON snapshots by approved query plan | normalized trial snapshot or source-result cache rows | therapies/trials section | freshness, status filter, disclaimer, cache staleness |

Supabase Postgres should own metadata, manifests, source-version rows, cache
references, and job status. Private Storage can hold generated source assets
after approval. Render disk should hold only the current runtime SQLite/cache
subset needed by the backend.

## PubMed And Edge Materialization Sequence

1. Freeze a seed manifest.

   Record the Eamos gene/variant/query cohort, intended corpus scope
   (`targeted_seed`, `filtered_pubmed`, or another approved label), source
   release labels, and exclusion policy. Store normalized seed terms only; do
   not include patient notes, request headers, prompts, user data, or free-text
   clinical narratives.

2. Run the budget and scope gate.

   Re-run the official listing budget command before any full or filtered
   PubMed decision because updatefiles change over time:

   ```powershell
   cd app/backend
   python -m app.cli.eamos_pubmed_corpus_budget --fetch-official-listings --compact
   ```

   The output must be reviewed against staging disk, Supabase Storage headroom,
   Render disk headroom, version overlap, rollback, and upload retry behavior.

3. Build a tiny fixture release first.

   Use the existing fixture-oriented tests and CLIs to prove import, license
   overlay, LitVar/PubTator edge import, checksum, preflight, search, and
   sanitized output. This is the only acceptable first execution lane.

4. Convert LitVar/PubTator edges offline.

   Convert operator-staged exports into edge JSONL, then import those JSONL
   files into PubMed-local with the same source-version and source-file
   manifest controls as PubMed XML. Acceptance requires:

   - non-zero edge count for positive fixtures;
   - orphan PMIDs reported and not silently fabricated;
   - edge source, file name, source kind, load order, identifier, mention, and
     relation type preserved;
   - no source paths, seed rows, raw abstracts, object URIs, signed URLs, or
     secrets emitted in reports.

5. Run a bounded representative slice before any real corpus build.

   Measure row counts, licensed abstract count, metadata-only count, literature
   edge count, source-file count, file size, materialization wall time, peak
   RSS, temp disk peak, preflight time, local search p50/p95, and 1k-variant
   batch p50/p95. Do not enable `PUBMED_LOCAL_ENABLED` from this slice unless
   Steven explicitly accepts its partial coverage label.

6. Only then consider generated-asset upload and runtime seeding.

   Uploading generated SQLite/manifest files to private Storage, registering
   metadata rows, syncing to Render disk, or enabling runtime flags all require
   separate approval. File presence is not acceptance; provider-cache and
   report-section health must prove the artifact is ready and sanitized.

## ClinicalTrials Materialization Sequence

ClinicalTrials should not be folded into PubMed-local SQLite by default. It is
a smaller, freshness-sensitive report source with different semantics.

Steven's PMAT-004 loading decision is report-first and cache-backed. The
therapies/trials section must be ready from the initial report payload whenever
a ClinicalTrials snapshot exists, and `/lookup/sections?include=therapies_trials`
must reuse the same cache snapshot when the frontend asks for a section
envelope. A scroll-triggered live ClinicalTrials.gov call is not the normal
serving model; it is a retry/refresh path only.

1. Define a snapshot contract.

   Capture query plan, selected query, active/not-yet status filter,
   ClinicalTrials.gov source URL, retrieved-at time, source API version,
   freshness TTL, row count, and discovery-only disclaimer. Preserve the
   existing `ClinicalTrialMatch` shape for NCT ID, title, status, phase,
   interventions, conditions, locations, match level, warnings, and source URL.

2. Add a tiny offline fixture before live snapshotting.

   The fixture should cover variant-level, gene-level fallback, disease-level
   fallback, no active matches, malformed study payload, and timeout/fallback
   behavior. The existing parser tests are the starting point.

3. Materialize to cache first, not a global corpus table.

   The first production-safe serving model is source-result/report-section
   cache keyed by normalized report input and ClinicalTrials query identity.
   It should render `available`, `empty`, `stale`, `partial`, and `failed`
   section states without making serial live HTTP calls on first paint.

   Local implementation note: `source_result_cache` stores the
   `clinical_trials` tool summary, request identity, source URL, source
   version, freshness, and warnings. Full `/api/v1/lookup` now checks this row
   before calling `ClinicalTrialsTool.get_trial_matches()`, so
   `report_profile.therapies_trials` can ship with the first report payload.
   `/api/v1/lookup/sections` includes `clinical_trials` in its
   source-result cache map and can hydrate the same section without a provider
   call when the cached source row exists.

   Section-state mapping:

   - rows present -> `available`;
   - no active matches with query executions -> `available` with empty
     `trial_rows` and a no-active warning, not a loading skeleton;
   - stale-on-failure freshness -> frontend `stale` state through the section
     envelope freshness block;
   - fetch/fallback warnings -> rendered immediately with warning state/copy;
   - missing tool/cache -> unavailable warning, not request-time download or
     startup materialization.

4. Keep live refresh explicit.

   `refresh=true` may bypass cache for a bounded backend refresh, but no
   request may create a durable global ClinicalTrials corpus unless a separate
   snapshot CLI and approval gate exists.

5. Add a later normalized snapshot only if cache proves insufficient.

   A future `clinical_trials_snapshot` artifact can be justified if repeated
   report traffic needs shared gene/disease snapshots. That decision needs a
   benchmark and freshness policy; it should not block PubMed-local or section
   registry work.

## Acceptance Before Real Materialization

Real materialization remains blocked until all of the following are true:

- seed scope and corpus label are documented;
- budget output is current and reviewed;
- tiny-fixture PubMed-local, LitVar edge, PubTator edge, and ClinicalTrials
  parser/cache tests are green;
- source reports are sanitized and contain no local paths, seed rows, abstracts,
  secrets, object URIs, signed URLs, or user data;
- benchmark output records time, memory, disk, row counts, freshness, and
  lookup latency;
- Supabase production-readiness runbook is complete for any planned remote
  Storage/schema action;
- Steven explicitly approves the exact materialization command, storage
  mutation, registration mutation, or runtime flag change being performed.

## Initial Task Breakdown

### PMAT-001 - Seed Manifest And Scope Decision

Status: implemented locally for the tiny fixture contract. No source download,
materialization, upload, runtime seeding, or runtime flag change was run.

Create a reviewed seed manifest format and a checked-in tiny fixture seed file.
Acceptance: no user/patient/request text; every seed has gene, optional variant
aliases, scope, source rationale, and corpus label.

Evidence:

- `app/backend/app/fixtures/literature/pmat_seed_manifest_tiny.json` records the
  tiny `targeted_seed` fixture for RPE65, ABCA4, and CEP290.
- `app/backend/app/services/pubmed_seed_manifest.py` validates the JSON manifest
  and renders the TSV query shape already consumed by PubMed-local and LitVar2
  edge tooling.
- `python -m app.cli.eamos_pubmed_seed_manifest --manifest-path ... --write-query-file ...`
  validates and writes a seed TSV without network, source download,
  materialization, upload, path leakage, or row leakage in JSON output.
- `app/backend/tests/test_pubmed_seed_manifest.py` covers fixture validity,
  TSV compatibility with `read_seed_queries`, sanitized reporting, and rejection
  of user/patient/request payload fields.

### PMAT-002 - PubMed Local Fixture Gate

Status: implemented locally for the checked-in tiny fixture path. No source
download, upload, runtime seeding, remote mutation, or runtime flag change was
run.

Run and document the existing PubMed-local fixture materialization/preflight
commands. Acceptance: ready SQLite fixture, checksum verified, licensed versus
metadata-only counts recorded, and sanitized output reviewed.

Evidence:

- `app/backend/tests/test_pubmed_seed_manifest.py` now drives the checked-in
  PMAT seed manifest through the existing PubMed-local materializer and
  preflight path using a copied fixture XML and generated MD5 sidecar in a temp
  directory.
- Fixture materialization reports ready SQLite output with `article_count=2`,
  `licensed_abstract_count=1`, `metadata_only_count=1`, `deleted_count=1`,
  `coverage_count=6`, `source_file_count=1`, and verified input checksum
  status.
- Fixture preflight reports ready status, checksum verification, matching
  article/license counts, six coverage queries, and sanitized output with no
  local path values, raw abstracts, or secret values emitted.
- `python -m pytest tests\test_pubmed_seed_manifest.py -q` passed.

### PMAT-003 - LitVar/PubTator Edge Fixture Gate

Status: implemented locally for generated tiny edge fixtures. No source
download, upload, runtime seeding, remote mutation, or runtime flag change was
run.

Run fixture conversion for LitVar and PubTator edges and import the outputs into
the PubMed-local fixture. Acceptance: edge counts and orphan skips recorded,
variant snippets survive EP-VLEx, and no live network is used.

Evidence:

- `app/backend/tests/test_pubmed_seed_manifest.py` now renders the checked-in
  PMAT seed manifest, creates temporary PubTator and LitVar fixture inputs with
  positive and orphan PMIDs, converts them through the existing edge CLIs, and
  imports both generated edge JSONL files into the PubMed-local fixture SQLite
  asset.
- PubTator conversion reports `edge_count=4` with two gene and two variant
  edges, no network use, and sanitized output. The PubMed-local fixture imports
  two PubTator edges and records two orphan-edge skips.
- LitVar conversion reports `record_count=1`, `pmid_count=2`, `edge_count=12`,
  entity counts of two gene, two rsID, and eight variant edges, no network use,
  and sanitized output. The PubMed-local fixture imports six LitVar edges and
  records six orphan-edge skips.
- Combined fixture materialization reports `literature_edge_count=8`,
  `source_file_count=3`, verified PubMed XML checksum status, and source-kind
  counts for one PubMed baseline XML file, one PubTator edge file, and one
  LitVar edge file.
- Fixture preflight reports ready status, `network_used=false`, eight
  literature edges, two PubTator orphan skips, six LitVar orphan skips, and no
  local path or abstract values emitted.
- Local PubMed search returns the edge-backed metadata-only PMID with both
  `pubtator` and `litvar2_snippet` evidence fields, and EP-VLEx returns an
  `exact_variant_snippet` sourced from the PubTator edge text.
- `python -m pytest tests\test_pubmed_seed_manifest.py -q` passed.

### PMAT-004 - ClinicalTrials Cache Snapshot Spec

Status: implemented locally for cache contract and no-second-call behavior. No
ClinicalTrials source download, upload, runtime seeding, remote mutation,
runtime flag change, or deploy was run.

Specify the source-result/report-section cache key, freshness TTL, stale
behavior, retry behavior, and status mapping for therapies/trials. Acceptance:
first paint can show cached/empty/stale/failed section states without serial
live HTTP.

Evidence:

- `LookupService.lookup()` reads a fresh `clinical_trials` source-result cache
  row before calling the live ClinicalTrials tool, and uses that cached summary
  to populate `report_profile.therapies_trials` in the first report payload.
- Structured no-row ClinicalTrials results now render deterministic no-active
  copy without falling through to `get_trials_summary()`, avoiding a second
  ClinicalTrials.gov call in real mode.
- `LookupService.lookup_sections()` maps `therapies_trials` to the
  `clinical_trials` source-result cache and reuses the cached snapshot before
  calling the live provider.
- `app/backend/tests/test_variant_cache.py` covers both paths: full report
  first-payload hydration from cache and therapies/trials section hydration
  from cache, with zero `get_trial_matches()` and zero `get_trials_summary()`
  provider calls.

### PMAT-005 - Bounded Slice Benchmark Plan

Status: implemented locally for the benchmark contract using checked-in tiny
fixtures. No real source download, upload, runtime seeding, remote mutation,
runtime flag change, or deploy was run.

Design the representative slice benchmark before any real source build.
Acceptance: the benchmark captures wall time, RSS, temp disk, output size,
row-count profiles, license profiles, edge profiles, preflight time, lookup
latency, and rollback procedure.

Evidence:

- `python -m app.cli.eamos_pmat_bounded_slice_benchmark --compact --require-ready`
  stages only checked-in PMAT tiny fixtures in a temp directory, converts
  PubTator and LitVar edges, materializes a temporary PubMed-local SQLite asset,
  preflights it, and measures local lookup plus batch-loop latency.
- Benchmark output includes wall-time steps, RSS checkpoints, temp-disk peak,
  generated output sizes, row counts, license counts, edge conversion/import/
  orphan profiles, preflight timing/checksum status, lookup p50/p95, batch
  p50/p95, and rollback procedure.
- The fixture profile records two articles, one licensed abstract, one
  metadata-only article, one deleted citation, six coverage rows, three source
  files, four converted PubTator edges, twelve converted LitVar edges, eight
  imported literature edges, two PubTator orphan skips, and six LitVar orphan
  skips.
- `docs/architecture-consistency-gate/pmat-005-bounded-slice-benchmark.md`
  defines the representative-slice approval gate. A future bounded real slice
  still requires separate approval for the exact operator-staged input set and
  remains separate from upload, registration, runtime seeding, deploy, or flag
  enablement.

## Out Of Scope

- Full PubMed baseline/update materialization.
- PubMed, PMC, LitVar, PubTator, or ClinicalTrials uploads.
- Supabase schema/storage mutation.
- Render runtime seeding or deploy.
- Runtime flag enablement for `PUBMED_LOCAL_ENABLED`, `LOCAL_EVIDENCE_ENABLED`,
  or `RAG_ENABLED`.
- Loading PubMed or PMC full text into Supabase Postgres.
- Drizzle ORM replacement of the Python SQLAlchemy/FastAPI backend ownership.
