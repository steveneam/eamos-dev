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
- **Codex:** COMPLETE @ 2026-07-16 08:52 UTC — the read-only Render-to-syd2
  Phase-1 readiness verifier and runbook are pushed on green `main`.

## Log Edit-Lock

UNLOCKED · 2026-07-16 08:52 +0000 · Codex (migration-readiness slice clear-safe)

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-16 08:52 +0000 · Codex migration readiness
Read CURRENT.md, agent_handoff/README.md, the migration master plan, then inspect git log/status.
Main commit 7e965ec adds a read-only source/runtime manifest verifier and exact Phase-1 runbook.
Live source proof is green for 35 objects / 43,500,288,345 bytes; no large object was downloaded.
The current image declares root 0:0; live Render id and the raw disk manifest remain unobserved.
The syd2 .drill canary requires an isolated runtime subtree; Swordfish guidance is requested.
CI run 29484848897 and Vercel passed. FROM-SWORDFISH.md remains watcher-owned and dirty.
Next, read any Swordfish reply, then obtain an authenticated operator capture of live Render id
and the raw manifest before running the content comparison. No seed, upload, deploy, or mutation.
Safe to clear: yes — the verified slice is pushed, remote checks are green, and locks are released.
```

## Pointer

- Main commit: `7e965ec`, `feat(ops): add migration manifest verifier`.
- CI: run `29484848897`; dependency security, both backend shards, aggregator,
  web, and frontend passed. Automatic Vercel production status is successful.
- Runbook: `docs/deployment/render-to-syd2-phase1.md`; exact source, Render,
  comparison, identity, and syd2 harness commands are frozen there.
- Swordfish asks: `agent_handoff/ASK-BACKS-FOR-SWORDFISH.md` requests numeric
  `deploy` UID/GID, the isolated runtime subtree, and artifact-routing guidance.
- Worktree: only `agent_handoff/FROM-SWORDFISH.md` is modified; it is
  watcher-owned and was not staged, committed, or altered by this lane.

## Delta

- The private bucket reconciled 35/35 objects and 40.513 GiB using list/head
  plus 628,449 bytes of small-object reads; manifest SHA-256 is recorded.
- The verifier fails closed on checksum/size authority disagreement and flags
  any runtime-only content identity despite different source/runtime paths.
- Current Docker identity is statically root `0:0`. Live identity, the raw
  Render manifest, current-cycle egress headroom, and the ClinGen dry run remain
  explicit Phase-1 gates.
- `/srv/project1/assets/runtime` is proposed so Swordfish's required `.drill`
  exclusion canary remains outside the exact application-tree diff.
- Full backend tests, Ruff/Black, package ratchets, Next build, local FE-to-BE
  proxy smoke, and the Swordfish manifest harness self-test passed.
- No Render, Supabase, syd2, provider, schema, seed, materialization, or deploy
  hook action ran.

## Next Action

- Read any Swordfish reply, then obtain explicit authenticated operator access
  or an operator-provided artifact for the live Render `id` and raw disk
  manifest. Run the committed content comparison only after validating the
  artifact checksum. Do not seed, upload, deploy, resize, change providers, or
  mutate Render, Supabase, or syd2 without the applicable explicit gate.
