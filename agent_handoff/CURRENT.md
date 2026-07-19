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
- **Codex:** ACTIVE @ 2026-07-19 09:55 +0000 — launched Product Workflow Lane A
  in `.claude/worktrees/product-contract-v1` on `agent/product/contract-v1` from
  `origin/main@4b3c130`. Backend dependencies are isolated in the lane venv;
  web dependencies are linked read-only to the main checkout.
- **Product-workflow sprint:** ACTIVE, Lane A only. Lane A owns the frozen
  Pydantic/TypeScript contract and canaries. B/C remain dependency-held until A
  is reviewed, required-CI green, explicitly approved, merged, and verified.
  Every later merge and Task F remote mutation retains its separate gate.
- **Phase-3c soak:** recovery window active from `2026-07-19T01:46:12Z` after
  a 7h15 shared-edge outage. Recovery middle is due around/after 2026-07-20
  01:46 UTC; earliest end is around/after 2026-07-21 01:46 UTC. Render remains
  live as rollback; do not close/cancel it.
- **GitHub Actions:** plan run `29682238832` for `5bd4d28` failed with seven
  zero-step jobs and two skips, matching the known minute lock. Steven ruled no
  additional spend; required CI waits for monthly renewal.
- **Evidence expansion:** Phases 0-6 are complete. Source acquisition or
  materialization, live providers, new-ruleset activation, and Phase 7 remain
  held behind their existing gates.
- **Runtime:** persistent `eamos` tmux under `agent-tmux.service` remains the
  execution seam.

## Log Edit-Lock

UNLOCKED · 2026-07-19 09:56 +0000 · Codex

## Shared File Locks

- **Codex / Lane A:** `app/backend/app/schemas/{__init__,workflow,batch,paper_variants,gene_viewer,workbench,report,variant_library}.py`,
  `app/web/lib/backend.ts`, Lane A contract canaries, and the Product Workflow
  Lane A row in `COORDINATION.md` until review handoff.

## Resume Prompt

```text
# Resume prompt · 2026-07-19 09:55 +0000 · Codex continue Product Workflow Lane A
Read CURRENT.md, peer mail, and plans/product-workflow-integration/{research,spec,plan}.md first.
Work only in .claude/worktrees/product-contract-v1 on agent/product/contract-v1.
Delta: Lane A is launched from origin/main@4b3c130; no product files are edited yet.
Implement only the frozen Pydantic/TypeScript contract and canaries in Lane A's owned paths; commit/push/PR, but never merge.
Do not fork B/C until A is reviewed, CI-green, explicitly merge-approved, merged, and verified on main.
If the recovery-middle floor passes before Lane A finishes, run that read-only sample before continuing.
Preserve all unrelated cloud/deploy/provider/source/Phase-7 holds, Render rollback, the CI-green merge gate, and the watcher-owned dirty inbox.
```

## Pointer

- Audit, contract, and launch package: `plans/product-workflow-integration/`
  (`research.md`, `spec.md`, and `plan.md`).
- Lane checkout: `.claude/worktrees/product-contract-v1`; branch:
  `agent/product/contract-v1`; live board: `COORDINATION.md`.
- Approval receipt: `docs/governance/decisions.md` (2026-07-19 Product Workflow
  V1 decision).
- Supabase convention:
  `docs/architecture-consistency-gate/task-f-supabase-production-readiness-runbook.md`;
  durable target/ledger inventory: `docs/db/supabase-inventory.md`.
- P0s: Paper omits required bearer auth; Batch leaves orphaned plaintext upload
  snapshots; Workbench overflows/clips at 390px.
- Whole-gene acceptance: variant is initial focus only; the continuous locus
  includes all exons/introns/UTRs and a distant selection must feed Primer.
- Baseline: web 193/193; focused backend 398 collected and green with expected
  skips; coordination 9/9; frontend boundary 275 tracked files and green.
- Approved plan/Supabase rollout `5bd4d28`; CI `29682238832` (zero-step lock).
- Phase-3c recovery timing, evidence, and exit contract:
  `docs/deployment/render-to-syd2-phase3.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- `gogogo` launched only Lane A at `origin/main@4b3c130`; no later lane launched.
- The repository's worktree install ratchet rejected the plan's stale lane-local
  `npm ci`; Codex restored the intended shared dependency link without deleting
  the generated 895 MB recovery copy, now at
  `/tmp/eamos-product-contract-v1-node_modules-20260719T0953Z` pending explicit
  cleanup authority.
- Evidence Security and Vibe Security are active in secure-implementation mode:
  bound untrusted nested input, reject unknown fields, allowlist same-origin
  return paths, and prove negative cases without expanding into route/auth work.
- Lane A exit is frozen: exact V1 schema parity, existing contract compatibility,
  all focused web/backend/boundary gates green, committed/pushed PR handoff, and
  no merge.
- Evidence expansion Phases 0-6 remain complete; Phase 7 and all source/live
  activations remain held.
- The clean Phase-3c recovery clock remains `2026-07-19T01:46:12Z`; Render is
  still live as rollback.
- Swordfish's watcher-owned inbox remains dirty and was neither edited nor
  staged by Codex.

## Next Action

- From the Lane A worktree, inventory current schema/contract conventions and
  run the focused baseline canaries; then implement only the frozen V1 contract,
  verify, commit/push/open the PR, and pause before merge.
