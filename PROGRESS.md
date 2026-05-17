# Eamos Genomic Report Tool — Build Progress

## Session 19 — 17 May 2026 — FE-5.5 pixel-check → FE-5.6 plan; direct-Codex workflow sync

Browser pixel-checked FE-5.5 (first non-headless look). 8 refinements captured
as new milestone **FE-5.6** in `plans/v2-frontend.md`, design decisions locked
with the user (dynamic reflow; unified edit-hub redesign; variant-render
small-now/defer-cascade). **No app code changed.** Separately: direct Codex app
access verified (full `E:\eamos` workspace read/write/delete + outbound
network); `agent_handoff/` created (Codex) as the live cross-agent coordination
folder, superseding the "Codex = grunt-work-only / plugin-limited / can't run
vitest" assumption — now historical, a property of the old plugin-mediated
path, not direct Codex. Stable-doc workflow sync applied: `CLAUDE.md`
(new "Direct Codex vs. plugin delegation" subsection), `plans/README.md`,
`README.md`, `ROADMAP.md` blockers row, this note; the two related memory
notes corrected. **Nothing committed.** Next: FE-5.6 (Claude) or a scoped
backend task (direct Codex). Detail: `agent_handoff/CURRENT.md`,
`plans/v2-frontend.md` "FE-5.6", `~/.claude/plans/next-session-eamos.md`.

## Session 18 — 16 May 2026 — FE-5.5 Sequence Viewer v2 (Benchling-grade) + chrome relayout

At the backend-first checkpoint the user redirected to the Workbench sequence
viewer. Reviewed the refreshed `Eamos Workbench v2.html` mock + Benchling/
SnapGene competition shots, gave a UI/UX opinion, and integrated 4 requested
changes as new milestone FE-5.5 (confirmed: augment-zoom + full v2 port).
Ported the v2 viewer to React (data model + 9 viewer components + chrome
relayout): gene minimap, exon strip, find/jump toolbar, ClinVar chevrons,
undo/redo + history, strand pill, export, wrapped 60-bp codon detail. 4 mods
landed: ClinVar density toggle, collapsible exon disclosure, horizontal
top-right tool selector (left rail removed), Benchling −/+ zoom slider
alongside semantic chips. 14 superseded FE-5 files deleted. Verified: vitest
24/24, build clean, contract 40/40 (pure FE, untouched). Then a Codex
adversarial hardening pass (`task-mp8d61ip-1zyj8k`) fixed 2 HIGH / 2 MED / 3
LOW (drag-unmount leak, popover portal/clamp, history-jump bounds, data-driven
intronic ClinVar mapping, a11y, keys, stale CSS comment); Claude re-verified
post-Codex (24/24, clean, 40/40). **Nothing committed.** Next: FE-6
(Primer/CRISPR) builds on the new chrome, or resume the backend-first M-002
track. Full detail: CHANGELOG.md Session 18.

## Session 17 — 16 May 2026 — Whole-project review → deepthink → hardening Session 1

Codex ran a whole-project adversarial-review (2 CRITICAL auth gaps, 3 HIGH, 4
MED, 4 LOW + ranked recs). deepthink (confidence CERTAIN) produced a
risk-ordered, Claude/Codex-lane-split, sessionized hardening plan. Session 1
executed: Claude fixed H1 (/report?q demo leak), M4 (dead AI button), L1
(hardcoded card meta), L2 (inert settings button), L4 (stale plan doc) —
vitest 21/21, build clean; Codex dispatched in parallel for C1/C2 auth on the
unauthenticated patient routes (+ authed test fixture + 7 test migrations +
401 test). ROADMAP.md rewritten to true state + the session plan. Resumable
handoff: `~/.claude/plans/next-session-eamos-hardening.md`. **Nothing
committed.** Remaining: Session 2 backend correctness batch → FE-6/7/8 →
M-002. Full detail: CHANGELOG.md Session 17.

## Session 16 — 16 May 2026 — Variant-search-engine: full-project cross-check + live fixes

BE-8…BE-13 + FE-14 **live-verified** (not just offline). Bidirectional
full-project audit (Claude→backend, Codex→frontend); consolidated findings
approved before any edits. Fixed: PubMed query too narrow (0→10 live articles),
LitVar2 query-by-rsID + `pmids`/`pmids_count` parse, cache-poison guard
(upsert only on resolved coords), `publications_callout.total_count` fallback
when LitVar2=0, and the frontend `coord` guard wrongly blocking VCF-quad
genomic input. Also fixed 3 workbench items (URL/data mismatch, scratchpad
drift, base-editor a11y). **Offline 80 passed / 4 skipped, contract 40/40;
vitest 21/21; Claude-run live smoke all Phase-C assertions green.** Nothing
committed. Full detail in CHANGELOG.md Session 16. Plan rows flipped to ✅ in
`plans/v2-backend.md` (BE-8…13) and `plans/v2-frontend.md` (FE-14).

## Status: Prototype v1 complete (widget demo)

## What's been built
- Landing page (two upload zones + Load Demo button)
- Processing animation (step-by-step progress)
- Full report for 5 IRD variants:
  - RPE65 p.Asp87Gly (VUS) — PRIMARY, Luxturna eligible
  - USH2A p.Glu767Serfs*21 (Likely Pathogenic)
  - ABCA4 p.Gly1961Glu (Likely Pathogenic)
  - RPGR c.2405+1G>A (Likely Pathogenic, X-linked)
  - CNGA3 p.Arg436Trp (VUS)

## Report sections implemented (all 11)
1. Classification badge + bottom line (AI-generated)
2. Clinical context — ERG, OCT, fundoscopy, pedigree (expandable images)
3. AI clinical summary (API-generated)
4. Classification snapshot — ACMG criteria, REVEL, CADD, SpliceAI, Franklin, gnomAD
5. Clinical integration — gene→protein→function→clinical (AI-generated, 4 bullets)
6. Gene/disease phenotype table + gene function
7. Gene therapy flag (Luxturna auto-surfaced for RPE65; dev pipeline for others)
8. Clinical trials (mock ClinicalTrials.gov data per gene)
9. Recommendations — tiered HIGH / MODERATE / ROUTINE with ACMG impact
10. Limitations — checkbox list
11. Clinician sign-off — name, date, status dropdown, version stamp

## Key design decisions
- Gene-agnostic: all logic driven by variant data, not hardcoded for RPE65
- Anthropic API called per variant for: bottomLine, summary, clinicalIntegration
- Fallback content if API fails
- ERG waveform SVG (normal vs patient)
- Pedigree SVG (4-generation, consanguinity shown)
- Classification colours: red=Pathogenic, amber=VUS, green=Benign
- Variant switcher tabs at top of report

## Session 4 task list (08 May 2026)
1. [x] Fix DNA notation to lead — variant table and sidebar now show transcript_hgvs
       primary, protein_change smaller/muted below (App.tsx buildVariantRows)
2. [x] Plain language variant decoder — backend + frontend complete (see Session 4 notes)
3. [x] Backend tool parameterisation — all four tools now gene-agnostic (see below)
4. [ ] Set use_real_apis = True and test with a real variant — blocked on IT (Node.js/Python network)
5. [ ] Wire frontend to real backend

## Session 4 — what was done (08 May 2026)

### Environment
- Project canonical location moved from D: (FAT32, full) to e:\eamos (NTFS, 12 GB free) (renamed from E:\HSIL-2026 after Session 5, commit d1060c0)
- E: drive reformatted from FAT32 to NTFS to support node_modules
- Node.js v22.15.0 portable at C:\temp\node\node-v22.15.0-win-x64 (IT permission pending for
  full network access — dev server starts but can't bind due to corporate network policy)
- Python 3.10.11 installed via company portal at C:\Program Files\Python310\
  pyproject.toml relaxed from >=3.11 to >=3.10 (no 3.11 syntax used anywhere)
- All backend dependencies installed: pip install -r requirements.txt ✓
- Private GitHub repo created: https://github.com/steveneam/eamos-dev
  Pushed via GitHub REST API (git not installed, github.com downloads blocked by IT)

### Task 1 — DNA notation fix (frontend, App.tsx)
File: app/frontend/src/App.tsx
- buildVariantRows() now returns variantDna + variantProtein separately
  instead of a single joined string
- variantDna = transcript_hgvs (falls back to consequence)
- variantProtein = protein_change, nullable — only renders if present
- Applied in 3 places: desktop table, mobile table, sidebar variant card
- Visual confirmation pending IT network clearance for Node.js dev server

### Task 3 — Backend tool parameterisation
All four tools now accept variant=None and use gene-agnostic input.
Fallback to fixture data preserved when variant=None or use_real_apis=False.

**clinvar.py** — removed CLINVAR_ID = "1421454"
  Now does two-step live fetch:
  1. esearch: GENE:c.cdna → resolves to ClinVar variation ID
  2. esummary: fetches classification, conditions, review status for that ID

**ensembl_vep.py** — removed HGVS = "NM_000329.3:c.260A>G" and hardcoded RPE65 filter
  Uses variant.transcript_hgvs directly.
  Gene filter now uses variant.gene with safe fallback to consequences[0].

**spliceai.py** — removed VARIANT = "chr1-68444869-T-C" (hardcoded genomic coords)
  Constructs GENE:c.cdna from variant.gene + extract_cdna(variant.transcript_hgvs).
  Note: SpliceAI REST endpoint accepting GENE:c.cdna format not yet live-tested —
  confirm when use_real_apis=True test is run.

**franklin.py** — removed SEARCH_TEXT = "RPE65:c.260A>G"
  Constructs GENE:c.cdna identically. Both parse_search and snp search use it.

**workflow.py** — variant collection moved before tool calls
  primary_variant = reports[0].extracted_case.variants[0] (with None guard)
  All tools called as tool.get_evidence(variant=primary_variant)

### Task 2 — Plain language variant decoder (also session 4)
New file: app/services/variant_decoder.py
- decode_variant(gene, transcript_hgvs, protein_change) → plain English string
- Pure regex/template — no LLM call, deterministic, works offline
- Handles 7 cdna notation types: substitution, single/multi-base deletion,
  insertion, duplication, splice site (both +/- offset directions)
- Handles 3 protein notation types: frameshift (fs*), missense, splice
- cdna notation tried first; protein fallback if no cdna match
- All five demo variants tested and produce correct output

app/schemas/run.py — variant_decoder: str | None added to ReportPayload
app/services/workflow.py — decode_variant() called for primary variant row,
  result stored in base_payload.variant_decoder
app/frontend/src/lib/backend.ts — variant_decoder?: string | null added
app/frontend/src/App.tsx — "What this variant means" callout block rendered
  between the executive summary and the variant table, only when field is non-null

### What's next (priority order for next session)
1. Set use_real_apis = True and run a live test (needs IT network clearance for Node.js/Python)
2. Wire frontend to real backend (replace mock data with live API responses)
3. Rotate GitHub PAT — current token was shared in chat session

## Session 15 — 15 May 2026 (continued)

### FE-5 — Sequence Viewer + click-to-edit

All-new frontend, zero backend-contract surface. Ported `e:\Web tool\Claude Design\Workbench\{data.js,sequence-viewer.js,side.js}` (viewer slice) to declarative React/TS.

**What landed:**

| Area | Files |
| ---- | ----- |
| Testable core | `src/lib/workbench/codon-table.ts` (`codonTable`/`aaThree`/`aaClass`/`translate`/`consequenceOf` — `consequenceOf` parameterised, not `this`-bound, for purity) + `src/lib/workbench/sample-rpe65.ts` (typed `WorkbenchSample`). |
| Viewer components | `src/components/workbench/viewer/`: `SequenceViewer`, `Track`, `BaseRow`, `CodonRow`, `AnnotationRow`, `DomainRow`, `VariantRow`, `ConservationRow`, `RestrictionRow`, `VariantMarker`, `EditPopover` (portalled to `<body>`, hover-preview + click-select). |
| Wiring | `WorkbenchShell` now owns `edits`/`scratch`/`tracksOn` + `applyEdit`/`resetEdit`/`resetAll`; `CanvasHeader` converted from uncontrolled `defaultChecked` to controlled (exports `TrackKey`/`DEFAULT_TRACKS_ON`); `SidePanel` gained the viewer branch (active-variant kv-list + scratchpad with count/Reset + reading guide), other tools keep the FE-4 placeholder for FE-6/7. |
| Tests | `vitest@^3` added as devDep + `"test": "vitest run"` script; `src/lib/workbench/codon-table.test.ts` (5 tests: GAC invariant guard, translate, missense p.Asp87Gly, frameshift on del, synonymous wobble). |

**Verified:** `cd app/frontend && npm run build` green (tsc -b + vite); `npm run test` → **5/5 PASS**; `cd app/backend && python -m pytest tests/test_frontend_contract.py -q` → **40/40 PASS** (no contract change). Browser pixel-fidelity check not possible in this environment — worth a visual pass next session (all CSS already present from FE-4's `workbench.css`).

**Deviations / flags for review:**

1. **Sample-data coherence fix (1 char).** The source `data.js` `sequence` had window index 28 = `C`, making codon 87 = `GCC` (Ala) — a verbatim `consequenceOf` would yield `p.Ala87Gly`, contradicting the plan's acceptance criterion *and* every other surface in Eamos (ContextStrip, report fixtures use `p.Asp87Gly`). The mock's own comments show the author was unsure about the indexing. Resolution: index 28 `C`→`A` so codon 87 = `GAC` (Asp); the verbatim algorithm then yields the spec-mandated `p.Asp87Gly`. No other base altered. Guarded by a Vitest assertion. Other ClinVar tooltip `hgvsP` labels in the mock have similar internal mismatches (e.g. c.257 p.Ala86Gly vs codon 86 = GTC) — left as-is (display-only, out of FE-5 scope, not computed by `consequenceOf`).
2. **Hover preview added to EditPopover.** Plan FE-5 UX + acceptance say "hover each button → live consequence preview"; the source `sequence-viewer.js` only previews on click. Implemented both: hover previews (non-committing), click selects, Apply commits. Faithful to source behavior + satisfies the stated acceptance.
3. **Marker rendering.** Source adds a `.sv-marker` to every `.sv-track-body` (stacked segments read as one line) with the flag on the first body — replicated faithfully via `<VariantMarker>` inside each `<Track>` rather than a single overlay (avoids the 110px label-column offset problem).

### What's next

FE-6 (Primer + CRISPR panels — BE-7 fixtures exist) → FE-7 (Alignment + Comparator) → FE-8 (AskEamos pill). Resume pointer in `plans/v2-frontend.md`.

---

## Session 14 — 15 May 2026 (continued)

### Parallel cycle 2: FE-3.5 closed, BE-6/BE-7 (Codex), FE-4 Workbench shell, FE-3.6 fidelity reconcile

Second parallel-execution cycle. Codex (`/codex:rescue --background`, agent `a862070de2d41f104`) ran `app/backend/` BE-6→BE-7 while Claude Code ran `app/frontend/` FE-4 then FE-3.6. No file overlap; `test_frontend_contract.py` was the sync canary.

#### Frontend (Claude Code)

| ID | What landed |
| -- | ----------- |
| FE-3.5 | Closed (was open from Session 13). The 6 report v2 components wired to `payload.*` with internal display interfaces renamed to avoid `backend.ts` name collisions. Surfaced that the backend fixture carried less than the mock → motivated BE-6/FE-3.6. |
| FE-4 | Workbench shell. New `/workbench` route in `App.tsx`. New components under `src/components/workbench/`: `tools.tsx` (TOOL_ORDER/TOOL_META/ToolIcon), `ToolRail`, `CanvasHeader`, `SidePanel`, `ContextStrip`, `WorkbenchShell`; new `src/pages/WorkbenchPage.tsx` (nav + ctx strip + shell, tool state, query-param seed). Mock CSS ported to `src/styles/workbench.css` via transform script: global resets + duplicate `:root` dropped, width vars remapped to FE-0 `--maxw-workbench*`, `.badge`→`.ctx-badge` (the one collision with `index.css`), 8 missing tokens added (`--line-3,--err,--err-tint,--r-sm/md/lg,--nav-h,--ctx-h`). Tool switching changes rail/header/side; viewer collapses for align/compare; responsive handled by ported media queries. **Plan deviation:** no-param `/workbench` defaults to the RPE65 sample instead of redirecting to `/` (v2 only serves RPE65; matches ReportPage demo behavior). |
| FE-3.6 | Report payload fidelity reconcile. `backend.ts` gained the 8 BE-6 field groups (all optional): `NearbyVariant.protein_change`; `CodonCell.{aa_alt,dna_ref,dna_alt}`; `LocusContext.coords`; `PredictorCard.verdict_label`; `AcmgCriteriaScaffold.{intro,note}`; `CuratedVariantsDistribution.{row_totals,subtitle}`; `AssociatedCondition.{db_tag,db_tag_bold,source_list}`; `PublicationsCallout.blurb`. `sample-report.ts` `RPE65_SAMPLE` v2 modules rewritten to mirror the new fixture. All 6 report components rewritten to consume the enriched payload and **the divergent SAMPLE datasets deleted** (replaced with compact empty-state lines when `data` is absent). |

Verified: `cd app/frontend && npm run build` green (tsc -b + vite, ~3.8s, 589KB JS); `cd app/backend && python -m pytest tests/test_frontend_contract.py -q` → **40/40 PASS** (BE-6 ↔ FE-3.6 drift resolved — the Session 13 known failure is now closed). Browser pixel-fidelity check not possible in this environment.

#### Backend (Codex — BE-6, BE-7)

| ID | What landed |
| -- | ----------- |
| BE-6 | Additive schema fields on `run.py` (no renames/drops): `LocusContext.coords`, `NearbyVariant.protein_change`, `CodonCell.{dna_ref,dna_alt,aa_alt}`, `PredictorCard.verdict_label`, `AcmgCriteriaScaffold.{intro,note}`, `CuratedVariantsDistribution.{row_totals,subtitle}`, `AssociatedCondition.{db_tag,db_tag_bold,source_list}`, `PublicationsCallout.blurb`. `lookup_v2_modules.json` fully rewritten to mirror the 6 frontend SAMPLE constants (11 nearby variants, 11 codon cells with DNA + Asp→Gly, descriptive predictor verdicts, ACMG intro/note, per-row distribution totals, 5 conditions, blurb). `test_frontend_contract.py` extended for all 8 field groups. |
| BE-7 | Workbench fixtures tightened to mock-JS values: `primer_rpe65.json` note text, `crispr_rpe65.json` guide cut positions/scores, `align_rpe65.json` match line + mismatch position + Q-scores. |

**Codex ambiguities surfaced (open for your review):** (1) CRISPR mock shows 6 guides with per-guide `recommended`/`cas`; kept to 3 guides, schema-less fields not added. (2) CRISPR HDR efficiency `12–18%` range → stored midpoint `0.15`. (3) Alignment mock highlights mismatch at index 13 but strings diverge at 14 → fixture uses consistent position 14.

#### What's next

FE-5 (Sequence Viewer + click-to-edit + `codon-table.ts` Vitest) → FE-6 (Primer + CRISPR panels) → FE-7 (Alignment + Comparator) → FE-8 (AskEamos pill). All are all-new frontend files with no backend contract dependency (BE-7 fixtures already exist). Resume pointers in `plans/v2-frontend.md`.

---

## Session 13 — 15 May 2026

### v2 rebuild implementation (frontend FE-0..FE-3, backend BE-1..BE-5)

Parallel execution: Claude Code on `app/frontend/`, Codex (via `openai/codex-plugin-cc` plugin, `/codex:rescue` route, `--write` flag) on `app/backend/`. Same git working tree, same filesystem, same ChatGPT auth. Codex completed BE-1..BE-5 in 22m 6s.

#### Frontend (Claude Code)

| ID | What landed |
| -- | ----------- |
| FE-0 | `index.css` gained `--bg-canvas`, sequence palette (`--base-A/T/C/G`), AA biochem palette (`--aa-hydro/polar/acid/basic/aroma/cys/stop`), width helpers (`--maxw-report/nav/landing/workbench`), `.hairline` + `.hairline-{b,t,l,r}` utilities. `ModePill` component created (Report ⇄ Workbench segmented pill, `?query` preserved). Wired into ReportPage TopNav. **Also fixed pre-existing tsconfig gap:** `tsconfig.app.json` was missing `"paths": { "@/*": ["./src/*"] }`, so every `@/`-aliased import was failing under `tsc -b`. Build was broken before this fix; clean now. |
| FE-1 | Franklin removed from active frontend surfaces: `sources.ts`, `sample-report.ts`, `FeaturesGrid`, `HowItWorks`, `LandingPage`. Replaced with AlphaMissense where a 6th database was named. `LegacyRunsApp.tsx` (frozen `/runs` surface) deliberately untouched. |
| FE-2 | Six new report v2 components in `src/components/report/`: `LocusContext`, `InSilicoGrid`, `AcmgCriteriaFold`, `CuratedVariantsGrid`, `AssociatedConditions`, `PublicationsCallout`. ~180 lines of v2 module CSS appended to `index.css` (`.locus-*`, `.pred-*`, `.fold`, `.acmg-*`, `.vardist-*`, `.cond*`, `.pubs-*`). Wired into 3 outer Cards in `ReportPage.tsx` (Card 2 Locus context, Card 3 Evidence by source with InSilicoGrid + EvidenceTable + AcmgCriteriaFold, Card 4 Gene context with DiseaseSection + CuratedVariantsGrid + AssociatedConditions + PublicationsCallout). `EvidenceTable` and `DiseaseSection` gained an `embedded` prop so they don't double-wrap. Each new module carries hard-coded `SAMPLE` blocks until FE-3.5 swaps to payload data. |
| FE-3 | `VariantHeader.tsx` rewritten with the v2 utility row: cross-DB chip strip (ClinVar / gnomAD / UCSC / Ensembl / OMIM / AlphaFold — **no Franklin, no "Compare elsewhere ↗" chip**), URLs constructed from `OMIM_BY_GENE` / `UNIPROT_BY_GENE` / `ENSEMBL_BY_GENE` tables. Tools row (Follow toggles state, Export PDF calls `window.print()`, Share copies URL to clipboard). 4-stat row (ClinVar / gnomAD AF / REVEL / AlphaMissense) — sample values until payload provides them. v2 variant-header CSS appended to `index.css`. |

Build verified clean at the end of each milestone: `tsc -b && vite build` → final state 573KB JS / 58KB CSS, 2.25s.

#### Backend (Codex)

| ID | What landed |
| -- | ----------- |
| BE-1 | Franklin archived to `archive/franklin/`. Removed from `app/tools/registry.py`, `app/services/workflow.py`, `app/services/lookup_service.py`, `app/rules/clinic_rules.py`, `app/core/config.py`, `.env.example`, and the relevant tests. Verification: `rg -n franklin app` (and `Franklin`) under `app/backend/` returns no matches. |
| BE-2 | `ReportPayload` extended with six new optional fields: `locus_context`, `in_silico_predictions`, `acmg_criteria_scaffold`, `curated_variants_distribution`, `associated_conditions`, `publications_callout`. New Pydantic models: `NearbyVariant`, `CodonCell`, `LocusContext`, `PredictorCard`, `InSilicoPredictions`, `AcmgCriterion`, `AcmgCriteriaScaffold`, `CuratedVariantsDistribution`, `AssociatedCondition`, `PublicationsCallout`. RPE65 fixture at `app/backend/app/fixtures/lookup_v2_modules.json` (5 nearby variants, 11 codon cells, 4 predictor cards, 28 ACMG criteria, 3×4 distribution matrix, 2 conditions, 816 publications). Lookup service wired to attach the fixture entry by `(gene, cdna)` key. |
| BE-3 | `POST /api/v1/chat` + `POST /api/v1/chat/stream`. Mock-mode returns variant-aware response mentioning the gene from `variant_context.variant_summary_rows[0]`. Live-mode wrapped via `ChatService` in `app/services/chat_service.py`. Run-scoped `POST /api/v1/runs/{run_id}/chat/stream` left unchanged. |
| BE-4 | `POST /api/v1/primer | /crispr | /align` returning fixture responses keyed by variant. 3 primer pairs (pair 1 ★ recommended), 3 gRNAs + ssODN block, alignment with 4 trace channels × 80 samples. Real engines (Primer3, CRISPOR, Needleman–Wunsch, biopython AB1) deferred to M-002. |
| BE-5 | New `tests/test_franklin_removed.py` enforces no `franklin` imports remain. `test_frontend_contract.py` extended to cover all new schemas. Final pytest: **36 passed, 4 skipped**. One known failure: `test_frontend_contract.py` itself — waiting on frontend (FE-3.5) to add the matching TypeScript interfaces. That's the planned sync point. |

Codex session id `019e26bf-c0db-7b03-aff3-a5303bac4eed` is resumable for follow-ups.

#### Open: FE-3.5 contract sync (next session)

Full plan section in `plans/v2-frontend.md` under "FE-3.5 — Contract sync". Summary: add ~25 TypeScript interfaces to `app/frontend/src/lib/backend.ts` matching the new Pydantic models, populate `sample-report.ts` from `lookup_v2_modules.json`, swap the 6 report v2 components from hard-coded `SAMPLE` blocks to payload-driven props. Estimated ~45 minutes. Closes the loop on `test_frontend_contract.py`.

---

## Session 12 — 14 May 2026

### v2 rebuild planned; Franklin archived from product

**Context:** Three new Claude Design mocks (`Eamos Landing Page.html`, `Eamos Report Page v2.html`, `Eamos Workbench v1.html`) iterate Eamos into two surfaces. The variant report v2 folds in Franklin-derived modules (cross-DB strip, locus context / region viewer, in-silico predictions deep-dive, ACMG criteria scaffolding, curated variants distribution, structured associated conditions, publications callout). The new Workbench surface adds sequence viewing with click-to-edit consequence prediction, Primer / CRISPR / Alignment (with AB1 chromatogram) / Comparator tools, and a tool-aware AskEamos floating pill.

Franklin (Genoox) is a competitor and is being removed from the active product surface.

### Plans written

- `plans/README.md` — parallel-work coordination doc explaining how Claude Code (frontend) and Codex (backend) run on the same branch against a shared TypeScript ↔ Pydantic contract.
- `plans/v2-frontend.md` — 9 milestones (FE-0 foundation through FE-8 AskEamos pill). Built on existing Phase 0–2 scaffolding; React/Vite preserved.
- `plans/v2-backend.md` — Codex-consumable brief, 5 milestones (BE-1 Franklin archive through BE-5 test sweep). Self-contained — every path, schema, and verification step included.

### Doc updates this session

- `CHANGELOG.md` — new entry summarising the rebuild plan and locked decisions.
- `DESIGN.md` — full rewrite around v2 tokens (Syne/Plus Jakarta Sans/JetBrains Mono, ink scale, sequence palette, AA biochem palette, 920/1180/1440 widths, Workbench layout chrome). Legacy `/runs` surface preserved as frozen appendix.
- `README.md` — Franklin dropped from Database Stack. Report Structure refreshed to v2 sections. Workbench surface added to Architecture.
- `ROADMAP.md` — Layer 1 v1 marked done. Layer 1 v2 + Workbench added as active phases. Layer 2 marked frozen at `/runs`.

### Decisions locked in

1. Stack: keep React + Vite. Next.js migration deferred.
2. Layer 2 patient report at `/runs` stays frozen (no design changes, no new features).
3. Workbench delivered all-at-once with sample data; real engines deferred to M-002.
4. Franklin: archive to `archive/franklin/` (preserve history, remove from active code).
5. v2 mock's `franklin.genoox.com` "Compare elsewhere ↗" chip dropped — we don't link to competitors.

### What's next

- Claude Code starts FE-0 (token additions, hairline utility, Workbench/canvas/AA palette additions).
- Codex picks up `plans/v2-backend.md` starting with BE-1 (Franklin archive).
- Sync point after each milestone: `cd app/backend && python -m pytest tests/ -q` clean + `cd app/frontend && npm run build` clean.

---

## Session 11 — 14 May 2026

### Environment update
- Node.js now has outbound network access (IT blocker resolved). Dev server and npm installs work without restriction.
- Python network access: re-verify `USE_REAL_APIS=true` pipeline with a real variant (next session).

### AlphaMissense — removed from product
- Decided against building AlphaMissense tool. Removed from ROADMAP and deleted `plans/alphamissense-tool.md`.

### Code quality pass (codebase analysis → refactor)
Ran 4-agent parallel codebase analysis. Issues found and fixed:

1. **Naming/branding** — `app_name = "hsil-demo-backend"` → `"eamos-backend"` in `config.py`; log message in `main.py` updated to `"Eamos backend ready"`.
2. **Unused config fields removed** — `search_default_limit`, `langchain_api_key`, `langchain_tracing_v2` deleted from `Settings` class.
3. **gnomad.py late import** — `import httpx` moved from inside `_fetch_live()` to module level, consistent with all other tools.
4. **franklin.py fallback URL** — Exception fallback now builds the specific variant URL (`gene-hgvs` form) the same way the fixture branch does, instead of falling back to bare homepage.
5. **workflow.py dead wire** — `_build_source_filenames()` output was collected but hardcoded to `[]` in the ReportPayload. Now passed through and stored correctly. Also removed redundant second call to the helper inside `_build_report_payload`.
6. **npm prune** — Extraneous transitive packages cleaned from `app/frontend/node_modules`.

### Issues noted but not changed (intentional)
- Duplication between `lookup_service.py` and `workflow.py` (therapy, clinical integration, evidence snapshot) — pre-existing intentional design.
- `case_label`, `expected_symptoms` in ReportPayload always `None` — future fields, not dead code.
- `_extract_cdna()` duplicated across 5 tool files — simple 4-liner, no shared utility added (surgical changes rule).
- `ai_generated_sections` inconsistency between services — Layer 2 concern only.

---

## Session 10 task list (10 May 2026)

1. [x] Solatis workflow dry run — validated explore → deepthink → plan pipeline end-to-end
2. [x] Discovered: ClinicalTrials.gov + Therapeutic Landscape already fully implemented
3. [x] Codebase analysis mapped tool/service/schema architecture across 4 parallel agents

### What's next
- Code quality pass: codebase analysis → refactor for consistency (session 11)

---

## Session 5 task list (09 May 2026)
1. [x] JWT secret hardening — `config.py` `jwt_secret` now required, no default
2. [x] `franklin.py` dead-code typo removed (`canonical_tanscript`)
3. [x] Backend README rewritten (architecture diagram, actual routes, setup)
4. [x] `CLAUDE.md` created at `e:\eamos` (was missing from E: drive copy)
5. [x] PubMed tool — `pubmed.py`, fixture, registry, schema, workflow wired
6. [x] Frontend publications section — 3 shown default, "Show N more", gene PubMed link
7. [x] Species selector — pill toggle in submit bar, Mouse disabled with "soon" badge
8. [ ] Visual smoke test — servers started session 6; verify species selector + publications in browser
9. [ ] Live API test — `USE_REAL_APIS=true` test with `RPE65:c.260A>G` (pending IT clearance)

## Next steps (priority order — original list)
1. [ ] Export to actual file (HTML) so dev team can use it
2. [ ] Improve two-input flow — show extracted data before generating report
3. [ ] Add OCT visual (simplified SVG)
4. [ ] Refine AI prompts for better clinical prose
5. [ ] Add similar cases / evidence anchor section
6. [ ] Delta classification tracking
7. [ ] Print/PDF export styling

## Codebase location
e:\eamos  ← canonical working copy (moved here 08 May 2026, D: was full/FAT32)
- Backend: FastAPI + Python
- Frontend: React + TypeScript (e:\eamos\app\frontend)
- Node.js portable: C:\temp\node\node-v22.15.0-win-x64
- Dev server: npm run dev → http://localhost:5173
- Agents: ClinVar, VEP, SpliceAI, Franklin API calls

## Session 3 — 07 May 2026 (continued)

### Backend deep-read findings

#### What was actually built in the hackathon
- Full pipeline architecture is solid: intake → tools → rules → draft → review
- LLM: OpenAI GPT-4o-mini via LangChain (not Anthropic). Frontend prototype
  uses Anthropic API directly — fine for demo, needs aligning when we wire together
- Default mode: use_real_apis = False — tools return fixture JSON, live API calls
  were written but never actually ran during the hackathon demo

#### Every tool is hardcoded to RPE65 p.Asp87Gly
- ClinvarTool: CLINVAR_ID = "1421454" (hardcoded)
- SpliceAiTool: VARIANT = "chr1-68444869-T-C" (hardcoded genomic coords)
- FranklinTool: SEARCH_TEXT = "RPE65:c.260A>G" (hardcoded)
- EnsemblVepTool: almost certainly same pattern
- Rules engine (clinic_rules.py) and draft prompts are already gene-agnostic ✓

#### What each API actually needs (for any gene/variant)
- ClinVar: numeric variation ID — need esearch step first to resolve
  HGVS → ClinVar ID, then esummary fetch. Two calls per variant.
  Base URL: https://eutils.ncbi.nlm.nih.gov/entrez/eutils
- SpliceAI: genomic coords in chr{n}-{pos}-{ref}-{alt} format (hg38).
  VEP response provides these as a byproduct — run VEP first.
  Base URL: https://spliceai-38-xwkwwwxdwq-uc.a.run.app/spliceai/
- Franklin: already uses GENE:c.cdna format (good). Needs auth —
  either franklin_api_token in env or email/password login for bearer token.
  Base URLs: https://api.genoox.com + https://franklin.genoox.com
- VEP (Ensembl): cleanest — accepts HGVS directly (NM_000329.3:c.260A>G).
  Returns genomic coords as byproduct. Run this first.
  Base URL: https://rest.ensembl.org

#### Order of operations for gene-agnostic pipeline
1. VEP first — accepts HGVS, returns genomic coords + consequence
2. SpliceAI — use coords from VEP response
3. ClinVar — esearch to get ID, then esummary
4. Franklin — dynamic SEARCH_TEXT from input variant, same auth flow

#### What needs changing (next session)
- Remove hardcoded constants from each tool class
- Make tools accept variant params at call time (not hardcoded)
- WorkflowService needs to pass variant into each tool call
- Rules engine and drafting: no changes needed
- Frontend: replace mock data with real API responses

#### Files to modify next session
- app/tools/clinvar.py — remove CLINVAR_ID, add esearch step
- app/tools/spliceai.py — remove VARIANT, accept coords from VEP
- app/tools/ensembl_vep.py — remove hardcoded HGVS, accept as param
- app/tools/franklin.py — remove SEARCH_TEXT constant, accept as param
- app/services/workflow.py — pass variant into tool calls
- app/core/config.py — set use_real_apis = True when ready to test


### Feature queued: Plain language variant decoder

**What:** A plain language explanation of what the variant notation means,
auto-generated and placed near the top of both the patient report and the
lookup tool. Sits between the classification badge and the first technical
section.

**Why:** Clinicians working adjacent to genetics (ophthalmologists,
neurologists, general geneticists) don't live and breathe HGVS notation
daily. Decoding it automatically removes friction and makes the report
readable to a broader clinical audience. Also useful in the search/lookup
tool for quick orientation.

**Notation types to handle:**
- c.353G>A — substitution (one base swapped, missense or synonymous)
- c.2299delG — single base deletion (frameshift)
- c.123_125del — multi-base deletion
- c.123_124insATCG — insertion
- c.123dupA — duplication
- c.2405+1G>A — splice site (intronic, after coding position)
- c.2405-3C>T — splice site (intronic, before next exon)
- p.Glu767Serfs*21 — frameshift with stop position
- p.Arg436Trp — missense (amino acid change)
- p.(splice) — predicted splice disruption, protein unknown

**Output format:** One short paragraph, plain English, no jargon.
Auto-detects notation type from the cdna/protein fields already in
the variant data. Generated by AI layer with a dedicated prompt.

**Example output for RPE65:c.353G>A:**
"In the RPE65 gene, a single DNA letter was swapped at position 353 —
a G changed to an A. This one-letter change alters a single amino acid
in the protein, which may affect how well it functions. The protein is
still produced but carries this change at that position."

**Example output for USH2A p.Glu767Serfs*21:**
"In the USH2A gene, a single DNA letter was deleted near position 767.
Because DNA is read in groups of three letters, removing one letter
shifts the entire reading frame. The protein is built incorrectly for
21 amino acids after that point, then hits an early stop signal —
almost certainly producing a shortened, non-functional protein."

**Example output for RPGR c.2405+1G>A:**
"In the RPGR gene, a DNA letter changed at a splice site — the signal
that tells the cell where to cut and join sections of the genetic
message. This sits 1 position into the intron after coding position
2405. Disrupting this signal likely causes the wrong sections to be
included when the protein is assembled, producing a faulty or absent
RPGR protein."

**Implementation:** Small dedicated function that parses the cdna string
with regex to detect notation type, then calls AI with a short prompt
specifying which type was detected and what the values are.
Cache result per variant — only call once.


### Critical simplification — all databases accept GENE:c.cdna format

**Discovery:** SpliceAI lookup tool accepts RPE65:c.353G>A directly
(confirmed by manual test). This means every database uses the same
input format — no coordinate conversion, no dependency ordering needed.

**Universal input format:** GENE:c.cdna
- ClinVar:  RPE65:c.353G>A ✓
- SpliceAI: RPE65:c.353G>A ✓
- Franklin: RPE65:c.353G>A ✓
- VEP:      NM_000329.2:c.353G>A (transcript variant, same principle)

**Implementation — replaces all four hardcoded constants:**
```python
search_text = f"{variant.gene}:{variant.cdna}"
```

That single line is the entire input construction for ClinVar, SpliceAI
and Franklin. VEP uses transcript instead of gene name, so:
```python
vep_input = f"{variant.transcript}:{variant.cdna}"
```

Both fields (gene, transcript, cdna) already exist in every variant
object in the current data model. Zero new fields needed.

**TODO next session:** Verify SpliceAI REST API endpoint (not just the
web UI) also accepts GENE:c.cdna format. If yes, the backend tool
parameterisation is trivially simple — one line change per tool file.


### Fix queued: DNA notation should be primary throughout, not protein notation

**Problem:** Report headers, variant tabs, and lookup results currently
lead with protein notation (p.Asp87Gly) and show DNA notation secondary.
This is clinically backwards for a genomic sequencing report tool.

**Why it matters:**
- Sequencing labs report in DNA/coding notation (c.260A>G) — that is
  the actual molecular finding
- Databases and APIs are indexed and searched by DNA notation
- Protein consequence (p.Asp87Gly) is derived/predicted from the DNA
  change — it is secondary information
- For splice, intronic, and frameshift variants there is often no clean
  protein notation at all
- Clinicians reading lab reports see c.260A>G first, not p.Asp87Gly

**What to change next session:**
- Report header: "RPE65 c.260A>G" as primary title
  with (p.Asp87Gly) in smaller text below as consequence
- Variant switcher tabs: show gene + cdna as primary label
  e.g. "RPE65 c.260A>G" not "RPE65 p.Asp87Gly"
- Lookup tool results header: same — cdna leads
- Plain language decoder: explain the DNA change first,
  protein consequence as downstream effect
- Search bar placeholder text: show c.260A>G format as example
  not p.Asp87Gly


### Future vision — species-agnostic variant lookup (post-human MVP)

**Concept:** The same lookup tool architecture — one search bar, one
report, aggregated from multiple databases — applied to veterinary
and non-human genomics. Same HGVS nomenclature, same report structure,
different database stack depending on species.

**Why the architecture supports this:**
- HGVS nomenclature is universal across species
- Ensembl VEP natively supports multiple species (dog, cat, horse etc.)
  — the VEP tool we already use works for non-human variants with
  minimal changes (just swap the genome assembly parameter)
- Report structure and plain language decoder are species-agnostic
- The lookup tool concept (one place, multiple databases) is identical

**Database stack for veterinary genomics:**
- NCBI GenBank / RefSeq — reference sequences for all species
- UCSC Genome Browser — genome assemblies (canFam for dog, felCat for cat)
- OMIA (Online Mendelian Inheritance in Animals) — animal equivalent of OMIM
- dbSNP — NCBI variant database, covers dog, cat and others
- Ensembl — VEP supports non-human assemblies natively

**Design decision to resolve when relevant:**
- Does user specify species upfront (determines database stack)?
- Or does tool auto-detect from gene name / genome build?

**Priority:** Post-human MVP. Get the human clinical genomics tool
right and validated by clinicians first. The animal extension is then
just a database stack swap — same architecture, same concept.

