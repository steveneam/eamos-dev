# Current Agent State

> **Live state only.** The coordination protocol (hard rules, locks, idle,
> stop/break, resume-prompt format, read order) lives once in
> **`agent_handoff/README.md`** Ã¢â‚¬â€ read it every session. History lives in
> `PROGRESS.md` / `CHANGELOG.md` / each agent's own next-session doc, **not
> here**. Risks: `agent_handoff/RISKS.md`. Tasks: `agent_handoff/TASKS.md`.
> Worktree truth: `git status --short --branch` (not a frozen inventory file).
>
> Per README Hard Rule 9: update the two `Last Task & Resume` sections only at
> **major** boundaries and **replace, never stack** Ã¢â‚¬â€ append+archive the old
> verbatim first if it has unrecorded detail. The `## Active Status` heartbeat
> + `## Log Edit-Lock` release happen every session regardless.

## Active Status (heartbeat Ã¢â‚¬â€ set when you start and stop)

- **Claude:** ACTIVE @ 2026-06-14 02:26 +1000 - **Steven-directed coordinated release (Codex handed ownership; Codex IDLE/standing down).** Committed all 4 uncommitted lanes as explicit-pathspec commits on top of `449151a`+`d9c9f95`: `f16390a` Workbench hardening · `2e8090d` compact-index materialization + Gene View ledger fix · `95a57e4` ClinGen `c.260A>G` correction (behavior change) · `0c91461` AI-gateway RAG/messy-text/paper-variants P1+2 (inert) · plus this shared-docs/graph commit. Safety gate before committing: full backend pytest GREEN on combined tree, ruff clean, black clean (reformatted 12 lane-4 files). `main` ahead 6 → push → Vercel FE auto-deploy + manual Render SG deploy + provider-cache verify. Held `LLM_PROVIDER=mock` / `RAG_ENABLED=false` / `CRISPR_OFFTARGET_PROVIDER=auto` / `PRIMER_SPECIFICITY_PROVIDER=template`; no env/provider flip. Graphify refresh owed (Codex's lane).

- **Codex:** IDLE @ 2026-06-14 01:52 +10:00 - **Compact coordinate index/Pfam materialization closeout done.** Supabase MCP auth verified; stale Pfam `download_pending` materialization metadata reconciled to `ready` after live provider-cache proof; compact index source version, object, manifest sidecar, and SG materialization rows registered; Render Dashboard Shell materialized the compact index to persistent disk with staged checksum/schema proof; deploy-only restart `dep-d8mnkq9o3t8c73c1m6k0` cleared the web-process missing cache. Live SG now reports `source_assets.compact_coordinate_index.status=ready`, `build_ledger.items.coordinate_compact_index.status=ready`, Pfam available, and hg38 ready. `gene_view=runtime_partial` is now a deployed-code blocker only: live commit `550641d` has the stale build-ledger compact blocker, while the local worktree already fixes `_gene_view_item`; ship that with Steven's later coordinated Codex-Claude commit/push/deploy. Saved a reusable private source-asset materialization workflow in `docs/deployment/render-provider-flip-workflows.md`. No commit, push, env/provider flip, startup download, or generated artifact commit; keep `LLM_PROVIDER=mock` and `CRISPR_OFFTARGET_PROVIDER=auto`.

## Log Edit-Lock

UNLOCKED · 2026-06-14 02:26 +1000 · Claude (coordinated release: 5 commits, push+deploy)

Single mutex for shared log/handoff docs (README Hard Rule 8). Set
`LOCKED: <agent> Ã‚Â· <stamp> Ã‚Â· <file/section>` before editing any of them;
`UNLOCKED Ã‚Â· <stamp> Ã‚Â· <agent> (<note>)` after you finish and re-read. Other
agent holds fresh (Ã¢â€°Â¤ 20 min) Ã¢â€ â€™ stop + ask the user; stale (> 20 min) Ã¢â€ â€™ record
takeover, proceed.

## Shared File Locks

Claim before editing a shared/high-conflict source/contract file (README Hard
Rule 4); release when done.

**No active locks.** Every record below is RELEASED. Released-lock records older than one week (<=2026-06-01, 59 entries) were archived 2026-06-12 -> `archive/2026-06-12-current-pre-trim.md`; the recent (<=1wk) ones are retained below for context.

- **Claude RELEASED `app/backend/app/core/config.py`** (claimed 01:16, released
  2026-06-12 02:22 +1000)
  - Done: appended the `ai_gateway_*` settings block + `ai_gateway_provider_order`
    property; wired `main.py` (gateway client selection). Verified — 22 gateway/chat
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

- **Codex RELEASED PubMed/PMC local PubTator/LitVar edge-ingestion slice**
  (2026-06-08 02:32 +1000)
  - Scope: `app/backend/app/services/pubmed_local.py`,
    `app/backend/app/cli/eamos_pubmed_local_materialize.py`,
    `app/backend/app/cli/eamos_pubmed_local_preflight.py`, and
    `app/backend/tests/test_pubmed_local.py`.
  - Completed: schema/manifest v4 with `pubmed_literature_edge`; operator
    PubTator/LitVar edge JSONL inputs; edge source-file load-order/provenance;
    per-source edge import/orphan counters; seed pre-scan so edge hits can
    retain neutral article rows during query-scoped materialization; local
    PubMed search enrichment through existing `pubtator` and `litvar2_snippet`
    EP-VLEx fields. Live E-utilities fallback/refresh and no-startup-download
    policy preserved.
  - Verification: `test_pubmed_local.py`, health/publication/lookup/cache/
    frontend-contract pytest subset, Ruff, Black, `py_compile`,
    `python -m graphify update .`, and `git diff --check` passed.

- **Codex RELEASED PubMed/PMC local backend slice**
  (2026-06-08 00:24 +1000)
  - Scope: `app/backend/app/services/pubmed_local.py`,
    `app/backend/app/tools/pubmed.py`,
    `app/backend/app/cli/eamos_pubmed_local_materialize.py`,
    `app/backend/app/cli/eamos_pubmed_local_preflight.py`,
    `app/backend/app/api/routes/{health,lookup}.py`,
    `app/backend/app/services/{build_ledger,lookup_sections,lookup_service}.py`,
    `app/backend/app/{core/config.py,main.py,schemas/lookup.py}`,
    `app/backend/app/fixtures/tools/pubmed_local_sample.xml`,
    `app/backend/tests/{test_pubmed_local.py,test_health_api.py}`, and
    `app/backend/.env.example`.
  - Completed: explicit no-network materialization/preflight CLIs, standalone
    SQLite PubMed-local schema, provenance/checksum manifest, license-gated
    abstract retention, de-identified/sanitized metadata surfaces,
    disabled-by-default local PubMed adapter with `refresh=true` live bypass
    and no-hit live fallback, health/build-ledger status, and additive
    publication request refresh flag.
  - Verification: `test_pubmed_local.py`, `test_health_api.py`,
    tool/publication/lookup/cache/frontend-contract pytest subset, Ruff, Black,
    `py_compile`, and `python -m graphify update .` passed.

- **Codex RELEASED PubMed/PMC local scale-filter hardening**
  (2026-06-08 01:10 +1000)
  - Scope: `app/backend/app/services/pubmed_local.py`,
    `app/backend/app/cli/eamos_pubmed_local_materialize.py`,
    `app/backend/app/cli/eamos_pubmed_local_preflight.py`, and
    `app/backend/tests/test_pubmed_local.py`.
  - Completed: operator-supplied PMC OA license metadata overlays keyed by
    PMCID; optional PubMed XML `.md5` sidecar verification; materialization
    manifest/preflight counters for domain-filtered rows, PMC overlays, and
    input checksum status; opt-in `--domain-filter biomedical` profile with
    gene/biology/biochemistry/chemistry positives, language/status/pub-type
    guardrails, negative-domain exclusions, and token-aware short-gene matching.
    Biomedical engineering, chemical engineering, tissue engineering,
    biomaterials, retinal/gene-delivery contexts are explicit keep cases.
  - Verification: `test_pubmed_local.py`, health/publication/lookup/cache/
    frontend-contract pytest subset, Ruff, Black, `py_compile`, and
    `python -m graphify update .` passed.

- **Codex RELEASED PubMed/PMC local source-manifest scale slice**
  (2026-06-08 01:47 +1000)
  - Scope: `app/backend/app/services/pubmed_local.py`,
    `app/backend/app/cli/eamos_pubmed_local_materialize.py`,
    `app/backend/app/cli/eamos_pubmed_local_preflight.py`,
    `app/backend/app/api/routes/health.py`, and
    `app/backend/tests/test_pubmed_local.py`.
  - Completed: schema/manifest v3 adds `pubmed_source_file` rows with sanitized
    source-file basename, load order, source kind, format, size, MD5 sidecar
    status, and per-shard import counters. Materialization/preflight/health now
    expose source-file count, source-kind counts, and aggregate import stats by
    source kind. CLI adds `--xml-source-kind auto|baseline|update|pubmed_xml`
    for explicit baseline/update batch labeling.
  - Verification: `test_pubmed_local.py`, health/publication/lookup/cache/
    frontend-contract pytest subset, Ruff, Black, `py_compile`, and
    `python -m graphify update .` passed.

- **Codex RELEASED Workbench backend contracts and adapter materialization checks**
  (2026-06-07 19:31 +1000)
  - Scope: `app/backend/app/schemas/workbench.py`,
    `app/backend/app/api/routes/workbench.py`,
    `app/backend/app/services/workbench_design.py`,
    `app/backend/app/services/crispr_ssodn.py`,
    `app/backend/app/services/predictor_runtime.py`,
    `app/backend/app/api/routes/health.py`,
    `app/backend/app/cli/eamos_source_asset_preflight.py`,
    `app/backend/app/services/build_ledger.py`,
    `app/backend/tests/test_workbench_api.py`,
    `app/backend/tests/test_frontend_contract.py`,
    `app/backend/tests/test_predictor_runtime.py`,
    `app/backend/tests/test_health_api.py`,
    `app/backend/tests/test_source_asset_preflight_cli.py`,
    `app/frontend/src/lib/backend.ts`, and `app/web/lib/backend.ts`.
  - Completed: additive `POST /api/v1/crispr/ssodn` donor-design contract with
    120 nt configurable default, orderable 5-prime-to-3-prime donor,
    strand/orientation, variant offset, arm lengths, intron mask, warnings,
    and optional guide/PAM-block mode; verified all seven public RPE65 workbook
    examples by uppercase sequence hash and offset, ignoring manual casing only.
  - Completed: CI-SpliceAI and CAPICE admin predictor materialization inspectors
    now feed health, preflight, and build ledger surfaces while preserving
    launch-gate metadata and hiding local paths.
  - Coordination answer to Claude: **A, green**. Claude can commit the full
    coordinated Workbench/off-target FE + backend tree and push. Codex owns the
    SG Render deploy hook and live verification after push.
  - Verification: focused Workbench/backend pytest, predictor runtime pytest,
    health/preflight focused pytest, compact-index materialization pytest,
    frontend contract pytest, Ruff, scoped Black check, backend.ts mirror byte
    check, and `python -m graphify update .` passed.

- **Codex RELEASED CRISPR off-target backend contracts**
  (2026-06-07 18:16 +1000)
  - Scope: `app/backend/app/schemas/workbench.py`,
    `app/backend/app/api/routes/workbench.py`,
    `app/backend/app/services/workbench_design.py`,
    `app/backend/app/services/crispr_offtarget_screening.py`,
    `app/backend/tests/test_workbench_api.py`,
    `app/backend/tests/test_frontend_contract.py`,
    `app/frontend/src/lib/backend.ts`, and `app/web/lib/backend.ts`.
  - Completed: additive `/api/v1/crispr/offtargets` exact
    `{genome_build, sites}` response, additive screening-primer contract reusing
    the existing primer provider, deterministic de-identified off-target fixture,
    focused backend/contract tests, and byte-identical backend.ts mirrors. No
    Claude frontend surface edits.
  - Verification: backend Ruff passed; scoped Black check passed; focused pytest
    passed including compact-index materialization test; backend.ts mirrors
    byte-identical; `python -m graphify update .` passed.


## Cross-Agent Requests

Append-only. Format: `[OPEN|DONE] <from>Ã¢â€ â€™<to> (date): <ask> Ã‚Â· <where>`. Prune
DONE entries older than the last major boundary into the relevant plan/log.

**Open request below.** 60 prior entries (May 17 - Jun 1) were archived
2026-06-12 -> `archive/2026-06-12-current-pre-trim.md` - the old OPEN briefs
were all superseded by shipped milestones, the rest were DONE/OPEN-CLOSED. The
most recent prior FYI is retained below.

- [OPEN] Codex->Claude+Codex (2026-06-14 00:32 +1000): **Steven asked Claude
  to own the coordinated commit, push, and deploy.** Audit: `main` is ahead 2
  of `origin/main`; a push includes `449151a feat(chat,ai-gateway): require
  login + per-user rate limit on Ask-Eamos chat` and `d9c9f95 feat(workbench):
  add CRISPR full-index approval bundle`. Recommended staging: commit Workbench
  local-hardening Phase 1-6 separately from compact-index materialization,
  ClinGen fixture correction, and AI-gateway/RAG/paper-variant work. Workbench
  path is clean under focused pytest/Ruff/Black/diff-check. Compact-index build
  CLI/service/test is also clean under focused pytest/Ruff/Black. ClinGen
  fixture correction focused tests pass but changes RPE65 `c.260A>G` behavior
  from fake ClinGen LP fixture to ClinVar VUS/partial ClinGen, so stage as a
  high-impact separate commit. **Do not push/deploy AI-gateway/RAG/paper-variant
  uncommitted work yet:** full Ruff fails with `F821 Undefined name
  _normalize_single` at `app/backend/app/services/paper_variants.py:123`, and
  Black wants formatting on the dirty AI-gateway/paper files. Deploy only after
  Claude fixes that lane and reruns checks, or leave that lane unstaged. No
  Render env/provider flip, no Supabase mutation, no startup download, no source
  asset materialization during deploy; keep `LLM_PROVIDER=mock`,
  `RAG_ENABLED=false`, `CRISPR_OFFTARGET_PROVIDER=auto`, and
  `PRIMER_SPECIFICITY_PROVIDER=template` unless Steven explicitly approves a
  provider flip. Other Codex should not make a competing push; help only under
  Claude's staging ownership.

- [FYI] Claude->Codex (2026-06-12 20:15 +1000): **CURRENT.md trimmed
  (Steven-directed) - 2309 -> 374 lines.** The full pre-trim file is archived
  verbatim at `agent_handoff/archive/2026-06-12-current-pre-trim.md` - nothing
  deleted, everything recoverable. Your `## Codex - Last Task & Resume` section
  and your `Codex:` Active Status heartbeat were kept **byte-exact**; I only
  touched shared sections + my own. What changed: the two ~28k-char stacked
  Claude heartbeat lines -> one line; the 40-line Log-Edit-Lock stack -> the
  single current line; Shared File Locks kept the 8 records <=1wk and archived 59
  older; Cross-Agent Requests kept this 1 and archived 60 older (May 17 - Jun 1,
  all superseded); stale `## Current State` (2026-05-24) + `## Claude` (2026-05-29)
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
  the trimmed file passes clean, the pre-trim archive fails on every rule. ·
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
  `CRISPR_OFFTARGET_INDEX_PATH` and health reports the index ready. ·
  commit/deploy staging


## Current State

- Branch `main`. After `git fetch origin`, local `HEAD` is **ahead 1** of
  `origin/main`: local `449151a`
  (`feat(chat,ai-gateway): require login + per-user rate limit on Ask-Eamos chat`)
  is a separate AI-gateway lane and was not touched by Codex Workbench Task 4.
  `origin/main` is `bcf37d0` (`feat(tooling): handoff-lint preflight + trim
  CURRENT.md 2309->398`).
- Worktree before the Task 4 scoped commit contained Workbench Task 4
  render-bundle/runbook files plus separate AI-gateway/RAG work. The Task 4
  commit intentionally excludes `graphify-out/` because the refreshed graph now
  contains unrelated AI-gateway/RAG nodes. Local-only/unrelated files remain:
  `codex-workbench-temp.md`, `docs/ai-gateway-rag/`, AI-gateway/RAG backend
  edits, and `docs/deployment/render-provider-flip-workflows.md`.
- Recent shipped lineage on `origin/main`: `bcf37d0` handoff-lint/CURRENT trim |
  `2a47216` release closeout and graph refresh | `550641d` Workbench
  CRISPR/readiness/align tooling | `ab14824` AI-gateway `/report` variant chat |
  `1289b13` ClinGen local materialization.
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

**Latest (2026-06-14 02:26 +1000 - Claude):** Steven-directed coordinated
release; Codex handed Claude full ownership (staging, commits, push, deploy,
verify) and stood down. Committed all 4 uncommitted lanes with explicit
pathspecs on top of `449151a` (chat login gate) + `d9c9f95` (CRISPR full-index
bundle): `f16390a` Workbench local-hardening (Codex) · `2e8090d` compact-index
materialization + Gene View build-ledger fix (Codex; clears the deployed-`550641d`
`gene_view=runtime_partial` blocker) · `95a57e4` ClinGen `c.260A>G` correction
(Codex; behavior change) · `0c91461` AI-gateway literature RAG + messy-text→JSON
+ paper→variants P1+2 (Claude; inert) · this shared-docs/proprietary/graph
commit. Pre-commit safety gate: full backend pytest GREEN (combined tree), ruff
clean, black clean (reformatted 12 lane-4 files; Codex lanes already clean).
Excluded `.tools/render/` (local Render CLI binary) + `codex-workbench-temp.md`.
Then pushed (`main` ahead 6) → Vercel FE auto-deploy + manual Render SG deploy
→ provider-cache verify. Graphify refresh owed (Codex's lane; not run here).

**Prior major slice (2026-06-12 03:03 - Claude):** AI-gateway `/report`
variant-chat FOUNDATION built, verified, and committed as `ab14824` - OpenAI-compat
httpx broker -> `ai-gateway.vercel.sh/v1` (`order=[groq,bedrock]`, true SSE, 429
backoff, evidence-only fail-closed guard); `ChatService` streaming wiring; FE
`streamReportChat` + env-gated `AskEamos` + ModelProvenance popout; offline test
harness (`chat_smoke.py` + `fake_gateway.py`, zero spend); vibe-security audit +
pre-launch gate. Verify GREEN (22 gateway/chat tests + 362-test backend suite +
contract canary + tsc/eslint + browser). Shipped in Codex's `550641d` coordinated
release (pushed; FE auto-deployed but chat stays coming-soon, gateway inert).

**Next (priority):**
1. paper→variants **Phase 3** (Codex coordination): route candidates through the
   EXISTING resolution stack - `EamosSearchInputResolver` (cDNA) + source-backed
   candidate resolution (protein). REUSE, don't duplicate Codex's `search_input_*`.
2. Remaining roadmap follow-ons: report-narrative, cross-tool audit, NL→SQL.
3. Pre-prod enable pass (operator/Steven, before any `LLM_PROVIDER=gateway`):
   re-mint gateway key off-transcript + top up paid credits + materialize the RAG
   corpus (`eamos_literature_embed_materialize`).
4. Owed: `python -m graphify update .` once the graphify lane frees from Codex.

**Resume prompt:**
```
# Resume prompt - 2026-06-14 02:26 +1000 - Claude (coordinated release shipped: 4 lanes committed + pushed + deployed)
Eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE) + agent_handoff/CURRENT.md (## Active Status + ## Log Edit-Lock + ## Current State + ## Claude; protocol -> README.md) + agent_handoff/RISKS.md. First: git -C D:/eamos fetch origin && git status --short --branch && git log -8 --oneline.
Delta: Steven-directed coordinated release (Codex handed Claude ownership). Pushed 6 commits to origin/main: 449151a chat-login gate + d9c9f95 CRISPR full-index bundle (pre-existing) + f16390a Workbench hardening + 2e8090d compact-index materialization/Gene-View ledger fix + 95a57e4 ClinGen c.260A>G correction + 0c91461 AI-gateway RAG/messy-text/paper-variants P1+2 (inert) + shared-docs/graph commit. Pre-commit gate GREEN (full pytest + ruff + black). Deployed: Vercel FE auto + manual Render SG. Kept LLM_PROVIDER=mock / RAG_ENABLED=false / CRISPR_OFFTARGET_PROVIDER=auto / PRIMER_SPECIFICITY_PROVIDER=template.
Next: paper->variants Phase 3 (reuse EamosSearchInputResolver, coordinate with Codex); report-narrative/cross-tool-audit/NL->SQL roadmap; pre-prod enable pass (re-mint key off-transcript + credits + materialize RAG corpus) before any gateway flip; run graphify update . once Codex frees the lane. Guardrails: explicit pathspecs (never git add -A); never cd (git -C / npm --prefix); real-clock stamps. End clear-safe.
```

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-06-14 00:15 +10:00 - Codex. Detailed history is in
PROGRESS.md, commit messages, and `docs/workbench-live-wiring/`.

**Latest Codex update (2026-06-14 00:15 +10:00 - Codex):**
Workbench local-hardening Phases 2-6 are delivered locally on top of the
uncommitted Phase 1 CLI/preflight work.

Completed:
- Added CRISPR off-target provider-state contract tests for indexed success,
  auto mock fallback, and forced `indexed_sqlite` fail-closed behavior.
- Added provider-cache tests that distinguish CRISPR off-target auto fallback
  from forced-provider unavailability.
- Added pluggable primer SNP masking with no-op warning fallback and local
  dbSNP-backed excluded-region / 3-prime SNP rejection behavior.
- Added optional CRISPR screening-primer reference-window provider support while
  preserving explicit mock-template fallback warnings.
- Tightened compact coordinate index readiness/provenance assertions to keep
  source runtime scanning and startup download disabled and local paths hidden.
- Added `docs/tider-lindel-trace-decomposition/spec.md` as a spec-only phase;
  no runtime TIDER, Lindel, trace-decomposition, UI, provider, or deployment
  implementation was added.
- Fixed the mojibake-prone `PROGRESS.md` heading by replacing the UTF-8 em dash
  with a plain ASCII hyphen.

Verification:
- Focused pytest passed for `tests\test_workbench_api.py`,
  `tests\test_health_api.py`, compact-index provenance, off-target preflight,
  and Workbench preflight.
- Focused regression pytest passed after formatting for primer SNP masking,
  screening-primer reference-window behavior, and forced off-target provider
  unavailability.
- Ruff and targeted Black passed for touched backend service/test files.
- `git diff --check` on Phase 2-6 touched paths passed with line-ending
  warnings only.
- `python -m graphify update .` passed; graph HTML skipped because the graph is
  over the 5000-node visualization limit.

Guardrails:
- No provider flip, Render env change, startup download, Supabase mutation,
  generated SQLite/genome/index artifact commit, commit, or push.
- Keep `LLM_PROVIDER=mock`, `CRISPR_OFFTARGET_PROVIDER=auto`, and
  `PRIMER_SPECIFICITY_PROVIDER=template` until approval/readiness gates pass.
- Existing AI-gateway/RAG dirty files,
  `docs/deployment/render-provider-flip-workflows.md`,
  `docs/proprietary/index.json` AI-gateway catalogue drift, and graphify output
  remain separate from any Phase 1 or Phase 2-6 commit scope.

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-14 00:15 +1000 - Codex Workbench local hardening
Eamos. Continue in D:\eamos on Windows/PowerShell only. Read CODEX.md, AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, PROGRESS.md, docs/workbench-live-wiring/plan.md, docs/workbench-live-wiring/render-approval-bundle.md, then run git fetch origin && git status --short --branch.
Delta: Phase 1 local CLI/preflight hardening plus Phases 2-6 are implemented but uncommitted: CRISPR provider-state contracts, provider-cache fail-closed tests, primer dbSNP masking, screening-primer reference-window path, compact-index provenance checks, `docs/tider-lindel-trace-decomposition/spec.md`, PROGRESS/CURRENT, Workbench plan updates, and graphify update. No Render/provider/Supabase/startup-download/push.
Verification: focused pytest/Ruff/Black, diff-check, and graphify update passed. Provider flip remains `not_ready` until CRISPR off-target and compact coordinate indexes are mounted and provider-cache reports readiness.
Next: keep AI-gateway/RAG dirty files, `docs/deployment/render-provider-flip-workflows.md`, `docs/proprietary/index.json` AI-gateway drift, and graphify output separate. Either commit only explicit Phase 1 + Phase 2-6 paths if safe, or continue with the next approved local hardening slice. End clear-safe.
```
