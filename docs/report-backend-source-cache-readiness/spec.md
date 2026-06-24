# Report Backend Launch and Source-Cache Readiness Spec

Status: Draft

## What

Ship the backend/data-contract work needed for:

- report-level data currency, source-version pins, and reliable gnomAD
  unavailable states,
- live or source-cache-backed ClinGen VCEP expert-panel assertions,
- populated calibrated in-silico fields in report predictor rows, and
- a bounded ClinVar gene-distribution index for the curated variants grid.

This spec prepares the next implementation session. It does not authorize a
deploy or environment flip.

## Context

The current report framework already rejects narrative-only ClinGen matches,
emits typed identity provenance, calculates predictor calibration through
`computational_calibration.py`, defines `CuratedVariantsDistribution`, and has
initial report data-currency and population unavailable-reason fields.

The remaining launch gap is that those capabilities are not fully backed by
live/materialized source-cache data on the report path:

- Expert panel can still degrade to a labelled partial/consensus snapshot.
- Predictor rows can reach the frontend with blank calibration fields.
- ClinVar gene distribution is explicitly disabled until a bounded index exists.

## Relevant Files

- `app/backend/app/tools/clingen.py`
- `app/backend/app/services/clingen_local.py`
- `app/backend/app/services/source_cache.py`
- `app/backend/app/repos/source_cache_repo.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/lookup_sections.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/services/report_data_currency.py`
- `app/backend/app/services/population_frequency_section.py`
- `app/backend/app/services/report_call_cards.py`
- `app/backend/app/services/computational_calibration.py`
- `app/backend/app/tools/computational_annotations.py`
- `app/backend/app/services/predictor_runtime.py`
- `app/backend/app/services/clinvar_local.py`
- `app/backend/app/api/routes/health.py`
- `app/backend/app/schemas/run.py`
- `app/web/lib/backend.ts`
- `app/frontend/src/lib/backend.ts`
- `app/web/components/report/CalibratedInSilicoTable.tsx`
- `app/web/components/report/ExpertPanelSection.tsx`
- `app/web/components/report/CuratedVariantsGrid.tsx`

## Requirements

### Report Data Currency and Source-Version Pins

- The report payload must populate `report_generated_at`.
- The report payload must populate `report_data_currency` when at least one
  source exposes freshness metadata.
- `VariantReportHeader.updated_at` must use the latest real source timestamp,
  falling back to `report_generated_at`.
- `ReportDataCurrencySource` rows must include source label, materialized or
  fetched date, upstream release date when known, tier, status, staleness days,
  and source version when available.
- No public report, health, or preflight response may expose local paths, secrets,
  object-storage URIs, or raw source rows.
- ClinGen, ClinVar, gnomAD, and predictor source versions must be preserved so
  the frontend data-currency line and exports can cite versions.

### gnomAD Population Frequency Source Status

- Population frequency report sections must always include a reliable
  `source_status` derived from the gnomAD evidence state.
- Missing, failed, stale, not-found, or metric-empty gnomAD states must include a
  machine-readable `unavailable_reason`.
- Blank population sections are not allowed when the backend knows the source
  failed or returned no usable frequency metrics.
- Population call cards and section signals must use the same backend status
  source as `PopulationFrequencyReportSection`.
- Existing gnomAD positive and negative controls must continue to distinguish
  "not present in gnomAD" from "source failed."

### ClinGen VCEP Source Cache

- The lookup/report path must attempt a bounded ClinGen VCEP source-cache lookup
  before falling back to live Evidence Repository calls.
- The cache key must follow existing precedence:
  CAID, ClinVar VCV, then gene plus HGVS identity.
- Cached rows must be revalidated through structured identity matching before
  they can populate `ExpertPanelSection`.
- `candidate_text` matches must never auto-attach VCEP criteria.
- Exact identity matches must populate `ExpertPanelProvenance.identity_match`.
- Source version, fetched timestamp, source URL, and cache state must survive
  into report provenance.
- Stale-on-failure may be used only with an explicit stale warning and freshness
  state.
- Missing or rejected candidates must preserve explicit warnings such as
  `variant_identity_guard_rejected_candidate` or the current local equivalent.
- The expert-panel partial note should become conditional on actual missing,
  partial, or stale source state, not permanent.

### In-Silico Calibration

- Every `ComputationalPredictorRow` with a supported predictor name and numeric
  score must have:
  - `calibrated_label`
  - `calibration_bucket`
  - `calibration_method`
  - `calibration_version`
- Backend calibration must use `computational_calibration.py`.
- Frontend code must not infer these fields from raw score if the backend leaves
  them null.
- Unsupported or unreviewed predictors must keep null calibration fields and a
  clear source/warning state when appropriate.
- Local predictor rows must preserve:
  - `source_id`
  - `version`
  - `source_url`
  - `public_serialization_allowed`
  - `launch_gate`
  - row warnings
- `PP3` and `BP4` computed ACMG rows must consume populated calibration data
  from the report section or source row, not string-mapped frontend state.

### ClinVar Gene-Distribution Index

- Request-time lookup must not scan a whole ClinVar VCF or whole ClinVar table
  to build gene distributions.
- A materializer must precompute a bounded gene index from local ClinVar data.
- Lookup must read a single gene record from the index.
- The current warning `clinvar_gene_distribution_excluded_pending_index` must
  remain when the index is absent or not ready.
- `CuratedVariantsDistribution` must include cells, row totals, total,
  source status, source ID, source version, source URL, serialization/license
  gates, and query-variant metadata when available.
- The index must preserve enough provenance for report data currency and health
  output.
- Public health/preflight output must not expose local paths, secrets, object
  storage URIs, or raw ClinVar rows.

## Frontend Coordination Items

The same CAR also names frontend-owned P0/P1 work. These are not Codex backend
implementation tasks, but this backend slice should unblock them:

- P0.3 gene-viewer failure boundary: backend should keep returning explicit
  gene/protein viewer warnings and statuses, but the visible fallback is Claude
  lane.
- P1.2 in-silico placeholder rows: backend owns populated calibration fields;
  Claude owns hiding or placeholder treatment for null rows.
- P1.3 curated-variants empty state: backend owns the index and warning; Claude
  owns the empty/unavailable rendering.
- P1.5 protein/snippet provenance notes: backend keeps warnings source-backed;
  Claude owns visible rendering.

## Data Contracts

### Expert Panel

Existing schema fields are sufficient:

```python
class ExpertPanelProvenance(BaseModel):
    source_url: str
    fetched_at: str
    source_version: str
    cache_record_id: str | None = None
    raw_jsonld_ref: str | None = None
    identity_match: EvidenceIdentityMatch | None = None
```

Implementation must guarantee that `identity_match` is non-null for attached
source assertions unless the row is legacy fixture-only and explicitly labelled.

### Computational Predictor Rows

Existing fields are sufficient. The implementation must populate them:

```python
calibrated_label: str | None
calibration_bucket: RampVerdict | None
calibration_method: str | None
calibration_version: str | None
```

The allowed calibrated buckets remain:

- `Pathogenic`
- `Likely pathogenic`
- `VUS`
- `Likely benign`
- `Benign`

### Curated Variants Distribution

Existing fields are sufficient for the report contract. The backing store needs a
new bounded gene-index representation, but the API response should remain:

```python
class CuratedVariantsDistribution(BaseModel):
    cells: dict[str, int]
    row_totals: dict[str, int]
    total: int
    subtitle: str
    reading: str
    source_status: str | None
    source_id: str | None
    source_version: str | None
    source_url: str | None
    public_serialization_allowed: bool | None
    launch_gate: str | None
    license_gate: str | None
    query_cell: str | None
    query_variant_id: str | None
    query_accession: str | None
    query_classification: str | None
    warnings: list[str]
```

## Implementation Notes

### Data Currency and gnomAD

- Confirm `lookup_service.py` always sets `report_generated_at` and
  `report_data_currency` after all source evidence has been collected.
- Extend `report_data_currency.py` only if existing summary parsing cannot
  include upstream release dates or source versions for the new source-cache
  tracks.
- Confirm `population_frequency_section.py` receives the same gnomAD status that
  call cards and section signals use.
- Add or tighten tests for source failure, source not found, stale cache, and
  no-frequency-metrics cases.

### ClinGen

- Add a cache-backed path to `ClingenTool.get_evidence()` or a small helper that
  can be injected into the tool without broad rewrites.
- Reuse `_filter_variant_identity_records()` and `_identity_match_for_record()`.
- Add source-cache upsert support if the existing repo only reads in this path.
- Preserve local SQLite search as a valid source when enabled and ready.
- Add tests for:
  - fresh source-cache hit,
  - stale source-cache hit after live failure,
  - live fetch then cache write,
  - narrative-only rejected candidate,
  - neighboring allele rejected,
  - provenance flowing into `report_profile.expert_panel`.

### In-Silico

- Audit all row constructors and ensure each route calls
  `calibration_field_values()` before serialization.
- Add normalization coverage for `CADD PHRED`, `CADD`, `REVEL`, `SpliceAI`,
  `AlphaMissense`, and `ESM1b`.
- Leave unreviewed predictors null rather than inventing buckets.
- Add tests for report orchestration, ACMG PP3/BP4 use, and frontend contract
  mirrors.

### ClinVar Gene Index

- Add a materializer CLI or extend an existing source-asset materializer with a
  role such as `clinvar_gene_distribution_index`.
- Add an inspection/preflight helper that returns sanitized readiness.
- Add a reader that returns one gene aggregate by normalized gene symbol.
- Update `lookup_service._clinvar_distribution_runtime_path()` to return a ready
  index path instead of hard-coded `None`.
- Keep the existing exclusion warning unless readiness passes.
- Add tests for:
  - index materialization from fixture VCF,
  - bounded lookup by gene,
  - query variant cell mapping,
  - missing index warning,
  - malformed/stale manifest fail-closed behavior.

## Acceptance Criteria

- ABCA4 `c.5461-10T>C` attaches the exact ClinGen VCEP assertion when source
  data contains it, with typed `identity_match` provenance.
- Report payload includes sanitized `report_generated_at` and
  `report_data_currency` where source freshness exists.
- gnomAD missing/failure/no-metrics cases emit `source_status`,
  `unavailable_reason`, and warnings instead of a silent blank section.
- ABCA4 `c.5234T>A` browser verification does not show fabricated VCEP,
  calibration, ClinVar distribution, or protein localization data.
- At least one non-ABCA4 cross-gene sweep passes with no source bleed.
- Calibrated predictor rows show populated calibration fields for supported
  scores and explicit nulls for unsupported predictors.
- ClinVar distribution returns a non-empty bounded aggregate when the index is
  present and the old exclusion warning when it is not.
- Provider-cache/source preflight emits sanitized readiness for all new assets.
- `npm --prefix app/web run lint`, focused backend tests, `git diff --check`,
  and `python -m graphify update .` pass before any later commit.

## Test Matrix

- `ABCA4 c.5461-10T>C`: ClinGen positive control for source-backed VCEP.
- `ABCA4 c.5234T>A`: report/browser verification for limitations and protein
  localization without fabricated exact source claims.
- `RPE65 c.260A>G`: gnomAD-negative and ClinVar/local-evidence regression.
- `USH2A c.2276G>T`: population-positive and report source-status regression.
- A gnomAD source-failure or no-metrics fixture: population unavailable reason.
- One neighboring ClinGen allele: identity guard negative control.
- One predictor-supported SNV with REVEL/CADD/SpliceAI rows.
- One local AlphaMissense or ESM1b row if runtime asset is present.
- One gene with no ClinVar index row.

## Out of Scope

- Commercial predictor unlock policy.
- Always-on source refresh scheduling.
- New frontend visual treatments beyond consuming additive fields.
- Clinical recommendations or patient-specific ACMG PM3/PP4 scoring.
- Live deployment.

## Review Gates

- Confirm the ClinVar index storage format before implementation.
- Confirm whether ClinGen live detail fetch is required or summary rows are
  acceptable for the first source-cache pass.
- Confirm the canonical cross-gene regression list before the final sweep.
