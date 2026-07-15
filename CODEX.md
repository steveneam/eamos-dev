# CODEX.md

Repo-specific entry point for direct Codex sessions in Eamos. The cross-agent
protocol is **not** restated here — it lives once in
`agent_handoff/README.md`.

## Start Here (every fresh Codex session)

Read in order:

1. `CODEX.md` (this file).
2. `AGENTS.md` — repo-level workflow, ratchet, and backend predictor rules.
3. `agent_handoff/README.md` — **the coordination protocol** (hard rules,
   locks, idle, stop/break, resume-prompt format, full read order).
4. `agent_handoff/CURRENT.md` — live state: Active Status, Log Edit-Lock,
   Shared File Locks, Cross-Agent Requests, Current State, the
   `## Codex — Last Task & Resume` section.
5. `docs/operations/risks-and-guardrails.md`.
6. The relevant active plan (`plans/<feature>/`, or `plans/v2-backend.md` for
   backend history) for the task at hand.
7. `git status --short --branch` and `git diff --stat`.

If the user gives a task brief inside `agent_handoff/CURRENT.md` or chat,
follow that brief before older context.

Commits and PRs carry no AI attribution: no `Co-Authored-By` trailers and no
"Generated with" footer. The tracked `.claude/settings.json` attribution block
is the harness-side enforcement; strip any attribution that still appears
before merge.

## Direct Codex Role — agent-agnostic (2026-07-08)

Codex owns the **whole repo**, same as Claude. There is **no** fixed
Claude=frontend / Codex=backend wall (Steven, 2026-07-08). Codex can edit any
file and take charge of anything — backend, frontend, data/pipeline, docs,
tests, tooling — and may audit/fix Claude's historical work, dependencies, and
branches. Steven picks the active agent by **availability and usage limits**,
not task type. Codex has verified full `D:\eamos` read/write, outbound network,
and runs its own verification (backend `pytest`/`ruff`/`black` + live smoke;
frontend build/`tsc`/`eslint`/`vitest` + browser when doing FE work). The old
"Codex only does grunt work / can't run vitest/server" model was plugin-era
history.

Do not launch WSL/Linux for routine Eamos work. After the 2026-05-28 D-drive
relocation, `vmmemWSL` exhausted host RAM and crashed the computer. Use
Windows-native checks first; WSL-native proof work requires explicit user
approval and the `%USERPROFILE%\.wslconfig` cap (`memory=4GB`,
`guiApplications=false`) to remain in place.

Codex can own any glob in the repo, full-stack. **Handoff hygiene still
applies** (README Hard Rules 1–2): narrate your own work in the
`## Codex — Last Task & Resume` section, and preserve Claude's `CURRENT.md`
section + `next-session-*` doc via append+archive rather than silent overwrite
— you *may* edit or reconcile them when it helps (e.g. Claude is away), never
clobber a narrative. Contract changes are **schema-first**: land the backend
Pydantic schema first, then update the `app/web/lib/backend.ts` TS mirror
(`test_frontend_contract.py` is the canary); if the other agent is mid-flight
on that surface, coordinate via `## Cross-Agent Requests` + locks. For
substantive new work, prefer a Blueprint `design-doc` → `spec` → `plan`
(artifacts under `plans/`) before straight code.

## Product Architecture Invariant

Eamos is a gene- and variant-agnostic search/evidence platform. Do not treat
ABCA4, RPE65, USH2A, or any other named gene/variant as the product boundary.
When fixing report, viewer, protein-architecture, source-cache, evidence, or
search behavior, first locate the shared normalization/selection/orchestration
boundary and make the fix there. Single-gene payloads are acceptable as
fixtures or smoke checks only; they are not sufficient proof that the system is
fixed.

Default verification for these fixes should include a pure/helper-level
regression with synthetic gene-agnostic inputs plus any relevant real fixture.
Browser verification remains useful for rendering and interaction, but it must
not be the only proof for gene-agnostic logic.

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
- Start each session by naming the README Hard Rule 10 deliverable: a net-new
  capability, proprietary Eamos tool/script, measurable performance
  improvement, or stronger verification layer. If the user explicitly
  constrains the session to commit/verify/cleanup/rescue-only work, record
  that lowered bar in `## Active Status` and the resume prompt.
- Every session still: update the `## Active Status` heartbeat, claim/release
  the single `## Log Edit-Lock` (stamp real local time from `date`), and end
  **clear-safe** — the final chat message ends with a labeled
  `Safe to clear: yes|no` line + reason and a fenced stamped resume `Prompt:`
  block (first line `# Resume prompt · YYYY-MM-DD HH:MM ±zzzz · Codex
  <session/task>`). The prompt must be in the message, not only the files.
- Verified normal slices are committed and pushed without asking Steven to
  repeat approval; this is the agent-agnostic standing decision in
  `docs/governance/decisions.md` and README Hard Rule 11. Inspect status, stage
  explicit owned paths, push/open the PR, watch CI, and stop at the existing
  merge-approval gate. Do not infer approval for reset/stash/clean/force-push,
  cleanup deletion, secrets, deploy/cloud mutations, FE-6/7/8, or M-002
  follow-ups. Surface product/design/UX decisions instead of silently changing
  behavior.
- DL-019 explicit staging rule is durable in `docs/governance/decisions.md`:
  before any staging/commit operation, run `git status --short`; never use
  `git add -A`, `git add .`, or `git commit -a`; stage only the current
  change's explicit owned paths with `git add -- <paths>`.
