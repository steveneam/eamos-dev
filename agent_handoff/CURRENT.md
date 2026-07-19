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
- **Codex:** DONE @ 2026-07-19 10:57 +0000 — Lane A is integrated on `main` as
  `6d2f6c9`; local substitute, preview/production Vercel, and current-main smokes
  passed. Actions did not run and superseded PR #15 is closed.
- **Product-workflow sprint:** Lane A is complete. B/C are dependency-unblocked
  but not launched; every later lane and Task F remote mutation retains its
  separate gate.
- **Phase-3c soak:** recovery window active from `2026-07-19T01:46:12Z` after
  a 7h15 shared-edge outage. Recovery middle is due around/after 2026-07-20
  01:46 UTC; earliest end is around/after 2026-07-21 01:46 UTC. Render remains
  live as rollback; do not close/cancel it.
- **GitHub Actions:** old run `29683028720` remains failed with seven zero-step
  jobs. Commit `6d2f6c9` used `[skip ci]`; no Actions job or spend ran. Steven's
  approval was Lane-A-only, not a blanket bypass.
- **Evidence expansion:** Phases 0-6 are complete. Source acquisition or
  materialization, live providers, new-ruleset activation, and Phase 7 remain
  held behind their existing gates.
## Log Edit-Lock

UNLOCKED · 2026-07-19 10:57 +0000 · Codex

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-19 10:57 +0000 · Codex Product Workflow after Lane A
Read CURRENT.md, commit 6d2f6c9, and plans/product-workflow-integration/plan.md first.
If the Phase-3c recovery-middle sample is due (around/after 2026-07-20 01:46 UTC), run it first.
Delta: Lane A is on main at 6d2f6c9; local substitute + preview/prod Vercel + current-main smokes passed, Actions skipped, PR #15 closed.
Docker was unavailable locally and Google Fonts blocked the pre-push local build; neither is recorded as passed.
Lane A's exception does not automatically apply to later lanes; B/C are unblocked but not launched.
Before the next implementation run, follow Steven's chosen sequential/manual or existing lane workflow explicitly.
Preserve all cloud/deploy/provider/source/Phase-7 holds, Render rollback, Task F gate, and the watcher-owned dirty inbox.
```

## Pointer

- Audit/contract/launch package: `plans/product-workflow-integration/`.
- Lane A: `main@6d2f6c9`; retained manual/original branches and worktree; PR #15
  closed. Their cleanup requires explicit authority.
- Approval receipt: `docs/governance/decisions.md` (2026-07-19 decision).
- Supabase convention:
  `docs/architecture-consistency-gate/task-f-supabase-production-readiness-runbook.md`;
  durable target/ledger inventory: `docs/db/supabase-inventory.md`.
- P0s: Paper omits required bearer auth; Batch leaves orphaned plaintext upload
  snapshots; Workbench overflows/clips at 390px.
- Whole-gene acceptance: variant is initial focus only; the continuous locus
  includes all exons/introns/UTRs and a distant selection must feed Primer.
- Approved plan/Supabase rollout `5bd4d28`; Lane A manual exception is recorded
  in `docs/governance/decisions.md`.
- Phase-3c recovery timing, evidence, and exit contract:
  `docs/deployment/render-to-syd2-phase3.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Lane A added the frozen canonical variant/context/selection, processing,
  run/artifact, related/curated, URL, and async contracts schema-first, mirrored
  in TypeScript with exact enum/required/nullability canaries.
- Secure-implementation review added negative tests for unknown client fields,
  unsafe/sensitive return paths, decoded controls, mismatched variant/selection/
  report targets, unsafe filenames/digests, and cross-run artifacts. No confirmed
  vulnerability remains in the inspected Lane A contract scope.
- Manual substitute passed focused and both full backend shards, web 193/193,
  TypeScript, ESLint, Black, Ruff, pip audit, the configured high-severity npm
  audit gate, frontend boundary 275 files, coordination 9/9, and diff-check.
- This host has no Docker executable. Local Next compilation was blocked only by
  Google Fonts timeouts; fresh preview and production Vercel builds passed.
- Steven's one-time Lane A override is recorded in the decision ledger, plan,
  and board. It does not relabel the zero-step Actions run as green.
- Exact commit `6d2f6c9` is on `origin/main`; current-main contract/web/structural
  smokes passed, Actions did not run, and superseded PR #15 is closed.
- No later lane, cloud, deploy, Supabase, provider, source, or Phase-7 mutation ran.
- The repository's worktree install ratchet rejected the plan's stale lane-local
  `npm ci`; Codex restored the intended shared dependency link without deleting
  the generated 895 MB recovery copy, now at
  `/tmp/eamos-product-contract-v1-node_modules-20260719T0953Z` pending explicit
  cleanup authority.
- Evidence expansion Phases 0-6 remain complete; Phase 7 and all source/live
  activations remain held.
- The clean Phase-3c recovery clock remains `2026-07-19T01:46:12Z`; Render is
  still live as rollback.
- Swordfish's watcher-owned inbox remains dirty and was neither edited nor
  staged by Codex.

## Next Action

- Run the recovery-middle sample first if due. Otherwise begin the next approved
  Product Workflow implementation mode from verified `main@6d2f6c9`; do not
  infer a later-lane CI waiver or cross any Task F/cloud/deploy gate.
