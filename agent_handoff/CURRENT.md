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
- **Codex:** PHASE-3C SOAK ACTIVE @ 2026-07-17 13:40 +0000 — beginning and
  verification-only pre-middle evidence remain green; the roughly 24-hour
  middle sample is due around/after 2026-07-18 11:31 UTC and the 48-hour floor
  around/after 2026-07-19 11:31 UTC. While waiting, the user-directed
  evidence-source research/planning slice completed with no runtime, source,
  provider, cloud, or database mutation. Render remains rollback; Phase 4
  remains held for separate direct authorization.
- **Runtime:** Codex is inside the persistent `eamos` tmux session under
  `agent-tmux.service`; the code-server terminal profile now defaults to that
  seam, so a code-server restart no longer owns this process cgroup.

## Log Edit-Lock

UNLOCKED · 2026-07-17 13:40 +0000 · Codex

## Shared File Locks

- None. Codex released the evidence-expansion planning locks at
  2026-07-17 13:40 +0000.

## Resume Prompt

```text
# Resume prompt · 2026-07-17 13:40 +0000 · Codex Phase-3c active soak
Read CURRENT.md, peer mail, and docs/deployment/render-to-syd2-phase3.md Phase 3c first.
Evidence-source research and its proposed implementation plan are complete and linked below.
Do not implement that plan or acquire/materialize source data during the frozen soak without direct approval.
Use scripts/eamos-report-performance-audit.mjs --require-ok for the timed samples.
Run the middle sample around/after 2026-07-18 11:31 UTC with exact Compose/resource proof.
Run the end sample around/after 2026-07-19 11:31 UTC; elapsed time alone does not close Phase 3c.
Keep Singapore Render and the old Application live; do not widen grants or enable auto-deploy.
Phase 4, Supabase, credentials, cleanup, source materialization, and Render cancellation remain gated.
Codex runs inside persistent tmux via agent-tmux.service; continue from that seam.
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
- No runtime code, source corpus, deployment, provider, environment, DNS,
  Render, Supabase, credential, cleanup, or Phase-4 state changed.

## Next Action

- At/after roughly 2026-07-18 11:31 UTC, run the Phase-3c middle sample:
  `--require-ok` report/viewer coverage plus DNS/TLS, direct/proxy/rollback
  health, provider, resource/restart/OOM, auth/CORS, and exact-contract checks.
  Repeat at/after the 48-hour floor; do not close Phase 3c on elapsed time alone
  or enter Phase 4 without Steven's separate direct authorization.
