# Workspace Rail — design spec

> Status: **draft for review** (Claude, 2026-06-04). Frontend-only; mock-first.
> Supersedes the right-side `/compare` builder rail shipped in `10e22eb`.
> Backend dependencies for the `/report` library are called out for Codex.

## 1. Goal

Adopt the modern-SaaS / AI-tool pattern Steven flagged: **controls on the left,
output on the right**, as one consistent, collapsible rail primitive across the
three product surfaces — so the *output* (table, canvas, report) is the stable
anchor everywhere, and the surfaces read as one system.

References that converged on this: Render / Supabase / Vercel / MarketCap
(left-nav dashboards), the AI-tool canon (Claude, Claude Code, ChatGPT, Grok,
Gemini — persistent left rail: new-action top → scrollable saved list → account
bottom), and **Illustrae** (its "Intelligent Canvas" is literally Excalidraw —
left tools + dominant canvas + a bottom AI prompt-bar).

## 2. Locked decisions (from Steven, 2026-06-04)

1. **Per-surface left controls on `/compare` + `/workbench`.** Top nav stays;
   no global nav sidebar. (`AskUserQuestion` answer: "Per-surface controls".)
2. **`/report` also gets a left rail** — but as a **variant library / worklist**
   (saved variants, folders/favourites, navigation), not just a TOC. The VCF
   output in `/compare` feeds saved variants into this library.
3. **`/report` left rail also carries "Related variants"** — a YouTube-style
   recommendation feed, but evidence-grounded (see §5.3). Collapsible, below the
   worklist.
4. **Design language**: take Illustrae's *layout pattern* + *AI prompt-bar* +
   *iconography/asset style*; **do NOT** take its visual language (rounded
   Assistant/Nunito/Lilita-One playfulness fights our clinical Reading Room).
5. **Everything collapsible**, MarketCap-clean (cards + list metrics).

## 3. The unifying primitive — `<WorkRail>`

One shared component (`app/web/components/layout/WorkRail.tsx`) used by all three
surfaces. Surface-specific content is passed as children; the chrome is identical.

| Property | Value |
| --- | --- |
| Side | left |
| Width | ~336px expanded (matches the existing 360px Workbench SidePanel band) |
| Collapsed | 48px icon rail (icon-only section heads); toggle always present |
| Output | `flex: 1`, fills the remainder; horizontal-scroll/canvas live here |
| Persistence | `localStorage` per surface (`eamos-rail-<surface>-collapsed`) |
| Responsive | `<1200px` auto-collapse to icon rail; `<760px` overlay-on-demand (drawer), never unmount — `display:none` per DESIGN.md |
| Header | surface title + a primary action button at the top (the "new" slot) |
| Motion | enter/collapse via `--dur-2`/`--ease-emphasized`; `prefers-reduced-motion` guard |
| Tokens | product surfaces: `--bg`/`--line` hairline + `--elev-1`; section heads reuse the existing `.side-section-head` chevron pattern |

Sections within the rail are collapsible (reuse the Workbench `CollapsibleSection`
pattern from `SidePanel.tsx`) so a dense rail never crowds.

## 4. Per-surface content

### 4.1 `/compare` — flip the builder rail right → left
The scope builder shipped in `10e22eb` (tabs: **Gene panels** / **Keywords**+file-attach
/ **LLM** coming-soon) + the filter chips move from the right into `<WorkRail>` on
the **left**. The **VariantTable** (split-pane) + **Generate** button become the
right-hand output. Everything else (filter model, panel tags, generate states)
is unchanged — this is a layout move, not a logic change. Lowest-risk surface
(the rail is one day old, mock-first).

### 4.2 `/workbench` — move the function box left
The **360px right SidePanel** (tool params: Scratchpad, Active variant, Transcript,
Protein features, Primer/CRISPR strategy) moves into `<WorkRail>` on the **left**.
The **tool switcher** (Sequence/Primer/CRISPR/Align/Compare — currently in the
horizontal `ContextStrip`) becomes the rail's top section. The **sequence canvas
stays dominant** on the right (Illustrae/Excalidraw model). The bottom-right
floating `AskEamosPill` (the prompt-bar analog) is retained and is the Illustrae
prompt-bar steal.

### 4.3 `/report` — the variant library rail (net-new feature)
A `<WorkRail>` whose content is the user's variant workspace. The report's
centered 920px editorial column stays as-is *inside* the right pane (reading-room
preserved). Sections, top → bottom:

1. **Top action:** `+ Save current variant` · `Import VCF →` (routes to `/compare`).
2. **Worklist / Saved variants** — MarketCap-style cards: gene · HGVS · classification
   dot (the ACMG ramp `--cls-*`). Saved from a `/compare` VCF run or the current
   report. Click → load that report. *(Recommended core.)*
3. **Folders / Collections** — user groupings ("Case 1042", "IRD review", "To sign
   off") + `+ New folder`. The MarketCap "Files" section. Drag a variant in. *(Core.)*
4. **Related variants** — see §5.3. *(Core, collapsible.)*
5. **Compare tray** — pin 2–N variants → "Open in Compare". *(Core.)*
6. **Section nav / jump-to** — scroll-spy over the current report's modules
   (Summary, In-silico, ACMG, Evidence, Conditions, Publications, Trials). *(Secondary.)*

Backlog (not in v1): Recently viewed · Review status (Unreviewed/In review/Signed
off) · Notes badge · `/runs` case linkage · in-worklist quick filters.

## 5. "Related variants" feed (§4.3 #4)

YouTube mechanic, evidence-grounded basis. Lanes, each a small card list
(gene · HGVS · class dot), sourced from data the report already computes:

- **In this gene** — nearby ClinVar variants (already in `<LocusContext>`). Highest relevance.
- **Same condition** — disease-linked variants (already in `<AssociatedConditions>`).
- **Same panel** — variants from the same IRD/Cardiac/Cancer panel (ties to `/compare`).
- **Same class / region** — other P/LP missense in the same domain.
- *(light)* **Frequently reviewed** — small popularity lane, used sparingly.

Guardrail: it is a *clinical discovery affordance*, not engagement-bait — every
recommendation is justified by a real genomic relationship, and the section is
collapsible so a clinician who only wants their worklist is never crowded. v1
ships lanes 1–4 on existing report signals; the popularity lane needs a backend
counter (Codex).

## 6. Visual language

Stay on the Eamos Reading Room system (DESIGN.md). Concretely:
- Rail surface: `--bg` + `0.5px --line` hairline + `--elev-1`; **no** Illustrae
  rounded/playful treatment.
- Cards: the existing `.card` vocabulary; classification dot from `--cls-*`.
- Icons: the rail tool-icon set; adopt Illustrae's *restraint of asset style*
  (clean line icons), not its hand-drawn Excalidraw fonts.
- Illustrae's own palette is logged for reference only: brand teal `#4e8d99` +
  plum `#6d445e` over a Tailwind grey ramp (extracted via `illustrae-pp-cli
  palette`). We keep our `--teal #1D9E75`.

## 7. Component architecture (new/changed)

```
app/web/components/layout/WorkRail.tsx        NEW — the shared primitive (chrome, collapse, persistence, responsive)
app/web/components/layout/WorkRailSection.tsx NEW — collapsible section (or reuse Workbench CollapsibleSection)
app/web/components/compare/CompareClient.tsx  EDIT — wrap builder+chips in <WorkRail>, table → right pane
app/web/components/workbench/WorkbenchShell.tsx EDIT — grid → WorkRail(left) / canvas(right); SidePanel content into rail
app/web/components/workbench/ContextStrip.tsx EDIT — tool switcher relocates into the rail head
app/web/components/report/VariantLibraryRail.tsx NEW — worklist + folders + related + tray + nav
app/web/components/report/RelatedVariants.tsx  NEW — the evidence-grounded lanes
app/web/lib/variant-library.ts                NEW — saved-variant + folder model (localStorage mock-first)
app/web/app/report/*                           EDIT — render the rail alongside the 920px column
app/web/app/globals.css                        EDIT — WorkRail chrome + collapse keyframes (reuse motion tokens)
```

## 8. Build plan (phased, mock-first, each its own gated pass)

0. **`<WorkRail>` primitive** + globals.css chrome + responsive/persistence. Verify: renders, collapses, persists, `<1200px` auto-collapses; tsc 0 / lint 0.
1. **`/compare`** — flip builder+chips into the rail; table → right. Verify: browser on :3000, all filter/generate behavior intact; drag-test chip reorder + split divider.
2. **`/workbench`** — SidePanel → left rail; tool switcher → rail head; canvas stays dominant. Verify: each tool's panel renders left; canvas unobstructed; `<1200px` collapse.
3. **`/report` library rail** — worklist + folders + compare tray + section-nav (mock-first via `variant-library.ts` localStorage). Verify: save-from-compare → appears in report rail → click loads.
4. **Related variants** — lanes 1–4 from existing report signals. Verify: lanes populate for the RPE65 sample; collapsible.

Each phase: durable structural/visual change → **Steven's explicit OK before shipping** (the rail is persistent nav chrome). tsc 0 / lint 0 / browser-verified gate per phase.

## 9. Backend dependencies (Codex lane)

- **Saved-variant + folder persistence** — v1 is FE localStorage mock; durable
  storage (per-account) needs a Supabase table + endpoints. Mock-first until then.
- **"Frequently reviewed" counter** — a view/lookup counter for the popularity lane.
- **Panel membership for "Same panel" related-lane** — rides the `/panels` work
  already planned (P2/P3); reuse `resolveFilterPanel`.

## 10. Out of scope / explicitly NOT doing

- **No global left-nav sidebar** (Vercel/Supabase model) — Steven chose per-surface.
- **No re-layout of the report's 920px editorial column** — the rail sits beside
  it; the reading-room column is preserved (and is load-bearing per DESIGN.md).
- **No Illustrae visual language** (rounded/playful type, hand-drawn fonts).
- **No `/runs` change** — frozen.

## 11. Addendum — output table + cross-surface library (decisions 2026-06-05, Steven)

These sharpen §4 and §5 with decisions made while building Phase 1.

### 11.1 The variant library is GLOBAL, not `/report`-only
The saved-variant store persists across **`/compare` + `/report` + `/workbench`** —
one source of truth (`lib/variant-library.ts`, localStorage mock-first →
per-account Supabase later). The WorkRail renders a shared **"Saved variants"**
section (+ folders) on all three surfaces:
- **`/compare`** — *save into* the library from the filtered output.
- **`/report`** — click a saved variant → load its report (reading room).
- **`/workbench`** — load a saved variant into the sequence viewer to analyse/edit.

Payoff: the worklist travels with you — no re-typing, no re-running the VCF
filter/generate. This elevates the library from a Phase-3 `/report` feature to a
**shared rail section** consumed by every surface's `<WorkRail>`.

### 11.2 `/compare` output-table interactions
1. **Sort** — clickable column headers: Gene (A→Z / Z→A), Variant (by parsed
   position low→high / high→low), # (original order). Paired ▲▼ indicator. **DONE (Phase 1).**
2. **Copy for spreadsheet** — top-right copy button → rich HTML table (Excel/Sheets
   formatted paste) + TSV fallback, via the shared `<CopyButton>`. **DONE (Phase 1).**
3. **Select** — per-row **checkbox** *and* **drag-to-select** a range of rows.
4. **Save selection → library** — two paths, both supported:
   - **Drag-and-drop** the selected rows onto a folder target in the WorkRail.
   - **Copy/paste shortcut** (Cmd/Ctrl+C on the selection → paste into a focused folder).
   - Plus a plain **"Save selected (N) →"** button as the always-available baseline.

   Note: "copy *for spreadsheet*" (11.2 #2, TSV/HTML to the OS clipboard) and
   "copy *to save into the library*" (11.2 #4, an in-app selection move) are
   **distinct semantics** — keep them as separate affordances so neither overloads
   the other.

### 11.3 Landing — sample VCF pill
Beside the hero "Try" report pills (`USH2A c.2276G>T` …), add a **sample-VCF pill**
that loads a small sample VCF stash and routes to `/compare` pre-filtered +
auto-generated — the cohort analog of the sample variant-report pills.
