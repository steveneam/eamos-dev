# Frontend cleanup backlog (`app/web`)

> Living tech-debt log for the active Next.js frontend. Created **2026-06-11** from a
> full adversarial review (Claude). Refresh anytime with the commands in
> [§ Reproduce](#reproduce). Scope = `app/web` only (the legacy Vite `app/frontend`
> is frozen/reference and out of scope). The backend is Codex's lane.

**Status legend:** `DONE` applied · `TODO` actionable next · `PARKED` intentional, do **not** remove ·
`CODEX` off-limits (Codex's active lane) · `ACCEPTED` flagged by a tool but correct as-is.

---

## Tooling baseline (this review)

| Gate | Before | After | Note |
|---|---|---|---|
| `tsc --noEmit` | clean in my zone | clean in my zone | only error is Codex's live workbench WIP (`mockStruct` / `buildPrimerAmpliconOverlay`), moves as he edits |
| `eslint .` | 4 warnings | **2 warnings** | all `react-hooks/set-state-in-effect` |
| `knip` unused files | 6 | **1** | the 1 = `scripts/contrast-gate.mjs`, kept on purpose |
| `knip` unused exports | 45 | **41** | |
| `knip` unused devDeps | 1 | 1 | `world-atlas` (see TODO) |

---

## DONE — applied 2026-06-11 (working tree only, not committed; Codex tree was live)

Deleted 5 dead files (zero importers, confirmed by knip + grep):
- `components/report/LimitationsSection.tsx`
- `components/search/SearchShell.tsx`
- `components/ui/CiteModal.tsx` — was a Steven-approved product-wide removal (2026-06-10), left git-recoverable
- `components/ui/Hairline.tsx`
- `components/ui/StatusPill.tsx` — dead duplicate (`report/TrialsSection.tsx` has its own live local `StatusPill`)

Removed / trimmed dead exports:
- `lib/chat.ts` — deleted unused `sendChat` (non-streaming wrapper; `streamChat` stays, it powers the rail)
- `lib/variant-format.ts` — deleted wholly-dead `FORMAT_HINTS`; unexported `classify` (internal-only)
- `lib/work-rail-collapse.ts` — unexported `storageKey` (internal-only)

Lint fix:
- `components/compare/VariantTable.tsx:112` — reset-selection-on-rows-change rewritten from a
  `setState`-in-effect (cascading renders) to the render-phase `prevRows` pattern.

---

## TODO — actionable next (do when Codex's workbench work has landed / tree is quiet)

### Unused devDependency
- `world-atlas` (`package.json`) — confirmed unused (the gnomAD basemap script doesn't import it).
  Remove in a **dedicated deps commit** (`npm uninstall world-atlas`) — deferred because it churns
  `package-lock.json` while the dev server + Codex were live.

### Candidate-dead exports (my zone — verify each is whole-dead vs internal-use, then remove or unexport)
| Symbol | File:line | Note |
|---|---|---|
| `IconPin` | `components/icons/Icon.tsx:37` | unused icon export |
| `tierConfig`, `tierShort` | `components/library/tier.ts:42,48` | library tier helpers |
| `ACMG_LABELS`, `isBenignAcmgCode` | `components/report/AcmgGrid.tsx:6,37` | report helpers |
| `STATE_THEME`, `CARD_ORDER` | `components/report/CallCardsGrid.tsx:60,73` | report consts |
| `GNOMAD_ANCESTRY_MAP_ANCHORS` | `components/report/gnomadAncestryMap.ts:12` | map data |
| `NON_GEOGRAPHIC_GROUPS` | `components/report/region-countries.ts:70` | map data |
| `ScorePin` | `components/report/ScoreScale.tsx:20` | shared scale piece — check if a sibling uses it |
| `hasClassificationTier` | `lib/classification.ts:52` | core classification lib |
| `REQUIRED_DRY_RUN_FIELDS` | `lib/messenger.ts:88` | messenger helper |

> Each needs a 1-line check: if the symbol is used inside its own module → just drop `export`;
> if used nowhere → delete it. `app/web` has no test suite and is a self-contained package, so
> knip's graph is the complete consumer set — these are reliably dead *within app/web*.

---

## PARKED — intentional, do NOT remove (flagged by knip but kept on purpose)

| Symbol(s) | File | Why kept |
|---|---|---|
| `priceFor`, `perMonth`, `yearlySavingPct`, `GST_RATE` | `lib/plans.ts` | yearly-billing helpers; explicit 2026-05-24 retain comment (UI shows monthly only for now) |
| `uploadBatch` | `lib/batch.ts` | client scaffold for the batch-VCF-upload feature ([[project_batch_vcf_panels]]) |
| `isSaved` | `lib/variant-library.ts` | library save-state API (save-toggle UI) |
| `scripts/contrast-gate.mjs` | — | manual dev tool (run by hand), not app code |

This codebase deliberately parks helpers (CiteModal "recoverable from git", yearly billing,
viewer-pane prefs) — a future sweep should treat documented/obvious-API parking as keep, not dead.

---

## ACCEPTED — tool-flagged but correct (leave)

- `components/compare/CompareClient.tsx:~62` — `setHydrated(true)` in a mount effect. `react-hooks/set-state-in-effect`
  fires, but this is a legitimate mount-time localStorage hydration read. Fixing via `useSyncExternalStore`
  adds SSR risk for no real gain.

---

## CODEX — off-limits (active lane; NOT necessarily dead)

Do not touch — Codex owns these and many "unused" symbols are contract/utility surface he is wiring:
- `lib/backend.ts` — 185 "unused" exported types. These **mirror the backend contract**, not dead code.
- `lib/api.ts` — `lookupSummary`, `alignSequences`
- `components/workbench/**` — incl. `align/read-model.ts` (13 orientation/trace helpers), `viewer/zoom-config.ts` `DEFAULT_BASES_PER_ROW`
- `lib/workbench/**` — `alignment-pairwise.ts`, `codon-table.ts` (`translate`, `consequenceOf`), `crispr-disclosure.ts`, `crispr-guide-map.ts`
- eslint `set-state-in-effect`: `report/PubMedSection.tsx:99` (and `report/LazySection.tsx` when present)
- tsc errors in `workbench/primer/*` / `workbench/viewer/*` — his transient WIP

Codex's FE exclusion list is in `codex-workbench-temp.md` ("Workbench-ready paths") + the PubMed lane files.

---

## Reproduce

```bash
# from app/web
npx tsc --noEmit                 # type errors
npm run lint                     # eslint (set-state-in-effect etc.)
npx -y knip --no-progress        # unused files / exports / deps
```
Re-run after Codex's workbench work lands so the moving tsc/knip results settle before the next sweep.
