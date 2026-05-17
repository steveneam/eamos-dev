# plans/

Active and historical work plans for Eamos.

## Active plan: v2 rebuild

The Eamos v2 rebuild ports three Claude Design mocks (`Eamos Landing Page.html`, `Eamos Report Page v2.html`, `Eamos Workbench v1.html` from `e:\Web tool\Claude Design\`) into the React/Vite frontend and extends the FastAPI backend to feed the new modules.

| File | Owner | Scope |
| ---- | ----- | ----- |
| [`v2-frontend.md`](v2-frontend.md) | Claude Code | Frontend port: Landing v2, Report v2 (new modules), Workbench (sequence viewer + 4 tools + AI pill). React + Vite, no migration. |
| [`v2-backend.md`](v2-backend.md) | Codex | Backend extensions: Franklin archive, lookup payload v2 fields, lookup-scoped chat endpoint, Workbench engine stubs. Self-contained brief — Codex can execute without reading this README or the mocks. |
| [`frontend-rebuild.md`](frontend-rebuild.md) | Historical | v1 rebuild (Phases 0–2 complete) — predecessor to v2. Keep for reference; do not execute. |

## Parallel work model

Claude Code and Codex run simultaneously on the same git branch.

**Contract surface** — the only place the two streams touch is the API contract:

| Frontend | Backend |
| -------- | ------- |
| `app/frontend/src/lib/backend.ts` (TypeScript interfaces) | `app/backend/app/schemas/*.py` (Pydantic models) |
| `app/frontend/src/lib/sample-report.ts` (mock payload) | `app/backend/app/fixtures/*.json` (fixture payload) |

When a backend payload field changes, both files update. The pre-existing `app/backend/tests/test_frontend_contract.py` parametrized test enforces that every Pydantic field on `LookupResponse` / `RunChatRequest` / `RunChatResponse` / `ReportPayload` / `EvidenceSourceSummary` / `VariantSummaryRow` / `PubMedArticle` appears in its TypeScript counterpart.

**Coordination rules**

1. Backend lands schema changes FIRST. Frontend stubs sample data shaped like the new schema until the backend ships, then swaps to the real call.
2. Either side can take Franklin archival (BE-1) independently — it's pure removal with no contract overlap.
3. Workbench engine endpoints (BE-4) return canned data keyed by variant. Frontend can develop against `workbench/data.js` style sample data until BE-4 lands.
4. Existing chat endpoint `POST /api/v1/runs/{run_id}/chat/stream` is unchanged. A new sibling endpoint `POST /api/v1/chat` is added for lookup/Workbench mode (no run id required).
5. Layer 2 (`/runs`) is frozen. Neither stream changes `LegacyRunsApp.tsx`, the run intake routes, or sign-off code.

**Sync checklist** — when finishing a milestone, before moving to the next:

- TypeScript builds clean: `cd app/frontend && npm run build` (runs `tsc -b` + Vite)
- Backend tests pass: `cd app/backend && python -m pytest tests/ -q`
- `test_frontend_contract.py` passes — every schema field has a TS counterpart
- No imports of `app.tools.franklin` remain anywhere

## Where Codex picks up

> **Workflow note (2026-05-17).** The plugin-mediated `/codex:rescue` flow
> described below is the **historical** delegation path. Direct Codex app
> sessions now have verified full `E:\eamos` workspace (read/write/delete) +
> outbound network access and can own substantive backend/API/pipeline/tool/
> test work directly — not only grunt work. Live cross-agent coordination is in
> `agent_handoff/` (read `agent_handoff/CURRENT.md` + `RISKS.md` before
> editing; update `CURRENT.md` before stopping; one agent at a time until both
> reliably use the folder). The plugin commands below remain accurate for the
> plugin path.

The Codex CLI runs alongside Claude Code via the [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) plugin. **No format mismatch** — per the plugin README, *"this plugin delegates through your local Codex CLI and Codex app server on the same machine"* and *"uses the same Codex install you would use directly"*. Codex writes to the same files Claude Code reads. Auth, config (`config.toml`), and the working tree are shared.

### How to hand the backend plan to Codex

Use `/codex:rescue` from inside this Claude Code session. Suggested prompt:

```
Execute plans/v2-backend.md. The plan is self-contained — every path, schema,
and verification step is in the document. Work top-down through milestones
BE-1 → BE-5. Stop after each milestone, run the verification command listed
under "Verify", and report what changed plus the test output. If anything is
ambiguous, surface it — don't pick silently.
```

Add `--background` to let Codex run while Claude Code proceeds with frontend work in parallel. Track with:

| Command | What |
| ------- | ---- |
| `/codex:status` | Shows running and recently completed Codex jobs |
| `/codex:result` | Returns final output + session id (resumable) |
| `/codex:cancel` | Stops an active background job |
| `/codex:review` | Read-only Codex review of the current working tree |
| `/codex:adversarial-review` | Codex review that challenges design choices |
| `/codex:setup` | Validates the local Codex install and auth |
| `/codex:setup --enable-review-gate` | Adds a `Stop` hook so Codex reviews Claude's work before each stop |

### Why this is safe to run in parallel

Both processes touch the same filesystem. To avoid conflicts:

1. **Different file ownership per milestone.** Each milestone in `v2-frontend.md` and `v2-backend.md` lists explicit file paths. Frontend = `app/frontend/`. Backend = `app/backend/`. No overlap.
2. **Contract changes land backend-first.** When `ReportPayload` gains a field, Codex ships the Pydantic side first; frontend follows with the matching TS interface. Until both are in place, `test_frontend_contract.py` is the canary.
3. **No simultaneous edits to shared docs.** `CHANGELOG.md`, `PROGRESS.md`, `README.md`, `ROADMAP.md` are edited by whoever ships the milestone, after the code change. Avoid editing them mid-flight.
4. **Run `git status` before merge.** Standard hygiene — neither side force-pushes.

## Quick start

```powershell
# Frontend
cd app/frontend
npm run dev      # → http://localhost:5173

# Backend
cd app/backend
python -m uvicorn app.main:create_app --factory --reload
# → http://localhost:8000/api/v1
```
