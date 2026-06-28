# Prelaunch Batch And Workbench Readiness Design

Status: draft for Steven review.
Created: 2026-06-28 by Codex.
Baseline: `main` at `e41008d` with `origin/main` fetched.

## Summary

The report backend source-cache pillar is complete for the ClinVar generated
artifact now live on SG. No further deploy, seed, provider flip, or runtime
script is needed for that artifact.

The remaining launch-readiness work is not another ClinVar materialization
slice. It is:

1. Frontend/presentation coordination for the report launch surface.
2. A broader local-asset freshness and update-policy decision.
3. Batch hardening and browser/API verification.
4. Workbench provider posture, honest fallback/source labels, and browser/API
   verification.

PubMed-local and DuckDB/Parquet should not block launch. Keep PubMed on the
current API/cache path until storage, Render disk, staging, and corpus scope are
approved. Keep DuckDB/Parquet as the disabled analytical lane; Phase 0/1 local
adapter and preflight work are enough for now.

This document is the design checkpoint. Per the design/spec/plan workflow, the
formal `spec.md` and `plan.md` should be written after Steven approves the
direction below.

## Context

The resumed handoff states:

- SG deploy `dep-d90er2lckfvc73ddmie0` is live on `e41008d`.
- `clinvar_gene_distribution_index` was synced from private Storage by the
  Dashboard Shell instance.
- `/api/v1/health/provider-cache` reports the ClinVar generated artifact ready.
- RPE65 `c.260A>G` full lookup uses `source_status=local_index`, total 1,136,
  `query_accession=VCV001421454`, `query_cell=vus_noncoding`, and no
  pending-index warning.

The working tree already had dirty documentation before this design:

- `PROGRESS.md`
- `agent_handoff/CURRENT.md`
- `docs/deployment/materialization-lessons-learned.md`
- `docs/report-backend-source-cache-readiness/plan.md`

Those files are left untouched here.

## Goals

- Treat the SG ClinVar generated artifact phase as closed unless a new defect is
  found.
- Define the safest PubMed launch posture.
- Define whether any DuckDB/Parquet work is needed before launch.
- Define the minimum Batch work needed to be genuinely functional before launch.
- Define the minimum Workbench work needed to be genuinely functional before
  launch.
- Preserve existing guardrails: no Render env mutation, provider flip, raw
  source download, Supabase metadata mutation, one-off live runtime script,
  commit, push, or destructive git action without Steven's exact approval.

## Non-goals

- Building, uploading, syncing, or enabling PubMed-local.
- Building literature embeddings or enabling RAG.
- Running a raw PubMed, PMC, or PubTator mirror.
- Building DuckDB Silver/Gold Parquet releases.
- Replacing tabix/SQLite/report-cache point lookups with DuckDB.
- Enabling CRISPR full-genome indexed off-targets on production.
- Enabling UCSC isPcr whole-genome primer specificity on production.
- Enabling advanced CRISPR R scoring providers.
- Adding account-role or commercial licensing filters.

## Constraints

- Production SG remains constrained by Render service memory and persistent disk.
- The current PubMed-local spec calls out Render disk as 60 GB and already
  competing with dbSNP, phyloP, hg38, Pfam, generated SQLite, and predictor
  caches.
- Runtime must not download sources at request time, startup, deploy, or Vercel
  build time.
- Public responses and health/preflight output must not leak local paths, signed
  URLs, secrets, private object URIs, or raw source snippets.
- Dirty graph and handoff files are expected; do not treat dirty generated graph
  output or documentation as a reason to skip codebase graph queries.

## Current State

### Report Source Cache Pillar

Decision: complete for the ClinVar generated artifact.

Acceptance evidence from the handoff and readiness plan:

- `source_assets.clinvar_gene_distribution_index ready=true`.
- 28,936 genes.
- 4,713,770 variants.
- Byte size 737,673,216.
- SHA-256
  `efbec24b6f0764d2bece7c0a3abc2c10fb9749494e7ae78e74e707a015f4f196`.
- RPE65 `c.260A>G` full lookup resolves through the local index.
- No pending-index warning remains for that path.

Remaining work is launch coordination, not artifact completion:

- Frontend/presentation signoff.
- Freshness/update-policy decision across local assets.
- Future provider/env flips only after exact approval.

### PubMed

Decision: leave PubMed as API/cache-backed for launch.

The PubMed corpus spec explicitly treats the earlier 200-PMID SQLite as a proof
artifact only, not a production PubMed-local corpus. It also recommends pausing
full PubMed materialization and proceeding with other lanes first.

Known corpus-size posture from the latest repo spec:

- PubMed baseline plus updates: about 58.254 GiB compressed.
- PubTator selector tables: about 6.783 GiB compressed.
- PMC OA XML/text scenarios are much larger and out of launch scope.
- Supabase object storage technically had enough headroom for one raw PubMed
  mirror at the time of the spec, but not enough room for safe version overlap.
- Render disk is the tighter runtime constraint for local SQLite and future
  embeddings.

Options:

1. Launch with API/cache PubMed.
   - Recommended.
   - No new disk, Storage, or Render mutation.
   - Keeps current PubMed, LitVar, and ClinicalTrials behavior honest.
   - Leaves `PUBMED_LOCAL_ENABLED=false` and `RAG_ENABLED=false`.

2. Build a targeted seed artifact.
   - Useful only for a small demo cohort or a bounded launch fixture.
   - Must be explicitly labeled `targeted_seed`.
   - Requires separate approval before any source download, Storage upload,
     metadata registration, Render sync, or provider flip.

3. Build a filtered PubMed generated artifact.
   - The preferred future PubMed-local path if Steven wants local PubMed.
   - Requires operator staging, likely 120-180 GiB free on a non-repo volume,
     source manifests, checksum validation, license-gated abstract persistence,
     and generated SQLite upload/sync approval.

4. Run a raw mirror or raw-plus-selectors mirror.
   - Not recommended before launch.
   - Needs a storage/version-overlap policy, deletion/rollback policy, upload
     retry plan, egress review, and Render disk plan.

Recommendation: do option 1 for launch. Revisit option 3 only after the Render
disk/storage decision.

### DuckDB And Parquet

Decision: no launch-blocking work.

The accepted ADR and plan define DuckDB/Parquet as an analytical lane, not the
single-coordinate report lookup path. Current implemented scope is sufficient
for launch:

- Disabled-by-default read-only DuckDB adapter.
- Sanitized provider-cache health.
- Manifest/checksum/row-count preflight contract.
- No route depends on DuckDB.
- No Silver/Gold corpus has been materialized.

DuckDB/Parquet should remain deferred until a benchmark-backed Phase 2/3
decision. Useful future workloads include:

- 1k to 100k variant batch cohort aggregation.
- Region scans.
- Report/source freshness audits.
- Reproducible materialization joins.

Do not use DuckDB to replace current tabix/SQLite/report-cache point lookups
before launch.

## Batch Design

### Existing Shape

The old Batch completion plan is behind the code. Current source already has
many of the requested pieces:

- Backend VCF ingestion rejects hg19/GRCh37 and gVCF records.
- Multiallelic rows are split and alleles are normalized parsimoniously.
- Upload reads are size-bounded and parsed with a variant cap.
- Upload endpoint is authenticated and rate-limited.
- Batch jobs run asynchronously through a bounded thread pool when the lookup
  service is bound.
- Jobs and uploads are in-memory with TTL/LRU cleanup.
- Lookup results map ClinVar, ACMG, population, predictors, report hrefs, and
  warnings into batch rows.
- Panel filtering uses curated panel symbols and compact-coordinate index
  intervals when available.
- Frontend upload/generate/poll/collect flows exist in the compare surface.
- Project-100-style tests assert real lookup summary output rather than only
  INFO-field passthrough.

### Launch MVP

Batch should launch as a bounded async VCF/panel workflow:

1. Input:
   - hg38 VCF upload.
   - Client-parsed variant lists for smaller inputs.
   - Maximum 5,000 backend variants per job.

2. Filtering:
   - PASS-only.
   - Population AF cutoff.
   - Region.
   - Panel symbol filtering.
   - Panel interval filtering when compact-coordinate index is ready.

3. Annotation:
   - Use the same lookup service as the report path.
   - Preserve warnings per row.
   - Surface source/provenance limitations instead of hiding them.

4. Output:
   - Paginated job results.
   - Cohort classification summary.
   - TSV export.
   - Chat context summary for the compared cohort.

5. Persistence:
   - Accept session-lifetime/in-memory jobs for launch unless Steven requires
     reloadable job history.
   - If reloadable history is required, add persistence as a separate spec
     because it introduces ownership, auth, cleanup, and privacy decisions.

### Batch Prelaunch Work

Required:

1. Harden `POST /api/v1/batch`.
   - Uploads are authenticated, but inline job creation is still a public
     bounded endpoint.
   - Apply authenticated principal and rate limiting to inline create as well,
     or explicitly decide that public bounded create is acceptable.

2. Browser/API proof.
   - Run the focused backend Batch tests.
   - Run web type/lint/build checks.
   - Browser-verify the compare surface with a small VCF and a Project-100 mock
     VCF against a local backend.
   - Live SG verification requires Steven approval if it exercises production
     runtime beyond read-only health.

3. Panel source decision.
   - Current panels are a local launch stub with warnings.
   - Decide whether this is acceptable for launch.
   - If real source-backed panels are required, create a separate panel-catalog
     spec for ClinGen/GenCC/MONDO/PanelApp import, provenance, and update
     policy.

4. Failure-state pass.
   - Ensure queued/running/failed/expired states have clear frontend behavior.
   - Confirm truncated client parse always uploads the original file when
     present.

Optional:

1. Job cancellation.
2. Persisted job history.
3. Larger cohort analytics through DuckDB/Parquet after Phase 2/3.

## Workbench Design

### Existing Shape

Workbench is already more than a static sample surface:

- Backend routes exist for primer design, CRISPR design, CRISPR off-targets,
  CRISPR screening primers, ssODN design, pairwise alignment, reference
  resolution, trace parsing/alignment, and TIDE-style observed outcomes.
- Primer3 thermodynamic and placement fields are exposed.
- Primer SNP masking has a local dbSNP provider path with warning-labeled
  fallback.
- CRISPR off-target provider supports mock, indexed SQLite, and auto fallback.
- Forced indexed mode fails closed when the index is missing.
- CRISPR screening primers can use reference windows when available.
- ssODN can return local MANE/hg38 transcript context where assets apply, and
  warning-labeled fallback where they do not.
- TIDE returns `source_backed=true` for observed-only backend trace analysis.
- Frontend routes deliberately fall back to bundled samples on backend-down or
  route-absent cases, with source/fallback labels in many surfaces.

### Launch MVP

Workbench should launch as a mixed source-backed/fallback design workbench with
honest labels:

1. Viewer:
   - Gene/protein sequence viewer works for the launch gene/variant path.
   - Track-level provenance and scaffold warnings remain visible where tracks
     are not fully hydrated.

2. Primer:
   - Primer3-backed design works.
   - Template specificity remains the default.
   - SNP masking is source-backed only when local dbSNP is configured.
   - Whole-genome UCSC isPcr remains approval-gated and disabled.

3. CRISPR:
   - Local deterministic SpCas9 guide design works.
   - ssODN design works where local context resolves.
   - Off-targets stay `auto` with mock fallback until the full SQLite index is
     built, mounted, preflighted, and explicitly enabled.
   - Advanced R scoring remains preflight-only until approved.

4. Align:
   - Pasted sequence alignment works.
   - AB1 trace parsing and trace alignment work within file/sample limits.
   - Optional WFA/abPOA/consensus engines are not required for launch.

5. Outcomes:
   - TIDE-style observed-only analysis works for valid trace pairs.
   - Predicted Lindel/frameshift scoring stays out of scope until provider
     readiness and model/runtime approvals.

### Workbench Prelaunch Work

Required:

1. Source/fallback label audit.
   - Browser-verify each Workbench tool with backend available and unavailable.
   - Ensure backend-backed results do not show sample/fallback labels.
   - Ensure fallback responses remain visibly marked.

2. Backend smoke suite.
   - Run focused Workbench API tests.
   - Include primer, CRISPR design, off-target auto fallback, forced-index
     fail-closed, screening primers, ssODN, align/reference, trace, and TIDE.

3. Provider posture document.
   - Record launch values for:
     - `PRIMER_SPECIFICITY_PROVIDER=template`.
     - `CRISPR_OFFTARGET_PROVIDER=auto`.
     - advanced CRISPR score provider disabled/default deterministic.
     - no isPcr or indexed off-target env flip.

4. Browser proof.
   - Verify `/workbench` viewer, Primer, CRISPR Design, CRISPR Off-targets,
     CRISPR Outcomes, and Align flows against a local backend.
   - Run mobile and desktop viewports.

Optional:

1. Implement the approved Benchling-style frontend apply polish if launch needs
   the higher-fidelity UX.
2. Add full track-level live provenance for gene/protein viewer.
3. Build/mount/enable the full CRISPR off-target index after explicit approval.
4. Enable isPcr after binary/reference/license approval.

## Architecture Views

### Batch

```text
VCF upload or inline variants
  -> batch route
  -> VCF ingest and prelookup filters
  -> bounded async BatchService job
  -> lookup service per variant
  -> paginated BatchJob results
  -> compare table, cohort summary, TSV, chat context
```

Primary launch risk: inline create perimeter and the decision on job
persistence/history.

### Workbench

```text
Workbench UI tool action
  -> app/web lib/api.ts
  -> FastAPI workbench route when available
  -> local provider or explicit fallback provider
  -> response with source/fallback metadata
  -> UI cards, overlays, tables, and disclosures
```

Primary launch risk: users mistaking a fallback/sample path for a source-backed
result. The launch bar is honest labeling plus verified backend success for the
main flows.

### PubMed

```text
Launch:
  report literature sections
    -> PubMed/LitVar/ClinicalTrials API/cache path

Future local:
  operator-staged sources
    -> offline materialization
    -> generated SQLite plus manifest
    -> private Storage upload
    -> approved Render sync
    -> provider-cache green
    -> explicit flag flip
```

Primary launch risk: overcommitting to a corpus before storage and staging are
approved. Do not do that for launch.

### DuckDB/Parquet

```text
Future analytical lane:
  source snapshots
    -> Bronze/Silver Parquet
    -> Gold joins
    -> benchmarks
    -> optional read-only runtime enablement
```

Primary launch risk: confusing the analytical lane with the proven report lookup
path. Keep it separate.

## Alternatives

### A: Delay launch until PubMed-local and DuckDB Gold exist

Rejected. It turns a working report/cache phase into a larger data-platform
release and adds storage, licensing, and operational risk.

### B: Materialize a PubMed targeted seed before launch

Possible, but only if a demo-critical use case needs it. It still requires exact
approval and clear `targeted_seed` labeling. It is not required for the current
launch posture.

### C: Add Batch job persistence before launch

Open. This is justified if launch users need reloadable job history or account
auditability. If session-lifetime results are acceptable, the existing in-memory
TTL model is simpler and lower risk.

### D: Require all Workbench providers to be fully source-backed before launch

Rejected for the general launch. Full off-target index, isPcr, advanced R
scores, and full viewer track hydration each need their own approval and
capacity work. Launch can be functional if fallback states are explicit and core
backend routes are verified.

## Cross-cutting Concerns

### Security And Abuse

- Gate or rate-limit Batch inline creation before launch.
- Preserve Workbench rate limits.
- Keep upload and trace file size/sample limits.
- Do not expose private paths or object locations in responses.

### Product Honesty

- Source-backed, fixture, mock, fallback, and unavailable states must remain
  distinguishable.
- Frontend samples are acceptable only as offline/fallback rendering aids.
- Launch claims should not say PubMed-local, full CRISPR off-target, isPcr, or
  DuckDB analytical serving are enabled unless those provider-cache checks are
  actually green.

### Operations

- No startup downloads.
- No request-time materialization.
- No remote object reads from request handlers.
- No live env flip without an approval record and rollback values.

### Testing

Before marking Batch and Workbench launch-ready:

- Run focused backend tests for Batch and Workbench.
- Run web type/lint/build checks.
- Browser-verify Batch and Workbench local flows.
- Only do live SG probes after explicit approval for the exact probe.

## Rollout

1. Approve this design.
2. Write `spec.md` for the prelaunch Batch and Workbench readiness work.
3. Write `plan.md` with task ordering, ownership, tests, and browser proofs.
4. Implement the small required hardening items.
5. Run focused local backend and web verification.
6. Browser-verify local Batch and Workbench.
7. Prepare a launch-readiness note that clearly says:
   - ClinVar generated artifact is complete.
   - PubMed remains API/cache.
   - DuckDB/Parquet remains disabled analytical lane.
   - Batch and Workbench launch surfaces are verified with documented limits.
8. Seek exact Steven approval for any live SG probe, provider flip, deploy,
   Storage mutation, or runtime sync.

## Open Questions

1. Is Batch session-lifetime in-memory job persistence acceptable for launch, or
   must users be able to reload historical jobs?
2. Are the current warning-labeled local launch panels acceptable, or must panel
   catalogs be source-backed from ClinGen/GenCC/MONDO/PanelApp before launch?
3. Is Workbench allowed to launch as mixed source-backed/fallback with honest
   labels, or must any specific provider be fully source-backed first?
4. Should PubMed stay API/cache-only until after launch, or is a targeted seed
   artifact needed for a specific demo or cohort?
5. What is the earliest point Steven wants to revisit Render disk expansion for
   PubMed-local, CRISPR off-target index, isPcr, and future DuckDB artifacts?

## Recommendation

Approve the following launch posture:

- Close the ClinVar/report generated-artifact phase.
- Leave PubMed on API/cache for launch.
- Leave DuckDB/Parquet disabled and analytical-only.
- Do a narrow Batch readiness pass focused on inline-create perimeter, panel
  source decision, local tests, and browser proof.
- Do a narrow Workbench readiness pass focused on source/fallback labeling,
  provider posture, local tests, and browser proof.

After approval, split this design into the formal implementation spec and plan.
