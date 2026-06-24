# Report Backend Launch and Source-Cache Readiness Design

Status: Draft

## Summary

Implement the remaining report launch-readiness backend data gaps as one bounded
backend readiness package:

1. Report data currency, source-version pins, and reliable gnomAD unavailable
   reasons.
2. Full live ClinGen VCEP Evidence Repository source-cache integration.
3. In-silico calibration population for report predictor rows.
4. A bounded ClinVar gene-distribution index for the curated variants grid.

These cover the Codex-owned P0.1, P0.2, P1.1, P1.2, P1.3, and P1.4 backend
items from `docs/report-launch-readiness/assignments.md` and the open Claude to
Codex CAR in `agent_handoff/CURRENT.md`. P0.3 and P1.5 are frontend failure-state
items and are tracked as coordination points only.

## Current State

The repo already has the core primitives:

- `app/backend/app/repos/source_cache_repo.py` stores versioned source-cache
  payloads with fresh/stale behavior.
- `app/backend/app/services/source_cache.py` defines
  `clingen_vcep_source_cache_key()` with CAID, ClinVar VCV, and HGVS precedence.
- `app/backend/app/tools/clingen.py` filters ClinGen rows through structured
  variant identity and returns `identity_match` metadata.
- `app/backend/app/schemas/run.py` has typed `EvidenceIdentityMatch`,
  `ExpertPanelSection`, `ComputationalPredictorRow`, and
  `CuratedVariantsDistribution` models.
- `app/backend/app/services/computational_calibration.py` centralizes REVEL,
  CADD, PrimateAI, SpliceAI, AlphaMissense, and ESM1b calibration thresholds.
- `app/backend/app/services/clinvar_local.py` can aggregate ClinVar records by
  gene, but `lookup_service.py` intentionally disables request-time aggregation
  through `clinvar_gene_distribution_excluded_pending_index`.
- `app/backend/app/services/report_data_currency.py` already builds sanitized
  report data-currency summaries and `lookup_service.py` populates
  `report_generated_at` and `report_data_currency`.
- `app/backend/app/services/population_frequency_section.py` and
  `variant_report_orchestrator.py` already support population-frequency
  `source_status` and `unavailable_reason` fields.

The missing work is not a new evidence model. It is materialization, bounded
lookup, report-path wiring, and test/live verification.

## Goals

- Expert-panel sections attach only source-backed ClinGen Evidence Repository
  records whose structured identity matches the requested variant.
- Expert-panel provenance includes source cache state, source version, fetched
  timestamp, source URL, and typed identity-match metadata.
- The report no longer shows the permanent expert-panel partial note when a live
  or local VCEP source-cache hit exists.
- Report payloads expose source freshness and source-version pins consistently
  enough for the frontend data-currency line and exports.
- gnomAD failures or no-hit cases surface a reliable source status,
  unavailable reason, and warning instead of a blank population section.
- In-silico rows carry calibrated label, bucket, method, and version wherever the
  backend has a supported predictor score.
- ClinVar curated-variants distribution is read from a bounded gene index rather
  than from a request-time whole-source scan.
- Empty, stale, missing, or not-ready source states remain explicit in warnings
  and source statuses.

## Non-Goals

- No deployment, environment flips, or Vercel/Render actions.
- No account-role or auth plumbing for predictor visibility.
- No new clinical interpretation beyond existing Eamos and source-backed fields.
- No hard-coded ABCA4, RPE65, BRCA1, or other per-gene special cases.
- No request-time whole-ClinVar or whole-ClinGen scans.
- No frontend redesign beyond the additive contract fields needed for mirrors.
- No implementation of frontend-only launch-readiness items such as the gene
  viewer error boundary or protein/snippet warning rendering.

## Design Principles

- Source-backed beats inferred. Source-asserted rows must preserve provenance and
  cannot be reconstructed from narrative text.
- Fail closed. Missing source cache, missing predictor assets, and absent ClinVar
  index rows return empty or limited sections with typed warnings.
- Bounded by construction. Request paths read precomputed records by source key,
  gene, variant ID, or indexed genomic coordinate.
- Additive contracts. Keep existing `warnings` and current payload shapes while
  adding typed fields or changing source status only where the schema already
  supports it.
- Shared contract first. Backend `run.py` and both frontend `backend.ts` mirrors
  stay byte-equivalent where the project expects it.

## Track 0: Data Currency, Source Versions, and gnomAD Status

This track makes the later source-cache work visible and auditable in the report.

### Proposed Flow

1. Treat `report_generated_at` and `report_data_currency` as the report-level
   freshness contract.
2. Ensure every report source that can provide a version or upstream date passes
   it into `EvidenceSourceSummary.summary["freshness"]`, source version fields,
   or the existing report data-currency builder inputs.
3. Populate `VariantReportHeader.updated_at` from the latest real source
   timestamp, falling back to `report_generated_at`.
4. Keep `ReportDataCurrencySource` sanitized: no local paths, object URIs,
   secrets, raw source rows, or operator-only paths.
5. Ensure population frequency report sections always carry a backend-owned
   `source_status`.
6. If gnomAD data is missing, failed, stale, or has no frequency metrics, set a
   machine-readable `unavailable_reason` and source warning.
7. Preserve source versions such as gnomAD release, ClinGen source version,
   ClinVar release, and predictor calibration/source versions so frontend and
   exports cite versions rather than only fetched timestamps.

### Contract

Use existing fields unless a gap appears during implementation:

- `ReportPayload.report_generated_at`
- `ReportPayload.report_data_currency`
- `VariantReportHeader.updated_at`
- `PopulationFrequencyReportSection.source_status`
- `PopulationFrequencyReportSection.unavailable_reason`
- `PopulationFrequencyReportSection.warnings`
- `SourceProvenance.version`
- `EvidenceSourceSummary.source_version`

### Acceptance Boundary

The frontend should be able to render data currency and population unavailable
states from backend-owned fields, with no string inference from empty rows.

## Track 1: ClinGen VCEP Source Cache

### Proposed Flow

1. Build request aliases from the resolved variant: CAID if present, ClinVar VCV,
   genomic HGVS, transcript HGVS, normalized cDNA, genomic variant ID, and
   assertion ID when an explicit selected candidate supplies one.
2. Compute source-cache keys with `clingen_vcep_source_cache_key()`.
3. Query `SourceCacheRepo` for fresh ClinGen VCEP rows before live network calls.
4. On fresh hit, validate the cached record through the same identity guard used
   by `ClingenTool`.
5. On fresh miss, use the existing local ClinGen SQLite search if enabled.
6. On allowed live fallback, fetch bounded Evidence Repository summary rows,
   fetch or preserve detailed assertion payloads when available, then upsert the
   source cache.
7. Return `ToolResult` with `status` of `cache`, `local`, `live`, `stale`, or
   `missing`; include source version, fetched timestamp, source URL, and
   `identity_match`.
8. `variant_report_orchestrator._build_expert_panel()` consumes the typed
   `ExpertPanelSection` only when `identity_match.auto_attach_allowed` is true.

### Cache Record Shape

Use the existing `source_cache` table unless a migration is strictly required.
The cached summary should contain:

- `expert_panel`: existing `ExpertPanelSection` shape.
- `identity_match`: existing `EvidenceIdentityMatch` shape.
- `assertion_id`, `caid`, `clinvar_variation_id`, `gene`, and normalized HGVS
  aliases.
- `source_version`, `fetched_at`, `source_url`, and raw payload hash or raw
  reference when available.
- Source warnings such as stale-on-failure or partial-detail fetch.

### Identity Contract

Only these tiers can attach automatically:

- `assertion_id`
- `caid`
- `clinvar_variation_id`
- `vrs`
- `spdi`
- `genomic_hgvs`
- `transcript_hgvs`

`candidate_text` can be returned as a candidate or warning, but must not populate
VCEP criteria or source-asserted ACMG rows.

## Track 2: In-Silico Calibration Population

### Proposed Flow

1. Keep `computational_calibration.py` as the single calibration policy source.
2. Ensure every predictor row that reaches `ComputationalDeepDiveSection` passes
   through `_computational_row_from_dict()` or equivalent calibration fill logic.
3. Normalize common names before calibration:
   - `CADD PHRED` and `CADD` route to CADD PHRED calibration.
   - `CI-SpliceAI` uses its own source metadata and should not masquerade as
     Walker 2023 SpliceAI unless the row explicitly maps to that policy.
   - `AlphaMissense`, `ESM1b`, `REVEL`, and `SpliceAI` keep existing methods and
     versions.
4. Preserve null calibration fields for unsupported or uncalibrated tools such
   as MetaLR, CAPICE, PrimateAI-3D, GPN-MSA, and Pangolin until a reviewed
   calibration policy exists.
5. Keep launch-gate/license metadata from local predictor adapters.
6. Use backend values as authoritative; frontend should display placeholders but
   not infer calibration buckets from raw scores.

### Population Boundary

This task is about report population, not acquiring every possible predictor
asset. If a predictor source is not materialized, the row should be absent or
not-ready with a source warning. If a supported score exists, calibration fields
must be populated.

## Track 3: ClinVar Gene-Distribution Index

### Proposed Flow

1. Add a build/materialization path that reads the ClinVar local VCF or imported
   records once and writes a compact gene index.
2. Index rows by normalized gene symbol.
3. Store only aggregate counts and query-variant lookup metadata needed by
   `CuratedVariantsDistribution`, not raw ClinVar rows.
4. Add settings for the index path and manifest path, parallel to existing local
   evidence asset settings.
5. Change `lookup_service._clinvar_distribution_runtime_path()` to return the
   ready index path only when the local evidence gate allows lookup and the
   index preflight passes.
6. Update `build_clinvar_gene_distribution()` or add a reader wrapper so lookup
   reads one bounded gene aggregate instead of scanning the VCF.
7. If the index is missing or stale, keep returning `None` plus
   `clinvar_gene_distribution_excluded_pending_index`.

### Index Record Shape

Each gene record should contain:

- `gene`
- `cells`
- `row_totals`
- `total`
- source status, source ID, source version, source URL
- public serialization, launch gate, and license gate fields
- optional query-variant index map keyed by genomic variant ID or VCV accession
  for `query_cell`, `query_accession`, and `query_classification`
- warnings and manifest provenance

The index should be SQLite or JSONL depending on existing local evidence
conventions. SQLite is preferred if query-variant maps are large; JSONL is
acceptable if records remain small and read by direct gene key.

## Cross-Track Interfaces

### Report Payload

No top-level report shape rewrite is needed. The three tracks update existing
fields:

- `report_profile.expert_panel`
- `report_profile.computational_deep_dive`
- `curated_variants_distribution`
- `report_generated_at`
- `report_data_currency`
- `report_profile.population_frequency`
- section-local warnings and source provenance
- source version pins that can feed the report data currency work

### Health and Preflight

Provider-cache or source-asset health should expose sanitized readiness:

- ClinGen VCEP source cache row counts, fresh/stale counts, source version, and
  ready/not-ready state.
- Predictor runtime readiness and which predictor families can populate
  calibrated rows.
- ClinVar gene-distribution index status, gene count, source version, checksum,
  and no local paths or raw rows in public output.
- gnomAD source status and unavailable reasons when population data is missing
  or failed.

### Frontend Mirrors

The backend should keep using existing schema fields where possible. If new
fields are needed, update:

- `app/web/lib/backend.ts`
- `app/frontend/src/lib/backend.ts`
- frontend contract tests

## Rollout

1. Land backend and contract tests locally with fixtures.
2. Run focused backend tests for report data currency, population frequency,
   ClinGen, computational annotations, orchestration, ClinVar local adapter,
   health/preflight, and frontend contract.
3. Run frontend lint and type mirrors.
4. Browser-verify local report behavior where local data exists.
5. Browser-verify live deployment after a future deploy, especially for ABCA4
   and a cross-gene sweep.

## Open Questions

- Should the ClinGen live path cache only summary rows, or fetch and cache full
  classification detail pages when the Evidence Repository exposes them?
- Should ClinVar gene-distribution index live beside the existing ClinVar local
  asset or as a generated artifact uploaded through the source-artifact flow?
- Which non-ABCA4 cross-gene regression set should be canonical for this slice:
  RPE65, USH2A, BRCA1, HBB, BRAF, or a small fixed mix?
- Are the existing report data-currency fields sufficient for P0.1/P1.4, or does
  the frontend need one more explicit source-version map?
