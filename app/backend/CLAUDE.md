# backend/

FastAPI + Python. Genomic variant pipeline: intake → tools → rules engine → draft → review.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `pyproject.toml` | Project name (`eamos-backend`), Python ≥3.10, test and lint config | Dependency or config changes |
| `requirements.txt` | Pinned runtime dependencies | Installing deps, adding packages |
| `README.md` | Architecture diagram, all routes, tool registry, config table, setup | First-time orientation, route questions |
| `app/main.py` | FastAPI app entry point, router registration, CORS | Adding routes, changing middleware |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `app/` | Python package root — entry point, all subpackages | First stop for backend code navigation |
| `app/api/routes/` | HTTP route handlers: auth, health, lookup, reports, runs, reviews, search | Adding or modifying an endpoint |
| `app/tools/` | Data-fetch tools: ClinVar, VEP, SpliceAI, Franklin, gnomAD, PubMed, ClinicalTrials | Adding a data source, debugging a fetch |
| `app/services/` | Business logic: workflow, lookup_service, draft_render, variant_decoder, recommendation | Changing pipeline or draft logic |
| `app/rules/` | ACMG classification rules engine | Classification or evidence-strength logic |
| `app/schemas/` | Pydantic request/response models (run, lookup, report, auth) | Type changes, API contract changes |
| `app/core/` | Config, DB session, auth deps, logging | Environment variables, DB, auth middleware |
| `app/fixtures/` | Fixture JSON for every tool (offline dev mode) | Understanding mock data shape |
| `app/agents/` | LLM client wrapper, prompts, tool bindings | LLM prompt changes, model switching |
| `app/repos/` | SQLite data-access layer (reports, runs, users, search) | DB query changes |
| `tests/` | pytest test suite — API, integration, smoke tests | Running or adding tests |

## Runtime flags

| Variable | Default | Effect |
| -------- | ------- | ------ |
| `USE_REAL_APIS` | `false` | `false` = tools return fixture JSON; `true` = live external calls (blocked on IT) |
| `LLM_PROVIDER` | `mock` | `mock` = no LLM calls; `openai` = live GPT-4o-mini via LangChain |
| `JWT_SECRET` | required | App refuses to start without this set |

## Development

```powershell
cd app/backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
# API:  http://localhost:8000/api/v1
# Docs: http://localhost:8000/docs
```
