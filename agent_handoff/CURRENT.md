# Current Agent State

## Current Objective

Keep Claude Code and direct Codex synchronized while the project moves from the
old plugin-limited Codex workflow to direct Codex sessions with verified full
workspace and network access.

Immediate practical objective: resume from the paused Eamos checkpoint without
conflicting edits or stale assumptions.

## Current Product Checkpoint

- Backend hardening Sessions 1 and 2 are complete and verified.
- Workbench FE-5.5 is complete and verified.
- Workbench FE-5.6 is planned next, based on browser pixel-check findings.
- FE-6/FE-7/FE-8 and M-002 real-engine work should not start until the user
  explicitly chooses the next direction.

## Current Worktree State

- Branch: `master`
- Nothing is committed.
- The worktree is intentionally dirty with a large verified batch spanning
  backend, frontend, tests, fixtures, docs, and plans.
- The dirty worktree should be treated as intentional project state, not as a
  cleanup target.

## Current Agent Coordination State

- Direct Codex has verified filesystem write/delete access in `E:\eamos`.
- Direct Codex has verified outbound network connectivity.
- The old "Codex only for grunt work" assumption came from earlier plugin-mode
  limitations and should not constrain future direct-Codex task assignment.
- For the next few tasks, run Claude Code and Codex one at a time until both
  reliably read and update this folder.

## Active Owner

No active owner. The recommended stable-doc workflow sync is **DONE** (Claude
Code, 2026-05-17 — see "Current status" below). User should choose the next
task and owner.

Likely next owner if continuing frontend refinement:

- Claude Code: FE-5.6 Workbench viewer refinement.

Likely next owner if continuing backend/API work:

- Direct Codex: scoped backend/API/pipeline/tool/test task.

## Files In Play

Current live coordination files:

- `agent_handoff/README.md`
- `agent_handoff/CURRENT.md`
- `agent_handoff/TASKS.md`
- `agent_handoff/DECISIONS.md`
- `agent_handoff/RISKS.md`
- `agent_handoff/WORKTREE_INVENTORY.md`
- `AGENT_HANDOFF.md` as a legacy pointer to this folder

Current project areas with major uncommitted work:

- `app/backend/**`
- `app/frontend/**`
- `plans/**`
- `README.md`
- `CHANGELOG.md`
- `PROGRESS.md`
- `ROADMAP.md`
- `.claude/**`

## Do Not Touch Without Explicit User Approval

- Do not commit.
- Do not stash.
- Do not reset, checkout, clean, or otherwise discard changes.
- Do not auto-start FE-6/FE-7/FE-8.
- Do not auto-dispatch M-002 real engines.
- Do not modify shared project docs just to tidy them.

## Canonical Resume Context

Agents should read, in this order:

1. `agent_handoff/README.md`
2. `agent_handoff/CURRENT.md`
3. `agent_handoff/RISKS.md`
4. `CLAUDE.md`
5. `PROGRESS.md`
6. `CHANGELOG.md`
7. `ROADMAP.md`
8. Relevant active plan, usually `plans/v2-frontend.md` or `plans/v2-backend.md`
9. `C:\Users\seamegdool\.claude\plans\next-session-eamos-hardening.md`
10. `git status --short`
11. `git diff --stat`

## Latest Verification Snapshot

Last recorded verification in project docs:

- Frontend FE-5.5: `npx vitest run` 24/24, `npm run build` clean.
- Backend hardening Session 2: offline pytest 86 passed / 4 skipped.
- Frontend contract: 40/40.
- `test_tool_invariants.py`: 5 passed.
- Browser pixel-check for FE-5.5 surfaced FE-5.6 planned fixes; that pass is
  pending implementation.

## Required Post-Task Update

At the end of any agent task, update this section:

- Task completed:
- Owner:
- Files changed:
- Verification run:
- Tests not run:
- Risks or blockers:
- Recommended next step:

Current status:

- Task completed: stable-doc workflow sync — corrected the now-historical
  "Codex = grunt-work-only / plugin-limited / can't run vitest-vite-server"
  framing so future Claude Code + direct Codex sessions stay aligned. Also
  recorded FE-5.5 pixel-check → FE-5.6 plan state (planning done in the prior
  Claude turn; no app code changed).
- Owner: Claude Code.
- Files changed (docs only, no app code, no commit):
  `CLAUDE.md` (new "Direct Codex vs. plugin delegation" subsection +
  clear-safe + golden-rule pointer), `plans/README.md` (historical-plugin
  note), `README.md` (network-clearance line + plugin pointer),
  `PROGRESS.md` (new Session 19 note), `ROADMAP.md` (Codex-dispatch blocker
  row → historical), `agent_handoff/CURRENT.md` (this update);
  plus 3 Claude memory notes corrected + `MEMORY.md` index hooks
  (`feedback_claude_codex_division`, `feedback_codex_grunt_work_delegation`,
  `reference_codex_parallel_workflow`); and from the prior turn
  `plans/v2-frontend.md` (FE-5.6 milestone) +
  `~/.claude/plans/next-session-eamos.md`.
- Not touched (per scope): `CHANGELOG.md`, `plans/v2-backend.md`,
  `app/backend/**`, `app/frontend/**`. No commit/stash/reset; dirty worktree
  preserved intact.
- Verification run: none — docs/memory only, no code path changed.
- Tests not run: vitest / pytest / build / contract — not applicable to a
  docs-only sync (last recorded project verification unchanged: FE-5.5 vitest
  24/24, build clean, contract 40/40, backend pytest 86p/4s).
- Risks or blockers: none introduced. Note: `plans/v2-frontend.md` and
  `plans/v2-backend.md` still describe the plugin-era parallel-run model in
  their execution narratives — left intact per scope (no current policy line
  directly conflicts); revisit if those plans are next edited.
- Recommended next step: user picks — (a) Claude Code executes **FE-5.6**
  (`plans/v2-frontend.md`, decisions locked) one verified unit at a time, or
  (b) a scoped backend/API task to **direct Codex**. One agent at a time until
  both reliably use this folder.
