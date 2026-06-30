# v2 Frontend Rebuild — Claude Code

> Superseded historical plan. Do not execute for live Eamos frontend work.
> The active frontend source of truth is the Next.js app in `app/web`.
> `app/frontend` is a frozen Vite reference retained only for comparison until
> Steven approves an exact deletion or regeneration task.

Port three Claude Design mocks to the React/Vite frontend without migrating to Next.js. Build on existing Phase 0–2 scaffolding (tokens, fonts, base components already in place per `plans/frontend-rebuild.md`).

## Status (2026-05-15)

| ID | Milestone | Status |
| -- | --------- | ------ |
| FE-0 | Foundation refresh | ✅ Done — tokens (canvas, base, AA, widths), `.hairline` utility, `ModePill` wired into ReportPage. Also fixed pre-existing `tsconfig` `@/*` path-alias gap. |
| FE-1 | Landing v2 | ✅ Done — Franklin removed from `sources.ts`, `sample-report.ts`, FeaturesGrid, HowItWorks, LandingPage; replaced with AlphaMissense where a 6th source was named. LegacyRunsApp untouched (frozen). |
| FE-2 | Report v2 new modules | ✅ Done — 6 components (LocusContext, InSilicoGrid, AcmgCriteriaFold, CuratedVariantsGrid, AssociatedConditions, PublicationsCallout). ~180 lines of v2 module CSS appended to `index.css`. Wired into 3 outer Cards in ReportPage. EvidenceTable + DiseaseSection gained an `embedded` prop. |
| FE-3 | Variant header v2 | ✅ Done — cross-DB chip strip (6 chips, no Franklin), tools row (Follow toggle, Export = window.print, Share = copy URL), 4-stat row (sample data). v2 header CSS appended. |
| FE-3.5 | Contract sync | ✅ Done (2026-05-15) — `backend.ts` interfaces added, `RPE65_SAMPLE` populated, 6 components wired to `payload.*` with renamed internal display interfaces. `tsc --noEmit` clean. Exposed a mock-fidelity gap → see FE-3.6. |
| FE-4 | Workbench shell | ✅ Done (2026-05-15). `/workbench` route + chrome (`src/components/workbench/*`, `WorkbenchPage`, scoped `styles/workbench.css`). tsc/build clean; all modules transform. Plan deviation: no-param `/workbench` defaults to RPE65 sample (not redirect to `/`). |
| FE-5 | Sequence Viewer + click-to-edit | ✅ Done (2026-05-15) — **superseded by FE-5.5** (built against the older Workbench v1 mock; the v2 mock is a substantial evolution). `src/lib/workbench/{codon-table,sample-rpe65}.ts` + 11 viewer components under `src/components/workbench/viewer/`; wired into `WorkbenchShell` (lifted `edits`/`scratch`/`tracksOn`, controlled `CanvasHeader`, viewer-mode `SidePanel`). Vitest added (`npm run test`, 5/5). `npm run build` green; `test_frontend_contract.py` 40/40 (unchanged — no contract touch). Deviations: (1) 1-char sample-data coherence fix so codon 87 = GAC/Asp → spec `p.Asp87Gly`; (2) hover-preview added to EditPopover (plan/acceptance say hover; source JS only previewed on click). |
| FE-3.6 | Report payload fidelity reconcile | ✅ Done (2026-05-15). `backend.ts` + `sample-report.ts` synced to BE-6; all 6 report components rewritten to consume the enriched payload; divergent SAMPLE datasets deleted (empty-state when no data). `npm run build` green; `test_frontend_contract.py` 40/40 PASS. |
| FE-5.5 | Sequence Viewer v2 (Benchling-grade) + chrome relayout | ✅ Done (2026-05-16). Ported `Eamos Workbench v2.html` + `Workbench v2/*` to React: `lib/workbench/{gene-window,sample-rpe65-v2,edit-state}.ts` + `gene-window.test.ts`; `viewer/{SequenceViewerV2,ViewerToolbar,GeneMinimap,ExonStrip,CodonDetail,SelectionBar,HistoryTimeline,EditPopoverV2,ZoomSlider,viewer-types}.tsx` + new `ToolBar.tsx`; rewrote `CanvasHeader`/`SidePanel`/`WorkbenchShell`. 4 mods all in: (1) ClinVar density toggle (Tracks dropdown, grouped w/ pins); (2) collapsible side-panel exon disclosure; (3) horizontal segmented tool selector top-right, left rail removed (`.wb` → 2-col); (4) Benchling −/+ density slider + retained Gene/Exon/Codon chips + minimap/exon-strip collapse + restriction-as-top-ticks/beige-band aesthetics. 14 superseded FE-5 files deleted. Verified: `npx vitest run` 24/24, `npm run build` clean, `test_frontend_contract.py` 40/40 (untouched). Then Codex adversarial hardening pass (`task-mp8d61ip-1zyj8k`) fixed 2 HIGH / 2 MED / 3 LOW (drag-unmount leak, popover portal+viewport clamp, history-jump bounds, data-driven intronic ClinVar mapping, a11y/keys/stale-CSS); Claude re-verified post-Codex (24/24, clean, 40/40). Browser pixel-check pending a dev-server session. |
| FE-5.6 | Workbench viewer refinement pass (8 pixel-check fixes) | **In progress (2026-05-17)** — Unit A (items 2,3,5) DONE + user-accepted; Unit B (item 1) DONE + verified; **Unit C (items 4,7 — unified edit-hub redesign) DONE + verified** (vitest 24/24, build clean, contract 40/40 + browser pixel-check: canvas selects, right-click cursor edit menu, Scratchpad hub, `SelectionBar` deleted, reducer kept in viewer). **Uncommitted.** Units D (item 6 dynamic reflow, highest risk) + E (item 8 variant-render) remain. Decisions locked (see "FE-5.6"). Execute before FE-6 (shares the chrome). |
| FE-6 | Primer + CRISPR panels | **CRISPR slice ✅ DONE + verified (2026-05-17 · Claude S26)** — `plans/crispr-integration.md` §5; mock-first on `CrisprResponse`. **Primer slice ✅ DONE + verified (2026-05-18 · Claude)** — `plans/primer-integration.md` §5 Phase A, mock-first on the frozen `POST /api/v1/primer` contract; the 3-layer progressive-disclosure card is the first reference implementation of DESIGN.md's Dashboard Interaction Language (`--elev-*`/`--dur-*`/`--ease-*` tokens + reduced-motion guard added to `index.css`). vitest 53/53, build clean, contract 40/40 untouched, DESIGN.md-conformance grep, browser pixel-check. Presentation is 3-layer cards, not the older "output table" wording (superseded — see `plans/primer-integration.md §4.4`). §6 Phase-B additive `specificity_detail` is a gated Codex brief (filed in `agent_handoff/CURRENT.md` Cross-Agent Requests). Builds on FE-5.5/FE-5.6 chrome. |
| FE-7 | Alignment + Comparator | **Alignment ✅ DONE + mock-wired** (`app/web/components/workbench/align/AlignPanel.tsx`, in `TOOL_ORDER`; paste/FASTA/AB1 chromatogram). **Comparator ❌ NOT BUILT** — ghost only: `tools.ts` has `TOOL_META.compare` + `WorkbenchTool 'compare'` + orphaned `.compare-grid` CSS, but `compare` is absent from `TOOL_ORDER`/`PANEL_TOOLS` (unreachable) and no `ComparatorGrid`/`ComparatorPanel` exists. Corrected 2026-06-06 (was "Pending"). |
| FE-8 | AskEamos pill (tool-aware) | **Pending — PARKED.** No `.tsx` mounts the pill (orphaned `.ai-pill`/`.ai-panel` CSS only). Deferred: LLM API key unfunded ([[feedback_askeamos_parked]]). Keep "COMING SOON" until Steven funds the key. Clarified 2026-06-06. |
| FE-14 | Search robustness + `cleanQuery()` | ✅ Done (2026-05-16). `cleanQuery()`/`isLikelyUnparseable()` + 1-retry/backoff + malformed/unresolved/offline/degraded states. Cross-check HIGH-2: `coord` regex widened to accept VCF-quad genomic input (`1-68444869-T-C`, `chr1:68444869:T:C`) the backend already accepts. No `backend.ts`/contract change. vitest 21/21, build clean. |

**Parallel run model (2026-05-15):** Claude Code runs FE-4 → FE-5 (all-new Workbench files, zero overlap with `app/backend/`) while Codex runs BE-6 → BE-7. When BE-6 lands the enriched schema+fixture, Claude Code picks up FE-3.6, then continues FE-6 → FE-7 → FE-8. `test_frontend_contract.py` is the BE-6 ↔ FE-3.6 drift canary.

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

> **FE-3.5 status: ✅ Done (2026-05-15).** Wiring complete. Discovered the backend fixture carries less than the mock; the 6 components still embed richer `SAMPLE` blocks as fallbacks. FE-3.6 (below) reconciles this once BE-6 enriches the payload.

---

## FE-3.6 — Report payload fidelity reconcile (✅ DONE 2026-05-15)

**Goal:** payload-driven rendering equals the Report Page v2 mock; lossy `SAMPLE`-fallback mappings deleted. **Achieved** — all 6 components consume the enriched payload; divergent SAMPLE datasets removed; `npm run build` green; `test_frontend_contract.py` 40/40. (Browser pixel check pending a session with a working dev server.)

**Done (2026-05-15):** Codex BE-6 verified (schema additive, fixture mirrors the SAMPLE constants). Frontend contract + component reconcile complete:
- `src/lib/backend.ts` — all 8 BE-6 field groups added (optional): `NearbyVariant.protein_change`; `CodonCell.{aa_alt,dna_ref,dna_alt}`; `LocusContext.coords`; `PredictorCard.verdict_label`; `AcmgCriteriaScaffold.{intro,note}`; `CuratedVariantsDistribution.{row_totals,subtitle}`; `AssociatedCondition.{db_tag,db_tag_bold,source_list}`; `PublicationsCallout.blurb`.
- `src/lib/sample-report.ts` — `RPE65_SAMPLE` v2 modules rewritten to mirror `lookup_v2_modules.json` exactly.
- Verified: `cd app/frontend && npm run build` green; `cd app/backend && python -m pytest tests/test_frontend_contract.py -q` → 40/40 PASS (BE-6 ↔ FE-3.6 drift resolved).

**Historical — completed.** The "remaining" component-reconcile work below was finished in FE-3.6 (✅ 2026-05-15): all 6 components consume the new fields and the divergent `SAMPLE`/default constants were removed. The file table that follows is retained as a record of what changed, not as outstanding work.

### Files to touch

| File | Change |
| ---- | ------ |
| `src/lib/backend.ts` | Add the BE-6 fields to the TS interfaces: `CodonCell.{aa_alt,dna_ref,dna_alt}`, `NearbyVariant.protein_change`, `LocusContext.coords`, `PredictorCard.verdict_label`, `AcmgCriteriaScaffold.{intro,note}`, `CuratedVariantsDistribution.{row_totals,subtitle}`, `AssociatedCondition.{db_tag,db_tag_bold,source_list}` (replacing `source`), `PublicationsCallout.blurb`. |
| `src/lib/sample-report.ts` | Repopulate `RPE65_SAMPLE` from the rewritten fixture so the offline demo matches the mock. |
| `LocusContext.tsx` | Use `dna_ref`/`dna_alt` to render the codon DNA + highlighted variant base; `aa_alt` for `Asp → Gly`; `coords` from payload; map all 11 `nearby_variants`. Delete `SAMPLE_NEARBY`/`SAMPLE_CODONS` (or keep only as a typed empty-state default, not a divergent dataset). |
| `InSilicoGrid.tsx` | Use `verdict_label` for the verdict text (drop the generic `VERDICT_LABEL` enum map). |
| `AcmgCriteriaFold.tsx` | Use payload `intro`/`note`; drop `SAMPLE_INTRO`/`SAMPLE_NOTE`. |
| `CuratedVariantsGrid.tsx` | Use `row_totals` + `subtitle`; recompute heat from real counts. |
| `AssociatedConditions.tsx` | Use `db_tag`/`db_tag_bold`/`source_list` directly; drop the `splitSource` heuristic. |
| `PublicationsCallout.tsx` | Use payload `blurb`. |
| `ReportPage.tsx` | No structural change — props already wired in FE-3.5. |

### Acceptance

- `npm run build` clean.
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q` passes (BE-6 ↔ FE-3.6 sync complete).
- `/report?demo=1` renders pixel-equivalent to the Report Page v2 mock — codon strip shows DNA + `Asp → Gly`, 11 locus dots, descriptive predictor verdicts, ACMG intro/note prose, per-row distribution totals, 5 associated conditions with split source attribution.
- No remaining divergent `SAMPLE` dataset constants in the 6 component files.

---

**Source mocks** (in `e:\Web tool\Claude Design\`):
- `Eamos Landing Page.html` — public landing
- `Eamos Report Page v2.html` — variant report v2 (replaces v1 mock)
- `Eamos Workbench v2.html` + `Workbench v2/*.{js,css}` — sequence-tools surface (v2 supersedes the retired `Eamos Workbench v1.html` + `Workbench/*`; FE-5.5 ports v2)

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

### FE-5.5 — Sequence Viewer v2 (Benchling-grade) + chrome relayout

**Why this milestone exists.** The design was revved: `Eamos Workbench v2.html`
+ `Workbench v2/*` (2026-05-16) supersedes the v1 mock FE-5 was built against.
The v2 viewer is a substantial evolution (gene minimap with ClinVar density,
exon strip, find/jump toolbar, ClinVar variant chevrons, undo/redo + edit
history, 3-way strand pill, export, wrapped 60 bp Benchling/SnapGene block
layout, intron/splice context). The user also requested 4 modifications and a
Benchling-style zoom slider. Doing this *before* FE-6/7/8 is required: those
panels share the canvas chrome and sit below the viewer — relaying the rail and
viewer after them means reworking their layout twice. Pure frontend; the
contract is untouched, so no Codex/backend dependency and the backend-first
checkpoint is undisturbed.

**Files**

```
src/lib/workbench/
  gene-window.ts            # port of data.js builders: buildFlatWindow / buildCodons /
                            #   consequenceAt (pure, testable); intron flanks + GT/AG splice
  sample-rpe65-v2.ts        # full 14-exon/intron structure, windowSegments, exonVariantCount
                            #   (density), proteinFeatures, genomicCoords, restriction flatPos
  gene-window.test.ts       # vitest: consequenceAt sub/del/splice/intronic; buildCodons frame
src/components/workbench/viewer/
  SequenceViewerV2.tsx      # orchestrator: toolbar → minimap → exon strip → codon detail →
                            #   selection bar → history timeline
  ViewerToolbar.tsx         # find/jump box, ClinVar ‹ count › chevrons, undo/redo/history toggle
  GeneMinimap.tsx           # proportional exon/intron band, ClinVar density bubbles (TOGGLEABLE),
                            #   active-window flag, 5′/3′ bookends, click-exon-to-jump
  ExonStrip.tsx             # current-exon header + ClinVar pins + ruler
  CodonDetail.tsx           # wrapped ROW_BP-base blocks; rows: annotation / domain / clinvar /
                            #   translation / ruler / sequence / complement / conservation /
                            #   restriction; intron-gap separators
  SelectionBar.tsx          # single-base / range selection summary + delete/replace/clear
  HistoryTimeline.tsx       # edit-history drawer (toggle; hidden by default)
  EditPopoverV2.tsx         # sub (A/T/C/G) / del / insert + live consequence preview
src/components/workbench/
  ToolBar.tsx               # NEW horizontal segmented tool selector (replaces left ToolRail)
  ZoomSlider.tsx            # Benchling −/+ density slider (BASE_W) + retained Gene/Exon/Codon chips
```

**State** (lift into `WorkbenchShell`, `useReducer` for edit/history):
`edits: Map<flatIdx, {kind:'sub'|'del'|'ins', alt}>`, `history[]`,
`historyCursor`, `selection`, `strandMode: 'top'|'both'|'rev'`,
`trackOn` (annotations/domains/clinvar/clinvarDensity/conservation/restriction),
`searchQuery`, `showHistory`, `baseW` (zoom density), `navCollapsed`
(minimap+exon-strip), `exonTableOpen` (side panel).

**The 4 modifications (the user's asks):**

1. **ClinVar density-bubble toggle.** Split the single ClinVar concern into two
   toggles in the Tracks dropdown: `ClinVar pins` (in-window dots, existing) and
   `ClinVar density` (the per-exon minimap bubbles — currently unconditional in
   `sv-minimap.js`). `GeneMinimap` renders bubbles only when
   `trackOn.clinvarDensity`.
2. **Collapsible exon table.** The side-panel Transcript section's
   `Exons (click to view)` table becomes a disclosure (`<details>`-style),
   default collapsed, state in `exonTableOpen`. Active-exon summary line stays
   visible when collapsed.
3. **Tool selector → horizontal, top-right.** Delete the left `.rail` column;
   `.wb` grid becomes `1fr / var(--side-w)`. New `ToolBar.tsx` is a horizontal
   segmented control (icon + label, 5 items) placed in `canvas-head-right`.
   Reclaims 64 px of viewer width permanently. Responsive: wraps under the title
   at < 900 px.
4. **Benchling zoom slider (augment).** `ZoomSlider.tsx` top-left of the viewer:
   a `−  ⎯⎯●⎯⎯  +` range input bound to `baseW` (≈ 8–22 px/base; `CodonDetail`
   reads it instead of the const), **plus** the existing Gene/Exon/Codon chips
   retained for semantic jumps (Gene → minimap-only fit; Exon → exon-strip
   focus; Codon → full base detail). Aesthetic pass while here: restriction
   sites as top-edge vertical ticks with bold labels (SnapGene style) and a
   beige feature arrow band for the gene/exon span. Keep the muted ~25%-chroma
   palette (DESIGN.md "never Benchling rainbow").

**CSS** — port the relevant `Workbench v2/workbench.css` rules into
`src/styles/workbench.css` (scoped, no global token collisions): `.sv-toolbar`,
`.sv-minimap*`, `.sv-exonstrip*`, `.sv-block*`, `.sv-codon/.sv-aa`, `.sv-base`,
`.sv-cv`, `.sv-selbar*`, `.sv-history*`, `.sv-edit-pop*`, `.sv-dropdown`,
`.sv-strand-pill`, plus new `.toolbar-seg` (horizontal selector) and
`.zoom-slider`. Remove now-dead `.rail*` rules. Domains default OFF-canvas
(side panel) per the v2 mock to save vertical space.

**Superseded by this milestone** (FE-5 files; replace, don't extend):
`viewer/{SequenceViewer,Track,BaseRow,CodonRow,AnnotationRow,DomainRow,VariantRow,ConservationRow,RestrictionRow,VariantMarker,EditPopover}.tsx`,
`ToolRail.tsx`. Keep `codon-table.ts` (still the shared codon/aa core).
`sample-rpe65.ts` retained only if still referenced; otherwise removed with its
FE-5 consumers.

**Verify**

```
cd app/frontend && npx vitest run        # green (gene-window.test.ts added)
cd app/frontend && npm run build         # tsc -b + vite, clean
cd app/backend  && python -m pytest tests/test_frontend_contract.py -q   # 40/40 (untouched)
```

Browser spot-check at `/workbench`: minimap renders 14-exon band; density
bubbles toggle; exon table collapses; tool selector is horizontal top-right and
the viewer spans full width; zoom slider changes base density live; click-edit
popover previews consequence; undo/redo works.

**Acceptance** — the 4 modifications are visibly present and correct; the
viewer matches the v2 mock's information hierarchy (minimap → exon strip →
codon detail); contract test still 40/40; build + vitest green.

### FE-5.6 — Workbench viewer refinement pass (8 pixel-check fixes)

> **Progress (2026-05-17) — FE-5.6 COMPLETE: all 8 items resolved.** Units A
> (items 2,3,5, S21, user-accepted), B (item 1, S23), C (items 4+7, S24) and
> **D + E (items 6 + 8, S25) DONE + verified**. Unit C — unified edit-hub
> redesign (canvas selects only; right-click cursor edit menu; Scratchpad
> absorbs the selection summary + range actions; `SelectionBar` deleted;
> reducer kept in viewer via the extended `onSelectionChange` /
> `SequenceViewerHandle` seam). **Unit D — dynamic reflow:** `buildLayout`
> extracted pure to `lib/workbench/codon-layout.ts` (`buildLayout(flat,
> rowBp)` + `LayoutItem` + `MIN_BP=12`); `CodonDetail` drives `rowBp` from a
> `useLayoutEffect` `ResizeObserver` on `.sv-detail` (`disconnect()` on
> unmount), memo keyed on `[containerW, baseW]` so width-resize, side-panel
> collapse **and zoom** all reflow. **Unit E — variant overlay:** a render-only
> baseline `sub` merged with user `edits` into the translation triplet only
> (`transEdits`) — never the reducer/Scratchpad/undo, survives "Reset all";
> `bases()` keeps `edits` so the queried ref base keeps `.variant` (the §E
> "`.variant` still reads correctly / distinct from user edits" constraint
> ruled out merging into `bases()`). Verified: vitest **35/35** (24 + 11 new
> pure layout cases) · build clean · contract **40/40** (untouched) · browser
> pixel-check (reflow on width/zoom/side-panel-collapse, **no h-scroll**;
> queried codon shows Gly + old Asp badge; Unit C left-select/right-edit not
> regressed). **Uncommitted** (working tree). Built on Codex's `88a3739`
> (ex-`f2de719`, Claude-reviewed). Next is user-gated (FE-6/7/8 / M-002) + the
> post-FE-5.6 Codex doc-sync pass. See `agent_handoff/CURRENT.md`.

**Why this milestone exists.** The 2026-05-17 browser pixel-check of FE-5.5
(first time the viewer was eyeballed, not just headless-verified) surfaced 8
changes. Several reshape FE-5.5 decisions; doing them *before* FE-6 is required
because FE-6's Primer/CRISPR panels share the canvas chrome and the side panel
this pass restructures — building FE-6 first means reworking it twice.

**Pre-flight (read before touching code).** Pure frontend; contract untouched
→ `test_frontend_contract.py` stays 40/40, no Codex/backend dependency.
**Nothing is committed** — the working tree is the only copy of the
variant-search + hardening + FE-5.5 batches. Work in small, independently
verifiable units; the dynamic-reflow item (item 6) is the highest risk —
isolate and verify it on its own.

**Locked decisions (user, 2026-05-17):**
- Item 6 → **dynamic reflow** (bases-per-row from live container width), not
  cosmetic.
- Items 4 + 7 → **unified edit-hub redesign** (canvas selects; all edits move
  off-canvas to a right-click context menu + the Scratchpad side panel).
- Item 8 → **small now, defer the cascade** (seed the queried variant as an
  applied baseline overlay; defer indel-aware downstream re-translation to
  M-002).

#### Work items (suggested order — lowest risk first)

**A. Mechanical / low-risk (one commit unit)**

**Item 2 — Remove the ExonStrip (the section between Gene View and Sequence
View).**
- `viewer/SequenceViewerV2.tsx`: drop the `ExonStrip` import and its render in
  the `!navCollapsed` block; keep `<GeneMinimap>`. `jumpToCdsPos` is still used
  by the imperative handle — keep it; only ExonStrip's `onPinClick` goes.
- Delete `viewer/ExonStrip.tsx`. Remove `.sv-exonstrip*` / `.sv-es-*` rules
  from `styles/workbench.css`.
- Copy sync: `viewer/ZoomSlider.tsx` nav-toggle `title`/label say "gene map +
  exon strip" — change to "gene map" (the toggle now controls only the
  minimap). Note in code/comment that `navCollapsed` now = minimap only.

**Item 3 — Merge ClinVar pins + density into one toggle** (reverses FE-5.5
mod #1 — conscious reversal per user: ClinVar everywhere or nowhere).
- `viewer/viewer-types.ts`: drop `clinvarDensity` from `TrackState` +
  `DEFAULT_TRACKS`.
- `CanvasHeader.tsx` `TRACKS`: remove the `clinvarDensity` row; relabel
  `clinvar` → `"ClinVar (gene map + in-window pins)"`.
- `viewer/GeneMinimap.tsx`: density bubbles render on `trackOn.clinvar`
  (rename the `showDensity` prop or pass `trackOn.clinvar` from
  `SequenceViewerV2`).
- Grep `clinvarDensity` repo-wide → zero remaining refs.

**Item 5 — Sticky collapse-context-panel button.**
- Root cause: `.side` is `position:sticky; overflow-y:auto`; the collapse
  button sits at the top of its *scrolling content*. Fix in
  `styles/workbench.css`: `.side-collapse-row { position: sticky; top: 0;
  z-index: 5; background: var(--bg); }` (+ a hairline-b and small padding so
  scrolled content doesn't bleed under). It's already the first child of the
  `.side` scroll container. Keep the `.wb.side-collapsed .side-collapse-row`
  override sticky too.

**B. Chrome relayout (one commit unit)**

**Item 1 — ContextStrip → tool selector; fold ClinVar/gnomAD into Active
variant.**
- `ContextStrip.tsx`: remove the right cluster (classification `ctx-badge` +
  `ctx-link`s). Add `tool` + `onSelectTool` props; render `<ToolBar>` in
  `.ctx-right`.
- `pages/WorkbenchPage.tsx`: pass `tool`/`setTool` into `<ContextStrip>` (state
  already lives here). Drop `RPE65_CTX.classification`/`links` from the strip
  call (keep the two URLs — they move to the side panel, below).
- `CanvasHeader.tsx`: remove the `<ToolBar>` render + `onSelectTool` prop; keep
  `tool` (still used for `TOOL_META` title/sub + `meta.tracks`) and the
  Tracks/strand/Export cluster. `WorkbenchShell.tsx`: stop threading
  `onSelectTool` into `CanvasHeader`.
- `SidePanel.tsx` `ViewerSide` "Active variant" section: add a compact
  external-links row (ClinVar + gnomAD — the two URLs from `RPE65_CTX.links`;
  keep as a fixture-level constant, consistent with the rest of the panel).
- **Layout sub-task / flag:** `--ctx-h` is `48px`; the segmented `ToolBar`
  (icon+label ×5) may not fit at that height. Either bump `--ctx-h` (it feeds
  `.wb` min-height + `.side` sticky offset — change in one place, both follow)
  or add a compact ToolBar variant. Decide visually during execution; verify
  the `.side` sticky `top:` math still lines up.

**C. Unified edit-hub redesign — items 4 + 7 (one commit unit; the
architectural one)**

Model: canvas = view/select only; **all editing moves off-canvas.**

- **Canvas (`CodonDetail.tsx`):** keep `onBaseMouseDown` drag-select
  (single + range + shift-extend already work). Left-click no longer opens the
  editor — remove the `onBaseClick`→popover path; click just selects. Add
  `onContextMenu` on base cells → `e.preventDefault()` → open the edit menu at
  the cursor.
- **Edit menu (`viewer/EditPopoverV2.tsx`):** repurpose as a cursor-anchored
  context menu (it already portals + viewport-clamps; switch the anchor from
  the base's `DOMRect` to the mouse point). Keeps sub/del/ins + live
  consequence preview. Optionally rename → `EditContextMenu.tsx`.
- **Scratchpad becomes the edit hub (`SidePanel.tsx` `ViewerSide`):** absorb
  the selection summary + range actions (delete N / replace / clear) from the
  now-deleted `SelectionBar`, above the existing edit-log list.
- **Architectural decision (central to this item):** selection state + the
  edit reducer currently live *inside* `SequenceViewerV2`; the side panel is a
  sibling rendered by `WorkbenchShell`. Do **not** lift the whole reducer.
  Instead extend the existing callback/handle seam (mirrors
  `onScratchChange`/`onActiveExonChange`): add an `onSelectionChange`
  callback + extend `SequenceViewerHandle` with `delSelection`/
  `replaceSelection`/`clearSelection`. `WorkbenchShell` holds the mirrored
  selection summary and passes it + the handle actions to `SidePanel`. The
  reducer stays in the viewer (least churn, preserves undo/redo + history).
- Delete `viewer/SelectionBar.tsx`; remove `.sv-selbar*` CSS; add
  Scratchpad selection/action CSS in the side-panel scope. Keyboard shortcuts
  (letter=sub, ⌫=del, arrows, Esc) already in `SequenceViewerV2` — keep; they
  fit "select then act."

**D. Dynamic reflow — item 6 (its own commit unit; highest risk)**

Honest framing for the executor: this is **not** a tweak and **not** something
the live test would have fixed. `CodonDetail` is fixed-pixel — every row is
`ROW_BP (60) × baseW`. Side-panel collapse only adds dead right-margin; zoom
changes `baseW` but never bases-per-row, so it never reflows. Both halves of
the user's comment 6 share this root cause.

- `viewer/CodonDetail.tsx`: make `ROW_BP` dynamic. `ResizeObserver` on
  `.sv-detail` (or `.sv-root`) → measure usable width → `rowBp =
  max(MIN_BP, floor((measuredW − RIGHT_MARGIN − padding) / baseW))`. Thread
  `rowBp` into `buildLayout(flat, rowBp)` (currently keys off the `ROW_BP`
  constant). Recompute on `baseW` change too, so **zoom also reflows**.
- Codon/translation/ruler/clinvar absolute positioning all derive from each
  row's `indices`, so they follow automatically; partial codons across a row
  boundary already render (`!allHere` path) — preserve that.
- Risks: `useMemo` deps, `ResizeObserver` lifecycle (clean up on unmount —
  remember the FE-5.5 drag-unmount leak Codex caught), and the intron-gap
  split interacting with a variable `rowBp`.
- Tests: extend `lib/workbench/gene-window.test.ts` (or a sibling) — extract
  `buildLayout` so it's pure and unit-test it across several `rowBp` values
  **including** intron-gap interaction (vitest can't measure DOM width; test
  the pure layout fn, not the observer).

**E. Variant-render small-now — item 8 (fold into D's unit or its own)**

- Seed the queried variant as an **applied baseline overlay** so its codon
  visibly shows the change (e.g. Asp→Gly), distinct from user edits: it must
  **not** appear in the Scratchpad edit log, **not** be on the undo stack, and
  survive "Reset all". Simplest: a separate baseline edit map merged with the
  user `edits` only at render time in `CodonDetail`'s translation/bases
  (don't push it through the reducer). Confirm the existing `.variant` CSS on
  the ref base still reads correctly once the codon also shows `changed`.
- **Defer (now an M-002 entry, added to "Tasks deferred to M-002"):**
  indel-aware spliced-CDS downstream re-translation — frameshift re-frames
  every downstream codon, recomputes the new premature/late stop, renders the
  truncated/extended protein. The current per-codon-independent recompute is
  not this; it is a new engine + viewer rework.

#### Verify (run after each commit unit; all green before reporting done)

```
cd app/frontend && npx vitest run        # green; +buildLayout cases for item 6
cd app/frontend && npm run build         # tsc -b + vite, clean
cd app/backend  && python -m pytest tests/test_frontend_contract.py -q   # 40/40 (untouched)
```
Then a browser pixel-check at `/workbench` (the gate that found these — don't
report done on headless alone): items 1–8 visibly correct; side-panel collapse
+ zoom both reflow the sequence; right-click edits, left-click selects; sticky
collapse button stays put while the side panel scrolls.

#### Acceptance

All 8 comments resolved with the locked decisions; vitest + build green;
contract still 40/40; FE-5.5's Codex-hardened fixes (drag-unmount, popover
portal/clamp, history bounds) not regressed by the redesign. Then the standard
clear-safe handoff + (post-verify) a scoped Codex grunt-work pass for
doc-sync/CHANGELOG/PROGRESS.

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

> **FE-6 CRISPR slice — ✅ DONE + verified 2026-05-17 23:47 +1000 · Claude Session 26.**
> The CRISPR half of FE-6 shipped per `plans/crispr-integration.md` **§5 Phase A**
> (Blueprint-1 gRNA design) **+ §8 Phase C-fe** (Blueprint-2 Outcomes scaffold),
> mock-first on the existing `CrisprResponse` contract. New
> `components/workbench/crispr/{CrisprPanel,DesignTab,GuideTrack,OutcomesTab,IndelSpectrum}.tsx`
> + `lib/workbench/{crispr-guide-map(+test),crispr-sample,crispr-tide-sample}.ts`;
> `api.ts` `designGuides`/`analyzeTide` (mock-first); `WorkbenchShell`/`SidePanel`
> (`CrisprSide`)/`workbench.css` wiring. Sub-tabs Design|Outcomes (rail stays 5
> tools). Verified: vitest **42/42** (+7 guide-map), build clean, contract
> **40/40** untouched, browser pixel-check at `/workbench`.
> **Codex-request compliance:** built **only** on the existing
> `CrisprResponse`/`CrisprGuide`/`HdrSsodn` fields — no additive fields
> (`specificity_score`/`target_sequence`/`genomic_region`), no `backend.ts`/
> schema change; TIDE shape kept FE-local (`crispr-tide-sample.ts`, Rule 5)
> until Codex ships §7. This satisfies the open Codex→Claude mock-first ask.
> Backend §6 (gRNA design engine) = Codex **M-002D**, done in parallel. §7
> (TIDE endpoint) brief filed in `agent_handoff/CURRENT.md` →
> `## Cross-Agent Requests` (pointer to `plans/crispr-integration.md §7`); FE
> stays mock-first, not blocked. FE-6 Primer panel **DONE+verified
> 2026-05-18** (Phase A). **Still open in FE-6:** further CRISPR polish —
> user-gated.

> **GV-005 + GV-006 — ✅ DONE + verified 2026-05-19 · Claude (user-directed).**
> Gene-viewer frontend per `plans/gene-viewer/{spec,plan}.md`, user-chosen
> hybrid adapter + Option-B layout (minimap = genomic; detail-pane
> Sequence|Protein switch; reference/variant allele toggle). New
> `lib/backend.ts` viewer mirror, `lib/api.ts` `getGeneViewer` (mock-first),
> `lib/workbench/{gene-viewer-sample,gene-viewer-adapter(+test)}.ts`,
> `components/workbench/viewer/ProteinView.tsx`; edited `WorkbenchShell`,
> `CanvasHeader`, `SequenceViewerV2`, `CodonDetail` (FE-5.6 Unit-E synthetic
> overlay superseded → adapter-driven allele basis), `styles/workbench.css`.
> ClinVar lollipops are **uniform size** (no frequency implication).
> Verified: vitest **73/73** (+20 adapter), build clean, contract **40/40**
> (viewer canary = Codex lane, filed in `agent_handoff/CURRENT.md` →
> Cross-Agent Requests, with the viewer-payload enrichment ask). Browser
> pixel-check passed (allele toggle flips c.260 A↔G / codon 87 Asp↔Gly;
> protein domain + lollipop @ aa87; minimap preserved; Primer below viewer).

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

### FE-14 — Search robustness states + `cleanQuery()`

The frontend half of the variant-search-engine integration (source plan:
`C:\Users\seamegdool\.claude\plans\before-you-beging-the-groovy-swan.md`). Pairs
with Codex's BE-8 (input normalization) and BE-12 (error contract). **No
`backend.ts` interface or contract change** — the schema is unchanged by design,
so `test_frontend_contract.py` stays 40/40. This milestone runs in parallel with
Codex BE-8…BE-13; file ownership is disjoint (`app/frontend/**` only).

**`cleanQuery()` (BE-8 frontend mirror, UX-only)** — add `cleanQuery()` to
`src/lib/variant-format.ts`, reusing the existing `classify()` / `FORMAT_HINTS`.
Call it before building the `LookupRequest`. Same intent as the backend
`normalize_variant_query`: strip a leading `GENE:`/`NM_`/`ENST` accession+colon,
collapse whitespace, **never lowercase HGVS** (`A>G`/`p.Asp87Gly` are
case-significant). This is a client-side affordance only — the backend
normalizes authoritatively; the mirror just gives instant feedback.

**Robustness states (BE-12 frontend half)** — in `src/pages/ReportPage.tsx` and
the lookup call site (the `variantLookup` function — confirm whether it lives in
`src/lib/api.ts` or `src/lib/backend.ts` at execution; the gitStatus shows
`backend.ts` is the live module). Three distinct states keyed off the **frozen
`warnings` codes** (see `plans/v2-backend.md` → "Frozen `warnings` codes" — the
canonical contract):

| Trigger | State | UI |
| ------- | ----- | -- |
| Client `classify() == 'unknown'` | malformed — no request sent | inline hint near the search box (reuse `FORMAT_HINTS`); never fires a request |
| `warnings` contains `input_unparseable:<kind>` | server-confirmed malformed | inline hint; surface `report_payload.limitations` |
| `warnings` contains `no_genomic_resolution` | resolved-but-no-data | "We couldn't resolve this variant" panel — visually **distinct** from a generic network failure; no auto-retry |
| network error / 5xx | transient | retry affordance; add **1 retry with backoff** in `variantLookup` (network/5xx only — **never** retry 4xx) |
| `warnings` contains `live_fetch_failed:` (prefix) | partial degradation | non-blocking "some sources used cached data" note; key on the **prefix only**, never parse the suffix (it's the exception class name, not the tool name — incoherence finding #6) |

**Verify**:

```bash
cd app/frontend && npm run build      # tsc -b + vite, clean
cd app/backend && python -m pytest tests/test_frontend_contract.py -q   # 40/40 (no contract touch)
```

Manual walkthrough: (1) paste `???not-a-variant???` → inline hint, no network
request; (2) paste `RPE65:c.260A>G` → cleaned to `c.260A>G` before the request;
(3) offline / kill backend → retry affordance, exactly one auto-retry with
backoff on the network failure, no retry on a 4xx.

**Acceptance** — the three states are visually distinct (malformed ≠
no-resolution ≠ network); `cleanQuery()` strips the `GENE:` prefix without
lowercasing HGVS; `npm run build` clean; contract test still 40/40.

---

## Tasks deferred to M-002 (post-v2)

- Real engine calls (Primer3 / CRISPOR / Needleman–Wunsch / AB1 parser). Sample data for v2.
- Multi-variant editing in the sequence viewer (one edit at a time tracked; multiple edits land sequentially).
- Dynamic downstream consequence rendering (FE-5.6 item 8, deferred half): indel-aware spliced-CDS re-translation — frameshift re-frames all downstream codons, recomputes the new premature/late stop, renders the truncated/extended protein. Distinct from the current per-codon-independent recompute; needs a new pure translation/frame-propagation module + viewer rework.
- Persist Workbench sessions (no persistence layer in v2; reload = reset).
- Real PhyloP + UniProt domain ingestion (currently sample-rpe65.ts hardcoded).
- Mouse mm39 support in Workbench (Sequence Viewer + tools assume human; mouse comes later).

---

## Out of scope

- Auth, billing, accounts, analytics
- Bulk VCF analysis pipeline
- Migrating Layer 2 (`/runs`) to v2 styling — it stays frozen on the old design system
- Migrating to Next.js
