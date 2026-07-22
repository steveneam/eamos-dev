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
- **Codex:** STOPPED AT TASK F EXACT-MUTATION GATE @ 2026-07-22 14:30 +0000.
- **Serial contract + backend:** PR #18 merged as `55300f4`; PR #16 merged as
  `5c5a950`. Their PR and post-merge `main` CI runs passed every backend shard,
  web/type/lint/build, structural/coordination guard, dependency audit,
  container contract, Vercel, and immutable-image publication.
- **Lane C:** PR #17, `agent/product/surface-flow@84c8655`, is rebased onto
  `5c5a950`, mergeable, and fully green including dependency security and
  Vercel. Steven pre-approved the code merges, but C remains held behind the
  successful Task F checkpoint.
- **Task F:** no remote migration was applied. Read-only `eamos-dev`
  (`cpdjxsgasaesysvxkpmi`) inventory confirms both `user_library` and the two
  `product_workflow_*` tables are absent; the migration ledger ends at the two
  variant-library migrations, security advisors are clear, the source bucket
  remains private, and performance findings are informational unused indexes.
  Applying the two reviewed migrations remains a separate exact mutation-card
  approval.
- **Phase 3 / Render:** Phase 3 is closed. The 13:33 UTC public end sample and
  Swordfish's independent 14:21 UTC syd2 host/container sample are green: exact
  digest and 23-file/47,943,536,945-byte tree, no restart/5xx/429/OOM/cgroup
  pressure since recovery, unchanged hardening, and healthy headroom. Phase 4
  may retire the Render rollback; no Render disk or service was deleted here.
- **Evidence expansion:** Phases 0-6 are complete. Source acquisition or
  materialization, live providers, new-ruleset activation, and Phase 7 remain
  held behind their existing gates.

## Log Edit-Lock

UNLOCKED · 2026-07-22 14:30 +0000 · Codex

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-22 14:30 +0000 · Codex Task F mutation gate
Read CURRENT.md, COORDINATION.md, and plans/product-workflow-integration/{plan,spec}.md first.
PR #18 (55300f4) and PR #16 (5c5a950) are merged with green post-merge CI and image publication.
PR #17 at 84c8655 is fully green and merge-pre-approved, but stays downstream of successful Task F.
Task F read-only inventory is captured; no remote migration has been applied.
Before mutation, present the filled exact card for eamos-dev cpdjxsgasaesysvxkpmi: user_library_document then product_workflow_runs, with rollback and redaction plan.
Only an explicit Task F Supabase mutation approval authorizes those two apply_migration calls.
After successful apply and verification, merge PR #17 under the existing code approval and verify main.
Phase 3 is closed from public plus independent host evidence; Render Phase 4 is ready, but no provider deletion was performed.
If Steven deletes Render, verify the old service/disk target and then recheck syd2/Vercel production health; deleting only the disk does not stop paid service compute.
No other cloud/deploy/provider/source/Phase-7 action is authorized.
Preserve watcher-owned FROM-SWORDFISH.md.
```

## Pointer

- Contract gate (merged): PR #18, `agent/product/contract-binding@85eb238`, worktree
  `.claude/worktrees/product-contract-binding`.
- Lane B (merged): PR #16, `agent/product/workflow-backend@824fc0d`, worktree
  `.claude/worktrees/product-workflow-backend`.
- Lane C: PR #17, `agent/product/surface-flow@84c8655`, worktree
  `.claude/worktrees/product-surface-flow`.
- Product contract/plan: `plans/product-workflow-integration/`.
- Local-only migration: `supabase/migrations/20260719113620_product_workflow_runs.sql`.
- Task F runbook:
  `docs/architecture-consistency-gate/task-f-supabase-production-readiness-runbook.md`.
- Phase-3c evidence contract: `docs/deployment/render-to-syd2-phase3.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- GitHub Actions billing is restored and jobs execute normally.
- PR #18 merged the additive Workbench design-context envelope, canonical
  cross-language digest semantics, Pydantic/TypeScript canaries, and supported
  dependency overrides; its clean clone installs with zero vulnerabilities.
- Lane B now preserves legacy whole-document Library clearing until v2 reserved
  rows appear, while keeping the v2 tombstone merge ratchet sticky. Backend
  hotspots were split without changing their APIs.
- Lane C's Compare run-output panels moved into a cohesive presentation module;
  the Impeccable product rules kept state, accessibility, and responsive
  behavior unchanged.
- PR #16 merged the durable backend and its repaired Library/structure slices;
  PR #17 is rebased and green but held behind Task F.
- Phase 3 closed on independent evidence. No remote Supabase mutation,
  Render deletion, deploy/provider/source action, or Phase 7 action occurred.

## Next Action

- Present Task F's filled exact mutation approval card. On explicit approval,
  apply `user_library_document` then `product_workflow_runs` once to the named
  `eamos-dev` project, verify ledger/tables/RLS/grants/advisors/two-owner
  isolation, then merge fully-green PR #17 and verify `main`. Phase 4 Render
  retirement is founder-performed and remains destructive; verify production
  immediately after Steven completes it.
