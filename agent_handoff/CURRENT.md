# Current Agent State

> ## ▶ BOOT: Steven types **`gogogo`** — that IS the whole resume prompt.
>
> **Agent, on `gogogo` (or any greeting with no task): do this, unprompted.**
> He cannot copy text out of the terminal, and he may be sending it from a
> Telegram topic on his phone. Read, in order, then act:
> 1. this whole file (Resume Prompt → Pointer → Delta → Next Action)
> 2. `CLAUDE.md` + `agent_handoff/README.md` (protocol) and your memory
> 3. `git log --oneline -8` and `git status` — trust the repo, not the stamp
>
> Then state the Next Action in one sentence, say what you are starting, and
> start it. Do not ask “shall I?” — the Next Action is the standing approval.
> Stop only at a founder gate (spend, irreversible action, or anything the
> protocol names a founder decision).
>
> _Boot block added 2026-07-13 at the founder's direction. Keep it at the top
> when overwriting this file._

> **Live state only — overwrite the whole file each wrap.** History belongs in
> Git, `PROGRESS.md`, and the agents' rolling logs. Protocol →
> `agent_handoff/README.md`; risks → `docs/operations/risks-and-guardrails.md`;
> worktree truth → `git status --short --branch`.

## Active Status

- **Claude:** STOPPED @ 2026-07-15 10:55 UTC — no active lane. Last work was PR
  #7 / the Linux-host hook and MCP cleanup recorded in its rolling log.
- **Codex:** STOPPED @ 2026-07-15 12:45 UTC — opened PR #9 from
  `codex/graphify-retirement`. Graphify retirement, package/worktree guards,
  Chrome MCP hardening, and the 2026-07-15 whole-repo audit are pushed. Local
  gates are green. GitHub Actions run `29416286779` is red only because all
  three jobs were refused before startup by the account billing/spending limit;
  this founder action is recorded in `NEEDS-STEVEN.md`. No deploy, provider,
  environment, database, Supabase schema, asset, resize, or cancellation
  mutation occurred.

## Log Edit-Lock

UNLOCKED · 2026-07-15 12:45 +0000 · Codex (PR #9 published; billing gate recorded)

## Resume Prompt

```text
# Resume prompt · 2026-07-15 12:45 +0000 · Codex PR #9 gate
Eamos on syd4. Read CURRENT.md, agent_handoff/README.md, then
docs/repo-structure/audit-2026-07-15.md. Check git status and PR #9.
Actions run 29416286779 never started: GitHub blocked runners for billing/spend.
Steven must restore Actions billing/limit; then rerun all three CI jobs.
Require fresh green CI + Vercel and Steven's explicit approval before merge.
After PR #9 lands, fix P0 run/report object authorization serially, with
two-user negative tests, before search auth/schema/dependency refactors.
Supabase and Chrome MCP are healthy; Render MCP awaits RENDER_API_KEY.
Do not mutate Supabase/Render/VPS state without the recorded approval gates.
```

## Pointer

- Review/merge gate: PR #9 → Actions run `29416286779` →
  `agent_handoff/NEEDS-STEVEN.md`.
- Audit and proposed Mode B lanes:
  `docs/repo-structure/audit-2026-07-15.md`.
- Render→VPS Phase 1 contract: `agent_handoff/FROM-SWORDFISH.md` and
  `/home/deploy/work/swordfish/research/project1-asset-migration-plan-2026-07-15.md`.

## Delta

- Removed both tracked Graphify skill copies, hooks/ignores, stale memory, and
  living-document instructions: commit `474c8b3` (2,934 net deletions).
- Added root hook preparation, install guards, active-web boundary command, and
  headless/isolated Chrome MCP arguments; real Chrome navigation and real
  Supabase MCP project lookup passed.
- Added the 470-line evidence-backed audit in `fb150c9`: 31 active source files
  exceed 1,000 lines (34 with frozen Vite), versus none in Thalon/Swordfish;
  P0 authorization plus P1 auth/schema/dependency/Render findings are ordered
  ahead of cosmetic package folds.
- Local verification: active Next lint/type/build green; frozen Vite lint and
  139 tests green (its build failure is documented); backend Ruff/Black green,
  pytest 1,619 passed / 20 skipped; boundary/structure ratchets green; live
  Render health returned 200.

## Next Action

- **Founder gate:** restore GitHub Actions billing/spending capacity.
- **Then lead:** rerun PR #9 checks, review full scope, and pause for Steven's
  explicit approval. Never merge on red.
- **After merge:** serial P0 authorization fix first; freeze the principal/owner
  contract before launching the four audit lanes.
- **Render MCP:** Steven creates a Render API key and exports it as
  `RENDER_API_KEY` outside chat; then verify read-only access. This does not
  authorize a deploy, migration, seed, resize, or cancellation.
