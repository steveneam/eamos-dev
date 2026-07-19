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
- **Codex:** RUNNING @ 2026-07-19 11:24 +0000 — leading Product Workflow Wave 1.
  Lane B owns backend/persistence and Lane C owns the disjoint Next.js surface
  flow; both start from current `origin/main@3f0a081`.
- **Product-workflow sprint:** Lane A is integrated at `6d2f6c9`; B/C are
  launching in separate worktrees under the frozen V1 contract. Merge order is
  B → gated Task F apply → C; no lane may merge itself or mutate Supabase.
- **Phase-3c soak:** recovery window active from `2026-07-19T01:46:12Z` after
  a 7h15 shared-edge outage. Recovery middle is due around/after 2026-07-20
  01:46 UTC; earliest end is around/after 2026-07-21 01:46 UTC. Render remains
  live as rollback; do not close/cancel it.
- **GitHub Actions:** old run `29683028720` remains failed with seven zero-step
  jobs. Commits `6d2f6c9` and `a79d08b` used `[skip ci]` under two separately
  recorded per-instance approvals; neither is a blanket bypass.
- **Evidence expansion:** Phases 0-6 are complete. Source acquisition or
  materialization, live providers, new-ruleset activation, and Phase 7 remain
  held behind their existing gates.

## Log Edit-Lock

UNLOCKED · 2026-07-19 11:26 +0000 · Codex

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-19 11:24 +0000 · Codex Product Workflow Wave 1 launch
Read CURRENT.md, COORDINATION.md, and plans/product-workflow-integration/plan.md first.
If the Phase-3c recovery-middle sample is due (around/after 2026-07-20 01:46 UTC), run it first.
Wave 1: Lane B backend/persistence and Lane C surface-flow run in disjoint worktrees from origin/main@3f0a081.
Lane A's schemas/backend.ts contract is frozen; stop for re-plan rather than editing it.
No lane links or mutates Supabase; Task F remains a post-B-merge founder-approved lead checkpoint.
Each lane must commit/push/open a PR and stop at review; later-lane CI has no manual waiver.
Preserve all cloud/deploy/provider/source/Phase-7 holds, Render rollback, Task F gate, and the watcher-owned dirty inbox.
```

## Pointer

- Audit/contract/launch package: `plans/product-workflow-integration/`.
- Wave 1 branches/worktrees: `agent/product/workflow-backend` at
  `.claude/worktrees/product-workflow-backend` and
  `agent/product/surface-flow` at `.claude/worktrees/product-surface-flow`.
- Lane A: integrated at `6d2f6c9`; retained manual/original branches and
  worktree require explicit cleanup authority.
- Local-font provenance, hashes, and licenses: `app/web/app/fonts/README.md`.
- Approval receipts: `docs/governance/decisions.md` (2026-07-19 decisions).
- Supabase convention:
  `docs/architecture-consistency-gate/task-f-supabase-production-readiness-runbook.md`;
  durable target/ledger inventory: `docs/db/supabase-inventory.md`.
- P0s: Paper omits required bearer auth; Batch leaves orphaned plaintext upload
  snapshots; Workbench overflows/clips at 390px.
- Whole-gene acceptance: variant is initial focus only; the continuous locus
  includes all exons/introns/UTRs and a distant selection must feed Primer.
- Approved plan/Supabase rollout `5bd4d28`; both manual exceptions are recorded
  separately in `docs/governance/decisions.md`.
- Phase-3c recovery timing, evidence, and exit contract:
  `docs/deployment/render-to-syd2-phase3.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Current `main` is `3f0a081`; Lane A's frozen contract and the local-font
  resilience slice are both present.
- Steven's `gogogo` supplies the fresh Wave 1 launch approval required by the
  active handoff; B/C remain bounded by their exact plan globs and frozen seam.
- Lane B is secure implementation mode: remove the Batch snapshot leak, add
  owner-scoped durable lifecycle/migration behavior, validate JWT issuer, and
  harden Workbench service boundaries with executable negative tests.
- Lane C owns Paper auth/disclosure plus Report/Batch/Library handoffs and UI
  states; it may run concurrently but cannot merge before B and Task F.
- No cloud, deploy, provider, source, Phase-7, Supabase-link, or remote migration
  action is part of either lane. Render remains the live rollback.
- The retained Lane A worktree/branches, 895 MB recovery copy, and watcher-owned
  dirty inbox are untouched and require their existing separate authorities.

## Next Action

- Complete B/C to separate verified, committed, pushed PR-review boundaries.
  Lead-review B first and pause for Steven's explicit merge approval; Task F and
  C merge remain downstream gates.
