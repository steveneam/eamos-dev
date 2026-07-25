# Next session as a Mode B parallel window

Status: proposed; needs Steven's partition approval, then per-lane launch approval.

Stamped: 2026-07-25 06:2x +0000 · Claude.

Sourced from thalon's proven practice on this box: `~/work/thalon/COORDINATION.md`
and `~/work/thalon/scripts/launch-lane.sh`. Eamos protocol:
`COORDINATION.md` §"How we run a sprint" and `AGENTS.md`.

## The mechanic that changes everything: the lead drives tmux, Steven only approves

Eamos's `COORDINATION.md` still describes Mode B as *"Steven opens one
terminal/runtime per lane"* and hands him **copy-paste launch commands**. That
is unusable — he cannot copy text out of any agent terminal.

Thalon already retired exactly this. From `scripts/launch-lane.sh`:

> the founder's old instruction card (open a terminal, cd to the worktree, run
> claude, paste the kickoff) is retired — s51 proved the lead can drive every
> mechanic itself via tmux and the founder only APPROVES.

Its script creates a **detached** tmux window in the agent's own session, starts
`claude` in the prepped worktree, waits for the `❯` prompt, then sends
`Read <kickoff> and execute it.` It refuses to double-launch an existing window,
and the lead monitors with `tmux capture-pane`.

**So Steven's entire involvement becomes: approve the partition, then approve each
launch. One short line each. No pasting, ever.** That is the single most valuable
thing to copy, and Eamos's Mode B description should be amended to match.

**One open question, asked and not yet answered.** Swordfish's brief says *never*
raw `tmux send-keys`. Thalon's launcher uses it. I read those as different
things — swordfish means cross-agent *signalling* (use `agent-comm`), while
thalon is a lead driving its own subordinate windows — but I asked thalon to
confirm and its composer was live, so the send refused twice and I did not spam
it. **Resolve that before shipping `scripts/eamos-launch-lane.sh`**; if the
distinction does not hold, the fallback is `agent-comm` plus a founder tap.

## What actually parallelizes — the honest read

Thalon's discipline here is worth copying too: it wrote *"only ONE task is
unconditionally lane-able"* rather than pretending a slate was parallel. Applying
the same test to `plan.md`:

| Phase | Parallelizable? | Why |
| --- | --- | --- |
| 1 — record the determination | **No** — lead serial | Every edit lands in the one shared `registry_records.py`. This is the freezable seam; it must merge *before* lanes fork. |
| 2 — primer engine | **No** — lead | One config flip plus a gated binary; nothing to divide. |
| 3 — predictor wiring | Partly | Each predictor has its own service + builder + tests, but they share `predictor_runtime.py` and the capability registry. Lane-able **only after** Phase 1 freezes those. |
| 5 — the six missing builders | **Yes — this is the real window** | Each is a *new* CLI file with its own tests and docs. Disjoint by construction, no shared seam once the registry is frozen. |
| 6 — Wave 4 surface truth | **No** | The campaign plan mandates a single web writer. Forcing it parallel just moves coupling into merge conflicts. |

So: **a serial lead spine, then one parallel builder window.** Phase 3 becomes a
second wave once Phase 1 is on `main`.

## Proposed partition — 4 lanes

Protocol caps lanes at 3-5 and requires the contract frozen first.

**Serial spine (lead, before any lane forks):** Phase 1 in full — the research
determination written per registry record, the isPcr NO-GO row split, the
`commercial_allowed` vocabulary revisited. Merged to `main`. This *is* the frozen
contract for this window; a lane needing to edit `registry_records.py` means the
partition was wrong → re-plan, never an ad-hoc edit.

| Lane | Owns (exact, new files) | Why it's first-wave |
| --- | --- | --- |
| **B-REF** | `app/backend/app/cli/eamos_grch38_runtime_build.py` + `tests/test_grch38_runtime_build.py` + `docs/live-product-verification/reference/**` | Load-bearing twice over: W3-REF-01 is the largest genuine acquisition, and primer Route B needs its FASTA. |
| **B-MANE** | `app/backend/app/cli/eamos_mane_intervals_build.py` + its tests + `docs/live-product-verification/mane/**` | MANE feeds Batch filtering, Workbench ssODN, Paper resolution, and Report context. Its GFF is already mounted, so the lane is builder-only. |
| **B-HGNC** | `app/backend/app/cli/eamos_hgnc_symbols_build.py` + its tests + `docs/live-product-verification/hgnc/**` | Batch gene filtering needs alias/withdrawn mapping; small, self-contained, high value. |
| **B-PAPER** | `app/backend/app/cli/eamos_paper_corpus_fetch.py` + its tests + `app/backend/tests/fixtures/paper_open_corpus/**` | Fully self-contained — tracked test fixtures, no runtime mount, no asset-store write. The safest lane to run alongside the others. |

**Deliberately held back to a second wave:** Mondo and the GenCC new-format
parser both *modify existing* parsers rather than adding new files, so they
carry conflict risk the four above do not. Lead-serial or wave two.

## Mechanics to copy, with the lessons already paid for

Thalon learned these the expensive way; adopt them rather than re-learning:

1. **Stagger every launch.** Thalon's record: syd4's 16 GB resize was *refused*
   by BinaryLane on host capacity, swap was raised to 6 GB, and *"STAGGER
   standing for all future lane launches"* was made a rule. syd4 also hosts five
   other agent sessions. Launch one lane, confirm it is working, then the next.
2. **Prep worktrees with absolute paths from the repo root.** Thalon logged two
   worktree mishaps from `cwd` persisting across shell calls — a nested worktree
   and a lane branch briefly kicked to `main`. I hit the same class of bug twice
   in this session (a broken Stop hook and a failed `git add`). Use `git -C` and
   `npm --prefix`, never `cd`.
3. **Backend-only lanes skip the web install.** All four lanes here are backend
   CLIs, so each needs only
   `python3 -m venv app/backend/.venv && app/backend/.venv/bin/pip install -r app/backend/requirements.txt`
   — not `npm --prefix app/web ci`. That is a large saving per worktree.
   `.worktreeinclude` already copies `app/backend/.env`, `app/web/.env.local`,
   and `.context/` automatically.
4. **Expect lane death and plan the salvage.** Thalon had a lane author
   everything then die on usage credits pre-verify; the lead inspected, found the
   red test's *real* bug, fixed, verified, merged. Budget for that: a dead lane
   is salvaged by the lead, not restarted from scratch.
5. **Lead is the sole merger**, serialized, rebased, on green only. Lanes mark
   their own coordination row `review` and never merge. A conflict outside a
   lane's own row is a partition leak → re-plan.
6. **Fresh founder approval per launch**, per named run — the partition approval
   is not a blanket grant.

## Housekeeping worth Steven's call first

`.claude/worktrees/` currently holds **15 worktrees at 10 GB**, all from merged
campaign lanes. Adding four more is fine on space (93 G free), but the stale ones
are clutter that makes `git worktree list` hard to read. Removing them is a
deletion, so it needs explicit approval under the no-delete rule — worth asking
at the same time as the partition, not assumed.

## What Steven is asked for

Two short answers, nothing to paste:

1. **Approve the partition** — the serial Phase 1 spine, then the four lanes
   B-REF / B-MANE / B-HGNC / B-PAPER.
2. **Approve worktree cleanup**, or decline and leave the 15 in place.

Then, per lane, one approval at launch time. The lead does the rest: prep the
worktree, write `agent_handoff/KICKOFF-<lane>.md`, launch detached, monitor by
`capture-pane`, review, rebase, merge.
