# Workbench Render Approval Bundle

Status: draft for Steven approval. Created 2026-06-13 21:33 +1000 by Codex.

## Purpose

This bundle is the approval gate before any production Workbench provider flip
that depends on mounted genome, CRISPR, dbSNP, ClinVar, or protein assets. It is
read-only planning and verification. It does not change Render env vars, upload
assets, start downloads, or enable providers.

AI gateway work is out of scope and remains Claude-owned. Keep
`LLM_PROVIDER=mock` unless the AI-gateway pre-launch security gate has separately
passed.

## Operator CLI

Generate the machine-readable approval package:

```powershell
cd app/backend
python -m app.cli.eamos_workbench_render_approval_bundle
```

Compact JSON:

```powershell
cd app/backend
python -m app.cli.eamos_workbench_render_approval_bundle --compact
```

The CLI output records:

- guardrails proving no network, mutation, env change, provider flip, startup
  download, or secret/path emission happened;
- the exact Render disk layout for Workbench assets;
- env changes that are allowed only after approval and readiness checks;
- operator preflight commands;
- SG and Vercel smoke probes;
- rollback env values.

Local ready/not-ready bundle:

```powershell
cd app/backend
python -m app.cli.eamos_workbench_preflight --compact
```

The local bundle performs no network calls or mutations. It distinguishes the
public auto-mode fallback state from provider-flip readiness: auto mode may
remain locally available through warning-labeled mock fallback while the CRISPR
index and compact coordinate assets are still `not_ready` for a forced flip.

## Disk Layout

Mount root:

```text
/var/data
```

Asset root:

```text
/var/data/eamos/bio_assets
```

Required before switching CRISPR off-targets to indexed SQLite:

```text
/var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite
/var/data/eamos/bio_assets/crispr/spcas9_offtargets.manifest.json
```

Reference-window support:

```text
/var/data/eamos/bio_assets/genomes/hg38.2bit
/var/data/eamos/bio_assets/transcripts/MANE.GRCh38.v1.5.refseq_genomic.gff.gz
/var/data/eamos/bio_assets/transcripts/GCF_000001405.40_GRCh38.p14_genomic.gff.gz
/var/data/eamos/bio_assets/transcripts/eamos-coordinate-index.latest.jsonl.gz
```

Optional primer specificity after UCSC/Kent licensing approval:

```text
/var/data/eamos/bio_assets/bin/isPcr
/var/data/eamos/bio_assets/genomes/hg38.2bit
```

Planned source assets for later Workbench provenance cleanup:

```text
/var/data/eamos/bio_assets/dbsnp/GCF_000001405.40.gz
/var/data/eamos/bio_assets/dbsnp/GCF_000001405.40.gz.tbi
/var/data/eamos/bio_assets/clinvar/clinvar.vcf.gz
/var/data/eamos/bio_assets/clinvar/clinvar.vcf.gz.tbi
/var/data/eamos/bio_assets/protein_annotation/Pfam-A.hmm
/var/data/eamos/bio_assets/protein_annotation/Pfam-A.hmm.h3*
/var/data/eamos/bio_assets/predictors/alphamissense/AlphaMissense_hg38.tsv.gz
```

## CRISPR Off-Target Full-Index Runbook

Full build input source:

```text
kind: twobit
genome_build: GRCh38
source: UCSC hg38.2bit
source_version: ucsc-hg38-md5-dcc3ea27079aa6dc3f9deccd7275e0f8
expected path on build host: /var/data/eamos/bio_assets/genomes/hg38.2bit
expected size: 835393456 bytes
expected MD5: dcc3ea27079aa6dc3f9deccd7275e0f8
```

Verify the source file before building:

```powershell
Get-FileHash -Algorithm MD5 /var/data/eamos/bio_assets/genomes/hg38.2bit
```

Estimate the full SpCas9 target count and conservative SQLite size:

```powershell
cd app/backend
python -m app.cli.eamos_crispr_offtarget_index estimate `
  --twobit /var/data/eamos/bio_assets/genomes/hg38.2bit `
  --genome-build GRCh38 `
  --source-version ucsc-hg38-md5-dcc3ea27079aa6dc3f9deccd7275e0f8
```

Build the full SQLite artifact on a host where the source file and destination
disk are visible:

```powershell
cd app/backend
python -m app.cli.eamos_crispr_offtarget_index build `
  --twobit /var/data/eamos/bio_assets/genomes/hg38.2bit `
  --output /var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite `
  --genome-build GRCh38 `
  --source-version ucsc-hg38-md5-dcc3ea27079aa6dc3f9deccd7275e0f8
```

Expected output path:

```text
/var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite
```

Generated artifact policy:

- Build outside the web deploy/startup path.
- Do not build or download the full index during Render build, predeploy, app
  startup, or request handling.
- Do not commit generated SQLite, genome, manifest, or index artifacts.

Checksum and manifest flow:

```powershell
cd app/backend
python -m app.cli.eamos_crispr_offtarget_index verify `
  --index /var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite `
  --genome-build GRCh38 `
  --min-target-count <estimate_target_count>

python -m app.cli.eamos_crispr_offtarget_index manifest `
  --index /var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite `
  --artifact-uri <private_artifact_uri> `
  --source-version ucsc-hg38-md5-dcc3ea27079aa6dc3f9deccd7275e0f8 `
  > /var/data/eamos/bio_assets/crispr/spcas9_offtargets.manifest.json
```

Expected manifest fields:

- `ready=true`
- `actual_sha256` is present and 64 hex characters
- `target_count` matches the verified artifact
- `source_version=ucsc-hg38-md5-dcc3ea27079aa6dc3f9deccd7275e0f8`
- `launch_gate=null`
- `local_path_values_emitted=false`

Pilot/tiny proof when the full build is not practical locally:

```powershell
$proof = Join-Path $env:TEMP "eamos-crispr-offtarget-proof"
New-Item -ItemType Directory -Force $proof | Out-Null
$tiny = Join-Path $proof "tiny.fa"
$index = Join-Path $proof "spcas9_offtargets.sqlite"
Set-Content -LiteralPath $tiny -Value ">chrPilot`nGAGTCCGAGCAGAAGAAGATAGGNNNNNNNNNNNNNNNNNNNN"

cd app/backend
python -m app.cli.eamos_crispr_offtarget_index estimate `
  --fasta $tiny `
  --genome-build GRCh38 `
  --source-version pilot-tiny
python -m app.cli.eamos_crispr_offtarget_index build `
  --fasta $tiny `
  --output $index `
  --genome-build GRCh38 `
  --source-version pilot-tiny
python -m app.cli.eamos_crispr_offtarget_index verify `
  --index $index `
  --genome-build GRCh38 `
  --min-target-count 1
python -m app.cli.eamos_crispr_offtarget_index manifest `
  --index $index `
  --artifact-uri <private_artifact_uri> `
  --source-version pilot-tiny
```

Pilot proof criteria:

- estimate reports `target_count >= 1`
- build returns `ready=true`
- verify returns `verification_ready=true`, `genome_build_matches=true`, and
  `target_count_meets_min=true`
- manifest returns `ready=true` and a 64-character `actual_sha256`
- every command reports `local_path_values_emitted=false`

Render copy and mount instructions:

- Copy `spcas9_offtargets.sqlite` and `spcas9_offtargets.manifest.json` onto the
  mounted Render disk under `/var/data/eamos/bio_assets/crispr/`.
- Use Render Shell, `scp`, or a controlled runtime copy command during an
  off-peak maintenance window.
- After copy, rerun `verify` and `manifest` against the mounted file.
- Only after provider-cache proves the mounted artifact is ready should
  `CRISPR_OFFTARGET_PROVIDER` be changed from `auto` to `indexed_sqlite`.

Task 4 proof captured 2026-06-13 22:15 +1000:

- Full hg38 build was not run locally in this session.
- Tiny proof used a synthetic FASTA with one SpCas9 NGG target and wrote only
  to `%TEMP%`, outside the repo.
- `estimate`: `target_count=1`, `estimated_sqlite_bytes=66720`.
- `build`: `ready=true`, `target_count=1`.
- `verify`: `verification_ready=true`.
- `manifest`: `ready=true`, `actual_sha256` length `64`.
- `query`: one site returned for guide `GAGTCCGAGCAGAAGAAGAT`.
- Combined CLI proof had `local_path_values_emitted=false`.
- Focused tests/smokes passed:
  - `python -m pytest tests\test_crispr_offtarget_index_cli.py tests\test_workbench_render_approval_bundle_cli.py tests\test_health_api.py -q`
  - `python -m ruff check app\cli\eamos_workbench_render_approval_bundle.py tests\test_workbench_render_approval_bundle_cli.py app\services\crispr_offtarget_index.py tests\test_crispr_offtarget_index_cli.py tests\test_health_api.py`
  - `python -m black --check --target-version py310 app\cli\eamos_workbench_render_approval_bundle.py tests\test_workbench_render_approval_bundle_cli.py`
  - `python -m app.cli.eamos_crispr_offtarget_index --help`
  - `python -m app.cli.eamos_workbench_render_approval_bundle --compact`
  - `python -m json.tool docs\proprietary\index.json`
  - `git diff --check -- <Task 4 touched paths>`
- Read-only live provider-cache smoke passed for SG and Vercel:
  `configured_provider=auto`, `status=mock_fallback`,
  `indexed_sqlite.ready=false`, and `request_time_supabase_search=false`.

## Env Changes

Do not change before approval:

```text
LLM_PROVIDER=mock
CRISPR_OFFTARGET_PROVIDER=auto
PRIMER_SPECIFICITY_PROVIDER=template
```

After the SpCas9 SQLite artifact is mounted and provider-cache reports ready:

```text
CRISPR_OFFTARGET_PROVIDER=indexed_sqlite
CRISPR_OFFTARGET_INDEX_PATH=/var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite
```

Reference-window support:

```text
HG38_2BIT_RUNTIME_ASSET_MODE=mounted_volume
HG38_2BIT_RUNTIME_ASSET_PATH=/var/data/eamos/bio_assets/genomes/hg38.2bit
COORDINATE_RESOLVER_HG38_2BIT_PATH=/var/data/eamos/bio_assets/genomes/hg38.2bit
COORDINATE_RESOLVER_MANE_GFF_PATH=/var/data/eamos/bio_assets/transcripts/MANE.GRCh38.v1.5.refseq_genomic.gff.gz
COORDINATE_RESOLVER_REFSEQ_GFF_PATH=/var/data/eamos/bio_assets/transcripts/GCF_000001405.40_GRCh38.p14_genomic.gff.gz
COORDINATE_RESOLVER_COMPACT_INDEX_PATH=/var/data/eamos/bio_assets/transcripts/eamos-coordinate-index.latest.jsonl.gz
```

Optional whole-genome primer specificity after licensing approval:

```text
PRIMER_SPECIFICITY_PROVIDER=ucsc_ispcr
UCSC_ISPCR_BINARY_PATH=/var/data/eamos/bio_assets/bin/isPcr
UCSC_ISPCR_HG38_PATH=/var/data/eamos/bio_assets/genomes/hg38.2bit
```

Optional protein annotation after HMMER/Pfam is materialized and indexed:

```text
PROTEIN_ANNOTATION_ENABLED=true
PROTEIN_ANNOTATION_PFAM_HMM_PATH=/var/data/eamos/bio_assets/protein_annotation/Pfam-A.hmm
```

Not finalized in code yet:

- dbSNP runtime VCF/TBI env names for primer SNP masking;
- ClinVar gene-window VCF/TBI env names for viewer tracks;
- AlphaMissense viewer heatmap env names.

## Preflight Commands

Run these on the host where the mounted files are visible:

```powershell
cd app/backend
python -m app.cli.eamos_workbench_preflight --compact

python -m app.cli.eamos_crispr_offtarget_preflight `
  --index-path /var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite `
  --provider indexed_sqlite `
  --genome-build GRCh38 `
  --min-target-count <manifest_target_count> `
  --require-ready `
  --compact
```

Expected:

- `ready_to_flip=true`
- `runtime_status=indexed_ready`
- `indexed_sqlite.verification_ready=true`
- `indexed_sqlite.local_path_values_emitted=false`

Then record the immutable manifest:

```powershell
cd app/backend
python -m app.cli.eamos_crispr_offtarget_index manifest `
  --index /var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite `
  --artifact-uri <private_artifact_uri> `
  --source-version <source_genome_version> `
  > /var/data/eamos/bio_assets/crispr/spcas9_offtargets.manifest.json
```

Expected:

- `ready=true`
- `actual_sha256` is present and recorded;
- `launch_gate=null`;
- `local_path_values_emitted=false`.

Readiness checks that should remain non-mutating:

```powershell
cd app/backend
python -m app.cli.eamos_crispr_score_preflight --compact
python -m app.cli.eamos_source_asset_preflight --compact
python -m app.cli.eamos_workbench_render_approval_bundle --compact
```

Status update - 2026-06-13 23:20 +1000 - Codex:

- Added `python -m app.cli.eamos_crispr_offtarget_preflight`, the normalized
  CRISPR off-target preflight wrapper used by runbooks. It emits sanitized JSON,
  reports auto-mode warning fallback separately from forced indexed fail-closed,
  and supports `--require-ready`.
- Extended `python -m app.cli.eamos_workbench_preflight --compact` with a single
  local ready/not-ready bundle for fixture freshness, cache readability,
  full-gene fixture timing, CRISPR off-target public runtime posture, primer
  specificity posture, CRISPR score runtime posture, CRISPR index flip
  readiness, and compact coordinate index readiness.
- No Render env, provider mode, storage, startup download, or generated source
  asset changed.

## Approval Questions

- Is the SG Render persistent disk mounted at `/var/data`?
- Where will the full SpCas9 SQLite index be built and copied from?
- What off-peak maintenance window should cover disk attach and env changes?
- Is UCSC/Kent `isPcr` licensing acceptable for production deployment?
- Which of dbSNP, ClinVar, Pfam/HMMER, and AlphaMissense are approved for this
  provider-flip window versus later track-level cleanup?

## Post-Flip Smoke

SG backend:

```powershell
curl -fsS https://eamos-dev-sg.onrender.com/healthz
curl -fsS https://eamos-dev-sg.onrender.com/api/v1/health/provider-cache
```

Vercel proxy:

```powershell
curl -fsS https://eamos-dev.vercel.app/api/v1/health/provider-cache
```

Expected provider-cache checks:

- `providers.crispr.off_target_screening.configured_provider=indexed_sqlite`
- `providers.crispr.off_target_screening.indexed_sqlite.ready=true`
- `providers.crispr.off_target_screening.request_time_supabase_search=false`
- no local paths, object URIs, or secrets in the JSON response.

Workbench API probes:

- `POST /api/v1/primer/design`
- `POST /api/v1/crispr/design`
- `POST /api/v1/crispr/offtargets`
- `POST /api/v1/crispr/screening-primers`
- `POST /api/v1/crispr/ssodn`
- `POST /api/v1/align/reference`
- `POST /api/v1/crispr/tide`

## Rollback

Set:

```text
CRISPR_OFFTARGET_PROVIDER=auto
PRIMER_SPECIFICITY_PROVIDER=template
PROTEIN_ANNOTATION_ENABLED=false
```

Keep:

```text
LLM_PROVIDER=mock
```

Then verify:

```powershell
curl -fsS https://eamos-dev-sg.onrender.com/healthz
curl -fsS https://eamos-dev-sg.onrender.com/api/v1/health/provider-cache
```
