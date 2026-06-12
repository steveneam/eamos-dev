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

- **Claude:** ACTIVE @ 2026-06-12 20:15 +1000 - **CURRENT.md trim/maintenance (user-directed).** Archived the full 2309-line pre-trim file verbatim -> `archive/2026-06-12-current-pre-trim.md`, then collapsed the bloat: the two ~28k-char stacked Claude heartbeat lines -> this single line; the 40-line Log-Edit-Lock stack -> one current line; 59 of 67 Shared File Locks (all released, dated <=2026-06-01) and 60 of 61 Cross-Agent Requests (May 17 - Jun 1; OPEN briefs all superseded by shipped milestones) -> archive; refreshed the stale `## Current State` (was 2026-05-24) and `## Claude - Last Task` (was 2026-05-29) to current. **No code/state change** - HEAD is the `ab14824` AI-gateway era; `main` ahead 1 of `origin/main` (Codex closeout `2a47216` unpushed - Codex Workbench owns push+deploy); `LLM_PROVIDER=mock`; dev `:3000` running (pre-existing). Next: AI-gateway pre-launch security gate before any prod-enable.

- **Codex:** IDLE @ 2026-06-12 03:26 +10:00 - **Coordinated release pushed/deployed; follow-up docs/graph closeout ready to commit.** Pushed `1289b13` ClinGen local materialization, `ab14824` Claude AI gateway, and `550641d` Workbench CRISPR/readiness/align tooling to `origin/main`; local `HEAD` and `origin/main` both resolve to `550641d5821bb0b1d9e7bc082e2055ecd1dc0b1a`. Vercel production `dpl_EPhYH5hu9HM5TBL6LtNqH16nEHtB` / `https://eamos-7b0jk46c4-steven-eamegdool-s-projects.vercel.app` is Ready and build logs show GitHub commit `550641d`. Render SG deploy `dep-d8lerncm0tmc73cb1sfg` is live on `550641d`. Live smoke passed: SG `/healthz` 200 with `llm_provider=mock`; SG+Vercel provider-cache kept CRISPR off-target `auto`/`mock_fallback`, `indexed_sqlite.ready=false`, primer specificity `template_window`; SG+Vercel `/api/v1/align/reference` for `RPE65:c.260A>G` returned `source=resolver`; SG+Vercel `/api/v1/crispr/tide` accepted the RPE65 AB1 fixture and returned source-backed observed-only TIDE. The follow-up commit includes the Claude AI gateway risk note, graphify output refresh, and this CURRENT closeout. Remaining local-only files after that commit: `.claude/settings.json` and `codex-workbench-temp.md`.

## Log Edit-Lock

UNLOCKED - 2026-06-12 20:15 +1000 - Claude (CURRENT.md user-directed trim: pre-trim snapshot archived verbatim; Active Status / Log-Edit-Lock / Shared File Locks / Cross-Agent Requests entries >1wk collapsed into archive; stale Current State + Claude Last Task refreshed; Codex section kept byte-exact; atomic single-write, lock was free - Codex idle since 03:26)

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

**No open cross-agent requests.** 60 prior entries (May 17 - Jun 1) were archived 2026-06-12 -> `archive/2026-06-12-current-pre-trim.md` - the OPEN briefs were all superseded by shipped milestones, the rest were DONE/OPEN-CLOSED. The most recent (combined-commit coordination, now DONE) is retained below.

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

- Branch `main`. Local **ahead 1** of `origin/main` - the one unpushed commit is
  Codex's `2a47216` (`docs(handoff): commit release closeout and graph refresh`).
  **Codex Workbench owns the push + Render/Vercel deploy** (Steven-directed); do
  not push unless Steven redirects. `origin/main` HEAD is `550641d`.
- Worktree (intentional local-only, do NOT stage): `M .claude/settings.json`,
  `?? codex-workbench-temp.md`.
- Recent shipped lineage on `origin/main`: `550641d` Workbench CRISPR/readiness/
  align tooling (Codex) | `ab14824` AI-gateway `/report` variant chat (Claude) |
  `1289b13` ClinGen local materialization (Codex).
- **AI-gateway is inert in prod:** `LLM_PROVIDER=mock` (Render auto-deploy OFF),
  FE chat gated coming-soon (`NEXT_PUBLIC_AI_CHAT_ENABLED` unset). Do NOT flip to
  `gateway` until the pre-launch security gate is resolved
  (`docs/ai-gateway/pre-launch-security.md`; RISKS.md top entry).
- `CRISPR_OFFTARGET_PROVIDER=auto` / `mock_fallback`; provider-cache
  `indexed_sqlite.ready=false` (no real index on Render yet).
- Verification last green (Codex, 2026-06-12 pre-push): focused Workbench / CRISPR /
  TIDE / frontend-contract / gateway pytest + backend Ruff / targeted Black +
  app/web & app/frontend tsc; live SG+Vercel health / provider-cache /
  align-reference / TIDE smokes (`/healthz` 200, `llm_provider=mock`).
- Gated (no auto-start): prod gateway enable, restricted predictor unlocks,
  Supabase / object-storage / startup downloads, destructive git. See `RISKS.md`.

## Claude - Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 1/2).
Full incremental detail in `~/.claude/plans/next-session-eamos.md` (START HERE).
Prior narratives (through the 2026-05-29 LazySection section and every intervening
session) are archived verbatim under `agent_handoff/archive/` and in the
`2026-06-12-current-pre-trim.md` snapshot.

**Latest (2026-06-12 20:15 +1000 - Claude):** user-directed `CURRENT.md`
trim/maintenance (this session) - full pre-trim file archived, bloat collapsed,
stale state sections refreshed. No code change.

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
1. Confirm Codex push+deploy of `2a47216`; live-verify only if Steven decides to
   prod-enable the gateway (gated on the pre-launch security gate).
2. **AI-gateway pre-launch security gate** (`docs/ai-gateway/pre-launch-security.md`):
   auth and/or per-user/tier token cap on the unauthenticated paid
   `/api/v1/chat/stream` before flipping `LLM_PROVIDER=gateway`; re-mint key; top up
   paid credits. Steven/product decisions - don't unilaterally add auth.
3. Follow-on roadmap (plan section 1): pgvector literature RAG -> 5 dossier
   features -> `/runs` patient-chat migration -> support bot.

**Resume prompt:**
```
# Resume prompt - 2026-06-12 20:15 +1000 - Claude (CURRENT.md trimmed; AI-gateway foundation shipped in 550641d)
Eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE) + agent_handoff/CURRENT.md (## Active Status + ## Log Edit-Lock + ## Current State + ## Claude; protocol -> README.md) + agent_handoff/RISKS.md (AI Gateway Pre-Launch Security Gate at top). First: git -C D:/eamos fetch origin && git status --short --branch && git log -8 --oneline.
Delta: CURRENT.md trimmed (full pre-trim archived -> archive/2026-06-12-current-pre-trim.md; 2309 lines -> trimmed). Code unchanged: origin/main HEAD 550641d (550641d Workbench + ab14824 AI-gateway + 1289b13 ClinGen); main ahead 1 (Codex 2a47216 closeout unpushed - Codex owns push+deploy). LLM_PROVIDER=mock; FE chat coming-soon.
Next: AI-gateway pre-launch security gate (docs/ai-gateway/pre-launch-security.md) before any prod gateway-enable; then pgvector RAG roadmap. Guardrails: FE-only; explicit pathspecs (never git add -A); never cd (git -C / npm --prefix); real-clock stamps; keep LLM_PROVIDER=mock. End clear-safe.
```

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-06-12 03:26 +10:00 - Codex. Detailed history is in
PROGRESS.md, commit messages, and `docs/workbench-live-wiring/`.

**Latest Codex update (2026-06-12 03:26 +10:00 - Codex):**
Coordinated release is committed, pushed, deployed, live-smoked, and the
follow-up handoff/risk/graphify closeout is ready to commit.

Completed:
- Committed Codex Workbench readiness as `550641d`
  (`feat(workbench): add CRISPR readiness and align reference tooling`).
- Pushed the coordinated local stack to `origin/main`: `1289b13` ClinGen local
  materialization, `ab14824` Claude AI gateway, and `550641d` Workbench
  CRISPR/readiness/align tooling.
- Vercel production deployment
  `https://eamos-7b0jk46c4-steven-eamegdool-s-projects.vercel.app` is Ready;
  build logs show GitHub commit `550641d`.
- Render SG deploy `dep-d8lerncm0tmc73cb1sfg` is live on commit `550641d`.
- Follow-up closeout includes `agent_handoff/RISKS.md`, this `CURRENT.md`
  closeout, and refreshed `graphify-out/` files.

Verification:
- Pre-push focused pytest for Workbench/CRISPR/TIDE/frontend-contract/gateway
  passed.
- Backend Ruff, targeted Black, `app/web` TypeScript, and `app/frontend`
  TypeScript passed.
- Vercel logs: build cloned GitHub commit `550641d`, compiled successfully, ran
  TypeScript, and deployed Ready.
- Render API: deploy `dep-d8lerncm0tmc73cb1sfg` status `live`, commit
  `550641d5821bb0b1d9e7bc082e2055ecd1dc0b1a`.
- Live SG `/healthz` returned 200 with `llm_provider=mock`.
- Live SG+Vercel provider-cache kept CRISPR off-target `auto` /
  `mock_fallback`, `indexed_sqlite.ready=false`, and primer specificity
  `template_window`.
- Live SG+Vercel `/api/v1/align/reference` for `RPE65:c.260A>G` returned
  `source=resolver`.
- Live SG+Vercel `/api/v1/crispr/tide` accepted the RPE65 AB1 fixture pair and
  returned source-backed observed-only TIDE.

Guardrails:
- No Render provider/env flip was performed.
- `LLM_PROVIDER` remains `mock` in live `/healthz`; do not switch to gateway
  until the AI gateway pre-launch auth/cost gate is resolved.
- `CRISPR_OFFTARGET_PROVIDER` remains `auto`; provider-cache reports
  `indexed_sqlite.ready=false`.
- `.claude/settings.json` and `codex-workbench-temp.md` remain intentionally
  uncommitted.
- `.claude/settings.json` and `codex-workbench-temp.md` remain the only
  intentional local-only files after the closeout commit.

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-12 03:26 +1000 - Codex coordinated release deployed and closeout committed

Eamos. Continue in D:\eamos on Windows/PowerShell only. Read CODEX.md, AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, PROGRESS.md, docs/workbench-live-wiring/plan.md, then run git status --short --branch.

Delta: Coordinated release pushed to `origin/main` at `550641d`: `1289b13` ClinGen local materialization + `ab14824` Claude AI gateway + `550641d` Workbench CRISPR/readiness/align tooling. Vercel production is Ready and Render SG deploy `dep-d8lerncm0tmc73cb1sfg` is live on `550641d`. Follow-up closeout committed `agent_handoff/RISKS.md`, `agent_handoff/CURRENT.md`, and refreshed `graphify-out/`.

Verification: pre-push focused pytest/Ruff/targeted Black/web+frontend TypeScript passed; live SG+Vercel health/provider-cache/align-reference/TIDE smokes passed. `LLM_PROVIDER=mock`; CRISPR off-target remains `auto`/`mock_fallback`.

Next: continue only after checking whether `.claude/settings.json` and `codex-workbench-temp.md` should remain local; do not commit either unless Steven explicitly asks. Keep `LLM_PROVIDER=mock` and `CRISPR_OFFTARGET_PROVIDER=auto` until their launch gates are resolved. End clear-safe.
```
