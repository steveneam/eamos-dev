# Workbench chrome + sequence-viewer canvas — design audit

Scout lane: the Workbench **shell/chrome** (nav, ContextStrip, ToolBar tool-switcher, CanvasHeader, SidePanel rail) and the **sequence-viewer canvas** (`viewer/*`). The tool *panels* (Primer/CRISPR/Align) are another scout's lane — flagged here only at the chrome↔panel seam.

Grounding: `DESIGN.md`, `app/web/app/globals.css`, `app/web/components/workbench/workbench.css` (read in full, 4025 lines), `app/web/lib/classification.ts`, `app/web/components/layout/work-rail.css` (canonical `.wr-section-*` grammar), `app/web/components/icons/Icon.tsx` (the 1.75 family), `app/web/components/workbench/ToolIcon.tsx`.

Skills run: **frontend-design** (lens applied) + **ui-ux-pro-max** targeted searches — `--domain ux` (focus-states High; "Z-Index Management" High → *define a 10/20/30/50 scale, never arbitrary*; "Stacking Context"; sticky-nav-overlap; empty/error states), `--domain style` (Data-Dense Dashboard: sticky headers, 12px, minimal padding; Dimensional Layering: 4-level z-scale), `--domain chart` (per-base/conservation: provide non-colour cue + a11y fallback). Cited inline below.

---

## 1. Snapshot

The Workbench is a 1440px clinical sequence IDE: shared nav → slim ContextStrip (gene·variant on the left, a segmented tool-switcher on the right) → a `WorkRail` controls-left / canvas-right split. The canvas stacks three foldable windows (Gene minimap → Protein view → Sequence detail) plus a Benchling-style click/drag/edit surface; the left rail carries the Scratchpad + evidence sections. The posture is genuinely strong — hairline-driven, tokenised motion/elevation, real keyboard + selection model, honest mock markers. The drift is **legacy inline SVGs (stroke-weight 2, not the 1.75 family)**, a **hardcoded ClinVar/lollipop colour ramp that bypasses `lib/classification.ts` AND violates the mandated ACMG ramp**, the **viewer `SectionHeader` not adopting the shared airy icon-led grammar**, and an **ad-hoc z-index stack** that collides the rail FAB with the AI pill.

---

## 2. Findings

### P0 — broken / invariant / a11y

**[P0] ClinVar + lollipop + scratch-cv colour ramp bypasses `lib/classification.ts` and breaks the ACMG ramp** · `workbench.css:740-744`, `1758-1762`, `3753-3757`
Three component ramps hardcode `.p #B82B2B / .lp #BA7517 / .vus #94a3b8 / .lb #6FA88F / .b #1D9E75`. This violates two invariants at once: (1) classification colour must route through `resolveClassificationConfig` / the `--cls-*` tokens (CLAUDE.md + `classification.ts` is "the SINGLE source"); (2) Steven's 2026-05-26 ACMG-ramp mandate (P→red, **LP→orange**, **VUS→true yellow**, **LB→lime**, B→green). The workbench instead paints **LP amber, VUS grey, LB sage** — grey is *reserved for NA/conflict* and must never be a tier, so VUS currently reads as "no data." Fix: replace each with the dot tokens — `.p→var(--cls-path-dot)`, `.lp→var(--cls-lpath-dot)`, `.vus→var(--cls-vus-dot)`, `.lb→var(--cls-lben-dot)`, `.b→var(--cls-ben-dot)`. Why: a VUS lollipop rendering grey is a clinical-meaning bug, not just a token drift. (3 surfaces × 5 = 15 lines.) **Token-only, but it changes verdict colour on a persistent surface → see §3.**

**[P0] Viewer `SectionHeader` ignores the shared airy icon-led grammar** · `SequenceViewerV2.tsx:741-777` (+ CSS `.sv-section-head` `workbench.css:552-584`)
The brief states the WorkRail grammar is "leading MONOCHROME glyph, uppercase Inter label, quiet far-right chevron." The rail's `.side-section-head` was already rebuilt to mirror `.wr-section-head` byte-for-byte (`workbench.css:1428-1484`) — but the *canvas* `SectionHeader` (Gene minimap / Protein view / Sequence) still has **no leading glyph**, puts the **chevron on the left**, hardcodes an inline `strokeWidth={2.4}` SVG instead of `<IconChevron>`, and uses `font-family: var(--mono)` for the label where the rail uses `var(--body)`. Result: the canvas and the rail (sitting side-by-side) read as two different systems. Fix: give each canvas window a leading `<Icon*>` (IconGene / IconProtein / IconList or IconWindow), move the chevron to the far right, swap the inline SVG for `<IconChevron size={12}>`, and align label face to Inter — i.e. make `.sv-section-head` track `.wr-section-head`. Why: the rail↔canvas seam is the single most visible consistency break on the surface. **Structural (changes a persistent header) → §3.**

**[P0] Viewer collapse-state has no `prefers-reduced-motion`-safe + non-colour-only cue parity, but more urgently: tracks dropdown + collapse toggles drop the 1.75 icon family** · `CanvasHeader.tsx:142-146, 186-190`, `ViewerToolbar.tsx:53-56, 120-136`, `SidePanel.tsx:91-93, 507-509, 746-748`, `SequenceViewerV2.tsx:767-769`
At least **8 inline SVGs** in my lane are hand-rolled at `strokeWidth={2}` (search lens, undo, redo, tracks hamburger, export tray, side-collapse chevron) — the exact anti-pattern `Icon.tsx`'s own header comment calls out ("was violating that with 7 ad-hoc glyphs… stepped 2 → 1.75 because these render smaller"). The family already ships `IconExport`, `IconChevron`, plus search/undo could move to it. Mixed 2.0/2.4/1.75 weights at 12-15px is visible. Fix: route every chrome glyph in my lane through `@/components/icons/Icon` (add an `IconSearch`/`IconUndo`/`IconRedo`/`IconTracks` if missing). Why: ui-ux-pro-max "Stroke Consistency" + "Consistent Icon Sizing" — mixing stroke weights at the same hierarchy level reduces perceived polish.

**[P0] Tool-switcher (ToolBar) icons are 24px-viewBox at strokeWidth 2 — heaviest icons on the surface** · `ToolIcon.tsx:4-11`
`ToolIcon` uses `strokeWidth: 2`. Its sibling `Icon.tsx` explicitly documents stepping to 1.75 ("icons whisper, text speaks") and these tool glyphs render at 15px (`.toolbar-seg-btn svg`). The active tool also turns its icon **teal** (`workbench.css:3061`), while the brief's rail grammar says leading glyphs are "MONOCHROME … never teal." The switcher is a tool-pill register (not a rail section), so teal-on-active is arguably acceptable *here* — but the **stroke weight should be 1.75** to match every other glyph. Fix: change `ToolIcon`'s `svgProps.strokeWidth` to `1.75`. Why: consistency with the one-pen family. (Teal-on-active = §3 judgement call.)

**[P0] `EditPopoverV2` consequence chips use raw hex off-palette** · `workbench.css:1115` (`.sv-pop-conseq .cs.stop { background:#1a1a1a }`), `1117` (`.cs.splice {background:#e8eaf2;color:#3b4877}`)
`#1a1a1a` is pure-ish black (DESIGN.md: "No pure black — use `--ink`"). The splice indigo `#e8eaf2/#3b4877` is an undocumented colour (repeated at `scratch-row .conseq.splice:1662`, `sv-feat-bar.oligo:694`, `align seq-hl-silent:1990`, `ic-bar.predicted:3420`). Fix: `stop` → `background: var(--ink); color: var(--bg)`. For splice indigo, promote to one token (e.g. `--splice-bg/--splice-ink`) and consume everywhere — it's a real recurring semantic ("silent / oligo / predicted / splice"), so a named token is justified. Why: "No colours outside the palette."

### P1 — inconsistency / hierarchy

**[P1] Two different zoom controls + a stale `.zoom-pill` ghost** · `workbench.css:154-177` (`.zoom-pill`, mono labels Gene/Exon/Codon), `3063-3089` (`.sv-zoombar`/`.zoom-slider`), `ZoomSlider.tsx`
The shipped control is the hover-revealed density slider (`ZoomSlider`), and its own comment says the "semantic Gene/Exon/Codon presets … were retired." But `.zoom-pill` CSS (the retired preset pill) is still in the stylesheet, dead. Fix: delete the orphaned `.zoom-pill` rules (`154-177`). Why: dead CSS that re-asserts a retired pattern invites accidental reuse — `Icon.tsx`/CLAUDE.md "mention don't delete pre-existing dead code" applies, so **flag, don't auto-delete** unless told. (Listed P1 because it's misleading, not breaking.)

**[P1] Zoom slider is hover-only-revealed → poor discoverability + touch-hostile** · `workbench.css:194-209` (`.sv-zoom-overlay-seq` opacity 0 until `:hover`), `ZoomSlider.tsx`
The only density control fades in on `.sv-sequence-wrap:hover`. ui-ux-pro-max `hover-vs-tap` (Critical): "don't rely on hover alone for primary interactions"; touch users get no zoom at all. Note the Align chromatogram already solved this exact problem — `.chromatogram-toggle` is a *persistent* handle "always visible so the trace-scale controls are discoverable on touch and don't rely on hover" (`workbench.css:2786`). The viewer should mirror that. Fix: a persistent small zoom handle (top-right of the Sequence window) that toggles the slider, matching `.chromatogram-toggle`. **Persistent-element change → §3.**

**[P1] Ad-hoc z-index stack — no scale, and the rail FAB sits at the same layer as nav while the AI pill floats above both unpredictably** · nav `.nav-wrap:50` (`workbench.css:27`) · `.side` sticky (no z) · `.sv-dropdown-menu:30` (247) · `.sv-cv:5` (728) / `.sv-cv.active:6` · `.sv-edit-pop:50` (1029) · `.ai-pill:100` (2882) · `.ai-panel:99` (2909) · `.sv-export-backdrop:200` (1131) · WorkRail `.work-rail` inline:45 / drawer:60 / scrim:55 / **FAB:50** (`work-rail.css`)
The rail drawer FAB is `z-50` — identical to the sticky `.nav-wrap` (`z-50`) — and the edit popover is also `z-50` (`.sv-edit-pop`). ui-ux-pro-max flags this twice: "Z-Index Management" (High — *define a scale 10/20/30/50, don't use arbitrary values*) and "Stacking Context" (sticky parents reset z). The values are scattered 5/6/30/45/50/55/60/99/100/200 with collisions. Fix: define a workbench z-scale in tokens (e.g. `--z-track:5 / --z-rail:45 / --z-nav:50 / --z-drawer:60 / --z-popover:70 / --z-pill:100 / --z-modal:200`) and consume it; the FAB must sit below nav, the edit popover above the rail. Why: today a popover opened near the nav, or the FAB under the nav, can mis-stack. **Token + structural → §3.**

**[P1] CanvasHeader renders nothing for Align, leaving the canvas-head row absent with no transition** · `CanvasHeader.tsx:87-88` (`if (!hasControls) return null`)
For Align the header returns `null` and the viewer is `viewer-collapsed`, so the canvas region collapses to just the tool panel with no header affordance — fine functionally, but the 14px `margin-bottom` and flush-right alignment of `.canvas-head` mean switching viewer→align produces a small layout jump. Minor. Fix: keep a zero-height placeholder or animate the collapse via the existing `--dur-2`. **Layout behaviour → §3 (low priority).**

**[P1] Viewer loading + error share one centered mono string; error has no recovery path** · `WorkbenchShell.tsx:279-283` (`<div className="viewer-loading" role={viewerError?'alert':'status'}>{viewerError ?? 'Loading sequence...'}`)
ui-ux-pro-max "Error Recovery" (Medium) + "Empty States" (Medium): an error should offer a next step. `Sequence unavailable for {gene} {cdna}` is a dead end — no retry, no "back to RPE65". The FullLocus path *does* this right (`FullLocusUnsupportedBanner` has a "Back to Window view" button). Also: a bare text "Loading…" for a >1s op should be a skeleton (ui-ux-pro-max `progressive-loading`). Fix: give the error state a retry button + a "load the sample (RPE65 c.260A>G)" fallback link; consider a skeleton for the load. Why: parity with the locus path + recoverability. **Copy/structural → §3.**

**[P1] `.viewer` transition animates `max-height`/`padding` (layout), against DESIGN.md** · `workbench.css:187` (`transition: max-height .25s ease, padding .25s ease, opacity .25s`)
DESIGN.md: "Animate transform, opacity, box-shadow, and colour only. Avoid animating layout (width/top/margin)." The viewer collapse animates `max-height` + `padding` with a raw `.25s ease` (also off the `--dur-*`/`--ease-*` tokens). Fix: at minimum move to `--dur-2 var(--ease-standard)`; ideally collapse via opacity + a grid-rows technique like `.primer-l3-wrap` already does (`workbench.css:3637`). Why: token + perf consistency. (Sanctioned size-transition exists, but this one isn't using it.)

**[P1] `.sv-detail` drag-select disables `user-select` site-wide; right-click-to-edit is the only edit entry → discoverability gap** · `workbench.css:592-604`, `SequenceViewerV2.tsx:492-494`, `SidePanel.tsx:142-144`
Editing a single base requires a *right-click* (context menu). The only hint lives in the Scratchpad selection card ("Right-click this base… press A/T/C/G"). A first-time user left-clicking a base just selects it with no visible "edit" affordance. ui-ux-pro-max discoverability/`gesture-alternative`: "always provide visible controls for critical actions." Fix: a small "Edit" affordance on a 1-base selection (e.g. a pencil button in the selection card already styled via `IconRename`), or a hover hint on the base. **Interaction/structural → §3.**

**[P1] Tool-switcher is icon+label but has no roving-tabindex / arrow-key nav; `aria-pressed` is right but it's a `role="group"` of buttons not a tablist** · `ToolBar.tsx:13-27`
It correctly uses `aria-pressed` + `title`. But four tool buttons that swap the whole canvas are conceptually tabs; today Tab stops on each, and there's no left/right arrow traversal. Minor a11y polish. Fix: either keep buttons (fine) but consider `role="tablist"`+arrow keys if these are treated as tabs. Low priority — current is acceptable.

### P2 — polish

**[P2] `--bg-soft2` referenced with a fallback that hides a missing token** · `workbench.css:570` (`background: var(--bg-soft2, var(--bg-soft))`), `1621`
`--bg-soft2` *is* defined in globals.css (`:18`), so the `, var(--bg-soft)` fallback is dead defensiveness and signals uncertainty about the token. Drop the fallback (`background: var(--bg-soft2)`). Cosmetic.

**[P2] `.sv-minimap` exon segments use raw hex (`#e6dfca / #c9bf99`) and `.sv-feat-bar.exon` uses `#f0ece2/#d8d0bb/#6b5a2a`** · `workbench.css:469-499`, `681-695`
The exon "cream" + domain "mauve" + oligo "indigo" feature bars are all raw hex, off-token. These are a coherent set (annotation-track palette) but undocumented. Fix: promote to a small named set (`--track-exon-*`, `--track-domain-*`, `--track-oligo-*`) so the canvas annotation palette is tokenised like `--base-*`/`--aa-*` already are. Why: DESIGN.md "Tokens, not magic numbers." (Volume makes this P2 not P0 — they're decorative track fills, not classification.)

**[P2] Numeric metrics in the side panel lack `tabular-nums`** · `SidePanel.tsx` Kv rows (e.g. `:441-456`), CSS `.kv-row .v` (`workbench.css:1796`)
The brief: scores/coords are mono — they are (`.kv-row .v {font-family:var(--mono)}`). But mono ≠ tabular figures unless `font-variant-numeric: tabular-nums` is set; the Align metrics already do this (`.align-metric b:2202`). Coords like `68,444,869` and counts in the kv-list/exon table would align cleaner with `tabular-nums`. Fix: add `font-variant-numeric: tabular-nums` to `.kv-row .v`, `.sv-vnav-count`, `.side-exon-row .ex-*`, `.v-stat .value` parity. Cheap polish.

**[P2] `.sv-section-head` hover uses raw `.15s`, off the motion tokens** · `workbench.css:567` (`transition: background .15s, color .15s`)
Several viewer transitions use raw `.15s`/`.12s`/`.2s ease` instead of `--dur-1`/`--ease-standard` (`.sv-base:763`, `.sv-cv:726`, `.sv-section-chev:576`, `.toolbar-seg-btn:3052`, `.sv-dropdown-btn:235`). The global reduced-motion guard still catches them, but they bypass the duration scale. Fix: swap raw durations for `--dur-1`/`--dur-2` + easings. Low-risk sweep.

**[P2] `.ai-panel-head` uses a decorative `linear-gradient`** · `workbench.css:2926` (`background: linear-gradient(180deg, var(--teal-tint), transparent)`)
DESIGN.md: "No decorative gradients (a gradient may only ever be a ≤4%-contrast functional surface wash)." teal-tint→transparent is a soft wash and borderline acceptable, but it's the only colour-gradient in the chrome. Note: AI pill/panel are parked (memory: AskEamos parked) — low priority, but flag for when it un-parks. Fix: flat `var(--teal-tint)` header band or drop.

**[P2] ContextStrip gene name is Spectral 600 at 18px — serif on a dense identity row** · `workbench.css:72-78` (`.ctx-gene {font-family:var(--display); font-weight:600}`)
DESIGN.md allows the gene name in display serif (it's a "gene name / running head" role), so this is *compliant*. But the brief's recent invariant is "variant identity (HGVS/protein) is Inter + tabular-nums." The `.ctx-var` beside it is correctly mono (`:79-84`). The serif gene + mono variant on one baseline row is intentional per spec — calling out only to confirm it's *not* a violation (the HGVS `c.260A>G` is mono, which is the coordinate register, correct). No change. (Documented so the next sweep doesn't "fix" it.)

**[P2] `.sv-cv` hover scales the dot (transform) but `.sv-base:hover` only changes background — inconsistent hover language between clickable canvas elements** · `workbench.css:737` vs `766`
Both are clickable; the ClinVar dot lifts/scales, the base just tints. Acceptable (different element scales) but the ClinVar dot's `scale(1.4)` with no `--dur` token reads slightly springy vs the rest. Minor — align to `--dur-1`.

---

## 3. 🟡 FLAGGED — needs Steven's OK before I implement

Durable / structural / persistent-element / verdict-colour changes — gated on explicit approval ([[feedback_subagent_recommendations_not_authorization]]):

1. **Route the ClinVar/lollipop/scratch-cv ramp through `--cls-*` (P0).** Token-only edit, but it **changes the rendered verdict colour** on three persistent surfaces (LP amber→orange, VUS grey→yellow, LB sage→lime). It's a correctness fix and I'm confident it's right per the 2026-05-26 mandate — but recolouring a clinical verdict is exactly the kind of durable visual change that should get a yes first.
2. **Adopt the airy icon-led grammar on the canvas `SectionHeader` (P0).** Adds a leading glyph, moves the chevron right, changes the label face mono→Inter — a persistent header redesign on the canvas. High-value (closes the rail↔canvas seam) but structural.
3. **Define + adopt a workbench z-index scale (P1).** Touches stacking on nav / rail / FAB / popovers — a persistent-chrome change; the FAB-under-nav fix in particular alters layering behaviour.
4. **Make the zoom control persistent instead of hover-revealed (P1).** Adds a persistent handle to the Sequence window (mirrors `.chromatogram-toggle`). Persistent-element change.
5. **Error-state recovery affordance + skeleton loading (P1).** Adds a retry/back-to-sample button + skeleton — new persistent UI in the canvas.
6. **Single-base "Edit" affordance (P1).** New interaction entry point on the canvas (today edit = right-click only).
7. **Tool-switcher active-icon teal vs monochrome (P0 sub-point).** Whether the active tool icon stays teal or goes monochrome is a deliberate call on persistent chrome.

---

## 4. Quick wins — safe, token-only, ship immediately

These trace directly to a token/value with no structural or verdict-colour change:

- **`.sv-pop-conseq .cs.stop` `#1a1a1a` → `var(--ink)` + `color:var(--bg)`** (P0) — `workbench.css:1115`. Kills pure-black.
- **`ToolIcon` `strokeWidth: 2 → 1.75`** (P0) — `ToolIcon.tsx:8`. Joins the one-pen family. (Keep teal-active per §3 unless told.)
- **Swap the 8 inline chrome SVGs for the `Icon.tsx` family** where a glyph already exists (`IconChevron`, `IconExport`) (P0) — `CanvasHeader.tsx:186`, `ViewerToolbar.tsx`, `SidePanel.tsx:746`, `SequenceViewerV2.tsx:767`. Pure swap, same shapes at 1.75.
- **Add `font-variant-numeric: tabular-nums`** to `.kv-row .v`, `.sv-vnav-count`, `.sv-hist-count`, `.side-exon-row .ex-*` (P2) — aligns columns.
- **Drop the dead `var(--bg-soft, …)`/`var(--bg-soft2, …)` fallbacks** (P2) — `workbench.css:570, 1621`.
- **Swap raw `.15s/.12s/.2s` transitions for `--dur-1`/`--dur-2` + easings** in `.sv-section-head`, `.sv-base`, `.sv-cv`, `.toolbar-seg-btn`, `.sv-dropdown-btn` (P2).
- **`.viewer` transition → `--dur-2 var(--ease-standard)`** (P1, the duration half is safe; the layout-property fix is §3).
- **Flatten `.ai-panel-head` gradient to `var(--teal-tint)`** (P2) — only if touching the parked AI pill.
- **Promote the splice-indigo `#e8eaf2/#3b4877` + annotation-track creams to named tokens** (P0/P2) — net-new tokens, but they de-duplicate 5+ raw-hex callsites; safe because values don't change, only their name. (If "no new tokens without approval" is strict, hold for §3.)

---

### Notes for adjacent scouts
- **Chrome↔panel seam:** the tool *panels* reuse chrome classes (`.tool-panel-head`, `.field`, `.btn-teal`, `.seg`) — those are the panel scout's, but note the **panel buttons** (`.btn-primary/.btn-teal/.btn-ghost`, `workbench.css:1859`) use raw `.15s all` transitions and `.btn-primary` is `--ink-2` navy while the active tool-pill is teal: a primary-action-colour question that spans both lanes.
- The **base palette `--base-A/T/C/G`** is correctly tokenised and reused everywhere (viewer, Align trace, chromatogram, CRISPR 20-mer) — that's the model the classification ramp should follow.
