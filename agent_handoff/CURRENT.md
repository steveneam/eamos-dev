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
- **Codex:** PHASE 0 COMPLETE @ 2026-07-17 15:46 +0000 — contract freeze is
  committed and pushed at `49cdacb`. Local guard/lint/typecheck/full tests are
  green; all required CI checks are green. Phase 1 is the next implementation
  slice. Phase 2 is only a candidate and is not authorized.
- **Phase-3c soak:** active. Middle evidence is due around/after
  2026-07-18 11:31 UTC; 48-hour floor is around/after 2026-07-19 11:31 UTC.
  A due timed checkpoint takes precedence over expansion work.
- **Runtime:** persistent `eamos` tmux under `agent-tmux.service` remains the
  execution seam.

## Log Edit-Lock

UNLOCKED · 2026-07-17 15:46 +0000 · Codex

## Shared File Locks

None.

## Resume Prompt

```text
# Resume prompt · 2026-07-17 15:46 +0000 · Codex Phase 1 next
Read CURRENT.md, peer mail, the Phase-3c runbook, and plans/evidence-source-expansion/plan.md first.
Phase 0 is frozen at 49cdacb with required CI green; do not reopen it without a concrete regression.
If the Phase-3c middle checkpoint is due (around/after 2026-07-18 11:31 UTC), run that evidence sample first.
Otherwise implement Phase 1 as one bounded verified slice: the REVEL-led Computational card, backend-derived labels/theme/provenance, independent four-card semantics, accessibility, focused tests, and required visual proof.
Commit, push, and watch CI at the verified boundary.
Do not start Phase 2: Steven said it may be considered next session, which is not direct approval for its source-route/materialization gates.
Use synthetic fixtures only; do not materialize corpora, mutate Supabase/provider/deployment state, or apply a final-SVC-v4 label.
```

## Pointer

- Phase-3c timing, proof, and exit contract:
  `docs/deployment/render-to-syd2-phase3.md`.
- Evidence expansion contract and research:
  `plans/evidence-source-expansion/plan.md` and `research.md`.
- Phase 0 freeze commit: `49cdacb`; CI run:
  `https://github.com/steveneam/eamos-dev/actions/runs/29593366520`.
- Stable Vercel seam: `eamos-dev.vercel.app`; prior Render rollback target:
  `https://eamos-dev-sg.onrender.com`.
- Current MaveDB acquisition boundary: `docs/mavedb-license-gate/notes.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Phase 0 froze backend/Pydantic and TypeScript contracts for versioned
  computational decisions, source-fact policy, provenance, and MaveDB v2.
- Predictor calibration and ACMG arithmetic now use backend `Decimal` with
  canonical decimal-string output, explicit boundaries/inclusivity, immutable
  profile checksums, REVEL preselection, no strongest-score fallback, and
  PP3/BP4 plus PP3/PM1 dependency enforcement.
- Source actions are field-specific and deny by default. Protected facts are
  filtered server-side and again for TSV/HTML/copy/PDF export; unsafe export
  link schemes are rejected.
- MaveDB uses separate archive/score-set/target/variant/match contracts, exact
  identity precedence, authoritative nested CC0 policy, neutral raw scores,
  multiple unaggregated measurements, and archive plus logical checksum gates.
  Zenodo v4 filename/size/MD5 are pinned; synthetic stores are explicitly
  `fixture_ready` and cannot serialize publicly.
- Local `npm run guard`, `lint`, `typecheck`, and `test` passed. CI required
  checks passed, including sharded backend tests, frontend build/test/lint,
  container contract, dependency security, and coordination ratchets.
- No corpus materialization, Supabase/provider/deployment mutation, final-v4
  activation, or Phase 2 work occurred.
- The long closeout was ratcheted into Hard Rule 12 in
  `agent_handoff/README.md`: freeze phase exits, triage late findings, stop
  general review after the first full green gate, and collapse immediately to
  commit/CI/handoff when Steven says wrap.

## Next Action

- On next-session resume, run the Phase-3c middle sample first if it is due.
  Otherwise implement Phase 1 only, bounded to the REVEL Computational-card
  slice and its proof. Preserve the other three cards' independent inputs and
  colors. Do not begin Phase 2 or any source materialization without Steven's
  separate direct authorization.
