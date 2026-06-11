# Eamos CRISPR Readiness Operator Tooling

Status: Active backend prototype
Type: Operator CLI + sanitized readiness workflow
Owner: Codex
Added: 2026-06-12 01:46 +1000 - Codex
Last updated: 2026-06-12 01:46 +1000 - Codex

## What It Does

Provides local operator checks for Workbench CRISPR readiness without flipping
runtime providers. The tooling preflights the optional `crisprScore` R runtime,
estimates SpCas9 off-target index size/counts from FASTA or 2bit inputs,
verifies built SQLite indexes, and emits a manifest with checksum and sanitized
asset metadata.

Primary commands:

```powershell
python -m app.cli.eamos_crispr_score_preflight --provider crisprscore_r
python -m app.cli.eamos_crispr_offtarget_index estimate --fasta hg38.fa
python -m app.cli.eamos_crispr_offtarget_index verify --index spcas9.sqlite --genome-build GRCh38
python -m app.cli.eamos_crispr_offtarget_index manifest --index spcas9.sqlite
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
- `app/backend/app/api/routes/health.py`
- `app/backend/tests/test_crispr_design.py`
- `app/backend/tests/test_crispr_offtarget_index_cli.py`
- `app/backend/tests/test_health_api.py`

## Caveats

- The score preflight only reports runtime/package readiness; it does not
  install R, Bioconductor packages, conda environments, or model assets.
- Off-target estimate size is intentionally conservative and should be replaced
  by the real built artifact manifest before any Render env flip.
- The indexed off-target provider remains in mock fallback unless explicitly
  configured and backed by a valid local SQLite index.
