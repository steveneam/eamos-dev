# Workbench + Report v3 design sweep — orchestration plan

Synthesis of the 4 scout reports (frontend-design + ui-ux-pro-max):
`workbench-chrome.md`, `workbench-tools.md`, `report-evidence.md`, `report-context-rail.md`.
Claude = orchestrator + implementor. Rule: durable/structural/visual changes (verdict-colour,
persistent-element, card geometry, primitive refactors) need **Steven's OK before shipping**
([[feedback_subagent_recommendations_not_authorization]]). Everything below is FE-only, `app/web`, token-first.

## The cross-surface picture

Both product surfaces are **structurally strong and mostly token-disciplined** — the foundations
(`lib/classification.ts` single ramp, `--base-*` palette, `--report-subpanel-*`, `.eamos-mock`,
the 1.75 `Icon` family, the airy WorkRail grammar) are real and largely respected. The drift is in
the **details**: a handful of a11y/contrast bugs, several raw-hex callsites that bypass existing
tokens, a couple of "mock-looks-real" honesty gaps, and — the deeper theme — **vocabulary
fragmentation**: the same idea (a verdict chip, a "score-on-a-scale" bar, a rail section, a summary
stat row) is drawn 3–5 different ways across components that sit side-by-side.

Four findings recur in **2+ scouts** (fix once, benefits everywhere):
- **`tabular-nums` is set in ~3 places only** (all Align). Every CRISPR/Primer numeric column + several
  report numerics render proportional → columns don't line up. (workbench-tools C1, workbench-chrome P2, report-evidence implicit.)
- **Raw splice/info-indigo hex `#3b4877`/`#e8eaf2`** repeated across viewer + CRISPR + Align — should
  re-point to the existing `--info-*` family. (workbench-chrome P0, workbench-tools P2/C4.)
- **`--warn` used where `--warn-text` is the AA-safe on-tint token** — the system's own comment says so.
  (report-context-rail P0, workbench-tools C4.)
- **Verdict/classification colour bypassed by raw hex** — the workbench ClinVar/lollipop ramp hardcodes
  off-ACMG colours; report badges drift their own dialects. (workbench-chrome P0, report-evidence P1.)

## 🟢 SHIPPING THIS PASS — safe quick wins (bug / a11y / token / mock-honesty, no durable restructure)

Token-only, correctness, accessibility, and mock-honesty fixes that trace directly to a token/value and
change no durable structure or clinical-verdict colour. Gates: app/web tsc 0-err + eslint baseline; browser-verify.

**Report — context/rail**
1. `ExpertPanelSection.tsx:30,59` — `--warn` → `--warn-text` (AA contrast on criterion + freshness chips).
2. `GeneDiseaseBlock.tsx:263` — `var(--ink) ` → `var(--ink)` (trailing-space drops the declaration; HI/TS mismatch).
3. `PublicationModal.tsx:189` — remove `backdrop-blur-sm` (DESIGN ban on overlay blur).
4. `PublicationModal.tsx:216` — drop `font-semibold` on the Spectral `<h2>` (serif = low weight).
5. `PubMedSection.tsx:405` — `<mark>` teal-on-teal (invisible) → `--warn-tint`/`--warn-text` (visible highlight).
6. `globals.css` `.ev-bars` — add `.strong` (3 fill) + `.lim` (1 fill) so all 4 ClinGen tiers encode level.
7. `MolecularContextBlock.tsx:108-119` — inline kicker → `className="eamos-kicker"`.
8. `PublicationTimelineChart.tsx` — dash/dim the mock gene-scope series (mock-honesty, color-not-only).
9. `ReportSectionNav.tsx:51` — `aria-current="true"` → `"location"`.
10. `TrialsSection.tsx:193` — `ACTIVE_NOT_RECRUITING` full-sat `--err` border → soft `--cls-path-bdr` (chip-grammar parity; **keeps red — the red-vs-neutral *semantics* question stays FLAGGED**).

**Report — evidence/cards**
11. `StackedCountBar.tsx:111` — `#fff` numerals → per-tier `--cls-*-text` map (AA on light VUS/LB dots).
12. `PopulationFrequencySection.tsx:1479` — raw black `boxShadow` → `var(--elev-3)`.
13. `PopulationFrequencySection.tsx:390` — raw hex gradient → flat `var(--bg-soft)`.
14. `CallCardsGrid.tsx:253` + `PopulationFrequencySection.tsx:334` — `borderRadius:7` → `var(--r-sm)`.
15. `VariantHeader.tsx:182-187` — wrap mock `1,204`/`5 Jun 2026` in `.eamos-mock` (mock-honesty on the hero).
16. `CalibratedInSilicoTable.tsx:319-327` — caption 9px→10px, `--ink-5`→`--ink-4` (readable floor).
17. `AfThermometer.tsx:300-346` — when `mock`, de-emphasise value text + pin to `--ink-4` (mock-honesty).

**Workbench — chrome**
18. `workbench.css:1115` — `.cs.stop` `#1a1a1a` → `var(--ink)` + `color:var(--bg)` (pure-black ban).
19. `ToolIcon.tsx:8` — `strokeWidth 2 → 1.75` (join the one-pen family; teal-active stays per FLAG).
20. tabular-nums on `.kv-row .v`, `.sv-vnav-count`, `.sv-hist-count`, `.side-exon-row .ex-*`.
21. `workbench.css:570,1621` — drop dead `var(--bg-soft2, …)` fallback.
22. raw `.15s/.12s/.2s` viewer transitions → `--dur-1`/`--dur-2` + easings (incl. `.viewer` duration half).

**Workbench — tools**
23. tabular-nums sweep: `.tool-table td.num`, `.cs-v`, `.primer-strand-m`, `.primer-product`, `.primer-dtm`, `.primer-kv dd`.
24. `.g-pam` table PAM → ribbon parity (`--warn-bdr` bg + `--warn-text` + inset `--warn` ring) — **restores documented intent** (the pale tint was the regression that was explicitly walked back).
25. `.crispr-summary` grid → `repeat(auto-fit, minmax(150px,1fr))` (kills the orphan 7th cell).
26. `.g-nt.mm` mismatch underline → inset ring (`inset 0 0 0 1.5px var(--ink-3)`) — matches "ringed mismatch" intent.
27. `.primer-badge` borders `#cbe3d8`/`#e8c6c6` → `color-mix(--teal)` / `--cls-path-bdr`.
28. `#633806` literals → `var(--warn-text)`.
29. `.seq-hl-silent` + `.ic-bar.predicted` indigo → `--info-*`.
30. `.aln-band` raw rgba → `color-mix` of `--err`/`--warn`/`--teal`.
31. `.chromatogram-het` — add 1px dashed top edge (a11y non-colour cue; the het-purple token-naming half stays FLAGGED).

## 🟡 FLAGGED — needs Steven's OK before I implement (durable / structural / verdict-colour)

Grouped for a decision pass:

**A. Verdict-colour correctness on persistent surfaces**
- Route the workbench **ClinVar / lollipop / scratch-cv ramp** through `--cls-*` (workbench-chrome P0). Token-only,
  but it *recolours clinical verdicts* (LP amber→orange, VUS grey→yellow, LB sage→lime) to match the 2026-05-26
  ACMG mandate. High-confidence correctness fix; recolouring a verdict still wants a yes.

**B. One evidence vocabulary (the deep theme)**
- Unified **`<EvidenceChip>`** primitive re-routing CallCards / MAVE / LoF / Eamos-ACMG / Tier tags to the
  `ClassificationBadge` spec (report-evidence P1: 5 dialects).
- Converge the **three "score-on-a-scale" visualisations** (§1 MAVE ladder / §2 EvidenceBar / §3 thermometer)
  onto one bullet-bar-with-pin + a shared `<ScorePin>` (report-evidence P1).
- One **`<InfoHint>`** affordance (inline-SVG "i", two variants) replacing the 2 today (report-evidence P1).

**C. Report card geometry + type**
- Call-card radius 10/pad 15-16/**Spectral 600** vs §-Card 14/16-24/Spectral 400 — align or tokenise the tiers (report-evidence P1).
- `AcmgGrid` met-cell **strength colouring** (Very-Strong…Supporting) instead of one flat red/green (report-evidence P1; shared component, hits §1 + auto-classifier).
- De-duplicate gnomAD **LOEUF/pLI** between `MolecularContextBlock` and `AfThermometer` (report-evidence P1; IA).
- `Card.tsx` **verdict accent** — render the documented 3px left rule, or remove the dead prop (report-evidence P0; durable-add vs dead-code-removal).

**D. Workbench chrome structure**
- Adopt the **airy icon-led grammar on the canvas `SectionHeader`** (workbench-chrome P0) — closes the rail↔canvas seam; persistent header redesign.
- Define + adopt a **workbench z-index scale** (workbench-chrome P1) — FAB-under-nav, popover-above-rail.
- **Persistent zoom handle** (mirror `.chromatogram-toggle`) instead of hover-only (workbench-chrome P1).
- Viewer **error-recovery affordance + skeleton load** (workbench-chrome P1).
- Single-base **"Edit" affordance** (today right-click only) (workbench-chrome P1).
- Tool-switcher active icon **teal vs monochrome** (workbench-chrome P0 sub-point).
- Swap the **8 inline chrome SVGs** for the `Icon.tsx` family (needs new IconSearch/Undo/Redo/Tracks) — safe but multi-file; better as its own focused pass.

**E. Workbench cross-surface + tool consistency**
- Converge `/workbench` **SidePanel onto the shared `<WorkRailSection>`** (report-context-rail P1) — makes "one rail grammar" actually true; touches shipped chrome (must stay pixel-identical).
- Unify the **summary-stat primitive** (CRISPR `.cs-cell` ↔ Align `.align-metric`) and the **result-card shape** across the 3 tools (workbench-tools C5).
- **Sticky `thead`** on `.tool-table` (workbench-tools P1) — low-risk, persistent; recommend yes.
- **Custom orientation listbox** to render the glyph via Icon.tsx (workbench-tools P2) — replaces a native control.
- Shared **`<SourcePill>`/`<ProvenanceFooter>`** across report §4–§8 (report-context-rail P2).
- **Trial-status semantics**: should `ACTIVE_NOT_RECRUITING` be red at all? (report-context-rail §3) — data-meaning call.

## Sequencing
Ship 🟢 → gate → browser-verify → present 🟡 A–E to Steven. The 🟡 work then proceeds in approval order
(A verdict-correctness first, then B vocabulary as the highest-leverage consistency win), each its own gated pass.
