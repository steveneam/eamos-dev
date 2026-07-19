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
- **Codex:** EVIDENCE EXPANSION PHASE 3 COMPLETE @ 2026-07-19 05:44 +0000 —
  safe OMIM cross-reference behavior and its full local gate are recorded in
  the top `PROGRESS.md` entry and the active evidence-expansion plan.
- **Phase-3c soak:** recovery window active from `2026-07-19T01:46:12Z` after
  a 7h15 shared-edge outage. Recovery middle is due around/after 2026-07-20
  01:46 UTC; earliest end is around/after 2026-07-21 01:46 UTC. Render remains
  live and Phase 4 remains held.
- **GitHub Actions:** Steven ruled no additional spend; wait for the monthly
  included-minutes renewal. Commit/push continues normally, but new code or
  deploy slices cannot clear a required CI boundary while Actions is blocked.
- **Evidence expansion:** Phases 0-3 are complete. Steven authorized the
  remaining code-eligible sequence; Phase 4 LOVD link/synthetic-fixture pilot
  is next, then Phases 5-6 only as their bounded gates pass. Phase 7 and every
  live/materialization gate remain held.
- **Live comm:** `agent-comm` is installed but targets Claude panes only, and
  `live-comm` is not exposed to Codex. Swordfish was notified at 05:10 UTC;
  async peer mail remains the reachable channel. This does not block Phase 3c.
- **Runtime:** persistent `eamos` tmux under `agent-tmux.service` remains the
  execution seam.

## Log Edit-Lock

UNLOCKED · 2026-07-19 05:44 +0000 · Codex

## Shared File Locks

None.

## Resume Prompt

```text
# Resume prompt · 2026-07-19 05:44 +0000 · Codex Phase-4 evidence expansion
Read CURRENT.md, peer mail, PROGRESS.md, the evidence-expansion plan, and the Phase-3c runbook first.
Phase 3 safe OMIM cross-references are complete and full npm run verify is green.
If the recovery-middle sample is due (around/after 2026-07-20 01:46 UTC), run it first.
Otherwise freeze the bounded Phase-4 exit checklist, then implement the LOVD link/synthetic-fixture pilot.
Use one reviewed installation identity, hand-authored schema fixtures, exact matches, and non-evidentiary presence only.
Keep live LOVD access, scraping, case/patient data, source downloads, materialization, providers, deploys, and Supabase held.
After Phase 4, advance through code-eligible Phases 5-6 only as each bounded gate passes; Phase 7 is held.
The clean soak window started at 2026-07-19T01:46:12Z; earliest closure is 2026-07-21 01:46 UTC.
Commit/push normally, but do not buy GitHub Actions minutes; required new-code CI waits for renewal.
Do not mutate deployments/providers/Supabase/Render, start Render-cancellation Phase 4, or clean watcher-owned files.
```

## Pointer

- Phase-3 implementation and verification receipt: top `PROGRESS.md` entry and
  `plans/evidence-source-expansion/plan.md`.
- OMIM contract/normalizer: `app/backend/app/schemas/run.py` and
  `app/backend/app/services/omim_cross_references.py`.
- Recovery checkpoint and reset receipt: `d326d06`.
- Phase-3c recovery timing, evidence, and exit contract:
  `docs/deployment/render-to-syd2-phase3.md`.
- Shared-edge reboot guardrail:
  `docs/operations/risks-and-guardrails.md`.
- Evidence expansion contract and research:
  `plans/evidence-source-expansion/plan.md` and `research.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- OMIM is now a typed, supplier-owned, `identifier_only` cross-reference with
  fixed canonical links and explicit MONDO/HPO/ClinGen/GenCC policy proof.
- Bare/legacy identifiers, unknown suppliers, wrong entry types, substituted
  URLs, and missing or denied decisions fail closed; links cannot create
  gene-disease validity or ACMG evidence.
- `omim_mim2gene` and `omim_licensed_api` are reserved but fully disabled. No
  OMIM content, parser, API client, download, cache, or provider was added.
- Full `npm run verify` passed in 212.1 seconds after the structural hotspot
  ratchet moved OMIM logic out of the report orchestrator (887 lines).
- The clean Phase-3c recovery clock remains `2026-07-19T01:46:12Z`; Render is
  still live as rollback. No live/cloud/Supabase/deploy mutation occurred.
- Swordfish's watcher-owned inbox remains dirty and was not edited or staged.

## Next Action

- At the next session, run the recovery-middle Phase-3c sample first only if its
  2026-07-20 01:46 UTC floor has passed. Otherwise start the bounded Phase-4
  LOVD link and synthetic-fixture pilot. Do not close/cancel Render.
