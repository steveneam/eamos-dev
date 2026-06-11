# Workbench Live-Wiring Audit

Status: draft for Steven review. Created 2026-06-11 by Codex.

## Summary

Workbench is not all mock anymore. The core primer, CRISPR design, ssODN, and
alignment routes have live backend paths, but several surfaces still either show
stale mock labels, fall back to fixtures when mounted source assets are absent,
or have no backend contract yet. This audit separates those cases so the next
implementation can remove the easy stale mocks first and keep the large Render
asset work approval-gated.

## Current Boundary

| Area | Current state | Live blocker | Approval/download needed |
| --- | --- | --- | --- |
| Primer thermodynamics | Backend emits Primer3 thermo fields; web result card still uses `mockStruct()` and "pending backend" copy. | Frontend consumption bug/stale UI only. | None. |
| Primer placement/overlay | Backend emits template/genomic primer and amplicon coordinates; web card/viewer still labels overlay schematic. | Frontend consumption and coordinate-aware overlay. | None. |
| Primer SNP avoidance | Request accepts `avoid_snps`; backend note says SNP masking is not applied. | Need local dbSNP range reader and Primer3 exclusion/post-filter policy. | dbSNP VCF+TBI materialized on Render; Linux `pysam` already in requirements. |
| Primer whole-genome specificity | Default is template-only; UCSC isPcr provider exists but is opt-in and deployment-gated. | Need Render-local `hg38.2bit` plus Linux `isPcr` smoke and licensing comfort. | UCSC/Kent binary approval, mounted hg38 asset. |
| CRISPR core guide design | Local deterministic SpCas9 guide enumeration and Hsu/MIT in-context scoring are live. | Advanced CRISPR predictors are unavailable/fallback by default. | Optional R/Bioconductor `crisprScore`, `Rscript`, and conda envs for RuleSet3/Lindel. |
| CRISPR off-target screening | Backend has an indexed SQLite provider; production `auto` currently reports mock fallback because no index artifact is mounted. | Need full-genome index build, checksum manifest, Render-local path. | Large private index artifact, Render disk/mount, env flip approval. |
| CRISPR screening primers | Backend designs primers for selected off-target windows; windows are only real when off-target sites and reference windows are real. | Depends on real off-target index and hg38 reference window. | Same as off-target index plus mounted hg38. |
| CRISPR outcomes | Web calls `/api/v1/crispr/tide`, but backend has no route. Frontend catches and returns sample outcome spectrum. | Need backend schema, route, service, tests, and FE contract mirrors. | No large asset for observed-only TIDE; optional Tracy/Lindel later. |
| CRISPR ssODN | Live for supported human SNVs when MANE GFF + hg38 are available; falls back to mock genomic window when unresolved. | Broaden source resolution and make UI label only true fallback states. | Mounted hg38/MANE for production; no new package. |
| Gene/protein viewer | Around-variant viewer can be source-backed; full-gene and scaffolded exon/conservation/protein/ClinVar tracks still use fixture/sample gaps. | Need live ClinVar gene-window hydration, local Pfam/UniProt protein features, optional AlphaMissense heatmap. | ClinVar VCF+TBI, Pfam/HMMER on Render disk, optional AlphaMissense TSV/index. |
| Alignment | `/align` and `/align/trace` exist; browser fallback remains. Reference accession search and WFA/consensus upgrades are not done. | Need sequence resolve endpoint and optional robust aligner packages. | Optional `pywfa`, `pyabpoa`, Tracy binary if approving robust engine/decompose phase. |
| AI gateway | Excluded by Steven for this audit. | Out of scope. | Out of scope. |

## Source Evidence

- `app/backend/app/schemas/workbench.py` already exposes `PrimerPair` thermo and
  placement fields plus `CrisprSsodnDesign.variant_genomic`.
- `app/backend/app/services/workbench_design.py` maps Primer3 fields into those
  contract fields and still appends "SNP masking was requested but is not yet
  applied."
- `app/web/components/workbench/primer/PrimerResultCard.tsx` still computes
  deterministic mock secondary-structure values and still says primer positions
  are pending backend.
- `app/backend/app/services/crispr_offtarget_screening.py` contains both
  `MockCasOffinderOffTargetProvider` and `IndexedSqliteCrisprOffTargetProvider`.
- `app/backend/app/services/crispr_offtarget_index.py` can inspect/build/query a
  local SQLite SpCas9 index and reports that request-time Supabase search and
  startup materialization are disabled.
- `app/backend/app/api/routes/health.py` exposes sanitized CRISPR off-target
  readiness and launch gates.
- `app/web/components/workbench/crispr/OutcomesTab.tsx` calls `analyzeTide()`;
  `app/web/lib/api.ts` catches any failure from `/api/v1/crispr/tide` and
  returns `CRISPR_TIDE_SAMPLE`.
- `app/backend/app/api/routes/workbench.py` exposes primer, CRISPR, off-target,
  screening-primer, ssODN, align, and trace routes, but no TIDE/outcomes route.
- `app/backend/app/services/gene_viewer.py` warns
  `clinvar_track_not_live_hydrated` in live transcript mode and sends full-gene
  requests through fixtures.
- `app/web/lib/workbench/gene-viewer-adapter.ts` fills exon/intron table and
  conservation from the RPE65 scaffold when the backend response lacks them.

## Work Already Ready Without External Approval

1. Replace primer `mockStruct()` display with live `PrimerPair` fields.
2. Render Primer3 position/genomic fields in the result card and copy payload.
3. Make the primer overlay coordinate-aware when backend placement fields exist,
   with an honest schematic fallback only when fields are absent.
4. Add a backend/frontend contract canary that fails if Workbench live responses
   expose stale "pending backend" fields in the UI model.
5. Add backend `/api/v1/crispr/tide` observed-only contract using existing AB1
   parse/alignment primitives, if Steven approves outcomes scope before the
   heavier Tracy/Lindel work.

## Work Requiring Approval Before Runtime Enablement

1. CRISPR off-target indexed provider: build a whole-genome SQLite artifact,
   copy it to Render persistent storage, verify health readiness, then change
   `CRISPR_OFFTARGET_PROVIDER` from `auto` to `indexed_sqlite`.
2. Primer SNP avoidance: materialize dbSNP VCF+TBI on Render and wire a
   fail-closed local SNP exclusion provider.
3. UCSC isPcr whole-genome primer specificity: install/provide the Linux `isPcr`
   binary, confirm Kent licensing comfort, and point it at mounted `hg38.2bit`.
4. CRISPR advanced scoring: install R/Bioconductor `crisprScore`, configure
   `Rscript`, and optionally configure RuleSet3/Lindel conda env paths.
5. Gene/protein live annotations: materialize ClinVar, Pfam/HMMER, and optional
   AlphaMissense assets before removing fixture/sample labels from those tracks.
