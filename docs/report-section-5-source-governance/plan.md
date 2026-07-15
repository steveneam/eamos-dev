# Report Section 5 Source Governance Plan

Status: superseded implementation plan. `DiseaseValidityDashboard` now owns the
coherent Section 5 surface. The retired standalone component paths below are
kept as historical rationale; use the live dashboard and current backend
profile before planning another change.

## Shared Decisions

Section 5 should read as a source-backed disease and curated-variant ledger, not
as a mixed collection of cards. MONDO, OMIM, Orphanet, MedGen, and HPO are
identifiers or ontologies. The clinical metrics are ClinGen Gene-Disease
Validity, GenCC assertion strength/count, HPO annotation support, ClinVar
classified-variant counts, and curated source freshness/provenance.

Every rendered row must carry source identity and launch metadata:
`source_id`, `source_version`, `source_url`, `license_gate`, `launch_gate`,
`public_serialization_allowed`, `match_level`, and provenance tags. The
frontend may sort, label, or hide rows, but it must not infer commercial status
from display text such as "OMIM".

## Task 1 - Harden Header Identifiers

Goal: make rsID and Ensembl transcript availability deterministic in the report
header.

Context: `VariantHeader` reads `report_profile.header`. The backend already has
`DbSnpLocalStore` for coordinate-to-rsID lookup and transcript aliases in the
coordinate/transcript model stores. Current reports can still miss these values
when ClinVar raw xrefs are absent, stale, or not copied into the header.

Relevant files:
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/services/dbsnp_local.py`
- `app/backend/app/services/gene_context_snapshot.py`
- `app/web/components/report/VariantHeader.tsx`
- `app/backend/tests/test_dbsnp_local_adapter.py`
- `app/backend/tests/test_variant_library_api.py`

Proposed approach: resolve `dbsnp_rsid` from ClinVar xrefs first, then local
dbSNP coordinate lookup using the canonical GRCh38 variant identity. Resolve
`ensembl_transcript` from `gene_context_snapshot.transcript_aliases` or the
transcript model store. Persist both into `report_profile.header` and invalidate
stale cached gene-context snapshots that predate transcript aliases.

Acceptance criteria:
- RPE65 c.260A>G displays `rs1645931040` and `ENST00000262340*` in Variant
  details without frontend-only inference.
- If dbSNP has no exact allele match, the header displays unavailable and the
  report warnings include the dbSNP miss reason.
- The header source/provenance path identifies whether rsID came from ClinVar or
  local dbSNP.

Verify:
- `pytest app/backend/tests/test_dbsnp_local_adapter.py app/backend/tests/test_variant_library_api.py`
- `npm --prefix app/web run lint`
- Browser check `/report?fixture=rpe65-negative`, expanded Variant details.

## Task 2 - Section 5 Data Contract

Goal: replace ad hoc Section 5 payloads with a typed source ledger for disease,
ontology, phenotype, and curated-variant facts.

Context: Section 5 currently combines `DiseaseSection`, `CuratedVariantsGrid`,
`AssociatedConditions`, and `GeneDiseaseBlock`. Some rows are real source-table
derived, while some labels/counts are fixture-style or not launch-gated.

Relevant files:
- `app/backend/app/schemas/run.py`
- `app/backend/app/services/clinical_source_tables.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/web/components/report/GeneDiseaseBlock.tsx`
- `app/web/components/report/AssociatedConditions.tsx`
- `app/web/components/report/CuratedVariantsGrid.tsx`

Proposed approach: add a typed Section 5 profile with:
- primary disease assertions from ClinGen Gene-Disease Validity and GenCC
- ontology crosswalk rows for MONDO, OMIM, Orphanet, MedGen, and HPO
- ClinVar curated-variant distribution rows with query scope and source counts
- source metadata per row, including free/pro and launch-gate tags
- explicit unavailable states when clinical source tables are fixture-scale

Acceptance criteria:
- MONDO is shown as an ontology/crosswalk source, not a metric.
- ClinGen/GenCC validity is the visible evidence metric.
- OMIM-derived identifiers and links carry a source tag and launch gate; public
  rendering can hide or downgrade them without changing component code.
- Copy/export output respects `public_serialization_allowed`.

Verify:
- Backend schema tests for Section 5 profile serialization.
- Frontend fixture test that Section 5 renders source chips and hides gated rows
  when launch filters are enabled.

## Task 3 - Curated Variant Distribution From Local ClinVar

Goal: make the curated variant distribution real and scope-aware.

Context: The gene viewer currently has bounded ClinVar markers. Section 5 shows
classified variant totals that must be backed by local ClinVar gene/range data
or explicitly marked fixture/unavailable.

Relevant files:
- `app/backend/app/services/clinvar_local.py`
- `app/backend/app/services/gene_viewer.py`
- `app/backend/app/services/clinical_source_tables.py`
- `app/web/components/report/CuratedVariantsGrid.tsx`

Proposed approach: implement a backend gene/range aggregation over local ClinVar
with exact transcript/gene scope, consequence buckets, clinical-significance
buckets, and provenance. Return density/count rows rather than every marker for
the first Section 5 pass; keep full marker browsing in the gene viewer.

Acceptance criteria:
- Counts are derived from source rows, not hardcoded fixtures.
- The payload includes query scope, total rows scanned, source version, and
  warnings for incomplete local assets.
- Large genes use aggregate buckets and do not create thousands of frontend DOM
  nodes.

Verify:
- Unit tests with the current local ClinVar fixture.
- Browser check for RPE65 and one larger-gene fixture/query.

## Task 4 - Section 5 UI Rebuild

Goal: make Section 5 scan like the in-silico table: sorted rows, source chips,
metric columns, and gated-source labels.

Context: The current Section 5 mixes prose, grids, condition cards, and a later
validity block. It should be one coherent disease-evidence surface.

Relevant files:
- `app/web/components/report/ReportClient.tsx`
- `app/web/components/report/GeneDiseaseBlock.tsx`
- `app/web/components/report/AssociatedConditions.tsx`
- `app/web/components/report/CuratedVariantsGrid.tsx`
- `app/web/components/report/CalibratedInSilicoTable.tsx`

Proposed approach: build a new Section 5 component with:
- top summary row: primary condition, inheritance, validity, source freshness
- source table: ClinGen, GenCC, MONDO, HPO, OMIM/Orphanet/MedGen identifiers
- curated variant distribution as a compact source-backed matrix
- condition rows sorted by validity, match level, and source priority
- `FREE`/`PRO`/`GATED` meta chips matching the in-silico source-chip pattern

Acceptance criteria:
- No row appears without source provenance.
- Launch-hidden rows leave an explicit "restricted source hidden" state when
  needed, not a blank gap.
- Mobile layout remains readable at 390 px and has no horizontal text overflow.

Verify:
- `npm --prefix app/web run lint`
- Browser screenshots at 390 px and 768 px.
- Existing report preflight at 390/768.

## Task 5 - Copy, Export, and Launch Filters

Goal: keep Section 5 display, copy, export, and launch filtering consistent.

Context: Section 5 has copy/export paths in `report-html` and `report-tsv`.
Those paths must not leak gated source text when public serialization is false.

Relevant files:
- `app/web/lib/report-html.ts`
- `app/web/lib/report-tsv.ts`
- `app/web/lib/report-export.ts`
- `app/web/components/report/ReportClient.tsx`

Proposed approach: route Section 5 copy/export through the same typed source
ledger used by the UI. Apply field-level filtering before HTML/TSV generation.

Acceptance criteria:
- Restricted OMIM/pro-source rows are hidden or reduced according to backend
  metadata.
- Source IDs and versions remain in internal/dev output.
- Public copy/export never includes fields marked not serializable.

Verify:
- Unit tests for public vs internal export.
- Manual browser copy check on Section 5.
