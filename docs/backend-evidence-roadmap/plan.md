# Backend Evidence Roadmap Plan

Status: Draft for review
Owner: Codex/backend
Last updated: 2026-06-03 23:55 +1000 - Codex

Source spec: `docs/backend-evidence-roadmap/spec.md`

## Shared Decisions

- This plan is the coordination layer above
  `docs/local-first-data-source-strategy/source-asset-rollout.md`.
- Preserve unrelated handoff, frontend, and existing plan changes.
- Do not mutate Render, Vercel, Oregon, or Supabase in this planning pass.
- Supabase uploads are allowed only when needed for an approved execution step,
  and the current bucket/file size limit must be checked first.
- Runtime local source reads require pre-seeded files, byte checks, checksums,
  manifests, and materialization metadata. No startup downloads.
- Disk-gated wiring waits for verified Standard 2 GB memory plus 60 GB disk at
  `/var/data`.
- AlphaMissense can be made adapter-ready behind gates, but display remains
  approval-gated.
- ESM1b remains fixture/internal until score-file terms or regenerated-score
  provenance are safe.
- Literature and AI gateway can wait until the weekend unless Steven redirects.

## Task 1 - Durable Roadmap Bundle

### Goal

Create a design/spec/plan bundle that covers the seven backend tracks and
records sequencing, approval gates, and verification expectations.

### Context

Existing docs cover the earlier local-first source foundation, but not the full
set of ACMG, PVS1/NMD, literature, AI gateway, and modern predictor lanes.

### Relevant Files

- `docs/backend-evidence-roadmap/design.md`
- `docs/backend-evidence-roadmap/spec.md`
- `docs/backend-evidence-roadmap/plan.md`
- `docs/local-first-data-source-strategy/source-asset-rollout.md`

### Proposed Approach

Keep the bundle short and reviewable. Reference existing docs instead of
copying them. Make approval gates explicit.

### Acceptance Criteria

- Design, spec, and plan exist.
- The seven requested tracks are covered.
- Supabase size-limit preflight, Render/Vercel/Oregon restrictions, no-startup
  downloads, and `/var/data` disk gates are recorded.
- Predictor-lane gates match Steven's current direction.

### Verify

```powershell
rg -n "AlphaMissense|ESM1b|ACMG|PVS1|Literature|AI gateway|/var/data|Oregon" docs/backend-evidence-roadmap
```

## Task 2 - AlphaMissense Materialization And Index Preflight

### Goal

Add a backend preflight that proves whether AlphaMissense is locally
materialized and indexed before any runtime adapter uses it.

### Context

Registry metadata is already present for
`google_deepmind_alphamissense_hg38`, and `TabixTsvPredictorReader` exists.
The missing piece is a predictor-specific readiness wrapper that checks the
source file, derived `.tbi`, manifest, checksums, configured runtime path, and
materialization metadata.

### Relevant Files

- `app/backend/app/data_sources/registry.py`
- `app/backend/app/data_sources/runtime_assets.py`
- `app/backend/app/services/indexed_sources.py`
- `app/backend/app/services/source_downloads.py`
- new: `app/backend/app/services/predictor_runtime.py`
- new: `app/backend/tests/test_predictor_runtime.py`

### Proposed Approach

Reuse the existing `RuntimeAssetPlan`, `RuntimeAssetInspection`, and
`SourceAssetMaterializationRecord` concepts where practical. Add a generic
predictor runtime plan that can resolve AlphaMissense from settings and
registry metadata. Report missing source file, missing index, missing manifest,
size/checksum mismatch, unsupported mode, and materialization metadata status.

### Acceptance Criteria

- Missing AlphaMissense file reports unavailable without throwing.
- Missing `.tbi` reports unavailable.
- Missing manifest blocks upload/materialization readiness.
- Checksum mismatch fails closed.
- Ready fixture asset reports local path readiness.
- Supabase upload planning reports the configured bucket/file size limit before
  any upload attempt.
- No network, Supabase, production download, or display change occurs.

### Source Reference

- `docs/backend-evidence-roadmap/spec.md` Requirements 2-5 and 21-23.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_predictor_runtime.py tests/test_source_downloads.py tests/test_data_source_registry.py -q
```

## Task 3 - AlphaMissense Runtime Adapter Wrapper

### Goal

Add an internal adapter wrapper that can query a materialized AlphaMissense
tabix TSV by exact variant and return calibrated provenance-rich rows, while
remaining hidden from user-visible reports.

### Context

The generic TSV reader can query exact variants. The report path still filters
AlphaMissense and must remain unchanged until display approval.

### Relevant Files

- `app/backend/app/services/indexed_sources.py`
- `app/backend/app/services/computational_calibration.py`
- new: `app/backend/app/services/alphamissense_local.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- new: `app/backend/tests/test_alphamissense_local_adapter.py`
- existing report contract tests that prove AlphaMissense remains hidden

### Proposed Approach

Implement a small adapter around `TabixTsvPredictorReader`. Accept injected
reader/preflight dependencies for tests. Add calibration fields via
`calibration_field_values("AlphaMissense", score)`. Return structured
unavailable states rather than falling through to fixtures.

### Acceptance Criteria

- Exact `chrom, position, ref, alt` lookup returns one fixture row.
- No-hit returns honest unavailable/no-record state.
- REF/ALT mismatch returns no record, not a guessed record.
- Calibration uses Bergquist 2025 bands.
- User-visible report serialization still excludes AlphaMissense.
- Adapter cannot open without preflight-ready source and index.

### Source Reference

- `docs/backend-evidence-roadmap/spec.md` Requirements 21-23.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_alphamissense_local_adapter.py tests/test_variant_report_orchestration.py tests/test_tool_invariants.py -q
```

## Task 4 - ESM1b MANE Assembly Job Scaffold

### Goal

Scaffold an offline assembly job that converts fixture ESM1b missense scores
and MANE/codon context into genomic SNV rows plus a provenance manifest.

### Context

`esm1b_assembly.py` already contains codon-to-genomic SNV primitives. The next
slice should add job-level structure without using production score files.

### Relevant Files

- `app/backend/app/services/esm1b_assembly.py`
- `app/backend/app/services/transcript_model.py`
- new fixture rows under `app/backend/app/fixtures/predictors/`
- `app/backend/tests/test_esm1b_assembly.py`

### Proposed Approach

Add a fixture-sized job helper that takes score rows and explicit codon context
objects, emits sorted TSV rows, and writes or returns a manifest payload with
source score checksum, MANE version, reference checksum, code version, output
checksum, warnings, and license gate state.

### Acceptance Criteria

- Fixture scores assemble to deterministic genomic SNV rows.
- Reverse-strand codons are handled through existing primitives.
- Codon/residue mismatch fails closed.
- Manifest records `internal_fixture_only` or equivalent gate.
- No production ESM1b score download or public serialization occurs.

### Source Reference

- `docs/backend-evidence-roadmap/spec.md` Requirements 24-25.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_esm1b_assembly.py tests/test_data_source_registry.py -q
```

## Task 5 - Disk-Gated Local Adapter Wiring

### Goal

After disk verification, wire proven local stores into runtime flows behind
explicit configuration.

### Context

This is blocked until Steven verifies Standard 2 GB memory plus 60 GB disk at
`/var/data`. Assets must be seeded off-peak and verified before use.

### Relevant Files

- `app/backend/app/core/config.py`
- `app/backend/app/services/local_evidence_orchestrator.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/search_input_resolver.py`
- `app/backend/app/services/gene_viewer.py`
- `app/backend/app/services/sequence_context.py`
- source asset preflight and health tests

### Proposed Approach

Use disabled-by-default settings per flow. At startup, do not download. At
request time, choose local stores only when runtime preflight is ready and the
flow is configured. Fall back only where existing behavior allows it.

### Acceptance Criteria

- Disk shape was verified and recorded before implementation.
- Local reads use `/var/data` or another approved materialized local path.
- Missing or bad assets do not crash fixture mode.
- Existing live/fixture behavior remains stable when the gate is off.
- No startup downloads.

### Source Reference

- `docs/backend-evidence-roadmap/spec.md` Requirements 3-8.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_local_evidence_orchestrator.py tests/test_variant_search_integration.py tests/test_gene_viewer.py tests/test_frontend_contract.py -q
```

## Task 6 - ACMG Points Engine Core

### Goal

Build deterministic advisory Tavtigian/SVI-style point scoring with transparent
evidence output.

### Context

Eamos currently has ACMG worksheet scaffolding and source-derived assertions,
but not a deterministic points engine.

### Relevant Files

- new: `app/backend/app/services/acmg_points.py`
- new: `app/backend/tests/test_acmg_points.py`
- integration targets: clinical consensus/report orchestration

### Proposed Approach

Create pure dataclasses or Pydantic models for evidence items, point weights,
direction, counted/not-counted reasons, total score, and advisory summary. Keep
ClinGen/ClinVar source verdicts separate.

### Acceptance Criteria

- Deterministic point totals for representative fixture evidence.
- Conflicting evidence is surfaced instead of hidden.
- Missing evidence is not converted into points.
- Output is advisory and does not produce a final classification.

### Source Reference

- `docs/backend-evidence-roadmap/spec.md` Requirements 9-11.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_acmg_points.py tests/test_clinical_consensus.py -q
```

## Task 7 - PVS1/NMD Conservative Engine

### Goal

Build a conservative PVS1/NMD support engine that defaults false or uncertain
when critical inputs are missing.

### Context

PVS1 needs transcript geometry, variant consequence, NMD expectations, critical
regions, and LoF mechanism data. Missing data must not produce confident calls.

### Relevant Files

- new: `app/backend/app/services/pvs1_nmd.py`
- new: `app/backend/tests/test_pvs1_nmd.py`
- `app/backend/app/services/transcript_model.py`

### Proposed Approach

Implement pure logic for supported variant shapes with explicit input
requirements and conservative unavailable states. Do not use AutoPVS1 code or
data.

### Acceptance Criteria

- Missing LoF mechanism data returns false or uncertain.
- Missing critical-region data returns false or uncertain.
- Unsupported variant shapes return unavailable.
- Supported fixture cases produce transparent reasoning.

### Source Reference

- `docs/backend-evidence-roadmap/spec.md` Requirements 12-14.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_pvs1_nmd.py tests/test_transcript_model_store.py -q
```

## Task 8 - Literature Schema/API/Fixture ETL Design

### Goal

Design literature metadata storage and fixture ETL without importing full text
or mutating Supabase.

### Context

Steven indicated literature engine work can wait until the weekend. The safe
first step is design and fixtures only.

### Relevant Files

- future docs under `docs/literature-engine/`
- `app/backend/app/services/publication_literature.py`
- `app/backend/tests/test_publication_literature.py`

### Proposed Approach

Specify metadata tables, source identifiers, query terms, snippet/offset
limits, link-outs, and copyright handling. Prepare fixture ETL only. Request
Supabase approval before migrations/imports.

### Acceptance Criteria

- Schema/API design exists.
- Fixture ETL stores metadata and bounded snippets only.
- No Supabase migration/import occurs without approval.
- Copyright risk is explicitly handled.

### Source Reference

- `docs/backend-evidence-roadmap/spec.md` Requirements 15-17.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_publication_literature.py -q
```

## Task 9 - Mocked AI Gateway Broker

### Goal

Build a provider-abstracted AI broker using a mock provider first.

### Context

Real Groq/DeepInfra or other provider enablement waits for secret/config
approval. The broker should prove privacy and logging boundaries before real
providers are enabled.

### Relevant Files

- `app/backend/app/agents/client.py`
- `app/backend/app/agents/prompts.py`
- new: `app/backend/app/services/ai_gateway.py`
- new: `app/backend/tests/test_ai_gateway.py`

### Proposed Approach

Add request/response models, allowlisted fields, redaction, mock provider,
timeouts, and no-verdict guardrails. Keep provider keys backend-only and absent
from frontend contracts.

### Acceptance Criteria

- Mock provider returns deterministic fixture responses.
- PHI-like disallowed fields are excluded or redacted.
- Logs do not contain raw PHI or secrets.
- Broker refuses verdict-decision prompts.
- No real provider key or network dependency is required.

### Source Reference

- `docs/backend-evidence-roadmap/spec.md` Requirements 18-20.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_ai_gateway.py tests/test_chat_service.py -q
```

## Task 10 - Isolated Predictor Lane Follow-Ups

### Goal

Keep non-AlphaMissense predictor lanes parked or isolated according to current
policy.

### Context

The modern predictor set is unevenly licensed and should not enter the main API
path by accident.

### Relevant Files

- `app/backend/app/data_sources/registry.py`
- `app/backend/app/data_sources/policy.py`
- future predictor-specific tests

### Proposed Approach

Add tests or policy rows only when needed:

- CI-SpliceAI isolated from the main API path.
- MaveDB per-record CC0 gate plus Supabase/import approval.
- CAPICE parked pending Steven decision.

### Acceptance Criteria

- Main API path does not include CI-SpliceAI.
- MaveDB cannot import non-CC0 records.
- CAPICE remains unavailable until policy choice is recorded.

### Source Reference

- `docs/backend-evidence-roadmap/spec.md` Requirements 26-28.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_source_field_policy.py tests/test_data_source_registry.py -q
```
