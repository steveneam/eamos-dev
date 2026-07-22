# COORDINATION — Eamos parallel-agent lane board

**Protocol source (read-only vault):** `Forj/bones/parallel-agents.md` (skeleton) +
`Forj/Wiki/reference/parallel-agent-workflow.md` (playbook). This file is the **live board**
+ the Eamos-specific adaptation. Keep it human-lean — do not machine-bloat it.
Ratchet policy: `docs/parallel-agents/ratchet-philosophy.md`.

**Ownership is agent-agnostic (Steven, 2026-07-08):** a lane assigns a *glob to a worktree*,
not a discipline to an agent. Either agent (Claude or Codex) can own any lane, full-stack; the
`owner` column records who ran it, not a role. Steven picks agents by availability + usage limits.

**Status:** _Product Workflow V1 ACTIVE — A/B/C integrated; D/E pending._ Historical
Mode-A dogfood completed 2026-07-03; its record remains below.

---

## Product Workflow V1 sprint (active)

_Launched: 2026-07-19 09:55 +0000 · Codex lead · Mode B · exact owned paths and frozen
contract: `plans/product-workflow-integration/plan.md` + `spec.md`._

Lane A was integrated and verified on `main` as `6d2f6c9` through Steven's
one-time manual CI-equivalent substitute. Wave 1 launched B/C from current
`origin/main@3f0a081`. Delivery is now
`A → design-binding → B → Task F apply → C → D → E`; the Task F mutation has
its own founder gate.

The serial Workbench design-binding amendment and Lane B are merged. Steven
approved Task F's filled exact mutation card on 2026-07-22; the two reviewed
`eamos-dev` migrations applied and passed ledger, RLS/grant/index, advisor, and
transaction-scoped two-owner verification. Lane C was then rebased, passed the
full required CI/Vercel gate, and merged as PR #17. Post-merge `main` CI run
`29930639353` passed every job, including immutable-image pull-back verification.

| lane | owner | owns (exact source) | branch | status | depends-on | merge-order |
|------|-------|---------------------|--------|--------|------------|-------------|
| A contract-v1 | Codex(wt) | `plan.md` Lane A schema/TS/canary paths | `agent/product/contract-v1-manual` | integrated `6d2f6c9` · Vercel green | — | 1 |
| serial design-binding | Codex lead | approved amendment paths in `plan.md` | `agent/product/contract-binding` | merged · PR #18 · `55300f4` | A merged | 2 |
| B workflow-backend | Codex(wt) | `plan.md` Lane B backend/migration paths | `agent/product/workflow-backend` | merged · PR #16 · `5c5a950` | design-binding merged | 3 |
| Task F apply | Codex lead | runbook + named `eamos-dev` migration checkpoint | — | complete · remote ledger `20260722144613` + `20260722144619`; post-apply proof green | B merged + fresh Steven approval | 4 |
| C surface-flow | Codex(wt) | `plan.md` Lane C web paths | `agent/product/surface-flow` | merged · PR #17 · `0d52e11` (head `f880655`) | A/B merged; merge after Task F | 5 |
| D workbench-canvas | unassigned | `plan.md` Lane D web paths | `agent/product/workbench-canvas` | pending | B + C merged | 6 |
| E workflow-ratchets | unassigned | `plan.md` Lane E scripts/docs/CI paths | `agent/product/workflow-ratchets` | pending | D merged | 7 |

---

## Live lanes

_lead: Claude · contract: FE-only presentational, no shared types (FROZEN @ 94def2a)_

| lane | owner | owns (glob) | branch | status | depends-on | merge-order |
|------|-------|-------------|--------|--------|------------|-------------|
| A popfreq-empty | Claude(wt) | `app/web/components/report/PopFreqEmptyState.tsx` | `agent/popfreq-empty-state` | merged `cd8f15e` | — | 1 |
| B geneviewer-eb | Claude(wt) | `app/web/components/report/GeneViewerErrorBoundary.tsx` | `agent/geneviewer-errorboundary` | merged `eeaefa3` | — | 2 |
| C insilico-rows | Claude(wt) | `app/web/components/report/InSilicoPlaceholderRows.tsx` | `agent/insilico-placeholder-rows` | merged `05e0321` | — | 3 |

_Integration (wire all 3 into `ReportClient.tsx`) is a single-owner step AFTER all lanes merge — not a lane._

## Search 7/8 sprint (closed: parallel launch canceled; implemented sequentially)

_lead: Codex · contract: Search response TypeScript mirror frozen in pushed commit `f7ef561` · status: A/B/C reviewed, committed, and pushed in `319b9e7`; parked worktrees/branches cleaned 2026-07-04 09:08 +1000_

The lane table below is a historical partition record, not an active sprint.
The three `.claude/worktrees/search-*` worktrees and local `agent/search/*`
branches were removed after Steven explicitly approved cleanup. Do not revive
the parallel flow without a fresh partition and launch package.

Serial pre-step before any lane forks:

- Freeze `SearchHit` / `SearchResponse` / `SearchAnswerResponse` by mirroring
  current backend Search schema types into `app/web/lib/backend.ts` and
  `app/frontend/src/lib/backend.ts`, with contract canary coverage.
- Contract freeze is the only lane-shared seam. Any lane needing to edit
  `app/web/lib/backend.ts`, `app/frontend/src/lib/backend.ts`, or
  `app/backend/app/schemas/search.py` means stop and re-plan with the lead.

| lane | owner | owns (glob) | branch | status | depends-on | merge-order |
|------|-------|-------------|--------|--------|------------|-------------|
| A ci-ratchets | Codex | `.github/workflows/ci.yml`; `app/backend/tests/test_pdf_text.py`; `app/backend/tests/test_source_reader_proofs.py` | `agent/search/ci-ratchets` | closed:sequential `319b9e7` | contract-freeze | 1 |
| B answer-hardening | Codex | `app/backend/app/services/search_answer.py`; `app/backend/tests/test_search_api_local.py`; `app/backend/tests/test_search_api.py` | `agent/search/answer-hardening` | closed:sequential `319b9e7` | contract-freeze | 2 |
| C results-web | Codex | `app/web/lib/search/**`; `app/web/components/search/**`; `app/web/app/search/**`; `app/web/app/api/v1/search/**`; `app/web/components/landing/LandingClient.tsx`; `app/web/components/report/ReportClient.tsx`; `app/web/lib/variant-search.ts` | `agent/search/results-web` | closed:sequential `319b9e7` | contract-freeze | 3 |

Steven launch package, after Codex confirms the contract-freeze commit is on
local `main`:

```powershell
git worktree add .claude/worktrees/search-ci-ratchets -b agent/search/ci-ratchets
git worktree add .claude/worktrees/search-answer-hardening -b agent/search/answer-hardening
git worktree add .claude/worktrees/search-results-web -b agent/search/results-web
```

Historical note: this launch package was run, then canceled before lane PRs.
The resulting worktrees/branches were cleaned after the sequential commit.

Status vocab: `pending · in_progress · blocked:<what> · review · merged`.
**One writer per row:** the lead owns assignments + merge-order; each owner writes only its
own `status`. Messages are append-only; you replace only your own state.

## Messages (append-only)

- 2026-07-03 (Claude, lead): Mode-A dogfood launched. 3 lanes forked from `main@ef9f7e2`, disjoint
  new files, no shared-glob contention. Lanes push `agent/*` + open PRs; lead runs the serialized
  gate in merge-order 1→2→3, pausing for Steven's OK before each merge.
- 2026-07-03 (Claude, lead): **Sprint closed — 3/3 merged, prod green.** `strict:true` forced a
  rebase + fresh CI run per lane after the first (expected tax, not a bug). Leftover
  `isolation:worktree` worktrees + local branches cleaned up. Field lessons + a `tsc`-in-CI
  follow-up recorded in `docs/parallel-agents/retrofit-notes.md`.
- 2026-07-03 (Claude, lead): **Integration done (single-owner, `28f0e35`, prod green).** Wired
  `GeneViewerErrorBoundary` around §4 (`ReportClient`) — a real gap. `PopFreqEmptyState` +
  `InSilicoPlaceholderRows` left **intentionally inert**: §3 already has
  `PopulationUnavailableStatePanel`, §2 already renders catalog placeholders + a LazySection
  loading state → wiring them would duplicate UI. Portable POC report for the Forj vault:
  `docs/parallel-agents/mode-a-vault-report.md`. **Sprint fully closed.**
- 2026-07-04 (Codex, lead): Search 7/8 parallel lane execution was canceled at Steven's request
  after the spawned-worker trial. Codex kept the pushed contract freeze (`f7ef561`) and implemented
  lanes A/B/C sequentially in the main checkout. Local verification passed, browser desktop smoke
  was partially completed, and mobile live verify was skipped at Steven's wrap request. Changes are
  uncommitted pending Steven review/commit approval; no deploy/env/provider/Supabase/source/destructive
  action occurred.
- 2026-07-04 (Codex, lead): **Search 7/8 closed.** Review found no blockers; committed/pushed
  sequential implementation as `319b9e7` on `origin/main`, then removed the parked
  `.claude/worktrees/search-*` worktrees and local `agent/search/*` branches after Steven's
  explicit cleanup approval. No deploy/env/provider/Supabase/source action occurred.
- 2026-07-19 (Codex, lead/owner): **Product Workflow Lane A is in review.** Commit
  `bf589e8` is pushed in PR #15; all Lane A local/structural gates and the Vercel
  preview passed. Actions run `29683028720` had seven failures with zero steps and
  two skips under the known minute lock, so required CI is not green. No merge or
  B/C launch occurred.
- 2026-07-19 (Codex, lead/owner): Steven approved a one-time Lane A manual
  CI-equivalent gate and direct integration. The contract was rebuilt unchanged
  on current `main`; focused/full backend, web, type/lint, boundary, coordination,
  Python audit/format/static, and diff gates passed. Docker is unavailable on
  this host and Google Fonts blocked the local Next build, so a fresh same-commit
  Vercel preview remains required before `main` promotion. No downstream or cloud
  gate was waived.
- 2026-07-19 (Codex, lead/owner): **Lane A integrated.** Exact commit `6d2f6c9`
  reached `main` with `[skip ci]`; Actions did not run, both preview and production
  Vercel builds passed, the current-main contract/web/structural smokes passed,
  and superseded PR #15 was closed. B/C were not launched and every downstream
  mutation/deploy gate remains intact.
- 2026-07-22 14:08 +0000 (Codex, lead/owner): **Actions restored; serial gate
  ready.** PR #18 is fully green and awaits Steven's explicit merge
  approval. Lane B (`682048b`) and Lane C (`fd5e4f3`) repaired their executed CI
  regressions and pass every branch-specific job plus Vercel; their only red job
  is the pre-contract dependency lock fixed by #18. No lane merged and Task F
  remains a separate fresh mutation approval.
- 2026-07-22 14:28 +0000 (Codex, lead/owner): **Serial merges green.** Steven
  approved the code merges; PR #18 merged as `55300f4` and PR #16 merged as
  `5c5a950` after clean rebases, full required CI, dependency security, and
  Vercel. PR #17 was rebased to `84c8655` and is fully green; it remains held
  behind Task F. Read-only `eamos-dev` inventory confirms the new migration is
  absent and security advisors are clear; no Supabase mutation occurred.

---

## How we run a sprint (Eamos)

**1. Agents propose — Steven approves.** When upcoming work has ≥2 dependency-independent
buckets that meet at one freezable contract, the agent proposes the partition (lanes, owned
globs, frozen contract, merge order) and hands Steven **exact copy-paste launch commands**.
Steven approves the partition and runs them; he never designs the setup. **3–5 lanes max;
coupled work runs sequentially** (forcing it parallel just moves the coupling into merge conflicts).

**2. Pick Mode A or Mode B as guidance, not dogma.**

- **Mode A:** one lead runs worktree-subagent lanes. Use it for small, quick,
  disjoint work where the lead can hold the whole sprint in one context.
- **Mode B:** Steven opens one terminal/runtime per lane, each pointed at its own
  worktree/branch. Use it for larger work, backend/cloud caution, longer local
  verification, or when lanes need independent context budgets.

Either mode keeps the same merge model: one lead is the sole merger, Steven
approves seams, and lanes never merge themselves.

**3. Freeze the contract first.** The interface where lanes meet — the backend↔FE API types
(schema-first: backend Pydantic defines it, TS mirrors it) — is committed to `main` *before* any
lane forks. One owner (any agent) for the sprint; frozen. A lane needing to edit it is the signal
the partition was wrong → re-plan, don't ad-hoc edit.
For Search 7/8, the frozen seam is the backend `SearchHit`/`SearchResponse`/`SearchAnswerResponse`
shape mirrored into the active web contract before lanes fork.

**4. Launch** (the agent hands Steven this, filled in — one terminal per lane, from `D:\eamos`):

```
git worktree add .claude/worktrees/<lane> -b agent/<lane>/<task>
cd .claude/worktrees/<lane>
# Claude Code auto-copies .worktreeinclude files (app/backend/.env, app/web/.env.local, .context/)
# install deps:  web → npm --prefix app/web ci   ·   frontend → npm --prefix app/frontend ci
#                backend → pip install -r app/backend/requirements.txt
# offset ports:  Next :3000/:3001/…   ·   Vite :5173/:5174/…
claude          # start the lane agent in this worktree
```

Codex lane sessions can use the same worktree directories; open a separate Codex
session with its working folder set to `.claude/worktrees/<lane>`.

**5. Cloud resource isolation (Eamos-specific):**

- **Supabase — single-owner serialized.** Exactly ONE lane owns `supabase/migrations/**` per
  sprint; migration / durable-DB work is **never parallelized** (no two lanes migrate one shared
  cloud DB). Most dev runs on the local seam (SQLite / `LLM_PROVIDER=mock`) → free per-worktree.
- **Vercel — per-lane previews are free.** Every `agent/*` branch push auto-creates a **preview**
  deploy = free per-lane verification. Only `main` = prod. Never run `vercel` from a worktree or
  from `app/web`; deploy from the repo root.
- **Render — main-only, Codex-owned.** Backend deploy happens post-merge, from `main`, owned by
  Codex (the deploy hook is intentionally **not** copied into worktrees). A lane never deploys prod.

**6. Lane scope rule.** One lane = one branch = one worktree = one disjoint
glob. `COORDINATION.md` is the only expected shared conflict. Before merging,
the lead checks lane scope with `git log --name-only main..<lane>` against the
owned glob. A conflict or touched file outside the board is a partition leak.

If a lane needs a shared surface outside its glob (for example `.github/workflows/ci.yml`
or a frozen contract), it does not edit it directly. It ships a `.example` file
inside its own glob or posts a board message telling the lead exactly what to
activate in a single-owner pass.

**7. Founder-only and lead-only actions are explicit.** Cloud root/IAM/billing,
provider/env flips, Supabase mutations, source materialization/download/upload,
deploy hook use, cleanup deletion, and branch surgery are `[Steven]` or
lead-approved actions. Lanes scaffold around them rather than blocking or
silently performing them.

**8. Merge gate — lead-run, Steven approves each seam.** One **lead** per sprint (the proposing
agent) is the **sole merger**; lane agents push + mark their row `review` + hand off — they never
merge their own branch. Lane ownership (who edits a glob) ≠ merge authority (the lead). Serialized,
one lane at a time in merge-order:
`rebase lane onto latest main → CI green (required check) → review → PAUSE for Steven's explicit
approval → lead merges → next lane rebases on new main`.
**Never merge on red.** If two lanes touched a shared file (partition leak), a deliberate
conflict-resolver pass reconciles it — flag both intents, keep the union, **never a silent overwrite** —
then fix the partition so it can't recur. Stuck ~3 iterations on one error → kill the lane, reassign fresh.

**9. Ratchets land with the lesson.** Each sprint promotes expensive lessons up
the ladder in `docs/parallel-agents/ratchet-philosophy.md`: executable checks
where possible, then structural seams, then tracked config, then docs. Tag
ratchets as invariant or opinion so Eamos can prune stale workflow tax at
re-charter.

---

## The merge gate infrastructure

- CI: `.github/workflows/ci.yml` — web (lint + vercel guard) · frontend (lint + vitest) ·
  backend (pytest).
- `main` is protected with the CI check **required**; `enforce_admins` is **off** by design —
  Steven + Codex keep direct-pushing routine commits, and only `agent/*` lane branches go through
  the PR + CI gate.
