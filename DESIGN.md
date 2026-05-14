# Eamos Design System — v2

Reference this file for all frontend work on the active surfaces: `/` (Landing), `/report` (Variant Report v2), `/workbench` (Workbench v1).

The legacy `/runs` (Layer 2 patient report) surface is **frozen** on the v1 design system — see the appendix at the bottom of this file.

Source-of-truth HTML mocks: `e:\Web tool\Claude Design\` — `Eamos Landing Page.html`, `Eamos Report Page v2.html`, `Eamos Workbench v1.html` + `Workbench/*.{js,css}`.

---

## Design Philosophy

Clean, professional, clinical — not consumer, not corporate. Dense but scannable. Every element earns its place.

- **0.5px hairlines** are load-bearing — they're what makes the surface feel clinical. Keep them as raw CSS via `.hairline` utility.
- **No shadows, no gradients.** Subtle borders only.
- **Active voice typography.** Display weights 500–700; body 400–500. Never above 700.
- **Tokens, not magic numbers.** Every colour and radius comes from `:root` CSS variables in `src/index.css`.

---

## Color Tokens

```css
:root {
  /* Surfaces */
  --bg:        #ffffff;
  --bg-soft:   #f8fafc;
  --bg-soft2:  #f1f5f9;
  --bg-tint:   #f3f7f6;   /* subtle teal-warm wash */
  --bg-canvas: #fbfcfd;   /* Workbench-only canvas wash */

  /* Ink scale (text + iconography) */
  --ink:   #0b1a2b;
  --ink-2: #1e3a5f;
  --ink-3: #475569;
  --ink-4: #94a3b8;
  --ink-5: #cbd5e1;

  /* Hairlines */
  --line:   #e2e8f0;
  --line-2: #cbd5e1;
  --line-3: #f1f5f9;

  /* Brand teal */
  --teal:      #1D9E75;
  --teal-deep: #156b50;
  --teal-tint: #f0f7f4;

  /* Status */
  --warn:      #BA7517;
  --warn-tint: #FAEEDA;
  --warn-bdr:  #FAC775;
  --err:       #B82B2B;
  --err-tint:  #fbeaea;
}
```

### Sequence palette (Workbench only)

Muted, ~25% chroma. **Never use Benchling rainbow.**

```css
--base-A: #d29a4a;
--base-T: #5081b9;
--base-C: #4a9d8f;
--base-G: #b75a5a;
```

### Amino-acid biochem class pill backgrounds (Workbench only)

```css
--aa-hydro: #f1ead8;   /* hydrophobic */
--aa-polar: #e0ecdb;   /* polar */
--aa-acid:  #f6e0e0;   /* acidic */
--aa-basic: #dbe5f4;   /* basic */
--aa-aroma: #ebe1f0;   /* aromatic */
--aa-cys:   #f4ecd2;   /* cysteine */
--aa-stop:  #d9dde2;   /* stop codon */
```

### Classification colours (semantic — never change)

| Tier | bg | text | bdr | dot |
| ---- | -- | ---- | --- | --- |
| Pathogenic | `#FCEBEB` | `#791F1F` | `#F7C1C1` | `#E24B4A` |
| Likely Pathogenic | `#FAEEDA` | `#633806` | `#FAC775` | `#BA7517` |
| VUS | `#FAEEDA` | `#854F0B` | `#EF9F27` | `#d97706` |
| Likely Benign | `#EAF3DE` | `#3B6D11` | `#C0DD97` | `#639922` |
| Benign | `#EAF3DE` | `#27500A` | `#9FE1CB` | `#1D9E75` |

### Predictor score scales

| Score | Range | Colour |
| ----- | ----- | ------ |
| SpliceAI | ≥ 0.5 | `--err` |
|         | ≥ 0.2 | `--warn` |
|         | < 0.2 | `--teal` |
| REVEL   | ≥ 0.7 | `--err` |
|         | ≥ 0.5 | `--warn` |
|         | < 0.5 | `--ink-3` |
| AlphaMissense | ≥ 0.564 | `--err` |
|               | ≥ 0.34  | `--warn` |
|               | < 0.34  | `--ink-3` |

---

## Typography

```css
--display: 'Syne', system-ui, sans-serif;
--body:    'Plus Jakarta Sans', system-ui, sans-serif;
--mono:    'JetBrains Mono', ui-monospace, monospace;

body { font-family: var(--body); font-size: 14.5px; line-height: 1.6; }
```

Loaded once via `@import` in `src/index.css`. Tailwind v4 `@theme inline` exposes them as `font-display`, `font-sans`, `font-mono`.

### Scale

| Size | Weight | Use |
| ---- | ------ | --- |
| 24px | 600 (display) | Gene name on variant header |
| 17px | 600 (display) | Logo wordmark |
| 14.5px | 400 | Body, paragraph text |
| 13px  | 500 | Section headers, nav text |
| 12.5px | 500 (mono) | HGVS in search input, transcript |
| 11.5px | 500 | Cross-DB chips, badge text |
| 10.5px | 500 (uppercase) | Section number labels, metadata |

**Never use weight > 700.**

---

## Radii & widths

```css
--r-sm: 6px;
--r-md: 10px;
--r-lg: 14px;
```

| Surface | Max width | Notes |
| ------- | --------- | ----- |
| Landing | 1180px | Centered content column; nav matches |
| Report  | 920px main column / 1180px nav | The 920px column is load-bearing for hairline density |
| Workbench | 1440px | 64px rail / flex canvas / 360px side panel |

Below 1200px the Workbench side panel collapses; below 760px the rail collapses too. Use `display:none` (don't unmount).

---

## Core Components

### Card (`.card` / `<Card>`)

```css
.card {
  background: var(--bg);
  border: 0.5px solid var(--line);
  border-radius: var(--r-lg);
  padding: 24px 28px;
}
```

Section spacing: `gap: 18px` between cards. No shadows.

### Hairline utility

```css
.hairline   { border: 0.5px solid var(--line); }
.hairline-b { border-bottom: 0.5px solid var(--line); }
.hairline-t { border-top:    0.5px solid var(--line); }
```

### Classification badge (`<ClassificationBadge>`)

`<span class="cb cb-{tier}"><span class="cb-dot" /> {Label}</span>`

Padding `2px 9px`, radius 4px, 0.5px border. Background/text/border from the tier table above.

### Cross-DB jump chip

For the variant header's external link strip.

```css
.v-jump-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 5px 10px;
  font-size: 11.5px; font-weight: 500;
  color: var(--ink-3);
  background: var(--bg-soft);
  border: 0.5px solid var(--line);
  border-radius: 6px;
}
.v-jump-chip:hover { color: var(--ink); border-color: var(--ink-5); }
.v-jump-chip .ext { color: var(--ink-4); }
```

Chip set (in order): ClinVar, gnomAD, UCSC, Ensembl, OMIM, AlphaFold. **No Franklin chip.**

### Buttons

| Variant | Background | Text | Border |
| ------- | ---------- | ---- | ------ |
| Primary (teal) | `--teal` | white | none |
| Navy (sign-off) | `--ink-2` | white | none |
| Ghost | none | `--ink-2` | 0.5px `--line-2` |
| Submit search (gene mode) | `--ink-2` | white | none |
| Submit search (AI mode)   | `--teal` | white | none |

Padding `9px 16px`. Radius `--r-md` (10px). Font weight 600, size 12.5–13px.

### Search shell (`.ns-shell`)

Pill-shaped (radius 100px), 0.5px border, focus glow:

```css
.ns-shell:focus-within {
  border-color: var(--teal);
  box-shadow: 0 0 0 3px rgba(29,158,117,0.12);
}
.ns-shell[data-mode="ai"]:focus-within {
  border-color: var(--ink-2);
  box-shadow: 0 0 0 3px rgba(30,58,95,0.10);
}
```

Mode toggle (Gene variant ⇄ AI) is a segmented control inside the pill. Submit button is a 34×34 circle (`--ink-2` in gene mode, `--teal` in AI mode).

### Mode pill — Report ⇄ Workbench

Sticky in top nav. Active item: ink background, white text. Inactive: ghost.

```css
.mode-pill {
  display: inline-flex;
  background: var(--bg-soft);
  border: 0.5px solid var(--line);
  border-radius: 100px;
  padding: 3px;
}
.mode-pill a {
  padding: 6px 12px;
  font-size: 12px; font-weight: 600;
  color: var(--ink-3);
  border-radius: 100px;
  display: inline-flex; align-items: center; gap: 6px;
}
.mode-pill a.active {
  background: var(--ink-2); color: #fff;
}
```

Preserves `?q=` across navigation.

---

## Report v2 modules

| Component | What |
| --------- | ---- |
| `<VariantHeader />` | Gene name (display, 24px), protein change (mono, ink-3), classification badges, cross-DB chip strip, tools row (Follow / Export PDF / Share), 4-stat row |
| `<AIStack />` | Composite of `<EvidenceSummary />` + `<AskEamos />` — ink-dark panel, no visible seam between halves |
| `<LocusContext />` | 5 lanes (P/LP/VUS/LB/B) of nearby ClinVar dots, vertical marker drops into 11-codon strip below. Footer link "Open full sequence in Workbench ↗" |
| `<InSilicoGrid />` | 4-card grid (REVEL / AlphaMissense / MetaLR / SpliceAI Δ), score + threshold bar + verdict badge. Consensus callout below the grid |
| `<EvidenceTable />` | Source-by-source evidence rows (existing, unchanged) |
| `<AcmgCriteriaFold />` | Collapsible 28-cell ACMG grid (PVS1 → BP7). Met cells: warn-tint (pathogenic) / teal-tint (benign). Disclaimer: "Supporting evidence, not classification." |
| `<DiseaseSection />` | Gene function (existing, unchanged) |
| `<CuratedVariantsGrid />` | 3×4 heat matrix (Pathogenic/VUS/Benign × LOF/Missense/Non-coding/Synonymous) + totals + reading |
| `<AssociatedConditions />` | Structured list — case count, evidence-level bar, inheritance pill, source attribution |
| `<PublicationsCallout />` | Total count + Google Scholar deep link + "AI summary" CTA → Ask Eamos |
| `<TrialsSection />` | ClinicalTrials.gov recruiting/active (existing) |
| `<LimitationsSection />` | Caveats and disclaimers (existing) |

---

## Workbench surface

### Layout chrome

| Component | What |
| --------- | ---- |
| `<TopNav />` | Same as Report — Eamos wordmark left, search shell centre, Report ⇄ Workbench mode pill right |
| `<ContextStrip />` | Slim row beneath nav: `RPE65 · c.260A>G · p.Asp87Gly · NM_000329.3 · chr1:68,444,869 T>C · GRCh38 · 21,138 bp gene` + classification badge + external DB chips |
| `<WorkbenchShell />` | 3-col layout (`grid-template-columns: 64px 1fr 360px`) |
| `<ToolRail />` | Vertical icon rail: Sequence / Primer / CRISPR / Align / Compare + Settings at bottom |
| `<CanvasHeader />` | Title + subtitle + track-toggle checkboxes (Annotations / Protein domains / Conservation / Restriction / ClinVar) + zoom pill (Gene / Exon / Codon) |
| `<SidePanel />` | 360px right column; content swaps per active tool (scratchpad for viewer, primer/CRISPR context for those tools, etc.) |
| `<AskEamosPill />` | Floating bottom-right 420×56 pill, expands upward into a chat panel. Label tracks active tool |

### Sequence viewer

Track order (top → bottom):

1. Ruler — codon numbers
2. Annotations — exon (cream) / CDS (teal-tint) / oligo (indigo) bars
3. UniProt domain — coloured bar
4. ClinVar — coloured dots positioned at variant `cdsPos`
5. Sequence (5′→3′) — DNA bases, A/T/C/G colour-coded, **clickable**
6. Translation — codon-aligned AA pills, background by biochem class
7. Conservation — PhyloP bar chart per base
8. Restriction — enzyme marks + labels (off by default)

A vertical pin runs through all tracks at the queried position.

### Click-to-edit popover (the differentiator)

Click any DNA base → popover anchored beneath:
- Header: position + reference base
- 5 buttons: A / T / C / G / del
- Hover preview: live consequence (Synonymous / Missense p.X / Stop gained / Frameshift) using `consequenceOf` from `src/lib/workbench/codon-table.ts`
- Apply commits the edit; canvas re-renders with new base highlighted; scratchpad logs the change
- "Reset to ref" reverts

### Tool panels

- Sequence Viewer is **always visible** unless `align` or `compare` is active, in which case the canvas collapses and the tool panel takes over the canvas slot.
- Primer + CRISPR panels sit BELOW the Sequence Viewer so the user can see what they're targeting while designing.
- Align and Compare replace the canvas entirely.

---

## Information hierarchy & navigation

```
Landing (/)  ─┬─→ Report (/report?q=GENE:c.cdna)  ⇄  Workbench (/workbench?q=...)
              │                                       │
              └─→ Patient Report intake (/runs)  [frozen — legacy v1 design]
                                                       │
                                                       └─→ Patient Report view (/runs/{id})
```

- Variant lookup IS the landing page.
- Report ⇄ Workbench mode pill in top nav preserves the `?q=` parameter on switch.
- Patient Report (`/runs`) accessed via ghost button on landing — secondary, low-traffic.

---

## What NOT to do

- No font weights above 700.
- No emojis or icons except external-link ↗, the Eamos logo mark, and the rail tool icons.
- No shadows. No gradients.
- No border radius > 14px (cards) or 100px (pills).
- No colours outside the palette above.
- No heavy borders — always 0.5px or 1px max.
- No pure black (#000000) — use `--ink` (#0b1a2b).
- No "Compare elsewhere ↗" link to franklin.genoox.com — Franklin is a competitor.
- No Franklin chip on the cross-DB strip — drop it.

---

## Quick reference

```
Page bg:         var(--bg-soft) for body, var(--bg) for cards
Card border:     0.5px solid var(--line)
Card radius:     var(--r-lg) (14px)
Card padding:    24px 28px

Primary brand:   var(--teal) (#1D9E75)
Secondary brand: var(--ink-2) (#1e3a5f)
Body text:       var(--ink)
Secondary text:  var(--ink-3)
Hint text:       var(--ink-4)

Base font:       'Plus Jakarta Sans'
Display font:    'Syne'
Mono font:       'JetBrains Mono'
Base size:       14.5px
Line height:     1.6
```

---

## Appendix — Legacy `/runs` surface (frozen)

The Layer 2 patient report flow at `/runs` is frozen on the v1 design system. Do not restyle it.

The v1 tokens are preserved in `src/index.css` under the `BACKWARD-COMPAT` block (`--canvas`, `--panel`, `--muted-ink`, `--teal-ghost`, `--danger`, etc.). They exist only for `LegacyRunsApp.tsx`. New work should never reach for them.

If Layer 2 is redesigned later, that's a separate cycle — file under "Layer 2 v2" in `ROADMAP.md`.

Legacy v1 component reference (Card, Section header, ACMG criteria tag, Primary/Secondary/Navy/Ghost buttons, Input/Select, Database link button, Inline source link, Table, Clinical Integration bullet, Bottom-line banner, Info banner, Gene function box, Upload zone, Loading state, Spinner, Top nav, Variant switcher tabs, ERG/Pedigree SVGs) — keep current behaviour. No spec changes.
