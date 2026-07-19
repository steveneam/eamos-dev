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
- **Codex:** DONE @ 2026-07-19 09:48 +0000 — recorded Steven's Product Workflow
  V1/five-lane approval and reconciled Supabase with the established serialized
  lane-author/lead-apply convention. No implementation or cloud mutation ran.
- **Product-workflow sprint:** APPROVED. Next `gogogo` launches Lane A only,
  after the recovery sample if due. Lane B may author/test its migration; the
  lead performs the post-merge Task F application checkpoint. Every merge still
  waits for Steven's explicit approval and green required CI.
- **Phase-3c soak:** recovery window active from `2026-07-19T01:46:12Z` after
  a 7h15 shared-edge outage. Recovery middle is due around/after 2026-07-20
  01:46 UTC; earliest end is around/after 2026-07-21 01:46 UTC. Render remains
  live as rollback; do not close/cancel it.
- **GitHub Actions:** clarification run `29681846578` for `b9af5a8` failed; all seven
  failed jobs had zero steps, consistent with the known minute lock. Steven
  ruled no additional spend; required CI waits for monthly renewal.
- **Evidence expansion:** Phases 0-6 are complete. Source acquisition or
  materialization, live providers, new-ruleset activation, and Phase 7 remain
  held behind their existing gates.
- **Runtime:** persistent `eamos` tmux under `agent-tmux.service` remains the
  execution seam.

## Log Edit-Lock

UNLOCKED · 2026-07-19 09:48 +0000 · Codex

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-19 09:48 +0000 · Codex launch Product Workflow Lane A
Read CURRENT.md, peer mail, and plans/product-workflow-integration/{research,spec,plan}.md first.
If the Phase-3c recovery-middle sample is due (around/after 2026-07-20 01:46 UTC), run it before sprint work.
Delta: Steven approved Product Workflow V1, all five lanes, and Lane B migration authoring; Supabase follows the existing lane-author/lead-apply Task F convention.
Launch Lane A only with plan.md's Wave-0 command and Lane A kickoff prompt.
Implement only the frozen Pydantic/TypeScript contract and canaries in Lane A's owned paths; commit/push/PR, but never merge.
Do not fork B/C until A is reviewed, CI-green, explicitly merge-approved, merged, and verified on main.
Lane B never mutates remote Supabase; after its merge the lead presents Task F's exact eamos-dev mutation card, applies once if approved, then runs advisors/smokes.
Preserve all unrelated cloud/deploy/provider/source/Phase-7 holds, Render rollback, the CI-green merge gate, and the watcher-owned dirty inbox.
```

## Pointer

- Audit, contract, and launch package: `plans/product-workflow-integration/`
  (`research.md`, `spec.md`, and `plan.md`).
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
- Whole-gene clarification `b9af5a8`; CI `29681846578` (zero-step minute lock).
- Phase-3c recovery timing, evidence, and exit contract:
  `docs/deployment/render-to-syd2-phase3.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Steven approved the frozen V1 contract, five-lane ownership/merge order, and
  Lane B local migration authoring on 2026-07-19.
- The contract includes canonical variant/context/selection, disclosure,
  workflow run/artifact, related/curated variants, URLs, and async states.
- Whole gene spans every exon, intervening intron, and UTR; a distant-exon
  selection/edit must feed Primer without replacing or cropping the locus.
- The Mode B sprint is A contract → B backend and C surface flow in parallel → D
  Workbench → E ratchets, with one web writer per wave and serialized delivery
  order A→B→Task F apply→C→D→E.
- Supabase is not deferred: Lane B authors/tests; after its merge the lead uses
  Task F to reconcile the remote ledger, obtain exact apply approval, mutate
  `eamos-dev` once, run advisors/two-user smokes, and update the inventory.
- Known preflight issue: July's read-only audit found local/remote migration-name
  drift and the repo's `user_library` migration absent remotely; never blind-push.
- No application, lane, cloud, deploy, Supabase, source, or Phase-7 mutation ran
  while recording this approval.
- Evidence expansion Phases 0-6 remain complete; Phase 7 and all source/live
  activations remain held.
- The clean Phase-3c recovery clock remains `2026-07-19T01:46:12Z`; Render is
  still live as rollback.
- Swordfish's watcher-owned inbox remains dirty and was neither edited nor
  staged by Codex.

## Next Action

- Run the recovery-middle sample first if its 2026-07-20 01:46 UTC floor has
  passed. Otherwise launch Lane A only using the exact Wave-0 command and kickoff
  prompt in `plans/product-workflow-integration/plan.md`; drive it through
  commit/push/PR/CI review, then pause for Steven's explicit merge approval.
