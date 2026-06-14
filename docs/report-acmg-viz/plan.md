# Report ACMG Viz Backend Plan

Status: prepared for next Codex session
Source spec: `docs/report-acmg-viz/spec.md`
Prepared: 2026-06-14 16:14 +1000 - Codex

## Task 0 - Freeze Backend Contract

Goal: add the frozen `eamos_computed_classification` contract to `app/backend/app/schemas/run.py` so Claude can build `lib/acmg/points.ts` and SVG instruments against a stable mock.

Context: this is backend-led and must land before frontend implementation. Do not implement engine behavior in this task beyond schema/model shape and fixture-safe serialization.

Relevant files:
- `docs/report-acmg-viz/spec.md` section 3
- `app/backend/app/schemas/run.py`
- `app/backend/tests/test_frontend_contract.py`

Proposed approach:
- Add Pydantic models for version pin, conflict, per-criterion rows, and `EamosComputedClassification`.
- Add `ReportPayload.eamos_computed_classification: EamosComputedClassification | None = None`.
- Preserve exact fields from spec section 3: `net_points`, `sum_pathogenic`, `sum_benign`, `tier`, `conflict`, `ba1_override`, `posterior`, `benign_cut`, `per_criterion[]`, and `acmg_version_pin`.
- Use Literal enums where the contract has closed values.

Acceptance criteria:
- `/report` payload schema can serialize a mock `eamos_computed_classification` block.
- Contract is additive and does not disturb existing `clinical_consensus`, `acmg_worksheet`, or `acmg_classification`.
- Claude can mirror the schema without guessing field names or enum values.

Verify:
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q`
- `cd app/backend && python -m ruff check app/schemas/run.py tests/test_frontend_contract.py`
- `cd app/backend && python -m black --check --target-version py310 app/schemas/run.py tests/test_frontend_contract.py`

Out of scope:
- Engine math, source wiring, frontend mirrors, SVG components.

## Task 1 - Points Core Advisory Engine

Goal: create `app/backend/app/services/acmg_points_engine.py` as a separate advisory engine with Tavtigian-2020 point math and posterior calculation.

Context: do not modify `clinical_consensus.py`. The new engine is Eamos-computed advisory output, distinct from curated ClinGen/ClinVar precedence.

Relevant files:
- `docs/report-acmg-viz/spec.md` sections 3-4
- `app/backend/app/services/computational_calibration.py`
- `app/backend/app/services/pvs1_nmd.py`
- `app/backend/app/schemas/run.py`
- New `app/backend/tests/test_acmg_points_engine.py`

Proposed approach:
- Implement strength-to-points as applied per criterion, not fixed per code.
- Compute `sum_pathogenic`, `sum_benign`, `net_points`, `tier`, and `posterior`.
- Formula: `OddsPath = 2.08 ** net`; `posterior = (OddsPath * 0.10) / ((OddsPath - 1) * 0.10 + 1)`.
- Implement Tavtigian default cuts: P >= +10, LP +6..+9, VUS 0..+5, LB -1..-6, B <= -7.
- Keep `acgs_panel` benign cut available but only selected by future VCEP overlay.
- Implement BA1 hard benign override and discordance cap to VUS.
- Emit unassessed v1 criteria as `triggered=false`, `applied_strength=null`, `points=0`, with source/provenance fields where known.

Acceptance criteria:
- Posterior anchors pass for net 0, +6, +9, +10, -1, -7.
- Worked examples pass: Very Strong + Strong = +12 Pathogenic; 2 Moderate + 1 Supporting = +5 VUS; PVS1 + PM2 Supporting = +9 Likely Pathogenic.
- BA1 override short-circuits to Benign.
- Conflicting pathogenic/benign evidence forces VUS regardless of net.
- Mutually exclusive pairs do not co-fire.

Verify:
- `cd app/backend && python -m pytest tests/test_acmg_points_engine.py -q`
- `cd app/backend && python -m ruff check app/services/acmg_points_engine.py tests/test_acmg_points_engine.py`
- `cd app/backend && python -m black --check --target-version py310 app/services/acmg_points_engine.py tests/test_acmg_points_engine.py`

Out of scope:
- VCEP overlay, coverage expansion, AI narration, benchmark harness, frontend.

## Task 2 - Evidence Wiring And Report Population

Goal: populate `ReportPayload.eamos_computed_classification` in lookup/report responses using existing evidence surfaces.

Context: v1 should reuse current data paths and mark unsupported criteria as not assessed. Do not change clinical consensus precedence behavior.

Relevant files:
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/acmg_points_engine.py`
- `app/backend/app/services/computational_calibration.py`
- `app/backend/app/services/pvs1_nmd.py`
- `app/backend/app/tools/gnomad.py`
- `app/backend/app/tools/clinvar.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_frontend_contract.py`

Proposed approach:
- Build a narrow adapter from existing `evidence_map` and `VariantSummaryRow`/variant namespace into the points engine input.
- Use calibrated predictor bands for PP3/BP4 when present.
- Use `pvs1_nmd.assess_pvs1_nmd` where consequence/exon context supports it.
- Use gnomAD/ClinVar summaries for BA1/BS1/BS2/PM2 and related v1 criteria only where source data is explicit.
- Emit "not assessed" rows for v1-excluded criteria and for unavailable source data.

Acceptance criteria:
- Existing lookup behavior and curated clinical consensus are unchanged.
- RPE65 fixture response includes a stable `eamos_computed_classification` block.
- Missing evidence does not invent criteria; it emits not-assessed rows.
- Source DB/version/reference fields are present when sourced from calibration/PVS1/gnomAD/ClinVar data.

Verify:
- `cd app/backend && python -m pytest tests/test_acmg_points_engine.py tests/test_variant_search_integration.py tests/test_frontend_contract.py -q`
- `cd app/backend && python -m ruff check app/services/acmg_points_engine.py app/services/lookup_service.py app/schemas/run.py tests/test_acmg_points_engine.py tests/test_variant_search_integration.py tests/test_frontend_contract.py`
- `cd app/backend && python -m black --check --target-version py310 app/services/acmg_points_engine.py app/services/lookup_service.py app/schemas/run.py tests/test_acmg_points_engine.py tests/test_variant_search_integration.py tests/test_frontend_contract.py`

Out of scope:
- Modifying `clinical_consensus.py`, frontend TypeScript, SVG instruments, VCEP overlay, benchmark harness.

## Task 3 - Fast-Follow ClinVar P/B Reference-Set Precompute

Goal: prepare the ClinVar >=2-star pathogenic/benign reference-set precompute needed for the B7 predictor beeswarm.

Context: this is explicitly fast-follow after the v1 hero contract/engine. It should be backend-owned and source-backed.

Relevant files:
- `docs/report-acmg-viz/spec.md` fast-follow notes
- Existing ClinVar local/source-cache tooling
- Future CLI under `app/backend/app/cli/`
- Future tests under `app/backend/tests/`

Proposed approach:
- Design a read-only/import CLI that derives per-predictor reference distributions from ClinVar >=2-star P/B records.
- Preserve source version, review-status threshold, included/excluded counts, and license/provenance metadata.
- Do not wire runtime report payloads until the precompute artifact is verified.

Acceptance criteria:
- Precompute can run offline against approved source inputs.
- Output records are versioned, source-backed, and reproducible.
- Beeswarm consumers can query pathogenic and benign distributions without recomputing from raw ClinVar at request time.

Verify:
- Focused CLI/unit tests once implemented.
- `git diff --check`
- `python -m graphify update .`

Out of scope:
- B7 frontend rendering and runtime provider flips.
