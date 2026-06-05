# Illustrae complement — icon module + `/workbench` library mount

> Status: **draft for review** (Claude, 2026-06-06). Docs only; no code is
> written until Steven OKs this document. Each durable structural/visual change
> is gated on Steven's explicit go-ahead before shipping (§5).

---

## 0. Scope and non-goals

**In scope:**

- A new `app/web/components/icons/Icon.tsx` module exporting ten named line-icon
  components using the project's established ToolIcon SVG idiom.
- A complete replacement table mapping every ad-hoc Unicode glyph in the
  rail/library to its named icon component.
- Mounting `<LibrarySection>` inside the `/workbench` `<WorkRail>` rail body,
  with a workbench-appropriate `onOpen` handler that loads the variant into the
  sequence viewer.

**Non-goals:**

- No store schema change (`lib/variant-library.ts` types are not touched).
- No new global CSS tokens or design-system variables.
- All changes are additive; existing component APIs are unchanged.
- No `/runs` change; that surface is frozen.
- No Illustrae visual language (fonts, corner rounding, color system). The only
  Illustrae steal targeted here is **asset-style restraint** — one coherent
  icon idiom, replacing scattered Unicode glyphs.
- The existing inline `<Chevron/>` functions in `WorkRail.tsx` (the panel
  collapse toggle) and `VariantCardRow.tsx` (the transcript HGVS caret) are
  **not** replaced by `IconChevron`; those are structural controls whose styling
  is tightly coupled to their local CSS. `IconChevron` replaces only the
  `<Chevron/>` defined inside `LibrarySection.tsx` (the folder-toggle chevron)
  and the inline `<Chevron/>` in `WorkRail.tsx`'s `WorkRailSection` head — both
  are purely decorative direction indicators sharing the same path.

---

## 1. Icon module

### 1.1 File

`app/web/components/icons/Icon.tsx`

This file is the single source for all named line icons in the library/rail
surfaces. No icon is defined anywhere else; the Unicode glyph occurrences listed
in §2 are deleted once their replacements land.

### 1.2 Shared SVG idiom

All icons use exactly the same attribute set as `ToolIcon.tsx` (the established
project idiom):

```
viewBox="0 0 24 24"
fill="none"
stroke="currentColor"
strokeWidth={2}
strokeLinecap="round"
strokeLinejoin="round"
```

Icons are colored purely via `currentColor` — the parent CSS `color:` value
propagates. No icon carries a hardcoded fill or stroke color.

### 1.3 Shared props contract

Every icon component accepts the same props shape. No per-icon props variation.

```ts
interface IconProps {
  /** Rendered width and height in px. Defaults to 16. */
  size?: number
  /** Additional className forwarded to the <svg> element. */
  className?: string
}
```

All extra props (`...rest`) are spread onto the `<svg>` element so callers can
pass `aria-hidden`, `style`, `data-*`, or `role` without wrapper divs.

`aria-hidden="true"` is **always applied** — icons are decorative; the parent
`<button>` or `<span>` carries the accessible label. The default `aria-hidden`
cannot be overridden to `false` by spread because the icon is never the sole
accessible label for anything; it is always paired with an `aria-label` on the
parent control (see §2 — every table row in §2 restates the required
`aria-label`).

### 1.4 Canonical named exports

Ten exports, names fixed — design agent and plan agent MUST use these exact
strings.

| Export | What it depicts | Path geometry (24×24 grid) |
| --- | --- | --- |
| `IconPin` | Two horizontal arrows pointing inward — "pin for compare" | `<line x1="5" y1="12" x2="10" y2="12" />` `<polyline points="7,9 10,12 7,15" />` `<line x1="19" y1="12" x2="14" y2="12" />` `<polyline points="17,9 14,12 17,15" />` |
| `IconRemove` | Diagonal cross (×) | `<line x1="18" y1="6" x2="6" y2="18" />` `<line x1="6" y1="6" x2="18" y2="18" />` |
| `IconBookmark` | Bookmark flag shape | `<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />` |
| `IconFolderMove` | Folder with right arrow | `<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />` `<line x1="12" y1="13" x2="16" y2="13" />` `<polyline points="14,11 16,13 14,15" />` |
| `IconDropInto` | Arrow pointing downward into a tray | `<line x1="12" y1="3" x2="12" y2="15" />` `<polyline points="8,11 12,15 16,11" />` `<line x1="5" y1="21" x2="19" y2="21" />` |
| `IconRename` | Pencil/edit mark | `<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />` `<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />` |
| `IconArrowRight` | Horizontal arrow pointing right | `<line x1="5" y1="12" x2="19" y2="12" />` `<polyline points="12,5 19,12 12,19" />` |
| `IconPlus` | Plus / add mark | `<line x1="12" y1="5" x2="12" y2="19" />` `<line x1="5" y1="12" x2="19" y2="12" />` |
| `IconCheck` | Checkmark (tick) | `<polyline points="20 6 9 17 4 12" />` |
| `IconChevron` | Downward chevron for collapsible heads | `<polyline points="6 9 12 15 18 9" />` |

### 1.5 Implementation note

Each export is a React function component returning `<svg>` directly. All ten
share the `svgProps` object (exactly as `ToolIcon.tsx` does at lines 4–11) so
the attribute defaults are written once:

```ts
const svgProps = {
  viewBox: '0 0 24 24',
  fill: 'none' as const,
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

export function IconPin({ size = 16, className, ...rest }: IconProps) {
  return <svg {...svgProps} width={size} height={size} className={className} aria-hidden="true" {...rest}>…</svg>
}
// … repeat for each icon
```

---

## 2. Glyph-to-icon replacement table

Every Unicode glyph used as a visual control indicator, listed by file, line,
control, replacement, and the `aria-label` that must be present on the parent
button (accessibility invariant: label must survive the swap).

### 2.1 `app/web/components/library/SavedVariantCard.tsx`

| Line | Glyph | Control | Replacement | Parent `aria-label` required |
| --- | --- | --- | --- | --- |
| 71 | `⇄` | Pin-for-compare toggle button (`.lib-card-pin`) | `<IconPin size={13} />` | `aria-pressed` already present; `title` "Pin for compare" / "Unpin from compare" stays as tooltip. No `aria-label` is on this button today — ADD `aria-label={pinned ? \`Unpin ${label} from compare\` : \`Pin ${label} for compare\`}`. |
| 79 | `✕` | Remove-from-library button (`.lib-card-remove`) | `<IconRemove size={13} />` | `aria-label={\`Remove ${label} from library\`}` — already present at line 78; preserve verbatim. |

### 2.2 `app/web/components/library/LibrarySection.tsx`

| Line | Glyph | Control / element | Replacement | `aria-label` required |
| --- | --- | --- | --- | --- |
| 195 | `⌬` | Empty-state decorative span (`.lib-empty-glyph`) | `<IconBookmark size={28} />` | `aria-hidden="true"` already on the span; move it to the icon via the always-on default (§1.3). Remove the `aria-hidden` from the span, keep the span as the layout wrapper: `<span className="lib-empty-glyph"><IconBookmark size={28} /></span>`. |
| 209 | `▾` (inside button text "Move to folder ▾") | Move-to-folder menu trigger (`.lib-seltoolbar-actions button`) | Replace the trailing `▾` with `<IconFolderMove size={13} />`. Button text becomes `Move to folder <IconFolderMove size={13} />`. | The button already has `aria-expanded`; ADD `aria-label="Move selected to folder"` for screen readers (the visual text "Move to folder" + icon is sufficient visually but an explicit label is cleaner). |
| 211 | `⇄` | Pin-selected button in selection toolbar | `<IconPin size={13} />` before the text "Pin". Button text becomes `<IconPin size={13} /> Pin`. | ADD `aria-label="Pin selected for compare"`. |
| 213 | `✕` | Clear-selection button (`.seltoolbar-clear`) | `<IconRemove size={13} />` | `aria-label="Clear selection"` — already present at line 213; preserve verbatim. |
| 318 | `⤓` (drag-over indicator inside folder toggle `.lib-folder-chev`) | Drop-target visual cue (conditionally rendered instead of `<Chevron />`) | `<IconDropInto size={13} />` | The surrounding `.lib-folder-toggle` button already has no `aria-label`; the folder toggle derives its accessible name from the visible folder name span at line 320. No change required. |
| 318 | `<Chevron />` (the local function at lines 394–400) | Folder-toggle chevron direction indicator | `<IconChevron size={11} />` | Same as above — no `aria-label` change. Remove the local `Chevron` function entirely (lines 394–400). |
| 324 | `✎` | Rename-folder button (`.lib-folder-actions button`) | `<IconRename size={13} />` | `aria-label={\`Rename ${f.name}\`}` — already present at line 324; preserve verbatim. |
| 333 | `✕` | Delete-folder button (`.lib-folder-actions .danger`) | `<IconRemove size={13} />` | `aria-label={\`Delete ${f.name}\`}` — already present at line 333; preserve verbatim. |
| 373 | `✕` (inside pin-chip unpin button) | Unpin-from-compare-tray button inside `.lib-pin-chip` | `<IconRemove size={11} />` | `aria-label={\`Unpin ${v.gene ?? v.query}\`}` — already present at line 373; preserve verbatim. |
| 388 | `→` (inside "Open in Compare →" button text) | Compare-tray open button | Replace trailing `→` with `<IconArrowRight size={13} />`. Button text: `Open in Compare <IconArrowRight size={13} />`. | No `aria-label` needed (button text is already descriptive). |
| 188 | `→` (inside `<Link>Import VCF →</Link>`) | Import VCF secondary link | Replace trailing `→` with `<IconArrowRight size={12} />`. | Link text "Import VCF" is descriptive; no change to accessible label. |

### 2.3 `app/web/components/layout/WorkRail.tsx`

| Line | Glyph | Control / element | Replacement | `aria-label` required |
| --- | --- | --- | --- | --- |
| 89 | `<Chevron />` (local function at lines 59–65) | `WorkRailSection` collapsible-head chevron | `<IconChevron size={12} />`. Remove the local `Chevron` function (lines 59–65). Import `IconChevron` from `@/components/icons/Icon`. | The parent `.wr-section-head` button already has `aria-expanded`; no label change needed. |

Note: The WorkRail toggle button's inline `<svg>` at lines 188–190 (the panel
collapse/expand chevron) is **not** replaced — that svg switches its `points`
attribute dynamically based on collapsed state; `IconChevron` is a fixed
downward chevron and would require a CSS `transform:rotate` to flip. Leave the
inline svg in place; it is not a Unicode glyph.

### 2.4 `app/web/components/report/VariantLibraryRail.tsx`

| Line | Glyph | Control | Replacement | `aria-label` required |
| --- | --- | --- | --- | --- |
| 68 | `✓ Saved` (text, not a glyph-only control) | `<SaveCurrentButton>` label when saved | Replace `✓` with `<IconCheck size={13} />`. Button text: `<IconCheck size={13} /> Saved`. | `aria-pressed` is already set; `aria-label` not required (button text is visible and descriptive). |
| 71 | `+ Save` (text) | `<SaveCurrentButton>` default label | Replace `+` with `<IconPlus size={13} />`. Button text: `<IconPlus size={13} /> Save`. | Same as above. |

---

## 3. `/workbench` LibrarySection mount contract

### 3.1 Where it mounts in `WorkbenchShell.tsx`

`WorkbenchShell` builds a `railContent` node (lines 144–187) that is passed as
`children` to `<WorkRail surface="workbench">` (line 281). `railContent`
currently contains two elements: a `.wb-rail-tools` ToolBar div and a
`<SidePanel>` (or a loading stub `<div className="side-section">`).

`<LibrarySection>` mounts **after** both the ToolBar and the SidePanel/stub, as
its own `.side-section`-style block within `railContent`. The ordering is:

```
railContent:
  1. <div className="wb-rail-tools"><ToolBar …/></div>
  2. <SidePanel …/>   (or loading stub)
  3. <LibrarySection onOpen={handleLibraryOpen} />   ← NEW
```

This order keeps the tool controls at the top of the rail (the clinician's
primary workbench interaction) and the variant library below as a supporting
worklist — consistent with the `/report` rail hierarchy where the report-specific
controls precede the library section.

The mount applies to **both** the data-ready branch and the loading-stub branch
of `railContent` (lines 144 and 166 respectively). `<LibrarySection>` reads its
own state via `useLibrary()` and does not depend on `data`; mounting it in both
branches is correct and avoids the library section disappearing while a new
variant loads.

### 3.2 `onOpen` behavior

On `/workbench`, clicking a saved-variant card should load that variant into the
sequence viewer. The viewer is driven by URL params (`gene`, `cdna`,
`transcript`) read via `useSearchParams()` in `WorkbenchClient` (lines 36–38).
The correct navigation is therefore:

```ts
function handleLibraryOpen(v: SavedVariant) {
  const params = new URLSearchParams()
  if (v.gene) params.set('gene', v.gene.toUpperCase())
  if (v.variant) params.set('cdna', v.variant)
  // hgvs_full not used here — only gene + cdna route the viewer
  router.push(`/workbench?${params.toString()}`)
}
```

`router` is the `useRouter()` instance already available in `WorkbenchShell`
(the component needs `'use client'` — already marked). This navigation pushes a
new URL; `WorkbenchClient` reads the updated params and passes the new
`gene`/`cdna` to `WorkbenchShell`, which triggers the `useEffect` fetch (line
91).

If `v.gene` or `v.variant` is null (degenerate saved variant), fall back to
`/workbench` without params (which loads the default RPE65 variant). Do not
suppress the click; give the user the default viewer rather than nothing.

### 3.3 Exact imports needed in `WorkbenchShell.tsx`

```ts
import { LibrarySection } from '@/components/library/LibrarySection'
import { useRouter } from 'next/navigation'
```

`useRouter` is already imported in `WorkbenchClient.tsx` but not in
`WorkbenchShell.tsx`. It must be added to `WorkbenchShell` since the
`handleLibraryOpen` callback lives there (next to the `railContent` definition).

`'use client'` is already present at line 1 of `WorkbenchShell.tsx`. No change
needed.

### 3.4 `currentQuery` prop

`LibrarySection` accepts an optional `currentQuery?: string` prop that marks the
currently-open variant's card with the "you are here" indicator. On
`/workbench`, pass:

```ts
currentQuery={`${gene} ${cdna}`.trim().toLowerCase()}
```

`gene` and `cdna` are already available as props on `WorkbenchShell` (lines
37–40). The store normalizes ids via `.toLowerCase()` (matching the store's
dedupe logic in `variant-library.ts`), so this produces a correct match.

### 3.5 No `WorkRail` prop changes

`WorkbenchShell` passes `<WorkRail surface="workbench" title="Workbench" output={…}>` with
no `action` prop (line 277–280). No action slot is added for the workbench rail
in this spec — the save affordance on `/workbench` is the individual card's
"save on hover" (+) icon in `<RelatedVariants>`, which is a Phase 4 detail.
The `/workbench` library mount is read-only in this pass (view/open saved
variants; save is not blocked, it just requires explicit navigation to `/report`
or `/compare`).

---

## 4. Non-goals and backward-compatibility guarantees

1. **No store schema change.** `SavedVariant`, `Folder`, and all store exports
   (`getLibrary`, `saveVariant`, `removeVariant`, `createFolder`, etc.) are
   touched only to import from, not to modify.

2. **No new global CSS tokens.** `Icon.tsx` emits plain `<svg>` elements. Color
   is `currentColor`; size is an inline `width`/`height`. No CSS variables are
   added to `globals.css` or any token file.

3. **Additive only.** The only net-new file is `app/web/components/icons/Icon.tsx`.
   All other changes are surgical within their respective files (glyph swaps,
   one `useRouter` import, one component mount).

4. **No `/runs` change.** The frozen v1 report surface is not touched.

5. **No Illustrae visual language.** Corner rounding, font choices, and color
   semantics are unchanged. The Illustrae steal is limited to icon-idiom
   consistency: one coherent stroke-based line-icon set instead of scattered
   Unicode.

6. **Existing inline SVGs in `WorkbenchClient.tsx` are not replaced.** The nav
   search, submit, and mode-pill icons (lines 77–161) are in-file inline SVGs
   serving one-off nav controls. They are correct and consistent with the idiom;
   they are not Unicode glyphs and do not need the `Icon.tsx` module.

7. **`VariantCardRow.tsx` `<Caret>` is not replaced.** The caret is a
   right-pointing chevron (different geometry from `IconChevron`), used in a
   toggled-state aria-expanded context with precise `11×11` sizing. It stays
   inline.

---

## 5. Phased build order and verify gates

Each step requires Steven's explicit go-ahead before shipping (memory:
structural/visual change = gate). Each step: `tsc` 0 / `lint` 0 / browser on
`:3000`.

| # | Step | Files changed | Verify |
| --- | --- | --- | --- |
| A | Create `Icon.tsx` with all ten named exports. No consumer changes yet. | `app/web/components/icons/Icon.tsx` (new) | `tsc` 0; `lint` 0; import in a scratch component to confirm no type errors. |
| B | Apply glyph→icon replacements across `SavedVariantCard.tsx`, `LibrarySection.tsx` (including removing local `Chevron` function), `WorkRail.tsx` (removing local `Chevron` in `WorkRailSection`), and `VariantLibraryRail.tsx`. | 4 files edited | `tsc` 0; `lint` 0; browser on `:3000`: all library controls render icons (not Unicode squares); every button still has its `aria-label` in DevTools accessibility tree; keyboard nav unchanged. |
| C | Mount `<LibrarySection>` on `/workbench` in `WorkbenchShell.tsx` with `onOpen` and `currentQuery`. | `WorkbenchShell.tsx` | `tsc` 0; `lint` 0; browser on `/workbench`: library section appears below the ToolBar/SidePanel; save a variant on `/report` then switch to `/workbench` — card appears; click card — URL updates to `/workbench?gene=…&cdna=…` and viewer loads that variant; "you are here" highlight on the current variant's card. |

**A11y invariant (applies to step B):** Open DevTools accessibility tree on
`/report` with at least one saved variant visible. For each control listed in §2:
the button/element must have a non-empty accessible name derived from
`aria-label` (not from icon text, which is `aria-hidden`). If any control loses
its name, the step has a regression — fix before marking the step done.

---

## 6. Summary

Five decisions locked in this spec:

1. **One icon module, ten canonical exports.** `app/web/components/icons/Icon.tsx`,
   ToolIcon idiom (viewBox 0 0 24 24, stroke currentColor, strokeWidth 2, round
   caps/joins), `size?` + `className?` + spread props, `aria-hidden` always.

2. **Complete glyph audit.** Eleven unique glyph occurrences across four files
   (`SavedVariantCard`, `LibrarySection`, `WorkRail`, `VariantLibraryRail`) are
   each mapped to a named icon with the parent `aria-label` requirement stated
   explicitly. Two local `Chevron` functions (`LibrarySection` lines 394–400 and
   `WorkRail` lines 59–65) are deleted once `IconChevron` lands.

3. **`/workbench` library mount is additive and non-structural.** `<LibrarySection>`
   appends to the existing `railContent` beneath `<SidePanel>`; no WorkRail prop
   changes; no new CSS. `onOpen` routes via `router.push('/workbench?gene=…&cdna=…')`
   matching how `WorkbenchClient` drives the viewer.

4. **Zero backward-compat breaks.** No store schema change; no CSS token
   additions; no API surface changes; `/runs` untouched.

5. **Three-step gated build order.** Icon module → glyph swaps + a11y verify →
   workbench mount + integration verify. Each step is independently shippable.
