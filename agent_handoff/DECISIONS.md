# Agent Coordination Decisions

## 2026-05-17: Create `agent_handoff/` As Universal Sync Point

Decision:

- Use `agent_handoff/` as the live operational coordination folder for Claude
  Code and direct Codex.

Reasoning:

- `CHANGELOG.md` should stay historical.
- `PROGRESS.md` should stay a session/build log.
- `ROADMAP.md` should stay strategic.
- `plans/*` should stay detailed execution plans.
- Agent handoffs are tactical and can be messy; they need their own workspace.

Implication:

- Both agents should read `agent_handoff/CURRENT.md` before editing.
- Both agents should update `agent_handoff/CURRENT.md` after finishing.

## 2026-05-17: Direct Codex Access Changes The Work Dynamic

Decision:

- Treat direct Codex as capable of substantive backend/API/pipeline/tool/test
  work, not only grunt work.

Reasoning:

- The old split came from plugin-mode limitations and access uncertainty.
- Direct Codex has now verified workspace filesystem access and outbound network
  connectivity.
- Direct Codex can inspect the full repo, run commands, edit files, and verify
  backend work directly.

Implication:

- Claude Code no longer needs to babysit Codex with excessive context for every
  backend task if the task is scoped and this folder is current.
- The user can delegate real backend tasks directly to Codex.
- Claude Code remains valuable for frontend/design/product context and for
  reviewing direct-Codex backend patches when useful.

## 2026-05-17: Sequential First, Parallel Later

Decision:

- Run Claude Code and Codex one at a time initially.
- Move to separate terminals only after both agents consistently use
  `agent_handoff/`.

Reasoning:

- The repo has a large intentional dirty worktree.
- The old assumptions are still present in existing docs and Claude's current
  context.
- Sequential handoff reduces accidental overlap while the new protocol settles.

Implication:

- At first, every task should end with a `CURRENT.md` update.
- Once stable, parallel work is acceptable with explicit disjoint file scopes.

## 2026-05-17: Stable Docs Need A Small Workflow Sync

Decision:

- Update stable workflow docs so future Claude Code sessions do not keep
  treating old direct-Codex limitations as current.

Files that should be updated:

- `CLAUDE.md`: primary repo behavior file. It currently says Codex owns grunt
  work and implies Codex cannot run server/build/live verification. That should
  be revised for direct Codex while preserving the UI/backend ownership default.
- `plans/README.md`: currently describes the Claude Code plugin `/codex:rescue`
  flow as the Codex path. It should distinguish historical/plugin delegation
  from direct Codex sessions.
- `README.md`: small update only where it points to the old plugin-based
  workflow or stale network-clearance assumptions.
- `PROGRESS.md`: add a short session note that direct Codex access was verified
  and `agent_handoff/` was created.
- `ROADMAP.md`: small hygiene update, especially the plugin-specific Codex
  dispatch reliability row.

Files that should usually not be updated for this workflow sync:

- `CHANGELOG.md`: leave historical entries intact.
- `plans/v2-backend.md` and `plans/v2-frontend.md`: treat as active/historical
  execution plans; do not churn unless the implementation plan itself changes.

Implication:

- This doc-sync is a good first Claude Code task tomorrow because it aligns
  Claude's future behavior before new implementation work starts.
- Keep edits small and surgical; no app code.
