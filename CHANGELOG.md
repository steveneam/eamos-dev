# Eamos — Change Log

## Session 13 — 15 May 2026

### v2 rebuild — frontend FE-0..FE-3 + backend BE-1..BE-5 landed in parallel

**Why:** First parallel-execution cycle using the `openai/codex-plugin-cc` plugin. Claude Code drove the React/Vite work; Codex executed `plans/v2-backend.md` against `app/backend/` end-to-end in 22m. Same git working tree, same auth, same filesystem — no format mismatch (the plugin delegates to the local Codex CLI).

**What changed:**

- **Frontend (FE-0..FE-3):** Foundation tokens + hairline utility + ModePill (FE-0); Franklin removed from active surfaces and replaced with AlphaMissense (FE-1); six new report v2 modules — LocusContext, InSilicoGrid, AcmgCriteriaFold, CuratedVariantsGrid, AssociatedConditions, PublicationsCallout — with ~180 lines of v2 module CSS appended to `index.css` (FE-2); VariantHeader rewritten with cross-DB chip strip, tools row, and 4-stat row (FE-3). Also fixed a pre-existing TypeScript path-alias gap in `tsconfig.app.json` (`@/*` mapping was missing — the build had been broken before this session).
- **Backend (BE-1..BE-5):** Franklin tool archived to `archive/franklin/` (BE-1); six new optional fields on `ReportPayload` with RPE65 fixture at `app/backend/app/fixtures/lookup_v2_modules.json` (BE-2); `POST /api/v1/chat` + `/chat/stream` (BE-3); `POST /api/v1/primer | /crispr | /align` returning fixture responses (BE-4); `test_franklin_removed.py` + extended `test_frontend_contract.py` (BE-5).
- **Plans:** `plans/v2-frontend.md` and `plans/v2-backend.md` updated with status tables. New "FE-3.5 — Contract sync" section in `plans/v2-frontend.md` defines the next milestone: add the matching TypeScript interfaces to `app/frontend/src/lib/backend.ts` so `test_frontend_contract.py` passes and the FE-2 components can swap from hard-coded SAMPLE blocks to payload-driven props.

**Known sync point:** `test_frontend_contract.py` is the only failing backend test — it's waiting on the FE-3.5 TypeScript interfaces. By design.

**Codex session id (resumable):** `019e26bf-c0db-7b03-aff3-a5303bac4eed`.

---

## Session 12 — 14 May 2026

### v2 rebuild plan written, Franklin archived from product

**Why:** Three Claude Design mocks (`Eamos Landing Page.html`, `Eamos Report Page v2.html`, `Eamos Workbench v1.html`) iterate Eamos into two surfaces — variant report v2 with new modules folded in, and a new Workbench (sequence viewer + Primer/CRISPR/Align/Compare tools + tool-aware AI pill). Franklin (Genoox) is the main competitor and is being removed from the product surface.

**What changed this session:**

- `plans/README.md` — parallel-work coordination doc (Claude Code frontend ↔ Codex backend, shared contract on `backend.ts` ↔ Pydantic).
- `plans/v2-frontend.md` — frontend port plan, 9 milestones (FE-0 foundation through FE-8 AskEamos pill). Built on existing Phase 0–2 scaffolding; React/Vite preserved (no Next.js migration).
- `plans/v2-backend.md` — Codex-consumable backend brief, 5 milestones (BE-1 Franklin archive through BE-5 test sweep). Self-contained — every path, schema, and verification step in the doc.
- `DESIGN.md` — full rewrite around v2 tokens (Syne/Plus Jakarta Sans/JBM, ink scale, sequence palette, AA biochem palette, 920/1180/1440 widths). Legacy `/runs` surface kept as a frozen appendix.
- `README.md` — Franklin dropped from Database Stack. Report Structure refreshed to v2 sections (locus context, in-silico grid, ACMG fold, curated variants distribution, structured conditions, publications callout). Workbench surface added.
- `ROADMAP.md` — Layer 1 v1 marked done. Two new active phases: Layer 1 v2 + Workbench. Layer 2 marked frozen at `/runs`.
- `PROGRESS.md` — Session 12 entry summarising the rebuild.

**Decisions locked in (the five conflicts surfaced):**

1. Stack: keep React + Vite. Next.js migration deferred — re-evaluate if file-based API routing becomes load-bearing.
2. Layer 2 patient report at `/runs` frozen — no design changes, no new features.
3. Workbench delivered all-at-once with sample data; real engines (Primer3, CRISPOR, Needleman–Wunsch, AB1 parser) deferred to M-002.
4. Franklin: archive to `archive/franklin/` (preserve history, remove from active code).
5. v2 mock includes a `franklin.genoox.com` "Compare elsewhere ↗" chip — dropped in implementation. We don't link to competitors.

**Not yet implemented:** plans are written; Claude Code starts FE-0, Codex picks up `plans/v2-backend.md`.

---

## Session 10 — 10 May 2026

### Changes made this session

#### 15. AlphaMissense tool implementation plan

**Why:** The Solatis workflow (explore → deepthink → plan → execute) needed a first
real test case. The original candidate (ClinicalTrials.gov integration) turned out to
be already fully implemented — `clinical_trials.py`, `GENE_THERAPY_MAP`, and the
`therapeutic_landscape` field wiring in both service layers were complete but undocumented.
AlphaMissense was chosen instead: it is listed as `_(planned)_` in README.md, has no
implementation file, and exercises all five layers the workflow is designed for
(tool file, fixture JSON, registry, service payload, frontend card).

**What changed:**
- `plans/alphamissense-tool.md` — full implementation plan: 3 milestones (M-001 tool
  foundation, M-002 pipeline wiring, M-003 frontend + docs), 7 architectural decisions
  (DL-001–DL-007), 5 rejected alternatives, 3 risks. Ready to execute.
- `plans/` directory created (commit 32a185c).

**Key decisions recorded in the plan:**
- Data shape = Point lookup only: `summary = {uniprot_id, residue, score, pathogenicity_category}`
  (user confirmed; may revisit later)
- Wire into existing `acmg_classification` string field — no new schema field
- Thresholds from Cheng et al., Science 2023 (doi:10.1126/science.adg7842, Table S5):
  `<0.34` likely_benign, `0.34–0.564` ambiguous, `>0.564` likely_pathogenic
- `alphamissense` inserted between `spliceai` and `clinvar` in the evidence tuple
  in both `lookup_service.py` and `workflow.py`

**Not yet implemented** — plan is written and QR-validated; execution is the next session task.

#### 16. Therapeutic Landscape + ClinicalTrials.gov — discovered as already complete

**Why documented:** ROADMAP listed this as a future task, but exploration revealed the
full implementation was already in place from a prior session with no changelog entry.

**What exists (undocumented until now):**
- `app/tools/clinical_trials.py` — `ClinicalTrialsTool` fetching recruiting/active trials
  from ClinicalTrials.gov REST API v2; fixture map for 4 genes (RPE65, RPGR, ABCA4, CNGA3)
- `GENE_THERAPY_MAP` in `app/services/lookup_service.py` — gene → approved therapy text
- `therapeutic_landscape` field wired in both `lookup_service.py` and `workflow.py` —
  combines `GENE_THERAPY_MAP` entry + `ClinicalTrialsTool.get_trials_summary(gene)`

#### 17. Karpathy coding guidelines added to CLAUDE.md

**Why:** Solatis optimization pass (commit 903d295) identified missing behavioral constraints.
Karpathy-style guidelines added to reduce common LLM coding mistakes: simplicity-first,
surgical changes, goal-driven execution, think-before-coding. Commit 32a185c.

---

## Session 5 — 09 May 2026

### Changes made this session

#### 8. JWT secret hardening
**Why:** The previous `config.py` had `jwt_secret: str = 'dev-insecure-change-me-please-replace'`
as a default, meaning the backend would start silently with an insecure key if `.env` was
missing. A missing JWT secret should be a hard startup failure, not a silent misconfiguration.

**What changed:**
- `app/core/config.py:31` — `jwt_secret` default removed. Field is now bare `str`, so
  `pydantic_settings` raises `ValidationError` at startup if `JWT_SECRET` is absent from `.env`.
- `.env.example` already contained `JWT_SECRET` — no example change needed.
- `.env` must be created from `.env.example` before first startup (documented in README).

#### 9. franklin.py dead-code typo removed
**Why:** `canonical_tanscript` (missing 's') was a dead variable assigned but never read.
No functional impact, but dead code is noise in a file that will be reviewed when live
Franklin API integration is wired.

**What changed:**
- `app/tools/franklin.py:92` — `canonical_tanscript` line deleted.

#### 10. Backend README rewritten
**Why:** The old README described endpoints that don't exist (`GET /healthz` → actual route
is `GET /healthz` but under wrong API prefix), omitted the actual tool/schema/service
architecture, and was generic hackathon boilerplate. Any new contributor reading it would
get a wrong mental model of the system.

**What changed:**
- `app/backend/README.md` — complete rewrite. Architecture diagram, all API routes
  (actual routes with correct prefixes), tools table, config table, setup instructions.

#### 11. CLAUDE.md created at E:\HSIL-2026
**Why:** The E: drive copy of the project was missing CLAUDE.md — the single source of
truth for what Eamos is, what has been built, and what the rules are. Without it, future
Claude sessions would have no project context.

**What changed:**
- `CLAUDE.md` — written fresh. Reflects all session 4 completions, updated next-task list,
  current tech stack, database stack, report structure, HGVS table, critical rules.

#### 12. PubMed publications tool
**Why:** "Publications" was listed as a required report section in the spec but had no
backend implementation. The fixture-backed pattern established for ClinVar/VEP/SpliceAI/
Franklin transfers directly: one class, one fixture file, live NCBI E-utilities path.

**What changed:**
- New `app/tools/pubmed.py` — `PubmedTool` using `FixtureBackedTool` base class.
  Live path: esearch (gene + cdna term against PubMed) → esummary → article list with
  PMID, title, authors (first author + et al.), journal, year, PubMed URL.
  Falls back to fixture if `USE_REAL_APIS=false` or on any network exception.
- New `app/fixtures/tools/pubmed_fixtures.json` — 3 representative RPE65 articles.
- `app/tools/registry.py` — `PubmedTool` registered under key `"pubmed"`.
- `app/schemas/run.py` — `PubMedArticle` Pydantic schema added; `pubmed_articles:
  list[PubMedArticle] | None` field added to `ReportPayload`.
- `app/services/workflow.py` — `"pubmed"` added to the tool loop; pubmed evidence
  extracted and coerced to `list[PubMedArticle]`; set on `base_payload.pubmed_articles`.

#### 13. Frontend publications section
**Why:** PubMed articles are now returned by the backend but nothing rendered them.
The spec requires: 3 articles shown by default, "Show N more" toggle, dotted-underline
links, "View all on PubMed" gene-search link.

**What changed:**
- `app/frontend/src/lib/backend.ts` — `PubMedArticle` TypeScript interface added;
  `pubmed_articles?: PubMedArticle[]` added to `ReportPayload` interface.
- `app/frontend/src/App.tsx` — `buildPublicationsSection()` function added.
  Renders after the Limitations section. 3 articles default, "Show N more" toggle.
  Each article: title as dotted-underline link to PubMed, authors + journal + year.
  "View all on PubMed" gene-search link top right. Renders nothing when field is empty.

#### 14. Species selector
**Why:** The spec requires a species toggle (Human hg38 / Mouse mm39) visible before the
search/submit bar. Mouse is not yet built but needs to be visible to signal roadmap intent.
Placing it in the submit bar keeps it always visible without adding a separate header row.

**What changed:**
- `app/frontend/src/App.tsx` — pill toggle added in the submit bar above "Submit reports".
  Human (hg38): active/teal. Mouse (mm39): disabled, 45% opacity, "soon" badge.
  `selectedSpecies` state (default: `"human"`). No backend changes — mouse database stack
  not built yet; toggle is UI scaffolding only.

---

## Session 4 — 08 May 2026

### Changes made this session

#### 5. DNA notation as primary in variant table and sidebar
**Why:** Sequencing labs report in DNA/coding notation (c.260A>G) — that is the
actual molecular finding. Protein consequence is derived and secondary. The previous
display joined both into one string with protein first, which is clinically backwards.

**What changed:**
- `buildVariantRows` in App.tsx now produces two separate fields:
  `variantDna` (transcript_hgvs → consequence fallback) and
  `variantProtein` (protein_change, nullable)
- Desktop variant table: DNA notation full-size, protein change 13px muted below
- Mobile variant table: DNA notation `font-medium`, protein change `text-sm muted`
- Sidebar "Variant Summary" card: DNA notation as primary line,
  protein change `text-xs` at reduced opacity
- Protein line only renders when non-null — no blank line for splice/frameshift variants

#### 6. Backend tool parameterisation — all four tools now gene-agnostic
**Why:** Every tool (ClinVar, VEP, SpliceAI, Franklin) was hardcoded to RPE65 p.Asp87Gly
with constants baked into the class body. Any variant other than that one would silently
return RPE65 data regardless of what was uploaded. This was the primary blocker between
fixture mode and real clinical use.

**What changed:**
- clinvar.py: removed `CLINVAR_ID = "1421454"`. Added two-step live fetch:
  esearch resolves GENE:c.cdna to a ClinVar variation ID, then esummary fetches
  classification, review status, and conditions for that ID.
- ensembl_vep.py: removed `HGVS = "NM_000329.3:c.260A>G"` and hardcoded `RPE65`
  gene filter. Uses `variant.transcript_hgvs` directly; canonical transcript
  selected by `variant.gene` with safe fallback to first result.
- spliceai.py: removed `VARIANT = "chr1-68444869-T-C"`. Constructs `GENE:c.cdna`
  string from variant fields. (Live REST endpoint format to confirm when tested.)
- franklin.py: removed `SEARCH_TEXT = "RPE65:c.260A>G"`. Same `GENE:c.cdna`
  construction for both parse_search and snp search calls.
- workflow.py: variant collection moved before tool calls. Primary variant extracted
  from report and passed into all tools via `tool.get_evidence(variant=primary_variant)`.
  All fallback behaviour preserved — variant=None falls through to fixture data.

**Also:**
- pyproject.toml: `requires-python` relaxed from `>=3.11` to `>=3.10`.
  No 3.11-specific syntax exists anywhere in the codebase; the constraint was conservative.
  Python 3.10.11 is installed and all dependencies install cleanly.

#### 7. Plain language variant decoder
**Why:** Clinicians outside core genetics (ophthalmologists, neurologists, general
geneticists) don't parse HGVS notation daily. Decoding it automatically reduces
friction and makes reports readable to a broader clinical audience.

**What changed:**
- New file `app/services/variant_decoder.py`: `decode_variant(gene, transcript_hgvs,
  protein_change)` returns a one-paragraph plain English explanation.
  Pure regex/template — no extra LLM call, works offline, deterministic.
  Handles 7 cdna types (substitution, single/multi-base deletion, insertion,
  duplication, splice site ±offset) and 3 protein types (frameshift, missense, splice).
  cdna notation tried first; protein change used as fallback.
- `app/schemas/run.py`: `variant_decoder: str | None = None` added to ReportPayload.
- `app/services/workflow.py`: decoder called for the primary variant row;
  result set on base_payload.variant_decoder before draft rendering.
- `app/frontend/src/lib/backend.ts`: `variant_decoder?: string | null` added
  to the ReportPayload TypeScript interface.
- `app/frontend/src/App.tsx`: "What this variant means" callout block inserted
  between the executive summary and the variant table. Teal label, muted body text,
  soft card style. Only renders when field is non-null.

Smoke tested against all five demo variants — all decode correctly.

#### Infrastructure: project moved to E:\HSIL-2026
- D: drive was FAT32 with ~20 MB free — could not hold node_modules
- E: drive reformatted from FAT32 to NTFS, project copied to E:\HSIL-2026
- Node.js v22.15.0 portable installed at C:\temp\node\node-v22.15.0-win-x64
- Python 3.10.11 installed via company portal; all backend deps installed
- Private dev repo created: https://github.com/steveneam/eamos-dev (account: steveneam)
  Pushes via GitHub REST API — git not installed, github.com downloads blocked by IT
- Dev server: `npm run dev` from E:\HSIL-2026\04_demo\app\frontend → localhost:5173
  (pending IT network clearance for Node.js to bind locally)

## Session 2 — 07 May 2026

### Changes made this session

#### 1. AI prompt refinement
**Why:** The original hackathon prompts were generic. They produced hedging,
passive language ("This report suggests...") instead of the active, clinician-
to-clinician tone that genomic geneticists actually use in handoff notes.
Clinicians testing the tool will lose trust immediately if the prose sounds
like a disclaimer rather than a colleague's assessment.

**What changed:**
- Added explicit instruction: "Write as a senior clinical geneticist handing
  off to a colleague — direct, active, no hedging openers"
- Instructed the model to lead with the gene and variant name, not a
  sentence about the report itself
- Tightened the clinical integration bullets: each must state a mechanism
  AND reference a specific numeric value with units (e.g. "b-wave ~18 µV;
  reference >150 µV") — not just describe findings in general terms
- Added instruction to avoid: "This report...", "Based on...", "It should
  be noted that...", "It is important to..."

#### 2. Export to standalone HTML file
**Why:** The prototype lives inside Claude's chat widget, which means only
people with this conversation can see it. The dev team needs a file they can
open in any browser, share, and use as a reference for rebuilding in React.
A standalone HTML file with no external dependencies (except the Anthropic
API call) is the simplest handoff format.

**What changed:**
- Wrapped the widget code in a full HTML document
- Added proper DOCTYPE, meta charset, viewport tag
- Kept all data and logic self-contained (no CDN dependencies)
- Added a visible file header comment explaining what the file is,
  who built it, and what each section does


## Session 3 — 07 May 2026

### Changes made this session

#### 3. Source hyperlinks in Section 4 (classification snapshot)
**Why:** Clinicians will not trust a number they cannot verify. Every data
point in the classification snapshot needs to be traceable back to its
source database in one click. This is also a regulatory requirement for
any clinical decision support tool — the evidence trail must be auditable.
Each label in Section 4 is now a hyperlink to the specific variant or gene
page on that database (ClinVar, gnomAD, SpliceAI Lookup, Franklin, OMIM,
AlphaFold).

**What changed:**
- Added URLS constant: pre-constructed deep links per variant to each
  database. Stored separately from variant data for maintainability.
- Section 4 labels now render as <a> tags pointing to the relevant
  database page, opening in a new tab.
- SpliceAI links to spliceailookup.broadinstitute.org (the correct
  public tool, not a constructed URL).
- gnomAD links to the gene page (gnomAD v4) since variant-level deep
  links require the gnomAD variant ID format (chr-pos-ref-alt) which
  we do not yet store.

#### 4. Variant / gene lookup mode (search bar)
**Why:** Clinicians and researchers frequently want to look up a variant
or gene without generating a patient report — when reviewing literature,
in a meeting, when a colleague mentions a variant. Opening six browser
tabs to cross-reference databases is the current workflow. This feature
collapses that into one search.

**What changed:**
- Added second mode to the tool: "Variant lookup" accessible from the
  landing page alongside the existing report generation flow.
- New view: 'lookup' — search bar that queries the mock variant database.
- If found: shows a condensed evidence card (classification, key scores,
  gene function) plus direct links to all databases for that variant.
- If not found: shows direct links to all external databases with the
  search term passed as a query parameter where each database supports it.
- "Generate report" button on lookup results — bridges lookup mode into
  the full report generation flow.
- This is intentionally a mock implementation. In production, this would
  hit the real database APIs directly (ClinVar, gnomAD, SpliceAI, Franklin).

