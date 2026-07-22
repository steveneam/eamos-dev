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
- **Codex:** ACTIVE @ 2026-07-22 17:06 +0000 — lead for the approved Live
  Product Completion campaign.
- **Lane D:** PR #21 merged as `ec075a8` after local/CI/Vercel and source-backed
  browser/API proof. Post-merge CI run `29940643472`, including immutable-image
  pull-back verification, passed.
- **Contract V2:** PR #22 merged as `641c0e5` after independent review, rebase,
  focused local verification, full CI, dependency audit, container contract,
  and Vercel passed.
- **Wave 1:** W/R/P are assigned to disjoint agents and B is lead-owned. All
  four launch from frozen-contract checkpoint `origin/main@0a3c980`.
- **Four-wave approval:** Steven approved Codex to continue through the four
  implementation waves and orchestrate the named worktrees/agents as
  dependencies unlock. Lead-run serialized merge review remains mandatory.
- **Production posture:** unchanged. No source materialization, live-provider,
  cloud, deploy, Supabase, or Phase-7 action occurred in this slice.

## Log Edit-Lock

UNLOCKED · 2026-07-22 18:21 +0000 · Codex

## Shared File Locks

- **Frozen Contract V2 seam:** released after verified PR #22 merge; no Wave 1
  lane may edit schemas, `backend.ts`, or the contract canaries.
- **Lane W:** held for `/root/workbench_engines`; exact `plan.md` Lane W globs.
- **Lane R:** held for `/root/report_evidence`; exact `plan.md` Lane R globs.
- **Lane P:** held for `/root/paper_deterministic`; exact `plan.md` Lane P globs.
- **Lane B:** held for Codex lead in `live-batch-wes`; exact Lane B globs.

## Resume Prompt

```text
# Resume prompt · 2026-07-22 18:18 +0000 · Codex Live Product Engine Wave
Read CURRENT.md, COORDINATION.md, and plans/live-product-completion/{research,spec,plan}.md first.
Contract V2 is merged at 641c0e5; launch W/R/P agents and lead-owned Batch from origin/main@0a3c980.
Keep schemas/backend.ts/contract canaries frozen and enforce each exact lane glob plus evidence-security invariants.
Review and merge only green in order W then R then P then B under Steven's explicit approval.
Continue into the approved serial runtime-composition and frontend waves as dependencies unlock.
Before material/source/provider/cloud/deploy/Supabase action, stop on its separately named gate and present exact evidence/cost/licence cards.
Never stage watcher-owned agent_handoff/FROM-SWORDFISH.md.
```

## Pointer

- Live campaign: `plans/live-product-completion/{research,spec,plan}.md`.
- Engine branches/worktrees: `agent/live/{workbench-engines,report-evidence,paper-deterministic,batch-wes}`
  under `.claude/worktrees/live-*`.
- Lane D record: merged PR #21; historical worktree
  `.claude/worktrees/product-workbench-canvas-review` remains non-authoritative.
- Product Workflow V1 background: `plans/product-workflow-integration/`.
- Watcher-owned `agent_handoff/FROM-SWORDFISH.md` remains dirty and untouched.

## Delta

- Merged green Contract V2 PR #22 as `641c0e5`, freezing additive execution,
  context, report, paper, panel, and WES Batch truth models plus TS parity.
- Preserved the security residual explicitly: legacy `UploadedReport` fields
  remain only for compatibility; new V2 outputs exclude raw uploads/handles.
- Unlocked the approved disjoint W/R/P/B engine wave while retaining separate
  material, source, provider, cloud, Supabase, and deployment gates.

## Next Action

- Create the four engine worktrees from the recorded frozen-contract base,
  launch W/R/P agents, and implement lead-owned Batch without crossing lane or
  material/provider/cloud gates.
