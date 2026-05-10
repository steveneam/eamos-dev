# CLAUDE.md — Eamos Genomic Intelligence Platform
# Read this file before doing anything in this project.
# This is the single source of truth for what Eamos is,
# what has been built, what the rules are, and what comes next.

---

## What Eamos Is

Eamos is a genomic intelligence platform being built by Steven (steveneam).
It has three layers, built in sequence:

### Layer 1 — Variant Intelligence Website (BUILD THIS FIRST)
A web-based variant lookup tool. A direct competitor to Franklin (Genoox)
at franklin.genoox.com — but more transparent, more accessible, and
eventually species-agnostic.

The primary goal: a researcher or clinician types in a gene and variant,
and gets a comprehensive aggregated evidence report from multiple databases
in one place. No more opening six browser tabs.

**Species supported (in order of priority):**
- Human (hg38) — build first
- Mouse (mm39) — build second, important for research community
- Others (zebrafish, rat etc.) — future, don't build yet

**Species selector UI:**
Toggle or tab at the top of the search interface, before the search bar.
Shows genome build transparently (hg38, mm39).
Pattern: similar to UCSC Genome Browser species selector.

```
[Human (hg38)]  [Mouse (mm39)]

Search: gene name or variant in HGVS notation...    [Search]
e.g. RPE65:c.260A>G  or  USH2A:c.2299delG
```

**Regulatory positioning:**
Pure variant lookup tool presenting publicly available database information.
Research and informational use only. Similar regulatory footing to Franklin.
No clinical recommendations made by the tool itself.

---

### Layer 2 — Clinical Report Generation Tool (BUILD SECOND)
Same variant intelligence engine as Layer 1, with a patient clinical
history layer on top. Generates a structured genomic interpretation
report for clinician review.

**Current scope:** Inherited retinal disease (IRD)
**Expansion path:** Cardiac genetics → Oncology → Neurology → Rare disease

**Positioning:** Research use only initially. Locked behind enterprise
agreement. Either same website (locked section) or separate website
using the same codebase. Purpose: get real clinical feedback without
full regulatory burden of a certified clinical decision support tool.

**Important:** This is deliberately a scout product. Steven does not
mind if this idea gets copied or scrutinised. The purpose is to get
market feedback, build brand recognition, and refine the approach
before the real mission (Layer 3).

---

### Layer 3 — Pet Genetic Testing Service (THE REAL MISSION)
The primary long-term business. Developed in parallel with Layers 1 and 2
but protected and not publicly discussed.

```
Sample (fur/cheek swab/blood)
        ↓
DNA extraction (in-house)
        ↓
NGS sequencing (external lab initially, own machine eventually)
        ↓
Sequencing analysis tool (variant calling pipeline — future build)
        ↓
Variant intelligence tool (Layer 1, adapted for pets)
        ↓
Report generation (Layer 2, adapted for veterinary context)
        ↓
Report to pet owner / vet
```

Species: cats and dogs first (similar to Basepaws + Embark combined
but with deeper genomic analysis and own report generation).

The infrastructure built in Layers 1 and 2 transfers directly to Layer 3.
Same code, same AI prompts, different database stack.

Do not discuss Layer 3 in any public-facing code, comments, or documentation.

---

## The Current Tech Stack

**Frontend:** React + TypeScript + Vite + Tailwind + Framer Motion
**Backend:** Python + FastAPI
**LLM (backend):** OpenAI GPT-4o-mini via LangChain (provider=openai)
**LLM (mock/offline mode):** provider=mock — no LLM calls at all
**Plain language decoder:** Pure regex/template — no LLM, deterministic, offline
**Database:** SQLite (local dev) / Postgres (Docker integration)
**Hosting:** Local development only — not deployed yet
**Repository:** Private GitHub repo (eamos-dev)
**Reference prototype:** eamos-prototype-v1.html (standalone HTML file,
shows target UI and report structure)

**Key paths (canonical working copy: E:\HSIL-2026):**
- Frontend: E:\HSIL-2026\04_demo\app\frontend\src\App.tsx
- Backend: E:\HSIL-2026\04_demo\app\backend\
- Node.js portable: C:\temp\node\node-v22.15.0-win-x64
- Start dev server: cd E:\HSIL-2026\04_demo\app\frontend && npm run dev
- Dev server: http://localhost:5173 (pending IT network clearance)

---

## Critical Rules — Never Break These

### 1. DNA notation is primary, protein notation is secondary
Always lead with the coding DNA notation:
- CORRECT: RPE65 c.260A>G (p.Asp87Gly)
- WRONG: RPE65 p.Asp87Gly

Reason: Sequencing labs report in DNA notation. Databases index on DNA
notation. APIs search by DNA notation. Protein consequence is derived
and secondary. For splice/intronic variants there is often no clean
protein notation at all.

Apply everywhere: report headers, variant tabs, search results,
search bar placeholder text, plain language decoder.

### 2. The tool is gene-agnostic — never hardcode a gene or variant
Every API call must be constructed dynamically from variant input fields.

Universal input format for all databases:
```python
search_text = f"{variant.gene}:{variant.cdna}"
# e.g. "RPE65:c.260A>G"

vep_input = f"{variant.transcript}:{variant.cdna}"
# e.g. "NM_000329.2:c.260A>G"
```

### 3. Source links on every data point
Every number, score, or classification shown to a user must have a
clickable link back to its source database. Clinicians and researchers
will not trust data they cannot verify.

Label hyperlink format: dotted underline, opens in new tab.
Show "GENE:c.cdna" as copy-paste text next to databases that
don't support URL pre-filling (SpliceAI web UI, Franklin web UI).

### 4. Plain language first, technical detail second
Every report starts with a plain language explanation of what the
variant notation means — before any technical sections.
Written for a clinician who is not a full-time geneticist.
No jargon. One short paragraph.

### 5. AI drafts, human checks — never autonomous clinical decisions
The tool generates drafts and aggregates evidence. It never makes
autonomous clinical decisions. Every report section that involves
clinical interpretation must be clearly labelled as AI-generated
and subject to clinician review.

### 6. Active voice, clinical register, no hedging
AI-generated text must read like a senior clinical geneticist
handing off to a colleague. Never start sentences with:
"This report...", "Based on...", "It should be noted...",
"It is important to...", "Please note..."
Lead with the gene, variant, or clinical finding.

### 7. Every score must reference a specific numeric value with units
Clinical integration bullets must anchor to actual investigation values.
WRONG: "ERG shows reduced responses"
RIGHT: "Scotopic b-wave amplitude of ~18 µV (reference: >150 µV)
reflects severe rod system dysfunction"

---

## Database Stack

### Human (hg38)

| Database | What it provides | Input format | API |
|---|---|---|---|
| ClinVar | Pathogenicity classification | GENE:c.cdna via esearch → variation ID → esummary | NCBI E-utilities (free) |
| Ensembl VEP | Molecular consequence, genomic coords | TRANSCRIPT:c.cdna | rest.ensembl.org (free) |
| SpliceAI | Splice impact prediction | GENE:c.cdna (confirmed works) | spliceailookup.broadinstitute.org |
| gnomAD | Population frequency | Gene page via Ensembl ID | gnomad.broadinstitute.org |
| Franklin | Functional evidence | GENE:c.cdna | api.genoox.com (auth required) |
| AlphaMissense | Protein impact score + domain map | UniProt ID | hegelab.org or Google lookup |
| AlphaFold | 3D protein structure | UniProt ID | alphafold.ebi.ac.uk |
| OMIM | Disease associations | Gene entry ID | omim.org |
| ClinicalTrials.gov | Relevant trials | Gene name | clinicaltrials.gov REST API v2 |
| PubMed | Publications | GENE[gene] AND c.cdna | NCBI E-utilities (free) |

### Mouse (mm39)

| Database | What it provides |
|---|---|
| MGI | Mouse gene/variant annotations, curated phenotypes |
| IMPC | Systematic knockout phenotypes |
| Ensembl VEP | Supports mm39 natively |
| AlphaMissense | Covers mouse proteins |
| AlphaFold | Covers mouse proteins |
| dbSNP | Mouse variants |
| PubMed | Same API, add [mus musculus] to search |

### Key gene metadata (human) — for constructing database URLs
```javascript
const GENE_META = {
  RPE65: { ensembl:'ENSG00000116745', omim:'180069', uniprot:'P40926' },
  USH2A: { ensembl:'ENSG00000042781', omim:'608400', uniprot:'O75445' },
  ABCA4: { ensembl:'ENSG00000198691', omim:'601691', uniprot:'P78363' },
  RPGR:  { ensembl:'ENSG00000156313', omim:'312610', uniprot:'P98161' },
  CNGA3: { ensembl:'ENSG00000144348', omim:'600053', uniprot:'Q16281' },
};
```
This will grow as more genes are added. Never hardcode URLs — always
construct dynamically from GENE_META + variant fields.

---

## Report Structure

### Layer 1 — Variant Lookup Report (human)
1. Variant header — GENE c.cdna (p.protein) — DNA NOTATION LEADS
2. Plain language decoder — what the notation means in plain English
3. AI evidence summary — what databases collectively say about pathogenicity
4. Classification snapshot — all scores with source hyperlinks
5. Clinical integration — gene→protein→function→phenotype (3 bullets)
6. Gene/disease phenotype — OMIM table + gene function
7. Gene therapy flag — auto-surfaced where applicable (e.g. Luxturna for RPE65)
8. Clinical trials — ClinicalTrials.gov (recruiting/active only)
9. Publications — PubMed (3 shown by default, expand to 10, link to PubMed)

### Layer 1 — Variant Lookup Report (mouse)
1. Variant header
2. Plain language decoder
3. AI evidence summary
4. Classification snapshot — MGI, VEP, REVEL, CADD, SpliceAI, AlphaMissense
5. Gene function and variant mechanism
6. IMPC knockout phenotype
7. Gene/disease association — MGI + human ortholog OMIM
8. Publications — PubMed

### Layer 2 — Patient Report (human, IRD scope)
Same as Layer 1 human PLUS:
- Section 2: Clinical context — ERG, OCT, fundoscopy, pedigree
  (expandable images, clinician can view inline)
- Section 3: AI clinical summary (patient-grounded, references
  specific investigation values with units)
- Section 9: Recommendations — tiered HIGH/MODERATE/ROUTINE
  with ACMG criteria impact noted
- Section 10: Limitations — checkbox list
- Section 11: Clinician sign-off — name, date, status, version stamp

Sections NOT in Layer 2 that differ from Layer 1:
- No "View all on PubMed" shortcut (replaced by curated evidence)
- Clinical trials section includes eligibility pre-assessment note

---

## HGVS Nomenclature — Know This

The tool must correctly parse and explain all common HGVS variant types:

| Notation | Type | Example |
|---|---|---|
| c.353G>A | Substitution (missense/synonymous) | One base swapped |
| c.2299delG | Single base deletion (frameshift) | Reading frame shifted |
| c.123_125del | Multi-base deletion | Multiple bases removed |
| c.123_124insATCG | Insertion | Bases inserted |
| c.123dupA | Duplication | Base duplicated |
| c.2405+1G>A | Splice site (intronic, after exon) | +n = n bases into intron |
| c.2405-3C>T | Splice site (intronic, before exon) | -n = n bases before exon |
| p.Glu767Serfs*21 | Frameshift with stop | fs = frameshift, *21 = stop at +21aa |
| p.Arg436Trp | Missense | Amino acid substitution |
| p.(splice) | Splice disruption | Protein consequence unknown |

Plain language decoder must auto-detect notation type from the cdna
string using regex and generate appropriate plain English explanation.

---

## What Has Been Built So Far

See PROGRESS.md and CHANGELOG.md for full detail.

**Summary:**
- HTML prototype (eamos-prototype-v1.html) — fully working demo
  showing all 11 report sections, 5 IRD variants, AI-generated content,
  ERG and pedigree SVG visualisations, gene therapy flags, clinical
  trials, source hyperlinks, variant lookup tool
- Variant lookup mode — search bar, full evidence report for found
  variants, external database links for unknown variants
- Source hyperlinks — ClinVar, gnomAD, SpliceAI, Franklin, OMIM,
  AlphaFold linked from classification snapshot labels
- GENE_META + getURLs() — dynamic URL construction, no hardcoding
- Refined AI prompts — active voice, clinical register, no hedging,
  numeric values required in every clinical bullet

**Hackathon backend (04_demo/app/backend/) — current state:**
- FastAPI backend fully wired: upload → pipeline → review → PDF export
- All four tool files (clinvar.py, spliceai.py, franklin.py,
  ensembl_vep.py) are now gene-agnostic — session 4 complete ✓
- use_real_apis = False by default — uses fixture JSON
  (IT network clearance pending for live API calls)
- Rules engine (clinic_rules.py) is gene-agnostic ✓
- Report drafting prompts are gene-agnostic ✓
- Plain language variant decoder — pure regex/template, offline ✓
- DNA notation fixed: c.cdna leads everywhere in frontend ✓
- LLM: OpenAI GPT-4o-mini (provider=mock for offline dev)

---

## Immediate Next Tasks (in priority order)

1. **Therapeutic Landscape** — wire real gene therapy + trials data:
   a. Hardcode GENE_THERAPY_MAP (RPE65→Luxturna etc.) in workflow.py
      and lookup_service.py — populate therapeutic_landscape field in
      both ReportPayload builders.
   b. Add ClinicalTrials.gov REST API v2 call (recruiting/active only,
      filtered by gene name) — fixture + live path pattern same as
      ClinVar/PubMed tools.
   (In progress session 9.)

2. **Frontend styling pass** — items 2–16 from DESIGN.md:
   Font weights, logo placeholder, species toggle pill shape,
   input border-radius, max-width container, card shadows,
   accessibility (contrast/focus), gene-only search mode,
   idle state polish, scroll-to-results, loading skeleton.
   Patient Report now accessed via ghost button on landing page —
   mode-switching tabs removed from header. (In progress session 9.)

3. **Live API test** — set USE_REAL_APIS=true in .env and run the
   pipeline with a real variant (e.g. RPE65:c.260A>G). Blocked on
   IT network clearance for Python outbound connections.
   Confirm SpliceAI REST endpoint accepts GENE:c.cdna format.

4. **Wire frontend to real backend** — replace mock data in React app
   with live API responses from the FastAPI backend.
   Requires live API test to pass first.

5. **Rotate GitHub PAT** — the token used in session 4 was visible in
   chat. Generate a new one in GitHub settings and update .env / scripts.

---

## Design Reference

**Primary design inspiration:** Franklin (franklin.genoox.com)
Study their layout, information hierarchy, and evidence presentation.
Build something cleaner, more transparent, and more accessible.

**Key design principles:**
- Clean, professional, clinical — not consumer, not corporate
- Every data point traceable to its source (hyperlinked)
- Dense but scannable — clinicians/researchers read fast
- Mobile-aware but desktop-first (clinical tools are used on desktops)
- Species selector prominent and always visible

**Colour coding (classification):**
- Pathogenic: red (#E24B4A / #791F1F)
- Likely Pathogenic: orange (#BA7517 / #633806)
- VUS: amber (#d97706 / #854F0B)
- Likely Benign: lime (#639922 / #3B6D11)
- Benign: green (#1D9E75 / #27500A)

**Priority colours (recommendations):**
- HIGH: red background
- MODERATE: amber background
- ROUTINE: blue background

---

## Things NOT to Do

- Never hardcode a gene name, variant, or ClinVar ID
- Never lead with protein notation (p.) — always lead with DNA (c.)
- Never make autonomous clinical recommendations
- Never use hedging openers in AI-generated text
- Never show a score without a source link
- Never discuss Layer 3 (pet business) in public code or comments
- Never use Franklin as a data source without proper auth handling
- Never deploy to production without clinician review governance
- Never assume use_real_apis = True — check config before testing

---

## Contact / Ownership

Project owner: Steven (steveneam on GitHub)
Private repo: github.com/steveneam/eamos-dev
Public portfolio repo: github.com/steveneam/Eamos---Genomic-Diagnosis-Tool
(public repo is frozen — do not push development work there)
