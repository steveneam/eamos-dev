# PMAT-005 Bounded Slice Benchmark

Last updated: 2026-06-27 19:22 +1000 - Codex.

Status: implemented locally as a fixture-backed benchmark harness. No real
PubMed, LitVar2, PubTator, ClinicalTrials, Supabase, Render, Vercel, Storage,
runtime seeding, runtime flag change, deploy, or source download is performed
by this gate.

## Purpose

PMAT-005 defines the measurement contract that must exist before Steven
approves any representative literature/trials source slice. The first
implementation runs only against checked-in PMAT tiny fixtures so the team can
review the metric shape, sanitization, and rollback procedure without creating
production artifacts.

## Command

```powershell
cd app/backend
python -m app.cli.eamos_pmat_bounded_slice_benchmark --compact --require-ready
```

Optional operator/debug form:

```powershell
cd app/backend
python -m app.cli.eamos_pmat_bounded_slice_benchmark `
  --output-dir <empty-temp-or-staging-dir> `
  --force `
  --lookup-runs 5 `
  --batch-size 1000 `
  --batch-runs 3 `
  --compact `
  --require-ready
```

The command stages only fixture-sized local files, converts tiny PubTator and
LitVar fixture inputs into edge JSONL, materializes a temporary PubMed-local
SQLite asset, preflights it, and measures local lookup and batch-loop latency.

## Metrics Contract

The benchmark JSON records:

- total and per-step wall time;
- process RSS checkpoint peak;
- temp disk peak;
- generated output sizes for SQLite, manifest, seed TSV, PubTator edges, and
  LitVar edges;
- source input profile by file name and byte count, never by local path;
- row-count profile;
- license profile;
- edge conversion/import/orphan profile;
- preflight readiness time and checksum status;
- local lookup p50/p95;
- batch-loop p50/p95;
- rollback procedure.

The JSON also carries guardrails proving no network download, source download,
Storage upload, Supabase mutation, Render/Vercel mutation, runtime seed,
runtime flag change, startup download, or request-time materialization occurred.
Output must not include local paths, raw abstracts, seed rows, secrets, object
URIs, signed URLs, or patient/user/request payloads.

## Fixture Evidence

The tiny fixture harness should report:

- two imported PubMed articles;
- one licensed abstract and one metadata-only article;
- one deleted citation;
- six coverage rows;
- three source files;
- four converted PubTator edges, with two imported and two orphan skips after
  PubMed-local import;
- twelve converted LitVar edges, with six imported and six orphan skips after
  PubMed-local import;
- eight imported literature edges total;
- ready preflight with checksum verified;
- local lookup status for the RPE65 PMAT variant without live fallback.

## Representative Slice Gate

A real bounded slice remains blocked until Steven separately approves the exact
operator-staged input set and corpus label. The representative run must use the
same metric contract and additionally record:

- approved seed manifest identity and scope label;
- staged source file count and byte count;
- source release/version labels;
- wall time and external peak-RSS sampling for long-running steps;
- temp disk peak and generated artifact byte counts;
- article, license, edge, source-file, and orphan-edge profiles;
- preflight time and checksum status;
- local lookup p50/p95 with at least five runs;
- 1k-variant batch p50/p95 with at least three batch runs;
- rollback/delete path.

The representative run is still not permission to upload, register, seed
runtime, deploy, or enable `PUBMED_LOCAL_ENABLED`, `LOCAL_EVIDENCE_ENABLED`, or
`RAG_ENABLED`. Each of those remains a separate explicit approval.

## Rollback

For PMAT-005 fixture output, rollback is deletion of the generated benchmark
output directory. For a future representative slice, rollback additionally
requires not uploading generated artifacts, not registering metadata rows, not
syncing to Render disk, and leaving runtime flags unchanged.
