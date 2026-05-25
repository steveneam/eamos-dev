# Workbench Migration — app/frontend → app/web

Pass 1 complete. This document covers the staged migration design for the
Eamos Workbench surface from Vite (`app/frontend`) to Next.js 16 App Router
(`app/web`).

---

## 1. File-by-file dependency map

### Entry / routing

| Vite (source) | Next.js (target) | Status |
|---|---|---|
| `src/pages/WorkbenchPage.tsx` | `app/workbench/page.tsx` + `components/workbench/WorkbenchClient.tsx` | ✅ pass 1 |
| React Router `<Link>`, `useNavigate`, `useSearchParams` | `next/link`, `next/navigation` `useRouter`/`useSearchParams` | ✅ pass 1 |

### Chrome components

| Vite | Next.js | Notes |
|---|---|---|
| `components/workbench/ContextStrip.tsx` | `components/workbench/ContextStrip.tsx` | ✅ pass 1 — `'use client'` |
| `components/workbench/ToolBar.tsx` | `components/workbench/ToolBar.tsx` | ✅ pass 1 — `'use client'` |
| `components/workbench/ToolIcon.tsx` | `components/workbench/ToolIcon.tsx` | ✅ pass 1 — pure SVG, no directive |
| `components/workbench/tools.tsx` | `components/workbench/tools.ts` | ✅ pass 1 — pure data, renamed `.ts` |
| `components/workbench/CanvasHeader.tsx` | `components/workbench/CanvasHeader.tsx` | ✅ pass 1 — `'use client'` |
| `components/workbench/SidePanel.tsx` | `components/workbench/SidePanel.tsx` | ✅ pass 1 — `'use client'` |
| `components/workbench/WorkbenchShell.tsx` | `components/workbench/WorkbenchShell.tsx` | ✅ pass 1 — `'use client'` |

### Viewer components

| Vite | Next.js | Notes |
|---|---|---|
| `components/workbench/viewer/SequenceViewerV2.tsx` | `components/workbench/viewer/SequenceViewerV2.tsx` | ✅ pass 1 skeleton — edit/history/protein wired in pass 2 |
| `components/workbench/viewer/ZoomSlider.tsx` | `components/workbench/viewer/ZoomSlider.tsx` | ✅ pass 1 |
| `components/workbench/viewer/viewer-types.ts` | `components/workbench/viewer/viewer-types.ts` | ✅ pass 1 |
| `components/workbench/viewer/zoom-config.ts` | `components/workbench/viewer/zoom-config.ts` | ✅ pass 1 |
| `components/workbench/viewer/GeneMinimap.tsx` | deferred | pass 2 |
| `components/workbench/viewer/HistoryTimeline.tsx` | deferred | pass 2 |
| `components/workbench/viewer/ProteinView.tsx` | deferred | pass 2 |
| `components/workbench/viewer/CodonDetail.tsx` | deferred | pass 2 |
| `components/workbench/viewer/EditPopoverV2.tsx` | deferred | pass 2 |
| `components/workbench/viewer/ViewerToolbar.tsx` | deferred | pass 2 |

### Tool panels (pass 2)

| Vite | Next.js | Notes |
|---|---|---|
| `components/workbench/PrimerPanel.tsx` | deferred | pass 2 — stubbed with loading message |
| `components/workbench/CrisprPanel.tsx` | deferred | pass 2 — stubbed |
| `components/workbench/AlignPanel.tsx` | deferred | pass 2 — stubbed |
| `components/workbench/ComparePanel.tsx` | deferred | pass 2 — stubbed |

### Lib files

| Vite (`src/lib/workbench/`) | Next.js (`lib/workbench/`) | Status |
|---|---|---|
| `codon-table.ts` | `codon-table.ts` | ✅ pass 1 — verbatim copy |
| `gene-window.ts` | `gene-window.ts` | ✅ pass 1 — verbatim copy |
| `edit-state.ts` | `edit-state.ts` | ✅ pass 1 — verbatim copy |
| `sample-rpe65-v2.ts` | `sample-rpe65-v2.ts` | ✅ pass 1 — verbatim copy |
| `gene-viewer-sample.ts` | `gene-viewer-sample.ts` | ✅ pass 1 — import path fixed (`../backend`) |
| `gene-viewer-adapter.ts` | `gene-viewer-adapter.ts` | ✅ pass 1 — import paths fixed |
| `primer-utils.ts` | deferred | pass 2 |
| `crispr-utils.ts` | deferred | pass 2 |
| `align-utils.ts` | deferred | pass 2 |

### API

| Vite (`src/lib/api.ts`) | Next.js (`lib/api.ts`) | Status |
|---|---|---|
| `variantLookup()` | already present | pre-existing |
| `lookupPublications()` | already present | pre-existing |
| `getGeneViewer()` | added in pass 1 | ✅ pass 1 |

### Styles

| Vite (`src/styles/workbench.css`) | Next.js | Status |
|---|---|---|
| `:root` tokens | merged into `app/globals.css` | ✅ pass 1 |
| All other rules | `components/workbench/workbench.css` | ✅ pass 1 |
| Import | `WorkbenchClient.tsx` `import './workbench.css'` | ✅ pass 1 |

---

## 2. `'use client'` boundary analysis

Next.js 16 App Router: components are React Server Components by default. Any
component using browser APIs, hooks (`useState`, `useEffect`, `useRef`,
`useCallback`, `useSearchParams`, `useRouter`), event handlers, or `forwardRef`
must be a Client Component.

| File | Directive | Reason |
|---|---|---|
| `app/workbench/page.tsx` | none (RSC) | Server entry; wraps client in `<Suspense>` |
| `WorkbenchClient.tsx` | `'use client'` | `useSearchParams`, `useRouter`, `useState`, form handler |
| `WorkbenchShell.tsx` | `'use client'` | `useState`, `useEffect`, `useCallback`, `useRef` |
| `ContextStrip.tsx` | `'use client'` | `onSelectTool` callback prop |
| `ToolBar.tsx` | `'use client'` | `onClick` handlers |
| `ToolIcon.tsx` | none | Pure SVG render, no hooks |
| `tools.ts` | none | Pure data module |
| `CanvasHeader.tsx` | `'use client'` | `useState`, `useEffect`, `useRef` (dropdown) |
| `SidePanel.tsx` | `'use client'` | `useState` (layer-3 expand), event handlers |
| `SequenceViewerV2.tsx` | `'use client'` | `forwardRef`, `useImperativeHandle`, `useMemo` |
| `ZoomSlider.tsx` | `'use client'` | `onChange` handlers |
| `viewer-types.ts` | none | Types only |
| `zoom-config.ts` | none | Constants only |
| All `lib/workbench/*.ts` | none | Pure TypeScript, framework-agnostic |

The Suspense boundary at `page.tsx` is required because `WorkbenchClient` calls
`useSearchParams()`, which needs a boundary for static build-time rendering.

---

## 3. Lib file portability assessment

All `lib/workbench/` files are framework-agnostic pure TypeScript. They have
zero React or browser API imports. They can be copied verbatim with only import
path adjustments:

- Vite: `@/` resolves to `src/` → paths like `@/lib/backend`
- Next.js: `@/` resolves to `./` (project root) → same path `@/lib/backend`

Internal cross-file imports use relative paths (`'../backend'`, `'./codon-table'`)
which work identically in both apps.

`gene-viewer-adapter.ts` uses a hybrid scaffold strategy: when the backend
payload is missing exon/intron data (offline / mock mode), it falls back to
`RPE65_V2` from `sample-rpe65-v2.ts`. This preserves the offline-first
development pattern in Next.js.

---

## 4. Staged port order by risk

| Pass | Scope | Risk | Gate |
|---|---|---|---|
| **1 (done)** | Route scaffold, chrome, viewer skeleton, lib files, CSS | Low — lib is pure TS; chrome is straightforward React | `tsc --noEmit` exit 0 |
| **2** | Full viewer wiring: edit-state, GeneMinimap, HistoryTimeline, ProteinView, CodonDetail, EditPopoverV2, ViewerToolbar, click/drag selection, keyboard shortcuts | Medium — large imperative DOM surface | tsc + visual verify |
| **3** | Tool panels: PrimerPanel, CrisprPanel, AlignPanel, ComparePanel | Medium — each panel has its own API call + state | tsc + backend integration test |
| **4** | Retire Vite workbench route (update React Router config) | Low — additive removal | E2E smoke on both apps |

---

## 5. Vitest migration strategy

The Vite app has no workbench-specific vitest tests at time of pass 1. When
tests are added:

- `lib/workbench/*.ts` tests: copy verbatim — pure TS, no framework coupling.
- Component tests: Next.js uses `jest` + `@testing-library/react` by convention.
  Vitest can also be used with `@vitejs/plugin-react` targeting the `app/web`
  package. Choose whichever the project standardises on.
- `getGeneViewer()` in `lib/api.ts`: mock with `jest.fn()` / `vi.fn()`, supply
  `GENE_VIEWER_SAMPLE` as the resolved value for offline tests.

---

## 6. Pass 1 — DONE vs REMAINING

### DONE (pass 1)

- `app/web/app/workbench/page.tsx` — RSC entry with Suspense boundary
- `app/web/components/workbench/WorkbenchClient.tsx` — nav, search, mode-pill, Suspense-safe client shell
- `app/web/components/workbench/WorkbenchShell.tsx` — orchestrator: data fetch, allele mode, tool routing
- `app/web/components/workbench/ContextStrip.tsx` — gene/variant strip + tool selector
- `app/web/components/workbench/ToolBar.tsx` — segmented tool control
- `app/web/components/workbench/ToolIcon.tsx` — SVG icons per tool
- `app/web/components/workbench/tools.ts` — TOOL_ORDER, TOOL_META, viewerCollapsed()
- `app/web/components/workbench/CanvasHeader.tsx` — tracks dropdown, strand pill, allele pill
- `app/web/components/workbench/SidePanel.tsx` — viewer/crispr/primer sides, scratch, selection hub
- `app/web/components/workbench/viewer/SequenceViewerV2.tsx` — pass-1 skeleton: flat base render, forwardRef stubs
- `app/web/components/workbench/viewer/ZoomSlider.tsx` — range slider + zoom preset chips
- `app/web/components/workbench/viewer/viewer-types.ts` — StrandMode, TrackState, DEFAULT_TRACKS, ZoomLevel, SelectionSummary
- `app/web/components/workbench/viewer/zoom-config.ts` — BASE_W_MIN/MAX, ZOOM_PRESETS
- `app/web/components/workbench/workbench.css` — full CSS port (~84 KB)
- `app/web/lib/workbench/codon-table.ts` — verbatim copy
- `app/web/lib/workbench/gene-window.ts` — verbatim copy
- `app/web/lib/workbench/edit-state.ts` — verbatim copy
- `app/web/lib/workbench/sample-rpe65-v2.ts` — verbatim copy
- `app/web/lib/workbench/gene-viewer-sample.ts` — verbatim copy, import path fixed
- `app/web/lib/workbench/gene-viewer-adapter.ts` — verbatim copy, import paths fixed
- `app/web/lib/api.ts` — added `getGeneViewer()`
- `app/web/app/globals.css` — added workbench-only root tokens (--line-3, --err, --err-tint, --r-sm/md/lg, --nav-h, --ctx-h)

### REMAINING (pass 2+)

**Viewer internals (pass 2)**
- Full edit/undo-redo state wiring (`editReducer` → SequenceViewerV2)
- GeneMinimap (gene-wide exon density overview)
- HistoryTimeline (edit history panel)
- ProteinView (domain lollipop view with ClinVar pins)
- CodonDetail (per-codon popup on click)
- EditPopoverV2 (right-click substitute/delete/insert)
- ViewerToolbar (copy / jump / export actions)
- Click/drag selection → SelectionSummary callbacks
- Keyboard shortcuts (A/T/C/G to substitute, ⌫ to delete)

**Tool panels (pass 3)**
- PrimerPanel (Tm, off-target, ssODN visualisation)
- CrisprPanel (guide track, indel chart, outcomes)
- AlignPanel (AB1 chromatogram + sequence alignment)
- ComparePanel (side-by-side variant grid)

**Cleanup (pass 4)**
- Retire Vite workbench route once Next.js version is verified in prod
- Remove workbench CSS from Vite build if fully migrated
