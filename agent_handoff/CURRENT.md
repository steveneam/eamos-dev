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

- **Claude:** STOPPED @ 2026-07-15 10:55 UTC — no active lane.
- **Codex:** COMPLETE @ 2026-07-16 08:16 UTC — Compare batch-model fold is
  pushed on synced `main`; CI and Vercel are green.

## Log Edit-Lock

RELEASED: 2026-07-16 08:16 +0000 · Codex (Compare fold verified clear-safe)

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-16 08:16 +0000 · Codex Compare batch fold
Read CURRENT.md, agent_handoff/README.md, the migration master plan, then inspect git log/status.
Main commit 7fb5459 preserves the named CompareClient route export while moving batch request,
progress, error, and issue-copy modeling into a focused, tested module.
Full web tests/lint/type/build, cross-code guards, 26 batch security tests, CI run 29482675204,
and Vercel passed. FROM-SWORDFISH.md remains watcher-owned and dirty.
The Phase-1 dry-run itself does not need Render; the mandatory live-disk manifest proof needs
read-only runtime shell/exec on the SG service, or an operator-provided raw manifest artifact.
Next, perform a read-only migration-readiness audit: confirm container UID and freeze exact
source/Render/syd2 manifest commands. Do not touch cloud, secrets, materialization, or deploy.
Safe to clear: yes — the verified code boundary is pushed and all remote checks are green.
```

## Pointer

- Main commit: `7fb5459`, `refactor(web): split compare batch lifecycle model`.
- CI: run `29482675204`; dependency security, both backend shards, aggregator,
  web, and frontend passed. Vercel deployment completed successfully.
- Local: 160 web tests, lint, TypeScript, production build, cross-code guards,
  and 26 focused backend batch tests passed.
- Worktree: only `agent_handoff/FROM-SWORDFISH.md` is modified; it is
  watcher-owned and was not staged, committed, or altered by this lane.

## Delta

- `CompareClient.tsx` fell from 1,323 to 1,132 lines. The 218-line
  `batchRunModel.ts` owns payload/filter adaptation and progress/error copy.
- Twelve focused model tests plus 1,200/250-line budgets protect the split.
- Security review preserved server auth, owner isolation, rate limits, upload
  bounds, and bounded Ask-Eamos scope. No confirmed vulnerability was added.
- No Render, Supabase, provider, schema, materialization, or deploy action ran.

## Next Action

- Perform the read-only Phase-1 migration-readiness audit: determine the
  container runtime UID/GID and freeze exact source-bucket, live-Render-disk,
  and syd2 manifest/diff commands. Do not execute any cloud, secret, seed,
  deploy, provider, or materialization action without its explicit gate.
