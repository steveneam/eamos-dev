# COORDINATION — Eamos parallel-agent lane board

**Protocol source (read-only vault):** `Forj/bones/parallel-agents.md` (skeleton) +
`Forj/Wiki/reference/parallel-agent-workflow.md` (playbook). This file is the **live board**
+ the Eamos-specific adaptation. Keep it human-lean — do not machine-bloat it.

**Status:** _Mode-A dogfood COMPLETE (merges) — 2026-07-03._ 3/3 lanes merged linear onto `main`
(`cd8f15e`/`eeaefa3`/`05e0321`); first-try green, zero conflicts; prod deploy green. Machinery
validated end-to-end. Components landed **inert (unimported)** — the follow-on `ReportClient`
integration (single-owner) is the remaining step. Lessons: `docs/parallel-agents/retrofit-notes.md`.

---

## Live lanes

_lead: Claude · contract: FE-only presentational, no shared types (FROZEN @ 94def2a)_

| lane | owner | owns (glob) | branch | status | depends-on | merge-order |
|------|-------|-------------|--------|--------|------------|-------------|
| A popfreq-empty | Claude(wt) | `app/web/components/report/PopFreqEmptyState.tsx` | `agent/popfreq-empty-state` | merged `cd8f15e` | — | 1 |
| B geneviewer-eb | Claude(wt) | `app/web/components/report/GeneViewerErrorBoundary.tsx` | `agent/geneviewer-errorboundary` | merged `eeaefa3` | — | 2 |
| C insilico-rows | Claude(wt) | `app/web/components/report/InSilicoPlaceholderRows.tsx` | `agent/insilico-placeholder-rows` | merged `05e0321` | — | 3 |

_Integration (wire all 3 into `ReportClient.tsx`) is a single-owner step AFTER all lanes merge — not a lane._

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
  follow-up recorded in `docs/parallel-agents/retrofit-notes.md`. Next: single-owner
  `ReportClient` integration of the 3 inert components.

---

## How we run a sprint (Eamos)

**1. Agents propose — Steven approves.** When upcoming work has ≥2 dependency-independent
buckets that meet at one freezable contract, the agent proposes the partition (lanes, owned
globs, frozen contract, merge order) and hands Steven **exact copy-paste launch commands**.
Steven approves the partition and runs them; he never designs the setup. **3–5 lanes max;
coupled work runs sequentially** (forcing it parallel just moves the coupling into merge conflicts).

**2. Freeze the contract first.** The interface where lanes meet — the backend↔FE API types
(backend-led) — is committed to `main` *before* any lane forks. One owner; frozen for the
sprint. A lane needing to edit it is the signal the partition was wrong → re-plan, don't ad-hoc edit.

**3. Launch** (the agent hands Steven this, filled in — one terminal per lane, from `D:\eamos`):

```
git worktree add .claude/worktrees/<lane> -b agent/<lane>/<task>
cd .claude/worktrees/<lane>
# Claude Code auto-copies .worktreeinclude files (app/backend/.env, app/web/.env.local, .context/)
# install deps:  web → npm --prefix app/web ci   ·   frontend → npm --prefix app/frontend ci
#                backend → pip install -r app/backend/requirements.txt
# offset ports:  Next :3000/:3001/…   ·   Vite :5173/:5174/…
claude          # start the lane agent in this worktree
```

**4. Cloud resource isolation (Eamos-specific):**

- **Supabase — single-owner serialized.** Exactly ONE lane owns `supabase/migrations/**` per
  sprint; migration / durable-DB work is **never parallelized** (no two lanes migrate one shared
  cloud DB). Most dev runs on the local seam (SQLite / `LLM_PROVIDER=mock`) → free per-worktree.
- **Vercel — per-lane previews are free.** Every `agent/*` branch push auto-creates a **preview**
  deploy = free per-lane verification. Only `main` = prod. Never run `vercel` from a worktree or
  from `app/web`; deploy from the repo root.
- **Render — main-only, Codex-owned.** Backend deploy happens post-merge, from `main`, owned by
  Codex (the deploy hook is intentionally **not** copied into worktrees). A lane never deploys prod.

**5. Merge gate — lead-run, Steven approves each seam.** One **lead** per sprint (the proposing
agent) is the **sole merger**; lane agents push + mark their row `review` + hand off — they never
merge their own branch. Lane ownership (who edits a glob) ≠ merge authority (the lead). Serialized,
one lane at a time in merge-order:
`rebase lane onto latest main → CI green (required check) → review → PAUSE for Steven's explicit
approval → lead merges → next lane rebases on new main`.
**Never merge on red.** If two lanes touched a shared file (partition leak), a deliberate
conflict-resolver pass reconciles it — flag both intents, keep the union, **never a silent overwrite** —
then fix the partition so it can't recur. Stuck ~3 iterations on one error → kill the lane, reassign fresh.

---

## The merge gate infrastructure

- CI: `.github/workflows/ci.yml` — web (lint + vercel guard) · frontend (lint + vitest) ·
  backend (pytest).
- `main` is protected with the CI check **required**; `enforce_admins` is **off** by design —
  Steven + Codex keep direct-pushing routine commits, and only `agent/*` lane branches go through
  the PR + CI gate.
