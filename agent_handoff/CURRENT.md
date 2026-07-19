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
- **Codex:** EVIDENCE EXPANSION PHASE 4 COMPLETE @ 2026-07-19 06:14 +0000 —
  the installation-scoped LOVD synthetic-fixture pilot and its 302.4-second
  full local gate are recorded in `PROGRESS.md` and the active plan.
- **Phase-3c soak:** recovery window active from `2026-07-19T01:46:12Z` after
  a 7h15 shared-edge outage. Recovery middle is due around/after 2026-07-20
  01:46 UTC; earliest end is around/after 2026-07-21 01:46 UTC. Render remains
  live as rollback; do not close/cancel it.
- **GitHub Actions:** Phase-3 run `29675375104` failed with zero steps/logs,
  consistent with the known minute lock. Steven ruled no additional spend;
  commit/push continues, but required CI waits for monthly renewal.
- **Evidence expansion:** Phases 0-4 are complete. Phase 5 code-only MaveDB
  importer repair is next, followed by Phase 6 only if its bounded gate passes.
  Source acquisition/materialization, live providers, and Phase 7 remain held.
- **Runtime:** persistent `eamos` tmux under `agent-tmux.service` remains the
  execution seam.

## Log Edit-Lock

UNLOCKED · 2026-07-19 06:14 +0000 · Codex

## Shared File Locks

None.

## Resume Prompt

```text
# Resume prompt · 2026-07-19 06:14 +0000 · Codex Phase-5 evidence expansion
Read CURRENT.md, peer mail, PROGRESS.md, the evidence-expansion plan, and the Phase-3c runbook first.
Phase 4 LOVD fixture-only integration is complete and full npm run verify passed in 302.4 seconds.
If the recovery-middle sample is due (around/after 2026-07-20 01:46 UTC), run it first.
Otherwise freeze a code-only Phase-5 MaveDB importer-repair checklist against hand-authored synthetic fixtures.
Repair schema-v2 identity, streaming archive parsing, exact Decimal values, license joins, canonical links, and neutral multi-match output.
Keep real archive acquisition/materialization, uploads, providers, deploys, Supabase, and all live source access held.
Advance to Phase 6 only after the bounded Phase-5 gate is fully green; Phase 7 remains held.
The clean soak window started at 2026-07-19T01:46:12Z; earliest closure is 2026-07-21 01:46 UTC.
Commit/push normally, but do not buy GitHub Actions minutes; required new-code CI waits for renewal.
Do not mutate deployments/providers/Supabase/Render or clean watcher-owned files.
```

## Pointer

- Phase-4 implementation and verification receipt: top `PROGRESS.md` entry and
  `plans/evidence-source-expansion/plan.md`.
- LOVD contract/adapter: `app/backend/app/schemas/run.py` and
  `app/backend/app/services/lovd_fixture_adapter.py`.
- Existing MaveDB scaffold: `app/backend/app/services/mavedb_local.py`,
  `app/backend/app/data_sources/registry_records_mavedb.py`, and focused tests.
- Recovery checkpoint and reset receipt: `d326d06`.
- Phase-3c recovery timing, evidence, and exit contract:
  `docs/deployment/render-to-syd2-phase3.md`.
- Shared-edge reboot guardrail:
  `docs/operations/risks-and-guardrails.md`.
- Evidence expansion contract and research:
  `plans/evidence-source-expansion/plan.md` and `research.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- LOVD now has one fixed Global Variome shared installation identity and a
  hand-authored JSON/Atom fixture adapter with no network capability.
- Exact assembly/transcript-version/HGVS matching, record-license checks,
  canonical URLs, and fixed policy decisions fail closed on drift or ambiguity.
- Prohibited case/person/classification/raw fields cannot enter backend or web
  models, product export, logs, analytics, or cache; unknown licenses are denied.
- The neutral report block states presence is not classification. LOVD input
  cannot alter ACMG points, criteria, call cards, or their UI themes.
- Full `npm run verify` passed in 302.4 seconds with 186 web tests, the complete
  backend suite, all ratchets, and the production build.
- The clean Phase-3c recovery clock remains `2026-07-19T01:46:12Z`; Render is
  still live as rollback. No live/cloud/Supabase/deploy mutation occurred.
- Swordfish's watcher-owned inbox remains dirty and was not edited or staged.

## Next Action

- Run the recovery-middle sample first only after its 2026-07-20 01:46 UTC
  floor. Otherwise start bounded, synthetic-fixture-only Phase 5 MaveDB importer
  repair. Do not acquire/materialize a real archive or close/cancel Render.
