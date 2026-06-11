# Workbench Live-Wiring Completion Spec

Status: draft for Steven review. Created 2026-06-11 by Codex.

## What

Complete the remaining Workbench live-wiring work by removing stale frontend
mock labels where backend data already exists, adding backend contracts where no
route exists, and preparing approval-gated local source assets for the features
that cannot be live without Render-mounted genome/protein data. The work keeps
AI gateway out of scope.

## Context

The combined Workbench integration shipped live provider wiring, Primer3
thermodynamics and placement fields, ssODN genomic coordinates, optional
indexed SQLite CRISPR off-target screening, and provider-cache health gates.
Production is intentionally still `CRISPR_OFFTARGET_PROVIDER=auto`; health
currently reports indexed SQLite not ready and mock fallback active. The
remaining gaps are not one thing: some are frontend stale displays, some are
backend gaps, and some are runtime asset gaps.

Relevant files:

- `app/backend/app/schemas/workbench.py`
- `app/backend/app/services/workbench_design.py`
- `app/backend/app/services/crispr_design.py`
- `app/backend/app/services/crispr_offtarget_index.py`
- `app/backend/app/services/crispr_offtarget_screening.py`
- `app/backend/app/services/crispr_ssodn.py`
- `app/backend/app/services/gene_viewer.py`
- `app/backend/app/services/protein_annotation.py`
- `app/backend/app/services/trace_parser.py`
- `app/backend/app/api/routes/workbench.py`
- `app/backend/app/api/routes/health.py`
- `app/web/components/workbench/**`
- `app/frontend/src/components/workbench/**`
- `app/web/lib/backend.ts`
- `app/frontend/src/lib/backend.ts`

## Requirements

1. Primer result cards must show live Primer3 secondary-structure and placement
   fields whenever the backend returns them.
2. Primer UI must keep an honest fallback label only when the active response
   lacks those fields or is an offline fixture.
3. `avoid_snps=true` must either perform source-backed SNP exclusion or return a
   clear warning that it is not active. It must not silently imply live SNP
   avoidance.
4. Whole-genome primer specificity must remain opt-in until `isPcr` and hg38
   assets are present and license/provenance metadata is recorded.
5. CRISPR off-target screening must use the SQLite provider only when a local
   index passes inspection. Missing/incompatible indexes must fail closed for
   explicit `indexed_sqlite` and stay mock fallback for `auto`.
6. CRISPR outcomes must not return the frontend sample once a backend route is
   present. A backend observed-only response is acceptable for the first live
   slice if it sets `source_backed=true`, `analysis_kind="tide"`, and
   `predicted_available=false`.
7. CRISPR advanced scoring must preserve provider labels and warnings for
   unavailable RuleSet/CRISPRscan/CRISPRater/MIT/CFD/Lindel sources.
8. ssODN must surface illustrative donor labels only when the response warning
   or template source proves the genomic window was not source-backed.
9. Gene/protein viewer tracks must not display sample-bounded ClinVar, protein,
   conservation, or AlphaMissense data as live. Each track needs source-backed
   provenance before the illustrative label is removed.
10. Alignment must retain the current backend `/align` and `/align/trace`
   contracts while preparing additive sequence-resolve and robust-engine
   improvements.
11. Render deployment must not perform large startup downloads or request-time
   Supabase/raw-source searches.
12. No generated genome, SQLite index, dbSNP, ClinVar, Pfam, AlphaMissense, or
   private source asset may be committed.

## Design

### 1. Primer Live-Field Consumption

No new backend fields are needed. `PrimerPair` already carries:

- `self_any_forward`, `self_any_reverse`
- `self_end_forward`, `self_end_reverse`
- `hairpin_tm_forward`, `hairpin_tm_reverse`
- `pair_compl_end`
- `forward_strand`, `reverse_strand`
- `forward_template_start`, `forward_template_stop`
- `reverse_template_start`, `reverse_template_stop`
- `genomic_chromosome`, `genome_build`
- `forward_genomic_start`, `forward_genomic_stop`
- `reverse_genomic_start`, `reverse_genomic_stop`
- `amplicon_template_start`, `amplicon_template_end`
- `amplicon_genomic_start`, `amplicon_genomic_end`

Implementation:

- Update `app/web/components/workbench/primer/PrimerResultCard.tsx` and the
  `app/frontend` mirror to compute `hasLiveThermo` and `hasLivePlacement`.
- Remove `mockStruct()` from the live path; keep it only in a named offline
  fallback helper.
- Change the copy payload to include live template/genomic start-stop values.
- Remove "pending backend" title/copy when live placement exists.
- Update `SequenceViewerV2` primer overlay to use
  `amplicon_template_start/end` for the collapsed sequence basis when possible,
  and `amplicon_genomic_start/end` for genomic/full-locus basis. If the active
  viewer window does not include the amplicon, render a bounded edge indicator
  instead of a misleading full-width schematic.
- Add frontend tests for live fields and fallback fields.

### 2. Primer SNP Avoidance

Backend design:

- Add a `PrimerSnpMaskingProvider` protocol in or near `workbench_design.py`.
- Add a default `NoopPrimerSnpMaskingProvider` that records
  `primer_snp_masking_not_configured`.
- Add a local dbSNP provider backed by `PysamIndexedVcfReader` for mounted
  dbSNP VCF+TBI. It queries the design template genomic interval.
- Convert returned SNPs into Primer3 exclusions using `SEQUENCE_EXCLUDED_REGION`
  and/or a post-filter that rejects primer pairs whose last 5 bases overlap a
  known SNP. The first slice should be conservative: reject 3-prime overlaps and
  warn for any body-overlap that was not excluded by Primer3.
- Add response notes with provider, source version, queried interval, SNP count,
  and exclusion count. Do not emit raw file paths.

Runtime assets:

- dbSNP GCF_000001405.40 VCF+TBI must be local on Render.
- `pysam==0.24.0` is already Linux-only in backend requirements.
- No Windows install is required for local unit tests; fixture tests can use tiny
  VCF files.

### 3. Primer Whole-Genome Specificity

Existing provider path:

- `PRIMER_SPECIFICITY_PROVIDER=template` is default and source-backed only for
  the resolved template window.
- `PRIMER_SPECIFICITY_PROVIDER=ucsc_ispcr` requires `UCSC_ISPCR_BINARY_PATH`,
  `UCSC_ISPCR_HG38_PATH`, and a Linux runtime.

Implementation:

- Add a Render preflight check that executes a bounded `isPcr` smoke against a
  known RPE65 primer pair and reports sanitized readiness in provider-cache
  health.
- Keep the provider disabled until the binary and `hg38.2bit` are mounted.
- Preserve notes that this is UCSC isPcr, not NCBI Primer-BLAST.

Approval:

- Confirm comfort with UCSC/Kent binary licensing before bundling or installing
  the binary on production.

### 4. CRISPR Advanced Guide Scoring

Current local deterministic guide design is live. The advanced scoring provider
exists but requires external runtime configuration.

Implementation:

- Add a `python -m app.cli.eamos_crisprscore_preflight` CLI to emit sanitized
  readiness for `Rscript`, `jsonlite`, `crisprScore`, RuleSet3 conda env, and
  Lindel conda env.
- Add provider-cache health fields for each advanced score family without
  exposing local paths.
- Do not switch `CRISPR_PROVIDER=crisprscore_r` until preflight is green.

Installs:

- R runtime with `Rscript`.
- Bioconductor `crisprScore`.
- R package `jsonlite`.
- Optional conda envs for RuleSet3 and Lindel if those methods are enabled.

### 5. CRISPR Off-Target SQLite Index

The code supports local SQLite, but no production index is mounted.

Implementation:

- Extend `python -m app.cli.eamos_crispr_offtarget_index` with:
  - dry-run size/time estimate over FASTA/2bit contig lengths,
  - build manifest with schema version, source genome checksum, target count,
    max mismatch radius, build host, build time, and SQLite checksum,
  - verify command that opens the SQLite read-only and runs known RPE65 guide
    queries,
  - optional split-contig build/stitch path if full build memory/disk requires
    chunking.
- Build the full artifact outside the web deploy path.
- Copy the artifact to private storage or directly to Render persistent disk.
- Set production env only after inspection returns ready:
  - `CRISPR_OFFTARGET_PROVIDER=indexed_sqlite`
  - `CRISPR_OFFTARGET_INDEX_PATH=/var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite`
- Keep `CRISPR_OFFTARGET_PROVIDER=auto` until the file is present and
  provider-cache reports `indexed_sqlite.ready=true`.

Render:

- Use the persistent disk path, not the build image or startup download.
- Because SG is the sole backend, schedule any disk attach/env flip for an
  off-peak maintenance window.

### 6. CRISPR Screening Primers

Screening primers become fully live after off-target sites and target windows
are real.

Implementation:

- Keep `crispr_screening_mock_template` only when the selected off-target site
  came from mock/deidentified enumeration or when hg38 window extraction fails.
- Once indexed off-targets are live, design primers against reference windows
  fetched from mounted hg38.
- Reuse the primer SNP and specificity providers where configured.

### 7. CRISPR Outcomes Backend Route

Add a first backend route for observed-only outcomes:

- `POST /api/v1/crispr/tide?cut_site_index=<int>`
- Multipart fields: `control_file`, `edited_file`
- Response shape mirrors current `CrisprTideResult`:
  - `source_backed: true`
  - `analysis_kind: "tide"`
  - `provider_label`
  - `cut_site_index`
  - `editing_efficiency`
  - `r_squared`
  - `spectrum[]`
  - `predicted_available: false`
  - `notes`

Engine first slice:

- Reuse `trace_parser.py` and trace/alignment utilities.
- Use existing SciPy dependency for non-negative least squares or a simpler
  bounded deterministic observed-only deconvolution if the trace data is not
  sufficient for a real TIDE solve.
- Avoid ICE/DECODR because licensing is not product-safe.
- Keep Lindel prediction separate from observed indel frequencies.

Future optional engine:

- Tracy `decompose` can be evaluated later as a permissive signal-level engine.

### 8. ssODN Fallback Shrink

Implementation:

- Keep current live path for supported human SNVs.
- Add tests for non-RPE65 MANE transcript success and unsupported variant
  fallback.
- Improve UI copy so it says "illustrative" only when
  `crispr_ssodn_mock_genomic_window` or `template_source=mock_*` is present.
- Add provider-cache or workbench preflight status for MANE GFF and hg38
  presence.

### 9. Gene/Protein Viewer Live Tracks

Split into track-owned providers:

- ClinVar gene/window hydration from local ClinVar VCF+TBI via `pysam`.
- Exon density from the same ClinVar query, counted by coding exon.
- Protein domains/features from existing ProteinAnnotationService and Pfam/HMMER
  runtime materialization.
- Optional AlphaMissense heatmap from local AlphaMissense TSV+index after asset
  approval.
- Conservation values from mounted phyloP bigWig if the viewer scope requires
  them.

Implementation:

- Add source status/provenance per track.
- The frontend removes sample/illustrative badges only per track, never for the
  entire viewer all at once.
- Full-gene mode remains fixture until a real full-locus sequence and annotation
  source is mounted and tested.

### 10. Alignment Completion

Current `/align` and `/align/trace` are backend-wired. Remaining work is
completion, not de-mocking:

- Add `POST /api/v1/sequence/resolve` for accession/reference search.
- Optionally add `pywfa` for ends-free affine alignment and `pyabpoa` for
  consensus if Steven approves robust alignment scope.
- Keep existing Biopython/Smith-Waterman fallback if optional packages are not
  installed.
- Keep browser fallback as offline resilience, but do not label the live path as
  browser-only when backend succeeds.

## Decisions

Decision: Treat primer thermo/placement as immediate cleanup, not backend
research.

- Alternatives: leave UI mock labels until all primer sources are live.
- Reason: backend fields already exist; stale UI copy is now misleading.
- Reversible: yes.

Decision: Keep CRISPR off-target provider `auto` until the mounted SQLite index
is verified.

- Alternatives: switch to `indexed_sqlite` now and let production fail closed.
- Reason: Steven wants mock fallback acceptable until the real artifact exists.
- Reversible: yes, via env only.

Decision: Build CRISPR outcomes as observed-only before predicted Lindel repair.

- Alternatives: wait for a full TIDE/Lindel stack before adding any backend
  route.
- Reason: the UI already accepts trace files; replacing the sample fallback with
  a source-backed observed-only route is useful and lower risk.
- Reversible: additive contract can later include predicted bins.

Decision: Track provenance per viewer track.

- Alternatives: mark the whole viewer live or mock.
- Reason: viewer data is mixed-source; per-track provenance avoids overstating
  ClinVar/protein/conservation readiness.
- Reversible: yes.

Assumption: Steven wants all backend/admin predictor wiring available behind
metadata and health gates, without adding role/account authorization plumbing.

## Versions

Existing backend requirements already include:

- `primer3-py>=2.3,<3`; local pip index reports 2.3.0 latest and installed.
- `biopython>=1.84,<2`; local pip index reports 1.87 latest and installed.
- `scipy>=1.14,<2`; local pip index reports 1.15.3 latest and installed.
- `twobitreader==3.1.8`; local pip index reports 3.1.8 latest and installed.
- `pysam==0.24.0` on non-Windows only.
- `pyBigWig==0.3.25` on non-Windows only.

Optional new packages for alignment completion:

- `pywfa>=0.5.1,<0.6`; local pip index reports 0.5.1 latest.
- `pyabpoa>=1.5.6,<2`; local pip index reports 1.5.6 latest.

External runtimes:

- R with `Rscript`, `jsonlite`, and Bioconductor `crisprScore` for advanced
  CRISPR scoring.
- Optional conda environments for RuleSet3 and Lindel under the existing
  `CRISPR_RULESET3_CONDA_ENV` and `CRISPR_LINDEL_CONDA_ENV` settings.
- Optional UCSC/Kent `isPcr` Linux binary for whole-genome primer specificity.
- Optional Tracy binary for signal-level CRISPR decompose after separate
  approval.

## Invariants

- Do not commit generated/private source artifacts.
- Do not enable startup downloads for genome/protein assets.
- Do not expose local file paths, object URIs, service keys, or signed raw-source
  URLs in health responses or frontend payloads.
- Keep both `backend.ts` mirrors byte-identical after contract changes.
- Preserve fixture/offline fallback behavior, but label it honestly.
- Keep unsupported variants fail-closed or warning-labeled; do not infer
  source-backed coordinates from unrelated fixtures.

## Error Behavior

- Missing primer live thermo/placement fields: UI falls back to labeled
  illustrative values and logs no hard error.
- SNP provider missing: response notes say SNP masking is not configured; if
  `avoid_snps=true`, warning code is included.
- Explicit `CRISPR_OFFTARGET_PROVIDER=indexed_sqlite` with missing index: backend
  returns 503 provider unavailable and health launch gate remains set.
- `CRISPR_OFFTARGET_PROVIDER=auto` with missing index: backend returns mock
  fallback and health reports `status=mock_fallback`.
- Outcomes parser failure: backend returns structured 422 for bad/unsupported
  trace files and 503 for missing parser dependency.
- Viewer source track unavailable: track is empty or fixture-labeled with a
  warning; do not synthesize live annotations.

## Testing Strategy

Backend:

- `cd app/backend; python -m pytest tests/test_workbench_api.py tests/test_health_api.py -q`
- Add focused tests for primer SNP masking, CRISPR TIDE route, off-target index
  manifest/verify, and viewer track provenance.
- `cd app/backend; python -m ruff check app tests`
- `cd app/backend; python -m black --check --target-version py310 app tests`

Frontend:

- `cd app/web; npx tsc --noEmit`
- `cd app/frontend; npx tsc --noEmit`
- Add or update Workbench component tests where available.
- Browser verify `/workbench` after UI changes.

Deployment:

- Before env flip: SG provider-cache must show mounted artifact readiness.
- After env flip: SG `/healthz`, provider-cache, primer, CRISPR design,
  off-target enumeration, screening primers, ssODN, align, and outcomes probes.
- Vercel proxy smoke for the same Workbench API routes.

## Out of Scope

- AI gateway.
- Patient Report Pipeline.
- Public frontend raw-source downloads.
- Committing generated source artifacts.
- Turning on commercial/restricted predictors without provenance/launch-gate
  metadata.
- Replacing the existing Workbench UI layout.
