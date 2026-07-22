# Variant Report evidence-truth verification

Status: Lane R local verification evidence, 2026-07-22. This directory is not
deployed-production proof and does not claim that absent runtime artifacts were
materialized.

## What this lane proves

- A report execution snapshot is bound to canonical gene, transcript, cDNA,
  protein, GRCh38 allele, and one opaque source-snapshot identifier.
- Summary and lazy section responses carry the same snapshot and section-level
  execution disclosures.
- Each named predictor has independent applicability, execution state,
  algorithm/source version, calibration, warnings, and exact missing-artifact
  requirements. A non-missense allele does not turn missense inapplicability
  into a failure.
- `live`, `local`, `cache`, `stale`, `fixture`, `fallback`, `missing`, and
  failure states are derived by one report policy. A successful peer cannot
  hide a failed or unavailable peer in an aggregate call card.
- Fallback or failed payloads cannot populate clinical classification, disease
  mechanism, molecular metrics, population frequency, ACMG assertions,
  functional literature, trial rows, or legacy report integration text.
- An executed local not-found lookup is disclosed as `not_found`; it is not
  presented as scientific coverage.
- Publication and trial rows retain variant, gene, disease, or discovery match
  scope rather than being promoted to exact-variant evidence.

Explicit fixture status remains visible in test/demo flows. Fixture evidence
cannot establish the canonical release identity, cannot be called fresh data,
and is rejected whenever it arrives under fallback or failure status.

## Evidence

- [Eight-variant and control matrix](./evidence-matrix.md)
- [Composition and artifact requests](./artifact-requests.md)
- Contract/regression suite: `app/backend/tests/test_report_execution_truth.py`
- Existing report, cache, API, publication, functional, provenance, and
  orchestration suites listed in `plans/live-product-completion/plan.md`.

## Verification boundary

The test matrix uses small in-memory source records to prove identity and state
semantics. It does not substitute for live source retrieval or predictor
artifact parity. The read-only local preflight on 2026-07-22 reported:

```text
AlphaMissense missing_source_file
ESM-1b       missing_source_file
CI-SpliceAI  score_cache_missing
CAPICE       model_artifact_missing
REVEL        score_cache_missing
PrimateAI-3D score_cache_missing
```

No source file, model, score cache, reference bundle, or index was downloaded,
generated, uploaded, registered, or activated by Lane R.
