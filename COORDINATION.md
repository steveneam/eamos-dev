# COORDINATION — Eamos parallel-agent lane board

**Protocol source (read-only vault):** `Forj/bones/parallel-agents.md` (skeleton) +
`Forj/Wiki/reference/parallel-agent-workflow.md` (playbook). This file is the **live board**
+ the Eamos-specific adaptation. Keep it human-lean — do not machine-bloat it.

**Status:** _no active parallel sprint._ The plumbing is inert until there are ≥2
dependency-independent buckets meeting at one freezable contract, and Steven approves a
partition. Agents propose the sprint (see below); Steven never designs the setup.

---

## Live lanes

_lead: — · contract: — (FROZEN @ —)_

| lane | owner | owns (glob) | branch | status | depends-on | merge-order |
|------|-------|-------------|--------|--------|------------|-------------|
| _(none active)_ | | | | | | |

Status vocab: `pending · in_progress · blocked:<what> · review · merged`.
**One writer per row:** the lead owns assignments + merge-order; each owner writes only its
own `status`. Messages are append-only; you replace only your own state.

## Messages (append-only)

- _(none yet)_

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

**5. Merge gate — agent-run, Steven approves each seam.** Serialized, one lane at a time in
merge-order:
`rebase lane onto latest main → CI green (required check) → review → PAUSE for Steven's explicit
approval → merge → next lane rebases on new main`.
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
