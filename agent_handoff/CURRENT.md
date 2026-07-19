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
- **Codex:** EVIDENCE EXPANSION PHASE 5 COMPLETE @ 2026-07-19 07:05 +0000 —
  the code-only MaveDB archive importer repair passed full local verification.
- **Phase-3c soak:** recovery window active from `2026-07-19T01:46:12Z` after
  a 7h15 shared-edge outage. Recovery middle is due around/after 2026-07-20
  01:46 UTC; earliest end is around/after 2026-07-21 01:46 UTC. Render remains
  live as rollback; do not close/cancel it.
- **GitHub Actions:** Phase-3 run `29675375104` failed with zero steps/logs,
  consistent with the known minute lock. Steven ruled no additional spend;
  commit/push continues, but required CI waits for monthly renewal.
- **Evidence expansion:** Phases 0-5 are complete. Bounded code-only Phase 6 is
  next. Source acquisition/materialization, live providers, ruleset activation,
  and Phase 7 remain held.
- **Runtime:** persistent `eamos` tmux under `agent-tmux.service` remains the
  execution seam.

## Log Edit-Lock

UNLOCKED · 2026-07-19 07:05 +0000 · Codex

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-19 07:05 +0000 · Codex Phase-6 evidence expansion
Read CURRENT.md, peer mail, PROGRESS.md, the evidence-expansion plan, and the Phase-3c runbook first.
Phase 5 MaveDB code-only importer repair is complete and full npm run verify passed in 224.9 seconds.
If the recovery-middle sample is due (around/after 2026-07-20 01:46 UTC), run it first.
Otherwise freeze and start bounded code-only Phase 6 current OddsPath/ruleset hardening.
Name aggregate model quantities honestly; audit BA1, dependency edges, and functional assay-validation gates without activating a new ruleset.
Keep source acquisition/materialization, live providers, deploys, Supabase, and SVC v4 activation held.
The clean soak window started at 2026-07-19T01:46:12Z; earliest closure is 2026-07-21 01:46 UTC.
Commit/push normally, but do not buy GitHub Actions minutes; required new-code CI waits for renewal.
Do not mutate deployments/providers/Supabase/Render or clean watcher-owned files.
```

## Pointer

- Phase-5 implementation and verification receipt: top `PROGRESS.md` entry and
  `plans/evidence-source-expansion/plan.md`.
- MaveDB parser/materializer: `app/backend/app/services/mavedb_archive.py` and
  `app/backend/app/services/mavedb_local.py`.
- Phase-6 ruleset surfaces: `app/backend/app/services/acmg_points.py`, report
  schemas/call cards, and the Phase-6 section of the active plan.
- Recovery checkpoint and reset receipt: `d326d06`.
- Phase-3c recovery timing, evidence, and exit contract:
  `docs/deployment/render-to-syd2-phase3.md`.
- Shared-edge reboot guardrail:
  `docs/operations/risks-and-guardrails.md`.
- Evidence expansion contract and research:
  `plans/evidence-source-expansion/plan.md` and `research.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- MaveDB now has a no-network/no-extraction documented-ZIP parser and schema-v2
  local store with authoritative license joins and exact numeric provenance.
- Hostile archives, ambiguous/deprecated or context-drifted matches, checksum
  failures, and stale schema signatures fail closed with fixed safe codes.
- Every exact score-set match renders separately as neutral `Uncurated` context;
  raw scores cannot activate PS3/BS3, points, or clinical color.
- Full `npm run verify` passed in 224.9 seconds with 188 web tests, the complete
  backend suite, all ratchets, and the production build.
- No real MaveDB archive was acquired or materialized; operator and live-runtime
  gates remain closed.
- The clean Phase-3c recovery clock remains `2026-07-19T01:46:12Z`; Render is
  still live as rollback. No live/cloud/Supabase/deploy mutation occurred.
- Swordfish's watcher-owned inbox remains dirty and was not edited or staged.

## Next Action

- Run the recovery-middle sample first only after its 2026-07-20 01:46 UTC
  floor. Otherwise freeze and start bounded code-only Phase 6 OddsPath/ruleset
  hardening. Do not activate a new ruleset or close/cancel Render.
