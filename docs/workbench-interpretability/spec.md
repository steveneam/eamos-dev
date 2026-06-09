# Workbench Pass D — interpretability spec

> **Status:** 🟡 SPEC — gated. **No code lands until Steven OKs.**
> Implementation spec for the three "Pass D — interpretability" items from the
> 2026-06-09 workbench audit ([`docs/workbench-audit/PLAN.md §4 D`](../workbench-audit/PLAN.md),
> [`primer-crispr.md §5`](../workbench-audit/primer-crispr.md), [`align.md §5`](../workbench-audit/align.md)).
> Active surface: `app/web` (Next.js 16, custom CSS + `globals.css` tokens). The
> `app/frontend/**` Vite copies are read-only reference and are **out of scope** —
> there is a second `CrisprPanel.tsx` at `app/frontend/src/components/workbench/crispr/`
> (graphify community 537); **do not touch it.**
>
> Each of the three items is **independently shippable + browser-verifiable** and
> can land as its own gated, verified commit. Recommended order: **D-1 score
> bullets** (self-contained, highest legibility lift) → **D-3 bridge** (small
> state lift, big flow win) → **D-2 Align lede** (most layout reflow).

---

## 0. Conventions this spec holds itself to

From `CLAUDE.md` / `DESIGN.md` / the audit:

- **Tokens, never raw hex.** All colour resolves to `globals.css` tokens.
- **`.eamos-mock` on gated/heuristic data** (`globals.css:414`), exactly as
  `SsodnLabDonor.tsx:158` already does in this directory.
- **Sequences stay monospace** (`var(--mono)`, `.seq`/`.mono`) — untouched.
- **Reuse `Icon.tsx` (1.75 weight, decorative `aria-hidden`)** for any new glyph;
  the host control carries the accessible name (`components/icons/Icon.tsx:16-34`).
- **`<EvidenceChip>` / `<TierTag>` for verdict/tier chips** where apt
  (`components/ui/`). **Not applicable to these three items** — see §1.4 (the
  score zones are an efficiency gauge, not an ACMG verdict, so they keep the
  score palette, not `--cls-*`).
- **Mock-first.** Every item works today against the existing mock fixtures with
  no backend change. Backend/contract notes (Codex's lane) called out per item.

---

## D-1 — CRISPR score bullet cells

### The problem (grounded)

On-target (0–100), off-target / CFD (0–1) and GC% render as **bare numbers
coloured by `.score-good` / `.score-mid` / `.score-bad`** — colour + font-weight
only, with the thresholds hidden in code:

- `workbench.css:1884-1886` — `.score-good {color:var(--teal-deep);font-weight:600}`,
  `.score-mid {color:var(--warn)}`, `.score-bad {color:var(--err)}`. **No shape,
  no track, no scale.**
- `DesignTab.tsx:70-75` — `offClass(v)` (`<20` good / `≤30` mid / else bad) and
  `onClass(v)` (`≥75` good / `≥60` mid / else bad). Thresholds invisible to the user.
- `DesignTab.tsx:503-509` — On-target cell (`onClass`), Off-target cell
  (`offClass`), **GC% cell with NO class at all** (`<td className="num">{g.gc_percent}</td>`)
  — reads flat even outside the 40–70 band.
- `OffTargetTab.tsx:32-34` — `offScoreClass(score)` (`≥0.2` bad / `≥0.05` mid /
  else good — note: **higher is worse** here, opposite sense to Design's on-target).
- `OffTargetTab.tsx:622-623` — off-target Score cell; `:592` — the pinned
  on-target row renders a hard-coded `1.000 score-good`.

Three audit findings converge here: **[L2 High]** colour-only magnitude,
**[L3 Medium]** two different scales (0–100 vs 0–1) rendered identically, and the
**GC% un-keyed** gap. [UPM Bullet-Chart AAA] + [UPM Color-Only High].

### The fix — a workbench-local `<ScoreBullet>` primitive

A compact, in-cell **bullet cell**: the numeric value (kept, tabular) sits beside
a thin horizontal track that shows **where the value lands on its range**, with
the **good zone tinted** and the active **threshold marked**. Magnitude becomes
non-colour (bar length + zone position), colour becomes redundant reinforcement.

**New file:** `app/web/components/workbench/ScoreBullet.tsx` (`'use client'` not
needed — pure presentational, no hooks/handlers).

```
interface ScoreBulletProps {
  value: number              // raw score
  min: number                // scale floor (0 for both On-target and CFD)
  max: number                // scale ceiling (100 On-target, 1 CFD, 100 GC%)
  // Threshold zone boundaries in VALUE units, low→high (1 or 2 entries):
  //   On-target: [60, 75]    (>=75 good, 60–75 mid, <60 bad)  higher better
  //   CFD/off:   [0.05, 0.2] (<0.05 good, 0.05–0.2 mid, >=0.2 bad) lower better
  //   GC%:       [40, 70]    (inside good, outside mid)        band
  thresholds: number[]
  sense: 'higher-better' | 'lower-better' | 'band'
  display: string            // pre-formatted label (keeps each callsite's toFixed)
  muted?: boolean            // heuristic / not-source-backed → dashed, ink-4
  title?: string             // full "value on min–max; good ≥ N" sentence
}
```

**Rendering model (Code Intent — NOT a diff):**

- Layout: a 2-column inline grid inside the `<td>` — `display` (right-aligned,
  `tabular-nums`, current `.num` treatment) then the track. Track is a flex row,
  fixed height **`6px`**, `border-radius:3px`, `background:var(--bg-soft)`,
  `box-shadow: inset 0 0 0 0.5px var(--line)` (matches the hairline language).
  Min width ~56px so it reads at the `min-width:920px` table.
- **Zone fill:** segment the track into the good/mid/bad regions by mapping each
  `thresholds[]` boundary to a fraction `(t - min)/(max - min)`. Tint each region
  with the **score palette** (good = `color-mix(in oklab, var(--teal-deep) 18%, transparent)`,
  mid = `color-mix(--warn 18%)`, bad = `color-mix(--err 14%)`) so the *good zone is
  visibly the target*, not just a colour on the number. For `sense:'band'` (GC%)
  the centre region (40–70) is the good tint, both tails mid.
- **Value marker:** a 2px-wide full-height `--ink` bar at `(value-min)/(max-min)`,
  with a `0 0 0 1.5px var(--bg)` ring so it reads on any zone tint (same marker
  idiom as `ScoreScale.tsx:38`, scaled down). Clamp position to `[0,1]`.
- **Colour of the number:** keep the existing `.score-good/mid/bad` text colour
  (derive the class from the same threshold logic) so the cell still passes a
  quick colour scan — but it is now **redundant** with the bar, satisfying
  [Color-Only].
- **`muted`:** when the provider is not source-backed (see backend note), drop the
  marker + number to `var(--ink-4)` and dash the track border — the established
  `.eamos-mock` affordance (`globals.css:414`), so a heuristic 74.3 doesn't read
  as a measured one.
- **a11y:** the track is `aria-hidden`; the cell already has a meaningful number.
  Put the full sentence on the existing `<th>` `title` (see range fix below) and
  a per-cell `title` via `ScoreBulletProps.title`
  (e.g. `"On-target 74.3 on 0–100 · good ≥ 75, weak < 60"`).

**CSS:** add a small `.score-bullet` block in `workbench.css` near the
`.score-*` rules (`1884-1887`). The three `.score-good/mid/bad` text rules
**stay** (still used for the number colour + the on-target `1.000` pin cell).
Inline styles are acceptable for the computed fractions (the `ScoreScale.tsx`
precedent uses inline styles for the same reason); keep static chrome in CSS.

### Wiring the three callsites

1. **Design On-target** — `DesignTab.tsx:503-505`. Replace the bare
   `<td className={...onClass}>` body with
   `<td className="num"><ScoreBullet value={g.on_target_score} min={0} max={100} thresholds={[60,75]} sense="higher-better" display={g.on_target_score.toFixed(1)} muted={!sourceBacked} title={…}/></td>`.
2. **Design Off-target** — `DesignTab.tsx:506-508`. Same, `min={0} max={1}`,
   `thresholds={[0.05,0.2]}`, `sense="lower-better"`, `display={…toFixed(1)}`.
   ⚠️ Note the contract quirk: this Design "off-target" field is on a **0–100-ish
   scale per `offClass` (`<20`/`≤30`)**, while the Off-targets-tab CFD score is
   **0–1 per `offScoreClass` (`≥0.05`/`≥0.2`)**. **Keep each callsite's existing
   thresholds and scale verbatim** — do not unify the numbers; only unify the
   *rendering*. (This is exactly the [L3] "two scales shown identically" trap —
   the fix is to surface the range, §below, not to make them the same.)
3. **Design GC%** — `DesignTab.tsx:509`. Currently un-keyed. Wrap in
   `<ScoreBullet value={g.gc_percent} min={0} max={100} thresholds={[40,70]} sense="band" display={String(g.gc_percent)}/>`.
4. **Off-targets Score** — `OffTargetTab.tsx:622-623`.
   `min={0} max={1} thresholds={[0.05,0.2]} sense="lower-better" display={s.score.toFixed(3)}`.
   `muted` is **not** applied here (the panel already self-discloses "mock
   Cas-OFFinder" globally at `:430-435`; a per-cell dash would double the tell).
5. **Off-targets pinned on-target row** — `OffTargetTab.tsx:592`. The hard-coded
   `1.000` can stay a plain `score-good` number **or** render a full-bar bullet
   for consistency; recommend the bullet (value 1.0 pinned hard right reads as
   "max" at a glance). Low stakes — implementer's call, note in PR.

Pull `sourceBacked` for the Design `muted` flag from the value already computed:
`const providerDisclosure = designProviderDisclosure(res)` →
`providerDisclosure.sourceBacked` (`DesignTab.tsx:161`, `crispr-disclosure.ts:63`).

### Surface the range ([L3])

Edit the visible `<th>` labels so the two scales are self-evident:

- `DesignTab.tsx:464` `On-target` → **`On-target (0–100)`**
- `DesignTab.tsx:467` `Off-target` → **`Off-target (lower safer)`**
- `OffTargetTab.tsx:570-571` `Score` → **`Score (CFD 0–1)`**

(`GC%` already reads as a percent.) Keep the existing rich `title` tooltips.

### Why a workbench-local primitive, not report's `ScoreScale.tsx`

Considered reusing `<ScaleTrack>`/`<ScorePin>` (`components/report/ScoreScale.tsx`).
**Rejected** because:

- `ScaleTrack` is a **pin-on-a-banded-axis** tuned for report-card width (8px
  track, 6px triangle pin + 12px stem, dashed threshold tick `:102-116`) — it
  overflows a 11.5px `td.num` row and reads as a different object than a table
  figure.
- Its own header comment scopes it to the report's calibrated evidence bars and
  the `--cls-*` ramp; the file deliberately documents that **§1 MAVE does not use
  it** because forcing pin-on-axis "implies a precision the bands don't have" — the
  same caution applies to a dense CRISPR table cell.
- A bullet cell is a **different chart** ([UPM Bullet-Chart]: value bar vs a
  qualitative-range background), not a marker-on-scale.

So `ScoreBullet` borrows `ScorePin`'s **marker idiom** (2px ink bar + `--bg`
ring) for visual kinship, but is its own compact primitive. If a later pass wants
one shared "scale" abstraction across report + workbench, that is a separate
convergence task (out of scope here).

### Backend / contract

**Pure FE.** No contract change — every field (`on_target_score`,
`off_target_score`, `gc_percent` on `CrisprGuide`; `score` on
`CrisprOffTargetSite`, `backend.ts:1234-1242,1318-1330`) already exists. `muted`
keys off the **existing** `source_backed` disclosure flag the FE already reads;
**no new field requested.** (If Codex later adds per-score provenance, the
`muted`/`title` inputs are the natural seam — note only, not a request.)

### Acceptance criteria

- [ ] On-target, Off-target, GC% (Design) and Score (Off-targets) each render a
      value **plus** a thin track with a tinted good zone and a value marker.
- [ ] Magnitude is legible **with colour vision disabled** (grayscale screenshot):
      bar length + marker position convey high/low without hue.
- [ ] The Design on-target (0–100) and Off-targets CFD (0–1) bullets visibly
      differ in scale, and the headers state the range.
- [ ] GC% inside 40–70 lands in the good zone; a 25% or 80% GC value lands in a
      tail zone (previously rendered flat/un-keyed).
- [ ] When the Design provider is **not** source-backed, the on-target/off-target
      bullets show the `.eamos-mock` dashed/muted treatment; when source-backed,
      they render solid.
- [ ] No raw hex introduced; `npm --prefix app/web run lint` clean; sequences
      still monospace.

---

## D-2 — Align result-card 3-tier hierarchy

### The problem (grounded)

`PairwiseView.tsx` renders **7 equal-weight metric tiles** in a flat
`auto-fit minmax(108px,1fr)` grid, so the answer a user wants ("does my read
match? where does it differ?") reads at the same size/weight as the
coordinate-span tiles:

- `PairwiseView.tsx:140-185` (`Summary`) — Identity, Coverage, Matches,
  Mismatches, Gaps, **Ref span, Read span** all via the same `<Metric>` at the
  same `.align-metric` weight.
- `workbench.css:2017-2048` — `.align-summary` flat grid; `.align-metric b`
  uniform 12px; the tone classes `b.ok/.warn/.err` (`2046-2048`) tint but do
  **not** resize.
- `PairwiseView.tsx:83-96` — the `◀▶` difference nav + the **active-diff label**
  (`align-diff-current`, the most "answer-like" element, `:94`) sit in a thin row
  *below* the metric grid.
- `PairwiseView.tsx:261-269` (`differenceLabel`) — already computes the human
  sentence (`ref 412: A→G`). `ReadRow.tsx:58-101` head already computes
  `identity%`, `N real`, `N low-Q`, `N het`, `core span`, source.

Audit findings **[L1]** (flat strip, no primary) + **[F1]/[F2]** (promote the
answer into a lede; make the diff navigator the focal point; turn the "No
mismatches" note into a confident green confirmation, not a muted aside,
`PairwiseView.tsx:237`).

### The fix — lede → strip → caption

Restructure the **top of `.align-results`** (`PairwiseView.tsx:73-119`) into
three tiers. **No new data** — every value already exists.

**Tier 1 — the LEDE (new, loud).** A single sentence card that states the answer:

> **96.2% identity** · 1 difference at ref 412 (A→G) · 1 het

Composition:

- **Identity** — promote to ~18–20px `--ink` (the loudest figure), tone-aware
  (`alignment.identity` → currently `formatPercent`, `PairwiseView.tsx:144,271`).
- **The active-difference clause** — reuse `differenceLabel(alignment.differences[safeActive])`
  (already rendered at `:94`) when `diffCount>0`; render the **count + active
  label** inline ("1 difference at ref 412 (A→G)" / "3 differences · ref 412
  (A→G)"). When `diffCount===0`, render a **confident green** "Exact match — no
  mismatches or gaps" using `--teal-deep`/`--teal-tint` (this is the [F2] fix —
  the good answer should look good, not muted like the current `align-diff-note`).
- **Het clause** — when `hetIndices.size>0`, append "· N het". `hetIndices`,
  `realMismatch`, `lowQMismatch` already flow into `PairwiseView` as props
  (`:23-24`) and are shown in the `ReadRow` head (`ReadRow.tsx:82-90`).
- The **`◀▶` diff navigator** (`PairwiseView.tsx:84-93`) moves **up into / beside
  the lede** ([F2]) so stepping differences is adjacent to the answer, not a
  detached row. Keep its behaviour (drives `activeCol` + smooth-scroll) verbatim.

**Tier 2 — the STRIP (demoted, kept).** The quantitative metrics stay as the
`.align-summary` grid but **without** Identity (now the lede) — keep Coverage,
Matches, Mismatches (still the click-toggle, `:158-165`), Gaps (toggle,
`:166-173`). These remain the existing `<Metric>`/`.align-metric` tiles,
unchanged weight.

**Tier 3 — the CAPTION (demoted hard).** **Ref span + Read span** drop out of the
tile grid into a single muted caption row under the strip: `--ink-4`, ~11px,
`tabular-nums`, e.g. `Ref 1–520 · Read 4–518`. Reuse the existing
`formatRange` (`PairwiseView.tsx:275-278`).

> ⚠️ **[L7] watch:** `formatRange` returns `${start+1}-${end}` while
> `differenceLabel` uses `referenceIndex+1`. When Ref span and the active-diff
> label sit closer together (lede vs caption), verify the conventions read
> consistently for a user cross-referencing "ref 412" against the span. This is a
> *glance-check during implementation*, not a code change in this spec — flag if
> they diverge.

**Component shape (Code Intent):**

- Add a `Lede` sub-component in `PairwiseView.tsx` (sibling to `Summary`,
  `Metric`, `DifferenceList`) taking `{ alignment, hetCount, activeDiff, diffCount,
  onStep, onSelectDiff }`. It owns Tier 1 (sentence + nav).
- `Summary` loses the Identity/Ref-span/Read-span `<Metric>`s; gains nothing.
- Render order in `PairwiseView` (`:73-117`): `<Lede/>` → `<Summary/>` (strip) →
  caption row → `<AlignedTrace/>` → `<DifferenceList/>`. The `AlignedTrace` and
  `DifferenceList` blocks are **unchanged**.

**CSS:** new `.align-lede` block in `workbench.css` (near `.align-summary`,
`2017`). Inline-baseline flex: big Identity, a tone-driven diff clause (reuse the
`--err`/`--err-tint` pill grammar already on `.align-diff-current`, `2140-2147`,
for the "has differences" case; `--teal-deep`/`--teal-tint` for the exact-match
case). Add `.align-spans-caption` (the Tier-3 row). The 7-up `.align-summary`
grid stays but now holds 4 tiles.

### Reuse / convergence note

The audit pairs this with **C5 "unify the result-card primitive across
Primer/CRISPR/Align"** (PLAN.md §3.2 / align §5 D2), with **Primer's
`PrimerResultCard` as the reference**. That cross-tool convergence is a **separate,
larger gated pass** — this spec deliberately scopes D-2 to **Align only** so it
ships independently. The `Lede` component is written so a later pass can lift it
toward a shared `ResultCardLede`. Do **not** expand scope to Primer/CRISPR here.

`<EvidenceChip>` is **not** used: the lede clauses are a metric sentence + a
diff-state pill, not an ACMG/strength verdict; the existing `--err`/`--teal`
pill tokens are the right vocabulary and keep parity with `.align-diff-current`.

### Backend / contract

**Pure FE.** Zero contract surface — all inputs (`alignment.*`, `hetIndices`,
`differences`) are already computed client-side in `read-model.ts` /
`alignment-pairwise` and passed into `PairwiseView`. No Codex dependency.

### Acceptance criteria

- [ ] On a read with ≥1 difference, the first line of the result card reads as a
      sentence with **Identity** as the largest figure and the **active-diff label**
      (`ref N: X→Y`) inline; stepping `◀▶` updates the label in the lede.
- [ ] On an exact-match read (`diffCount===0`), the lede shows a **green**
      "Exact match" confirmation (not a muted grey aside), and the diff navigator
      is absent.
- [ ] **Ref span / Read span** no longer appear as full-weight tiles — they read
      as one muted `--ink-4` caption line.
- [ ] The strip shows Coverage / Matches / Mismatches / Gaps; Mismatches & Gaps
      still toggle their chip lists (`showMismatch`/`showGap` behaviour intact).
- [ ] Eye lands on the answer in <1s (heading-hierarchy check; verify against a
      multi-read alignment).
- [ ] `npm --prefix app/web run lint` clean; no raw hex; sequences monospace.

---

## D-3 — Design → Off-targets deep-link bridge

### The problem (grounded)

The recommended guide is designed in the **Design** sub-tab, but to screen it the
user must **switch to the Off-targets sub-tab and hand-retype the 20-mer + PAM +
locus**. Today the two tabs share nothing:

- `CrisprPanel.tsx:31-83` — owns `const [tab, setTab] = useState<SubTab>('design')`
  and renders `<DesignTab>` / `<OffTargetTab>` / `<OutcomesTab>` with **no shared
  state** beyond `gene`/`cdna`.
- `DesignTab.tsx:478-516` — guide rows; the recommended one is `recIdx`
  (`:200`, `recommendedGuideIndex`, `crispr-guide-ranking.ts:8`) and is marked
  `'rec. '` + `★` (`:396, :490`). Each row has `g.guide`, `g.pam`, `g.strand`,
  and a template-relative position via `mapGuide` (`:479`).
- `OffTargetTab.tsx:140-160` — the inputs to pre-fill:
  `guide` (`DEFAULT_GUIDE`, `:142`), `pam` (`:143`), `chrom` (`:146`),
  `pos` (`:147`), `strand` (`:147`). Form fields render at `:327-412`.

Audit **§4 / §5.1 (highest-leverage flow fix)**: a per-row "Screen this guide for
off-targets" action that switches the panel to Off-targets and pre-fills the
spacer — "turns three tabs into one workflow."

### The fix — lift a `screenSeed`, add a per-row action

**State lift (minimal):** `CrisprPanel` already owns `tab` — add one sibling
state object and pass setters down. **No global store** (the variant-library
store is for cross-surface state; this is two sibling tabs in one panel).

```
// CrisprPanel.tsx
interface ScreenSeed {
  guide: string
  pam: string
  chrom?: string         // optional — locus may be template-relative, see below
  pos?: string
  strand?: '+' | '-'
  source: string         // e.g. "Design · guide 3 (recommended)" for a provenance line
}
const [screenSeed, setScreenSeed] = useState<ScreenSeed | null>(null)
```

- `<DesignTab onScreenGuide={(seed)=>{ setScreenSeed(seed); setTab('offtargets') }} />`
- `<OffTargetTab seed={screenSeed} onSeedConsumed={()=>setScreenSeed(null)} />`

**Design side — the per-row action** (`DesignTab.tsx`):

- Add a prop `onScreenGuide?: (seed: ScreenSeed) => void`.
- Add a **trailing cell** (or fold into the existing `Notes` cell `:513`) per
  guide row with a compact action button:
  `<button type="button" className="ots-export-btn" title="Screen this guide genome-wide for off-target sites" onClick={()=>onScreenGuide({ guide:g.guide, pam:g.pam, strand:g.strand, source:`Design · guide ${g.index}${g.index===recIdx?' (recommended)':''}` })}>Screen ↗</button>`
  - Use the existing subtle `.ots-export-btn` button style (already a quiet
    workbench action button) — **do not** introduce a new button class.
  - Leading glyph: `IconScope` (crosshair "aim at this locus",
    `Icon.tsx:188-199`) at `size={13}` — it is the closest existing verb to
    "screen this site" and is already the Workbench "active scope/target" glyph.
    The button keeps a real text label ("Screen"); the icon is decorative
    (`aria-hidden`, per the Icon contract).
  - **Add a header `<th>`** for the action column (`DesignTab.tsx:474-475`,
    after `Notes`) so the table stays well-formed; bump the empty-state
    `colSpan` (`:519`) from `10` → `11`.
  - **Recommended-row emphasis:** the rec row already has `.selected`
    (`:484`); no extra styling needed — but the action there reads as the
    primary next step.

**Off-targets side — consume the seed** (`OffTargetTab.tsx`):

- Add props `seed?: ScreenSeed | null` and `onSeedConsumed?: () => void`.
- On mount / when `seed` changes, **pre-fill the form once**: `setGuide(seed.guide)`,
  `setPam(seed.pam || 'NGG')`, and `setStrand(seed.strand)` when present; then
  call `onSeedConsumed()` so re-entering the tab manually doesn't clobber edits.
  Use a `useEffect` keyed on a stable seed id (e.g. `seed?.guide`), guarded so it
  runs only when a *new* seed arrives (compare against a `useRef` of the last
  consumed guide), mirroring the existing "reset on change" pattern in
  `ReadRow.tsx:51-55`.
- **Locus pre-fill caveat (important):** Design positions are **template-relative**,
  not genomic (`DesignTab.tsx:448-451,471` "not genomic coordinates"), while the
  Off-targets `chrom`/`pos` want a **genomic** anchor (`:370-397`). So **do not
  fabricate a genomic locus from the template offset.** Pre-fill `guide`/`pam`
  (and `strand` if set); **leave `chrom`/`pos` at their existing defaults** and
  show a one-line `.help-note` provenance + caveat:
  > Seeded from {seed.source}. Spacer + PAM filled; set the genomic on-target
  > locus below before enumerating (Design positions are template-relative).
- Render that provenance line only while a seed-derived guide is active (clears
  on manual edit via the existing `clearComputed`, `:167-173`). Mark it with
  `.eamos-mock`? **No** — it's a real provenance note, not mock data; use a plain
  `.help-note` (the panel's existing idiom, e.g. `:430`).

**Flow nicety:** after `setTab('offtargets')`, the user lands on a form already
holding their spacer — they only confirm the locus + hit **Enumerate**. That is
the "three tabs → one workflow" win.

### Reuse / scope

- Reuses `.ots-export-btn` (button), `IconScope` (glyph), `.help-note`
  (provenance), `.selected` (rec row) — **no new component or class.**
- State lift is local to `CrisprPanel` (the existing tab owner). The audit's
  "1 Design → 2 Screen → 3 Confirm" ordinal-hint idea (PLAN.md §4 flow) is a
  **separate copy/affordance task** — out of scope here; this spec ships just the
  functional bridge.

### Backend / contract

**Pure FE.** No new endpoint, no contract change — `OffTargetTab` already calls
`enumerateOffTargets` with these inputs; the bridge only **pre-fills existing
form state**. The genomic-locus gap is a *product* reality (Design is
template-relative), surfaced as copy, **not** a backend ask. (If Codex later
returns a genomic anchor on `CrisprGuide`, the `chrom`/`pos` seed fields are the
ready seam — note only.)

### Acceptance criteria

- [ ] Each Design guide row has a "Screen ↗" action; clicking it switches the
      panel to the **Off-targets** sub-tab.
- [ ] On arrival, the Off-targets **Guide protospacer** and **PAM** inputs are
      pre-filled from the clicked guide (and **Strand** when available); the user
      did not retype the 20-mer.
- [ ] A provenance `.help-note` states which guide seeded the form **and** the
      template-relative-locus caveat; `chrom`/`pos` remain editable defaults
      (no fabricated genomic coordinate).
- [ ] Editing the protospacer manually afterwards clears the seed provenance
      (no stale "seeded from…" line) and behaves exactly as today.
- [ ] Switching tabs back and forth without clicking the action does **not**
      re-pre-fill or clobber a manual edit (seed consumed once).
- [ ] Table stays well-formed (header + empty-state `colSpan` updated); lint clean.

---

## Cross-item summary

| Item | Files (active `app/web`) | New file | Backend? | Ships alone |
|---|---|---|---|---|
| **D-1** score bullets | `crispr/DesignTab.tsx` (`70-75,464-509`), `crispr/OffTargetTab.tsx` (`32-34,570-623`), `workbench.css` (`1884-1887`) | `components/workbench/ScoreBullet.tsx` | No (pure FE; uses existing `source_backed`) | ✅ |
| **D-2** Align lede | `align/PairwiseView.tsx` (`73-185,261-278`), `workbench.css` (`2017-2048,2140-2147`) | (sub-component in `PairwiseView`) | No | ✅ |
| **D-3** bridge | `crispr/CrisprPanel.tsx` (`31-83`), `crispr/DesignTab.tsx` (`200,474-519`), `crispr/OffTargetTab.tsx` (`140-160,327-412`) | none | No | ✅ |

**Shared discipline:** tokens-only; `.eamos-mock` for heuristic data (D-1 only,
keyed off `source_backed`); `Icon.tsx` for the one new glyph (D-3 `IconScope`);
sequences stay `--mono`; **do not touch the `app/frontend` Vite copies**; each item
is its own gated, browser-verified commit (`npm --prefix app/web run dev` →
`/workbench`, load a variant, exercise CRISPR Design/Off-targets + Align).

**Browser-verify checklist (all three):** grayscale screenshot for D-1 colour
independence; multi-read + exact-match alignment for D-2; click-through
Design→Off-targets for D-3.

**Explicitly deferred (not in this spec):** cross-tool result-card convergence
(C5 / Primer reference), the "1→2→3" ordinal sub-tab hint, sticky table headers
([L1]), the Cas-enzyme / mismatch-dedup / Outcomes-gate controls (audit §5
items 3–7), a shared report↔workbench scale abstraction. Each is its own gated
pass.
