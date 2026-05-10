# Eamos Design System

Reference this file for all frontend work.
Reference design: [Franklin](https://franklin.genoox.com) — clinical genomics tool with similar density and professional register.

---

## Design Philosophy

Clean, professional, clinical — not consumer, not corporate.
Dense but scannable. Clinicians and researchers read fast and need to find specific numbers quickly. Every element earns its place. No decorative elements. No gradients. No shadows. No rounded corners on single-sided borders. Subtle borders, not heavy outlines.

---

## Color Palette (CSS Variables)

```css
:root {
  /* Backgrounds */
  --bg:      #f8fafc;   /* page background — very light blue-grey */
  --bg2:     #ffffff;   /* card background — pure white */
  --bg3:     #f1f5f9;   /* secondary background — slightly darker */

  /* Text */
  --text:    #1e293b;   /* primary text — near black */
  --text2:   #475569;   /* secondary text — medium grey */
  --text3:   #94a3b8;   /* tertiary text — light grey (labels, hints) */

  /* Borders */
  --border:  #e2e8f0;   /* primary border — very subtle */
  --border2: #cbd5e1;   /* secondary border — slightly more visible */

  /* Brand */
  --teal:    #1D9E75;   /* primary brand colour — section numbers,
                           primary buttons, active states, links */
  --navy:    #1e3a5f;   /* secondary brand — sign-off button,
                           top navigation bar */

  /* Info banner */
  --info-bg:     #eff6ff;   /* light blue background */
  --info-border: #bfdbfe;   /* blue border */
  --info-text:   #1d4ed8;   /* blue text */
}
```

### Classification Colors (semantic — never change these)
```css
/* Pathogenic */
--cls-p-bg:  #FCEBEB;  --cls-p-text: #791F1F;
--cls-p-bdr: #F7C1C1;  --cls-p-dot:  #E24B4A;

/* Likely Pathogenic */
--cls-lp-bg:  #FAEEDA; --cls-lp-text: #633806;
--cls-lp-bdr: #FAC775; --cls-lp-dot:  #BA7517;

/* VUS (Variant of Uncertain Significance) */
--cls-vus-bg:  #FAEEDA; --cls-vus-text: #854F0B;
--cls-vus-bdr: #EF9F27; --cls-vus-dot:  #d97706;

/* Likely Benign */
--cls-lb-bg:  #EAF3DE; --cls-lb-text: #3B6D11;
--cls-lb-bdr: #C0DD97; --cls-lb-dot:  #639922;

/* Benign */
--cls-b-bg:  #EAF3DE; --cls-b-text: #27500A;
--cls-b-bdr: #9FE1CB; --cls-b-dot:  #1D9E75;
```

### Recommendation Priority Colors
```css
/* HIGH */
--pri-h-bg: #FCEBEB; --pri-h-text: #791F1F; --pri-h-bdr: #F7C1C1;

/* MODERATE */
--pri-m-bg: #FAEEDA; --pri-m-text: #633806; --pri-m-bdr: #FAC775;

/* ROUTINE */
--pri-r-bg: #E6F1FB; --pri-r-text: #0C447C; --pri-r-bdr: #B5D4F4;
```

### SpliceAI Score Colors
```css
High   (>= 0.5): #E24B4A  /* red */
Moderate (>= 0.2): #BA7517  /* amber */
Low    (< 0.2):  #1D9E75  /* teal/green */
```

### Score Colors (REVEL, CADD)
```css
REVEL >= 0.7 or CADD >= 30: #E24B4A  /* red — high */
REVEL >= 0.5 or CADD >= 20: #BA7517  /* amber — moderate */
Otherwise:                   #475569  /* grey — low/neutral */
```

---

## Typography

```css
font-family: system-ui, -apple-system, sans-serif;
/* No custom fonts — system fonts load instantly and look clean */

font-size: 14px;      /* base body text */
line-height: 1.6;     /* comfortable reading */
color: #1e293b;       /* --text */
```

### Font Size Scale
```
17-18px  font-weight: 500  — variant/gene name (main title in report header)
15-16px  font-weight: 500  — page titles, card titles (landing page)
14px     font-weight: 500  — section headers (.s-hd)
13px     font-weight: 400  — body text, AI summary paragraphs
13px     font-weight: 500  — nav text, important labels
12px     font-weight: 400  — table content, secondary body text
12px     font-weight: 500  — button text, tab text (active)
11px     font-weight: 500  — small labels, expand buttons, hints
10px     font-weight: 500  — badge text (UPPERCASE), ACMG tags,
                             section number circles, metadata
```

### Font Weight Rule
Only use 400 (regular) and 500 (medium).
Never use 600, 700, or bold — too heavy for this design.

---

## Spacing System

All spacing uses multiples of 4px.

```
4px   — gap between inline elements (badge dot + text)
5px   — small gap (badge padding vertical, inline gaps)
6px   — gap between title and subtitle in headers
7-8px — gap between badge elements, small margins
8px   — table cell padding, small component padding
9-10px — badge padding horizontal, component gaps
10px  — section header bottom margin, standard gap
11px  — clinical integration bullet gap
12px  — card padding vertical, standard margins
14px  — card padding horizontal (smaller cards)
16px  — card padding vertical (standard cards)
20px  — card padding horizontal (standard cards)
24px  — page padding, large section gaps
28-32px — section spacing on landing page
40px  — large section padding (landing page hero)
```

---

## Core Components

### Card
The primary content container. Used for every report section.

```css
.card {
  background: #ffffff;           /* --bg2 */
  border: 0.5px solid #e2e8f0;  /* --border — very subtle */
  border-radius: 12px;           /* rounded corners */
  padding: 16px 20px;            /* vertical / horizontal */
  margin-bottom: 12px;           /* gap between cards */
}
```

**Special card variants:**
- Gene therapy card (approved): `border: 0.5px solid #9FE1CB` (green tint)
- Sign-off card: `border: 0.5px solid #cbd5e1` (slightly stronger border)

### Section Header (.s-hd)
Every report section starts with a numbered teal circle + title.

```css
.s-hd {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;                    /* --text */
  margin: 0 0 12px;
  padding-bottom: 10px;
  border-bottom: 0.5px solid #e2e8f0; /* --border */
  display: flex;
  align-items: center;
  gap: 10px;
}
```

### Section Number Circle (.num)
```css
.num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #1D9E75;    /* --teal */
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 500;
  flex-shrink: 0;
}
```

### Classification Badge (.cb)
```css
.cb {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 9px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 0.5px solid;
  /* bg, color, border-color set dynamically per classification */
}

/* Dot inside badge */
.cb-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  display: inline-block;
}
```

### Priority Badge (.pb)
Same styles as .cb — just different colors per priority level.
```css
.pb {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 9px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 0.5px solid;
}
```

### ACMG Criteria Tag
Small inline tag for individual ACMG criteria codes.
```css
{
  font-size: 10px;
  background: #f1f5f9;          /* --bg3 */
  border: 0.5px solid #e2e8f0;  /* --border */
  border-radius: 4px;
  padding: 2px 7px;
  margin: 1px;
  display: inline-block;
  color: #475569;               /* --text2 */
}
```

### Primary Button
```css
{
  padding: 11px 0;              /* full width variant */
  /* OR */
  padding: 9px 20px;            /* fixed width variant */
  background: #1D9E75;          /* --teal */
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
}
```

### Secondary Button
```css
{
  padding: 9px 20px;
  background: #ffffff;          /* --bg2 */
  color: #1e293b;               /* --text */
  border: 0.5px solid #cbd5e1;  /* --border2 */
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
}
```

### Navy Button (sign-off, important actions)
```css
{
  padding: 9px 20px;
  background: #1e3a5f;          /* --navy */
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
```

### Ghost Button (Patient Report entry — landing page)
```css
{
  font-size: 12px;
  color: #475569;
  background: none;
  border: 0.5px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 16px;
  cursor: pointer;
  width: 100%;
  text-align: left;
  margin-top: 12px;
}
/* Label: "For clinicians: Generate a patient report →" */
/* Sublabel: font-size 11px, color #94a3b8 */
/*   "Upload genomic sequencing data + patient history" */
```

### Back Button (small, ghost)
```css
{
  font-size: 12px;
  color: #475569;               /* --text2 */
  background: none;
  border: 0.5px solid #cbd5e1;  /* --border2 */
  border-radius: 6px;
  padding: 5px 12px;
  cursor: pointer;
}
```

### Search Button
```css
{
  padding: 7px 18px;
  background: #1e3a5f;          /* --navy */
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
```

### Input / Select
```css
input, select {
  padding: 7px 10px;
  border: 0.5px solid #cbd5e1;  /* --border2 */
  border-radius: 8px;
  font-size: 12px;
  background: #ffffff;          /* --bg2 */
  color: #1e293b;               /* --text */
  width: 100%;
  box-sizing: border-box;
  font-family: inherit;
}
```

### Database Link Button (external source links)
Blue pill-style links for ClinVar, gnomAD, SpliceAI etc.
```css
{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border: 0.5px solid #bfdbfe;  /* --info-border */
  border-radius: 6px;
  font-size: 11px;
  color: #1d4ed8;               /* --info-text */
  text-decoration: none;
  background: #eff6ff;          /* --info-bg */
}
/* Arrow symbol ↗ after label text */
```

### Hyperlink (inline source links in tables)
Dotted underline — signals "verify this" without being aggressive.
```css
a.source-link {
  color: #94a3b8;               /* --text3 — subtle */
  text-decoration: underline;
  text-underline-offset: 3px;
  text-decoration-style: dotted;
  /* ↗ symbol appended to label */
}
```

### Table
```css
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
tr {
  border-bottom: 0.5px solid #e2e8f0;  /* --border */
}
td, th {
  padding: 8px 10px;
  vertical-align: top;
}
th {
  color: #94a3b8;               /* --text3 */
  font-weight: 500;
  text-align: left;
}
/* Label column (left) */
td.label {
  color: #94a3b8;               /* --text3 */
  width: 34-36%;
  padding-right: 12px;
  white-space: nowrap;
}
```

### Clinical Integration Bullet
Numbered bullet card for the clinical integration section.
```css
{
  display: flex;
  gap: 11px;
  padding: 12px;
  background: #f8fafc;          /* slightly off-white */
  border: 0.5px solid #e2e8f0;  /* --border */
  border-radius: 8px;
}
/* Number circle: same as .num — 22px teal circle */
/* Title: font-size 12px, font-weight 500, margin-bottom 4px */
/* Content: font-size 12px, color #475569, line-height 1.7 */
```

### Bottom Line / Evidence Banner
Coloured left-border banner at top of report/card.
```css
{
  background: {classification bg color};
  border: 0.5px solid {classification border color};
  border-radius: 8px;
  padding: 11px 15px;
  border-left: 3px solid {classification dot color};
  /* Note: left border is 3px, others 0.5px */
}
/* Label: font-size 10px, font-weight 500, uppercase,
   letter-spacing 0.08em, color = classification text color */
/* Content: font-size 13px, line-height 1.7 */
```

### Info Banner (referral details, notes)
```css
{
  padding: 8px 12px;
  background: #eff6ff;          /* --info-bg */
  border: 0.5px solid #bfdbfe;  /* --info-border */
  border-radius: 6px;
  font-size: 11px;
  color: #1d4ed8;               /* --info-text */
  margin-top: 10px;
}
```

### Gene Function / Content Box
Secondary content box within a card.
```css
{
  padding: 10px 12px;
  background: #f8fafc;
  border: 0.5px solid #e2e8f0;  /* --border */
  border-radius: 8px;
}
/* Label: font-size 10px, font-weight 500, color #94a3b8,
   text-transform uppercase, letter-spacing 0.06em, margin-bottom 5px */
/* Content: font-size 12px, color #475569, line-height 1.7 */
```

### Upload Zone (patient report intake page)
```css
{
  border: 0.5px dashed #cbd5e1;  /* --border2 — dashed */
  border-radius: 8px;
  padding: 18px 14px;
  text-align: center;
}
/* Title: font-size 12px, font-weight 500 */
/* Description: font-size 11px, color #94a3b8 */
/* Browse button: inline-block, padding 4px 12px,
   border 0.5px solid #cbd5e1, border-radius 6px,
   font-size 11px, color #475569 */
```

### Loading State
```css
.loading {
  color: #94a3b8;               /* --text3 */
  font-style: italic;
  font-size: 12px;
}
/* Text: "Generating..." */
```

### Spinner (processing view)
```css
.spin {
  width: 28px;
  height: 28px;
  border: 2px solid #cbd5e1;    /* --border2 */
  border-top-color: #1D9E75;    /* --teal */
  border-radius: 50%;
  animation: sp 1s linear infinite;
  margin: 0 auto 16px;
}
@keyframes sp { to { transform: rotate(360deg); } }
```

---

## Navigation & Header

### Top Navigation Bar (report view)
```css
{
  background: #ffffff;
  border-bottom: 0.5px solid #e2e8f0;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 10;
}
```

Contents (left to right):
- Eamos logo mark: 26px × 26px, border-radius 6px, background #1D9E75,
  letter "E" in white, font-size 13px, font-weight 500
- "Eamos" text: font-size 13px, font-weight 500
- Divider: color #e2e8f0
- Patient name: font-size 12px, font-weight 500
- MRN: font-size 11px, color #94a3b8
- Flex spacer
- Version stamp: font-size 10px, color #94a3b8 (right aligned)
- Back button (ghost style, right)

### Variant Switcher Tabs
```css
.vtab {
  padding: 10px 14px;
  border: none;
  background: none;
  cursor: pointer;
  white-space: nowrap;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  border-bottom: 2px solid transparent;
  font-family: inherit;
}
/* Active tab: border-bottom color = classification dot color */
/* Active tab text: classification text color, font-weight 500 */
/* Inactive tab text: color #475569, font-weight 400 */
```

Tab contents (stacked vertically):
- Row 1: dot (6px circle, classification color) + gene name (font-size 12px)
         + PRIMARY badge if applicable (9px, teal bg, white text)
- Row 2: cdna notation (font-size 10px, color #94a3b8, padding-left 11px)
  NOTE: cdna notation is shown in tabs, NOT protein notation

Tab container:
```css
{
  background: #ffffff;
  border-bottom: 0.5px solid #e2e8f0;
  padding: 0 20px;
  overflow-x: auto;   /* horizontal scroll for many variants */
  display: flex;
}
```

---

## Page Layouts & Information Hierarchy

### Primary Product — Variant Lookup
The variant lookup IS the landing page. Users arrive and immediately see the search bar. Think of it like Google — the search is the homepage, not something you navigate to.

The Patient Report (Layer 2) is secondary — accessed via a ghost button at the bottom of the landing page. Mode-switching tabs are not in the header.

---

### Landing Page — Variant Lookup (PRIMARY)
```css
{
  background: #f1f5f9;
  min-height: 100vh;
  padding: 40px 20px;
}
/* Max width of content: 680px, centered */
```

Layout (top to bottom):
```
[Eamos logo mark] Eamos Genomics
Clinical Genomic Intelligence Platform

[Human (hg38)]  [Mouse (mm39)]      ← species toggle tabs

Search any gene or variant
e.g. RPE65:c.260A>G  or  USH2A      ← placeholder text
[_________________________________] [Search]

──── ── results appear below ── ── ──

[results card if searched]
```

Logo area:
- Logo mark: 30px × 30px, border-radius 8px, background #1D9E75
- "Eamos Genomics" text: font-size 17px, font-weight 500
- Subtitle: font-size 11px, color #94a3b8, letter-spacing 0.08em,
  text-transform uppercase, margin-bottom 24px

Species toggle (sits above search bar):
```css
{
  display: flex;
  gap: 0;
  border: 0.5px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
  width: fit-content;
}
/* Each tab: padding 7px 20px, font-size 12px, font-weight 500 */
/* Active: background #1D9E75, color #ffffff */
/* Inactive: background #ffffff, color #475569 */
/* Shows genome build: "Human (hg38)" / "Mouse (mm39)" */
```

Search bar:
```css
{
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
input {
  flex: 1;
  padding: 10px 14px;     /* slightly larger than default for hero */
  font-size: 14px;
  border: 0.5px solid #cbd5e1;
  border-radius: 8px;
}
/* Search button: navy (#1e3a5f), padding 10px 24px */
```

Helper text below search:
- font-size 11px, color #94a3b8
- "Enter gene name (e.g. RPE65) or variant in HGVS notation
  (e.g. c.260A>G, p.Asp87Gly). No patient data required."

Patient Report access (ghost button at bottom of page):
```
─────────────────────────────────────────
For clinicians: Generate a patient report →
─────────────────────────────────────────
```

Footer note: font-size 11px, color #94a3b8, margin-top 16px
"For research and informational use only · Not for clinical
decision-making without appropriate governance"

---

### Variant Lookup Results (same page, below search bar)
Results appear on the same page below the search bar — no navigation.
The search bar stays visible at top so the user can refine their search.

Layout when results found:
```
[search bar — stays visible]

RPE65 c.260A>G                     [Generate patient report →]
(p.Asp87Gly) · NM_000329.2 · Homozygous · AR
[VUS badge]  [LCA2 / RP20 pill]

[ClinVar ↗]  [gnomAD ↗]  [SpliceAI ↗]  [Franklin ↗]  [OMIM ↗]  [AlphaFold ↗]

──── Evidence Report ────

1  AI evidence summary
2  Classification snapshot
3  Clinical integration
4  Gene / disease phenotype
5  Gene therapy status
6  Clinical trials
7  Publications
```

Layout when not found:
```
[search bar]

"[query]" not found in database
Search directly:
[ClinVar ↗]  [gnomAD ↗]  [SpliceAI ↗]  [Franklin ↗]  [OMIM ↗]  [AlphaFold ↗]
```

---

### Patient Report Intake Page (SECONDARY — Layer 2)
Accessed via ghost button from the landing page. Separate view.

```css
{
  background: #f1f5f9;
  min-height: 100vh;
  padding: 40px 20px;
}
/* Max width: 580px, centered */
```

Layout:
```
← Back to search

Upload patient data

[Genomic sequencing report]  [Patient clinical history]
     Browse files                  Browse files

─── or ───

[Load demo patient — Sarah Chen (IRD panel, 5 variants)]
```

---

### Patient Report Page (Layer 2 output)
Full report view. Sticky top nav with patient name, MRN, version stamp.
Variant switcher tabs below nav.
Report sections in scrollable content area below.
Max-width: 860px, centered.

---

## Summary — Navigation Flow

```
Landing page (Variant Lookup — PRIMARY)
    │
    ├── [search] → Results appear on same page
    │       └── [Generate patient report →] → Patient Report Intake
    │
    └── [For clinicians: Generate a patient report →]
            └── Patient Report Intake (Layer 2)
                    └── [Load demo / upload] → Patient Report view
```

---

## Eamos Logo Mark

```css
{
  width: 26-30px;               /* 26px in nav, 30px on landing */
  height: 26-30px;
  border-radius: 6-8px;         /* 6px in nav, 8px on landing */
  background: #1D9E75;          /* --teal */
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12-15px;           /* scales with size */
  font-weight: 500;
  color: #ffffff;
}
/* Content: letter "E" */
```

---

## SVG Assets

### ERG Waveform (Clinical Context)
Comparative waveform showing normal eye vs patient.
- ViewBox: `0 0 380 108`
- Width: 100% (responsive)
- Grid lines: stroke #e2e8f0, stroke-width 0.5
- Normal waveform: stroke #1D9E75 (teal), stroke-width 1.5
- Patient waveform: stroke #E24B4A (red), stroke-width 1.5
- Labels: font-size 8-9px, color matches waveform
- Divider: dashed line between normal and patient panels
- Caption: font-size 7px, color #94a3b8

### Pedigree Diagram (Clinical Context)
Four-generation family tree.
- ViewBox: `0 0 310 190`
- Width: 100% (responsive)
- Male: square (rect), fill var(--bg2), stroke var(--text2)
- Female: circle, fill var(--bg2), stroke var(--text2)
- Affected: filled with #E24B4A (red)
- Consanguinity: double line between parents
- Proband arrow: font-size 8px, color #A32D2D, "← Proband"
- Generation labels: font-size 10px, color #475569, font-weight 500
- Legend: font-size 7px, color #94a3b8

---

## Grid Layouts Used

```css
/* Two-column grid (clinical context cards, gene therapy details) */
display: grid;
grid-template-columns: 1fr 1fr;
gap: 10-12px;

/* Three-column grid (sign-off inputs) */
display: grid;
grid-template-columns: 1fr 1fr 1fr;
gap: 12px;

/* Flex wrap (database link buttons, badge groups) */
display: flex;
flex-wrap: wrap;
gap: 8px;

/* Flex column (report sections, recommendation list) */
display: flex;
flex-direction: column;
gap: 9-12px;
```

---

## Responsive Behavior

Desktop first. The tool is used on desktop monitors in clinical settings.
- Report max-width: 860px (patient), 700px (lookup)
- Landing max-width: 580px
- All centered with margin: 0 auto
- Variant tabs: overflow-x: auto (scrollable on small screens)
- Two-column grids collapse gracefully with flex-wrap where needed

---

## What NOT to Do

- No shadows (box-shadow: none)
- No gradients
- No font weights above 500
- No border-radius above 12px (cards) or 8px (buttons/inputs)
- No colors outside the defined palette above
- No emojis or icons (except the "E" logo mark and ↗ for external links)
- No heavy borders — always 0.5px or 1px maximum
- No full black (#000000) — use #1e293b for darkest text
- No pure white backgrounds for the page — use #f8fafc or #f1f5f9
- No centered body text — always left-aligned
- No ALL CAPS text except badge labels and small metadata labels

---

## Quick Reference — Most Used Values

```
Page bg:         #f1f5f9
Card bg:         #ffffff
Card border:     0.5px solid #e2e8f0
Card radius:     12px
Card padding:    16px 20px

Primary color:   #1D9E75  (teal)
Secondary color: #1e3a5f  (navy)
Body text:       #1e293b
Secondary text:  #475569
Hint text:       #94a3b8
Border:          #e2e8f0

Base font:       system-ui, -apple-system, sans-serif
Base size:       14px
Base weight:     400
Strong weight:   500 (never above this)
Line height:     1.6

Section circle:  22px, border-radius 50%, bg #1D9E75
Gap between cards: 12px
Page padding:    16-20px
```

---

## Implementation Status

### Done (through session 9)
- Classification colour system (all 5 tiers + priority + score colours)
- Typography scale (font sizes, weights, line heights)
- Card component + section header + number circle
- Classification badge (.cb) + priority badge (.pb)
- ACMG criteria tags
- Button variants (primary, secondary, navy, ghost, back, search)
- Input / select styling
- Database link buttons (blue pill style)
- Inline source links (dotted underline)
- Table layout + label column
- Clinical integration bullets
- Bottom line / evidence banner
- Info banner
- Gene function / content box
- Upload zone
- Loading state + spinner
- Top navigation bar (report view)
- Variant switcher tabs (cdna-first, classification color)
- ERG waveform SVG
- Pedigree SVG
- Landing page layout (variant lookup as primary product)
- Species toggle (Human active, Mouse "soon" badge)
- Ghost button entry to Patient Report
- "← Back to search" in report intake view

### Still to do (session 10+)
- Font weight audit — ensure no 600/700 weights remain from Tailwind defaults
- Logo placeholder — "E" mark in correct teal, correct size per context
- Species toggle pill shape — verify border-radius matches spec
- Input border-radius — audit all inputs for 8px radius
- Max-width container — enforce 680px/860px/580px limits consistently
- Accessibility — contrast ratios, focus ring styles
- Gene-only search mode — accept bare gene name (e.g. "USH2A") without variant
- Idle state polish — landing page before first search
- Scroll-to-results — auto-scroll after search submission
- Loading skeleton — placeholder cards while lookup runs
- Therapeutic landscape card — gene therapy + clinical trials sections
