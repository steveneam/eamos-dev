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
- **Codex:** STOPPED @ 2026-07-15 15:08 UTC — Steven approved PR #12; it is
  rebase-merged at `dfc83cb`, post-merge implementation CI is green, and no
  cloud mutation or deploy was performed. Next is the read-only `user_library`
  migration preflight.

## Log Edit-Lock

UNLOCKED · 2026-07-15 15:08 +0000 · Codex (PR #12 merge recorded)

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-15 15:08 +0000 · Codex user-library migration preflight
Read CURRENT.md, agent_handoff/README.md, then docs/repo-structure/audit-2026-07-15.md.
PR #12 is rebase-merged at dfc83cb; post-merge run 29426486423 is green.
Search now accepts local + Supabase JWTs with owner-scoped filtering intact.
Verified scoped work commits/pushes automatically; do not ask Steven again for that.
Start the read-only missing user_library preflight from the audit and migration SQL.
Reconfirm live table absence and migration-ledger identity; run only bounded read-only smokes.
Review SQL and produce rollback plus verification steps before proposing an apply.
Applying the migration, invoking a deploy hook, M-013, and all cloud mutations remain founder-gated.
Safe to clear: yes — main is clean, PR #12 is merged, and the next preflight is read-only.
```

## Pointer

- Merged target: PR #12 at `dfc83cb` on `main`.
- Rebased commits: implementation `ea189ee`; governance correction `0329a5a`.
- Final PR run `29426282277` and post-merge run `29426486423` are green.

## Delta

- `GET /api/v1/search` and `POST /api/v1/search/answer` accept local and
  signature-verified Supabase principals; rate limiting and owner filtering
  still derive from the authenticated principal's server-side user ID.
- The new Supabase route test failed 401 before the change, then passed through
  ES256/JWKS verification; local compatibility and cross-user isolation pass.
- Full backend: 1,628 passed / 20 skipped (1,648 total). Ruff and Black pass.
- Boundary/frontend-contract: 369 passed; web boundary, ESLint, TypeScript,
  production build, and local Next-proxy-to-FastAPI HTTP smoke pass.
- PR CI passed both backend shards, the stable aggregator, web, frontend, and
  Vercel preview. Exact timings and non-mutation scope are in `PROGRESS.md`.
- Eamos now matches Thalon/Swordfish: verified scoped work commits and pushes
  without repeat permission; merge and hazardous actions remain gated.
- No deploy hook or Supabase mutation ran; the live signed-in search smoke and
  missing `user_library` apply remain separate gated operations.

## Next Action

- Perform the read-only `user_library` preflight: reconcile local/remote
  migration identity, confirm the live table state, review the SQL, and write
  rollback plus bounded verification steps.
- Stop for Steven's explicit approval before applying any migration or invoking
  a deploy hook. M-013 and all Render/Supabase/VPS mutations remain gated.
