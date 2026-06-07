# Eamos `/report` v3 redesign — DESIGN (UI/UX)

> Companion to `spec.md` (source of truth). This file fixes **concrete token
> values, spacing, type, microcopy, and reduced-motion-safe interactions** so
> the implementation pass (`plan.md`) can build without re-deciding design.
>
> **Fidelity rule:** this is a *refinement of the existing warm-paper / teal /
> Spectral system*, NOT a new aesthetic. Every value below is an existing
> `globals.css` token or an existing component pattern (`.eamos-kicker`,
> `.v-tool`, `.v-jump-chip`, `ClassificationBadge`, the `GNOMAD_AF_BANDS`
> model, the `STATE_THEME`/`--cls-*` ramp). No new colours, no new fonts, no
> raw `box-shadow`, no weight > 700, hairlines stay 0.5px.
>
> **Design-intelligence citations** (ui-ux-pro-max, folded in below):
> - **Accessibility · "Color Only"** (severity High) — *never convey info by
>   colour alone; pair colour with icon/text.* Drives every card, chip, and
>   thermometer here: colour is **always** doubled by a text verdict word.
> - **Interaction · "Hover States"** + **Animation · "Hover vs Tap"** (High) —
>   *don't rely only on hover for important actions; critical info must be
>   keyboard/tap-reachable.* Drives the tooltip pass: `title` + `aria-label` on
>   every control, and any decision-load-bearing fact also lives in visible text.
> - **Chart · "Gauge / Bullet Chart"** (AAA a11y) — *single KPI vs threshold;
>   numeric value always visible as text, never colour-position alone; target =
>   a marker line; qualitative ranges labelled with threshold text.* Drives the
>   §3 AF thermometer and the constraint readout.
> - **Feedback · "Loading Indicators"** — drives the LazySection skeletons stay.

---

## 0. Token vocabulary used (all pre-existing)

| Role | Token(s) |
| ---- | -------- |
| Page / card surface | `--bg-soft` (body), `--bg` (card), `--bg-soft2` (recessed) |
| Hairline | `--line` (0.5px), `--line-2`, `--line-3` |
| Ink ramp | `--ink` · `--ink-2` · `--ink-3` · `--ink-4` · `--ink-5` |
| Brand | `--teal` · `--teal-deep` · `--teal-tint` · `--teal-bdr` |
| Status | `--warn` · `--warn-text` · `--warn-tint` · `--warn-bdr` · `--err` |
| Classification ramp | `--cls-path-*` → `--cls-lpath-*` → `--cls-vus-*` → `--cls-lben-*` → `--cls-ben-*`; `--cls-na-*` = unresolved/NA (grey, **never a tier**) |
| Off-ramp info | `--info-bg / -text / -bdr / -dot` (blue — "uncurated / context") |
| AF bands | `GNOMAD_AF_BANDS` (BA1 ≥5% green `#1aa06d` · BS1 1–5% mint `#93d6b3` · 0.1–1% amber `#e0a23a` · PM2 <0.1% red `#dc5b4f`) |
| Type | `--display` (Spectral, **heading-only**) · `--body` (Inter) · `--mono` (JetBrains, HGVS/coords/scores) |
| Radii | `--r-sm` 6 · `--r-md` 10 · `--r-lg` 14; pills 100px |
| Elevation | `--elev-1` rest · `--elev-2` hover · `--elev-3` overlay |
| Motion | `--dur-1` 120 · `--dur-2` 200 · `--dur-3` 320; `--ease-standard` · `--ease-emphasized` · `--ease-exit` |
| Focus ring | `box-shadow: 0 0 0 3px rgba(29,158,117,0.14)` + `border-color: var(--teal)` |

Reused class primitives: `.eamos-kicker`, `.v-tool`, `.v-jump-chip`,
`.call-card-btn`, `ClassificationBadge` (the `cb`/`cb-dot` chip).

Page column stays **920px** (load-bearing for hairline density). Cards
`gap: 18px`. Nothing below widens the column.

---

## 1. The 4-card full-colour system (`CallCardsGrid`)

Today only `lab_functional` is themed (via `STATE_THEME` keyed on
`ui_color_theme`). v3 extends the **same mechanism** to all four cards. No new
colour primitives — every state maps onto the existing `--cls-*` ramp + `--info-*`
+ `--cls-na-*` grey already used by `STATE_THEME`.

### 1.1 How each axis reads its verdict-state

Each card exposes a `verdict_state` (string enum, identical keys to the existing
`STATE_THEME`) derived per axis. **Backend supplies it where it can; FE derives
mock-first otherwise and tags the card with the §3 "needs live data" marker.**

| Card (L→R) | verdict-state source | maps to ramp tier |
| ---------- | -------------------- | ----------------- |
| **Computational** | calibrated damaging↔benign call (consensus of in-silico table) | damaging → `--cls-path-*`/`--cls-lpath-*`; ambiguous → `--cls-vus-*`; tolerated → `--cls-lben-*`/`--cls-ben-*`; no engines → `--cls-na-*` |
| **Clinical** | ACMG/ClinGen/ClinVar classification (P/LP/VUS/LB/B) | direct 1:1 onto `--cls-{path,lpath,vus,lben,ben}-*`; conflicting → `--cls-na-*` grey (per DESIGN mandate) |
| **Population** | AF-class band (the **same** `GNOMAD_AF_BANDS` model as §3) | BA1/BS1 → `--cls-ben-*` (benign); 0.1–1% intermediate → `--cls-vus-*` (yellow); PM2 <0.1% → `--cls-lpath-*` (path-leaning); not-observed → `--cls-na-*` |
| **Lab & Functional** | existing functional STATE (`STATE_THEME` as shipped) | unchanged: red/lpath/vus/ben + `--info-*` uncurated + `--cls-na-*` none |

> **Population note:** PM2 is *supporting*, so it leans **`--cls-lpath`** (orange),
> not full `--cls-path` red — absence is suggestive, not diagnostic. This is the
> honest mapping and matches the §3 thermometer's own restraint.

### 1.2 Resting card treatment per state (the full-colour surface)

Reuse `STATE_THEME`'s exact recipe — tint bg, ramp border, ramp text — now
applied to **all four** cards, not just functional. Per card:

```
border:        0.5px solid var(--cls-{tier}-bdr)
background:    var(--cls-{tier}-bg)
title ink:     var(--cls-{tier}-text)   /* the .eamos-kicker, tinted to match */
primary label: var(--ink)               /* stays near-black for max legibility on the pale tint */
box-shadow:    var(--elev-1)
border-radius: 10px        padding: 15px 16px      min-height: 158px
```

On a tinted card the **badges become crisp chips on `var(--bg)` white** (exactly
the existing functional-card rule): verdict chip keeps the tier `border` + `text`;
the rest go neutral (`--line` border, `--ink-2`). This keeps badge legibility on
the pale wash and is already proven in code.

`--cls-na-*` (grey) cards read as honest "no data / conflicting" — never a false
green/red.

### 1.3 Colour-not-alone (ui-ux-pro-max "Color Only", High)

Every card states its verdict in **words**, never colour alone:
- **Title** (kicker): the axis name — "Computational", "Clinical", "Population",
  "Lab & Functional".
- **Primary label** (`--display` 18/600): the verdict in plain language —
  "Likely damaging", "Pathogenic · ClinGen", "Common (BA1, benign)", "Absent
  from gnomAD". This is the load-bearing fact; colour merely reinforces it.
- A **leading verdict dot** (`--cls-{tier}-dot`, 8px) sits before the title so
  CVD users get a shape+position anchor, mirroring `ExpertPanelSection`'s dot.

### 1.4 3-layer Dashboard Interaction Language (kept)

- **Layer 1** — verdict colour + dot + primary label (one glance).
- **Layer 2** — up-to-3 badges (calibrated score / criterion count / source).
- **Layer 3** — "View detail" navigates to the matching section (existing
  `scrollToInteraction`); interactive cards keep `--elev-1`→`--elev-2` hover,
  the teal focus ring, and the `:active` `scale(.985)` press.

Card order may be backend-driven (`report_call_cards`); FE re-sorts to the
locked L→R order if the contract disagrees.

---

## 2. The SLIM hero + expandable details disclosure

The current `variant-header-card` (28×32 padding, 36px gene title, full chip
strip, `.v-tools` row) is **too tall** for a "slim" read. v3 compresses the
*resting* bar and pushes the audit detail behind a disclosure.

### 2.1 Collapsed slim bar (always visible)

Target resting height **≈ 76–84px** (one line of identity + one action row), down
from the current ~150px+ block. Padding `16px 24px` (was `28px 32px`), card
radius stays `--r-lg`.

**Row 1 — identity (single line, wraps gracefully):**
```
[GENE]  c.260A>G        p.Asp87Gly      ● Likely pathogenic       4-segment strip ▸
 ↑display 26px/400      ↑mono 14/500     ↑ClassificationBadge      ↑see 2.3
 var(--ink)            var(--ink-3)       (dot+label, existing)
```
- Gene: `--display` **26px/400** (down from 36 — the slim register), `--ink`.
- DNA primary: `c.cdna` in `--mono` 14px/500 `--ink-2` — **DNA is primary**,
  protein recedes.
- Protein: `p.consequence` `--mono` 13px `--ink-4`, muted.
- Classification badge: existing `ClassificationBadge` (dot + word).

**Row 2 — actions + meta (right-aligned cluster, 32px tall):**
```
[ 1,204 views · updated 3 d ago ]ᵍʰᵒˢᵗ     [Save] [Export] [Share]   [Details ▸]
↑ §3 mock marker + tooltip                  ↑ .v-tool cluster (2.2)   ↑ disclosure toggle
```

Total: two compact rows. The **cross-DB "Open in" chip strip moves into the
expanded Details panel** (it is reference-jump, not glance-level) — this is the
single biggest slimming win.

### 2.2 Save / Export / Share cluster

Keep the existing `.v-tool` chip (icon + label, `--bg`/`--line`, hover →
`--bg-soft2` + `--ink-5`, teal focus ring, `:active` press). Three changes:
- **"Follow" → "Save"** (bookmark/plus icon). Wires to `saveVariant()` from
  `@/lib/variant-library` (the rail already uses it). Toggled state: label
  "Saved", `--teal-deep` text + `--teal-bdr` border + `--teal-tint` bg (the
  existing `.v-tool.followed` recipe, repurposed).
- **Export** unchanged (`ExportMenu` slot or `window.print()`).
- **Share** unchanged (copy-link, 2s "Copied" confirm — honest feedback).
- "Save" is the **primary** of the three (it persists state): give it the
  teal-tint active treatment; Export/Share stay ghost. One focal action per
  region (DESIGN principle #2).

### 2.3 The thin 4-segment colour strip (validated — keep)

A **4px-tall, 4-segment** horizontal strip in Row 1's right edge previews the
4 cards' verdict colours (Computational · Clinical · Population · Lab). Each
segment = `--cls-{tier}-dot` of that axis. Width ~88px (4 × 22px). It is a
**glance-level preview**, not interactive on its own, but the whole strip is a
button that scrolls to `#call-cards`.

- **Colour-not-alone:** `aria-label="Evidence at a glance: Computational
  likely-damaging, Clinical pathogenic, Population absent, Functional
  deficient"`, and each segment carries its own `title="Computational: likely
  damaging"`. A CVD user reads the words; the strip is decoration over text.
- Validation verdict: **ship it**. It is honest (mirrors real card states),
  tiny, and reinforces the "4 cards are the only top display" decision. Risk
  (looks like a meaningless rainbow) is mitigated by the per-segment tooltips
  and the ≤4% restraint — segments are the muted `dot` tier, not saturated.

### 2.4 Expanded Details disclosure

`<details>`/`<summary>` semantics, `--dur-2 ease-emphasized`, chevron rotates,
height via grid-rows (no layout-jank). Panel = `--bg-soft` inset, `--r-md`,
`14px 16px`, opens **inside** the hero card (no separate card).

Contents (a 2-col `auto / 1fr` `<dl>`, `--mono` values, `--ink-2`):

| dt (`--ink-4`) | dd (`--mono`, `--ink-2`) |
| --- | --- |
| Genomic (1-based) | `chr1:68,444,869` |
| VCF | `1-68444869-T-C` + `CopyButton` |
| HGVS c. | `NM_000329.3:c.260A>G` |
| HGVS p. | `NP_000320.1:p.(Asp87Gly)` |
| HGVS g. | `NC_000001.11:g.68444869T>C` |
| MANE transcript | `NM_000329.3 (MANE Select)` |
| Genome build | `GRCh38 / hg38` |
| rsID | `rs62637009` (links dbSNP) |
| Consequence | `missense_variant` |
| Open in | the existing `.v-jump-chip` strip (ClinVar · gnomAD · Ensembl · …) |

Each abbreviation (HGVS, MANE, VCF) carries a tooltip (see §7).

---

## 3. The "mock but needs live data" marker

A single, tasteful, consistent marker so **no placeholder ever reads as a real
number**. (spec locked decision #2.)

### 3.1 The visual — a "ghost chip"

A small inline chip rendered with a **dotted hairline** + a faint diagonal hatch
wash, deliberately distinct from every solid surface in the system:

```css
.eamos-mock {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 1px 7px;
  border: 1px dashed var(--ink-5);          /* dashed = "not final" signal */
  border-radius: 999px;
  background: repeating-linear-gradient(    /* ≤4% functional wash, sanctioned */
    45deg, transparent, transparent 5px,
    color-mix(in oklab, var(--ink-4) 6%, transparent) 5px,
    color-mix(in oklab, var(--ink-4) 6%, transparent 7px));
  color: var(--ink-4);
  font-family: var(--body); font-size: 10px; font-weight: 600;
  letter-spacing: 0.02em;
}
.eamos-mock::before { content: ''; width: 5px; height: 5px; border-radius: 999px;
  border: 1px dashed var(--ink-4); }   /* hollow dotted dot — shape cue, not colour */
```

Two forms:
- **Inline value form** — the mock number renders at `opacity: .72` immediately
  followed by the chip: `1,204 views ⟨needs live data⟩`.
- **Standalone form** — when the whole metric is absent: just the chip reading
  `Needs live data`.

It is **monochrome** (ink-4, no colour) on purpose: it must never compete with a
verdict colour, and it reads identically under CVD.

### 3.2 Tooltip copy

`title` / `aria-label`:
> "Preview value — not yet wired to live data. This number is illustrative and
> will update once the data source is connected."

Applied to: hero view-count + last-updated; related-variant views / updated /
New-Updated pills; any constraint metric (Z/LOEUF/pLI) the contract doesn't yet
carry; ClinVar submitter free-text if absent; pub-graph per-year counts.

---

## 4. §3 Population — AF thermometer + constraint readout

Sits **above** the existing `PopulationFrequencySection` tabs (world map etc.,
unchanged). Two stacked blocks inside one `--bg-soft` card.

### 4.1 Franklin-style AF "thermometer"

A horizontal **bullet/threshold bar** (ui-ux-pro-max "Bullet Chart", AAA — value
as text + threshold labels, never colour-position alone). Reuses the **exact
`GNOMAD_AF_BANDS` cutoffs** already in the codebase, so §3 and the §1 Population
card agree by construction.

Layout (single row, ~44px tall, full column width):

```
 BENIGN ◄───────────────────────────────────────────► PATHOGENIC-LEANING
 ┌──────────┬──────────┬──────────────┬───────────────────────────┐
 │  ≥ 5%    │  1–5%    │   0.1–1%     │          < 0.1%           │   ← zone labels (mono 9.5)
 │  BA1     │  BS1     │  (interm.)   │   PM2          not obs.   │   ← acmg chips
 │  green   │  mint    │   amber      │   red            grey     │   ← band fills, 6px tall
 └──────────┴──────────┴──────────────┴───────────────────────────┘
                              ▲  0.0008%  (gnomAD v4, joint)            ← the variant marker + readout
```

- **Zones** are the 4 `GNOMAD_AF_BANDS` (same green/mint/amber/red hexes), drawn
  as a 6px-tall segmented track. Widths are **log-scaled** (AF spans 5%→0% — a
  log axis is the only honest layout; linear would crush everything into the
  rare end). Each zone labelled with its **threshold text** (`≥5%`, `1–5%`,
  `0.1–1%`, `<0.1%`) and its **ACMG chip** (BA1/BS1/PM2) below — text, not
  colour, carries the meaning.
- **The variant marker** = a 2px vertical `--ink` rule (the "target line" from
  the bullet-chart pattern) dropped at the variant's AF, with a caret. Directly
  beside it, the **numeric AF as text** (`--mono` 13px `--ink`): `0.0008%` +
  source caption (`gnomAD v4 · joint`). **Never hover-only** — the value is
  always visible.
- **Not-observed / absent** → marker pinned at the far rare end on the **grey**
  `--cls-na`-equivalent terminus with the label "Not observed in gnomAD", *not*
  red — honest (matches the map's `noData` rule). PM2-supporting is conveyed in
  the readout text, not by painting it red.
- **Headline chip** above the bar: a `ClassificationBadge`-style pill stating the
  AF verdict in words — "Common · benign (BA1)" or "Absent · PM2-supporting".

Reduced-motion: the marker does not animate into place (or `--dur-1` opacity
fade only). No sweeping fill animation.

### 4.2 Constraint readout — Z-score / LOEUF / pLI

A compact 3-up stat row beneath the thermometer (gene-level constraint, gnomAD).
Each is a labelled stat, **value-as-text first**, with a tiny inline scale and a
tooltip:

```
 Missense Z (mis_z)        LOEUF                  pLI
 ┌─────────────────┐       ┌─────────────────┐    ┌─────────────────┐
 │  3.42  ⓘ        │       │  0.21  ⓘ         │    │  1.00  ⓘ        │
 │ ▕▏▕▏▕▏▕▏░░  hi   │       │ ▕▏░░░░░  low      │    │ ●●●●●●●●●●  high │
 │ constrained     │       │ intolerant of LoF│    │ LoF-intolerant   │
 └─────────────────┘       └─────────────────┘    └─────────────────┘
   --mono value, --display-free, plain-word verdict beneath each
```

- **mis_z / lof_z**: higher = more constrained. Mini bar fills toward `--warn`/
  `--cls-lpath` as Z rises above ~3.09 (the conventional constrained cutoff);
  plain word "constrained" / "tolerant".
- **LOEUF**: lower = more LoF-intolerant. Map <0.35 → constrained
  (`--cls-lpath`-leaning), >1.0 → tolerant (`--ink-3`); word beneath.
- **pLI**: ≥0.9 → "LoF-intolerant" (`--cls-lpath`-leaning); <0.1 → tolerant.
- All three are **`--mono` numbers** + a one-word verdict + tooltip; colour is a
  reinforcement, never the only signal.
- If the contract doesn't yet carry constraint, render with the **§3 ghost
  chip** ("needs live data") — mock-first, honestly labelled.

---

## 5. Related-variants rail card (2-line, YouTube-style)

Rail width **~336px** (the WorkRail rail). Replaces the current dense
`VariantCardRow` in the related lanes with a slightly taller, scannable 2-line
card. Card: `--bg`, `0.5px --line`, `--r-md`, `10px 12px`, interactive
(`--elev-1`→`--elev-2` hover, teal focus, `:active` press).

```
 ┌────────────────────────────────────────────────┐  336px
 │ RPE65  c.272G>A          [ New ]ᵖⁱˡˡ            │  line 1: identity + state pill
 │ ▔▔▔▔▔ mono 12.5/600                              │
 │ ▮▮▮▮   1,043 views · updated 2 wk ago ⟨mock⟩    │  line 2: 4-chip row + meta
 └────────────────────────────────────────────────┘
```

- **Line 1**: `GENE c.cdna` (`--mono` 12.5/600, `--ink`; gene `--ink` / cdna
  `--ink-2`). Truncate cdna with ellipsis at the card edge; full value in `title`.
  Right edge: **New / Updated** pill (see §7) — only one shows.
- **Line 2 — mini 4-colour chip row**: four 8×8 rounded squares (`--cls-{tier}-dot`
  of each axis), 3px gap, **mirroring the 4 main cards in the same L→R order**.
  Each square has a `title` ("Computational: likely damaging"); the row has an
  `aria-label` summarising all four (colour-not-alone). Followed by `views` +
  `updated` in `--body` 10.5 `--ink-4`, both wearing the ghost-marker until
  Codex wires them.
- **Hover**: card lifts one elevation step, border → `--ink-5`; the New/Updated
  pill does not change. Whole card navigates to that variant's report
  (`reportHrefForQuery`).
- A trailing **"＋ Save"** affordance appears on hover/focus at the card's right
  (the existing `lib-related-add` button), `aria-label="Save GENE c.cdna to
  library"`.
- Truncation rule: identity single-line ellipsis; the 4-chip row never wraps;
  meta truncates `updated` before `views`.

The lane guardrail copy stays ("Suggestions are based on real genomic
relationships … not popularity") — honest, anti-dark-pattern.

---

## 6. §1 Clinical — the reusable "curator quote" block

One block component used for **both** ClinGen (VCEP) and ClinVar so the section
reads as one consistent grammar. It extends today's `ExpertPanelSection`
narrative + criteria-chip pattern; ClinVar gets the same shell for its submitter
interpretation text.

```
 ┌───────────────────────────────────────────────────────────────┐
 │ ● ClinGen  expert panel          RPE65 VCEP · Curated 2023-08  │  header: dot + source + meta
 │───────────────────────────────────────────────────────────────│
 │ [ Likely pathogenic ]   View on ClinGen ↗                      │  verdict badge + dotted source link
 │                                                                 │
 │ ❝ This variant meets PM1, PM2, PP3 … the panel classifies it   │  ← the QUOTE: assessment text
 │   as Likely Pathogenic for RPE65-related retinopathy. ❞         │     --body 13/1.55 --ink-2
 │                                                                 │
 │ [PM1] [PM2] [PP3_Moderate §] [PP1]                              │  ← criteria chips (existing CriterionChip)
 └───────────────────────────────────────────────────────────────┘
```

Shared anatomy (a `<CuratorQuote>` component):
- **Header**: verdict dot (`--cls-{tier}-dot`) + source name (`.eamos-kicker`) +
  light meta (VCEP name / submitter count, `--ink-4`).
- **Verdict row**: `ClassificationBadge` + a **dotted-underline source link**
  (`text-decoration: dotted; text-underline-offset: 3px; color: --teal-deep`) —
  the dotted underline signals "outbound provenance", distinct from solid links.
- **The quote**: the curator's free text in `--body` 13/1.55 `--ink-2`, set off
  with a thin `--teal-bdr` left rule (3px) + `--teal-tint` faint wash, so it
  reads as *quoted assessment*, not Eamos prose. A genuine `❝` is avoided as an
  emoji-glyph; instead the left-rule + indent carries the "quote" semantics
  (DESIGN bans decorative glyphs).
- **Criteria chips**: the existing `CriterionChip` (mono code, `§` override
  marker, rationale on hover). ClinVar uses the same chip shape for its
  review-status / consequence.
- ClinVar variant: same shell — classification badge + review-status stars +
  the **submitter interpretation text** as the quote (ghost-marked if the
  contract doesn't carry free-text yet) + the submitter `StackedCountBar`.

This unifies §1 so a clinician learns the pattern once and reads both sources
the same way.

---

## 7. Cross-cutting HOVER-TOOLTIP / affordance pass

**Rule** (spec §"Intuitiveness"): every toggle, button, and jargon label gets
`title` **and** `aria-label`; tooltips explain *what the control does* or *what
the term means* in plain language — never restate the label. Critical info is
**also** in visible text (ui-ux-pro-max "Hover vs Tap", High) so nothing is
hover-only. Tooltips are keyboard-reachable (focus shows them where the browser
allows; the visible-text duplication covers the gap).

### 7.1 The full microcopy list

**4 card verdict states**
- Computational card → "Eamos's combined call from the in-silico predictors
  (REVEL, CADD, SpliceAI, …). Damaging means the tools agree the change is
  likely harmful to the protein."
- Clinical card → "The clinical classification (ACMG / ClinGen / ClinVar):
  Pathogenic through Benign, or VUS when evidence is uncertain."
- Population card → "How common this variant is in the general population
  (gnomAD). Common variants are usually benign; very rare or absent variants
  can support a pathogenic call."
- Lab & Functional card → "What wet-lab experiments show about the variant's
  effect on protein function, and who curated that evidence (ClinGen / ClinVar)."
- 4-segment hero strip → "Evidence at a glance — one colour per card:
  Computational, Clinical, Population, Lab & Functional."

**AF-class chips**
- BA1 → "Allele frequency ≥ 5% in a general population — stand-alone evidence
  the variant is benign (ACMG BA1)."
- BS1 → "Allele frequency higher than expected for the disease (1–5%) — strong
  evidence toward benign (ACMG BS1)."
- PM2 → "Absent or extremely rare (< 0.1%) in population databases — supporting
  evidence toward pathogenic (ACMG PM2)."
- 0.1–1% (intermediate) → "Uncommon — between the benign and pathogenic
  frequency thresholds; not decisive on its own."
- Not observed → "Not seen in any gnomAD sample. Treated as absent (PM2-
  supporting), not as proof of pathogenicity."

**Constraint metrics**
- Missense Z (mis_z) → "How depleted this gene is of missense changes versus
  expectation. Higher = more constrained = changes are less tolerated
  (Z ≳ 3 is constrained)."
- LOEUF → "Loss-of-function observed/expected upper-bound fraction. Lower =
  the gene tolerates loss-of-function poorly (< 0.35 is LoF-intolerant)."
- pLI → "Probability the gene is intolerant of a single loss-of-function allele.
  ≥ 0.9 = highly LoF-intolerant."

**ACMG criterion chips** (per code; the existing `CriterionChip` already shows
rationale on hover — keep, and add a plain-English gloss when no rationale):
- Generic fallback → "ACMG criterion {CODE}: {plain-language meaning}. Hover
  shows the curator's rationale for applying it here."
- `§` override marker → "This expert panel applied a different strength than the
  default ACMG rule (VCEP-specific calibration)."

**ClinGen / ClinVar review status**
- ClinGen VCEP → "A ClinGen Variant Curation Expert Panel — domain experts who
  classify variants for a specific gene/disease using gene-tuned ACMG rules."
- ClinVar review stars → "ClinVar review confidence (0–4 stars). More stars =
  more independent submitters agree, or an expert panel reviewed it."
- ClinVar 'Stale' chip → existing freshness reason; keep.
- Submitter bar → "How ClinVar's submitters classified this variant, by tier."

**Publication variant/gene toggle**
- Variant scope → "Show publications that cite this specific variant." (Outbound
  link label corrected **Google Scholar → PubMed**, per spec small-fix.)
- Gene scope → "Show publications about the whole gene, not just this variant."
- The toggle itself → "Switch the publication list and year-graph between this
  variant and the whole gene."

**Save / Export / Share cluster**
- Save → "Save this variant to your library so you can return to it." (toggled:
  "Saved — remove from your library.")
- Export → "Download or print this report as a PDF."
- Share → "Copy a link to this exact report." (after: "Link copied.")

**New / Updated pills**
- New → "Added to Eamos recently."
- Updated → "Evidence for this variant changed recently — its classification or
  sources were revised." (both ghost-marked until Codex supplies timestamps.)

**'Needs live data' marker** → see §3.2.

**Abbreviations (any first occurrence gets a tooltip)**
- HGVS → "Human Genome Variation Society nomenclature — the standard way to
  write a variant (c. = coding DNA, p. = protein, g. = genomic)."
- MANE → "Matched Annotation from NCBI and EMBL-EBI — the single agreed-upon
  reference transcript for the gene (MANE Select)."
- VCEP → "Variant Curation Expert Panel (ClinGen)."
- LOEUF / pLI / Z-score → as above.
- VCF → "Variant Call Format — `chrom-pos-ref-alt`, the file-level
  representation."
- rsID → "dbSNP reference SNP identifier — a stable ID for this position's
  variant across databases."
- ACMG → "American College of Medical Genetics — the standard variant-
  classification framework (the PVS1…BP7 criteria)."

### 7.2 Affordance hardening (intuitiveness)

- **Clickable looks clickable** (DESIGN #3): all 4 cards, related-variant cards,
  the hero strip, the Details toggle, and tabs use `cursor: pointer`, an
  elevation/border hover response, and the teal focus ring. Static readouts
  (constraint stats, the thermometer track, quote text) **never** lift and use
  default cursor.
- **One focal action per region**: Save in the hero; "View detail" on a card;
  the variant link on a rail card.
- **Honest feedback only**: Share's 2s "Copied", disclosure chevron rotation,
  card hover — all reflect real state; no fabricated progress (DESIGN #4).
- **Reduced motion**: the global `prefers-reduced-motion` guard already in
  `globals.css` covers all of the above; the thermometer marker and disclosure
  collapse to `.01ms` transitions; no looping/decorative animation anywhere.

---

## 8. Section order & preservation notes (for the build)

Reordered per spec: **1 Clinical → 2 In-silico → 3 Population → 4 Gene & locus
→ 5 Disease & curated → 6 Publications → 7 Therapies → 8 AI summary.** Preserve
`LazySection` wrapping, section keys, and `targetFor(...)` anchor IDs through the
reorder (call-card `scrollToInteraction` depends on them). Remove `MatrixOverture`
entirely; the 4 cards are the only top display.

---

## 9. Acceptance checklist (design-verifiable)

- [ ] All 4 cards full-coloured by verdict-state via `--cls-*`/`--info-*`/`--cls-na`;
      each states its verdict in **words + dot**, not colour alone.
- [ ] Hero resting height ≤ ~84px; DNA `c.` primary, protein muted; 4-segment
      strip present with per-segment tooltips; cross-DB chips moved into Details.
- [ ] Details discloses full coords (chr:pos 1-based + VCF), c./p./g. HGVS, MANE,
      build, rsID, consequence — all `--mono`, copyable VCF.
- [ ] "Follow" → "Save" wired to `variant-library`; Scholar → PubMed corrected.
- [ ] Every mock metric wears the `.eamos-mock` ghost chip + its tooltip.
- [ ] §3 AF thermometer uses the `GNOMAD_AF_BANDS` cutoffs, shows the numeric AF
      as visible text + a target-line marker, labels BA1/BS1/PM2 in text, and
      pins absent variants to grey (not red).
- [ ] Constraint mis_z / LOEUF / pLI shown as value-first stats with one-word
      verdicts + tooltips (ghost-marked if unwired).
- [ ] Related-variant rail cards are 2-line, 336px, with the 4-colour mirror row
      + views/updated + New/Updated pill, each tooltip'd.
- [ ] §1 ClinGen and ClinVar both use the shared `<CuratorQuote>` block (quote +
      criteria chips + dotted source link).
- [ ] Tooltip pass complete per §7.1; nothing decision-critical is hover-only.
- [ ] No new tokens/fonts; weight ≤ 700; hairlines 0.5px; no raw box-shadow;
      `prefers-reduced-motion` guard honoured.
