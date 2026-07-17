# Eamos — Genomic Intelligence Platform

## Overview

Eamos is a genomic intelligence platform that aggregates evidence from multiple public databases and presents it in a single structured report. A researcher or clinician types a gene and variant in HGVS notation and gets classification, population frequency, splice prediction, protein impact, and clinical trial data — without opening six browser tabs.

Two surfaces:

- **Variant report** (`/report`) — the v2 evidence report with locus context, in-silico predictions deep-dive, ACMG criteria scaffolding, curated variants distribution, structured associated conditions, and a publications callout.
- **Workbench** (`/workbench`) — sequence viewer with click-to-edit consequence prediction, Primer designer, CRISPR designer (gRNA + HDR ssODN), Sequence alignment (with AB1 chromatogram), Variant comparator, and a tool-aware AskEamos floating pill.

Both surfaces share the same variant context via the URL (`?q=GENE:c.cdna`) and a top-nav Report ⇄ Workbench mode toggle.

Three layers organisationally: Layer 1 (the variant report + Workbench), Layer 2 (clinical patient report at `/runs` — currently frozen on the v1 design system), Layer 3 (internal — not discussed publicly).

---

## Tech Stack

| Component | Technology |
| --------- | ---------- |
| Active frontend | `app/web` - Next.js + React + TypeScript + Tailwind CSS |
| Backend | Python 3.10 + FastAPI + Uvicorn |
| LLM (default) | `provider=mock` — no API calls; deterministic fixture responses |
| LLM (live) | OpenAI GPT-4o-mini via LangChain (`provider=openai`) |
| Plain language decoder | Pure regex/template — no LLM, fully offline |
| Database | SQLite in-memory (dev) / PostgreSQL (Docker) |
| Auth | JWT (secret required at startup — no default) |
| Node.js (Windows) | IT-managed system install at `C:\Program Files\nodejs\` (already on PATH) |
| Python (Windows) | `C:\Program Files\Python310\` |

> **Production services / vendor stack** (Vercel · Render · Supabase · Stripe · Resend · PostHog · Sentry · AI Gateway · Groq · Llama · Porkbun) and the deliberate "not using" list (Pinecone / Clerk / Cloudflare / Aceternity) live in [`docs/tech-stack.md`](docs/tech-stack.md).

**Key paths:**

| Item | Path |
| ---- | ---- |
| Active frontend source | `app/web/app/` + `app/web/components/` |
| Backend source | `app/backend/app/` |
| Backend config | `app/backend/.env` (from `.env.example`; gitignored) |
| Design system | `DESIGN.md` |

**Start dev servers:**

```powershell
# Backend
$env:PATH = "C:\Program Files\Python310\;C:\Program Files\Python310\Scripts\;$env:PATH"
npm run dev:backend
# -> http://localhost:8532

# Active frontend
cd app/web
npm run dev
# -> http://localhost:3532
# Node.js: IT-managed system install at C:\Program Files\nodejs\ (already on PATH).
```

**Repository verification:** run `npm run verify` from the repository root for
the structural guards, frontend/backend lint, TypeScript, unit/integration
tests, and the active production build. Individual stages are available as
`npm run guard`, `lint`, `typecheck`, `test`, and `build`. Run
`npm run audit` separately for the network-backed frontend and backend
dependency advisory gates.

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
Evidence pipeline (tools in parallel):
  ClinVar       → pathogenicity classification
  Ensembl VEP   → molecular consequence, genomic coords
  SpliceAI      → splice impact score
  gnomAD        → population allele frequency
  AlphaMissense → protein impact score
  PubMed        → relevant publications
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

`USE_REAL_APIS=false` — all tools return fixture JSON. `LLM_PROVIDER=mock` — no OpenAI calls. Live mode needs outbound HTTPS for Python — verified working against real APIs 2026-05-16 (the earlier session-9 corporate-policy block no longer applies).

---

## Database Stack

### Human (hg38)

| Database | What it provides | Input format | API |
| -------- | ---------------- | ------------ | --- |
| ClinVar | Pathogenicity classification, review status, conditions | `GENE:c.cdna` via esearch → variation ID → esummary | NCBI E-utilities (free) |
| Ensembl VEP | Molecular consequence, genomic coords, canonical transcript | `TRANSCRIPT:c.cdna` | rest.ensembl.org (free) |
| SpliceAI | Splice impact score (delta score, position) | `GENE:c.cdna` | spliceailookup.broadinstitute.org |
| gnomAD | Population allele frequency (v4) | Gene page via Ensembl ID | gnomad.broadinstitute.org |
| AlphaMissense _(planned)_ | Protein impact score + domain map | UniProt ID | hegelab.org |
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
search_text = f"{variant.gene}:{variant.cdna}"    # ClinVar, SpliceAI
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

### Variant Report v2 (`/report`)

1. **Breadcrumb**
2. **Variant header** — gene + cDNA notation (primary), protein change (mono), classification badges, cross-DB jump strip (ClinVar / gnomAD / UCSC / Ensembl / OMIM / AlphaFold), tools row (Follow / Export PDF / Share), 4-stat row
3. **AIStack** — composite evidence summary + inline AskEamos chat (ink-dark panel, no visible seam between halves)
4. **Locus context** — region viewer: 5 lanes (P/LP/VUS/LB/B) of nearby ClinVar dots, vertical marker drops into 11-codon strip. "Open full sequence in Workbench ↗" handoff link
5. **Evidence by source** — `<InSilicoGrid />` (REVEL / AlphaMissense / MetaLR / SpliceAI Δ) + evidence table + verify-at-source chips + `<AcmgCriteriaFold />` (collapsible PVS1 → BP7 grid, met cells highlighted)
6. **Gene context & associated conditions** — gene function callout + curated variants distribution (3×4 heat matrix) + structured conditions list (case count, evidence level, inheritance pill, source) + publications callout
7. **Active trials & approved therapies** — ClinicalTrials.gov recruiting/active
8. **Limitations & caveats**

### Workbench (`/workbench`)

| Tool | What |
| ---- | ---- |
| **Sequence Viewer** (always visible, the spine) | Multi-track view (ruler / annotations / domain / ClinVar dots / DNA / translation / conservation / restriction) with vertical pin at the queried position. Click any DNA base → popover with live consequence preview using the real codon table |
| **Primer designer** | Sanger / qPCR / ARMS modes; output table with ★ recommended pair highlighted |
| **CRISPR designer** | gRNA scoring table + HDR ssODN repair block |
| **Sequence alignment** | Pairwise alignment + Canvas-rendered AB1 chromatogram |
| **Variant comparator** | 2–3 variant side-by-side property grid with predictor bars |
| **AskEamos pill** | Floating bottom-right, tool-aware. Suggested questions change per active tool |

### Variant Report — mouse mm39 _(planned, not yet implemented)_

Same section structure as human, with the database stack swapped: MGI for variant annotation, IMPC for knockout phenotype, VEP-mouse for consequence, mouse-specific PubMed query. Hidden from the v2 UI until the mouse pipeline ships.

### Layer 2 — Patient Report (`/runs`) — FROZEN

The Layer 2 patient report flow (PDF intake → 11-section clinical report with ERG, OCT, fundoscopy, pedigree, recommendations, clinician sign-off) remains live at `/runs` but is frozen on the v1 design system. No new features or design changes. A Layer 2 v2 redesign is on the roadmap as a future cycle.

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

Clinicians and researchers will not trust a number they cannot verify. Every score, classification, or frequency shown must be a hyperlink to its source database. Dotted underline style (`text-decoration-style: dotted`). Opens in new tab. Where the database does not support URL pre-filling (SpliceAI web UI), show `GENE:c.cdna` as copy-paste text.

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

### Active voice, clinical register, no hedging

Every generated section leads with the gene, variant, or clinical finding. Never open with "This report…", "Based on…", "It should be noted…", or "Please note…". This is enforced in the LLM prompt and applies to all AI-drafted text in both Layer 1 and Layer 2 outputs.

### Pet genetics — not discussed publicly

This platform has a separate internal business context involving pet genetics. Do not reference, mention, or expose this in any public-facing code, comments, or documentation.

---

## Directory Map

| Directory / File | What |
| ---------------- | ---- |
| `app/web/` | Active Next.js frontend - `/`, `/report`, `/workbench`, account/checkout/auth |
| `app/backend/` | FastAPI backend — `app/` contains tools, services, schemas, routes |
| `plans/` | Active and historical work plans. **Start at `plans/README.md`** for the agent-agnostic parallel-worktree workflow (any agent owns any part of the repo, chosen by availability; Steven 2026-07-08). Both Claude and Codex have verified full workspace + outbound-network access; live cross-agent coordination is in `agent_handoff/`. The plugin-mediated path ([openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc)) is historical. |
| `docs/proprietary/` | Catalogue of Eamos-original scripts, CLIs, algorithms, and orchestration logic (EP-VLEx, search input resolution) |
| `archive/` | Retired drafts, session handoffs, historical notes — includes `archive/franklin/` (the archived Genoox tool) |
| `.claude/agents/` | Custom subagent role definitions (architect, developer, debugger, quality-reviewer, technical-writer, ui-ux-consultant) |
| `.claude/conventions/` | Universal coding and documentation standards |
| `.claude/skills/` | Agent workflow scripts (planner, deepthink, codebase-analysis, refactor, etc.) |
| `CLAUDE.md` | Navigation index — files, subdirectories, dev commands |
| `DESIGN.md` | Full design system — v2 tokens, components, Workbench layout chrome |
| `PROGRESS.md` | Session-by-session build log |
| `CHANGELOG.md` | Feature changelog |
| `ROADMAP.md` | Active phases and future cycles |

---

# My Claude Code Workflow

I use Claude Code for most of my work. After months of iteration, I noticed a
pattern: LLM-assisted code rots faster than hand-written code. Technical debt
accumulates because the LLM does not know what it does not know, and neither do
you until it is too late.

This repo is my solution: skills and workflows that force planning before
execution, keep context focused, and catch mistakes before they compound.

## Why This Exists

LLM-assisted coding fails long-term. Technical debt accumulates because the LLM
cannot see it, and you are moving too fast to notice. I treat this as an
engineering problem, not a tooling problem.

LLMs are tools, not collaborators. When an engineer says "add retry logic",
another engineer infers exponential backoff, jitter, and idempotency. An LLM
infers nothing you do not explicitly state. It cannot read the room. It has no
institutional memory. It will cheerfully implement the wrong thing with perfect
confidence and call it "production-ready".

Larger context windows do not help. Giving an LLM more text is like giving a
human a larger stack of papers; attention drifts to the beginning and end, and
details in the middle get missed. More context makes this worse. Give the LLM
exactly what it needs for the task at hand -- nothing more.

## Principles

This workflow is built on four principles.

### Context Hygiene

Each task gets precisely the information it needs -- no more. Sub-agents start
with a fresh context, so architectural knowledge must be encoded somewhere
persistent.

I use a two-file pattern in every directory:

**CLAUDE.md** -- Claude loads these automatically when entering a directory.
Because they load whether needed or not, content must be minimal: a tabular
index with short descriptions and triggers for when to open each file. When
Claude opens `app/web/controller.py`, it retrieves just the indexes along that
path -- not prose it might never need.

**README.md** -- Invisible knowledge: architecture decisions, invariants not
apparent from code. The test: if a developer could learn it by reading source
files, it does not belong here. Claude reads these only when the CLAUDE.md
trigger says to.

The principle is just-in-time context. Indexes load automatically but stay
small. Detailed knowledge loads only when relevant.

The technical writer agent enforces token budgets: ~200 tokens for CLAUDE.md,
~500 for README.md, 100 for function docs, 150 for module docs. These limits
force discipline -- if you are exceeding them, you are probably documenting what
code already shows. Function docs include "use when..." triggers so the LLM
knows when to reach for them.

The planner workflow maintains this hierarchy automatically. If you bypass the
planner, you maintain it yourself.

### Planning Before Execution

LLMs make first-shot mistakes. Always. The workflow separates planning from
execution, forcing ambiguities to surface when they are cheap to fix.

Plans capture why decisions were made, what alternatives were rejected, and what
risks were accepted. Plans are written to files. When you clear context and
start fresh, the reasoning survives.

### Review Cycles

Execution is split into milestones -- smaller units that are manageable and can
be validated individually. This ensures continuous, verified progress. Without
it, execution becomes a waterfall: one small oversight early on and agents
compound each mistake until the result is unusable.

Quality gates run at every stage. A technical writer agent checks clarity; a
quality reviewer checks completeness. The loop runs until both pass.

Plans pass review before execution begins. During execution, each milestone
passes review before the next starts.

### Cost-Effective Delegation

The orchestrator delegates to smaller agents -- Haiku for straightforward tasks,
Sonnet for moderate complexity. Prompts are injected just-in-time, giving
smaller models precisely the guidance they need at each step.

When quality review fails or problems recur, the orchestrator escalates to
higher-quality models. Expensive models are reserved for genuine ambiguity, not
routine work.

## Does This Actually Work?

I have not run formal benchmarks. I can only tell you what I have observed using
this workflow to build and maintain non-trivial applications entirely with
Claude Code -- backend systems, data pipelines, streaming applications in C++,
Python, and Go.

The problems I used to hit constantly are gone:

**Ambiguity resolution.** You ask an LLM "make me a sandwich" and it comes back
with a grilled cheese. Technically correct. Not what you meant. The planning
phase forces these misunderstandings to surface before you have built the wrong
thing.

**Code hygiene.** Without review cycles, the same utility function gets
reimplemented fifteen times across a codebase. The quality reviewer catches
this. The technical writer ensures documentation stays consistent.

**LLM-navigable documentation.** Function docs include "use when..." triggers.
CLAUDE.md files tell the LLM which files matter for a given task. The LLM stops
guessing which code is relevant.

Is it better than writing code by hand? I think so, but I cannot speak for
everyone. This workflow is opinionated. I am a backend engineer -- the patterns
should apply to frontend work, but I have not tested that. If you are less
experienced with software engineering, I would like to know whether this helps
or adds overhead.

If you are serious about LLM-assisted coding and want to try a structured
approach, give it a shot. I would like to hear what works and what does not.

## Quick Start

Clone into your Claude Code configuration directory:

```bash
# Per-project
git clone https://github.com/solatis/claude-config .claude

# Global (new setup)
git clone https://github.com/solatis/claude-config ~/.claude

# Global (existing ~/.claude)
cd ~/.claude
git remote add workflow https://github.com/solatis/claude-config
git fetch workflow
git merge workflow/main --allow-unrelated-histories
```

## Usage

The workflow for non-trivial changes: explore -> plan -> execute.

**1. Explore the problem.** Understand what you are dealing with. Figure out the
solution.

This is relatively free-form. If the project and/or surface area is particularly
large, use the `codebase-analysis` skill to explore the project's code properly
before proposing a solution.

**2. (Optional) Think it through.** I reach for `deepthink` very often, more than
any other skill. It handles analytical questions where you do not know the answer
structure yet -- taxonomy design, trade-offs, definitional questions, evaluative
judgments, exploratory investigations.

It auto-detects complexity. Quick mode reasons directly. Full mode launches
parallel sub-agents with different analytical perspectives, then synthesizes
through agreement patterns. Both self-verify.

So, for most analytical questions, deepthink is enough. It explores your
codebase when context is missing. Reach for specialized skills only when the
question is clearly scoped:

- `problem-analysis`: Root cause analysis specifically
- `decision-critic`: Stress-testing a specific decision

**3. Write a plan.** "Use your planner skill to write a plan to
plans/my-feature.md"

The planner runs your plan through review cycles -- technical writer for
clarity, quality reviewer for completeness -- until it passes.

The planner captures all decisions, tradeoffs, and information not visible from
the code so that this context does not get lost.

**4. Clear context.** `/clear` -- start fresh. You have written everything
needed into the plan.

**5. Execute.** "Use your planner skill to execute plans/my-feature.md"

The planner delegates to sub-agents. It never writes code directly. Each
milestone goes through the developer, then the technical-writer and
quality-reviewer. No milestone starts until the previous one passes review.

Where possible, it executes multiple tasks in parallel.

For detailed breakdowns of each skill, see their READMEs:

- [DeepThink](skills/deepthink/README.md)
- [Codebase Analysis](skills/codebase-analysis/README.md)
- [Problem Analysis](skills/problem-analysis/README.md)
- [Decision Critic](skills/decision-critic/README.md)
- [Planner](skills/planner/README.md)

### In Practice

I needed to migrate a legacy C# Windows Service from print-based logging to
something that actually rotates files.

The codebase had a homegrown Log() method writing to a single file with
File.AppendAllText. No rotation, no log levels, synchronous I/O blocking the
thread. Six Console.WriteLine calls scattered elsewhere went nowhere when
running as a service.

I started with exploration and analysis in a single prompt:

```
Use your codebase analysis skill to briefly explore this C# project,
with a focus on all the places where debug logs are currently emitted.

Then use your problem analysis skill to think through an appropriate
logging framework:
 * must work with .NET Framework 4.8.1
 * must support log rotation out of the box
 * we run multiple processes on the same machine, so it needs structured
   multi-process support
```

The codebase analysis found 31 call sites and the Console.WriteLine leakage. The
problem analysis evaluated NLog, Serilog, log4net, and
Microsoft.Extensions.Logging against my constraints.

The recommendation was NLog. It handles rotation and async out of the box.
Multi-process support comes from layout variables. Serilog would work but
requires three packages for the same functionality.

I agreed with the recommendation. Not a complicated decision, so I skipped the
`decision-critic` and moved to planning:

```
Use your planner skill to write an implementation plan to: plan-logging.md
```

The planner surfaced two ambiguities:

1. Replace all Log() call sites, or just the implementation? Obvious to a human,
   but worth clarifying upfront.
2. Log rotation defaults. The planner assumed 1-day rotation, but I also need
   size-based rotation at 1GB.

The plan went through review. The technical writer flagged comments that
explained what rather than why -- the NLog.config had comments like "configures
file target" instead of explaining the rotation strategy. The quality reviewer
caught two issues I would have missed: no explicit LogManager.Shutdown() in the
service's OnStop() handler, and incorrect file paths missing the src/ prefix.

These are the bugs that ship to production when you skip review cycles. The
shutdown issue would have caused log loss on service restart. The path issue
would have failed silently.

After fixes, I cleared context and executed:

```
Use your planner skill to execute: @plan-logging.md
```

The developer, debugger, technical writer, and quality reviewer run the
implementation. Each milestone passes review before the next starts. If the
implementation deviated from the plan, I would know.

## Other Skills

Not every task needs the full planning workflow. These skills handle specific
concerns.

### DeepThink

I use this skill multiple times a day -- whenever I do not know what shape the
answer should take.

Unlike `problem-analysis` or `decision-critic`, deepthink has no fixed
structure. It handles trade-offs, taxonomy questions, evaluative judgments --
whatever you throw at it.

So, when do I reach for it?

Meta-cognitive debugging. I keep making the same mistake. The LLM keeps
misunderstanding the task. Why? Something is broken and I need to see it before
I can fix it.

Strategy evaluation. Multiple valid approaches exist (and gut feel is not
enough). PDF conversion: download the TeX source, parse the PDF directly, or
let the LLM render it visually. S3 artifact versioning: timestamp paths,
pointer files, checksums. Systematic comparison beats intuition.

Best practices research. What is the canonical approach? How do mature CI/CD
systems handle artifact versioning? Industry patterns likely exist -- I just do
not know them yet.

Architecture and design. How should these components interact? Where do the
delegation boundaries go? I think them through before committing to code.

Consolidation decisions. Should these two skills be merged? Do they serve
distinct purposes, or am I maintaining unnecessary complexity?

Two modes, auto-detected. Quick mode reasons directly. Full mode launches
parallel sub-agents with distinct analytical perspectives, then synthesizes
through agreement patterns.

```
Use your deepthink skill to think through [question]
```

For explicit mode selection:

```
Use your deepthink skill (quick) to [question]
Use your deepthink skill (full) to [question]
```

### Refactor

LLM-generated code accumulates technical debt. The LLM does not see duplication
across files or notice god functions growing.

The refactor skill explores multiple dimensions in parallel -- naming,
extraction, types, errors, modules, architecture, abstraction -- validates
findings against evidence, and outputs prioritized recommendations. It does not
generate code; it tells you what to fix and why.

Use it when:

- After LLM-generated features work but feel messy
- Before major changes to identify friction points
- Code review reveals structural issues
- Simple changes require touching many files

```
Use your refactor skill on src/services/
```

With focus area:

```
Use your refactor skill on src/ -- focus on refactoring the rendering engine so that it can be reused in multiple components.
```

### Prompt Engineer

This workflow consists entirely of prompts. Each can be optimized individually.

The skill analyzes prompts, proposes changes with explicit pattern attribution,
and waits for your approval before applying anything.

Use it when:

- A sub-agent definition is not performing as expected
- Optimizing a skill's Python script prompts
- Reviewing a multi-prompt workflow for consistency

```
Use your prompt engineer skill to optimize the system prompt for agents/developer.md
```

The skill was optimized using itself.

### Doc Sync

The CLAUDE.md/README.md hierarchy requires maintenance. The structure changes
over time. Documentation drifts.

The doc-sync skill audits and synchronizes documentation across a repository.

Use it when:

- Bootstrapping the workflow on an existing repository
- After major refactors or directory restructuring
- Periodic audits to check for documentation drift

If you use the planning workflow consistently, the technical writer agent
handles documentation as part of execution. Doc-sync is primarily for
bootstrapping or recovery.

```
Use your doc-sync skill to synchronize documentation across this repository
```

For targeted updates:

```
Use your doc-sync skill to update documentation in src/validators/
```
---

## Contact

**Project owner:** Steven (steveneam on GitHub)
**Private dev repo:** github.com/steveneam/eamos-dev (push target — main branch)
**Push method:** GitHub REST API (no git binary; `GITHUB_PAT` in `app/backend/.env`)
