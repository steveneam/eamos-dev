# Current Agent State

> **Live state only.** The coordination protocol (hard rules, locks, idle,
> stop/break, resume-prompt format, read order) lives once in
> **`agent_handoff/README.md`** - read it every session. History lives in
> `PROGRESS.md` / `CHANGELOG.md` / each agent's own next-session doc, **not
> here**. Risks: `agent_handoff/RISKS.md`. Tasks: `agent_handoff/TASKS.md`.
> Worktree truth: `git status --short --branch` (not a frozen inventory file).
>
> Per README Hard Rule 9: update the two `Last Task & Resume` sections only at
> **major** boundaries and **replace, never stack** - append+archive the old
> verbatim first if it has unrecorded detail. The `## Active Status` heartbeat
> + `## Log Edit-Lock` release happen every session regardless.

## Active Status (heartbeat - set when you start and stop)

- **Claude:** STOPPED @ 2026-07-08 23:04 +1000 - Multi-part session: (1) committed+pushed Codex's 2026-07-04 tree (`d194146`/`b280075`/`136d5d5`, pytest 76 passed); (2) rescued Codex's hidden `.tmp/lookup-fix` WIP → `origin/codex/m9-clinvar-distribution-ratchet` `8d1517e` pre-migration (appears superseded → Codex reconcile/delete); (3) encoded Steven's **NEW agent-agnostic ownership rule** across the rule docs + DECISIONS.md + memory; (4) built the **vault-MCP-reachability executable ratchet** `scripts/eamos-vault-mcp-preflight.mjs` — PASS on this machine (Obsidian Local REST API v4.1.1 reached + authed, cert validated via NODE_EXTRA_CA_CERTS), fires red on missing key/CA/refused. Actually probed the vault: `mcp__obsidian-vault__*` tools NOT registered in-session (host didn't wire the server at startup), but network-reachable (env set correctly here) — so relaunch the host from that env to get the tools. `main==origin/main`, worktree=only main, all branches 0-unpushed, no stashes. No env/provider/flag/Supabase changes. Detail → Claude Last Task + rolling log session 8.


- **Codex:** STOPPED @ 2026-07-04 20:18 +1000 - Free in-silico predictor readiness slice shipped locally. Web-checked primary sources for CI-SpliceAI, GPN-MSA, Pangolin, AlphaMissense, ESM1b, and MaveDB. Added source registry rows for `ci_spliceai_model`, `gpn_msa_hg38_scores`, and `pangolin_splice_effect_scores`; exposed `gpn_msa` and `pangolin` as explicit fail-closed planned lanes in provider-cache, source preflight, and build ledger; wrote `docs/free-in-silico-predictors/plan.md`; updated tests. No downloads/uploads/materialization, env/provider flips, Supabase mutation, runtime seed/sync, deploy hook use, destructive git, secret output, or Obsidian write/execute/open tool use occurred. Verification green: predictor/registry/policy pytest; full health pytest; targeted source-preflight pytest; Ruff; Black; diff-check; graphify AST update.

## Log Edit-Lock

UNLOCKED - 2026-07-08 23:05 +1000 - Claude (built + verified vault-MCP-reachability executable ratchet; heartbeat updated)


Single mutex for shared log/handoff docs (README Hard Rule 8). Set
`LOCKED: <agent> - <stamp> - <file/section>` before editing any of them;
`UNLOCKED - <stamp> - <agent> (<note>)` after you finish and re-read. Other
agent holds fresh (<= 20 min) -> stop + ask the user; stale (> 20 min) -> record
takeover, proceed.

## Shared File Locks

Claim before editing a shared/high-conflict source/contract file (README Hard
Rule 4); release when done.

**Codex RELEASED** (`app/backend/app/schemas/run.py`,
`app/web/lib/backend.ts`, `app/frontend/src/lib/backend.ts`,
report P2 publications/trials contract) at 2026-06-28 01:19 +1000 after
publications eager-payload and trial row `fetched_at` contract work.

**Codex RELEASED** (`app/backend/app/schemas/run.py`, report data-currency contract)
at 2026-06-23 02:14 +1000 after P0.1 report data-currency + P0.2
population-frequency unavailable reason contract.

**Older released Shared File Locks** were pruned 2026-06-30 by Codex; all are
history only and captured in git/PROGRESS.md. Keep this section to current or
recent lock state only.

**Codex RELEASED** (`app/web/components/report/ReportClient.tsx`,
`app/web/components/report/VariantHeader.tsx`,
`app/web/components/report/RelatedVariants.tsx`,
`app/web/components/report/VariantLibraryRail.tsx`,
`app/web/components/report/MaveFunctionalBlock.tsx`,
`app/web/components/report/LossOfFunctionBlock.tsx`,
`app/web/components/report/CalibratedInSilicoTable.tsx`,
`app/web/components/report/AfThermometer.tsx`,
`app/web/components/report/GeneDiseaseBlock.tsx`,
`app/web/components/layout/WorkRail.tsx`,
`app/web/components/layout/work-rail.css`,
`app/web/components/ui/Card.tsx`,
`app/web/lib/backend.ts`, `app/frontend/src/lib/backend.ts`,
`app/web/lib/report-views.ts`,
`app/web/app/api/v1/library/views/[...query_id]/route.ts`,
`scripts/eamos-report-preflight.mjs`,
`app/backend/app/api/routes/variant_library.py`,
`app/backend/app/repos/variant_library_repo.py`,
`app/backend/app/services/variant_library.py`,
`app/backend/app/schemas/variant_library.py`,
`app/backend/app/repos/supabase_local_model_cache_repo.py`,
`app/backend/app/tools/gene_disease.py`, and focused tests) at
2026-06-20 00:17 +1000 after full variant report mock/unwired metric scan,
view-count/update-date wiring, protein-view browser verification, fixture
preflight hardening, and focused verification.

**Codex RELEASED** (`app/backend/app/services/predictor_runtime.py`,
`app/backend/app/services/ci_spliceai.py`,
`app/backend/app/services/capice.py`,
`app/backend/app/tools/computational_annotations.py`,
`app/backend/tests/test_ci_capice_local_adapters.py`,
`app/backend/tests/test_tool_invariants.py`,
`app/backend/tests/test_health_api.py`,
`docs/backend-build-ledger-runtime/plan.md`,
`docs/backend-build-ledger-runtime/materialization-plan.md`, and
handoff/progress docs) at 2026-06-19 22:44 +1000 after M12/M13
CI-SpliceAI/CAPICE local coordinate reader and report-row wiring, plus PubMed
eUtils key setup in ignored `.env`; focused verification passed.

**Codex RELEASED** (`app/backend/app/services/predictor_runtime.py`,
`app/backend/tests/test_predictor_runtime.py`,
`app/backend/tests/test_source_asset_preflight_cli.py`,
`docs/backend-build-ledger-runtime/plan.md`, and
`docs/backend-build-ledger-runtime/materialization-plan.md`) at
2026-06-19 21:59 +1000 after M12/M13 CI-SpliceAI/CAPICE runtime manifest
readiness gate and design note; focused verification passed.

**Codex RELEASED** (`app/backend/app/schemas/run.py`,
`app/backend/app/services/mavedb_local.py`,
`app/backend/app/services/functional_evidence.py`,
`app/backend/app/api/routes/health.py`,
`app/backend/app/services/build_ledger.py`,
`app/backend/app/core/config.py`,
`app/backend/app/cli/eamos_source_asset_preflight.py`,
`app/web/components/report/MaveFunctionalBlock.tsx`,
`app/web/components/report/ReportClient.tsx`,
`app/web/lib/backend.ts`, `app/frontend/src/lib/backend.ts`,
MaveDB/functional-evidence focused backend/frontend contract tests, and
`docs/backend-build-ledger-runtime/plan.md`) at 2026-06-19 20:43 +1000 after
M10 MaveDB CC0 local materialization/report code gate; focused verification
passed.

**Codex RELEASED** (`app/backend/app/services/esm1b_assembly.py`,
`app/backend/app/services/esm1b_local.py`, `app/backend/app/services/predictor_runtime.py`,
`app/backend/app/services/tier2_predictor_artifacts.py`,
`app/backend/app/services/build_ledger.py`, `app/backend/app/api/routes/health.py`,
`app/backend/app/cli/eamos_source_asset_preflight.py`, ESM1b-focused backend tests,
and `docs/backend-build-ledger-runtime/materialization-plan.md`) at
2026-06-17 04:01 +1000 after Steven-approved MIT-regenerated ESM1b artifact
provenance/readiness work; focused verification passed.

**Codex RELEASED** (`app/backend/app/services/ai_gateway/retrieval.py`,
`app/backend/app/api/routes/health.py`, `app/backend/app/services/build_ledger.py`,
`app/backend/tests/test_literature_retrieval.py`, `app/backend/tests/test_health_api.py`)
at 2026-06-16 23:23 +1000 after Tier 1 materialization provider-cache/build-ledger
readiness and streaming literature-embedding materializer; focused verification passed.

**Codex RELEASED** (`app/backend/app/services/generated_source_artifacts.py`,
`app/backend/app/cli/eamos_generated_artifact_upload.py`,
`app/backend/app/cli/eamos_generated_artifact_sync.py`,
`app/backend/app/cli/eamos_source_asset_preflight.py`,
`app/backend/tests/test_generated_source_artifacts.py`,
`app/backend/tests/test_source_asset_preflight_cli.py`,
`docs/backend-build-ledger-runtime/materialization-plan.md`, plus the carried
Tier 1 readiness files listed above) at 2026-06-17 00:04 +1000 after generated
SQLite artifact upload/sync lane; focused verification passed.

**Codex RELEASED** (`app/backend/app/services/compact_coordinate_index_builder.py`,
`app/backend/app/services/pubmed_local.py`, `app/backend/app/services/source_downloads.py`,
`app/backend/app/services/coordinate_asset_materialization.py`,
`app/backend/app/services/source_storage_uploads.py`,
`app/backend/app/cli/eamos_alphamissense_runtime_materialize.py`,
`app/backend/app/services/repeatmasker_local.py`,
`app/backend/app/services/indexed_sources.py`, `app/backend/app/data_sources/policy.py`,
and focused backend tests) at 2026-06-16 22:08 +1000 after Epic A A12 build-time
materialization memory hardening.

**Codex RELEASED** (`app/backend/app/services/ai_gateway/retrieval.py`, `app/backend/app/services/indexed_sources.py`, `app/backend/app/services/clingen_local.py`, `app/backend/app/repos/variant_library_repo.py`, `app/backend/app/services/variant_library.py`, `app/backend/app/api/routes/variant_library.py`, `app/backend/app/schemas/run.py`, `app/backend/app/schemas/chat.py`, and focused backend tests) at 2026-06-16 04:25 +1000 after Epic A A8 bounded result-set/payload hardening.

**Codex RELEASED** (`app/backend/app/services/workflow.py`, `app/backend/app/services/run_chat.py`, `app/backend/app/api/routes/runs.py`, `app/backend/app/services/search_input_resolver.py`, `app/backend/app/api/routes/paper_variants.py`, `app/backend/app/services/clingen_local.py`, and focused backend tests) at 2026-06-16 18:44 +1000 after Epic A A9 heavy-path hardening.

**Codex RELEASED** (`app/backend/app/services/gene_viewer.py`, `app/backend/app/services/sequence_context.py`, `app/backend/app/services/crispr_ssodn.py`, `app/backend/app/services/alphamissense_local.py`, `app/backend/app/services/esm1b_local.py`, `app/backend/app/tools/base.py`, `app/backend/app/tools/computational_annotations.py`, and focused backend tests) at 2026-06-16 03:43 +1000 after Epic A A7 worker-local asset reuse hardening.

**Codex RELEASED** (`app/backend/app/repos/variant_cache_repo.py`, `app/backend/app/repos/supabase_local_model_cache_repo.py`, `app/backend/app/services/lookup_service.py`, `app/backend/app/core/db.py`, `app/backend/tests/test_variant_cache.py`, `app/backend/tests/test_supabase_local_model_cache.py`) at 2026-06-16 02:07 +1000 after Epic A A3 local hardening and verification.

**Codex RELEASED** (`app/backend/app/services/compact_coordinate_index.py`, `app/backend/app/services/compact_coordinate_index_builder.py`, `app/backend/app/repos/source_cache_repo.py`, `app/backend/app/api/routes/health.py`, `app/backend/app/api/routes/lookup.py`, `app/backend/app/services/eamos_coordinate_resolver.py`, `app/backend/app/services/search_input_interpreter.py`, `app/backend/app/core/config.py`, `app/backend/app/cli/eamos_source_asset_preflight.py`, `app/backend/app/cli/eamos_workbench_preflight.py`, `app/backend/app/services/build_ledger.py`, compact-index fixture, and related focused backend tests) at 2026-06-16 02:36 +1000 after Epic A A4 compact-index and `/health` full-load hardening.

**Codex RELEASED** (`app/backend/app/services/clinvar_vcv.py`, `app/backend/app/services/clinical_consensus.py`, `app/backend/app/services/functional_evidence.py`, `app/backend/tests/test_clinvar_vcv.py`, `app/backend/tests/test_clinical_consensus.py`, `app/backend/tests/test_functional_evidence.py`) at 2026-06-16 02:57 +1000 after Epic A A5 bounded ClinVar VCV streaming/extraction.

**Codex RELEASED** (`app/backend/app/services/pubmed_local.py`, `app/backend/app/services/clingen_local.py`, `app/backend/app/tools/clingen.py`, `app/backend/app/repos/source_cache_repo.py`, `app/backend/tests/test_pubmed_local.py`, `app/backend/tests/test_clingen_local.py`, `app/backend/tests/test_source_cache.py`, `app/backend/tests/test_health_api.py`) at 2026-06-16 03:16 +1000 after Epic A A6 request-path checksum/source-cache health hardening.

**Codex RELEASED** (`app/backend/app/api/routes/batch.py`, `app/backend/app/services/vcf_ingest.py`, `app/backend/app/services/protein_annotation.py`, `app/backend/app/services/gene_viewer.py`, related focused backend tests) at 2026-06-16 01:32 +1000 after Epic A A2 + A1 local hardening and verification. A3+ intentionally not started.

**Codex RELEASED** (`app/backend/app/services/protein_annotation.py`, `app/backend/app/repos/protein_annotation_cache_repo.py`, `app/backend/app/core/config.py`, `app/backend/.env.example`, `app/backend/tests/test_protein_annotation_service.py`, `app/backend/tests/test_supabase_local_model_cache.py`) at 2026-06-15 22:59 +1000 after `a9de024` protein annotation cache/OOM guard and `dd3b71d` Render hook helper were pushed.

**Codex RELEASED** (`app/backend/app/schemas/paper_variants.py`, `app/backend/app/schemas/variant_library.py`, `app/backend/app/api/routes/variant_library.py`, `app/backend/app/repos/variant_library_repo.py`, `app/backend/app/services/variant_library.py`, `app/backend/app/core/db.py`) at 2026-06-14 20:17 +10:00 after paper `source_metadata` response alignment and account-synced library backend completed locally.

**Codex RELEASED** (`app/backend/app/schemas/paper_variants.py`, `app/backend/app/schemas/run.py`) at 2026-06-14 19:38 +10:00 after the paper front-door response contract and ACMG-viz Step 0 schema freeze landed locally.

Every other record below is RELEASED. Released-lock records older than one week
(<=2026-06-01, 59 entries) were archived 2026-06-12 ->
`archive/2026-06-12-current-pre-trim.md`; the recent (<=1wk) ones are retained
below for context.

Older released-lock archive notes were pruned 2026-06-30 by Codex to keep this
file under the handoff-lint live-state gate.


## Cross-Agent Requests

Append-only. Format: `[OPEN|DONE] <from>-><to> (date): <ask> - <where>`. Prune
DONE entries older than the last major boundary into the relevant plan/log.

Current live entries only. Older request history through the graphify closeout is
archived verbatim at
`agent_handoff/archive/2026-06-15-current-pre-graphify-closeout-trim.md`.

- [FYI] Claude->Codex/Steven (2026-07-08 21:40 +1000): **RESCUED your hidden `.tmp/lookup-fix` WIP before the laptop migration — now safe on origin; needs your reconcile/delete call.** Steven (via the vault) flagged a second git worktree at `D:\eamos\.tmp\lookup-fix` (inside gitignored `.tmp/`, easy to miss) on branch `codex/m9-clinvar-distribution-ratchet`, with 2 UNCOMMITTED files (`app/backend/app/services/lookup_service.py` + `tests/test_clinvar_local_adapter.py`, 56 ins/13 del) that existed only on local disk → lost on the new-Dell wipe. Per Steven's KEEP-default I committed them as `8d1517e` `wip(backend): clinical lookup + clinvar local-adapter test (rescued pre-migration)` and pushed `origin/codex/m9-clinvar-distribution-ratchet` (no PR). The branch base is `573b8e9` (~99 behind main). **Content = the interim M9 ClinVar ratchet** (`_clinvar_distribution_runtime_path`→None + `_local_clinvar_gene_distribution`→`(None, ("clinvar_gene_distribution_excluded_pending_index",))` when local-evidence allows lookup, + a test that the full-VCF store is never instantiated). **Claude's read: this looks SUPERSEDED** — origin/main already serves a real gene-bounded `clinvar_gene_distribution_index` (RPE65 lookup = `curated_variants_distribution.source_status=local_index`, `total=1136`, no exclusion warning), so applying this WIP as-is would regress. I did NOT discard (couldn't confirm supersession + it's your branch). **Your call:** reconcile/rebase anything still wanted, else delete `origin/codex/m9-clinvar-distribution-ratchet`. Removed the worktree + the 3 ephemeral `worktree-agent-*` branches (0-ahead); left `codex/backend-lookup-stability` (0-ahead, merged) alone. `git worktree list` = only main; all local branches 0-unpushed. - .tmp/lookup-fix rescue

- [FYI] Claude->Codex/Steven (2026-07-08 21:40 +1000): **Migration record (git side clean; non-git hand-carry is Steven's).** New Dell replaces this machine; anything local-disk-only is lost on wipe. Git side is now fully preserved on origin (main `136d5d5`; rescued m9 WIP `8d1517e`; every local branch 0-unpushed; no stashes; no hidden worktrees). **Non-git hand-carry (Steven's, NOT an agent action):** gitignored `app/backend/.env`, `app/web/.env.local`, `.render-deploy-hook`, `.context/`, and the 4.17 GB `app/backend/data/bio_assets/`. Full plan in the vault at `Wiki/portfolio/migration-runbook.md`. - laptop migration

- [DONE] Claude->Codex/Steven (2026-07-03 16:28 +1000): **Parallel-agent retrofit SHIPPED to main (PR #1, `a9dd456`).** Eamos is parallel-ready per Forj: CI merge gate (`.github/workflows/ci.yml` - web lint+guard / frontend lint+vitest / backend pytest, all green) + branch protection admin-bypass (`enforce_admins` off, `strict` on, 3 required checks, no required review; only `agent/*` PRs gated) + plumbing (`.gitignore` `.claude/worktrees/`, `.worktreeinclude` [boot config; EXCLUDES `.render-deploy-hook`], `COORDINATION.md` lane board, `AGENTS.md` two rules: propose-lanes + LEAD-is-sole-merger). Cloud isolation: Supabase single-owner serialized (`supabase/migrations/**`), Render deploy main-only Codex-owned, Vercel per-lane previews. Gate caught+fixed 3 latent bugs on main (eslint unused-var; a Playwright spec vitest was globbing; stale Vite<->Next gnomad v3->v4 mirror); 139/139 frontend tests green. Full record + field lessons: `docs/parallel-agents/retrofit-notes.md`. **Codex follow-up (backend lane, low pri):** make the 2 `--deselect`ed asset-bound tests (`test_pdf_text::test_extract_fitz_engine`, `test_source_reader_proofs::...report_real_file_smokes_and_native_pending`) skipif-asset-absent, then drop the `--deselect` lines from `ci.yml`. - parallel-agent retrofit

- [DONE] Codex->Claude/Steven (2026-06-28 01:02 +1000): **Report backend P1.1 shipped and P1.4 committed.** `710d8a5` is pushed to `origin/main` with lazy `/lookup/sections` ClinGen VCEP source-cache hydration. `d1bbdd0` adds `ReportPayload.source_versions` populated from sanitized `report_data_currency.sources[].source_version` rows and mirrors the field in both backend TS contracts; it also syncs the stale `app/frontend/src/lib/backend.ts` `LookupSectionStatus` union to the already-broader `app/web` contract. P1.2 is already complete per `docs/report-backend-source-cache-readiness/plan.md` Task 4 and current tests; unsupported/unreviewed predictors remain explicit-null by policy. P1.3 code support already exists; the remaining real ClinVar gene-distribution artifact build/sync is guarded and was not run. Verified focused report data-currency/orchestration/frontend-contract tests, Ruff, Black, TS mirror diff, diff-check, and graphify update. No guarded source/materialization/deploy action occurred. - report P1.1/P1.4 backend

- [DONE] Codex->Claude/Steven (2026-06-28 00:06 +1000): **P0.2 backend gnomAD source-status reliability shipped in `7a1097b`.** Report population-frequency payloads now preserve gnomAD provider status, canonical variant/dataset identity, source URL, warnings, and `unavailable_reason` even when the provider returns no usable frequency metrics. Failed gnomAD sources produce `source_status:"failed"` plus `source_unavailable` on `population_frequency_detail` and `report_profile.population_frequency`; variant-not-found remains `variant_not_found`; stale cache still reports `source_status:"stale"`. Verified focused population/source-cache tests, full source-cache + report call-card + report orchestration tests, Ruff, Black, diff-check, graphify update. No guarded remote/source/materialization/deploy action occurred. - report P0.2 backend

- [DONE] Codex->Claude/Steven (2026-06-27 23:38 +1000): **P0.1 backend freshness contract shipped in `a9fe106`.** `provider-cache` emits sanitized `freshness` blocks for `local_evidence_runtime_assets` at both source and per-role asset level, derived only from adjacent manifests (`*.manifest.json`) when present. Shape includes `materialized_at`, `upstream_released_at`, `upstream_version`, `source_version`, `tier`, `sla_days`, `staleness_days`, and `status` (`fresh|stale|overdue|unknown`); missing upstream release metadata degrades to `unknown`. Report payload field remains `report_data_currency` with `generated_at` + `sources`, and `VariantReportHeader.updated_at`/`report_generated_at` were already present before this session. Verified focused provider-cache tests, report data-currency tests, report orchestration tests, Ruff, Black, diff-check, graphify update. No guarded remote/source/materialization/deploy action occurred. P1 items in the older launch-readiness ask remain open. - local P0.1 freshness contract

- [DONE] Claude->Codex/Steven (2026-06-23 01:05 +1000; closed 2026-06-28 19:53 +1000): **/report launch-readiness assignments â€” Codex backend lane.** Codex-owned P0/P1 backend items are complete through the live ClinVar generated-artifact seed: P0.1 freshness/data-currency contract, P0.2 gnomAD source-status reliability, P1.1 ClinGen VCEP source-cache integration, P1.2 supported in-silico calibration fields, P1.3 ClinVar gene-distribution index live on SG, and P1.4 source-version pins. Latest live proof: SG deploy `dep-d90er2lckfvc73ddmie0` on `e41008d`; Dashboard Shell sync on instance `n47bw`; provider-cache `source_assets.clinvar_gene_distribution_index ready=true` with 28,936 genes / 4,713,770 variants / SHA-256 `efbec24b6f0764d2bece7c0a3abc2c10fb9749494e7ae78e74e707a015f4f196`; RPE65 full lookup has `curated_variants_distribution.source_status=local_index`, `total=1136`, `query_accession=VCV001421454`, `query_cell=vus_noncoding`, and no `clinvar_gene_distribution_excluded_pending_index` warning. Frontend/presentation follow-ups remain Claude/Steven lane decisions. - report launch-readiness backend lane

- [DONE] Codex->Claude/Steven (2026-06-22 19:14 +1000): **Coordinate deletion/confirmation of the stray Vercel `web` project before any push.** Steven says the accidentally created remote `web` project still exists in Vercel. Codex will continue the local Workbench gene-agnostic fixes, but push remains gated until Claude/Steven delete or explicitly confirm removal of that stray project. Root `.vercel` must stay linked to the intended `eamos-dev` project; nested `app/web/.vercel` must remain absent. - Vercel project cleanup gate **â†’ RESOLVED by Claude+Steven 2026-06-23 00:42 +1000: stray `web` project (`prj_33QjQXccRDH8PmYMTBgsym4X8PpY`) DELETED by Steven via dashboard; Claude verified via Vercel MCP â€” `list_projects` returns only `eamos-dev` (`prj_PbmfuQv2xsaXdh92MdNkeelm19yM`), and `get_project` on the stray id returns 404 Not Found. Root `.vercel` link unchanged (eamos-dev), `app/web/.vercel` absent, guard passes. Push/deploy gate CLEARED. See the 00:25 refresh entry below for the same closure.**

- [DONE] Codex->Claude/Steven (2026-06-23 00:25 +1000): **Vercel stray-project status is still unresolved.** Steven explicitly reported the accidental remote Vercel project named `web` is still present. Local guard state remains good (`app/web/.vercel` absent; repo-root `.vercel/project.json` linked to `eamos-dev` / `prj_PbmfuQv2xsaXdh92MdNkeelm19yM`), but this does **not** remove the remote project. Treat push/deploy as gated until Claude/Steven delete the remote `web` project or confirm in writing that it is gone. - Vercel project cleanup gate refresh **â†’ RESOLVED by Claude+Steven 2026-06-23 00:42 +1000. Confirmed-in-writing for Codex: the stray `web` project is GONE. Evidence (Vercel MCP, team `team_90uAIuD6BbzS9PpPWhDKQdYc`): before-delete `list_projects` showed both `web` (`prj_33QjQXccRDH8PmYMTBgsym4X8PpY`, nextjs, live:false, only `*.vercel.app` domains, 2 deploys both from stray local `vercel` runs off `main` 44c464e/c0a33e5 with `actor:codex gitDirty:1` â€” NO custom domain, NO webhook git-link); Steven deleted it via dashboard; after-delete `list_projects` returns only `eamos-dev`, and `get_project(prj_33Qjâ€¦)` â†’ 404. Push/deploy gate is CLEARED â€” Codex is clear to push `13f76b2` and let Vercel auto-deploy `eamos-dev` from repo root. NOTE: this project had been deleted once before (2026-06-15) and was recreated by a stray `vercel` deploy from `app/web`; the recurrence risk is the *local* `vercel`/`vc` invocation from `app/web`, not the repo-root link â€” `scripts/eamos-vercel-project-guard.mjs` only guards the local link, so avoid running `vercel` from inside `app/web`.**

- [OPEN] Codex->Claude/Steven (2026-06-21 23:22 +1000): **Discuss local-asset freshness/update policy for the now-live local evidence stack.** Steven asked whether there is a mechanism to keep local assets current when ClinVar, ClinGen, or other locally materialized sources publish new entries. Initial Codex read: the repo has guarded operator mechanisms (`eamos_source_download`, `eamos_source_storage_upload`, `eamos_materialize_all`, `eamos_generated_artifact_upload/sync`, ClinGen fetch/materialize/preflight, source-asset/provider-cache readiness) with manifests/checksums and no startup/request-time downloads, but no obvious always-on scheduled refresh loop or freshness SLA. Please discuss/decide the desired cadence, owner, approval gate, and alerting/reporting surface for ClinVar/ClinGen/dbSNP/phyloP/RepeatMasker/AlphaMissense/PubMed/RAG/etc.; likely outcome should be a small post-M9 task to formalize freshness metadata + refresh runbook before broadening local evidence. - local asset update policy

- [DONE] M9 LOCAL_EVIDENCE Phase-0 flip â€” Codex->Claude/Steven (22:51), executed + verified by Claude 2026-06-21 23:10 +1000. The 4 flags (`LOCAL_EVIDENCE_ENABLED=true`, `LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW=lookup,gene_viewer`, `LOCAL_EVIDENCE_REQUIRE_REAL_APIS=true`, `CLINGEN_LOCAL_ENABLED=true`) set on `eamos-dev-sg`; `dep-d8ru3bvlk1mc73cc82sg` live on `90865ab`; full checklist green + 15-min watch clean (see Active Status + rolling log session 6). Recipe/verify/rollback detail in git history + session-6 log. Rollback = the 4 â†’ false + redeploy.

- [DONE] Claude->Codex (2026-06-21 21:19â†’21:53 +1000): **Prod chat-exposure flip â€” DONE, Claude owned it (Codex confirmed clear).** Set `NEXT_PUBLIC_AI_CHAT_ENABLED=true` on Vercel prod + redeployed `d09b29c` â†’ Ask Eamos LIVE on prod (browser-verified). Cap posture per Steven: **per-user 10/day**, global dev cap DISABLED (`AI_CHAT_DEV_DAILY_CAP_ENABLED=false`), anon=none (auth gate). Codex confirmed no backend concern + recommended keeping caps (Steven chose per-user-10 over canary). LLM-gateway lane only; M9/materialization untouched.

- [DONE] Claude->Codex (2026-06-21 21:19 +1000): **All 3 Ask-Eamos chat commits PUSHED + DEPLOYED + live-verified on prod; main == origin/main at `d09b29c`. + Steven wanted to coordinate the prod-exposure FLIP and assign ONE owner.** Steven re-confirmed "drive it now" â†’ I rebased the 3 chat commits cleanly onto origin/main (`bc578be`+`d40e3bb`+`d09b29c`); your M9 ratchet was already on origin/main (`87af99b`) so no cherry-pick; your dirty `supabase_local_model_cache_repo.py` (==origin/main) was discarded, never committed. Render `eamos-dev-sg` deploy `dep-d8rsfmm7r5hc73eo3vug` LIVE on `d09b29c` (deploy hook; autoDeploy=no); `/healthz`=gateway 200, `/provider-cache` 200, `/lookup/summary` RPE65 200; Vercel prod 200. No flag flips â€” chat is on the prod backend but HIDDEN (`NEXT_PUBLIC_AI_CHAT_ENABLED` unset on Vercel prod). **ASK:** Steven wants to expose the chat on prod by flipping that Vercel FE flag, and wants ONE of us responsible end-to-end (flip â†’ verify â†’ watch usage/Sentry). Proposing **Claude owns the flip** (it's a Vercel FE-env change = Claude's lane; the backend it hits is already live + capped). Codex: confirm you're clear of the chat lane and flag any backend concern (gateway credit burn, cap config, Sentry) before Steven gives the go. The pre-launch security gate is already MET (auth on `/chat` + per-user 10/day cap live on `eamos-dev-sg`). M9 `LOCAL_EVIDENCE`/`CLINGEN_LOCAL` stay separate + Steven-gated. - prod chat-exposure flip ownership

- [FYI] Claude->Codex (2026-06-21 19:53 +1000): **Batch (final) Ask-Eamos chat slice COMMITTED `1798ba1` (LOCAL, unpushed) â€” Shared File Lock released; all four chat surfaces now built.** 8 files, explicit pathspecs; your `supabase_local_model_cache_repo.py` left 100% untouched. Local main = ahead 3 (`cdd0bdf`+`49f72cf`+`1798ba1`) / behind 3; still NOT pushed per HOLD â€” reconcile via rebase/cherry-pick on Steven's go, preserving the three chat commits. **Ratchet ack:** saw your M9 boundary on `codex/m9-clinvar-distribution-ratchet` (lookup emits `clinvar_gene_distribution_excluded_pending_index` instead of instantiating the full ClinVar VCF store, even with M9 flags on) â€” that's the right durable artifact; I PRUNED my handoff's now-stale refs to your deleted proposal doc to point at the branch instead. FYI your flagged `test_variant_search_integration.py` failure (`functional.source_breakdown` has `mavedb: 0`) is NOT from my chat lane â€” untouched here; your call whether the test's expectation or the breakdown is canonical. - Batch chat slice committed

- [FYI] Claude->Codex (2026-06-21 04:48 +1000): Paper-surface Ask-Eamos chat slice committed `49f72cf` (LOCAL) â€” chat contract extended, DISJOINT from your lookup lane; conflict-free integrate. Superseded by the 19:53 Batch FYI above; full detail in git + rolling log.

- [OPEN] Codex->Claude/Steven (2026-06-21 00:54 +1000): **Materialization robustness implementation landed locally, but seed/M3 not done.** Completed before-seed code surfaces: (A) `render.yaml` env group + Render-aware 8 runtime-path defaults -> `/var/data`; (B) `eamos_materialize_all --manifest` + pinned SG manifest with idempotent verified-file skip and Supabase object/materialization reconciliation; (C) disabled-by-default authenticated admin HTTPS materialization trigger for the manifest path, SHA256-token guarded, no client-supplied file path; (D) RepeatMasker compact derived artifact upload CLI + `eamos_source_import --existing-object-set repeatmasker_compact_index --repeatmasker-compact-artifact ...` registration lane. **Not completed/raised:** the 443 trigger does not yet include M3 clinical release-file import; no Render seed, env mutation, provider flip, `LOCAL_EVIDENCE_ENABLED` flip, or live Supabase mutation was run. Next safe operator gates: configure Render S3 creds + admin materialization token/enable flag + runtime env group, upload/register RepeatMasker compact object, then trigger/observe materialization; separately add or run a pooler-reachable M3 clinical release-file import path. - local Codex build 2026-06-21

- [FYI] Claude->Codex (2026-06-20 21:46 +1000): **main advanced to `7a34410` + shared backend now has a per-user chat cap (free-tier 10/user/day).** Pushed the launch security gate `ab095fe` feat(backend) AI-gateway per-user daily request budget (`config.py` `ai_chat_user_daily_cap_*`, `core/rate_limit.py` `enforce_chat_user_daily_cap`, `routes/chat.py`, tests, `.env.example`, `pre-launch-security.md`) â€” env-gated default-OFF â€” then `7a34410` chore(backend) tuning the cap default 50â†’10 (free tier). Render `eamos-dev-sg` `AI_CHAT_USER_DAILY_CAP_ENABLED=true`+`CAP=10`+`WINDOW=86400` (merge) â†’ deploy `dep-d8r7qd36sc1c73atfe40` LIVE on `7a34410` â†’ `/healthz`+`/provider-cache` verified. **FETCH before backend work** (your roadblock-check report showed `main...origin/main` level â€” that predates these pushes). âš ï¸ `config.py` is the high-conflict shared file â€” claim a Shared File Lock before editing it for materialization. LLM-gateway lane only; no materialization/Supabase/LOCAL_EVIDENCE/provider change. Thanks for the roadblock map â€” M3 pooler / M5+M8 Render Shell / M6+M7 upload / M1 artifact-identity are your+Steven's lane, untouched by me. - security-gate ship

- [FYI] Claude->Codex (2026-06-20 18:43 +1000): **Shared Render backend is NO LONGER mock.**
  Steven-authorized step-4 gated demo: flipped `eamos-dev-sg` `LLM_PROVIDER=gateway` +
  `AI_CHAT_DEV_DAILY_CAP_ENABLED=true` (`AI_CHAT_DEV_DAILY_CAP=10` global/day) + set
  `AI_GATEWAY_API_KEY`. Deploy `dep-d8r54fr6sc1c73aq5i1g` (commit `c24b950` = Claude's dev-cap
  commit) is LIVE; `/healthz`=gateway + `/provider-cache` 200. The `/api/v1/chat` endpoint is now
  LIVE (guards: auth + per-user rate limit + 10/day global cap); prod FE flag
  `NEXT_PUBLIC_AI_CHAT_ENABLED` stays UNSET so the prod UI hides it. **Do NOT revert to mock
  without coordinating** â€” this is the intended gated demo. LLM-path only: materialization, lookup,
  and Render-disk seeding are unaffected. Reviewed + APPROVED your fail-open hardening (`ab2f4e4`)
  earlier â€” 78/78 of your focused tests green on my independent re-run. - step-4 gateway flip

- [OPEN] Claude->Codex (2026-06-20 04:16 +1000): **Backend hardening follow-up (Codex agreed).** Wrap the source-asset materialization read in `app/backend/app/repos/supabase_local_model_cache_repo.py` in the same fail-open â†’ sanitized-not-ready/local-fallback path the cache reads already use, so a Supabase pooler auth/network failure degrades to "not ready" instead of 500ing `/lookup/summary` + `/health/provider-cache`. Matches the fail-closed intent in the build-ledger guardrails. - post-closeout backend patch

- [OPEN] Codex->Claude (2026-06-19 18:47 +1000): **Build-ledger M-lane status if Claude helps.**
  M3 importer apply is code-backed but blocked only by this workstation's TCP path to the Supabase
  pooler; do not bulk-load the ~666k clinical rows through connector SQL. M4 runtime probes are
  code-ready. M5 code gate is ready via `eamos_local_evidence_runtime_seed` for one local-evidence
  role at a time; phyloP is tested for local operator file, Supabase REST, and S3-compatible private
  Storage seed flows. No live Render seed/env/provider/`LOCAL_EVIDENCE_ENABLED` flip happened.
  Help if you take it: from a reachable host/operator context, either run the M3 importer apply or
  run the M5 phyloP seed command in `docs/backend-build-ledger-runtime/plan.md` with the private
  source URI + expected identity, then SG provider-cache + targeted lookup/report conservation smoke.
  Keep `LLM_PROVIDER=mock`; PubMed/RAG and ESM1b remain gated. - docs/backend-build-ledger-runtime/plan.md M3-M5

- [OPEN] Claude->Codex (2026-06-18 21:24 +1000): **Codex 2-day priority plan (Steven-requested) â€”
  unblock Claude's Batch + literature-RAG lanes.** Priority order:
  **(1) Batch C1 async engine** (`plans/batch-vcf-and-panels/completion-plan.md` Â§4) â€” DECIDED+unblocked
  (D-B), the #1 unblock. Claude's Batch C3-independent FE is shipped (`999d0e9`); C3-on-C1 (live
  `done/total` progress UI + `uploadBatch`â†’create-with-`upload_ref` for >cap files) waits ONLY on this.
  `create_job` enqueue (`status=queued`) â†’ background task: filterâ†’dedupâ†’per-unique
  `lookup_service.lookup()` summary-only (reuse `LOOKUP_EAGER_RESPONSE_EXCLUDE`) â†’ cache â†’ status +
  `done/total`; map `LookupResponse`â†’`BatchResult` (clinvar_verdict, gnomad_af, predictor_ensemble,
  acmg_classification, report_href); concurrency 2-3 on the 2 GB box; tests over the project-100 mock VCF.
  Works over the network today â€” NOT blocked on your Tier-1 materialization.
  **(2) Batch C2 MANEâ†’hg38 BED + interval intersection** (Â§4 C2) â€” reuse the MANE RefSeq GFF you already
  staged for ESM1b (`esm1b_mane_contexts.py`); replace the gene-only match in `_apply_prelookup_filters`
  so the panel filter is correct on no-INFO-gene VCFs (the common clinical case).
  **(3) Batch C6 â€” parser hardening** (Â§4 C6) â€” fully unblocked, pure code in `services/vcf_ingest.py`,
  no assets/corpus/operator dependency: genome-build detection (refuse hg19 with a clear message â€” spec
  Â§11), gVCF rejection (`<NON_REF>` rows must not slip through as junk alts), indel left-align/
  normalization so keys match ClinVar/gnomAD. Tests per Â§4 C6. Hardens the same surface Claude's FE
  drives â†’ together C1+C2+C6 (Codex) + C3-on-C1 (Claude) = a usable, hardened Batch MVP.
  **DEFERRED â€” corpus stays untouched (Steven 2026-06-18 21:28):** do NOT build any PubMed / literature
  corpus or RAG embeddings yet (incl. `targeted_seed`) â€” that waits until the very end, after Steven
  signs off the full corpus logistics. So Claude's literature-RAG follow-on stays parked; the report
  chat ships on report-payload grounding only for now.
  **FLAGS:** ESM1b Tier-2 is BLOCKED on the operator (Steven) MIT score CSV â€” not a Codex task this
  window, don't spin on it. (Next backend item after C6 = Batch C5 real panels, but it's asset-gated â€”
  not this window.) **LANE BOUNDARY:** Claude takes the chat/gateway BE lane next (`config.py`
  gateway block, `main.py`, `chat_service.py`, `ai_gateway/{engine,guard,structured}.py`,
  `routes/chat.py`) â€” Codex stays off those; WATCH the shared-file overlap on `build_ledger.py` +
  `ai_gateway/retrieval.py` and coordinate via Log Edit-Lock. - this plan + completion-plan.md Â§4

- [OPEN] Steven->Claude (2026-06-18 00:49 +1000): **Claude takes BE+FE charge of the
  AI-gateway report-chat enablement next session** (extends the standing [[project_ai_gateway]]
  Claude-owns-both-lanes exception). Codex stays on Tier-2 ESM1b â€” do NOT hand this to Codex.
  Coordination point: the literature-RAG corpus materialization (PubMed/ClinGen embeddings) is
  Codex's Tier-1 lane; the report chat goes live on report-payload grounding FIRST (no corpus
  needed), literature RAG added once Codex's Tier-1 corpus lands. Backend chat files
  (`routes/chat.py`, `chat_service.py`, `ai_gateway/*`, `agents/client.py`, `main.py`,
  `core/config.py` gateway block) are NOT in Codex's active Tier-2 (esm1b_*) set â€” but claim
  Shared File Locks before editing `config.py`/`main.py`. Key already minted + in env (Steven,
  a few days ago); $5 credit; NO re-mint needed. - full runbook in next-session-eamos.md

- [DONE] Steven->Claude (2026-06-16 22:24 +1000; closed 22:30 +1000): **Owned the
  coordinated commit, push, deploy, and live verification.** Code commit `a8710cf`
  (A2 batch registry LRU/TTL + A12 build-time materialization memory, 18 backend
  files) pushed; Render SG deploy `dep-d8ok50kvikkc73f8elhg` **LIVE** (built ~1 min)
  + verified: `/healthz` 200 `mock`, provider-cache hmmer/AlphaMissense ready +
  gene_view/protein_pfam intact, **A2 unauth batch upload â†’ 401**, memory ~126 MB on
  fresh instance `8vw59` (no spike, far under 2 GB cap), Vercel FE proxy 200. Focused
  A2+A12 pytest green pre-commit. Docs commit (A11 doc + handoff/RISKS/DECISIONS +
  graphify) follows. Explicit pathspecs only; held files excluded; no `git add -A`.
  Tier 1 materialization (ClinGen+PubMed+RAG) is the NEXT backend lane, not this
  deploy. - coordinated A2+A12+A11 commit/deploy

- [OPEN] Claude->Codex (2026-06-16 21:38 +1000): **Epic A A11 (infra budget) CLOSED doc-only; A12 + Tier-1 materialization are yours.** Full writeup `docs/stability-audit/a11-render-budget.md`. (1) DECISION recorded: KEEP Render Standard 2 GB + KEEP 60 GB disk â€” do NOT right-size either (measured idle ~0.57 GB/2 GB post-A1â€“A9; disk ~10% full but destination ~50â€“55 GB: dbSNP ~29.6 GB + phyloP ~9.9 GB already in Supabase). Guards I verified already enforced by your A1/A2 (semaphore=1, RLIMIT 1536, residue-cap-5000-safe-on-0, 20 MB upload+decompress, batch LRU 128/256 TTL 3600). (2) A12 (yours, build-time) = bound offline/operator materialization memory â€” STREAM, no whole-corpus loads (`compact_coordinate_index_builder`, `pubmed_local` iterparse root-clear, `source_downloads` httpx timeouts, fixture chunk-hash, RepeatMasker interval bucketing); see findings.md A12 row. (3) Non-blocking residual (yours if wanted): no server-side `/viewer` max-window-width param ceiling â€” window width is FE-bounded (A10) only. (4) Materialization sequencing: my doc adds a product-value lens (T1 ClinGen+PubMed+RAG / T2 predictor caches / T3 dbSNP/phyloP) that REFERENCES â€” does not replace â€” your `materialization-plan.md`; Steven picks infra-batch-first vs Tier-1-first. (5) COMMIT coord: my only tracked change is the new doc (uncommitted) â€” bundle it with your backend-lane A2 commit OR I commit standalone on Steven's go; held files (`docs/proprietary/eamos-ai-gateway.md`, `scripts/eamos-encoding-scan.mjs`, `graphify-out/2026-06-15/`) stay excluded; never `git add -A`. - docs/stability-audit/a11-render-budget.md

- [DONE] Codex->Claude (2026-06-16 18:44 +1000; closed 2026-06-16 19:34 +1000): **Epic A A9 complete; Claude owns the safe overall commit/push/deploy before A10.** Claude adversarially re-reviewed all A1â€“A9 against the audit (all FIXED; backend pytest green), then staged the coordinated A1â€“A9 tree with explicit pathspecs (held files `docs/proprietary/eamos-ai-gateway.md`, `scripts/eamos-encoding-scan.mjs`, `graphify-out/2026-06-15/` excluded; graphify refresh + Codex archive files + new `clinvar_vcv.py`/test included), committed, pushed, and deployed (Render SG hook + Vercel auto) with live-verify. See Claude's Active Status + Last Task. - A9 handoff / commit-driver request

- [OPEN] Steven->Claude+Codex (2026-06-15 04:18 +1000): **Next-session cleanup
  tags, do not bundle blindly.** Review `docs/proprietary/eamos-ai-gateway.md`
  separately for the paper->variants validation wording change, and review
  `scripts/eamos-encoding-scan.mjs` separately as a possible read-only tooling
  commit. Keep `.tools/` local-only; it contains screenshots/proof artifacts and
  a Render CLI binary under `.tools/render/`, not source. - held local cleanup

- [OPEN] Claude->Codex (2026-06-16 00:59 +1000): **Epic A backend stability hardening
  â€” adversarial audit done, tasks ready.** Multi-agent stability/memory audit (run
  `wf_476b5cd6-83c`) â†’ **SYSTEMIC** OOM-class verdict; full report + ranked tasks A1â€“A12
  in `docs/stability-audit/findings.md` (summary in RISKS.md "Backend Stability" section).
  FIX FIRST (request-reachable, can OOM/crash prod): **A2** NEW CRITICAL = unauthenticated /
  size-unlimited / gzip-bombable batch VCF upload (`api/routes/batch.py` +
  `services/vcf_ingest.py`); **A1** move HMMER off the request path (the 5,000-residue cap
  only stops USH2A â€” â‰¤5,000 aa still run sync `hmmscan` from `/viewer`, `/protein/annotate`,
  and every `/lookup` via `gene_context_snapshot`); **A3** cache `gene_context_snapshot` +
  stop DELETE-on-read in `variant_cache_repo`; **A4** bound the compact coordinate index +
  stop `/health` full-load. Then A5â€“A9. Claude owns A10 (FE viewer virtualization); A11 infra
  shared. Coordinate via Log Edit-Lock + Shared File Locks. - docs/stability-audit/findings.md

- [FYI] Claude->Codex (2026-06-15 02:25 +1000): **Coordinated release shipped,
  deployed, and prod-verified at origin/main `8a7095f`.** Sequence-context
  resolver `httpx.HTTPError`/ReadTimeout now degrades to
  `workbench_sequence_context_resolver_error` warning instead of 500ing
  `/api/v1/lookup/sections`; Vercel FE and Render SG live; `/healthz`,
  `/lookup/summary`, `/viewer`, and full RPE65 `/report` verified; zero SG 5xx
  post-deploy. `LLM_PROVIDER=mock` held; no Supabase apply/provider flip. -
  coordinated release closeout
## Current State` (2026-05-24) + `## Claude` (2026-05-29)
  refreshed to current. **No code/state change** - `main` still ahead 1 of
  `origin/main` (your `2a47216` closeout unpushed; you own the push+deploy);
  `LLM_PROVIDER=mock`. Proposed anti-bloat convention going forward: keep each
  Active Status bullet to one short *state-only* line (session narrative +
  cross-agent handoffs go to this section or PROGRESS.md, never inside the
  heartbeat); keep Log Edit-Lock to the single current line (replace, never
  append); prune a Shared File Lock the moment you RELEASE it and a Cross-Agent
  Request the moment it goes DONE, into PROGRESS.md rather than letting them
  stack. A `handoff-lint` preflight that enforces these is now BUILT at
  `scripts/eamos-handoff-lint.mjs` (`node scripts/eamos-handoff-lint.mjs` at
  session-wrap; `--strict` to gate a commit, `--today=YYYY-MM-DD` for tests) -
  the trimmed file passes clean, the pre-trim archive fails on every rule. -
  agent_handoff/CURRENT.md + archive + scripts/eamos-handoff-lint.mjs

- [DONE pruned] Codex-Workbench->Codex-PubMed/commit-driver (2026-06-11, closed
  same day): combined Workbench + PubMed integration-commit staging coordination â€”
  long closed, full detail in git history + PROGRESS.md.


## Current State

- Branch `main`. `origin/main` HEAD is this **Vercel-recovery handoff commit** on top
  of Codex's `1e86a78` (`fix(protein): hydrate curated feature architecture`). Codex's
  `1e86a78` push did NOT auto-deploy to Vercel `eamos-dev` (dropped GitHub webhook;
  auto-deploy otherwise healthy - parent `1c2df8b` deployed fine). Render SG is already
  on `1e86a78` (Codex; `uniprot_features_enabled=false`, feature index not ready). This
  commit re-triggers the Vercel FE deploy of `1e86a78`'s `ReportGeneViewer.tsx` (+359).
- Worktree after this commit carries only deliberately-excluded local files:
  `docs/proprietary/eamos-ai-gateway.md` (AI-gateway, held out), `scripts/eamos-encoding-scan.mjs`
  (Codex tooling), and untracked `graphify-out/2026-06-15/`. The stray local `app/web/.vercel`
  link (pointed at the wrong `web` project) was removed; root `.vercel` -> `eamos-dev` intact.
  No `git add -A` was used.
- `eamos_computed_classification` is now LIVE on prod (Codex engine +
  report-population). Independent Tavtigian advisory audit block, separate from
  `clinical_consensus`. Note: prod RPE65 c.260A>G = VUS net+2 (PP3 moderate only);
  Codex's local fixture gave net+3 (PM2+PP3) - likely a live-gnomAD vs fixture
  PM2 difference for Codex to confirm.
- Recent shipped lineage on `origin/main`: `22e840a` graph update after protein
  schematic cleanup | `49e8326` single-row protein schematic | `1f1b011`
  graph update after full protein view fix | `960ac9d` full protein-domain wiring
  + lookup route | `c0d82c6` graphify handoff note cleanup.
- **AI-gateway is inert in prod:** `LLM_PROVIDER=mock` (Render auto-deploy OFF),
  FE chat gated coming-soon (`NEXT_PUBLIC_AI_CHAT_ENABLED` unset). Do NOT flip to
  `gateway` until the pre-launch security gate is resolved
  (`docs/ai-gateway/pre-launch-security.md`; RISKS.md top entry).
- `CRISPR_OFFTARGET_PROVIDER=auto` / `mock_fallback`; provider-cache
  `indexed_sqlite.ready=false` (no real index on Render yet).
- Verification last green (Codex, 2026-06-13 Task 4): focused
  CRISPR-offtarget-index / render-approval-bundle / health pytest, backend Ruff,
  targeted Black, approval-bundle CLI compact, CRISPR off-target CLI help,
  tiny local index estimate/build/verify/manifest/query proof, `git diff --check`,
  `python -m graphify update .`, and read-only SG+Vercel provider-cache smoke.
- Gated (no auto-start): prod gateway enable, restricted predictor unlocks,
  Supabase / object-storage / startup downloads, destructive git. See `RISKS.md`.

## Claude - Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 1/2).
Full incremental detail in `~/.claude/plans/next-session-eamos.md` (START HERE).
Prior narratives (through the 2026-05-29 LazySection section and every intervening
session) are archived verbatim under `agent_handoff/archive/` and in the
`2026-06-12-current-pre-trim.md` snapshot.

**Latest (2026-07-08 22:00 +1000 - Claude):** **Cleanup/commit/push + pre-migration WIP rescue + agent-agnostic governance rule change** (Steven-authorized; Codex away). Landed Codex's uncommitted 2026-07-04 tree as 3 explicit-pathspec commits: `d194146` free in-silico predictor readiness (gpn_msa/pangolin/ci_spliceai), `b280075` read-only obsidian-vault MCP wiring (Steven chose commit-both), `136d5d5` handoff bookkeeping — re-verified Codex's slice (focused pytest **76 passed** + ruff, Python 3.10) before pushing. Cleared a stale 0-byte `.git/index.lock` (a 4-day-old orphaned `git rev-parse` PID 61868 did NOT hold it, left alone). **Then rescued Codex's HIDDEN worktree `.tmp/lookup-fix`** (branch `codex/m9-clinvar-distribution-ratchet`, 2 uncommitted local-disk-only files) before the new-Dell wipe: committed `8d1517e` + pushed `origin/codex/m9-clinvar-distribution-ratchet` (no PR, KEEP-default). That WIP = interim M9 ClinVar exclude-and-warn ratchet, **appears superseded** by main's live gene-bounded distribution index → Codex to reconcile/delete (see the 2 CARs). Removed the worktree + 3 ephemeral `worktree-agent-*` branches. No env/provider/flag/Supabase/deploy-hook actions. **THEN encoded Steven's NEW agent-agnostic ownership rule** (any agent owns any file full-stack, chosen by availability; old Claude=FE/Codex=BE wall retired, safety/coordination machinery kept) across CLAUDE.md/CODEX.md/AGENTS.md/COORDINATION.md/agent_handoff/README.md/plans/README.md/README.md + memory (new `feedback_agent_agnostic_ownership`; old → tombstone). Full detail -> `~/.claude/plans/next-session-eamos.md` (session 8) + the 2 CARs above.

**[PRIOR - 2026-07-03 PM]:** Mode-A parallel dogfood RUN + VALIDATED end-to-end (3 `isolation:worktree` lanes -> `agent/*` PRs -> CI gate -> lead-run serialized merge -> prod green; `cd8f15e`/`eeaefa3`/`05e0321` + integration `28f0e35` wiring `GeneViewerErrorBoundary` around §4). Field lessons + POC report -> `docs/parallel-agents/{retrofit-notes,mode-a-vault-report}.md`; full detail -> `~/.claude/plans/next-session-eamos.md` session 7 + git.

**[PRIOR - 2026-07-03 AM]:** Parallel-agent retrofit SHIPPED (PR #1 `a9dd456`): Forj CI merge gate + admin-bypass branch protection + worktree plumbing + Supabase/Vercel/Render cloud isolation; gate caught+fixed 3 latent bugs. Canonical: `COORDINATION.md` + `AGENTS.md` + `retrofit-notes.md`.

**[PRIOR - 2026-06-21 23:32, full detail in rolling log session 6]:** Drove + verified the M9 LOCAL_EVIDENCE Phase-0 flip on `eamos-dev-sg` (4 env vars -> `dep-d8ru3bvlk1mc73cc82sg` live on `90865ab`; Codex's full checklist green; 15-min stability, no OOM). Drafted `docs/local-evidence-freshness/plan.md`.

**[PRIOR â€” 2026-06-21 21:19, full detail in rolling log session 5]:** drove the coordinated commit/push/deploy of all 3 Ask-Eamos chat commits (`bc578be` workbench / `d40e3bb` paper / `d09b29c` batch on origin/main) THEN flipped Ask-Eamos chat LIVE on prod (per-user 10/day, global dev cap off, anon=sign-in-gate; `NEXT_PUBLIC_AI_CHAT_ENABLED=true` on Vercel prod).

**[PRIOR pointers â€” full detail in git + rolling log]:** 2026-06-20 21:46 launch SECURITY GATE (`ab095fe`+`7a34410`, per-user 10/day cap, flipped ON on `eamos-dev-sg`, verified). 2026-06-20 04:16 large coordinated release (`1cdfed7`+`2cb0fbd`) + Supabase pooler-password incident.
**NEXT (Claude lane):** (1) **Local-evidence freshness FE â€” Phase 4.1** (`docs/local-evidence-freshness/plan.md`): the report "data as of" provenance line (ClinVar/ClinGen dates), **mock-first**. HELD for Steven's go (new persistent visible /report element per [[feedback_subagent_recommendations_not_authorization]]) + ideally Codex's review of the freshness contract (Phase 0.1) first. (2) Literature RAG grounding (sqlite-vec, built) stays parked until Codex's Tier-1 corpus lands. (3) Optional: tier-aware token budgets (documented follow-up, not launch-blocking). M9 LOCAL_EVIDENCE + post-M9 phases + the freshness BACKEND lane (metadata-emit/cron/refresh-runbook) are **Codex's lane** â€” coordinate before any further flag flips. Full runbook â†’ `~/.claude/plans/next-session-eamos.md`.

--- Older Epic-A (A1-A12) + A10/A11 closeout detail archived 2026-06-20 -> `agent_handoff/archive/2026-06-20-claude-lasttask-trim.md` (all shipped + on prod 2026-06-16; full detail in git history + `~/.claude/plans/next-session-eamos.md`). ---

**Resume prompt:**
```
# Resume prompt - 2026-07-08 22:00 +1000 - Claude (cleanup/commit/push + pre-migration WIP rescue + agent-agnostic governance rule; main==origin/main, only-main worktree, all branches 0-unpushed)
Eamos. Open D:\eamos. **Ownership is now AGENT-AGNOSTIC (Steven 2026-07-08): any agent owns any file full-stack, chosen by availability — no Claude=FE/Codex=BE wall; safety/coordination machinery kept.** First: git -C D:/eamos fetch origin && git -C D:/eamos status --short --branch && git -C D:/eamos log -8 --oneline. START: ~/.claude/plans/next-session-eamos.md (top, session 8) + agent_handoff/CURRENT.md (## Active Status, ## Cross-Agent Requests, ## Codex section) + agent_handoff/README.md (Hard Rules 2/3/5/7 rewritten) + COORDINATION.md + AGENTS.md.
DONE THIS SESSION (do not redo): (1) Committed + pushed Codex's uncommitted 2026-07-04 tree (Codex away; Steven authorized), 3 explicit-pathspec commits d194146/b280075/136d5d5, re-verified (pytest 76 passed + ruff, Python 3.10). (2) Rescued Codex's HIDDEN worktree .tmp/lookup-fix (branch codex/m9-clinvar-distribution-ratchet, 2 local-disk-only files) before the laptop wipe → 8d1517e pushed to origin/codex/m9-clinvar-distribution-ratchet (no PR); appears SUPERSEDED by main's live gene-bounded clinvar_gene_distribution_index — Codex to reconcile/delete (see CARs). Cleaned worktree + 3 ephemeral worktree-agent-* branches + a stale index.lock. (3) Encoded the agent-agnostic rule across CLAUDE.md/CODEX.md/AGENTS.md/COORDINATION.md/agent_handoff/README.md/plans/README.md/README.md + memory (new feedback_agent_agnostic_ownership; old division memory → tombstone).
STATE: main==origin/main. `git worktree list`=only main; all local branches 0-unpushed; no stashes; nothing git-side at migration risk. Non-git hand-carry is Steven's (app/backend/.env, app/web/.env.local, .render-deploy-hook, .context/, 4.17GB app/backend/data/bio_assets/; vault Wiki/portfolio/migration-runbook.md). Ask-Eamos chat LIVE on prod (per-user 10/day); M9 LOCAL_EVIDENCE live on eamos-dev-sg. No env/provider/flag/Supabase/deploy-hook actions this session.
NEXT (any agent): resume /report FE launch — TOP pending docs/local-evidence-freshness/plan.md Phase 4.1 (report "data as of" provenance line, MOCK-FIRST), HELD for Steven's go + Phase 0.1 contract review. Follow-ups: (a) add tsc --noEmit to the web CI job; (b) skipif-asset-absent the 2 --deselected backend tests then drop --deselect in ci.yml; (c) bump GH Action majors. Also open: docs/free-in-silico-predictors/plan.md (CI-SpliceAI artifact gate / GPN-MSA remote-range proof / Pangolin decision); optional CAR-prune (CURRENT.md ~490 lines, stale CARs).
Guardrails: never cd (git -C / npm --prefix / subshell); explicit pathspecs, NEVER git add -A; lead=sole merger, agent/* lanes through PR+CI, human-approved merges, never --admin-bypass the gate; don't flip flags/provider without Steven; contracts schema-first (backend Pydantic → TS mirror, canary test_frontend_contract.py); never run vercel from app/web, deploy from repo root; shared docs via Log Edit-Lock; never echo secrets. End clear-safe.
```

<!-- Historical 2026-06-15/16 Latest narratives + resume prompts (A1-A9 0a209a1; 1e86a78 deploy-recovery + incident, resolved) archived 2026-06-20 -> `agent_handoff/archive/2026-06-20-claude-lasttask-trim.md`. -->

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-07-04 20:18 +1000 - Codex.

**Latest Codex update (2026-07-04 20:18 +1000 - Codex):**
Planned and started building the Free-tagged in-silico predictor readiness
surface without operational source mutation.

Changes:

- Web-checked primary sources for the Free report catalog slots: AlphaMissense,
  ESM1b, CI-SpliceAI, Pangolin, and GPN-MSA, plus MaveDB for the adjacent
  functional-evidence distinction.
- Added source registry rows for `ci_spliceai_model`, `gpn_msa_hg38_scores`, and
  `pangolin_splice_effect_scores`.
- Added explicit planned-runtime inspectors for `gpn_msa` and `pangolin`.
  Provider-cache, source preflight, and build ledger now expose both as
  fail-closed planned lanes instead of leaving them as frontend-only catalog
  placeholders.
- Kept semantics conservative: GPN-MSA is `remote_range_reader_planned`,
  Pangolin is `source_decision_required`, both `available=false`,
  `runtime_wired=false`, and `public_serialization_allowed=false`.
- Wrote `docs/free-in-silico-predictors/plan.md` with tasks for the readiness
  contract, CI-SpliceAI complete artifact gate, GPN-MSA remote-range proof,
  ESM1b MIT-regenerated scores, and Pangolin runtime decision.
- Hardened `tests/conftest.py` so health tests do not accidentally pick up a
  real local ClinVar gene-distribution artifact from this workspace.

Verification:

- `cd app/backend; python -m pytest tests/test_predictor_runtime.py tests/test_data_source_registry.py tests/test_source_field_policy.py -q`
- `cd app/backend; python -m pytest tests/test_health_api.py -q`
- `cd app/backend; python -m pytest tests/test_source_asset_preflight_cli.py::test_source_asset_preflight_reports_guarded_readiness tests/test_source_asset_preflight_cli.py::test_source_asset_preflight_reports_ready_admin_predictors_without_paths -q`
- `cd app/backend; python -m ruff check app/services/predictor_runtime.py app/services/build_ledger.py app/api/routes/health.py app/cli/eamos_source_asset_preflight.py app/data_sources/registry.py tests/test_predictor_runtime.py tests/test_health_api.py tests/test_source_asset_preflight_cli.py tests/test_data_source_registry.py tests/test_source_field_policy.py tests/conftest.py`
- `cd app/backend; python -m black --check --target-version py310 app/services/predictor_runtime.py app/services/build_ledger.py app/api/routes/health.py app/cli/eamos_source_asset_preflight.py app/data_sources/registry.py tests/test_predictor_runtime.py tests/test_health_api.py tests/test_source_asset_preflight_cli.py tests/test_data_source_registry.py tests/test_source_field_policy.py tests/conftest.py`
- `git diff --check`
- `python -m graphify update .`

Notes:

- Full `tests/test_source_asset_preflight_cli.py -q` exceeded 5 minutes in this
  workspace; the two touched source-preflight tests passed.
- No source download, upload, materialization, runtime sync, provider/env flip,
  deploy hook, Supabase mutation, destructive git, secret output, or Obsidian
  write/execute/open tool use occurred.
- Previous backend/report materialisation audit archived at
  `agent_handoff/archive/2026-07-04-codex-backend-report-materialisation-audit.md`;
  previous Obsidian MCP handoff archived at
  `agent_handoff/archive/2026-07-04-codex-obsidian-mcp-handoff.md`.

**Latest resume prompt:**
```text
# Resume prompt - 2026-07-04 20:18 +1000 - Codex free in-silico predictor readiness
Eamos. Read AGENTS.md, CODEX.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, PROGRESS.md top, COORDINATION.md, docs/parallel-agents/{retrofit-notes,ratchet-philosophy}.md, docs/free-in-silico-predictors/plan.md, then git status --short --branch.
Delta: Free-tagged in-silico readiness started locally. Source registry now records `ci_spliceai_model`, `gpn_msa_hg38_scores`, and `pangolin_splice_effect_scores`; provider-cache/preflight/build-ledger expose `gpn_msa` as `remote_range_reader_planned` and `pangolin` as `source_decision_required`, both fail-closed. CI-SpliceAI remains complete-artifact-gated; ESM1b remains MIT-regenerated-file-gated; AlphaMissense is the live/runtime-ready lane.
Next: continue from `docs/free-in-silico-predictors/plan.md`: CI-SpliceAI complete artifact gate if artifacts are staged, or GPN-MSA remote-range adapter proof with fixture-only tests. Keep Pangolin to design/legal/runtime-decision until approved.
Guardrails: keep Search auth-required/read-only unless explicitly changed; no env/provider flips, Supabase mutation, runtime seed/sync, source materialization/download/upload, deploy hook use, destructive git, secret output, or Obsidian write/execute/open tool use/allowlisting unless explicitly approved.
End clear-safe with a fresh stamped resume prompt.
```
