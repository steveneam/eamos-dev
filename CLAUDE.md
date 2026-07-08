# Eamos — Genomic Intelligence Platform

Variant intelligence platform. Two active surfaces: `/report` (variant evidence report v2) and `/workbench` (sequence viewer + Primer/CRISPR/Align/Compare tools). Legacy patient report at `/runs` is frozen on the v1 design system. Full spec in `README.md`.

## Collaboration model — agent-agnostic (2026-07-08)

**Any agent owns the whole repo.** There is **no** fixed Claude=frontend /
Codex=backend wall. Either agent (Claude or Codex) can edit any file and take
charge of anything — frontend, backend, data/pipeline, docs, tests, tooling —
plus audit and fix the *other* agent's historical work, dependencies, and
branches (including `codex/*` / `agent/*` branches). Steven picks the active
agent per session by **availability and usage limits**, not by task type;
whichever agent is running takes charge of whatever the task needs, full-stack.

This **supersedes** the old "Claude for UI, Codex for Code" division of labour.
Both agents have full `D:\eamos` read/write + network and run their own
verification (frontend build/tsc/eslint/vitest + browser; backend
pytest/ruff/black + live smoke) — the old "Codex = grunt work / can't run
vitest/server" framing was a *plugin-era* limitation, historical only.

What did **not** change: the **coordination + safety machinery** stays in full
(git-safety hard rules, shared-file + log-edit locks, no-delete/append+archive,
schema-first contracts, the parallel-lane sprint model, clear-safe handoff).
Agent-agnostic removes the *role wall*, not the discipline that keeps two
agents from clobbering each other. When both agents are active at once, take
disjoint scopes and coordinate via the locks + `COORDINATION.md` board.

### Coordination protocol — single home

The full cross-agent protocol — hard rules (no-delete/append+archive,
own-section handoff, agent-agnostic parallel lanes, shared-file + log-edit
locks, schema-first contracts, no-idle), the
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
| `plans/` | Active and historical work plans — start at `plans/README.md` for the agent-agnostic parallel-worktree workflow | Planning, picking up active milestones |
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

# R (headless data analysis, BOTH agents — no RStudio GUI needed). Working area is
#   GLOBAL at D:\r-scratch (outside this repo; see its README + demo.R template).
#   Run via: C:\Users\seamegdool\AppData\Local\Programs\R\R-4.6.0\bin\x64\Rscript.exe  (R 4.6.0)
#   Stack: readr/readxl/dplyr/tidyr/stringr/lubridate/ggplot2/scales/data.table/janitor/knitr/rmarkdown.
#   Graphs via ggsave() (PNG/PDF/SVG, no display device). Not on PATH — use the absolute path.
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

### 5. Compounding Learning — leave a ratchet

**Every incident, review, or hard-won lesson should leave a durable artifact behind, not live only in chat.**

The loop is **capture → route → compress → verify it fires** (not capture alone). Route each lesson to *one* canonical home by half-life, and link rather than duplicate:

- Minutes–hours → chat / status update
- This session's state → `agent_handoff/CURRENT.md`
- Known risk / operational guardrail → `agent_handoff/RISKS.md` or the active plan
- Cross-session invariant → `MEMORY.md` / `AGENTS.md` / this file / a skill
- Repeatable action → a script or CLI
- Behavioral guarantee → a test

Two disciplines:
- **Add-only is a leak.** A bloated store is anti-memory — recall degrades. Every add pairs with a prune or correction of the now-stale copy (delete/replace, don't just append).
- **Shared rule layers are proposed, not unilaterally written.** Tests and scripts in owned code can be written directly; changes to `CLAUDE.md` / `AGENTS.md` should be coordinated, because bad or duplicated rules create drift.

(Converged Claude + Codex, 2026-06-20.)

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `python -m graphify query "<question>"` when graphify-out/graph.json exists. Use `python -m graphify path "<A>" "<B>"` for relationships and `python -m graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `python -m graphify update .` to keep the graph current (AST-only, no API cost).

Maintenance practice:
- Follow the Selom-style maintenance model: use cheap AST updates routinely, and run semantic extraction only when Steven explicitly asks or at deliberate release/handoff checkpoints.
- Before any semantic pass, resolve and pin the graphify Python interpreter in `graphify-out/.graphify_python`, then run corpus detection and sanity-check the file/word counts. Keep multi-GB references, fixtures, generated payloads, screenshots, archives, `.tools/`, and vendored/tooling docs out via `.graphifyignore`.
- Do not treat the semantic pass as covered by `graphify update .`; update is AST-only and free, while semantic extraction is LLM-backed and should be occasional.
- Eamos is above graphify's default 5,000-node HTML visualization threshold. Default `graphify export html` may produce an aggregated community view; when Steven wants the Selom-style full raw HTML, use `graphify export html --graph graphify-out/graph.json --node-limit 20000`.
- Full raw HTML can be large/heavy; verify it in Chrome after export when changing visualization output.
