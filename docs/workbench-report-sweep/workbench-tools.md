# Workbench Tool Panels — Design Audit & Spec (Primer · CRISPR · Align)

Surface: `/workbench` tool panels in `app/web/components/workbench/{primer,crispr,align}/**`.
Scope: design audit + token-first fix spec. **No product code edited.**
Ground truth: `DESIGN.md`, `app/web/app/globals.css`, `app/web/components/workbench/workbench.css`, `app/web/lib/classification.ts`.
Skills applied: `frontend-design` (clinical-restraint lens) + `ui-ux-pro-max` (targeted `--domain ux` searches; cited inline as **[UPM]**).

---

## 1. Snapshot

The three tools are clearly the work of one hand and broadly share a grammar: a `.tool-panel-head` (Spectral 16px title + mono sub), a `.seg` segmented switcher, the `.tool-form` field grid, `.btn-teal` primary action, `.help-note` caveats, and `--base-*`-coloured sequence renderers. **Primer is the reference implementation** — it executes the DESIGN.md 3-layer Dashboard Interaction Language faithfully (`card--interactive`, real ARIA disclosure, honest single-pending loading, focusable tooltips) and is the most polished. **CRISPR** is the densest and most divergent: two `.tool-table`s, a `.crispr-summary` roll-up, a hand-rolled `GuideTrack` ribbon and `IndelSpectrum` SVG; it carries the most off-token colour and the most table-density debt. **Align** is internally strong (shared-coordinate trace, `tabular-nums` metric strip, 4-way orientation) but uses a *different* result-card and metric grammar from Primer/CRISPR, and leans on raw rgba/hex in the chromatogram layer.

The single biggest cross-tool gap is **numeric typography**: the invariant says scores/coords/Tm/GC are mono **and tabular**, but `font-variant-numeric: tabular-nums` is set in only three places (all in Align). Every CRISPR table column, every Primer Tm/GC/ΔTm, and the candidate-summary values render with proportional figures — columns of numbers don't line up. The second is **PAM emphasis**, which is correct in the CRISPR ribbon (saturated amber) but reverts to the exact "invisible pale tint" the project history called out in the CRISPR *table*. Consistency with the report surface is good on tokens (same `--cls-*`, `--base-*`, `--ink-*`) but the three tools do not share one result-card or metric shape.

---

## 2. Findings

### PRIMER (`primer/PrimerPanel.tsx`, `primer/PrimerResultCard.tsx`)

**[P1] Tm / GC / ΔTm / product numbers are not tabular** · `PrimerResultCard.tsx:133-135,147-149,163,206,211,218,223` + css `workbench.css:3588,3594,3604,3606`
Problem: `.primer-seq`, `.primer-strand-m`, `.primer-product`, `.primer-dtm` are mono but have no `font-variant-numeric`. The invariant says scores/coords are mono **tabular**; here `Tm 59.8` over `Tm 61.0` don't align, and the Layer-3 `.primer-kv` `<dd>` columns wobble.
Fix: add `font-variant-numeric: tabular-nums;` to `.primer-strand-m`, `.primer-product`, `.primer-dtm`, and the `.primer-kv dd` rule (search `.primer-kv` block). Token-only, no value invented.
Why: invariant adherence + **[UPM Content/Number-Formatting]** — number columns must not shift.

**[P2] `.primer-badge` borders use raw hex** · `workbench.css:3544,3548,3552` (`#cbe3d8`, `#e8c6c6`)
Problem: the teal/err badge borders are literal hex, not tokens, despite the bg/text already being `--teal-tint`/`--warn-tint`/`--err-tint`.
Fix: `tone-teal` border → `color-mix(in oklab, var(--teal) 28%, transparent)`; `tone-err` border → `var(--cls-path-bdr)` (or `color-mix(in oklab, var(--err) 28%, transparent)`). `tone-warn` already uses `--warn-bdr` — match that pattern.
Why: "no raw hex in components" (DESIGN.md tokens rule); `#cbe3d8` recurs in 3 files (see cross-tool C4).

**[P2] Copy-pair success is announced but the star is a glyph** · `PrimerResultCard.tsx:99,3559`
Problem: `★` is a text glyph (DESIGN.md permits it as the one sanctioned non-icon mark, and there is an `sr-only` "(recommended)"). This is *fine* — flagged only so it is not "corrected" into an Icon.tsx call. No change.

*Primer otherwise passes: `card--interactive` hover, `aria-expanded`/`aria-controls` disclosure, focusable `.primer-tip-q` with `aria-label`, honest 3-phase pending, `--elev-3` tooltip. This is the template the other two should converge toward.*

---

### CRISPR (`crispr/CrisprPanel.tsx`, `DesignTab.tsx`, `OffTargetTab.tsx`, `GuideTrack.tsx`, `IndelSpectrum.tsx`, `OutcomesTab.tsx`)

**[P0] Table PAM is the "invisible pale tint" — contradicts the ribbon and the stated intent** · css `workbench.css:3213-3217` vs `3364-3373`
Problem: the design intent (memory + DESIGN history) is "PAM emphasised — amber box + caption, NOT a pale tint." The **ribbon** `.gt-base.pam` correctly uses saturated `--warn-bdr` + inset `--warn` ring. But the **table** `.g-pam` (the `Guide 5′→3′ + PAM` column, shown on every row) uses pale `--warn-tint` with a `--warn-bdr` hairline — exactly the invisible tint that was explicitly walked back. Two renderers of the same concept disagree.
Fix: bring `.g-pam` to ribbon parity: `background: var(--warn-bdr); color: var(--warn-text); box-shadow: inset 0 0 0 0.5px var(--warn); font-weight: 700;` (drop the `border`, keep `padding`/`radius`). One token swap, no new values.
Why: invariant of the feature (PAM must be unmistakable) + internal consistency; the table is where users actually scan guides, so the *weaker* treatment is on the higher-traffic surface.

**[P1] No numeric column is tabular in either CRISPR table** · `DesignTab.tsx:485-505`, `OffTargetTab.tsx:591-642,757-779` + css `workbench.css:1922-1926`
Problem: `.tool-table td.num` (Start/End, On-target, Off-target, GC%, Score, MM, Tm, product) and `.cs-v` (line 3207) are mono but lack `tabular-nums`. Scores like `0.241`/`1.000`, `74.3`/`8.1`, GC `45`/`100` don't right-align cleanly; the stacked F/R Tm cells (`ots-primer` `768-777`) wobble vertically.
Fix: add `font-variant-numeric: tabular-nums;` to `.tool-table td.num` and `.cs-v`. (Align's `.align-metric b` already does this — copy the declaration.)
Why: invariant + **[UPM]** number-column stability; this is the densest numeric surface in the Workbench.

**[P1] Off-target mismatch cue is real but described as "ringed" — and is colour+underline only** · `OffTargetTab.tsx:66-74`, css `workbench.css:3259-3264`; header copy says "underlined" (`576`)
Problem: mismatched bases get `.g-nt.mm` = bolder weight + 2px underline. That is two non-colour cues (good, satisfies **[UPM Accessibility/Color-Only, Severity High]**). But the intent on record is a *ring* around the mismatched base, and the on-target row pins fine. The current underline collides visually with the PAM box's bottom edge at small sizes and is easy to miss against the base colour.
Fix (token-only, keeps "never colour-alone"): swap underline for a ring — `.g-nt.mm { box-shadow: inset 0 0 0 1.5px var(--ink-3); border-radius: 2px; font-weight: 800; }`. Uses an existing ink token; reads as the spec'd "ringed mismatch" and survives at 11.5px.
Why: matches stated feature intent + stronger glance-legibility than a thin underline.

**[P1] Candidate-summary `.crispr-summary` is a 2-col grid of 7 cells → orphan row** · `DesignTab.tsx:352-395`, css `workbench.css:3191-3208`
Problem: `repeat(2, 1fr)` with 6 or 7 `.cs-cell`s leaves a lone "Recommended" cell spanning an awkward half when `recIdx>=0` (7 items in a 2-col grid). On the Off-target summary it's 4 cells = clean; on Design it's 6–7.
Fix: `grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));` (mirrors `.align-summary:2177`). Self-balances 4/6/7 cells; no orphan. Keep the `max-width: 560px → 1fr` fallback.
Why: rhythm/alignment; reuses the Align summary's proven responsive pattern for cross-tool consistency.

**[P1] Wide tables (`min-width: 920px`) scroll under a non-sticky header** · css `workbench.css:1898-1907,3166-3173`
Problem: `.crispr-table-wrap` is `overflow-x: auto` over a 920px-min table inside a ~such-width canvas; `thead th` has no `position: sticky`. On a filtered Off-target list (many rows) the column headers scroll out of view vertically, and there is no horizontal header pinning either. **[UPM Responsive/Table-Handling]** is satisfied for overflow but the header legibility is not.
Fix: `.tool-table thead th { position: sticky; top: 0; z-index: 1; background: var(--bg); }`. (The table already sits in a scroll container.) Token-only.
Why: a 10-column genomic table is unusable once the header is gone; sticky header is the standard remedy.

**[P2] `.seq-hl-silent` and `.ic-bar.predicted` use a raw indigo (`#e8eaf2`/`#3b4877`)** · css `workbench.css:1990,3420`
Problem: the ssODN "silent PAM-blocking edit" highlight and the predicted indel bars use literal indigo with no token. The same indigo (`#3b4877`/`#e8eaf2`) appears in the viewer's oligo bar and `.sv-pop-conseq .cs.splice` — it is a de-facto fourth accent with no name.
Fix: introduce one Workbench token pair in globals (`--wb-indigo: #3b4877; --wb-indigo-tint: #e8eaf2;`) OR re-point these to the existing `--info-*` family (`--info-text`/`--info-bg`, oklch indigo already defined at globals `115-118`). Prefer `--info-*` — it already exists and is CVD-checked.
Why: "no colours outside the palette / no raw hex in components"; this is the single most-repeated unofficial colour in the Workbench.

**[P2] Outcomes `.crispr-file` native file input is unstyled** · `OutcomesTab.tsx:56-94`, css `workbench.css:3403`
Problem: control/edited trace pickers are raw `<input type=file>` with only padding/size set — the OS "Choose File" button breaks the clinical surface, unlike Align's `.align-file-btn` label-wrapped picker.
Fix: adopt Align's pattern — wrap in a `<label className="align-file-btn">` styled control with a hidden input (already exists at `AlignPanel.tsx:168-178`). Reuse, don't restyle the native widget.
Why: consistency with the other upload affordance in the same surface; native file buttons are the classic "looks unprofessional" tell.

**[P2] `IndelSpectrum` has no empty/no-data branch** · `IndelSpectrum.tsx:28-35`
Problem: if `spectrum` is empty the SVG renders an axis frame with no bars. **[UPM Charts/empty-data-state]** wants "No data yet" guidance, not a blank axis.
Fix: guard `if (spectrum.length === 0) return <div className="help-note">No indel bins to plot.</div>`. (OutcomesTab only renders it inside `res &&`, so low-risk, but the component is reusable.)
Why: defensive empty-state; cheap.

*CRISPR strengths to preserve: every `<th>` carries a `title` tooltip; sort buttons have `aria-label`; the on-target row is pinned with `inset 2px 0 0 var(--teal)` + text "on"; loading disables the button; row `:focus-visible` ring exists.*

---

### ALIGN (`align/AlignPanel.tsx`, `AlignedTrace.tsx`, `PairwiseView.tsx`, `ReadRow.tsx`)

**[P1] `.aln-band` diff/search fills are raw rgba, off the `--cls-*` / token system** · css `workbench.css:2772-2778`
Problem: mismatch `rgba(193,58,52,.18)`, gap `rgba(186,117,23,.14)`, search `rgba(212,175,55,.26/.5)` are literal. The mismatch red (`193,58,52`) is *not* `--err` (`#B82B2B` = `184,43,43`) and the search gold (`212,175,55`) is a brand-new colour with no token anywhere.
Fix: mismatch → `color-mix(in oklab, var(--err) 18%, transparent)`; gap/lowq → `color-mix(in oklab, var(--warn) 14%, transparent)`; active → `color-mix(in oklab, var(--teal) 18%, transparent)` (the `.aln-band.active` stroke is already `--teal-deep`). For search, reuse `--warn` mixes rather than inventing gold, OR name a `--wb-find` token once.
Why: token discipline + the diff red should equal the rest of the app's `--err`, not a near-miss.

**[P1] Het marker is colour-only (purple block + purple count), violating "never colour alone"** · `AlignedTrace.tsx:250-252`, `ReadRow.tsx:82-90`, css `workbench.css:2816,2834`
Problem: heterozygous positions are signalled solely by a `#7c5cd6` purple band under the trace and a purple "N het" count. No shape, no glyph, no text on the band itself. **[UPM Accessibility/Color-Only, Severity High]** — a CVD user cannot distinguish het from a normal column.
Fix: keep the band but add a non-colour cue — a small "²" / double-peak tick glyph, or a 1px dashed top edge (`stroke-dasharray`) on the het rect; and in the head, the `.tag-het` already has descriptive `title` (good) but pair the count with a glyph (e.g. a `⌇`/"het" text label, which it has) — the band is the gap.
Why: a11y; het calls are clinically load-bearing.

**[P2] `#7c5cd6` het purple is a raw hex with no token** · css `workbench.css:2816,2834` (`.chromatogram-het`, `.tag-het`)
Problem: purple het colour is literal in two rules and is otherwise absent from the palette.
Fix: name it once — `--wb-het: #7c5cd6;` in the Workbench token block (globals) — or re-point to `--info-dot` (oklch indigo) if a distinct het hue isn't required. Document why purple if kept (it sits off the ACMG ramp deliberately, like `--info-*`).
Why: token discipline; pairs with the P1 above.

**[P2] Orientation `<select>` carries the orientation glyph in option text, not on the collapsed control** · `ReadRow.tsx:23-28,103-115`
Problem: the 4-way orientation (`→/←/↕/⇄`) is in each `<option>` label, so the collapsed native select *does* show the active glyph (good — this satisfies the "icon next to it" ask). But the glyphs are Unicode arrows inside a native select; on Windows they render in the OS font, not Inter/mono, and the native select can't be fully styled.
Fix (no structural change): acceptable as-is for a native select. If polish is wanted later, a custom listbox would let the glyph use Icon.tsx — but that is a FLAGGED structural change (see §3), not a token fix. Leave for now; note only.
Why: documents the seam; avoids an unapproved control rewrite.

**[P2] Align result grammar diverges from Primer/CRISPR** · `PairwiseView.tsx:140-186` (`.align-summary`/`.align-metric`) vs `.crispr-summary`/`.cs-cell`
Problem: Align uses `.align-metric` cards (label-over-value, bordered, `tabular-nums`); CRISPR uses `.cs-cell` (label-left value-right, borderless grid). Same conceptual "summary stat row," two visual languages. Neither is wrong; they just don't match.
Fix: not a token fix — pick one summary primitive for all three tools. Align's `.align-metric` is the better-built one (tabular, bordered, toggle variant). FLAGGED (§3) — needs Steven's OK before unifying.
Why: cross-tool consistency; structural, so flagged not auto-applied.

*Align strengths: `tabular-nums` on the metric strip + diff counter, descriptive `title` on every metric, `role="alert"` on parse errors, `role="status"` on parsing, `aria-label` on nav arrows, `.align-read-btn.remove` hover→`--err`, chromatogram controls gated to real `.ab1` traces, reduced-motion-safe overlay.*

---

### CROSS-TOOL

**[C1 · P1] `tabular-nums` applied in only 3 of N numeric surfaces** — see Primer P1 + CRISPR P1. The invariant ("scores/coords = mono **tabular**") is met in Align's metric strip and nowhere else. One sweep: add `font-variant-numeric: tabular-nums` to `.tool-table td.num`, `.cs-v`, `.primer-strand-m`, `.primer-product`, `.primer-dtm`, `.primer-kv dd`. Pure token-class addition.

**[C2 · P1] PAM has two contradictory treatments** — ribbon (saturated) vs table (pale tint). Unify on the saturated ribbon style (CRISPR P0). After the fix, PAM reads identically in the table, the `GuideTrack`, and the off-target rows (`.g-pam` is shared by all three).

**[C3 · P1] Three separate sequence renderers, one base palette — verify parity.** `--base-*` is correctly consumed by: `.g-nt.{A,T,C,G}` (CRISPR table `3222-3225`), `.align-base-legend .abl` (`2165-2168`), `.align-trace-channel` (`2397-2400`), `.chromatogram-ref/letter` (`2780-2824`). **All four use the shared tokens — this is a pass.** The only base-colour gaps are the *highlight* layers (`.aln-band`, `.seq-hl-*`), covered by C4.

**[C4 · P2] Recurring raw hex across the Workbench, no token:** `#cbe3d8` (teal-soft border — Primer badge `3544`, `.align-read-btn.active` `2739`, `.ai-action` `1879`), `#3b4877`/`#e8eaf2` (indigo — `seq-hl-silent`, `ic-bar.predicted`, viewer oligo, splice conseq), `#7c5cd6` (het purple), the `.aln-band` rgba set, `#633806` (warn-text — but `--warn-text` *exists* at globals:75, so these should reference it). Single cleanup: route teal-soft → `color-mix(var(--teal) 28%)`, indigo → `--info-*`, het → named `--wb-het`, warn-text literals → `var(--warn-text)`.

**[C5 · P2] Result-card / summary shape differs three ways** — Primer `.primer-card` (3-layer disclosure), CRISPR `.crispr-summary`+two tables, Align `.align-read-card`+`.align-metric`. Token grammar matches (fonts, hairlines, `--bg-canvas`); the *component* shapes don't. Converging them is structural → FLAGGED (§3).

**[C6 · P2] Export affordance is consistent within Off-target but absent elsewhere** — `.ots-export-btn` (Copy/Download .tsv) is well-built (focus ring, teal hover, `title`). Primer has `Copy pair` (clipboard) but no download; CRISPR Design table has *no* export at all. Not a bug; note the asymmetry for a future "export" pattern pass.

---

## 3. 🟡 FLAGGED — needs Steven's OK (durable / structural / layout)

1. **Unify the summary-stat primitive across all three tools** (CRISPR `.cs-cell` → adopt Align's `.align-metric`, or vice-versa). Changes the look of the CRISPR candidate/off-target summaries. (C5 / Align P2.)
2. **Unify the result-card shape** — i.e. give CRISPR guides and Align reads the Primer 3-layer progressive-disclosure card. Large refactor; per DESIGN.md adoption note ("each its own gated pass — do not retro-restyle shipped panels without an explicit milestone"). (C5.)
3. **Sticky `thead` on `.tool-table`** (CRISPR P1) — visually durable (header gains a background band on scroll). Low-risk but persistent; confirm before shipping.
4. **Custom orientation listbox** to render the orientation glyph via Icon.tsx instead of a native `<select>` (Align P2) — replaces a native control; defer unless Steven wants it.
5. **New Workbench colour tokens** (`--wb-het`, optional `--wb-find`) vs re-pointing to `--info-*` — introducing named tokens is a design-system change; pick the re-point unless a distinct hue is required.

---

## 4. Quick wins (token-only, safe to ship now)

| # | Fix | File:line | Change |
|---|-----|-----------|--------|
| Q1 | Tabular figures sweep | css `1922`,`3207`,`3588-3610` + `.primer-kv dd` | add `font-variant-numeric: tabular-nums;` to `.tool-table td.num`, `.cs-v`, `.primer-strand-m`, `.primer-product`, `.primer-dtm`, `.primer-kv dd` (C1 / Primer P1 / CRISPR P1) |
| Q2 | Table PAM → ribbon parity | css `3213-3217` | `bg: var(--warn-bdr); color: var(--warn-text); box-shadow: inset 0 0 0 .5px var(--warn);` drop border (CRISPR P0) |
| Q3 | Self-balancing candidate summary | css `3192` | `grid-template-columns: repeat(auto-fit, minmax(150px,1fr));` (CRISPR P1) |
| Q4 | Mismatch ring | css `3259-3264` | `.g-nt.mm { box-shadow: inset 0 0 0 1.5px var(--ink-3); border-radius:2px; font-weight:800; }` (CRISPR P1) |
| Q5 | Primer badge borders → tokens | css `3544`,`3552` | teal border → `color-mix(in oklab, var(--teal) 28%, transparent)`; err border → `var(--cls-path-bdr)` (Primer P2) |
| Q6 | warn-text literals → token | css `1991`,`3548` | replace `#633806` with `var(--warn-text)` (C4) |
| Q7 | Indigo → `--info-*` | css `1990`,`3420` | `.seq-hl-silent` bg→`var(--info-bg)` text→`var(--info-text)`; `.ic-bar.predicted` fill→`var(--info-dot)` (CRISPR P2 / C4) |
| Q8 | `.aln-band` rgba → token mixes | css `2772-2776` | mismatch→`color-mix(var(--err) 18%)`, gap→`color-mix(var(--warn) 14%)`, active fill→`color-mix(var(--teal) 18%)` (Align P1) |

Q9 (slightly more than token but trivial): het non-colour cue — add a 1px dashed top edge to `.chromatogram-het` (Align P1, the a11y half; the token-naming half is FLAGGED #5).

---

### Notes / non-issues (so they aren't "fixed")
- `★` recommended glyph (Primer/CRISPR) is the one DESIGN.md-sanctioned text mark with `sr-only` backup — keep.
- `.sv-export-backdrop` uses `backdrop-filter: blur(2px)` (`workbench.css:1136`) — DESIGN.md bans blur on **sticky/overlay** chrome for keystroke repaint; a one-shot export *modal* backdrop is the edge case, but it's worth a glance since the rule is worded broadly. Owned by the viewer/export surface, **out of this lane** — noted only.
- Off-target enumeration, sort, and primer-design buttons all `disabled={loading}` / `disabled={…length===0}` with inline reason text — **[UPM Loading-Buttons, Severity High]** satisfied.
