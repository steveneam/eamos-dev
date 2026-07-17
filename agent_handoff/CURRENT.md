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
- **Codex:** STOPPED @ 2026-07-17 07:39 +0000 — explicit CLI-maintenance and
  peer-mail-intake session only. Global Codex moved from `0.144.4` to stable
  `0.144.5`; version and help smokes passed. Swordfish's inbound was read and
  locally acknowledged. No product code, cloud, provider, source-materialization,
  migration, environment, or deploy mutation was performed.

## Log Edit-Lock

UNLOCKED · 2026-07-17 07:40 +0000 · Codex

## Shared File Locks

- None. Codex released the handoff lock at 2026-07-17 07:40 +0000 after the
  verified CLI update and read-only Swordfish intake.

## Resume Prompt

```text
# Resume prompt · 2026-07-17 07:39 +0000 · Codex CLI maintenance / Swordfish intake
Read CURRENT.md, README.md, CLAUDE.md, ROADMAP.md, and plans/variant-report-experience/plan.md.
Codex CLI is globally updated from 0.144.4 to stable 0.144.5; version/help smokes are green.
Swordfish Phase 1 is green; Phase 3, cutover, provider, Render, and cleanup gates remain held.
Before any bulk seed, prove peak transient disk use; 81 GiB cannot fit a 2x 41 GiB staging pass.
Local lanes are frontend 3532 and backend 8532; no repository port change has been made.
Next, resume the read-only representative variant report matrix unless Steven redirects explicitly.
Never edit or stage FROM-SWORDFISH.md.
Do not bulk-seed or mutate Supabase, providers, cloud, migrations, deploys, or env.
```

## Pointer

- Current roadmap: `ROADMAP.md`; next cycle is Report evidence and runtime
  closure.
- Completed presentation record: `plans/variant-report-experience/plan.md` and
  the 2026-07-16 15:44 entry in `PROGRESS.md`.
- Swordfish's latest inbound records the green Phase 1 proof, held migration
  gates, peak-disk question, and frontend/backend port lanes.
- Watcher-owned `agent_handoff/FROM-SWORDFISH.md` may be dirty; never edit or
  stage it.

## Delta

- `/usr/bin/codex` and global package `@openai/codex` now resolve to stable
  `0.144.5`; `codex --version` and `codex --help` both exit cleanly.
- Swordfish's ClinGen one-off pipe proof met the Phase 1 checksum, schema,
  manifest, isolation, and cleanup criteria. Later migration phases remain held.
- The next migration prerequisite is a read-only peak-transient-disk proof.
  Swordfish also assigned frontend `3532` and backend `8532`; neither port is
  adopted in repository code yet.

## Next Action

- Run a read-only representative-variant matrix across all seven report
  sections, distinguish source absence from presentation defects, and recommend
  the smallest evidence/runtime closure slice. Keep every cloud, provider,
  materialization, migration, environment, and deploy gate closed; if Steven
  redirects to port adoption or migration planning, treat that as a new bounded
  slice.
