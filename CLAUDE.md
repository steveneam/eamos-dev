# Eamos — Genomic Intelligence Platform

Variant intelligence platform. Two active surfaces: `/report` (variant evidence report v2) and `/workbench` (sequence viewer + Primer/CRISPR/Align/Compare tools). Legacy patient report at `/runs` is frozen on the v1 design system. Full spec in `README.md`.

## Collaboration model — Golden rule

**Claude for UI, Codex for Code.** Default division of labour:

- **Claude Code** owns the frontend: UI design, React/component work,
  copywriting, and the frontend plan (`plans/v2-frontend.md`,
  `app/frontend/**`).
- **Codex** owns the backend: API, pipeline, data plumbing, and the backend
  plan (`plans/v2-backend.md`, `app/backend/**`).

This is the default, not a hard wall. The user may swap roles or ask one to
review/check the other's work — follow explicit per-task instructions when
given; otherwise apply the golden rule. Ownership is a default, not a technical
limit — see "Direct Codex vs. plugin delegation" below; live cross-agent
coordination state lives in `agent_handoff/`.

### Direct Codex vs. plugin delegation

**Direct Codex app sessions** (verified 2026-05-17) have full read/write
access to the `E:\eamos` workspace and outbound network connectivity. Direct
Codex can own substantive backend/API/pipeline/tool/test work and run its own
backend verification (`pytest`, live smoke) when a task is scoped to it — it is
**not** limited to grunt work. The earlier "Codex = grunt work only / Claude
must run all verification / Codex sandbox can't run a server or vitest/vite"
model was a constraint of the **historical plugin-mediated** `codex:rescue`
flow, not a property of direct Codex; treat that framing in older docs/memory
as historical.

Coordination is via `agent_handoff/` (live operational source of truth — read
`agent_handoff/CURRENT.md` + `agent_handoff/RISKS.md` before editing, update
`CURRENT.md` before stopping). Run one agent at a time until both reliably use
`agent_handoff/`; then parallel terminals are fine with explicit disjoint file
scopes (backend/schema lands before frontend contract consumers; no
simultaneous edits to shared docs). Either agent still makes a deliberate,
scoped handoff at a **verified task boundary** — never mid-task, never on
trivial turns. Routine `CHANGELOG`/`PROGRESS`/`README`/`ROADMAP` prose and
cleanup/lint/dead-code/doc-sync sweeps remain natural Codex work; the
substantive design/code stays with its owning agent.

### Every task ends clear-safe

The user `/clear`s and starts a fresh session between tasks. A task is not
"done" until it is **clear-safe**: (1) a paste-able resume prompt, (2) a
self-contained handoff doc at `~/.claude/plans/next-session-eamos.md` (state ·
done & verified · next · gotchas · resume prompt; readable cold in ~3 min),
(3) `agent_handoff/CURRENT.md` plus `CHANGELOG`/`PROGRESS`/active
`plans/*`/memory all synced and mutually consistent. Do not report a task
complete until these exist.

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
| `docs/` | Architecture guides, API research, design brief, design system | Database API details, architecture decisions, design |
| `pitch/` | Pitch deck outline and speaking notes | Presentation work |
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
