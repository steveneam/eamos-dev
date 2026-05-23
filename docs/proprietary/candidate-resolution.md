# Source-Backed Candidate Resolution

Status: First-slice backend prototype
Type: Interpreter/resolver service
Owner: Codex backend
Added: 2026-05-21 19:07 +1000 - Codex
Last updated: 2026-05-23 18:00 +1000 - Codex

## What It Does

Source-Backed Candidate Resolution is the web-facing search interpretation
layer added for the Variant Evidence Report search bar. It wraps the
deterministic Eamos Search Input Resolver, exposes parse preview, and returns
auto-selected candidates, ranked choices, or recommendations before the
frontend asks the user to clarify.

This is not a separate CLI. It is a backend service and API contract.

## Why It Is Eamos-Original

The custom part is the candidate-gating behavior:

- Uses one raw search field (`search_text`) while preserving the legacy
  structured lookup contract.
- Returns auditable interpretation modes such as `deterministic`,
  `auto_resolved`, `needs_selection`, and `suggestions`.
- Auto-selects only when exactly one high-confidence source-backed candidate
  supports the interpreted intent.
- Returns ranked choices when multiple plausible candidates exist.
- Returns near-miss recommendations instead of dead-end "not found" style
  behavior.
- Keeps AI output behind deterministic validation and source-backed candidate
  resolution; the Task 4 AI extractor proposes intent only.

## Source Of Truth

- Interpreter: `app/backend/app/services/search_input_interpreter.py`
- Candidate resolver: `app/backend/app/services/search_candidate_resolver.py`
- AI extractor: `app/backend/app/services/search_input_ai.py`
- Curated AI lexicon: `app/backend/app/fixtures/search_input_lexicon.json`
- First-slice candidate records:
  `app/backend/app/fixtures/search_candidate_records.json`
- Schemas: `app/backend/app/schemas/lookup.py`
- Route: `app/backend/app/api/routes/lookup.py`
- Lookup wiring: `app/backend/app/services/lookup_service.py`
- API surfaces:
  - `POST /api/v1/lookup/parse`
  - `POST /api/v1/lookup` with `search_text` or `query`
  - optional `LookupResponse.search_interpretation`
- Tests:
  - `app/backend/tests/test_variant_search_integration.py`
  - `app/backend/tests/test_frontend_contract.py`
  - `app/backend/tests/test_search_input_resolver.py`
  - `app/backend/tests/test_lookup_normalize.py`
- Plans:
  - `plans/search-bar-ai-input/spec.md`
  - `plans/search-bar-ai-input/plan.md`

## Current Examples

- `RPE65:c.260A>G` -> deterministic lookup.
- `1-68444869-T-C` -> source-backed auto-resolution to RPE65 `c.260A>G` when
  the curated candidate fixture supports it.
- `RPE65:c.259A>G` -> near-miss suggestion toward reported `c.260A>G`.
- `CFTR:p.Leu441fs` -> recommendation toward
  `CFTR c.1321_1323del (p.Leu441del)`, not auto-selection of a non-existent
  frameshift.
- `CFTR:p.Leu441del` -> auto-resolution to the curated candidate.

## Current Verification

On 2026-05-21, focused lookup/search/contract tests, `ruff`, `black --check`,
and the full backend `pytest` suite passed with existing JWT test-key warnings
only.

## Caveats

- The candidate provider is currently a small source-labeled fixture boundary,
  designed to be replaced or expanded with ClinVar/MyVariant/local-index
  candidate search.
- Plain-language AI extraction is mock-first and disabled by default. Live AI
  smoke remains a separate approved task.
- Frontend candidate picker and interpretation chips are Claude-owned unless
  explicitly redirected.
