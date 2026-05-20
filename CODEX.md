# CODEX.md

Repo-specific entry point for direct Codex sessions in Eamos. The cross-agent
protocol is **not** restated here — it lives once in
`agent_handoff/README.md`.

## Start Here (every fresh Codex session)

Read in order:

1. `CODEX.md` (this file).
2. `agent_handoff/README.md` — **the coordination protocol** (hard rules,
   locks, idle, stop/break, resume-prompt format, full read order).
3. `agent_handoff/CURRENT.md` — live state: Active Status, Log Edit-Lock,
   Shared File Locks, Cross-Agent Requests, Current State, the
   `## Codex — Last Task & Resume` section.
4. `agent_handoff/RISKS.md`.
5. `plans/v2-backend.md` (backend) — plus `plans/<feature>/` if assigned.
6. `git status --short --branch` and `git diff --stat`.

If the user gives a task brief inside `agent_handoff/CURRENT.md` or chat,
follow that brief before older context.

## Direct Codex Role

Direct Codex has verified full `E:\eamos` read/write, outbound network, and
local frontend/backend verification. The old "Codex only does grunt work /
can't run vitest/server" model was plugin-era history. Direct Codex can own
substantive backend/API/pipeline/tool/test work when scoped, and runs its own
backend verification (`pytest`, live smoke). Claude Code remains the default
owner for UI/product/design-heavy frontend and browser/pixel iteration.

Codex lane: `app/backend/**` + `plans/v2-backend.md` + the
`## Codex — Last Task & Resume` / Active Status / Risks / Tasks sections Codex
owns. Do not touch `app/frontend/**`, Claude's `CURRENT.md` section, or
Claude's `next-session-*` doc (README Hard Rules 1–2). Contract changes are
backend-led (Codex owns the schema; announce via `## Cross-Agent Requests`).
For remaining backend work, start with global Blueprint `design-doc` → `spec`
→ `plan` (artifacts under `plans/`) before implementation, not straight code.

## Coordination Protocol — single home

All of it — hard rules, the **CURRENT.md-only-at-major-boundaries +
replace-never-stack rule (Hard Rule 9)**, Log Edit-Lock + Shared File Lock
mechanics, Idle/Usage-Exhaustion Protocol, Integration Checkpoint, Stop/Break
semantics, Required-Postflight clear-safe close, and the Resume-Prompt format
— is defined once in **`agent_handoff/README.md`**. Read it every session;
do not re-state its rules here.

Codex-specific reminders that follow from it:

- Update the `## Codex — Last Task & Resume` section only at **major**
  boundaries and **replace, never stack** "Previous/Latest Codex update"
  blocks. Keep incremental history in `PROGRESS.md` + `plans/v2-backend.md`
  (and a Codex next-session doc if you keep one) — not in `CURRENT.md`.
  Append+archive prior section content verbatim to
  `agent_handoff/archive/<date>-<slug>.md` before replacing if it has
  detail not yet recorded elsewhere (README Hard Rule 1).
- Every session still: update the `## Active Status` heartbeat, claim/release
  the single `## Log Edit-Lock` (stamp real local time from `date`), and end
  **clear-safe** — the final chat message ends with a labeled
  `Safe to clear: yes|no` line + reason and a fenced stamped resume `Prompt:`
  block (first line `# Resume prompt · YYYY-MM-DD HH:MM ±zzzz · Codex
  <session/task>`). The prompt must be in the message, not only the files.
- No commit/push/reset/stash/clean/force-push unless the user or the active
  task brief explicitly authorizes it. Do not start FE-6/7/8 or M-002
  follow-ups without explicit user direction. Surface product/design/UX
  decisions for the user instead of silently changing behavior.
