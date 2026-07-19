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
- **Codex:** DONE/HELD @ 2026-07-19 10:17 +0000 — Product Workflow Lane A is
  committed/pushed as `bf589e8` on `agent/product/contract-v1`; PR #15 is open
  in review. Local gates and the Vercel preview passed. No merge occurred.
- **Product-workflow sprint:** Lane A is REVIEW, required-CI blocked by the
  known GitHub Actions minute lock. B/C remain dependency-held until A is
  required-CI green, explicitly merge-approved, merged, and verified on main.
  Every later merge and Task F remote mutation retains its separate gate.
- **Phase-3c soak:** recovery window active from `2026-07-19T01:46:12Z` after
  a 7h15 shared-edge outage. Recovery middle is due around/after 2026-07-20
  01:46 UTC; earliest end is around/after 2026-07-21 01:46 UTC. Render remains
  live as rollback; do not close/cancel it.
- **GitHub Actions:** PR run `29683028720` for `bf589e8` failed seven jobs with
  `steps: []` and skipped two, matching the known minute lock. Steven ruled no
  additional spend; required CI is not green and waits for monthly renewal.
- **Evidence expansion:** Phases 0-6 are complete. Source acquisition or
  materialization, live providers, new-ruleset activation, and Phase 7 remain
  held behind their existing gates.
- **Runtime:** persistent `eamos` tmux under `agent-tmux.service` remains the
  execution seam.

## Log Edit-Lock

UNLOCKED · 2026-07-19 10:19 +0000 · Codex

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-19 10:17 +0000 · Codex Product Workflow Lane A CI gate
Read CURRENT.md, PR #15, Actions run 29683028720, and plans/product-workflow-integration/plan.md first.
If the Phase-3c recovery-middle sample is due (around/after 2026-07-20 01:46 UTC), run it first.
Delta: Lane A bf589e8 is pushed/review; local gates + Vercel passed, but seven required CI jobs had zero steps under the known minute lock.
Do not merge or launch B/C while required CI is red, and do not spend to bypass the monthly lock.
When Actions renew, rebase without force-push using the plan's fresh review-branch procedure, rerun CI, review scope, then present Steven the merge card.
The 895 MB npm recovery copy in /tmp requires explicit cleanup authority; the lane uses the shared node_modules link.
Preserve all cloud/deploy/provider/source/Phase-7 holds, Render rollback, Task F gate, and the watcher-owned dirty inbox.
```

## Pointer

- Audit/contract/launch package: `plans/product-workflow-integration/`.
- Lane: `.claude/worktrees/product-contract-v1`; `agent/product/contract-v1`;
  `bf589e8`; PR #15; board: `COORDINATION.md`.
- Approval receipt: `docs/governance/decisions.md` (2026-07-19 decision).
- Supabase convention:
  `docs/architecture-consistency-gate/task-f-supabase-production-readiness-runbook.md`;
  durable target/ledger inventory: `docs/db/supabase-inventory.md`.
- P0s: Paper omits required bearer auth; Batch leaves orphaned plaintext upload
  snapshots; Workbench overflows/clips at 390px.
- Whole-gene acceptance: variant is initial focus only; the continuous locus
  includes all exons/introns/UTRs and a distant selection must feed Primer.
- Approved plan/Supabase rollout `5bd4d28`; Lane A PR CI `29683028720`
  (seven zero-step failures; required CI not green).
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
- Full local gate passed: focused + adjacent backend contract/boundary/Workbench
  tests (expected skips only), web 193/193, TypeScript, ESLint, Black, Ruff,
  frontend boundary 275 files, coordination 9/9, strict handoff lint, diff-check.
- Commit `bf589e8` is pushed and PR #15 is open. Its Vercel preview passed; Actions
  run `29683028720` confirmed the known zero-step minute lock, so no merge ran.
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

- Run the Phase-3c recovery-middle sample first if its floor has passed. Otherwise
  hold PR #15 until Actions minutes renew; then obtain a real green required-CI
  run and Steven's explicit merge approval before merging or releasing B/C.
