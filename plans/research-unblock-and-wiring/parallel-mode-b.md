# Next session as a Mode B parallel window

Status: proposed; needs Steven's partition approval, then per-lane launch approval.

Stamped: 2026-07-25 06:2x +0000 · Claude.

Sourced from thalon's proven practice on this box
(`~/work/thalon/COORDINATION.md`, `~/work/thalon/scripts/launch-lane.sh`) plus its
and selom's direct answers to the asks I sent over live-comm — see
`agent_handoff/FROM-THALON-lane-mechanics.md` and `agent_handoff/FROM-SELOM.md`.
Eamos protocol: `COORDINATION.md` §"How we run a sprint" and `AGENTS.md`.

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

**The send-keys question is resolved — thalon confirmed it** (2026-07-25,
`agent_handoff/FROM-THALON-lane-mechanics.md`):

> your own windows → drive them directly; any pane you didn't create →
> agent-comm, no exceptions.

Swordfish's prohibition is the **cross-agent** rule: injecting into another
agent's composer risks splicing into a parked draft, forging provenance, or
submitting multi-line bodies as extra turns. A lead driving windows it created
itself is an operator driving its own terminals. Grey zone thalon flags: a lane
that has been running long enough to hold its own in-flight state deserves the
same courtesy as a peer — peek before typing. So
`scripts/eamos-launch-lane.sh` is unblocked.

**And the kickoff keeps one deliberate human step.** Thalon: send-keys reliably
*types* into a freshly-booted composer but the submit is racy, so they park the
kickoff and press Enter once by hand after eyeballing it. Keep that — it is a
cheap checkpoint, and pressing Enter is exactly the kind of tap Steven can do.

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

## Sizing: launch concurrently, bound the test peaks

**My earlier stagger-the-launches bullet was wrong, and thalon corrected it.**
The stagger rule died with the 2026-07-19 syd4 resize (16 GiB / 6 vCPU). Thalon's
measurement: ~2.26 GiB peak per lane worker, so **4 concurrent lanes plus the
lead fit with headroom**, and the 6 GB swap is backstop rather than working set.

**The binding constraint is vCPU during test runs, not RAM or launch timing.**
Selom independently measured the box the same day and reached the same root
cause from the other direction:

```
6 vCPU · 15.99 GB · 9.10 GB available · 5 agent sessions live
5 claude sessions   ≈ 1.9 GB TOTAL
one Next dev server ≈ 1.4 GB   (≈ three claude sessions)
a browser           ≈ 1.5 GB
```

So the agents are not what eats this box. Concretely:

1. **Cap per-lane test parallelism at `-n 2`, never `-n auto`.** Eamos uses
   pytest-xdist; four lanes each fanning out to 6 workers is 24 processes on
   6 vCPU and ~8-9.6 GB of transient peak — straight into the ceiling. Stagger
   the heavy *suite runs*, not the launches.
2. **No lane runs a dev server or a headless browser.** Thalon never solved lane
   ports because it never needed to — Turbopack fatals on out-of-root symlinks
   ("points out of the filesystem root"), so **visual checks happen on the
   lead's checkout after rebase.** That also settles where this session's owed
   PR #31 browser evidence goes: the lead's checkout, not a lane. If a lane ever
   genuinely needs a server, budget ~1.5 GB, drop a lane, and use swordfish's
   derived-lane-port convention rather than a bare port.
3. **Verify `OOMPolicy=continue` on `agent-tmux.service` before forking.** With
   `stop`, one fat lane OOM takes down every session on the box. Checked today
   and it passes — one command, and the failure mode is the whole fleet.

Selom suggested keeping staggered launches; thalon retired them from lived
post-resize experience while selom has not yet run lanes. Following thalon on
launch timing and selom on the `-n 2` cap satisfies both, because both are really
about the same thing: bound the peaks.

## Mechanics to copy, with the lessons already paid for

1. **Prep worktrees with absolute paths from the repo root.** Thalon logged two
   mishaps from `cwd` persisting across shell calls — a nested worktree and a
   lane branch briefly kicked to `main`. I hit the same class twice today (a
   broken Stop hook, a failed `git add`). Use `git -C` and `npm --prefix`, never
   `cd`.
2. **Assert what a fresh worktree does not have.** `.venv`, `.env`, and
   `node_modules` are all gitignored, so a new lane starts without them.
   `.worktreeinclude` copies `app/backend/.env`, `app/web/.env.local`, and
   `.context/`; everything else is asserted at setup, never discovered at merge.
3. **Lane prep is one command:** `node scripts/eamos-worktree-setup.mjs <lane>`.
   Written and proven 2026-07-25 to close a real gap — `guard-worktree-install.mjs`
   pointed at `eamos-worktree-setup.ps1`, a Windows-era PowerShell script with no
   POSIX equivalent, so a fresh worktree had no deps and no documented way to get
   them. The new script creates the worktree, links deps, and verifies them.
4. **Deps are linked, not installed — measured, not assumed.** Installs live in
   the main checkout; lanes symlink `app/backend/.venv` and
   `app/web/node_modules`. Verified in a probe worktree, all through the links:
   `pytest -n 2` (resolving the **lane's** package, not main's), eslint, vitest
   (37 files / 258 tests), and the web boundary guard all pass. Cost is ~0 bytes
   and no install time per lane, against ~1.6 GB and several minutes each if
   installed fresh.
5. **Never `npm install` inside a worktree** — npm v7+ replaces a linked
   `node_modules` with a real per-lane tree and forks the dependency graph.
   `guard-worktree-install.mjs` blocks it at preinstall.
6. **Worktree deps half-work silently on Linux.** Node resolution walks up to the
   main checkout, so vitest can pass while eslint (workspace-nested deps) fails.
   The setup script asserts the `.bin`-through-link path *and* that backend
   imports resolve to the lane rather than to main — a link that silently
   resolved upward would make a lane green against the wrong code, which is the
   worst failure mode available here.
6. **Keep lane tests env-free by design.** A lane whose tests want real env or
   secrets is a smell — restructure the test.
7. **Kill by PID from `pgrep -af`, never `pkill -f`.** Selom hit this today —
   `pkill -f` matched *its own command line*, killed its script and left the
   server alive. It explains the stray exit-144 I saw doing the same thing, and
   with N lanes it kills other lanes' processes.
8. **Git hooks are shared** across worktrees via the common `.git`, so the
   box-level pre-commit invariants run in every lane for free.
9. **Expect lane death and salvage it.** Thalon had a lane author everything then
   die on usage credits pre-verify; the lead inspected, found the red test's
   *real* bug, fixed, verified, merged. A dead lane is salvaged, not restarted.
10. **Lead is sole merger** — serialized, rebased, green only. Lanes mark their
    own coordination row `review` and never merge. A conflict outside a lane's
    own row is a partition leak → re-plan.
11. **Fresh founder approval per launch.** The partition approval is not a
    blanket grant.

Credit: `agent_handoff/FROM-THALON-lane-mechanics.md` (thalon s68, lived lane
experience) and `agent_handoff/FROM-SELOM.md` (selom, measured box data). Thalon's
fuller brain-dump — merge-train and tripwire sections apply verbatim — is at
`~/work/thalon/.context/peer-notes/lane-mechanics-braindump.md`.

## Status: approved and prepped (2026-07-25)

Steven approved the partition and the worktree cleanup.

**Cleanup done.** All 14 stale worktrees removed — `.claude/worktrees/` went from
**10 GB to 4 KB**, and free disk from 93 G to 102 G. Every branch was verified
pushed and identical to origin first, and `git worktree remove` does not delete
branches, so nothing was lost: all 21 `agent/*` branches remain, including
`agent/product/workbench-canvas`, whose tip is not an ancestor of `main` and
which therefore keeps its own record.

**Prep proven.** `scripts/eamos-worktree-setup.mjs` exists and was exercised
end-to-end on a throwaway lane, then removed.

## Remaining before launch

1. Merge the serial Phase 1 spine to `main` — it is the frozen seam.
2. Write `scripts/eamos-launch-lane.sh`, adapted from thalon's, now that the
   send-keys distinction is confirmed. Keep the parked-kickoff-plus-one-Enter
   checkpoint.
3. Write `agent_handoff/KICKOFF-<lane>.md` per lane.
4. Verify `OOMPolicy=continue` still holds, then launch — concurrently, four
   lanes, tests capped at `-n 2`.

Steven's only remaining input is **one approval per lane at launch time**; the
partition approval is not a blanket grant. The lead does everything else: prep,
kickoff, launch detached, monitor by `capture-pane`, review, rebase, merge.
