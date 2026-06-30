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

Batch safety baseline is complete and pushed in
`f7d74c2 feat(batch): require auth for launch jobs`: source disclosure,
bearer-token transport, authenticated and owner-scoped create/get flows, a
Batch job rate-limit scope, and removal of silent mock fallbacks. The Sprint B
local UI pass now handles typed failure, expiry, auth, stale-scope, and empty
results states. Batch should still not be called fully launch-ready until the
signed-in browser path is proven with an approved Supabase Auth test approach or
an existing approved session.

Workbench may launch as mixed source-backed/fallback only if labels are honest.
The next Workbench work is a shared disclosure taxonomy and local functional
proof. This posture does not enable new providers.

## Panel Launch Policy

Current panels remain acceptable only as warning-labeled local launch panels.
The web Batch scope UI surfaces panel warnings in both the preset list and the
active-scope chip, mapping known local/fixture/mock warnings to visible
`local launch`, `fixture`, or `warning` labels.

A source-backed generated panel catalog is not enabled by this posture. Build an
offline SQLite panel artifact plus manifest/preflight only if Steven explicitly
makes source-backed panel provenance a launch blocker. No raw panel source
download or live panel-provider collection is approved by this note.

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
