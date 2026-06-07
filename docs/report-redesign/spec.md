# Eamos `/report` v3 redesign — SPEC (confirmed)

> Status: requirements confirmed with Steven 2026-06-07. Build = **one pass**
> after `design.md` (UI/UX) + `plan.md` (implementation) land (subagent-assisted).
> FE-only where possible; **backend-gated metrics ship mock-first WITH a visible
> "needs live data" label** — never silent fake numbers.
> Reference IA: `…/EAMOS Web Tool/Wiki/variant-report-layout.canvas` (8-section
> tool→metric→ACMG map). Design system: `DESIGN.md` (warm-paper, teal, Spectral
> display / Inter body / JetBrains Mono for HGVS+scores).

## Locked decisions
1. **Remove the 12-tile `MatrixOverture`** entirely. The 4 cards are the only top display.
2. **Mock-first** for unsourced metrics, but **every placeholder carries an explicit, tasteful marker** that it needs Codex/backend wiring.
3. **Hero stays SLIM** + gains an **expandable details disclosure** (full genomic coords, all HGVS, transcript/MANE, build, rsID, consequence).
4. **One-pass build** (not staged) after design + plan.

## Top area (hero)
- Slim bar: `GENE c.cdna` (DNA primary) · `p.consequence` (muted) · classification badge · **view-count + last-updated** (mock+label) · **Save** (replaces the meaningless "Follow"; wires to the existing variant-library save) · Export · Share.
- **Expandable "details"** disclosure: full genomic coordinates (chr:pos 1-based + VCF `1-68444869-T-C`), all HGVS (c./p./g.), MANE transcript, genome build, rsID, consequence.
- Validate in design: a thin **4-segment colour strip** in the hero previewing the 4 cards.

## 4 cards (`CallCardsGrid`) — order L→R: **Computational · Clinical · Population · Lab & Functional**
- **All four fully coloured** by their own verdict state (today only `lab_functional` uses `fnTheme`; extend to all four). Colour source per axis:
  - **Computational** — calibrated damaging↔benign ramp.
  - **Clinical** — ACMG/ClinGen classification ramp (P/LP/VUS/LB/B).
  - **Population** — AF-class ramp (BA1/BS1 → benign green; PM2 → path-leaning; intermediate → yellow).
  - **Lab & Functional** — existing functional-state ramp.
- Keep 3-layer Dashboard Interaction Language (verdict+number → headline → `<details>` audit).
- Card order may be backend-driven (`report_call_cards`); if so, re-sort in FE.

## 8 sections (reordered — today is Population→In-silico→Clinical…)
1. **Clinical** — ClinGen VCEP (classification + criteria chips + the VCEP's **written rationale inline**) → ClinVar (classification + review status + **submitter interpretation text inline**) → 28-criteria ACMG overview. Bottom of section: expandable **"Eamos 28 ACMG criteria"** (InterVar-style per-criterion met/unmet + rationale).
2. **In-silico** — keep current calibrated table; gated engines (REVEL/CADD/PrimateAI/SpliceAI) may be absent/blurred on Free.
3. **Population** — top: **Franklin-style AF classification** (path/benign chip + AF "thermometer" vs BA1/BS1/PM2 thresholds) + **genomic constraint Z-score** (`mis_z`/`lof_z`) + LOEUF/pLI. Below: world map (existing `PopulationFrequencySection` tabs).
4. **Gene & locus** (`MolecularContextBlock`).
5. **Disease & curated variants** (`DiseaseSection` + `GeneDiseaseBlock`).
6. **Publications** — variant-toggle link **Google Scholar → PubMed**. Pub graph reflects **both variant and gene** (per-year counts).
7. **Therapies & clinical trials** (`TrialsSection` — keep).
8. **AI evidence summary** — RAG/LLM summary of the **whole report** (explains; never decides the verdict).

## Related variants (rail) — 2-line, YouTube-style cards
- Line 1: variant (`GENE c.cdna`) + **New / Updated** pill.
- Line 2: mini **4-colour chip row** (mirrors the 4 main cards) · **views** · **last-updated**.
- mock+label for views / updated / per-variant states until Codex.

## Intuitiveness + hover tooltips (cross-cutting)
- Apply **ui-ux-pro-max + frontend-design** throughout: the redesign must be **as intuitive as possible** — clear affordances, predictable interactions, obvious primary actions, no unexplained jargon.
- **Hover info pop-outs (`title` + `aria-label`) on every toggle, button, and jargon label that needs one** — same pass as the Workbench. Targets include: the 4 card verdict states, AF-class chips (BA1/BS1/PM2), constraint Z-score / LOEUF / pLI, ACMG criterion chips, ClinGen/ClinVar review-status, the variant/gene publication toggle, the Save/Export/Share cluster, the New/Updated pills, the "needs live data" markers, and any abbreviation (HGVS, MANE, VCEP, etc.).
- Tooltips explain **what the control does** or **what the term means** (plain language), never just restate the label. Keyboard-reachable; not hover-only for critical info.

## Small fixes
- `PublicationsCallout.tsx` (~L149-161): variant-scope **"Google Scholar" → "PubMed"**.
- Hero **"Follow" → "Save"** (library save).

## FE-now vs Codex backend
- **FE now:** remove matrix, reorder sections, colour all 4 cards, slim hero + details disclosure, Follow→Save, Scholar→PubMed, related-variant 2-line shell, Franklin AF visual, AF/constraint layout.
- **Codex (mock+label until wired):** real view counts, last-updated, New/Updated timestamps, per-related-variant 4-axis states, constraint Z-score (if not already in contract), ClinVar submitter free-text (if not in contract), pub-graph per-year counts (variant + gene).

## Verified current touch-points
- `ReportClient.tsx` `ReportBody` (L587+): `MatrixOverture` L722, `CallCardsGrid` L728, Population L747, In-silico L787, ExpertPanel/ClinVar L827-845, MolecularContext L913, Disease/GeneDisease L945-948, PubMed L975, Trials L993, AI summary after.
- `CallCardsGrid.tsx`: `BADGE_TONES` + `fnTheme` (only `lab_functional` coloured today, L204).
- Hero (Follow/Export/Share) in the ready-report render of `ReportClient.tsx`.
- Sections are `LazySection`-wrapped + keyed + have anchor IDs via `targetFor(...)` — **preserve lazy-loading + anchors** through any reorder.
- Related variants: `components/library/**` (`VariantLibraryRail` / related lanes) on the report rail.
