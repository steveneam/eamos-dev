# Eamos repo structure plan

Status: foundation ratchet active.
Created: 2026-06-30 by Codex.
Reference model: Selom `docs/repo-structure/plan.md` and AI helper/DCPS notes.

## Decision

Adopt the Selom rule: split on responsibility, not on a hard line count.

A cohesive 900-line module can stay whole. A 250-line file that mixes routing,
validation, persistence, provider IO, and UI state should be split. The rule is
enforced by tests where possible, not by memory or chat convention alone.

Rejected for Eamos:

- A blanket `src/` move. The backend already has an `app` package and the
  churn would touch imports, tests, deployment, and docs without changing the
  product boundary.
- A hard 150-line cap. Eamos has generated contracts, schemas, provider
  adapters, and fixtures where line count alone is a bad signal.
- Barrel `index.ts` hubs. They make imports less explicit and can reintroduce
  eager import problems in the web app.

## Current structure truth

Backend route structure is already in good shape:

- `app/backend/app/main.py` is the FastAPI composition root.
- Domain routes live under `app/backend/app/api/routes`.
- `app/backend/app/api/routes/__init__.py` builds the aggregate router.
- There are no `@app.get` / `@app.post` route handlers in `main.py`.

The largest current responsibility hotspots from the 2026-06-30 audit are:

| File | Lines | Why it matters |
| --- | ---: | --- |
| `app/web/components/workbench/workbench.css` | 4028 | Multiple Workbench tool style domains in one global sheet. |
| `app/backend/app/services/gene_viewer.py` | 3497 | Fixture provider, live source client, transcript projection, full-locus geometry, protein tracks, and allele display in one module. |
| `app/backend/app/services/pubmed_local.py` | 2978 | Store, schema, XML/JSONL parsing, materialization, coverage, search, and manifest logic in one module. Folded 2026-07-02 into a facade plus constants, models, license policy, and parser/source helpers. |
| `app/backend/app/services/lookup_service.py` | 2890 | Cache identity, source hydration, report shell/sections cache, evidence summaries, and orchestration in one module. First fold 2026-07-02 extracted cache codecs, ClinVar distribution runtime helpers, and shared utility helpers behind the existing facade. |
| `app/backend/app/services/workbench_design.py` | 2206 | Primer providers, SNP masking, isPcr, alignment, trace parsing, disclosure, and service orchestration in one module. Folded 2026-07-02 into a facade plus common, protocols, fixture, primer, alignment, and service modules. |
| `app/backend/app/services/clinvar_local.py` | 2091 | Runtime adapter plus generated gene-distribution materializer/index code. |
| `app/web/components/report/ReportGeneViewer.tsx` | 2487 | Report-specific viewer UI plus viewer state, adaptation, controls, and rendering. |

These are the refactor targets. Generated lockfiles, generated JSON fixtures,
contract mirrors, and historical plans are not structure problems by themselves.

## Durable conventions

### Backend

- Routes stay in `app/backend/app/api/routes/<domain>.py` as `APIRouter`
  modules. `main.py` wires app state and includes the aggregate API router; it
  does not define HTTP handlers.
- New backend domains get a route module, a schema module, and a service/repo
  module as needed. Do not add unrelated helpers to an existing large service
  just because it is nearby.
- Split service modules when they hold multiple engines. Preserve public import
  paths with a package `__init__.py` shim during migrations so route/schema tests
  catch contract drift.
- AI code follows the deterministic-core/probabilistic-shell pattern: LLMs may
  parse, rank, or propose typed payloads; deterministic validators and services
  decide what runs or mutates state.
- Provider/license/provenance/launch-gate metadata stays with predictor rows,
  health output, and preflight output during any split.

### Frontend

- Feature modules live in feature folders. Avoid adding flat `*-api.ts` modules
  under `app/web/lib` or `app/frontend/src/lib`; use `lib/<feature>/api.ts`
  when a feature endpoint layer grows.
- No `index.ts` barrel hubs under frontend `lib` directories.
- Heavy browser libraries must be dynamically imported from browser-only code.
  Do not add static top-level imports for WebGL, plotting, PDF, or editor
  packages.
- Large components should be split by state/behavior boundaries first:
  orchestration hooks, pure adapters, table/detail subcomponents, and CSS blocks
  per tool. Do not shard a presentational component solely to satisfy a number.
- The active Next app is `app/web`; `app/frontend` is a frozen historical Vite
  reference. Do not mirror new product work into `app/frontend`.

### Docs

- This file is the single home for structure policy.
- `docs/README.md` remains the broad docs index.
- Completed records belong in the appropriate records/archive location rather
  than live planning docs.

## Enforcement

`app/backend/tests/test_structure_guard.py` is the current ratchet. It checks:

- `main.py` has no `@app.<method>` handlers and includes `build_api_router()`.
- Backend route modules use `APIRouter`.
- Frontend `lib` folders do not grow barrel `index.ts` hubs.
- Frontend `lib` folders do not add flat `*-api.ts` feature modules.
- Known heavy browser libraries are not statically imported in web/frontend
  TypeScript.
- Active frontend source-of-truth docs do not describe `app/frontend` or Vite
  as the live product app unless the document is explicitly superseded/frozen.
- Current oversized hotspots have fixed line budgets so future work cannot
  keep expanding them silently.

The budgets are not a style cap for the whole repo. They are a tripwire on
known files that need deliberate package/hook/CSS splits.

## Refactor sequence

### R0 - Foundation ratchet

Done in this pass:

- Add this structure plan.
- Add the structure guard test.
- Follow-up cleanup: `app/backend/app/services/protein_annotation.py` has been
  split by responsibility into:
  - `protein_annotation.py` for service orchestration, HMMER runtime, Pfam parse,
    normalization, cache behavior, and runtime path helpers.
  - `protein_uniprot_features.py` for UniProt flatfile parsing, feature index
    scan/build helpers, labels, descriptions, and lane mapping.
  - `protein_feature_projection.py` for bundled feature seeds and conversion
    from `ProteinDomainTrack` into viewer `ProteinFeatures`.
- Follow-up cleanup: `app/frontend` has been quarantined as a frozen historical
  Vite reference, active docs now point at `app/web`, and the structure guard
  includes a docs drift guard.
- Follow-up cleanup: the first Search Control Plane slice has been wired:
  `create_app()` constructs search services, `/api/v1/search` uses an explicit
  search rate limit, and run creation indexes newly created runs.
- Follow-up cleanup: Search Control Plane Tasks 4-5 are implemented for the
  current run/report index. Private rows are owner-filtered, ownerless private
  rows fail closed until backfilled, provider-cache health reports search
  readiness, and `eamos_search_index_backfill` provides dry-run-first rebuilds.
- Follow-up cleanup: Search Control Plane Task 6 has its first non-run/report
  workspace slice. Saved variant-library rows now index as owner-scoped private
  `library_variant` documents on save, bulk save, whole-library replace, and
  delete. Public/source-backed product entities remain open.
- Wave 3 data asset policy is now active in
  `docs/repo-structure/source-asset-policy.md`. The structure guard requires
  tracked files under `app/backend/data/source_assets` to live under registered
  source ids and to carry `.manifest.json` sidecars.
- Wave 4 `gene_viewer.py` fold is now a compatibility facade plus service and
  fixture provider. Source-backed models, source client, source provider,
  protein/AlphaMissense track hydration, fixture records, full-locus renderer,
  transcript-window renderer, shared errors, variants, and utilities live in
  dedicated modules. The public `app.services.gene_viewer` import surface is
  preserved and covered by a focused facade import test.
- Wave 4 `workbench_design.py` fold is now a compatibility facade. Shared
  constants/errors, protocols, fixture loading, primer/SNP/isPcr providers,
  Sanger alignment/AB1 parsing, and service orchestration live in focused
  `workbench_design_*` modules. Existing route/import behavior is preserved.
- Wave 4 `pubmed_local.py` fold now separates constants, dataclass models,
  license policy, and XML/JSONL/source-manifest/seed/domain parsing helpers
  from the SQLite store/materialization/search facade. PubMed launch posture is
  unchanged: no startup materialization, provider flip, source download, or
  runtime seed/sync.
- Wave 4 `lookup_service.py` first fold now keeps the public import surface as
  a compatibility facade while cache schema versions/codecs, source-result cache
  conversion, ClinVar gene-distribution runtime gating, and shared text helpers
  live in focused `lookup_service_*` modules. The main service remains the next
  measured optimization target because source-cache orchestration and full
  report-payload assembly still live inside `lookup()`.

Verification:

- `cd app/backend; python -m pytest tests/test_structure_guard.py -q`
- `cd app/backend; python -m pytest tests/test_protein_annotation_service.py tests/test_pfam_materialization_cli.py tests/test_structure_guard.py -q`
- `cd app/backend; python -m pytest tests/test_search_api_local.py tests/test_search_api.py tests/test_rate_limits.py tests/test_structure_guard.py -q`
- `cd app/backend; python -m pytest tests/test_gene_viewer.py tests/test_workbench_api.py -q`

Current protein-annotation line-count ratchet:

- `app/backend/app/services/protein_annotation.py`: budget 1000 lines; current
  post-format count is 898.

Current gene-viewer line-count ratchets:

- `app/backend/app/services/gene_viewer.py`: budget 500 lines; current
  post-format facade count is about 330.
- Split `gene_viewer_*` modules have their own budgets in
  `tests/test_structure_guard.py` so the provider/protein/source-client/window
  responsibilities cannot silently collapse back into the facade.
- Split `workbench_design_*` and `pubmed_local_*` modules have their own
  budgets in `tests/test_structure_guard.py`; the old monolith budgets have
  been replaced by facade/module budgets.
- Split `lookup_service_*` modules have their own budgets in
  `tests/test_structure_guard.py`; `lookup_service.py` is ratcheted below the
  pre-fold monolith size and the facade import surface is covered by a focused
  structure test.

### R1 - Gene viewer package fold

Target: `app/backend/app/services/gene_viewer.py`.

Search Wave 2 has its first wiring slice complete. Continue remaining search
work from `docs/search-index/spec.md` and `docs/search-index/plan.md`, starting
with public/source-backed Task 6 breadth, approve/drop/report-payload refresh
hooks, and later frontend results integration.

Follow-up update, 2026-06-30:

- First slice done: source-backed transcript models/protocols now live in
  `gene_viewer_models.py`; `gene_viewer.py` re-imports them to preserve existing
  tests and external imports.
- Follow-up slice done, 2026-07-01: source client, shared errors, variant
  projection, transcript window rendering, fixture-record conversion,
  full-locus/full-gene rendering, and small utility helpers now live in focused
  modules. The public `app.services.gene_viewer` facade still re-exports the
  existing service/provider/model names.
- Follow-up slice done, 2026-07-01: `SourceBackedGeneViewerProvider` now lives
  in `gene_viewer_source_provider.py`, and protein-domain plus AlphaMissense
  hydration helpers live in `gene_viewer_protein_tracks.py`. The facade is
  ratcheted at 500 lines and the new public import-surface test locks the
  compatibility behavior.

Proposed package:

```text
app/backend/app/services/gene_viewer/
  __init__.py              # re-export existing public imports
  service.py               # GeneViewerService and top-level service errors
  source_client.py         # HttpGeneViewerSourceClient and source fetch logic
  source_models.py         # SourceTranscript*, SourceBackedViewerBundle
  source_provider.py       # SourceBackedGeneViewerProvider
  fixture_provider.py      # fixture provider and curated fixture conversion
  full_locus.py            # full-gene/full-locus geometry and coordinate maps
  transcript_window.py     # TranscriptWindowBuilder and allele display operations
  protein_tracks.py        # protein/AlphaMissense hydration helpers
  utils.py                 # small sequence/id helpers only
```

Contract:

- Preserve `from app.services.gene_viewer import GeneViewerService, ...`.
- Run `tests/test_gene_viewer.py`, `tests/test_workbench_api.py`, and focused
  report/viewer tests before and after.
- No source downloads, provider flips, or fixture rewrites.

Next backend package-fold priority should move to `lookup_service.py` unless
new gene-viewer behavior requires another targeted split.

### R2 - Workbench CSS and design split

Targets:

- `app/web/components/workbench/workbench.css`
- `app/backend/app/services/workbench_design.py`

CSS should split by tool block only when the import path and Next global-CSS
constraints are confirmed. Candidate files:

```text
components/workbench/workbench.css         # tokens, shell, common controls
components/workbench/align/align.css
components/workbench/crispr/crispr.css
components/workbench/primer/primer.css
components/workbench/viewer/viewer.css
```

Backend design package candidate:

```text
app/backend/app/services/workbench_design.py              # compatibility facade
app/backend/app/services/workbench_design_common.py       # constants/errors/shared helpers
app/backend/app/services/workbench_design_protocols.py    # provider protocols
app/backend/app/services/workbench_design_fixture.py      # fixture provider
app/backend/app/services/workbench_design_primer.py       # Primer3, SNP masking, isPcr
app/backend/app/services/workbench_design_alignment.py    # Sanger alignment + AB1 parsing
app/backend/app/services/workbench_design_service.py      # WorkbenchDesignService orchestration
```

Backend split status: done 2026-07-02. Frontend Workbench CSS remains open and
is still Claude/frontend-lane work unless Steven redirects.

### R3 - PubMed local package fold

Target: `app/backend/app/services/pubmed_local.py`.

Split by store/materialization/search/parser boundaries:

```text
app/backend/app/services/pubmed_local.py                 # compatibility facade, store/materialization/search
app/backend/app/services/pubmed_local_constants.py       # constants/source policy markers
app/backend/app/services/pubmed_local_models.py          # dataclasses/schema error
app/backend/app/services/pubmed_local_license_policy.py  # license/profile text policy
app/backend/app/services/pubmed_local_parsing.py         # XML/JSONL/source manifest/seed/domain helpers
```

Keep launch posture unchanged: PubMed remains API/cache unless separately
approved.

First backend split status: done 2026-07-02. Further split of SQLite schema,
store, coverage, search, and materialization internals can happen later if this
facade starts growing again, but the largest parser/policy mix has been pulled
out and guarded.

### R4 - Lookup orchestration split

Target: `app/backend/app/services/lookup_service.py`.

Split only after the current launch verification work is closed. Candidate
modules:

```text
lookup/
  __init__.py
  service.py
  cache_identity.py
  report_shell_cache.py
  section_cache.py
  source_hydration.py
  evidence_context.py
  trial_summaries.py
```

This is high blast-radius because it touches report, cache, lazy sections, and
variant-library behavior.

First fold status: started 2026-07-02. The cache/ClinVar helper extraction is
complete and guarded. Next safe lookup slices should be measured against lookup
timing diagnostics and should target source-cache orchestration inside
`lookup()`, publication/trial section builders, and report-payload assembly
without changing route contracts or source/provider posture.

### R5 - Report and Compare frontend decomposition

Targets:

- `app/web/components/report/ReportGeneViewer.tsx`
- `app/web/components/report/PopulationFrequencySection.tsx`
- `app/web/components/report/ReportClient.tsx`
- `app/web/components/compare/CompareClient.tsx`
- `app/web/components/paper/PaperClient.tsx`

Preferred extraction order:

1. Pure adapters and formatting helpers.
2. Hooks for state machines.
3. Repeated row/card subcomponents.
4. CSS only after behavior is stable.

## What not to do

- Do not run a broad formatter across backend/frontend just to make files look
  different.
- Do not move generated contract mirrors by hand.
- Do not create barrel files to hide long import paths.
- Do not start the package folds during a launch/browser-proof task unless the
  fold is the explicit assigned task.
- Do not treat fixture size as a runtime architecture smell unless the fixture
  is eagerly imported into a user-facing path.
