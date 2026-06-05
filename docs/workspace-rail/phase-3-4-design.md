# Phase 3 + 4 — `/report` variant-library rail: VISUAL DESIGN

> Status: **design spec for build** (Claude DESIGN agent, 2026-06-06).
> Companion to `phase-3-4-report-library.md` (architecture + locked decisions).
> This doc is the **visual contract only** — token-grounded look, DOM-class
> sketches, and a ready-to-lift `library.css`. No data wiring, no build order.
>
> **Grounded in:** `DESIGN.md` (Reading Room v2 tokens), `globals.css` (the live
> `--cls-*` / `--teal-*` / `--ink-*` / `--line*` values), `work-rail.css` (the
> chrome my components live inside), `compare.css` + `VariantTable.tsx` +
> `ScopeGate.tsx` (the sibling card/chip/drag-over vocabulary I match).
>
> **Aesthetic north star:** a clinician's quiet worklist. Warm, calm, editorial,
> low-chrome. 0.5px hairlines do the structural work; one teal accent; motion is
> short and honest. Restraint over decoration — this is not a dashboard.

---

## 0. Token discipline (what I use, what I do NOT invent)

Everything below resolves to **existing** custom properties already in
`globals.css`. No new global token is required. The complete set I lean on:

| Role | Tokens |
| ---- | ------ |
| Surfaces | `--bg`, `--bg-soft`, `--bg-soft2` |
| Ink scale | `--ink`, `--ink-2`, `--ink-3`, `--ink-4`, `--ink-5` |
| Hairlines | `--line`, `--line-2` |
| Brand / selection | `--teal`, `--teal-deep`, `--teal-tint`, `--teal-bdr` |
| Classification dots | `--cls-path-dot`, `--cls-lpath-dot`, `--cls-vus-dot`, `--cls-lben-dot`, `--cls-ben-dot`, `--cls-na-dot` |
| Radii | `--r-sm` (6px), `--r-md` (10px), `--r-lg` (14px) |
| Elevation | `--elev-1`, `--elev-2` |
| Motion | `--dur-1/2/3`, `--ease-standard`, `--ease-emphasized` |
| Type | `--mono` (HGVS), `--body`, `--display` (NOT used here — rail is too small for serif) |

**Type rule honoured:** `--display` (Spectral) is heading-only and never below
24px. The rail's largest text is 13px, so **everything in the rail is `--body`
(Inter) + `--mono` (HGVS only).** No serif in the rail — correct per DESIGN.md's
hard rule. The reading column to the right keeps its serif running heads; the
rail stays sans/mono so the two registers read as "index vs. essay".

**One proposed token (NOT assumed — listed for your call, §10).** The class-dot
sizing + the card-row geometry are expressed inline as plain px (matching how
`VariantTable`/`ScopeGate` already hard-code their geometry), so **no new token
is strictly needed**. The only thing I'd *consider* promoting is a shared
`--cls-dot-sz`, but the existing surfaces (locus 9px, vardist 6px, legend 7px)
already use ad-hoc dot sizes, so I keep that pattern and do **not** add a token.

---

## 1. `<VariantCardRow>` — the shared presentational row

The atom under **both** saved-variant cards and related-variant cards. It owns
*only* the identity read: class dot · gene (bold) · compact HGVS (mono) · the
progressive-disclosure of the full transcript HGVS. It carries **no** chrome
(no checkbox, no remove, no pin) — that belongs to the wrappers in §2/§4. This
is the single source of truth so the two card families never drift.

### 1.1 Anatomy (one line, dot + identity + optional expand)

```
●  USH2A · c.2276G>T                                    ⌄
└┬┘ └──┬──┘ └───┬───┘                                   └┬┘
 │     │        │                                        └ caret — reveals full HGVS
 │     │        └ compact HGVS, --mono, --ink-3
 │     └ gene, --body 600, --ink
 └ class dot, 8px, --cls-{tier}-dot (--cls-na-dot when unknown)
```

Expanded (caret open / hover-reveal):

```
●  USH2A · c.2276G>T                                    ⌃
   NM_206933.4:c.2276G>T                                       ← full transcript HGVS,
   └──────────┬────────┘                                         --mono 11px, --ink-4,
              the disclosed row                                   one hairline-top tie
```

### 1.2 Layout & sizing

- **Row:** `display:flex; align-items:baseline; gap:8px`. Min-height 34px so a
  tapped target stays comfortable; vertical padding `7px 9px`. (Mirrors the
  `wr-section-head` padding rhythm and the compare-row `10px 14px` feel, tuned
  down for the narrower 336px rail.)
- **Class dot:** `8px` circle, `flex:0 0 auto`, a `1px solid var(--bg)` ring
  (exactly the locus-dot treatment — `border:1px solid #fff` there, but token-
  correct here against the warm page). `margin-top:1px` to optically center on
  the baseline-aligned text. Color = `--cls-{tier}-dot`; neutral `--cls-na-dot`
  (grey) when classification is unknown.
- **Identity line:** gene `--body / 600 / 13px / --ink`, then a low-contrast
  middot separator `·` in `--ink-5`, then compact HGVS `--mono / 12px / --ink-3`.
  HGVS truncates with ellipsis at the row's right edge before the caret.
- **Caret:** `14px` square, `--ink-4`, only present when `hgvs_full` exists and
  differs from the compact form. `flex:0 0 auto`, far right.

### 1.3 Progressive disclosure — the locked "full transcript HGVS" reveal

The decision (locked §3) is: compact `GENE · c.…` by default, full
`NM_…:c.…` behind a tasteful expand. Two reveal mechanisms, **both subtle**,
both reduced-motion-safe:

1. **Caret toggle (primary, accessible).** A small chevron at the row's right
   edge (`<button aria-expanded>`). Click rotates it `0deg → 90deg` over
   `--dur-2 / --ease-emphasized` (the exact `.wr-section-chev` / disclosure
   chevron motion already in the system). The full-HGVS row reveals via a
   grid-rows `0fr → 1fr` transition (the sanctioned height technique — no
   `display` animation, no layout jank) plus `opacity 0→1` and a `-2px→0`
   translate. Duration `--dur-2`.
2. **Hover-peek (progressive, pointer-only).** On `:hover` of the whole row
   (devices with `hover: hover`), the full-HGVS row fades in the same way at
   `--dur-1` — a quiet "peek" that does not commit. The caret state is the
   authoritative open/closed; hover only previews. Guarded by
   `@media (hover: hover)` so touch never gets a stuck peek, and the
   `prefers-reduced-motion` guard (global) drops both transitions to instant.

The disclosed row is visually quieter than the compact line — `--mono / 11px /
--ink-4`, tied to the identity above by a `0.5px var(--line)` top hairline that
only appears when open, so a closed card is a clean single line and an open one
reads as "row + footnote". This is the report's own `eamos-disclosure` grammar,
shrunk to row scale.

**Selectable text:** the disclosed full HGVS sets `user-select: text` so a
clinician can copy `NM_206933.4:c.2276G>T` straight out — the whole point of
surfacing it.

### 1.4 Hover / interactive state

`<VariantCardRow>` is **presentational and static on its own** — it does not
lift. The *clickability* (open report) is owned by the wrapper card (§2.2,
§4.2), which is the interactive surface. Within the row, only two things
respond:

- the **caret** (color `--ink-4 → --ink-2`, `--dur-1`),
- the **identity** never changes on its own hover; the wrapping card's hover
  tint is what signals "this whole row opens a report".

This keeps the atom dumb and lets each wrapper decide its own affordance —
exactly how `VariantTable` rows and `ScopeGate` chips keep their geometry local.

---

## 2. `<SavedVariantCard>` — VariantCardRow + worklist chrome

A worklist entry. `<VariantCardRow>` at its heart; around it the selection,
remove, pin, and selected-state chrome — all of it matched to
`VariantTable`'s selected-row vocabulary so the rail and the compare table feel
like one family.

### 2.1 Layout

```
┌─────────────────────────────────────────────────────┐
│ ☐  ● USH2A · c.2276G>T                      ⇄   ✕  ⌄ │   ← idle
│      NM_206933.4:c.2276G>T                           │   ← (expanded)
└─────────────────────────────────────────────────────┘
 │  │                                          │   │
 │  └ <VariantCardRow> (flex:1, min-width:0)   │   └ remove ✕ (hover-reveal)
 └ selection checkbox (left, --teal-deep accent)│
                                                 └ pin-for-compare toggle (⇄)
```

- **Card shell:** `display:flex; align-items:flex-start; gap:8px`,
  `padding:8px 10px`, `border-radius: var(--r-md)` (10px), `border:0.5px solid
  transparent` at rest (the hairline only materialises on hover/selected so a
  quiet list of cards reads as an unruled column, not a grid of boxes). Resting
  `box-shadow: none` — these are list rows, not floating cards. They live
  *inside* the rail's already-`--elev-1` surface, so per-card elevation would be
  noise.
- **Checkbox:** native `<input type=checkbox>`, `accentColor: var(--teal-deep)`
  (identical to `VariantTable`'s checkboxes), `flex:0 0 auto`, `margin-top:2px`
  to align with the dot. `aria-label="Select USH2A c.2276G>T"`.
- **Body:** `<VariantCardRow>` fills the middle (`flex:1; min-width:0`).
- **Pin toggle (`⇄`):** a 22px icon button, `--ink-4` idle → `--teal-deep`
  when pinned. Hover-reveal alongside remove (opacity 0 → 1 on card hover) **but**
  stays visible when *active* (pinned) so a clinician sees the pin without
  hovering. `aria-pressed`, `title="Pin for compare"`.
- **Remove (`✕`):** 22px icon button, `--ink-4`, hover-reveal (opacity 0 at
  rest, 1 on card `:hover`/`:focus-within`), hover color `--ink-2`,
  `aria-label="Remove USH2A c.2276G>T from library"`. Matches the FilterChip ✕
  geometry in `ScopeGate` (16px there; 22px here for a comfortable rail target).

### 2.2 States

| State | Treatment |
| ----- | --------- |
| **Idle** | transparent border, no shadow; pin/remove hidden (opacity 0) |
| **Hover** | `background: var(--bg-soft)`; border → `0.5px var(--line)`; pin + remove fade in (`--dur-1`); cursor pointer on the body (opens report) |
| **Focus-within** | same as hover + the standard teal focus ring on the focused control |
| **Selected** (checkbox on) | `background: var(--teal-tint)`; a **3px `var(--teal-deep)` left accent bar** (the exact `VariantTable` selected-row signal, ported to a `box-shadow: inset 3px 0 0 var(--teal-deep)` so it rides the card's radius); border → `0.5px var(--teal-bdr)` |
| **Pinned** | pin icon `--teal-deep` + a faint teal dot is *not* added (the icon color is enough); pin stays visible |
| **Currently-open report** (this card == the report on screen) | a slim `2px` left bar in `--ink-4` + `background: var(--bg-soft)` so "you are here" reads without competing with teal selection. Subtle — it's a position cue, not a status |

The **selected** treatment is deliberately the same teal-tint + left-bar as the
compare table's selected row — a clinician who selects rows in Compare and then
sees the saved list recognises the language instantly.

### 2.3 Click targets (no overlap)

The card body (dot + identity) opens the report; the checkbox, pin, remove, and
caret are independent controls. Per the `VariantTable` pattern (it already
guards `INPUT`/`A` targets), the card's `onClick` ignores events originating in
those controls. Keyboard: the body is a `<button>`/role, controls are
separately tabbable.

---

## 3. `<LibrarySection>` — the worklist, folders, toolbar, tray

The shared cross-surface block. Rendered as a stack of `<WorkRailSection>`s
(the existing chrome — uppercase mono 11px head, chevron, `meta` count slot).
I do **not** restyle `wr-section*`; I fill the `wr-section-body`.

### 3.1 "Saved variants" worklist

- `<WorkRailSection title="Saved variants" meta={count}>`. The `meta` count uses
  the existing `.wr-section-meta` (sans 500, `--ink-3`) — e.g. a small pill
  `12`. I render the count as a `.lib-count` chip (see CSS) for a touch more
  presence than bare text, matching the `n genes` mono metadata in `ScopeGate`.
- Below the head: a thin **secondary action row** — `Import VCF →` as a quiet
  text link (`--ink-4`, mono 11px, teal on hover), right-aligned. This is the
  only chrome above the list; it does not compete with the cards.
- The list: top-level `<SavedVariantCard>`s (no folder), newest-first. Cards sit
  in a flat column, `gap: 2px` (they self-separate via hover/selected, not
  rules — the unruled-worklist feel).
- **Enter animation:** new cards fade+rise (`opacity 0→1`, `translateY 4px→0`,
  `--dur-2 / --ease-standard`) — the exact list-item enter from DESIGN.md. No
  stagger needed for a save-one flow; if a batch save lands many, cap stagger at
  ~240ms per the motion rules.

**Empty state** (spec §7 Q4 copy, locked-adjacent): a calm panel, not a loud
empty-illustration. `--bg-soft` fill, `0.5px dashed --line-2`, `--r-md`,
centered, `--ink-4`:

> **No saved variants yet.**
> Save the variant you're viewing, or import a VCF in Compare to build a worklist.

The "Save the variant you're viewing" phrase is a link to the Save action; "Compare"
links to `/compare`. One quiet `⌬` glyph (the ScopeGate idle glyph) above the
copy ties the two surfaces' empty states together.

### 3.2 "Folders" — collapsible groups + CRUD + drop targets

- `<WorkRailSection title="Folders" meta={folders.length}>`.
- **Each folder** is a `.lib-folder` group:
  - **Folder header** (`.lib-folder-head`): a flex row — a small folder glyph
    (`▸`/`▾` disclosure chevron, reusing the `.wr-section-chev` rotation),
    the **name** (`--body / 600 / 12.5px / --ink-2`), a `.lib-count` chip
    (variant count), and — on hover — rename + delete affordances (two 20px icon
    buttons, `--ink-4`, hover-reveal like the card controls). Clicking the
    header (outside the buttons) collapses/expands the group.
  - **Group body:** the folder's `<SavedVariantCard>`s, indented `10px` from the
    header with a `0.5px var(--line)` left rule running down the group — a quiet
    "these belong to the folder above" tie (the one place I add a rule, because
    nesting needs it). Collapsible via grid-rows, same as the card disclosure.
- **`+ New folder`:** at the bottom of the section, a `.lib-newfolder` affordance.
  Idle: a ghost row `+ New folder` (`--ink-4`, `--body 12.5px`, dashed-free, just
  a `+` glyph). Click → it becomes an **inline text input** (`.lib-folder-input`)
  styled like the ScopeGate region input (`0.5px var(--line-2)`, `--r-sm`, `--bg`,
  12px) with a tiny ✓/Enter to commit and Esc to cancel. Empty/duplicate names
  are ignored (no error chrome — the input just stays open).
- **Rename:** the folder name swaps to the same inline input in place (the
  header text becomes editable); Enter commits, Esc reverts.
- **Delete:** the ✕ on the folder header → a quiet inline confirm (the header
  row swaps to "Delete folder? Its variants move to Saved. [Cancel] [Delete]" in
  `--ink-3`, with Delete in `--err`). Never a modal — too heavy for a rail.
  Deleting re-files variants to top-level (store `moveVariant(…, null)`).

#### Drag-over (DnD-into-folder) — match ScopeGate's drop zone exactly

The locked decision (§"Decisions locked" #1) is **both** button and DnD. The
drag-over treatment is the **same visual language ScopeGate already ships** so
the two drop interactions are one system:

| | ScopeGate (reference) | Folder header (this) |
| --- | --- | --- |
| Idle | — | normal header |
| **Drag-over** | `1.5px solid var(--teal)`, bg `var(--teal-tint)`, color `var(--teal-deep)`, `transform: scale(1.015)`, weight → 600 | **identical**: the folder header gets `outline: 1.5px solid var(--teal)` (outline, not border, so layout doesn't shift), `background: var(--teal-tint)`, the name → `--teal-deep`, and a `scale(1.012)` lift |
| Transition | `border/background/color/transform .15s ease` | same — `--dur-1`-ish (`.15s`) on the same four properties |
| Glyph swap | `⌬` → `⤓` | the folder chevron is replaced by a `⤓` drop glyph in `--teal-deep` while drag-over |

Dragged card: while a `<SavedVariantCard>` (or a multi-selection) is being
dragged, it gets `opacity: .5` and a `grabbing` cursor (the FilterChip drag
handle uses `cursor: grab`; we go to `grabbing` mid-drag). A faint count badge
("3 variants") follows under the pointer via a custom drag image — but that's a
build detail; visually the key is the **drop-target highlight matches
ScopeGate**.

### 3.3 Selection toolbar

Appears **only when ≥1 card is selected** (mirrors `VariantTable`, which only
shows "Save selected (n) →" when `selected.size > 0`). It is a slim sticky bar
pinned to the **bottom** of the worklist section body (or floating just above
the section divider), so it never pushes the list. Treatment:

```
┌─────────────────────────────────────────────┐
│ 3 selected   Move to folder ▾   ⇄ Pin   ✕    │
└─────────────────────────────────────────────┘
```

- Shell: `.lib-seltoolbar` — `background: var(--teal-tint)`, `0.5px solid
  var(--teal-bdr)`, `--r-md`, `padding: 6px 10px`, the exact `--teal-tint /
  --teal-bdr / --teal-deep` family as the compare "✓ Saved n to library" chip.
- **Count:** `3 selected`, `--teal-deep / 600 / 11.5px`.
- **Move to folder ▾:** a small button that opens a popover menu of folders +
  "New folder…". The popover uses `--elev-3` (overlay) + `--bg` + `0.5px --line`,
  `--r-md` — the only `--elev-3` surface in the rail, justified because it's a
  true overlay. Menu items reuse the `ScopeGate` `MenuItem` look (`8px 9px`,
  hover `--bg-soft`).
- **Pin (`⇄ Pin`):** pins the selection into the Compare tray.
- **Clear (`✕`):** deselects all.

### 3.4 "Compare tray"

- `<WorkRailSection title="Compare tray" meta={pinned.length}>`.
- **Pinned chips:** each pinned variant is a compact chip — gene + compact HGVS,
  with a small `✕` to unpin. Visually a **smaller cousin of the FilterChip** in
  ScopeGate: `display:inline-flex; gap:6px; padding:4px 6px 4px 7px; border:0.5px
  solid var(--teal-bdr); background: var(--teal-tint); border-radius:9px; font:
  --mono 11px; color: --teal-deep`. Chips wrap (`flex-wrap`), `gap: 6px`.
- **Empty tray** state: one muted line — *"Pin 2 or more saved variants to line
  them up in Compare."* (`--ink-4`, 11.5px).
- **"Open in Compare →"** button: a primary-ish action, **enabled only at ≥2**
  pinned. Uses the `.cmp-cta--done` register from `compare.css` (teal-tint fill,
  `--teal-bdr` border, `--teal-deep` text) at rail scale — *not* the solid teal
  CTA (that's the heavy "Generate" action on Compare; this is a lighter "go
  there"). Disabled <2: `opacity .5`, `cursor not-allowed`, title "Pin at least
  2 variants".

---

## 4. `<RelatedVariants>` — evidence lanes (Phase 4)

`<WorkRailSection title="Related variants" defaultOpen={false}>` — **closed by
default** (spec guardrail: a clinician who wants only their worklist is never
crowded). Inside, a stack of **collapsible lane rows**.

### 4.1 Lane row

Each lane (In this gene / Same condition / Same panel / Same class · region) is
a `.lib-lane` — its own mini-disclosure:

```
▸  In this gene                          5      ← lane head (collapsed)
─────────────────────────────────────────
▾  In this gene                          5      ← lane head (open)
   ●  USH2A · c.2299delG                 +      ← VariantCardRow + hover "+"
   ●  USH2A · c.2276G>T                  +
   …
```

- **Lane head:** a quieter `.wr-section-head` sibling — same uppercase-ish, but
  **not** uppercase (lanes are sub-grouping, not top sections): `--body / 600 /
  11.5px / --ink-3`, a `.wr-section-chev` chevron, and a `.lib-count` on the
  right. Hover `--bg-soft`. Lanes with no data are omitted entirely (not shown
  empty).
- **Lane body:** a list of **read-only** `<VariantCardRow>`s (no checkbox, no
  remove, no pin). Each row is clickable (opens that variant's report) and on
  hover reveals a single **"+" save affordance** at its right edge — a 20px icon
  button, `--ink-4 → --teal-deep`, `title="Save to library"`. This is the
  discovery → worklist loop, kept to one quiet glyph.
- **"Same panel" lane** special row: instead of variants, it shows the panel(s)
  the gene belongs to as a `PanelTag`-style chip + a `Open in Compare scoped to
  this panel →` link (the `.locus-workbench-link` underline-on-hover treatment).
- **"Same condition" lane** rows are informational (condition name + case count
  + an `ev-bars`-style evidence bar reused from `.ev-bars` in globals) — no per-
  variant link in v1, so these rows are **not** `VariantCardRow`s; they're a slim
  `.lib-cond-row` echoing the report's `.cond` mini-shape at rail scale.

### 4.2 Card-row reuse

Lanes reuse `<VariantCardRow>` verbatim (the dot · gene · HGVS atom), wrapped in
a `.lib-related-row` that adds *only* the hover "+" — proving the §1 extraction
pays off (saved cards add checkbox/remove/pin; related rows add "+"; the atom is
shared, no style drift).

### 4.3 Guardrail note (spec §4.3)

Below all lanes, one muted line — the `.lib-guardrail`:

> Suggestions are based on real genomic relationships in this report — shared
> gene, condition, panel, or variant class — not popularity.

`--ink-4 / 11px / line-height 1.5`, a `0.5px var(--line)` top hairline, sits as a
quiet footnote. It frames the feature as clinical discovery, not engagement
bait. The whole section stays collapsed by default.

---

## 5. `/report` rail integration — the look

### 5.1 Rail flush-left, reading column centered

`<WorkRail surface="report" title="Library" …>` renders the existing `<WorkRail>`
chrome: a **336px** (`--rail-w`) rail flush-left with a `0.5px var(--line)`
right border + `--elev-1`, sticky under the 60px TopNav (`--rail-top` default is
correct — the `StickyVariantRibbon` lives in the output, not the chrome). The
report's `--maxw-report-frame` reading column stays its own `mx-auto`-centered
`<main>` inside the `work-output` pane, so on wide screens the essay stays
optically centered in the space *right of* the rail. The reading room is
untouched; the rail simply sits beside it.

```
┌──────────┬──────────────────────────────────────────────┐
│ LIBRARY  │                                              │
│ [+ Save] │            (reading column, centered          │
│ ──────── │             in the remaining space,           │
│ Saved    │             --maxw-report-frame)              │
│ Folders  │                                              │
│ Related  │                                              │
│ Compare  │                                              │
│ On page  │                                              │
└──────────┴──────────────────────────────────────────────┘
   336px                    flex:1
```

Below 1200px the rail becomes the existing off-canvas drawer (WorkRail handles
it); the reading column goes full-width. No new responsive code — I inherit the
shell.

### 5.2 Rail head — "Library" + the Save action

The `<WorkRail>` head already renders: a toggle chevron, the **title** (uppercase
mono 11px `--ink-3` — so it reads `LIBRARY`), and an `action` slot. I put the
**Save-current button** in the `action` slot:

- **Idle (not saved):** `+ Save` — a compact button, `.lib-save-btn`, in the
  `.cmp-cta--done` teal-tint register but small (`padding: 5px 11px`, 11.5px,
  600): `background: var(--teal-tint)`, `0.5px var(--teal-bdr)`, `--teal-deep`
  text, a leading `+`. Reads as "add this to my list".
- **Saved:** swaps to **`✓ Saved`** — same chip, now with a check glyph,
  `cursor: default`, slightly lower contrast (it's a confirmed state, not an
  action). This is the exact "✓ Saved n to library" language from
  `VariantTable`, singularised for one variant — instant cross-surface
  recognition.
- **No identity available:** disabled (`opacity .5`, `not-allowed`,
  `title="No variant identity available"`).

The head therefore reads, left→right: `‹ LIBRARY   [+ Save]` — index label +
one primary action, nothing else. Quiet.

---

## 6. Component DOM sketches (so JSX matches the CSS)

Class names the `library.css` below targets. Keep these exact.

```
<VariantCardRow>
  .lib-row[data-open]
    button.lib-row-id            (the clickable identity — dot + gene + hgvs)
      span.lib-dot.cls-{tier}
      span.lib-gene
      span.lib-sep   ("·")
      span.lib-hgvs                (compact, --mono, truncates)
    button.lib-row-caret[aria-expanded]   (only if hgvs_full)
      svg                         (chevron)
  .lib-row-full[hidden|grid-rows]          (disclosed full HGVS)
    code.lib-hgvs-full

<SavedVariantCard>
  .lib-card[data-selected][data-here][data-pinned]
    input.lib-card-check[type=checkbox]
    <VariantCardRow … />          (flex:1)
    .lib-card-actions
      button.lib-card-pin[aria-pressed]
      button.lib-card-remove

<LibrarySection>  (inside <WorkRailSection> bodies)
  Saved:
    .lib-secbar                   (Import VCF → link row)
    .lib-list                     (cards) | .lib-empty (empty state)
    .lib-seltoolbar               (only when selected.size>0)
  Folders:
    .lib-folder[data-open][data-dragover]
      .lib-folder-head
        button.lib-folder-toggle  (chevron + name + .lib-count)
        .lib-folder-actions       (rename/delete icon btns, hover-reveal)
      .lib-folder-body            (grid-rows; left-rule; cards)
    .lib-newfolder                (ghost → .lib-folder-input on click)
  Compare tray:
    .lib-tray
      span.lib-pin-chip           (× N, wrap)  | .lib-tray-empty
      button.lib-tray-open

<RelatedVariants>  (inside <WorkRailSection defaultOpen=false>)
  .lib-lane[data-open]
    button.lib-lane-head          (chevron + label + .lib-count)
    .lib-lane-body                (grid-rows)
      .lib-related-row            (<VariantCardRow/> + button.lib-related-add "+")
      | .lib-cond-row             (Same-condition informational row)
      | .lib-panel-row            (Same-panel chip + Compare link)
  .lib-guardrail
```

---

## 7. `library.css` — full draft (lift into `app/web/components/library/library.css`)

Real tokens only. Geometry inline-px matches how `VariantTable`/`ScopeGate`
already express theirs. Reduced-motion is covered by the global guard in
`globals.css`, with belt-and-braces local `transition: none` on the animated bits.

```css
/* ═══════════════════════════════════════════════════════════════════════
   Variant library — saved worklist, folders, compare tray, related lanes.
   Lives inside <WorkRail> (work-rail.css). Reading Room vocabulary: --bg
   surface, 0.5px --line hairlines, one teal accent, --cls-* dots, short
   honest motion. Matches /compare's VariantTable + ScopeGate so the rail
   and the compare table read as one family. No new global tokens.
   Spec: docs/workspace-rail/phase-3-4-design.md.
═════════════════════════════════════════════════════════════════════════ */

/* ─────────────── §1  VariantCardRow — the shared atom ─────────────── */
.lib-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}
.lib-row-id {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 7px;
  padding: 0;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  color: inherit;
  font: inherit;
}
.lib-dot {
  flex: 0 0 auto;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1px solid var(--bg);   /* ring lifts the dot off the warm page */
  transform: translateY(1px);    /* optical center on the baseline text */
  background: var(--cls-na-dot);
}
.lib-dot.cls-path  { background: var(--cls-path-dot); }
.lib-dot.cls-lpath { background: var(--cls-lpath-dot); }
.lib-dot.cls-vus   { background: var(--cls-vus-dot); }
.lib-dot.cls-lben  { background: var(--cls-lben-dot); }
.lib-dot.cls-ben   { background: var(--cls-ben-dot); }
.lib-dot.cls-na    { background: var(--cls-na-dot); }
.lib-gene {
  flex: 0 0 auto;
  font-family: var(--body);
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -0.005em;
}
.lib-sep { flex: 0 0 auto; color: var(--ink-5); font-size: 12px; }
.lib-hgvs {
  flex: 1 1 auto;
  min-width: 0;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--ink-3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lib-row-caret {
  flex: 0 0 auto;
  width: 14px;
  height: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  background: none;
  color: var(--ink-4);
  cursor: pointer;
  transition: color var(--dur-1) var(--ease-standard);
}
.lib-row-caret:hover { color: var(--ink-2); }
.lib-row-caret svg {
  transition: transform var(--dur-2) var(--ease-emphasized);
}
.lib-row-caret[aria-expanded='true'] svg { transform: rotate(90deg); color: var(--teal-deep); }

/* Disclosed full transcript HGVS — grid-rows reveal (the sanctioned height
   technique). Closed = 0fr (no height); open = 1fr. */
.lib-row-full {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows var(--dur-2) var(--ease-emphasized);
}
.lib-row[data-open='true'] .lib-row-full,
.lib-card:hover .lib-row-full,        /* hover-peek (pointer only, see media query) */
.lib-related-row:hover .lib-row-full {
  grid-template-rows: 1fr;
}
.lib-row-full > .lib-hgvs-full {
  overflow: hidden;
  min-height: 0;
  margin: 4px 0 1px 16px;            /* indent under the dot+gene */
  padding-top: 4px;
  border-top: 0.5px solid transparent;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ink-4);
  user-select: text;                 /* copyable */
  opacity: 0;
  transform: translateY(-2px);
  transition: opacity var(--dur-2) var(--ease-standard),
              transform var(--dur-2) var(--ease-standard);
}
.lib-row[data-open='true'] .lib-hgvs-full,
.lib-card:hover .lib-hgvs-full,
.lib-related-row:hover .lib-hgvs-full {
  opacity: 1;
  transform: translateY(0);
  border-top-color: var(--line);
}
/* Hover-peek only on true hover devices; touch uses the caret. */
@media (hover: none) {
  .lib-card:hover .lib-row-full,
  .lib-related-row:hover .lib-row-full { grid-template-rows: 0fr; }
  .lib-card:hover .lib-hgvs-full,
  .lib-related-row:hover .lib-hgvs-full { opacity: 0; }
}

/* ─────────────── §2  SavedVariantCard — worklist chrome ─────────────── */
.lib-list { display: flex; flex-direction: column; gap: 2px; }
.lib-card {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--r-md);
  border: 0.5px solid transparent;
  cursor: pointer;
  transition: background var(--dur-1) var(--ease-standard),
              border-color var(--dur-1) var(--ease-standard);
  /* enter animation */
  animation: lib-row-in var(--dur-2) var(--ease-standard) both;
}
@keyframes lib-row-in {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}
.lib-card:hover,
.lib-card:focus-within {
  background: var(--bg-soft);
  border-color: var(--line);
}
.lib-card[data-here='true'] {
  background: var(--bg-soft);
  box-shadow: inset 2px 0 0 var(--ink-4);   /* "you are here" position cue */
}
.lib-card[data-selected='true'] {
  background: var(--teal-tint);
  border-color: var(--teal-bdr);
  box-shadow: inset 3px 0 0 var(--teal-deep);   /* VariantTable selected-row bar */
}
.lib-card-check {
  flex: 0 0 auto;
  margin-top: 2px;
  cursor: pointer;
  accent-color: var(--teal-deep);
}
.lib-card-actions {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--dur-1) var(--ease-standard);
}
.lib-card:hover .lib-card-actions,
.lib-card:focus-within .lib-card-actions,
.lib-card[data-pinned='true'] .lib-card-actions { opacity: 1; }
.lib-card-pin,
.lib-card-remove {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: none;
  color: var(--ink-4);
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  transition: color var(--dur-1) var(--ease-standard), background var(--dur-1) var(--ease-standard);
}
.lib-card-pin:hover,
.lib-card-remove:hover { background: var(--bg-soft2); color: var(--ink-2); }
.lib-card-pin[aria-pressed='true'] { color: var(--teal-deep); opacity: 1; }

/* ─────────────── §3.1  Saved section: secondary bar + count + empty ─────────────── */
.lib-secbar {
  display: flex;
  justify-content: flex-end;
  margin: -2px 0 6px;
}
.lib-secbar a {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ink-4);
  text-decoration: none;
  transition: color var(--dur-1) var(--ease-standard);
}
.lib-secbar a:hover { color: var(--teal-deep); }
.lib-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 100px;
  background: var(--bg-soft2);
  font-family: var(--mono);
  font-size: 10.5px;
  font-weight: 600;
  color: var(--ink-3);
}
.lib-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 18px 14px;
  border: 0.5px dashed var(--line-2);
  border-radius: var(--r-md);
  background: var(--bg-soft);
  text-align: center;
}
.lib-empty .lib-empty-glyph { font-size: 16px; color: var(--ink-5); line-height: 1; }
.lib-empty strong { font-size: 12.5px; font-weight: 600; color: var(--ink-2); }
.lib-empty p { margin: 0; font-size: 11.5px; line-height: 1.5; color: var(--ink-4); }
.lib-empty a { color: var(--teal-deep); text-decoration: underline; text-underline-offset: 2px; }

/* ─────────────── §3.2  Folders ─────────────── */
.lib-folder { border-radius: var(--r-md); }
.lib-folder + .lib-folder { margin-top: 2px; }
.lib-folder-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 8px;
  border-radius: var(--r-sm);
  outline: 1.5px solid transparent;          /* drag-over uses outline (no layout shift) */
  background: transparent;
  transition: background .15s ease, outline-color .15s ease, color .15s ease, transform .15s ease;
}
.lib-folder-head:hover { background: var(--bg-soft); }
.lib-folder-toggle {
  flex: 1 1 auto;
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  text-align: left;
  color: inherit;
}
.lib-folder-chev {
  width: 14px; height: 14px;
  display: inline-flex; align-items: center; justify-content: center;
  color: var(--ink-3);
  transition: transform var(--dur-2) var(--ease-emphasized);
  flex: 0 0 auto;
}
.lib-folder[data-open='false'] .lib-folder-chev { transform: rotate(-90deg); }
.lib-folder-name {
  flex: 1 1 auto;
  min-width: 0;
  font-family: var(--body);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lib-folder-actions {
  flex: 0 0 auto;
  display: inline-flex;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--dur-1) var(--ease-standard);
}
.lib-folder-head:hover .lib-folder-actions { opacity: 1; }
.lib-folder-actions button {
  width: 20px; height: 20px;
  display: inline-flex; align-items: center; justify-content: center;
  padding: 0; border: none; border-radius: 5px;
  background: none; color: var(--ink-4); cursor: pointer; font-size: 12px;
  transition: color var(--dur-1) var(--ease-standard), background var(--dur-1) var(--ease-standard);
}
.lib-folder-actions button:hover { background: var(--bg-soft2); color: var(--ink-2); }
.lib-folder-actions button.danger:hover { color: var(--err); }

/* Drag-over a folder — MATCHES ScopeGate's drop zone (teal solid edge,
   teal-tint fill, teal-deep text, subtle scale). */
.lib-folder[data-dragover='true'] .lib-folder-head {
  outline-color: var(--teal);
  background: var(--teal-tint);
  transform: scale(1.012);
}
.lib-folder[data-dragover='true'] .lib-folder-name { color: var(--teal-deep); }

/* Folder body — collapsible, left-ruled to tie the nested cards to their head. */
.lib-folder-body {
  display: grid;
  grid-template-rows: 1fr;
  transition: grid-template-rows var(--dur-2) var(--ease-emphasized);
}
.lib-folder[data-open='false'] .lib-folder-body { grid-template-rows: 0fr; }
.lib-folder-body > .lib-folder-cards {
  overflow: hidden;
  min-height: 0;
  margin-left: 10px;
  padding-left: 8px;
  border-left: 0.5px solid var(--line);
}

/* New-folder affordance + inline input */
.lib-newfolder {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  padding: 6px 8px;
  border: none;
  background: none;
  color: var(--ink-4);
  font-family: var(--body);
  font-size: 12.5px;
  cursor: pointer;
  border-radius: var(--r-sm);
  transition: color var(--dur-1) var(--ease-standard), background var(--dur-1) var(--ease-standard);
}
.lib-newfolder:hover { color: var(--ink-2); background: var(--bg-soft); }
.lib-folder-input {
  width: 100%;
  margin-top: 6px;
  padding: 5px 8px;
  border-radius: var(--r-sm);
  border: 0.5px solid var(--line-2);
  background: var(--bg);
  font-family: var(--body);
  font-size: 12.5px;
  color: var(--ink);
}
.lib-folder-input:focus-visible {
  outline: none;
  border-color: var(--teal);
  box-shadow: 0 0 0 3px rgba(29, 158, 117, 0.18);
}

/* Inline delete-confirm row */
.lib-folder-confirm {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 8px; font-size: 11.5px; color: var(--ink-3);
}
.lib-folder-confirm button { font-size: 11.5px; font-weight: 600; cursor: pointer; background: none; border: none; padding: 0; }
.lib-folder-confirm .confirm-cancel { color: var(--ink-4); }
.lib-folder-confirm .confirm-del { color: var(--err); }

/* ─────────────── §3.3  Selection toolbar ─────────────── */
.lib-seltoolbar {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  padding: 6px 10px;
  border-radius: var(--r-md);
  border: 0.5px solid var(--teal-bdr);
  background: var(--teal-tint);
  box-shadow: var(--elev-1);
}
.lib-seltoolbar-count { font-size: 11.5px; font-weight: 600; color: var(--teal-deep); white-space: nowrap; }
.lib-seltoolbar button {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 9px; border-radius: 7px;
  border: 0.5px solid var(--teal-bdr); background: var(--bg);
  color: var(--teal-deep); font-size: 11.5px; font-weight: 600; cursor: pointer;
  transition: background var(--dur-1) var(--ease-standard), border-color var(--dur-1) var(--ease-standard);
}
.lib-seltoolbar button:hover { background: var(--bg-soft); }
.lib-seltoolbar .seltoolbar-clear { margin-left: auto; border: none; background: none; color: var(--teal-deep); padding: 4px 6px; }

/* Move-to-folder popover (the one --elev-3 overlay in the rail) */
.lib-folder-menu {
  position: absolute;
  z-index: 20;
  min-width: 180px;
  padding: 4px;
  border-radius: var(--r-md);
  border: 0.5px solid var(--line);
  background: var(--bg);
  box-shadow: var(--elev-3);
  animation: lib-overlay-in var(--dur-2) var(--ease-standard) both;
}
@keyframes lib-overlay-in {
  from { opacity: 0; transform: scale(.98); }
  to   { opacity: 1; transform: scale(1); }
}
.lib-folder-menu button {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  width: 100%; text-align: left;
  padding: 8px 9px; border-radius: var(--r-sm);
  border: none; background: transparent; color: var(--ink);
  font-size: 12.5px; cursor: pointer;
}
.lib-folder-menu button:hover { background: var(--bg-soft); }

/* ─────────────── §3.4  Compare tray ─────────────── */
.lib-tray { display: flex; flex-wrap: wrap; gap: 6px; }
.lib-pin-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px 4px 7px;
  border-radius: 9px;
  border: 0.5px solid var(--teal-bdr);
  background: var(--teal-tint);
  font-family: var(--mono);
  font-size: 11px;
  color: var(--teal-deep);
}
.lib-pin-chip button {
  display: inline-flex; align-items: center; justify-content: center;
  width: 14px; height: 14px; padding: 0;
  border: none; border-radius: 4px; background: none;
  color: var(--teal-deep); opacity: .7; font-size: 11px; line-height: 1; cursor: pointer;
}
.lib-pin-chip button:hover { opacity: 1; }
.lib-tray-empty { font-size: 11.5px; color: var(--ink-4); line-height: 1.5; }
.lib-tray-open {
  display: inline-flex; align-items: center; gap: 6px;
  width: 100%; justify-content: center;
  margin-top: 8px; padding: 8px 14px;
  border-radius: var(--r-md);
  border: 0.5px solid var(--teal-bdr);
  background: var(--teal-tint);
  color: var(--teal-deep);
  font-size: 12px; font-weight: 600; cursor: pointer;
  transition: background var(--dur-1) var(--ease-standard), box-shadow var(--dur-2) var(--ease-standard);
}
.lib-tray-open:hover { background: var(--bg-soft); box-shadow: var(--elev-1); }
.lib-tray-open:disabled { opacity: .5; cursor: not-allowed; box-shadow: none; }

/* ─────────────── §4  Related variants lanes ─────────────── */
.lib-lane + .lib-lane { margin-top: 2px; }
.lib-lane-head {
  display: flex; align-items: center; gap: 7px;
  width: 100%; padding: 7px 8px;
  border: none; border-radius: var(--r-sm);
  background: transparent; cursor: pointer; text-align: left;
  font-family: var(--body); font-size: 11.5px; font-weight: 600; color: var(--ink-3);
  transition: background var(--dur-1) var(--ease-standard), color var(--dur-1) var(--ease-standard);
}
.lib-lane-head:hover { background: var(--bg-soft); color: var(--ink-2); }
.lib-lane-chev {
  width: 14px; height: 14px; flex: 0 0 auto;
  display: inline-flex; align-items: center; justify-content: center;
  color: var(--ink-4);
  transition: transform var(--dur-2) var(--ease-emphasized);
}
.lib-lane[data-open='false'] .lib-lane-chev { transform: rotate(-90deg); }
.lib-lane-label { flex: 1 1 auto; }
.lib-lane-body {
  display: grid; grid-template-rows: 1fr;
  transition: grid-template-rows var(--dur-2) var(--ease-emphasized);
}
.lib-lane[data-open='false'] .lib-lane-body { grid-template-rows: 0fr; }
.lib-lane-body > .lib-lane-rows { overflow: hidden; min-height: 0; padding-left: 6px; }

.lib-related-row {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 8px; border-radius: var(--r-sm);
  cursor: pointer;
  transition: background var(--dur-1) var(--ease-standard);
}
.lib-related-row:hover { background: var(--bg-soft); }
.lib-related-add {
  flex: 0 0 auto;
  width: 20px; height: 20px;
  display: inline-flex; align-items: center; justify-content: center;
  padding: 0; border: none; border-radius: 5px;
  background: none; color: var(--ink-4); cursor: pointer; font-size: 14px; line-height: 1;
  opacity: 0;
  transition: color var(--dur-1) var(--ease-standard), background var(--dur-1) var(--ease-standard), opacity var(--dur-1) var(--ease-standard);
}
.lib-related-row:hover .lib-related-add { opacity: 1; }
.lib-related-add:hover { color: var(--teal-deep); background: var(--bg-soft2); }

/* Same-condition informational row (echoes report .cond at rail scale) */
.lib-cond-row {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 8px; font-size: 12px; color: var(--ink-2);
}
.lib-cond-row .cond-n { font-family: var(--mono); font-size: 12px; font-weight: 600; color: var(--teal-deep); }
.lib-cond-row .cond-name { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Same-panel row */
.lib-panel-row { display: flex; flex-direction: column; gap: 6px; padding: 7px 8px; }
.lib-panel-link {
  font-size: 11.5px; font-weight: 600; color: var(--teal-deep);
  text-decoration: underline; text-decoration-color: transparent; text-underline-offset: 3px;
  transition: text-decoration-color var(--dur-1) var(--ease-standard), color var(--dur-1) var(--ease-standard);
}
.lib-panel-link:hover { color: var(--teal); text-decoration-color: var(--teal); }

.lib-guardrail {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 0.5px solid var(--line);
  font-size: 11px;
  line-height: 1.5;
  color: var(--ink-4);
}

/* ─────────────── §5  Rail head Save action ─────────────── */
.lib-save-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 11px;
  border-radius: 8px;
  border: 0.5px solid var(--teal-bdr);
  background: var(--teal-tint);
  color: var(--teal-deep);
  font-size: 11.5px; font-weight: 600; cursor: pointer;
  transition: background var(--dur-1) var(--ease-standard), box-shadow var(--dur-2) var(--ease-standard);
}
.lib-save-btn:hover { box-shadow: var(--elev-1); }
.lib-save-btn[data-saved='true'] { cursor: default; opacity: .85; }
.lib-save-btn:disabled { opacity: .5; cursor: not-allowed; box-shadow: none; }

/* ─────────────── Reduced-motion (belt-and-braces; global guard also covers) ─────────────── */
@media (prefers-reduced-motion: reduce) {
  .lib-card,
  .lib-row-full,
  .lib-hgvs-full,
  .lib-folder-body,
  .lib-folder-head,
  .lib-lane-body,
  .lib-row-caret svg,
  .lib-folder-chev,
  .lib-lane-chev,
  .lib-folder-menu {
    transition: none;
    animation: none;
  }
}
```

---

## 8. Why this matches the family (self-check against the brief)

- **Saved cards ≈ compare table rows + PanelTag chips.** Selected card =
  `--teal-tint` fill + 3px `--teal-deep` inset left bar — *byte-for-byte* the
  `VariantTable` selected-row signal. Checkbox `accent-color: --teal-deep`
  matches. The "✓ Saved" language and the teal-tint/`--teal-bdr` action chips
  are lifted from `VariantTable`'s save flash and `compare.css`'s `.cmp-cta--done`.
- **Drag-over = ScopeGate's drop zone.** Same teal solid edge + `--teal-tint`
  fill + `--teal-deep` text + subtle `scale` + `⤓` glyph, same `.15s` four-prop
  transition. A clinician learns it once.
- **Class dots = the `--cls-*` ramp**, neutral `--cls-na-dot` when unknown —
  exactly the locus/vardist dot grammar.
- **Disclosure = the report's own grammar**, shrunk: chevron rotate `--dur-2 /
  --ease-emphasized`, grid-rows height, opacity+translate reveal — the
  `eamos-disclosure` pattern at row scale.
- **Restraint:** unruled card column, hover-revealed controls, one teal accent,
  serif kept out of the rail, Related closed by default + a quiet guardrail
  footnote. Low-chrome worklist, not a dashboard.

---

## 9. Open visual choices (for your call — none block the build)

1. **Card "you are here" cue.** I used a 2px `--ink-4` inset bar + `--bg-soft`
   for the currently-open report's card (distinct from teal selection). If you'd
   rather it be invisible (no position cue) or use a faint teal-left instead,
   say so — I kept it grey to avoid two teal meanings.
2. **Folder nesting rule.** I add the *one* explicit rule in the rail (a 0.5px
   left line down a folder's cards) because nesting genuinely needs the tie.
   Everything else stays unruled. OK to keep that single rule?
3. **Count chip vs. bare meta.** I render counts as a small `--bg-soft2` pill
   (`.lib-count`) for a touch more presence than the bare `.wr-section-meta`
   text. If you want it barer, drop `.lib-count` and pass a plain number to the
   section `meta` slot.

## 10. Token proposal (NOT assumed)

**None required.** Every value resolves to an existing `globals.css` custom
property; geometry is inline-px consistent with `VariantTable`/`ScopeGate`. The
only thing I considered and *rejected* was a shared `--cls-dot-sz` token —
rejected because the existing surfaces already use per-context dot sizes (locus
9px, vardist 6px, legend 7px), so a global dot-size token would mismatch them.
If you later want one, it's a clean additive follow-up; nothing here depends on it.
