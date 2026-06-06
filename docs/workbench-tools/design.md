# Workbench tools — design (FE-6 Primer + CRISPR · FE-7 Alignment · AskEamos parked)

> ⚠ **REVISION 2026-06-06 (Steven):** the **Variant Comparator (property grid) is DROPPED** —
> redundant with the per-variant report + the Batch (`/compare`) table. "Compare two variants" in
> the Workbench = pairwise **sequence alignment** (variant-vs-variant / variant-vs-control, web or
> Sanger AB1), an **extension of the Align tool**, not a new tool. The Comparator content in §0/§2/§3
> below is **superseded** — actionable revised plan: `docs/workbench-tools/plan.md` (Phases A/B/C) +
> the `spec.md` revision banner.

---


Frontend architecture / design doc. **Design only — no application code.** Active surface is the
Next.js 16 app at `app/web/`. The Vite app (`app/frontend/`) is read-only reference; `/runs` is frozen v1.

Stamped 2026-06-06 14:00 +1000. Ground truth verified against the tree at commit `8a571eb`.

---

## §0 Ground-truth audit (verified — do NOT trust ROADMAP.md / plans/v2-frontend.md status lines)

> **The brief's premise is itself partly stale.** The brief says live engines are "M-002 Codex backend deps —
> design against the FROZEN stub contracts… never assume the real engine exists." **That is no longer true.**
> `app/backend/app/services/workbench_design.py` is a real 1,405-line service with a Primer3 provider, a
> Bio.Align pairwise aligner, an AB1 trace parser, and two CRISPR providers — wired in `app/main.py:234`.
> `primer3-py 2.3.0` and `biopython 1.87` are **installed and import-clean** (verified via `python -c`), and
> pinned in `requirements.txt:23-24`. The real engine exists; it is **gated behind `settings.use_real_apis`**
> (default `false` → fixture provider). So §5 below is "flip the flag + verify shapes," not "build the engine."

### Per-component state

| Component / file | State | Evidence (`file:line`) |
| --- | --- | --- |
| **Tool orchestration** | | |
| `WorkbenchClient.tsx` (nav, search, tool state) | **BUILT** | `app/web/components/workbench/WorkbenchClient.tsx:32-179`; `tool` state `:44`, default `'viewer'` |
| `WorkbenchShell.tsx` (canvas + rail + panels) | **BUILT** | `app/web/components/workbench/WorkbenchShell.tsx:74-309`; `renderToolPanel` `:48-64`; `PANEL_TOOLS = ['primer','crispr','align']` `:46` |
| `ToolBar.tsx` (rail switcher) | **BUILT** | `app/web/components/workbench/ToolBar.tsx:11-30`, maps `TOOL_ORDER` |
| `tools.ts` (registry) | **BUILT, but `compare` orphaned** | `tools.ts:3` `TOOL_ORDER = ['viewer','primer','crispr','align']` — **`compare` is NOT in the order**; `TOOL_META.compare` exists `:41-46` but nothing renders it |
| `ContextStrip.tsx` | **BUILT** (wayfinder only; tool switcher moved to rail) | `ContextStrip.tsx:14-26` — `tool`/`onSelectTool` props accepted but unused |
| `CanvasHeader.tsx` | **BUILT** | `app/web/components/workbench/CanvasHeader.tsx` (track toggles, allele/strand/viewer-mode) |
| `viewer/*` (sequence viewer) | **BUILT** (out of scope here; FE-3.6/FE-5/GV done) | `viewer/SequenceViewerV2.tsx`, `FullLocusViewer.tsx`, etc. |
| **FE-6 Primer** | | |
| `primer/PrimerPanel.tsx` | **MOCK-WIRED, complete** | `PrimerPanel.tsx:35-289`; form `:143-211`, modes Sanger/qPCR/ARMS `:18-22`, calls `designPrimers` `:99` |
| `primer/PrimerResultCard.tsx` | **BUILT** (canonical 3-layer disclosure card) | `PrimerResultCard.tsx:59-259` (Layer 1/2/3 `:84/:110/:156`) |
| `lib/api.ts` `designPrimers` | **MOCK-WIRED** (POST `/api/v1/primer`, mock on `TypeError`) | `api.ts:154-166` → `PRIMER_SAMPLE` fallback `:163` |
| ARMS real mode | **PLACEHOLDER** (FE guards an "unsupported" backend error) | `PrimerPanel.tsx:104-105, 247-252` |
| **FE-6 CRISPR** | | |
| `crispr/CrisprPanel.tsx` (Design/Outcomes tabs) | **BUILT** shell | `CrisprPanel.tsx:18-63` |
| `crispr/DesignTab.tsx` (gRNA table + ssODN) | **MOCK-WIRED, complete** | `DesignTab.tsx:118-410`; calls `designGuides` `:160`; SaCas9/Cas12a are **disabled placeholders** `:32-46` |
| `crispr/GuideTrack.tsx` | **BUILT** | `app/web/components/workbench/crispr/GuideTrack.tsx` (rendered `DesignTab.tsx:397`) |
| `crispr/OutcomesTab.tsx` (TIDE) | **MOCK-WIRED, honest "observed-only"** | `OutcomesTab.tsx:13-162`; calls `analyzeTide` `:43`; caveats `:112-125` |
| `crispr/IndelSpectrum.tsx` | **BUILT** (SVG grouped bars) | `IndelSpectrum.tsx:23-129` |
| `lib/api.ts` `designGuides` | **MOCK-WIRED** (POST `/api/v1/crispr`) | `api.ts:168-180` → `CRISPR_SAMPLE` `:177` |
| `lib/api.ts` `analyzeTide` | **MOCK-WIRED** (POST `/api/v1/crispr/tide`) | `api.ts:182-199` → `CRISPR_TIDE_SAMPLE` on any error `:197` |
| **FE-7 Alignment** | | |
| `align/AlignPanel.tsx` (pairwise + chromatogram) | **MOCK-WIRED, complete** | `AlignPanel.tsx:29-262`; browser fallback `compareSequences` `:51`; API call `requestApiAlignment` `:672-701`; chromatogram SVG `:473-525` |
| `lib/api.ts` align | **PARTIAL** — align is **not** in `api.ts`; `AlignPanel` calls `/api/v1/align` directly, **with NO mock fallback** | `AlignPanel.tsx:26-27, 689-700`; contrast `api.ts` (no `align` export) |
| **FE-7 Comparator** | | |
| `compare/ComparatorGrid.tsx` (the 2–3 variant grid) | **MISSING** | No file in `app/web/components/workbench/`; absent in Vite ref too (no `workbench/compare/` dir, verified `ls`) |
| `.compare-grid` CSS | **ORPHANED CSS** (styles exist, no consumer) | `workbench.css:2394-2434`; grep for `compare-grid` in `*.tsx` → **No matches** |
| `compare` tool wiring | **PLACEHOLDER** (type + meta + icon exist; never mounted) | type `lib/backend.ts:1145`; `TOOL_META.compare` `tools.ts:41-46`; icon `ToolIcon.tsx:44-50`; **absent from `TOOL_ORDER` & `PANEL_TOOLS`** |
| **FE-8 AskEamos pill** | | |
| `ai/AskEamosPill.tsx` (floating tool-aware pill) | **MISSING** | No `workbench/ai/` dir in either app (verified `ls`) |
| `.ai-pill` / `.ai-panel` CSS | **ORPHANED CSS** | `workbench.css:2436-2525`; grep `ai-pill` in `*.tsx` → **No matches** |
| `aistack/AskEamos.tsx` (report chat box) | **BUILT but PARKED** ("Coming soon" when `runId === null`) | `app/web/components/aistack/AskEamos.tsx:28, 115-131, 226-229` |
| `/api/v1/chat` + `/chat/stream` (backend) | **EXISTS, governed by `LLM_PROVIDER=mock`** | `app/backend/app/api/routes/chat.py:12-33` |

### Backend reality (read-only; informs §5)

| Endpoint | Handler | Real engine | Gating |
| --- | --- | --- | --- |
| `POST /api/v1/primer` | `workbench.py:51-57` | `Primer3PrimerProvider` (`workbench_design.py:366-453`) + specificity providers `:197-364` | `use_real_apis` else `WorkbenchFixtureProvider.primers` (`:1302-1305`) |
| `POST /api/v1/crispr` | `workbench.py:60-66` | `LocalDeterministicCrisprProvider` / `CrisprScoreRBackedCrisprProvider` (`:1258-1276`) | `use_real_apis` else fixture (`:1307-1310`) |
| `POST /api/v1/align` | `workbench.py:69-75` | `LocalSangerAlignmentProvider` + `Bio.Align.PairwiseAligner` (`:455-471, 625`) + `parse_ab1_base64` (`trace_parser.py`, `:519-534`) | `use_real_apis` else fixture (`:1312-1315`) |
| `POST /api/v1/crispr/tide` | **NOT FOUND** in `workbench.py` | — | FE `analyzeTide` exists but the **TIDE endpoint is not implemented** → always 404/error → FE serves `CRISPR_TIDE_SAMPLE`. This is the real M-002 gap. |

**Headline correction to ROADMAP.md (dated 2026-05-16):** it lists FE-6/FE-7 as "Pending." In fact
**FE-6 (Primer + CRISPR) is shipped and mock-wired; FE-7 Alignment is shipped and mock-wired; FE-7 Comparator
and FE-8 AskEamos pill are unbuilt (orphaned CSS only).** The backend engines exist and are flag-gated, not absent.

---

## §1 Problem & goals

**Problem.** The Workbench tool surface is ~70% complete but reads as finished only on three of five tools.
Primer, CRISPR, and Align are real, polished panels — but the **Comparator** (FE-7) and the **AskEamos pill**
(FE-8) are ghost surfaces: a tool type, meta, icon, and CSS with no component behind them. A user who notices the
`compare` icon never sees it (it isn't in the rail). The existing tools are also entirely **mock-first**, with
honest-but-prominent demo disclaimers; flipping to real data is a backend-flag + shape-verify job, not a rebuild.

**Goals (this design).**
1. **Close FE-7 Comparator** — design the 2–3 variant side-by-side grid that the type/meta/icon/CSS already
   anticipate, wired to a real data source (per-variant lookup), with all states.
2. **Decide FE-7 Comparator data path** — reuse the variant-library store for column selection; source predictor
   evidence from `LookupResponse` (a lookup per column) for v1; flag a batched compare endpoint as the Codex win.
3. **Close FE-8 AskEamos affordance** — design the *placeholder* pill only (PARKED: no funded LLM key). Mount a
   disabled, tool-aware "Coming soon" pill; design the live wiring contract but do **not** build it.
4. **Promote the real engines** — define the path from mock-first to `use_real_apis` for Primer/CRISPR/Align,
   the per-tool "live vs demo" provenance affordance, and the one true backend gap (TIDE endpoint).
5. **Tighten existing states** — Align has no mock fallback (network error = dead trace panel); Comparator and
   the pill need full empty/loading/error/edge coverage.

**Non-goals.** Rebuilding Primer/CRISPR/Align (they ship). Building live AskEamos. Touching `app/backend/**`,
`/runs`, or the Batch (`/compare` route) surface. New icon system. Schema/contract edits.

---

## §2 UX / IA / flows (per tool)

### 2.1 Rail & tool model (shared)

Tools live in the left rail (`ToolBar`, inside `WorkRail`). To surface the Comparator, **`compare` must be added
to `TOOL_ORDER`** (`tools.ts:3`) and to the panel render path (`PANEL_TOOLS` + `renderToolPanel`,
`WorkbenchShell.tsx:46-64`). Like Align, Compare **collapses the sequence viewer** (`viewerCollapsed`,
`tools.ts:50-52` — add `tool === 'compare'`), because its output is a full-width grid, not a sequence track.

⚠ **GATED — needs Steven OK:** adding a 5th rail tool is a durable nav change. Recommended order:
`Sequence · Primer · CRISPR · Align · Compare` (Compare last — it's a cross-variant view, not a single-variant tool).

### 2.2 FE-6 Primer — states (already built; gaps only)

Flow: pick mode → set Tm/product/SNP constraints → **Generate & validate** → feed of 3-layer result cards.

| State | Current | Gap to close |
| --- | --- | --- |
| Empty (pre-run) | `primer-prompt` copy `PrimerPanel.tsx:280-286` | none |
| Loading | 3 honest phase chips `:227-236` | none |
| Success | card feed `:264-277`, recommended ★ row | none |
| Error | `primer-error` `:245` | none |
| Edge: no pairs satisfy constraints | `primer-empty` `:270-275` | none |
| Edge: ARMS real mode | "not implemented" placeholder `:247-252` | **resolve via §5** (backend ARMS or hide ARMS until ready) |
| Edge: offline mock mode mismatch | `primer-mock-note` `:256-263` | replaced by the **live/demo provenance chip** (§3.4) once `use_real_apis` lands |

### 2.3 FE-6 CRISPR — states (already built; gaps only)

Design tab: Cas/strand/off-target → **Design SpCas9 guides** → guide table + GuideTrack + ssODN block.
Outcomes tab: upload control+edited AB1 + cut index → **Analyze outcomes** → efficiency + IndelSpectrum.

| State | Current | Gap |
| --- | --- | --- |
| Design empty/loading/success/error | all present `DesignTab.tsx:259-407` | none |
| Design edge: SaCas9 / Cas12a | disabled options + caveats `:32-46, 280-285` | none (honest) |
| Outcomes empty/loading/error | present `OutcomesTab.tsx:97-127` | none |
| Outcomes success | efficiency + spectrum `:129-159` | **honest only while TIDE endpoint missing** — keep observed-only until §5 ships `/crispr/tide` |
| Outcomes edge: backend never returns predicted bins | `showPredicted` guarded by `outcomeDisclosure` `:20, 151-156` | none (correct) |

### 2.4 FE-7 Alignment — states (already built; one real gap)

| State | Current | Gap |
| --- | --- | --- |
| Browser fallback (paste/FASTA) | `compareSequences` `:51`, always available | none |
| API align loading/success/error | `apiStatus` machine `:65-90`, TracePanel `:408-471` | none |
| Chromatogram present | SVG channels `:473-525` | none |
| **Edge: backend unreachable (TypeError)** | **throws → `apiStatus='error'`**, trace panel dead | **GAP**: unlike `designPrimers`/`designGuides`, `AlignPanel` has **no mock fallback** (`AlignPanel.tsx:689-700` vs `api.ts:163,177`). Add an align mock (e.g. an `ALIGN_SAMPLE`) so offline demo paints a 4-channel trace, matching Primer/CRISPR behaviour. Error copy already correctly says "browser alignment remains available" `:440`. |
| Edge: JSON trace upload | handled `:71-72, 664-670` | none |

### 2.5 FE-7 Comparator — NEW (states designed from scratch)

**Purpose.** Side-by-side comparison of **2–3 variants** (`TOOL_META.compare.sub`, `tools.ts:45`). Rows =
properties; columns = variants. Read at-a-glance: which variant is most pathogenic, where predictors disagree.

**Column selection (data path decision).** Columns are chosen from the **variant library** (`variant-library.ts`),
which the Workbench rail already renders (`LibrarySection`, `WorkbenchShell.tsx:305`) and which `/compare` (Batch)
already writes to. But `SavedVariant` only stores `gene/variant/query/classification/hgvs_full`
(`variant-library.ts:4-19`) — **not** the predictor evidence the grid needs. So:

- **Column 1** is always the current Workbench variant (`gene` + `cdna` from `WorkbenchClient`).
- **Columns 2–3** are picked from a compact library picker (or pasted as `GENE c.x>y`).
- For each column, the grid runs `variantLookup()` (`api.ts:38-69`) to get a full `LookupResponse`, from which it
  reads REVEL/SpliceAI/gnomAD/ClinVar/codon/consequence/domain. (`VariantSummaryRow` `backend.ts:57-64` is too
  thin — it has no scores — so the summary endpoint alone is insufficient.)

Rows (per FE-7 plan `plans/v2-frontend.md:897`): **Codon · Consequence · ClinVar · gnomAD AF · REVEL ·
SpliceAI Δ · UniProt domain · Conservation · Mechanism.** (AlphaMissense is **ON HOLD** project-wide — omit the row;
keep the data path so it can re-appear. Memory: AlphaMissense removed from FE display only, reversible.)

| State | Design |
| --- | --- |
| Empty (≤1 variant chosen) | "Add a second variant to compare." + library picker + paste field. Column 1 (current variant) shown filled; columns 2–3 are dashed add-tiles. |
| Loading (per column) | Each column header shows a spinner + the HGVS being resolved; rows render skeleton cells. Columns resolve **independently** (one slow lookup must not block the others — `Promise.allSettled`, not `all`). |
| Success | 4-col grid (`200px 1fr 1fr 1fr`, already in `.compare-grid` `workbench.css:2396`). Predictor rows render **score + horizontal bar with a threshold marker** (REVEL ≥0.7, SpliceAI Δ ≥0.5). Mechanism/ClinVar cells use `--warn/--ok/--err` tone classes (`.compare-grid .v.warn/.ok/.err` `:2432-2434`). |
| Error (one column fails) | That column shows an inline error cell ("Lookup failed — retry") with a retry affordance; the **other columns stay rendered** (the allSettled win). |
| Edge: cross-gene compare | Allowed, but Codon/domain rows show "—" where not comparable; add a subtle "different gene" note in the column header. |
| Edge: 3rd column removed | Grid reflows to `200px 1fr 1fr` (drop a column template); no layout jump. |
| Edge: predictor absent for a variant | Cell = "—" (not 0); never imply a missing score is a benign score. |

### 2.6 FE-8 AskEamos pill — PLACEHOLDER only (PARKED)

Per the parked-feature memory + brief: **no live wiring.** Design the affordance, not the chat.

- Floating bottom-right pill (`.ai-pill`, `workbench.css:2437-2454`), mounted in `WorkbenchShell` so it persists
  across tool switches (the FE-8 plan requires "stays mounted," `plans/v2-frontend.md:918`).
- Label: `Ask Eamos · <tool>` where `<tool>` tracks the active tool (`viewer/primer/crispr/align/compare`),
  reading the same `tool` state already threaded through `WorkbenchShell`.
- **Disabled state**: a "Coming soon" badge (mirror the report `AskEamos` pattern, `AskEamos.tsx:115-131`).
  Click does **not** open a live chat; instead it opens the `.ai-panel` (`workbench.css:2465-2480`) showing the
  parked message + the tool-aware suggested-question chips from the plan (`plans/v2-frontend.md:911-916`) rendered
  as **non-submitting** preview chips (so the IA is visible, but nothing calls `/api/v1/chat`).

| State | Design |
| --- | --- |
| Idle (collapsed) | pill with tool label + "Coming soon" dot |
| Open (panel) | parked banner ("Variant-aware chat is coming…", reuse `AskEamos.tsx:228` copy) + greyed suggested chips |
| Disabled input | textarea present but `disabled` with the parked placeholder; send button inert |

⚠ **GATED — needs Steven OK:** mounting a persistent floating pill is a durable visual/nav element. Recommend
shipping it **disabled/Coming-soon** only after Steven confirms he wants the affordance visible before funding the key.

---

## §3 Visual design (within the existing system)

All within the Reading Room OKLCH system (`DESIGN.md`, `app/web/app/globals.css`): `--ink-*`, `--line`,
`--bg-soft*`, `--mono` for codes/sequences, the elevation scale `--elev-0..3`, motion tokens `--dur-1..3` +
`--ease-standard/emphasized/exit`, and the **Dashboard Interaction Language** (`DESIGN.md:22-160`).

### 3.1 Reuse, don't reinvent
- **Icons**: `ToolIcon.tsx` already has a `compare` glyph (two columns, `:44-50`) — use it. No new icon system.
- **Cards/disclosure**: the Comparator's per-cell "view evidence" detail (if any) follows the
  `PrimerResultCard` 3-layer pattern (`PrimerResultCard.tsx:7-23`) — `button[aria-expanded]` + grid-rows reveal.
- **Tables**: reuse `.tool-table` (CRISPR guide table, `DesignTab.tsx:339`) idioms for any tabular comparator
  fallback; the primary comparator layout is the existing `.compare-grid`.
- **Status tones**: reuse the `Metric` tone pattern (`ok/warn/err`) from `AlignPanel.tsx:281-296`.

### 3.2 Comparator grid
- Layout: existing `.compare-grid` (`grid-template-columns: 200px 1fr 1fr 1fr`, `workbench.css:2394-2410`).
  For 2 variants, switch to `200px 1fr 1fr` at the component level (inline template override; no new token).
- Row headers (`.row-h`): uppercase `--ink-4` labels. Column headers (`.col-h`): `--mono` HGVS.
- **Predictor bar** (new micro-component, but **no new token**): a 0–1 horizontal track (`--bg-soft` rail,
  `--teal`/`--warn`/`--err` fill by tier) with a 1px threshold marker at the clinical cutoff. Mirrors the report
  predictor-bar idiom referenced in the FE-7 plan (`plans/v2-frontend.md:897`).
- Mechanism/ClinVar cells: `.v.warn/.ok/.err` (already defined `:2432-2434`).

### 3.3 AskEamos pill
- `.ai-pill` + `.ai-panel` CSS already exist and conform (`--ink-2` pill, `--elev`-style shadow, `--teal-deep`
  hover, `workbench.css:2437-2525`). Reuse verbatim; add only a disabled/coming-soon visual treatment (reduce
  opacity, swap hover off, append the "Coming soon" pill used in `AskEamos.tsx:115-131`).

### 3.4 New affordance: live-vs-demo provenance chip (small, shared)
The biggest honesty win once `use_real_apis` flips: a small chip in each tool's panel head reading **`Live`**
(teal) or **`Demo data`** (neutral), driven by a response marker. Today Primer fakes this with `primer-mock-note`
(`PrimerPanel.tsx:256-263`) and CRISPR with provider disclosure (`crispr-disclosure.ts`). Unify into one chip
component used by Primer/CRISPR/Align/Comparator. **New token: none** (uses `--teal-tint`/`--bg-soft`).

### 3.5 New tokens called out
**None required.** Every surface maps to existing tokens. If Steven wants the predictor-bar threshold marker to
have a dedicated colour, that would be one new token (`--threshold`) — flagged, not assumed.

---

## §4 Component plan

### Extend (existing files)
| File | Change (intent, not diff) |
| --- | --- |
| `tools.ts` | Add `'compare'` to `TOOL_ORDER` `:3`; extend `viewerCollapsed` `:50-52` to include `compare`. ⚠ GATED. |
| `WorkbenchShell.tsx` | Add `'compare'` to `PANEL_TOOLS` `:46`; add `case 'compare'` to `renderToolPanel` `:48-64`; mount `<AskEamosPill tool={tool} />` (disabled) once per shell `:296-308`. |
| `lib/api.ts` | Add `alignSequences()` export mirroring `designPrimers` mock-first pattern `:154-166` (close the Align no-fallback gap, §2.4). Add an `ALIGN_SAMPLE` fixture under `lib/workbench/`. Optionally add `compareVariants()` if the batched endpoint lands (§5). |

### New files
| File | Purpose |
| --- | --- |
| `components/workbench/compare/ComparatorPanel.tsx` | FE-7 grid: column picker (current + library + paste), per-column `variantLookup`, `Promise.allSettled` resolution, the `.compare-grid` render, all §2.5 states. |
| `components/workbench/compare/ComparatorColumn.tsx` | One variant column: header (HGVS + spinner/error/retry), maps `LookupResponse` → row cells. |
| `components/workbench/compare/PredictorBar.tsx` | 0–1 bar + threshold marker (REVEL/SpliceAI). |
| `lib/workbench/comparator-map.ts` | Pure mapping `LookupResponse → ComparatorRow[]` (testable; mirrors `gene-viewer-adapter` style). Reads codon/consequence/clinvar/gnomad/spliceai/REVEL/domain from `backend.ts` fields. |
| `components/workbench/ai/AskEamosPill.tsx` | Disabled tool-aware pill + parked panel. Reuses `.ai-pill`/`.ai-panel` CSS. **No `/api/v1/chat` call.** |
| `lib/workbench/align-sample.ts` | `ALIGN_SAMPLE` mock for the offline align fallback. |

### Touch-free (reference only)
`PrimerPanel`, `PrimerResultCard`, `CrisprPanel`, `DesignTab`, `OutcomesTab`, `GuideTrack`, `IndelSpectrum`,
`AlignPanel` core — unless the unified provenance chip (§3.4) is approved, which would lightly edit each panel head.

---

## §5 Backend deps (Codex lane / M-002)

| # | Dep | Why | Status |
| --- | --- | --- | --- |
| **D1** | **Flip `use_real_apis` (or a Workbench-scoped flag) in the deployed env** so `/primer`,`/crispr`,`/align` return Primer3/Bio.Align/CRISPR output instead of fixtures. | The engine is built (`workbench_design.py`) and deps installed; only the flag gates it. This is the single highest-leverage backend action. | Engine BUILT (`workbench.py:51-75`, providers `:1302-1315`); flag `settings.use_real_apis` default `false`. |
| **D2** | **Implement `POST /api/v1/crispr/tide`.** | FE `analyzeTide` (`api.ts:182-199`) calls it but the route **does not exist** in `workbench.py` → always falls back to `CRISPR_TIDE_SAMPLE`. This is the real M-002 gap. Outcomes tab can't show real TIDE/Lindel data without it. | **NOT FOUND** in `workbench.py`. FE mock-first, not blocked. |
| **D3** | **Response shape parity for the live path** — confirm `PrimerResponse`/`CrisprResponse`/`AlignResponse` from the *real* providers match the FE `backend.ts` mirrors and the fixtures (esp. `pairs`, `guides`, `trace_channels`, `q_scores`). | FE renders straight off these shapes; a drift = silent blanks. | Schemas at `app/backend/app/schemas/workbench.py`; FE mirror `lib/backend.ts`. Verify, don't assume. |
| **D4** | **ARMS real-mode primer design** (or an explicit "ARMS unsupported" error code FE can detect). | `PrimerPanel` already guards an ARMS-unsupported error (`:104-105, 247-252`); needs the backend to either support ARMS or return a stable code. | FE guard BUILT; backend behaviour unverified. |
| **D5** | **(Comparator efficiency) Batched compare endpoint** `POST /api/v1/compare` taking 2–3 variants → predictor rows in one round-trip. | v1 Comparator can ship on N parallel `variantLookup` calls (no backend dep), but that's N full pipeline runs. A batched endpoint returning just the comparator rows is the scale win. | Optional; FE v1 works without it. |
| **D6** | **AskEamos `/api/v1/chat` real provider** — **DO NOT REQUEST.** PARKED until Steven funds an LLM key (`LLM_PROVIDER=mock`). | FE-8 is placeholder-only by design. | Route EXISTS (`chat.py:12-33`) but mock; intentionally not wired. |

---

## §6 Gated items (⚠ need Steven's explicit OK before shipping)

1. **Add `compare` as a 5th rail tool** (durable nav change). `TOOL_ORDER` + `PANEL_TOOLS` + `viewerCollapsed`.
   Recommended position: last. Without this the Comparator is unreachable.
2. **Mount a persistent floating AskEamos pill** (durable visual element on every Workbench view), even disabled.
   Recommend: ship it Coming-soon only if Steven wants the affordance visible pre-funding; otherwise leave the
   orphaned CSS dormant and skip FE-8 entirely this cycle.
3. **Flip Workbench to live data** (`use_real_apis` for the tool endpoints in the deployed env). This changes what
   every clinician sees from "RPE65 demo fixture" to real per-variant output — a product-visible behaviour change,
   and a Codex/deploy action (memory: after a backend push Codex owns the Render redeploy + live verify).

---

## §7 Open questions for Steven

1. **Comparator scope** — is the v1 column set the full FE-7 row list (Codon/Consequence/ClinVar/gnomAD/REVEL/
   SpliceAI/domain/conservation/mechanism, **minus AlphaMissense** per the hold), or a leaner first cut
   (ClinVar + REVEL + SpliceAI + gnomAD)? Leaner ships faster and dodges the conservation/mechanism sourcing.
2. **Comparator column source** — confirm columns come from the **variant library** (current + saved) plus a paste
   field, rather than a free-typed search per column. (Library is already in the rail; reuse is cheap.)
3. **AskEamos pill** — do you want the disabled "Coming soon" pill **visible now** (sets user expectation), or
   should FE-8 stay fully dormant until the LLM key is funded? (I will not wire live chat either way.)
4. **Go-live on real tool data** — do you want me to coordinate with Codex to flip `use_real_apis` for the
   Workbench endpoints (and own the live-verify), or keep Workbench mock-first until the Comparator + provenance
   chip land so the whole surface flips to "Live" at once?
5. **Align mock fallback** — OK to add an `ALIGN_SAMPLE` so an offline `/workbench` paints a chromatogram (matching
   Primer/CRISPR behaviour)? Tiny, but it's a new fixture and a small `api.ts` addition.
