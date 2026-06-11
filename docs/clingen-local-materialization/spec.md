# ClinGen Local Materialization Spec

## What

Build a backend-owned local materialization lane for ClinGen eRepo VCEP
classifications and CSpec criteria specifications. The system must support
operator-run full-source snapshots and test-sized fixture snapshots, expose
sanitized readiness through health/preflight, and let lookup/report sections
render from local ClinGen rows without live eRepo calls.

## Context

Current code:

- `app/backend/app/tools/clingen.py` searches live eRepo or fixture rows.
- `app/backend/app/services/source_cache.py` and `SourceCacheRepo` already
  provide fresh/stale source cache behavior, including ClinGen VCEP keys.
- `app/backend/app/services/lookup_service.py` records ClinGen evidence and
  feeds clinical consensus, functional evidence, report orchestration, and lazy
  section envelopes.
- `app/backend/app/services/lookup_sections.py` returns the `clingen_vcep`
  lazy section.
- `app/backend/app/services/pubmed_local.py` provides the strongest existing
  source-asset pattern for local SQLite inspection/materialization.

The missing piece is a local source asset for variant-level ClinGen VCEP/eRepo
and CSpec. ClinGen gene validity is local today, but it is not the same as
variant-level VCEP classifications.

## Requirements

1. Runtime lookup must not download ClinGen source data at startup or during
   ordinary requests.
2. A local ClinGen source asset must be materialized only by explicit CLI.
3. The source fetcher must support operator-run full eRepo/CSpec paging into
   JSONL, and the materializer must consume the same JSONL path used by tests.
4. Local runtime lookup must return the existing `ToolResult` shape used by
   `ClingenTool`.
5. Local runtime lookup must match by CAID, ClinVar VCV, gene/HGVS terms, and
   fallback text fields.
6. CSpec data must preserve source metadata and be ready to enrich criteria
   provenance, even if the first public report shape remains unchanged.
7. Health/preflight output must be sanitized and include enabled state, ready
   state, schema version, source version, row counts, checksum state, and
   fallback policy.
8. Existing report contracts must remain compatible:
   `ExpertPanelSection`, `AcmgWorksheetLedger`, `FunctionalEvidenceSummary`,
   `PublicationLiterature`, and `LookupSectionFetchResponse`.
9. Tests must prove `clingen_vcep`, clinical consensus, and functional evidence
   can use local fixture/cache rows with no live calls.
10. Supabase corpus/vector work is out of scope.

## Design

### Backend Service

Add `app/backend/app/services/clingen_local.py`.

Core objects:

- `ClinGenLocalInspection`
- `ClinGenLocalMaterializationResult`
- `ClinGenLocalStore`
- `inspect_clingen_local_store(settings)`
- `materialize_clingen_local_store(settings, erepo_jsonl_files, cspec_jsonl_files, ...)`

The SQLite schema is intentionally small:

- `clingen_local_manifest`
- `clingen_erepo_classification`
- `clingen_erepo_classification_term`
- `clingen_cspec_entity`
- `clingen_cspec_link`

The runtime store returns `ToolResult` through a method such as
`search_tool_result(variant, limit=25)`.

### CLI

Add:

- `python -m app.cli.eamos_clingen_local_fetch`
- `python -m app.cli.eamos_clingen_local_materialize`
- `python -m app.cli.eamos_clingen_local_preflight`

Fetch CLI inputs:

- `--output-dir`
- `--skip-erepo`
- `--skip-cspec`
- `--erepo-base-url`
- `--cspec-base-url`
- `--erepo-page-size`
- `--cspec-page-size`
- `--cspec-detail`
- `--cspec-entity-type`
- `--max-pages`
- retry/backoff flags
- `--force`
- `--compact`
- `--require-ready`

First slice CLI inputs:

- `--from-erepo-jsonl-file`
- `--from-cspec-jsonl-file`
- `--output`
- `--manifest`
- `--source-version`
- `--force`
- `--compact`
- `--require-ready`

### Runtime Wiring

Add settings:

- `clingen_local_enabled`
- `clingen_local_sqlite_path`
- `clingen_local_manifest_path`
- `clingen_local_fallback_on_no_hit`
- `clingen_local_max_results`
- `clingen_local_materialize_timeout_seconds`
- `clingen_cspec_base_url`

Update `ClingenTool.get_evidence()`:

1. If local enabled and no refresh, inspect and query local.
2. If local returns matching rows or fallback is disabled, return local result.
3. If local unavailable/no-hit and `USE_REAL_APIS=true`, call live eRepo.
4. If live fails, preserve existing fixture/fallback behavior.

### Health

Add `source_assets.clingen_local` to provider-cache health and the source asset
preflight report, with no local paths or secrets.

### Frontend Expectations

No frontend contract change is required for the first slice. The frontend keeps
using:

- `LookupSectionEnvelope.section_id="clingen_vcep"`
- `ExpertPanelSection.freshness`
- `ExpertPanelProvenance`
- `AcmgWorksheetLedger.criteria`

If CSpec criteria provenance is later exposed visibly, it should be additive on
existing criterion/provenance objects.

## Decisions

- **Full snapshot support**: yes. Operator CLI should support materializing the
  whole public eRepo classification set and relevant CSpec registry entities.
  Tests use tiny fixtures. This is reversible because runtime can disable the
  local asset.
- **Runtime source priority**: local first, then source cache stale/fresh
  behavior around `LookupService`, then live eRepo, then fixture only in
  non-real/fallback paths. This preserves current behavior.
- **Storage**: local SQLite source asset plus manifest. Avoid Supabase for this
  lane. Reversible by disabling the setting.
- **CSpec first-slice use**: preserve CSpec metadata in the local asset and
  inspection output, but do not alter report public schemas until a UI need is
  explicit.
- **Refresh behavior**: `refresh=true` bypasses local runtime results and tries
  live eRepo, but materialization is still CLI-only.

## Invariants

- `ClingenTool` must not bleed RPE65 fixture rows into unrelated variants.
- A malformed local asset must not crash `/api/v1/lookup` or provider-cache.
- Local rows must preserve `source_url`, `source_version`, `fetched_at`,
  `caId`, `uuid`, VCEP affiliation ID, criteria, and CSpec references when
  supplied.
- `clingen_vcep` lazy section must remain `available`, `partial`, or `missing`
  only.
- Public responses must not emit local paths, raw object URIs, secrets, or
  materializer input filenames.

## Error Behavior

- Local DB missing: return local unavailable warning and fall back if allowed.
- Manifest missing: health/preflight not ready; runtime falls back if allowed.
- Checksum mismatch: health/preflight not ready; runtime falls back if allowed.
- Local no-hit with complete snapshot: return `missing`/`local_no_hit` without
  fixture bleed.
- Local no-hit with incomplete snapshot: warning notes incomplete coverage and
  live fallback is allowed when configured.
- Live eRepo failure: existing source-cache stale behavior can serve stale rows;
  otherwise fallback remains current behavior.

## Testing Strategy

Focused tests:

- Materialize tiny eRepo/CSpec JSONL into SQLite and preflight it.
- `ClingenTool` returns local rows for RPE65 without calling live.
- `ClingenTool` returns no-hit for unrelated variants without fixture bleed.
- `LookupService` `clingen_vcep` section renders from local rows.
- Functional evidence and clinical consensus see local VCEP criteria/summary.
- Health output includes sanitized `clingen_local`.

Regression checks:

- `tests/test_tool_invariants.py`
- `tests/test_lookup_section_fetch_contract.py`
- `tests/test_clinical_consensus.py`
- `tests/test_functional_evidence.py`
- `tests/test_health_api.py`
- Ruff/Black on touched backend files.

## Out Of Scope

- Supabase corpus/vector tables.
- Production Render asset seeding.
- CSpec UI redesign.
- Reinterpreting ACMG criteria beyond source assertions and Eamos hints.
- Full CSpec document rendering.
