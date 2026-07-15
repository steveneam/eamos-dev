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
- **Codex:** STOPPED @ 2026-07-15 14:22 UTC — backend-CI optimization is complete
  on PR #11 and every GitHub check is green. The merge is paused for Steven's
  explicit approval. No active lane and no cloud mutation authorized.

## Log Edit-Lock

UNLOCKED · 2026-07-15 14:22 +0000 · Codex (PR-11 green; merge approval pending)

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-15 14:22 +0000 · Codex PR-11 merge gate
Read CURRENT.md, agent_handoff/README.md, then audit-2026-07-15.md.
PR #11 is open at 86e2873; GitHub run 29423099999 is fully green.
Cache suites fell 142.92s -> 17.62s with production behavior unchanged.
Worksteal was slower, so current xdist scheduling stays; two stable shards pass.
Required backend check now completes in ~2m08s versus the prior 3m35s.
Wait for Steven's explicit merge approval; no second GitHub reviewer is planned.
On approval, recheck main/CI, admin-merge PR #11, then verify post-merge CI.
M-013 branch-policy repair and all cloud mutations remain founder-gated.
Safe to clear: yes — the branch is pushed, CI is green, and merge is user-gated.
```

## Pointer

- Open target: PR #11 at `86e2873`; CI run `29423099999` is green.
- Base: main `9e73e31`; branch `codex/backend-ci-hermetic-worksteal`.
- Source audit and later lanes: `docs/repo-structure/audit-2026-07-15.md`.

## Delta

- Cache tests retain live-cache semantics but use offline coordinate, consensus,
  and gene-context providers; 39 tests improved by 87.7% wall time.
- Full two-worker load scheduler: 119.87s; worksteal: 125.03s, so no scheduler
  change. SHA-256 test-ID shards cover exactly all 1,646 collected tests.
- Local shard walls: 64.60s / 72.41s. GitHub pytest steps: 74s / 73s; total
  shard jobs: 2m01s / 1m57s. Stable aggregator `backend (pytest)` passed in 3s.
- Ruff, Black, 369 boundary/frontend-contract tests, web boundary, web/frontend
  CI, and Vercel preview are green. Python remains 3.12.
- Durable evidence and exact measurements are at the top of `PROGRESS.md`.

## Next Action

- Await Steven's explicit approval before merging PR #11. It is mergeable but
  branch policy reports blocked because solo self-review cannot satisfy the
  configured review/stale-check requirements; use the established admin override
  only after approval.
- If main moves, rebase and require the full PR matrix green again before merge.
- After merge, verify main CI and refresh `PROGRESS.md` / this handoff.
- M-013 required-check policy and all Render/Supabase/VPS mutations remain
  separately founder-gated.
