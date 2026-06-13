# Eamos CRISPR Readiness Operator Tooling

Status: Active backend prototype
Type: Operator CLI + sanitized readiness workflow
Owner: Codex
Added: 2026-06-12 01:46 +1000 - Codex
Last updated: 2026-06-13 22:04 +1000 - Codex

## What It Does

Provides local operator checks for Workbench CRISPR readiness without flipping
runtime providers. The tooling preflights the optional `crisprScore` R runtime,
estimates SpCas9 off-target index size/counts from FASTA or 2bit inputs,
verifies built SQLite indexes, and emits a manifest with checksum and sanitized
asset metadata. It also emits the Workbench Render approval bundle that captures
the exact disk layout, CRISPR off-target full-index runbook, env changes, smoke
checks, and rollback plan before any production provider flip.

Primary commands:

```powershell
python -m app.cli.eamos_crispr_score_preflight --provider crisprscore_r
python -m app.cli.eamos_crispr_offtarget_index estimate --fasta hg38.fa
python -m app.cli.eamos_crispr_offtarget_index verify --index spcas9.sqlite --genome-build GRCh38
python -m app.cli.eamos_crispr_offtarget_index manifest --index spcas9.sqlite
python -m app.cli.eamos_workbench_render_approval_bundle --compact
```

## Why It Is Eamos-Original

The workflow is specific to the Eamos Workbench launch posture: it keeps
`CRISPR_OFFTARGET_PROVIDER=auto` until a real Render-mounted artifact is ready,
preserves launch-gate and provenance metadata, and emits JSON that intentionally
does not leak local filesystem paths.

## Source Of Truth

- `app/backend/app/services/crispr_design.py`
- `app/backend/app/services/crispr_offtarget_index.py`
- `app/backend/app/cli/eamos_crispr_score_preflight.py`
- `app/backend/app/cli/eamos_crispr_offtarget_index.py`
- `app/backend/app/cli/eamos_workbench_render_approval_bundle.py`
- `app/backend/app/api/routes/health.py`
- `app/backend/tests/test_crispr_design.py`
- `app/backend/tests/test_crispr_offtarget_index_cli.py`
- `app/backend/tests/test_workbench_render_approval_bundle_cli.py`
- `app/backend/tests/test_health_api.py`

## Caveats

- The score preflight only reports runtime/package readiness; it does not
  install R, Bioconductor packages, conda environments, or model assets.
- Off-target estimate size is intentionally conservative and should be replaced
  by the real built artifact manifest before any Render env flip.
- The full-index runbook pins the GRCh38 input to UCSC `hg38.2bit`, records the
  expected source MD5, and requires `verify` + `manifest` before any provider
  env change.
- The indexed off-target provider remains in mock fallback unless explicitly
  configured and backed by a valid local SQLite index.
- The Render approval bundle is a decision artifact and smoke checklist; it does
  not call Render, upload files, or change environment variables.
