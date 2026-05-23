# Archived handoff — Direct Codex, Blueprint-skill cleanup (2026-05-17)

> Superseded by Claude Session 21 (FE-5.6 Unit A). Preserved here because the
> `agent_handoff/CURRENT.md` "Required Post-Task Update" block is a single
> rolling block; this is Codex's prior task record + its resume prompt,
> verbatim, so nothing is lost. The durable Codex backend-planning guidance
> still lives in `CURRENT.md` ("Active Owner" → "Next intended Direct Codex
> backend flow", the top "Next backend objective") and in `CODEX.md`.

## Current status (as left by Codex)

- Task completed: cleaned accidental repo-local Blueprint skill install, restored Claude project skill files, and installed Blueprint globally.
- Owner: Direct Codex.
- Files changed:
  - `CODEX.md` now requires every final task closeout to include explicit
    clear-safe assurance (`Safe to clear: yes/no`) plus a clearly labeled
    `Prompt:` block.
  - `agent_handoff/CURRENT.md` now includes `Clear-safe status` in the required
    post-task update template.
  - `CODEX.md` now records the backend planning rule: remaining backend work
    starts with global Blueprint `design-doc` -> `spec` -> `plan`, with
    reviewable `plans/` artifacts before implementation.
  - `agent_handoff/CURRENT.md` now records the same next backend objective
    outside the resume prompt so fresh sessions do not depend on chat memory.
  - No Blueprint skill files remain in the project working tree.
  - Accidental repo-local generated paths were removed, including `.agents/`,
    `skills-lock.json`, `skills/`, `.aider-desk/`, `.adal/`, `.augment/`,
    `.bob/`, and other tool-specific generated folders.
  - `.claude/skills/refactor/*` in the project was restored to the tracked
    pre-Blueprint state.
  - Global user-level Blueprint skills were installed outside the repo under
    `C:\Users\seamegdool\.agents\skills\{address-pr-feedback,branch,browser-verify,commit,design-doc,implement,plan,refactor,review,spec,tdd}`.
  - The Skills CLI also copied those global Blueprint skills for Claude Code
    under `C:\Users\seamegdool\.claude\skills\...`.
  - `CODEX.md` (new direct-Codex operating guide: startup order, role, standing
    rules, backend planning rule, required clear-safe postflight,
    resume-prompt shape)
  - `agent_handoff/README.md` (requires Codex to read `CODEX.md`, uses
    `git status --short --branch`, and makes clear-safe + resume prompt a
    standing rule)
  - `agent_handoff/CURRENT.md` (adds `CODEX.md` to canonical resume context and
    records this clear-safe handoff + Blueprint skill check)
- Verification run:
  - `npx skills --help` (confirmed local Skills CLI works)
  - `npm view skills version description bin` (confirmed CLI package metadata)
  - `npx skills add owainlewis/blueprint --list` (Blueprint exposes 11 skills:
    `address-pr-feedback`, `branch`, `browser-verify`, `commit`, `design-doc`,
    `implement`, `plan`, `refactor`, `review`, `spec`, `tdd`)
  - `npx skills add owainlewis/blueprint --skill review --agent codex -y --copy`
    (installed `review` to `.agents/skills/review`)
  - `npx skills add owainlewis/blueprint --all --agent codex -y --copy`
    (installed all 11 Blueprint skills; CLI reported "Installing to all 55
    agents" despite `--agent codex`; this repo-local install was later removed)
  - Removed accidental repo-local generated skill folders after verifying each
    resolved path stayed under `E:\eamos`.
  - `git restore -- .claude\skills\refactor` (restored tracked Claude project
    refactor skill files that the broad install had overwritten)
  - `npx skills add owainlewis/blueprint -g --skill '*' --agent codex claude-code -y --copy`
    (installed all 11 Blueprint skills globally for Codex/Claude Code)
  - `npx skills list --json` now returns `[]`, confirming no project-local
    skills are registered.
  - `npx skills list -g --json` confirms global Blueprint skills are registered.
  - `Get-ChildItem C:\Users\seamegdool\.agents\skills` confirms all 11 Blueprint
    skill directories exist globally.
  - `git status --short --branch` confirms the repo is dirty only with the
    intended docs/handoff changes plus `CODEX.md`.
  - Documentation inspection after adding durable backend planning memory.
- Tests not run: app tests not applicable; skill install/docs-only check.
- Risks or blockers:
  - Working tree is intentionally dirty only with Codex-memory docs/handoff
    updates; no Blueprint skill folders remain in the repo.
  - Branch remains ahead of origin by one unpushed Direct Codex refactor commit.
  - Blueprint is not Claude-only on paper; global install completed. This
    current Codex session may not auto-discover newly installed global skills
    until a fresh session, but Direct Codex can still use them manually by
    reading `C:\Users\seamegdool\.agents\skills\<name>\SKILL.md`.
  - Global install output said each skill was copied for both Codex and Claude
    Code. `npx skills list -g --json` reports the `.agents\skills` entries with
    agent metadata `Claude Code`; treat that as CLI metadata oddity unless a
    fresh Codex session fails to discover them.
  - Global install reported `refactor` overwrote a Claude Code global skill
    target. This is outside the project working tree; if Claude's global
    `refactor` behavior matters, review
    `C:\Users\seamegdool\.claude\skills\refactor\SKILL.md`.
  - Leftover filesystem shell
    `.claude/skills/scripts/skills/planner/quality_reviewer_bad/` remains
    corrupt/unremovable until E: can be repaired/dismounted; tracked
    `quality_reviewer` files are restored and readable.
- Commit/push state: not committed; branch is `checkpoint/v2-batches-2026-05-17`
  ahead of `origin/checkpoint/v2-batches-2026-05-17` by one prior commit.
- Recommended next step: in the next backend session, use the global Blueprint
  `design-doc`, `spec`, and `plan` skills for the remaining backend work to
  produce reviewable artifacts under `plans/` before implementation. Commit the
  repo docs/handoff update separately if the user wants this coordination state
  preserved in git.
- Clear-safe status: safe to clear this Codex session now. There is no active
  tool/process/task in progress; repo-local Blueprint skill folders were
  removed; remaining working-tree changes are intentional docs/handoff updates
  (`CODEX.md`, `agent_handoff/CURRENT.md`, `agent_handoff/README.md`).
- Resume prompt (Codex):
  `Resume Eamos from agent_handoff/CURRENT.md. Read CODEX.md,
  agent_handoff/CURRENT.md, agent_handoff/RISKS.md, and git status --short
  --branch first. Current branch is checkpoint/v2-batches-2026-05-17, ahead of
  origin by one unpushed Direct Codex refactor commit, with uncommitted
  CODEX/agent_handoff docs only. Accidental repo-local Blueprint skill folders
  were removed and project .claude/skills/refactor was restored. Blueprint is
  installed globally under C:\Users\seamegdool\.agents\skills and
  C:\Users\seamegdool\.claude\skills. For remaining backend work, use
  Blueprint design-doc, spec, and plan skills to produce reviewable artifacts
  under plans/ before implementation. Do not start FE-6/FE-7/FE-8/M-002 without
  explicit approval. Before editing, restate file scope; before stopping, update
  agent_handoff/CURRENT.md with clear-safe handoff and next resume prompt.`
