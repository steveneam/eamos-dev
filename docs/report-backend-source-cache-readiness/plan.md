# Report Backend Launch and Source-Cache Readiness Plan

Status: Complete with browser residual; ClinVar generated artifact live on SG - 2026-06-28 - Codex

## Goal

Prepare the next implementation session to finish the Codex-owned report
launch-readiness backend gaps in small, verifiable slices:

- P0.1: report data currency, report-generated timestamps, and freshness fields,
- P0.2: reliable gnomAD source status and unavailable reason,
- P1.1: live/source-cache ClinGen VCEP integration,
- P1.2: in-silico calibration population, and
- P1.3: ClinVar gene-distribution index,
- P1.4: source version pins.

P0.3, the Claude-side parts of P1.2/P1.3, and P1.5 remain frontend coordination
items. This plan includes the backend fields and warnings that unblock them.

## Guardrails

- Do not deploy.
- Do not run `vercel` or `vc` from `app/web`.
- Keep root `.vercel` linked to `eamos-dev`; keep `app/web/.vercel` absent.
- Use explicit pathspecs if committing later.
- Do not stage held handoff, proprietary, report-launch, tmp, or tooling files
  unless Steven explicitly asks.
- Preserve source provenance, license gates, launch gates, and public
  serialization metadata.
- Keep warnings as compatibility fields when adding typed state.

## Task 0: Discovery and Fixtures

Status: COMPLETE - 2026-06-24 - Codex.

Evidence:

- Read the launch-readiness assignments, source-cache readiness design/spec/plan,
  report evidence framework design/spec, handoff CARs, and risks.
- Ran focused source searches across data currency, gnomAD population status,
  ClinGen source-cache/identity, in-silico calibration, and ClinVar
  gene-distribution paths.
- Confirmed current controls in tests/fixtures: ABCA4 `c.5461-10T>C` as the
  ClinGen VCEP positive control, ABCA4/RPE65 no-identity or neighboring ClinGen
  controls, RPE65 `c.260A>G` for gnomAD-negative/local-evidence regression, and
  USH2A `c.2276G>T` for gnomAD-positive regression coverage.
- Confirmed `SourceCacheRepo.upsert()` is already available and used by
  `LookupService` for selected source-cache-backed lookups, including ClinGen.

Files changed:

- `docs/report-backend-source-cache-readiness/plan.md` status/checklist update
  only. No source edits for Task 0 discovery.

Tests run:

- `python -m pytest tests/test_report_data_currency.py tests/test_variant_report_orchestration.py tests/test_clingen_local.py tests/test_computational_calibration.py tests/test_clinvar_local_adapter.py -q`
  from `app/backend` - passed, 73 tests.

Remaining gap:

- None for discovery. Proceed to Task 1 validation/tightening for data currency,
  source versions, and gnomAD status.

Goal: Establish exact current behavior and fixture coverage before source edits.

Context:

- The open CAR in `agent_handoff/CURRENT.md` names these items as Codex-owned.
- Existing source-cache and calibration primitives are already present.
- Some report-framework files are dirty from the previous backend pass.

Files:

- `docs/report-launch-readiness/assignments.md`
- `docs/report-evidence-framework/spec.md`
- `docs/report-evidence-framework/design.md`
- `app/backend/tests/test_clingen_local.py`
- `app/backend/tests/test_tool_invariants.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_clinvar_local_adapter.py`

Actions:

- Run focused searches for ClinGen, source-cache, computational calibration, and
  ClinVar distribution paths.
- Include report data-currency and population frequency source-status paths in
  the same discovery pass.
- Record current ABCA4, RPE65, USH2A, and one negative neighboring allele
  behavior.
- Identify whether the source-cache repo has write/upsert support usable for
  ClinGen live fetches.

Acceptance:

- Current behavior is known before edits.
- Test controls are selected.
- No code changes yet.

Verify:

```powershell
python -m pytest tests/test_report_data_currency.py tests/test_variant_report_orchestration.py tests/test_clingen_local.py tests/test_computational_calibration.py tests/test_clinvar_local_adapter.py -q
```

## Task 1: Data Currency, Source Versions, and gnomAD Status

Status: COMPLETE - 2026-06-24 - Codex.

Evidence:

- `LookupService` already sets `report_generated_at` and
  `report_data_currency` after evidence collection, then builds the typed report
  profile from the populated payload.
- `VariantReportDataOrchestrator` already sets `VariantReportHeader.updated_at`
  from the latest real evidence timestamp with a fallback to
  `report_generated_at`.
- `report_data_currency.py` already sanitizes public fields and preserves source
  versions from source summaries, source-cache rows, gnomAD datasets, and expert
  panel provenance without exposing local paths or object URIs.
- `report_call_cards.py` and `population_frequency_section.py` already map
  gnomAD not-found, source-failure, stale-cache, missing-detail, and
  no-frequency-metric states to backend-owned `source_status`,
  `unavailable_reason`, and warnings.
- Added focused regressions proving lookup payload freshness/version fields and
  gnomAD stale-on-failure propagation into the population section, call card,
  and report data-currency source row.

Files changed:

- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_source_cache.py`
- `docs/report-backend-source-cache-readiness/plan.md`

Tests run:

- `python -m pytest tests/test_report_data_currency.py tests/test_variant_report_orchestration.py tests/test_source_cache.py -q`
  from `app/backend` - passed, 27 tests.

Remaining gap:

- None for Task 1. P1.4 source-version pins remain preserved through existing
  fields; future tasks may add more source-specific versions as new caches or
  indexes land.

Goal: Close the broader backend CAR prerequisites before the source-cache/index
work depends on them.

Files:

- `app/backend/app/services/report_data_currency.py`
- `app/backend/app/services/population_frequency_section.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/services/report_call_cards.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/schemas/run.py`
- `app/backend/tests/test_report_data_currency.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_source_cache.py`
- `app/web/lib/backend.ts`
- `app/frontend/src/lib/backend.ts`

Actions:

- Confirm `report_generated_at` and `report_data_currency` are populated after
  source evidence collection.
- Ensure `VariantReportHeader.updated_at` uses latest real source timestamp.
- Preserve gnomAD, ClinGen, ClinVar, and predictor source versions for payload,
  provenance, and exports.
- Ensure gnomAD missing, failed, stale, not-found, and no-frequency-metrics cases
  set `source_status`, `unavailable_reason`, and warnings.
- Keep call-card and section-signal source statuses aligned with the population
  section.

Acceptance:

- Data-currency output is sanitized and version-aware.
- Population frequency never renders as an unexplained blank when backend source
  state is known.
- Existing gnomAD positive and negative controls still distinguish source absence
  from source failure.

Verify:

```powershell
python -m pytest tests/test_report_data_currency.py tests/test_variant_report_orchestration.py tests/test_source_cache.py -q
```

## Task 2: ClinGen Source-Cache Reader and Writer

Status: COMPLETE - 2026-06-24 - Codex.

Evidence:

- `SourceCacheRepo.upsert()` already supports versioned ClinGen cache writes, and
  `LookupService` already reads fresh ClinGen VCEP source-cache hits before live
  Evidence Repository calls.
- Cache keys already follow the planned CAID, ClinVar VCV, then HGVS precedence
  through `clingen_vcep_source_cache_key()`.
- Added a cached ClinGen identity guard:
  `cached_clingen_result_matches_variant()` revalidates cached rows through the
  same ClinGen identity matching rules using either typed `identity_match`
  metadata or cached raw records.
- `LookupService` now ignores identity-mismatched fresh ClinGen cache hits before
  producer execution and refuses identity-mismatched stale fallback rows, while
  preserving a compatibility warning.
- Added a regression proving an identity-mismatched cached VCEP panel does not
  attach and live/local producer execution continues.

Files changed:

- `app/backend/app/tools/clingen.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/tests/test_source_cache.py`
- `docs/report-backend-source-cache-readiness/plan.md`

Tests run:

- `python -m pytest tests/test_source_cache.py tests/test_clingen_local.py -q`
  from `app/backend` - passed, 23 tests.

Remaining gap:

- None for Task 2. Task 3 still owns report-path expert-panel behavior and
  lookup-section partial/empty states.

Goal: Make ClinGen VCEP cacheable and readable by exact variant identity.

Files:

- `app/backend/app/tools/clingen.py`
- `app/backend/app/services/source_cache.py`
- `app/backend/app/repos/source_cache_repo.py`
- `app/backend/tests/test_clingen_local.py`
- `app/backend/tests/test_source_cache.py`

Actions:

- Add or reuse source-cache upsert for ClinGen `ToolResult` payloads.
- Read fresh source-cache hits before live Evidence Repository calls.
- Validate cached rows through `_filter_variant_identity_records()`.
- Preserve stale-on-failure behavior with explicit warnings.
- Store source version, source URL, fetched timestamp, and identity metadata.

Acceptance:

- Fresh cache hit returns `status="cache"` or the agreed cache status and does
  not call live network.
- Stale cache hit after live failure returns stale status plus warning.
- Narrative-only cached candidates do not attach.
- Cache keys follow CAID, VCV, HGVS precedence.

Verify:

```powershell
python -m pytest tests/test_source_cache.py tests/test_clingen_local.py -q
```

## Task 3: ClinGen Report Integration

Status: COMPLETE - 2026-06-24 - Codex.

Evidence:

- Existing report orchestration already carries ClinGen `identity_match` into
  `ExpertPanelSection.provenance`, source version, source URL, freshness, and
  stale-on-failure state.
- Existing lookup-section contract returns `clingen_vcep` as `available` with a
  typed expert-panel payload when an identity-matched panel is present, and
  `partial`/`missing` with warnings when only clinical-consensus fallback exists.
- Added a report-builder guard so `ExpertPanelSection` is emitted only when
  `EvidenceIdentityMatch.auto_attach_allowed` is true.
- Added a regression proving a ClinGen result with expert-panel narrative but no
  typed identity match does not attach to the report.

Files changed:

- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `docs/report-backend-source-cache-readiness/plan.md`

Tests run:

- `python -m pytest tests/test_variant_report_orchestration.py tests/test_lookup_section_fetch_contract.py tests/test_frontend_contract.py -q`
  from `app/backend` - passed, 368 tests.

Remaining gap:

- Backend Task 3 is complete. The visible frontend partial-note copy still says
  the Evidence Repository source-cache is not wired; that is a frontend
  coordination follow-up unless Steven asks Codex to edit it.

Goal: Ensure source-backed VCEP rows populate report expert-panel sections and
partial notes become conditional.

Files:

- `app/backend/app/tools/clingen.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/services/lookup_sections.py`
- `app/backend/app/schemas/run.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_lookup_section_fetch_contract.py`
- `app/web/lib/backend.ts`
- `app/frontend/src/lib/backend.ts`

Actions:

- Ensure `ExpertPanelSection` is emitted only for identity-matched source rows.
- Ensure `provenance.identity_match` flows from `EvidenceSourceSummary` to the
  report profile.
- Ensure lookup section responses distinguish available, partial, stale, empty,
  and error states without changing frontend assumptions unexpectedly.
- Update TypeScript mirrors only if the Python schema changes.

Acceptance:

- Positive control attaches the expected ClinGen assertion with typed identity
  provenance.
- Negative controls return missing/partial with warnings and no criteria.
- Existing frontend expert-panel rendering does not need to infer source state.

Verify:

```powershell
python -m pytest tests/test_variant_report_orchestration.py tests/test_lookup_section_fetch_contract.py tests/test_frontend_contract.py -q
```

## Task 4: In-Silico Calibration Population

Status: COMPLETE - 2026-06-24 - Codex.

Evidence:

- `computational_calibration.py` is the single calibration policy source for
  REVEL, CADD/CADD PHRED, SpliceAI, AlphaMissense, and ESM1b.
- `computational_annotations.py` and
  `variant_report_orchestrator._computational_row_from_dict()` already populate
  calibrated label, bucket, method, and version for supported numeric scores.
- Unsupported/unreviewed predictors such as MetaLR, PrimateAI-3D, phyloP, and
  unknown engines already return explicit null calibration fields.
- `acmg_points_engine.py` already derives PP3/BP4 strength from backend
  calibration labels/methods and preserves source/version/SVI references.
- Existing tests cover CADD alias normalization, supported predictor boundaries,
  unsupported nulls, report-row population, and PP3/BP4 computation.

Files changed:

- `docs/report-backend-source-cache-readiness/plan.md` status/checklist update
  only. No Task 4 source edits were needed.

Tests run:

- `python -m pytest tests/test_computational_calibration.py tests/test_tool_invariants.py tests/test_variant_report_orchestration.py tests/test_acmg_points_engine.py -q`
  from `app/backend` - passed, 112 tests.

Remaining gap:

- None for Task 4. Missing predictor assets should continue to produce absent or
  not-ready rows with source warnings rather than fabricated calibration data.

Goal: Populate backend calibration fields for every supported report predictor
row with a numeric score.

Files:

- `app/backend/app/services/computational_calibration.py`
- `app/backend/app/tools/computational_annotations.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/services/acmg_points_engine.py`
- `app/backend/tests/test_computational_calibration.py`
- `app/backend/tests/test_tool_invariants.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_acmg_points_engine.py`
- `app/web/lib/backend.ts`
- `app/frontend/src/lib/backend.ts`

Actions:

- Audit every predictor row constructor.
- Normalize aliases such as `CADD PHRED` and `CADD`.
- Apply `calibration_field_values()` consistently.
- Preserve null calibration for unsupported tools.
- Ensure PP3/BP4 computed rows consume backend calibration, not UI-derived
  display text.

Acceptance:

- Supported predictor rows carry label, bucket, method, and version.
- Unsupported predictor rows have explicit nulls.
- ACMG PP3/BP4 rows remain deterministic and source-backed.
- Launch-gate and license metadata remain intact.

Verify:

```powershell
python -m pytest tests/test_computational_calibration.py tests/test_tool_invariants.py tests/test_variant_report_orchestration.py tests/test_acmg_points_engine.py -q
```

## Task 5: ClinVar Gene-Distribution Index

Status: COMPLETE - 2026-06-24 - Codex.

Evidence:

- Added a SQLite ClinVar gene-distribution materializer and bounded reader in
  `clinvar_local.py`; request-path reads fetch one gene aggregate plus one
  optional exact query-variant row and do not scan the ClinVar VCF/table.
- `LookupService` now removes the
  `clinvar_gene_distribution_excluded_pending_index` boundary only when local
  evidence lookup is enabled and the generated index passes readiness
  inspection; missing or malformed indexes preserve the existing warning.
- `CuratedVariantsDistribution` from the index carries cells, row totals,
  totals, source status, source ID/version/URL, public serialization metadata,
  launch/license gates, warnings/status notes, and exact query-variant cell,
  accession, and classification metadata when indexed.
- Provider-cache health and source-asset preflight now expose sanitized
  `clinvar_gene_distribution_index` status without local paths, object URIs,
  secrets, or raw ClinVar rows.

Files changed:

- `app/backend/app/services/clinvar_local.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/core/config.py`
- `app/backend/app/api/routes/health.py`
- `app/backend/app/cli/eamos_source_asset_preflight.py`
- `app/backend/tests/test_clinvar_local_adapter.py`
- `app/backend/tests/test_health_api.py`
- `app/backend/tests/test_source_asset_preflight_cli.py`
- `docs/report-backend-source-cache-readiness/plan.md`

Tests run:

- `python -m pytest tests/test_clinvar_local_adapter.py -q` from
  `app/backend` - passed, 15 tests.
- `python -m pytest tests/test_health_api.py -q` from `app/backend` -
  passed, 23 tests.
- `python -m pytest tests/test_source_asset_preflight_cli.py::test_source_asset_preflight_reports_guarded_readiness tests/test_source_asset_preflight_cli.py::test_source_asset_preflight_reports_clinvar_gene_index_ready_without_paths -q`
  from `app/backend` - passed, 2 tests.
- `python -m pytest tests/test_clinvar_local_adapter.py tests/test_health_api.py tests/test_source_asset_preflight_cli.py -q`
  from `app/backend` - passed, 50 tests.

Remaining gap:

- None for Task 5. Operational deployment still requires generating/syncing the
  index artifact to the runtime disk, but the request path fails closed with the
  existing warning until that artifact is ready.

Goal: Replace the `clinvar_gene_distribution_excluded_pending_index` boundary
with a bounded gene-index reader when the index is present.

Files:

- `app/backend/app/services/clinvar_local.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/core/config.py`
- `app/backend/app/api/routes/health.py`
- `app/backend/app/cli/eamos_source_asset_preflight.py`
- new or existing ClinVar materializer CLI/service
- `app/backend/tests/test_clinvar_local_adapter.py`
- `app/backend/tests/test_health_api.py`
- `app/backend/tests/test_source_asset_preflight_cli.py`

Actions:

- Choose SQLite or JSONL index format.
- Materialize per-gene cells, row totals, total, source metadata, warnings, and
  optional query-variant lookup metadata.
- Add sanitized inspect/preflight output.
- Gate lookup on local evidence settings plus index readiness.
- Keep the existing exclusion warning when not ready.

Acceptance:

- Lookup reads a single bounded gene aggregate when ready.
- Missing index preserves current warning behavior.
- No local path, object URI, secret, or raw ClinVar row leaks.
- Query variant cell is populated when the index has the variant.

Verify:

```powershell
python -m pytest tests/test_clinvar_local_adapter.py tests/test_health_api.py tests/test_source_asset_preflight_cli.py -q
```

## Task 6: Cross-Gene Regression Sweep

Status: COMPLETE WITH BROWSER RESIDUAL - 2026-06-24 - Codex.

Evidence:

- Existing cross-gene backend regressions cover ABCA4 exact VCEP identity,
  narrative/neighboring-variant rejection, no-identity expert-panel
  non-attachment, RPE65/USH2A/BRCA1/RPGRIP1 fixture non-bleed, gnomAD no-hit
  and source-failure states, and explicit population-frequency unavailable
  reasons.
- `ABCA4 c.5234T>A` from this task list is not present in the current fixtures;
  the available ABCA4 protein/localization control is `ABCA4 c.5435T>A`
  (`p.Ile1812Asn`), and that backend gene-viewer fixture test passed.
- Browser verification on `http://localhost:3001/report?gene=ABCA4&cdna=c.5435T%3EA`
  rendered the local report with ABCA4 gene context and full protein
  architecture/features on desktop and mobile. Screenshots saved to
  `.tmp/task6-abca4-report-desktop.png` and
  `.tmp/task6-abca4-report-mobile.png`.
- The browser check also found local `/api/v1/viewer` requests returning HTTP
  500 while the report fallback still rendered the protein panel. This remains
  a P0.3/frontend-failure-boundary coordination residual unless Steven asks
  Codex to take the viewer endpoint/fallback lane.

Files changed:

- `docs/report-backend-source-cache-readiness/plan.md` status/checklist update
  only. No Task 6 source edits were needed beyond Tasks 1-5.

Tests and checks run:

- `python -m pytest tests/test_clingen_local.py::test_clingen_local_prefers_exact_variant_identity_over_narrative_mentions tests/test_variant_report_orchestration.py::test_lookup_clingen_identity_match_flows_into_expert_panel_provenance tests/test_variant_report_orchestration.py::test_lookup_clingen_expert_panel_without_identity_match_does_not_attach tests/test_variant_report_orchestration.py::test_lookup_non_rpe65_variants_degrade_without_rpe65_fixture_bleed tests/test_source_cache.py::test_clingen_vcep_lookup_rejects_identity_mismatched_source_cache tests/test_source_cache.py::test_arbitrary_gnomad_no_hit_is_not_persisted_as_fresh_success tests/test_gnomad_tool.py::test_gnomad_live_fallback_does_not_attach_mismatched_fixture_detail tests/test_gnomad_tool.py::test_gnomad_live_no_hit_does_not_attach_fixture_metrics tests/test_population_frequency_section.py -q`
  from `app/backend` - passed, 12 tests.
- `python -m pytest tests/test_gene_viewer.py::test_source_backed_provider_uses_curated_fixture_for_full_gene_until_live_hydration -q`
  from `app/backend` - passed, 1 test.
- `npm --prefix app/web run lint` from repo root - passed.
- `git diff --check -- app/backend/app/services/clinvar_local.py app/backend/app/services/lookup_service.py app/backend/app/core/config.py app/backend/app/api/routes/health.py app/backend/app/cli/eamos_source_asset_preflight.py app/backend/tests/test_clinvar_local_adapter.py app/backend/tests/test_health_api.py app/backend/tests/test_source_asset_preflight_cli.py docs/report-backend-source-cache-readiness/plan.md`
  from repo root - passed with Git line-ending warnings only.

Remaining gap:

- Browser residual: local `/api/v1/viewer` returned HTTP 500 for the ABCA4
  around-variant viewer request, although the report page rendered the protein
  architecture from fallback/report data. This is recorded under the broader
  P0.3 frontend coordination lane unless Steven asks otherwise.

Goal: Prove the three tracks are gene-agnostic and do not bleed source rows
between variants.

Controls:

- `ABCA4 c.5461-10T>C`: ClinGen VCEP positive control.
- `ABCA4 c.5234T>A`: limitations/protein-localization browser check.
- `RPE65 c.260A>G`: gnomAD-negative and local-evidence regression.
- `USH2A c.2276G>T`: gnomAD-positive regression.
- A gnomAD no-hit or source-failure fixture: unavailable reason regression.
- One neighboring ClinGen allele or no-identity candidate.

Actions:

- Run backend lookup/report tests for each control.
- Run browser verification on `http://localhost:3001` if the local app can show
  the relevant report state.
- If local protein view remains bare but live deployment has the full view, use
  live verification only for the protein visualization claim.

Acceptance:

- No exact-source section is populated from narrative or neighboring variants.
- Supported predictor rows are calibrated where data exists.
- ClinVar grid is populated only when the index is ready.
- Empty and partial states are explicit.

Verify:

```powershell
npm --prefix app/web run lint
git diff --check
node scripts/eamos-web-boundary.mjs
```

## Task 7: Docs and Handoff

Goal: Mark the next-session outcome accurately without overstating partial work.

Files:

- `docs/report-backend-source-cache-readiness/plan.md`
- `docs/report-evidence-framework/plan.md`
- `agent_handoff/CURRENT.md` only if Steven wants handoff updates

Actions:

- Update this plan task statuses after implementation.
- Mark any still-partial bucket explicitly.
- Record verification commands and browser checks.
- Do not stage unrelated held handoff/proprietary/report-launch/tmp/tooling
  files.

Acceptance:

- Docs distinguish complete, partial, and deferred work.
- Final status includes exact tests run and anything not run.

Status: COMPLETE - 2026-06-24 - Codex.

Evidence:

- This running plan now records Tasks 0-6 with explicit complete/partial status,
  dates, files changed, tests run, and remaining gaps.
- `docs/report-evidence-framework/plan.md` was reconciled to the current ABCA4
  browser evidence: the available fixture-backed browser control is
  `ABCA4 c.5435T>A`, not `ABCA4 c.5234T>A`.
- `agent_handoff/CURRENT.md` was not edited because this task scopes that file
  to "only if Steven wants handoff updates"; no such handoff update was
  requested.
- No unrelated held handoff/proprietary/report-launch/tmp/tooling files were
  staged; no commit, push, or deploy was performed.

Files changed:

- `docs/report-backend-source-cache-readiness/plan.md`
- `docs/report-evidence-framework/plan.md`

Tests run:

- Documentation-only task closeout. Implementation verification is recorded in
  Tasks 1-6 above, including focused backend tests, `npm --prefix app/web run
  lint`, `git diff --check`, and browser verification on
  `http://localhost:3001`.

Remaining gap:

- Browser residual remains: the local ABCA4 report rendered the full protein
  architecture, but the supporting `/api/v1/viewer` request returned HTTP 500.
  Keep this as P0.3/frontend coordination unless Steven asks Codex to take it.
- Operational artifact gap remains: the ClinVar gene-distribution SQLite index
  now has materializer/reader/health/preflight support, but a real runtime
  artifact must still be generated and synced for deployed environments.

## Follow-up: Operational ClinVar Artifact Lane

Status: LIVE SG ARTIFACT SEEDED AND READY - 2026-06-28 - Codex.

Evidence:

- `inspect_clinvar_gene_distribution_index()` now fails closed unless the SQLite
  gene-distribution index and the configured sidecar manifest are both present
  and matching the expected artifact identity, upstream source, schema version,
  byte size, and SHA-256 checksum.
- Lookup gating still preserves
  `clinvar_gene_distribution_excluded_pending_index` when the index is missing,
  malformed, or generated without the sidecar manifest; a bare SQLite file is
  not treated as deploy-ready.
- The materializer service also validates the manifest when an index already
  exists and `force=False`, so an existing bare SQLite file cannot bypass the
  fail-closed readiness check.
- Added an explicit operator materialization CLI that builds the SQLite index
  and manifest from a local ClinVar VCF, emits sanitized JSON readiness output,
  and performs no startup download, request-time materialization, network fetch,
  patient-data access, local-path emission, object-URI emission, secret emission,
  or raw-row emission.
- Provider-cache health and source-asset preflight ready-state tests now require
  a matching manifest beside the index.

Files changed:

- `app/backend/app/services/clinvar_local.py`
- `app/backend/app/cli/eamos_clinvar_gene_distribution_materialize.py`
- `app/backend/tests/test_clinvar_local_adapter.py`
- `app/backend/tests/test_health_api.py`
- `app/backend/tests/test_source_asset_preflight_cli.py`
- `docs/report-backend-source-cache-readiness/plan.md`

Tests and checks run:

- `python -m pytest tests/test_clinvar_local_adapter.py -q` from `app/backend`
  - failed once on a missing `json` test import, then passed, 16 tests; rerun
  after the existing-index materializer fix also passed, 16 tests.
- `python -m pytest tests/test_health_api.py::test_provider_cache_health_returns_sanitized_empty_aggregates tests/test_health_api.py::test_provider_cache_health_reports_clinvar_gene_index_ready_without_paths -q`
  from `app/backend` - passed, 2 tests.
- `python -m pytest tests/test_source_asset_preflight_cli.py::test_source_asset_preflight_reports_guarded_readiness tests/test_source_asset_preflight_cli.py::test_source_asset_preflight_reports_clinvar_gene_index_ready_without_paths -q`
  from `app/backend` - passed, 2 tests.
- `python -m pytest tests/test_clinvar_local_adapter.py tests/test_health_api.py tests/test_source_asset_preflight_cli.py -q`
  from `app/backend` - timed out after 304 seconds with no useful pytest
  output; rerun by file to isolate the slow preflight suite.
- `python -m pytest tests/test_health_api.py -q` from `app/backend` -
  passed, 23 tests.
- `python -m pytest tests/test_source_asset_preflight_cli.py -q` from
  `app/backend` - passed, 12 tests.
- `python -m py_compile app\cli\eamos_clinvar_gene_distribution_materialize.py`
  from `app/backend` - passed.
- `python -m app.cli.eamos_clinvar_gene_distribution_materialize --from-vcf app/fixtures/data_sources/clinvar_tiny.vcf --output <temp>\index.sqlite --manifest <temp>\manifest.json --force --compact --require-ready`
  from `app/backend` - passed with sanitized ready output.
- `git diff --check -- app/backend/app/services/clinvar_local.py app/backend/tests/test_clinvar_local_adapter.py app/backend/tests/test_health_api.py app/backend/tests/test_source_asset_preflight_cli.py`
  from repo root - passed with Git line-ending warnings only.
- `npm --prefix app/web run lint` from repo root - passed.

Remaining gap:

- A real source-backed ClinVar gene-distribution artifact still has not been
  generated from the production ClinVar VCF or synced to deployed runtime
  storage. Until that is done, deployed environments should remain closed with
  explicit pending-index/manifest status rather than fabricating evidence.
- No commit, push, deploy, Vercel command, or real runtime artifact generation
  was run in this follow-up.
- Protein architecture remains a separate P0.3/frontend coordination residual:
  the ABCA4 report can render from fallback/report data, but the local
  around-variant `/api/v1/viewer` request reproduced HTTP 500 and the
  UniProt/Pfam/HMMER display merge needs redesign in the next protein-view pass.

2026-06-28 continuation:

- The real local ClinVar VCF exposed rows missing `CLNSIG`; strict parser
  behavior remains the default, while the gene-distribution materializer now
  skips malformed VCF rows explicitly and records `skipped_row_count` in index
  metadata, readiness inspection, and the sidecar manifest.
- The gene-distribution materializer no longer builds a full `ClinVarLocalStore`
  before writing the artifact. It streams VCF rows, batches
  `clinvar_gene_distribution_variant` inserts, keeps only per-gene counters in
  memory, and computes checksums/file dates without whole-file reads.
- `clinvar_gene_distribution_index` is registered with the generated-artifact
  upload/sync planner as a private generated SQLite runtime artifact. This adds
  planning and local/sync validation only; no Storage upload, private sync,
  deploy, env mutation, flag flip, source download, or completed real artifact
  build was performed.

Additional tests and checks:

- `python -m pytest tests/test_clinvar_local_adapter.py::test_materialized_gene_distribution_index_reads_bounded_gene_payload tests/test_clinvar_local_adapter.py::test_gene_distribution_materializer_skips_unusable_real_rows tests/test_clinvar_local_adapter.py::test_gene_distribution_materializer_does_not_use_full_store tests/test_clinvar_local_adapter.py::test_parser_failures_are_structured_for_malformed_vcf_rows -q`
  from `app/backend` - passed, 4 tests.
- `python -m pytest tests/test_generated_source_artifacts.py::test_generated_artifact_upload_plan_includes_tier1_sqlites_without_paths tests/test_generated_source_artifacts.py::test_generated_artifact_sync_accepts_clinvar_gene_distribution_index -q`
  from `app/backend` - passed, 2 tests.
- `python -m pytest tests/test_clinvar_local_adapter.py tests/test_generated_source_artifacts.py tests/test_health_api.py::test_provider_cache_health_reports_clinvar_gene_index_ready_without_paths tests/test_source_asset_preflight_cli.py::test_source_asset_preflight_reports_guarded_readiness tests/test_source_asset_preflight_cli.py::test_source_asset_preflight_reports_clinvar_gene_index_ready_without_paths -q`
  from `app/backend` - passed, 31 tests.
- `python -m ruff check app/services/clinvar_local.py app/services/generated_source_artifacts.py app/cli/eamos_generated_artifact_upload.py app/cli/eamos_generated_artifact_sync.py tests/test_clinvar_local_adapter.py tests/test_generated_source_artifacts.py tests/test_source_asset_preflight_cli.py`
  from `app/backend` - passed.
- `python -m black --check --target-version py310 app/services/clinvar_local.py app/services/generated_source_artifacts.py app/cli/eamos_generated_artifact_upload.py app/cli/eamos_generated_artifact_sync.py tests/test_clinvar_local_adapter.py tests/test_generated_source_artifacts.py tests/test_source_asset_preflight_cli.py`
  from `app/backend` - passed.

2026-06-28 real local materialization:

- After committing/pushing `7c5e4b6`, Codex ran a bounded local build against the
  already-present `app/backend/data/bio_assets/clinvar/clinvar.vcf.gz` with no
  source download, network, upload/sync, deploy, env mutation, flag flip, or
  runtime seed.
- Command shape: `python -m app.cli.eamos_clinvar_gene_distribution_materialize
  --from-vcf <local clinvar.vcf.gz> --output <local sqlite> --manifest <local
  manifest> --force --compact --require-ready`, monitored every 30 seconds under
  a 45-minute ceiling.
- The materializer process exited after about 40 minutes. A wrapper log-printing
  bug tripped on an empty stderr file after process exit, but the materializer
  stdout and artifact inspection reported `ready=true`.
- Result: `actual_size_bytes=737673216`, `gene_count=28936`,
  `variant_count=4713770`, `skipped_row_count=243588`, `schema_version=
  eamos.clinvar_gene_distribution.v1`, SHA-256
  `efbec24b6f0764d2bece7c0a3abc2c10fb9749494e7ae78e74e707a015f4f196`, source
  version `ClinVar GRCh38 VCF weekly release 2026-05-25 / clinvar_20260523`.
- Read-only source-asset preflight sees `clinvar_gene_distribution_index` as
  ready and plans the generated artifact for private Storage upload with
  `upload_performed=false` and `network_used=false`. No upload/sync was run.
- Direct runtime-reader smoke for `RPE65` + `1-68444869-T-C` returned
  `total=1136`, row totals `benign=420`, `pathogenic=327`, `vus=389`, and
  query metadata `VCV001421454` / `vus_noncoding` with no warnings.
- `eamos_source_asset_preflight` now supports operator summary output formats:
  default `--format toon`, plus `--format markdown`, `--format csv`, and full
  machine JSON via `--format json` or legacy `--compact`. The TOON summary keeps
  the large preflight report chat/log-friendly while preserving JSON for
  automation.

2026-06-28 private generated-artifact upload/sync:

- Steven approved the exact guarded action: private generated-artifact
  upload/sync planning and execution for `clinvar_gene_distribution_index`.
- Upload plan for only `clinvar_gene_distribution_index` reported one eligible
  private Storage item: bucket `eamos-source-assets`, object path under
  `generated/eamos_clinvar_gene_distribution_index/clinvar_gene_distribution_sqlite/`
  with SHA-256
  `efbec24b6f0764d2bece7c0a3abc2c10fb9749494e7ae78e74e707a015f4f196`,
  byte size `737673216`, schema `eamos.clinvar_gene_distribution.v1`, and
  source version `ClinVar GRCh38 VCF weekly release 2026-05-25 /
  clinvar_20260523`. S3 multipart credentials were configured; REST
  service-role write was not.
- Executed the upload with `--upload-mode s3_multipart --upload`. Result:
  `uploaded_count=1`, `blocked_count=0`, `failed_count=0`; the SQLite artifact
  and checksum manifest were uploaded to private Storage. The command emitted no
  local paths, secrets, signed URLs, public bucket fallback, Supabase metadata
  mutation, Render env mutation, deploy, provider flip, startup download, or
  request-time materialization.
- First remote sync attempt used explicit `--expected-*` values and correctly
  failed closed after download/checksum verification with
  `runtime_probe_schema_validation_failed:manifest_identity_mismatch`, because
  the explicit-identity path wrote a checksum-only manifest. The follow-up sync
  used the uploaded Storage manifest as the identity source and passed:
  `ready=true`, `downloaded=true`, `manifest_written=true`,
  `md5_verified=true`, `sha256_verified=true`, `schema_validated=true`.
- Post-sync verification passed: `eamos_source_asset_preflight --format toon`
  reports `clinvar_gene_distribution_index` ready with count `4713770`, byte
  size `737673216`, and the expected SHA-256; focused generated-artifact and
  preflight pytest passed; a direct runtime-reader smoke for `RPE65` +
  `1-68444869-T-C` returned `total=1136`, row totals `benign=420`,
  `pathogenic=327`, `vus=389`, query accession `VCV001421454`, query cell
  `vus_noncoding`, and no warnings.

Remaining live-runtime boundary after upload/sync:

- The durable private Storage object now exists and the local runtime path has
  been re-synced from it, but no deploy, Render env mutation, provider flip,
  live Render-disk seed, or live runtime materialization was run. Deployed
  environments remain unchanged until Steven separately approves the live
  Render-disk sync/seed and any flag/provider steps.

2026-06-28 live Render-disk seed attempt:

- Steven approved the exact live Render-disk seed/sync action, still excluding
  deploy, Render env mutation, provider/flag flip, source download, Supabase
  metadata mutation, and unreviewed source changes.
- The app's 443 admin materialization endpoint is not usable for this artifact
  as deployed: SG has `ADMIN_MATERIALIZATION_ENABLED=false`, the default
  manifest path is not overridden, and the deployed manifest is the older M6-M8
  batch without `clinvar_gene_distribution_index`.
- Render Dashboard Shell over HTTPS is usable and reached live SG instance
  `fl4bm`. Read-only preflight showed `/var/data/eamos` mounted with about
  `15G` free, Python `3.12.13`, private Supabase/S3 env vars set, and the
  ClinVar gene-distribution SQLite/manifest missing from the target disk path.
- The committed sync command failed closed before writing any file because the
  deployed image's `eamos_generated_artifact_sync` CLI predates the
  `clinvar_gene_distribution_index` artifact registration. It accepts only
  `clingen_local`, `pubmed_local`, and `literature_embeddings`; the live reader
  exists, but the generated-artifact registry and validation branch do not.
- Live provider-cache already exposes
  `source_assets.clinvar_gene_distribution_index` as `ready=false`,
  `status=missing`.
- No disk seed, deploy, env mutation, provider/flag flip, source download,
  Supabase metadata mutation, or one-off runtime script was run after the
  committed CLI path failed.
 - Next approved path should be explicit: deploy current `main` so the committed
  generated-artifact registry/materializer branch is live, then rerun the same
  Dashboard Shell sync command; or separately approve a one-off live runtime
  script that injects the missing generated-artifact definition/validation branch
  and syncs the private Storage object to disk.

2026-06-28 approved deploy + live Render-disk sync:

- Steven approved path A: deploy current `main` to SG, then rerun the same
  Dashboard Shell generated-artifact sync command.
- Render deploy `dep-d90er2lckfvc73ddmie0` reached `live` on commit
  `e41008dfda6ea6d31f1399e0f4916d3c6d2cffba`.
- Render Dashboard Shell reconnected to live instance `n47bw`; the committed
  `eamos_generated_artifact_sync` CLI accepted
  `clinvar_gene_distribution_index` and synced the private Storage object with
  `--download-mode s3_multipart --force --require-ready --compact`.
- Sync output was `ready=true`: `downloaded=true`, `byte_size=737673216`,
  `manifest_written=true`, `md5_verified=true`, `sha256_verified=true`,
  `checksum_computed=true`, `schema_validated=true`, and `warnings=[]`.
- Live `/api/v1/health/provider-cache` now reports
  `source_assets.clinvar_gene_distribution_index ready=true status=ready`,
  schema `eamos.clinvar_gene_distribution.v1`, source version
  `ClinVar GRCh38 VCF weekly release 2026-05-25 / clinvar_20260523`,
  `gene_count=28936`, `variant_count=4713770`,
  `actual_size_bytes=737673216`, SHA-256
  `efbec24b6f0764d2bece7c0a3abc2c10fb9749494e7ae78e74e707a015f4f196`,
  and `skipped_row_count=243588`.
- Live RPE65 lookup smoke now consumes the index:
  `report_payload.curated_variants_distribution.total=1136`,
  `row_totals benign=420 / pathogenic=327 / vus=389`,
  `source_status=local_index`, `query_accession=VCV001421454`,
  `query_cell=vus_noncoding`, and the old
  `clinvar_gene_distribution_excluded_pending_index` warning is absent.
- No Vercel command, Render env mutation, provider/flag flip, raw source
  download, public bucket fallback, signed URL, Supabase metadata mutation, or
  one-off runtime patch script occurred.
