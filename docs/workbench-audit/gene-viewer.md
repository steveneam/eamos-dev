# Gene-viewer window — design audit (`/workbench`)

> **2026-07-15 retirement note:** `GeneMinimap.tsx` and `ProteinView.tsx` had no
> runtime importer and were removed in the verified frontend-retirement slice.
> Their inventories below are historical evidence, not current implementation
> instructions. Re-audit the live `SequenceViewerV2` / `FullLocusViewer` path
> before applying any related recommendation.

> **Status:** 🟡 AUDIT — review-gated. No `app/web/**` code lands until Steven OKs
> the recommendations in §5 ([[feedback_subagent_recommendations_not_authorization]]).
> Lane 1 of the 2026-06-09 4-scout workbench audit (frontend-design + ui-ux-pro-max).
> Persisted by the main agent (scout direct-write is harness-blocked).

Scope: the sequence/gene viewer and **every** control inside it — `SequenceViewerV2` (`viewer/`), `CanvasHeader`, `ViewerToolbar`, `ZoomSlider`, `CodonDetail` (the base grid), `GeneMinimap`, `ProteinView`, `FullLocusViewer`, and the selection/edit affordances. Grounded in `app/web/components/workbench/**`, `app/web/app/globals.css` tokens, and `DESIGN.md`. Skills run: **ui-ux-pro-max** `--domain ux` (hover-vs-tap Critical, visual-hierarchy, content-priority, table-handling), `--domain style` (typography/contrast, icon stroke/size discipline), `--domain chart` (legend-visible, color-not-only, pattern-texture, axis-readability) + **frontend-design** lens.

> **Stale-prior-work corrections (verified against source).** Three P0s in `docs/workbench-report-sweep/workbench-chrome.md` are already **fixed** in current code and should be struck from that doc: (1) the ClinVar ramp now uses `--cls-*` tokens (`workbench.css:756-760`, with a comment recording the fix); (2) the protein lollipop `headdot` likewise (`workbench.css:3772-3776`); (3) the canvas `SectionHeader` **has** adopted the airy icon-led grammar — leading `<IconGene/IconProtein/IconList>`, far-right `<IconChevron>`, Inter label (`SequenceViewerV2.tsx:637-672, 746-787` + `.sv-section-head` `workbench.css:555-597`). The `--z-popover` token is also live (`globals.css:195`, consumed at `workbench.css:249, 1046`). Build on these — don't re-flag them.

---

## 1. Snapshot

The viewer is a stacked, three-window clinical sequence canvas inside the center column: **Gene minimap** (whole-transcript proportional band) → **Protein view** (backbone + domains + ClinVar lollipops) → **Sequence** (the Benchling-style wrapped base grid with per-base tracks: annotations, domain, ClinVar pins, translation, ruler, bases, conservation, restriction). Above it sits a `ViewerToolbar` (find/jump, ClinVar stepper, undo/redo/history); the view controls (Tracks/strand/allele/Window·Full-gene/Export) live in the flush-right `CanvasHeader`. The posture is genuinely sophisticated — real selection+edit model, honest per-base positioning, tokenised colour.

**The three biggest gaps vs the Benchling / Apple bar:**

1. **The thing the user most needs to see is the least visible.** The queried-variant marker (`sv-marker-thin`) is a **0.5px `--warn` hairline that renders in only one wrapped row** (`CodonDetail.tsx:529-535`; `.sv-marker-thin` `workbench.css:926-933`) — directly contradicting DESIGN.md's own invariant "a vertical pin runs through **all** tracks at the queried position" (line 586). On a 14px-dense grid this near-invisible line is the single worst legibility miss. Benchling makes the active feature/selection unmissable; here it's a whisper.
2. **Base grid reads small and flat vs Benchling.** Bases are **13px** (`.sv-base` `workbench.css:775`) at a default `baseW=14px` (`ZOOM_PRESETS.exon`, `WorkbenchShell.tsx:75`), and the only density control is **hidden until you hover the sequence** (`.sv-zoom-overlay-seq` opacity 0 → 1 on `:hover`, `workbench.css:194-209`). Benchling defaults bases larger (~15-16px) with an always-visible zoom. ui-ux-pro-max `hover-vs-tap` (**Critical**): "don't rely on hover alone for primary interactions" — touch + first-time users never discover zoom. The ruler ticks (`9.5px --ink-4`) and AA numbers (`8.5px --ink-4`) sit below the AA-legibility floor.
3. **No persistent coordinate anchor when scrolling.** The grid scrolls inside a `max-height:62vh` box (`.sv-detail` `workbench.css:614-616`) with **no sticky ruler or column header** — scroll down and you lose all sense of where c.X is. Each wrapped row carries its own right-edge `c.NNN` (`sv-block-pos`), but there's no top-anchored "you are here." Benchling keeps the position axis pinned. ui-ux-pro-max Data-Dense guidance: sticky headers on scrollable dense grids.

---

## 2. Interactable inventory + verdict table

Every control in the gene-viewer lane. Verdict ∈ KEEP / IMPROVE / REMOVE.

### ViewerToolbar (`ViewerToolbar.tsx`)

| Element | file:line | Purpose | Verdict | What to do |
|---|---|---|---|---|
| Find / jump input | `ViewerToolbar.tsx:54-71` | Jump to c./p./exon/ATCG; parser at `SequenceViewerV2.tsx:391-415` | **KEEP** | Strong. Placeholder is a great affordance. Add a tiny `⌘F` hint chip at the right end (the binding exists, `SequenceViewerV2.tsx:556-559`, but is invisible) — discoverability per ui-ux-pro-max `keyboard-shortcuts`. |
| Clear-search (✕) | `ViewerToolbar.tsx:72-76` | Clears query | **KEEP** | Correct (uses `<IconRemove>`). |
| ClinVar ◢ prev / ◣ next | `ViewerToolbar.tsx:86-106` | Step through in-window ClinVar variants | **IMPROVE** | The count pill between the chevrons reads as a static number, not "N variants you can step." Label it `‹ 1/12 ›` style (current index / total) once a dot is focused — turns a count into a position. Add `tabular-nums` to `.sv-vnav-count` (`workbench.css:369`). |
| Undo / Redo | `ViewerToolbar.tsx:110-129` | Edit history | **KEEP** | Good — already on the 1.75 `<IconUndo>/<IconRedo>` family. |
| "N edits ▾" history toggle | `ViewerToolbar.tsx:132-140` | Opens `HistoryTimeline` | **KEEP** | Fine. |
| Reset | `ViewerToolbar.tsx:141-143` | Clears all edits | **KEEP** | Destructive — give it `--err` text on hover + a one-step confirm (ui-ux-pro-max `confirmation-dialogs`); today one click nukes all edits silently. |
| "No edits" idle text | `ViewerToolbar.tsx:146` | Empty state | **KEEP** | Fine. |

### CanvasHeader view controls (`CanvasHeader.tsx`)

| Element | file:line | Purpose | Verdict | What to do |
|---|---|---|---|---|
| Window / Full-gene pill | `CanvasHeader.tsx:94-112` | Switch CDS-window ↔ full locus | **KEEP** | Good. But "Full gene" drops into a far less legible viewer (see §3 FullLocus) — the toggle promises parity it doesn't deliver. |
| Reference / Variant pill | `CanvasHeader.tsx:113-131` | Sequence basis (ref vs SNV-applied) | **IMPROVE** | High-value but **mono pill text at 11.5px in the far-right cluster** is easy to miss, and "Reference/Variant" doesn't say *what changes*. Consider a clearer active-state (the queried base/codon visibly flips) + a one-line helper. This is a genuinely powerful feature buried in chrome. |
| Tracks ▾ dropdown + count | `CanvasHeader.tsx:134-161` | Toggle 5 tracks | **IMPROVE** | Keep, but the count badge (`{trackCount}`) shows e.g. "3" with no sense of *of 5*. Show `3/5`. The menu labels are clear. `<IconTracks>` correct. |
| 5 track checkboxes | `CanvasHeader.tsx:149-158` | annotations/domains/clinvar/conservation/restriction | **KEEP** | Good labels. |
| Strand pill 5′→3′ / Both / 3′→5′ | `CanvasHeader.tsx:163-175` | Strand orientation | **KEEP** | Correct. |
| Export button | `CanvasHeader.tsx:177-185` | `window.print()` | **IMPROVE** | Labeled "Export" but only triggers browser print — mismatched expectation (user expects PNG/SVG/FASTA). Either rename to **"Print"** or wire a real export menu. ui-ux-pro-max `error-clarity`/honest-affordance. |
| (Align) header returns `null` | `CanvasHeader.tsx:88-89` | No controls for Align | **KEEP** | Fine; minor layout jump noted in chrome doc. |

### ZoomSlider (`ZoomSlider.tsx`)

| Element | file:line | Purpose | Verdict | What to do |
|---|---|---|---|---|
| − / + zoom steppers | `ZoomSlider.tsx:18-42` | ±2px/base density | **KEEP** | Functional. |
| Density range slider | `ZoomSlider.tsx:26-34` | Continuous 8-22px/base | **IMPROVE** | The control is fine; its **hover-only reveal** is the problem (`.sv-zoom-overlay-seq`, §3-A). Make it persistent (mirror the always-visible `.chromatogram-toggle` precedent the chrome doc cites). The − / + are 18px hit targets — below the 44px touch floor (ui-ux-pro-max `touch-target-size`). |
| `.zoom-pill` (Gene/Exon/Codon) | `workbench.css:154-177` | **DEAD** — retired presets, never rendered (`ZoomSlider.tsx:10-13` confirms removal) | **REMOVE** | Orphaned CSS that re-asserts a retired pattern. Flag-don't-autodelete per CLAUDE.md. |

### Sequence base grid (`CodonDetail.tsx`)

| Element | file:line | Purpose | Verdict | What to do |
|---|---|---|---|---|
| Base cell (click/drag/right-click) | `CodonDetail.tsx:489-516` | Select (L-click/drag), edit (R-click) | **IMPROVE** | Core surface. 13px is small (§3-B). **Edit is right-click-only** — no visible affordance; first-timers won't find it (ui-ux-pro-max `gesture-alternative` Critical). See §3-E. |
| Selection band + edge handles | `CodonDetail.tsx:630-664`; CSS `939-983` | Benchling cross-row selection w/ drag knobs | **KEEP** | Excellent — the most Benchling-grade element here. Knobs are well-designed (`::after` grab knob). |
| ClinVar dot (clickable) | `CodonDetail.tsx:316-331`; CSS `731-768` | Per-variant pin → focus + Scratchpad card | **KEEP** | Verdict ramp now correct (`--cls-*`). 10px dot w/ 20px hit area — good. |
| Queried-variant pin | `CodonDetail.tsx:529-535`; CSS `926-933` | Mark the queried position | **IMPROVE (P0 legibility)** | 0.5px, one-row-only. **This is the #1 fix** — see §3-A. |
| Restriction-site bar | `CodonDetail.tsx:583-612`; CSS `902-923` | Hover-highlight + click-select enzyme span | **KEEP** | Good (now a visible bar, not a hairline). |
| Splice-site GT/AG tag | `CodonDetail.tsx:241-260`; CSS `711-728` | 2bp donor/acceptor flag | **KEEP** | Strong — `--warn` on white text, unmissable. |
| Oligo / exon / intron feature bars | `CodonDetail.tsx:216-286`; CSS `694-708` | Annotation track | **IMPROVE (token)** | Exon `#f0ece2/#d8d0bb/#6b5a2a`, domain `#efe5ee/...`, oligo `#e8eaf2/...` are **raw hex off-token**. Promote to `--track-exon-*`/`--track-domain-*`/`--track-oligo-*` (chrome doc P2; values unchanged). |
| Translation AA pill | `CodonDetail.tsx:383-391`; CSS `846-875` | Codon→AA, biochem-class bg | **KEEP** | Good use of `--aa-*`. AA-num 8.5px is small (§3-C). |
| Ruler tick (c.NNN) | `CodonDetail.tsx:396-410`; CSS `664-676` | Coordinate every 10bp | **IMPROVE** | 9.5px `--ink-4` is below AA floor; and it scrolls away (§3-D, no sticky). |
| Conservation bar (PhyloP) | `CodonDetail.tsx:568-580`; CSS `891-899` | Per-base conservation height | **IMPROVE (chart)** | A bar chart with **no axis, no scale, no legend** — `height: v*26` teal bars float meaninglessly. ui-ux-pro-max `legend-visible` + `axis-labels`: add a min/max scale chip and a one-word legend ("PhyloP 0–8"). |
| Conservation complement/strand rows | `CodonDetail.tsx:682-687` | "Both" strand row | **KEEP** | Dimmed-55% complement is a sensible legibility choice. |
| Intron gap separator | `CodonDetail.tsx:122-129`; CSS `646-661` | "N bp omitted" | **KEEP** | Clear and honest. |
| Insertion marker (+N) | `CodonDetail.tsx:517-525`; CSS `878-888` | Edit insertion glyph | **KEEP** | Fine. |

### GeneMinimap (`GeneMinimap.tsx`)

| Element | file:line | Purpose | Verdict | What to do |
|---|---|---|---|---|
| Exon segment button | `GeneMinimap.tsx:126-153`; CSS `469-500` | Click → jump to exon | **IMPROVE** | The active exon is teal-tinted (good), but **exon fill is raw `#e6dfca`/`#c9bf99`** (off-token). Exon numbers are 9.5px and hidden under 1.8% width — many exons show as unlabeled cream slivers. This is exactly the "hard to see vs Benchling" the owner flagged: the minimap is low-contrast cream-on-warm-white. Raise segment border contrast (`--line-2`→ stronger) and tokenise the cream. |
| Intron hairline | `GeneMinimap.tsx:154-161`; CSS `501-510` | 1px connector | **KEEP** | Fine. |
| ClinVar density bubble | `GeneMinimap.tsx:96-121`; CSS `450-457` | Per-exon variant count | **KEEP** | `--warn` 30% opacity — readable. |
| Active-window flag (c.X) | `GeneMinimap.tsx:165-169`; CSS `511-536` | "you are here" callout | **KEEP** | Good — this is the *minimap's* version of the pin and it works; the *sequence grid* needs the same strength (§3-A). |
| 5′ / CDS bp / 3′ bookends | `GeneMinimap.tsx:171-175` | Orientation labels | **KEEP** | Fine. |

### ProteinView (`ProteinView.tsx`)

| Element | file:line | Purpose | Verdict | What to do |
|---|---|---|---|---|
| Lollipop head + stem | `ProteinView.tsx:164-190`; CSS `3757-3776` | ClinVar projected to aa | **IMPROVE (chart)** | Verdict ramp correct. But heads are **colour-only** — ui-ux-pro-max `color-not-only`/`pattern-texture` (CVD): a P vs LP vs VUS dot is distinguishable only by hue. Only the *queried* one gets a label (`:183-187`); the rest need hover (fine) **plus a visible legend** mapping colour→class. There is no class legend anywhere in the protein view. |
| Domain bar | `ProteinView.tsx:220-234`; CSS `3816-3821` | UniProt domains on backbone | **KEEP** | Teal-tint + label; good. Labels hide under 14% width — acceptable. |
| Region features (signal/membrane) | `ProteinView.tsx:205-219` | Feature spans | **KEEP** | Fine (hover titles). |
| Point features (active site/palmitoyl/query) | `ProteinView.tsx:247-269` | Residue points below backbone | **IMPROVE** | Colour/shape-coded points with **no legend** — a user can't tell active-site from palmitoylation from queried without hovering each. Add a compact legend row. |
| Scale ticks (aa) | `ProteinView.tsx:271-277`; CSS `3848-3852` | aa axis | **KEEP** | Good — this is the axis the conservation track lacks. |
| "Uniform size" legend note | `ProteinView.tsx:284-287` | Explains no size-encoding | **KEEP** | Excellent honest-design note. Extend this legend block to also carry the **class colour key** (closes the two IMPROVEs above). |

### FullLocusViewer (`FullLocusViewer.tsx`) — "Full gene" mode

| Element | file:line | Purpose | Verdict | What to do |
|---|---|---|---|---|
| 1-based / Genomic coord toggle | `FullLocusViewer.tsx:142-157` | Coordinate basis | **KEEP** | Useful. |
| Base cell | `FullLocusViewer.tsx:95-99`; CSS `3962-3986` | Locus base render | **IMPROVE (major)** | Bases are **monochrome ink** (`fl-base--exon → --ink`, no A/T/C/G colour) — a hard legibility regression vs the window grid, and **not clickable/selectable/editable**. This is an explicit unfinished proof-slice (file header: "No selection, edit … or color schemes this slice"). Flag as the biggest gap behind the "Full gene" promise — see §5. |
| Variant row highlight | `FullLocusViewer.tsx:70`; CSS `3933-3936` | Inset amber bar on variant row | **KEEP** | This is done *right* here (full-row inset shadow + tint) — ironically the window grid's pin should borrow this strength. |
| Unsupported "Back to Window" | `FullLocusViewer.tsx:217-236` | Recovery for unsupported genes | **KEEP** | Model recovery affordance — the viewer's *loading/error* state should copy this (chrome doc P1). |

---

## 3. Legibility / visual-hierarchy findings (each with the token/size fix)

**A. [P0] The queried-variant pin is a one-row 0.5px hairline — make it the unmissable full-canvas anchor it's specified to be.** `CodonDetail.tsx:529-535`, `.sv-marker-thin` `workbench.css:926-933`. Today `width:0.5px; background:--warn` and it only renders where `indices.includes(qIdx)`. DESIGN.md:586 mandates a pin "through all tracks." Fix: (1) widen to a **1.5-2px `--warn` rule** with a soft `--warn-tint` halo so it reads at 14px density; (2) render it in **every wrapped row** at the queried column (or, simpler and more Benchling-like, give the queried base/codon the full-row inset treatment that `FullLocusViewer`'s `.fl-row--has-variant` already uses — `box-shadow: inset 2px 0 0 --warn` + row tint). This is the highest-leverage legibility fix in the whole lane. **Durable visual → §5.**

**B. [P0-legibility] Base grid is too small + zoom is undiscoverable.** `.sv-base font-size:13px` (`workbench.css:775`), default `baseW=14px` (`WorkbenchShell.tsx:75`). Benchling's default base row is larger and its zoom is always on-screen. Two fixes: (1) bump the **default to `ZOOM_PRESETS.codon` (20px)** *or* raise the base font to **14px** — the owner explicitly said the gene view is hard to see vs Benchling, and this is the direct cause; (2) make the zoom **persistent** (next finding). Note the 4 base colours are deliberately ~25% chroma (`--base-A #d29a4a` etc., DESIGN.md "never Benchling rainbow") — keep the muted palette, but size is the lever, not saturation. ui-ux-pro-max `readable-font-size`. **Durable (default zoom) → §5.**

**C. [P1] Zoom slider hover-reveal fails touch + discoverability.** `.sv-zoom-overlay-seq { opacity:0 … }` → `:hover/:focus-within` (`workbench.css:194-209`). ui-ux-pro-max `hover-vs-tap` (**Critical**). The Align chromatogram already solved this with a *persistent* `.chromatogram-toggle` "always visible so the controls are discoverable on touch and don't rely on hover." Mirror it: a small persistent zoom handle docked top-right of the Sequence window that opens the slider. **Persistent-element → §5.**

**D. [P1] No sticky coordinate anchor in the scroll box.** `.sv-detail { max-height:62vh; overflow-y:auto }` (`workbench.css:614-616`) with no `position:sticky` ruler/header. Scrolling a multi-kb sequence loses all "where am I." Fix: a thin **sticky position strip** (current top-of-viewport c.X → c.Y range + active exon) pinned at the top of `.sv-detail`. ui-ux-pro-max Data-Dense sticky-header guidance; `content-priority`. **Structural → §5.**

**E. [P1] Single-base edit is right-click-only — no visible affordance.** `CodonDetail.tsx:506-513` (context menu), the only hint is buried in the Scratchpad card. A first-time left-click just selects. ui-ux-pro-max `gesture-alternative` (**Critical**): "always provide visible controls for critical actions." Fix: a small pencil affordance on a 1-base selection (or an "Edit" button in the selection summary card), reusing `<IconRename>`. **Interaction/structural → §5.**

**F. [P1] Conservation track is a legend-less, axis-less bar chart.** `.sv-cons-bar { height: v*26 }` (`workbench.css:891-899`), values from `data.conservation`. ui-ux-pro-max `legend-visible` + `axis-labels` + `contrast-data`: a bar chart with no scale communicates nothing quantitative. Fix: a min/max tick + a "PhyloP" label chip at the track's left edge; the `--teal` 0.55-opacity bars are fine. **Low-risk additive.**

**G. [P2] Sub-AA-floor type on ruler / AA-num / minimap labels.** `.sv-ruler-tick 9.5px`, `.sv-aa-num 8.5px`, `.sv-mm-exon-num 9.5px`, `.sv-block-pos .sub 9px` — all `--ink-4` (`globals.css:58` = 4.6:1, AA *at ≥11px*, not at 8.5px). On a dense warm-white grid these are strained. Fix: floor secondary mono labels at **10px** and bump the ones carrying coordinates (`sv-ruler-tick`, `sv-block-pos`) to `--ink-3`. ui-ux-pro-max `contrast-readability`.

**H. [P2] Missing `tabular-nums` on viewer figures.** `.sv-vnav-count`, `.sv-hist-count`, `.sv-block-pos`, ruler ticks are `--mono` but not `font-variant-numeric: tabular-nums` — coordinates jitter column-width as you step. The Align metrics already set it. Cheap polish. ui-ux-pro-max `number-tabular`.

**I. [P2] `.viewer` + several viewer transitions animate layout / bypass motion tokens.** `.viewer { transition: max-height .25s ease, padding .25s }` (`workbench.css:187`) and the `.viewer-collapsed` max-height pattern (`:213`) animate layout — DESIGN.md: "animate transform/opacity only." Plus raw `.08s/.12s/.15s` durations on `.sv-base`, `.sv-cv`, `.sv-section-head` bypass `--dur-1/--dur-2`. Swap to the tokens; collapse via opacity+grid-rows. (Chrome doc + 3-col spec both flag this — coordinate.)

---

## 4. Flow + eye-guidance (Apple-like seamlessness)

The vertical stack **minimap → protein → sequence** is a sound zoom-in narrative (whole gene → protein consequence → base detail), and the section headers now share one grammar — good. But the eye-guidance breaks in three concrete places:

1. **No through-line for the queried variant across the three windows.** The minimap flags it (`.sv-mm-flag`, strong), the protein view labels it (`.sv-pv-poplabel`, strong), but the sequence grid barely marks it (§3-A). The user's eye should be able to track *one* variant from gene → protein → base. Fix: make the sequence pin as loud as the other two so the queried variant is a continuous visual thread top-to-bottom. This single change does the most for "the next action is obvious."

2. **The most powerful controls are the quietest.** Reference/Variant basis-switching (the feature that makes this a *variant* workbench, not a sequence viewer) is an 11.5px mono pill in the far-right `CanvasHeader` cluster, visually identical to Strand. ui-ux-pro-max `primary-action` / `visual-hierarchy`: the highest-value control should not have the lowest visual weight. Consider promoting Reference/Variant to a clearer labelled toggle near the sequence, where its effect is visible.

3. **Zoom — the thing the owner says is hard to see — is invisible until hover.** Apple-grade seamlessness means the control for the current problem is already in view. Persistent zoom (§3-C) + a larger default (§3-B) directly answers "make the gene view easier to see."

Positive flow notes worth preserving: the find→jump→select→edit→Scratchpad loop is coherent; the selection band is genuinely Benchling-grade; the intron-gap "N bp omitted" separators keep the CDS-window honest; the protein "uniform size" legend note is exactly the kind of trust-building copy Apple-grade tools use.

---

## 5. 🟡 Durable / structural recommendations (GATED — need Steven's OK before any code)

Ranked by leverage (legibility-per-effort), per [[feedback_subagent_recommendations_not_authorization]]:

1. **Queried-variant pin → full-canvas anchor (§3-A).** Highest leverage. Borrow `FullLocusViewer`'s `.fl-row--has-variant` inset-shadow+tint pattern OR a 1.5-2px haloed `--warn` rule rendered in every row. Closes the DESIGN.md:586 invariant gap and the top "hard to see" complaint. *Durable visual on a persistent element.*

2. **Larger default base size + persistent zoom (§3-B, §3-C).** Set default `baseW` to `ZOOM_PRESETS.codon` (20px) or base font 14px, and make `ZoomSlider` a persistent handle (mirror `.chromatogram-toggle`). Directly answers the owner's "gene view hard to see vs Benchling." *Changes default density + a persistent control.*

3. **Sticky coordinate strip in `.sv-detail` (§3-D).** A pinned "current c.X-Y · exon N" header in the scroll box. Big orientation win on long sequences; Benchling-parity. *New persistent chrome.*

4. **Single-base Edit affordance (§3-E).** Visible pencil/Edit entry so editing isn't right-click-only. *New interaction entry point.*

5. **Class legends on the Protein view + a scale on Conservation (§2 ProteinView, §3-F).** Add a colour→ACMG-class key (extend the existing `.sv-pv-legend`) and a PhyloP min/max scale. CVD-safety (`color-not-only`) + chart-legend compliance. *Additive but adds persistent legend UI.*

6. **FullLocus "Full gene" parity (§2 FullLocus).** Today "Full gene" drops to monochrome, non-interactive bases — a visible downgrade behind a peer toggle. Either (a) bring A/T/C/G colour + selection to FullLocus, or (b) re-label/scope the toggle so it doesn't promise window-grade legibility it can't deliver yet. *Structural; larger — confirm scope/priority with Steven.*

7. **Tokenise the annotation/minimap palette (§2, §3 — exon/domain/oligo/minimap creams).** Promote the raw hex to `--track-*` tokens; raise minimap segment contrast so it stops reading as cream-on-warm-white. *Net-new tokens (values unchanged).*

**Safe quick-wins (token/value only, no structural or verdict-colour change):** delete dead `.zoom-pill` (`workbench.css:154-177`); add `tabular-nums` to `.sv-vnav-count`/`.sv-hist-count`/`.sv-block-pos`/ruler; floor secondary mono labels at 10px + bump coordinate labels to `--ink-3`; swap raw `.08s/.12s/.15s` viewer transitions to `--dur-1/--dur-2`; `3/5`-style "of N" on the Tracks + ClinVar counts.

**Out of scope (noted):** There is **no AlphaMissense heatmap track in the workbench viewer** — that's a `/report §2` feature. The only intensity element is the PhyloP conservation track (§3-F). All findings were captured against the `app/web/**` Next surface; the unimported GeneMinimap/ProteinView findings are historical per the retirement note above.
