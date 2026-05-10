# app/

Python package root for the FastAPI backend. Contains the app entry point and all subpackages.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `main.py` | FastAPI app entry point, router registration, CORS config | Adding routes, changing middleware |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `api/` | HTTP layer — route handlers grouped by resource | Adding or modifying an endpoint |
| `tools/` | Data-fetch tools: one file per external database | Adding a data source, debugging a fetch |
| `services/` | Business logic: pipeline orchestration, draft rendering, variant decoding | Changing pipeline or draft logic |
| `rules/` | ACMG evidence classification rules engine | Classification or evidence-strength logic |
| `schemas/` | Pydantic request/response models | Type changes, API contract changes |
| `core/` | Config, DB session, auth dependencies, logging setup | Environment variables, DB, auth middleware |
| `fixtures/` | Fixture JSON for offline dev mode | Understanding mock data shape |
| `agents/` | LLM client wrapper, prompt templates, LangChain tool bindings | LLM prompt changes, model switching |
| `repos/` | SQLite data-access layer | DB query changes |
