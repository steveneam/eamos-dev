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
- **Codex:** STOPPED @ 2026-07-15 15:01 UTC — P1 search auth and the corrected
  automatic verified-slice commit/push rule are pushed in PR #12. Initial PR CI
  is green; the branch is at the explicit merge-approval gate.

## Log Edit-Lock

UNLOCKED · 2026-07-15 15:01 +0000 · Codex (PR #12 pushed; locks released)

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-15 15:01 +0000 · Codex PR 12 merge gate
Read CURRENT.md, agent_handoff/README.md, then docs/repo-structure/audit-2026-07-15.md.
PR #12 contains P1 search dual-provider auth plus the verified-slice git rule correction.
Branch: codex/p1-search-auth-principal; all owned work is pushed.
Search query/answer accept local + Supabase JWTs and retain owner-scoped filtering.
Tests cover ES256/JWKS, local compatibility, and cross-user private isolation.
The initial PR run 29425995342 is fully green; recheck the latest run before merge.
Verified scoped work now commits/pushes automatically; do not ask Steven again for that.
PR merge still requires Steven's explicit approval and a green rebased head.
The live Supabase migration, deploy hook, M-013, and all cloud mutations remain founder-gated.
Safe to clear: yes — PR #12 is pushed and the only next action is the merge gate.
```

## Pointer

- PR: `#12` from `codex/p1-search-auth-principal` into `main`.
- Implementation: `0308716`; governance correction: `0f9cc67`.
- Initial green run: `29425995342`; latest PR head must be rechecked before merge.

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

## Next Action

- Founder gate: Steven must explicitly approve merging PR #12.
- Before merge, the lead rechecks scope, rebases onto latest `main` if needed,
  waits for every required check to pass, then merges only on Steven's go.
- Do not apply the missing live Supabase migration or invoke a deploy hook in
  this lane. M-013 and all Render/Supabase/VPS mutations remain separately gated.
