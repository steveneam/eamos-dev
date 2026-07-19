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
- **Codex:** DONE @ 2026-07-19 11:14 +0000 — repository-local fonts are on
  `main@a79d08b`; the offline-constrained local build and Vercel production
  passed, and no GitHub Actions run started.
- **Product-workflow sprint:** Lane A is complete. B/C are dependency-unblocked
  but not launched; every later lane and Task F remote mutation retains its
  separate gate.
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

UNLOCKED · 2026-07-19 11:14 +0000 · Codex

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-19 11:14 +0000 · Codex after local-font resilience
Read CURRENT.md, commit a79d08b, and plans/product-workflow-integration/plan.md first.
If the Phase-3c recovery-middle sample is due (around/after 2026-07-20 01:46 UTC), run it first.
Delta: a79d08b vendors the exact Inter/Spectral/IBM Plex Mono Latin files and licenses; builds no longer fetch Google Fonts.
Font gate: web 193/193, type, lint, boundary, dead-proxy production build, and real Vercel production all passed; Actions skipped.
Lane A remains complete at 6d2f6c9; B/C are unblocked but not launched, and neither manual exception applies to later lanes.
Docker remains unavailable, but neither completed slice changed a container path.
Preserve all cloud/deploy/provider/source/Phase-7 holds, Render rollback, Task F gate, and the watcher-owned dirty inbox.
```

## Pointer

- Audit/contract/launch package: `plans/product-workflow-integration/`.
- Lane A: `main@6d2f6c9`; retained manual/original branches and worktree; PR #15
  closed. Their cleanup requires explicit authority.
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

- `a79d08b` replaces `next/font/google` with `next/font/local` and commits seven
  exact Latin WOFF2 assets (about 128 KB) for Inter 400–700, Spectral 400–700,
  and IBM Plex Mono 400/500 with their family-specific SIL OFL 1.1 notices.
- Existing `--display`, `--body`, and `--mono` variables, weights, upright style,
  `display: swap`, preload behavior, and system fallback stacks remain intact.
- The font slice passed web 193/193, TypeScript, ESLint, the 275-file boundary,
  diff-check, and a full production build with HTTP(S) forced through a dead
  local proxy. The production manifest contains exactly the seven local files.
- Exact commit `a79d08b` is on `origin/main`; Actions did not start and Vercel
  production deployment `HoZVc4nrJARWYRvJ6ZQdvyxeSTvo` passed.
- Steven's font-only manual approval is separate from the Lane A exception and
  does not waive any later-lane CI, review, or merge requirement.
- Lane A's schema-first contract, TypeScript mirror, negative security canaries,
  and full manual substitute are complete on `origin/main@6d2f6c9`; PR #15 is
  closed and the one-time exception remains recorded in the ledger/plan/board.
- This host has no Docker executable. Neither Lane A nor the font slice changed
  Docker/container paths; the former Google Fonts build blocker is now removed.
- No later lane, cloud, deploy, Supabase, provider, source, or Phase-7 mutation ran.
- A generated 895 MB recovery copy remains at
  `/tmp/eamos-product-contract-v1-node_modules-20260719T0953Z` pending explicit
  cleanup authority.
- Evidence expansion Phases 0-6 remain complete; Phase 7/source/live activations
  stay held. Phase-3c's clock remains `2026-07-19T01:46:12Z`; Render stays live.
- Swordfish's watcher-owned inbox remains dirty and was neither edited nor
  staged by Codex.

## Next Action

- Run the recovery-middle sample first if due. Otherwise begin the next approved
  Product Workflow implementation mode from verified `main@a79d08b`; do not
  infer a later-lane CI waiver or cross any Task F/cloud/deploy gate.
