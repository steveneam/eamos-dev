# v2 Frontend Rebuild — Claude Code

Port three Claude Design mocks to the React/Vite frontend without migrating to Next.js. Build on existing Phase 0–2 scaffolding (tokens, fonts, base components already in place per `plans/frontend-rebuild.md`).

## Status (2026-05-15)

| ID | Milestone | Status |
| -- | --------- | ------ |
| FE-0 | Foundation refresh | ✅ Done — tokens (canvas, base, AA, widths), `.hairline` utility, `ModePill` wired into ReportPage. Also fixed pre-existing `tsconfig` `@/*` path-alias gap. |
| FE-1 | Landing v2 | ✅ Done — Franklin removed from `sources.ts`, `sample-report.ts`, FeaturesGrid, HowItWorks, LandingPage; replaced with AlphaMissense where a 6th source was named. LegacyRunsApp untouched (frozen). |
| FE-2 | Report v2 new modules | ✅ Done — 6 components (LocusContext, InSilicoGrid, AcmgCriteriaFold, CuratedVariantsGrid, AssociatedConditions, PublicationsCallout). ~180 lines of v2 module CSS appended to `index.css`. Wired into 3 outer Cards in ReportPage. EvidenceTable + DiseaseSection gained an `embedded` prop. |
| FE-3 | Variant header v2 | ✅ Done — cross-DB chip strip (6 chips, no Franklin), tools row (Follow toggle, Export = window.print, Share = copy URL), 4-stat row (sample data). v2 header CSS appended. |
| **FE-3.5** | **Contract sync** | **Next — see section below.** |
| FE-4 | Workbench shell | Pending |
| FE-5 | Sequence Viewer + click-to-edit | Pending |
| FE-6 | Primer + CRISPR panels | Pending |
| FE-7 | Alignment + Comparator | Pending |
| FE-8 | AskEamos pill (tool-aware) | Pending |

Build last verified clean at end of FE-3: `tsc -b && vite build` → 573KB JS / 58KB CSS, 2.25s.

---

## FE-3.5 — Contract sync (next session)

**Goal:** Add the TypeScript interfaces for the new Pydantic models Codex shipped in BE-2 / BE-3 / BE-4, so `app/backend/tests/test_frontend_contract.py` passes and the FE-2 components can swap from hard-coded `SAMPLE` blocks to real `ReportPayload` data.

**Why this is the next thing:** The contract test currently fails — it's the canary that flags drift between Pydantic and TypeScript. The FE-2 modules render from hard-coded sample data right now; they should consume the new payload fields once the interfaces exist.

### Files to touch

| File | Change |
| ---- | ------ |
| `app/frontend/src/lib/backend.ts` | Add all new interfaces below. Extend the existing `ReportPayload` with six new optional fields. |
| `app/frontend/src/lib/sample-report.ts` | Optional but recommended: populate the new fields in `RPE65_SAMPLE` from Codex's `app/backend/app/fixtures/lookup_v2_modules.json` so the offline demo shows real data. |
| `app/frontend/src/components/report/LocusContext.tsx` | Wire from `payload.locus_context` instead of inline `SAMPLE_NEARBY` / `SAMPLE_CODONS`. Keep the SAMPLE blocks as the prop default so the component still renders standalone. |
| `app/frontend/src/components/report/InSilicoGrid.tsx` | Wire from `payload.in_silico_predictions`. |
| `app/frontend/src/components/report/AcmgCriteriaFold.tsx` | Wire from `payload.acmg_criteria_scaffold`. |
| `app/frontend/src/components/report/CuratedVariantsGrid.tsx` | Wire from `payload.curated_variants_distribution`. Note: backend uses object keys like `pathogenic_lof` / `vus_missense` / `benign_synonymous`; the component currently uses an array-of-rows shape. Decide whether to (a) add a transform helper or (b) restructure the component to consume the dict directly. Recommend (a) for minimal churn. |
| `app/frontend/src/components/report/AssociatedConditions.tsx` | Wire from `payload.associated_conditions`. |
| `app/frontend/src/components/report/PublicationsCallout.tsx` | Wire from `payload.publications_callout`. |
| `app/frontend/src/pages/ReportPage.tsx` | Pass `payload.*` props into each new module. Keep sample-data fallback for legacy mode. |

### Interfaces to add to `backend.ts`

Mirror `app/backend/app/schemas/run.py` (the new types Codex added near the top):

```ts
export type ClassificationTier =
  | 'pathogenic'
  | 'likely_pathogenic'
  | 'vus'
  | 'likely_benign'
  | 'benign'

export type AcmgVerdict = 'met' | 'not_met' | 'not_assessed'
export type PredictorVerdict = 'damaging' | 'tolerated' | 'uncertain'

export interface NearbyVariant {
  cds_pos: number
  classification: ClassificationTier
  hgvs: string
  clinvar_id?: string | null
}

export interface CodonCell {
  codon_number: number
  aa_ref: string
  is_query?: boolean
}

export interface LocusContext {
  gene: string
  centre_cdna: string
  nearby_variants: NearbyVariant[]
  codon_strip: CodonCell[]
}

export interface PredictorCard {
  name: 'REVEL' | 'AlphaMissense' | 'MetaLR' | 'SpliceAI'
  score: number
  threshold: number
  verdict: PredictorVerdict
  source_url?: string | null
}

export interface InSilicoPredictions {
  cards: PredictorCard[]
  consensus_note: string
}

export type AcmgCode =
  | 'PVS1'
  | 'PS1' | 'PS2' | 'PS3' | 'PS4'
  | 'PM1' | 'PM2' | 'PM3' | 'PM4' | 'PM5' | 'PM6'
  | 'PP1' | 'PP2' | 'PP3' | 'PP4' | 'PP5'
  | 'BA1'
  | 'BS1' | 'BS2' | 'BS3' | 'BS4'
  | 'BP1' | 'BP2' | 'BP3' | 'BP4' | 'BP5' | 'BP6' | 'BP7'

export interface AcmgCriterion {
  code: AcmgCode
  verdict: AcmgVerdict
  note?: string | null
}

export interface AcmgCriteriaScaffold {
  criteria: AcmgCriterion[]
  disclaimer: string
}

export interface CuratedVariantsDistribution {
  cells: Record<string, number>     // keys: "pathogenic_lof", "vus_missense", ... 12 total
  total: number
  reading: string
}

export type EvidenceLevel = 'definitive' | 'strong' | 'moderate' | 'limited'
export type Inheritance = 'AR' | 'AD' | 'XL' | 'MT'

export interface AssociatedCondition {
  name: string
  case_count: number
  evidence_level: EvidenceLevel
  inheritance: Inheritance
  source: string
}

export interface PublicationsCallout {
  total_count: number
  scholar_url: string
  ai_summary_prompt: string
}
```

Then extend `ReportPayload`:

```ts
export interface ReportPayload {
  // ... all existing fields unchanged ...
  locus_context?: LocusContext | null
  in_silico_predictions?: InSilicoPredictions | null
  acmg_criteria_scaffold?: AcmgCriteriaScaffold | null
  curated_variants_distribution?: CuratedVariantsDistribution | null
  associated_conditions?: AssociatedCondition[]
  publications_callout?: PublicationsCallout | null
}
```

From `app/backend/app/schemas/chat.py`:

```ts
export type WorkbenchTool = 'viewer' | 'primer' | 'crispr' | 'align' | 'compare'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface WorkbenchEdit {
  position: number
  ref_base: 'A' | 'T' | 'C' | 'G'
  new_base: 'A' | 'T' | 'C' | 'G' | 'del'
  consequence: string
}

export interface WorkbenchContext {
  active_tool: WorkbenchTool
  scratchpad: WorkbenchEdit[]
  selected_primer_pair?: number | null
  selected_guide?: number | null
}

export interface ChatRequest {
  question: string
  variant_context: ReportPayload
  history?: ChatMessage[]
  workbench?: WorkbenchContext | null
}

export interface ChatResponse {
  answer: string
}
```

From `app/backend/app/schemas/workbench.py`:

```ts
export type PrimerMode = 'sanger' | 'qpcr' | 'arms'

export interface PrimerRequest {
  gene: string
  cdna: string
  mode?: PrimerMode
  tm_min?: number
  tm_max?: number
  product_size_min?: number
  product_size_max?: number
  avoid_snps?: boolean
}

export interface PrimerPair {
  index: number
  forward: string
  reverse: string
  tm_forward: number
  tm_reverse: number
  gc_forward: number
  gc_reverse: number
  product_size: number
  specificity_hits: number
  notes?: string
  recommended?: boolean
}

export interface PrimerResponse {
  mode: PrimerMode
  pairs: PrimerPair[]
}

export type CasEnzyme = 'SpCas9' | 'SaCas9' | 'Cas12a'

export interface CrisprRequest {
  gene: string
  cdna: string
  cas?: CasEnzyme
  strand_filter?: 'both' | 'plus' | 'minus'
  off_target_tolerance?: number
}

export interface CrisprGuide {
  index: number
  cut_position: number
  strand: '+' | '-'
  guide: string
  pam: string
  on_target_score: number
  off_target_score: number
  gc_percent: number
  notes?: string
}

export interface HdrSsodn {
  reference_arm: string
  variant_arm: string
  repair_template: string
  edits_encoded: string[]
  arm_lengths: Record<string, number>
  estimated_hdr_efficiency: number
}

export interface CrisprResponse {
  cas: CasEnzyme
  guides: CrisprGuide[]
  ssodn?: HdrSsodn | null
}

export interface AlignRequest {
  gene: string
  cdna: string
  user_sequence?: string | null
  ab1_blob_base64?: string | null
}

export interface TraceChannel {
  base: 'A' | 'T' | 'C' | 'G'
  values: number[]
}

export interface AlignResponse {
  reference: string
  sanger_read: string
  match_line: string
  mismatch_positions: number[]
  target_position: number
  trace_channels: TraceChannel[]
  base_calls: string[]
  q_scores: number[]
}
```

### Sequencing

1. Add all the interfaces above to `app/frontend/src/lib/backend.ts`. Keep existing interfaces. Don't drop or rename anything.
2. Run `cd app/frontend && npm run build` — should pass.
3. Run `cd app/backend && python -m pytest tests/test_frontend_contract.py -q` — should now pass (Codex pre-extended the test for these fields).
4. Update `RPE65_SAMPLE` in `sample-report.ts` to include `locus_context`, `in_silico_predictions`, `acmg_criteria_scaffold`, `curated_variants_distribution`, `associated_conditions`, `publications_callout`. Mirror the shape from `app/backend/app/fixtures/lookup_v2_modules.json` (Codex's file).
5. Update the 6 FE-2 components to accept optional `payload`-derived props and fall back to their `SAMPLE` blocks when undefined. Wire from `payload.*` in `ReportPage.tsx`.
6. Browser spot-check at `/report?demo` — both modes (sample fallback + real backend) should render identically.

### Acceptance

- `npm run build` clean.
- `pytest tests/ -q` from `app/backend` shows 0 failures (currently 1: `test_frontend_contract.py`).
- The 6 report v2 modules render the same content whether driven by `RPE65_SAMPLE` or by `POST /api/v1/lookup` against the live backend.
- No TypeScript errors when consuming `payload.locus_context?.nearby_variants` etc.

Estimated effort: ~45 minutes of mostly mechanical interface entry + minor component wiring.

---

**Source mocks** (in `e:\Web tool\Claude Design\`):
- `Eamos Landing Page.html` — public landing
- `Eamos Report Page v2.html` — variant report v2 (replaces v1 mock)
- `Eamos Workbench v1.html` + `Workbench/*.{js,css}` — new sequence-tools surface

**Stack** — React 18 + TypeScript + Vite + Tailwind v4. **Do not migrate to Next.js.** Re-evaluate later if file-based API routing / RSC becomes load-bearing.

**Routes**

| Path | Page | Source mock |
| ---- | ---- | ----------- |
| `/` | `pages/LandingPage.tsx` | `Eamos Landing Page.html` |
| `/report` | `pages/ReportPage.tsx` | `Eamos Report Page v2.html` |
| `/workbench` | `pages/WorkbenchPage.tsx` (new) | `Eamos Workbench v1.html` |
| `/runs` | `pages/LegacyRunsApp.tsx` | **Frozen — do not modify.** Layer 2 patient report flow. |

---

## Milestones

### FE-0 — Foundation refresh

Existing `src/index.css` has the v2 tokens, the Google Fonts import, and Tailwind theme wiring. Confirm and extend.

**Add to `src/index.css`** (in the `:root` block):

```css
/* Workbench-only canvas wash */
--bg-canvas: #fbfcfd;

/* Sequence palette — muted, ~25% chroma. Never use Benchling rainbow. */
--base-A: #d29a4a;
--base-T: #5081b9;
--base-C: #4a9d8f;
--base-G: #b75a5a;

/* Amino-acid biochem class pill backgrounds */
--aa-hydro: #f1ead8;
--aa-polar: #e0ecdb;
--aa-acid:  #f6e0e0;
--aa-basic: #dbe5f4;
--aa-aroma: #ebe1f0;
--aa-cys:   #f4ecd2;
--aa-stop:  #d9dde2;

/* Width helpers — exposed as CSS vars so JSX can read them too */
--maxw-report: 920px;
--maxw-nav: 1180px;
--maxw-landing: 1180px;
--maxw-workbench: 1440px;
--maxw-workbench-rail: 64px;
--maxw-workbench-side: 360px;
```

**Hairline utility class** — add to `index.css`:

```css
.hairline { border: 0.5px solid var(--line); }
.hairline-b { border-bottom: 0.5px solid var(--line); }
.hairline-t { border-top: 0.5px solid var(--line); }
```

**Verify** — `cd app/frontend && npm run build` passes. Visit `/`, `/report`, `/workbench` (workbench will 404 until FE-4).

### FE-1 — Landing v2

`Eamos Landing Page.html` is the source of truth.

Files to update (already exist):
- `src/pages/LandingPage.tsx` — top-level layout
- `src/components/layout/TopNav.tsx` — add segmented `Report | Workbench` mode pill in nav actions (preserved across pages, links to `/report?q=...` and `/workbench?q=...` with current query)
- `src/components/landing/SourceStrip.tsx` — **remove Franklin** from the source list. Final list: ClinVar, gnomAD, Ensembl VEP, SpliceAI, AlphaMissense, OMIM, PubMed.
- `src/components/landing/FeaturesGrid.tsx` — copy/icons per mock
- `src/components/landing/HowItWorks.tsx` — copy per mock
- `src/components/landing/SiteFooter.tsx` — copy per mock
- `src/components/search/SearchShell.tsx` — confirm Gene variant ⇄ AI mode toggle matches the mock

**Acceptance** — landing renders pixel-close at 100% zoom on 1440px desktop. 1180px max-width centered. No Franklin links anywhere.

### FE-2 — Report v2: new modules

Six new components in `src/components/report/`. All take typed props from `ReportPayload` (extended in BE-2). Until BE-2 ships, hard-code sample data inside each component file in a `const SAMPLE` block, then swap to props once `ReportPayload` carries the fields.

| Component | File | What |
| --------- | ---- | ---- |
| `LocusContext.tsx` | new | Horizontal track, 5 stacked lanes (P/LP/VUS/LB/B) with nearby ClinVar variants as colored dots. Vertical marker drops to a codon strip (11 codons centred on the variant). Footer: legend + "Open full sequence in Workbench ↗" link. |
| `InSilicoGrid.tsx` | new | 4-card grid: REVEL / AlphaMissense / MetaLR / SpliceAI Δ. Each card: score, threshold marker on a 0→1 bar, verdict badge. Below the grid: a "Predictors converge / disagree" callout. |
| `AcmgCriteriaFold.tsx` | new | Collapsible fold showing the 28-criterion ACMG 2015/2022 grid (PVS1, PS1–4, PM1–6, PP1–5, BA1, BS1–4, BP1–7). Met criteria highlighted (warn-tint for pathogenic, teal-tint for benign). Disclaimer copy below grid: "Supporting evidence, not classification." |
| `CuratedVariantsGrid.tsx` | new | 3×4 heat-shaded matrix: rows = Pathogenic / VUS / Benign; cols = LOF / Missense / Non-coding / Synonymous. Counts + totals. One-line reading below the matrix. |
| `AssociatedConditions.tsx` | new | Vertical list of conditions. Each: case count, evidence level bar (Definitive / Strong / Moderate / Limited), inheritance pill (AR/AD/XL), source attribution. |
| `PublicationsCallout.tsx` | new | Compact strip: total publication count, Google Scholar deep link, "AI summary" button that drops a pre-filled question into Ask Eamos. |

Wire into `pages/ReportPage.tsx` in the order from the v2 spec:

1. Breadcrumb
2. `<VariantHeader />` (expanded — see FE-3)
3. `<AIStack />` (unchanged from v1)
4. `<LocusContext />` (new)
5. Evidence by source — wrap with: `<InSilicoGrid />` + existing `<EvidenceTable />` + existing verify-at-source chips + `<AcmgCriteriaFold />` (new)
6. Gene context — `<DiseaseSection />` (existing) at top + `<CuratedVariantsGrid />` + `<AssociatedConditions />` + `<PublicationsCallout />`
7. `<TrialsSection />` (unchanged)
8. `<LimitationsSection />` (unchanged)

**Acceptance** — `/report?q=RPE65:c.260A>G` renders all sections. At 920px main column, all hairlines survive at 100/125/150% zoom. No Franklin chip in the cross-DB strip.

### FE-3 — Variant header v2 + cross-DB strip + tools row

Expand `src/components/report/VariantHeader.tsx` to match the v2 mock:

- Gene name (display font), protein change (mono), classification badge(s)
- Cross-DB jump strip — 6 chips: ClinVar / gnomAD / UCSC / Ensembl / OMIM / AlphaFold. **No Franklin chip. No "Compare elsewhere ↗" link.** (The mock includes one — drop it.)
- Tools row — three ghost buttons: Follow / Export PDF / Share. Wire to no-op handlers for now; flag as M-002.
- 4-stat row — Position / Codon / Reference Population / Conservation. Pull values from `VariantSummaryRow`.

**Acceptance** — header occupies ~28px vertical padding × 32px horizontal, hairline-bordered, matches mock layout.

### FE-4 — Workbench shell

New page + layout chrome. Files:

```
src/pages/WorkbenchPage.tsx
src/components/workbench/
  WorkbenchShell.tsx       # 3-col layout: rail (64) / canvas (flex) / side (360)
  ContextStrip.tsx         # slim row beneath nav: gene · cdna · protein · transcript · coord · build · gene length
  ToolRail.tsx             # left icon rail, 5 tools, vertical
  SidePanel.tsx            # right panel, content swaps per active tool
  CanvasHeader.tsx         # title + subtitle + track-toggle checkboxes + zoom pill
```

Tool state: a `WorkbenchPage`-level `useState<Tool>('viewer')` drives rail active style + canvas header content + side panel content + Sequence Viewer visibility (collapses for `align`/`compare`).

Responsive — at <1200px collapse side panel; at <760px collapse rail. Hide → don't unmount.

URL — read `?q=RPE65:c.260A>G` to seed gene/variant context. If absent, redirect to `/` for now.

**Acceptance** — empty Workbench shell renders, tool buttons switch active state, no canvas content yet.

### FE-5 — Sequence Viewer + click-to-edit

The Workbench spine. Port `workbench/sequence-viewer.js` + `workbench/data.js` to TypeScript.

Files:

```
src/lib/workbench/
  codon-table.ts           # codonTable, aaThree, aaClass, translate, consequenceOf
  sample-rpe65.ts          # 90-bp window centred on c.260, ClinVar variants, conservation, restriction enzymes
src/components/workbench/viewer/
  SequenceViewer.tsx       # orchestrates tracks
  Track.tsx                # generic <Track label>{children}</Track>
  BaseRow.tsx              # clickable A/T/C/G bases, colour by base, hover state
  CodonRow.tsx             # AA pills, background by biochem class
  AnnotationRow.tsx        # exon / CDS / oligo bars
  DomainRow.tsx            # UniProt domain bar (carotenoid oxygenase for RPE65)
  VariantRow.tsx           # ClinVar dots positioned by cdsPos, coloured by classification
  ConservationRow.tsx      # PhyloP bars per base
  RestrictionRow.tsx       # enzyme marks + labels (off by default)
  VariantMarker.tsx        # vertical pin line + flag across all tracks
  EditPopover.tsx          # base-edit interaction
```

`codon-table.ts` is the testable core. Port `translate(seq)` and `consequenceOf(refSeq, pos, newBase)` verbatim from `workbench/data.js`. Add a Vitest unit test asserting:
- `consequenceOf` on `RPE65 c.260` GAC→GGC returns "Missense p.Asp87Gly"
- Same position, `del` option returns "Frameshift"
- Synonymous mutation returns "Synonymous"

`EditPopover` UX (the differentiator):
- Click any DNA base → popover anchored beneath the base
- Header: "Position 28 · ref A"
- 5 buttons: A / T / C / G / del
- Hover each button → live consequence preview (Synonymous / Missense p.X / Stop gained / Frameshift) using `consequenceOf`
- Apply → log edit to side-panel scratchpad, re-render base + AA pill at edited position
- "Reset to ref" → revert

Side panel content (driven by `WorkbenchPage` state):
- viewer active → kv-list of active variant + scratchpad + reading guide

**Acceptance** — clicking base 28 (the c.260 position) opens popover; hovering G shows "Missense p.Asp87Gly"; Apply commits, scratchpad logs the edit.

### FE-6 — Primer + CRISPR panels

```
src/components/workbench/primer/PrimerPanel.tsx
src/components/workbench/crispr/CrisprPanel.tsx
```

Port from `workbench/primer.js` + `workbench/crispr.js`.

**PrimerPanel** — segmented mode tabs (Sanger / qPCR / ARMS). Form: Target / Tm / Product size / GC / SNP avoidance / Run. Output table: # / Forward / Reverse / Tm (F/R) / GC (F/R) / Product / Specificity / Notes. Recommended pair: ★ + teal-tint row background.

**CrisprPanel** — form: target region (±10 bp default) / Cas enzyme (SpCas9/SaCas9/Cas12a) / strand filter / off-target tolerance. Output: gRNA table + HDR ssODN block (3 stacked lines: reference / variant / repair template; corrective bases teal-tint, silent PAM mutation indigo, target base warn-tint).

Side panel content updates: primer mode info + target context + AI assist chips; crispr editing strategy + window + AI assist chips.

Engine calls — POST to `/api/v1/primer` and `/api/v1/crispr` (BE-4). Until BE-4 ships, use canned response shapes from sample data.

**Acceptance** — switching to Primer keeps Sequence Viewer visible above; tables render with sample data; ★ row highlights.

### FE-7 — Alignment + Comparator

```
src/components/workbench/align/AlignmentPanel.tsx
src/components/workbench/align/Chromatogram.tsx
src/components/workbench/compare/ComparatorGrid.tsx
```

Port from `workbench/alignment.js` + `workbench/comparator.js`.

**AlignmentPanel** — two blocks:
1. Alignment block (3 rows: Reference / Match / Sanger read). Mismatches red; target base warn-tint background. Pairwise (Needleman–Wunsch) computed server-side (BE-4); client renders.
2. Chromatogram block — Canvas-based AB1 trace. 4 colour channels (A/T/C/G as Gaussian peaks), base calls row beneath, Q-scores beneath that. Dashed warn-coloured vertical marker at target base. Port the drawing code verbatim — it's self-contained.

Inputs — paste textarea, "Upload AB1" button (uses FileReader to send blob to `/api/v1/align`), "Paste FASTA" button.

**ComparatorGrid** — rows = properties, cols = up to 3 variants. Rows: Codon / Consequence / ClinVar / gnomAD AF / REVEL / AlphaMissense / SpliceAI Δ / UniProt domain / Conservation / Mechanism. Predictors render as score + horizontal bar with threshold marker. Mechanism cells: warn / ok / err colours for at-a-glance reading.

When Align or Compare is active, the Sequence Viewer collapses (canvas content replaced).

**Acceptance** — Align tab paints 4-channel chromatogram; Compare tab renders 3-column grid with predictor bars.

### FE-8 — AskEamos pill (tool-aware)

```
src/components/workbench/ai/AskEamosPill.tsx
```

Floating bottom-right button (420×56). Label: `Ask Eamos · <current tool>` — updates from `WorkbenchPage` state. Click expands into a 420px-wide chat panel that grows upward.

Suggested-question chips change per tool:
- viewer → "What does this missense do?" / "Is this in a domain?"
- primer → "Best primer pair for Sanger?" / "Why is the recommended pair starred?"
- crispr → "Best guide for this variant" / "ssODN repair efficiency?"
- align → "How do I read this trace?" / "Q-score interpretation"
- compare → "Which variant is most pathogenic?" / "Why do the predictors disagree?"

Chat history persists within session (`useState` on WorkbenchPage, not localStorage). Pill stays mounted across tool switches.

When opened from a suggested-question chip inside a panel (e.g. "Best guide for this variant" inside CrisprPanel), the question is pre-filled and submitted automatically.

Wire to `POST /api/v1/chat` (BE-3) with body:

```ts
{
  question: string,
  variantContext: ReportPayload,  // current variant
  history: ChatMessage[],
  workbench: {
    activeTool: 'viewer' | 'primer' | 'crispr' | 'align' | 'compare',
    scratchpad: Edit[],
    selectedPrimerPair?: number,
    selectedGuide?: number,
  }
}
```

Response — stream as `text/plain` (same shape as existing `/runs/.../chat/stream`).

For `/report` (not Workbench), use the same `<AskEamos />` component as today, also calling `POST /api/v1/chat` but with `workbench` omitted.

**Acceptance** — pill renders on `/workbench`, label tracks active tool, sending a question hits `/api/v1/chat` and streams response into the panel.

---

## Tasks deferred to M-002 (post-v2)

- Real engine calls (Primer3 / CRISPOR / Needleman–Wunsch / AB1 parser). Sample data for v2.
- Multi-variant editing in the sequence viewer (one edit at a time tracked; multiple edits land sequentially).
- Persist Workbench sessions (no persistence layer in v2; reload = reset).
- Real PhyloP + UniProt domain ingestion (currently sample-rpe65.ts hardcoded).
- Mouse mm39 support in Workbench (Sequence Viewer + tools assume human; mouse comes later).

---

## Out of scope

- Auth, billing, accounts, analytics
- Bulk VCF analysis pipeline
- Migrating Layer 2 (`/runs`) to v2 styling — it stays frozen on the old design system
- Migrating to Next.js
