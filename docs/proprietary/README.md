# Eamos Proprietary Catalogue

This folder is an engineering catalogue for Eamos-original scripts,
algorithms, CLIs, and orchestration logic created during the project. It is an
index, not a second source tree: implementation stays in `app/`, tests stay in
`tests/`, and plans stay in `plans/`.

The goal is simple: when Codex or Claude builds something project-original and
worth remembering, add a short entry here so it is easy to find later.

## Timestamp Rule

Every proprietary catalogue entry must record when the entry was added and
when it was last updated, using local project time:
`YYYY-MM-DD HH:MM +zzzz - Agent`.

Update both the human-readable entry and `index.json` whenever the underlying
script, algorithm, CLI, service, or orchestration behavior changes.

## What Belongs Here

- Custom algorithms or service pipelines built for Eamos.
- Developer CLIs created for Eamos workflows.
- Project-specific orchestration logic that coordinates third-party sources in
  a novel or reusable way.
- Mock-first or fixture-backed prototypes that may become product IP.

## What Does Not Belong Here

- Third-party APIs, papers, source docs, or copied external code.
- Generic wrappers with no Eamos-specific behavior.
- Runtime secrets, credentials, customer data, or patient data.
- Full duplicated source code from `app/`.

## Current Entries

| Entry | Type | Added | Last updated | Implementation |
| --- | --- | --- | --- | --- |
| [EP-VLEx](./ep-vlex.md) | Backend algorithm/service | 2026-05-19 19:56 +1000 - Codex | 2026-05-23 18:00 +1000 - Codex | `app/backend/app/services/publication_literature.py` |
| [Eamos Search Input Resolver + CLI](./eamos-search-input.md) | Parser/resolver + developer CLI | 2026-05-21 17:54 +1000 - Codex | 2026-05-23 18:00 +1000 - Codex | `app/backend/app/services/search_input_resolver.py`, `app/backend/app/cli/eamos_search_input.py` |
| [Source-Backed Candidate Resolution](./candidate-resolution.md) | Backend interpreter/resolver | 2026-05-21 19:07 +1000 - Codex | 2026-05-23 18:00 +1000 - Codex | `app/backend/app/services/search_input_interpreter.py`, `app/backend/app/services/search_candidate_resolver.py` |
| [Search Input AI Extractor + Lexicon](./search-input-ai.md) | Mock-first AI extraction service | 2026-05-21 23:09 +1000 - Codex | 2026-05-23 18:00 +1000 - Codex | `app/backend/app/services/search_input_ai.py`, `app/backend/app/fixtures/search_input_lexicon.json` |
| [Variant Report Data Orchestrator](./variant-report-orchestration.md) | Backend orchestration layer | 2026-05-23 12:10 +1000 - Codex | 2026-05-23 19:51 +1000 - Codex | `app/backend/app/services/variant_report_orchestrator.py`, `app/backend/app/services/report_extraction_plan.py`, `app/backend/app/services/population_frequency_section.py`, `app/backend/app/tools/gene_disease.py`, `app/backend/app/tools/molecular_context.py`, `app/backend/app/tools/computational_annotations.py` |
| [gnomAD Genetic Ancestry Map Anchors](./gnomad-ancestry-map.md) | UI mapping algorithm | 2026-05-24 01:56 +1000 - Codex | 2026-05-24 03:38 +1000 - Codex | `app/frontend/src/components/report/gnomadAncestryMap.ts`, `app/web/components/report/gnomadAncestryMap.ts` |

Machine-readable index: [index.json](./index.json).

## Entry Template

Use this shape for future additions:

```md
# Name

Status: Prototype | Active | Deprecated
Type: Algorithm | CLI | Service | Orchestration layer
Owner: Codex | Claude | Shared
Added: YYYY-MM-DD HH:MM +zzzz - Agent
Last updated: YYYY-MM-DD HH:MM +zzzz - Agent

## What It Does

Short plain-language summary.

## Why It Is Eamos-Original

What logic, workflow, ranking, extraction, or source orchestration is custom.

## Source Of Truth

- Implementation files
- API or CLI entry points
- Tests
- Plans/specs

## Caveats

Known limits, non-goals, source dependencies, and safety constraints.
```
