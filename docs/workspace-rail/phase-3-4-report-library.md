# Phase 3 + 4 — `/report` variant-library rail & related-variants feed

> Status: **draft for review** (Claude, 2026-06-05). Frontend-only; mock-first.
> Builds on the shipped `<WorkRail>` primitive (Phase 0) + `lib/variant-library.ts`
> store. Implementation plan for spec.md §4.3 + §5 + §11. **No code is written
> until Steven OKs this doc.** Each durable (structural/visual) change is gated on
> Steven's explicit go-ahead before shipping (§6).

---

## 0. Scope & non-goals

**In scope (this spec):**
- Phase 3 — the `/report` `<WorkRail>` left rail: Save action, Saved-variants
  worklist, Folders/Collections, Compare tray, Section nav. Mock-first on the
  existing `lib/variant-library.ts` localStorage store.
- Phase 4 — the evidence-grounded Related-variants feed (lanes 1–4 from existing
  report signals; popularity lane flagged for Codex).
- The **shared** "Saved variants" rail section that also mounts on `/compare`
  + `/workbench` (§11.1), extracted so all three surfaces render one component.

**Non-goals (unchanged from spec.md §10):**
- No re-layout of the report's editorial column. The `--maxw-report-frame`
  reading column is load-bearing (DESIGN.md) and becomes the WorkRail **output**
  verbatim — its internal markup is not touched.
- No durable per-account persistence in this phase (Supabase is §5 backend lane).
- No Illustrae visual language. No `/runs` change.
- The store API (`getLibrary/saveVariants/removeVariant/isSaved/subscribe`) is
  **not** redesigned. We *extend* it (folder CRUD, single-save) additively.

---

## 1. Component architecture

### 1.1 New files

```
app/web/components/library/LibrarySection.tsx     NEW — the SHARED rail section: Saved
                                                       variants + Folders + Compare tray.
                                                       Consumed by all three surfaces.
app/web/components/library/SavedVariantCard.tsx    NEW — one MarketCap-style card
                                                       (gene · HGVS · class dot · remove).
app/web/components/library/useLibrary.ts           NEW — useSyncExternalStore hook over
                                                       the store's subscribe()/getLibrary().
app/web/components/report/VariantLibraryRail.tsx   NEW — the /report rail body: composes
                                                       <LibrarySection/> + <RelatedVariants/>
                                                       + <ReportSectionNav/> as WorkRailSections.
app/web/components/report/RelatedVariants.tsx      NEW — the evidence-grounded lanes (Phase 4).
app/web/components/report/ReportSectionNav.tsx     NEW — scroll-spy jump-to over report modules.
app/web/components/library/library.css             NEW — card + folder + tray + lane styles
                                                       (Reading Room tokens; no new globals).
```

### 1.2 Store extensions — `lib/variant-library.ts` (additive only)

The store already has `getLibrary / saveVariants / removeVariant / isSaved /
subscribe` + `SavedVariant / Folder` types + the `'eamos:library-change'` event.
Add **only** the operations the rail needs; do not change existing signatures.

```ts
// Folder CRUD
export function createFolder(name: string): Folder            // push + persist + dispatch
export function renameFolder(id: string, name: string): void
export function removeFolder(id: string): void                // also nulls folderId of its variants
export function moveVariant(id: string, folderId: string | null): void  // re-file a saved variant

// Single-variant save from the report header (the "Save current variant" CTA).
// Mirrors saveVariants() dedupe (id = query.toLowerCase()); returns true if added.
export function saveVariant(v: ParsedVariant, folderId?: string | null): boolean
```

`saveVariant` reuses the existing dedupe + `dispatch()` path (one-element
`saveVariants` call internally is acceptable — keep it a thin wrapper).
**No type changes** to `SavedVariant`/`Folder`; `folderId` already exists.

### 1.3 `useLibrary` hook (new — the single subscription point)

Every surface re-renders on `'eamos:library-change'` + cross-tab `'storage'` via
the store's existing `subscribe()`. Wrap it once so no component hand-rolls an
effect:

```ts
// components/library/useLibrary.ts
import { useSyncExternalStore } from 'react'
import { getLibrary, subscribe, type LibraryStore } from '@/lib/variant-library'

const SERVER_SNAPSHOT: LibraryStore = { variants: [], folders: [] }

export function useLibrary(): LibraryStore {
  return useSyncExternalStore(subscribe, getLibrary, () => SERVER_SNAPSHOT)
}
```

Caveat: `getLibrary()` parses localStorage on **every** call, returning a fresh
object each time → `useSyncExternalStore` would loop on referential inequality.
Fix: memoize the last snapshot in the store module (cache the parsed object;
invalidate the cache inside `persist()` and on the `'storage'` event) and have
`getLibrary()` return the cached reference. This is the one **internal** store
change required; the public API is unchanged. Verify with React StrictMode (no
infinite render).

### 1.4 Edits to `ReportClient.tsx`

The current `<main>` (lines 441–510) renders the editorial column directly. Wrap
it in `<WorkRail surface="report">` **only on the `ready` state** — the loading /
error / malformed / interpretation states keep the current full-width centered
`<main>` (no rail over an error). Concretely, in `ReportBody` (or a thin wrapper
around the `ready` branch):

- Keep the existing `<main>` content (the `<div className="flex flex-col gap-3.5">`
  returned by `ReportBody`) **untouched** — it is passed as the WorkRail `output`.
- The rail body is `<VariantLibraryRail data={data} query={query} />` (needs the
  loaded `LookupResponse` for the Save-current CTA identity + Related lanes).

Sketch (only the `ready` branch changes; error/loading branches unchanged):

```tsx
{activeState.kind === 'ready' && (
  <WorkRail
    surface="report"
    title="Library"
    action={<SaveCurrentButton data={activeState.data} />}
    output={
      <main className="mx-auto" style={{ width:'100%', maxWidth:'var(--maxw-report-frame)', padding:'32px 32px 80px' }}>
        <ReportBody key={activeState.requestKey} data={activeState.data} … />
      </main>
    }
  >
    <VariantLibraryRail data={activeState.data} query={queryLabel} />
  </WorkRail>
)}
```

Layout notes:
- The current `<main>` wraps **all** states. Refactor so the wrapping `<main>`
  (with `maxWidth: --maxw-report-frame`) moves **inside** the `ready` branch's
  `output` slot. The non-ready states render their own centered `<main>` exactly
  as today (extract a small `<CenteredMain>` wrapper to avoid duplicating the
  style object — surgical, one wrapper).
- `<WorkRail>` itself is `display:flex; width:100%`. To keep the rail flush-left
  and the report column centered in the remaining space, the `output` is the
  existing centered `<main>` (it already does `mx-auto` + max-width), so the
  reading room stays centered in the right pane. Verify the column does not
  visually shift more than the rail width on wide screens (acceptable — that is
  the intended controls-left layout; confirm with Steven on first browser pass).
- `--rail-top`: `/report` has the single 60px `TopNav`, so the default
  `--rail-top: var(--nav-h, 60px)` is correct. **But** the report also renders a
  `<StickyVariantRibbon>` inside the column — that ribbon is inside the output,
  not the chrome, so it does not affect `--rail-top`. No override needed.

State/props summary:
- `ReportClient` already has `gene/cdna/transcript/proteinChange/q`,
  `queryLabel`, and `activeState.data` (the `LookupResponse`). No new
  page-level state. The rail is **purely** driven by `useLibrary()` + the loaded
  report payload; it holds no report-fetching state.

---

## 2. Rail sections (spec §4.3)

`<VariantLibraryRail>` renders these as `<WorkRailSection>` children, top→bottom.
Order matches §4.3.

### 2.1 Top action (WorkRail `action` + first body row)

Two actions:
1. **`+ Save current variant`** — passed as the WorkRail `action` slot (top of
   the rail head). Identity comes from the loaded payload (see §7 Q2):
   `header = data.report_payload.report_profile?.header`; build a `ParsedVariant`
   `{ gene: header.gene, variant: header.cdna, query: \`${header.gene} ${header.cdna}\`, raw: query }`
   and call `saveVariant(...)`. Disabled + label-swapped to **"✓ Saved"** when
   `isSaved(query)` is true (read via `useLibrary()` so it updates live).
   Fallback when `header` is absent: derive from `row0` (`variant_summary_rows[0]`)
   exactly as the ribbon does (ReportClient lines 575–579). If neither resolves,
   render the button disabled with title "No variant identity available".
2. **`Import VCF →`** — a `<Link href="/compare">` rendered as the first row of
   the **Saved variants** section header area (small secondary link). Routes to
   `/compare` (the cohort entry point). No state.

### 2.2 Saved variants — worklist (the SHARED `<LibrarySection>`)

This is **`<LibrarySection>`**, the cross-surface component (§3). Renders:
- A `<WorkRailSection title="Saved variants" meta={count}>`.
- The variants **not** in a folder, newest-first (`savedAt` desc), each a
  `<SavedVariantCard>`.
- Empty state copy (see §7 Q4).

`<SavedVariantCard>` (MarketCap-style row card):
```
┌────────────────────────────────────────────┐
│ ● USH2A                              [×]     │   ← class dot + gene (bold)
│   NM_206933.4:c.2276G>T                      │   ← HGVS, mono, --ink-3
└────────────────────────────────────────────┘
```
- **Class dot**: `SavedVariant` does **not** carry a classification today (the
  store saves gene/variant/query/raw only). v1: render the dot in the **neutral
  `--cls-na-*`** state (no class known at save time from a `/compare` row). When
  the card is for the **currently open report**, we *do* know the class — colour
  that one dot from the report verdict. Full per-variant class requires a stored
  classification (backlog: extend `SavedVariant` with an optional
  `classification?: ClassificationTier` populated on save-from-report; flagged in
  §7 Q5, not built now to avoid a store schema change without Steven's OK).
- **Gene / HGVS**: `gene` + `variant` (fallback `query`). Mono for HGVS.
- **Click** (card body) → `router.push(reportHrefForQuery(query))` — loads that
  variant's report in the reading room. Reuse `reportHrefForQuery` from
  `lib/variant-search.ts` (already maps a saved `query` → `/report?…`). On
  `/report` this is in-app navigation; on `/workbench` it should instead load
  into the viewer (the surface passes an `onOpen(variant)` prop — see §3).
- **Remove `[×]`**: `removeVariant(id)`. Hover-reveal, `aria-label="Remove …"`.
- **Selection checkbox**: per §11.2, the card carries a checkbox for multi-select
  (drives drag-into-folder + Compare-tray pin). Left of the gene. Selection state
  lives in `<LibrarySection>` (a `Set<id>`), not the store.

### 2.3 Folders / Collections

- `<WorkRailSection title="Folders" meta={folders.length}>`.
- Each folder: a collapsible sub-group (folder name + variant count) listing its
  `<SavedVariantCard>`s (variants where `folderId === folder.id`).
- **`+ New folder`** — inline text input → `createFolder(name)`. Empty-name and
  duplicate-name guard (trim; ignore empties).
- **Rename / delete** folder — affordances on the folder header (rename = inline
  edit; delete = `removeFolder` after a confirm; deleting re-files its variants to
  the top-level Saved list via `moveVariant(…, null)`, never deletes variants).
- **Drag a variant in** (§11.2 #4): the folder header is a drop target. Two
  mechanisms, both supported, button-first (see §7 Q1):
  - **Baseline (always on):** with rows selected, a **"Move to folder ▾"** button
    on the selection toolbar → `moveVariant` for each selected id.
  - **DnD (progressive):** HTML5 drag (`draggable` cards; folder header
    `onDragOver`/`onDrop`) → `moveVariant`. Guarded behind a capability check;
    if Steven defers DnD, ship button-only first.

### 2.4 Related variants

`<RelatedVariants data={data} />` rendered as its own collapsible
`<WorkRailSection title="Related variants" defaultOpen={false}>`. Full detail in
§4. Collapsible and **closed by default** so a clinician who only wants their
worklist is never crowded (spec §5 guardrail).

### 2.5 Compare tray

- `<WorkRailSection title="Compare tray" meta={pinned.length}>`.
- Pin 2–N saved variants (a "pin" toggle on each card, or "Pin selected" on the
  selection toolbar). Pinned ids live in `<LibrarySection>` local state +
  `localStorage` key `eamos.compare-tray.v1` (small, mock-first; not in the
  variant store — it is ephemeral UI state, not saved data).
- **"Open in Compare →"** button (enabled when ≥2 pinned): writes the pinned
  variants into the compare stash (`lib/variant-file` `writeCompareVariants`/
  the stash the `/compare` page reads) and routes to `/compare`. Confirm the
  exact stash writer name during build (the reader is `readCompareVariants`);
  if no writer is exported, add a thin `writeCompareVariants(variants, source)`
  to `lib/variant-file` (additive). Source label e.g. `"Compare tray"`.

### 2.6 Section nav / jump-to (`<ReportSectionNav>`)

- `<WorkRailSection title="On this page" defaultOpen={false}>` (secondary).
- Scroll-spy over the report module anchors already in `ReportBody`:
  `population_frequency`, `evidence_by_source`, `clinical_evidence`,
  `gene_context`, `associated_conditions` / `curated_variants`, `publications`,
  `trials`, `ai_summary` (the `<div id=… className="scroll-mt-24" />` anchors).
- Build: an `IntersectionObserver` over those ids; the active one gets an
  `aria-current` + accent. Click → `el.scrollIntoView({ behavior:'smooth' })`.
  Labels: Summary/Population, In-silico, Clinical evidence, Gene & locus,
  Disease & conditions, Publications, Trials, AI summary.
- `data`-driven: only list anchors whose section actually rendered (e.g. skip
  Population when `populationSection` is null — pass the rendered-section ids down,
  or have the nav probe `document.getElementById` after mount).

---

## 3. Cross-surface behaviour (§11.1)

The **Saved variants + Folders + Compare tray** block is one component,
`<LibrarySection>`, mounted by every surface's `<WorkRail>`:

| Surface | Where mounted | Card click behaviour (`onOpen`) | Save-into |
| --- | --- | --- | --- |
| `/compare` | a new section in the existing `<WorkRail surface="compare">` (alongside `<ScopeGate>`) | `router.push(reportHref)` (open report) | already saves via `VariantTable` `handleSave` |
| `/report` | inside `<VariantLibraryRail>` | `router.push(reportHref)` (load report) | `Save current variant` CTA (§2.1) |
| `/workbench` | inside the workbench rail (Phase 2 work) | `onOpen` loads the variant into the sequence viewer | future |

- `<LibrarySection>` takes an **`onOpen?: (v: SavedVariant) => void`** prop so the
  surface decides navigate-vs-load; default = `router.push(reportHrefForQuery(v.query))`.
- Re-render on change is **automatic** via `useLibrary()` (the shared
  `useSyncExternalStore` over `subscribe()`); no surface wires its own listener.
- This is the **same store already shipped** — `/compare` already writes to it
  (`VariantTable` → `saveVariants`). Phase 3 makes the *read* side visible on
  every rail. `/compare` integration here is small (mount `<LibrarySection>`); it
  is listed so the section is genuinely shared, but the gated structural change is
  the `/report` rail — `/compare`/`/workbench` mounts can land in the same pass or
  follow, per Steven.

---

## 4. Related-variants feed (§5, Phase 4)

`<RelatedVariants data={data} />`. Four evidence lanes from data the report
**already computes** (no new fetch), each a small card list (gene · HGVS ·
class dot), collapsible. Popularity lane is flagged for Codex.

### 4.1 Lanes → existing report signals

| Lane | Source field (in `data.report_payload`) | Card content | Notes |
| --- | --- | --- | --- |
| **In this gene** | `locus_context.nearby_variants: NearbyVariant[]` (`<LocusContext>`) | `header.gene` · `nv.hgvs` (or `protein_change`) · dot from `nv.classification` (`ClassificationTier` → `--cls-*`) | Highest relevance. `clinvar_id` available for a ClinVar deep-link. Each maps to a report via `reportHrefForQuery(\`${gene} ${nv.hgvs}\`)`. |
| **Same condition** | `associated_conditions: AssociatedCondition[]` (`<AssociatedConditions>`) | condition `name` · `case_count` · evidence level | v1: this lane lists the **conditions** (not other variants — we have no per-condition variant list client-side). Frame as "Conditions linked to this gene"; each row is informational (no per-variant link yet). True same-condition *variants* need a backend lane (flag in §5). |
| **Same panel** | panel membership for `header.gene` via `lib/panels` (`getPanel`) + `resolveFilterPanel` | panel name · gene count · "Open in Compare scoped to this panel →" | Ties to `/compare`. v1 shows which panel(s) the gene belongs to and deep-links `/compare` pre-scoped; per-variant lists ride the `/panels` backend (§5). |
| **Same class / region** | derived client-side from `locus_context.nearby_variants` filtered to the **same `classification`** as the queried variant **and** within the locus window | gene · hgvs · class dot | A filtered view of lane 1 (P/LP neighbours in the same region). No new data. |
| *(light)* **Frequently reviewed** | — | — | **Needs a backend counter (Codex).** Not built in Phase 4; render the lane header with a "Coming soon" affordance or omit entirely until the counter exists (§7 Q — default: omit). |

### 4.2 Card shape & interactions

- Reuse `<SavedVariantCard>`'s visual vocabulary but **read-only** (no remove/
  checkbox) — extract the inner visual (`SavedVariantCard` → a presentational
  `<VariantCardRow>` used by both saved cards and related cards) to avoid two card
  styles drifting. Saved cards add the remove/checkbox chrome around it.
- Click a related variant → `router.push(reportHrefForQuery(...))` (loads that
  report). A small **"+"** save affordance on hover → `saveVariant(...)` straight
  into the library (the discovery → worklist loop).
- Each lane is its own collapsible row inside the Related section; lanes with no
  data are omitted (e.g. no `locus_context` → no "In this gene" lane).

### 4.3 Guardrail copy (spec §5)

Below the lanes, a one-line muted note:
> Suggestions are based on real genomic relationships in this report — shared
> gene, condition, panel, or variant class — not popularity.

This keeps the feature framed as a **clinical discovery affordance**, not
engagement bait (spec §5 guardrail). The whole section is collapsed by default.

---

## 5. Backend dependencies (Codex lane — restates spec §9)

All Phase 3/4 FE work is **mock-first on localStorage**; these are the durable
follow-ups, none blocking the FE:

1. **Durable saved-variant + collection persistence** — replace the localStorage
   store with per-account Supabase. Suggested schema (Codex owns final shape):
   - `saved_variant(id, user_id, gene, variant, query, raw, classification?, folder_id?, saved_at)`
   - `collection(id, user_id, name, created_at)` (the "folder")
   - CRUD endpoints mirroring the store API (`saveVariant`, `removeVariant`,
     `createFolder`, `moveVariant`, …). The FE swaps `lib/variant-library.ts`'s
     persistence backend behind the **same exported API**, so no rail component
     changes. RLS: user owns their rows.
2. **"Frequently reviewed" popularity counter** — a per-variant view/lookup
   counter feeding the popularity lane (§4.1). Until it exists, that lane is
   omitted. Codex owns the counter table + an aggregate endpoint.
3. **Per-variant lists for "Same condition" / "Same panel" lanes** — to upgrade
   those lanes from "conditions/panels for this gene" to "other **variants** in
   this condition/panel", the backend needs a condition→variants and
   panel→curated-variants lookup. Panel membership rides the `/panels` work
   already planned (P2/P3); reuse `resolveFilterPanel`. Mock-first lanes ship now
   without it.

---

## 6. Phased build order (each gated on Steven's OK)

Durable structural/visual change = persistent nav chrome → **Steven's explicit OK
before shipping each step** (memory: subagent/plan recs ≠ authorization). Each
step: `tsc` 0 / `lint` 0 / browser-verified on `:3000`.

| # | Step | Verify |
| --- | --- | --- |
| 3a | Store extensions (`createFolder/renameFolder/removeFolder/moveVariant/saveVariant`) + snapshot memoization for `useLibrary`. **No UI.** | unit-level: save/move/remove round-trip in localStorage; `useLibrary` doesn't loop in StrictMode |
| 3b | `<LibrarySection>` + `<SavedVariantCard>`/`<VariantCardRow>` + `useLibrary`. Mount **read-only Saved list** into `/report` rail via `<VariantLibraryRail>` (no folders/tray yet). Wrap `ReportClient` `ready` branch in `<WorkRail>`. | save on `/compare` → appears in `/report` rail → click loads that report; reading column visually intact; rail collapses/persists; `<1200px` drawer |
| 3c | Folders (create/rename/delete + move via **button**; DnD behind §7 Q1) + selection toolbar. | new folder; move selected; delete re-files not deletes |
| 3d | Compare tray (pin → Open in Compare) + Section nav scroll-spy. | pin 2 → `/compare` opens with those variants; nav highlights active module on scroll |
| 3e | Mount `<LibrarySection>` on `/compare` (+ `/workbench` when Phase 2 lands) — the shared section. | same saved list on all surfaces; one store |
| 4a | `<RelatedVariants>` lanes 1 + 4 (In this gene, Same class/region) from `locus_context`. | lanes populate on the USH2A / RPE65 sample; collapsible; closed by default |
| 4b | Lanes 2 + 3 (Same condition, Same panel) from `associated_conditions` + `getPanel`. | conditions/panel render; Same-panel deep-links `/compare` |
| 4c | Popularity lane — **only when Codex's counter ships**; omitted until then. | n/a (backend-gated) |

---

## 7. Open questions / decisions for Steven

1. **Folder drag-and-drop vs button-first?** §11.2 specifies both DnD *and* a
   button. Recommendation: ship **"Move to folder ▾" button + selection** first
   (robust, accessible, testable headless), add HTML5 DnD as a progressive
   enhancement in a follow-up. OK to defer DnD?
2. **"Save current variant" identity source.** Plan: read
   `report_payload.report_profile.header` (gene/cdna/transcript/protein_change),
   fall back to `variant_summary_rows[0]` (exactly as the StickyVariantRibbon
   already does), and store `query = \`${gene} ${cdna}\``. The saved `query` then
   round-trips through `reportHrefForQuery` to reload the same report. Confirm
   this identity (vs. e.g. storing the full transcript HGVS) is the right key.
3. **Saved-variant classification dot.** The store saves no classification today,
   so saved cards show a neutral `--cls-na` dot (only the currently-open report's
   card can be coloured). Colouring every card needs a one-field, additive store
   change (`classification?` on `SavedVariant`, set on save-from-report). Approve
   that small schema add now, or accept neutral dots in v1?
4. **Empty-state copy** for an empty library (proposed):
   *"No saved variants yet. Save the variant you're viewing, or import a VCF in
   Compare to build a worklist."* — wording OK?
5. **`/compare` + `/workbench` mounts in the same pass?** §11.1 makes the section
   shared. `/report` is the gated build; mounting the *same* `<LibrarySection>` on
   `/compare` is low-risk (it already writes to the store). Land them together, or
   `/report`-only first and the other surfaces after?

---

## 8. Summary

- **One shared `<LibrarySection>`** (Saved + Folders + Compare tray), driven by a
  `useLibrary()` `useSyncExternalStore` hook over the *already-shipped*
  `lib/variant-library.ts` store; mounted in every surface's `<WorkRail>`.
- **`/report` wraps only its `ready` state** in `<WorkRail surface="report">`; the
  `--maxw-report-frame` reading column becomes the `output` **verbatim** — the
  reading room is preserved, the rail sits flush-left.
- **Store grows additively** (folder CRUD + `saveVariant` + snapshot memoization);
  public API and `SavedVariant`/`Folder` types are otherwise unchanged.
- **Related variants** reuses report data already on the payload
  (`locus_context.nearby_variants`, `associated_conditions`, panel membership) —
  no new fetch; popularity lane is backend-gated (Codex).
- **Everything mock-first + phased + Steven-gated**; durable Supabase persistence
  and the popularity counter are Codex follow-ups that swap behind the same FE API.

## Decisions locked (Steven, 2026-06-05)

Resolves the three open questions — build against these.

1. **Folders — do BOTH.** Ship the "Move to folder" button + multi-select AND
   HTML5 drag-and-drop of a selection onto a folder target. Not either/or: button
   = reliable baseline, DnD = the delightful path.
2. **Saved-variant classification dot — APPROVED.** Add the additive
   `classification?: ClassificationTier` field to `SavedVariant`, captured at save
   time from the report payload, so every saved card shows a coloured `--cls-*`
   dot (neutral `--cls-na` only when genuinely unknown).
3. **Save key — CONFIRMED + full HGVS via progressive disclosure.** Store the
   compact `query = "GENE c.…"` as the round-trip key (`reportHrefForQuery`) AND
   also store the **full transcript HGVS** (e.g. `NM_206933.4:c.2276G>T`) on the
   `SavedVariant`. Cards show the compact form by default; the full transcript
   HGVS lives behind a tasteful expand / "view more" disclosure (hover-reveal or a
   small caret) — compact by default, full detail on demand, made to look nice.

⇒ `SavedVariant` gains two additive optional fields: `classification?` and
`hgvs_full?`. Store API stays backward-compatible.
