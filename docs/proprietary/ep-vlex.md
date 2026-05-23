# EP-VLEx

Status: Active backend prototype
Type: Algorithm/service
Owner: Codex backend
Added: 2026-05-19 19:56 +1000 - Codex
Last updated: 2026-05-23 18:00 +1000 - Codex

## What It Does

EP-VLEx, the Eamos Proprietary Variant Literature Extractor, builds a
variant-specific publication inventory for the Variant Evidence Report. It
generates variant aliases, aggregates PMID candidates across sources,
deduplicates publications, attaches source tags/snippets where available, and
supports paginated expansion beyond the initial report rows.

## Why It Is Eamos-Original

The custom part is the orchestration and ranking layer:

- Builds a term bundle from gene, cDNA HGVS, transcript HGVS, protein aliases,
  rsID, and genomic aliases.
- Aggregates PMID evidence across LitVar2, PubMed, and ClinVar citation-like
  source structures.
- Deduplicates PMIDs while preserving source breakdown.
- Labels snippet provenance/status instead of fabricating text when only
  table, supplemental, or citation-only evidence is available.
- Separates general publication inventory from functional-study counting.

## Source Of Truth

- Service: `app/backend/app/services/publication_literature.py`
- Lookup wiring: `app/backend/app/services/lookup_service.py`
- Schemas: `app/backend/app/schemas/run.py`
- API surfaces:
  - `POST /api/v1/lookup` -> `report_payload.publications_literature`
  - `POST /api/v1/lookup/publications`
- Tests:
  - `app/backend/tests/test_publication_literature.py`
  - `app/backend/tests/test_variant_search_integration.py`
  - `app/backend/tests/test_variant_cache.py`
  - `app/backend/tests/test_frontend_contract.py`
- Plans:
  - `plans/variant-literature-extraction/design.md`
  - `plans/variant-literature-extraction/spec.md`
  - `plans/variant-literature-extraction/plan.md`

## Current Verification

Recorded in `PROGRESS.md` and `plans/v2-backend.md`. The latest full backend
suite after later search-input work passed on 2026-05-21 with existing JWT
test-key warnings only.

## Caveats

- EP-VLEx is the general publication inventory, not the functional evidence
  study counter.
- It does not assign final ACMG PS3/BS3 strength.
- PubTator/PMC full-text extraction remains a future quality upgrade.
- Frontend rendering/mirroring remains Claude-owned unless explicitly
  redirected.
