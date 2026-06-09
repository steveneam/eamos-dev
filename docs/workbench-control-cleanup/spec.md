# Workbench control-cleanup — implementation spec (`/workbench`)

> **Status:** 🟡 GATED — review-required. **No `app/web/**` code lands until Steven OKs.**
> Consolidates the small, independently-shippable, browser-verifiable items flagged in
> `docs/workbench-audit/primer-crispr.md §5` (A) and `docs/workbench-audit/gene-viewer.md §5`
> (B/C/D). Each item below is self-contained: own files, own acceptance test, own commit.
> Per [[feedback_subagent_recommendations_not_authorization]] the **structural** ones (C, and the
> handle change in D) need an explicit yes before code; the rest are token/copy/legend additive.

**Active surface:** Next.js 16 `app/web` (custom CSS + `globals.css` tokens). Vite `app/frontend` is the
frozen reference, out of scope.

**Conventions enforced throughout** (CLAUDE.md + DESIGN.md):
- Tokens, never raw hex. Verdict colour only via `--cls-*` (the `lib/classification.ts` ramp); base colour
  only via `--base-A/T/C/G` (`globals.css:124-127`); feature/state colour via `--warn-*`/`--teal-*`/`--info-*`.
- Reuse `Icon.tsx` (1.75 pen) — here `<IconRename>` (`Icon.tsx:88`). Reuse `<TierTag>` (`ui/TierTag.tsx`),
  `<InfoHint>` (`ui/InfoHint.tsx`) where a hint/badge is wanted.
- Sequences stay monospace (`--mono`). Mock-first; any sample/fallback surface keeps an honest marker.
- Animate transform/opacity only; durations via `--dur-*`.

**Backend (Codex) dependency callout:** only **A4 (Outcomes gating)** has a real backend coupling (the TIDE
contract). Everything else is **pure frontend**. A4 is therefore specced as a *FE-only "Preview" brand now*,
with the *gate* deferred to Codex — see A4.

---

## Item index + leverage ranking

Ranked by leverage-per-effort (highest first). "Effort" is relative dev size; "Risk" is visible-regression risk.

| Rank | ID | Title | Type | Effort | Risk | Backend |
|---|---|---|---|---|---|---|
| 1 | **A1** | Collapse Cas-enzyme `<select>` → "SpCas9 · NGG" chip | FE, copy+markup | XS | low | none |
| 2 | **A2** | Drop faux "Target window: server-resolved" input | FE, markup | XS | low | none |
| 3 | **B2** | Conservation track PhyloP min/max scale chip | FE, additive chart | XS | low | none |
| 4 | **A3** | De-duplicate the two mismatch controls (relabel) | FE, copy | XS | low | none |
| 5 | **B1** | Protein view colour→ACMG legend + point-feature key | FE, additive legend | S | low | none |
| 6 | **A5** | Outcomes styled file-picker (reuse `align-file-btn`) | FE, markup+css | S | low | none |
| 7 | **D**  | Visible single-base Edit affordance | FE **structural** (1 handle method) | S | med | none |
| 8 | **A4** | Outcomes self-disclaimers → one "Preview" brand | FE now / gate=Codex | S | low | **yes (gate)** |
| 9 | **C**  | FullLocus "Full gene" parity (recommend **C-b** relabel now, **C-a** colour next) | FE **structural** | C-b: S / C-a: M | med | none |

Rationale for the ordering: A1/A2/A3 are the purest "purpose-or-remove" wins — they delete confusion for
near-zero code and zero risk, and they directly answer the owner's "every interactable must justify itself"
lens. B2 is the cheapest legibility gain (a 2-tick chip on an axis-less chart). B1 and A5 are slightly larger
but still additive and low-risk. D and C are the two genuinely structural items (new interaction entry / new
render behaviour) and carry the only medium regression risk, so they sort last; A4 sits beside them because
its honest fix is FE-cheap but its *correct* end-state waits on a Codex contract.

---

## A. CRISPR — resolve faux / disabled / duplicate controls

### A1 — Collapse the Cas-enzyme `<select>` to a single "SpCas9 · NGG" chip

**Problem (grounded).** `DesignTab.tsx:235-251` renders a `<select>` whose 3 options come from
`CAS_OPTIONS` (`:22-48`); two of them (`SaCas9`, `Cas12a`) are `disabled: true` and exist only to be greyed
out, and the `onChange` at `:239-244` early-returns on any non-`SpCas9` value (`if (nextCas !== 'SpCas9') return`)
— so the control can never change state. It is a 3-option dropdown with 1 reachable option. The two
unavailable enzymes then re-emit their `caveat` strings as standalone `help-note` lines at `:324-328`
(`unavailableCas.map(...)`), and `selectedCas.caveat` adds a third at `:323`. That is three caveat lines
explaining a control the user can't operate.

**Decision.** Replace the `<select>` with a static, non-interactive chip reading **`SpCas9 · NGG`** plus a one-line
"more enzymes coming" note. Drop `CAS_OPTIONS` down to the single SpCas9 entry (or inline the label) and remove
the two `disabled` options and the two redundant `help-note` lines.

**Files**
- `app/web/components/workbench/crispr/DesignTab.tsx`
- `app/web/components/workbench/workbench.css` (one new `.crispr-enzyme-chip` rule)

**Code intent**
- In `DesignTab.tsx`, replace the `Cas enzyme` `<label className="field">…</label>` block (`:233-252`) with a
  read-only field: keep the `field-label` "Cas enzyme", render a static chip element (`<span className="cra-meta">`
  is the existing "pill-ish" class, or a new `.crispr-enzyme-chip`) containing the text `SpCas9 · NGG`. No
  `<select>`, no `onChange`.
- Trim `CAS_OPTIONS` (`:22-48`) to the single `SpCas9` object (keep its `caveat` if A1 keeps one note), and delete
  the `SaCas9`/`Cas12a` entries.
- Remove `unavailableCas` (`:160`) and its `.map` render block (`:324-328`). Keep at most ONE provider note: prefer
  the existing `providerDisclosure` lines (`:317-322`) — drop `selectedCas.caveat` at `:323` too if it now duplicates
  the chip's "real-mode SpCas9 only" message. Net: the `crispr-caveats` block loses 1-3 lines.
- The `cas` state (`:148`) stays `'SpCas9'` and is still passed in the `CrisprRequest` payload (`:185`) — the request
  shape is unchanged, so the backend contract is untouched.
- `casPam()` (`:78-80`) and the summary "Enzyme" cell (`:366-370`) can stay; they already read `SpCas9 · NGG`.

**Token/convention notes.** Chip uses `--teal-tint`/`--teal-bdr`/`--teal-deep` (matches the read-only,
"locked-in" feel) or the neutral `--bg-soft`/`--line`. No raw hex.

**Acceptance criteria**
- The Design form shows a non-interactive "SpCas9 · NGG" chip where the dropdown was; there is no `<select>` for Cas
  enzyme in the DOM.
- Exactly one (or zero) caveat line about enzyme support remains; the two "(unavailable)" lines are gone.
- Designing guides still works and the request still carries `cas: 'SpCas9'` (network payload unchanged).
- Keyboard tab order no longer stops on a dead dropdown.

---

### A2 — Drop the faux "Target window: server-resolved" input

**Problem (grounded).** `DesignTab.tsx:289-298` renders a `<label className="field">` with a disabled, readOnly
`<input type="text" value="server-resolved">`. It looks like an input, is permanently inert, and sits in the form
immediately before the CTA — an inverted input affordance. There is already a `help-note` at `:448-451` explaining
that Start/End/Region are template-relative offsets.

**Decision.** Remove the faux input entirely. Fold its meaning into the existing help-note (the design window is
resolved server-side from the gene/cDNA), so no information is lost.

**Files**
- `app/web/components/workbench/crispr/DesignTab.tsx`

**Code intent**
- Delete the entire `Target window` `<label>` block (`:289-298`).
- Append a short clause to the existing post-CTA `help-note` (`:448-451`) or the provider note: e.g. "The design
  window is resolved on the server from the selected gene / cDNA." (Plain caption text, not a control.)
- No state to remove (the value was a literal string).

**Acceptance criteria**
- No disabled "server-resolved" text input exists in the Design form.
- The "design window is server-resolved" idea is still stated as caption/help text.
- The form now ends with three live fields (Cas chip is static, Strand, Off-target tolerance) → CTA, with no inert
  field interrupting the run path.

---

### A3 — De-duplicate the two mismatch controls (search vs view)

**Problem (grounded).** Off-targets has two near-identically-named numeric controls:
- **Search radius** — `OffTargetTab.tsx:355-369`, label "Max mismatches", state `maxMismatches` (`:144`), sent in the
  enumeration request `max_mismatches` (`:196`). This bounds *what the genome search returns*.
- **View filter** — `OffTargetTab.tsx:537-549`, label "Max mm", state `filterMm` (`:156`), used in `visibleOff`
  (`:220-221`) to hide rows client-side. This bounds *what the already-returned table shows*.

Two controls, both 0-4, named "Max mismatches" / "Max mm", on the same surface — the panel's biggest confusion
(audit §2 / §4). The empty-state at `:648-650` and the autoPick tooltips also lean on "mismatches" ambiguously.

**Decision.** Disambiguate by label + tooltip rather than merge (they are genuinely two different operations —
search budget vs display filter — and merging would lose the ability to over-fetch then narrow). Rename to make the
distinction unmistakable:
- Search field → **"Search ≤ N mm"** (label) — "Genome search radius: the maximum mismatches the search will *return*."
- Curate field → **"Show ≤ N mm"** (label) — "Display filter: hide returned off-targets above this many mismatches."

**Files**
- `app/web/components/workbench/crispr/OffTargetTab.tsx`

**Code intent**
- Search field (`:355-369`): change `<span className="field-label">Max mismatches</span>` → `Search ≤ N mm` (render
  the live value, e.g. `Search ≤ {maxMismatches} mm`), and add/clarify a `title` on the `<label>` stating it is the
  *search return radius* (this field currently has no `title`).
- Curate field (`:537-549`): change `<span className="field-label">Max mm</span>` → `Show ≤ {filterMm} mm`; update the
  existing `title` (`:538-540`) to say "Display filter — hides already-returned off-targets above this many mismatches
  (does not re-run the search)."
- Optionally align the empty-state copy (`:648-650`) to "No off-targets shown at ≤ {filterMm} mm" so it reads as a view
  filter, not a search result.
- No state/behaviour change — relabel only.

**Acceptance criteria**
- The two controls read "Search ≤ N mm" and "Show ≤ N mm"; neither is just "Max mm".
- Each has a tooltip that names which operation it bounds (search return vs display filter).
- Behaviour is identical (over-fetch then narrow still works).

---

### A4 — Outcomes self-disclaimers → one "Preview" brand (gate deferred to Codex)

**Problem (grounded).** `OutcomesTab.tsx:113-126` stacks **three** `help-note` caveats before any result, all
saying variations of "this is sample/fallback, not a real TIDE solve" (`:114-117`, `:118-121`, `:122-125`). A tab
that opens by disclaiming itself three times reads as unfinished (audit §4: "commit or preview"). The disclosure
text comes from `outcomeDisclosure(res)` (`lib/workbench/crispr-disclosure`) and the sample type
`crispr-tide-sample`.

**Decision (two-phase, FE now).**
- **Now (FE-only):** brand the tab **once** at the top with a single "Preview" marker (reuse `<TierTag>`? — no, that's
  Free/Pro; instead a small inline "Preview" pill in the section/tool header, styled like `.crispr-result-note`'s
  warn-tint), and collapse the three stacked caveats into **one** concise honest line ("Preview — outcomes are
  observed-only sample/fallback until a source-backed TIDE/Lindel result is returned."). Keep the per-result
  `predictionLine`/`notes` (`:157-158`) which are already conditional on real data.
- **Later (Codex):** the *real* gate — hide/replace the Preview surface when the backend returns source-backed TIDE
  with numeric predicted bins — depends on the TIDE contract (`outcomeDisclosure` already inspects `res`; the
  `showPredicted`/`seriesLabel` fields are the hook). **Flag to Codex:** define when `outcomeDisclosure` should report
  "real" vs "preview" so the FE can drop the Preview brand.

**Files**
- `app/web/components/workbench/crispr/OutcomesTab.tsx`
- `app/web/components/workbench/workbench.css` (one `.crispr-preview-tag` rule, or reuse `.crispr-result-note`)
- (later) `app/web/lib/workbench/crispr-disclosure.ts` — Codex-owned gate logic

**Code intent**
- Add a one-time "Preview" pill near the top of the `crispr-outcomes` block (above the form, or in the `btn-row`'s
  `tool-panel-sub`), shown whenever `outcomeInfo` indicates sample/fallback (the existing disclosure object already
  distinguishes this — confirm the flag name with Codex; today `outcomeInfo.showPredicted` / `sourceLabel` carry it).
- Replace the three `help-note`s at `:113-126` with a single `help-note` carrying the consolidated sentence.
- Do NOT remove the honest per-result lines (`:157-158`).
- Leave the Codex gate as a TODO comment referencing the contract.

**Token/convention notes.** Preview pill uses `--warn-tint`/`--warn-bdr`/`--warn-text` (same family as
`.crispr-result-note`), uppercase 9.5px like `<TierTag>` for visual kinship. `.eamos-mock` marker stays where the
sample data is surfaced.

**Acceptance criteria**
- The Outcomes tab shows **one** "Preview" marker and **one** consolidated caveat line, not three stacked disclaimers.
- The marker is present in mock/fallback mode and is wired to disappear when the disclosure object reports a
  source-backed solve (gate logic owned by Codex; FE reads the flag).
- A paste-ready Codex note is included (below) describing the contract hook.

---

### A5 — Outcomes styled file-picker (reuse Align's `align-file-btn` label pattern)

**Problem (grounded).** `OutcomesTab.tsx:54-79` renders two raw native `<input type="file" className="field-input
crispr-file">` controls (`.crispr-file` styles them only with padding/font, `workbench.css:2750`). The OS file button
breaks the clinical surface. Align already solved this: `AlignPanel.tsx:168-179` wraps a *hidden* `<input type="file">`
inside a styled `<label className="align-read-btn align-file-btn">` so the visible control is a teal button reading
"Upload FASTA", with the chosen filename shown elsewhere.

**Decision.** Mirror the Align label pattern for both Outcomes file inputs: hidden `<input>`, styled `<label>` button,
and surface the chosen filename (the tab already prints `control?.name`/`edited?.name` in `tool-panel-sub` at `:108`).

**Files**
- `app/web/components/workbench/crispr/OutcomesTab.tsx`
- `app/web/components/workbench/workbench.css` (reuse `.align-file-btn` / `.align-read-btn`; add a small
  `.crispr-file-btn` only if a CRISPR-specific accent is needed — prefer reuse)

**Code intent**
- For each of the two `<label className="field">` blocks (`:54-66`, `:67-79`), keep the `field-label` ("Control trace
  …" / "Edited trace …") and replace the raw `<input className="field-input crispr-file" type="file" …>` with the
  Align idiom:
  ```
  <label className="align-read-btn align-file-btn">
    {control ? 'Replace file' : 'Choose file'}
    <input type="file" accept=".ab1,.json" hidden disabled={loading}
           onChange={(e) => { setControl(e.target.files?.[0] ?? null); clearComputed() }} />
  </label>
  ```
  (same for `edited`/`setEdited`).
- Keep the existing filename echo in `tool-panel-sub` (`:107-110`) so the user still sees what they picked; optionally
  add an inline filename next to each button.
- Remove the now-unused `.crispr-file` class usage (the rule can stay or be flagged dead per CLAUDE.md surgical rule —
  mention it, don't delete unrelated CSS unless it becomes orphaned by this change; here it does, so removing the
  `.crispr-file` rule at `workbench.css:2750` is in-scope).
- `accept=".ab1,.json"` and the `disabled={loading}` behaviour are preserved.

**Acceptance criteria**
- Both trace inputs render as styled buttons (teal `align-read-btn`), not the native OS file widget.
- The chosen filename is still visible after selection.
- `.ab1`/`.json` accept filter and loading-disable still apply; Analyze still runs.

---

## B. Gene viewer — legends

### B1 — Protein view: colour→ACMG legend + point-feature key

**Problem (grounded).** `ProteinView.tsx` draws two colour-coded layers with no legend:
1. **Lollipop heads** (`:164-190`) — `.sv-pv-headdot.{p,lp,vus,lb,b}` are the `--cls-*` verdict dots
   (`workbench.css:3156-3160`). Only the *queried* one is labelled (`:183-187`); every other variant's ACMG class is
   communicated by hue alone. CVD users can't tell P from LP from VUS. There is no class key anywhere in the protein
   view.
2. **Point features** (`:247-269`) — `.sv-pv-pt.{active,palmitoyl,query}` (`workbench.css:3225-3230`) are
   colour+shape coded (active = `#BA7517`, palmitoyl = `--base-C` teal, query = `--ink` larger). No legend says which
   diamond is which.

There IS an existing legend block — `.sv-pv-legend` (`:280-294`, CSS `3238-3242`) — which already carries the
"uniform size" honest note. The audit explicitly says to **extend this block** to also carry the colour keys.

**Decision.** Extend `.sv-pv-legend` with two compact key rows:
- **ACMG class key:** five swatches (`--cls-*-dot` colours) + labels from `classLabel()` — `Pathogenic /
  Likely Pathogenic / VUS / Likely Benign / Benign`. Only render classes actually present among `lollipops` (so a
  window with no benign variants doesn't show a benign swatch). Colour is the cue *plus* the text label, satisfying
  `color-not-only`.
- **Point-feature key:** three small diamond glyphs matching `.sv-pv-pt.active/.palmitoyl/.query` + labels
  ("Active site", "Palmitoylation", "Queried"). Render only the kinds present (`activeSites.length`, etc.).

**Files**
- `app/web/components/workbench/viewer/ProteinView.tsx`
- `app/web/components/workbench/workbench.css` (new `.sv-pv-key`, `.sv-pv-key-swatch`, `.sv-pv-key-diamond` rules)

**Code intent**
- In `ProteinView.tsx`, compute the present class set from `lollipops` (e.g. `const presentClasses = new Set(lollipops.map(p => p.cls))`)
  and the present point-feature kinds from `activeSites`/`palmitoylation` (`query` is always present).
- Inside the existing `<div className="sv-pv-legend">` (`:280-294`), add **above** the "uniform size" note:
  - a `<div className="sv-pv-key">` row mapping over an ordered `['p','lp','vus','lb','b']` filtered by
    `presentClasses`, each as `<span className="sv-pv-key-swatch <cls>" /> {classLabel(cls)}`.
  - a second `<div className="sv-pv-key">` for point features, each as a rotated-square `sv-pv-key-diamond <kind>` +
    label, conditional on presence.
- Reuse `classLabel` (already imported, `:6`) and `ClinClass` type. Do NOT introduce new verdict hex — the swatch
  classes map to `--cls-*-dot` exactly as `.sv-pv-headdot.<cls>` does.

**Token/convention notes.**
- Swatch fill: `.sv-pv-key-swatch.p { background: var(--cls-path-dot) }` … (mirror `3156-3160`). A circular 10px dot to
  match the headdot shape.
- Point-feature diamond: reuse the exact fills `.active → #BA7517`?? **No** — `#BA7517` at `3225` is an off-token raw
  hex (it equals `--warn`). **Flag:** when adding the key, point the swatch (and ideally `.sv-pv-pt.active` itself, if
  Steven wants the token cleanup in-scope) at `var(--warn)`. Palmitoyl swatch uses `var(--base-C)` (already tokenised
  at `3226`). Query swatch uses `var(--ink)`. Keep the 45° `transform: rotate(45deg)` so the legend glyph matches the
  on-backbone glyph shape (shape is a second non-colour cue).
- The legend is `font: 400 11px var(--body)` (inherited from `.sv-pv-legend`) — above the AA floor.

**Acceptance criteria**
- The protein view shows a visible ACMG colour key (swatch + word per class present) and a point-feature key
  (diamond + word per feature present).
- Each entry pairs colour with a text label (no colour-only encoding).
- Only classes/features actually rendered in the current window appear in the key.
- The existing "uniform size" note is preserved.
- No new raw verdict hex; swatch colours resolve to `--cls-*-dot`.

---

### B2 — Conservation track: PhyloP min/max scale chip

**Problem (grounded).** `CodonDetail.tsx:568-580` renders `.sv-cons-bar` divs with `height: v * 26`
(`workbench.css:874-882`, `v` from `data.conservation`, teal at 0.55 opacity). It is a bar chart with **no axis, no
scale, no legend** — the bar heights are quantitatively meaningless to the reader. Each bar's `title` shows
`PhyloP {v}` on hover (`:576`), but nothing visible says the range. ProteinView's `.sv-pv-scale` (`:271-277`) is the
in-tree precedent for an axis chip.

**Decision.** Add a small, always-visible "PhyloP" scale chip at the **left edge** of the conservation track row,
showing the min/max of the encoding (the bars are normalised `v` in roughly 0-1 mapped to 0-26px; the underlying
PhyloP scale is conventionally ~ -14…+6, but the data here is the normalised `v`). Show the chip as `PhyloP` with a
min and max tick label so the height has meaning. Keep the teal bars unchanged.

**Files**
- `app/web/components/workbench/viewer/CodonDetail.tsx`
- `app/web/components/workbench/workbench.css` (new `.sv-cons-scale` rule)

**Code intent**
- In `CodonDetail.tsx` `conservation()` (`:568-580`) — or in the track wrapper where the row is emitted
  (`:688` `row('conservation', 30, conservation())`) — prepend a fixed-position label chip at the row's left edge:
  a `<span className="sv-cons-scale">PhyloP</span>` plus two tick labels (low/high). Because the bars are normalised
  `v`, the honest labels are the *bounds of v in this window* (`min`/`max` over `data.conservation`) OR a fixed
  "low / high" pair if exact PhyloP values aren't carried. **Decision:** show `PhyloP` + `low`→`high` words anchored at
  the track's left, plus keep the per-bar `title` numeric readout. (If `data.conservation` carries true PhyloP scores
  rather than 0-1, show the numeric min/max instead — confirm the field's units when implementing; the `title` already
  prints `v.toFixed(2)`.)
- The chip must not overlap the first bars: render it in the track's left gutter (the track row is full-width `w`;
  reuse the same left-gutter approach as other track labels, or absolutely-position at `left: 0` with a small
  background so bars behind it stay legible).

**Token/convention notes.** Chip text `font: 500 10px var(--body)` (the 10px secondary-label floor from gene-viewer
§3-G), `color: var(--ink-3)`. No new colour. Bars stay `--teal` 0.55.

**Acceptance criteria**
- The conservation track shows a visible "PhyloP" label with a min/max (or low/high) scale, without hovering.
- Bar rendering is unchanged (same heights, same teal).
- The scale chip does not obscure the data bars (sits in the gutter or on a small backing).
- Per-bar hover `title` numeric readout is retained.

---

## C. FullLocus "Full gene" parity

**Problem (grounded).** The CanvasHeader Window/Full-gene toggle (`CanvasHeader.tsx:94-112`, modes at `:31-38`)
presents "Window" and "Full gene" as **peer** view modes. But "Full gene" drops into `FullLocusViewer.tsx`, whose
base cells (`:95-99`) are:
- **monochrome** — `.fl-base--exon/--cds → color: var(--ink)`, `--intron → --ink-4` (`workbench.css:3350-3357`),
  i.e. coloured by *band kind*, never by A/T/C/G. The window grid colours every base by letter
  (`.sv-base.A/.T/.C/.G → var(--base-*)`, `workbench.css:765-768`).
- **non-interactive** — the cell is a bare `<span>` with a `title` only; no `data-idx`, no `onMouseDown`/
  `onContextMenu`, no selection band, no edit. The file header literally says "No selection, edit … or color
  schemes this slice" (`:3-7`).

So a peer toggle promises window-grade parity it does not deliver — a visible downgrade (audit gene-viewer §5.6).

**Decision — ship C-b now, schedule C-a.** Two scoping options:

- **C-b (recommended, ship now — effort S, low risk): re-scope/label the toggle so it stops promising parity.**
  Relabel "Full gene" → **"Full gene (overview)"** (or add a small "overview" sub-tag), and update its `title` to
  "Whole genomic locus — read-only overview; base colour, selection and editing live in Window view." Optionally add a
  one-line caption inside `FullLocusViewer` (near the `fl-header` or `fl-provenance`) stating the same. This is honest,
  cheap, and removes the false-peer impression immediately. It also matches the existing honest-design voice
  (the "uniform size" note, the intron-gap "N bp omitted" separators).

- **C-a (next, larger — effort M, medium risk): bring base colour + selection to FullLocus.**
  - *Base colour (smaller half):* the cell already uppercases `base` (`:98`). Add a letter class so `--base-*` applies:
    in `RowDOM` (`:81-99`), append `'ACGT'.includes(base.toUpperCase()) ? base.toUpperCase() : ''` to the `classes`
    array, and add CSS `.fl-base.A { color: var(--base-A) }` … (mirror `765-768`). Decide precedence vs the band-kind
    colour (`--intron`/`--utr` greying) — likely keep band background tints but let the letter drive text colour for
    exon/cds bases only, so introns stay dimmed. This is a contained, low-risk visual upgrade.
  - *Selection/edit (larger half):* this is real work — FullLocus has no flat-index model wired to the
    `SequenceViewerV2` selection reducer; bases would need `data-idx` (genomic/locus index), `onMouseDown` selection,
    and a path into the edit reducer. **This couples to the viewer's edit-state architecture** and is a meaningfully
    bigger change (its own milestone). Recommend deferring selection/edit and shipping only base colour in C-a if
    Steven wants partial parity sooner.

**Effort estimate.**
- C-b: ~30-45 min (one label + one title + optional caption). Pure copy/markup.
- C-a base-colour-only: ~1-2 h (one class concat + 4 CSS rules + precedence decision + browser check across
  RPE65/ABCA4 introns).
- C-a full selection+edit: **multi-hour structural milestone** — out of scope for "small, independently-shippable";
  recommend a separate spec if pursued.

**Recommendation.** **Ship C-b now** (closes the false-promise honestly for ~zero risk). **Schedule C-a base-colour**
as the next small upgrade once C-b lands. **Defer C-a selection/edit** to its own milestone — do not bundle it here.

**Files**
- C-b: `app/web/components/workbench/CanvasHeader.tsx` (the `VIEWER_MODES` label/title, `:31-38`); optional
  `FullLocusViewer.tsx` caption + `workbench.css` caption rule.
- C-a (base colour): `app/web/components/workbench/viewer/FullLocusViewer.tsx` (`:81-99`),
  `app/web/components/workbench/workbench.css` (`.fl-base.A/T/C/G` rules near `3350`).

**Code intent (C-b)**
- In `CanvasHeader.tsx`, change the `locus` mode entry (`:33-37`): `label: 'Full gene'` → `label: 'Full gene'` with a
  visually-attached "overview" qualifier (either inline in the label, or via a small sub-span), and `title` →
  "Whole genomic locus — read-only overview; base colour, selection and editing are in Window view."
- (Optional) add a `<div className="fl-overview-note">` inside `FullLocusViewer` near `:197` stating the same.

**Code intent (C-a, base colour — if approved)**
- `RowDOM` (`:81-99`): add the letter class to `classes` (exon/cds bases only, to preserve intron/UTR dimming).
- CSS: add `.fl-base--exon.A, .fl-base--cds.A { color: var(--base-A) }` … (or a more specific selector that wins over
  `--ink`). Keep `.fl-base--intron`/`--utr*` as-is.

**Acceptance criteria (C-b)**
- The toggle no longer presents "Full gene" as a flat peer of "Window"; its label/tooltip state it is a read-only
  overview and that colour/selection/edit live in Window view.
- No behaviour change to the viewer.

**Acceptance criteria (C-a base colour, if shipped)**
- Exon/CDS bases in Full-gene view render in `--base-A/T/C/G` exactly as the Window grid; introns/UTRs keep their
  dimmed/tinted treatment.
- No raw hex; colours resolve to `--base-*`.
- Verified on RPE65 + ABCA4 (intron-heavy) that intron dimming is preserved.

---

## D. Single-base Edit affordance

**Problem (grounded).** Editing a single base is **right-click-only**:
- The canvas cell wires `onContextMenu → onBaseContextMenu(i, x, y)` (`CodonDetail.tsx:506-513`), which sets the
  popover anchor (`SequenceViewerV2.tsx:494-496` → `setPopover({idx,x,y})`), opening `EditPopoverV2` (the real
  single-base editor: A/T/C/G substitute, del, insert, consequence preview — `EditPopoverV2.tsx`).
- Left-click just selects (`onBaseMouseDown`, `:500-503`).
- The only *visible* hint is the side-panel single-base card's text: `scratch-sel-hint` "Right-click this base in the
  canvas to edit it…" (`SidePanel.tsx:139-142`). There is **no visible control** — first-timers (and touch users) will
  never discover editing. ui-ux-pro-max `gesture-alternative` (Critical).

The range case already has visible **Delete**/**Replace** buttons (`SidePanel.tsx:164-190`) wired through the viewer's
imperative handle (`delSelection`/`replaceSelection`, `SequenceViewerV2.tsx:265-275`). The single-base case has none.

**Decision.** Add a visible **Edit** entry to the single-base selection summary card (`SidePanel.tsx`, the
`selection.len === 1` branch, `:128-152`), reusing `<IconRename>` (the pencil, `Icon.tsx:88`). Clicking it opens the
existing `EditPopoverV2` anchored to the selected base — i.e. surface the same editor the right-click opens, from a
discoverable button. This requires a **new imperative-handle method** on the viewer (`openEditAt(idx)` /
`editSelection()`) so the side panel can trigger the popover for the currently-selected base. (This is the one
**structural** bit — a single new handle method + one call site.)

**Files**
- `app/web/components/workbench/SidePanel.tsx` (the single-base `SelectionBlock`, `:128-152`)
- `app/web/components/workbench/viewer/SequenceViewerV2.tsx` (imperative handle: add `openEditAt`/`editSelection`)
- `app/web/components/workbench/viewer/viewer-types.ts` (extend the handle interface)
- `app/web/components/workbench/workbench.css` (an `.scratch-sel-btn` icon variant if needed — likely reuse existing)
- (whichever parent wires the side panel to the viewer handle — `WorkbenchShell`/the page — to thread the new prop)

**Code intent**
- **Viewer handle (SequenceViewerV2.tsx):** add a callback that opens the popover for a given flat index. The popover
  is already cursor-anchored via `{idx,x,y}`; for a button-triggered open there's no cursor point, so anchor to the
  selected base's on-screen position. Two clean options:
  1. `editSelection()` — derive `idx` from `selection` (single-base), compute the anchor from the base cell's
     `getBoundingClientRect()` (query `.sv-base[data-idx="<idx>"]`), then `setPopover({idx, x, y})`. Reuses 100% of the
     existing popover. **Preferred** (no popover changes).
  2. `openEditAt(idx)` — same, generalised. Expose via `useImperativeHandle` (the handle is built around
     `:360-374`; add the method to that object and to the `viewer-types` handle type).
- **Side panel (SidePanel.tsx):** in the `selection.len === 1` branch (`:128-152`):
  - Add an **Edit** button to `scratch-sel-actions` (`:143-147`): `<button className="scratch-sel-btn"
    onClick={onEdit}><IconRename size={13} /> Edit base</button>`. Import `IconRename` (already imported in this file,
    `:8`).
  - Soften the `scratch-sel-hint` (`:139-142`) to mention both paths: "Click **Edit** (or right-click this base) to
    substitute / delete / insert. With it selected, press **A/T/C/G** or **⌫**." Keep the keyboard hint.
  - Thread a new `onEdit` prop down through `ScratchpadSection` → `SelectionBlock` (mirroring `onDel`/`onReplace`/
    `onClear`).
- **Wiring:** the parent that holds the viewer `ref` passes `onEdit={() => viewerRef.current?.editSelection()}` into
  the side panel (mirror how `onDelSelection`/`onReplaceSelection` are already threaded).

**Token/convention notes.** Button reuses `.scratch-sel-btn` (existing). Icon is `<IconRename>` at 13px to match the
section icon (`SidePanel.tsx:287` uses `size={14}`; the in-card button uses 13). No new colour. The popover itself is
unchanged (so its consequence-preview + insert behaviour are reused verbatim — no duplicated editor).

**Acceptance criteria**
- With exactly one base selected, the side-panel selection card shows a visible **Edit** button (pencil + label).
- Clicking it opens the same `EditPopoverV2` (substitute/del/insert + consequence preview) that right-click opens,
  anchored at/near the selected base.
- Right-click still works (unchanged); keyboard A/T/C/G/⌫ still works.
- The hint copy names the visible Edit control (no longer "right-click only").
- No second/duplicate editor is introduced — the button reuses the existing popover.

---

## Backend (Codex) handoff — paste-ready

> Only **A4** touches the backend, and only as a *future* gate. The rest is pure frontend.

```
CRISPR Outcomes "Preview" gate (FE A4):
The Outcomes tab (app/web/components/workbench/crispr/OutcomesTab.tsx) will brand itself
"Preview" while it is showing observed-only sample/fallback data, and drop the brand when a
real TIDE/Lindel solve is returned. The FE reads this from outcomeDisclosure(res)
(app/web/lib/workbench/crispr-disclosure.ts). Please define, on the TIDE response contract,
an explicit signal the FE can switch on — e.g. a `source: 'sample' | 'tide' | 'lindel'` or a
`solved: boolean` field — so the FE can decide Preview vs committed without inferring it from
showPredicted/seriesLabel. No FE change to request shape; this is a response-field + disclosure
mapping decision. Everything else in docs/workbench-control-cleanup/spec.md is FE-only.
```

---

## Decision log

- **A1 collapse vs per-option `title`:** chose **collapse to a static chip** over keeping disabled options with
  `title`s. A control that can't change isn't a control; a chip states the fact without faking interactivity.
- **A3 rename vs merge:** chose **rename (Search ≤ / Show ≤)** over merging into one field. They are two operations
  (search budget vs display filter); merging loses over-fetch-then-narrow. Distinct labels + tooltips remove the
  confusion without removing a capability.
- **A4 brand-now / gate-later:** the honest fix (one Preview brand) is FE-cheap and ships now; the *correct* gate needs
  a backend signal, so it's flagged to Codex rather than guessed.
- **B1 extend existing legend:** reuse `.sv-pv-legend` (already present, already carries the honest "uniform size"
  note) rather than invent a new legend container — matches the audit's explicit instruction and the one-vocabulary
  theme.
- **B1 point-feature `#BA7517`:** flagged the raw hex (`workbench.css:3225`) — it equals `--warn`; the legend swatch
  must use `var(--warn)`, and the on-backbone glyph should be re-pointed too if token-cleanup is in scope.
- **B2 honest scale:** the bars are normalised `v`, so the chip shows window min/max (or low/high) and keeps the
  per-bar numeric `title`, rather than printing a fixed PhyloP range the data may not match — confirm `conservation`
  units at implementation.
- **C ship C-b, schedule C-a, defer selection/edit:** relabelling the toggle is the honest, zero-risk win now; base
  colour is a contained next step; wiring FullLocus into the edit reducer is a real milestone and must not be smuggled
  into a "small change" batch.
- **D reuse the popover via a handle method:** rather than build a second single-base editor in the side panel,
  surface the existing `EditPopoverV2` from a visible button through one new imperative-handle method. One editor, two
  entry points (button + right-click).

## Rejected alternatives

- **A1 — keep the dropdown, just hide disabled options.** Rejected: still a dropdown with one option (dead control),
  and the user loses the explicit "more coming" signal a chip+note gives.
- **A3 — merge to a single mismatch number.** Rejected: conflates the search radius with the view filter; you can no
  longer fetch wide then narrow the table without re-running the search.
- **A4 — delete the Outcomes tab until TIDE is real.** Rejected: the scaffold + IndelSpectrum + file flow are useful
  and honest *as a preview*; deleting loses built work. "Preview" brand is the lower-cost, reversible choice.
- **B1 — size- or pattern-encode lollipops for class.** Rejected: size is deliberately uniform (ClinVar is curated, not
  frequency — `ProteinView.tsx:14-23` invariant). A legend adds the second cue without breaking that invariant.
- **C-a full parity now (selection+edit in FullLocus).** Rejected for this batch: couples to the edit-state reducer; not
  "small/independently-shippable." Belongs in its own milestone.
- **D — add an "Edit" button that opens a NEW inline editor in the side panel.** Rejected: duplicates `EditPopoverV2`'s
  substitute/del/insert + consequence-preview logic. Reusing the popover keeps one source of truth.

---

**Doc path:** `D:\eamos\docs\workbench-control-cleanup\spec.md`
