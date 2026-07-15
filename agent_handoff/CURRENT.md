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
- **Codex:** REVIEW @ 2026-07-15 13:49 UTC — lead for PR #10, the verified
  serial P0 run/report object-authorization gate. CI watch is active; merge is
  paused for Steven's explicit approval. No deploy or cloud mutation authorized.

## Log Edit-Lock

UNLOCKED · 2026-07-15 13:50 +0000 · Codex (PR-10 handoff reconciled; locks released)

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-15 13:49 +0000 · Codex PR-10 review
Read CURRENT.md, agent_handoff/README.md, then audit-2026-07-15.md.
Branch codex/p0-run-report-authorization; PR #10 is open against main.
P0 now stores and enforces (provider, user_id) owners for reports/runs,
adds fail-closed legacy upgrades/backfill, and proves two-user denials.
Commits: bb37345 security gate; 97c6e00 Black py312 pin.
Full backend pytest, Ruff/Black, contract and boundary guards passed locally.
Python stays on 3.12 by Steven's direction; 3.15 beta was not adopted.
Check PR #10 CI/review; fix red only. Do not merge without Steven approval.
After approved merge, run post-merge verification, then start backend CI work.
Safe to clear: yes — branch pushed, PR open, worktree handoff only.
```

## Pointer

- Review target: PR #10, `codex/p0-run-report-authorization` → `main`.
- Implementation commits: `bb37345` and `97c6e00`.
- Source audit and later lanes: `docs/repo-structure/audit-2026-07-15.md`.

## Delta

- PR #10 persists server-derived owner provider/user IDs and scopes every
  mounted run read/mutation at both service and repository boundaries.
- Ownerless rows fail closed; startup upgrades both SQLite/Postgres and only
  backfill unambiguous legacy local owners. Duplicate review route removed.
- Focused affected sweep: 98 passed. Full backend pytest and all structural,
  frontend-contract, Ruff, Black, and diff checks passed.
- Steven chose Python 3.12; Black is pinned to `py312` with no warning.
- Durable milestone evidence is recorded at the top of `PROGRESS.md`.

## Next Action

- Watch PR #10 checks, inspect scope, and resolve only genuine red findings.
- Pause for Steven's explicit approval before merge; never merge on red.
- After merge, verify `main`, then make cache tests hermetic and benchmark
  xdist `--dist=worksteal`; shard only if the backend gate remains over 90s.
- M-013 required-check policy and all Render/Supabase/VPS mutations remain
  separately founder-gated.
