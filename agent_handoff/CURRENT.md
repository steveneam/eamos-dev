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
- **Codex:** PHASE-3C SOAK ACTIVE @ 2026-07-17 13:51 +0000 — pre-middle
  evidence is green; middle is due around/after 2026-07-18 11:31 UTC and the
  48-hour floor around/after 2026-07-19 11:31 UTC. Steven authorized expansion
  Phase 0 then Phase 1 next session as sequential verified slices. A due timed
  soak checkpoint takes precedence. Render remains rollback; source
  materialization, Phase 2+, and deployment Phase 4 require separate approval.
- **Runtime:** Codex is inside the persistent `eamos` tmux session under
  `agent-tmux.service`; the code-server terminal profile now defaults to that
  seam, so a code-server restart no longer owns this process cgroup.

## Log Edit-Lock

UNLOCKED · 2026-07-17 13:51 +0000 · Codex

## Shared File Locks

- None. Codex released the next-session scope lock at 2026-07-17 13:51 +0000.

## Resume Prompt

```text
# Resume prompt · 2026-07-17 13:51 +0000 · Codex Phase 0/1 authorized
Read CURRENT.md, peer mail, the Phase-3c runbook, and plans/evidence-source-expansion/plan.md first.
Steven explicitly authorized expansion Phase 0 and Phase 1 for this next session.
If the roughly 24-hour soak checkpoint is due, run it first; never miss the timed evidence window.
Implement Phase 0 as the first verified slice: calibration/Decimal/preselection, source policy, and MaveDB v2 contract.
Commit, push, and require green CI before treating the shared contract as frozen.
Then implement Phase 1 as a second verified slice: REVEL-led Computational card and its tests/visual proof.
Preserve all four cards' independent inputs/colors; REVEL changes only Computational.
Use synthetic fixtures only; no corpus materialization, Supabase/provider/deploy changes, or final-v4 label.
Keep rollback infrastructure live and continue inside persistent tmux.
```

## Pointer

- Full mutation ledger, proof, and soak exit contract:
  `docs/deployment/render-to-syd2-phase3.md` → Phase 3c.
- Executable full-report failure ratchet:
  `scripts/eamos-report-performance-audit.mjs --require-ok`; regression test:
  `scripts/eamos-report-performance-audit.test.mjs`.
- Hardened Compose: `5rBnRf20ht4wGRQ856ZLO`; public-label redeploy:
  `SSvNBmx91esTGz1tohYoU`; immutable contract: `deploy/syd2/compose.yaml`.
- Stable Vercel production seam: `eamos-dev.vercel.app`; initial cutover
  deployment: `dpl_2Yy6712rwE4zHqaKPHjJoCxmC9SZ`. Every `main` push creates a
  successor deployment, so follow the alias rather than treating that ID as
  current. Prior rollback target: `https://eamos-dev-sg.onrender.com`.
- Beginning-sample proof and 503 characterization are in the runbook; the
  verification-only 12:40 pulse is at the top of `PROGRESS.md`; the 12:20
  false-positive correction is in
  `agent_handoff/ASK-BACKS-FOR-SWORDFISH.md`.
- Trusted-proxy residual and remediation gate:
  `docs/operations/risks-and-guardrails.md`.
- Proposed evidence-source work:
  `plans/evidence-source-expansion/research.md` and
  `plans/evidence-source-expansion/plan.md`; current MaveDB acquisition boundary:
  `docs/mavedb-license-gate/notes.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Three read-only research lanes plus a repository audit produced a proposed
  implementation plan for REVEL/SVC v4, ESM-1b, OMIM, LOVD, MaveDB, and
  OddsPath. `npm run guard` passed in 3.4 seconds.
- The existing four-card report contract is preserved: REVEL controls only the
  Computational card's PP3/BP4 state and color; Clinical, Population, and Lab &
  Functional retain independent inputs and themes. Final SVC v4 remains gated
  on publication, immutable transcription, shadow cases, and clinical approval.
- MaveDB's pinned CC0 bulk subset is rights-eligible, but the current schema-v1
  importer is not launchable: it overwrites variants within a score set, trusts
  caller license/URL fields, bypasses checksum verification in readiness, and
  collapses multiple matches. The plan freezes schema-v2, hostile-archive,
  canonical-link, raw-score-only, and no-automatic-PS3/BS3 gates.
- ESM-1b uses a clean offline regeneration route; OMIM stays provenance-correct
  link-only; LOVD stays link/synthetic-fixture-only; OddsPath classification and
  assay meanings remain distinct.
- Steven's direct 2026-07-17 13:50 instruction authorizes implementation of
  Phase 0 and Phase 1 in the next session, superseding the prior planning-only
  hold for those two phases only. Phase 0 is the serial contract/correctness
  slice; Phase 1 may begin only after Phase 0 is committed, pushed, and green.
- No runtime code, source corpus, deployment, provider, environment, DNS,
  Render, Supabase, credential, cleanup, or Phase-4 state changed.

## Next Action

- On next-session resume, run the Phase-3c middle sample first if it is at/after
  roughly 2026-07-18 11:31 UTC. Otherwise begin expansion Phase 0 as one serial
  verified slice; commit, push, and require green CI before freezing its shared
  contract. Then implement Phase 1 as a separate verified REVEL Computational-
  card slice. Interrupt expansion for any due timed soak evidence. Do not start
  expansion Phase 2+, materialize source corpora, mutate Supabase/provider/
  deployment state, apply a final-SVC-v4 label, or enter deployment Phase 4
  without Steven's separate direct authorization.
