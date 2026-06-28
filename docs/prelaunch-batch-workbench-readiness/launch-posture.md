# Prelaunch Batch And Workbench Launch Posture

Status: active launch posture.
Created: 2026-06-28 by Codex.
Applies to: Sprint A Task 0.1 in
`docs/prelaunch-batch-workbench-readiness/plan.md`.

## Source Documents

- `docs/prelaunch-batch-workbench-readiness/design.md`
- `docs/prelaunch-batch-workbench-readiness/review.md`
- `docs/prelaunch-batch-workbench-readiness/plan.md`
- `docs/prelaunch-batch-workbench-readiness/resume-prompt.md`

## Current Launch Position

The ClinVar/report generated-artifact phase is complete for launch scope.
`clinvar_gene_distribution_index` is live on SG, provider-cache reports it
ready, and the RPE65 `c.260A>G` report path uses the local gene-distribution
index without the pending-index warning. No further deploy, seed, provider
flip, runtime script, or live sync is needed for that artifact.

PubMed remains API/cache-backed for launch. PubMed-local, literature
embeddings, and RAG are not enabled and should not be claimed as launch
features.

DuckDB/Parquet remains disabled analytical infrastructure for launch. It is
not part of report point-lookups, Batch launch readiness, or Workbench launch
readiness until a later benchmark-backed analytical phase.

Batch is not launch-ready yet. The first launch-readiness pass is Sprint A:
source disclosure, bearer-token transport, authenticated and owner-scoped
create/get flows, a Batch job rate-limit scope, and removal of silent mock
fallbacks.

Workbench may launch as mixed source-backed/fallback only if labels are honest.
The next Workbench work is a shared disclosure taxonomy and local functional
proof. This posture does not enable new providers.

## Explicitly Not Enabled

- PubMed-local generated artifact.
- Literature embeddings or RAG.
- DuckDB analytical serving.
- UCSC isPcr whole-genome primer specificity.
- Indexed CRISPR off-target provider on production.
- Advanced CRISPR R scoring providers.
- Source-backed generated panel catalog.
- Batch SQL persistence or reloadable job history.

Current panels remain warning-labeled local launch panels unless Steven makes
source-backed panel provenance a launch blocker.

## Required Approvals

Do not run any of these without Steven approving that exact action:

- Vercel command.
- Render env mutation.
- Provider or flag flip.
- Raw source download.
- Supabase metadata mutation.
- Supabase Storage mutation.
- One-off live runtime script.
- Runtime seed or sync.
- Live SG probe beyond read-only health.
- Destructive git.
- Commit.
- Push.

## Launch Evidence Bar

Before Batch or Workbench is called launch-ready, evidence must distinguish:

- source-backed results from local-provider results;
- fallback, fixture, gated, and unavailable states;
- local verification from live SG verification;
- current API/cache behavior from future local materialization work.

This note is a posture statement only. It does not change runtime behavior,
provider configuration, storage state, or deployment state.
