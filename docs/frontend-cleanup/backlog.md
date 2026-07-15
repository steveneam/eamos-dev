# Active frontend cleanup backlog (`app/web`)

Status: refreshed 2026-07-15 after the repository-structure audit.

`app/web` is the sole frontend application. The historical Vite tree was
retired after its useful pure tests moved here; the structure guard prevents a
second maintained frontend or contract mirror from returning.

## Completed in the 2026-07-15 retirement slice

- Removed `app/frontend` and its separate package, lockfile, Vite build, CI
  install, stale `/runs` copy, and duplicated `backend.ts` contract.
- Moved 13 pure Vitest files into the corresponding active modules. The active
  suite now covers 135 tests and runs through `npm run test`.
- Removed seven audited no-importer files from `app/web`:
  `AssociatedConditions.tsx`, `DiseaseSection.tsx`, `GeneDiseaseBlock.tsx`,
  `InSilicoPlaceholderRows.tsx`, `PopFreqEmptyState.tsx`, `GeneMinimap.tsx`, and
  `ProteinView.tsx`.
- Added active-web test, boundary, typecheck, lint, and production-build steps
  to CI. The historical frontend check name remains as a cheap retirement
  canary until branch protection is updated separately.
- Removed unused root Vite dependencies and stale worktree/harness references.
- Removed 380 lines of orphaned `GeneMinimap` / `ProteinView` CSS and lowered
  the stylesheet growth ratchet from 4,100 to 3,650 lines.
- Split the remaining Workbench stylesheet byte-for-byte into shell, viewer,
  side-panel, tool, and designer ownership files; the largest is now 1,078
  lines and each file has its own growth ratchet.
- Extracted the population age-distribution chart/export responsibility into
  `PopulationAgeDistribution.tsx`, reducing the parent frequency section from
  1,880 to 1,580 lines with independent 1,600/325-line ratchets.

## Current measured backlog

Knip reports no additional unused runtime file. It reports only
`scripts/contrast-gate.mjs`, which is an intentional manual verification tool.
Its `world-atlas` result is a false positive because
`scripts/build-gnomad-basemap.mjs` resolves the atlas JSON dynamically.

Remaining work should be responsibility-based rather than a blanket export
purge:

1. Continue decomposing `ReportGeneViewer.tsx`, the remaining population map /
   ancestry responsibilities, and `ReportClient.tsx` around controller,
   adapter, rendering, and state seams.
2. Review Knip's non-contract exported helpers one module at a time. Unexport
   internal helpers; keep backend contract types and documented operator or
   future-product APIs.
3. Measure landing/report/workbench bundles after the structural splits and
   defer analytics or heavy client code only where the production build proves
   a page-level gain.

## Reproduce

```bash
cd app/web
npm run test
npx tsc --noEmit -p tsconfig.json
npm run lint
npm run build
npx -y knip --no-progress
```
