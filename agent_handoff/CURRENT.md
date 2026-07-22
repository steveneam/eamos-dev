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
- **Codex:** STOPPED AT PR #18 MERGE APPROVAL GATE @ 2026-07-22 14:08 +0000.
- **Serial contract gate:** PR #18 on `agent/product/contract-binding` is fully
  green: all GitHub Actions
  jobs, dependency security, Vercel, full local backend/web suites, structural
  guards, and the frontend-contract canary passed. It remains unmerged pending
  Steven's explicit approval.
- **Lane B:** PR #16, `agent/product/workflow-backend@682048b`. The Library
  legacy-replace regression and both structure-budget failures are fixed. Full
  local backend and every branch-specific CI/Vercel check pass; dependency
  security alone is red because this pre-contract branch still carries the old
  lockfile. Rebase only after #18 merges.
- **Lane C:** PR #17, `agent/product/surface-flow@fd5e4f3`. CompareClient was
  split below its structure budget without UI behavior changes. Full local web
  verification and every branch-specific CI/Vercel check pass; dependency
  security has the same pre-contract-only failure. It remains downstream of B
  and Task F.
- **Task F:** no remote migration was applied. It remains a separate, fresh
  founder-approved Supabase mutation checkpoint after B merges and before C.
- **Phase-3c recovery/end:** the 2026-07-22 13:33 UTC public sample is green
  across DNS/HTTP/TLS/headers/CORS/auth/health/provider parity, deterministic
  parse, and two production report-performance runs. Independent read-only
  host/container evidence is requested from Swordfish and still pending.
  Render remains live as rollback; no Phase 4 action occurred.
- **Evidence expansion:** Phases 0-6 are complete. Source acquisition or
  materialization, live providers, new-ruleset activation, and Phase 7 remain
  held behind their existing gates.

## Log Edit-Lock

UNLOCKED · 2026-07-22 14:08 +0000 · Codex

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-22 14:08 +0000 · Codex Product Workflow serial merge gate
Read CURRENT.md, COORDINATION.md, and plans/product-workflow-integration/{plan,spec}.md first.
PR #18 is fully green and awaits Steven's explicit merge approval.
Do not merge #18 unless Steven approves it by name; no other gate is waived.
After approval, lead merges #18, verifies main, rebases PR #16, and watches fresh CI.
PR #16 at 682048b passes every branch-specific check; only the pre-contract dependency lock is red.
Once rebased CI is fully green, pause again for Steven's explicit Lane B merge approval.
Task F remains a separate fresh Supabase mutation approval after B merges.
PR #17 at fd5e4f3 stays downstream of successful Task F; do not merge it early.
Check ASK-BACKS/FROM-SWORDFISH for the pending Phase-3c host/container evidence.
No remote Supabase/cloud/deploy/provider/source/Phase-7 or Render action is authorized.
Preserve watcher-owned FROM-SWORDFISH.md.
```

## Pointer

- Contract gate: PR #18, `agent/product/contract-binding`, worktree
  `.claude/worktrees/product-contract-binding`.
- Lane B: PR #16, `agent/product/workflow-backend@682048b`, worktree
  `.claude/worktrees/product-workflow-backend`.
- Lane C: PR #17, `agent/product/surface-flow@fd5e4f3`, worktree
  `.claude/worktrees/product-surface-flow`.
- Product contract/plan: `plans/product-workflow-integration/`.
- Local-only migration: `supabase/migrations/20260719113620_product_workflow_runs.sql`.
- Task F runbook:
  `docs/architecture-consistency-gate/task-f-supabase-production-readiness-runbook.md`.
- Phase-3c evidence contract: `docs/deployment/render-to-syd2-phase3.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- GitHub Actions billing is restored and jobs execute normally.
- PR #18 froze the additive Workbench design-context envelope, canonical
  cross-language digest semantics, Pydantic/TypeScript canaries, and supported
  dependency overrides; its clean clone installs with zero vulnerabilities.
- Lane B now preserves legacy whole-document Library clearing until v2 reserved
  rows appear, while keeping the v2 tombstone merge ratchet sticky. Backend
  hotspots were split without changing their APIs.
- Lane C's Compare run-output panels moved into a cohesive presentation module;
  the Impeccable product rules kept state, accessibility, and responsive
  behavior unchanged.
- No merge, remote Supabase mutation, cloud/deploy/provider/source action,
  Phase 4, or Phase 7 action occurred.

## Next Action

- Wait for Steven's explicit approval to merge fully-green PR #18. On approval,
  merge it as lead, verify `main`, then rebase PR #16 onto the new contract
  base and run the serialized CI/review gate. Also ingest Swordfish's pending
  Phase-3c host evidence when it arrives.
