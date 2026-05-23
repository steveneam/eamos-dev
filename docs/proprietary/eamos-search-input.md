# Eamos Search Input Resolver And CLI

Status: Active backend prototype
Type: Parser/resolver plus developer CLI
Owner: Codex backend
Added: 2026-05-21 17:54 +1000 - Codex
Last updated: 2026-05-23 18:00 +1000 - Codex

## What It Does

The Eamos Search Input Resolver converts user-supplied variant text into
normalized internal fields and source-specific query inputs for Variant
Validator, Ensembl VEP, gnomAD, SpliceAI, ClinVar, and literature lookup.

The developer CLI exposes that parser from the command line:

```powershell
cd app/backend
python -m app.cli.eamos_search_input "RPE65:c.260A>G"
```

It can also read a file of examples and emits JSON bundles for parser/source
debugging.

## Why It Is Eamos-Original

The custom part is the Eamos-specific resolver/orchestrator:

- Accepts exact user formats such as `GENE:c.`, transcript HGVS with gene
  annotation, rsID, RefSeq genomic HGVS, gnomAD-style `chr-pos-ref-alt`, and
  simple VCF-like typed coordinates.
- Normalizes variants without lowercasing HGVS.
- Resolves missing MANE/RefSeq transcript context in live mode.
- Converts supported genomic IDs into source-appropriate identifiers.
- Emits separate source inputs instead of sending one brittle string to every
  provider.

## Source Of Truth

- Resolver: `app/backend/app/services/search_input_resolver.py`
- CLI: `app/backend/app/cli/eamos_search_input.py`
- Shared helpers: `app/backend/app/services/sequence_context.py`
- Tests:
  - `app/backend/tests/test_search_input_resolver.py`
  - `app/backend/tests/test_lookup_normalize.py`
  - `app/backend/tests/test_eamos_search_input_cli.py`
  - `app/backend/tests/test_tool_invariants.py`
- Plans:
  - `plans/v2-backend.md`
  - `plans/search-bar-ai-input/spec.md`
  - `plans/search-bar-ai-input/plan.md`

## Current Verification

The resolver and CLI were verified with focused backend tests and direct CLI
fixture-mode runs against the user-supplied variant test stack. Later full
backend verification also passed after the web search-input layer was added.

## Caveats

- This layer is deterministic. It does not perform AI extraction.
- Live transcript and coordinate hydration depend on configured external
  source availability.
- Exact source calls still use downstream provider adapters and their own
  availability/fallback rules.
