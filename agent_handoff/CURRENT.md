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
- **Codex:** PHASES 1/2 COMPLETE @ 2026-07-17 17:19 +0000 — implementation
  commit `b7c41c7` is pushed. Full local verification and required CI run
  `29599296576` are green.
- **Phase-3c soak:** active. Middle evidence is due around/after
  2026-07-18 11:31 UTC; 48-hour floor is around/after 2026-07-19 11:31 UTC.
  A due timed checkpoint takes precedence over new expansion work.
- **Runtime:** persistent `eamos` tmux under `agent-tmux.service` remains the
  execution seam.

## Log Edit-Lock

UNLOCKED · 2026-07-17 17:19 +0000 · Codex

## Shared File Locks

None.

## Resume Prompt

```text
# Resume prompt · 2026-07-17 17:14 +0000 · Codex Phases 1/2 complete
Read CURRENT.md, peer mail, PROGRESS.md, and plans/evidence-source-expansion/plan.md first.
REVEL call-card Phase 1 and synthetic-fixture-only ESM-1b Phase 2 are complete at b7c41c7.
CI run 29599296576 is green; do not reopen the slice without a concrete regression.
If the Phase-3c middle checkpoint is due (around/after 2026-07-18 11:31 UTC), run that evidence sample first.
Otherwise stop at the next founder-directed task; no further evidence-expansion phase is authorized.
Do not download/run ESM-1b weights or corpora, materialize bgzip/Tabix assets, upload, mutate Supabase/providers/deployments, or clean watcher-owned files.
```

## Pointer

- Implementation: `b7c41c7`; CI:
  `https://github.com/steveneam/eamos-dev/actions/runs/29599296576`.
- Evidence expansion contract and research:
  `plans/evidence-source-expansion/plan.md` and `research.md`.
- Phase-3c timing, proof, and exit contract:
  `docs/deployment/render-to-syd2-phase3.md`.
- Durable completion receipt: top entry in `PROGRESS.md`.
- ESM-1b runtime/materialization boundary:
  `docs/backend-build-ledger-runtime/materialization-plan.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- The Computational call card is REVEL-led from the typed backend decision,
  including score, PP3/BP4 code, points, theme, provenance, explicit unavailable
  and not-applicable states, independent card colors, and export parity.
- Evidence accounting replaces combined/consensus copy. Browser proof covered
  five states at 390/768/1024/1440; the mobile carousel now has 24-pixel tap
  targets and scored Lighthouse accessibility 97.
- The ESM-1b fixture worker streams bounded inputs through SQLite into
  deterministic raw-score shards, handles contextual duplicates, caps fixture
  inputs at 100,000 rows, and preserves exact 1022/512/scale-20 tiling.
- Runtime activation requires a complete release-ready v2 proof and verifies
  the canonical route plus mounted asset/index name, size, and SHA-256.
- `npm run verify` passed in 243.0 seconds, including all structural guards,
  174 web tests, the complete backend suite, and the 17-route production build.
- No model/corpus download, scoring, bgzip/Tabix materialization, upload,
  Supabase/provider/deployment mutation, or cleanup occurred.

## Next Action

- On the next resume, run the Phase-3c middle sample if its time floor has
  passed. Otherwise wait for Steven's next explicit task; do not start another
  evidence-expansion phase.
