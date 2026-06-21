# Post-M9 Flip Readiness Plan

Status: Phase 0 complete; Phases 1-6 are the active post-M9 queue
Owner: Codex/backend after Claude-led Phase 0
Last updated: 2026-06-21 23:42 +1000 - Codex

## Source Context

This plan now starts from the completed M9 local-evidence flip that Claude drove
from `agent_handoff/CURRENT.md`.

Current live SG readiness observed after the Phase 0 flip:

- `local_evidence_runtime_assets.ready=true`, `ready_count=4/4`.
- `dbsnp_local_adapter.status=ready`.
- `clinvar_local_adapter.status=ready`.
- `repeatmasker_local_adapter.status=ready`.
- `clingen_local.status=ready`, `enabled=true`, `classification_count=12690`.
- `clingen_local_adapter.status=ready`.
- `local_evidence_orchestrator.status=enabled`,
  `wired_surfaces=[lookup,gene_viewer]`.
- As of the pre-fix live deploy, the orchestrator build-ledger row can still
  carry the cosmetic `local_evidence_flow_not_enabled` blocker even while
  `lookup` and `gene_viewer` are enabled. Codex patched this locally on
  2026-06-21 so intentionally excluded flows do not appear as top-level
  blockers after the next backend deploy.
- `clinical_source_tables.status=import_ready`.
- `mavedb.status=cc0_import_not_materialized`.
- `pubmed_local.status=db_missing`.
- `literature_embeddings.status=db_missing`.
- Tier-2 predictor adapters are runtime-wired but missing score/model artifacts.

Related docs:

- `agent_handoff/CURRENT.md`
- `agent_handoff/RISKS.md`
- `docs/backend-evidence-roadmap/spec.md`
- `docs/clingen-local-materialization/spec.md`
- `docs/pubmed-corpus-materialization/spec.md`
- `docs/backend-build-ledger-runtime/materialization-plan.md`

## Sequencing

Do not bundle these phases into the M9 env flip. Phase 0 should prove the
existing M9 recipe alone. Phase 0 is complete; Phases 1+ are Codex follow-up
work after M9 is live and stable.

Steven may decide to pull Tier-1 PubMed/RAG work forward ahead of M3/MaveDB or
Workbench because it also unblocks report-chat literature grounding. Until that
decision is explicit, keep this phase order and do not start PubMed/RAG.

## Phase 0 - Claude-Led M9 Env Flip - COMPLETE

### Task 0.1 - Execute The Four-Flag M9 Flip

Goal: Enable the already-live M9 local-evidence path and ClinGen local adapter
without enabling search/workbench, PubMed/RAG, M3 import, or Tier-2 predictors.

Context: Code commit `90865ab` is live on SG and keeps ClinVar exact lookups
bounded while excluding gene-wide ClinVar distribution.

Relevant files or references:

- `agent_handoff/CURRENT.md`
- `app/backend/app/services/local_evidence_orchestrator.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/tools/clinvar.py`

Proposed approach:

- On `eamos-dev-sg`, set only:
  - `LOCAL_EVIDENCE_ENABLED=true`
  - `LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW=lookup,gene_viewer`
  - `LOCAL_EVIDENCE_REQUIRE_REAL_APIS=true`
  - `CLINGEN_LOCAL_ENABLED=true`
- Redeploy the patched `origin/main` HEAD.
- Run health, provider-cache, and lookup smoke checks.

Acceptance criteria:

- `/healthz` returns 200.
- `/api/v1/health/provider-cache` returns 200.
- Provider-cache shows local evidence orchestrator enabled/ready for the allowed
  flows and still reports `local_path_values_emitted=false`.
- Provider-cache shows `clingen_local.enabled=true`.
- RPE65 `c.260A>G` lookup summary returns 200.
- RPE65 lookup warnings include
  `clinvar_gene_distribution_excluded_pending_index`.
- No response emits local paths, private object URIs, secrets, or raw source
  rows.
- Render memory remains stable and no OOM/502 appears during smoke tests.

Source reference: `agent_handoff/CURRENT.md` M9 flip recipe.

Outcome: COMPLETE 2026-06-21 23:10 +1000. Claude set the four flags on
`eamos-dev-sg`; deploy `dep-d8ru3bvlk1mc73cc82sg` is live on `90865ab`.
Verification was green: `/healthz`, provider-cache, RPE65/HBB/BRAF lookups,
15/15 health watch over 15 minutes, memory flat around 667 MB/2 GB, and no
OOM/502 or path/object URI/secret leakage.

Verify:

```powershell
$base = "https://eamos-dev-sg.onrender.com"
Invoke-RestMethod -Uri "$base/healthz" -Method Get -TimeoutSec 60
Invoke-RestMethod -Uri "$base/api/v1/health/provider-cache" -Method Get -TimeoutSec 90
Invoke-RestMethod -Uri "$base/api/v1/lookup/summary" -Method Post `
  -ContentType "application/json" `
  -Body (@{ gene = "RPE65"; cdna = "c.260A>G"; species = "human" } | ConvertTo-Json) `
  -TimeoutSec 180
```

Out of scope:

- Search/workbench local evidence.
- PubMed/RAG.
- M3 clinical import.
- Tier-2 predictors.
- Any provider switch beyond the four flags.

### Task 0.2 - M9 Rollback Drill

Goal: Keep the rollback path explicit and quick.

Context: M9 is the first local-evidence runtime flip on the sole SG backend.

Proposed approach:

- If health, memory, lookup, or leak checks fail, set:
  - `LOCAL_EVIDENCE_ENABLED=false`
  - `CLINGEN_LOCAL_ENABLED=false`
- Redeploy and rerun health/provider-cache/RPE65 lookup.

Acceptance criteria:

- Rollback restores provider-cache to local orchestrator disabled.
- `/healthz`, provider-cache, and RPE65 lookup return 200 after rollback.

Source reference: `agent_handoff/RISKS.md` sole-live-backend guardrails.

Verify: Same smoke commands as Task 0.1.

Out of scope: Root-causing the failed flip during rollback. Capture evidence and
open a follow-up.

## Phase 1 - M3 Clinical Source Tables Import

### Task 1.1 - Preflight The M3 Import Gate

Goal: Confirm the clinical source table import can run safely on SG without
turning it into a broad env/provider flip.

Context: Provider-cache reports `clinical_source_tables.status=import_ready`.
The committed admin import endpoint exists, but no live M3 import has run.
Prerequisite: use a pooler-reachable host for the import or extend the
443-admin materialization trigger to cover M3 clinical release-file import. The
existing 443 materialization trigger does not yet cover this import path.

Relevant files or references:

- `app/backend/app/api/routes/materialization.py`
- `app/backend/app/services/clinical_source_import.py`
- `app/backend/data/source_assets/**`
- `agent_handoff/RISKS.md`

Proposed approach:

- Confirm the admin materialization gate and token flow are configured only for
  the import window.
- Confirm release files are present in the backend image/runtime context.
- Run the import in dry/smoke mode if available before apply.
- Confirm response payloads are sanitized counts and source versions only.

Acceptance criteria:

- Admin gate is disabled before and after the import window.
- Import preflight reports expected source files and row counts.
- No client-supplied path can influence the import source.
- Response emits no local paths, object URIs, secrets, or raw source rows.

Source reference: Codex M3 admin import closeout in `agent_handoff/CURRENT.md`.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_materialization_routes.py tests/test_source_asset_preflight_cli.py -q
```

Out of scope:

- M9 env flags.
- PubMed/RAG.
- Supabase schema migrations.

### Task 1.2 - Run And Verify M3 Import

Goal: Apply the already-staged clinical source table import and prove lookup
behavior remains stable.

Context: This is an operator action after Task 1.1 passes.

Relevant files or references:

- `app/backend/app/api/routes/materialization.py`
- `app/backend/app/repos/supabase_local_model_cache_repo.py`
- `app/backend/tests/test_source_cache.py`

Proposed approach:

- Enable the admin gate for the import window.
- Call the admin import endpoint.
- Verify sanitized row counts.
- Disable the admin gate.
- Smoke provider-cache and representative lookups.

Acceptance criteria:

- Import returns expected row counts for MONDO, HPO, ClinGen, and GenCC.
- Source-cache/provider-cache remains healthy.
- RPE65 and one non-RPE65 lookup return 200.
- No public response emits source table internals or local paths.

Source reference: `app/backend/data/source_assets` manifests.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_source_cache.py tests/test_variant_cache.py -q
```

Out of scope:

- New clinical source parsers.
- UI changes.

## Phase 2 - MaveDB CC0 Local Materialization

### Task 2.1 - Build MaveDB CC0 Materialization Preflight

Goal: Make MaveDB the next flip-ready local evidence item by proving CC0-only
artifact readiness.

Context: Provider-cache reports `mavedb.status=cc0_import_not_materialized`.
MaveDB has a cleaner licensing profile than restricted Tier-2 predictors when
CC0 gating is enforced.

Relevant files or references:

- `app/backend/app/services/mavedb_local.py`
- `app/backend/app/services/functional_evidence.py`
- `app/backend/app/api/routes/health.py`
- `docs/backend-evidence-roadmap/spec.md`

Proposed approach:

- Add or extend preflight output for MaveDB CC0 source status.
- Verify materialization manifests, checksums, row counts, and CC0 gating.
- Keep runtime disabled or fail-closed until provider-cache is green.

Acceptance criteria:

- Preflight distinguishes missing artifact, non-CC0 rows, checksum mismatch,
  and ready CC0 artifact.
- Health/provider-cache emits no local paths or raw MaveDB rows.
- Missing MaveDB artifact does not degrade lookup stability.

Source reference: backend evidence roadmap requirement 27.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_mavedb_local.py tests/test_functional_evidence.py tests/test_health_api.py -q
```

Out of scope:

- Restricted predictor unlocks.
- UI redesign.

### Task 2.2 - Materialize And Smoke MaveDB CC0

Goal: Put the MaveDB CC0 artifact on SG and verify report/lookup behavior from
the local adapter.

Context: Task 2.1 must pass first.

Proposed approach:

- Materialize a CC0-only SQLite artifact and manifest.
- Sync to the approved runtime path.
- Verify provider-cache readiness.
- Run lookup/report smokes for variants with and without MaveDB hits.

Acceptance criteria:

- Provider-cache reports MaveDB ready.
- Local MaveDB hit appears with provenance and CC0 status.
- No-hit and missing-artifact paths remain fail-closed.
- No local paths/object URIs/secrets are emitted.

Source reference: `app/backend/app/services/mavedb_local.py`.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_mavedb_local.py tests/test_variant_report_publication_functional_integration.py -q
```

Out of scope:

- Non-CC0 MaveDB data.
- PubMed/RAG.

## Phase 3 - Workbench Local Evidence Readiness

### Task 3.1 - Add Workbench-Flow Preflight And Smoke Coverage

Goal: Prepare `workbench` for a later `LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW`
addition without bundling it into M9.

Context: Provider-cache reports `workbench_local_tools.status=code_available_reference_gated`.
M9 intentionally enables only `lookup,gene_viewer`.

Relevant files or references:

- `app/backend/app/services/local_evidence_orchestrator.py`
- `app/backend/app/cli/eamos_workbench_preflight.py`
- `app/backend/app/cli/eamos_workbench_render_approval_bundle.py`
- `app/backend/app/api/routes/primer.py`
- `app/backend/app/api/routes/crispr.py`
- `app/backend/app/api/routes/align.py`

Proposed approach:

- Extend workbench preflight to assert local-evidence dependencies without
  reading full source files.
- Add API smoke coverage for primer/CRISPR/align paths with local evidence
  enabled in test settings.
- Keep exact flow inclusion out of prod until preflight passes on SG.

Acceptance criteria:

- Preflight reports ready/not-ready with sanitized guardrails.
- Workbench endpoint smokes return bounded responses and do not emit local paths.
- Search remains excluded.

Source reference: current M9 allowed-flow recipe.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_workbench_preflight_cli.py tests/test_workbench_render_approval_bundle_cli.py tests/test_crispr_design.py tests/test_primer_design.py -q
```

Out of scope:

- Flipping `workbench` in production.
- Frontend workbench UI changes.

### Task 3.2 - Controlled Workbench Flow Flip

Goal: Add `workbench` to allowed flows only after Task 3.1 passes on SG.

Context: This is a separate env change after M9 stability.

Proposed approach:

- Change `LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW` from `lookup,gene_viewer` to
  `lookup,gene_viewer,workbench`.
- Redeploy and smoke workbench endpoints.

Acceptance criteria:

- Provider-cache remains green.
- Workbench endpoint smokes return 200 or expected bounded validation errors.
- No search local evidence is enabled.
- No local paths, object URIs, or secrets are emitted.

Source reference: `LOCAL_EVIDENCE_RUNTIME_FLOWS` in
`local_evidence_orchestrator.py`.

Verify: Run the workbench preflight and targeted endpoint smokes against SG.

Out of scope: Search flow.

## Phase 4 - PubMed Local And Literature RAG

Sequencing note: this phase may move earlier if Steven explicitly chooses the
Tier-1-first path for Ask-Eamos/report-chat literature grounding. Do not treat
that as approved until recorded.

### Task 4.1 - Decide PubMed Corpus Scope

Goal: Convert PubMed from "db_missing" to an approved materialization plan
without accidentally promoting the 200-PMID proof artifact.

Context: Provider-cache reports `pubmed_local.status=db_missing` and
`literature_embeddings.status=db_missing`.

Relevant files or references:

- `docs/pubmed-corpus-materialization/spec.md`
- `app/backend/app/cli/eamos_pubmed_corpus_budget.py`
- `app/backend/app/services/pubmed_local.py`
- `app/backend/app/cli/eamos_literature_embed_materialize.py`

Proposed approach:

- Rerun the official-listing budget.
- Choose `targeted_seed`, `filtered_pubmed`, or `raw_mirror`.
- Record storage, staging, egress, and license implications.

Acceptance criteria:

- Steven approves a corpus scope before any upload/materialization.
- Plan explicitly rejects the 200-PMID proof artifact for production.
- Runtime flags remain unchanged.

Source reference: PubMed corpus materialization decisions D1-D5.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_pubmed_corpus_budget --fetch-official-listings --compact
```

Out of scope:

- Uploads.
- RAG enablement.
- Runtime flags.

### Task 4.2 - Materialize PubMed Local For Approved Scope

Goal: Build and verify `pubmed-local.sqlite` for the approved corpus scope.

Context: Task 4.1 approval is required.

Proposed approach:

- Stage source files outside the repo.
- Stream materialize PubMed-local.
- Verify license-gated abstract policy and manifest checksums.
- Preflight the generated SQLite.

Acceptance criteria:

- Materialization reports corpus scope, source versions, row counts, and license
  coverage truthfully.
- Preflight is ready and sanitized.
- Zero-row or checksum mismatch outputs fail closed.

Source reference: `docs/pubmed-corpus-materialization/spec.md`.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_pubmed_local.py tests/test_pubmed_pubtator_edges.py tests/test_pubmed_litvar_edges.py -q
```

Out of scope:

- RAG embeddings.
- Runtime enablement.

### Task 4.3 - Materialize Literature Embeddings And Flip RAG

Goal: Enable literature RAG only after PubMed-local is verified.

Context: Literature embeddings must inherit PubMed-local licensing behavior.

Proposed approach:

- Build `literature-embeddings.sqlite` from verified PubMed-local only.
- Preflight embeddings.
- Flip RAG only after provider-cache is green.

Acceptance criteria:

- Provider-cache reports literature embeddings ready.
- RAG retrieval returns bounded snippets/metadata only.
- No unlicensed full abstract text is emitted.
- `RAG_ENABLED` remains false until the final flip window.

Source reference: PubMed corpus materialization requirements 6-9.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_literature_retrieval.py tests/test_generated_source_artifacts.py -q
```

Out of scope:

- pgvector/Postgres migration.
- Full PMC/PubTator raw mirror.

## Phase 5 - Tier-2 Predictor Artifact Readiness

### Task 5.1 - CI-SpliceAI Score Cache Readiness

Goal: Move CI-SpliceAI from honest missing-cache state to materialized
score-cache readiness.

Context: Provider-cache reports `ci_spliceai.status=score_cache_missing`.

Relevant files or references:

- `app/backend/app/services/ci_spliceai.py`
- `app/backend/app/services/predictor_runtime.py`
- `docs/backend-evidence-roadmap/spec.md`

Proposed approach:

- Materialize model/reference/score cache artifacts.
- Preserve launch-filter metadata.
- Verify exact variant lookup and fail-closed paths.

Acceptance criteria:

- Provider-cache reports ready or a precise blocker.
- Lookup/report payload includes provenance and launch metadata for local hits.
- Missing/corrupt cache fails closed.

Source reference: backend evidence roadmap requirement 26.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_ci_capice_local_adapters.py tests/test_source_asset_preflight_cli.py -q
```

Out of scope: Commercialization filtering.

### Task 5.2 - CAPICE Model And Feature Cache Readiness

Goal: Move CAPICE from missing model artifact to honest readiness.

Context: Provider-cache reports `capice.status=model_artifact_missing`.

Proposed approach:

- Materialize CAPICE model artifact and SpliceAI feature cache.
- Preserve launch-filter and provenance metadata.
- Verify bounded local inference or lookup behavior.

Acceptance criteria:

- Provider-cache reports ready or precise blockers.
- CAPICE local output is reproducible in tests.
- Missing model/cache does not crash lookup.

Source reference: backend evidence roadmap requirement 28.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_ci_capice_local_adapters.py tests/test_tool_invariants.py -q
```

Out of scope: Public launch filtering.

### Task 5.3 - REVEL And PrimateAI-3D Score Cache Readiness

Goal: Materialize exact-variant score caches for REVEL and PrimateAI-3D.

Context: Provider-cache reports both as `score_cache_missing`.

Proposed approach:

- Build or sync indexed score caches.
- Verify exact variant lookup, provenance, and checksum behavior.
- Keep launch/license metadata attached to rows.

Acceptance criteria:

- Provider-cache reports ready or precise blockers.
- Local hits serialize with provenance and launch metadata.
- Cache misses and corrupt artifacts fail closed.

Source reference: backend evidence roadmap predictor requirements.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_restricted_predictors.py tests/test_tool_invariants.py -q
```

Out of scope:

- Entitlement/commercial launch filters.

### Task 5.4 - ESM1b MIT-Regenerated Artifact Readiness

Goal: Complete ESM1b from missing source file to MIT-regenerated artifact
readiness.

Context: Provider-cache reports `esm1b.status=missing_source_file` with launch
gate `esm1b_mit_regeneration_required`.

Proposed approach:

- Use the MIT-regenerated source path only.
- Materialize the indexed artifact and manifest.
- Verify local exact lookup/report serialization.

Acceptance criteria:

- Provider-cache reports ESM1b ready.
- Report rows preserve ESM1b provenance and launch-gate metadata.
- No restricted source score file is used.

Source reference: backend evidence roadmap requirements 24-25.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_esm1b_assembly.py tests/test_esm1b_local.py tests/test_tool_invariants.py -q
```

Out of scope: Restricted ESM1b score-file use.

## Phase 6 - Search Local Evidence

### Task 6.1 - Search Flow Safety Review

Goal: Decide whether `search` can ever join local evidence allowed flows.

Context: M9 intentionally excludes search. Search has broader input surfaces and
needs its own bounded-query proof.

Relevant files or references:

- `app/backend/app/services/search_input_resolver.py`
- `app/backend/app/services/search_candidate_resolver.py`
- `app/backend/app/services/local_evidence_orchestrator.py`

Proposed approach:

- Audit search candidate paths for bounded local reads.
- Add tests that malformed/broad inputs cannot trigger full asset scans.
- Define if search should use only candidate metadata or full local evidence.

Acceptance criteria:

- Search local evidence has a written go/no-go decision.
- Any enabled path is bounded and sanitized.
- No broad gene-wide/full-corpus scan can run from public search input.

Source reference: M9 search exclusion decision in `agent_handoff/CURRENT.md`.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_variant_search_integration.py tests/test_lookup_section_fetch_contract.py -q
```

Known caveat: `tests/test_variant_search_integration.py` has a pre-existing
red around `functional.source_breakdown` expecting `mavedb` non-zero while
MaveDB is not materialized. Do not misread that as a search local-evidence
regression without checking the exact failure.

Out of scope:

- Enabling search before this review.

## Global Guardrails

- Never use `git add -A` for these phases.
- Keep parked dirty files out of commits unless explicitly reviewed.
- No startup downloads.
- No public buckets or frontend-readable private source paths.
- No Render env mutation without a phase-specific flip recipe and rollback.
- Every phase must include no-path/no-secret/no-object-URI verification.
- After code changes, run `python -m graphify update .`.
