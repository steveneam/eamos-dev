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
- **Codex:** STOPPED AT NEXT-SESSION/INFRA GATE @ 2026-07-19 13:08 +0000 —
  Product Workflow Wave 1 lanes B/C are clean, pushed, reviewed, and unmerged.
- **Lane B:** PR #16, `agent/product/workflow-backend@7a19b40`. All required
  local tests/guards and Vercel are green. Actions run `29688114049` rejected
  every job before any step because account billing/spending blocked execution.
- **Lane C:** PR #17, `agent/product/surface-flow@389bab1`. All required local
  tests/guards, responsive/authenticated browser evidence, and Vercel are green.
  Actions run `29687949192` has the same zero-step account-billing failure.
- **Merge gate:** Steven approved the minimal Workbench design-binding contract
  re-plan at 13:08 +0000 and directed that it start next session; no re-plan
  edits have begun. Restore Actions billing and obtain green required runs,
  then review/rebase B and pause for Steven's explicit merge approval. Never
  merge on red.
- **Task F:** no remote migration has been applied. It remains a separate,
  fresh founder-approved Supabase mutation checkpoint after B merges and before
  C can merge. Merge order remains B → Task F → C.
- **Phase-3c soak:** recovery window active from `2026-07-19T01:46:12Z` after
  a 7h15 shared-edge outage. Recovery middle is due around/after 2026-07-20
  01:46 UTC; earliest end is around/after 2026-07-21 01:46 UTC. Render remains
  live as rollback; do not close/cancel it.
- **Evidence expansion:** Phases 0-6 are complete. Source acquisition or
  materialization, live providers, new-ruleset activation, and Phase 7 remain
  held behind their existing gates.

## Log Edit-Lock

UNLOCKED · 2026-07-19 13:09 +0000 · Codex

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-19 13:08 +0000 · Codex Workbench contract re-plan approved
Read CURRENT.md, COORDINATION.md, and plans/product-workflow-integration/{plan,spec}.md first.
If Phase-3c recovery-middle is due around/after 2026-07-20 01:46 UTC, run it first.
Lane B: PR #16 at 7a19b40; Lane C: PR #17 at 389bab1; both clean, pushed, and Vercel green.
GitHub Actions did not start because account billing/spending limits rejected every job; restore billing and rerun both, never merge red.
Steven approved the minimal Workbench design-binding contract re-plan; begin it now as the next-session task.
Freeze the smallest schema/TS/canary amendment binding build, reference basis, edit revision, and context digest before implementation resumes.
After green CI and the verified contract amendment, lead rebases/reviews B and pauses for Steven's explicit merge approval.
Only after B merges, present the filled Task F migration mutation template and wait for fresh confirmation.
C remains downstream of a successful Task F checkpoint; do not merge it early.
No remote Supabase/cloud/deploy/provider/source/Phase-7 action is authorized.
Preserve Render rollback and watcher-owned FROM-SWORDFISH.md.
```

## Pointer

- Audit/contract/launch package: `plans/product-workflow-integration/`.
- Lane B: PR #16, `agent/product/workflow-backend@7a19b40`, worktree
  `.claude/worktrees/product-workflow-backend`.
- Lane C: PR #17, `agent/product/surface-flow@389bab1`, worktree
  `.claude/worktrees/product-surface-flow`.
- Local-only migration: `supabase/migrations/20260719113620_product_workflow_runs.sql`.
- Approval receipt: `docs/governance/decisions.md` (2026-07-19 Workbench re-plan).
- Task F runbook: `docs/architecture-consistency-gate/task-f-supabase-production-readiness-runbook.md`.
- Phase-3c recovery timing, evidence, and exit contract:
  `docs/deployment/render-to-syd2-phase3.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Lane B delivered owner-scoped durable Batch/Paper/Workbench lifecycle,
  paging/export/cancel/delete/expiry behavior, JWT issuer validation, Library
  v2 tombstone merging, whole-gene fail-closed locus handling, and local-only
  migration/schema support.
- Lead security review added ASGI Paper cancellation finalization and bounded
  compare-and-swap retries that preserve concurrent Library tombstones.
- Lane C delivered authenticated Paper disclosure/extraction, Report/Paper/
  Batch/Library handoffs and responsive product states. Lead security review
  neutralized spreadsheet formulas in Paper TSV exports.
- Steven approved the minimal contract re-plan that will bind Workbench design
  requests to build/reference basis, edit revision, and context digest. He
  directed that it start next session; no contract edits have begun.
- Both PRs passed their complete local verification and Vercel checks. GitHub
  Actions failures are infrastructure-only zero-step billing rejections, not
  executed-test failures; they still block merge.
- No cloud, deploy, provider, source, Phase-7, Supabase-link, or remote migration
  action occurred. No merge occurred. Render remains the live rollback.

## Next Action

- On the next `gogogo`, run the recovery-middle sample first if due; otherwise
  begin the approved minimal Workbench design-binding contract re-plan. Keep B/C
  unmerged while the amendment is frozen and locally verified. Steven restores
  Actions billing and reruns both PRs before B's serialized merge gate; Task F
  remains a later, separate mutation approval.
