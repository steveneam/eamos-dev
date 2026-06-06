# Workbench tools — phased build runbook (Align extension · Align mock fallback)

## ⚠ REVISION 2026-06-06 (Steven directive) — Comparator DROPPED; Workbench "compare" = sequence Alignment

> Decision (Steven, after reviewing this plan): the property-grid **Variant Comparator is cut.**
> It duplicates the report (per-variant) and the Batch table (multi-variant annotations). What
> "compare two variants" means in the Workbench is **pairwise sequence alignment** —
> variant-vs-variant, or variant-vs-control (reference / wild-type) — from web sequence or
> **Sanger AB1** import. That is the **Align** tool's job (it already does reference-vs-read +
> AB1 chromatogram), so we **extend Align** instead of building a new tool.

**What changes vs the runbook below:**
- ❌ **DROPPED:** Phase 0 (`.compare-grid` CSS fix), Phase 2 (Comparator components —
  `comparator-map` / `PredictorBar` / `ComparatorColumn` / `ComparatorPanel`), Phase 3 (5th
  `compare` rail tool). The `TOOL_META.compare` ghost + orphaned `.compare-grid` / `.predictor-bar`
  CSS stay **dormant** — do not build on them, do not add `'compare'` to `TOOL_ORDER`. (Fully
  removing the ghost means dropping `'compare'` from the `WorkbenchTool` union in `backend.ts`, a
  contract mirror → a Codex-coordinated cleanup, deferred.)
- ✅ **KEPT:** Phase 1 (Align offline mock fallback) → becomes **Phase A** below.
- ✅ **KEPT skipped:** Phase 4 (AskEamos pill) — Steven didn't select it; parked.

**New phases (the revised build):**

| # | Phase | Gated? | What | Verify (tsc 0 / lint 0 + browser) |
| - | ----- | ------ | ---- | -------------------------------- |
| **A** | Align offline mock fallback | ungated | = old Phase 1 (1.1–1.3): `ALIGN_SAMPLE` fixture + mock-first `alignSequences()` in `lib/api.ts` + reroute `AlignPanel`'s bare `fetch`. | offline `/workbench` → Align paints the chromatogram from the sample, not a dead error. |
| **B** | **Align "comparison subjects" — variant-vs-variant + variant-vs-control** | ⚠ GATED (UI change to the Align panel) | Add a **two-subject selector** to `AlignPanel` (`components/workbench/align/AlignPanel.tsx`): Subject A & Subject B, each from **{current variant · pick from library · reference/control (wild-type) · paste/FASTA · Sanger AB1}**. Default A = reference/control, B = current variant (= today's behaviour, `makeAlignmentSeed`, unchanged). Choosing a *variant* loads its sequence = the reference window with that variant's edit applied (reuse the gene-window + edit-state apply path; v1 = same-gene A & B applied to the shared window). Pairwise alignment + 4-channel chromatogram render unchanged. | pick variant A vs variant B (both from library) → pairwise alignment + diffs render; variant-vs-control still the default; AB1 upload still works for either subject. |
| **C** | **Repurpose WorkRail "Compare tray" → "Align in Workbench"** | ⚠ GATED (behaviour change to shared `LibrarySection`) | The Compare tray (pin 2+ saved variants) currently routes to `/compare` (Batch). Repoint its primary action to **"Align in Workbench"** — load the first two pinned variants into the Align tool as Subject A / B (`/workbench?...`). Optionally keep a secondary "Open in Batch" link. Rename the tray copy so "Compare" no longer implies the Batch table. | pin 2 library variants → "Align in Workbench" → Workbench opens on Align with A=var1, B=var2 aligned. |

**Order:** A (self-contained, ungated) → B (the core extension) → C (the tray hand-off, after B exists).
B and C are durable UI changes → Steven's final OK on browser-verify before ship (he's directed the
direction). **Backend:** `POST /api/v1/align` already exists (Sanger/AB1); variant-vs-variant where both
sequences come from the gene window is **FE-only** (apply edits client-side) — no new Codex contract for v1.

---

> Everything from here down is the **ORIGINAL (now SUPERSEDED) Comparator runbook**, retained for
> rationale + the still-valid Phase 1 (Align mock) detail (= Phase A above). Phases 0/2/3 are dropped.


Build runbook. **Markdown only — this deliverable edits no code.** Active surface is the Next.js 16 app at
`app/web/`. The Vite app (`app/frontend/`) is read-only reference; `/runs` is frozen v1.

Stamped 2026-06-06 (Wave 3). Built on the orchestrator-fact-checked spec `docs/workbench-tools/spec.md` and design
`docs/workbench-tools/design.md`. Every `file:line` below was re-confirmed against the tree at commit `8a571eb`
while writing this runbook.

**Verify gate (applies to EVERY step unless stated otherwise).** `app/web` has **no test runner** for app code
(there is no vitest config in `app/web`; the spec's §5 "Vitest is the FE harness" describes the *Vite* app — do NOT
assume a runner exists here). So each step's gate is:

1. `npx tsc --noEmit` run **inside `app/web`** → **0 errors**, AND
2. `npm --prefix app/web run lint` → **0 errors**, AND
3. a **browser-verify on `:3000`** of the SPECIFIC named condition in the step's "Browser-verify" cell.

**Abort on the first error.** Do not proceed to the next step until all three pass. Commands:

```
# type-check (must cd into app/web; the tsconfig is project-local)
( cd app/web && npx tsc --noEmit )
# lint
npm --prefix app/web run lint
# dev server is presumed already running on :3000 — do NOT start/stop a :3000 server (HARD RULE)
```

> **Pure-logic test note.** The mapper (`comparator-map.ts`) is the correctness core. With no runner in `app/web`,
> its "test" is **type-level + a temporary scratch assertion you delete before the step's gate** (or run via the Vite
> app's vitest if Steven later wants real specs). The runbook treats the mapper's gate as `tsc` clean + a browser
> render that proves the row set, `—`-not-`0`, and allSettled behaviour. (Open item — see Risks R7.)

---

## Phase order (one line)

**P0 (CSS fix) → P1 (Align mock, un-gated, self-contained) → P2 (Comparator components, UN-WIRED) → P3 (⚠ GATED rail wiring) → P4 (⚠ GATED AskEamos pill, optional).** Codex dep (TIDE endpoint) runs in a **separate lane**, blocks nothing here.

Rationale: P0/P1 are surgical and independently shippable. **P2 lands the entire Comparator (components + pure
mapper) un-wired** — the files exist and type-check but are NOT in `TOOL_ORDER`, so they are fully buildable and
code-reviewable **without** touching nav. P3 is the single gated nav flip that makes Compare reachable. P4 is
optional and gated. This ordering means the only irreversible/durable change (the rail) is isolated to one
approval-gated step that can wait on Steven without blocking P0–P2.

---

## Runbook (phased table)

### Phase 0 — Orphaned CSS fix (un-gated, prerequisite for P2's reflow)  ❌ SUPERSEDED (Comparator dropped — see REVISION at top)

| # | Unit | Files (CREATE/EDIT + anchors) | Browser-verify on `:3000` |
| --- | --- | --- | --- |
| 0.1 | Replace the hard-coded 4-column `nth-child(4n)` border rule with a class the components control, so a 2-variant (3-col) grid clears its last border. **Add the `.predictor-bar` block** (rail + fill + 1px threshold marker) using existing tokens only. | **EDIT** `components/workbench/workbench.css:2410` — replace `.compare-grid > div:nth-child(4n) { border-right: none; }` with `.compare-grid > div.col-last { border-right: none; }`. **EDIT** same file, insert a `.predictor-bar` block adjacent to the `.compare-grid` rules (`:2426-2434` area): track `background: var(--bg-soft)`, fill `var(--teal-deep)`/`var(--warn)`/`var(--err)` by tone class, 1px marker via `var(--line)`. **No new token** (DESIGN §3.5). | CSS-only change, no consumer yet → verify **no visual regression anywhere** on `/workbench` (the `.compare-grid`/`.predictor-bar` selectors have no DOM match until P2). Confirm `:3000/workbench` renders identically (Primer/CRISPR/Align panels unchanged). tsc/lint still gate. |

> Why P0 first: it is pure CSS, has **zero DOM consumers today** (grep `compare-grid` in `*.tsx` → no matches), so
> it is the safest possible first commit and unblocks P2's "remove 3rd column → border clears" edge without a later
> CSS round-trip.

### Phase 1 — Align offline mock fallback (un-gated, self-contained)

| # | Unit | Files (CREATE/EDIT + anchors) | Browser-verify on `:3000` |
| --- | --- | --- | --- |
| 1.1 | Create the `ALIGN_SAMPLE` fixture satisfying the `AlignResponse` mirror that `TracePanel`/chromatogram read (alignment rows + `trace_channels` + `q_scores`). Build from a small RPE65-region pair to stay on-brand. | **CREATE** `lib/workbench/align-sample.ts` — export `ALIGN_SAMPLE` typed against the align response shape consumed by `normalizeAlignResponse` (`AlignApiResponseShape`, `align/AlignPanel.tsx:9`, from `lib/workbench/alignment-pairwise`). Mirror the field set the chromatogram reads (`AlignPanel.tsx:473-525`). | None yet (no consumer) → gate is **tsc clean** (proves the fixture satisfies the response type) + lint. |
| 1.2 | Add `alignSequences()` to `lib/api.ts` next to `designPrimers`, mock-first: `try { fetch /api/v1/align } catch (err) { if (err instanceof TypeError) return ALIGN_SAMPLE; throw err }`. | **EDIT** `lib/api.ts` after `:166` (immediately after `designPrimers`, before `designGuides`) — add `export async function alignSequences(payload): Promise<…align response…>`. Import `ALIGN_SAMPLE` from `lib/workbench/align-sample`. Match the request body `requestApiAlignment` builds (`AlignPanel.tsx:683-688`: `{ gene, cdna, user_sequence, ab1_blob_base64 }`). | None yet → tsc + lint gate. |
| 1.3 | Reroute `AlignPanel`'s one bare-`fetch` call site through `alignSequences()` so the mock fallback applies. **Surgical**: swap the call site only; keep `apiStatus` machine + `TracePanel` + error copy intact. | **EDIT** `components/workbench/align/AlignPanel.tsx:689-700` (`requestApiAlignment`) — replace the inline `fetch(ALIGN_API_URL, …)` + `!response.ok` block with a call to the new `alignSequences()` from `lib/api`. Leave `runApiAlignment` (`:65-90`), `normalizeAlignResponse`, the JSON-upload path (`:71-72`, `readTraceJson` `:664-670`), and the browser `compareSequences` path (`:51`) untouched. The `ALIGN_API_URL` const (`:27`) becomes dead if no longer referenced — remove **only if your change orphans it** (own-mess cleanup). | **DevTools → Network → Offline**, then on `/workbench` open the **Align** tool and run an API alignment: the panel must paint the **4-channel chromatogram from `ALIGN_SAMPLE`** (not a dead error panel). Online: real `/api/v1/align` path still works. JSON-trace upload + browser paste fallback still work. |

> Why P1 before P2: it is independent of the Comparator and the rail, mirrors an existing proven idiom
> (`designPrimers` `:154-166`), and closes the one true Align gap (DESIGN §2.4) in three tiny surgical edits.

### Phase 2 — Comparator components, **UN-WIRED** (un-gated; the bulk of the work)  ❌ SUPERSEDED (Comparator dropped — see REVISION at top)

All P2 files are created but **NOT added to `TOOL_ORDER`/`PANEL_TOOLS`** — they compile and are reviewable without
any nav change. The Comparator is reachable only after P3.

| # | Unit | Files (CREATE/EDIT + anchors) | Browser-verify on `:3000` |
| --- | --- | --- | --- |
| 2.1 | **Pure mapper** `LookupResponse → ComparatorRow[]` — the testable core, no React. Define local view-model types `ComparatorRow`/`ComparatorCell` here (NOT in `backend.ts`). | **CREATE** `lib/workbench/comparator-map.ts`. Read from `report_payload`: Codon ← `locus_context.codon_strip[]` where `is_query` (`backend.ts:442-456`); REVEL/SpliceAI ← `in_silico_predictions.cards[]` by `name` (`backend.ts:459-466`), SpliceAI fallback `computational_deep_dive.spliceai_max_delta` (`backend.ts:882`); Conservation ← `computational_deep_dive.conservation[]` (`backend.ts:884`). **ClinVar/gnomAD AF: do NOT use `variant_summary_rows[].clinvar/.gnomad` — those fields do not exist on `VariantSummaryRow` (`backend.ts:57-64`).** See **Risks R1** for the corrected sources (`call_cards` / `population_frequency_detail`); render `—` if unavailable. Missing predictor → cell `value: null` (→ `—`), **never `0`**. AlphaMissense **read but not emitted** to the render list. | No consumer yet → gate is **tsc clean** + lint. (Correctness is exercised visually in 2.4.) |
| 2.2 | **PredictorBar** — pure presentational 0–1 track + threshold marker. Color keyed off `PredictorCard.verdict` (`damaging`/`tolerated`/`uncertain`, `backend.ts:463`), NOT a FE re-threshold. A11y `role="meter"` + `aria-valuemin/max/now` + `aria-label`. | **CREATE** `components/workbench/compare/PredictorBar.tsx`. Uses the `.predictor-bar` CSS from P0; tone classes `.v.warn/.ok/.err` (`workbench.css:2432-2434`). Score text beside the bar in `--mono`. | Standalone component → no direct route; verified inside 2.4. tsc + lint gate. |
| 2.3 | **ComparatorColumn** — one column header + per-row cells from one `LookupResponse`. Header: HGVS (`--mono`), spinner, inline error+retry, remove-✕. Emits `.col-last` on the final column's cells (drives the P0 CSS fix). | **CREATE** `components/workbench/compare/ComparatorColumn.tsx`. Header cell class `.col-h` (`workbench.css:2419`); row cells `.row-h` for the label column. remove-✕ `aria-label="Remove {hgvs} column"`; retry `aria-label="Retry lookup for {hgvs}"`. | Verified inside 2.4. tsc + lint gate. |
| 2.4 | **ComparatorPanel** — orchestrator: column state (`ColumnState` local type), picker (current + variant-library + paste), `Promise.allSettled` lookups, renders `.compare-grid`, all states. Column 1 = current variant (fixed, not removable); cols 2–3 from library picker / paste; max 3. | **CREATE** `components/workbench/compare/ComparatorPanel.tsx`. Props `{ gene, cdna }`. Library via `getLibrary()` (`variant-library.ts:55`) + `subscribe()` (`:120`) through `useSyncExternalStore` (same pattern as `LibrarySection`). Per column call `variantLookup({gene, cdna})` (`api.ts:38`) — it already retries once + is AbortSignal-aware; do NOT re-implement. **`Promise.allSettled`, never `Promise.all`.** Grid template `200px 1fr 1fr 1fr` (3 variants) / inline `200px 1fr 1fr` (2). Dedupe picker by `query.toLowerCase()` (`variant-library.ts:85`). Wrap grid `role="table"`. | **Temporarily** render `<ComparatorPanel>` on a scratch route or by a temporary local default to eyeball it (then revert before the gate — do NOT ship a temp route). Confirm: (a) empty state "Add a second variant…" + add-tiles; (b) add a 2nd library variant → both columns resolve, predictor bars show `role="meter"` + score; (c) force one column to reject (offline one lookup) → that column shows error+retry, the other **stays rendered** (proves allSettled); (d) remove 3rd column → grid reflows to 3-col, **no last-border artifact** (proves P0). tsc + lint gate. |

> P2 net result: the full Comparator exists, type-checks, lints, and is reviewable — but is **not in the rail**.
> Nothing on `/workbench` changes for a user until P3. This is the "buildable + reviewable without the gated rail
> change" property the brief requires.

### Phase 3 — ⚠ GATED rail wiring (durable nav change — needs Steven OK before ship)  ❌ SUPERSEDED (no 5th rail tool — see REVISION at top)

> **⚠ GATED — needs Steven OK before ship.** Adding a 5th rail tool is a durable nav change (spec §7.1, design §6).
> **Recommendation: YES, position LAST** (`Sequence · Primer · CRISPR · Align · Compare`) — Compare is a
> cross-variant view, belongs after the single-variant tools. Do NOT land P3 until Steven approves. P0–P2 ship
> without it; the Comparator simply isn't reachable yet.

| # | Unit | Files (CREATE/EDIT + anchors) | Browser-verify on `:3000` |
| --- | --- | --- | --- |
| 3.1 | Append `'compare'` to `TOOL_ORDER`. `ToolBar` maps `TOOL_ORDER` automatically (`ToolBar.tsx:11-30`) and the glyph (`ToolIcon.tsx:44-50`) + `TOOL_META.compare` (`tools.ts:41-46`) already exist — so this one line makes the rail button appear. | **EDIT** `components/workbench/tools.ts:3` → `['viewer','primer','crispr','align','compare']`. | Rail now shows **5 tools**; the Compare button renders with the two-column glyph and label "Compare". |
| 3.2 | Extend `viewerCollapsed` so Compare collapses the sequence viewer (full-width grid, not a track). | **EDIT** `components/workbench/tools.ts:50-52` → `return tool === 'align' \|\| tool === 'compare'`. | Selecting Compare collapses the viewer canvas (same behaviour as Align). |
| 3.3 | Add `'compare'` to `PANEL_TOOLS` and a `case 'compare'` to `renderToolPanel`. | **EDIT** `components/workbench/WorkbenchShell.tsx:46` → add `'compare'` to `PANEL_TOOLS`. **EDIT** `WorkbenchShell.tsx:48-64` (`renderToolPanel`) → `case 'compare': return <ComparatorPanel gene={gene} cdna={cdna} />` (import from `./compare/ComparatorPanel`). | Click **Compare** in the rail → the Comparator grid mounts with the viewer collapsed; column 1 is the current variant; add a library variant → second column resolves; all P2 states reachable from the real rail. Primer/CRISPR/Align unchanged (regression check). |

### Phase 4 — ⚠ GATED AskEamos placeholder shell (optional this cycle — recommend deferring)

> **⚠ GATED — needs Steven OK before ship.** Mounting a persistent floating pill is a durable visual element on
> every Workbench view (spec §7.2, design §6). **Recommendation: SKIP this cycle.** It adds a visible "Coming soon"
> affordance for a parked feature with no funded LLM key (memory: AskEamos parked until Steven funds the key). The
> orphaned CSS (`.ai-pill`/`.ai-panel`, `workbench.css:2437-2525`) stays dormant at zero cost. Build P4 **only if**
> Steven explicitly wants the affordance visible pre-funding. Live chat stays unwired either way.

| # | Unit | Files (CREATE/EDIT + anchors) | Browser-verify on `:3000` |
| --- | --- | --- | --- |
| 4.1 | **AskEamosPill** — disabled, tool-aware "Coming soon" pill + parked panel. **No network; imports nothing chat-related from `lib/api.ts`; never references `/api/v1/chat`.** Collapsed: `Ask Eamos · {tool}` + "Coming soon" dot. Open: parked banner (copy idiom from `aistack/AskEamos.tsx:226-229`) + **non-interactive** preview chips (`<span>`, not buttons); textarea `disabled`; send inert. | **CREATE** `components/workbench/ai/AskEamosPill.tsx`. Reuse `.ai-pill`/`.ai-panel` CSS verbatim (`workbench.css:2437-2525`) + a disabled treatment (reduced opacity, hover off). Pill is `<button aria-disabled>` `aria-label="Ask Eamos about {tool} — coming soon"`; open panel `role="dialog"`. | No consumer yet → tsc + lint gate. |
| 4.2 | Mount `<AskEamosPill tool={tool} />` **once** in `WorkbenchShell` so it persists across tool switches. | **EDIT** `components/workbench/WorkbenchShell.tsx:296-308` (shell return, inside the `wb-work-shell-wrap`/`WorkRail`) — mount once; the `tool` prop is already in scope (`:74`). | Floating "Coming soon" pill visible on `/workbench`, label tracks the active tool (switch tools → label updates), persists across switches. Click → parked panel with greyed preview chips + disabled textarea. **Network tab: zero `/api/v1/chat` calls** when clicking. |

---

## Codex dependency lane (separate — blocks nothing in P0–P4)

This lane is **not on the FE critical path**. Every FE phase ships mock-first without it. Backend is Codex-owned
(do not touch `app/backend/**`).

| # | Dep | Why it matters | FE impact |
| --- | --- | --- | --- |
| **C1 (the one that matters)** | **Implement `POST /api/v1/crispr/tide`** — route is **NOT FOUND** in `workbench.py` (design §0 backend table). FE `analyzeTide` (`api.ts:182-199`) calls it but the endpoint doesn't exist → always falls back to `CRISPR_TIDE_SAMPLE`. | Without it the Outcomes tab can never show **real** TIDE/Lindel data — only the bundled sample. This is the single Codex dep gating real comparator-adjacent outcomes. | None blocking — FE already mock-first (`catch → CRISPR_TIDE_SAMPLE`, `api.ts:197`). When C1 lands, real outcomes light up automatically. |
| C2 (optional) | Batched `POST /api/v1/compare` (2–3 variants → comparator rows in one round-trip). | v1 ships on **N parallel `variantLookup` calls** (no backend dep) — but that's N full pipeline runs. A batched endpoint is the scale win. | None — P2 works without it. A later FE `compareVariants()` swap is a drop-in. |
| C3 (deferred, gated) | Flip `use_real_apis` in the deployed env (Primer/CRISPR/Align real engines, design §5 D1). | Product-visible flip from RPE65 fixture → real per-variant output. | Deferred to Wave 3 alongside the provenance chip (spec §7.3); Codex owns the Render redeploy + live-verify (memory). Out of scope here. |

---

## Risks

- **R1 (load-bearing — ground-truth correction to the spec).** The spec's mapper table (§3.1) and §1 cite
  `variant_summary_rows[].clinvar` (`backend.ts:222`) and `.gnomad` (`backend.ts:220`). **These citations are wrong.**
  Lines 220/222 belong to `SearchInputSourceInputs` (`backend.ts:217-224`) — those are *source-tool query echoes*
  (the gnomAD/ClinVar query string used), **not** variant evidence values. `VariantSummaryRow` (`backend.ts:57-64`)
  has **no** `clinvar`/`gnomad`/`spliceai` fields (only `consequence`, `variation_type`, `protein_change`, etc.).
  → **Mapper fix:** source ClinVar verdict + gnomAD AF from the real fields — `call_cards` (`clinvar_verdict` /
  `gnomad_af`, `backend.ts:1896-1897`) and/or `population_frequency_detail` (`backend.ts:109`, AF at `:937/:973`).
  If neither is present, render `—`. **Do not** read 220/222. (This is the one place the spec would actively
  mislead an implementer; flag it in the P2.1 PR description.)
- **R2 (no test runner in `app/web`).** The spec's §5 Vitest plan targets the *Vite* app, not `app/web` (no vitest
  config here). The mapper — the correctness core — therefore has **no automated guard** in this app. Mitigation:
  gate the mapper on `tsc` + the explicit browser checks in 2.4 (row set present, `—`-not-`0`, allSettled). If
  Steven wants real mapper specs, add a vitest config to `app/web` as a separate (out-of-scope) task. (See R7.)
- **R3 (Comparator has no offline mock — spec Open Q §8.4).** Unlike Primer/CRISPR/Align, the report-style
  `variantLookup` has **no bundled sample fixture**. Offline ⇒ every non-cached column shows error+retry (column 1
  on the default RPE65 request may still paint via the viewer's own fallback, but the comparator columns won't).
  Decision needed: ship with **no comparator mock** (offline = per-column error), or add a small `LOOKUP_SAMPLE`
  fixture. Recommendation: ship without it this cycle (keeps the change surgical); the error+retry state is honest.
- **R4 (gated steps land last by design).** If Steven defers P3, the Comparator is built but unreachable — that is
  the intended safe state, not a bug. Do not "temporarily" wire it to demo it; use the P2.4 scratch-render-then-revert
  approach instead.
- **R5 (Align fixture shape drift).** `ALIGN_SAMPLE` must satisfy exactly what `normalizeAlignResponse` /
  `TracePanel` read (`AlignPanel.tsx:473-525`). A missing `trace_channels`/`q_scores` field = a blank trace, not a
  type error if the field is optional. Mitigation: build the fixture by mirroring the response the live `/api/v1/align`
  returns for the RPE65 default, and verify the chromatogram actually paints (1.3 browser-verify), not just that it
  type-checks.
- **R6 (`ALIGN_API_URL` orphan).** Rerouting 1.3 may orphan the `ALIGN_API_URL` const (`AlignPanel.tsx:27`). Remove
  it **only if** your change makes it unused (own-mess cleanup per CLAUDE.md §3); don't touch it otherwise.
- **R7 (predictor verdict union).** PredictorBar keys color off `PredictorCard.verdict`. Confirm the verdict union
  values at `backend.ts` (the `PredictorVerdict` type) match the `damaging/tolerated/uncertain` the spec assumes —
  if the union differs, map defensively (unknown verdict → neutral `--bg-soft` fill, never `--err`).

## Recommended first 3 steps

1. **P0.1 — CSS fix.** Replace `nth-child(4n)` → `.col-last` and add the `.predictor-bar` block
   (`components/workbench/workbench.css:2410`, `:2426-2434`). Zero DOM consumers today → safest possible first commit;
   unblocks P2's reflow edge. Gate: tsc + lint + `/workbench` visually unchanged.
2. **P1.1 + P1.2 — Align fixture + `alignSequences()`.** Create `lib/workbench/align-sample.ts` and add the
   mock-first `alignSequences()` to `lib/api.ts` after `:166`. Self-contained, mirrors `designPrimers`. Gate: tsc + lint
   (no consumer yet).
3. **P2.1 — pure mapper `comparator-map.ts`** with the **R1 correction baked in** (ClinVar/gnomAD from `call_cards` /
   `population_frequency_detail`, never `backend.ts:220/222`). It is the correctness core, has no UI dependency, and
   every later component renders off it. Gate: tsc clean + lint.

(P1.3 then wires Align end-to-end with the offline chromatogram browser-verify; P2.2–2.4 build the UI on the mapper.)
