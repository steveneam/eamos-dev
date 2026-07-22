# Live Product Completion — Parallel Delivery Plan

Status: proposed; planning only; no new live-product lane launched.

Stamped: 2026-07-22 16:31 +0000 · Codex.

Canonical inputs:

- `plans/live-product-completion/research.md`
- `plans/live-product-completion/spec.md`
- `COORDINATION.md`
- `agent_handoff/README.md`

## Outcome

Close the gap between “the control exists” and “the named scientific operation
actually ran” across Workbench, Variant Report, Paper → Variants, and Batch /
Compare. The completed product is universally free, source- and
algorithm-explicit, fail closed, input-bound, reproducible where possible, and
tested across a deliberately varied matrix rather than a single RPE65 path.

This is a Mode B campaign. It needs independent backend/runtime context,
scientific fixtures and larger artifacts, and serialized merge/deploy caution.
The lead is Codex. Lane ownership is file ownership, not a frontend/backend or
agent identity boundary.

## Non-negotiable release rules

1. An ordinary release request returns executed output or a typed unavailable /
   not-applicable state. It never returns a fixture, illustrative record,
   unrelated sequence window, heuristic relabelled as a named method, or VCF
   passthrough presented as Eamos annotation.
2. Every output is bound to the canonical input identity and carries the
   execution/source/material fields frozen in the contract window.
3. Small fixtures, builders, manifests, checksums, source versions, licences,
   validation expectations, and retrieval instructions are tracked in Git.
   Large genome/model/cache artifacts use the approved asset store and an
   immutable tracked manifest.
4. Universal free access removes Eamos price tiers, not upstream licences,
   retention, consent, privacy, rate limits, attribution, or scientific
   validation.
5. Raw sequence, AB1, PDF text/bytes, VCF rows/genotypes, notes, and credentials
   stay out of URLs, logs, errors, analytics, and durable state unless an
   explicit retention contract says otherwise.
6. Contract changes are schema-first. The boundary test, web boundary, and
   frontend-contract canary remain green.

## Dependency graph

```text
finish current Product Workflow Lane D
  -> Steven merge approval -> merge/verify D
  -> serial Contract V2 window
  -> Steven merge approval -> merge/verify contract
  -> parallel backend engine wave: Workbench | Report | Paper | Batch
  -> serialized lane reviews/approvals/merges
  -> serial runtime composition/dependency integration
  -> separately approved parallel artifact/material wave
  -> one frontend truth-and-wiring writer
  -> re-chartered integrated ratchets (replaces stale old Lane E)
  -> approved deployment + live multi-variant/WES/PDF matrix
```

No downstream wave starts from unmerged branches. Contract drift stops a lane
and returns to the lead; it is not patched independently in four branches.

## Gate 0 — close the current Product Workflow slice

The only currently active product writer is Lane D on
`agent/product/workbench-canvas`. It finishes its already-approved frontend
scope, runs focused gates, commits, pushes, opens/updates its PR, and hands the
lead exact evidence. The lead then:

1. audits `origin/main..origin/agent/product/workbench-canvas` for owned paths,
   hard-coded scientific facts, mock fallbacks, raw-input persistence, and
   contract drift;
2. rebases without force-push, runs the Lane D and structural gates, and watches
   required CI;
3. asks Steven for the existing explicit merge approval;
4. merges only on green and verifies current `main`.

Do **not** launch the historical Lane E after D. Its frozen verification target
predates this scientific-live campaign. Its useful intent is re-chartered as
the final ratchet lane below after all four surfaces and their materials land.

## Wave 0 — serial Contract V2 window

Branch: `agent/live/product-contract-v2`

Worktree: `.claude/worktrees/live-product-contract-v2`

This is the one serial schema/contract writer. It performs no engine, provider,
source acquisition, UI, cloud, or deployment work.

### Owned paths

```text
app/backend/app/schemas/__init__.py
app/backend/app/schemas/capabilities.py                    # new
app/backend/app/schemas/workbench.py
app/backend/app/schemas/lookup.py
app/backend/app/schemas/report.py
app/backend/app/schemas/paper_variants.py
app/backend/app/schemas/batch.py
app/backend/app/schemas/panels.py
app/backend/app/schemas/workflow.py
app/web/lib/backend.ts
app/backend/tests/test_frontend_contract.py
app/backend/tests/test_live_product_contract.py            # new
```

### Frozen outputs

- One shared execution/source disclosure that bridges existing
  `SourceDisclosure`, processing disclosure, report provenance, and capability
  health without giving the same state multiple meanings.
- Workbench Context V2: transcript/build, immutable reference basis, selection,
  sparse edits, revision, digest, orientation, verified locus, and stale-result
  semantics on every tool request/result.
- Per-score CRISPR identity and method/version fields; no aggregate “score” that
  hides algorithm differences.
- Paper document-bundle, extraction-quality, mention, evidence-span, biological
  context, and resolution contracts.
- Batch input envelope, original/normalized allele, source snapshot, filter
  disposition, sample provenance, pagination/export, and per-field execution
  state.
- Report section and per-predictor applicability/execution/source state derived
  from one canonical policy.
- Additive compatibility only where needed. Every shim has a test and removal
  note.

### Exit gate

```bash
app/backend/.venv/bin/pytest -q \
  app/backend/tests/test_live_product_contract.py \
  app/backend/tests/test_frontend_contract.py \
  app/backend/tests/test_batch_panel_schemas.py
npm --prefix app/web test
npm --prefix app/web run typecheck
node scripts/eamos-web-boundary.mjs
app/backend/.venv/bin/pytest -q app/backend/tests/test_boundary.py
git diff --check
```

The lead reviews, asks Steven for merge approval, merges, and verifies. Only the
resulting `origin/main` may be the base for Wave 1.

## Wave 1 — four parallel backend engine lanes

The system has four active slots including the lead. The lead owns Batch in its
own worktree and launches three agents for Workbench, Report, and Paper. Each
lane begins by converting the baseline into executable red tests, then
implements only its owned paths. No lane edits schemas, `backend.ts`, `main.py`,
configuration, dependency lockfiles, container files, CI, shared materialization
orchestrators, or another lane's tests.

Dependency or runtime-image needs are handed to the lead as an exact request:
package/binary, pinned version, licence, expected image/asset cost, import or
argv seam, health check, and fallback behavior. They land later in the serial
composition lane.

### Lane W — Workbench engines

Branch: `agent/live/workbench-engines`

Owned paths:

```text
app/backend/app/api/routes/workbench.py
app/backend/app/services/sequence_context.py
app/backend/app/services/sequence_window_model.py
app/backend/app/services/variant_applied_model.py
app/backend/app/services/transcript_model.py
app/backend/app/services/workbench_design*.py
app/backend/app/services/crispr_*.py
app/backend/app/services/trace_*.py
app/backend/app/cli/eamos_workbench_*.py
app/backend/app/cli/eamos_crispr_*.py
app/backend/app/fixtures/workbench/**                      # synthetic/test only
app/backend/tests/test_sequence_context.py
app/backend/tests/test_sequence_window_model.py
app/backend/tests/test_workbench_api.py
app/backend/tests/test_crispr_*.py
app/backend/tests/test_workbench_*.py
docs/live-product-verification/workbench/**                # new
```

Required implementation:

1. Execute Context V2 exactly for Primer, CRISPR, ssODN, screening primers,
   alignment, and outcomes. Add transcript/build context to every path; reject
   reference/digest/selection mismatch.
2. Keep Primer3 as the design/thermodynamic engine; wire source-backed dbSNP
   masking and whole-genome isPcr when present. Distinguish template-only from
   whole-genome specificity and show every unassessed metric honestly.
3. Replace the default CRISPR heuristic/window/mock path with a local
   CRISPOR-equivalent architecture: verified genome-wide enumeration, rs3 Rule
   Set 3 on-target, MIT/CFD off-target scores, and complete guide/PAM/cut/genomic
   binding. CRISPOR web is optional/consented only.
4. Make ssODN class support explicit. Implement and test supported SNV/indel
   paths or return typed unavailable; remove fixed HDR efficiency and unproved
   synthesized-window success.
5. Implement real chromatogram decomposition under the name TIDE, or rename the
   current consensus comparison and keep TIDE unavailable. Never ship the proxy
   as TIDE.
6. Remove positional large-alignment fallback; use a real bounded aligner or a
   typed limit.
7. Prove forward/reverse strand, splice, UTR, distant selection, indels,
   invalid-reference, no-primer/no-PAM, corrupt AB1, and long-alignment cases.

Focused exit:

```bash
app/backend/.venv/bin/pytest -q \
  app/backend/tests/test_sequence_context.py \
  app/backend/tests/test_sequence_window_model.py \
  app/backend/tests/test_workbench_api.py \
  app/backend/tests/test_crispr_design.py \
  app/backend/tests/test_crispr_offtarget_index_cli.py \
  app/backend/tests/test_crispr_offtarget_preflight_cli.py \
  app/backend/tests/test_crispr_tide_cli.py \
  app/backend/tests/test_workbench_preflight_cli.py
app/backend/.venv/bin/pytest -q app/backend/tests/test_boundary.py
git diff --check
```

### Lane R — Variant Report evidence truth

Branch: `agent/live/report-evidence`

Owned paths:

```text
app/backend/app/api/routes/lookup.py
app/backend/app/api/routes/reports.py
app/backend/app/services/lookup_*.py
app/backend/app/services/report_*.py
app/backend/app/services/variant_report_*.py
app/backend/app/services/computational_*.py
app/backend/app/services/predictor_runtime.py
app/backend/app/services/alphamissense_local.py
app/backend/app/services/capice.py
app/backend/app/services/ci_spliceai.py
app/backend/app/services/esm1b_local.py
app/backend/app/services/gene_context_snapshot.py
app/backend/app/services/population_frequency_section.py
app/backend/app/services/clinical_consensus.py
app/backend/app/services/clinical_source_tables.py
app/backend/app/services/functional_evidence.py
app/backend/app/services/publication_literature.py
app/backend/tests/test_lookup_*.py
app/backend/tests/test_report_*.py
app/backend/tests/test_variant_report_*.py
app/backend/tests/test_computational_*.py
docs/live-product-verification/report/**                   # new
```

Required implementation:

1. Make canonical allele/transcript/build identity and source match level the
   root of every section, call card, export, warning, and provenance row.
2. Consolidate evidence status/provenance so a local executed result cannot be
   rendered as fallback and a not-found row cannot imply local coverage.
3. Give each predictor independent applicability, artifact readiness, execution
   state, algorithm/version, and calibration. Non-applicable is not failure.
4. Complete local/cache-backed molecular context and computational paths where
   licensed artifacts already exist; missing assets return exact requirements.
5. Preserve exact-variant versus protein/gene/disease/discovery-only scope in
   publications and trials.
6. Pass RPE65, ABCA4, USH2A, HBB, TP53, BRCA1, CFTR, F8 plus invalid/unsupported
   controls with no fixture bleed and source-version visibility.

Focused exit:

```bash
app/backend/.venv/bin/pytest -q \
  app/backend/tests/test_lookup_section_fetch_contract.py \
  app/backend/tests/test_lookup_service_report_payload.py \
  app/backend/tests/test_report_api.py \
  app/backend/tests/test_report_cache_contract.py \
  app/backend/tests/test_report_call_cards.py \
  app/backend/tests/test_report_data_currency.py \
  app/backend/tests/test_report_provenance_policy.py \
  app/backend/tests/test_variant_report_orchestration.py \
  app/backend/tests/test_variant_report_publication_functional_integration.py
app/backend/.venv/bin/pytest -q app/backend/tests/test_boundary.py
git diff --check
```

### Lane P — deterministic Paper → Variants

Branch: `agent/live/paper-deterministic`

Owned paths:

```text
app/backend/app/api/routes/paper_variants.py
app/backend/app/services/paper_variants.py
app/backend/app/services/pdf_text.py
app/backend/app/services/paper_extract/**                   # new
app/backend/app/cli/eamos_paper_variants.py
app/backend/app/fixtures/paper_variants/**                  # new synthetic only
app/backend/tests/test_paper_variants.py
app/backend/tests/test_pdf_text.py
app/backend/tests/test_paper_extract_*.py                   # new
docs/live-product-verification/paper/**                     # new
```

Required implementation:

1. Adapt, do not copy data from, Selom's deterministic architecture: PDFium
   page text/raster, pypdf metadata/images, optional pikepdf XMP, typed main +
   supplement bundle, page markers, section/caption/reference segmentation, and
   exact/token-canonical recovery passes.
2. Replace the mock-labelled regex seam with L1–L3 deterministic extraction and
   truthful provenance. Remove/hard-gate fitz/PyMuPDF unless cleared.
3. Implement typed HGVS/accession/rsID/legacy mention grammar, bounded
   gene/transcript association, exact page/section/span/quote evidence, and
   clinical/family/construct/rescue/comparator/reference contexts.
4. Keep mention extraction separate from Eamos allele resolution. Group
   representations only after the resolver proves equivalence.
5. Exclude references by default, detect blank/scanned/garbled pages, and return
   `ocr_required` or ambiguity rather than zero-candidate success.
6. Build an Eamos-owned synthetic plus legally usable open-access corpus with
   checksums, licences, expected mentions/exclusions, and mutation cases. Do not
   copy Selom's absent/private corpus.
7. Optional AI/OCR/vision remains L4, consented and non-critical; it never
   overwrites deterministic evidence.

Focused exit:

```bash
app/backend/.venv/bin/pytest -q \
  app/backend/tests/test_paper_variants.py \
  app/backend/tests/test_pdf_text.py \
  app/backend/tests/test_paper_extract_*.py
app/backend/.venv/bin/pytest -q app/backend/tests/test_boundary.py
git diff --check
```

### Lane B — WES/panel-first Batch

Branch: `agent/live/batch-wes`

Owned paths:

```text
app/backend/app/api/routes/batch.py
app/backend/app/api/routes/panels.py
app/backend/app/services/batch.py
app/backend/app/services/vcf_ingest.py
app/backend/app/services/panels.py
app/backend/app/services/batch_engine/**                    # new
app/backend/app/fixtures/batch/**                          # new synthetic only
app/backend/tests/test_batch_api.py
app/backend/tests/test_batch_panel_schemas.py
app/backend/tests/test_vcf_ingest.py
app/backend/tests/test_panels_api.py
app/backend/tests/test_batch_wes_*.py                       # new
docs/live-product-verification/batch/**                    # new
```

Required implementation:

1. Replace the bespoke list-first parser with a benchmark-selected HTSlib path
   (`pysam` baseline, `cyvcf2` challenger). Stream VCF/VCF.gz; add BCF only after
   parity. Keep gVCF/WGS/cohort/SV/CNV exclusions explicit in V1.
2. Separate raw-ingestion bounds from the post-filter annotation cap. A
   25k–150k-row synthetic WES-shaped file with a small gene-panel result must
   run without retaining all rows or failing at raw row 5,001.
3. Use pinned GRCh38 plus `bcftools norm` or a proven equivalent for REF check,
   left alignment, multiallelic split, and normalization. Fixed argv only; no
   shell/user paths in commands.
4. Build gene filtering from versioned MANE intervals plus HGNC alias mapping,
   GenCC gene-disease assertions, Mondo disease mappings, and custom gene lists.
   PanelApp remains a named launch-gated overlay because its terms restrict
   downstream use.
5. Offer coordinate-backed whole-gene, MANE exon + splice-flank, and validated
   capture-BED scopes. Input `GENE`/`ANN` is provenance, not authority. Separate
   cheap pre-annotation filters from consequence/frequency/classification/
   evidence filters, with counted reasons and honest unavailable-source state.
6. Filter before expensive annotation, deduplicate normalized alleles while
   retaining row/sample provenance, and annotate through the same local core /
   source snapshot as direct Report lookup.
7. Remove successful INFO-passthrough release behavior. Missing `LookupService`
   is a startup/preflight failure; each completed shared field equals direct
   lookup for the same variant and snapshot.
8. Replace daemon-thread-only execution with an owner-bound recoverable lease or
   queue. Prove restart, retry, cancel, expiry, delete, and streamed export.
9. Benchmark memory/wall time on 25k/75k/150k raw rows and 0/10/500/5,000/
   over-cap filtered rows. Freeze neutral deployment limits from evidence.

Focused exit:

```bash
app/backend/.venv/bin/pytest -q \
  app/backend/tests/test_batch_api.py \
  app/backend/tests/test_batch_panel_schemas.py \
  app/backend/tests/test_vcf_ingest.py \
  app/backend/tests/test_panels_api.py \
  app/backend/tests/test_batch_wes_*.py
app/backend/.venv/bin/pytest -q app/backend/tests/test_boundary.py
git diff --check
```

## Wave 1 review and merge order

Lane agents push, open/update a PR, mark only their coordination row `review`,
and hand the lead `{branch, PR, files, isolation, tests, scientific matrix,
dependency requests, material requirements, risks}`. They never merge.

The lead serializes integration in this order:

1. Workbench engines;
2. Variant Report evidence;
3. deterministic Paper;
4. WES Batch.

Before each merge the lead audits `git log --name-only`, rebases onto current
`main`, reruns focused plus boundary/contract gates, watches CI, and asks Steven
for explicit approval. Batch is last so its direct-lookup equivalence test runs
against the merged Report implementation. A conflict outside the lane's own
coordination row is a partition leak and triggers re-plan.

## Wave 2 — serial runtime composition and dependencies

Branch: `agent/live/runtime-composition`

This small lead-owned lane begins only after the four engine branches merge. It
integrates already-reviewed dependency requests and service construction; it
does not redesign engines.

Owned paths:

```text
app/backend/app/main.py
app/backend/app/core/config.py
app/backend/requirements*.txt
app/backend/Dockerfile
docker-compose*.yml
app/backend/app/capabilities/**                            # new registry/runtime
app/backend/tests/test_health_api.py
app/backend/tests/test_syd2_compose_contract.py
app/backend/tests/test_live_product_composition.py          # new
```

Exit requires:

- all services injected at startup with no lazy scientific fallback;
- pinned packages/binaries, licence/SBOM rows, bounded subprocess adapters, and
  image-size/startup measurements;
- the machine-readable capability/material registry and executed preflights;
- dependency-absent tests returning typed unavailable/startup failure; and
- full backend tests, boundary guard, frontend contract canary, container build
  and runtime identity checks.

This lane follows the normal review/explicit merge-approval gate.

## Wave 3 — separately approved material/artifact work

No source download, bulk materialization, object-store write, provider flip,
environment mutation, or deployment is authorized by this planning document.
Before launch, the lead presents one card per artifact: source URL, terms,
version, expected compressed/uncompressed size, destination, checksum strategy,
builder, runtime mount, update cadence, rollback, and functional probe.

After Steven approves the named cards, up to four disjoint lanes may build in
parallel:

| Lane | Artifacts | Exclusive build surface |
| --- | --- | --- |
| M-W | GRCh38 CRISPR index, rs3/model runtime, isPcr reference, dbSNP primer mask, TIDE validation fixtures | Workbench-specific builders/manifests/preflights |
| M-R | Missing Report predictor/calibration and molecular-context artifacts | Predictor/source-specific builders/manifests/preflights |
| M-P | Synthetic/open-access Paper corpus and PDFium/OCR quality fixtures | Paper corpus manifests/builders only |
| M-B | MANE, HGNC, GenCC, Mondo, normalized interval/tabix indexes, optional pinned VEP cache | Batch/panel builders/manifests/preflights only |

Shared asset roots and the global materialization manifest have one lead writer
in a short serialized integration commit after lane merges. PanelApp and CRISPOR
web remain disabled unless their separate rights/retention/consent cards pass.

## Wave 4 — one frontend truth-and-wiring writer

Branch: `agent/live/surface-truth`

Only one web writer runs in this wave. It starts after the engine, composition,
and approved material contracts are merged and uses the Impeccable and security
skills. It consumes the frozen `backend.ts` contract; schema drift returns to a
serial amendment.

Owned paths:

```text
app/web/app/workbench/**
app/web/app/report/**
app/web/app/paper/**
app/web/app/compare/**
app/web/components/workbench/**
app/web/components/report/**
app/web/components/paper/**
app/web/components/compare/**
app/web/lib/api.ts
app/web/lib/workbench/**
app/web/lib/batch.ts
app/web/lib/batch-summary.ts
app/web/lib/compare-filters.ts
app/web/lib/panels.ts
app/web/lib/panels.mock.ts
app/web/lib/paperVariants.ts
app/web/lib/report-*.ts
```

Tasks:

1. Remove all ordinary scientific sample/mock fallbacks, including panel
   fallback. Explicit demo/test modes remain isolated and visibly labelled.
2. Render execution, provider/algorithm, applicability, source release,
   artifact, validation, stale/unavailable, and consent/retention truth without
   burying the scientific result.
3. Bind Workbench result lifecycle to Context V2 and clearly separate measured
   Primer structure/Tm/specificity, CRISPR score families, ssODN support, real
   TIDE, and alignment limits.
4. Preserve the Report reading hierarchy while making per-section and
   per-predictor truth inspectable and exportable.
5. Expose Paper mentions with page/section/span/context and resolution status;
   make source text/quotes bounded and accessible.
6. Make Batch visibly WES/panel-first: explain format/envelope exclusions,
   source-backed panel/version, pre/post-filter counts, row provenance,
   restart/cancel/delete, pagination, and streamed export.
7. Browser-test loading, empty, unavailable, partial, stale, auth, consent,
   offline, error, keyboard, reduced-motion, mobile, and large-data states.

The lane must pass web test/typecheck/lint/build, both boundary guards, the
frontend-contract canary, and fresh browser evidence before review.

## Wave 5 — re-chartered integrated ratchets

Branch: `agent/live/product-ratchets-v2`

This supersedes the unlaunched historical `agent/product/workflow-ratchets`
scope. It begins only after the frontend truth lane merges.

Owned paths:

```text
scripts/eamos-live-product-*.mjs                           # new
docs/live-product-verification/integrated/**               # new
.github/workflows/ci.yml
package.json
```

It adds summary-safe executable matrices for:

- the eight shared variants across Report and every applicable Workbench tool;
- Primer Tm/structure/specificity/SNP truth and failure states;
- CRISPR guide/on-target/off-target/ssODN/outcome/TIDE truth;
- Paper selectable/garbled/scanned/supplement/context/reference cases;
- Batch 25k/75k/150k WES-shaped streams, filter counts, direct-lookup equality,
  restart and export;
- cross-surface handoffs, auth/ownership, privacy/retention/deletion;
- keyboard/mobile/reduced-motion and performance budgets; and
- registry ↔ deployed artifact ↔ functional-preflight agreement.

It invokes rather than weakens `test_boundary.py`,
`eamos-web-boundary.mjs`, `test_frontend_contract.py`, coordination, and the
existing root verify.

## Approved deployment gate

Deployment is not part of any implementation lane. After all merges and local
green, the lead presents the exact environment/provider/material diff, rollback
and smoke matrix. Only after Steven's separate approval does the lead deploy and
run:

1. health/capability/preflight checks;
2. eight-variant Report and Workbench matrix;
3. Paper synthetic/open-access corpus matrix;
4. Batch WES-shaped size/filter/restart/export matrix; and
5. privacy/log/retention plus browser smoke.

A provider marked ready must have an artifact digest and an executed functional
probe. A green file-existence check alone cannot release it.

## Exact next-session launch commands

Steven confirmed on 2026-07-22 that, next session, his `gogogo` is the fresh
per-session approval for Codex to create and orchestrate the named Contract V2,
Workbench, Report, Paper, and Batch worktrees/agents below as their dependencies
unlock. He does not need to run these commands himself. Do not run them today.
First merge/verify current Lane D; then run the contract lane. Each merge and
all material/source/provider/cloud/deploy actions keep their separate approval
gates.

### Contract window

```bash
cd /home/deploy/work/eamos
git fetch origin
git worktree add .claude/worktrees/live-product-contract-v2 -b agent/live/product-contract-v2 origin/main
cd .claude/worktrees/live-product-contract-v2
python3 -m venv app/backend/.venv
app/backend/.venv/bin/pip install -r app/backend/requirements.txt
npm --prefix app/web ci
codex
```

Contract kickoff:

```text
You own the serial Live Product Contract V2 lane on agent/live/product-contract-v2. Read AGENTS.md, nested instructions, COORDINATION.md, agent_handoff/README.md, and plans/live-product-completion/{research,spec,plan}.md completely. Work only in Wave 0's exact schema, backend.ts, and contract-test paths. Freeze the shared execution disclosure plus Workbench Context V2, Report per-source/per-predictor state, Paper document/mention/span model, and WES Batch normalization/filter/source-snapshot model. Bridge existing contracts additively; do not implement engines, UI, providers, sources, dependencies, cloud, Supabase, deploys, or out-of-glob files except your own COORDINATION row. If the spec is insufficient, stop and propose one amendment. Run every Wave 0 gate and diff-check, stage only owned paths, commit/push without AI attribution, open/update the PR, mark review, and hand Codex lead {branch, PR, files, isolation, tests, compatibility risks}. Never merge.
```

### Parallel engine wave after Contract V2 merges

Workbench:

```bash
cd /home/deploy/work/eamos
git fetch origin
git worktree add .claude/worktrees/live-workbench-engines -b agent/live/workbench-engines origin/main
cd .claude/worktrees/live-workbench-engines
python3 -m venv app/backend/.venv
app/backend/.venv/bin/pip install -r app/backend/requirements.txt
codex
```

Report:

```bash
cd /home/deploy/work/eamos
git fetch origin
git worktree add .claude/worktrees/live-report-evidence -b agent/live/report-evidence origin/main
cd .claude/worktrees/live-report-evidence
python3 -m venv app/backend/.venv
app/backend/.venv/bin/pip install -r app/backend/requirements.txt
codex
```

Paper:

```bash
cd /home/deploy/work/eamos
git fetch origin
git worktree add .claude/worktrees/live-paper-deterministic -b agent/live/paper-deterministic origin/main
cd .claude/worktrees/live-paper-deterministic
python3 -m venv app/backend/.venv
app/backend/.venv/bin/pip install -r app/backend/requirements.txt
codex
```

Batch (lead):

```bash
cd /home/deploy/work/eamos
git fetch origin
git worktree add .claude/worktrees/live-batch-wes -b agent/live/batch-wes origin/main
cd .claude/worktrees/live-batch-wes
python3 -m venv app/backend/.venv
app/backend/.venv/bin/pip install -r app/backend/requirements.txt
codex
```

Workbench kickoff:

```text
You own Lane W (Workbench Engines) on agent/live/workbench-engines. Read AGENTS.md, nested instructions, COORDINATION.md, agent_handoff/README.md, and plans/live-product-completion/{research,spec,plan}.md completely. Confirm Contract V2 is in your base. Work only in Lane W's exact paths. Turn Primer, secondary structure/Tm/specificity/SNP masking, CRISPR on/off-target, ssODN, real TIDE or honestly renamed trace comparison, and alignment into input-bound executed capabilities across the full matrix. Use local CRISPOR-equivalent architecture and fail closed without artifacts. Do not edit schemas/backend.ts/main/config/dependencies/container/materialization/cloud/deploy/frontend or out-of-glob files except your COORDINATION row. Hand exact dependency/artifact requests to the lead. Run Lane W gates, stage only owned paths, commit/push, open/update PR, mark review, and hand off complete evidence. Never merge.
```

Report kickoff:

```text
You own Lane R (Variant Report Evidence Truth) on agent/live/report-evidence. Read AGENTS.md, nested instructions, COORDINATION.md, agent_handoff/README.md, and plans/live-product-completion/{research,spec,plan}.md completely. Confirm Contract V2 is in your base. Work only in Lane R's exact paths. Make variant identity, match level, source status/provenance, per-predictor applicability/execution, molecular context, publications/trials, exports, and call-card inputs truthful across the eight-variant matrix with no fixture bleed. Do not edit schemas/backend.ts/main/config/dependencies/container/materialization/cloud/deploy/frontend or out-of-glob files except your COORDINATION row. Hand exact dependency/artifact requests to the lead. Run Lane R gates, stage only owned paths, commit/push, open/update PR, mark review, and hand off complete evidence. Never merge.
```

Paper kickoff:

```text
You own Lane P (Deterministic Paper to Variants) on agent/live/paper-deterministic. Read AGENTS.md, nested instructions, COORDINATION.md, agent_handoff/README.md, and plans/live-product-completion/{research,spec,plan}.md completely. Confirm Contract V2 is in your base. Work only in Lane P's exact paths. Adapt Selom's deterministic PDF/page/metadata/segmentation/recovery architecture without copying its corpus; build Eamos variant mention/context/span/resolution layers and a synthetic/open-access corpus. Remove mock/provenance ambiguity and fail honestly for scanned/ambiguous input. Do not edit schemas/backend.ts/main/config/dependencies/container/materialization/cloud/deploy/frontend or out-of-glob files except your COORDINATION row. Hand exact dependency/artifact requests to the lead. Run Lane P gates, stage only owned paths, commit/push, open/update PR, mark review, and hand off complete evidence. Never merge.
```

Batch kickoff:

```text
You own Lane B (WES/Panel Batch) on agent/live/batch-wes. Read AGENTS.md, nested instructions, COORDINATION.md, agent_handoff/README.md, and plans/live-product-completion/{research,spec,plan}.md completely. Confirm Contract V2 is in your base. Work only in Lane B's exact paths. Build a streaming GRCh38 VCF/VCF.gz filter-first engine using the benchmarked HTSlib path, pinned normalization/reference checks, source-backed MANE/HGNC/GenCC/Mondo/custom panels, post-filter annotation caps, direct Report-lookup equality, restart-safe leases, paging/export, and synthetic WES load/rejection matrices. Keep PanelApp launch-gated and reject gVCF/WGS/cohort/SV/CNV scope honestly. Do not edit schemas/backend.ts/main/config/dependencies/container/global materialization/cloud/deploy/frontend or out-of-glob files except your COORDINATION row. Hand exact dependency/artifact requests to the lead. Run Lane B gates, stage only owned paths, commit/push, open/update PR, mark review, and hand off complete evidence. Never merge.
```

## Final release checklist

- Current Product Workflow Lane D is reviewed, explicitly approved, merged,
  and verified; old Lane E was not launched stale.
- Contract V2 is frozen and every parallel lane consumed it without drift.
- Every Workbench named feature is executed or typed unavailable across the
  shared matrix; no mock/local-window/proxy claim remains in ordinary mode.
- Report source/provenance/applicability states agree and no fixture crosses a
  variant boundary.
- Paper page/span/context evidence and resolution separation pass the corpus.
- Batch accepts WES-shaped input by filtering before the post-filter cap,
  rejects unsupported scale/formats honestly, and equals direct Report lookup.
- Capability/material registry, deployed artifacts, and functional preflights
  agree.
- Full backend/web/contract/boundary/security/privacy/a11y/performance gates and
  approved live matrices are green.
- Every lane is committed/pushed/PR-reviewed; every merge and every cloud/
  source/material/deploy mutation has its own Steven approval and receipt.
