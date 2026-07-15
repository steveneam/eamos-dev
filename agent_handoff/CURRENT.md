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
- **Codex:** STOPPED @ 2026-07-15 13:06 UTC — explicit user-constrained merge
  session complete. PR #9 was rebase-merged into `main` as `a6c5671` after
  Steven's fresh approval and a green serialized gate. GitHub Actions billing
  is restored. The CI action wrappers now use their established Node-24-runtime
  `v6` majors; run `29417353081` passed backend, frontend, and web with zero
  annotations, and Vercel passed. No deploy, provider, environment, database,
  Supabase schema, asset, resize, or cancellation mutation occurred.

## Log Edit-Lock

UNLOCKED · 2026-07-15 13:07 +0000 · Codex (PR #9 merged; live state refreshed)

## Resume Prompt

```text
# Resume prompt · 2026-07-15 13:06 +0000 · Codex post-PR-9
Eamos on syd4. Read CURRENT.md, agent_handoff/README.md, then
docs/repo-structure/audit-2026-07-15.md. Check git status and recent main CI.
PR #9 is merged at a6c5671: Graphify is retired, MCP startup is hardened,
the repo audit is published, and Actions wrappers use Node-24-runtime v6.
Start the audit's serial P0 run/report object-authorization fix next.
Freeze the principal/owner contract and add two-user negative tests first.
Do not launch parallel refactor lanes until that shared contract is stable.
Supabase and Chrome MCP are healthy; Render MCP awaits RENDER_API_KEY.
Do not mutate Supabase/Render/VPS state without the recorded approval gates.
```

## Pointer

- Merged scope and CI evidence: PR #9 / Actions run `29417353081`.
- Audit and proposed later Mode B lanes:
  `docs/repo-structure/audit-2026-07-15.md`.
- Render→VPS Phase 1 contract: `agent_handoff/FROM-SWORDFISH.md` and
  `/home/deploy/work/swordfish/research/project1-asset-migration-plan-2026-07-15.md`.

## Delta

- Rebase-merged Graphify retirement, hook/package/worktree guards, Chrome MCP
  hardening, and the 2026-07-15 whole-repo audit via PR #9.
- The audit found 31 active source files over 1,000 lines versus none in
  Thalon/Swordfish, and orders P0 authorization ahead of structural refactors.
- Restored GitHub Actions capacity, upgraded `checkout`, `setup-node`, and
  `setup-python` to Node-24-runtime `v6`, and verified all CI/Vercel checks green
  with zero action annotations.
- Local verification carried by the merged gate: active Next lint/type/build;
  frozen Vite lint and 139 tests; backend Ruff/Black and 1,619 passed / 20
  skipped; boundary/structure ratchets; live Render health 200.

## Next Action

- **Serial P0:** fix run/report object authorization first; freeze the
  principal/owner contract and prove two-user cross-tenant denials before any
  auth/schema/dependency refactor lanes.
- **Founder decision still open:** M-013 aggregate required-check policy in
  `agent_handoff/NEEDS-STEVEN.md`; it does not block the P0 fix.
- **Render MCP:** Steven creates a Render API key and exports it as
  `RENDER_API_KEY` outside chat; then verify read-only access. This does not
  authorize a deploy, migration, seed, resize, or cancellation.
