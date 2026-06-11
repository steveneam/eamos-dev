# ClinGen Local Materialization Plan

## Shared Decisions

- The local ClinGen lane supports a full operator snapshot of public eRepo VCEP
  classifications and relevant CSpec entities.
- Runtime lookup never downloads bulk ClinGen data.
- Local SQLite plus manifest is the first storage tier.
- Keep existing public report schemas unchanged in the first slice.
- Preserve provenance, license/source, launch-gate, and refresh metadata.
- No Supabase corpus/vector work.

## Task CLG-1 - Local Store, Materializer, And Preflight

Goal: Add the local ClinGen SQLite source asset and explicit CLIs.

Context: `pubmed_local.py` already shows the local-source pattern. ClinGen needs
a smaller version for eRepo/CSpec.

Relevant files:

- `app/backend/app/services/clingen_local.py`
- `app/backend/app/services/clingen_source_fetch.py`
- `app/backend/app/cli/eamos_clingen_local_fetch.py`
- `app/backend/app/cli/eamos_clingen_local_materialize.py`
- `app/backend/app/cli/eamos_clingen_local_preflight.py`
- `app/backend/app/core/config.py`
- `app/backend/tests/test_clingen_local.py`

Proposed approach:

- Add SQLite schema and manifest.
- Add operator-only eRepo/CSpec JSONL snapshot fetcher.
- Import eRepo JSONL rows and CSpec JSONL entities.
- Build search terms from gene, HGVS, CAID, ClinVar VCV, criteria, and VCEP
  metadata.
- Produce sanitized materialization and preflight JSON.

Acceptance criteria:

- Tiny eRepo/CSpec JSONL materializes into a ready local asset.
- Mocked eRepo/CSpec pages fetch to JSONL with retry/backoff and no raw rows in
  stdout.
- Preflight returns ready, schema version, source version, eRepo row count,
  CSpec entity count, checksum state, and no local paths.
- `--require-ready` exits non-zero for missing or unreadable assets.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_clingen_local.py -q
python -m app.cli.eamos_clingen_local_fetch --max-pages 1 --compact --force
python -m app.cli.eamos_clingen_local_preflight --compact
python -m ruff check app/services/clingen_local.py app/services/clingen_source_fetch.py app/cli/eamos_clingen_local_fetch.py app/cli/eamos_clingen_local_materialize.py app/cli/eamos_clingen_local_preflight.py tests/test_clingen_local.py
python -m black --check --target-version py310 app/services/clingen_local.py app/services/clingen_source_fetch.py app/cli/eamos_clingen_local_fetch.py app/cli/eamos_clingen_local_materialize.py app/cli/eamos_clingen_local_preflight.py tests/test_clingen_local.py
```

Full operator workflow:

```powershell
cd app/backend
python -m app.cli.eamos_clingen_local_fetch --force
python -m app.cli.eamos_clingen_local_materialize `
  --from-erepo-jsonl-file data/bio_assets/clingen/source/clingen-erepo-classifications.jsonl `
  --from-cspec-jsonl-file data/bio_assets/clingen/source/clingen-cspec-entities.jsonl `
  --source-version "ClinGen eRepo/CSpec snapshot YYYY-MM-DD" `
  --force --require-ready
python -m app.cli.eamos_clingen_local_preflight --require-ready --compact
```

## Task CLG-2 - Local-First ClingenTool Runtime

Goal: Make `ClingenTool` prefer local materialized VCEP rows when enabled.

Context: The tool already returns the correct `ToolResult` shape and fixture
filtering behavior. `LookupService` already wraps it with source-cache logic.

Relevant files:

- `app/backend/app/tools/clingen.py`
- `app/backend/app/services/clingen_local.py`
- `app/backend/tests/test_tool_invariants.py`
- `app/backend/tests/test_lookup_section_fetch_contract.py`
- `app/backend/tests/test_clinical_consensus.py`
- `app/backend/tests/test_functional_evidence.py`

Proposed approach:

- Add local lookup before fixture/live fallback when
  `clingen_local_enabled=true`.
- Keep `refresh=true` as a live bypass when real APIs are enabled.
- Return existing expert-panel and criteria payloads from local rows.
- Preserve no-fixture-bleed behavior on local no-hit.

Acceptance criteria:

- RPE65 local row populates `report_profile.expert_panel` and
  `clingen_vcep` section without live calls.
- Unrelated variants return missing/no-hit instead of RPE65 fixture data.
- Clinical consensus uses local ClinGen ahead of ClinVar.
- Functional evidence collects PS3/BS3 rows from local ClinGen raw records.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_tool_invariants.py tests/test_lookup_section_fetch_contract.py tests/test_clinical_consensus.py tests/test_functional_evidence.py -q
```

Out of scope: CSpec public UI rendering.

## Task CLG-3 - Health And Build Ledger Readiness

Goal: Expose sanitized ClinGen local readiness through provider-cache and
preflight surfaces.

Context: Provider-cache already reports `pubmed_local`, source cache, and build
ledger items.

Relevant files:

- `app/backend/app/api/routes/health.py`
- `app/backend/app/services/build_ledger.py`
- `app/backend/app/cli/eamos_source_asset_preflight.py`
- `app/backend/tests/test_health_api.py`

Proposed approach:

- Add `source_assets.clingen_local`.
- Add or update build-ledger source item for VCEP/eRepo/CSpec local
  materialization.
- Keep all output sanitized.

Acceptance criteria:

- Missing local asset reports not ready without crashing.
- Ready local asset reports counts and checksum state.
- Output includes no local paths, secrets, object URIs, or raw source rows.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_health_api.py -q
```

Out of scope: Render env changes.

## Task CLG-4 - Paged API Fetch Mode

Goal: Verify operator-run full-source fetching from public eRepo/CSpec APIs.

Context: eRepo and CSpec both expose paged APIs. Full snapshot should happen by
CLI only.

Relevant files:

- `app/backend/app/services/clingen_source_fetch.py`
- `app/backend/app/cli/eamos_clingen_local_fetch.py`
- `app/backend/app/cli/eamos_clingen_local_materialize.py`
- `app/backend/tests/test_clingen_local.py`

Proposed approach:

- Page through eRepo `summary/classifications` and CSpec entity endpoints with
  bounded `pgSize`, delay, retry/backoff, and stop conditions.
- Reuse the JSONL import normalization path.
- Emit sanitized fetch stats, not raw rows.

Acceptance criteria:

- Tests mock paged responses and prove retry/backoff and pagination stop.
- CLI output reports fetch counts, source version, and warnings.
- Runtime app does not call the fetch path.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_clingen_local.py -q
```

Out of scope: executing a full production snapshot in CI.

## Task CLG-5 - Production Snapshot Runbook

Goal: Document and execute a safe full-snapshot materialization when approved.

Context: Full snapshot is the intended production input, but should not be
mixed into ordinary deploys.

Relevant files:

- `docs/clingen-local-materialization/runbook.md`
- `PROGRESS.md`
- `agent_handoff/CURRENT.md`

Proposed approach:

- Specify commands, expected output, source URLs, row counts, checksum capture,
  and rollback.
- Run locally or on Render disk only after the CLI is verified.
- Enable `CLINGEN_LOCAL_ENABLED=true` only after preflight is ready.

Acceptance criteria:

- Steven can reproduce the full materialization without inventing API rules.
- Rollback is setting `CLINGEN_LOCAL_ENABLED=false`.
- No source rows, local paths, or secrets are committed.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_clingen_local_preflight --compact --require-ready
python -m pytest tests/test_lookup_section_fetch_contract.py tests/test_health_api.py -q
```

Out of scope: Supabase upload.
