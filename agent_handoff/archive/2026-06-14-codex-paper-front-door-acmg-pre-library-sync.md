# Codex Prior Section Archive - 2026-06-14 20:17 +10:00

Archived verbatim before replacing `agent_handoff/CURRENT.md` -> `## Codex - Last Task & Resume`.

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-06-14 19:38 +10:00 - Codex. Prior Codex section archived at `agent_handoff/archive/2026-06-14-codex-paper-front-door-pre-replace.md`.

**Latest Codex update (2026-06-14 19:38 +10:00 - Codex):**
Paper front door and ACMG-viz Step 0 contract freeze are complete locally. I also tightened the protein-only resolver after Steven's His313 feedback: same-gene/same-residue recommendations are source-backed, gene-agnostic, and round-trip through candidate selection; distant same-gene cDNA fallbacks are not returned.

Completed:
- Added `POST /api/v1/paper-variants/extract` in `app/backend/app/api/routes/paper_variants.py`, wired into the API router. It accepts JSON `{text}` or multipart PDF (`file`/`pdf`), uses `pdf_text.extract_pdf_text`, requires login via `require_authenticated_principal`, and uses the chat rate limiter per authenticated user.
- Added `PaperVariantsExtractRequest`, `PaperVariantsPdfMeta`, `PaperVariantsGuardrails`, and `PaperVariantsExtractResponse`; response stays sanitized and includes CLI-style mode/generated/provider/pdf/guardrail/count metadata.
- Kept the extractor mock-first unless `LLM_PROVIDER=gateway`; no provider/env flip.
- Extended `SearchCandidateResolver` to take settings and query already-materialized local ClinGen eRepo rows for same-residue protein candidates when `clingen_local_enabled` is true. It uses bounded read-only SQLite queries, no startup/download/materialization path, no request-time checksum sweep, and keeps source labels.
- Added dynamic local candidate-id lookup so a gene-agnostic local ClinGen recommendation can be selected later, not only displayed.
- Seeded the two RPE65 His313 ClinVar examples Steven named: `VCV001679125` c.938A>G/p.His313Arg and `VCV001180616` c.938A>C/p.His313Pro. Local ClinGen proves the Arg row; NCBI E-utilities confirmed the Pro row maps to ClinVar Variation ID 1180616 and ClinGen Allele Registry CA340744823.
- Tightened protein-only behavior: exact clinical protein matches can auto-resolve; experimental protein constructs stay fail-closed as candidate lists even if an exact source-backed candidate exists. Same-residue/different-substitution candidates are medium confidence and require user selection.
- Added the ACMG-viz Step 0 schema only in `app/backend/app/schemas/run.py`: `ReportPayload.eamos_computed_classification` plus the nested `EamosComputed*` Pydantic models per spec section 3. Did not touch `clinical_consensus.py`.
- Added/updated tests for auth/rate-limit endpoint behavior, PDF/JSON response metadata, source-backed protein candidate ranking, gene-agnostic local ClinGen recommendation + selection round-trip, experimental fail-closed semantics, and the ACMG contract canary.

Verification recorded 2026-06-14 19:38 +10:00:
- `git fetch origin` passed at session start; `git status --short --branch` showed `main...origin/main` and the expected dirty backend/frontend/docs/graph worktree.
- `python -m pytest tests/test_paper_variants.py tests/test_rate_limits.py tests/test_report_acmg_contract.py tests/test_search_input_resolver.py tests/test_variant_search_integration.py tests/test_lookup_normalize.py tests/test_tool_invariants.py tests/test_clingen_local.py -q` passed.
- `python -m ruff check app/api/routes/paper_variants.py app/api/routes/__init__.py app/schemas/paper_variants.py app/schemas/run.py app/services/paper_variants.py app/services/search_candidate_resolver.py app/services/clingen_local.py app/services/search_input_interpreter.py tests/test_paper_variants.py tests/test_variant_search_integration.py tests/test_rate_limits.py tests/test_report_acmg_contract.py tests/test_clingen_local.py` passed.
- `python -m black --check ...` for the same backend/schema/test files passed (with the known Python 3.10/3.15 Black parser warning only).
- Real PDF smoke on Steven's RPE65 paper passed: H68Y/H182A/H313A/H527A rows were gene `RPE65`, `context=experimental_construct`, `validated=false`, and returned source-backed same-residue candidates where available. H313A candidates were c.938A>G/p.His313Arg and c.938A>C/p.His313Pro.
- `python -m pytest tests/test_frontend_contract.py -q` currently fails as expected until Claude mirrors `eamos_computed_classification` in both frontend `backend.ts` files and restores byte identity between them.
- `git diff --check` passed with line-ending warnings only.
- `node scripts/eamos-encoding-scan.mjs ... --json` passed with no findings for the touched backend/schema/test/handoff files.
- `python -m graphify update .` passed; graph HTML was skipped due >5000 nodes as before.

Guardrails:
- No Render env/provider flip, Supabase mutation, startup download/materialization, commit, push, RAG enablement, AI-gateway runtime flip, or `clinical_consensus.py` edits.
- Keep `LLM_PROVIDER=mock`, `RAG_ENABLED=false`, `CRISPR_OFFTARGET_PROVIDER=auto`, and `PRIMER_SPECIFICITY_PROVIDER=template`.
- Frontend files under `app/web/**` / `app/frontend/**` remain Claude-owned; Codex did not edit the contract mirrors.

Message for Claude:
- Backend contract to mirror: `POST /api/v1/paper-variants/extract` and `PaperVariantsExtractResponse` from `schemas/paper_variants.py`; `ValidatedPaperVariant` now includes `resolved_candidate_id`, `source_support`, `source_inputs`, ranked `candidates`, `resolver_warnings`, and `resolver_provenance`.
- ACMG contract to mirror: `ReportPayload.eamos_computed_classification?: EamosComputedClassification | null` and nested shape from `schemas/run.py` / `docs/report-acmg-viz/spec.md` section 3.
- `tests/test_frontend_contract.py` is the current coordination canary and is expected red until the mirror is done.

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-14 19:38 +1000 - Codex paper front door + ACMG contract complete
Eamos. Read CODEX.md, AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, docs/paper-variants-ui/spec.md, docs/report-acmg-viz/spec.md, docs/report-acmg-viz/plan.md, then run git fetch origin && git status --short --branch.
Delta: backend `POST /api/v1/paper-variants/extract` is complete locally, protein-only source-backed recommendations are gene-agnostic/fail-closed, and ACMG-viz Step 0 `ReportPayload.eamos_computed_classification` is frozen in Pydantic. Verification green for backend pytest/Ruff/Black/diff-check/encoding/graphify; real RPE65 PDF smoke returns H313A -> c.938A>G and c.938A>C candidates; frontend contract canary is red only because Claude still needs to mirror backend.ts.
Next: coordinate with Claude to mirror `PaperVariantsExtractResponse` + `eamos_computed_classification` in `app/frontend/src/lib/backend.ts` and `app/web/lib/backend.ts`; then rerun `tests/test_frontend_contract.py`. Do not start ACMG points engine, VCEP overlay, AI narration, benchmark harness, ClinVar P/B precompute, Render/Supabase/startup-download/provider flip, commit, or push unless explicitly asked. End clear-safe.
```
