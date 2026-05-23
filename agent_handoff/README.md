# Agent Handoff Protocol — Canonical Source

This folder is the shared operational source of truth for Claude Code and
direct Codex sessions. **This README is the single home for the coordination
protocol** (hard rules, locks, idle, stop/break, resume-prompt format).
`CLAUDE.md`, `CODEX.md`, and `agent_handoff/CURRENT.md` point here instead of
re-stating the rules — change a rule *once*, here.

- **README.md (this file)** = the stable rules (rarely changes).
- **CURRENT.md** = live state only (changes at major task boundaries).
- **PROGRESS.md / CHANGELOG.md / each agent's own next-session doc** = history.

_Last restructured: 2026-05-18 14:02 +1000 · Claude (user-mandated dedup +
CURRENT.md trim). Prior README + the pre-trim 1200-line CURRENT.md are archived
verbatim under `agent_handoff/archive/2026-05-18-*`._

## Read Order (every fresh session)

1. `CODEX.md` (direct Codex) or `CLAUDE.md` (Claude) — agent-specific entry.
2. `agent_handoff/README.md` (this file — the protocol).
3. `agent_handoff/CURRENT.md` — live state: Active Status, Log Edit-Lock,
   Shared File Locks, Cross-Agent Requests, Current State, the two
   `Last Task & Resume` sections.
4. `agent_handoff/RISKS.md` — hazards, gated work, do-not-touch.
5. The relevant active plan: `plans/v2-frontend.md` (Claude) or
   `plans/v2-backend.md` (Codex); plus `plans/<feature>/` if assigned.
6. `git status --short --branch` and `git diff --stat` — the live worktree
   truth (do **not** rely on a frozen inventory file for this).

`agent_handoff/TASKS.md` (task queue) and `agent_handoff/DECISIONS.md`
(durable coordination decisions) are read when relevant.

## Hard Rules (user-mandated — breaking any needs explicit per-instance user OK)

1. **Never delete or overwrite the other agent's plan, handoff section, task
   brief, or `next-session-*` doc. Default-deny.** Supersede only by
   *append + archive*: copy the old content verbatim to
   `agent_handoff/archive/<date>-<slug>.md`, then write the new.
2. **Each agent writes only its own `CURRENT.md` section** —
   `## Claude — Last Task & Resume` / `## Codex — Last Task & Resume`. You read
   the other's; you never rewrite it.
3. **Parallel mode is ON.** Claude (frontend: `app/frontend/**` +
   `plans/v2-frontend.md`) and Codex (backend: `app/backend/**` +
   `plans/v2-backend.md`) run simultaneously on disjoint scopes. Role swaps
   only on explicit user command, recorded in `## Active Status`.
4. **Shared files need a lock.** Before editing a shared/high-conflict file
   (`CLAUDE.md`, `CODEX.md`, `agent_handoff/*`, `CHANGELOG.md`, `PROGRESS.md`,
   `ROADMAP.md`, `plans/README.md`, `app/frontend/src/lib/backend.ts`, backend
   schema files), claim it in `CURRENT.md` → `## Shared File Locks`; if held,
   defer or file a `## Cross-Agent Requests` entry. Never both editing one file.
5. **Contract changes are backend-led.** Frontend never edits the
   `app/frontend/src/lib/backend.ts` contract *shape* or backend schema; it
   requests the change via `## Cross-Agent Requests`.
   `test_frontend_contract.py` is the canary.
6. **No idle waiting.** If blocked, the other agent is out of usage/context, or
   your lane's next milestone is user-gated, follow `## Idle /
   Usage-Exhaustion Protocol` below. Never idle; never start a gated milestone
   to fill time.
7. **Roles are explicit; swaps are written.** Default: Claude = frontend +
   integration-checkpoint driver; Codex = backend + fallback driver. A swap is
   valid only when (a) the user commands it and (b) it is written into
   `## Active Status`. No silent swaps.
8. **Timestamp + edit-lock on every log/handoff write.** For
   `agent_handoff/CURRENT.md`, `RISKS.md`, `TASKS.md`, `DECISIONS.md`,
   `CHANGELOG.md`, `PROGRESS.md`, `ROADMAP.md`, active `plans/*`:
   - **Stamp the section you edit** `YYYY-MM-DD HH:MM ±zzzz · <agent>`. Read
     the real clock (`Get-Date` / `date`) — never guess the time.
   - **Claim the single `## Log Edit-Lock` line first, release it last.** Set
     `LOCKED: <agent> · <stamp> · <file/section>` before editing any of them;
     set `UNLOCKED · <stamp> · <agent> (<note>)` only after you finish *and*
     re-read to confirm no concurrent change.
   - **Lock already held by the other agent:** fresh (≤ 20 min) → **STOP**,
     do not read-then-edit the logs, surface it to the user, ask before
     proceeding. Stale (> 20 min) → assume mid-edit abandonment (see Idle
     Protocol), record the takeover in your own section with a stamp, proceed.
   This is distinct from `## Shared File Locks` (Rule 4 covers source/contract
   files; this covers the log/handoff docs themselves).
9. **`CURRENT.md` is updated at MAJOR task/milestone boundaries only — and you
   REPLACE, never stack.** (User-mandated 2026-05-18.)
   - Do **not** rewrite the detailed `Last Task & Resume` narrative after every
     minor task. Minor/incremental progress goes to **your own rolling log**,
     not `CURRENT.md`: Claude → `~/.claude/plans/next-session-eamos.md`;
     Codex → `PROGRESS.md` + `plans/v2-backend.md` (and its own next-session
     doc if it keeps one).
   - When you *do* update your `CURRENT.md` section, **replace** its prior
     contents with the current state — do not append "Previous update" /
     "Latest update" blocks or stack historical resume prompts. If the prior
     content has detail not yet recorded elsewhere, append+archive it verbatim
     to `agent_handoff/archive/<date>-<slug>.md` *before* replacing (Rule 1),
     then write the new state clean.
   - **Still every session (the safety mechanism, not gated):** update the
     `## Active Status` heartbeat line, release the `## Log Edit-Lock`, and end
     clear-safe. The *narrative* is gated to major boundaries; the *heartbeat +
     lock release + clear-safe close* are not.
   - "Major" = a verified milestone (an FE-x unit, an M-00x slice, a
     checkpoint commit, a reviewable plan set), or a user-visible state change.
     A trivial turn, a doc tidy, or a partial step is not major.

## Idle / Usage-Exhaustion Protocol

Blocked on the other agent, they're out of usage/context, or your lane's next
milestone is user-gated: do **not** idle, do **not** start a gated milestone.
In your own ownership only, take the highest-value safe work:

1. **Plan ahead** — reviewable `design-doc`/`spec`/`plan` artifacts for upcoming
   milestones in your lane (allowed even when implementation is gated).
2. **Harden your own tree** — behavior-preserving refactor / lint / dead-code /
   type-safety / coverage, scoped strictly to your folders, fully revertible,
   no contract-shape change.
3. **Mock-first** — if blocked on the other's deliverable, build/verify against
   the mock/stub so your work integrates when they return.
4. **Write the precise ask** — put exactly what you need into `## Cross-Agent
   Requests` so they execute on return, no round-trips.
5. **Lane free time** — Claude: browser/pixel/a11y QA, visual-polish backlog,
   component-doc tightening. Codex: backend error-path/perf hardening, security
   review of its own surface, test hardening.

Never in free time: gated milestones (FE-6/7/8, M-002), the other agent's
tree, shared-contract shape, broad reformatting, commits/pushes without ask,
speculative features. When **you** are about to run out: reach a verified
boundary, write your own section + archive anything superseded, leave a
prioritized pickup queue, and state in `## Cross-Agent Requests` whether the
other agent is now blocked on you and the minimal unblock.

## Integration Checkpoint

Periodic joint verification that frontend + backend still agree, run at
milestone boundaries (not mid-task, not every task).

- **Driver: Claude (default).** Fallback: Codex, only if Claude is out of
  usage/context and the user commands the swap (record in `## Active Status`).
- Driver runs: `cd app/backend && python -m pytest
  tests/test_frontend_contract.py -q` (the contract canary) + a frontend build
  + a frontend↔backend smoke against the live/mock backend, then logs the
  result in its own section and flags any drift in `## Cross-Agent Requests`.

## Stop / Break Semantics (both agents)

When the user says "take a break / wrap / stop here / that's enough / let's
pause" or otherwise signals stopping:

- Do **not** start new scope. Do **not** ask new non-blocking questions.
- Reach the nearest **verified** boundary (never stop mid-edit/mid-verify).
- Finalize the handoff: own `CURRENT.md` section (if a major boundary) + the
  `## Active Status` heartbeat + Log-Edit-Lock release; archive (never delete)
  anything superseded.
- The **final chat message must end with** (1) a clearly labeled
  `Safe to clear: yes|no` line + reason, and (2) a fenced, paste-ready resume
  `Prompt:` block. The prompt must be in the message, not only in the files.
- "Break" = clean stop, not "ask me what's next".

## Resume Prompt Format

A resume prompt is a **pointer, not a state dump** (~8 lines). It says what to
read first, the one-line delta since last session, and the gate — the protocol,
git lineage, and lane rules already live in the files it names; re-encoding
them is what ballooned past prompts.

Its **first line must be a stamp** (real local time, not guessed):
`# Resume prompt · YYYY-MM-DD HH:MM ±zzzz · <agent> <session/task>` — so the
user can identify the latest when collecting prompts. The same stamped prompt
goes in the agent's `CURRENT.md` section and (for Claude) the next-session doc.

Shape:

```text
# Resume prompt · 2026-05-18 14:02 +1000 · <agent> <session/task>
Eamos. Read agent_handoff/CURRENT.md (Coordination protocol → README.md;
your section; Locks; Requests), agent_handoff/RISKS.md, <your active plan>,
then git status --short --branch. Delta: <one line>. Next: <one line / gate>.
End clear-safe (Safe-to-clear line + fresh stamped resume prompt).
```

## Source-Of-Truth Roles

Live coordination (this folder):

- `CURRENT.md` — current operational state, owner, files in play,
  verification, next step. **State only. No history, no rule re-statement.**
- `TASKS.md` — queued/candidate tasks with suggested ownership.
- `DECISIONS.md` — durable coordination decisions not to be rediscovered.
- `RISKS.md` — known hazards, failing/pending checks, do-not-touch.
- `on_hold/` — dated prioritized pause register for gated/parked work so
  resume prompts can point instead of re-stating every hold.
- `archive/` — superseded handoffs/snapshots, kept verbatim (Rule 1).

Project history (NOT this folder):

- `CHANGELOG.md` — historical feature/change record.
- `PROGRESS.md` — session/build log (the home for per-task narrative history).
- `ROADMAP.md` — strategic product/build sequence.
- `plans/*` — detailed execution plans.

## Why This Folder Exists / Direct-Codex Context

The earlier split treated Claude as the driver and Codex as a
backend/grunt/review delegate via a Claude Code plugin with constrained
network/verification. **That changed:** direct Codex app sessions have verified
full `E:\eamos` read/write, outbound network, and local frontend/backend
verification. The old split is now a *coordination convention, not a technical
limit* — direct Codex can own substantive backend/API/pipeline/tool/test work
when scoped. Claude remains the default owner for UI/product/design-heavy
frontend, context-rich planning, and visual iteration.

## Practical Ownership (default; user can override per task)

- **Claude Code:** frontend UI, visual design, Workbench layout, product copy,
  browser/pixel iteration, frontend plans.
- **Direct Codex:** backend APIs, evidence tools, data pipelines, schema
  contracts, tests, live/API verification, security hardening, backend plans,
  adversarial code review.
