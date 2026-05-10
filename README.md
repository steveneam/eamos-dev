# Eamos — Genomic Intelligence Platform

## Overview

Eamos is a genomic intelligence platform that aggregates evidence from multiple public databases and presents it in a single structured report. A researcher or clinician types a gene and variant in HGVS notation and gets classification, population frequency, splice prediction, protein impact, and clinical trial data — without opening six browser tabs. The platform is built in three layers: Layer 1 (variant lookup web tool), Layer 2 (clinical report generation), and Layer 3 (internal — not discussed publicly). Layer 1 is the active build target.

---

## Tech Stack

| Component | Technology |
| --------- | ---------- |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS + Framer Motion |
| Backend | Python 3.10 + FastAPI + Uvicorn |
| LLM (default) | `provider=mock` — no API calls; deterministic fixture responses |
| LLM (live) | OpenAI GPT-4o-mini via LangChain (`provider=openai`) |
| Plain language decoder | Pure regex/template — no LLM, fully offline |
| Database | SQLite in-memory (dev) / PostgreSQL (Docker) |
| Auth | JWT (secret required at startup — no default) |
| Node.js (Windows) | Portable at `C:\temp\node\node-v22.15.0-win-x64` |
| Python (Windows) | `C:\Program Files\Python310\` |

**Key paths:**

| Item | Path |
| ---- | ---- |
| Frontend source | `app/frontend/src/App.tsx` |
| Backend source | `app/backend/app/` |
| Backend config | `app/backend/.env` (from `.env.example`; gitignored) |
| Design system | `DESIGN.md` |
| Prototype | `docs/design/` |

**Start dev servers:**

```powershell
# Backend
$env:PATH = "C:\Program Files\Python310\;C:\Program Files\Python310\Scripts\;$env:PATH"
cd app/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend
$env:PATH = "C:\temp\node\node-v22.15.0-win-x64;$env:PATH"
cd app/frontend
npm run dev
# → http://localhost:5173
```

---

## Architecture

### Layer 1 — Variant Lookup (the landing page)

The search bar IS the homepage. Users arrive and immediately search. No navigation required.

```
User types: RPE65:c.260A>G
        ↓
POST /api/v1/lookup
  { gene, cdna, transcript?, protein_change?, species }
        ↓
Evidence pipeline (5 tools in parallel):
  ClinVar    → pathogenicity classification
  Ensembl VEP → molecular consequence, genomic coords
  SpliceAI   → splice impact score
  Franklin   → functional evidence (auth required)
  PubMed     → relevant publications
        ↓
Rules engine (clinic_rules.py)
        ↓
Draft render (LLM or mock)
        ↓
ReportPayload returned to frontend
        ↓
Layer 1 report rendered (7 sections)
```

When a variant is **not found**: the frontend shows direct links to all external databases with the search term pre-filled where each API supports it.

From lookup results, the user can click **"Generate patient report →"** to enter Layer 2.

### Layer 2 — Patient Report (ghost-button flow)

Accessed via "For clinicians: Generate a patient report →" at the bottom of the landing page. Separate view — does not compete with the search bar.

```
PDF upload (genomic report + patient history)
        ↓
POST /api/v1/reports/upload
        ↓
Intake service (LLM extraction → structured case)
        ↓
POST /api/v1/runs (same 5-tool evidence pipeline as Layer 1)
        ↓
Rules engine → draft render
        ↓
ReportPayload with patient context (ERG, OCT, pedigree, recommendations)
        ↓
Layer 2 report rendered (11 sections)
        ↓
Clinician edits draft → signs off → PDF export
```

### Information Hierarchy (important design decision)

Layer 1 lookup = landing page. Layer 2 patient report = secondary, accessed via ghost button. No top-level navigation tabs between modes. This mirrors how Google's search is the homepage — the product, not a sub-page.

### Default operating mode

`USE_REAL_APIS=false` — all tools return fixture JSON. `LLM_PROVIDER=mock` — no OpenAI calls. Live mode requires IT network clearance (outbound HTTPS for Python blocked by corporate policy as of session 9).

---

## Database Stack

### Human (hg38)

| Database | What it provides | Input format | API |
| -------- | ---------------- | ------------ | --- |
| ClinVar | Pathogenicity classification, review status, conditions | `GENE:c.cdna` via esearch → variation ID → esummary | NCBI E-utilities (free) |
| Ensembl VEP | Molecular consequence, genomic coords, canonical transcript | `TRANSCRIPT:c.cdna` | rest.ensembl.org (free) |
| SpliceAI | Splice impact score (delta score, position) | `GENE:c.cdna` | spliceailookup.broadinstitute.org |
| gnomAD | Population allele frequency (v4) | Gene page via Ensembl ID | gnomad.broadinstitute.org |
| Franklin | Functional evidence, variant curation | `GENE:c.cdna` | api.genoox.com (auth required) |
| AlphaMissense | Protein impact score + domain map | UniProt ID | hegelab.org |
| AlphaFold | 3D protein structure | UniProt ID | alphafold.ebi.ac.uk |
| OMIM | Gene–disease associations | Gene entry ID | omim.org |
| ClinicalTrials.gov | Recruiting and active trials | Gene name | clinicaltrials.gov REST API v2 |
| PubMed | Publications (title, abstract excerpt, PMID link) | `GENE[gene] AND c.cdna` | NCBI E-utilities (free) |

### Mouse (mm39)

| Database | What it provides |
| -------- | ---------------- |
| MGI | Mouse gene/variant annotations, curated phenotypes |
| IMPC | Systematic knockout phenotypes |
| Ensembl VEP | Supports mm39 natively (same API, different assembly) |
| AlphaMissense | Covers mouse proteins |
| AlphaFold | Covers mouse proteins |
| dbSNP | Mouse variants |
| PubMed | Same API — add `[mus musculus]` to search term |

### Universal API input format

Every tool accepts the same format — no coordinate conversion or dependency ordering needed:

```python
search_text = f"{variant.gene}:{variant.cdna}"    # ClinVar, SpliceAI, Franklin
vep_input   = f"{variant.transcript}:{variant.cdna}"  # Ensembl VEP
```

### GENE_META — gene metadata for URL construction

```javascript
const GENE_META = {
  RPE65: { ensembl: 'ENSG00000116745', omim: '180069', uniprot: 'P40926' },
  USH2A: { ensembl: 'ENSG00000042781', omim: '608400', uniprot: 'O75445' },
  ABCA4: { ensembl: 'ENSG00000198691', omim: '601691', uniprot: 'P78363' },
  RPGR:  { ensembl: 'ENSG00000156313', omim: '312610', uniprot: 'P98161' },
  CNGA3: { ensembl: 'ENSG00000144348', omim: '600053', uniprot: 'Q16281' },
};
```

Never hardcode database URLs. Always construct dynamically from `GENE_META` + variant fields.

---

## Report Structure

### Layer 1 — Variant Lookup Report (human)

1. Variant header — `GENE c.cdna (p.protein)` — DNA notation leads
2. Plain language decoder — what the notation means in plain English
3. AI evidence summary — what databases collectively say about pathogenicity
4. Classification snapshot — all scores with source hyperlinks
5. Clinical integration — gene → protein → function → phenotype (3 bullets with numeric values)
6. Gene/disease phenotype — OMIM table + gene function
7. Gene therapy flag — auto-surfaced where applicable (e.g. Luxturna for RPE65)
8. Clinical trials — ClinicalTrials.gov (recruiting/active only)
9. Publications — PubMed (3 shown default, expand toggle, abstract excerpts, PubMed gene-search link)

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

Same 9 sections as Layer 1 human, plus:

- **Section 2:** Clinical context — ERG (waveform SVG), OCT, fundoscopy, pedigree (4-generation SVG). Expandable images inline.
- **Section 3:** AI clinical summary — patient-grounded; references specific investigation values with units
- **Section 9:** Recommendations — tiered HIGH / MODERATE / ROUTINE with ACMG criteria noted
- **Section 10:** Limitations — checkbox list
- **Section 11:** Clinician sign-off — name, date, status dropdown, version stamp

Differences from Layer 1: no "View all on PubMed" shortcut (replaced by curated evidence); clinical trials section includes eligibility pre-assessment note.

---

## HGVS Nomenclature

The plain language decoder auto-detects notation type from the cdna/protein string using regex.

| Notation | Type | Plain English concept |
| -------- | ---- | --------------------- |
| `c.353G>A` | Substitution (missense/synonymous) | One base swapped; protein may be altered |
| `c.2299delG` | Single-base deletion (frameshift) | Reading frame shifted; early stop likely |
| `c.123_125del` | Multi-base deletion | Multiple bases removed |
| `c.123_124insATCG` | Insertion | Bases inserted; frameshift if not multiple of 3 |
| `c.123dupA` | Duplication | Base duplicated |
| `c.2405+1G>A` | Splice site (intronic, after exon) | Disrupts splice donor; protein likely faulty or absent |
| `c.2405-3C>T` | Splice site (intronic, before exon) | Disrupts splice acceptor |
| `p.Glu767Serfs*21` | Frameshift with premature stop | Protein truncated at position +21 |
| `p.Arg436Trp` | Missense | Single amino acid substitution |
| `p.(splice)` | Splice disruption | Protein consequence unknown |

---

## What Has Been Built — Sessions 1–9

| Session | Date | What was delivered |
| ------- | ---- | ------------------ |
| 1 | ~06 May | HTML prototype with all 11 report sections, 5 IRD variants (RPE65, USH2A, ABCA4, RPGR, CNGA3), ERG waveform SVG, pedigree SVG, gene therapy flags, clinical trials mock data |
| 2 | 07 May | AI prompt refinement (active voice, clinical register, numeric values required); export to standalone HTML |
| 3 | 07 May | Source hyperlinks (ClinVar, gnomAD, SpliceAI, Franklin, OMIM, AlphaFold) in classification snapshot; variant lookup mode (search bar, found/not-found states, external DB links) |
| 4 | 08 May | DNA notation leads everywhere (c.cdna primary, p.protein muted below); plain language variant decoder (regex/template, offline, 7 cdna types, 3 protein types); all 4 backend tools gene-agnostic (ClinVar, VEP, SpliceAI, Franklin); project moved from D: (FAT32) to E: (NTFS) |
| 5 | 09 May | PubMed tool (fixture + live NCBI path); frontend publications section (3 default, show-more toggle); species selector pill (Human active, Mouse "soon"); JWT secret hardening (required at startup) |
| 6 | 09 May | Backend .env created; full fixture-mode pipeline smoke test passed; report section restructure (Classification & Evidence, Gene & Disease Context, Patient Clinical Findings, Genomic Interpretation, Recommended Next Steps, Therapeutic Landscape placeholder, Limitations); `therapeutic_landscape` field added to schema |
| 7 | ~10 May | PubMed abstract excerpts (200-char preview) with per-article "Show full abstract" expand toggle |
| 8 | ~10 May | Eamos branding (magicgene → Eamos in index.html and App.tsx header); Layer 1 lookup backend endpoint (`POST /api/v1/lookup` — schemas, service, route, wired into main.py); frontend lookup types and `variantLookup()` API call |
| 9 | 10 May | DESIGN.md created (full design system: typography, colour, spacing, components); 6 custom subagent role files (`.claude/agents/`); information hierarchy fix (Lookup = landing page; Patient Report = ghost button at bottom); styling items 2–16 in progress |

---

## Key Design Decisions and Invariants

### DNA notation is primary — always

Sequencing labs report in coding notation (`c.260A>G`). Databases are indexed by coding notation. APIs accept coding notation. Protein consequence (`p.Asp87Gly`) is derived and secondary — for splice and intronic variants it often does not exist.

**Rule:** Every display surface shows `GENE c.cdna` as the primary label. Protein consequence appears below in smaller, muted text — only when non-null.

### Source link on every data point — non-negotiable

Clinicians and researchers will not trust a number they cannot verify. Every score, classification, or frequency shown must be a hyperlink to its source database. Dotted underline style (`text-decoration-style: dotted`). Opens in new tab. Where the database does not support URL pre-filling (Franklin, SpliceAI web UI), show `GENE:c.cdna` as copy-paste text.

### All tools are gene-agnostic — no hardcoding

Every tool was originally hardcoded to `RPE65 p.Asp87Gly`. This was the primary blocker for real clinical use: any other variant would silently return RPE65 data. Session 4 removed all hardcoded constants. Every tool now constructs its search text from the variant object at call time.

### Plain language first — before any technical section

Every report opens with a one-paragraph plain English explanation of what the notation means, written for a clinician who does not parse HGVS daily. The decoder runs offline (pure regex) — no LLM call. cdna notation tried first; protein notation used as fallback.

### AI drafts, human checks

The tool aggregates and drafts. It never makes autonomous clinical decisions. Every AI-generated section is labelled accordingly. The Layer 2 report has a clinician sign-off section (Section 11) with name, date, status, and version stamp.

### Clinical bullets require numeric values with units

WRONG: "ERG shows reduced responses."
RIGHT: "Scotopic b-wave amplitude ~18 µV (reference: >150 µV) reflects severe rod system dysfunction."

This is enforced in the LLM prompt. The plain language decoder never approximates — it only describes what the notation type means, not clinical severity.

### Mode switching: Lookup = landing page, Patient Report = ghost button

The variant lookup search bar is the product homepage. No top-level navigation tabs between "Lookup" and "Patient Report" modes. The Layer 2 entry point is a contextual ghost button at the bottom of the landing page ("For clinicians: Generate a patient report →"). This matches how Google's search is the homepage — not a sub-page you navigate to.

---

## Directory Map

| Directory / File | What |
| ---------------- | ---- |
| `app/frontend/` | React + Vite frontend — `src/App.tsx` is the main file |
| `app/backend/` | FastAPI backend — `app/` contains tools, services, schemas, routes |
| `app/shared/contracts/` | Shared API contract (backend-api.json) |
| `docs/architecture/` | API research, backend workflow, database-specific guides (ClinVar, VEP, SpliceAI, Franklin) |
| `docs/design/` | Design brief, design system, Stitch design files |
| `docs/research/` | Problem scope, narrowing research |
| `docs/sources/` | Source index |
| `pitch/` | Pitch deck outline and speaking notes |
| `archive/` | Retired drafts, session handoffs, historical notes |
| `.claude/agents/` | Custom subagent role definitions (architect, developer, debugger, quality-reviewer, technical-writer, ui-ux-consultant) |
| `.claude/conventions/` | Universal coding and documentation standards |
| `.claude/skills/` | Agent workflow scripts (planner, deepthink, codebase-analysis, refactor, etc.) |
| `CLAUDE.md` | Navigation index + critical rules (read first) |
| `DESIGN.md` | Full design system — typography, colour, spacing, component specs |
| `PROGRESS.md` | Session-by-session build log |
| `CHANGELOG.md` | Feature changelog |

---

## Contact

**Project owner:** Steven (steveneam on GitHub)
**Private dev repo:** github.com/steveneam/eamos-dev (push target — main branch)
**Push method:** GitHub REST API (no git binary; `GITHUB_PAT` in `app/backend/.env`)
