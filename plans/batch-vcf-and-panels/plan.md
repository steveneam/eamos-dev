# Batch VCF And Panels Implementation Plan

Status: backend plan updated 2026-06-04 - Codex
Source spec: `plans/batch-vcf-and-panels/spec.md`

## Coordination Notes

- Codex green-lights publishing `ce47146` (`feat(evidence): add gated predictor roadmap and adapters`). It is backend-scoped, gated, and focused backend tests passed natively on Windows. The remaining publish decision is product/deploy scope because the same `git push` also publishes Claude's frontend commit `d830531` to Vercel production, including the global mono font swap.
- The batch/panels contract is backend-first. Land Pydantic schemas in `app/backend/app/schemas/*.py` before Claude mirrors TypeScript types in `app/web/lib/backend.ts`.
- The ratified batch contract uses upload negotiation: `POST /api/v1/batch/uploads` returns `upload_ref`; `POST /api/v1/batch` creates the job with either inline variants or that `upload_ref`.
- `GET /api/v1/batch/{job_id}` must be paged from day one using `limit` and `cursor`. SSE is optional and waits until polling is correct.
- Panel filtering correctness is interval-first: resolve symbols through HGNC normalization into MANE Select GFF3-derived hg38 BED intervals. VCF INFO gene symbols are only an optimization.
- AF filtering has two phases: INFO-AF can run before lookup; gnomAD-AF can only run after lookup. Use `n_to_lookup` for pre-lookup scope/quota estimates and `n_after_filters` only once final post-lookup filtering is known.
- Do not open or depend on WSL without explicit user approval. Native Windows verification is acceptable for repo tests; WSL bio tools are available only by approval.

## Task 1 - Batch And Panel Schemas

Goal: Create the backend contract surface before frontend work starts.

Context: The spec's section 8 is now the source of truth. The frontend should not invent client types ahead of backend Pydantic models.

Relevant files or references:
- `plans/batch-vcf-and-panels/spec.md`
- `plans/README.md`
- `app/backend/app/schemas/`
- `app/backend/tests/test_frontend_contract.py`
- `app/web/lib/backend.ts`

Proposed approach:
- Add Pydantic models for panels, parsed variants, batch filters, upload refs, job creation, job status, paged result responses, and page metadata.
- Model `n_input`, `n_to_lookup`, optional `n_after_filters`, `est_seconds`, `results`, and `page`.
- Define batch statuses and per-variant states explicitly.
- Keep the first API implementation stubbed if needed, but make schemas and tests real.

Acceptance criteria:
- Backend schemas express the exact section 8 contract, including `limit` and `cursor` paging.
- `n_to_lookup` and `n_after_filters` have distinct documented semantics.
- Frontend contract tests fail if the TypeScript mirror omits a backend field.

Verify:
- `cd app/backend; python -m pytest tests/test_frontend_contract.py -q`
- `cd app/backend; python -m pytest tests/test_*batch* tests/test_*panel* -q` once those test files exist.

Out of scope:
- Running real batch jobs.
- Saving custom panels.
- SSE.

## Task 2 - Mock VCF Generator And Truth Fixtures

Goal: Provide deterministic, known-truth VCFs that prove parser, panel-filter, dedup, and result behavior.

Context: The generator is the first backend deliverable because it gives both backend and frontend stable fixtures without depending on clinical data uploads.

Relevant files or references:
- `plans/batch-vcf-and-panels/spec.md` section 7
- `app/backend/scripts/make_test_vcf.py`
- `app/backend/tests/fixtures/vcf/`
- `app/web/lib/variant-file.ts`

Proposed approach:
- Build `make_test_vcf.py` with deterministic `--seed`, `--n`, `--panel`, `--mix`, `--multiallelic`, `--with-genotypes`, `--chr-prefix`, and `--malformed` flags.
- Emit a manifest next to each generated fixture with expected gene, classification bucket, filter behavior, and known malformed-line counts.
- Keep committed fixtures small. Generate larger fixtures during tests.

Acceptance criteria:
- Fixture generation is deterministic for the same seed.
- Truth manifests can assert expected panel membership and parsed variant counts.
- Multi-allelic, chr-prefix, malformed, header, duplicate, and genotype cases are covered.

Verify:
- `cd app/backend; python -m pytest tests/test_make_test_vcf.py -q`
- `cd app/web; npm test -- variant-file` if the frontend test harness exists.

Out of scope:
- Population-genetics simulation.
- FASTQ/read simulation.

## Task 3 - Panel Catalog And Interval Resource

Goal: Build the commercial-safe panel core and the hg38 interval resource required for correct VCF filtering.

Context: Large-VCF feasibility depends on panel filtering. The core source layer is local ClinGen/GenCC/MONDO/HGNC; PanelApp AU waits for ToU/legal confirmation.

Relevant files or references:
- `plans/batch-vcf-and-panels/spec.md` sections 6.1-6.4
- `app/backend/app/services/transcript_model.py`
- Local ClinGen/GenCC/MONDO/HGNC assets already referenced by the source registry
- MANE Select GFF3-derived gene intervals

Proposed approach:
- Implement panel source loaders for local ClinGen/GenCC/MONDO/HGNC.
- Normalize gene symbols through HGNC IDs and aliases.
- Produce a versioned hg38 BED-like interval map from MANE Select GFF3.
- Add `/api/v1/panels`, `/api/v1/panels/{slug}`, and `/api/v1/panels/resolve`.
- Make interval intersection the correctness path; use INFO symbols only as a short-circuit when trustworthy.

Acceptance criteria:
- Panels return stable slugs, versions, provenance, gene lists, and `intervals_ref`.
- Unknown or deprecated symbols return warnings rather than silently dropping genes.
- Panel filtering tests pass even when VCF INFO gene annotations are missing or wrong.
- Boundary behavior for introns/UTRs/flanks is documented and tested.

Verify:
- `cd app/backend; python -m pytest tests/test_panels*.py tests/test_panel_intervals*.py -q`
- `cd app/backend; python -m pytest tests/test_frontend_contract.py -q`

Out of scope:
- PanelApp AU overlay.
- Supabase saved custom panels.
- LLM panel builder.

## Task 4 - Batch Upload And Polling Job Engine

Goal: Implement the core async batch path with polling, pagination, dedup, and lookup reuse.

Context: The engine must call `lookup_service.lookup()` in process, below the per-IP HTTP lookup limiter. Job submission gets its own batch limits.

Relevant files or references:
- `app/backend/app/api/routes/`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/core/rate_limit.py`
- `plans/batch-vcf-and-panels/spec.md` sections 5.4 and 8

Proposed approach:
- Add upload-ref handling and job creation.
- Parse inline variants for the small path; store upload refs for the large path without trying to process huge files in request handlers.
- Normalize, dedup, apply pre-lookup filters, compute `n_to_lookup`, and enqueue the job.
- Process a bounded worker pool, cache by variant key, and store summary-level results.
- Implement paged `GET /api/v1/batch/{job_id}?limit&cursor` before SSE.

Acceptance criteria:
- Duplicate variants are looked up once and represented predictably in results.
- Polling returns status, progress, and stable pages without loading all results into the response.
- `n_to_lookup` drives estimates and quota. `n_after_filters` is absent/null until completion when post-lookup filters apply.
- Internal per-variant calls do not trip `RATE_LIMIT_LOOKUP`.

Verify:
- `cd app/backend; python -m pytest tests/test_batch*.py -q`
- `cd app/backend; python -m pytest tests/test_rate_limit*.py -q`

Out of scope:
- SSE.
- Large server-side VCF parsing optimizations beyond the upload-ref path.
- Cohort dashboard UI.

## Task 5 - Results Summary And Export Contract

Goal: Provide the result shape the frontend dashboard and exports need without full per-variant report payloads.

Context: Batch results should stay summary-level. Full reports remain lazy when a user opens a row.

Relevant files or references:
- `plans/batch-vcf-and-panels/spec.md` sections 5.5, 5.6, and 8
- `app/backend/app/schemas/run.py`
- `app/web/components/compare/CompareClient.tsx`
- `app/web/lib/report-export.ts`

Proposed approach:
- Return `BatchResult` rows with variant key, gene, HGVS, ClinVar verdict, gnomAD AF, predictor ensemble summary, ACMG classification summary, and `report_href`.
- Add aggregate counts for loaded result sets only when cheap and bounded.
- Keep publication/deep-dive/expert-panel payloads behind single-report lazy fetch.

Acceptance criteria:
- Result rows are enough for sorting, filtering, cohort summaries, and TSV export.
- Result pages do not include full `report_payload`.
- `report_href` opens or fetches a single full report for the selected row.

Verify:
- `cd app/backend; python -m pytest tests/test_batch_results*.py -q`
- Frontend verification after Claude wires the dashboard.

Out of scope:
- PDF/whole-report export for every row.
- Recomputing expensive per-row lazy sections during batch summary generation.

## Task 6 - PanelApp AU Overlay

Goal: Add recognizable named clinical panels after legal/ToU clearance.

Context: PanelApp AU is useful for clinician trust but is not needed for the commercial-safe core or mock-first build.

Relevant files or references:
- `plans/batch-vcf-and-panels/spec.md` sections 6.2 and 10
- PanelApp AU ToU/legal notes once written

Proposed approach:
- Wait for written ToU/legal confirmation and exact launch-panel list.
- Import versioned green/amber/red panel definitions with provenance and attribution.
- Map PanelApp genes through the same HGNC + MANE interval resource used by the core panels.

Acceptance criteria:
- Overlay panels show version, source, confidence, provenance URL, and attribution.
- OMIM-derived content is not redistributed unless separately licensed.
- Core local panels continue to work offline when the overlay is disabled.

Verify:
- `cd app/backend; python -m pytest tests/test_panelapp*.py tests/test_panels*.py -q`

Out of scope:
- Launching PanelApp AU before ToU/legal approval.
- Replacing the local ClinGen/GenCC/MONDO/HGNC core.
