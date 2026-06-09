# Control-cleanup — execution-ready build plan

> Code-verified against `app/web` on 2026-06-10 (subagent). The spec
> `docs/workbench-control-cleanup/spec.md` is sound but line numbers + several
> CSS/architecture anchors drifted; **build to the anchors here.** Order:
> A-items (cheap, non-conflict) → B (legends) → C-b → **D last** (single-base edit,
> touches SequenceViewerV2 — sequence after any viewer work is committed).
> Conventions: `--cls-*` only via classification; tokens not hex; `.eamos-mock` for
> mock; gene-viewer bases stay uniform `--ink` mono (NOT coloured), AA pills coloured.

## A1 — Cas-enzyme `<select>` → static "SpCas9 · NGG" chip
`crispr/DesignTab.tsx`: replace the Cas `<label>`+`<select>` (**233-252**) with a
read-only `<span className="crispr-enzyme-chip">SpCas9 · NGG</span>`; trim
`CAS_OPTIONS` (**22-48**) to the single SpCas9 entry; delete `unavailableCas` (**160**)
+ its map (**324-328**). Keep `cas` state/payload/`casPam`/summary cell untouched
(request shape unchanged). Add `.crispr-enzyme-chip` CSS near `.crispr-result-note`
(**2637**), teal-tint or neutral tokens. Verify: no `<select>` for Cas; static chip;
guides still design; the two "(unavailable)" caveats gone.

## A2 — Drop the faux "Target window: server-resolved" input
`DesignTab.tsx`: delete the disabled input block (**289-298**); append to the post-CTA
help-note (**446-449**) "The design window is resolved on the server from the selected
gene / cDNA." No state to remove.

## A3 — De-dup the two mismatch controls (relabel only)
`crispr/OffTargetTab.tsx`: search field (**355-369**) label → `Search ≤ {maxMismatches} mm`
+ title "Genome search radius — max mismatches the search returns." Curate field
(**537-549**) label → `Show ≤ {filterMm} mm` + title "Display filter — hides returned
off-targets above this many mismatches (no re-run)." Empty-state (**646-651**) →
"No off-targets shown at ≤ {filterMm} mm". No behaviour change.

## A4 — Outcomes self-disclaimers → one "Preview" brand
`crispr/OutcomesTab.tsx`: the gate **already exists** — `outcomeInfo.sourceBacked`
(`crispr-disclosure.ts`). Replace the three stacked `help-note`s (**113-126**) with one,
gated on `!outcomeInfo.sourceBacked`; add a `<span className="crispr-preview-tag eamos-mock">Preview</span>`
pill near the top. Keep per-result honest lines (**157-158**). CSS reuse
`.crispr-result-note` (**2628**) or a `--warn-*` `.crispr-preview-tag`.

## A5 — Outcomes styled file-picker (mirror Align)
`crispr/OutcomesTab.tsx`: replace the two raw `<input type="file" className="field-input crispr-file">`
(**54-66**, **67-79**) with the Align idiom `<label className="align-read-btn align-file-btn">{file?'Replace file':'Choose file'}<input type="file" accept=".ab1,.json" hidden …/></label>`
(pattern at `AlignPanel.tsx:168-174`). Filename echo already in `tool-panel-sub`
(**107-110**). `.crispr-file` (**2882**) becomes orphaned — remove it.

## B1 — Protein view ACMG legend + point-feature key  ⚠ Steven deprioritised the viewer
`viewer/ProteinView.tsx`: add a `.sv-pv-key` (ACMG dots) for the classes present
(`new Set(lollipops.map(p=>p.cls))`, order `['p','lp','vus','lb','b']`) + a feature key
(active-site / palmitoyl / queried diamonds), above the "uniform size" note (**280-294**).
CSS near `.sv-pv-legend` (**3368**): `.sv-pv-key-swatch.{p,lp,vus,lb,b}` → `var(--cls-*-dot)`
(mirror `.sv-pv-headdot` **3286-3290**); `.sv-pv-key-diamond.{active,palmitoyl,query}`.
**NOTE:** this fixes the no-legend finding from the viewer sweep, but Steven said the
gene/protein viewer will be reworked when the backend lands — confirm before investing.

## B2 — Conservation PhyloP scale chip
`viewer/CodonDetail.tsx`: conservation renders **per wrapped row** (`conservation()`
**548-560**, emitted at `row('conservation',30,…)` **667**) — a single left-edge chip
isn't free. Prepend a `<span className="sv-cons-scale">PhyloP low→high</span>` as the
row's first child. CSS `.sv-cons-scale` near `.sv-cons-bar` (**878**), `--paper` backing.
(Same viewer-rework caveat as B1.)

## C-b — FullLocus "Full gene" honest relabel
`CanvasHeader.tsx`: `VIEWER_MODES` (**29-38**) `locus` entry → label "Full gene ·
overview", title "Whole genomic locus — read-only overview; base colour, selection,
editing live in Window view." Optional caption in `FullLocusViewer.tsx` after
`<LocusHeader/>` (**202**). (C-a base-colour/selection deferred per spec.)

## D — Visible single-base Edit affordance  (STRUCTURAL; do LAST — touches SequenceViewerV2)
**Ground-truth fix: the handle `SequenceViewerHandle` is in `SequenceViewerV2.tsx:48-58`,
NOT `viewer-types.ts` (spec is wrong). Parent is `WorkbenchShell.tsx` (ref `:153`,
side-panel wiring `:205-222`).**
- **D.1 `SequenceViewerV2.tsx`:** add `editSelection()` useCallback near `clearSelection`
  (**~276**) — derive `idx` from single-base `selection`, find the anchor via the
  `rootRef.querySelector('.sv-base[data-idx="${idx}"]')` pattern (mirror `scrollToIdx`
  **321-328**), read `getBoundingClientRect()`, call existing `setPopover({idx,x,y})`
  (state **125-127**) → reuses `EditPopoverV2` verbatim. Add `editSelection` to the
  handle interface (**48-58**) + `useImperativeHandle` (**361-379**).
- **D.2 `SidePanel.tsx`:** add `onEdit` to `SelectionBlock` (**108-118**) + a
  `<button className="scratch-sel-btn"><IconRename size={13}/> Edit base</button>` in
  `scratch-sel-actions` (**143-147**); thread `onEdit` through `ScratchpadSection`
  (**245-263**, render **323-330**) + `SidePanelProps` (**26-41**) + `ViewerSide`
  (**399-435**), mirroring `onDelSelection`. Soften the hint (**139-142**). `IconRename`
  already imported (`SidePanel.tsx:8`).
- **D.3 `WorkbenchShell.tsx`:** add `onEdit={()=>viewerRef.current?.editSelection()}` to
  `<SidePanel>` (**205-222**), mirroring `onDelSelection` (**219**).
- Verify: left-click a base → "Edit base" pencil button → opens EditPopoverV2; right-click
  + A/T/C/G/⌫ still work; no duplicate editor.

## Conflict notes
Primer/canvas work is committed (HEAD ≥ `93e9d45`); `SequenceViewerV2` now also has the
primer-overlay banner (sequence section) + the `selectedPrimer` prop — D.1's edits
(handle interface, a new useCallback, the imperative-handle object) don't touch that
render layer, but re-read 48-58 / 361-379 before editing. `tools.ts` untouched by cleanup.
