# Workbench 3-column shell — promote the active tool into a right work-rail

**Status:** DESIGN EXPLORATION + SPEC. Review-gated — no `app/web/**` code lands until Steven OKs the recommended option + the open questions in §7. ([[feedback_subagent_recommendations_not_authorization]]: durable/structural/visual change needs an explicit yes first.)

**Scope:** Frontend-only, `/workbench`. Token-first (reuse `--cls-*`, the airy `.wr-section` grammar, the `Icon.tsx` 1.75 family, `--dur-*`/`--ease-*`, `--report-subpanel-*`). Reuse the existing `WorkRail` collapse/drawer machinery over inventing a parallel system.

**Method run (owner standing rules):**
- **Repository/source inspection** — surfaced the canonical machinery: `WorkRail.tsx` (`readCollapsed`/`storageKey`/`initialCollapsed`/`subscribeCompact`/`getServerCompactSnapshot`, the `--rail-live-w` custom prop, `mode-drawer`/`mode-inline`/`is-collapsed`/`is-open`), `WorkRailSection`, `LibrarySection`. Direct reads confirmed the compose path.
- **ui-ux-pro-max** — `--domain ux` searches for split-pane/collapsible/three-column, progressive disclosure, z-index/affordance/breakpoints. Cited inline.
- **Reference screenshot** (`Screenshot 2026-06-08 211055.png`) — a 3-pane SaaS shell: narrow left nav rail · center content canvas with its own collapse chevron · right "Workspace" panel that is *tabbed* (Conversations / Memory) and itself collapsible. Grounds proportions + the "center has a collapse handle, right panel is a peer rail" pattern.
- **DESIGN.md** motion table + **`docs/workbench-report-sweep/workbench-chrome.md`** (z-index-scale finding, the `.viewer` layout-animation finding).

---

## 0. Correction to the brief's "current implementation" notes

Two stale claims in the task brief, verified against source — flagging so the plan is built on truth:

1. **`viewerCollapsed(tool)` returns true ONLY for `align`**, not primer/crispr/align.
   `tools.ts:50-52` → `return tool === 'align'`. Today Primer and CRISPR keep the viewer **fully expanded** above the panel; only Align hides it (`.viewer-collapsed`). This matters: the brief's premise ("when a tool is active the viewer is not as important") is currently only realised for Align. The 3-col model generalises that intent to all three tools — but the *default* viewer state per tool is now a real product decision (§4, §7).
2. The `.viewer.viewer-collapsed` rule is at **`workbench.css:213`** (brief said 213 — correct), and its transition animates `max-height`/`padding` (layout), which the chrome audit already flagged as a DESIGN.md violation (`workbench.css:187`). The 3-col collapse must NOT inherit that pattern — see §4 motion.

---

## 1. Current state

```
/workbench, tool active (today)                       viewport ≥1200px
┌──────────────────────────────────────────────────────────────────────┐
│ TopNav (z-50, 60px)                                                    │
├──────────────────────────────────────────────────────────────────────┤
│ ContextStrip  gene · variant ········· [Sequence|Primer|CRISPR|Align] │  48px
├───────────────┬───────────────────────────────────────────────────────┤
│ WorkRail      │  .work-output → <main class="canvas">                  │
│ (left, 336px) │  ┌─────────────────────────────────────────────────┐  │
│ sticky        │  │ CanvasHeader (view controls, flush-right)        │  │
│               │  ├─────────────────────────────────────────────────┤  │
│ SidePanel:    │  │ <section class="viewer">                          │ │
│  Scratchpad   │  │   SequenceViewerV2 / FullLocus                    │ │
│  evidence kv  │  │   (collapsed→max-height:0 ONLY for align)         │ │
│  exon table   │  ├─────────────────────────────────────────────────┤  │
│               │  │ <section class="tool-panels">  ← FULL canvas width│ │
│ LibrarySection│  │   .tool-panel.active → Primer / CRISPR / Align    │ │
│               │  │   (stacked BELOW the viewer)                      │ │
│ collapse→48px │  └─────────────────────────────────────────────────┘  │
└───────────────┴───────────────────────────────────────────────────────┘
        ▲ controls                    ▲ output: viewer ABOVE, tool BELOW (vertical stack)
```

**Why the tool sits below today.** `WorkbenchShell.canvasOutput` is a single `<main class="canvas">` that vertically stacks `CanvasHeader` → `.viewer` → `.tool-panels`. `.tool-panels` (`workbench.css:1816`) maps `PANEL_TOOLS=['primer','crispr','align']` and shows only the active `.tool-panel` (`display:block`), full canvas width (`padding:22px 24px`). The viewer and the tool compete for the same vertical column; on Primer/CRISPR the viewer keeps full height, pushing the tool far down the page. The left `WorkRail` is the only horizontal split; the canvas itself has no internal columns.

**Pieces already in place we will reuse (not rebuild):**
- `WorkRail`'s collapse model: inline ≥1200 (336px ↔ 48px icon rail), drawer <1200 (off-canvas + scrim + FAB), `localStorage` persistence per `surface`, `--rail-live-w` published for fixed descendants, full `prefers-reduced-motion` guard, `useSyncExternalStore` SSR-safe breakpoint. (`WorkRail.tsx`, `work-rail.css`.)
- `WorkRailSection` airy icon-led grammar (`.wr-section*`) — the right rail's internal section chrome.
- `viewerCollapsed(tool)` + `.viewer-collapsed` — the existing viewer-hide hook (currently align-only).
- `ZoomSlider`, `CanvasHeader` track/strand/allele toggles — the viewer's own controls.

---

## 2. Target — ASCII mockups

### (a) Tool active + viewer EXPANDED — the new default for Primer/CRISPR (≥1200px)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ TopNav (z-50)                                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│ ContextStrip  gene · variant ················· [Sequence|Primer|CRISPR|Align] │
├───────────────┬───────────────────────────────────┬────────────────────────────┤
│ WorkRail      │ CANVAS (center, viewer)            │ TOOL RAIL (right)          │
│ left 336px    │  flex:1, min-width:0               │ ~46–50% of canvas, ≥420px  │
│ ◀ controls    │ ┌───────────────────────────────┐ │ ┌────────────────────────┐ │
│               │ │ CanvasHeader   [⤢ minimise ▾] │ │ │ Tool head  CRISPR  [⤢]  │ │
│ Scratchpad    │ ├───────────────────────────────┤ │ │  Design│Off-tgt│Outcome │ │
│ evidence      │ │ SequenceViewerV2              │ │ ├────────────────────────┤ │
│ exon table    │ │  (window / locus)             │ │ │  form fields (auto-fit) │ │
│               │ │                               │ │ │  [Generate]             │ │
│ Library       │ │                               │ │ │  result feed / tables   │ │
│               │ └───────────────────────────────┘ │ │   (overflow-x:auto)     │ │
│ collapse→48   │   ▲ "this is the sequence"         │ └────────────────────────┘ │
└───────────────┴───────────────────────────────────┴────────────────────────────┘
   STEP 1 context        STEP 2 see the sequence          STEP 3 act on it
   left → right workflow reading order (ui-ux-pro-max visual-hierarchy / "guide the eye")
```

### (b) Tool active + viewer MINIMISED/COLLAPSED — default for Align, opt-in for Primer/CRISPR

```
┌───────────────┬──────────┬─────────────────────────────────────────────────────┐
│ WorkRail 336  │ VIEWER   │ TOOL RAIL (right) — now ~70% of canvas               │
│               │ rail 48  │ ┌─────────────────────────────────────────────────┐ │
│ Scratchpad    │ ┌──────┐ │ │ Align   Reference · reads · chromatogram   [⤢]  │ │
│ evidence      │ │ S    │ │ ├─────────────────────────────────────────────────┤ │
│ Library       │ │ E ⤢  │ │ │ Reference / template ............ [Edit]        │ │
│               │ │ Q    │ │ │ Drop .ab1 reads ┄┄┄┄  [Choose .ab1] [Paste]     │ │
│               │ │ ↕    │ │ │ Find sequence  [ACGT…]                           │ │
│               │ │ rail │ │ │ ReadRow (chromatogram) — wide, gets the room     │ │
│               │ └──────┘ │ └─────────────────────────────────────────────────┘ │
└───────────────┴──────────┴─────────────────────────────────────────────────────┘
   the viewer becomes a thin vertical "Sequence" rail with an expand (⤢) handle —
   mirrors WorkRail's own .work-rail-stub collapsed treatment (writing-mode vertical label).
   Click ⤢ → it slides back to layout (a).
```

A *fully hidden* state (not even a rail stub) is available too — see §4 state model `hidden`. Default for Align is `collapsed` (rail stub visible, discoverable), NOT `hidden`, so the user can always get the sequence back without re-selecting the Sequence tool.

### (c) No tool active (Sequence/viewer mode) — UNCHANGED, 2-column

```
┌───────────────┬────────────────────────────────────────────────────────────────┐
│ WorkRail 336  │ CANVAS (full width) — viewer only, exactly as today             │
│ Scratchpad    │ ┌────────────────────────────────────────────────────────────┐ │
│ evidence      │ │ CanvasHeader (Window/Full-gene · allele · tracks · export)  │ │
│ Library       │ ├────────────────────────────────────────────────────────────┤ │
│               │ │ SequenceViewerV2 — full canvas width                        │ │
│               │ └────────────────────────────────────────────────────────────┘ │
└───────────────┴────────────────────────────────────────────────────────────────┘
   tool === 'viewer'  →  NO right rail, NO viewer-collapse handle. Pure viewer.
```

### (d) Narrow / responsive (<~1200px) — collapse order

```
1180px → 1024px  (tool active)
┌──────────┬──────────────────────────────────────────────────────────────────────┐
│ (left    │ CANVAS center                    │ TOOL RAIL right                    │
│  rail →  │ viewer (auto-minimised to rail   │ tool panel, now dominant           │
│  DRAWER, │  stub if tool needs the room)    │                                    │
│  off-    │                                  │                                    │
│  canvas, │                                  │                                    │
│  FAB)    │                                  │                                    │
└──────────┴──────────────────────────────────────────────────────────────────────┘

< ~900px  (single column, the right rail itself becomes a drawer/stacked)
┌────────────────────────────────────────────────────────────────────────────────┐
│ FAB ▤ (left rail)              FAB ⚙ (tool rail)                                 │
│ CANVAS full width: viewer (collapsible) → tool panel STACKED below (≈ today)     │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Collapse order (first to give way):**
1. **Left `WorkRail` → drawer first**, at the *existing* `BP_COMPACT` = `max-width:1199px`. This is already implemented; it frees the most horizontal room and the SidePanel/Library are "reference," not the active task. (ui-ux-pro-max `content-priority`: secondary content folds first.)
2. **Center viewer → rail-stub** next (auto, tool-driven) so the tool rail keeps a usable measure.
3. **Tool rail → stacked-below or its own drawer** last, at a second breakpoint (~900px), reverting to today's vertical stack — the tool is the active task, so it's the last to lose its column. Below this width the 3-col model is abandoned for the vertical stack (no horizontal scroll — ui-ux-pro-max `horizontal-scroll` High).

---

## 3. Options

### Option A — reuse `WorkRail` as a *mirrored right rail inside the canvas output*

Render a second `<WorkRail>` (or a thin `WorkRail`-derived `side="right"` variant) **inside** `canvasOutput`, wrapping the viewer as its `output` and the tool panel as its rail `children`, mirrored to the right edge.

- **How:** `canvasOutput` becomes `tool==='viewer' ? <viewer/> : <WorkRail side="right" surface="workbench-tool" output={<viewer/>}>{toolPanel}</WorkRail>`. Add a `side?: 'left'|'right'` prop to `WorkRail`: flips `flex-direction`, `border-right`→`border-left`, the stub/scrim/FAB anchoring, and the toggle chevron direction.
- **Pros:** Maximum reuse — collapse/drawer/persistence/`--rail-live-w`/reduced-motion all come free. One mental model, two instances. The viewer's collapse becomes *the right rail's `output` shrinking*, which is exactly what the collapsed-rail machinery does in reverse.
- **Cons:** `WorkRail` is currently hardcoded left (sticky `top`, `border-right`, stub rotate, FAB `left:16px`, drawer `translateX(-100%)`). A `side` prop touches ~8 CSS rules and the toggle SVG. **Nesting two `WorkRail`s** means two sticky contexts + two `--rail-live-w` publishers — the inner one must not clobber the outer (scope the custom prop or rename). Also the right rail's "rail" is the *tool* (the important thing) and its "output" is the *viewer* (the de-emphasised thing) — semantically inverted from the left rail, which may confuse the shared component's vocabulary ("output is the stable anchor").

### Option B — a new `.canvas` grid `[viewer | tool-rail]`, reposition the existing `.tool-panels`

Keep one `<main class="canvas">`. When a tool is active, switch `.canvas` to a 2-col CSS grid: `grid-template-columns: minmax(0,1fr) var(--tool-rail-w)`. Move `.tool-panels` into the right grid track; the viewer + CanvasHeader stay in the left track. Viewer collapse toggles the left track to a fixed 48px stub (`grid-template-columns: 48px minmax(0,1fr)`), or to `0` for hidden.

- **How:** A `data-tool-active` / `data-viewer-state` attribute on `.canvas` drives the grid template. The viewer-collapse handle is a small button in the CanvasHeader (or a stub button when collapsed). The tool rail gets its own sticky + scroll + section chrome reusing `.wr-section`/`.side-section`.
- **Pros:** No `WorkRail` API change; no nested sticky contexts; one grid is the simplest mental model and the cleanest stacking story (one z-context for the canvas). Animating `grid-template-columns` is *sanctioned* by DESIGN.md's Disclosure row (`grid-rows`/`grid-cols` + opacity) and there's precedent (`.primer-l3-wrap` grid-rows reveal). Full control over the viewer↔tool split ratio via one `--tool-rail-w` token.
- **Cons:** Re-implements *some* of what `WorkRail` already does (collapse handle, persistence, the <1200 drawer for the tool rail). We'd lift the helpers (`storageKey`/`readCollapsed`) into a tiny shared module rather than duplicate. More net-new CSS than A, but it's additive and scoped to `.canvas`.

### Option C — Hybrid (RECOMMENDED): grid-based canvas split (B) + a small shared `WorkRailSection`-grammar tool-rail, with the viewer-collapse helpers factored out of `WorkRail`

Take Option B's single-grid canvas (cleanest stacking, no nested rails, owner-controlled split ratio), but:
- Build the **tool rail's internal chrome from the existing shared primitives** — `.wr-section`/`WorkRailSection` for any grouping, the `Icon.tsx` 1.75 family for the head glyph, `--report-subpanel-*` for card geometry — so the right rail reads as the *same system* as the left rail and the report. No new visual language.
- Factor the 3 collapse helpers (`storageKey`, `readCollapsed`, persisted toggle) out of `WorkRail.tsx` into `lib/work-rail-collapse.ts` and have BOTH the left `WorkRail` and the new viewer-collapse consume them — so persistence/SSR behaviour is identical and DRY, without forcing a `side` prop or a nested rail.
- Reuse `WorkRail`'s **drawer mechanics conceptually** (scrim + FAB + `translateX`) for the <900px tool-rail fallback, but only if QA shows the stacked-below fallback is insufficient (start with stacked-below — simpler).

- **Pros of C over A:** avoids the nested-sticky / inverted-semantics / `--rail-live-w` collision problems of A; avoids the duplication risk of pure B by sharing helpers; keeps one z-context. Owner gets a real split-ratio knob. The right rail is visually identical to the left rail without bending `WorkRail`'s "output is the anchor" contract.
- **Pros of C over B:** DRY persistence; the rail chrome is the *shared* grammar, not a one-off.
- **Cons:** Requires a small, clean refactor (extract 3 helper fns) before the feature — a touch of upfront cost, but it's a pure lift with no behaviour change and makes both rails honest.

**Recommendation: Option C.** It maximises reuse where reuse is cheap (the section grammar, the collapse helpers, the tokens) and avoids reuse where it's expensive/awkward (forcing `WorkRail`'s left-anchored, output-is-anchor shape onto a right rail whose "anchor" is the de-emphasised viewer). The single-grid canvas is the simplest stacking and the most honest fit for "left → center → right is one workflow."

---

## 4. Gene-viewer state model

A 3-state model on the **center viewer**, owned by `WorkbenchShell` (lifted from the current binary `viewerCollapsed(tool)`).

```ts
type ViewerPane = 'expanded' | 'collapsed' | 'hidden'
```

| State | What it looks like | Affordance to leave it |
| --- | --- | --- |
| `expanded` | viewer at full center-column width (mockup a) | minimise handle in CanvasHeader (⤢/▾) → `collapsed` |
| `collapsed` | thin 48px vertical "Sequence" rail stub (mockup b), mirrors `.work-rail-stub` (writing-mode vertical label + expand button) | the stub *is* the expand button → `expanded`; tool rail grows to fill |
| `hidden` | viewer removed from layout; a single restore chip in CanvasHeader region ("Show sequence") | restore chip → `expanded` |

**Default state per tool** (replaces `viewerCollapsed`; this is a §7 decision, proposed defaults):
- `viewer` → N/A (no tool; 2-col, no handle).
- `primer` → **`expanded`** (primer design references the exon/SNP context; keep the sequence visible). The brief's "viewer is not as important" is honoured by the *narrower* center column, not by hiding.
- `crispr` → **`expanded`** (guide placement is spatial; the user wants to see PAM/exon context). Off-targets sub-tab is table-heavy → see §5; the user can `collapse` to give the table room.
- `align` → **`collapsed`** (today it's fully hidden; `collapsed` is strictly better — keeps a discoverable handle instead of a dead area). The trace is the wide element → it wants the room.

**Where the handle lives.** In `expanded`, a single icon button at the right end of the CanvasHeader row (`IconWindow`/a minimise glyph from the 1.75 family), `aria-label="Minimise sequence"`, `aria-expanded`, `title`. In `collapsed`, the stub itself (`role=button`, `aria-label="Expand sequence"`). This mirrors `WorkRail`'s own toggle+stub pair exactly. Note the chrome audit already wants a *persistent* (non-hover) handle here — this satisfies that.

**Persistence.** Per-tool viewer state persists in `localStorage` (`eamos-wb-viewer-<tool>`), reusing the extracted `readCollapsed`/`storageKey` helpers (Option C). SSR returns the proposed default; client reads the persisted value in a lazy `useState` initializer — same no-setState-in-effect pattern `WorkRail`/`WorkbenchShell` already use.

**Motion (token-compliant — this is the load-bearing constraint).**
- The split MUST animate via **`grid-template-columns`** (sanctioned by DESIGN.md Disclosure: `grid-rows`/cols + opacity) at `--dur-2 var(--ease-emphasized)` — NOT `max-height`/`padding`/`width` on the viewer (the chrome audit's `.viewer` finding; DESIGN.md "avoid animating width/top/margin").
- The viewer content cross-fades `opacity` 0→1; the stub label fades in on the exit.
- The chevron/minimise glyph uses `transform: rotate` (DESIGN.md Disclosure).
- Ship the `@media (prefers-reduced-motion: reduce)` guard (drop the transition; instant state swap) — match `work-rail.css`'s existing guard.

**Keyboard / a11y.**
- The minimise/expand handle is a real `<button>` with `aria-expanded` + `aria-label` + `title`; Tab-reachable; visible focus ring (`box-shadow: 0 0 0 3px color-mix(--teal 22%)` per `.wr-section-head:focus-visible`).
- State change does not steal focus from the tool rail; after collapse, focus stays on the handle (which becomes the stub).
- The viewer region keeps a stable landmark (`role` unchanged); `hidden` removes it but leaves the restore chip in the tab order.
- Non-colour cue: the stub carries the word "Sequence" (text, not colour) so the collapsed state is legible to everyone (ui-ux-pro-max `color-not-only`).

**Interactive vs static legibility (the owner's "guide the eye" goal).**
- Reading order is strictly **left (context) → center (see) → right (act)** — the workflow is the layout. (ui-ux-pro-max `visual-hierarchy`.)
- Every editable/interactive control keeps the existing affordance vocabulary: `.field-input`/`.field-select` borders (ui-ux-pro-max `input-affordance`), `.btn-teal` for the one primary action per rail (ui-ux-pro-max `primary-action`: one CTA per region — Primer's "Generate & validate", CRISPR's run, Align's "Use this reference"), hover feedback on every clickable (`hover:bg`, the chrome audit's hover-state finding).
- The collapse/expand handles are persistent (not hover-revealed) so they're discoverable on touch — matching the existing `.chromatogram-toggle` precedent the chrome audit cites.

---

## 5. Per-panel reflow risks at ~half width

Target right-rail measure: ~46–50% of a 1440px-max canvas minus the 336px left rail ≈ **480–540px** when the viewer is `expanded`; ~70% (≈760px) when the viewer is `collapsed`. Min usable rail width: **≥420px** (below that, force the viewer to `collapsed` or stack).

### Primer (`PrimerPanel`) — LOW risk
- `.tool-form` is `grid-template-columns: repeat(auto-fit, minmax(170px,1fr))` (`workbench.css:1847`) → reflows from 5 cols → 2–3 cols cleanly at ~500px. No change needed.
- `.tool-panel-head` is `flex-wrap` already; the mode `seg` will wrap under the title — fine.
- `PrimerResultCard` feed is single-column (`.primer-feed-item`) — already narrow-friendly.
- **Verdict:** works at ≥420px as-is. No `expand-to-full` needed.

### CRISPR (`CrisprPanel`) — MEDIUM risk
- Three sub-tabs (Design / Off-targets / Outcomes). `.crispr-summary` already collapses to 1fr at `max-width:560px` (`workbench.css:3225`) — but that breakpoint is *viewport*-based; in a half-width rail the *container* is ~500px while the viewport is 1440px, so the media query won't fire. **This is the core risk: viewport media queries don't see the rail width.** Fix: either (a) container queries (`@container`) on the tool rail, or (b) drive the breakpoint off a `data-rail-narrow` attribute the shell sets when the viewer is `expanded`.
- `.crispr-table-wrap` already has `overflow-x:auto` (`workbench.css:3183`) so the two-table degrades to horizontal scroll — acceptable but not ideal (ui-ux-pro-max `table-handling`: scroll is the sanctioned fallback).
- **Off-targets sub-tab** (`OffTargetTab`): base-coloured 20-mers + ringed mismatches + pinned on-target row + ±flank screening primers. This is the **widest CRISPR content**; at ~500px it will horizontal-scroll heavily.
- **Verdict:** Design + Outcomes are fine with container-aware breakpoints. **Off-targets argues for an `expand-tool-to-full` affordance** (a maximise handle on the tool rail that forces the viewer `hidden` and the rail to full canvas width) OR an auto-`collapse` of the viewer when the Off-targets sub-tab is selected.

### Align (`AlignPanel`) — HIGH risk → strongest full-width argument
- `.align-source-grid` is a two-column grid `minmax(0,1.15fr) minmax(280px,0.85fr)` (`workbench.css:2018-2020`) — at ~500px the 280px min track forces an ugly squeeze; needs to collapse to 1-col (again, container-aware, not viewport).
- `ReadRow` chromatogram trace is intrinsically wide (per-base columns); it's the single widest element in any tool and already scrolls.
- Align **already** sets the viewer to hidden today (`viewerCollapsed('align')===true`), confirming Align doesn't need the sequence beside it.
- **Verdict:** Align should default to viewer-`collapsed` (mockup b) so the rail is ~70% wide, AND expose `expand-tool-to-full` (viewer `hidden`) for the trace. The `.align-source-grid`, `.align-input-row` (`repeat(2,minmax(0,1fr))`), and `.align-source-stats` (`repeat(3,…)`) all need a container-narrow 1-col fallback.

**Cross-cutting reflow rule:** because the rail width is decoupled from the viewport, **all three panels need container-relative breakpoints** (`@container` on the tool-rail wrapper is the clean answer; a `data-*` flag the shell sets is the no-`@container` fallback). Tables get `overflow-x:auto` wrappers (most already have them). The widest surfaces (CRISPR Off-targets, Align trace) justify an **`expand-tool-to-full`** maximise affordance on the tool rail that drives the viewer to `hidden`.

---

## 6. Component + CSS change map

Legend: 🟡 = DURABLE/STRUCTURAL/persistent-element — needs Steven's OK (§7). 🟢 = additive/safe within the approved feature.

| File | Change | Flag |
| --- | --- | --- |
| `lib/work-rail-collapse.ts` **(new)** | Extract `storageKey`/`readCollapsed`/persisted-toggle from `WorkRail.tsx` (pure lift, no behaviour change); consumed by `WorkRail` + the new viewer state. | 🟢 (refactor, behaviour-neutral) |
| `components/layout/WorkRail.tsx` | Import the extracted helpers (delete the now-duplicated local fns). No API change in Option C. | 🟢 |
| `components/workbench/tools.ts` | Replace `viewerCollapsed(tool): boolean` with `defaultViewerPane(tool): ViewerPane` (`expanded`/`collapsed`/`hidden`). Encodes the §4 per-tool defaults. | 🟡 (changes default layout behaviour per tool) |
| `components/workbench/WorkbenchShell.tsx` | Lift `viewerPane` state (3-state, persisted); restructure `canvasOutput` so that when `tool!=='viewer'` the canvas is a 2-track grid `[viewer \| tool-rail]`; move the active `.tool-panel` into the right track; keep the `tool==='viewer'` path as today (2-col). Wire the minimise/expand/maximise handles. | 🟡 (the core structural change) |
| `components/workbench/CanvasHeader.tsx` | Add the viewer minimise/restore handle (1.75-family glyph, `aria-expanded`, `title`). Decide what happens to track/strand/export when the viewer is `collapsed`/`hidden` (move into the rail-stub menu, or hide — §7). | 🟡 (persistent chrome) |
| `components/workbench/workbench.css` | New `.canvas[data-tool-active]` grid + `--tool-rail-w` token; `.wb-tool-rail` (sticky, scroll, reuse `.wr-section`/`.side-section` grammar); `.wb-viewer-stub` (mirror `.work-rail-stub`); grid-cols transition at `--dur-2 var(--ease-emphasized)` + reduced-motion guard. **Do NOT reuse the `.viewer-collapsed` max-height pattern** (audit-flagged). Container-aware (`@container`) breakpoints for the panels OR a `data-rail-narrow` hook. | 🟡 (new persistent layout chrome) |
| `components/workbench/primer|crispr|align/*.css` rules | Convert the panels' internal viewport media queries (`max-width:560px`, the align grids) to container-relative so they fire on rail width, not viewport. Add `overflow-x:auto` where missing. | 🟢 (within feature; behaviour-improving) |
| z-index | Introduce the workbench z-scale the chrome audit already specced (`--z-rail/--z-nav/--z-drawer/--z-popover/--z-pill`) so the new tool-rail + its (optional) drawer/FAB don't collide with nav/AI-pill. | 🟡 (touches stacking on persistent chrome — coordinate with the chrome-audit item, don't double-define) |

**Tokens to reuse (no new visual language):** `--cls-*` (any verdict colour stays correct), `.wr-section`/`.side-section` grammar, `Icon.tsx` 1.75 family (`IconWindow`/`IconChevron`/an `IconExpand`), `--dur-*`/`--ease-*`, `--report-subpanel-*` (rail card geometry), `--side-w`/`--maxw-workbench-side` (mirror the left rail's width vocabulary for the tool rail), the published `--rail-live-w` pattern if a fixed descendant needs offsetting.

---

## 7. Open questions for Steven

1. **Default viewer state per tool.** Proposed: Primer `expanded`, CRISPR `expanded`, Align `collapsed`. Agree? In particular: should CRISPR auto-`collapse` the viewer when the **Off-targets** sub-tab (the widest content) is selected?
2. **Split ratio.** Proposed ~50/50 when `expanded` (viewer | tool), ~30/70 when `collapsed`. Fixed token, or **user-resizable** (drag handle between the two)? Resizable is more work + a new interaction; I'd ship fixed first unless you want the drag handle in v1.
3. **Is the right tool-rail itself collapsible** (like the left rail can icon-collapse), or only the *center viewer* collapses? The reference screenshot's right "Workspace" panel has its own collapse chevron. Proposed: the tool rail does NOT icon-collapse (it's the active task); only the viewer collapses. Confirm.
4. **CanvasHeader controls when the viewer is `collapsed`/`hidden`.** The track/strand/allele/export controls belong to the viewer. When the viewer is a 48px stub or hidden, do those controls (a) hide, (b) move into the rail-stub as a small menu, or (c) stay docked in a slim header strip? Proposed: hide in `hidden`, collapse into a stub menu in `collapsed`.
5. **`expand-tool-to-full` affordance.** Should the tool rail get a maximise handle that drives the viewer to `hidden` and the rail to full canvas width (for CRISPR Off-targets + Align trace)? Proposed: yes, as a small handle on the tool-rail head.
6. **Narrow fallback (<900px):** revert to today's vertical stack (viewer above, tool below) — confirm that's preferred over making the tool rail its own bottom drawer.
