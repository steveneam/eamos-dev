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
- **Codex:** PHASE-3C RECOVERY BASELINE COMPLETE @ 2026-07-19 05:03 +0000 —
  live verification and incident receipt are recorded in `d326d06`.
- **Phase-3c soak:** recovery window active from `2026-07-19T01:46:12Z` after
  a 7h15 shared-edge outage. Recovery middle is due around/after 2026-07-20
  01:46 UTC; earliest end is around/after 2026-07-21 01:46 UTC. Render remains
  live and Phase 4 remains held.
- **GitHub Actions:** Steven ruled no additional spend; wait for the monthly
  included-minutes renewal. Commit/push continues normally, but new code or
  deploy slices cannot clear a required CI boundary while Actions is blocked.
- **Evidence expansion:** Steven authorized the remaining code-eligible work
  for the next session at 05:17 UTC. Phase 2 is complete; start with the bounded
  Phase-3 OMIM cross-reference slice, then advance through Phases 4-6 only as
  their gates pass. Phase 7 and every live/materialization gate remain held.
- **Live comm:** `agent-comm` is installed but targets Claude panes only, and
  `live-comm` is not exposed to Codex. Swordfish was notified at 05:10 UTC;
  async peer mail remains the reachable channel. This does not block Phase 3c.
- **Runtime:** persistent `eamos` tmux under `agent-tmux.service` remains the
  execution seam.

## Log Edit-Lock

UNLOCKED · 2026-07-19 05:17 +0000 · Codex

## Shared File Locks

None.

## Resume Prompt

```text
# Resume prompt · 2026-07-19 05:17 +0000 · Codex Phase-3 evidence expansion
Read CURRENT.md, peer mail, PROGRESS.md, the evidence-expansion plan, and the Phase-3c runbook first.
Phase 2 is complete; Steven authorized remaining code-eligible work for this session.
If the recovery-middle sample is due (around/after 2026-07-20 01:46 UTC), run it first.
Otherwise freeze a bounded Phase-3 exit checklist, then implement safe OMIM cross-reference-only behavior.
Keep OMIM content/API/mim2gene, downloads, materialization, providers, deploys, and Supabase held.
After Phase 3, advance through code-eligible Phases 4-6 only as each bounded gate passes; Phase 7 is held.
The clean soak window started at 2026-07-19T01:46:12Z; earliest closure is 2026-07-21 01:46 UTC.
Commit/push normally, but do not buy GitHub Actions minutes; required new-code CI waits for renewal.
Use async peer mail for Eamos/Codex; current live-comm targets Claude panes only.
Do not mutate deployments/providers/Supabase/Render, start Render-cancellation Phase 4, or clean watcher-owned files.
```

## Pointer

- Recovery checkpoint and reset receipt: `d326d06`; durable details are the
  top entry in `PROGRESS.md`.
- Phase-3c recovery timing, evidence, and exit contract:
  `docs/deployment/render-to-syd2-phase3.md`.
- Shared-edge reboot guardrail:
  `docs/operations/risks-and-guardrails.md`.
- Implementation: `b7c41c7`; CI:
  `https://github.com/steveneam/eamos-dev/actions/runs/29599296576`.
- Evidence expansion contract and research:
  `plans/evidence-source-expansion/plan.md` and `research.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Swordfish's receipt and direct syd2 evidence corroborated a public-edge outage
  from 2026-07-18 18:30 to 2026-07-19 01:46 UTC. Current health cannot make that
  interval clean, so the consecutive observation clock restarted.
- The recovery baseline passed DNS/TLS, direct syd2 and Render health, exact
  direct/Vercel origin identity, two complete `--require-ok` report/viewer
  passes, auth/CORS/header checks, and zero post-recovery app/edge 5xx.
- The exact Compose, digest, hardening, mounts, runtime tree, and zero host
  bindings remain intact. Disk has 35,376,615,424 bytes free; Docker reported
  880 MiB / 2 GiB after load; all cgroup pressure/OOM counters are zero.
- The longstanding Dokploy project-default network was reconciled against the
  original inspection; Traefik remains explicitly pinned to `dokploy-network`.
- Swordfish's edge-convergence unit is enabled and active but has not yet seen a
  natural reboot. Render remains the rollback throughout the restarted soak.
- Swordfish's live-comm claim is only partial for Eamos: the executable cannot
  target this Codex session and its skill is Claude-only. A durable correction
  was sent; no production or soak action follows.
- Steven authorized continued code-eligible evidence expansion for the next
  session. Phase 2 is already complete; Phase 3 OMIM cross-reference-only work
  is next, with all source-content and live-operation gates preserved.
- No deployment, provider, DNS, environment, Supabase, Render, credential,
  cleanup, or Render-cancellation Phase-4 mutation occurred.

## Next Action

- At the next session, run the recovery-middle Phase-3c sample first only if its
  2026-07-20 01:46 UTC floor has passed. Otherwise start the bounded Phase-3
  safe OMIM cross-reference slice. Do not close/cancel Render.
