# Workbench tools — implementation spec (Align extension · Align mock fallback)

## ⚠ REVISION 2026-06-06 (Steven directive) — Comparator DROPPED; Workbench "compare" = Align

> The property-grid **Variant Comparator is CUT** — redundant with the report (per-variant) and the
> Batch table (multi-variant annotations). "Compare two variants" in the Workbench means pairwise
> **sequence alignment** — variant-vs-variant or variant-vs-control (reference/wild-type), from web
> sequence or **Sanger AB1** — which is the existing **Align** tool's job. We **extend Align**, not
> build a new tool. **Actionable revised runbook: `docs/workbench-tools/plan.md` Phases A/B/C.**

- **SUPERSEDED in this spec:** every **Comparator** section — the grid, `comparator-map`,
  `PredictorBar`, `ComparatorColumn`, `ComparatorPanel`, and the 5th-`compare`-rail-tool wiring.
- **STILL VALID:** the **Align offline mock fallback** spec (→ plan Phase A). **STILL PARKED:** the
  AskEamos placeholder (Steven didn't select it).
- **NEW scope (see plan):** Align two-subject selector (A/B each = current variant · library pick ·
  reference/control · paste/FASTA · Sanger AB1; variant-vs-control stays the default); repurpose the
  WorkRail "Compare tray" → "Align in Workbench".
- **Ghost cleanup (Codex-coordinated):** drop `'compare'` from the `WorkbenchTool` union
  (`backend.ts` + both `backend.ts` mirrors), then remove `TOOL_META.compare` + the orphaned
  `.compare-grid` / `.predictor-bar` CSS. FE-only until then: just never add `'compare'` to `TOOL_ORDER`.

---


Implementation spec. **Markdown only — no application code in this deliverable.** Active surface is the
Next.js 16 app at `app/web/`. The Vite app (`app/frontend/`) is read-only reference; `/runs` is frozen v1.

Stamped 2026-06-06. Built on the verified Wave-1 design `docs/workbench-tools/design.md` (trust its §0 audit) and
re-verified against the tree at commit `8a571eb`. Every `file:line` below was re-confirmed while writing this spec.

---

## §0 Scope & non-goals

### In scope (this spec is buildable now, mock-first)
1. **FE-7 Comparator** — the missing 2–3 variant side-by-side grid. New components + a pure mapper; data sourced
   per-column from `variantLookup()` (`LookupResponse`), resolved independently via `Promise.allSettled`.
2. **Wire `compare` into the rail** — add it to `TOOL_ORDER` (`tools.ts:3`), `PANEL_TOOLS` + `renderToolPanel`
   (`WorkbenchShell.tsx:46-64`), `viewerCollapsed` (`tools.ts:50-52`). ⚠ **GATED nav change** (§7.1).
3. **Align offline mock fallback** — add `alignSequences()` to `lib/api.ts` mirroring `designPrimers`'s mock-first
   pattern (`api.ts:154-166`), plus an `ALIGN_SAMPLE` fixture, so a network error paints a demo trace instead of a
   dead panel (the one true Align gap, design §2.4).
4. **FE-8 AskEamos pill** — a **disabled, tool-aware "Coming soon" placeholder shell only**. No `/api/v1/chat` call.
   ⚠ **GATED visual element** (§7.2).

### Out of scope (non-goals)
- Rebuilding Primer / CRISPR / Align panels — they are BUILT + mock-wired and ship as-is
  (`PrimerPanel.tsx:35-289`, `CrisprPanel.tsx:18-63`, `AlignPanel.tsx:29-262`).
- Building **live** AskEamos chat (PARKED: LLM key unfunded; route is `LLM_PROVIDER=mock`, `chat.py:12-33`).
- Any edit to `app/backend/**`, `agent_handoff/**`, `/runs`, the Batch (`/compare` route) surface, the icon system
  (`Icon.tsx` / `ToolIcon.tsx`), the design tokens, or any `:3000` dev server.
- Flipping `use_real_apis` (a Codex/deploy action, §6 D1; §7.3 gated).
- The unified live-vs-demo provenance chip (design §3.4) — **deferred to Wave 3**; not specified here to keep this
  change set surgical. The Comparator reuses the existing `primer-mock-note` idiom in v1.
- AlphaMissense — project-wide ON HOLD; the comparator omits the row but the mapper keeps the data path (§3.1).

---

## §1 Contracts & types (reuse — do not redefine)

All types already exist in `app/web/lib/backend.ts`. **No new contract types. No schema edits.** Cite & reuse:

| Type | Location | Use in this spec |
| --- | --- | --- |
| `WorkbenchTool` (incl `'compare'`) | `backend.ts:1145` | already a union member; rail wiring only |
| `LookupRequest` / `LookupResponse` | `backend.ts:307-314` (`LookupResponse`) | per-column comparator data source |
| `ReportPayload` | `backend.ts:82-112` | `LookupResponse.report_payload` carries everything the grid needs |
| `InSilicoPredictions` / `PredictorCard` | `backend.ts:459-471` | **the predictor rows** — `{name,score,threshold,verdict,verdict_label}`; exactly the bar shape |
| `LocusContext` / `CodonCell` | `backend.ts:451-457, 442-449` | Codon row (`codon_strip`, `is_query`) |
| `VariantSummaryRow` | `backend.ts:57-64` | gnomAD AF (`:220`) / spliceai (`:221`) / clinvar (`:222`) header fields |
| `ComputationalDeepDiveSection` / `ComputationalPredictorRow` | `backend.ts:865-887` | Conservation row + SpliceAI Δ (`spliceai_max_delta:882`) when `in_silico_predictions` is thin |
| `PrimerResponse` / `CrisprResponse` / `AlignResponse` | mirrors in `backend.ts` | unchanged; Align fixture must match `AlignResponse` shape |

### `variantLookup()` (the comparator's only network call)
`api.ts:38-69`. Signature: `variantLookup(payload: LookupRequest, init?: {signal?: AbortSignal}) → Promise<LookupResponse>`.
It already does **one transient retry** (network `TypeError` + 5xx) and is `AbortSignal`-aware — the comparator gets
cancellation + retry for free; it must NOT re-implement them.

### New **local** (non-contract) types — defined inside the new files, not in `backend.ts`
- `ComparatorRow` (in `lib/workbench/comparator-map.ts`): the mapped row model the grid renders.
  Shape: `{ id: string; label: string; kind: 'text' | 'tone' | 'predictor'; cells: ComparatorCell[] }`.
- `ComparatorCell`: `{ value: string | null; tone?: 'ok'|'warn'|'err'; score?: number; threshold?: number }`
  (`value: null` ⇒ render `—`; `score`/`threshold` present ⇒ render a `PredictorBar`).
- `ColumnState` (in `ComparatorPanel.tsx`): `{ id; query: string; gene: string; cdna: string;
  status: 'loading'|'ready'|'error'; data?: LookupResponse; error?: string }`.

These are UI view-models, not wire contracts — they live with their consumers.

---

## §2 Component / file plan — CREATE vs EDIT (with line anchors)

### CREATE
| File | Purpose | Key references |
| --- | --- | --- |
| `components/workbench/compare/ComparatorPanel.tsx` | Orchestrator: column state, picker (current + library + paste), `Promise.allSettled` lookups, renders the `.compare-grid`, all §3.1 states. | mirrors `PrimerPanel.tsx:35-289` panel shape; `variantLookup` `api.ts:38` |
| `components/workbench/compare/ComparatorColumn.tsx` | One column header cell + per-row cells from one `LookupResponse`. Header shows HGVS, spinner, error+retry, remove-✕. | `.compare-grid > div.col-h` `workbench.css:2419` |
| `components/workbench/compare/PredictorBar.tsx` | 0–1 horizontal bar + threshold marker. Pure presentational. | tone classes `workbench.css:2432-2434`; `PredictorCard` `backend.ts:459-466` |
| `lib/workbench/comparator-map.ts` | **Pure** `LookupResponse → ComparatorRow[]`. The testable core. No React. | reads `report_payload.in_silico_predictions` / `locus_context` / `variant_summary_rows` |
| `lib/workbench/align-sample.ts` | `ALIGN_SAMPLE: AlignResponse` fixture for the offline fallback. Must satisfy the `AlignResponse` mirror (trace_channels / q_scores / alignment rows). | shape parity with `AlignPanel.tsx` consumers `:408-525` |
| `components/workbench/ai/AskEamosPill.tsx` | Disabled tool-aware pill + parked panel. **No network.** | `.ai-pill`/`.ai-panel` `workbench.css:2437-2525`; parked copy idiom `aistack/AskEamos.tsx:226-229` |

### EDIT
| File | Anchor | Change (intent — not a diff) |
| --- | --- | --- |
| `components/workbench/tools.ts` | `:3` | Add `'compare'` to `TOOL_ORDER` (recommend last). ⚠ GATED §7.1 |
| `components/workbench/tools.ts` | `:50-52` | `viewerCollapsed`: return true for `tool === 'align' \|\| tool === 'compare'` (compare is a full-width grid, not a track). |
| `components/workbench/WorkbenchShell.tsx` | `:46` | Add `'compare'` to `PANEL_TOOLS`. ⚠ GATED §7.1 |
| `components/workbench/WorkbenchShell.tsx` | `:48-64` | Add `case 'compare': return <ComparatorPanel gene={gene} cdna={cdna} />` to `renderToolPanel`. |
| `components/workbench/WorkbenchShell.tsx` | `:296-308` (shell return) | Mount `<AskEamosPill tool={tool} />` **once** so it persists across tool switches. ⚠ GATED §7.2 |
| `lib/api.ts` | after `:166` (next to `designPrimers`) | Add `alignSequences(payload): Promise<AlignResponse>` — POST `/api/v1/align`, `catch (err) { if (err instanceof TypeError) return ALIGN_SAMPLE; throw err }`. |
| `components/workbench/align/AlignPanel.tsx` | `:672-701` (`requestApiAlignment`) | Route the API call through the new `alignSequences()` instead of the bare `fetch` so the mock fallback applies. Surgical: swap the call site only; keep `apiStatus` machine intact. |

### CSS — **edit, do not author new**
The orphaned `.compare-grid` CSS (`workbench.css:2394-2434`) and `.ai-pill`/`.ai-panel` (`:2437-2525`) are reused.
**One required CSS fix** (see §3.1 edge): `.compare-grid > div:nth-child(4n) { border-right: none; }` (`:2410`)
hard-codes a 4-column grid; for a 2-variant (3-column) layout the last-column border won't clear. Resolve by using a
last-of-row class on cells from the components rather than `nth-child(4n)` — i.e. components add a `.col-last` class
and the CSS targets `.compare-grid > div.col-last { border-right: none; }`. (Replaces the `nth-child` rule; tiny.)
A `.predictor-bar` block is added near the `.compare-grid` rules (rail + fill + 1px threshold marker), using existing
tokens only (`--bg-soft`, `--teal-deep`, `--warn`, `--err`, `--line`). No new token (design §3.5).

---

## §3 Behaviour spec

### 3.1 Comparator — 2–3 variant grid

**Layout.** `.compare-grid` with `grid-template-columns: 200px 1fr 1fr 1fr` for 3 variants (`workbench.css:2396`).
For 2 variants override at the component level to `200px 1fr 1fr` (inline style; no new token). First grid column =
row-header labels (`.row-h`); remaining columns = variants. Compare collapses the sequence viewer (`viewerCollapsed`).

**Columns.**
- **Column 1 is always the current Workbench variant** — `gene` + `cdna` threaded from `WorkbenchClient`
  (`WorkbenchShell` already receives `gene`/`cdna`, `:41-42`). It is fixed and not removable.
- **Columns 2–3** are added from a compact picker with two sources:
  1. **Variant library** — read via `getLibrary()` (`variant-library.ts:55`) + `subscribe()` (`:120`) through
     `useSyncExternalStore` (the same pattern `LibrarySection` already uses). Each `SavedVariant` gives
     `gene`/`query`/`hgvs_full` (`:4-19`) — enough to build a `LookupRequest`.
  2. **Paste field** — free text `GENE c.x>y`; parsed into `{gene, cdna}` (reuse the existing input-resolution path
     the report search uses; if unavailable inline, accept the raw string as `cdna` and let the backend resolve).
- **Add/remove.** Empty column slots render as dashed add-tiles. A filled column 2/3 shows a remove-✕ in its header.
  Max 3 columns total (`TOOL_META.compare.sub` says "2–3 variants", `tools.ts:44`); the add-tile disappears at 3.

**Data path (per column).** For each non-current column, call `variantLookup({gene, cdna})` and map the
`LookupResponse.report_payload` through `comparator-map.ts`. **Column 1 reuses the same lookup** (do NOT special-case
it to read the viewer payload — the viewer payload is a `GeneViewerResponse`, not a `LookupResponse`; uniform lookups
keep the mapper single-path). Resolve all columns with **`Promise.allSettled`, never `Promise.all`** — one slow or
failed lookup must not blank the others.

**Rows (mapper output, in order).** Source each from `report_payload`:

| Row | Source field | Notes |
| --- | --- | --- |
| Codon | `locus_context.codon_strip[]` where `is_query` (`backend.ts:442-456`) | `aa_ref{codon}aa_alt`; `—` if absent |
| Consequence | derive from codon cell / `variant_summary_rows` | text |
| ClinVar | `variant_summary_rows[].clinvar` (`backend.ts:222`) | tone cell (`ok`/`warn`/`err` by verdict text) |
| gnomAD AF | `variant_summary_rows[].gnomad` (`backend.ts:220`) | text; `—` (not `0`) when absent |
| REVEL | `in_silico_predictions.cards[]` where `name==='REVEL'` (`backend.ts:459-466`) | **predictor bar** (score+threshold 0.7) |
| SpliceAI Δ | `in_silico_predictions.cards[] name==='SpliceAI'`, else `computational_deep_dive.spliceai_max_delta` (`backend.ts:882`) | **predictor bar** (threshold 0.5) |
| UniProt domain | from `computational_deep_dive` / report header | text; `—` if none |
| Conservation | `computational_deep_dive.conservation[]` (`backend.ts:884`) | text |
| Mechanism | report mechanism note | tone cell |

**AlphaMissense row is omitted** (project ON HOLD). The mapper still *reads* an AlphaMissense `PredictorCard` if
present (`backend.ts:460` includes it in the union) and stores it un-rendered, so re-enabling is one render-list edit.

**Predictor bar.** A 0–1 track (`--bg-soft` rail) with fill colored by tier and a 1px threshold marker at the
clinical cutoff (REVEL 0.7, SpliceAI 0.5). Fill `--teal-deep` when below/benign side, `--warn` mid, `--err` when past
the damaging threshold — keyed off `PredictorCard.verdict` (`damaging`/`tolerated`/`uncertain`, `backend.ts:432,463`)
so color tracks the backend's verdict, not a FE re-threshold. Score text sits beside the bar in `--mono`.

#### States & edge cases
| State | Behaviour |
| --- | --- |
| Empty (≤1 column filled) | "Add a second variant to compare." Column 1 filled; columns 2–3 dashed add-tiles + library picker + paste field. |
| Loading (per column) | Column header shows spinner + the HGVS being resolved; that column's row cells render skeletons. Columns resolve independently (allSettled). |
| Success | Full grid; predictor rows show bar + score; tone cells colored. |
| Error (one column) | Only that column shows an inline "Lookup failed — retry" header with a retry button (re-issues `variantLookup`); other columns stay rendered. |
| Edge: cross-gene compare | Allowed. Codon / domain cells render `—` where not comparable; column header shows a subtle "different gene" note when `column.gene !== current.gene`. |
| Edge: 3rd column removed | Grid reflows to `200px 1fr 1fr`; cells get `.col-last` so the right border clears (the CSS fix, §2). No layout jump. |
| Edge: predictor absent | Cell = `—`, never `0`. A missing score must never read as a benign score. |
| Edge: duplicate variant added | Picker dedupes against existing columns by `query.toLowerCase()` (same key `saveVariants` uses, `variant-library.ts:85`). |
| Edge: backend down (TypeError) | `variantLookup` already retries once then throws → column → error state with retry. (No comparator mock fixture in v1 — the report-style lookup has no bundled sample; flagged as Open Q §8.) |

#### A11y
- Grid wrapped in `role="table"`; row-header cells `role="rowheader"`, column headers `role="columnheader"`.
- Predictor bar: `role="meter"` with `aria-valuemin=0 aria-valuemax=1 aria-valuenow={score}` +
  `aria-label="REVEL 0.82 (threshold 0.70)"`. Color is never the only signal — score text always present.
- Add-tile is a real `<button>`; remove-✕ has `aria-label="Remove {hgvs} column"`.
- Retry button is focusable, `aria-label="Retry lookup for {hgvs}"`.

### 3.2 Wire `compare` into the rail — ⚠ GATED nav change (§7.1)
- `TOOL_ORDER` (`tools.ts:3`): append `'compare'` → `['viewer','primer','crispr','align','compare']`. Recommended
  **last** — it is a cross-variant view, not a single-variant tool.
- `PANEL_TOOLS` (`WorkbenchShell.tsx:46`): add `'compare'`.
- `renderToolPanel` (`:48-64`): `case 'compare'` → `<ComparatorPanel gene cdna />`.
- `viewerCollapsed` (`tools.ts:50-52`): include `compare`.
- `ToolBar` (`ToolBar.tsx:11-30`) maps `TOOL_ORDER` automatically — **no edit needed**; the `compare` glyph already
  exists (`ToolIcon.tsx:44-50`) and `TOOL_META.compare` is defined (`tools.ts:41-46`). Adding to the order alone
  makes the rail button appear.
- Until Steven approves, the Comparator components can land **un-wired** (files exist, not in `TOOL_ORDER`), so the
  build is reviewable without a live nav change.

### 3.3 Align offline mock fallback
- New `alignSequences(payload): Promise<AlignResponse>` in `lib/api.ts` (next to `designPrimers`, `:154-166`),
  same mock-first idiom: `try { fetch /api/v1/align } catch (TypeError) { return ALIGN_SAMPLE }`.
- `AlignPanel.tsx` currently calls `/api/v1/align` directly with **no fallback** (`:672-701`); reroute that one call
  site through `alignSequences()`. The `apiStatus` state machine (`:65-90`) and `TracePanel` (`:408-471`) are
  untouched — on offline, the resolved `ALIGN_SAMPLE` flows through the existing success path and paints the 4-channel
  trace, matching Primer/CRISPR behaviour. Error copy ("browser alignment remains available", `:440`) is unchanged.
- `ALIGN_SAMPLE` must include the fields `TracePanel`/chromatogram read: alignment rows + `trace_channels` +
  `q_scores` (`AlignPanel.tsx:473-525`). Build it from a small RPE65-region pair to stay on-brand with the viewer.
- Only the **API path** gets the mock; the browser-fallback `compareSequences` path (`:51`) is unaffected.

### 3.4 AskEamos disabled placeholder shell — ⚠ GATED visual element (§7.2)
- `<AskEamosPill tool={tool} />` mounted once in `WorkbenchShell` (`:296-308`) so it persists across tool switches
  (FE-8 plan: "stays mounted"). Reuses `.ai-pill`/`.ai-panel` CSS verbatim (`workbench.css:2437-2525`) + a
  disabled treatment (reduced opacity, hover off).
- **Collapsed (idle):** pill labeled `Ask Eamos · {tool}` (tool from the threaded `tool` prop:
  viewer/primer/crispr/align/compare) + a "Coming soon" dot.
- **Open (panel):** clicking opens `.ai-panel` showing the parked banner (reuse copy idiom from
  `aistack/AskEamos.tsx:226-229`) + tool-aware suggested-question chips rendered as **non-submitting preview chips**
  (so the IA is visible but nothing calls the API).
- **Disabled input:** textarea present but `disabled` with a parked placeholder; send button inert.
- **Hard invariant:** this component imports nothing from `lib/api.ts` related to chat and never references
  `/api/v1/chat`. It is a shell.
- A11y: pill is a `<button aria-disabled>` with `aria-label="Ask Eamos about {tool} — coming soon"`; the open panel
  is `role="dialog" aria-label` + focus-trap-free (it's inert content); preview chips are non-interactive `<span>`s,
  not buttons (nothing to activate).

---

## §4 Invariants (existing tools must not regress)

1. **Primer/CRISPR/Align panels render identically** for all existing states — no edits except the single Align call
   re-route (§3.3). `PrimerPanel`, `PrimerResultCard`, `CrisprPanel`, `DesignTab`, `OutcomesTab`, `GuideTrack`,
   `IndelSpectrum` are touch-free.
2. **Mock-first preserved everywhere.** `designPrimers`/`designGuides`/`analyzeTide` keep their `TypeError`→sample
   fallbacks (`api.ts:163,177,197`); the new `alignSequences` follows the same shape; default `provider=mock`.
3. **Rail ordering before `compare`** is unchanged (`viewer · primer · crispr · align`); adding `compare` appends,
   does not reorder.
4. **The viewer still collapses for align** (`viewerCollapsed` keeps `align`; only adds `compare`).
5. **No contract/schema drift.** Zero edits to `backend.ts` type definitions, `app/backend/**`, or any wire shape.
6. **No new icon, no new token, no new dependency.** Reuse `ToolIcon` compare glyph + existing OKLCH tokens + the
   orphaned CSS (with the one `nth-child(4n)`→`.col-last` fix).
7. **AskEamos never goes live.** No `/api/v1/chat` call from anywhere new.
8. **Type-check + lint clean** — `npm --prefix app/web run lint` and `tsc` pass (app/web has the flat
   `eslint-config-next@16` gate).

---

## §5 Test plan

Vitest is the FE harness (see existing `lib/workbench/*` adapter tests). Prioritise the **pure mapper** — it carries
the comparator's correctness.

### Unit — `lib/workbench/comparator-map.ts` (highest value; pure, no React)
- Maps a full `LookupResponse` → all rows present, correct order, AlphaMissense excluded from the render list.
- REVEL/SpliceAI cells carry `score` + `threshold` (predictor-bar inputs); verdict→tone mapping correct.
- Missing predictor → cell `value: null` (renders `—`), **never `0`**.
- Missing `locus_context`/`in_silico_predictions` → graceful `—` rows, no throw.
- Cross-gene inputs → Codon/domain `—`; text rows still populate.

### Unit — `lib/workbench/align-sample.ts`
- `ALIGN_SAMPLE` satisfies the `AlignResponse` mirror (type-level + a runtime shape assert: has alignment rows,
  `trace_channels`, `q_scores`).

### Unit — `lib/api.ts` `alignSequences`
- 200 → returns parsed `AlignResponse`.
- `fetch` throws `TypeError` (offline) → returns `ALIGN_SAMPLE`.
- non-TypeError / 4xx → throws (no mock swallow), matching `designPrimers` semantics.

### Component — `ComparatorPanel`
- Empty: ≤1 column → add-tiles + picker shown.
- Two columns resolve → grid renders both; predictor bars present with `role="meter"` + correct `aria-valuenow`.
- One column rejects (mock `variantLookup` to reject for col 2) → col 2 error+retry, col 1 still rendered
  (proves `allSettled`, not `all`).
- Remove 3rd column → grid reflows to 3-col template; no last-border artifact (proves the `.col-last` CSS fix).
- Duplicate add is rejected by the picker dedupe.

### Component — `AskEamosPill`
- Renders disabled with `Ask Eamos · {tool}`; tool label updates with the `tool` prop.
- Open → parked banner + non-interactive preview chips; textarea `disabled`.
- Asserts **no** network call (spy on `fetch`/api — zero calls).

### Regression / manual (browser-verify on `:3000`)
- Primer/CRISPR/Align panels visually unchanged; Align offline (devtools offline) now paints a trace.
- Rail shows 5 tools only after the gated wiring lands; `compare` opens the grid with the viewer collapsed.

---

## §6 Backend deps (Codex lane / M-002)

| # | Dep | Why it matters | Status / blocking? |
| --- | --- | --- | --- |
| **D1** | Flip `use_real_apis` (or a Workbench-scoped flag) in the deployed env so `/primer`,`/crispr`,`/align` return real Primer3 / Bio.Align / CRISPR output instead of fixtures. | Highest-leverage backend action: engine is BUILT (`workbench_design.py`, providers `:1302-1315`), deps installed, only the flag gates it. | Not blocking this spec (mock-first). Product-visible → §7.3 gated. |
| **D2** | **Implement `POST /api/v1/crispr/tide`.** | FE `analyzeTide` (`api.ts:182-199`) calls it but the route **does not exist** in `workbench.py` → always 404 → FE serves `CRISPR_TIDE_SAMPLE`. **This is the single Codex dep that matters most** — Outcomes can't show real TIDE/Lindel data without it. | NOT FOUND in `workbench.py`. FE mock-first, not blocked, but real outcomes are gated on it. |
| **D3** | Live-path response-shape parity: confirm real `PrimerResponse`/`CrisprResponse`/`AlignResponse` match the `backend.ts` mirrors + fixtures (esp. `pairs`, `guides`, `trace_channels`, `q_scores`). | FE renders straight off these shapes; drift = silent blanks once D1 flips. | Verify when D1 lands. Schemas `app/backend/app/schemas/workbench.py`. |
| **D4** | (Comparator scale) Optional batched `POST /api/v1/compare` taking 2–3 variants → comparator rows in one round-trip. | v1 ships on N parallel `variantLookup` calls (no backend dep), but that's N full pipeline runs. A batched endpoint returning just the comparator rows is the scale win. | Optional. FE v1 works without it. |
| **D5** | AskEamos `/api/v1/chat` real provider — **DO NOT REQUEST.** | PARKED until Steven funds an LLM key (`LLM_PROVIDER=mock`). FE-8 is placeholder-only by design. | Route exists (`chat.py:12-33`); intentionally mock. |
| **D6** | ARMS real-mode primer design (or a stable "ARMS unsupported" error code). | `PrimerPanel` already guards an ARMS-unsupported error (`:104-105, 247-252`). | FE guard built; backend behaviour unverified. Not in this spec's scope. |

---

## §7 Gated items (⚠ need Steven's explicit OK before shipping — recommendation ≠ authorization)

1. **Add `compare` as a 5th rail tool** (durable nav change: `TOOL_ORDER` + `PANEL_TOOLS` + `viewerCollapsed`).
   **Decision needed:** include it, and where? **Recommendation:** YES, position **last**
   (`Sequence · Primer · CRISPR · Align · Compare`) — cross-variant view belongs after the single-variant tools.
   Mitigation: components can land un-wired so review happens before the nav flips.
2. **Mount the persistent floating AskEamos pill** (durable visual element on every Workbench view), even disabled.
   **Decision needed:** show a "Coming soon" pill now, or leave FE-8 fully dormant? **Recommendation:** ship it
   **disabled/Coming-soon** only if Steven wants the affordance visible pre-funding; otherwise skip FE-8 this cycle
   and leave the orphaned CSS dormant. (Open Q §8.3.)
3. **Flip Workbench to live data** (`use_real_apis` for the tool endpoints in the deployed env — D1). **Decision
   needed:** flip now, or keep mock-first until the Comparator + provenance chip land so the whole surface flips to
   "Live" at once? **Recommendation:** keep mock-first this cycle; flip in Wave 3 alongside the provenance chip so the
   change is legible (and per memory, Codex owns the Render redeploy + live-verify after the backend push).

---

## §8 Open questions for Steven

1. **Comparator row scope** — ship the full FE-7 row set (Codon · Consequence · ClinVar · gnomAD · REVEL · SpliceAI ·
   domain · conservation · mechanism, **minus AlphaMissense**), or a leaner first cut
   (ClinVar + REVEL + SpliceAI + gnomAD)? Leaner ships faster and dodges the conservation/domain sourcing edge cases.
2. **Comparator column source** — confirm columns come from the **variant library** (current + saved) plus a paste
   field, not a free-typed per-column search. (Library is already in the rail; reuse is cheap.)
3. **AskEamos pill visibility** — disabled "Coming soon" pill visible **now** (sets expectation), or fully dormant
   until the LLM key is funded? (Live chat stays unwired either way.)
4. **Comparator offline behaviour** — the report-style `variantLookup` has **no bundled sample fixture** (unlike
   primer/crispr/align). OK to ship the Comparator with **no offline mock** (offline ⇒ per-column error+retry), or do
   you want a small `LOOKUP_SAMPLE` so an offline `/workbench` Comparator paints demo columns? (Adds one fixture.)
5. **Align mock fallback** — OK to add `ALIGN_SAMPLE` + `alignSequences()` so an offline `/workbench` paints a
   chromatogram (matching Primer/CRISPR)? Tiny: one fixture + one `api.ts` export + one call-site re-route.
6. **Provenance chip timing** — confirm the unified live-vs-demo chip (design §3.4) is **deferred to Wave 3** (flips
   with `use_real_apis`), not built in this change set.
