# Eamos — Genomic Intelligence Platform

Variant intelligence platform. Two active surfaces: `/report` (variant evidence report v2) and `/workbench` (sequence viewer + Primer/CRISPR/Align/Compare tools). Legacy patient report at `/runs` is frozen on the v1 design system. Full spec in `README.md`.

## Collaboration model — Golden rule

**Claude for UI, Codex for Code.** Default division of labour:

- **Claude Code** owns the frontend: UI design, React/component work,
  copywriting, the frontend plan (`plans/v2-frontend.md`, `app/frontend/**`).
- **Codex** owns the backend: API, pipeline, data plumbing, the backend plan
  (`plans/v2-backend.md`, `app/backend/**`).

The default, not a hard wall — the user may swap roles or ask one to
review the other's work; follow explicit per-task instructions when given.
Direct Codex app sessions (verified 2026-05-17) have full workspace
read/write + network and can own substantive backend/test work with their own
verification — the old "Codex = grunt work only / can't run vitest/server"
framing was a *plugin-era* limitation, historical only.

### Coordination protocol — single home

The full cross-agent protocol — hard rules (no-delete/append+archive,
own-section-only, parallel-mode lanes, shared-file + log-edit locks,
backend-led contracts, no-idle, explicit role swaps), the
**CURRENT.md-only-at-major-boundaries + replace-never-stack rule** (Hard Rule
9), the Idle/Usage-Exhaustion Protocol, Integration Checkpoint, Stop/Break
semantics, and the Resume-Prompt format — lives in **one place**:
**`agent_handoff/README.md`**. Read it every session; do not re-state its
rules here or elsewhere (change a rule once, there).

Operational summary: live state is `agent_handoff/CURRENT.md` (state only —
update your own section at *major* boundaries, replace don't stack; the
`## Active Status` heartbeat + `## Log Edit-Lock` release happen every
session). Risks → `agent_handoff/RISKS.md`. Per-task history → `PROGRESS.md`
+ Claude's own `~/.claude/plans/next-session-eamos.md` (Claude's rolling log;
keep incremental detail there, not in CURRENT.md). Every task/break still ends
**clear-safe**: final chat message ends with a labeled `Safe to clear: yes|no`
line + a fenced stamped resume `Prompt:` (format in README.md).

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `README.md` | Full project spec: surfaces, database stack, report structure, HGVS table, invariants | Onboarding, spec questions, product vision, invariants |
| `PROGRESS.md` | Session-by-session build log | Checking what has been built |
| `CHANGELOG.md` | Feature changelog | Reviewing recent changes |
| `DESIGN.md` | Design system v2 — tokens, components, Workbench layout chrome | Any frontend styling work |
| `ROADMAP.md` | Active phases (Layer 1 v2 + Workbench) and future cycles | Understanding build sequence |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `app/` | Frontend (React/Vite/Tailwind) + Backend (FastAPI/Python) + shared contracts | All code work |
| `plans/` | Active and historical work plans — start at `plans/README.md` for the parallel Claude Code (frontend) ↔ Codex (backend) workflow | Planning, picking up active milestones |
| `docs/` | Catalogue of Eamos-original scripts, CLIs, algorithms, and orchestration logic (`proprietary/`) | Finding custom project-generated systems (EP-VLEx, search input resolution) |
| `archive/` | Retired drafts and historical session notes (includes `archive/franklin/` once BE-1 lands) | Historical context only |
| `.claude/` | Agent roles, conventions, output styles, skills | Workflow, agent config, conventions |

## Development

```
# Start frontend dev server
cd app/frontend && npm run dev
# → http://localhost:5173

# Node.js (Windows): IT-managed system install at C:\Program Files\nodejs\node.exe (already on PATH)
# Backend root: app/backend/
# LLM default: provider=mock (offline dev) — never assume use_real_apis=True
```

## Coding Guidelines

Behavioral guidelines to reduce common LLM coding mistakes.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.
