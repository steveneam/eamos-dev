# Illustrae complement — the cohesive line-icon set: VISUAL DESIGN

> Status: **design spec for build** (Claude DESIGN agent, 2026-06-06).
> Companion to `phase-3-4-design.md` (the rail's visual contract) and
> `phase-3-4-report-library.md` (architecture + locked decisions).
> This doc closes the **one unbuilt Illustrae steal** (spec §6): asset-style
> restraint = a single cohesive clean line-icon set. Today the rail mixes clean
> SVGs (`<Chevron>`, `<Caret>`, the `ToolIcon` family) with ad-hoc Unicode
> glyphs (`⇄ ✕ ⌬ ▾ ⤓ ✎ →`). This unifies them.
>
> **Grounded in:** the **Illustrae live design system** (extracted via
> `illustrae-pp-cli`, 2026-06-06 — authoritative numbers below), `DESIGN.md`
> (Reading Room v2), `globals.css` (the live `--teal #1D9E75` / `--ink-*` /
> `--line` / `--r-*` / `--dur-*` / `--ease-*` values), `ToolIcon.tsx` (the
> clean-SVG idiom I match: viewBox `0 0 24 24`, `fill none`, `stroke
> currentColor`, round caps/joins), and the four glyph users
> (`SavedVariantCard`, `LibrarySection`, `VariantCardRow`, `WorkRail`).
>
> **Aesthetic north star:** Illustrae's *discipline* (one minimal, self-hosted
> asset family — not its *register*). Eamos is a clinician's quiet worklist, so
> the family is clean clinical line-work, **never** hand-drawn. One stroke
> weight, one viewBox, one accessibility rule. Restraint over decoration.

---

## 0. Token discipline (what I use, what I do NOT invent)

Everything below resolves to **existing** custom properties already in
`globals.css`. **No new global token is required** — icons inherit color via
`currentColor` from whatever control hosts them, and size via a per-call
`width`/`height` prop (the `ToolIcon` / `WorkRail` `<Chevron>` pattern, which
already passes literal `width="11"`/`"12"`/`"13"`). The set I lean on:

| Role | Tokens |
| ---- | ------ |
| Icon color (inherited) | `currentColor` ← `--ink-4` idle, `--ink-2` hover, `--teal-deep` active, `--err` destructive-hover |
| Hairlines (none in icons) | icons are stroke-only; structural hairlines stay `--line` / `--line-2` on containers |
| Motion (chevron rotate only) | `--dur-2`, `--ease-emphasized` (disclosure), `--dur-1` `--ease-standard` (color) |
| Radii (N/A to icons) | `--r-sm/md/lg` stay on the *buttons*, not the SVGs |

**The one geometric constant I do fix (local, not a global token):** every icon
is authored on a `0 0 24 24` viewBox with `strokeWidth` **1.75** and
`strokeLinecap/strokeLinejoin: round`. This is the single source of "family
resemblance" — identical to `ToolIcon`'s `svgProps` except the weight steps down
from `2` to `1.75` (see §2.0 for why). Rendered size is set per context by a
`width`/`height` prop, never by re-authoring the path.

---

## 1. Steal / Reject / Already-done matrix

Each Illustrae facet (extracted 2026-06-06) judged against the clinical Reading
Room, grounded in the extracted numbers — not vibes.

| Illustrae facet | Extracted value | Call | Why (token-grounded) |
| --- | --- | --- | --- |
| **Palette — brand** | teal `#4e8d99` (10×) + plum `#6d445e` (7×) | **REJECT (already have our own)** | Their teal `#4e8d99` is a *desaturated blue-grey* teal; ours is `--teal #1D9E75`, a saturated **green**-teal that anchors the red→yellow→green classification ramp (`--cls-path-dot` → `--cls-ben-dot`). Adopting `#4e8d99` would collide with `--cls-vus`/`--cls-lben` hues and break the one-accent rule. Their **plum** `#6d445e` is a genuinely nice secondary, but a second brand hue fights "one teal accent" — REJECT. Keep `--teal` / `--teal-deep` / `--teal-tint` / `--teal-bdr`. |
| **Palette — status** | Mantine rainbow: reds `#fa5252…#c92a2a`, blues `#1c7ed6…#4dabf7`, greens `#0fb884/#2b8a3e` | **REJECT** | Saturated, cool, screen-bright — built for a playful canvas app. Ours are OKLCH, warm-anchored, AA-tuned on warm white (`--cls-*` ramp + `--err #B82B2B`). Their blues have no home in a report that has no "info" tier. REJECT wholesale. |
| **Fonts** | Assistant, Nunito, Lilita One, **Comic Shanns** (hand-drawn), Cascadia | **REJECT** | Lilita One (display marker) + Comic Shanns (Excalidraw hand-mono) define a **playful** register. Eamos is Spectral (serif heads, ≥24px) + Inter (`--body`) + a clinical `--mono` for HGVS. A hand-drawn mono in a variant report reads as *un*-serious — the exact opposite of clinical trust. REJECT. |
| **Radii** | `--border-radius-lg` (29×), `12px`, `.5rem`, `4px` — generous | **REJECT (theirs) / KEEP (ours)** | Their dominant `--border-radius-lg` (used 29×) is the visual signature of a *soft, friendly* canvas. Ours are tighter and tiered for an editorial worklist: `--r-sm 6` / `--r-md 10` / `--r-lg 14`. Generous rounding would soften the hairline-structured worklist into a toy. KEEP our tighter scale. |
| **Assets** | 4 self-hosted fonts + Cloudinary AI illustrations; **minimal** | **STEAL — the discipline, not the assets** | This is the actual steal (spec §6): Illustrae ships a *deliberately tiny, cohesive* asset family — no icon-font grab-bag, no mixed sources. Eamos today violates this with 7 ad-hoc Unicode glyphs (`⇄ ✕ ⌬ ▾ ⤓ ✎ →`) living beside clean SVGs. **STEAL the principle**: one self-authored line-icon family, zero external icon deps, every glyph from the same hand. That is §2. |
| **Layout** | Mantine UI + Excalidraw "Intelligent Canvas" shell | **ALREADY-DONE** | Their controls-frame-canvas pattern is exactly our `<WorkRail>` (controls-left / output-right, one chrome / three surfaces). Shipped 2026-06-06 (Phases 0–2, origin/main `2f947c6`). Nothing to take. |
| **Iconography** | clean single-source line set (implied by the minimal-asset discipline + Excalidraw's consistent stroke vocabulary) | **STEAL → §2** | The concrete output of the asset-discipline steal. Illustrae's strength is that *every* mark looks like it came from one pen. Eamos's `ToolIcon` already proves we can do this (5 perfectly consistent line icons); the rail just never finished the job. §2 extends that one pen to the 7 glyphs. |

**Net:** one steal (asset-style restraint → a cohesive line-icon family), one
already-done (layout = `<WorkRail>`), everything else rejected because Illustrae's
playful register fights the clinical Reading Room. We take the *discipline* and
apply it in *our* register.

---

## 2. The icon set — `app/web/components/icons/Icon.tsx`

One module, named exports, one authoring constant. The clinical answer to
Illustrae's asset restraint: **clean line-work, not hand-drawn.**

### 2.0 Shared authoring constant (the "one pen")

```tsx
// app/web/components/icons/Icon.tsx
const iconProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.75,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
} as const
```

Identical to `ToolIcon`'s `svgProps` **except** `strokeWidth` steps `2 → 1.75`.
Rationale: `ToolIcon` marks are tool-tab glyphs rendered ~18–22px; this family
renders **smaller** (12–16px) inline beside 11–13px text. At 12px a weight-2
stroke optically bolds against `--mono`/`--body` text; **1.75** keeps the icon
visually quieter than the label it sits next to — the Reading Room "icons
whisper, text speaks" rule. (The existing `<Chevron>`/`<Caret>` use `2.4`
because a lone polyline needs more presence; full glyphs with multiple strokes
do not — see §2.3 for folding those in.)

Every component takes one prop: `size?: number` (default per the table in §2.2),
spread as `width={size} height={size}`. No color prop — color is `currentColor`,
owned by the host button's existing CSS (`.lib-card-pin`, `.lib-folder-actions
button`, etc., already set `color: var(--ink-4)` → hover `--ink-2`).

### 2.1 The ten icons — glyph replaced, path intent, ASCII sketch

Canonical names (use **exactly** these so spec / plan / impl agree):

| Component | Replaces | Renders where | Path intent |
| --- | --- | --- | --- |
| `IconPin` | `⇄` | card pin-for-compare; seltoolbar "Pin" | two horizontal arrows, opposed (compare = "line these up"). |
| `IconRemove` | `✕` | card remove; seltoolbar clear; folder delete; tray unpin | a clean X — two crossed strokes, equal length, 5→19 / 5→19. |
| `IconBookmark` | _(new — the Save action + lane "+")_ | rail-head Save; related-lane save-to-library | a bookmark ribbon (Save register). `IconPlus` is the alternate for the lane "+" if a ribbon reads too heavy at 16px — see §2.2. |
| `IconFolderMove` | `▾` ("Move to folder") | seltoolbar "Move to folder" | a folder outline with a small down-caret notch, OR a folder + right-chevron. Carries the "into a folder" meaning the bare `▾` never did. |
| `IconDropInto` | `⤓` | folder header while drag-over | a down-arrow landing into an open tray/bracket — "drop here". |
| `IconRename` | `✎` | folder rename | a pencil at 45°, nib lower-left, eraser upper-right. |
| `IconArrowRight` | `→` | "Import VCF", "Open in Compare", lane "Open in Compare scoped…" | a thin right arrow: shaft + chevron head. |
| `IconPlus` | _(formalizes the `+` in "+ New folder", "+ Save")_ | "New folder"; lane "+"; Save leading mark | a plus, 6→18 / 6→18 crossed at center. |
| `IconCheck` | _(the `✓` in "✓ Saved")_ | Save confirmed state | a checkmark, 5,13 → 9,17 → 19,7. |
| `IconChevron` | _(folds in `<Chevron>` + `<Caret>`)_ | section/lane/folder disclosure; row caret | a single down-polyline `6,9 12,15 18,9`; rotate via CSS for caret/collapsed. |

ASCII intent (authoring guide — not final coordinates):

```
IconPin (⇄)            IconRemove (✕)         IconBookmark            IconFolderMove (▾)
  ──────▶                ╲   ╱                  ┌─────┐                 ┌──┐
  ◀──────                 ╲ ╱                   │     │                 │  └────┐
 two opposed              ╳                     │  ▽  │  ribbon          │   folder
 h-arrows               ╱   ╲                   └──▽──┘  notch           └───────┘ ▾

IconDropInto (⤓)       IconRename (✎)         IconArrowRight (→)      IconPlus (+)
    │                      ╱▔                     ─────────▶              │
    ▼                    ╱                       shaft + head          ──┼──
  ┌───┐                ╱  pencil                                          │
  └───┘  tray         ╱_  at 45°                IconCheck (✓)         IconChevron (v)
  open bracket                                    ╲    ╱                ╲   ╱
                                                   ╲  ╱                  ╲ ╱
                                                    ╲╱  tick              v  (rotate per state)
```

### 2.2 Size per context

Sizes are set by the host, matching the existing literal-`width` pattern. Three
contexts only — keep it tight:

| Context | size | Examples |
| --- | --- | --- |
| **Section / lane / folder chevron** | **12px** (folder/lane) · keep **11px** for the row caret to match today | `IconChevron` in `wr-section-chev` is **12** (matches `WorkRail`'s `<Chevron width="12">`); folder/lane chevrons 12; `VariantCardRow` caret stays **11** (matches today's `<Caret width="11">`). |
| **Card action** | **16px** | `IconPin`, `IconRemove` inside `.lib-card-pin` / `.lib-card-remove` (the 22px button); `IconRename`/`IconRemove` in `.lib-folder-actions` (20px button) → **14px** there so the glyph isn't cramped in the smaller button; `IconBookmark`/`IconPlus` lane "+" in the 20px button → **16px**. |
| **Inline link arrow** | **12px** | `IconArrowRight` after "Import VCF", "Open in Compare" — sits inline with 11–11.5px text, so 12 keeps optical balance (a 16px arrow would shout). `IconCheck`/`IconPlus` in the Save chip → **13px** to match the chip's 11.5px label. |

Rule of thumb: **icon ≈ text cap-height + ~1–2px**. Never larger than the label
it serves — Reading Room restraint.

### 2.3 Accessibility rule (one rule, no exceptions)

**The SVG is always decorative; meaning lives on the control.** Concretely:

- Every `<svg>` in this family carries `aria-hidden="true"` and **no** `<title>`,
  no `role="img"`. (The components hard-code `aria-hidden`; callers can't forget.)
- The **meaning** is carried by the hosting control's existing
  `aria-label` / `aria-pressed` / `aria-expanded`:
  - `.lib-card-pin` keeps `aria-pressed={pinned}` + `title="Pin for compare"` —
    `IconPin` is mute.
  - `.lib-card-remove` keeps `aria-label="Remove … from library"` —
    `IconRemove` is mute.
  - folder rename/delete keep `aria-label="Rename …"` / `aria-label="Delete …"`.
  - the disclosure chevrons live inside buttons that already carry
    `aria-expanded` (`wr-section-head`, `lib-folder-toggle`, `lib-lane-head`,
    `lib-row-caret`) — `IconChevron` is mute and rotates via the existing
    `[aria-expanded='true'] svg { transform: rotate(...) }` / `[data-open]` CSS.
  - inline arrows (`IconArrowRight`) sit **inside** a text link/button whose
    visible text ("Import VCF", "Open in Compare") *is* the label — the arrow is
    pure affordance, `aria-hidden`.

This is exactly today's `<span aria-hidden>` glyph treatment, made structural:
the icon can never leak a confusing accessible name, because it has none.

### 2.4 What does NOT change

- `ToolIcon.tsx` stays as-is (its 5 tool glyphs already obey the family;
  weight-2 is correct at tool-tab scale). The new module is a **sibling**, not a
  rewrite.
- `<Chevron>` in `WorkRail.tsx` and `<Caret>` in `VariantCardRow.tsx` are
  **folded into** `IconChevron` (one source), but their *rendered* size/weight
  is preserved (12px / 11px; the polyline-only mark keeps its 2.4 presence via a
  per-call `strokeWidth` override on the chevron only — see §2.0 note). Net DOM
  output is visually identical; the win is one definition instead of three.
- No CSS class changes are required: every host button already styles
  `color`/`width`-implied geometry. The icons drop into the existing JSX slots
  where the Unicode glyph is today (e.g. `LibrarySection` line 71 `⇄` →
  `<IconPin size={16} />`).

---

## 3. Visual-default recommendations (the 3 open choices from `phase-3-4-design.md` §9)

The sibling doc left three visual defaults for a call. Recommending one each,
grounded in the same restraint principle (one teal meaning; hairlines do
structure; quiet over loud).

### (a) Currently-open-report "you are here" card cue

**Recommend: the grey 2px left bar** (`box-shadow: inset 2px 0 0 var(--ink-4)`
+ `--bg-soft`), as `phase-3-4-design.md` §2.2 already drafted.

Rationale: teal is *selection* (`inset 3px --teal-deep` + `--teal-tint`). "You
are here" is **position**, not status — a second teal meaning would be the one
thing the Reading Room forbids (one accent, one meaning). A faint-teal cue
collides; "none" loses a genuinely useful orientation signal in a long worklist.
Grey at 2px (thinner than selection's 3px) reads as "current" without competing.

### (b) The single 0.5px folder nesting rule

**Recommend: keep it** (the one `border-left: 0.5px var(--line)` down a folder's
cards, `phase-3-4-design.md` §3.2).

Rationale: the worklist is deliberately *unruled* — cards self-separate by
hover/selection. Nesting is the **one** place that breaks down: without a tie,
indented cards float ambiguously. A single 0.5px hairline is exactly the
Reading-Room idiom ("hairlines do the structural work") applied where structure
genuinely exists. It's the lone rule, and it earns its place. Dropping it trades
a real legibility gain for a purity that the eye doesn't reward.

### (c) Section counts — pill chip vs bare number

**Recommend: the bare number** via `wr-section-meta` — i.e. **drop `.lib-count`**
for the top-level section heads (Saved / Folders / Compare tray).

Rationale: this is the one place I'd correct the sibling draft toward more
restraint. The `wr-section-meta` slot is already a quiet sans-500 `--ink-3`
number — it matches every other rail section across `/workbench` and `/compare`.
A `--bg-soft2` pill adds a second "count vocabulary" the rest of the rail doesn't
use, and three pills stacked down the rail head read busier than the worklist
itself. **Keep `.lib-count` only inside folder headers**, where a count sits
*mid-row* beside the folder name and a bare number would collide with the name —
there the pill earns separation. Section heads get the bare meta. One count
style per structural level: bare at section level, pill at row level.

---

## Summary of key calls

- **One steal, applied in our register:** Illustrae's asset *discipline* (a
  deliberately tiny, single-source family) becomes one self-authored clinical
  line-icon module `app/web/components/icons/Icon.tsx` — viewBox `0 0 24 24`,
  `strokeWidth 1.75`, round caps, `currentColor`, exporting `IconPin`,
  `IconRemove`, `IconBookmark`, `IconFolderMove`, `IconDropInto`, `IconRename`,
  `IconArrowRight`, `IconPlus`, `IconCheck`, `IconChevron`; it retires all 7
  Unicode glyphs (`⇄ ✕ ⌬ ▾ ⤓ ✎ →`) and folds in the existing `<Chevron>`/`<Caret>`.
  Everything else from Illustrae (teal `#4e8d99`, plum, Mantine rainbow, hand-drawn
  Comic Shanns, generous `--border-radius-lg`) is **rejected** — it fights the
  clinical Reading Room; the layout steal is **already done** (`<WorkRail>`).
- **No new global token, one accessibility rule:** icons size via a per-call
  `size` prop (12px chevron / 16px card action / 12px inline arrow), color via
  `currentColor` from the host button; every SVG is `aria-hidden` with meaning
  carried by the control's existing `aria-label`/`aria-pressed`/`aria-expanded`.
- **Three visual defaults recommended:** (a) "you are here" = grey 2px bar (teal
  stays selection-only); (b) keep the single 0.5px folder nesting rule (the one
  place structure truly needs it); (c) section counts = bare `wr-section-meta`
  number, pill `.lib-count` kept only at folder-row level.

File written: `D:\eamos\docs\workspace-rail\illustrae-complement-design.md`
