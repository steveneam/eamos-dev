# Eamos — Genomic Intelligence Platform

Variant intelligence web tool: a researcher or clinician types a gene and variant (HGVS notation) and gets an aggregated evidence report from ClinVar, VEP, SpliceAI, gnomAD, AlphaMissense, and more — in one place. Full product spec, database stack, and architecture in `README.md`.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `README.md` | Full project spec: layers, database stack, report structure, HGVS table, design reference | Onboarding, spec questions, product vision |
| `PROGRESS.md` | Session-by-session build log | Checking what has been built |
| `CHANGELOG.md` | Feature changelog | Reviewing recent changes |
| `DESIGN.md` | Design system, styling items 2–16 | Frontend styling work |
| `ROADMAP.md` | Planned feature phases | Understanding build sequence |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `app/` | Frontend (React/Vite/Tailwind) + Backend (FastAPI/Python) + shared contracts | All code work |
| `docs/` | Architecture guides, API research, design brief, design system | Database API details, architecture decisions, design |
| `pitch/` | Pitch deck outline and speaking notes | Presentation work |
| `archive/` | Retired drafts and historical session notes | Historical context only |
| `.claude/` | Agent roles, conventions, output styles, skills | Workflow, agent config, conventions |

## Development

```
# Start frontend dev server
cd app/frontend && npm run dev
# → http://localhost:5173

# Node.js portable (Windows): C:\temp\node\node-v22.15.0-win-x64
# Backend root: app/backend/
# LLM default: provider=mock (offline dev) — never assume use_real_apis=True
```

## Critical Rules — Never Break These

1. **DNA notation leads** — always `c.cdna` first, protein `(p.xxx)` second.
   CORRECT: `RPE65 c.260A>G (p.Asp87Gly)` — WRONG: `RPE65 p.Asp87Gly`.
   Apply everywhere: report headers, variant tabs, search results, search bar placeholder, plain language decoder.

2. **Gene-agnostic — never hardcode** a gene name, variant, or ClinVar ID.
   All API calls constructed dynamically: `f"{variant.gene}:{variant.cdna}"`.

3. **Source link on every data point** — every score, classification, or number must hyperlink to its source database. Dotted underline, opens in new tab.

4. **Plain language first** — every report opens with a plain English explanation of the variant notation before any technical sections. Written for a non-specialist clinician. No jargon. One short paragraph.

5. **AI drafts, human checks** — never autonomous clinical decisions. Every AI-generated section must be labelled AI-generated and subject to clinician review.

6. **Active voice, clinical register, no hedging** — lead with the gene, variant, or clinical finding. Never open with "This report…", "Based on…", "It should be noted…", "Please note…".

7. **Every score needs a number with units** — clinical bullets must cite actual values.
   WRONG: "ERG shows reduced responses"
   RIGHT: "Scotopic b-wave ~18 µV (reference: >150 µV) reflects severe rod system dysfunction"

Do not discuss the pet genetics business in any public-facing code, comments, or documentation.

## Immediate Next Tasks

1. **Therapeutic Landscape** — wire `GENE_THERAPY_MAP` in `app/backend/app/services/` and populate `therapeutic_landscape` in both `ReportPayload` builders. Add ClinicalTrials.gov REST API v2 call (recruiting/active only, filtered by gene name) following the ClinVar/PubMed tool pattern in `app/backend/app/tools/`.

2. **Frontend styling pass** — items 2–16 from `DESIGN.md`: font weights, logo placeholder, species toggle pill shape, input border-radius, card shadows, accessibility (contrast/focus), gene-only search mode, idle state polish, scroll-to-results, loading skeleton. Patient Report accessed via ghost button on landing page — mode-switching tabs removed from header.

3. **Live API test** — set `USE_REAL_APIS=true` in `.env`, run pipeline with `RPE65:c.260A>G`. Blocked on IT network clearance for Python outbound connections. Confirm SpliceAI REST endpoint accepts `GENE:c.cdna` format.

4. **Wire frontend to real backend** — replace mock data in React app with live FastAPI responses. Requires task 3 first.

5. **Rotate GitHub PAT** — token from session 4 was exposed in chat. Generate new one in GitHub settings and update `.env`.
