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

- **Claude:** IDLE @ 2026-06-15 02:25 +1000 - **Drove the coordinated release: 2 commits SHIPPED + DEPLOYED + verified on prod.** `1b2cf53` feat â€” interactive ACMG explainer (Claude tasks 1-3) + AlphaMissense report FE wiring (Codex's 5 files) [14 files, explicit pathspecs]. `8a7095f` fix(lookup) â€” sequence-context resolver `httpx` timeouts now degrade to a `workbench_sequence_context_resolver_error` warning instead of 500ing `/api/v1/lookup/sections` (the prod 500 Codex traced to `sequence_context.py`; Steven-approved cross-lane fix; +regression test). Gates green: app/web tsc, app/frontend tsc -b, vitest 26/26, focused backend pytest (sequence_context + orchestration/contract/gene-viewer), ruff+black. **Deployed:** Vercel FE auto (live - landingâ†’/account "Submit evidence" verified in prod SSR); Render SG redeployed via hook â†’ `dep-d8nd9agjs32c73djccp0` LIVE at `8a7095f`. **Prod-verified:** `/healthz` 200, `/api/v1/lookup/summary` RPE65 200 @34.7s (the slow VariantValidator path that used to 500 now completes), `/api/v1/viewer` 200 + AlphaMissense, full `/report?gene=RPE65&cdna=c.260A>G` renders (live engine VUS net+2 32.5%, **no** `illustrative` flag; AlphaMissense + Pfam protein domains live), **zero 5xx** in SG request logs post-deploy. `LLM_PROVIDER=mock` held; no Supabase apply / provider/env flip; graphify-out + AI-gateway doc still excluded (Codex lane).

- **Codex:** IDLE @ 2026-06-15 04:25 +1000 - **Graphify semantic pass + maintenance guidance committed and pushed.** `origin/main` is `146ae9c` with graphify refresh `4ff5ac2` plus handoff cleanup `146ae9c`. Full raw `graphify-out/graph.html` renders 10,803 nodes / 29,423 edges / 574 communities; semantic cache exists. Held local cleanup remains: AI-gateway doc wording and encoding-scan helper need separate review; `.tools/` is local-only and ignored. No manual deploy/Supabase/provider mutation.

## Log Edit-Lock

UNLOCKED - 2026-06-15 04:25 +1000 - Codex (graphify closeout pushed + held cleanup tags; own section/heartbeat only, released cleanly)

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

- Branch `main`. `origin/main` == local `HEAD` == **`f772cc6`**
  (`feat(report,paper,library): ACMG points viz wave + paper->variants front door
  + account library sync`) - the 2026-06-14 coordinated release Claude drove.
  Shipped + deployed: **Render eamos-dev-sg redeployed (live)**, **Vercel FE
  auto-deployed**, E2E-verified on prod.
- Worktree after the release still carries deliberately-excluded local files:
  `graphify-out/*` (**Codex lane - `graphify update` owed against `f772cc6`**),
  `docs/proprietary/eamos-ai-gateway.md` (AI-gateway, held out),
  `scripts/eamos-encoding-scan.mjs` (Codex tooling), `.tools/` (Claude scratch
  screenshots), `codex-workbench-temp.md`. No `git add -A` was used.
- `eamos_computed_classification` is now LIVE on prod (Codex engine +
  report-population). Independent Tavtigian advisory audit block, separate from
  `clinical_consensus`. Note: prod RPE65 c.260A>G = VUS net+2 (PP3 moderate only);
  Codex's local fixture gave net+3 (PM2+PP3) - likely a live-gnomAD vs fixture
  PM2 difference for Codex to confirm.
- Recent shipped lineage on `origin/main`: `f772cc6` ACMG-viz+paper+library |
  `3ccef4d` coordinated-release closeout + graph refresh | `0c91461` AI-gateway
  literature RAG + paper->variants P1+2 (inert) | `95a57e4` RPE65 fixture fix.
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

**Latest (2026-06-14 23:14 +1000 - Claude):** Built the **ACMG-viz wave** then
drove the **coordinated commit+push+deploy** (`f772cc6`, LIVE on prod). The viz
wave = `/report` Â§2 capstone that DRAWS the EAMOS-computed Tavtigian-2020 points
decision; the three shipped lanes (ACMG viz + paper->variants + account library
sync) were all bundled into one release.
- **ACMG viz** (Card-2 placement, Steven-chosen): `lib/acmg/{points(+frontend
  mirror+vitest 11/11),mock,fingerprint}` + `components/report/{PosteriorGauge,
  PointWaterfall,EvidencePlane,EvidenceFingerprint,ConfidenceChannel,
  AdvisorySummaryStrip}.tsx` + reworked `EamosAcmgClassifier` (**hideable
  `Disclosure` capstone** in Â§2; legacy Richards demoted to audit) + `ReportClient`
  (glance strip [fingerprint+posterior chip] under the call cards; capstone in Â§2).
  Instruments match the vault `Wiki/assets` mockups: **net-linear gauge** (posterior
  labelled at dividers), **diverging-bar waterfall** + net->tier axis, **padded-puck
  plane** w/ crosshair+callout. Mock is **verdict-matched** (never contradicts the
  curated call). `points.ts` is the pure engine mirror (posterior 2.08^net,
  Tavtigian cuts), vitest-pinned to engine anchors.
- **Shipped:** `f772cc6` (60 files, explicit pathspecs). Codex's backend
  (acmg_points_engine, paper route, library GET/PUT, migration) + Claude's FE in
  one commit. All gates green (Codex's backend pytest groups + contract canary +
  both tsc + vitest + diff-check).
- **Deployed + E2E-verified on prod:** Render eamos-dev-sg redeployed (live, serves
  `eamos_computed_classification`); Vercel FE auto-deployed.
  `/report?gene=RPE65&cdna=c.260A>G` -> live engine block VUS net+2 posterior 32.5%;
  instruments render engine-fed, `.eamos-mock` flag correctly absent. FE mirror ==
  engine (posterior(2)=32.5%).
- **Guardrails held:** `LLM_PROVIDER=mock`; **Supabase migration committed, NOT
  applied** (needs Steven OK); excluded AI-gateway doc / `graphify-out` / scratch.

**Next (priority):**
1. **graphify update** against `f772cc6` (Codex lane) - graph is stale, excluded
   from the release.
2. **Apply the Supabase migration** `20260614195800_user_library_document.sql` when
   Steven approves (committed but not applied; account library sync needs it live).
3. **ACMG viz fast-follow** (`docs/report-acmg-viz/spec.md` Â§1): interactive Explore
   drag-card; B1 predictor forest / B7 beeswarm (needs Codex ClinVar P/B precompute);
   B2 constraint forest. Plus optional: thread real conservation/constraint into the
   fingerprint (currently mock-flagged), merge gauge+waterfall axis if it reads
   redundant (Steven flagged to watch).
4. Confirm with Codex the prod RPE65 net+2 (PP3-only) vs local net+3 (PM2+PP3)
   gnomAD/fixture difference.

**Resume prompt:**
```
# Resume prompt - 2026-06-14 23:14 +1000 - Claude (ACMG viz wave SHIPPED+DEPLOYED f772cc6)
Eamos. Open from D:\eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE) + agent_handoff/CURRENT.md (## Active Status + ## Log Edit-Lock + ## Current State + ## Claude; protocol -> README.md) + agent_handoff/RISKS.md. First: git -C D:/eamos fetch origin && git status --short --branch && git log -5 --oneline.
Delta: ACMG points-viz wave built + the 3 verified lanes (ACMG viz + paper->variants + account library) SHIPPED in one coordinated commit f772cc6, pushed to origin/main, Render eamos-dev-sg redeployed + Vercel FE auto-deployed, E2E-verified on prod (RPE65 c.260A>G -> live engine VUS net+2 posterior 32.5%, no illustrative flag). ACMG viz = Â§2 hideable Disclosure capstone (PosteriorGauge/EvidencePlane/PointWaterfall/EvidenceFingerprint/ConfidenceChannel) drawing the Tavtigian points decision; lib/acmg/points.ts pure mirror (+vitest 11/11, mirrored to app/frontend); matches vault Wiki/assets mockups. LLM_PROVIDER=mock held; Supabase migration committed NOT applied.
Next: (1) graphify update vs f772cc6 (Codex lane); (2) apply Supabase migration when Steven OKs; (3) ACMG viz fast-follow (Explore drag-card, B1 forest/B7 beeswarm, thread real conservation/constraint into fingerprint); (4) confirm w/ Codex the prod RPE65 net+2 vs local net+3 PM2 gnomAD/fixture diff. Guardrails: reuse-first, mock-first, never cd (git -C / npm --prefix), LLM stays mock, no Supabase apply / provider flip without Steven, new routes/nav need Steven OK. End clear-safe.
```

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-06-15 04:25 +10:00 - Codex. Prior AlphaMissense/protein viewer release details are retained in Cross-Agent Requests above and were shipped by Claude at `8a7095f`.

**Latest Codex update (2026-06-15 04:25 +10:00 - Codex):**
Graphify semantic refresh and maintenance guidance are complete and pushed. `origin/main` is `146ae9c`, including graphify refresh commit `4ff5ac2` (`chore(graphify): refresh semantic graph and maintenance guidance`) and handoff cleanup commit `146ae9c` (`docs(handoff): tag graphify follow-ups`).

Completed:
- Verified Claude's `8a7095f` sequence-context timeout fix: `httpx.HTTPError`/ReadTimeout now degrades to `workbench_sequence_context_resolver_error` warning instead of bubbling a 500; focused sequence-context, orchestration/contract/gene-viewer, and lookup-section contract pytest passed.
- Cleaned Codex-owned graphify leftovers, pinned graphify Python to `graphify-out/.graphify_python`, and optimized `.graphifyignore` to exclude reference/generated/public/test-result/tooling noise before semantic extraction.
- Ran graphify semantic extraction over 189 docs in 13 chunks; semantic cache now exists.
- Rebuilt final graph at commit `8a7095f`: `10,803` nodes, `29,423` links, `39` hyperedges, `574` communities.
- Generated full raw node-level `graphify-out/graph.html` with `graphify export html --graph graphify-out/graph.json --node-limit 20000`; Chrome verified nonblank canvas, vis-network loaded, search accepted `AlphaMissense`.
- Added durable graphify maintenance practice to `AGENTS.md` and `CLAUDE.md`; added `AGENTS.md` to Codex read order in `CODEX.md`.
- Added `.tools/` to `.gitignore` because it holds local screenshots/proof files and a Render CLI binary, not source.

Verification recorded 2026-06-15 04:18 +10:00:
- `git diff --cached --check` passed before commit `4ff5ac2`.
- `graphify-out/graph.json` check: `10,803` nodes, `29,423` links, `39` hyperedges, built_at_commit `8a7095f46855e3759c9012f7e6310ca62c517602`.
- `graphify-out/graph.html` contains `10803 nodes Â· 29423 edges Â· 574 communities`.
- Chrome DevTools render check passed for raw HTML: live canvas nonblank, `vis` ready, no console errors other than vis-network layout info.

Held local follow-ups for next session:
- `docs/proprietary/eamos-ai-gateway.md`: review separately for the paper->variants validation wording change; safe-looking doc diff but not graphify/Render scope.
- `scripts/eamos-encoding-scan.mjs`: review separately as a possible read-only mojibake scanner tooling commit; safe-looking but currently untracked and not wired into scripts/tests.
- `.tools/`: keep ignored/local-only. It includes screenshots and `.tools/render/cli_v2.20.0.exe`; do not commit.
- `docs/proprietary/eamos-ai-gateway.md` and `scripts/eamos-encoding-scan.mjs` should not be bundled into graphify, Render, or handoff commits.

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-15 04:25 +1000 - Codex graphify semantic refresh pushed
Eamos. Read CODEX.md, AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, then run git fetch origin && git status --short --branch.
Delta: Claude's `8a7095f` timeout fix was validated; graphify semantic pass completed and was pushed to `origin/main` in `4ff5ac2`, followed by handoff cleanup `146ae9c`. Eamos graph now has 10,803 nodes / 29,423 links / 39 hyperedges / 574 communities; semantic cache exists; Chrome verified raw `graphify-out/graph.html` renders. `.tools/` is ignored because it contains local screenshots and a Render CLI binary.
Next: review held local items separately: `docs/proprietary/eamos-ai-gateway.md` paper->variants wording and `scripts/eamos-encoding-scan.mjs` read-only mojibake scanner. Do not bundle those with graphify/Render. Keep graphify maintenance practice: run cheap `graphify update .` after code changes; run semantic extraction only at Steven's prompt or deliberate release/handoff checkpoints after corpus sanity check. Guardrails: no Supabase apply/mutation, no provider/env flips, keep `LLM_PROVIDER=mock`, `RAG_ENABLED=false`, `CRISPR_OFFTARGET_PROVIDER=auto`, `PRIMER_SPECIFICITY_PROVIDER=template`. End clear-safe.
```
