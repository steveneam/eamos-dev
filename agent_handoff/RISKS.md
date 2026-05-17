# Agent Risks And Guardrails

## Dirty Worktree

The worktree is intentionally dirty and contains verified work.

Guardrails:

- Do not commit unless the user asks.
- Do not stash unless the user asks.
- Do not reset, checkout, clean, or discard changes.
- Do not treat untracked files as junk.

## Old Agent-Split Assumptions

Some existing docs say or imply Claude Code owns substantive work while Codex
does backend/grunt/review work through the plugin.

Current interpretation:

- Those docs explain the historical workflow.
- They are not a technical restriction on direct Codex sessions.
- Direct Codex can do meaningful backend work when explicitly delegated.

## Shared Files

High-conflict files:

- `CHANGELOG.md`
- `PROGRESS.md`
- `ROADMAP.md`
- `CLAUDE.md`
- `plans/*`
- `app/frontend/src/lib/backend.ts`
- backend Pydantic schema files when frontend contract work is active

Guardrail:

- Update shared docs at task boundaries, not while another agent is actively
  editing adjacent work.

## Gated Work

Do not start without explicit user direction:

- FE-6
- FE-7
- FE-8
- M-002 real engines
- commits or branch surgery
- broad cleanup/refactors

## Verification Expectations

Use focused verification scaled to the task:

- Backend/API/schema: `cd app/backend && python -m pytest tests/ -q`
- Contract: `cd app/backend && python -m pytest tests/test_frontend_contract.py -q`
- Frontend: `cd app/frontend && npm run build`
- Frontend unit tests: `cd app/frontend && npm run test`
- Browser/pixel checks: required after meaningful Workbench UI changes.

If a check is not run, record it in `agent_handoff/CURRENT.md`.

