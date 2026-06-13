# Workbench Live-Wiring Execution Plan

Status: draft for Steven review. Created 2026-06-11 by Codex.

## Shared Decisions Before Implementation

- Keep production `CRISPR_OFFTARGET_PROVIDER=auto` until a real local SQLite
  index exists on Render and provider-cache says `indexed_sqlite.ready=true`.
- Do not do request-time Supabase search or startup materialization for genome
  or protein assets.
- Do not commit generated/private assets.
- Do not remove fallback paths; remove stale or misleading labels from live
  paths.
- Treat AI gateway as out of scope.

## Task 1 - Primer Result Card Consumes Live Fields

Goal: Remove stale primer mock labels where backend Primer3 data exists.

Context: Backend schemas and `backend.ts` mirrors already expose Primer3
secondary-structure and placement fields. The web card still uses deterministic
mock values.

Relevant files:

- `app/web/components/workbench/primer/PrimerResultCard.tsx`
- `app/frontend/src/components/workbench/primer/PrimerResultCard.tsx`
- `app/web/components/workbench/viewer/SequenceViewerV2.tsx`
- `app/frontend/src/components/workbench/viewer/SequenceViewerV2.tsx`
- `app/web/lib/workbench/primer-metrics.ts`

Proposed approach:

- Add live field helpers and fallback helpers.
- Render live thermo and placement values when non-null.
- Change copy payload and tooltip text to remove "pending backend" when fields
  exist.
- Make the amplicon overlay coordinate-aware and edge-clipped if the amplicon is
  outside the current visible window.

Acceptance criteria:

- No `.eamos-mock` appears for Primer3 thermo/placement when backend returns
  live fields.
- Offline fixture/fallback still has honest illustrative labels.
- Primer copy payload includes live start/stop and genomic coordinates.

Verify:

- `cd app/web; npx tsc --noEmit`
- `cd app/frontend; npx tsc --noEmit`
- Browser verify `/workbench` primer result card.

Out of scope:

- SNP masking.
- Whole-genome primer specificity.

## Task 2 - Primer SNP Masking Provider

Goal: Make `avoid_snps=true` actually source-backed when dbSNP is mounted.

Context: Backend currently appends "SNP masking was requested but is not yet
applied." dbSNP local adapters and Linux `pysam` indexed readers already exist.

Relevant files:

- `app/backend/app/services/workbench_design.py`
- `app/backend/app/services/indexed_sources.py`
- `app/backend/app/services/dbsnp_local.py`
- `app/backend/app/core/config.py`
- `app/backend/tests/test_workbench_api.py`
- `app/backend/tests/test_dbsnp_local_adapter.py`

Proposed approach:

- Add settings for dbSNP runtime VCF/TBI path if not already available through
  source asset metadata.
- Add a SNP masking provider that queries dbSNP records over the design template
  interval.
- Add Primer3 excluded regions and/or post-filter pairs whose 3-prime ends
  overlap SNPs.
- Add notes and warning codes showing provider state and exclusion counts.

Acceptance criteria:

- With a tiny indexed dbSNP fixture, a primer overlapping a 3-prime SNP is
  rejected or demoted.
- With no dbSNP asset, behavior remains available but warning-labeled.
- No raw paths appear in API responses.

Verify:

- `cd app/backend; python -m pytest tests/test_workbench_api.py tests/test_dbsnp_local_adapter.py -q`
- `cd app/backend; python -m ruff check app tests`
- `cd app/backend; python -m black --check --target-version py310 app tests`

Out of scope:

- Whole-genome specificity via isPcr.

Status update - 2026-06-14 00:07 +1000 - Codex:

- Added a pluggable primer SNP masking provider surface with a no-op fallback
  and local dbSNP-backed implementation.
- Primer3 requests now receive source-backed excluded regions when dbSNP records
  overlap the design window, and candidate pairs are rejected when a SNP lands
  in the 3-prime risk window.
- Added focused tests for unconfigured `avoid_snps=true` warnings, dbSNP
  excluded-region injection, 3-prime pair rejection, and sanitized notes. isPcr
  remains approval-gated and unchanged.

## Task 3 - Primer Whole-Genome isPcr Readiness

Goal: Prepare an approval-gated path to source-backed whole-genome primer
specificity.

Context: The provider exists, but production should not enable it until
`isPcr`, hg38, and licensing are handled.

Relevant files:

- `app/backend/app/services/workbench_design.py`
- `app/backend/app/api/routes/health.py`
- `app/backend/app/core/config.py`
- `app/backend/tests/test_health_api.py`

Proposed approach:

- Add a sanitized provider-cache readiness probe for UCSC isPcr.
- Add a bounded CLI smoke over a known primer pair and local `hg38.2bit`.
- Keep `PRIMER_SPECIFICITY_PROVIDER=template` by default.

Acceptance criteria:

- Health can distinguish `template`, `ucsc_ispcr_ready`, and
  `ucsc_ispcr_unavailable`.
- Enabling `ucsc_ispcr` without binary/reference fails closed with a clear 503.

Verify:

- `cd app/backend; python -m pytest tests/test_workbench_api.py tests/test_health_api.py -q`
- CLI help/smoke with a tiny fake provider where possible.

Approval needed:

- UCSC/Kent binary license/distribution comfort.
- Render-local binary and hg38 path.

Status update - 2026-06-12 01:46 +1000 - Codex:

- Provider-cache now reports sanitized primer specificity readiness for the
  default `template` provider and the `ucsc_ispcr` binary/reference asset pair.
- `PRIMER_SPECIFICITY_PROVIDER=template` remains the default; no env flip.

## Task 4 - CRISPR Off-Target Index Build/Verify Package

Goal: Prepare the full-genome SpCas9 SQLite artifact workflow up to the Render
env flip.

Context: The code can inspect/query/build an index, but no full artifact is
mounted in production.

Relevant files:

- `app/backend/app/services/crispr_offtarget_index.py`
- `app/backend/app/cli/eamos_crispr_offtarget_index.py`
- `app/backend/app/services/crispr_offtarget_screening.py`
- `app/backend/app/api/routes/health.py`
- `app/backend/tests/test_workbench_api.py`
- `app/backend/tests/test_health_api.py`

Proposed approach:

- Extend the CLI with `estimate`, `build`, `verify`, and `manifest` subcommands
  if missing.
- Build a tiny fixture index in tests and a pilot contig index locally to prove
  query shape.
- Prepare a full-build runbook that writes to an ignored local path, computes
  checksum, and records target count.
- Prepare Render copy/mount instructions, but do not flip env.

Acceptance criteria:

- Tiny fixture index tests pass.
- Full index runbook names exact input, output, checksum, and Render path.
- Provider-cache remains mock fallback until env is explicitly changed.

Verify:

- `cd app/backend; python -m app.cli.eamos_crispr_offtarget_index --help`
- `cd app/backend; python -m pytest tests/test_workbench_api.py tests/test_health_api.py -q`

Approval needed:

- Where to build the full index.
- Whether the existing Render disk is attached and large enough.
- When to copy the artifact and switch env.

Status update - 2026-06-12 01:46 +1000 - Codex:

- `python -m app.cli.eamos_crispr_offtarget_index` now includes `estimate`,
  `verify`, and `manifest` alongside existing `build`, `inspect`, and `query`.
- Added CLI tests for tiny FASTA estimate plus sanitized verify/manifest output.
- Provider-cache remains mock fallback unless a valid local index is mounted and
  the provider is explicitly configured.

Status update - 2026-06-13 22:04 +1000 - Codex:

- Added the full-index runbook/proof to
  `docs/workbench-live-wiring/render-approval-bundle.md` and the structured
  `python -m app.cli.eamos_workbench_render_approval_bundle` JSON.
- Full build input is pinned to UCSC `hg38.2bit` / GRCh38 with expected MD5
  `dcc3ea27079aa6dc3f9deccd7275e0f8`, expected size `835393456` bytes, and
  Render-mounted path `/var/data/eamos/bio_assets/genomes/hg38.2bit`.
- The runbook records the full build command, expected SQLite path, checksum /
  manifest flow, pilot tiny proof, Render copy/mount instructions,
  provider-cache readiness criteria, rollback values, and generated-artifact
  no-commit policy.
- Tiny proof and read-only live provider-cache smoke are captured in the
  approval bundle: local pilot index verified/manifested/query-smoked in
  `%TEMP%`; SG and Vercel remain `auto` / `mock_fallback` with
  `indexed_sqlite.ready=false`.
- No provider flip, Render env change, startup download, Supabase mutation, or
  generated genome/SQLite/index artifact commit was performed.

Status update - 2026-06-13 23:20 +1000 - Codex:

- Added `python -m app.cli.eamos_crispr_offtarget_preflight` as the normalized
  local runbook gate for CRISPR off-target index readiness. Auto mode reports
  warning-labeled mock fallback without failing public runtime; forced
  `indexed_sqlite` mode fails closed under `--require-ready` until the mounted
  SQLite index verifies.
- Extended `python -m app.cli.eamos_workbench_preflight --compact` with one
  local ready/not-ready bundle. It summarizes fixture freshness, cache
  readability, full-gene fixture timings, CRISPR off-target public runtime
  posture, primer specificity, CRISPR score runtime, CRISPR index flip
  readiness, and compact coordinate index readiness without network calls or
  mutations.
- Updated the approval-bundle CLI and docs to list
  `eamos_workbench_preflight --compact` before the off-target-specific
  `eamos_crispr_offtarget_preflight` gate.
- No provider flip, Render env change, startup download, Supabase mutation,
  or generated genome/SQLite/index artifact commit was performed.

Status update - 2026-06-14 00:07 +1000 - Codex:

- Hardened provider-state contracts with focused tests for indexed off-target
  success, auto-mode mock fallback when no index is mounted, and forced
  `indexed_sqlite` fail-closed behavior when the index is missing.
- Provider-cache tests now distinguish `auto` mock fallback from forced provider
  unavailability. No provider flip, env change, Render mutation, or generated
  index asset was performed.

## Task 5 - CRISPR Screening Primers Over Real Windows

Goal: Make screening primers fully live once off-target sites are real.

Context: Primer generation works, but mock off-target coordinates force mock
windows.

Relevant files:

- `app/backend/app/services/crispr_offtarget_screening.py`
- `app/backend/app/services/workbench_design.py`
- `app/web/components/workbench/crispr/OffTargetTab.tsx`
- `app/frontend/src/components/workbench/crispr/OffTargetTab.tsx`

Proposed approach:

- Ensure indexed off-target sites carry enough chromosome/position/strand data.
- Fetch reference windows from mounted hg38 for selected sites.
- Keep `crispr_screening_mock_template` only when source windows are absent.
- Propagate primer SNP/specificity notes into the screening-primer table.

Acceptance criteria:

- With indexed sites and hg38 available, no mock-window warning appears.
- With mock sites or missing hg38, warning remains explicit.

Verify:

- Backend focused pytest for screening-primer windows.
- Web/frontend type checks.

Depends on:

- Task 4 for real indexed sites.
- Mounted hg38 asset.

Status update - 2026-06-14 00:07 +1000 - Codex:

- Added an optional screening reference-window provider path for CRISPR
  screening primers. When a usable reference window is supplied, primers report
  `template_source="reference_window"` instead of the mock template.
- Missing or unusable reference windows still fall back to the explicit
  `crispr_screening_mock_template` warning state.
- Added focused tests for reference-window coordinate calls, target offsets, and
  fallback warning preservation.

## Task 6 - CRISPR Outcomes Backend Route

Goal: Replace frontend sample/fallback with a source-backed observed-only
backend route.

Context: `app/web/lib/api.ts` already posts to `/api/v1/crispr/tide`; backend
has no route.

Relevant files:

- `app/backend/app/schemas/workbench.py`
- `app/backend/app/api/routes/workbench.py`
- `app/backend/app/services/trace_parser.py`
- `app/backend/app/services/trace_analysis.py`
- `app/backend/app/services/crispr_tide.py`
- `app/backend/app/services/workbench_design.py`
- `app/backend/app/cli/eamos_crispr_tide.py`
- `app/backend/tests/test_crispr_tide_cli.py`
- `app/web/lib/workbench/crispr-tide-sample.ts`
- `app/web/lib/api.ts`
- `app/web/components/workbench/crispr/OutcomesTab.tsx`

Proposed approach:

- Add `CrisprTideRequest`/`CrisprTideResponse` style schemas or reuse the
  existing frontend shape as backend schema.
- Add multipart route accepting control and edited files plus cut index.
- Parse AB1 with existing trace parser.
- Compute observed spectrum and editing efficiency. Use SciPy where useful.
- Return `source_backed=true`, `analysis_kind="tide"`, and
  `predicted_available=false` for first slice.
- Keep frontend sample fallback only for network/offline failures.
- Add an operator CLI for the same local adapter so a trace pair can be analyzed
  without a browser session or running FastAPI.

Acceptance criteria:

- Uploading two valid traces returns a backend response, not
  `CRISPR_TIDE_SAMPLE`.
- Bad trace files return structured 422.
- Frontend disclosure shows "TIDE" or provider label, not "Frontend sample."
- `python -m app.cli.eamos_crispr_tide` emits sanitized JSON, names no raw local
  paths in error output, and preserves observed-only/no-prediction guardrails.

Verify:

- Backend route tests with fixture traces.
- CLI tests and a direct CLI smoke with the RPE65 AB1 fixture.
- `cd app/web; npx tsc --noEmit`
- Browser verify Outcomes tab.

Out of scope:

- Predicted Lindel bins.
- Tracy integration.

## Task 7 - CRISPR Advanced Score Preflight

Goal: Make advanced CRISPR score readiness explicit before enabling R scoring.

Context: `crisprscore_r` provider exists but depends on R/Bioconductor and
optional conda envs.

Relevant files:

- `app/backend/app/services/crispr_design.py`
- `app/backend/app/api/routes/health.py`
- `app/backend/app/core/config.py`
- `app/backend/tests/test_crispr_design.py`
- `app/backend/tests/test_health_api.py`

Proposed approach:

- Add a preflight CLI for Rscript/jsonlite/crisprScore/RuleSet3/Lindel.
- Expand health fields to show configured/available per score family.
- Keep provider default local deterministic.

Acceptance criteria:

- Missing R runtime is reported as unavailable, not fatal.
- Configured provider with bad R setup falls back or fails according to existing
  provider semantics with warnings.

Verify:

- Backend focused tests.
- CLI help.

Approval needed:

- R installation target.
- Bioconductor `crisprScore` install.
- Conda env locations for RuleSet3/Lindel.

Status update - 2026-06-12 01:46 +1000 - Codex:

- Added `python -m app.cli.eamos_crispr_score_preflight` for sanitized
  Rscript/jsonlite/crisprScore/RuleSet3/Lindel readiness.
- Provider-cache now reuses the same inspection and exposes per-score-family
  readiness without local paths.
- CRISPR provider default remains local deterministic.

## Task 8 - ssODN Fallback Shrink

Goal: Reduce false illustrative labels by proving more real ssODN contexts and
making fallback states precise.

Context: RPE65 c.260A>G can resolve live when local transcript/hg38 assets are
available. Unsupported variants still fallback.

Relevant files:

- `app/backend/app/services/crispr_ssodn.py`
- `app/backend/app/services/sequence_context.py`
- `app/web/components/workbench/crispr/SsodnLabDonor.tsx`
- `app/frontend/src/components/workbench/crispr/SsodnLabDonor.tsx`
- `app/backend/tests/test_workbench_api.py`

Proposed approach:

- Add additional MANE/hg38 fixture tests for non-RPE65 human SNVs.
- Add preflight health for ssODN local transcript and hg38 readiness.
- Tighten UI fallback copy around explicit warning codes.

Acceptance criteria:

- Source-backed responses never show "illustrative."
- Unsupported/missing-source responses still show the label and warning.

Verify:

- Backend focused pytest.
- Web/frontend type checks.

Depends on:

- Mounted hg38 and MANE GFF for production breadth.

## Task 9 - Gene/Protein Viewer Track Provenance

Goal: Move viewer annotations from sample/scaffolded to per-track live source
status.

Context: Viewer live mode still warns `clinvar_track_not_live_hydrated`; full
gene mode is fixture-backed; frontend fills scaffold fields.

Relevant files:

- `app/backend/app/services/gene_viewer.py`
- `app/backend/app/schemas/gene_viewer.py`
- `app/backend/app/services/protein_annotation.py`
- `app/backend/app/services/clinvar_local.py`
- `app/backend/app/services/alphamissense_local.py`
- `app/web/lib/workbench/gene-viewer-adapter.ts`
- `app/web/components/workbench/viewer/GeneMinimap.tsx`
- `app/web/components/workbench/viewer/ProteinView.tsx`

Proposed approach:

- Add per-track source status in `ViewerTracks` or provenance.
- Hydrate ClinVar variants and exon density from local ClinVar VCF+TBI.
- Hydrate protein features from ProteinAnnotationService when Pfam/HMMER is
  mounted.
- Add optional AlphaMissense heatmap only after local asset is approved.
- Keep scaffold warnings until full-gene data is source-backed.

Acceptance criteria:

- UI can show which tracks are live and which are scaffolded.
- ClinVar counts and lollipops are source-backed for the queried gene/window
  when ClinVar is mounted.
- Protein domains/features are source-backed when Pfam/HMMER is enabled.

Verify:

- Backend gene viewer tests.
- Protein annotation tests.
- Web/frontend type checks.
- Browser verify viewer after UI changes.

Status update - 2026-06-12 01:46 +1000 - Codex:

- Sequence-window dragging now caches row hit-test geometry for the drag
  lifetime.
- Full-gene rows are memoized and row-level CSS containment/content visibility
  was added to reduce long-window paint work.
- Smooth scroll behavior now respects reduced-motion preferences.

Status update - 2026-06-14 00:07 +1000 - Codex:

- Tightened compact-coordinate index readiness and provenance tests. Health now
  asserts source runtime scanning and startup download remain disabled for the
  compact index path.
- The compact coordinate index source provenance test now asserts sanitized
  identifiers and no raw local index path leakage.

Approval needed:

- ClinVar local materialization on Render.
- Pfam/HMMER persistent disk enablement.
- AlphaMissense asset approval if included.

## Task 10 - Alignment Backend Completion

Goal: Remove remaining "coming via backend" alignment gaps while preserving
offline fallback.

Context: `/align` and `/align/trace` exist. Accession reference lookup and
optional robust WFA/consensus are not implemented.

Relevant files:

- `docs/workbench-align-engine/spec.md`
- `app/backend/app/api/routes/workbench.py`
- `app/backend/app/services/workbench_design.py`
- `app/backend/app/services/trace_parser.py`
- `app/web/components/workbench/align/AlignPanel.tsx`

Proposed approach:

- Add sequence/reference resolve endpoint as an additive route.
- Add optional WFA/abPOA dependencies only after approval.
- Keep Biopython/current fallback when optional packages are absent.
- Update frontend copy so backend-resolved references are not described as
  future work after the endpoint lands.

Acceptance criteria:

- Accession search can resolve a known RefSeq/Ensembl reference.
- Current align/trace contracts remain compatible.
- Browser fallback remains only for offline/unavailable cases.

Verify:

- Backend align tests.
- Web/frontend type checks.
- Browser verify Align panel.

Approval needed:

- Add `pywfa` and `pyabpoa` to requirements if robust engine is in scope.
- Tracy binary only if decompose phase is approved.

Status update - 2026-06-12 01:46 +1000 - Codex:

- Added additive `POST /api/v1/align/reference` to resolve the backend
  reference window and target metadata without requiring a read.
- Added shared backend/frontend contract types and a Next API helper.
- No optional WFA/abPOA dependencies were added.

## Task 11 - Render Approval Bundle

Goal: Present a single approval package before any production provider flip.

Context: Several tasks need mounted private assets or runtime installs.

Proposed approval bundle:

- Exact Render disk path layout:
  - `/var/data/eamos/bio_assets/genomes/hg38.2bit`
  - `/var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite`
  - `/var/data/eamos/bio_assets/dbsnp/GCF_000001405.40.gz`
  - `/var/data/eamos/bio_assets/dbsnp/GCF_000001405.40.gz.tbi`
  - `/var/data/eamos/bio_assets/clinvar/clinvar.vcf.gz`
  - `/var/data/eamos/bio_assets/clinvar/clinvar.vcf.gz.tbi`
  - `/var/data/eamos/bio_assets/protein_annotation/Pfam-A.hmm`
  - `/var/data/eamos/bio_assets/protein_annotation/Pfam-A.hmm.h3*`
- Exact env changes:
  - `CRISPR_OFFTARGET_PROVIDER=indexed_sqlite`
  - `CRISPR_OFFTARGET_INDEX_PATH=/var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite`
  - optional `PRIMER_SPECIFICITY_PROVIDER=ucsc_ispcr`
  - optional dbSNP/ClinVar/Pfam path envs once code names are final
- Preflight output showing ready status.
- Rollback plan: set providers back to `auto`/`template`/disabled.

Acceptance criteria:

- Steven can approve one set of installs, mounts, env changes, and smoke tests.
- No production flip happens before that approval.

Verify after approval:

- SG `/healthz`
- SG `/api/v1/health/provider-cache`
- SG and Vercel Workbench API probes for primer, CRISPR design, off-targets,
  screening primers, ssODN, align, and outcomes.

Status update - 2026-06-13 21:33 +1000 - Codex:

- Added `docs/workbench-live-wiring/render-approval-bundle.md` with the exact
  Render disk layout, env changes, preflight commands, post-flip smoke checks,
  approval questions, and rollback values.
- Added `python -m app.cli.eamos_workbench_render_approval_bundle`, a read-only
  sanitized JSON generator for the same approval package. The CLI performs no
  network calls, Render mutations, env changes, provider flips, startup
  downloads, or source-asset writes.
- Provider posture remains unchanged: keep `LLM_PROVIDER=mock`,
  `CRISPR_OFFTARGET_PROVIDER=auto`, and `PRIMER_SPECIFICITY_PROVIDER=template`
  until the approval bundle is accepted and provider-cache proves readiness.

## Task 12 - TIDER, Lindel, and Trace Decomposition Spec

Goal: Define the next CRISPR outcomes lane without mixing implementation into
the current observed-only route.

Context: `/api/v1/crispr/tide` is intentionally observed-only. TIDER-style
template repair, Lindel prediction, and signal-level trace decomposition need a
separate source-backed design before runtime work.

Relevant files:

- `docs/tider-lindel-trace-decomposition/spec.md`
- `app/backend/app/services/trace_parser.py`
- `app/backend/app/services/crispr_tide.py`
- `app/backend/app/schemas/workbench.py`

Status update - 2026-06-14 00:07 +1000 - Codex:

- Added `docs/tider-lindel-trace-decomposition/spec.md` as a spec-only phase.
- The spec separates observed indel decomposition, Lindel prediction, and
  TIDER-style template-directed repair provider surfaces.
- It preserves the existing observed-only route until a reviewed additive route
  or contract extension passes quality gates and tests.
- No runtime TIDER, Lindel, trace-decomposition, UI, provider, or deployment
  implementation was added in this phase.
