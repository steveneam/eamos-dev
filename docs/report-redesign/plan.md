# Eamos `/report` v3 redesign — IMPLEMENTATION PLAN (file-by-file)

> Companion to `docs/report-redesign/spec.md` (source of truth). Build = **one
> pass** after design. Active frontend = **Next.js 16 at `app/web/`** (NOT the
> legacy Vite `app/frontend/`). All paths below are under `app/web/` unless
> stated. **Read-only on code while planning; this doc is the only output.**
>
> Conventions in force:
> - **Mock-first**: every backend-gated metric ships with an explicit, tasteful
>   "needs live data" marker — never a silent fake number.
> - **Design tokens only** — reuse `--cls-*` / `--info-*` / `--teal-*` / `--ink-*`
>   ramps already in `globals.css`; no new hex.
> - **Contract parity**: any change to `app/web/lib/backend.ts` MUST be mirrored
>   byte-identical in `app/frontend/src/lib/backend.ts` (verified identical at
>   HEAD). **This plan makes NO contract changes** — all new fields are Codex's
>   to add (see §10). FE reads them defensively (optional, `?? null`).
> - Never commit/push; never touch `/runs` or `app/frontend/**`.

---

## 0. Verified ground truth (what already exists — don't rebuild)

These were confirmed by reading the live code; they materially shrink the work:

1. **Card colour is ALREADY in the contract, per card.** Every
   `ReportCallCard` carries `ui_color_theme: string`
   (`app/web/lib/backend.ts` L666). The RPE65 fixture proves all four cards emit
   a real theme today:
   - `population_frequency` → `neutral_slate_state`
   - `computational` → `risk_red_state`
   - `lab_functional` → `neutral_slate_state`
   - `clinical_consensus` → `caution_orange_state`
   The FE simply **ignores** `ui_color_theme` for 3 of the 4 cards
   (`CallCardsGrid.tsx` L104-105 gates `fnTheme` on `card_id === 'lab_functional'`).
   → Colouring all 4 is a pure FE change reusing the existing field + the
   existing `STATE_THEME` map. **No backend dependency for card colour.**

2. **Backend can emit `caution_orange_state`** (3 occurrences in
   `app/backend`), but the FE `STATE_THEME` map (`CallCardsGrid.tsx` L23-30)
   has only `caution_yellow_state`. The full backend set is:
   `danger_red_state, risk_red_state, caution_yellow_state, caution_orange_state,
   safe_green_state, info_blue_state, neutral_slate_state`. The map must cover
   **all 7** or cards silently fall back to white (`?? null`).

3. **ExpertPanelSection already renders the VCEP written rationale inline**
   (`data.narrative`, L192-194) + criteria chips with hover rationale
   (`CriterionChip` `title=`, L75-83). The Clinical-section spec item "VCEP
   rationale inline" is **already satisfied**; §3 work is reorder + tooltips,
   not new rationale rendering.

4. **ClinVarBlock already renders** classification + review status + submitter
   **count** stacked bar + conditions/consequence free-text (`ClinVarBlock.tsx`).
   What is missing is per-submitter **free-text interpretation** — backend-gated.

5. **Save already exists and is wired to the variant-library store**:
   `SaveCurrentButton` (`VariantLibraryRail.tsx` L44-82) calls `saveVariant(...)`
   from `@/lib/variant-library` and is already mounted in the WorkRail `action`
   slot (`ReportClient.tsx` L479). The hero "Follow" button
   (`VariantHeader.tsx` L198-209) is a **dead local-state toggle** — it must be
   re-pointed at this exact save path, NOT a second save system.

6. **`MatrixOverture` has only 3 real consumers**: `ReportClient.tsx`,
   `MatrixOverture.tsx`, `MatrixTile.tsx`. (`classification.ts` L9 only *mentions*
   `MatrixTile` in a comment — not a code dependency.) Safe to remove.

7. **`pLI` and `LOEUF` already flow** via the `molecular_context` evidence row
   (`MolecularContextBlock.tsx` reads `gnomad_constraint.{loeuf,pli}`;
   `MolecularContextSection.loeuf` L858). **Constraint Z-scores `mis_z`/`lof_z`
   are NOT anywhere in the contract** → backend-gated.

8. **rsID is NOT in the contract** (`VariantReportHeader` L819-830 and
   `VariantSummaryRow` L57-64 have no rsID/dbSNP field). MANE-select flag is
   also not explicit. Build is implicitly hg38 (`genomic_hg38`). So in the hero
   details disclosure: coords/HGVS/transcript/build/consequence are FE-now;
   **rsID + explicit MANE flag are backend-gated**.

9. **Section anchors live in TWO places that must stay in sync**:
   - `ReportClient.tsx` `ReportBody`: `<div id="…" className="scroll-mt-24" />`
     anchors + numbered `<Card number={n}>`.
   - `ReportSectionNav.tsx` L13-22: a **hardcoded `ANCHORS` array** (id+label,
     in the OLD order) driving the rail "On this page" scroll-spy.
   The reorder is incomplete unless BOTH are updated. The card-deep-link
   scroller (`CallCardsGrid.scrollToInteraction`, L57-64) resolves
   `card.interaction.target_*` against `document.getElementById` — those target
   ids must keep existing.

---

## 1. Remove `MatrixOverture`

**Goal:** the 4 cards become the only top display. No orphaned imports, anchors,
or deep-link targets.

### Files
- **`components/report/ReportClient.tsx`**
  - **Remove** the import line **L30**: `import { MatrixOverture } from '@/components/report/MatrixOverture'`.
  - **Remove** the render at **L718-722** (the JSX comment block + `<MatrixOverture key={\`matrix-${variantKey}\`} payload={payload} request={summaryRequest} />`).
  - `summaryRequest` is STILL used by `effectiveSummaryRequest`/LazySection (L613-631, L780, L835, L970) — **keep the `summaryRequest` prop and the `useMemo` at L249-264.** Only the MatrixOverture consumer goes away. Verify no unused-var lint after removal: `summaryRequest` remains referenced, so no further cleanup needed there.
- **`components/report/MatrixOverture.tsx`** — **delete the file.**
- **`components/report/MatrixTile.tsx`** — **delete the file** (only `MatrixOverture` imports it; confirmed by graphify edge `MatrixOverture.tsx --imports--> MatrixTile()`).
- **`components/ui/CarouselDots.tsx`** — **KEEP.** Still imported by `CallCardsGrid.tsx` L3. Do not delete.
- **`lib/classification.ts`** — **no change.** L9 only references `MatrixTile` in a doc comment; leave the comment or trim the stale clause (cosmetic, optional — note as dead-comment, don't expand scope).

### Verify
- `grep MatrixOverture|MatrixTile app/web` returns only the comment in `classification.ts`.
- No `target_section_id`/`target_panel_id` on any call card points at a tile-only anchor (cards point at the numbered section anchors, which survive).

**FE-now.** No backend.

---

## 2. Reorder `ReportBody` sections → Clinical · In-silico · Population · Gene&locus · Disease · Publications · Trials · AI

**Goal:** reorder while **preserving LazySection lazy-loading, React keys, and
section anchor IDs**. This is the highest-risk mechanical change.

Current order (`ReportClient.tsx` L724-1036): 1 Population (L730) · 2 In-silico
(L751) · 3 Clinical (L793) · 4 Gene&locus (L849) · 5 Disease (L916) ·
6 Publications (L951) · 7 Trials (L991) · 8 AI (L1014).

Target order: **1 Clinical · 2 In-silico · 3 Population · 4 Gene&locus ·
5 Disease · 6 Publications · 7 Trials · 8 AI.**

→ Only the **first three** move: Clinical (was 3) to slot 1, In-silico (was 2)
stays slot 2, Population (was 1) to slot 3. Gene&locus..AI keep relative order
and slots 4-8. This is a **block reorder of three JSX blocks**, not a rewrite.

### Exact mechanics (preserve everything)

For each moved block, move it **verbatim** (anchor `<div>` + `<Card>` +
`LazySection`/children) — do **not** re-derive contents. Then fix three things:

1. **`Card number={n}`** — renumber so the on-page numbering matches the new
   order:
   - Clinical block (currently `number={3}`, L798) → `number={1}`.
   - In-silico block (`number={2}`, L759) → stays `number={2}`.
   - Population block: today it's `Card number={1}` (L734); → `number={3}`.
   - Gene&locus `4`, Disease `5`, Publications `number={6}` (passed to `PubMedSection` L977), Trials `number={7}` (L996), AI `8` (L1018) — **unchanged**.
2. **Anchor `<div id=…>`** — keep each block's existing `id` attached to that
   block as it moves (so deep-links + scroll-spy still resolve):
   - Clinical: `id="clinical_evidence"` (L797) moves with the block to slot 1.
   - In-silico: `id="evidence_by_source"` (L757) stays slot 2.
   - Population: `id="population_frequency"` (L731) moves to slot 3.
   **Do not renumber/rename ids** — `card.interaction.target_section_id` and
   `ReportSectionNav` both key on these literal strings.
3. **`LazySection` keys + props** — move them **with their block, untouched**.
   - Clinical wraps `clingen_vcep` LazySection (key `vcep-${variantKey}…`, L828).
   - In-silico wraps `computational_deep_dive` LazySection (key `insilico-…`, L773).
   - Population is **not** lazy (it reads `populationSection` eagerly, L732-749).
   Keys are derived from `variantKey` + lazy-override suffix; they are
   **position-independent**, so reordering does not affect remount behaviour.
   The IntersectionObserver inside `LazySection` fires on viewport entry
   regardless of DOM order. **No key changes needed.**

### `populationTarget` / `populationSection` guards
`populationTarget` + `populationSection` (L678-683) are computed once at the top
of `ReportBody` — **leave them where they are**; only the JSX that consumes them
(the slot-3 block) moves. The `{populationSection && (...)}` conditional moves
intact (L732-749).

### `ReportSectionNav.tsx` — MUST update the hardcoded list
**`components/report/ReportSectionNav.tsx` L13-22**: reorder the `ANCHORS`
array to the new section order so the rail "On this page" list and scroll-spy
match:
```
clinical_evidence  → "Clinical evidence"
evidence_by_source → "In-silico predictions"
population_frequency → "Population frequency"
gene_context       → "Gene & locus"
associated_conditions → "Disease & conditions"
publications       → "Publications"
trials             → "Trials"
ai_summary         → "AI summary"
```
(Labels already exist; just reorder rows. The two extra anchors
`curated_variants` (L922) is not in this nav and stays as-is.)

### Verify
- All 8 `id`s still present in the DOM; deep-link scroller + rail nav land on the right block.
- LazySection still lazy-fetches `clingen_vcep` / `computational_deep_dive` (test `?lazy=clingen_vcep` + `?lazy=computational_deep_dive` force-load hatch still fires).
- Card numbers read 1→8 top to bottom.

**FE-now.** No backend.

> **Risk:** the numbered `<Card>` prop, the anchor `<div id>`, and
> `ReportSectionNav.ANCHORS` are three separate sources of truth for order.
> Update all three in the same pass or the nav/deep-links desync.

---

## 3. `CallCardsGrid` — colour all 4 cards + reorder Computational · Clinical · Population · Lab&Functional

**Goal:** every card is fully tinted by its own `ui_color_theme` (today only
`lab_functional`), and the cards render in the spec order.

### File: `components/report/CallCardsGrid.tsx`

**3a. Extend `STATE_THEME` to all 7 backend states** (L23-30). Add the missing
`caution_orange_state` key (maps to the LP/orange ramp — reuse `--cls-lpath-*`
or, if a distinct orange token is wanted, validate in design; default to
`--cls-lpath-*`). Confirm all 7 keys present:
```
danger_red_state    → --cls-path-*
risk_red_state      → --cls-lpath-*
caution_orange_state→ --cls-lpath-*   (ADD — currently missing)
caution_yellow_state→ --cls-vus-*
safe_green_state    → --cls-ben-*
info_blue_state     → --info-*
neutral_slate_state → --cls-na-*
```

**3b. Derive `theme` for EVERY card, not just functional** (L104-105). Replace:
```
const isFunctionalCard = card.card_id === 'lab_functional'
const fnTheme = isFunctionalCard ? STATE_THEME[card.ui_color_theme] ?? null : null
```
with a generic per-card theme lookup:
```
const cardTheme = STATE_THEME[card.ui_color_theme] ?? null
```
Then drive the card surface (`<article>`/`<button>` `background`+`border`,
L201-207 and L246-256) and the verdict-badge chip styling (L113-124) off
`cardTheme` for all cards. **`neutral_slate_state` cards** (e.g. "No
Population/Functional Data") tint to the calm grey `--cls-na-*` — which reads as
"no call yet", exactly right.

**3c. Keep the functional-only extras gated** — `fnMetrics`, `verdictAttr`,
`fnNote`, the "via ClinGen/ClinVar" attribution, and "Code rests on N of M"
(L106-127) are sourced from `functional_evidence.display_metrics`, which only
exists for the functional card. Keep `card_id === 'lab_functional'` gating those
extras only; the *colour* is now generic. (i.e. split "is functional" from "has
theme": all cards get theme; only functional gets the metrics text.)

**3d. Reorder the cards L→R: Computational · Clinical · Population · Lab&Functional.**
`payload.call_cards.cards` order is **backend-driven** (the FE maps in array
order, L92). Today's fixture order is population, computational, lab_functional,
clinical_consensus — i.e. **NOT** the spec order. Two options:
- **Chosen (FE re-sort, robust):** sort `cards` in the FE by a fixed
  `CARD_ORDER` index before mapping, so order is deterministic regardless of
  payload order:
  ```
  const CARD_ORDER: ReportCallCardId[] = ['computational','clinical_consensus','population_frequency','lab_functional']
  const cards = [...(payload.call_cards?.cards ?? [])].sort(
    (a,b) => CARD_ORDER.indexOf(a.card_id) - CARD_ORDER.indexOf(b.card_id))
  ```
  Unknown ids (none today) sort last. This is a 4-line FE change; no backend
  dependency, and it survives Codex re-ordering the payload later.
- Rejected: relying on Codex to emit the order — couples FE display to backend
  array order and silently breaks if the payload order drifts.

**3e. Per-card verdict-state SOURCE (for tooltips + colour) — confirmed:**
| Card | `card_id` | colour/verdict source |
| --- | --- | --- |
| Computational | `computational` | `ui_color_theme` (backend, calibrated damaging↔benign ramp) — already `risk_red_state` etc. |
| Clinical | `clinical_consensus` | `ui_color_theme` (ACMG/ClinGen ramp) — already `caution_orange_state` etc. |
| Population | `population_frequency` | `ui_color_theme` (AF-class ramp) — already `neutral_slate_state` etc. |
| Lab & Functional | `lab_functional` | `ui_color_theme` (functional-state ramp) + `functional_evidence.display_metrics` extras |
All four colour states come from the **same backend `ui_color_theme` field** —
no per-axis FE derivation needed. The FE only maps the string → tokens.

**Verify:** all 4 cards tinted in the RPE65 fixture (red computational, orange
clinical, grey population, grey functional); order reads Computational, Clinical,
Population, Lab&Functional; functional "via ClinGen" + "code rests on" still show.

**FE-now.** No backend (colour + order both satisfiable from existing payload).

---

## 4. Slim hero + expandable details disclosure + Follow→Save

**Goal:** the hero stays a slim identity bar; a `<details>`/disclosure reveals
full coords / all HGVS / transcript(MANE) / build / rsID / consequence; the dead
"Follow" toggle becomes a real **Save** wired to the existing library store.

### Hero markup location
`components/report/VariantHeader.tsx` — the whole `<header>`/`<section
className="variant-header-card">` (L90-317). It is rendered by `ReportBody` at
`ReportClient.tsx` L712-716.

### 4a. Slim the bar (`VariantHeader.tsx`)
- Keep line 1 (`{gene} {proteinChange}`, L133-151) and the classification badge
  cluster (L188-196). The DNA-primary spec ("`GENE c.cdna`") — surface `c.cdna`
  next to the gene: today the title shows `gene` + `proteinChange` and the meta
  line (L152-170) shows `[transcriptHgvs, genomic, consequence]`. Promote the
  `c.` portion (split `transcriptHgvs` on `:`) into the headline next to the
  gene, demote `p.` to muted — matches the spec hero "GENE c.cdna (primary) ·
  p.consequence (muted)". Reuse `row.transcript_hgvs?.split(':').pop()`.
- **Move the full meta** (`transcriptHgvs · genomic · consequence`, L152-170) +
  the "Open in" cross-DB chips (L172-185) **into the details disclosure** so the
  resting bar is slim. The cross-DB chips (`buildCrossDbChips`, L19-49) stay —
  just relocate inside the disclosure.

### 4b. Add the expandable details disclosure (`VariantHeader.tsx`)
Add a `<details>` (or a controlled disclosure with `aria-expanded`) below the
slim identity line. Contents, all from **existing payload fields**:
| Field | Source | FE-now? |
| --- | --- | --- |
| Genomic coords (chr:pos hg38) | `row.genomic_hg38` (L80) | FE-now |
| VCF form (`1-68444869-T-C`) | derive from `genomic_hg38` (already in that shape per fixture) | FE-now |
| HGVS c. | `transcript_hgvs.split(':')[1]` / header.cdna | FE-now |
| HGVS p. | `row.protein_change` | FE-now |
| HGVS g. | `row.genomic_hg38` if g.-form present, else omit | FE-now (omit if absent) |
| Transcript / MANE | `header.transcript` (transcript yes; MANE flag) | transcript FE-now; **MANE flag backend-gated (mock+label)** |
| Genome build | literal "GRCh38 / hg38" (no build field; hg38 is the only build) | FE-now (static label) |
| rsID | — **not in contract** | **backend-gated (mock+label "needs live data")** |
| Consequence | `row.consequence ?? row.variation_type` | FE-now |
Use the design-system disclosure pattern (caret + `aria-expanded`); keyboard
reachable. rsID + MANE rows render a tasteful "needs live data" marker until §10
ships them.

### 4c. View-count + last-updated in the slim bar
Spec wants "view-count + last-updated (mock+label)" in the hero. Add a small
muted cluster next to the classification badge. Both are **backend-gated** →
render a mock value with an explicit marker (e.g. a dotted-underline `title`
"Estimated — live view counts not yet wired"). See §10.

### 4d. Follow → Save (wire to existing library save)
**Do NOT invent a second save system.** The existing save is
`SaveCurrentButton` (`VariantLibraryRail.tsx` L44-82) → `saveVariant()` from
`@/lib/variant-library`, already mounted in the WorkRail action slot
(`ReportClient.tsx` L479). Two clean options:
- **Chosen:** delete the dead Follow `<button>` (L198-209) and its `followed`
  state (L86) from `VariantHeader.tsx`, and render `<SaveCurrentButton>` (or a
  hero-styled variant of it) in the hero tools cluster. Because the hero only
  has `payload` (not the full `LookupResponse`), either (a) pass `data` down to
  `VariantHeader` from `ReportBody` (it already has `data`, L587), or (b) extract
  the `saveVariant` call + `reportIdentity`-style identity derivation into the
  hero using `payload` only. Prefer **(a)**: thread `data` into `VariantHeader`
  and reuse `SaveCurrentButton` verbatim so there is exactly one save path and
  the "Saved" state stays in sync with the rail button via the shared
  `useLibrary()` store.
- Rejected: keeping a local `followed` toggle — it persists nothing and
  duplicates intent.
Match the existing `v-tool` button styling so it sits in the tools row with
Export/Share. Keep label **"Save" / "Saved"** (icon `IconPlus`/`IconCheck`).

### 4e. Optional 4-segment hero colour strip
Spec: "Validate in design: a thin 4-segment colour strip in the hero previewing
the 4 cards." This is **design-validated, not committed** — if design keeps it,
build it from `payload.call_cards.cards` mapped through the same `STATE_THEME`
(reuse §3's map; do not duplicate). Mark as optional in design.md; if dropped,
no code.

**FE-now** except: rsID, MANE flag, view-count, last-updated (mock+label → §10).

---

## 5. `PublicationsCallout`: variant-scope Google Scholar → PubMed

### File: `components/report/PublicationsCallout.tsx` (L148-163)
The spec's "~L149-161" maps to the **variant-scope** outbound link, currently
"Google Scholar" using `data.scholar_url` (L149-162). Change the variant-scope
link to **PubMed**:
- Build a PubMed URL for the variant scope (mirror the gene-scope pattern at
  L43-47): prefer a backend-supplied variant PubMed query if present; else
  construct `https://pubmed.ncbi.nlm.nih.gov/?term=<gene cdna/protein>` from the
  props the callout already receives indirectly (it has `geneSymbol`; the
  variant terms are in `data` — if no variant query string is exposed, use a
  `geneSymbol`-scoped fallback and label it).
- Change the visible label "Google Scholar ↗" → "PubMed ↗".
- `data.scholar_url` becomes unused for the variant link — leave the contract
  field (don't touch `backend.ts`); it may still be exported. Note as
  now-unused-by-FE, do not remove from the type.

The gene-scope branch (L164-178) already uses PubMed — leave it. Add `title`/
`aria-label` per §7.

**FE-now.** (If a dedicated variant-scoped PubMed `term` is wanted from the
backend rather than a client-built query, that's an optional §10 enhancement —
not required to ship the label/link swap.)

---

## 6. Related-variants 2-line YouTube-style card redesign

**Goal:** each related-variant row becomes a 2-line card: line 1 = `GENE c.cdna`
+ New/Updated pill; line 2 = mini 4-colour chip row (mirrors the 4 main cards) +
views + last-updated.

### Components
- **`components/report/RelatedVariants.tsx`** — the lanes ("In this gene", "Same
  class · region", "Same condition", "Same panel"), built from
  `locus_context.nearby_variants` + `associated_conditions` + bundled panels.
  **No new fetch** (it reuses report data).
- **`components/library/VariantCardRow.tsx`** — the shared presentational row
  used by BOTH saved-variant cards and related lanes. It is the **canonical row**
  (class dot · gene · compact HGVS + caret to full HGVS). Changing it affects the
  saved-variant cards too.

### Approach
Because `VariantCardRow` is shared, do **not** overload it with related-only
chrome. Build the 2-line treatment as a related-variant-specific wrapper in
`RelatedVariants.tsx` (the `nearbyRow` renderer, L58-76), keeping
`VariantCardRow` for line 1's identity (it already gives `GENE · c.cdna`):
- **Line 1:** existing `VariantCardRow` (gene + hgvs + open) + a **New/Updated
  pill** (backend-gated; mock+label).
- **Line 2:** a new mini chip row:
  - **4-colour chip row** mirroring the 4 main cards' verdict states for THAT
    variant. Per-variant 4-axis states are **not in `NearbyVariant`**
    (`backend.ts` L434-440 has only `cds_pos, classification, hgvs, clinvar_id,
    protein_change`). → **backend-gated**: render 4 mini chips driven by mock
    states + an explicit "illustrative — per-variant calls not yet wired" marker
    on the lane. Reuse §3's `STATE_THEME` token map so the mini chips match the
    big cards exactly (single source of colour truth).
  - **views** + **last-updated** — also not in `NearbyVariant` → backend-gated
    mock+label.
  - **New/Updated pill** — needs per-variant `created_at`/`updated_at` →
    backend-gated mock+label.

### Styling
The `lib-related-row` / `lib-related-add` / `lib-lane*` classes already exist
(used in `RelatedVariants.tsx`); add the 2-line layout + mini-chip classes in
the same stylesheet that defines `lib-related-*` (find via the existing class
usage — likely a shared library CSS). Keep tokens.

**FE shell now; all the new line-2 data (4-axis states, views, last-updated,
New/Updated) is mock+label until §10.** The card *structure* ships now; the
numbers are honestly marked as illustrative.

---

## 7. Cross-cutting tooltip / affordance pass (`title` + `aria-label`)

**Goal:** every toggle, button, and jargon label that needs one gets a plain-
language hover pop-out — same pass as the Workbench. Tooltips explain *what the
control does* or *what the term means*, never restate the label. Keyboard-
reachable; not hover-only for anything critical.

Enumerated targets + file:
| Control / label | File | Note |
| --- | --- | --- |
| 4 card verdict states (each card surface + verdict badge) | `CallCardsGrid.tsx` | `aria-label` on `<article>`; `title` on verdict badge explaining the state (e.g. "Calibrated computational call: damaging") |
| AF-class chips (BA1/BS1/PM2) | Population section (`PopulationFrequencySection.tsx` + new Franklin AF block) | define each code in plain language |
| Constraint Z-score / LOEUF / pLI | `MolecularContextBlock.tsx` (L134-163) | LOEUF/pLI exist now; add `title` defining each; Z-score row is mock+label |
| ACMG criterion chips | `ExpertPanelSection.tsx` (`CriterionChip`, already has rationale `title` L83) + `AcmgCriteriaFold.tsx` | extend the InterVar fold chips with the same |
| ClinGen / ClinVar review-status (stars) | `ClinVarBlock.tsx` (L111-113), `ExpertPanelSection.tsx` (`FreshnessChip` already has `title`) | define "review status / star rating" |
| Variant/Gene publication toggle | `PublicationsCallout.tsx` (L62-77) | `title`/`aria-label` "Scope publications to this variant / the whole gene" |
| Save / Export / Share cluster | `VariantHeader.tsx` (L197-245) | Share already has `aria-label`; add `title` to Save + Export |
| New / Updated pills | `RelatedVariants.tsx` | "Added/updated in the last N days (illustrative)" |
| "needs live data" markers | everywhere a mock metric renders | `title` explaining why it's a placeholder |
| Abbreviations (HGVS, MANE, VCEP, LOEUF, pLI, CADD, REVEL, SpliceAI) | hero details + relevant sections | `<abbr title="…">` or dotted-underline `title` |
| Cross-DB "Open in" chips | `VariantHeader.tsx` (L172-185) | `title` "Open this variant in ClinVar/gnomAD/…" |

Use a consistent affordance (dotted underline for term-definitions; `title`+`aria-label` for controls). Apply **ui-ux-pro-max + frontend-design** intuitiveness review in design.md (clear affordances, one obvious primary action per cluster, no unexplained jargon).

**FE-now.**

---

## 8. Single-pass build order

Do it in this order to minimise churn and keep the tree compiling between steps:

1. **§1 Remove MatrixOverture** (delete 2 files, 2 edits in ReportClient). Smallest, unblocks the top area. Verify build.
2. **§3 CallCardsGrid** (theme map + generic theme + CARD_ORDER sort). Self-contained; produces the new top display the spec wants.
3. **§2 Reorder ReportBody** (move 2 blocks, renumber Cards, update `ReportSectionNav.ANCHORS`). Do after §1 so there's no MatrixOverture in the moved region. Verify all anchors + lazy hatch.
4. **§4 Hero** (slim + details disclosure + Follow→Save via threaded `data`/`SaveCurrentButton` + mock view/updated). Touches VariantHeader + a prop thread in ReportBody.
5. **§5 PublicationsCallout** Scholar→PubMed (tiny).
6. **§6 RelatedVariants** 2-line redesign + mini chip row reusing §3's token map (so §3 must land first).
7. **§7 Tooltip/affordance pass** last — sweeps every touched + adjacent control once the structure is final.
8. **Design pass (ui-ux-pro-max + frontend-design)** validates the hero strip (§4e), Franklin AF visual (Population), and overall intuitiveness — fold into design.md, applied across 2-7.

Rationale: §3 ships the shared `STATE_THEME` map that §4e and §6 reuse, so it lands before its consumers. §2 lands after §1 to avoid moving dead code.

---

## 9. Biggest risks / unknowns

1. **Tri-source section ordering (§2).** Card `number` props, anchor `<div id>`,
   and `ReportSectionNav.ANCHORS` are three independent order sources. Miss one
   → broken deep-links or a desynced rail nav. Mitigate: change all three in the
   same commit; verify each anchor resolves.
2. **Card order is backend-array-driven (§3d).** The fixture order ≠ spec order.
   FE re-sort via `CARD_ORDER` is the safe fix; if instead we rely on Codex to
   reorder the payload, FE display silently breaks if the payload drifts. Chosen:
   FE sort.
3. **`caution_orange_state` gap (§3a).** The map currently lacks it; the live
   clinical card uses it. If not added, the Clinical card silently renders white.
4. **Full-bleed layout (`CenteredMain bleed`, ReportClient L481/561-573).** The
   ready report runs full-width (no narrow frame). The widened hero + 4-up cards
   already use this; the reordered sections inherit it. Watch that the slimmed
   hero + details disclosure don't overflow at the full-bleed width and that the
   `variant-header-card` mobile breakpoint (L283-314) still holds.
5. **LazySection IntersectionObserver after reorder.** Moving the Clinical
   (`clingen_vcep`) block to the top means it's in-viewport on load → it will
   eager-resolve via IO immediately. That's fine functionally, but confirm the
   `?lazy=` force-load hatch and the `ExpertPanelPartialNote` empty/error views
   (ReportClient L84-104, L840-841) still behave. Keys are position-independent,
   so no remount surprises.
6. **Hero Save needs `data`, hero only has `payload`.** Threading `data` into
   `VariantHeader` (chosen) is clean but adds a prop; the alternative
   (re-deriving identity from `payload`) risks a second, drifting save path.
   Must reuse `saveVariant` + `useLibrary` so the hero and rail "Saved" states
   stay in sync.
7. **Mock honesty.** Every backend-gated value (rsID, MANE flag, view count,
   last-updated, per-variant 4-axis chips, New/Updated pills, constraint
   Z-score, submitter free-text) must carry a visible marker. Risk = a
   placeholder shipping as a silent fake number. Enforce one shared "needs live
   data" affordance.
8. **Contract parity.** This plan changes NO contract. If any sub-task tempts a
   `backend.ts` field add, STOP — it's Codex's (§10), and both `backend.ts`
   files must stay byte-identical.

---

## 10. Codex backend handoff (fields / endpoints needed)

All FE shells ship mock+label now; these make them live. Each new field is
**optional** so the FE keeps rendering during rollout. **Any type added here must
be mirrored byte-identical in BOTH `app/web/lib/backend.ts` and
`app/frontend/src/lib/backend.ts`.**

| # | Need | Extends which `backend.ts` type | Notes |
| --- | --- | --- | --- |
| 1 | **View count** (per variant) | `VariantReportHeader` (L819) — add `view_count?: number \| null`; or a new `report_metrics` block on `ReportPayload` | Drives hero view-count + related-card views |
| 2 | **Last-updated** timestamp (per variant) | `VariantReportHeader` — add `last_updated?: string \| null` (ISO) | Hero + related cards |
| 3 | **New / Updated** timestamps | `NearbyVariant` (L434) — add `created_at?`/`updated_at?` (ISO) | Drives the New/Updated pill (compute "new" vs "updated" in FE from age) |
| 4 | **Per-related-variant 4-axis states** | `NearbyVariant` — add `axis_states?: { computational?: string; clinical?: string; population?: string; lab_functional?: string } \| null` using the same `ui_color_theme` vocabulary | Drives the mini 4-colour chip row; reuse the 7-state theme strings |
| 5 | **Constraint Z-scores `mis_z` / `lof_z`** | `MolecularContextSection` (L850) — add `mis_z?: number \| null`, `lof_z?: number \| null` (already has `loeuf`); and/or the `gnomad_constraint` evidence summary read by `MolecularContextBlock` | pLI + LOEUF already flow; only Z-scores are missing |
| 6 | **ClinVar submitter free-text interpretation** | the `clinvar` evidence row `summary` (read in `ClinVarBlock`) — add per-submitter `interpretation`/`comment` text alongside the existing numeric `submitter_counts` | Spec wants "submitter interpretation text inline" |
| 7 | **Pub-graph per-year counts (variant AND gene)** | `PublicationScopeCounts` / `PublicationsCallout` (publications types) — add `per_year?: { year: number; count: number }[]` for BOTH `variant` and `gene` scopes | Spec §6 "pub graph reflects both variant and gene" |
| 8 | **rsID** (dbSNP) | `VariantReportHeader` (L819) and/or `VariantSummaryRow` (L57) — add `rsid?: string \| null` | Hero details disclosure |
| 9 | **MANE-select flag** | `VariantReportHeader` — add `is_mane_select?: boolean \| null` (or `mane_transcript?: string`) | Hero details "transcript / MANE" |
| 10 | *(optional)* **Variant-scoped PubMed `term`** | `PublicationsCallout`/`PublicationScopeCounts` — add `variant.query` like the existing gene-scope `query` | Lets §5's PubMed link use a curated variant term instead of an FE-built one |

Codex also owns the live-verify + Render redeploy loop once these land (per the
standing Codex-backend handoff rule).

---

## Appendix — files touched (FE, this plan)

| File | Change | §|
| --- | --- | --- |
| `components/report/ReportClient.tsx` | remove MatrixOverture import+render; reorder 3 section blocks + renumber Cards; thread `data` into VariantHeader | 1,2,4 |
| `components/report/MatrixOverture.tsx` | **delete** | 1 |
| `components/report/MatrixTile.tsx` | **delete** | 1 |
| `components/report/ReportSectionNav.tsx` | reorder `ANCHORS` | 2 |
| `components/report/CallCardsGrid.tsx` | full 7-state theme map; generic per-card theme; `CARD_ORDER` sort | 3 |
| `components/report/VariantHeader.tsx` | slim bar; details disclosure; Follow→Save (SaveCurrentButton); view/updated mock | 4 |
| `components/report/PublicationsCallout.tsx` | variant-scope Scholar→PubMed | 5 |
| `components/report/RelatedVariants.tsx` | 2-line card + mini 4-colour chip row + pills/views/updated (mock) | 6 |
| (shared library CSS for `lib-related-*`) | 2-line + mini-chip styles | 6 |
| multiple (table in §7) | `title`/`aria-label` tooltip pass | 7 |
| `lib/backend.ts` (web) + `lib/backend.ts` (frontend) | **NO CHANGE this plan** — Codex owns §10 | — |
