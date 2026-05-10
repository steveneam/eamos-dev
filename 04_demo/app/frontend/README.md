# HSIL 2026 Demo Frontend

## Template and stack

- React + TypeScript scaffold
- Tailwind CSS v4 (via @tailwindcss/vite)
- React Router for simple page flow

```bash
cd 04_demo/app/frontend
npm install
npm run dev
```

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

This keeps frontend work aligned with backend-driven contracts in `shared/contracts`.