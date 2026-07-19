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
- **Codex:** EVIDENCE EXPANSION PHASE 6 COMPLETE @ 2026-07-19 08:39 +0000 —
  the bounded code-only ruleset hardening passed full local verification.
- **Phase-3c soak:** recovery window active from `2026-07-19T01:46:12Z` after
  a 7h15 shared-edge outage. Recovery middle is due around/after 2026-07-20
  01:46 UTC; earliest end is around/after 2026-07-21 01:46 UTC. Render remains
  live as rollback; do not close/cancel it.
- **GitHub Actions:** Phase-3 run `29675375104` failed with zero steps/logs,
  consistent with the known minute lock. Steven ruled no additional spend;
  commit/push continues, but required CI waits for monthly renewal.
- **Evidence expansion:** Phases 0-6 are complete. Source acquisition or
  materialization, live providers, new-ruleset activation, and Phase 7 remain
  held behind their existing gates.
- **Runtime:** persistent `eamos` tmux under `agent-tmux.service` remains the
  execution seam.

## Log Edit-Lock

UNLOCKED · 2026-07-19 08:39 +0000 · Codex

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-19 08:39 +0000 · Codex Phase-6 complete
Read CURRENT.md, peer mail, PROGRESS.md, the evidence-expansion plan, and the Phase-3c runbook first.
Phase 6 ruleset hardening is complete; full npm run verify passed in 310.2 seconds.
If the recovery-middle sample is due (around/after 2026-07-20 01:46 UTC), run it first.
Before that floor, do not start Phase 7; it requires the final published standard and explicit activation gates.
Keep source acquisition/materialization, live providers, deploys, Supabase, new-ruleset activation, and SVC v4 held.
The clean soak window started at 2026-07-19T01:46:12Z; earliest closure is 2026-07-21 01:46 UTC.
Do not buy GitHub Actions minutes; required Phase-6 CI waits for monthly renewal.
Do not mutate deployments/providers/Supabase/Render or clean watcher-owned files.
```

## Pointer

- Phase-6 implementation and verification receipt: top `PROGRESS.md` entry and
  `plans/evidence-source-expansion/plan.md`.
- Phase-6 backend: `app/backend/app/services/acmg_points_engine.py`,
  `acmg_policy_registry.py`, `functional_assay_validation.py`, and
  `app/backend/app/schemas/run.py`.
- Phase-6 web mirror/instruments: `app/web/lib/backend.ts`,
  `app/web/lib/acmg/points.ts`, and `app/web/components/report/PosteriorGauge.tsx`.
- Recovery checkpoint and reset receipt: `d326d06`.
- Phase-3c recovery timing, evidence, and exit contract:
  `docs/deployment/render-to-syd2-phase3.md`.
- Shared-edge reboot guardrail:
  `docs/operations/risks-and-guardrails.md`.
- Evidence expansion contract and research:
  `plans/evidence-source-expansion/plan.md` and `research.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Aggregate likelihood ratio and Bayesian quantities are honestly named under
  a version-pinned historical replay; BA1 has no model posterior and renders N/A.
- PS3/BS3 count only through a published, exact-context, confusion-matrix-backed
  assay validation with Brnich OddsPath, confidence, provenance, selection, and
  independent-evidence gates. Unvalidated source assertions remain context-only.
- Versioned population policies replace global thresholds. Exact RPE65 GN120
  context gets deterministic CSpec precedence plus an auditable general-policy diff.
- Full `npm run verify` passed in 310.2 seconds with 193 web tests, the complete
  backend suite, all ratchets, and the 17-route production build.
- No source acquisition/materialization, live request, upload, provider,
  deployment, Render, Supabase, cleanup, new-ruleset, or SVC v4 action occurred.
- The clean Phase-3c recovery clock remains `2026-07-19T01:46:12Z`; Render is
  still live as rollback.
- Swordfish's watcher-owned inbox remains dirty and was not edited or staged.

## Next Action

- At or after the 2026-07-20 01:46 UTC floor, run the Phase-3c recovery-middle
  sample first. Before that floor, preserve the evidence and runtime holds;
  do not start Phase 7 or close/cancel Render.
