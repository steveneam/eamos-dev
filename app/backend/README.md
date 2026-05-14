# Eamos Backend

FastAPI backend for the Eamos genomic variant intelligence platform.
Accepts sequencing report uploads, runs the variant evidence pipeline,
and returns structured clinical report drafts for clinician review.

## Architecture

```
PDF upload
    ↓
PDF extractor (LLM-backed or fixture fallback)
    ↓
Variant evidence tools (ClinVar, Ensembl VEP, SpliceAI, Franklin, gnomAD, PubMed, ClinicalTrials.gov)
    ↓
Rules engine (ACMG criteria, classification tiers)
    ↓
Report draft (LLM-generated sections, AI-labelled)
    ↓
Clinician review → finalize → PDF export
```

## Project layout

```
app/
  api/routes/     HTTP route handlers (reports, runs, reviews, search, auth, health)
  agents/         LLM client, prompts, tool wrappers
  core/           config.py (Settings), db.py (SQLAlchemy)
  fixtures/       Fixture JSON for each tool (used when use_real_apis=False)
  repos/          Database access layer
  rules/          Deterministic rules engine (clinic_rules.py)
  schemas/        Pydantic request/response models
  services/       workflow.py (pipeline orchestration), variant_decoder.py
  tools/          clinvar.py, ensembl_vep.py, spliceai.py, franklin.py, gnomad.py, pubmed.py, clinical_trials.py
tests/            pytest suite (SQLite for local, Postgres for Docker integration)
```

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/reports/upload` | Upload a sequencing report PDF |
| POST | `/api/v1/reports/{report_id}/run` | Run the evidence pipeline for a report |
| POST | `/api/v1/runs/batch` | Run multiple reports as a batch |
| POST | `/api/v1/reports/{report_id}/review` | Submit clinician review for a report |
| POST | `/api/v1/runs/{run_id}/review` | Submit clinician review for a run |
| POST | `/api/v1/runs/{run_id}/finalize` | Lock a reviewed run |
| GET  | `/api/v1/runs/{run_id}/final.pdf` | Download the finalized PDF |
| GET  | `/api/v1/healthz` | Health check |

## Evidence tools

| Tool | Source | Input | Live when |
|------|--------|-------|-----------|
| ClinVar | NCBI E-utilities | `GENE:c.cdna` → esearch → esummary | `USE_REAL_APIS=true` |
| Ensembl VEP | rest.ensembl.org | `TRANSCRIPT:c.cdna` | `USE_REAL_APIS=true` |
| SpliceAI | Broad Institute | `GENE:c.cdna` | `USE_REAL_APIS=true` |
| Franklin | api.genoox.com | `GENE:c.cdna` + auth | `USE_REAL_APIS=true` + Franklin credentials |
| gnomAD | gnomAD GraphQL API | `GENE:c.cdna` → allele frequency, homozygous count | `USE_REAL_APIS=true` |
| PubMed | NCBI E-utilities (esearch + esummary) | gene + variant keywords → abstracts, article metadata | `USE_REAL_APIS=true` |
| ClinicalTrials.gov | ClinicalTrials REST API v2 | gene name → recruiting/active trials | `USE_REAL_APIS=true` |

All tools fall back to fixture JSON when `USE_REAL_APIS=false` (default).
The variant plain-language decoder (`services/variant_decoder.py`) runs
offline — pure regex/template, no API call.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then edit .env — JWT_SECRET is required
```

`JWT_SECRET` has no default and must be set explicitly. Use at least 32
random characters.

```bash
uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000
```

## Configuration (`.env`)

| Key | Default | Notes |
|-----|---------|-------|
| `JWT_SECRET` | — | **Required.** No default. |
| `JWT_ALGORITHM` | `HS256` | |
| `JWT_TTL_DAYS` | `7` | |
| `USE_REAL_APIS` | `false` | Set `true` to call live databases |
| `LLM_PROVIDER` | `mock` | `openai` to enable GPT-4o-mini |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `FRANKLIN_API_TOKEN` | — | Or set `FRANKLIN_EMAIL` + `FRANKLIN_PASSWORD` |
| `DATABASE_URL` | SQLite | Switch to Postgres URL for production |

## Testing

```bash
pytest                       # local — uses SQLite
docker compose up --build    # integration — uses Postgres
```

AI-backed extraction tests are skipped automatically when no API key is set.

## Guardrail

Patient uploads must never silently fall back to fixture extraction.
Do not increase backend complexity beyond what the demo requires.
