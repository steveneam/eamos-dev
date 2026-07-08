# Free In-Silico Predictor Materialization Plan

Status: Planned / code-readiness started - 2026-07-04 - Codex

## Context

The report in-silico catalog marks these predictors as Free:

- AlphaMissense
- ESM1b
- CI-SpliceAI
- Pangolin
- GPN-MSA

This plan covers backend readiness only. It does not approve downloads, uploads,
runtime sync, Supabase writes, Render env/provider flips, or public launch
filters. Health, source preflight, and build ledger must distinguish visible
planned slots from materialized source-backed predictor rows.

Current source findings, checked 2026-07-04 from primary sources:

- AlphaMissense: Zenodo `10813168`, CC BY 4.0, hg38 score table already has the
  local runtime lane in Eamos.
- ESM1b: `ntranoslab/esm-variants` code path is usable for MIT-model
  regeneration; the precomputed Hugging Face score zip remains excluded from
  production.
- CI-SpliceAI: official offline annotation repo is CC BY 4.0; the hosted web
  service states it may not be used commercially, so Eamos must self-host.
- GPN-MSA: official `songlab/gpn-msa-hg38-scores` Hugging Face dataset is MIT,
  tabix-queryable, and large enough that remote byte-range proof should precede
  any local materialization.
- Pangolin: official repo/paper record GPL-3.0; runtime packaging and dependency
  obligations need review before it becomes a server-side dependency.

## Decisions

- Treat "Free" as product visibility, not materialization approval.
- Emit backend status for every Free catalog slot, including planned/unwired
  lanes, so the report UI cannot silently imply live data.
- Keep materialization fail-closed: no row is emitted unless the backend adapter
  returns a source-backed score with provenance and a reviewed field allowlist.
- Prefer static exact-variant cache or remote range lookup for very large
  genome-wide assets. Request-time model inference needs a separate resource
  envelope proof.

## Task 1 - Readiness Contract For Free Predictor Slots

Goal: Make health/preflight/build-ledger expose every Free catalog predictor
without pretending missing lanes are available.

Context: AlphaMissense, ESM1b, and CI-SpliceAI already had backend lanes; GPN-MSA
and Pangolin were visible only in frontend catalog placeholders.

Relevant files:

- `app/backend/app/services/predictor_runtime.py`
- `app/backend/app/api/routes/health.py`
- `app/backend/app/cli/eamos_source_asset_preflight.py`
- `app/backend/app/services/build_ledger.py`
- `app/backend/app/data_sources/registry.py`

Acceptance criteria:

- `/api/v1/health/provider-cache` includes `gpn_msa` and `pangolin` under
  `providers.indexed_predictors`.
- Source preflight includes the same keys under `predictor_runtime_assets`.
- Build ledger includes `gpn_msa` and `pangolin` items.
- `gpn_msa` status is `remote_range_reader_planned`, `available=false`,
  `runtime_wired=false`, and `public_serialization_allowed=false`.
- `pangolin` status is `source_decision_required`, `available=false`,
  `runtime_wired=false`, and `public_serialization_allowed=false`.
- No local paths, object URIs, secrets, raw source rows, or source downloads are
  emitted or performed.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_predictor_runtime.py tests/test_health_api.py tests/test_source_asset_preflight_cli.py tests/test_data_source_registry.py tests/test_source_field_policy.py -q
```

## Task 2 - CI-SpliceAI Complete Artifact Gate

Goal: Move CI-SpliceAI from `score_cache_missing` to ready only when the complete
self-hosted model/reference/score-cache set exists.

Context: The offline annotation repo is the production path; the hosted service
must not be used by Eamos production. Existing Eamos runtime gates already block
bare or partial artifact sets.

Acceptance criteria:

- Model, reference bundle, bgzip score cache, tabix index, and sidecar manifests
  are all present and identity-matched.
- Missing or partial artifact sets report precise blockers.
- Lookup/report emits `CI-SpliceAI` rows only for source-backed local hits.
- Provenance, source version, launch metadata, and calibration fields are
  preserved on rows.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_ci_capice_local_adapters.py tests/test_predictor_runtime.py tests/test_tool_invariants.py -q
python -m app.cli.eamos_tier2_predictor_artifact_upload --artifact ci_spliceai --compact
```

Out of scope: Artifact upload, Supabase registration, Render sync, env flips.

## Task 3 - GPN-MSA Remote Range Reader Proof

Goal: Prove exact-variant GPN-MSA lookup from the official tabix score dataset
without downloading the full 81.2 GB score table.

Context: The official Hugging Face dataset documents `scores.tsv.bgz` and
`scores.tsv.bgz.tbi` and tabix region queries. A remote byte-range reader is the
lowest-storage path, but Eamos must prove latency, error handling, and schema
before exposing rows.

Proposed approach:

- Add a `GpnMsaLocalOrRemoteAdapter` with an injected reader interface.
- Start with tests over tiny fixture score/index files; do not hit the network
  in tests.
- Add a read-only operator preflight that can validate remote HEAD/range
  semantics when explicitly run.
- Emit score rows only after exact `(chrom, pos, ref, alt)` match.

Acceptance criteria:

- Cache miss, malformed row, missing index, range failure, and timeout fail
  closed with warnings.
- Provider-cache remains `remote_range_reader_planned` until source snapshot and
  reader proof are recorded.
- No full-file load, startup download, request-time materialization, or local path
  leak.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_gpn_msa_adapter.py tests/test_predictor_runtime.py tests/test_tool_invariants.py -q
```

Out of scope: Full local materialization and production remote-range enablement.

## Task 4 - ESM1b MIT-Regenerated Scores

Goal: Complete the existing ESM1b lane after operator-side MIT-model regeneration
produces the private score CSV.

Context: Eamos must not use the non-commercial precomputed Hugging Face score
zip as a production artifact.

Acceptance criteria:

- Runtime artifact and tabix index are generated from MIT-regenerated scores.
- Manifest records MANE release, reference checksum, model/source provenance,
  and no production launch gate for the clean path.
- Provider-cache/build-ledger report ready only after explicit runtime sync.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_esm1b_assembly.py tests/test_esm1b_local_adapter.py tests/test_predictor_runtime.py -q
```

Out of scope: Running the private regeneration job or staging its output without
Steven approval.

## Task 5 - Pangolin Runtime Decision

Goal: Decide whether Pangolin should be server-side inference, a precomputed
score cache, or remain a placeholder until a safer source path exists.

Context: Pangolin is GPL-3.0 and model inference needs reference sequence,
annotation DB, and likely nontrivial compute. This is not just a small tabix
cache.

Proposed approach:

- Write a short design note comparing:
  - local Python dependency and model inference;
  - offline precompute/cache for variants of interest;
  - no backend materialization until a curated score source exists.
- Include GPL packaging/redistribution obligations and Render resource envelope.
- Choose one path before code implementation.

Acceptance criteria:

- Source, terms, artifact shape, and runtime envelope are recorded.
- Provider-cache remains `source_decision_required` until the decision is made.
- Any later adapter fails closed and emits no rows without source-backed scores.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_predictor_runtime.py tests/test_health_api.py -q
```

Out of scope: Installing Pangolin, building GTF databases, or running model
inference in production.

## Parallel Split

This work can run as a 3-lane parallel sprint after the readiness contract is
merged:

- Lane A: CI-SpliceAI artifact gate and adapter verification.
- Lane B: GPN-MSA remote-range adapter proof.
- Lane C: Pangolin runtime decision/design only.

Frozen contract: provider-cache and preflight keys for
`ci_spliceai`, `gpn_msa`, and `pangolin`; row emission remains fail-closed.
Merge order: readiness contract -> CI-SpliceAI -> GPN-MSA -> Pangolin decision.
