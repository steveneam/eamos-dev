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
- **Codex:** ACTIVE @ 2026-07-15 13:59 UTC — PR #10 is merged and post-merge
  main is green. Starting the queued backend CI optimization: hermetic cache
  tests, then xdist work-steal benchmark. No deploy or cloud mutation authorized.

## Log Edit-Lock

UNLOCKED · 2026-07-15 13:59 +0000 · Codex (PR-10 merge recorded; locks released)

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-15 13:59 +0000 · Codex backend-CI optimization
Read CURRENT.md, agent_handoff/README.md, then audit-2026-07-15.md.
PR #10 is rebase-merged at 5d8b76b; P0 run/report ownership is complete.
Post-merge main CI 29421304052 is green; Python remains 3.12.
Profile cache-test live-network waits and make those tests hermetic first.
Then benchmark current xdist scheduling against --dist=worksteal.
Add duration-balanced shards only if the verified backend gate stays >90s.
Preserve test coverage and production live-resolution behavior.
M-013 branch-policy repair and all cloud mutations remain founder-gated.
Safe to clear: yes — main is clean and the next benchmark is reproducible.
```

## Pointer

- Merged target: PR #10 at `5d8b76b`; post-merge CI `29421304052`.
- Implementation commits on main: `5c3e2ee` and `bda710e`.
- Source audit and later lanes: `docs/repo-structure/audit-2026-07-15.md`.

## Delta

- PR #10 now persists server-derived owner provider/user IDs and scopes every
  mounted run read/mutation at both service and repository boundaries.
- Ownerless rows fail closed; startup upgrades both SQLite/Postgres and only
  backfill unambiguous legacy local owners. Duplicate review route removed.
- Focused affected sweep: 98 passed. Full backend pytest and all structural,
  frontend-contract, Ruff, Black, and diff checks passed.
- Steven chose Python 3.12; Black is pinned to `py312` with no warning.
- Thalon, Swordfish, and Eamos all use chat approval plus admin merge override;
  no second GitHub reviewer account will be added.
- Durable milestone evidence is recorded at the top of `PROGRESS.md`.

## Next Action

- Make cache tests hermetic, then benchmark xdist `--dist=worksteal`; shard only
  if the backend gate remains over 90s after the fix.
- Preserve production live-source behavior and test assertions; optimize only
  redundant network waiting and scheduling overhead.
- M-013 required-check policy and all Render/Supabase/VPS mutations remain
  separately founder-gated.
