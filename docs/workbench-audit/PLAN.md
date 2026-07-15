# Workbench audit — synthesis + sequencing plan

> **Status:** 🟡 AUDIT SYNTHESIS — review-gated. Nothing ships until Steven picks from §4.
> 2026-06-09 4-scout audit (Steven-directed): "Benchling-grade, Apple-like — audit every
> interactable for purpose-or-remove + improve; the gene view is hard to see vs Benchling;
> further optimise Task A." Lanes: [gene-viewer](gene-viewer.md) · [primer-crispr](primer-crispr.md)
> · [align](align.md) · [shell-flow](shell-flow.md). Method: direct source reads +
> frontend-design + ui-ux-pro-max, every finding grounded in `file:line` + the token to use.

## Headline

Both the viewer and the tools are **structurally strong and largely token-disciplined** — real selection/edit model, honest per-base positioning, progressive-disclosure cards, one shared rail, a shipped `--z-*` scale, the `--cls-*`/`--base-*` palettes mostly respected. **No rendered control is purposeless-and-removable** (the tools are lean); the gaps are **legibility, discoverability, flow, and ~600 lines of orphaned/dead chrome**. The single biggest lever is the **flow** (tool sits *below* the viewer, not beside it) — exactly what Task A's 3-col layout fixes — followed by the **gene-view legibility** Steven called out directly.

## Cross-cutting themes (recur across 2+ lanes — fix once, benefits everywhere)

1. **Flow: the tool sits below the viewer, so the eye never reads context → see → act.** `.tool-panels` stacks under `.viewer` (`WorkbenchShell.tsx:286`); on Primer/CRISPR the form is below the fold. **Task A's 3-col grid is the #1 structural fix** (gene-viewer §4 + shell-flow §1/§3). Both gated specs are validated; shell-flow §4 answers every open question.
2. **The answer/queried-variant is under-emphasised — make it the loudest thing.** The sequence-grid variant pin is a 0.5px one-row hairline (`CodonDetail.tsx:529`, contradicts DESIGN.md:586 "pin through all tracks"); the Align result card has no lede stating "96.2% identity · 1 diff at ref 412." Promote the answer (gene-viewer §3-A, align §4-F1).
3. **Power features hide behind hover/handles — make them persistent.** Viewer zoom is hover-only (`.sv-zoom-overlay-seq`), Align trace-scale hides behind a 22px handle, single-base edit is right-click-only, CRISPR score thresholds are invisible. The in-repo `.chromatogram-toggle` (always-visible) is the precedent to mirror. **[UPM hover-vs-tap Critical]**.
4. **Score/chart legibility: colour-only magnitude + legend-less/axis-less charts.** CRISPR On/Off/CFD/GC are colour+weight only with hidden thresholds (`workbench.css:1944`); the conservation track, the Align trace, and the indel chart have no axis/legend; the protein lollipops + Align het marker encode by hue alone. Converge on a **bullet cell** (value + thin track + labelled zone) + always-visible legends/axes. **[UPM bullet-chart AAA / color-only High]**.
5. **Legibility floor.** Base grid is 13px at a 14px default (Benchling ~16px); ruler/AA/minimap labels dip to 8.5–9.5px; `tabular-nums` missing on several figures (`ctx-var`, exon table, viewer counts). Raise the floor.
6. **Dead/orphan chrome + raw-hex off-token (~600 lines).** ~540 lines dead Align CSS (`workbench.css:2475-2672`), the CSS-ghost `.ai-pill`/`.ai-panel`, the retired `.zoom-pill`, the no-op `SidePanel` collapse button (+ unreachable stub + no-op handler), the dead `TOOL_META.compare`/`ToolIcon` case; raw indigo `#3b4877` ×4 → `--info-*`, het `#7c5cd6` → `--info-dot`/`--wb-het`, find-gold → `--warn` mix, minimap/exon/oligo creams → `--track-*`.
7. **Label honesty / faux controls.** Align state-vs-action toggles ("Full read"/"Q-trim"), the CRISPR `Target window: server-resolved` faux-input, the Cas-enzyme select with one selectable option, the Outcomes tab that disclaims itself, the doubled Off-targets mismatch control.
8. **A11y debt.** Colour-only encodings (#4), reduced-motion gaps (Align smooth-scroll + spinner unguarded), no sticky table/coordinate headers, sub-AA type.
9. **DESIGN.md `559-571` is stale** — still documents a vertical `<ToolRail/>`, `<TopNav/>`, bottom-right `<AskEamosPill/>`, `64px 1fr 360px` grid that match neither the shipped tree nor Task A. Reconcile when Task A lands.

## §3. Two buckets

### 🟢 Safe batch (token / dead-code / copy / a11y — low-risk; could ship as ONE gated pass)
- **tabular-nums sweep** — `.ctx-var`, `.ex-num/-range/-bp/-var`, `.sv-vnav-count`/`.sv-hist-count`/`.sv-block-pos`, ruler ticks.
- **sticky `.tool-table thead`** (`position:sticky;top:0;background:var(--bg-soft)` — bg already present) — every Workbench table.
- **raw-hex → tokens** — `#3b4877`/`#e8eaf2` (silent/predicted ×4) → `--info-*`; het `#7c5cd6` → `--info-dot` or a named `--wb-het`; find-gold → `color-mix(--warn)`; minimap/exon/oligo creams → `--track-*`.
- **reduced-motion guard** — gate Align `behavior:'smooth'` (`AlignedTrace.tsx:113`) + the `align-spin` spinner.
- **type floor** — secondary mono labels → 10px; coordinate labels → `--ink-3`.
- **stale copy** — off-target `<th>` "underlined" → "ringed" (`OffTargetTab.tsx:576`).
- **missing affordances** — `title` on CRISPR sub-tabs + Design/Outcomes CTAs; `sr-only` on the screening ★; empty-state + axis/legend on conservation + indel charts.
- **dead-code deletion (bigger, pure removal)** — `.zoom-pill`, `.ai-pill`/`.ai-panel`, ~540 dead Align CSS lines, the no-op `SidePanel` collapse block + props, `TOOL_META.compare`/`ToolIcon` case. *(Pre-existing dead code → flagged-not-auto-deleted per CLAUDE.md; needs an explicit "yes, sweep it.")*

### 🟡 Durable / structural (gated — each its own verified pass), ranked by leverage
1. **Task A — 3-col layout** (controls | viewer | tool-rail) + **bottom-left cluster** (account + COMING-SOON Ask + Cite/Feedback relocation). The #1 flow fix. Ship the chrome-foot cluster first (lower-risk, no canvas restructure), then the 3-col grid (Option C). Open Qs answered in shell-flow §4.
2. **Queried-variant pin → full-canvas anchor** (gene-viewer §3-A) — the top "hard to see" miss; borrow `FullLocusViewer`'s row-inset+tint.
3. **Larger default base size + persistent zoom** (gene-viewer §3-B/C) — the direct answer to "gene view hard to see vs Benchling."
4. **Score bullet cells** (CRISPR On/Off/CFD/GC) — interpretable-at-a-glance; shared primitive.
5. **Align result-card 3-tier hierarchy** (lede → strip → details) + **cross-tool result-card convergence** (Primer is the reference).
6. **CRISPR Design → Off-targets bridge** — deep-link the recommended spacer; turns three tabs into one workflow.
7. **Sticky coordinate strip** in the sequence scroll box (gene-viewer §3-D).
8. **Single-base Edit affordance** (not right-click-only) (gene-viewer §3-E).
9. **Align trace coordinate ruler** (align §3-L2).
10. **Resolve faux/dead controls** — Cas-enzyme select, `Target window` faux-input, doubled mismatch control, Outcomes gate/preview.
11. **Protein-view + conservation legends** (colour→class key + PhyloP scale).
12. **FullLocus "Full gene" parity** (today drops to monochrome non-interactive bases behind a peer toggle).
13. **Reconcile DESIGN.md** with the shipped + Task-A shell.

## §4. Decisions for Steven (the menu)

- **A. Greenlight Task A?** (the 3-col layout + bottom-left cluster) — the biggest flow upgrade. Recommended order: chrome-foot cluster first, then 3-col. Both gated specs are now validated with answered open questions.
- **B. Greenlight the gene-view legibility trio** (pin anchor + larger default base/persistent zoom + sticky coord strip) — directly answers your "hard to see vs Benchling."
- **C. Greenlight the 🟢 safe batch** (token/a11y/copy + the dead-code sweep) as one low-risk pass.
- **D. Greenlight the interpretability set** (score bullet cells + Align card lede + Design→Off-target bridge).
- **E. Anything to drop?** No interactable was found purposeless-and-removable, but several are faux/disabled-forever (Cas-enzyme, Target-window) or self-disclaiming (Outcomes) — confirm collapse-vs-keep.

**Recommended sequence:** C (safe batch, immediate lift) → B (the "hard to see" complaint) → A (flow) → D (interpretability) → remaining polish. Each durable item ships as its own gated, browser-verified pass.
