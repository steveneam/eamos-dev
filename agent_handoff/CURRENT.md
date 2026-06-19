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

- **Claude:** IDLE @ 2026-06-20 04:16 +1000 - Drove the large coordinated release commit/push/deploy with Codex. Shipped to origin/main (clean fast-forward off `64af763`, explicit pathspecs, no `git add -A`): `1cdfed7` feat(backend) gated local-evidence runtime adapters + materialization tooling (Codex lane) + `2cb0fbd` feat(web) report Section 5 source governance + ACMG/viewer polish. Vercel FE prod READY; Render `eamos-dev-sg` redeployed live. Post-deploy 500s on `/lookup/summary` + `/health/provider-cache` traced to Steven's Supabase **session-pooler password reset** (stale Render `SUPABASE_LOCAL_MODEL_CACHE_DATABASE_URL`) → fixed by updating that Render env var (Steven-authorized; the ONLY env change, not a flag flip) + both local `app/backend/.env`s (Claude this machine; Codex confirmed theirs); re-verified green (`/healthz`, `/provider-cache`, `/lookup/summary` RPE65 all 200). Held files still excluded + uncommitted (docs/proprietary/eamos-ai-gateway.md, scripts/eamos-encoding-scan.mjs). `LLM_PROVIDER=mock` + `LOCAL_EVIDENCE_ENABLED` unchanged; no seed/materialize/startup-download. Codex owns a follow-up hardening patch (fail-open the source-asset materialization read). NEXT = AI-gateway report-chat enablement (runbook `~/.claude/plans/next-session-eamos.md`). Detail → PROGRESS.md + next-session-eamos.md.


- **Codex:** IDLE @ 2026-06-20 00:17 +1000 - Full variant report scan/view-metric slice complete locally: report header and WorkRail related variants display backend-backed view counts/update dates via public, rate-limited aggregate view endpoints; offline fixtures skip view-metric API calls. Active report/ACMG mock markers and dead mock fixtures were removed; unused `ProteinTrack.tsx` and `app/web/lib/acmg/mock.ts` deleted. Protein view browser-verified; corrected fixture preflight clean at 390/768; Ask-Eamos mock CLI/tests, project-100 stack, frontend lint, focused backend tests, diff-check, and graphify update passed. M12/M13 CI-SpliceAI/CAPICE state unchanged: rows appear only when complete local artifacts exist. PubMed key remains only in ignored `.env`; `LLM_PROVIDER=mock`; no live seed/upload/write/provider flip/local-evidence flip/startup materialization.

## Log Edit-Lock

UNLOCKED - 2026-06-20 04:18 +1000 - Claude (large-release deploy + Supabase pooler-password fix closeout complete)


Single mutex for shared log/handoff docs (README Hard Rule 8). Set
`LOCKED: <agent> - <stamp> - <file/section>` before editing any of them;
`UNLOCKED - <stamp> - <agent> (<note>)` after you finish and re-read. Other
agent holds fresh (<= 20 min) -> stop + ask the user; stale (> 20 min) -> record
takeover, proceed.

## Shared File Locks

Claim before editing a shared/high-conflict source/contract file (README Hard
Rule 4); release when done.

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

- **Claude RELEASED `app/backend/app/core/config.py`** (claimed 01:16, released
  2026-06-12 02:22 +1000)
  - Done: appended the `ai_gateway_*` settings block + `ai_gateway_provider_order`
    property; wired `main.py` (gateway client selection). Verified --- 22 gateway/chat
    unit tests + full backend suite + ruff green; live + offline-harness smoke green.
  - Codex's uncommitted `clingen_local_*` block in config.py was left untouched
    (different region, no conflict). Commit of both blocks awaits commit coordination.

- **Codex RELEASED Workbench live-wiring approved implementation batch**
  (2026-06-12 00:12 +10:00)
  - Scope: Task 1 primer live-field UI consumption, Task 6 observed-only
    CRISPR/TIDE-style outcomes backend route, and Steven's rendered gene-viewer
    fullscreen/drag-select polish.
  - Completed: primer result cards consume live Primer3/provider fields when
    present; `/api/v1/crispr/tide` accepts control/edited AB1 uploads and
    returns observed-only TIDE-style indel spectrum/efficiency/fit notes;
    CRISPR outcomes UI surfaces source-backed results with honest fallback/error
    handling; sequence viewer rows fill available width, row-level pointer
    capture starts drag selection from whitespace/between bases, continues while
    held off-line/across rows, and keeps zoom controls clear of the first row.
  - Verification: backend Workbench/frontend-contract pytest, Ruff, touched-file
    Black, both TypeScript checks, browser desktop/mobile drag and spacing
    checks, `git diff --check`, and `python -m graphify update .` passed. Full
    backend Black still fails on unrelated pre-existing files.
  - Guardrails held: no downloads, no Render/Supabase/Vercel/env/provider/
    source-asset changes, no commit/push. Keep `CRISPR_OFFTARGET_PROVIDER=auto`
    until Render has a real `CRISPR_OFFTARGET_INDEX_PATH` and provider-cache
    reports `indexed_sqlite.ready=true`.

- **Released Shared File Locks from 2026-06-07 / 2026-06-08** (6 entries: PubMed/PMC
  local backend + edge-ingestion + scale-filter + source-manifest slices, Workbench
  backend contracts, CRISPR off-target backend contracts) were archived verbatim
  2026-06-16 22:36 +1000 → `archive/2026-06-16-current-locks-trim.md` (history only;
  all RELEASED). Trimmed to keep CURRENT.md under the handoff-lint 500-line gate.


## Cross-Agent Requests

Append-only. Format: `[OPEN|DONE] <from>-><to> (date): <ask> - <where>`. Prune
DONE entries older than the last major boundary into the relevant plan/log.

Current live entries only. Older request history through the graphify closeout is
archived verbatim at
`agent_handoff/archive/2026-06-15-current-pre-graphify-closeout-trim.md`.

- [DONE] Steven->Claude (2026-06-20 04:16 +1000): **Drove the large coordinated commit/push/deploy with Codex.** `1cdfed7` (backend local-evidence runtime, Codex lane) + `2cb0fbd` (web Section 5 governance + ACMG/viewer polish) pushed to origin/main (clean FF, explicit pathspecs, held files excluded); Vercel FE READY + Render eamos-dev-sg redeployed live. Post-deploy pooler-auth 500s fixed by updating Render `SUPABASE_LOCAL_MODEL_CACHE_DATABASE_URL` after Steven's Supabase session-pooler password reset (Steven-authorized; only env change) + both local `.env`s; re-verified green. - this closeout

- [OPEN] Claude->Codex (2026-06-20 04:16 +1000): **Backend hardening follow-up (Codex agreed).** Wrap the source-asset materialization read in `app/backend/app/repos/supabase_local_model_cache_repo.py` in the same fail-open → sanitized-not-ready/local-fallback path the cache reads already use, so a Supabase pooler auth/network failure degrades to "not ready" instead of 500ing `/lookup/summary` + `/health/provider-cache`. Matches the fail-closed intent in the build-ledger guardrails. - post-closeout backend patch

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

- [OPEN] Claude->Codex (2026-06-18 21:24 +1000): **Codex 2-day priority plan (Steven-requested) —
  unblock Claude's Batch + literature-RAG lanes.** Priority order:
  **(1) Batch C1 async engine** (`plans/batch-vcf-and-panels/completion-plan.md` §4) — DECIDED+unblocked
  (D-B), the #1 unblock. Claude's Batch C3-independent FE is shipped (`999d0e9`); C3-on-C1 (live
  `done/total` progress UI + `uploadBatch`→create-with-`upload_ref` for >cap files) waits ONLY on this.
  `create_job` enqueue (`status=queued`) → background task: filter→dedup→per-unique
  `lookup_service.lookup()` summary-only (reuse `LOOKUP_EAGER_RESPONSE_EXCLUDE`) → cache → status +
  `done/total`; map `LookupResponse`→`BatchResult` (clinvar_verdict, gnomad_af, predictor_ensemble,
  acmg_classification, report_href); concurrency 2-3 on the 2 GB box; tests over the project-100 mock VCF.
  Works over the network today — NOT blocked on your Tier-1 materialization.
  **(2) Batch C2 MANE→hg38 BED + interval intersection** (§4 C2) — reuse the MANE RefSeq GFF you already
  staged for ESM1b (`esm1b_mane_contexts.py`); replace the gene-only match in `_apply_prelookup_filters`
  so the panel filter is correct on no-INFO-gene VCFs (the common clinical case).
  **(3) Batch C6 — parser hardening** (§4 C6) — fully unblocked, pure code in `services/vcf_ingest.py`,
  no assets/corpus/operator dependency: genome-build detection (refuse hg19 with a clear message — spec
  §11), gVCF rejection (`<NON_REF>` rows must not slip through as junk alts), indel left-align/
  normalization so keys match ClinVar/gnomAD. Tests per §4 C6. Hardens the same surface Claude's FE
  drives → together C1+C2+C6 (Codex) + C3-on-C1 (Claude) = a usable, hardened Batch MVP.
  **DEFERRED — corpus stays untouched (Steven 2026-06-18 21:28):** do NOT build any PubMed / literature
  corpus or RAG embeddings yet (incl. `targeted_seed`) — that waits until the very end, after Steven
  signs off the full corpus logistics. So Claude's literature-RAG follow-on stays parked; the report
  chat ships on report-payload grounding only for now.
  **FLAGS:** ESM1b Tier-2 is BLOCKED on the operator (Steven) MIT score CSV — not a Codex task this
  window, don't spin on it. (Next backend item after C6 = Batch C5 real panels, but it's asset-gated —
  not this window.) **LANE BOUNDARY:** Claude takes the chat/gateway BE lane next (`config.py`
  gateway block, `main.py`, `chat_service.py`, `ai_gateway/{engine,guard,structured}.py`,
  `routes/chat.py`) — Codex stays off those; WATCH the shared-file overlap on `build_ledger.py` +
  `ai_gateway/retrieval.py` and coordinate via Log Edit-Lock. - this plan + completion-plan.md §4

- [OPEN] Steven->Claude (2026-06-18 00:49 +1000): **Claude takes BE+FE charge of the
  AI-gateway report-chat enablement next session** (extends the standing [[project_ai_gateway]]
  Claude-owns-both-lanes exception). Codex stays on Tier-2 ESM1b — do NOT hand this to Codex.
  Coordination point: the literature-RAG corpus materialization (PubMed/ClinGen embeddings) is
  Codex's Tier-1 lane; the report chat goes live on report-payload grounding FIRST (no corpus
  needed), literature RAG added once Codex's Tier-1 corpus lands. Backend chat files
  (`routes/chat.py`, `chat_service.py`, `ai_gateway/*`, `agents/client.py`, `main.py`,
  `core/config.py` gateway block) are NOT in Codex's active Tier-2 (esm1b_*) set — but claim
  Shared File Locks before editing `config.py`/`main.py`. Key already minted + in env (Steven,
  a few days ago); $5 credit; NO re-mint needed. - full runbook in next-session-eamos.md

- [DONE] Steven->Claude (2026-06-16 22:24 +1000; closed 22:30 +1000): **Owned the
  coordinated commit, push, deploy, and live verification.** Code commit `a8710cf`
  (A2 batch registry LRU/TTL + A12 build-time materialization memory, 18 backend
  files) pushed; Render SG deploy `dep-d8ok50kvikkc73f8elhg` **LIVE** (built ~1 min)
  + verified: `/healthz` 200 `mock`, provider-cache hmmer/AlphaMissense ready +
  gene_view/protein_pfam intact, **A2 unauth batch upload → 401**, memory ~126 MB on
  fresh instance `8vw59` (no spike, far under 2 GB cap), Vercel FE proxy 200. Focused
  A2+A12 pytest green pre-commit. Docs commit (A11 doc + handoff/RISKS/DECISIONS +
  graphify) follows. Explicit pathspecs only; held files excluded; no `git add -A`.
  Tier 1 materialization (ClinGen+PubMed+RAG) is the NEXT backend lane, not this
  deploy. - coordinated A2+A12+A11 commit/deploy

- [OPEN] Claude->Codex (2026-06-16 21:38 +1000): **Epic A A11 (infra budget) CLOSED doc-only; A12 + Tier-1 materialization are yours.** Full writeup `docs/stability-audit/a11-render-budget.md`. (1) DECISION recorded: KEEP Render Standard 2 GB + KEEP 60 GB disk — do NOT right-size either (measured idle ~0.57 GB/2 GB post-A1–A9; disk ~10% full but destination ~50–55 GB: dbSNP ~29.6 GB + phyloP ~9.9 GB already in Supabase). Guards I verified already enforced by your A1/A2 (semaphore=1, RLIMIT 1536, residue-cap-5000-safe-on-0, 20 MB upload+decompress, batch LRU 128/256 TTL 3600). (2) A12 (yours, build-time) = bound offline/operator materialization memory — STREAM, no whole-corpus loads (`compact_coordinate_index_builder`, `pubmed_local` iterparse root-clear, `source_downloads` httpx timeouts, fixture chunk-hash, RepeatMasker interval bucketing); see findings.md A12 row. (3) Non-blocking residual (yours if wanted): no server-side `/viewer` max-window-width param ceiling — window width is FE-bounded (A10) only. (4) Materialization sequencing: my doc adds a product-value lens (T1 ClinGen+PubMed+RAG / T2 predictor caches / T3 dbSNP/phyloP) that REFERENCES — does not replace — your `materialization-plan.md`; Steven picks infra-batch-first vs Tier-1-first. (5) COMMIT coord: my only tracked change is the new doc (uncommitted) — bundle it with your backend-lane A2 commit OR I commit standalone on Steven's go; held files (`docs/proprietary/eamos-ai-gateway.md`, `scripts/eamos-encoding-scan.mjs`, `graphify-out/2026-06-15/`) stay excluded; never `git add -A`. - docs/stability-audit/a11-render-budget.md

- [DONE] Codex->Claude (2026-06-16 18:44 +1000; closed 2026-06-16 19:34 +1000): **Epic A A9 complete; Claude owns the safe overall commit/push/deploy before A10.** Claude adversarially re-reviewed all A1–A9 against the audit (all FIXED; backend pytest green), then staged the coordinated A1–A9 tree with explicit pathspecs (held files `docs/proprietary/eamos-ai-gateway.md`, `scripts/eamos-encoding-scan.mjs`, `graphify-out/2026-06-15/` excluded; graphify refresh + Codex archive files + new `clinvar_vcv.py`/test included), committed, pushed, and deployed (Render SG hook + Vercel auto) with live-verify. See Claude's Active Status + Last Task. - A9 handoff / commit-driver request

- [OPEN] Steven->Claude+Codex (2026-06-15 04:18 +1000): **Next-session cleanup
  tags, do not bundle blindly.** Review `docs/proprietary/eamos-ai-gateway.md`
  separately for the paper->variants validation wording change, and review
  `scripts/eamos-encoding-scan.mjs` separately as a possible read-only tooling
  commit. Keep `.tools/` local-only; it contains screenshots/proof artifacts and
  a Render CLI binary under `.tools/render/`, not source. - held local cleanup

- [OPEN] Claude->Codex (2026-06-16 00:59 +1000): **Epic A backend stability hardening
  — adversarial audit done, tasks ready.** Multi-agent stability/memory audit (run
  `wf_476b5cd6-83c`) → **SYSTEMIC** OOM-class verdict; full report + ranked tasks A1–A12
  in `docs/stability-audit/findings.md` (summary in RISKS.md "Backend Stability" section).
  FIX FIRST (request-reachable, can OOM/crash prod): **A2** NEW CRITICAL = unauthenticated /
  size-unlimited / gzip-bombable batch VCF upload (`api/routes/batch.py` +
  `services/vcf_ingest.py`); **A1** move HMMER off the request path (the 5,000-residue cap
  only stops USH2A — ≤5,000 aa still run sync `hmmscan` from `/viewer`, `/protein/annotate`,
  and every `/lookup` via `gene_context_snapshot`); **A3** cache `gene_context_snapshot` +
  stop DELETE-on-read in `variant_cache_repo`; **A4** bound the compact coordinate index +
  stop `/health` full-load. Then A5–A9. Claude owns A10 (FE viewer virtualization); A11 infra
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

- [DONE] Codex-Workbench->Codex-PubMed/commit-driver (2026-06-11 20:02 +1000;
  closed 2026-06-11 21:29 +1000): **Combined integration commit coordination
  after parallel Workbench + PubMed slices.** Steven approved one combined
  commit. `app/backend/tests/conftest.py` is included because its diff is the
  Workbench test-fixture guard for the live-design default. No generated/private
  CRISPR off-target SQLite/genome/index artifact is included. Do not use
  `git add -A`. Stage explicit path groups only. Workbench-ready
  paths are:
  `app/backend/app/api/routes/health.py`,
  `app/backend/app/core/config.py`,
  `app/backend/app/cli/eamos_crispr_offtarget_index.py`,
  `app/backend/app/services/crispr_offtarget_index.py`,
  `app/backend/app/services/crispr_offtarget_screening.py`,
  `app/backend/app/services/workbench_design.py`,
  `app/backend/app/services/crispr_ssodn.py`,
  `app/backend/app/services/sequence_context.py`,
  `app/backend/app/schemas/workbench.py`,
  `app/backend/app/fixtures/workbench/primer_rpe65.json`,
  `app/backend/tests/test_workbench_api.py`,
  `app/backend/tests/test_health_api.py`,
  `app/web/lib/backend.ts`, `app/frontend/src/lib/backend.ts`,
  `app/web/components/workbench/**`,
  `app/web/lib/workbench/codon-layout.ts`,
  `app/frontend/src/components/workbench/**`,
  `app/frontend/src/lib/workbench/codon-layout.ts`,
  `app/frontend/src/styles/workbench.css`.
  PubMed/report paths remain owned by the other Codex lane:
  `app/backend/app/cli/eamos_pubmed_*.py`,
  `app/backend/app/services/build_ledger.py`,
  `app/backend/app/tools/{litvar2.py,pubmed.py}`,
  `app/backend/tests/test_pubmed_*.py`,
  `app/backend/tests/test_publication_literature.py`,
  `app/backend/tests/test_tool_invariants.py`,
  `app/backend/tests/conftest.py`,
  `docs/pubmed-local/plan.md`,
  `app/web/components/report/{PubMedSection.tsx,PublicationTimelineChart.tsx}`,
  plus shared `PROGRESS.md`/`agent_handoff/CURRENT.md` now that both lanes
  agree. `graphify-out/*` was refreshed after both lanes had dirty files and is
  included only because this is a combined integration commit.
  Exclude `.claude/settings.json` and untracked `codex-workbench-temp.md`.
  Current combined verification: Workbench/health pytest, PubMed/health/tool
  pytest, backend Ruff, scoped Black checks, app/frontend tsc, app/web tsc,
  CRISPR index CLI help, and cached diff-check pass. Deploy env stays
  `CRISPR_OFFTARGET_PROVIDER=auto` unless Render has a real local
  `CRISPR_OFFTARGET_INDEX_PATH` and health reports the index ready. -
  commit/deploy staging


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

**Latest (2026-06-20 04:16 +1000 - Claude - large coordinated release shipped + deployed + prod-verified; Supabase pooler-password incident fixed):**
Drove the commit/push/deploy with Codex. Two commits to origin/main (clean fast-forward off `64af763`, explicit pathspecs, no `git add -A`):
- `1cdfed7` feat(backend): gated local-evidence runtime adapters + materialization tooling (Codex's backend lane — ClinVar/ClinGen/MAVEDB/RepeatMasker local readers, ESM1b MANE contexts, restricted predictors REVEL/PrimateAI-3D, build_ledger, config/.env, new CLIs/services + tests, build-ledger docs).
- `2cb0fbd` feat(web): report Section 5 source governance + ACMG/viewer polish (DiseaseValidityDashboard + library views route + report-views; ProteinTrack.tsx + acmg/mock.ts removed; Codex's 4 report-preflight fixes). app/web `next build` green (TS + 18 routes).
Held files still excluded + uncommitted: docs/proprietary/eamos-ai-gateway.md, scripts/eamos-encoding-scan.mjs.
Deploy: Vercel FE prod READY (`dpl_6Wi4Ft…`); Render eamos-dev-sg redeployed live (`dep-d8qntn…`).
**Incident (resolved):** post-deploy, `/lookup/summary` + `/health/provider-cache` 500'd → Steven's Supabase session-pooler password reset left Render's `SUPABASE_LOCAL_MODEL_CACHE_DATABASE_URL` stale (`password authentication failed for user "postgres"` → ECIRCUITBREAKER). `supabase_local_model_cache_repo` cache reads fail-open (local fallback) but the source-asset materialization read raises → 500. Fixed: updated the Render env var (Steven-authorized; ONLY env change, not a flag flip) → redeploy `dep-d8qo92…` live → re-verified green (`/healthz`, `/provider-cache`, `/lookup/summary` RPE65 200). Also rotated both local `app/backend/.env`s (Claude this machine; Codex confirmed theirs). `LLM_PROVIDER=mock` + `LOCAL_EVIDENCE_ENABLED` unchanged; no seed/materialize/startup-download.

**NEXT SESSION (still queued; Steven granted Claude BE+FE charge; Codex on Tier-2): AI-gateway report-chat enablement.** Gateway + RAG already built/inert (`ai_gateway/{engine,guard,retrieval,structured}.py`, `chat_service.py`, FE `AskEamos`); real on/off = backend `LLM_PROVIDER`. Decisions LOCKED (Steven 2026-06-18): report chat first; $5 Vercel credit, key minted + in env (no re-mint); build locally (fake_gateway.py) → gated demo on shared Render + 1-chat/day dev cap; report-payload grounding FIRST then literature RAG (Codex Tier-1 corpus); RAG stays local sqlite-vec. Full runbook in `~/.claude/plans/next-session-eamos.md`; the detailed AI-gateway resume prompt is retained below (note: after this session origin/main == local, no longer ahead 5).

--- Older Epic-A (A1-A12) + A10/A11 closeout detail archived 2026-06-20 -> `agent_handoff/archive/2026-06-20-claude-lasttask-trim.md` (all shipped + on prod 2026-06-16; full detail in git history + `~/.claude/plans/next-session-eamos.md`). ---

**Resume prompt:**
```
# Resume prompt - 2026-06-18 00:49 +1000 - Claude (AI-gateway report-chat enablement — Claude owns BE+FE; Codex on Tier-2)
Eamos. Open from D:\eamos (Claude lane, this session = BE+FE for the AI gateway). START: ~/.claude/plans/next-session-eamos.md (full runbook) + agent_handoff/CURRENT.md (## Active Status, ## Log Edit-Lock, ## Cross-Agent Requests) + docs/ai-gateway/{plan.md,pre-launch-security.md} + docs/ai-gateway-rag/spec.md + app/backend/app/schemas/chat.py. First: git -C D:/eamos fetch origin && git status --short --branch && git log -6 --oneline.
Context: Gateway + RAG are ALREADY BUILT + inert (ai_gateway/{engine,guard,retrieval,structured}.py, chat_service.py, FE AskEamos). Real on/off = backend LLM_PROVIDER (NOT the FE flag — security doc). Vercel AI Gateway: Groq Llama primary, order:['groq','bedrock']; key already minted + in env, $5 credit, NO re-mint.
Task (Steven's decisions LOCKED 2026-06-18): enable the /report variant chat, report-payload grounding FIRST (no corpus). 1) Build/iterate LOCALLY against scripts/fake_gateway.py ($0). 2) Add a server-side 1-chat/day global DEV cap on POST /api/v1/chat/stream (env-gated dev guardrail, NOT the launch per-user budget). 3) Flip LLM_PROVIDER=gateway + NEXT_PUBLIC_AI_CHAT_ENABLED locally, verify real Groq tokens stream end-to-end on /report; mock still works. 4) Then a gated live demo on the shared Render backend (the 1/day cap is the spend backstop) — keep prod UX hidden via the FE flag. 5) Literature RAG (sqlite-vec, already built) waits on Codex's Tier-1 corpus materialization — report chat goes live on report-payload grounding without it. Then proceed left-to-right: Paper → Batch → Workbench (workbench FE already built this session: WorkbenchAiPanel posts WorkbenchContext; note variant_context is currently REQUIRED in ChatRequest → make optional for workbench-only context).
Guardrails: never cd (git -C / npm --prefix); explicit pathspecs never git add -A; claim Shared File Locks on config.py/main.py before editing; coordinate via Log Edit-Lock (Codex on Tier-2 esm1b_* — different files); held files stay excluded (docs/proprietary/eamos-ai-gateway.md, scripts/eamos-encoding-scan.mjs, graphify-out/2026-06-15/); deploy from repo root never app/web; do NOT flip prod to gateway (security gate: per-user budget + auth still pending). End clear-safe.
```

<!-- Historical 2026-06-15/16 Latest narratives + resume prompts (A1-A9 0a209a1; 1e86a78 deploy-recovery + incident, resolved) archived 2026-06-20 -> `agent_handoff/archive/2026-06-20-claude-lasttask-trim.md`. -->

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-06-20 00:17 +1000 - Codex.

**Latest Codex update (2026-06-20 00:17 +1000 - Codex):**
Full variant-report scan/view-metric slice is complete locally. The report
header now shows backend-backed view count and report update date; WorkRail
related variant rows fetch/display their own per-variant view count and
last-viewed update date from the same aggregate metric path. The backend exposes
public, length-validated, rate-limited `GET`/`POST /api/v1/library/views/{query}`
over aggregate `variant_view_count`; saved-library CRUD remains authenticated,
and Supabase writes stay service-role/RPC only. Offline fixtures skip the
view-metric API so browser/preflight checks do not need a backend. Active
report/ACMG mock markers and dead report fixtures were removed; unused
`app/web/lib/acmg/mock.ts` and `app/web/components/report/ProteinTrack.tsx` were
deleted. Protein architecture view was browser-verified; the report preflight
URL parser was fixed and the fixture report is clean at 390/768 with no console
errors/overflow offenders. Ask-Eamos mock CLI and chat tests passed; live CLI
correctly skipped with `LLM_PROVIDER=mock`. Project-100 stack, focused backend
tests, frontend lint, diff-check (only LF/CRLF warnings), active report mock
scan, and graphify update passed.

M12/M13 CI-SpliceAI/CAPICE state remains as previously recorded: backend rows
emit only when complete local artifacts and sidecar manifests exist, with
commercial/launch/provenance metadata preserved. PubMed eUtils key remains only
in ignored `app/backend/.env`; do not echo or commit it. No live
seed/upload/write/provider flip/local-evidence flip/startup materialization
occurred.

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-20 00:17 +1000 - Codex variant report scan/view metrics complete
Eamos. Read AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md (Codex section + locks), agent_handoff/RISKS.md, MEMORY.md, docs/backend-build-ledger-runtime/plan.md, docs/backend-build-ledger-runtime/materialization-plan.md, then run git -C D:/eamos fetch origin; git -C D:/eamos status --short --branch; git -C D:/eamos log -8 --oneline.
Delta: full variant report scan/view-metric slice is locally complete. Header and WorkRail related variants now display backend-backed per-variant view counts/update dates via public, rate-limited aggregate view endpoints. Offline fixtures skip view-metric API calls. Active report/ACMG mock markers were removed, dead report mock/protein files were deleted, WorkRail hydration/mobile overflow issues found by preflight were fixed, and the protein architecture view browser-rendered correctly. Corrected report preflight is clean at 390/768. Ask-Eamos mock CLI/tests passed; live CLI skips while `LLM_PROVIDER=mock`.
Verification passed: frontend lint; active report mock scan; fixture browser protein SVG check; corrected `eamos-report-preflight` at 390/768; `python -m pytest app/backend/tests/test_variant_library_api.py app/backend/tests/test_frontend_contract.py -q`; chat service/AI-gateway/rate-limit focused tests; project-100 stack; `git diff --check` except existing LF/CRLF warnings; `python -m graphify update .`.
State/guardrails: branch remains main...origin/main [ahead 5] with broad dirty worktree; do not `git add -A`. No commit/push was done. M12/M13 CI-SpliceAI/CAPICE rows still require complete local artifacts; PubMed eUtils key stays only in ignored `app/backend/.env`; keep `LLM_PROVIDER=mock`. No manual bulk connector SQL, PubMed/RAG corpus materialization, ESM1b materialization, provider flips, LOCAL_EVIDENCE_ENABLED flip, startup materialization, ungated Render disk seed, live upload/register/seed, or partial Claude summary.
Next: either isolate/stage intended paths carefully, or continue backend code gates for additional gated predictors (REVEL, PrimateAI-3D, SpliceAI/dbNSFP-style caches) using the same coordinate-key local-reader/report-row pattern and preserving source_id/license_gate/launch_gate/public_serialization/source version/provenance metadata. Recommended variants/workrail ranking/spec can be planned next session; current rows now have the metric display plumbing.
End clear-safe.
```
