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
5. The relevant active plan for the task (`plans/<feature>/`, or
   `plans/v2-backend.md` for backend history) — whichever the work touches.
6. `git status --short --branch` and `git diff --stat` — the live worktree
   truth (do **not** rely on a frozen inventory file for this).

`agent_handoff/TASKS.md` (task queue) and `agent_handoff/DECISIONS.md`
(durable coordination decisions) are read when relevant.

## Hard Rules (user-mandated — breaking any needs explicit per-instance user OK)

1. **Never delete or overwrite the other agent's plan, handoff section, task
   brief, or `next-session-*` doc. Default-deny.** Supersede only by
   *append + archive*: copy the old content verbatim to
   `agent_handoff/archive/<date>-<slug>.md`, then write the new.
2. **Narrate your own work in your own `CURRENT.md` section** —
   `## Claude — Last Task & Resume` / `## Codex — Last Task & Resume`. You
   *may* edit or reconcile the other agent's section (e.g. when it is away, or
   to fix a factual error) — this is agent-agnostic — but **preserve its
   content via append+archive (Rule 1); never silently clobber a narrative.**
   Default to writing only your own; reach into the other's only with cause.
3. **Agent-agnostic ownership (Steven, 2026-07-08).** Any agent (Claude or
   Codex) can own any file, any lane, full-stack (frontend + backend + data +
   docs + tests + tooling), and may audit/fix the other agent's historical
   work, dependencies, and branches. There is **no** fixed Claude=frontend /
   Codex=backend wall. Steven picks the active agent by availability + usage
   limits. When two agents run at once, they take **disjoint scopes** and
   coordinate via the board + locks — but which agent owns which scope is not
   fixed by role; record the split in `## Active Status` to avoid collisions.
4. **Shared files need a lock.** Before editing a shared/high-conflict file
   (`CLAUDE.md`, `CODEX.md`, `agent_handoff/*`, `CHANGELOG.md`, `PROGRESS.md`,
   `ROADMAP.md`, `plans/README.md`, `app/frontend/src/lib/backend.ts`, backend
   schema files), claim it in `CURRENT.md` → `## Shared File Locks`; if held,
   defer or file a `## Cross-Agent Requests` entry. Never both editing one file.
5. **Contract changes are schema-first.** Whoever changes a payload lands the
   backend Pydantic schema *first*, then updates the active
   `app/web/lib/backend.ts` TS mirror (and `app/frontend/src/lib/backend.ts` if
   touched); `test_frontend_contract.py` is the canary. This is an *ordering*
   rule, not a role rule — the same agent can do both ends. If the other agent
   is mid-flight on that contract surface, coordinate via `## Cross-Agent
   Requests` + a Shared File Lock instead of editing in parallel.
6. **No idle waiting.** If blocked, or your next milestone is user-gated,
   follow `## Idle / Usage-Exhaustion Protocol` below. Never idle; never start a
   gated milestone to fill time.
7. **Ownership is by availability, not role.** There is no default FE/BE split
   and no "swap" to authorize — any agent can take any work at any time. When
   both agents are active simultaneously, write who owns which scope in
   `## Active Status` so the two don't collide on the same files.
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
10. **Raise the bar each session — ship something net-new, not just
    maintenance.** (User-mandated 2026-05-29.)
    The active plan and the user's decisions outrank this rule. "Net-new" is
    satisfied by deepening the moat *within* the plan — never by inventing
    scope. Building unrequested structure (layout chrome, navigation, new
    persistent UI) or deviating from the plan to satisfy this rule is a
    *violation* of it, not a satisfaction. Removing, simplifying, fixing, or
    hardening what the plan already calls for fully counts. Any durable
    structural/visual/architectural change needs the user's explicit OK
    *before* it ships, whatever the source of the idea.
    Every Claude or Codex session
    must land at least one of:
    - a new user-visible capability,
    - a proprietary Eamos tool/script,
    - a measurable performance improvement (load time, bundle size, cache
      hit-rate, query latency — name the metric in your commit/section), or
    - a stronger verification layer (new test surface, new contract canary,
      new preflight check).

    Patches, lint sweeps, doc tidies, and pure refactors do not satisfy this
    rule on their own — pair them with something net-new. Aim bigger than
    patching: think faster data loading, smarter cache/preflight tooling,
    proprietary validation scripts, or sharper user-facing surfaces.
    *Exception:* explicit user-constrained sessions (e.g. "just commit",
    "just clean up", "just verify", "rescue-only") — write the constraint
    into your `## Active Status` so the next session sees why the bar was
    lowered. All existing guardrails still apply: no runtime local-source
    wiring, no Supabase / object-storage / startup downloads, no production
    downloads, no restricted predictor unlocks, no destructive git.
    Local-source runtime wiring stays approval-only.

## Idle / Usage-Exhaustion Protocol

The next milestone is user-gated, or you're waiting on something: do **not**
idle, do **not** start a gated milestone. Take the highest-value safe work
(anywhere in the repo — ownership is agent-agnostic):

1. **Plan ahead** — reviewable `design-doc`/`spec`/`plan` artifacts for upcoming
   milestones (allowed even when implementation is gated).
2. **Harden the tree** — behavior-preserving refactor / lint / dead-code /
   type-safety / coverage, tightly scoped, fully revertible, no
   contract-shape change.
3. **Mock-first** — if blocked on a not-yet-built deliverable, build/verify
   against the mock/stub so the work integrates when it lands.
4. **Write the precise ask** — put exactly what you need into `## Cross-Agent
   Requests` so the next session executes it with no round-trips.
5. **Free-time menu** — browser/pixel/a11y QA, visual-polish backlog,
   component-doc tightening, backend error-path/perf hardening, security review,
   test hardening.

Never in free time: gated milestones (FE-6/7/8, M-002), **the other agent's
in-flight / uncommitted work** (don't stomp a live worktree or dirty tree
without coordinating), shared-contract shape mid-flight, broad reformatting,
commits/pushes without ask, speculative features. When **you** are about to run
out: reach a verified boundary, write your own section + archive anything
superseded, leave a prioritized pickup queue, and state in `## Cross-Agent
Requests` whatever the next session needs to continue.

## Integration Checkpoint

Periodic joint verification that frontend + backend still agree, run at
milestone boundaries (not mid-task, not every task).

- **Driver: whichever agent is active** at the milestone boundary (record it
  in `## Active Status`).
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
network/verification. **That is fully retired.** Direct Codex app sessions have
verified full `D:\eamos` read/write, outbound network, and local
frontend+backend verification, exactly as Claude does. As of 2026-07-08 there
is no role split at all: **ownership is agent-agnostic** — either agent owns any
part of the repo, full-stack, and Steven picks the active agent by availability
+ usage limits (see Hard Rule 3).

## Capabilities (both agents; ownership is agent-agnostic)

Neither of these is a lane — either agent can and does own any of it. Listed so
a session knows the full surface it may be asked to take:

- **Frontend:** UI, visual design, Workbench layout, product copy,
  browser/pixel iteration, frontend plans.
- **Backend:** APIs, evidence tools, data pipelines, schema contracts, tests,
  live/API verification, security hardening, backend plans, adversarial review.

Steven assigns whichever agent is available; that agent takes whatever the task
needs across both.
