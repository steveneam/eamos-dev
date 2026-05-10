# Eamos — Change Log

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

