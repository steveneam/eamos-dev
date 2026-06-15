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

- **Claude:** IDLE @ 2026-06-15 21:52 +1000 - **Vercel recovery.** `eamos-dev` had not auto-deployed Codex's `1e86a78` (`fix(protein)`): the GitHub->Vercel webhook for that one push dropped (auto-deploy itself healthy - every commit through parent `1c2df8b` deployed). Render SG was already on `1e86a78`; only the Vercel FE lagged at `1c2df8b` (missing `ReportGeneViewer.tsx` +359). Re-triggered via this combined handoff commit (+ `app/web/.gitignore` now ignores `.vercel`); removed the stray local `app/web/.vercel` link that had sent Codex's manual `vercel --prod` to the wrong `web` project (`web-beryl-delta-96`, never the real domain). Remote `web` project left intact per Steven. Held files still excluded; `LLM_PROVIDER=mock` held; no Supabase/provider/env flip.

- **Codex:** IDLE @ 2026-06-15 21:15 +1000 - **Protein architecture consistency fix is local and verified, not committed/deployed.** USH2A now uses local UniProtKB/Swiss-Prot feature-table records before Pfam/HMMER so signal peptide, TM, PDZ-binding motif, topology/motif/site categories, and source-backed partial tracks are not hidden when HMMER is unavailable. UI has category filters, sites hidden by default, persistent aa scale, pattern legend, no-resize/no-twitch toggle behavior, and browser proof screenshots under `.tmp/`. Guardrails held: no Supabase mutation, provider/env flip, Render/Vercel deploy, or bundle of held AI-gateway doc / encoding-scan helper.

## Log Edit-Lock

UNLOCKED - 2026-06-15 21:52 +1000 - Claude (Vercel recovery: re-triggered eamos-dev deploy of 1e86a78 via this combined handoff commit; removed stray local app/web/.vercel)

Single mutex for shared log/handoff docs (README Hard Rule 8). Set
`LOCKED: <agent> - <stamp> - <file/section>` before editing any of them;
`UNLOCKED - <stamp> - <agent> (<note>)` after you finish and re-read. Other
agent holds fresh (<= 20 min) -> stop + ask the user; stale (> 20 min) -> record
takeover, proceed.

## Shared File Locks

Claim before editing a shared/high-conflict source/contract file (README Hard
Rule 4); release when done.

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

Append-only. Format: `[OPEN|DONE] <from>-><to> (date): <ask> - <where>`. Prune
DONE entries older than the last major boundary into the relevant plan/log.

Current live entries only. Older request history through the graphify closeout is
archived verbatim at
`agent_handoff/archive/2026-06-15-current-pre-graphify-closeout-trim.md`.

- [OPEN] Steven->Claude+Codex (2026-06-15 04:18 +1000): **Next-session cleanup
  tags, do not bundle blindly.** Review `docs/proprietary/eamos-ai-gateway.md`
  separately for the paper->variants validation wording change, and review
  `scripts/eamos-encoding-scan.mjs` separately as a possible read-only tooling
  commit. Keep `.tools/` local-only; it contains screenshots/proof artifacts and
  a Render CLI binary under `.tools/render/`, not source. - held local cleanup

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

**Latest (2026-06-15 21:52 +1000 - Claude - Vercel deploy recovery):** Codex pushed
`1e86a78` (`fix(protein): hydrate curated feature architecture` - `ReportGeneViewer.tsx`
+359 + backend protein_annotation/health/config/CLI/tests + graphify) and deployed it to
Render SG, but Vercel `eamos-dev` never auto-deployed it. Diagnosed via the Vercel MCP:
auto-deploy is healthy (every commit through the parent `1c2df8b` deployed as a
`githubDeployment` build) - the GitHub->Vercel webhook for the single `1e86a78` push was
dropped (no build created at all). The mistaken `web`-project deploy Codex did from
`app/web` never touched the real domain (it sits on `web-beryl-delta-96.vercel.app`).
- **Fix (Steven-approved):** re-triggered the GitHub auto-deploy with this combined handoff
  commit (handoff state + `app/web/.gitignore` now ignoring `.vercel`); removed the stray
  local `app/web/.vercel` link so a future `vercel deploy` from `app/web` can't target `web`.
- **Excluded** (held, per Steven): `docs/proprietary/eamos-ai-gateway.md`,
  `scripts/eamos-encoding-scan.mjs`, untracked `graphify-out/2026-06-15/`. No `git add -A`.
- **Did NOT touch:** the remote `web` Vercel project/deployment (Steven's call), Render env
  (`uniprot_features_enabled=false` held), Supabase, `LLM_PROVIDER=mock`.

**Next (priority):**
1. Verify the new Vercel deploy goes READY and serves `1e86a78`'s `ReportGeneViewer.tsx`
   curated protein feature architecture on `https://eamos-dev.vercel.app`.
2. Original work resumes: **genomic view Section 4 not started** (pairs with Codex's
   gene-view figure-style refresh follow-up tracked in its own section).
3. Optional, on Steven's go: clean up / delete the remote `web` Vercel project + its stray
   `web-beryl-delta-96` deployment.
4. graphify semantic pass still owed at a deliberate checkpoint (Codex lane; AST `update`
   is current).

**Resume prompt:**
```
# Resume prompt - 2026-06-15 21:52 +1000 - Claude (Vercel deploy recovery; 1e86a78 re-triggered)
Eamos. Open from D:\eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE) + agent_handoff/CURRENT.md (## Active Status + ## Log Edit-Lock + ## Current State + ## Claude; protocol -> README.md) + agent_handoff/RISKS.md. First: git -C D:/eamos fetch origin && git status --short --branch && git log -5 --oneline.
Delta: Codex's 1e86a78 (fix(protein): ReportGeneViewer.tsx +359 + backend) deployed to Render SG but Vercel eamos-dev never auto-deployed it (dropped GitHub webhook; auto-deploy otherwise healthy). Re-triggered via a combined handoff commit (+ app/web/.gitignore ignores .vercel) and removed the stray local app/web/.vercel link that had sent Codex's manual vercel --prod to the wrong `web` project (web-beryl-delta-96; never the real domain). Held files excluded; remote `web` project left intact per Steven; Render env / LLM_PROVIDER=mock untouched.
Next: (1) confirm the new Vercel deploy is READY + serves 1e86a78's protein feature architecture on eamos-dev.vercel.app; (2) resume original work = genomic view Section 4 (not started); (3) optional on Steven's go: delete the remote `web` Vercel project + web-beryl-delta-96 deploy; (4) graphify semantic pass owed (Codex lane). Guardrails: reuse-first, mock-first, never cd (git -C / npm --prefix), LLM stays mock, no Supabase apply / provider/env flip without Steven, new routes/nav need Steven OK, never git add -A (held files). End clear-safe.
```

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-06-15 15:56 +10:00 - Codex. Prior AlphaMissense/protein viewer release details are retained in Cross-Agent Requests above and were shipped by Claude at `8a7095f`.

**Latest Codex update (2026-06-15 15:56 +10:00 - Codex):**
Report protein architecture refresh is complete, committed, pushed, deployed to Vercel production, and live-verified on `https://eamos-dev.vercel.app`.

Completed:
- Recovered the prior protein-view intent from `plans/gene-viewer/*`, `plans/predictor-visuals-contracts/spec.md`, protein annotation tests, and `agent_handoff/on_hold/register.md`: active scope is the 1-D protein architecture/domain track; the on-hold item is only the future 3-D AlphaFold/Molstar lane.
- Diagnosed the report mismatch: `ReportGeneViewer` was rendering the compact/window `/api/v1/viewer` protein track, flattening lanes/descriptions/sites, and showing only a small chip subset. The full lookup/report payload already carries the richer `protein_domain_track`.
- Diagnosed the lookup failure in the screenshot: the Next rewrite/proxy was socket-hanging on the large/slow USH2A lookup, while direct SG returned 200. Added a narrow same-origin `POST /api/v1/lookup` route so the report loads through local/prod web without the proxy 500.
- Shipped `ReportClient`/`ReportGeneViewer` wiring so the report passes and consumes the full payload `protein_domain_track` first, with standardized scrollable gene/protein canvas widths and source-backed protein length/features.
- Reworked the protein diagram from multi-lane collision rows into a single figure-style architecture schematic: one 34px white protein backbone, black outer outline, thinner black domain outlines, rectangular colored domain blocks, horizontal scroll for long proteins, and source-hit summarization outside the primary figure.
- Added canonical domain-family grouping and filtering: repeated classes keep consistent gene-agnostic colors; canonical architecture blocks are preferred; overlapping/alternate/weak HMMER/Pfam hits (for example Purple acid/Chitinase-style surprises) are summarized rather than shown as primary protein architecture when canonical USH2A domains exist.
- Added multi-select domain-family cards. Clicking a description card toggles yellow highlights on all matching domains in the schematic; selected repeated families show exact amino-acid ranges as visible pills, so users do not need to hover to recover per-domain coordinates.
- Ran the required cheap graph maintenance pass: `python -m graphify update .` (AST-only; no semantic extraction). `graphify-out/graph.html` was restored/left tracked because graphify skipped HTML regeneration due the >5k node threshold.
- Pushed commits: `960ac9d fix(report): render full protein domain architecture`, `1f1b011 chore(graphify): update after protein view fix`, `49e8326 fix(report): simplify protein architecture schematic`, and `22e840a chore(graphify): update after protein schematic cleanup`.
- Deployed by Vercel production auto-build: deployment `dpl_8QfBR96Y3K83f3MjGUqz8fLVKUTt`, URL `https://eamos-px73bt9ue-steven-eamegdool-s-projects.vercel.app`, aliases include `https://eamos-dev.vercel.app`.

Verification recorded 2026-06-15 15:56 +10:00:
- `./node_modules/.bin/tsc.cmd --noEmit` in `app/web` passed.
- `npm --prefix app/web run lint` passed with only pre-existing unrelated React effect warnings in `CompareClient.tsx` and `PubMedSection.tsx`.
- `git diff --check` passed apart from existing LF/CRLF warnings.
- Local browser verification on USH2A confirmed one protein architecture row, `5,202 aa`, `50 architecture blocks`, `248 source hits`, no primary Purple-acid/Chitinase cards, FN3 card range pills, and yellow multi-select highlighting.
- Live Vercel verification on `https://eamos-dev.vercel.app/report?gene=USH2A&cdna=c.2276G%3ET` confirmed `POST /api/v1/lookup` 200, `POST /api/v1/viewer` 200, lookup sections 200, `5,202 aa`, `50 architecture blocks`, `248 source hits`, FN3 selected card shows all exact ranges, and production console only has pre-existing form/id + CSS preload warnings.
- No Supabase mutation, provider/env flip, Render deploy, or backend env change was performed.

Held local follow-ups for next session:
- Apply the same concept to the **gene view**: standardize figure-style size, preserve horizontal scroll for long genes, make the gene/locus track less squashed, use clear outer/inner outlines, and expose exact coordinates without hover-only dependence. Start from `ReportGeneViewer.tsx` and the reference protein screenshots from `C:\Users\seamegdool\Pictures\Screenshots\Screenshot 2026-06-15 023012.png` and `...023026.png`.
- `docs/proprietary/eamos-ai-gateway.md`: review separately for the paper->variants validation wording change; safe-looking doc diff but not graphify/Render scope.
- `scripts/eamos-encoding-scan.mjs`: review separately as a possible read-only mojibake scanner tooling commit; safe-looking but currently untracked and not wired into scripts/tests.
- `.tools/`: keep ignored/local-only. It includes screenshots and `.tools/render/cli_v2.20.0.exe`; do not commit.
- `docs/proprietary/eamos-ai-gateway.md` and `scripts/eamos-encoding-scan.mjs` should not be bundled into graphify, Render, or handoff commits.

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-15 15:56 +1000 - Codex protein architecture deployed; gene view next
Eamos. Open `D:\eamos`. Read CODEX.md, AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, then run git fetch origin && git status --short --branch && git log -6 --oneline.
Delta: Protein architecture refresh is shipped and deployed. Pushed commits: `960ac9d` full report protein-domain wiring + same-origin lookup route, `1f1b011` graph update, `49e8326` single-row figure-style protein schematic, `22e840a` graph update. Vercel production deploy `dpl_8QfBR96Y3K83f3MjGUqz8fLVKUTt` is Ready and aliased to `https://eamos-dev.vercel.app`. Live USH2A report verified: 5,202 aa, 50 architecture blocks, 248 source hits, one protein row, black outer backbone outline, thinner domain outlines, canonical domain cards, FN3 selected card exposes all exact amino-acid ranges and highlights domains yellow. Purple-acid/Chitinase-style raw HMMER surprises are summarized, not primary architecture. Tests: app/web tsc, app/web lint (only pre-existing warnings), `git diff --check`, local + live browser verification. `python -m graphify update .` was run; no semantic extraction.
Next: apply the same figure-style/scroller concept to the gene view in `ReportGeneViewer.tsx`: standardized height/size, horizontal scroll for long genes, clearer outer/inner outlines, less squashing, and visible coordinates instead of hover-only dependence. Use the reference protein screenshots from `C:\Users\seamegdool\Pictures\Screenshots\Screenshot 2026-06-15 023012.png` and `...023026.png`. Do not bundle held local items: `docs/proprietary/eamos-ai-gateway.md` and `scripts/eamos-encoding-scan.mjs`. Guardrails: no Supabase apply/mutation, no provider/env flips, keep `LLM_PROVIDER=mock`, `RAG_ENABLED=false`, `CRISPR_OFFTARGET_PROVIDER=auto`, `PRIMER_SPECIFICITY_PROVIDER=template`. End clear-safe.
```
