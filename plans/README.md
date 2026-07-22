# plans/

Active and historical work plans for Eamos.

Plan index refreshed: 2026-07-22 16:29 +0000 · Codex.

## Universal-Free Product Ratchet

Stamped: 2026-07-16 13:19 +0000 · Codex.

`plans/landing-free-public/plan.md` and the 2026-07-16 governance decision
supersede every historical pricing, checkout, Free/Pro/Max, premium-wall, and
predictor-entitlement passage in this directory. Historical payment code may
remain dormant with its security controls intact; it is not an active product
surface. Operational limits such as batch size, rate limits, and provider
capacity are neutral reliability controls and must not become paid access gates.

## Active Frontend Source Of Truth

The live Eamos frontend is the Next.js app in `app/web`. Production build,
browser proof, Vercel guard, and new product work target `app/web`.

The historical Vite implementation was retired on 2026-07-15 after its useful
pure tests moved into `app/web`. Git history preserves the old implementation;
do not recreate a second hand-maintained frontend or contract mirror.

## Active And Historical Plans

| File | Owner | Scope |
| ---- | ----- | ----- |
| [`live-product-completion/`](live-product-completion/) | Codex | **Proposed; planning complete, not launched.** Four-surface scientific-live campaign for Workbench engines, Variant Report evidence truth, Selom-informed deterministic Paper extraction, and WES/panel-first Batch, followed by runtime/material/UI/ratchet waves. Fresh per-session lane approvals and separate material/cloud/deploy gates remain required. |
| [`product-workflow-integration/`](product-workflow-integration/) | Codex | **Lane D active; A/B/Task F/C integrated.** The approved V1 workflow foundation is being closed at Lane D. Its unlaunched Lane E is re-chartered by `live-product-completion/plan.md` after the broader scientific-live stack, rather than launched against a stale target. |
| [`evidence-source-expansion/`](evidence-source-expansion/) | Codex | **Proposed.** REVEL-led computational evidence within the existing four independent call-card axes; calibration/source-contract repairs; clean ESM-1b regeneration; safe OMIM/LOVD slices; corrected CC0 MaveDB ingestion; OddsPath hardening; final-publication gate for SVC v4. |
| [`variant-report-experience/plan.md`](variant-report-experience/plan.md) | Codex | **Complete.** Four call cards hand directly to Clinical, with one coherent chapter system across all report sections. |
| [`landing-free-public/plan.md`](landing-free-public/plan.md) | Codex | **Complete.** Free-public landing, universal-free predictor presentation, responsive product gallery, safe share paths, and privacy-safe discovery telemetry. |
| [`batch-vcf-and-panels/`](batch-vcf-and-panels/) | Historical/active architecture | Batch and panel architecture remains useful; its old tier gates are explicitly superseded by neutral operational safety bounds. |
| [`variant-report-layout/`](variant-report-layout/) | Historical | May call-card/backend plan. The four-card contract shipped; current presentation work is owned by `variant-report-experience/plan.md`. |
| [`variant-report-data-orchestration/`](variant-report-data-orchestration/) | Historical/reference | Detailed report source and section ledger. Audit live contracts before treating any old `planned` cell as current work. |
| [`auth-pricing/`](auth-pricing/) | Historical | Auth notes are historical context; all pricing/payment product requirements are superseded. Dormant backend payment controls remain hardened. |
| [`v2-redesign-impeccable.md`](v2-redesign-impeccable.md) | Historical | Superseded design execution plan. Durable design decisions live in `DESIGN.md`; paid-wall and predictor-gating passages are void. |
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
npm run dev      # -> http://localhost:3532 (pinned; never auto-increments)

# Backend
cd app/backend
python -m uvicorn app.main:create_app --factory --reload --port 8532
# -> http://localhost:8532/api/v1
```

## Historical Codex Plugin Notes

The plugin-mediated `/codex:rescue` flow formerly described here is historical.
Direct Codex app sessions now have verified full `D:\eamos` workspace access and
can own substantive backend/API/pipeline/tool/test work directly when scoped.
Live cross-agent coordination lives in `agent_handoff/`.
