# frontend/

React + TypeScript + Vite + Tailwind. Variant lookup landing page (primary product) and patient report generation flow (secondary, ghost-button access).

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `src/App.tsx` | Root component — all views, state, search logic, report render | Any UI or view change |
| `src/lib/api.ts` | API call functions: `variantLookup()`, report submission | Adding or changing API calls |
| `src/lib/backend.ts` | TypeScript types matching FastAPI response schemas | Changing request/response shapes |
| `src/index.css` | Global styles, Tailwind base | Changing design tokens or global styles |
| `index.html` | HTML shell — page title, favicon | Changing page metadata |
| `vite.config.ts` | Vite build config, dev server proxy | Build or proxy changes |
| `package.json` | Dependencies, npm scripts | Adding packages, checking versions |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `src/components/ui/` | Radix-based UI primitives (badge, button, dialog, tabs, textarea) | Modifying shared UI building blocks |
| `src/lib/` | API client, backend types, utility functions | Data fetching or type changes |

## Development

```powershell
$env:PATH = 'C:\temp\node\node-v22.15.0-win-x64;' + $env:PATH
npm run dev      # → http://localhost:5173
npm run build    # type-check (tsc -b) + Vite bundle
```

Design tokens and component specs: `DESIGN.md` at repo root.
