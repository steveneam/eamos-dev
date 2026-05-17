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

- Branch: `checkpoint/v2-batches-2026-05-17` (created from `master`, pushed,
  tracking `origin/checkpoint/v2-batches-2026-05-17`).
- **Committed & pushed 2026-05-17:** `9a27ef0` — one comprehensive checkpoint
  of all ~3 verified batches (variant-search engine, backend hardening S1–S2,
  Workbench FE-4/5/5.5 + Codex hardening, FE-5.6 plan, agent_handoff/ +
  workflow-doc sync). 110 files, +12039 / −2862.
- **`origin/main` untouched at `e0f1763`** — checkpoint is off the default
  branch by design; open a PR when ready.
- Working tree is now **clean**. There is a real git restore point — Codex
  refactoring is low-risk (revert = `git checkout 9a27ef0 -- <path>`).
- Caveat: commit author/committer auto-resolved to
  `Steven Eamegdool <seamegdool@cmri.org.au>` (git user.* not explicitly set);
  fixable via `git commit --amend --reset-author` while it's only on this
  branch, if the user wants different identity.

## Current Agent Coordination State

- Direct Codex has verified filesystem write/delete access in `E:\eamos`.
- Direct Codex has verified outbound network connectivity.
- The old "Codex only for grunt work" assumption came from earlier plugin-mode
  limitations and should not constrain future direct-Codex task assignment.
- For the next few tasks, run Claude Code and Codex one at a time until both
  reliably read and update this folder.

## Active Owner

No active owner. Direct Codex completed the review / analysis /
behavior-preserving refactor of the Claude-owned frontend + planning/handoff
surface on 2026-05-17. Claude Code can resume when the user chooses the next
task.

### Codex task brief — "Review + refactor Claude's folders"

**Goal.** Independent review, analysis, and *behavior-preserving* refactor of
the code/docs Claude has produced so far. Improve clarity, structure, dead
code, duplication, naming, types, and consistency **without changing runtime
behavior or UX**, and surface (don't silently fix) anything that needs a
product/design decision.

**In scope (Claude-owned surface):**
- `app/frontend/src/components/workbench/**` (FE-4/5/5.5 chrome + viewer)
- `app/frontend/src/lib/workbench/**` (gene-window, codon-table, edit-state,
  sample data, tests)
- `app/frontend/src/styles/workbench.css`
- `app/frontend/src/components/report/**` (Report v2 modules)
- `app/frontend/src/lib/{api,backend,sample-report,variant-format}.ts` (+
  `variant-format.test.ts`)
- `app/frontend/src/pages/{WorkbenchPage,ReportPage}.tsx`, `App.tsx`
- `plans/v2-frontend.md`, `plans/README.md`, `agent_handoff/**`,
  `next-session` handoff docs

**Out of scope / DO NOT TOUCH:**
- `app/backend/**` (Codex's own domain — separate task, not this one)
- `/runs` legacy patient flow (`LegacyRunsApp.tsx`, run intake/sign-off) —
  **frozen**, no design changes
- `app/frontend/src/lib/backend.ts` *contract shape* — keep every field; it is
  the canary for `test_frontend_contract.py` (refactor internals only, no
  field renames/removals)
- **Do NOT implement FE-5.6.** It is planned, decisions locked, and is Claude's
  to build. Reviewing/refactoring the *current* FE-5.5 code is in scope;
  pre-empting or changing the FE-5.5 UX is not. If a refactor finding overlaps
  an FE-5.6 item, note it for Claude — don't act on it.
- No behavior/UX changes, no dependency bumps, no broad reformatting churn.

**Verify (direct Codex now has the access to run these):**
- `cd app/frontend && npx vitest run` → must stay green (24/24 + variant-format)
- `cd app/frontend && npm run build` → `tsc -b` + vite clean
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q` →
  40/40 (unchanged — proves no contract drift)
- If any gate cannot run in your environment, say so explicitly and leave it
  for Claude to run — do not report "done" on an unrun gate.

**Git discipline.** Work on `checkpoint/v2-batches-2026-05-17` (or a branch off
it). Commit the refactor as its own revertible commit(s) separate from
`9a27ef0`, `Co-Authored-By` trailer. Do not touch `origin/main`. Do not
force-push. No commits unless the work is verified.

**Handoff discipline (now a hard standing rule).** Read this file +
`agent_handoff/RISKS.md` before editing; update the "Required Post-Task Update"
block below before stopping (files changed, verification run, tests not run,
risks, recommended next step). The next session resumes from this file, not
chat memory.

**Deliverable.** A findings report (severity-ranked: structural / dead code /
duplication / type-safety / naming / doc drift), the behavior-preserving
refactor applied + verified, and anything product-shaping surfaced for Claude
+ the user — not silently changed.

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

- Checkpoint commit/push to a feature branch is **done & user-authorized**
  (`9a27ef0`). Still: no force-push, no rewriting `9a27ef0`, no pushing to
  `origin/main`.
- Do not stash. Do not reset/clean/discard.
- Do not auto-start FE-6/FE-7/FE-8 or M-002 real engines.
- **Do not implement FE-5.6** (Claude's, decisions locked) — review/refactor
  of existing FE-5.5 only.
- Do not modify shared project docs just to tidy them (doc drift → report it).

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
- All of the above committed as `9a27ef0` on
  `checkpoint/v2-batches-2026-05-17` (pushed). No re-verification was run for
  the commit itself (no code changed in the commit/doc-sync turns).

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

- Task completed: Direct Codex review / analysis / behavior-preserving refactor
  of the Claude-owned frontend + planning/handoff surface. No FE-5.6 behavior
  or UX was implemented.
- Owner: Direct Codex.
- Files changed:
  - `app/frontend/src/components/workbench/ToolIcon.tsx` (new component-only
    split from mixed workbench tool metadata)
  - `app/frontend/src/components/workbench/ToolBar.tsx`
  - `app/frontend/src/components/workbench/WorkbenchShell.tsx`
  - `app/frontend/src/components/workbench/tools.tsx`
  - `app/frontend/src/components/workbench/viewer/zoom-config.ts` (new
    constants-only zoom config)
  - `app/frontend/src/components/workbench/viewer/ZoomSlider.tsx`
  - `app/frontend/src/components/workbench/viewer/CodonDetail.tsx`
  - `app/frontend/src/components/workbench/viewer/EditPopoverV2.tsx`
  - `app/frontend/src/components/workbench/viewer/SequenceViewerV2.tsx`
  - `app/frontend/src/lib/variant-format.ts`
  - `app/frontend/src/pages/ReportPage.tsx`
  - `agent_handoff/CURRENT.md`
  - `agent_handoff/TASKS.md`
- Findings report:
  - Structural: workbench tool metadata and the icon component shared one module,
    and zoom constants lived in the component module. Split them so Fast Refresh
    sees component-only files without changing rendered output.
  - Type-safety: edit-popover substitution previews used `as never`; replaced
    with a base guard and typed substitution callbacks.
  - Dead code: `CodonDetail` exported local-only `ROW_BP` and re-exported an
    unused `posDisplay`; removed those exports and the stale eslint-disable.
  - Naming/consistency: `variant-format.ts` had unnecessary escaped hyphens in
    a character class; cleaned without changing the regex meaning.
  - Doc drift: no product docs changed. `agent_handoff/` already reflected the
    active task; updated status only.
  - Product-shaping: none silently changed. FE-5.6-overlapping items remain for
    Claude; this pass did not alter UX or implement planned refinements.
- Verification run:
  - `cd app/frontend && npx vitest run` - 24 passed.
  - `cd app/frontend && npm run build` - clean (`tsc -b` + Vite; existing
    chunk-size warning only).
  - `cd app/backend && python -m pytest tests/test_frontend_contract.py -q` -
    40 passed.
  - Extra: `cd app/frontend && npm run lint` - clean after refactor.
- Tests not run: no browser/pixel check; no UX behavior changed, and FE-5.6
  browser work remains Claude-owned.
- Risks or blockers:
  - The tracked `.claude/skills/scripts/skills/planner/quality_reviewer` files
    were restored and are readable.
  - A renamed leftover filesystem shell,
    `.claude/skills/scripts/skills/planner/quality_reviewer_bad/`, remains
    corrupt/unremovable while E: is mounted. `chkdsk E:` read-only found no
    errors; `chkdsk E: /f` requested dismount/restart scheduling. A local
    `.git/info/exclude` entry prevents git from traversing that shell. Full
    cleanup requires running filesystem repair when the E: volume can be
    dismounted or checked at restart.
- Commit: `Refactor Workbench frontend surface` on `checkpoint/v2-batches-2026-05-17`; not pushed at handoff time.
- Recommended next step: Claude Code can resume for FE-5.6, or the user can assign a scoped backend/API task to direct Codex.



