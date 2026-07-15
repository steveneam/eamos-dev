# /report — Context sections + Library rail + Ribbon + Section-nav design audit

> **2026-07-15 structure update:** `AssociatedConditions.tsx` and
> `GeneDiseaseBlock.tsx` were confirmed unimported after
> `DiseaseValidityDashboard` took ownership of Section 5, then retired. Findings
> naming those files are historical and must not be treated as live defects.

> Scope: §4–§8 context blocks (gene/locus, disease/conditions, publications, trials, expert panel, curated variants, limitations, provenance), the `VariantLibraryRail` (`LibrarySection` + `RelatedVariants` + `ReportSectionNav`), the `StickyVariantRibbon`, and cross-surface coherence with `/workbench`'s `SidePanel`.
> Grounded in `DESIGN.md`, `app/web/app/globals.css`, `lib/classification.ts`, `components/layout/work-rail.css`, `components/library/library.css`. Skills: **frontend-design** + **ui-ux-pro-max** (searches cited inline).
> _Persisted by main agent — scout's direct `.md` write was harness-blocked._

## 1 · Snapshot

The context sections are well-architected and largely on-token — the `--report-subpanel-*` inset geometry, `eamos-kicker` field-labels, `eamos-mock` markers, the classification ramp via `lib/classification.ts`, and the publication-scope toggle all read as one disciplined system, and the timeline SVG is genuinely good (continuous zero-filled axis, accessible `aria-label`, mono tick figures). The **rail + ribbon + section-nav scroll-spy** are the strongest part of the surface: the shared `<WorkRail>` "airy icon-led" grammar is real, the ribbon's `--rail-live-w` offset resolves correctly (it lives inside `.work-output` so the custom property inherits), and the nav anchors match the DOM order exactly. **Cross-surface verdict: partial coherence — the `1.75` Icon family and token vocabulary are genuinely shared, but `/workbench`'s `SidePanel` re-implements the rail-section grammar as a parallel `.side-section` CSS twin (with a hand-inlined chevron) instead of consuming the shared `<WorkRailSection>` primitive, so the two surfaces are visually-mirrored-but-structurally-forked.** The defects that matter are a cluster of **`--warn`-on-`--warn-tint` contrast failures** (the design system's own comment says `--warn-text` is the AA-safe pair), an **invisible `<mark>` highlight** (teal-tint on teal-tint) in publication snippets, the **`backdrop-blur` on `PublicationModal`** (DESIGN explicitly bans blur on overlays), a **silently-dropped colour** from a trailing-space token bug, **two ClinGen evidence tiers that render no visual fill**, and a **dead section-nav link** when population data is absent.

## 2 · Findings

### P0 — bug / invariant violation / a11y / mock-looks-real

**[P0] Publication snippet `<mark>` highlight is invisible (teal-tint on teal-tint)** · `PubMedSection.tsx:377` + `:403-405`
The `SnippetBlock` container is `background: var(--teal-tint)` (line 377), and `highlightTerms` wraps matched terms in a `<mark>` whose background is *also* `var(--teal-tint)` (line 405). The matched-term highlight — the entire point of surfacing snippets — has **zero contrast against its own container**. The text colour shifts to `--teal-deep`, but with no background delta the "highlight" reads as plain coloured text at best, invisible at worst. **Fix:** give the `<mark>` a distinct fill — `background: var(--warn-tint)` + `color: var(--warn-text)` (amber-on-cream is the established "attention" pair and contrasts cleanly against the teal-tint card), or keep teal text but set `background: color-mix(in oklab, var(--teal) 18%, transparent)`. **Why:** a highlight that can't be seen is a silent feature failure; `ui-ux-pro-max` color-contrast (4.5:1) + `color-not-only` both apply.

**[P0] `--warn` text on `--warn-tint` fails AA on the criterion/freshness chips** · `ExpertPanelSection.tsx:30` (`CRITERION_STATE_TINT.conflicting` `ink: 'var(--warn)'`) · `ExpertPanelSection.tsx:59` (`FreshnessChip` "Stale", `color: 'var(--warn)'`)
`--warn` (`#BA7517`) on `--warn-tint` (`#FAEEDA`) is ≈3.4:1 — below AA 4.5:1 for the 10–11.5px chip text. `globals.css:75` documents the correct pair explicitly: *"`--warn-text: #633806;` — dark-amber text on `--warn-tint` (AA on the tint)."* `ProvenanceNote.tsx:47` already uses `--warn-text` correctly; these two chips use the wrong token. **Fix:** swap `var(--warn)` → `var(--warn-text)` in both the `conflicting` tint and the `FreshnessChip` "Stale" colour. The `§` override glyph (`:106,205`) at `--teal-deep` is fine. **Why:** invariant — the token table reserves `--warn-text` for exactly this on-tint case; AA on a clinical criterion chip is non-negotiable.

**[P0] `PublicationModal` backdrop uses `backdrop-blur-sm` — DESIGN bans blur on overlays** · `PublicationModal.tsx:189`
The dialog backdrop className includes `backdrop-blur-sm`. DESIGN.md "Banned hover affordances" (2026-05-26, user-mandated): *"No `backdrop-filter: blur(...)` on any sticky/overlay element. Repaints on every keystroke (mobile typing lag); use an opaque token instead."* The report's other overlays (`lib-folder-menu` popover, `--elev-3`) correctly avoid it. **Fix:** delete `backdrop-blur-sm`; the existing scrim `rgba(11, 26, 43, 0.45)` already isolates the foreground (within `ui-ux-pro-max`'s 40–60% scrim guidance). **Why:** named, durable design-system ban; the blur is a perf cost the system already paid to remove elsewhere.

**[P0] `color: 'var(--ink) '` (trailing space) silently drops the colour** · `GeneDiseaseBlock.tsx:263`
The ClinGen-dosage HI value is styled `color: 'var(--ink) '` — the trailing space makes the value invalid, so the browser drops the declaration and the HI score inherits the muted `--ink-2` parent instead of the intended `--ink`. The TS sibling (`:267`) correctly uses `'var(--ink)'`, so HI and TS render at *different* weights for no reason. **Fix:** `color: 'var(--ink)'` (strip the space). **Why:** real rendering bug producing inconsistent emphasis between two adjacent values on one row.

**[P0] `population_frequency` section-nav item can be a dead link → empty scroll target** · `ReportSectionNav.tsx:16` (anchor listed unconditionally) · `ReportClient.tsx:826-845` (anchor `<div>` unconditional, but the `<Card>` is `{populationSection && …}`)
The anchor div always renders, but the visible Card only renders when `populationSection` exists. When population data is absent, clicking "Population frequency" scrolls to a **0-height empty anchor** with nothing below it, and the IntersectionObserver observes a zero-height target that can never become active. The file's own comment acknowledges the anchor "may be an empty anchor" but the nav offers it as a normal target regardless. **Fix (small, token-free):** in `ReportSectionNav`, filter the rendered items to anchors with non-zero height at observe-time (`el.getBoundingClientRect().height > 0`, or check the anchor's `nextElementSibling`), so an empty section drops out. **Why:** `ui-ux-pro-max` `empty-nav-state` — "when a nav destination is unavailable, explain why instead of silently hiding it"; here it neither explains nor scrolls usefully.

### P1 — inconsistency / hierarchy / cross-surface drift

**[P1] CROSS-SURFACE: `/workbench` SidePanel forks the rail-section grammar instead of sharing it** · `SidePanel.tsx:57-99` (`CollapsibleSection` + `.side-section*`) vs `WorkRail.tsx:75-95` (`WorkRailSection` + `.wr-section*`)
The two surfaces do **not** share one rail primitive. `/report` composes the shared `<WorkRailSection>` (RelatedVariants, ReportSectionNav both import it); `/workbench`'s `SidePanel` hand-rolls an identical-looking `CollapsibleSection` over a parallel `.side-section` class set in `workbench.css`, with the chevron inlined as a raw `<svg … strokeWidth={2.4}>` (`:90-94`) duplicating the family's `IconChevron`. The leading glyphs *are* shared (both pull `IconScope`/`IconGene`/etc. from the one `Icon.tsx` 1.75 family — good), so this is structural drift, not visual: any future change to the rail-section head metrics, focus ring, or chevron motion must be made twice and can silently diverge. **Fix (FLAGGED — see §3):** converge `SidePanel`'s `CollapsibleSection` onto `<WorkRailSection>` (or alias `.side-section` to the `.wr-section` rules so there is one source of truth), and replace the inlined chevron with `<IconChevron size={12} />`. **Why:** the stated goal is "ONE rail grammar, ONE icon family"; a forked twin is the exact drift this audit exists to catch.

**[P1] ClinGen evidence-level bars render no fill for `strong` and `limited`** · `AssociatedConditions.tsx:60-63` (emits `ev-bars def|strong|mod|lim`) · `globals.css:730-731` (only `.ev-bars.def` and `.ev-bars.mod` get fills)
`AssociatedConditions` maps four evidence levels onto `.ev-bars`, but `globals.css` only styles `.ev-bars.def` (3 teal) and `.ev-bars.mod` (2 teal). **There is no `.ev-bars.strong` or `.ev-bars.lim` rule**, so a "Strong" and a "Limited" condition render *identical all-grey bars* — the bar stops encoding the level for two of four tiers, and Strong (which outranks Moderate) shows weaker than Moderate. **Fix:** add `.ev-bars.strong span:nth-child(1),(2),(3){background:var(--teal)}` and `.ev-bars.lim span:nth-child(1){background:var(--teal)}` so fill is monotonic with confidence. The text label keeps it from being color-only, but the bar is currently meaningless for half the tiers. **Why:** a data glyph that doesn't encode the data is worse than none.

**[P1] `GeneDiseaseBlock` GenCC pill is mock but borrows the live ClinGen tier's colour + count** · `GeneDiseaseBlock.tsx:155-208`
The GenCC pill is `.eamos-mock`-tagged (good) but (a) title-cases the *live* ClinGen validity for its label, (b) hard-codes `genccSubmitters = 5`, and (c) paints itself with the **same `tone` border/ink as the live ClinGen pill** beside it. Two same-colour pills, one live, one fabricated — colour reads as two agreeing sources where there is one. **Fix:** make the GenCC pill quieter than its live sibling — neutral `--line` border, `--ink-3` ink — so the mock reads provisional, not confirming; consider `~5`/`est.` on the count. **Why:** `.eamos-mock` discipline — gated mock must not borrow the visual authority of the live datum next to it.

**[P1] Trial status `ACTIVE_NOT_RECRUITING` uses raw `--err` as border (off the tint+soft-border grammar)** · `TrialsSection.tsx:193`
Every other status/criterion chip uses tint + *soft* border (`RECRUITING`→`--teal-bdr`, `NOT_YET_RECRUITING`→`--warn-bdr`). `ACTIVE_NOT_RECRUITING` uses `border: 'var(--err)'` — full-saturation red — giving one chip a hard hairline heavier than its peers. There's no `--err-bdr` token; the established soft-red is `--cls-path-bdr` (`#ffbfb7`). **Fix:** `border: 'var(--cls-path-bdr)'` (or add a named `--err-bdr` if a system-wide non-classification red border is wanted — justify the token). Also worth a glance: "active, not recruiting" is a *neutral/ongoing* state — red may overstate it (see §3). **Why:** chip-grammar consistency + visual-weight parity across a row of peers.

**[P1] Section-nav active state can blank mid-section on scroll (observer keys off 1px markers)** · `ReportSectionNav.tsx:31-40`
The observer sets `active` to the top-most intersecting anchor in a `-80px / -70%` band, but the anchors are zero-height `<div>` markers, not the sections. Once a long section's marker scrolls past the top band, **no** active item shows until the next marker enters — the highlight drops mid-section. **Fix:** observe the section content wrappers (or give anchors section-spanning height), or widen the bottom band (`-70%`→`-55%`) and retain last-known active when nothing intersects. **Why:** `ui-ux-pro-max` Navigation `Active State` — current location must stay continuously indicated.

**[P1] `MolecularContextBlock` re-implements `.eamos-kicker` inline instead of using the class** · `MolecularContextBlock.tsx:108-119` vs `globals.css:667-672`
The `ChipRow` label is `fontSize:10.5, fontWeight:700, uppercase, letterSpacing:'0.08em', color:'var(--ink-4)'` — byte-for-byte `.eamos-kicker`, inline. The block's own header (`:163`) correctly uses the class. Two kicker treatments that drift the moment the canonical kicker changes. **Fix:** apply `className="eamos-kicker"` to the `ChipRow` label, keep only the `flex` layout style. **Why:** kicker is a canonical field-label; inline copies defeat the token.

**[P1] `PublicationModal` heading uses Spectral at `font-semibold` (600)** · `PublicationModal.tsx:216-224`
The `<h2>` is `fontFamily: var(--display)` (Spectral) + `font-semibold` (600). DESIGN: *"the serif reads authoritative at low weight (300–400 large), so bold is rarely needed"*; every other card title is Spectral 400 (or sans 600). Spectral 600 is off the type-scale and reads slightly clotted at 18px. **Fix:** drop `font-semibold` (Spectral 400, matching `Card` titles), or add rank via size not weight. **Why:** typographic invariant — Spectral is heading-role at low weight.

### P2 — polish

**[P2] `RelatedVariants` "1,043 views · added 5 Jun 2026" is hard-coded mock on every card** · `RelatedVariants.tsx:94`
Every card shows the *same* literal metric. It has a `REL_MOCK_TIP` title + dotted help cursor, but unlike the `.eamos-mock` pill it reads as real-but-broken (all variants can't have 1,043 views). **Fix:** either add a `.eamos-mock` marker to the lane, or suppress the views/date line until wired and keep only the live classification + axis squares. **Why:** mock-looks-real tell at polish tier.

**[P2] `RelatedVariants` (and Pub/Trials) inject per-render `<style>` blocks instead of using the stylesheet** · `RelatedVariants.tsx:175-206` (`.rel-card*`); also `PubMedSection.tsx` `pubStyles`, `TrialsSection.tsx` `.trial-row-link`
Rail/section styles ship as inline `<style>` nodes while siblings live in `library.css`. **Fix:** move `.rel-card*` into `library.css` (`§4 Related variants lanes`' neighbour) and the article/trial hover rules into the report stylesheet. **Why:** one stylesheet per surface; avoids duplicate `<style>` nodes. Behaviour-neutral.

**[P2] Provenance / source pills are inconsistent across context blocks** · `MolecularContextBlock.tsx:192-201` · `GeneDiseaseBlock.tsx:240-255` · `ExpertPanelSection.tsx:222-233` · `PubMedSection.tsx:330-348`
Source attribution appears in ≥4 shapes (teal inline-underline links, an `--ink-4` provenance footer, uppercase pill chips). Each is fine, but the report's most trust-bearing element has no single signature. **Fix (FLAGGED if layout changes — §3):** factor a shared `<SourcePill>`/`<ProvenanceLink>` (teal-deep, `text-underline-offset:3px`, `↗`) + one `<ProvenanceFooter>` for version/fetched-at, adopt across §4–§8. **Why:** multi-source provenance is a core trust surface.

**[P2] `PublicationTimelineChart` gives no visual cue the gene series is mock** · `PublicationTimelineChart.tsx:135-136`
On "gene" scope the synthesised series draws in the *same* `--teal` line+area as the live variant series; only the disclosure `Mock` tag signals it. **Fix:** render the gene-scope (mock) line dashed (`stroke-dasharray: 4 3`) or at reduced `stroke-opacity`. `ui-ux-pro-max` chart guidance: differentiate series by line style, not colour alone. **Why:** mock-looks-real at chart level; cheap token-free signal.

**[P2] `ReportSectionNav` `aria-current="true"` should be `aria-current="location"`** · `ReportSectionNav.tsx:51`
For an in-page index, the correct token is `aria-current="location"` (or `"page"`). **Fix:** `aria-current={active === a.id ? 'location' : undefined}` + update the `library.css:519` selector to `[aria-current]`. **Why:** a11y precision for the section landmark.

## 3 · 🟡 FLAGGED — needs Steven's OK

1. **Converge `/workbench` SidePanel onto shared `<WorkRailSection>` (P1 cross-surface).** Merging the `.side-section` twin into `.wr-section` touches shipped workbench chrome (must stay pixel-identical). Recommend doing it — it's the single fix that makes "one rail grammar" true — but needs go-ahead.
2. **Introduce shared `<SourcePill>` / `<ProvenanceFooter>` primitives across §4–§8 (P2).** Small IA standardisation, but edits multiple shipped sections' provenance rows (persistent element).
3. **Trial status semantics: should `ACTIVE_NOT_RECRUITING` be red?** Recolouring a status tier (red→neutral) is a data-meaning decision, not pure polish — confirm intended semantics before changing tone, not just the border token.
4. **Empty-section handling in `ReportSectionNav` (P0 dead link).** Fix is safe/token-free, but the *policy* — hide unavailable section vs. show disabled-with-reason — is a nav decision; `ui-ux-pro-max` `empty-nav-state` prefers "explain why" over "silently hide". Confirm which.

## 4 · Quick wins (safe, token-only, shippable now)

| # | File:line | Change |
| - | --------- | ------ |
| 1 | `ExpertPanelSection.tsx:30` | `conflicting.ink`: `var(--warn)` → `var(--warn-text)` (AA) |
| 2 | `ExpertPanelSection.tsx:59` | `FreshnessChip` "Stale": `var(--warn)` → `var(--warn-text)` (AA) |
| 3 | `GeneDiseaseBlock.tsx:263` | `color: 'var(--ink) '` → `color: 'var(--ink)'` (strip trailing space) |
| 4 | `PublicationModal.tsx:189` | remove `backdrop-blur-sm` from backdrop className (DESIGN ban) |
| 5 | `PublicationModal.tsx:216` | drop `font-semibold` on the Spectral `<h2>` |
| 6 | `PubMedSection.tsx:405` | `<mark>` bg `var(--teal-tint)` → `var(--warn-tint)` + `color: var(--warn-text)` |
| 7 | `TrialsSection.tsx:193` | `ACTIVE_NOT_RECRUITING` border `var(--err)` → `var(--cls-path-bdr)` |
| 8 | `globals.css:730-731` | add `.ev-bars.strong` (3 teal) + `.ev-bars.lim` (1 teal) for monotonic fill |
| 9 | `MolecularContextBlock.tsx:108-119` | replace inline kicker rules with `className="eamos-kicker"` |
| 10 | `PublicationTimelineChart.tsx:136` | dash/dim the gene-scope (mock) line when `isGene && geneMock` |

### Appendix — already right (don't re-touch)

- `--rail-live-w` ribbon offset **resolves correctly** — the ribbon is a DOM descendant of `.work-output` inside `.work-shell`; CSS custom properties inherit through the tree irrespective of `position: fixed`, so `left: var(--rail-live-w, 0px)` tracks collapse/drawer state.
- Ribbon z-index layering correct: nav `z-50` > inline rail `z-45` > ribbon `z-40` (rail owns left edge, ribbon content centred) — per `work-rail.css:50-52`. Rail toggle stays clickable when the ribbon pins.
- Ribbon variant identity honours the invariant: gene = Inter 600, HGVS = Inter tabular-nums (`StickyVariantRibbon.tsx:137-166`); reduced-motion is reactive via `useSyncExternalStore`.
- `PublicationModal` focus-trap, ESC, scroll-lock, return-focus, `?pub=PMID:` URL round-trip all correct (`:78-171`).
- Section-nav anchor ids match DOM order one-to-one (`ReportClient.tsx:720/781/826/854/907/951/978/1002` ↔ `ReportSectionNav.tsx:14-23`).
- The 1.75 monochrome `Icon.tsx` family **is** shared across `/report` rail and `/workbench` SidePanel glyphs — only the section-*container* grammar is forked (P1 cross-surface).
- Classification colour logic flows through `lib/classification.ts` everywhere it should — no inline tier hex in the audited context files.
