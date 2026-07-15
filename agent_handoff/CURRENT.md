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
- **Codex:** STOPPED @ 2026-07-15 14:35 UTC — Steven approved PR #11; it is
  rebase-merged and post-merge implementation CI is green. No active lane and
  no cloud mutation authorized. Next audit item is the P1 search-auth split.

## Log Edit-Lock

UNLOCKED · 2026-07-15 14:35 +0000 · Codex (PR-11 merge recorded; locks released)

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-15 14:35 +0000 · Codex P1 search-auth split
Read CURRENT.md, agent_handoff/README.md, then docs/repo-structure/audit-2026-07-15.md.
PR #11 is rebase-merged at 5d581a8; latest main checks are green at wrap.
Backend cache tests are hermetic and the exhaustive two-shard CI gate is live.
Start P1 search auth: move /api/v1/search to AuthenticatedPrincipal.
Preserve owner-scoped SearchAccessContext; do not widen report/run access.
Add a Supabase-JWT route test plus local-token compatibility coverage.
Use the vibe-security skill because this changes auth and user-data access.
Python remains 3.12; no second GitHub reviewer account is planned.
M-013 branch-policy repair and all cloud mutations remain founder-gated.
Safe to clear: yes — main is clean, PR #11 is merged, and the next lane is scoped.
```

## Pointer

- Merged target: PR #11 at `5d581a8`; post-merge run `29424019736` is green.
- Implementation commit on main: `a336e3a`; Python remains 3.12.
- Next lane: P1 search auth in `docs/repo-structure/audit-2026-07-15.md`.

## Delta

- Cache tests retain live-cache semantics but use offline coordinate, consensus,
  and gene-context providers; 39 tests improved by 87.7% wall time.
- Full two-worker load scheduler: 119.87s; worksteal: 125.03s, so no scheduler
  change. SHA-256 test-ID shards cover exactly all 1,646 collected tests.
- Post-merge main shard jobs passed in 1m58s / 2m04s; stable aggregator
  `backend (pytest)` passed in 3s. Web passed in 1m10s; frontend in 31s.
- Ruff, Black, 369 boundary/frontend-contract tests, web boundary, web/frontend
  CI, and Vercel preview are green. Python remains 3.12.
- Durable evidence and exact measurements are at the top of `PROGRESS.md`.

## Next Action

- Correct the active search auth split next: accept both Supabase and local
  principals while retaining owner-scoped search access and non-enumeration.
- Add negative cross-user coverage and both token compatibility paths before any
  route dependency change lands.
- Do not apply the missing live Supabase migration in this lane; that remains a
  separate reviewed, rollback-ready founder-gated operation.
- M-013 required-check policy and all Render/Supabase/VPS mutations remain
  separately founder-gated.
