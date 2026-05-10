# src/

React + TypeScript application source.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `App.tsx` | Root component — all views, search state, lookup flow, report render | Any UI or view change |
| `main.tsx` | React entry point — mounts `<App />` into the DOM | Changing app bootstrap |
| `index.css` | Global styles, Tailwind base import | Changing design tokens or global styles |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `components/` | Shared UI components | Modifying UI building blocks |
| `lib/` | API client, backend types, utilities | Data fetching, type changes |
