# plans/

Active and historical work plans for Eamos.

## Active Frontend Source Of Truth

The live Eamos frontend is the Next.js app in `app/web`. Production build,
browser proof, Vercel guard, and new product work target `app/web`.

The historical Vite implementation was retired on 2026-07-15 after its useful
pure tests moved into `app/web`. Git history preserves the old implementation;
do not recreate a second hand-maintained frontend or contract mirror.

## Active And Historical Plans

| File | Owner | Scope |
| ---- | ----- | ----- |
| [`landing-free-public/plan.md`](landing-free-public/plan.md) | Codex | Active free-public landing reposition, monetization removal, and reproducible real-product feature captures. |
| [`v2-backend.md`](v2-backend.md) | Codex | Backend extensions and historical backend ledger. Prefer newer scoped docs when present. |
| [`v2-frontend.md`](v2-frontend.md) | Historical | Superseded frontend port notes for the old Vite app. Active frontend work now lives in `app/web`. |
| [`frontend-rebuild.md`](frontend-rebuild.md) | Historical | Original React/Vite rebuild. Keep for reference; do not execute. |

## Contract Surface

The main backend/frontend touch point is the API contract:

| Frontend | Backend |
| -------- | ------- |
| `app/web/lib/backend.ts` (TypeScript interfaces) | `app/backend/app/schemas/*.py` (Pydantic models) |
| `app/web/lib/rpe65-sample.json` and live API helpers | `app/backend/app/fixtures/*.json` (fixture payloads) |

When a backend payload field changes, backend schema changes land first, the
active `app/web` TypeScript contract is updated, and
`app/backend/tests/test_frontend_contract.py` remains the canary.

## Coordination Rules

Ownership is **agent-agnostic** (Steven, 2026-07-08) — either agent (Claude or
Codex) can own any plan/glob, full-stack; the "Owner" column above is historical
attribution, not a lane. These rules are about *ordering and safety*, not roles:

1. Backend lands schema changes first (schema-first contract; the same agent can
   do both ends).
2. Current frontend product work targets `app/web/`.
3. Do not recreate the retired `app/frontend/` Vite application or a second
   hand-maintained TypeScript contract.
4. No simultaneous edits to shared docs. Use the handoff lock protocol in
   `agent_handoff/README.md`.
5. Run `git status --short --branch` before staging or merging. Neither agent
   force-pushes.

## Quick Start

```powershell
# Frontend
cd app/web
npm run dev      # -> http://localhost:3000 or the next available Next.js port

# Backend
cd app/backend
python -m uvicorn app.main:create_app --factory --reload
# -> http://localhost:8000/api/v1
```

## Historical Codex Plugin Notes

The plugin-mediated `/codex:rescue` flow formerly described here is historical.
Direct Codex app sessions now have verified full `D:\eamos` workspace access and
can own substantive backend/API/pipeline/tool/test work directly when scoped.
Live cross-agent coordination lives in `agent_handoff/`.
