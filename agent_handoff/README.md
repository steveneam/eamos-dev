# Agent Handoff Protocol — Canonical Source

Shared source of truth for Claude Code and direct Codex sessions. **This README
is the single home for the coordination protocol** — `CLAUDE.md`, `CODEX.md`, and
`CURRENT.md` point here; change a rule *once*, here.

- **README.md** = stable rules (rarely changes).
- **CURRENT.md** = live state only: the lean 5-heading overwrite-whole-file form
  (Active Status / Log Edit-Lock / Resume Prompt / Pointer / Delta / Next Action);
  zero append surfaces, gated by `eamos-handoff-lint --strict`.
- **PROGRESS.md / CHANGELOG.md / each agent's next-session doc** = history.

## Read Order (every session)

`CLAUDE.md`/`CODEX.md` → this file → `CURRENT.md` (live state) → `RISKS.md`
(hazards/gated) → the active `plans/<feature>/` → `git status --short --branch` +
`git diff --stat` (live worktree truth). `TASKS.md` and `DECISIONS.md` when relevant.

## Hard Rules (user-mandated — breaking any needs explicit per-instance user OK)

1. **Never delete/overwrite the other agent's plan, handoff section, task brief,
   or `next-session-*` doc.** Supersede only by *append + archive*: copy the old
   verbatim to `agent_handoff/archive/<date>-<slug>.md`, then write new.
2. **Narrate your own work in your own `CURRENT.md` section.** You may reconcile
   the other's section (it's away / a factual error) but must preserve it via
   append+archive (Rule 1) — never silently clobber.
3. **Agent-agnostic ownership (Steven 2026-07-08).** Any agent owns any file/lane
   full-stack (FE + BE + data + docs + tests + tooling) and may audit/fix the
   other's historical work, deps, and branches. No fixed Claude=FE / Codex=BE
   wall; Steven picks the active agent by availability + usage limits.
4. **Shared files need a lock.** Before editing a shared/high-conflict file
   (`CLAUDE.md`, `CODEX.md`, `agent_handoff/*`, `CHANGELOG.md`, `PROGRESS.md`,
   `ROADMAP.md`, `plans/README.md`, `app/*/lib/backend.ts`, backend schemas), claim
   it in `CURRENT.md → ## Shared File Locks` (a lock line lives there only while
   held; released locks → PROGRESS.md); if held, defer or file a Cross-Agent
   Request. Never both editing one file.
5. **Contract changes are schema-first.** Land the backend Pydantic schema first,
   then the `app/web/lib/backend.ts` mirror (and `app/frontend/src/lib/backend.ts`
   if touched); `test_frontend_contract.py` is the canary. Ordering, not role.
6. **No idle waiting.** Blocked or the next milestone is user-gated → follow the
   Idle Protocol; never idle, never start a gated milestone to fill time.
7. **Ownership is by availability, not role.** Two agents at once → take **disjoint
   scopes**, record who owns which in `## Active Status` (see Rule 3).
8. **Timestamp + edit-lock every log/handoff write** (`CURRENT.md`, `RISKS.md`,
   `TASKS.md`, `DECISIONS.md`, `CHANGELOG.md`, `PROGRESS.md`, `ROADMAP.md`, active
   `plans/*`). Stamp the section `YYYY-MM-DD HH:MM ±zzzz · <agent>` from the real
   clock. Claim the single `## Log Edit-Lock` line first (`LOCKED: …`), release
   last (`UNLOCKED · …`) after re-reading. Other agent's lock fresh (≤20 min) →
   STOP + ask; stale (>20 min) → record takeover, proceed.
9. **`CURRENT.md` updates at MAJOR boundaries only — REPLACE, never stack.**
   Minor progress → your own rolling log (Claude →
   `~/.claude/plans/next-session-eamos.md`; Codex → `PROGRESS.md`), never here.
   When you update, overwrite the whole file to the lean form; append+archive
   verbatim first (Rule 1) if it held unrecorded detail. **Every session
   regardless** (safety, not gated): refresh `## Active Status`, release
   `## Log Edit-Lock`, end clear-safe. "Major" = a verified milestone or a
   user-visible state change.
10. **Raise the bar each session — ship net-new, not just maintenance.** The plan
    and Steven's decisions OUTRANK this; "net-new" is deepening the moat *within*
    the plan, never inventing scope. Durable structural/visual/architectural
    change needs Steven's explicit OK *before* it ships. Land ≥1 of: a new
    user-visible capability, a proprietary tool/script, a measurable perf win
    (name the metric), or a stronger verification layer. Lint/doc/refactor sweeps
    don't satisfy it alone. *Exception:* explicit user-constrained sessions ("just
    commit / clean up / verify") — record the constraint in `## Active Status`.

## Idle / Usage-Exhaustion Protocol

Blocked or waiting → never idle, never start a gated milestone. Take the
highest-value safe work anywhere (agent-agnostic): plan-ahead reviewable
artifacts; behavior-preserving hardening (no contract-shape change); mock-first
against a not-yet-built dep; write the precise ask into `## Cross-Agent Requests`;
browser/a11y/perf/security/test QA. Never in free time: gated milestones, the
other agent's in-flight work, shared-contract shape mid-flight, broad reformatting,
commits/pushes without ask, speculative features.

## Integration Checkpoint

At milestone boundaries (not mid-task) the active agent runs `cd app/backend &&
python -m pytest tests/test_frontend_contract.py -q` + a frontend build + a FE↔BE
smoke, logs it in its section, flags drift in `## Cross-Agent Requests`.

## Stop / Break Semantics

On "break / wrap / stop / pause": start no new scope, ask no new non-blocking
questions, reach the nearest **verified** boundary, finalize the handoff (own
`CURRENT.md` section if major + heartbeat + lock release; archive, never delete,
anything superseded). **The final chat message must end with** (1) a labeled
`Safe to clear: yes|no` line + reason and (2) a fenced, paste-ready resume
`Prompt:` block — in the message, not only the files.

## Resume Prompt Format

A pointer, not a state dump (~8 lines, ≤15 for the lint). First line is a stamp
(real local time): `# Resume prompt · YYYY-MM-DD HH:MM ±zzzz · <agent> <task>`.
Say what to read first, the one-line delta, and the gate. The same stamped prompt
goes in `CURRENT.md → ## Resume Prompt`.

## Wrap Ritual — mechanical rolling-log rotate-to-archive

Keep the live docs lean by rotating history OUT, never stacking it IN.
`CURRENT.md`: overwrite to the lean 5-heading form; released locks, DONE/stale
Cross-Agent Requests, and superseded narratives move to `PROGRESS.md`; the
pre-reshape file is archived verbatim (Rule 1) when it held unrecorded detail;
`eamos-handoff-lint --strict` must pass. Rolling logs: when one grows past
readability, rotate its oldest sessions verbatim to `archive/<date>-<slug>.md` and
leave a one-line pointer.

## Roles & Capabilities (agent-agnostic — neither is a lane)

Live (this folder): `CURRENT.md` (state only), `TASKS.md`, `DECISIONS.md`,
`RISKS.md`, `on_hold/`, `archive/` (verbatim snapshots). History (NOT here):
`CHANGELOG.md`, `PROGRESS.md` (per-task narrative home), `ROADMAP.md`, `plans/*`.
Either agent owns any of FE (UI, design, Workbench, copy, browser iteration) or BE
(APIs, evidence tools, pipelines, schema contracts, tests, live verification,
security, review). Direct Codex sessions have full `D:\eamos` read/write, network,
and local FE+BE verification, exactly as Claude does.
