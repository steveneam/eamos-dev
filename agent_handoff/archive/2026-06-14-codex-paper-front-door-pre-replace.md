## Codex - Last Task & Resume` section
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
  the trimmed file passes clean, the pre-trim archive fails on every rule. Â·
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
  `CRISPR_OFFTARGET_INDEX_PATH` and health reports the index ready. Â·
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
bundle): `f16390a` Workbench local-hardening (Codex) Â· `2e8090d` compact-index
materialization + Gene View build-ledger fix (Codex; clears the deployed-`550641d`
`gene_view=runtime_partial` blocker) Â· `95a57e4` ClinGen `c.260A>G` correction
(Codex; behavior change) Â· `0c91461` AI-gateway literature RAG + messy-textâ†’JSON
+ paperâ†’variants P1+2 (Claude; inert) Â· this shared-docs/proprietary/graph
commit. Pre-commit safety gate: full backend pytest GREEN (combined tree), ruff
clean, black clean (reformatted 12 lane-4 files; Codex lanes already clean).
Excluded `.tools/render/` (local Render CLI binary) + `codex-workbench-temp.md`.
Then pushed (`main` ahead 6) â†’ Vercel FE auto-deploy + manual Render SG deploy
â†’ provider-cache verify. Graphify refresh owed (Codex's lane; not run here).

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
1. paperâ†’variants **Phase 3** (Codex coordination): route candidates through the
   EXISTING resolution stack - `EamosSearchInputResolver` (cDNA) + source-backed
   candidate resolution (protein). REUSE, don't duplicate Codex's `search_input_*`.
2. Remaining roadmap follow-ons: report-narrative, cross-tool audit, NLâ†’SQL.
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
Section last edited: 2026-06-14 16:14 +10:00 - Codex. Detailed history is in
PROGRESS.md, commit messages, and the touched docs.

**Latest Codex update (2026-06-14 16:29 +10:00 - Codex):**
Paper->variants Phase 3 is complete locally, the next paper front-door endpoint
is queued, and the ACMG visualization backend lane is prepared behind it.

Completed:
- Ran `python -m graphify update .` before code work. It rebuilt
  `graphify-out/` and skipped only oversized HTML viz; Gemini/API-key and
  graphify skill/package-version tips were informational.
- Replaced the paper->variants direct VariantValidator-only gate with existing
  Eamos resolver composition: cDNA/genomic candidates now route through
  `EamosSearchInputResolver`; protein candidates route through
  `SearchCandidateResolver`.
- Preserved fail-closed semantics: a single high-confidence source-backed
  protein candidate validates; ambiguous/medium suggestions are returned as
  candidates; experimental protein constructs remain explicitly non-coordinate
  `experimental_construct` records.
- Added additive paper-variant output fields for `resolved_candidate_id`,
  `source_support`, `source_inputs`, ranked `candidates`,
  `resolver_warnings`, and `resolver_provenance`.
- Updated `eamos_paper_variants` CLI wording and
  `docs/proprietary/eamos-ai-gateway.md` to reflect the resolver stack.
- Added read-only `scripts/eamos-encoding-scan.mjs`. Byte check showed
  `paper_variants.py` is valid UTF-8; visible mojibake there is a shell/tool
  rendering issue.
- Per Steven's follow-up, repaired the narrow live handoff mojibake in
  `agent_handoff/CURRENT.md` to ASCII-safe text. The old archive remains
  historical and still has pre-existing mojibake unless explicitly normalized.
- Read `docs/report-acmg-viz/spec.md`, queried graphify for ACMG/report
  contract context, inspected `schemas/run.py`, `computational_calibration.py`,
  and `pvs1_nmd.py`, then added `docs/report-acmg-viz/plan.md` for next-session
  execution.
- Read Claude's `docs/paper-variants-ui/spec.md`. Next session should build the
  backend front door first: `POST /api/v1/paper-variants/extract`, accepting
  JSON `{text}` or a PDF upload, wrapping
  `PaperVariantsService(settings).extract(text, validate=True)`, reusing
  `services/pdf_text.extract_pdf_text`, and returning sanitized
  `PaperVariantsResult` plus CLI-style guardrail and PDF metadata. It must be
  login-gated and rate-limited like `/chat/stream`, mock-first unless
  `LLM_PROVIDER=gateway`, and must not duplicate `search_input_*`.
- Next-session ACMG prep conclusion: Step 0 is backend-led contract freeze in
  `schemas/run.py`; then create separate advisory
  `services/acmg_points_engine.py`; do not touch `clinical_consensus.py`.
  Reuse `computational_calibration.py` and `pvs1_nmd.py`; gnomAD/ClinVar
  source wiring comes after core math and schema freeze.

Verification recorded 2026-06-14 16:14 +10:00:
- `git fetch origin` passed; `git status --short --branch` showed
  `main...origin/main` with only intended local edits plus pre-existing
  untracked `.tools/` and `codex-workbench-temp.md`.
- `git log -8 --oneline` confirmed `origin/main` at `3ccef4d` coordinated
  release closeout.
- `python -m pytest tests/test_paper_variants.py -q` passed (13 tests).
- `python -m pytest tests/test_search_input_resolver.py tests/test_variant_search_integration.py -q`
  passed (46 tests).
- `python -m pytest tests/test_frontend_contract.py tests/test_lookup_normalize.py tests/test_tool_invariants.py -q`
  passed.
- `python -m ruff check app/services/paper_variants.py app/schemas/paper_variants.py app/cli/eamos_paper_variants.py tests/test_paper_variants.py`
  passed.
- `python -m black --check --target-version py310 app/services/paper_variants.py app/schemas/paper_variants.py app/cli/eamos_paper_variants.py tests/test_paper_variants.py`
  passed.
- `node scripts/eamos-encoding-scan.mjs app/backend/app/services/paper_variants.py app/backend/app/schemas/paper_variants.py app/backend/app/cli/eamos_paper_variants.py app/backend/tests/test_paper_variants.py scripts/eamos-encoding-scan.mjs --json`
  passed with no findings in touched paper/scanner files.
- `git diff --check` passed with line-ending warnings only.
- Final `python -m graphify update .`: first run hit a 120s local timeout;
  rerun with a longer timeout passed and reported no code-graph topology
  changes.
- `node scripts/eamos-encoding-scan.mjs agent_handoff/CURRENT.md docs/report-acmg-viz/plan.md --json`
  passed with no findings.
- `git diff --check -- agent_handoff/CURRENT.md docs/report-acmg-viz/plan.md scripts/eamos-encoding-scan.mjs`
  passed with line-ending warnings only.
- `docs/paper-variants-ui/spec.md` was read and queued; no endpoint code was
  changed in this note-only update.

Guardrails:
- No Render env/provider flip, Supabase mutation, startup download, commit,
  push, RAG enablement, AI-gateway runtime flip, or search_input_* API change.
- Keep `LLM_PROVIDER=mock`, `RAG_ENABLED=false`,
  `CRISPR_OFFTARGET_PROVIDER=auto`, and
  `PRIMER_SPECIFICITY_PROVIDER=template`.

Message for Claude:
- paper->variants Phase 3 is now wired through Codex's existing stack:
  cDNA/genomic -> `EamosSearchInputResolver`; protein -> source-backed
  `SearchCandidateResolver`. Do not duplicate `search_input_*`; compose these
  services and preserve candidate/provenance/fail-closed semantics.
- ACMG-viz backend plan is ready at `docs/report-acmg-viz/plan.md`. Codex owns
  Step 0 contract freeze: add `eamos_computed_classification` in
  `schemas/run.py` exactly from spec section 3, then separate
  `acmg_points_engine.py`. Claude can mock the frozen contract for
  `lib/acmg/points.ts` and SVG instruments after that.
- Paper-variants front door is queued before ACMG-viz: Codex should expose
  `POST /api/v1/paper-variants/extract` with JSON text or PDF upload,
  login-gated/rate-limited like `/chat/stream`, returning the same sanitized
  candidate/provenance/fail-closed output the FE will render. Backend owns the
  request/response shape; Claude will mirror it in `backend.ts`.

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-14 16:29 +1000 - Codex paper front door, then ACMG contract
Eamos. Read CODEX.md, AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, docs/paper-variants-ui/spec.md, docs/report-acmg-viz/spec.md, docs/report-acmg-viz/plan.md, then run git fetch origin && git status --short --branch.
Delta: paper->variants Phase 3 is complete locally; live CURRENT.md mojibake is repaired scanner-clean; next backend queue is paper front door first, then ACMG-viz contract freeze. First task: expose `POST /api/v1/paper-variants/extract` wrapping `PaperVariantsService(settings).extract(text, validate=True)`, accepting JSON `{text}` or PDF upload via `pdf_text.extract_pdf_text`, returning sanitized `PaperVariantsResult` plus CLI-style guardrail/pdf meta.
Guardrails for first task: login-gated and rate-limited like `/chat/stream`; mock-first regex extractor unless `LLM_PROVIDER=gateway`; backend-led request/response contract for Claude to mirror in `backend.ts`; no `search_input_*` duplication; preserve candidate/provenance/fail-closed semantics.
Then: ACMG-viz Step 0 contract freeze only: add `ReportPayload.eamos_computed_classification` in `schemas/run.py` per `docs/report-acmg-viz/spec.md` section 3, then separate `services/acmg_points_engine.py` core in a later slice. Do not touch `clinical_consensus.py`; keep VCEP overlay, AI narration, benchmark harness, coverage expansion, and ClinVar P/B precompute out of v1 unless explicitly started.
Verification so far: prior paper/search-input/lookup/contract pytest + Ruff/Black + graphify passed; mojibake scan for CURRENT.md and new plan passed; diff-check for handoff/plan/scanner passed with line-ending warnings only. No Render/Supabase/startup-download/provider flip/commit/push. End clear-safe.
```

