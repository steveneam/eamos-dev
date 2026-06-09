# Workbench Primer & CRISPR — Design Audit (`/workbench`)

> **Status:** 🟡 AUDIT — review-gated. No code lands until Steven OKs the §5 recommendations
> ([[feedback_subagent_recommendations_not_authorization]]). Lane 2 of the 2026-06-09 4-scout
> workbench audit (frontend-design + ui-ux-pro-max). Persisted by the main agent.

Surface: `/workbench` tool panels. Files: `components/workbench/primer/**`, `components/workbench/crispr/**`, styles `workbench.css`, tokens `globals.css`. Skills: `frontend-design` + `ui-ux-pro-max` `--domain ux|chart` (cited inline as **[UPM]**). Prior art: `docs/workbench-report-sweep/workbench-tools.md`.

**Staleness note vs the prior sweep (important):** most of that sweep's token-only "quick wins" have since shipped. Verified against current source: table PAM is now ribbon-parity (`workbench.css:3230-3234`), the mismatch cue is a ring not an underline (`3278-3282`), `.tool-table td.num` + `.cs-v` carry `tabular-nums` (`1942`, `3224`), and `.crispr-summary` is self-balancing `auto-fit minmax(150px,1fr)` (`3209`). So the old P0/P1 numeric+PAM+orphan findings are **closed**. This audit covers what remains, plus the owner's "purpose-or-remove every interactable + half-width legibility" lens.

---

## 1. Snapshot

**Primer** is a genuinely Benchling-grade panel: a tight 5-field constraint form, one teal primary CTA, an honest 3-phase loading list, and a result *feed* of 3-layer progressive-disclosure cards. Every control has a `title`, the tooltip is a real focusable ARIA pattern, and the badge taxonomy (`primer-metrics.ts:48-79`) is a clean 4-state verdict. This is the reference the rest of the Workbench should converge toward — leave its structure alone; only small gaps remain.

**CRISPR** is three sub-tabs (Design / Off-targets / Outcomes) and is the dense, divergent surface. Functionally rich and accessibility-aware (pinned on-target row, per-`<th>` tooltips, `aria-label` sort buttons, focus rings) but it carries the workbench's hardest legibility problem and several controls that fail a "what does a real user do with this?" test.

**The 3 biggest problems vs the Apple/Benchling bar:**

1. **The off-target table is a 10-column, `min-width: 920px` grid (`workbench.css:3188`) with no sticky header.** On a long filtered list the `thead` scrolls out of view; narrow it (or the planned 3-column output) and it horizontal-scrolls. **[UPM Responsive/Table-Handling]** overflow is satisfied; header legibility is not.
2. **Score interpretability is weak and inconsistent.** On-target (0–100), off-target/CFD (0–1) and GC scores are bare numbers coloured good/mid/bad with **colour + font-weight only** (`workbench.css:1944-1946`) — no bar, no scale, no threshold marker. A user can't tell *how* good `74.3` is without the hidden 60/75 breakpoints (`DesignTab.tsx:72-74`). **[UPM Charts/Performance-vs-Target]** + **[UPM Color-Only, High]**. Two different score scales are rendered identically.
3. **Several controls are non-functional, disabled-forever, or duplicate state** — the Design "Target window: server-resolved" read-only faux-input, the SaCas9/Cas12a options that exist only to be disabled, the duplicated mismatch control (search `Max mismatches` vs curate `Max mm`), and the Outcomes tab whose three caveats say "this isn't real yet."

---

## 2. Interactable inventory + verdict table

### PRIMER — `primer/PrimerPanel.tsx` + `primer/PrimerResultCard.tsx`

| Element | file:line | Purpose | Verdict | What to do |
|---|---|---|---|---|
| Mode segmented (Sanger / qPCR / ARMS) | `PrimerPanel.tsx:138-153` | Pick primer chemistry; each has a real `tip` | **KEEP** | ARMS honestly empty-stated (`267-272`). |
| Tm min / Tm max (°C) inputs | `PrimerPanel.tsx:157-185` | Tm bounds | **KEEP** | Correct number inputs; consider a paired "Tm window" later (§5). |
| Product min / max (bp) inputs | `PrimerPanel.tsx:186-211` | Amplicon bounds | **KEEP** | Good. |
| Avoid SNPs select (Yes/No) | `PrimerPanel.tsx:212-229` | Toggle 3′ SNP avoidance | **IMPROVE** | A boolean Yes/No `<select>` is heavier than the choice — make it a checkbox/2-segment toggle. |
| Generate & validate (CTA) | `PrimerPanel.tsx:233-241` | Run design | **KEEP** | Exemplary: `disabled={loading}`, label flips, strong `title`. |
| Loading phase pills | `PrimerPanel.tsx:247-256` | Honest single-pending state | **KEEP** | DESIGN.md #4 done right. |
| Verdict badge / ★ recommended / Copy / F-R select / audit disclosure / `?` tips | `PrimerResultCard.tsx:86-264` | Result card | **KEEP** | Reference-grade ARIA + progressive disclosure. Do not convert ★ to an Icon (sanctioned text mark). |

**Primer verdict: structurally complete and best-in-class.** Only `Avoid SNPs` is a real control IMPROVE; the rest are *content* gaps (§3/§4): no self/hetero-dimer surfaced, no primer start-position, no download.

### CRISPR — Design (`crispr/DesignTab.tsx`)

| Element | file:line | Purpose | Verdict | What to do |
|---|---|---|---|---|
| Sub-tab control (Design/Off-targets/Outcomes) | `CrisprPanel.tsx:41-69` | Switch CRISPR mode | **IMPROVE** | No `title` on the three tabs (Primer's mode tabs all have one). Add one-line `title`s so the workflow reads design→screen→confirm. |
| Cas enzyme select (SpCas9 / SaCas9✗ / Cas12a✗) | `DesignTab.tsx:232-251` | Choose nuclease | **IMPROVE / partial REMOVE** | Two of three options are permanently `disabled` and `onChange` ignores non-SpCas9 (`240`). Collapse to a single "SpCas9 · NGG" chip + "more enzymes coming", or move the unavailable note onto each option's `title` (drop the 2 redundant `help-note` lines `322-326`). |
| Strand select (Both/Plus/Minus) | `DesignTab.tsx:252-269` | Filter guide strand | **KEEP** | Real, sensible default. |
| Off-target tolerance number (0–5) | `DesignTab.tsx:270-287` | Mismatch budget | **KEEP** | Clamped, `title`. |
| **Target window** "server-resolved" (disabled input) | `DesignTab.tsx:288-297` | — (shows a fixed string) | **REMOVE** | A disabled input that only ever displays `"server-resolved"`. Looks interactive, isn't (**[UPM Input-Affordance]** inverted). Replace with a plain caption or fold into the `help-note` at `444-447`. |
| Design SpCas9 guides (CTA) | `DesignTab.tsx:301-308` | Run design | **IMPROVE** | Good behaviour but **no `title`** (every other CTA has one). Add it. |
| Sort segmented (Default / On-target high / Off-target low) | `DesignTab.tsx:397-425` | Reorder guides | **KEEP** | `title`+`aria-label` each. |
| Min on-target range slider | `DesignTab.tsx:426-441` | Filter weak guides | **IMPROVE** | `step=5` slider is imprecise for an exact threshold; show "All" at 0 (not `>= 0`). Consider number+slider pair. |
| Candidate-summary cells / guide rows / 20-mer+PAM / GuideTrack ribbon | `DesignTab.tsx:352-512`, `GuideTrack.tsx` | Roll-up, inspect, map | **KEEP** | Self-balancing grid, focusable rows, `--base-*` + saturated PAM, `role="img"` ribbon. Solid. |
| On/Off/GC score cells | `DesignTab.tsx:499-505` | Per-guide scores | **IMPROVE** | Colour+weight only ([L2]). GC% has **no** good/mid/bad class (`505`) — reads flat even out of the 40–70 band. |
| ssODN three-arm visual | `DesignTab.tsx:544-592` | Show HDR edits | **IMPROVE** | Strong concept; the "silent PAM-blocking edit" highlight uses **raw indigo hex** (`workbench.css:2007`) off-token ([L4]). Add a one-line "why this appears" intro. |

### CRISPR — Off-targets (`crispr/OffTargetTab.tsx`)

| Element | file:line | Purpose | Verdict | What to do |
|---|---|---|---|---|
| Guide protospacer input / PAM input | `OffTargetTab.tsx:327-354` | Seed the search | **KEEP** | Validates 17–20 nt; mono; `spellCheck=false`. |
| **Max mismatches** number (0–4) | `OffTargetTab.tsx:355-369` | *Search* radius | **IMPROVE (dedupe)** | There is a **second** "Max mm" in the curate bar (`537-549`) that *filters*. Two near-identical controls named almost the same thing is the panel's biggest confusion. Rename "Search ≤ N" vs "Show ≤ N", or merge. |
| On-target chr / pos / strand | `OffTargetTab.tsx:370-412` | Anchor the locus | **KEEP / group** | Could be one "chr:pos (±)" compound field later (§5). |
| Enumerate off-targets (CTA) / Sort / Top-N / Auto-pick / Max-mm filter / Coding-only / row checkboxes / pinned on-target row / 20-mer+ring / export TSV / flank / name-prefix / design-primers CTA / screening-primer table / export panel | `OffTargetTab.tsx:416-797` | Screen + curate + export | **KEEP** (mostly) | Bulk-action pattern done right; pinned on-target anchor excellent; TSV export Benchling-grade. **BUG:** the `<th>` `title` still says bases "are underlined" (`576`) — it's now a *ring* ([L5]). Add `sr-only` to the screening table's ★ (`758`). |
| Score / MM / Biotype / Locus cells | `OffTargetTab.tsx:621-643` | Per-site detail | **IMPROVE** | Score colour-only ([L2]); biotype chip good. |

### CRISPR — Outcomes (`crispr/OutcomesTab.tsx`)

| Element | file:line | Purpose | Verdict | What to do |
|---|---|---|---|---|
| Control / Edited trace file inputs (.ab1/JSON) | `OutcomesTab.tsx:54-79` | Upload baseline + edited | **IMPROVE** | Raw native `<input type=file>` (`.crispr-file`) — the OS button breaks the clinical surface. Reuse Align's styled `align-file-btn` label pattern. |
| Cas9 cleavage base index / Analyze CTA / result stats | `OutcomesTab.tsx:80-150` | Run TIDE + roll-up | **IMPROVE** | Analyze CTA has no `title`; add one. |
| IndelSpectrum chart | `IndelSpectrum.tsx` | Observed (±predicted) indels | **IMPROVE** | (a) no empty-data branch (`28-35`) — render a "no data" message; (b) predicted series uses **raw indigo `#3b4877`** (`3438`) off-token. |
| Whole **Outcomes tab** | `OutcomesTab.tsx` | Post-edit QC | **🟡 KEEP-but-question (§5)** | Three stacked caveats (`113-125`) effectively say "sample/fallback, not a real TIDE solve." A tab that disclaims itself is a credibility cost — gate behind real backend TIDE, or brand "Preview." Steven's call. |

---

## 3. Legibility / visual-hierarchy findings

**[L1 · High] Off-target table has no sticky header** · `workbench.css:1914-1924`, wrap `3183-3189`. `min-width:920px` in `overflow-x:auto`, no `position:sticky` on `.tool-table thead th`. Fix (token-only): `thead th { position: sticky; top: 0; background: var(--bg-soft); }` (the th already has that bg). **[UPM Table-Handling]**.

**[L2 · High] Scores are colour-only for magnitude** · `workbench.css:1944-1946` (`.score-good/mid/bad` = colour + weight, no shape), `DesignTab.tsx:499,502`, `OffTargetTab.tsx:622`. No one can read "how good" without the hidden 60/75 / 0.05/0.2 breakpoints. **[UPM Color-Only High]** + **[UPM Performance-vs-Target]**. Min fix: a tiny inline micro-bar/bullet behind the number so magnitude is non-colour. GC% (`DesignTab.tsx:505`) has *no* class — add `score-*` keyed to 40–70. Bigger fix §5.

**[L3 · Medium] Two score scales presented identically** · Design on-target 0–100 vs CFD 0–1, same palette, nothing tells the user they differ. Fix: range in the visible header — "On-target (0–100)" / "Score (CFD 0–1)".

**[L4 · Medium] Raw indigo hex, three places** · `workbench.css:2007` (`.seq-hl-silent`), `3419` (`.sw.silent/.predicted`), `3438` (`.ic-bar.predicted`) all `#3b4877`/`#e8eaf2`. Re-point to the existing CVD-checked `--info-bg`/`--info-text`/`--info-dot` (`globals.css:115-118`).

**[L5 · Medium] Stale "underlined" copy** · `OffTargetTab.tsx:576` `<th>` `title` says mismatches "are underlined" — impl is now a *ring* (`workbench.css:3278-3282`). Copy bug.

**[L6/L7 · Low] Non-issues** · seq/name cells correctly NOT tabular (letters) — don't add it in a future sweep; `.seq-hl-pam` already uses `--warn-*` (prior C4 closed).

---

## 4. Flow + eye-guidance (Apple-like seamlessness)

**Primer — already seamless; two refinements.** Form → CTA → phase pills → result feed reads cleanly; the recommended pair gets a teal tint so the eye lands first. Gap: a PCR user scans for **self/hetero-dimer + 3′-complementarity** and **primer start position** (Primer3 computes them, the card never shows them). Add a "Dimers: none / flagged" line to Layer 3. (Content, not a control.)

**CRISPR Design — make the workflow legible as a path.** The three sub-tabs read as flat siblings; give them `title`s + a subtle "1 Design → 2 Screen → 3 Confirm" ordinal hint. **Highest-leverage flow fix: a "Screen this guide for off-targets" action on the recommended guide row** that deep-links the spacer into the Off-targets protospacer field — today the user hand-copies a 20-mer between tabs. That one bridge makes the panel feel like one tool. Drop the faux `Target window` input that interrupts the form right before the CTA.

**CRISPR Off-targets — reduce the two-mismatch confusion + protect the header.** The search form then a curate bar that re-introduces a mismatch control reads like two filter systems; disambiguate search-vs-view. Sticky header ([L1]) is the biggest "legible at width" win. The pinned on-target row + ringed mismatches are excellent — keep.

**CRISPR Outcomes — commit or preview.** The tab opens with three disclaimers before any result; gate it until real TIDE, or brand "Preview" once at top. The styled file-picker fix removes the one overtly "unfinished" tell.

---

## 5. 🟡 Durable / structural recommendations (gated) — ranked by leverage

1. **Bridge Design → Off-targets (deep-link the recommended spacer).** Highest leverage for "seamless." A per-row "Screen off-targets" action that switches `CrisprPanel` to the Off-targets tab and pre-fills `guide`/`pam`/locus. Turns three tabs into one workflow. *Structural (cross-tab state).*
2. **Real score cells (bullet/threshold, not colour-only numbers).** Replace `score-good/mid/bad` text colour with a compact bullet cell (number + thin track + labelled good/mid/bad zone). Apply to On-target, CFD, GC%. Fixes [L2]+[L3]. **[UPM Bullet-Chart AAA]**. *Durable visual across both CRISPR tables.*
3. **Sticky `.tool-table thead`** ([L1]). Token-only, low-risk, but a visible scroll change — benefits every Workbench table.
4. **Resolve the Cas-enzyme control.** Collapse to a single "SpCas9 · NGG" chip (drop the 2 disabled options + 2 caveat lines), or move "unavailable" onto each option. Clearest purpose-or-remove failure in Design.
5. **De-duplicate the two mismatch controls** in Off-targets (search vs filter). Merge or rename unmistakably.
6. **Gate or "Preview"-brand the Outcomes tab** (coordinate with Codex on the TIDE contract).
7. **Styled file-picker for Outcomes** (reuse Align's `align-file-btn`). Low-risk.
8. **Compound locus / Tm-window inputs** (optional density polish; defer).

### Non-issues (so they aren't "fixed")
★ recommended glyph (sanctioned text mark — keep, add `sr-only` on the screening ★); `td.num`/`.cs-v`/primer metrics already tabular (C1 closed); table+ribbon PAM at parity (P0 closed); mismatch ring non-colour-redundant (P1 closed, only [L5] copy stale); all CTAs gate on `disabled={loading}` (**[UPM Submit-Feedback]** satisfied).

**Bottom line:** Primer is at the bar — leave it, add dimer/position content. CRISPR needs (1) the Design→Off-targets bridge, (2) interpretable score cells, (3) a sticky header, (4) removal/dedup of the faux `Target window`, the disabled-only enzymes, and the doubled mismatch control.
