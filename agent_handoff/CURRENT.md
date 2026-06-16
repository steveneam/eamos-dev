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

- **Claude:** IDLE @ 2026-06-16 22:36 +1000 - Drove the coordinated Epic A A2+A12+A11 commit/push/deploy/verify as commit-driver (Steven's direction). Code `a8710cf` (Codex A2 batch registry LRU/TTL + A12 materialization memory, 18 files) + docs commit (A11 doc + handoff + graphify) pushed; Render SG `dep-d8ok50kvikkc73f8elhg` LIVE + verified (`/healthz` 200 mock, A2 unauth→401, ~126 MB fresh instance, Vercel 200). Request-reachable OOM/crash class A1–A12 + A11 infra fully closed + on prod. `LLM_PROVIDER=mock`; held files excluded; no Supabase/provider flip. NEXT = Tier-1 materialization (Codex lane): ClinGen+PubMed+literature-RAG. Detail → `~/.claude/plans/next-session-eamos.md`.


- **Codex:** IDLE @ 2026-06-17 00:58 +1000 - Tier 1 generated-artifact lane committed locally at current `HEAD` and ClinGen local generated SQLite artifact + manifest uploaded to private Supabase Storage via S3 multipart. Upload-safe patch landed after first attempt exposed unsupported SQLite MIME + unsanitized failure text; final retry uploaded `eamos_clingen_local` SHA256 `4b4a93b86116425f9949ea168df506b3ca17808d26db4e336ad833d1f73ada3d`. PubMed local and literature embeddings are not present locally yet. Guardrails held: no Supabase metadata registration/apply, no provider flip, no `LOCAL_EVIDENCE_ENABLED` flip, no Render/Vercel mutation, held/unrelated files excluded.

## Log Edit-Lock

UNLOCKED - 2026-06-17 00:58 +1000 - Codex (Tier 1 commit amended with upload-safe fix; ClinGen generated artifact uploaded; metadata/provider flips still gated)


Single mutex for shared log/handoff docs (README Hard Rule 8). Set
`LOCKED: <agent> - <stamp> - <file/section>` before editing any of them;
`UNLOCKED - <stamp> - <agent> (<note>)` after you finish and re-read. Other
agent holds fresh (<= 20 min) -> stop + ask the user; stale (> 20 min) -> record
takeover, proceed.

## Shared File Locks

Claim before editing a shared/high-conflict source/contract file (README Hard
Rule 4); release when done.

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

**Latest (2026-06-16 22:30 +1000 - Claude - coordinated A2+A12+A11 commit/push/deploy/verify):**
Drove the coordinated release as commit-driver (Steven's direction). **Code commit `a8710cf`** =
Codex's A2 batch registry LRU/TTL + A12 build-time materialization memory bounds (18 backend files,
staged via `git add app/backend` — no held files there) pushed; focused A2+A12 pytest green pre-commit.
**Render SG deploy `dep-d8ok50kvikkc73f8elhg` LIVE** (built ~1 min) + live-verified: `/healthz` 200
`mock`/db ok, provider-cache hmmer+AlphaMissense ready + gene_view/protein_pfam intact, **A2 unauth
batch upload → 401**, memory ~126 MB on fresh instance `8vw59` (no spike, far under 2 GB), Vercel FE
proxy 200. Docs commit (A11 doc + this handoff/RISKS/DECISIONS + graphify refresh) follows. **The
request-reachable OOM/crash class A1–A12 + A11 infra is now fully closed + on prod.** NEXT = Tier-1
materialization (Codex lane): ClinGen + PubMed + literature-RAG.

--- A11 detail (closed earlier this session, doc-only): Closed A11 with
`docs/stability-audit/a11-render-budget.md` — grounded the OOM/concurrency safety budget in MEASURED
prod RSS (Render MCP) and recorded the sizing decisions. **KEEP Standard 2 GB** (idle ~0.57 GB / 2 GB ~27% post-A1–A9; OOM'd instance hit
2.07 GB on 06-15; heavy compute off the request path — all guards already enforced by Codex
A1/A2: cache-or-fail-closed `allow_run=False`, `BoundedSemaphore(1)`, `RLIMIT_AS` 1536 MB,
residue cap 5000-safe-on-0, 20 MB upload + 20 MB gzip-decompress ceilings, batch LRU 128/256
TTL 3600s). **KEEP 60 GB disk** (right-sized: ~5–6 GB / 60 GB ~10% today, but durable Supabase
holds dbSNP ~29.6 GB + phyloP ~9.9 GB → full local-first stack ~50–55 GB; Render disks can't
shrink). Doc adds a product-value materialization sequencing lens (Tier 1 ClinGen+PubMed/RAG →
Tier 2 predictor caches → Tier 3 dbSNP/phyloP) referencing Codex's `materialization-plan.md`.
One residual = server-side viewer window-width ceiling is FE-only (A10) today → Codex follow-up,
non-blocking. Answered Steven live: full Render account = 1 web svc (Standard 2 GB) + 60 GB disk,
no Postgres/KV, ≈$40/mo list. **No code/backend/infra change**; `LLM_PROVIDER=mock`; held files
excluded. NEXT = A12 (Codex, build-time) + Tier-1 materialization (Codex lane + gated offline
downloads). Prior milestone (A10 FE virtualization, commit `858a036`, Vercel
`dpl_5g1mV9EhYnz8i7cyrMwarnMw9KWr`) detail retained below for context:

**Prior (2026-06-16 20:42 +1000 - Claude - Epic A A10 (FE virtualization) shipped):**
Implemented + shipped A10, the last request-reachable (FE browser-crash) item of the
stability epic. Commit `858a036` (FE-only, 5 files), pushed, Vercel auto-deploying
(`dpl_5g1mV9EhYnz8i7cyrMwarnMw9KWr`, BUILDING at push time — confirm READY + spot-check).
- **FullLocusViewer** windowed (fixed-height virtual scroller; only on-screen rows mount)
  + `.fl-scroller` gains a viewport `max-height` so the full-gene locus scrolls in its own
  pane — **Steven-approved** visible change (virtualization is impossible without a bounded
  viewport; the scroller was already built for internal scroll). Live-verified RPE65
  full-gene: 265 rows / 21,200 base-spans → **~54 rows / ~4,300 mounted**; scroll shifts the
  window, variant row mounts + highlights, exon/intron banding intact. CFTR (~3,150 rows) =
  same bounded path → no crash.
- **ReportGeneViewer** AlphaMissense band → ≤800 mean-score bins (was ~5,200 rect+title per
  residue); ≤800-aa proteins unchanged. Node-proven (533→identical, 5,202→≤800, averaging,
  ends, variant sums). On-screen long-protein heatmap is a post-deploy spot-check (RPE65
  fixture has no AM data; the local dev server's prod API proxy was 5xx-ing on
  `/lookup/sections`).
- **CodonDetail** O(n²) per-render scans hoisted to parent useMemo Set/Map (search
  window-string + clinvar/oligo/qIdx `flat.findIndex`) → O(1) per base.
- **SequenceViewerV2** `onRestrictionSelect` → useCallback (blocksEqual holds during drags).
Verified: tsc + eslint green; 33/33 Node logic-equivalence checks; live browser pass.
Minor follow-up: full-locus auto-scroll targets model `variantRowIndex` (≈223) but the
variant pin is on row ≈200 — pre-existing adapter mismatch, unchanged from the original;
log for the adapter owner.
**Commit status (UPDATE 2026-06-16 22:30):** Claude drove the coordinated commit as commit-driver —
Codex's A2+A12 backend tree is now committed (`a8710cf`) + deployed (`dep-d8ok50kvikkc73f8elhg`
live + verified) + the A11 doc/handoff/graphify in the following docs commit. No longer uncommitted.

**Resume prompt:**
```
# Resume prompt - 2026-06-16 22:30 +1000 - Claude (Epic A A2+A12+A11 committed/deployed/verified → Tier-1 materialization next)
Eamos. Open from D:\eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE — top section) + agent_handoff/CURRENT.md (## Active Status, ## Log Edit-Lock, ## Cross-Agent Requests) + agent_handoff/RISKS.md (Backend Stability: A1–A12 + A11 all DONE + deployed) + docs/backend-build-ledger-runtime/materialization-plan.md (Codex's per-asset sequence) + docs/stability-audit/a11-render-budget.md (infra budget + disk roadmap). First: git -C D:/eamos fetch origin && git status --short --branch && git log -6 --oneline.
Context: Epic A is fully shipped + on prod. Code commit a8710cf (Codex A2 batch registry LRU/TTL + A12 build-time materialization memory, 18 files) + a docs commit (A11 doc + handoff + graphify) both pushed; Render SG dep-d8ok50kvikkc73f8elhg LIVE + verified (/healthz 200 mock, hmmer/AM ready, A2 unauth upload→401, mem ~126MB fresh instance 8vw59, Vercel 200). The request-reachable OOM/crash class A1–A12 + A11 infra is closed. KEEP Render Standard 2 GB + 60 GB disk (rationale in a11-render-budget.md). Held files still excluded/dirty: docs/proprietary/eamos-ai-gateway.md, scripts/eamos-encoding-scan.mjs, graphify-out/2026-06-15/.
Task: Tier-1 materialization (Codex's backend lane; Steven decided Tier-1-first): ClinGen local + PubMed local + literature embeddings (RAG) — smallest footprint, biggest product unlock (literature engine + variant-chat RAG). Materialize OFFLINE → Supabase private Storage → Render-disk sync; NEVER startup-download; no Render one-off jobs for disk seeding; no LOCAL_EVIDENCE_ENABLED flip until verified via provider-cache. Then Tier 2 predictor caches, Tier 3 dbSNP/phyloP. Optional backend residuals: A3 shared lookup-assembly cache + server-side /viewer window-width ceiling (FE-only today). Claude FE: no open ask.
Guardrails: never cd (git -C / npm --prefix); explicit pathspecs never git add -A; LLM stays mock; no Supabase apply/provider flip; held files stay excluded; coordinate via Log Edit-Lock + Shared File Locks; deploy from repo root never app/web. End clear-safe.
```

<!-- history below: 2026-06-16 19:46 A1–A9 (shipped 0a209a1); then 1e86a78 deploy-recovery + incident (resolved) -->
**Latest (2026-06-16 19:46 +1000 - Claude - Epic A A1–A9 shipped + prod-verified):**
Adversarially re-reviewed Codex's Epic A A1–A9, ran backend pytest GREEN, committed `0a209a1`,
pushed, deployed Render SG + Vercel, live-verified prod (USH2A `cache_hit`/248 features ~571 MB;
A2 unauth batch upload → 401). Full detail in `~/.claude/plans/next-session-eamos.md`.

<!-- history below: 1e86a78 deploy-recovery + incident (now resolved; A1–A9 superseded it) -->
**Latest (2026-06-15 22:16 +1000 - Claude - deploy recovery + OPEN prod incident):**
Recovered the dropped-webhook Vercel deploy of Codex's `1e86a78`, then discovered `1e86a78`
is a degraded prod release.
- **Deploy recovery (DONE):** `1e86a78` never auto-deployed to `eamos-dev` (one-off dropped
  GitHub->Vercel webhook; auto-deploy otherwise healthy). Re-triggered via `50d9dc8` (handoff +
  `app/web/.gitignore` ignores `.vercel`) -> Vercel built `dpl_8Hced...` READY, aliased to
  `eamos-dev.vercel.app` (200), carrying `1e86a78`'s `ReportGeneViewer.tsx`. Removed the stray
  local `app/web/.vercel` link and **deleted the wrong `web` Vercel project** (Steven OK; Codex's
  manual `vercel --prod` from `app/web` had gone there, to `web-beryl-delta-96`, never the real
  domain). `vercel project ls` -> only `eamos-dev`. **Always deploy from repo root, never `app/web`.**
- **OPEN INCIDENT (next session):** `1e86a78` reached Vercel prod for the first time and showed
  two regressions, both backend-rooted: (1) **Render SG OOM >2GB** (instance 8wqsn, 22:00, on the
  USH2A 5,202 aa protein annotation via the reworked `protein_annotation.py` - inefficient/leak);
  (2) **protein features missing** vs Codex's earlier "50 blocks/248 hits" because the new
  UniProt-first path needs `uniprot_features_enabled` + a seeded Render feature index, both
  off/not-ready. Full write-up: RISKS.md top section (committed `814c1fd`).
- **Steven deferred the fix to next session + authorized Claude CROSS-LANE** (backend + frontend +
  Render/Vercel) to fix it. Prod left on `1e86a78` (degraded). Rollback-first is a valid opener
  (Vercel target `dpl_4FZS9XtQxjrvXmDFyCNGtPPpvpfc` = `1c2df8b`).
- Guardrails held: `LLM_PROVIDER=mock`; no Supabase apply / provider flip; held files excluded
  (`docs/proprietary/eamos-ai-gateway.md`, `scripts/eamos-encoding-scan.mjs`, `graphify-out/2026-06-15/`).

**Next (priority):**
1. **Fix the `1e86a78` regression** (cross-lane authorized): profile + fix `protein_annotation.py`
   memory on large proteins (USH2A); fix the flag-off fallback so the full Pfam/HMMER architecture
   shows (no feature loss), OR provision+seed the Render UniProt index + flip the flag. Coordinate
   with Codex (locks). Then redeploy (Render hook + Vercel) and live-verify USH2A.
2. If the fix isn't quick, **roll back first** (Vercel `1c2df8b` + Render pre-`1e86a78`) to restore
   the verified-good protein architecture, then fix offline.
3. Backlog: genomic view Section 4 (not started); graphify semantic pass; B1 forest/B7 beeswarm.

**Resume prompt:**
```
# Resume prompt - 2026-06-15 23:30 +1000 - Claude (1e86a78 incident RESOLVED + verified on prod)
# NOTE: the 1e86a78 fix task in the body below is DONE (Codex shipped a9de024/dd3b71d; Claude verified live on SG at 23:30 - USH2A 200 cache_hit/248 hits, memory flat ~1.21GB, no OOM). Do NOT re-fix. Next work = backlog: genomic view Section 4, a backend hmmscan e-value/overlap threshold (raw 248 hits incl. cross-fold noise), graphify semantic pass. START HERE = ~/.claude/plans/next-session-eamos.md (✅ RESOLVED section). Body kept verbatim for history:
# --- historical resume prompt (1e86a78 fix, now complete) ---
# Resume prompt - 2026-06-15 22:16 +1000 - Claude (OPEN prod incident: fix 1e86a78, cross-lane authorized)
Eamos. Open from D:\eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE) + agent_handoff/CURRENT.md (## Active Status + ## Log Edit-Lock + ## Current State + ## Claude; protocol -> README.md) + agent_handoff/RISKS.md (TOP section = the 1e86a78 incident). First: git -C D:/eamos fetch origin && git status --short --branch && git log -6 --oneline.
Context: Tonight Claude recovered a dropped-webhook Vercel deploy of Codex's 1e86a78 (re-triggered via 50d9dc8 -> live on eamos-dev.vercel.app), removed the stray app/web/.vercel link, and deleted the wrong `web` Vercel project (Steven OK). But 1e86a78 reached prod for the first time and is DEGRADED: (1) Render SG OOM >2GB on the USH2A protein annotation (reworked protein_annotation.py - inefficient/leak), and (2) protein features missing because the new UniProt-first path needs uniprot_features_enabled + a seeded Render feature index, both off/not-ready. Full detail in RISKS.md (committed 814c1fd).
Task: FIX the 1e86a78 regression. STEVEN AUTHORIZED CLAUDE CROSS-LANE this session - drive backend + frontend + web server (Render + Vercel). Plan: reproduce USH2A locally + watch RSS; fix protein_annotation memory (stream/cap, no whole-payload buffering); make flag-off fall back to full Pfam/HMMER architecture without dropping features OR provision+seed the Render UniProt index (pre-seed, no startup-download) + flip the flag; verify (pytest + local browser); deploy Render via .render-deploy-hook + Vercel auto on push; live-verify USH2A full architecture + no OOM under load. Rollback-first is a valid opener if the fix isn't quick (Vercel dpl_4FZS9XtQxjrvXmDFyCNGtPPpvpfc = 1c2df8b; Render pre-1e86a78). COORDINATE with Codex (Log Edit-Lock + Shared File Locks; he got the same handoff - don't double-drive app/backend/**). Guardrails: never cd (git -C / npm --prefix), explicit pathspecs never git add -A, LLM stays mock, no Supabase apply/provider flip without Steven, held files (ai-gateway doc, encoding-scan, graphify-out/2026-06-15) stay excluded, deploy from repo root never app/web. End clear-safe.
```

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-06-17 00:58 +1000 - Codex.

**Latest Codex update (2026-06-17 00:58 +1000 - Codex):**
Tier 1 materialization readiness plus the generated-artifact upload/sync lane is committed locally.
ClinGen local generated SQLite was also uploaded to private Supabase Storage after Steven approval.
No push/deploy/provider flip and no Supabase metadata registration/apply. Prior section archived at
`agent_handoff/archive/2026-06-17-codex-tier1-readiness-pre-generated-artifact.md`.

Completed:
- Committed the slice locally at current `HEAD` (`feat(backend): add Tier 1 generated artifact sync lane`)
  with explicit pathspecs; held/unrelated files were left out.
- Literature embedding materializer is streaming/batched; provider-cache now reports sanitized
  `source_assets.literature_embeddings`; build ledger includes `literature_rag_embeddings`.
- Added generated Tier 1 artifact service for ClinGen local, PubMed local, and literature RAG
  SQLite assets. It computes checksum identity manifests, plans/uploads to private Supabase
  Storage through the existing REST/S3 transports, and syncs from local file or private Storage
  to Render-disk runtime paths via temp-file, checksum, schema validation, manifest sidecar, and
  atomic replace.
- Added CLIs: `python -m app.cli.eamos_generated_artifact_upload` and
  `python -m app.cli.eamos_generated_artifact_sync`.
- `eamos_source_asset_preflight` now includes a read-only `generated_artifact_upload_plan`.
- `docs/backend-build-ledger-runtime/materialization-plan.md` now documents the generated SQLite
  upload/sync lane and keeps metadata registration as the next separate step.
- Non-mutating upload plan found one ready local artifact: `clingen_local` 463,036,416 bytes,
  schema `eamos.clingen_local.v1`, SHA256
  `4b4a93b86116425f9949ea168df506b3ca17808d26db4e336ad833d1f73ada3d`. PubMed local and
  literature embeddings were missing locally.
- First approved ClinGen S3 upload attempt failed because Supabase rejected
  `application/vnd.sqlite3`; it also exposed unsanitized local-path text in failure messages.
  Fixed generated-artifact uploads to use `application/octet-stream` and sanitize merged upload
  failures, added regression coverage, amended the commit, reran graphify, then retried.
- Final approved ClinGen upload succeeded: asset and manifest are in private Storage at
  `generated/eamos_clingen_local/clingen_local_sqlite/sha256-4b4a93b86116425f9949ea168df506b3ca17808d26db4e336ad833d1f73ada3d/`.

Verification:
- Focused pytest files passed individually:
  `test_generated_source_artifacts.py`, `test_source_storage_uploads.py`,
  `test_compact_coordinate_index_materialization.py`, `test_literature_retrieval.py`,
  `test_health_api.py`, and `test_source_asset_preflight_cli.py` (`-p no:langsmith` for the slow
  preflight file so teardown returned cleanly).
- `python -m py_compile ...` on touched runtime/test files.
- `python -m ruff check ...` on touched runtime/test files.
- `python -m black --check --fast ...` on touched runtime/test files.
- `git diff --check -- ...` passed with only existing LF/CRLF warnings.
- `python -m graphify update .` passed after the upload-safe code fix; graph rebuilt to 14,055
  nodes / 33,487 edges and backed up curated files under `graphify-out/2026-06-17/`.
- `python -m app.cli.eamos_generated_artifact_upload --compact` planned one ready artifact and two
  missing artifacts; `python -m app.cli.eamos_generated_artifact_upload --artifact clingen_local
  --upload --upload-mode s3_multipart --compact` succeeded on retry.
- No Supabase metadata registration/apply, no `LOCAL_EVIDENCE_ENABLED` flip, no Render/Vercel
  mutation, no push/deploy/live Render verification.

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-17 00:58 +1000 - Codex Tier 1 generated-artifact commit + ClinGen upload
Eamos. Read AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, agent_handoff/DECISIONS.md, docs/backend-build-ledger-runtime/materialization-plan.md, docs/stability-audit/a11-render-budget.md, then run git status --short --branch and git log -5 --oneline.
Delta: Tier 1 generated-artifact lane committed locally at current `HEAD`; approved ClinGen local generated SQLite artifact + manifest uploaded to private Storage under the SHA256 `4b4a93b86116425f9949ea168df506b3ca17808d26db4e336ad833d1f73ada3d` path. Upload-safe fix amended into the commit after Supabase rejected `application/vnd.sqlite3` and exposed unsanitized failure text.
Next: add Supabase metadata registration rows for the uploaded ClinGen generated artifact (`source_asset_objects` / `source_asset_materializations`) when Steven approves metadata mutation, or build/upload PubMed local + literature embeddings first if the next priority is completing the Tier 1 trio before registration. Render-disk sync remains separate and gated.
Guardrails: `LLM_PROVIDER=mock`; no Supabase apply/provider flip without Steven; no `LOCAL_EVIDENCE_ENABLED` flip until provider-cache/materialization verification is green; no Render one-off disk seeding; deploy from repo root only; explicit pathspecs never `git add -A`; keep held files excluded (`docs/proprietary/eamos-ai-gateway.md`, `scripts/eamos-encoding-scan.mjs`, `graphify-out/2026-06-15/`); unrelated `README.md`/`docs/tech-stack.md` should be reviewed separately if still dirty. End clear-safe.
```
