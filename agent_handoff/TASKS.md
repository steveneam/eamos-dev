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
| Direct-Codex workflow doc sync | Claude Code | DONE 2026-05-17 | Stable docs corrected; memory synced. |
| Checkpoint commit + push | Claude Code | DONE 2026-05-17 | `9a27ef0` on `checkpoint/v2-batches-2026-05-17` (pushed); `origin/main` preserved. |
| Review + refactor Claude's folders | Direct Codex | DONE 2026-05-17 | Behavior-preserving lint/type/refactor pass on FE-5.5 frontend surface. Verified: vitest 24/24, frontend build clean, frontend contract 40/40, eslint clean. Committed separately as `Refactor Workbench frontend surface`, not pushed at handoff time. |
| FE-5.6 Workbench viewer refinement | Claude Code | Ready after Codex review | Decisions locked in `plans/v2-frontend.md` "FE-5.6". Runs before FE-6 (shares chrome). |
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



