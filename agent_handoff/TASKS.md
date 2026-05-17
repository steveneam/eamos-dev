# Agent Task Queue

## How To Use

Use this file for live task coordination only. Keep detailed implementation
plans in `plans/*`.

Each task should name:

- owner
- file scope
- status
- verification
- whether another agent may work in parallel

## Current Candidate Tasks

| Task | Suggested owner | Status | Notes |
| ---- | --------------- | ------ | ----- |
| Direct-Codex workflow doc sync | Claude Code | Recommended first task tomorrow | Update stable docs so future Claude sessions understand direct Codex has verified access and can own substantive backend work. Scope: `CLAUDE.md`, `plans/README.md`, `README.md`, `PROGRESS.md`, `ROADMAP.md`; avoid `CHANGELOG.md` and active implementation plans unless necessary. |
| FE-5.6 Workbench viewer refinement | Claude Code | Waiting for user direction | Based on browser pixel-check findings. Should run before FE-6 because it shares Workbench chrome. |
| FE-6 Primer + CRISPR panels | Claude Code | Gated | Build against frozen stub contracts only after user chooses to proceed. |
| FE-7 Alignment + Comparator | Claude Code | Gated | Stub data exists; wait for user direction. |
| FE-8 AskEamos pill | Claude Code, possible small Codex backend review | Gated | Can ship against mock `/api/v1/chat`; live chat is M-002. |
| M-002 real engines | Direct Codex | Gated | Feasibility-gated backend work; do not start without user approval. |
| Backend/API/pipeline task | Direct Codex | Available when scoped | Direct Codex now has verified access and can own meaningful backend work. |
| Cross-agent review | Opposite of implementer | Available when useful | One agent implements; the other reviews for regressions, missing tests, and contract drift. |

## Parallel Work Rule

Parallel work is allowed only when file ownership is explicit and disjoint.

Examples:

- Safe: Claude owns `app/frontend/src/components/workbench/**`; Codex owns
  `app/backend/app/tools/**` and backend tests.
- Risky: both agents editing `app/frontend/src/lib/backend.ts`,
  `plans/v2-frontend.md`, or shared docs at the same time.
