# Frozen Vite Frontend Reference

This React + Vite tree is a historical/reference frontend. It is stale for the
live Eamos report surface, including the Section 2 in-silico predictor panel,
AlphaMissense display, gene/protein viewer, and current backend contracts.

Quarantine status, 2026-06-30:

- No live CI, deploy, Vercel, or browser-proof workflow should depend on this
  folder.
- Do not mirror new product work into this tree.
- Do not use this folder's package scripts as release verification.
- Keep the files in place until Steven approves an exact deletion or
  regeneration task.

Use `app/web` for active `/report`, `/workbench`, account, checkout, auth, and
production frontend work. Do not copy `app/frontend` mocks or thresholds into
live report code without checking the current `app/web` implementation and
backend contract first.

Future cleanup: retire this Vite tree or replace it with a generated/current
mirror of the live Next implementation once no active tooling depends on it.

## Template and stack

- React + TypeScript scaffold
- Tailwind CSS v4 (via @tailwindcss/vite)
- React Router for simple page flow

```bash
cd 04_demo/app/frontend
npm install
npm run dev
```

The commands above are historical only. The active dev server is
`cd app/web && npm run dev`.

## Applied layout

- `src/routes/AppRouter.tsx`
- `src/components/AppShell.tsx` (shared layout + nav)
- `src/features/cases/DashboardPage.tsx`
- `src/features/cases/CaseWorkspacePage.tsx`
- `src/features/cases/ReviewBoardPage.tsx`
- `src/features/cases/mockCases.ts`
- `src/types/demo.ts`

## Why this shape

`App.tsx` is intentionally minimal and only mounts the router.

- routing + shell live in `routes/` + `components/`
- pages live in `features/cases/`
- API/client-facing shared types in `types/`

This keeps frontend work aligned with the backend contract types in
`src/lib/backend.ts` (mirrored from `app/backend/app/schemas/`, guarded by
`app/backend/tests/test_frontend_contract.py`).
