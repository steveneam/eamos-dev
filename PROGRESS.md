# Eamos Genomic Report Tool — Build Progress

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

