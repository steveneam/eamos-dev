# Agent Handoff Protocol

This folder is the shared operational source of truth for Claude Code and
direct Codex sessions.

Use it when:

- starting a fresh agent session
- finishing a task
- switching work between Claude Code and Codex
- resolving doubt about ownership, dirty files, next steps, or verification

## Why This Folder Exists

The earlier project split treated Claude Code as the main driver and Codex as a
backend/grunt-work/review delegate. That was reasonable at the time because
Codex was being used through a Claude Code plugin and had apparent limitations:

- unreliable or constrained network/API access
- uncertainty about whether Codex could run meaningful backend verification
- plugin-mediated context handoff
- higher risk that Codex would lack the latest project state

That assumption has changed for direct Codex app sessions. Direct Codex access
has now been verified for:

- reading the full repo at `E:\eamos`
- writing and deleting files in the workspace
- outbound network connectivity
- inspecting backend/frontend contracts, tests, docs, and plans

So the old split should now be understood as a coordination convention, not a
technical limitation. Codex can take substantive backend/API/pipeline/tooling
work directly when the user delegates it. Claude Code remains strong for UI,
product/design-heavy frontend work, context-rich planning, and visual iteration.

## Source-Of-Truth Roles

This folder is for live coordination only.

- `agent_handoff/CURRENT.md`: current operational state, owner, files in play,
  verification, and next step.
- `agent_handoff/TASKS.md`: queued or candidate tasks with suggested ownership.
- `agent_handoff/DECISIONS.md`: decisions that should not be rediscovered.
- `agent_handoff/RISKS.md`: known hazards, failing/pending checks, and do-not-touch
  constraints.
- `agent_handoff/archive/`: old handoffs after they are superseded.

Do not use this folder as a replacement for project history:

- `CHANGELOG.md` remains the historical feature/change record.
- `PROGRESS.md` remains the session/build log.
- `ROADMAP.md` remains the strategic product/build sequence.
- `plans/*` remain detailed execution plans.

## Required Agent Behavior

Before starting work, both Claude Code and Codex should:

1. Read `agent_handoff/CURRENT.md`.
2. Read `agent_handoff/RISKS.md`.
3. Run `git status --short`.
4. State the intended owner, task, and file scope before editing.

After finishing work, the active agent should update:

1. `agent_handoff/CURRENT.md` with changed files, verification, and next step.
2. `agent_handoff/TASKS.md` if task status changed.
3. `agent_handoff/RISKS.md` if new risks, failing tests, or blocked areas were found.
4. `CHANGELOG.md`, `PROGRESS.md`, `ROADMAP.md`, or `plans/*` only when the task
   actually changes project state and the user expects those docs to be synced.

## Coordination Model

Default sequential mode, while getting both agents in sync:

- Run one agent at a time.
- Require the agent to read `agent_handoff/CURRENT.md` before edits.
- Require the agent to update `agent_handoff/CURRENT.md` before stopping.
- The next agent starts from that file, not from chat memory.

Parallel mode, once both agents are aligned:

- Claude Code and Codex may run in separate terminals only with explicit file
  ownership.
- Do not let both agents edit the same files at the same time.
- Backend/schema changes should land before frontend contract consumers.
- Shared docs should be updated at the end of a task, not mid-flight by both agents.

## Practical Ownership

Suggested defaults:

- Claude Code: frontend UI, visual design, Workbench layout, product copy,
  browser/pixel iteration, frontend plans.
- Direct Codex: backend APIs, evidence tools, data pipelines, schema contracts,
  tests, live/API verification, security hardening, backend plans, adversarial
  code review.

The user can override this on any task.

