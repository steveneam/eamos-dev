# Render Provider Flip Workflows

Last live proof: 2026-06-14 01:47 +10:00.

This runbook captures the proven SG Render workflow for source-asset
materialization and provider flips. Keep it secret-free: command examples may
name env vars, service IDs, public URLs, and private Storage object paths, but
must not print API keys, service-role keys, JWTs, database URLs, or signed URLs.

## SG Anchors

- Render service: `srv-d8ctvoh9rddc73a27nb0`
- Render URL: `https://eamos-dev-sg.onrender.com`
- Render disk mount: `/var/data/eamos`
- Render Shell URL: `https://dashboard.render.com/web/srv-d8ctvoh9rddc73a27nb0/shell`
- Local API auth expected: `RENDER_API_KEY`
- Health endpoints:
  - `GET /healthz`
  - `GET /api/v1/health/provider-cache`

## Hard Gates

- Keep `LLM_PROVIDER=mock` unless the AI gateway security gate explicitly
  clears a provider flip.
- Do not use Render one-off jobs to materialize files onto the web service
  persistent disk. Use Render Shell, direct SSH/SCP, or a controlled command in
  the live service runtime.
- Render disk is a runtime cache only. Supabase private Storage/Postgres remain
  durable sources.
- No startup, build-time, or predeploy source downloads for large assets.
- Provider env flips happen only after mounted artifacts are verified by a CLI
  smoke or provider-cache readiness.
- `COORDINATE_RESOLVER_ASSET_MATERIALIZATION_ENABLED=false` remains the
  default; raw GFF paths are offline build inputs, not runtime scan inputs.
- Provider-cache and public health output must stay path/object-URI/secret
  sanitized.

## Observe Live State

PowerShell:

```powershell
$base = "https://eamos-dev-sg.onrender.com"
$health = Invoke-RestMethod -Uri "$base/healthz" -Method Get -TimeoutSec 30
$providerCache = Invoke-RestMethod -Uri "$base/api/v1/health/provider-cache" -Method Get -TimeoutSec 60

[pscustomobject]@{
  healthz = $health
  protein_annotation = $providerCache.providers.protein_annotation
  compact_coordinate_index = $providerCache.source_assets.compact_coordinate_index
  hg38_2bit = $providerCache.source_assets.hg38_2bit
  crispr = $providerCache.providers.crispr_off_target_screening
} | ConvertTo-Json -Depth 10
```

## Render Disk Access

Direct SSH can be blocked by local network policy. If this times out before
authentication, use Render Dashboard Shell instead.

```powershell
Test-NetConnection ssh.singapore.render.com -Port 22 |
  Select-Object ComputerName,RemoteAddress,RemotePort,TcpTestSucceeded
```

Dashboard path:

1. Open `https://dashboard.render.com/web/srv-d8ctvoh9rddc73a27nb0/shell`.
2. Confirm the prompt is the live service instance and current directory is
   `/app`.
3. Start with a read-only inventory:

```bash
bash -lc 'printf "pwd=%s\n" "$PWD"; df -h /var/data/eamos; for p in \
/var/data/eamos/bio_assets/genomes/hg38.2bit \
/var/data/eamos/bio_assets/transcripts/eamos-coordinate-index.latest.jsonl.gz \
/var/data/eamos/bio_assets/protein_annotation/Pfam-A.hmm \
/var/data/eamos/bio_assets/protein_annotation/downloads/Pfam-A.hmm.gz; do \
if [ -e "$p" ]; then stat -c "path=%n size=%s" "$p"; else echo "missing=$p"; fi; \
done; for b in python python3 hmmscan hmmpress gunzip; do \
command -v "$b" >/dev/null 2>&1 && echo "tool=$b ok" || echo "tool=$b missing"; \
done; for k in SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY PROTEIN_ANNOTATION_ENABLED \
PROTEIN_ANNOTATION_PFAM_HMM_PATH COORDINATE_RESOLVER_COMPACT_INDEX_PATH \
HG38_2BIT_RUNTIME_ASSET_PATH; do \
if [ -n "${!k}" ]; then echo "env=$k set"; else echo "env=$k missing"; fi; \
done'
```

## Reusable Source Asset Materialization Workflow

Use this workflow for any private source asset that must be registered in
Supabase and materialized onto the Render SG persistent disk. It is deliberately
asset-agnostic so Pfam, compact coordinate indexes, CRISPR indexes, and future
runtime assets follow the same proof path.

1. Confirm the private Storage object and manifest exist before touching Render.
   Query `storage.objects` plus the `eamos_private` inventory tables; the
   source object must remain private and must not be exposed to frontend/public
   buckets.
2. Register durable metadata first:
   `eamos_private.local_source_versions`, the main
   `eamos_private.source_asset_objects` row, any manifest/sidecar object row,
   and the target `eamos_private.source_asset_materializations` row. The
   materialization starts as `download_pending`; do not mark it `ready` from
   Supabase metadata alone.
3. Preserve provenance and launch-gate fields on every row: release/version,
   checksum, byte size, source URI, license/review status, approval status, and
   explicit `public_exposure_allowed=false` / frontend access disabled unless a
   separate launch decision says otherwise.
4. In Render Dashboard Shell from `/app`, run a read-only preflight first:
   confirm `/var/data/eamos` disk space, target file state, required tools, and
   required env var presence. Check only whether secrets are set; never print
   secret values.
5. Use the committed asset materializer CLI when the deployed image contains the
   needed reader/validator fixes. If the live image predates a local fix, either
   deploy the fix first or document a one-off Render Shell workaround that stages
   under a reader-compatible temp suffix and emits sanitized JSON only.
6. Verify on Render before the atomic move: expected byte size, checksum,
   schema/reader smoke, required counts, and fail-closed behavior. Only then
   replace the target path on the persistent disk.
7. If the web process caches provider-cache state, trigger a deploy-only restart
   of the existing build. Do not change env vars, provider modes, build
   commands, predeploy commands, or startup downloads as part of a materialization
   proof unless that is separately approved.
8. Accept readiness from live health, not from files alone. Verify `/healthz`
   and `/api/v1/health/provider-cache`; the relevant `source_assets.*.ready`
   field and build-ledger item must agree with the materialized disk proof.
9. Reconcile the Supabase materialization row from `download_pending` to `ready`
   only after live provider-cache proof. Include `verified_at`, `ready_marker`,
   checksum/size, source object URI, Render service id, and guardrail metadata
   showing no startup download, no public/frontend exposure, and no raw runtime
   scan.
10. If the asset is ready but the build ledger remains inconsistent, treat that
    as a deployed-code blocker. Record it in metadata/docs, but do not mask it by
    downgrading a proven materialization back to `download_pending`.

## Protein Pfam/HMMER Flip

Status after 2026-06-13 proof:

- Disk had `hg38.2bit` ready.
- Pfam files were absent before the run.
- Live image had `python`, `hmmscan`, `hmmpress`, and `gunzip`.
- `eamos_pfam_runtime_materialize` existed in the live image.
- Materialization downloaded the private Pfam object, verified MD5 and SHA256,
  extracted `Pfam-A.hmm`, ran `hmmpress`, and passed ABCA4 smoke.
- Provider-cache after env flip reported
  `providers.protein_annotation.status=available`,
  `available=true`, and `hmmer.missing_index_count=0`.
- Supabase `eamos_private.source_asset_materializations` was reconciled at
  2026-06-14 01:19 +1000: Pfam SG materialization is `ready` with the
  persistent-disk gz path, MD5 `dc814cc181ece09102c09c4e6c19f2fd`, and ready
  marker `render_sg_provider_cache_available_hmmer_ready`.

Materialize from Render Shell:

```bash
time python -m app.cli.eamos_pfam_runtime_materialize \
  --compact \
  --source-object-uri supabase://eamos-source-assets/hmmer_pfam_a/pfam_current_release_2026-05-29/md5-dc814cc181ece09102c09c4e6c19f2fd/Pfam-A.hmm.gz \
  --pfam-hmm-gz-path /var/data/eamos/bio_assets/protein_annotation/downloads/Pfam-A.hmm.gz \
  --pfam-hmm-path /var/data/eamos/bio_assets/protein_annotation/Pfam-A.hmm \
  --prepare \
  --smoke-control ABCA4 \
  --require-ready \
  --hmmscan-timeout-seconds 90 \
  --hmmpress-timeout-seconds 1800
```

Expected success fields in compact JSON:

- `materialization.status=ready`
- `materialization.md5_verified=true`
- `materialization.sha256_verified=true`
- `runtime_prepare.status=ready`
- `runtime_prepare.hmmpress_ran=true`
- `runtime_prepare.missing_index_count=0`
- `protein_smokes[0].status=available`

Flip env via Render API, then redeploy the existing build:

```powershell
$ErrorActionPreference = "Stop"
$serviceId = "srv-d8ctvoh9rddc73a27nb0"
$headers = @{
  Authorization = "Bearer $env:RENDER_API_KEY"
  Accept = "application/json"
  "Content-Type" = "application/json"
}

$updates = [ordered]@{
  PROTEIN_ANNOTATION_ENABLED = "true"
  PROTEIN_ANNOTATION_PFAM_HMM_PATH = "/var/data/eamos/bio_assets/protein_annotation/Pfam-A.hmm"
}

foreach ($key in $updates.Keys) {
  $body = @{ value = $updates[$key] } | ConvertTo-Json
  Invoke-RestMethod `
    -Headers $headers `
    -Uri "https://api.render.com/v1/services/$serviceId/env-vars/$key" `
    -Method Put `
    -Body $body | Out-Null
}

$deployBody = @{ deployMode = "deploy_only" } | ConvertTo-Json
$deploy = Invoke-RestMethod `
  -Headers $headers `
  -Uri "https://api.render.com/v1/services/$serviceId/deploys" `
  -Method Post `
  -Body $deployBody

$deploy.id
```

Poll deploy:

```powershell
$deployId = "<deploy id>"
$deadline = (Get-Date).AddMinutes(6)
do {
  $deploy = Invoke-RestMethod `
    -Headers @{ Authorization = "Bearer $env:RENDER_API_KEY"; Accept = "application/json" } `
    -Uri "https://api.render.com/v1/services/srv-d8ctvoh9rddc73a27nb0/deploys/$deployId" `
    -Method Get
  "$((Get-Date).ToString('o')) $($deploy.status)"
  if ($deploy.status -in @("live", "build_failed", "update_failed", "canceled")) { break }
  Start-Sleep -Seconds 10
} while ((Get-Date) -lt $deadline)
```

Verify:

```powershell
$base = "https://eamos-dev-sg.onrender.com"
Invoke-RestMethod -Uri "$base/healthz" -Method Get -TimeoutSec 30
(Invoke-RestMethod -Uri "$base/api/v1/health/provider-cache" -Method Get -TimeoutSec 60).providers.protein_annotation |
  ConvertTo-Json -Depth 8
```

Rollback:

```powershell
$serviceId = "srv-d8ctvoh9rddc73a27nb0"
$headers = @{
  Authorization = "Bearer $env:RENDER_API_KEY"
  Accept = "application/json"
  "Content-Type" = "application/json"
}

Invoke-RestMethod `
  -Headers $headers `
  -Uri "https://api.render.com/v1/services/$serviceId/env-vars/PROTEIN_ANNOTATION_ENABLED" `
  -Method Put `
  -Body (@{ value = "false" } | ConvertTo-Json) | Out-Null

Invoke-RestMethod `
  -Headers $headers `
  -Uri "https://api.render.com/v1/services/$serviceId/deploys" `
  -Method Post `
  -Body (@{ deployMode = "deploy_only" } | ConvertTo-Json)
```

## Compact Coordinate Index

Current status after the 2026-06-14 compact-index publish/materialization proof:

- `HG38_2BIT_RUNTIME_ASSET_PATH` is set and the file exists.
- `COORDINATE_RESOLVER_COMPACT_INDEX_PATH` is set to
  `/var/data/eamos/bio_assets/transcripts/eamos-coordinate-index.latest.jsonl.gz`.
- The production transcript-only compact artifact was built locally from
  private MANE/RefSeq GFF inputs, uploaded to private Supabase Storage, and
  materialized back locally through the same private-storage CLI path.
- Supabase metadata registration is done: source version, artifact object,
  manifest sidecar, and SG materialization row.
- Render Shell materialization is done. The live `550641d` CLI failed on the
  known temp `.tmp` gzip validation bug, so the successful Render Shell proof
  staged the private Storage object under a `.jsonl.gz` temp name, verified
  size/SHA256, validated schema/counts, and atomically moved it to the target.
- Deploy-only restart `dep-d8mnkq9o3t8c73c1m6k0` cleared the web-process
  missing cache.
- Live SG health now reports
  `source_assets.compact_coordinate_index.status=ready` and
  `build_ledger.items.coordinate_compact_index.status=ready`.
- Gene View remains `runtime_partial` only because deployed commit `550641d`
  has a stale build-ledger blocker; the local worktree already fixes
  `_gene_view_item` to use `coordinate_index_status`.

Do not point runtime at raw GFF scans. Build the compact index offline from
release-pinned source inputs with the committed transcript-only builder:

```bash
python -m app.cli.eamos_compact_index_build \
  --mane-gff <MANE.GRCh38.refseq_genomic.gff.gz> \
  --refseq-gff <GCF_000001405.40_GRCh38.p14_genomic.gff.gz> \
  --all-genes \
  --output <staging>/eamos-coordinate-index.latest.jsonl.gz \
  --require-ready \
  --compact
```

Pilot builds can use `--gene` or `--gene-list`; production builds should use
`--all-genes`. The builder emits transcript geometry only, so ClinVar/dbSNP
variant rows can be enriched later without inventing clinical evidence.

Published compact artifact:

- Object URI:
  `supabase://eamos-source-assets/transcripts/eamos_coordinate_index/eamos-coordinate-index.2026-06-14-transcript-gff-v1.jsonl.gz`
- Manifest object:
  `transcripts/eamos_coordinate_index/eamos-coordinate-index.2026-06-14-transcript-gff-v1.jsonl.gz.manifest.json`
- Artifact version: `2026-06-14-transcript-gff-v1`
- Size: `11597735`
- SHA256:
  `8b9e2b8c706d11823e92e25d2aaca23b2af978e086580667491ac141bfbf856e`
- Transcript count: `130509`
- Gene count: `20318`
- Variant count: `0`; this build intentionally contains transcript geometry
  only and does not infer ClinVar or ClinGen evidence.

The materializer validates gzip payloads by magic bytes as well as `.gz`
suffix, because private-storage downloads are schema-checked while staged under
a temporary `.tmp` name.

Materialize it from Render Shell using the committed CLI after the gzip-magic
fix is deployed:

```bash
python -m app.cli.eamos_compact_index_materialize \
  --source-object-uri supabase://eamos-source-assets/transcripts/eamos_coordinate_index/eamos-coordinate-index.2026-06-14-transcript-gff-v1.jsonl.gz \
  --compact-index-path /var/data/eamos/bio_assets/transcripts/eamos-coordinate-index.latest.jsonl.gz \
  --expected-size-bytes 11597735 \
  --expected-sha256 8b9e2b8c706d11823e92e25d2aaca23b2af978e086580667491ac141bfbf856e \
  --require-ready \
  --compact
```

Expected success fields:

- `materialization.status=ready`
- `materialization.downloaded=true`
- `materialization.sha256_verified=true`
- `materialization.schema_validated=true`
- `materialization.transcript_count=130509`
- `guardrails.startup_downloads=not_used`
- `guardrails.raw_gff_runtime_scan=not_used`

On live `550641d`, do not repeat the failed CLI form; it validates the private
Storage temp download as `.tmp` and returns `schema_validation_failed` even
after SHA256 passes. The one-off workaround already succeeded and should be
superseded by deploying the local gzip-magic reader fix.

Only after provider-cache reports the compact index ready should any coordinate
or Gene View provider env be changed.

## Workbench CRISPR Off-Target Runtime

Use this same workflow for Workbench off-target assets. The other Workbench
approval docs can own CRISPR-specific artifact policy, but Render execution
should still follow this file for disk access, env flips, deploy-only redeploys,
provider-cache verification, and rollback.

Current SG policy:

- Keep `CRISPR_OFFTARGET_PROVIDER=auto` unless a real indexed artifact is mounted
  and provider-cache reports `indexed_sqlite.ready=true`.
- Do not commit generated genome, guide, or SQLite index artifacts.
- Do not use Render one-off jobs to seed the SG web service disk.
- Use Render Shell, direct SSH/SCP, or a controlled runtime command during an
  explicit maintenance window.
- Keep Workbench fallback labels until provider-cache proves the mounted
  artifact is ready after redeploy.

Expected shape:

```bash
# Run from Render Shell after the CRISPR SQLite index has been copied or
# materialized onto /var/data/eamos.
python -m app.cli.eamos_crispr_offtarget_preflight \
  --index-path /var/data/eamos/bio_assets/crispr/offtarget/<index>.sqlite \
  --require-ready \
  --compact
```

Then, and only then, flip provider env through the targeted Render API pattern
from the Pfam section:

```powershell
$updates = [ordered]@{
  CRISPR_OFFTARGET_PROVIDER = "indexed_sqlite"
  CRISPR_OFFTARGET_INDEX_PATH = "/var/data/eamos/bio_assets/crispr/offtarget/<index>.sqlite"
}
```

After deploy-only redeploy, verify:

```powershell
$pc = Invoke-RestMethod `
  -Uri "https://eamos-dev-sg.onrender.com/api/v1/health/provider-cache" `
  -Method Get `
  -TimeoutSec 60

$pc.providers.crispr_off_target_screening | ConvertTo-Json -Depth 8
```

Rollback is env-only:

```powershell
$updates = [ordered]@{
  CRISPR_OFFTARGET_PROVIDER = "auto"
  CRISPR_OFFTARGET_INDEX_PATH = ""
}
```

## Local Adapter Full-Set Materialization

The build ledger separates "wired" from "materialized". Backend wiring exists
for several local adapters, but most are not yet live because their runtime
assets are not on the SG disk or not represented in source-asset metadata.

Observed Supabase/Render state on 2026-06-14:

| Lane | Durable source observed | Render disk | Provider-cache/build-ledger status | Next action |
| --- | --- | --- | --- | --- |
| `hg38_2bit` | source metadata + Storage object | ready | `ready` | no flip needed |
| `protein_pfam` | source metadata + Storage object; materialization metadata reconciled to `ready` | ready | `available` | monitor/cache smoke |
| `coordinate_compact_index` | compact artifact + manifest in private Storage; metadata ready | ready | `ready` | deploy local build-ledger fix so Gene View ledger stops carrying the stale compact-index blocker |
| `alphamissense` | registry metadata; no private Storage object observed on 2026-06-14 | missing | `missing_source_file` | stage/upload durable object, then seed bgzip+tbi in a maintenance window |
| `dbsnp_local_adapter` | Storage object observed, source metadata gap | missing | `source_ready_for_materialization` | register/verify metadata, seed bgzip+tbi |
| `phylop_conservation_reader` | Storage object observed, source metadata gap | missing | `source_ready_for_materialization` | register/verify metadata, seed bigWig |
| `clinvar_local_adapter` | not proven in this pass | missing | `source_ready_for_materialization` | locate/register/seed bgzip+tbi |
| `repeatmasker_local_adapter` | not proven in this pass | missing | `source_ready_for_materialization` | locate/register/seed compact interval index |
| `local_evidence_orchestrator` | mixed | disabled | `disabled` | enable only after whole indexed batch is green |

The next backend work should close the source metadata gaps before large-file
materialization. Prefer committed CLIs/services over manual SQL so provenance,
license, launch-gate, checksum, and materialization rows stay consistent.

## AlphaMissense Runtime Materialization

AlphaMissense is about 643 MB compressed, but bgzip/tabix indexing can still
stress the live web process. After the 2026-06-14 memory-limit restart warning
on `eamos-dev-sg`, treat this as a maintenance-window operation, not a casual
runtime command.

Preflight from Render Shell:

```bash
bash -lc 'pwd; df -h /var/data/eamos; free -h; command -v python; python - <<PY
import importlib.util
print("pysam", bool(importlib.util.find_spec("pysam")))
PY'
```

Materialize with the committed streaming CLI only after the current code is
deployed:

```bash
time python -m app.cli.eamos_alphamissense_runtime_materialize \
  --target-path /var/data/eamos/bio_assets/predictors/alphamissense/AlphaMissense_hg38.tsv.gz \
  --expected-size-bytes 642961469 \
  --expected-md5 9fd167735f16a1b87da6eb3e4c25fcb5 \
  --require-ready \
  --compact
```

The CLI streams the download, verifies MD5/size, creates
`AlphaMissense_hg38.tsv.gz.tbi`, writes a sanitized manifest, and runs the same
runtime preflight used by provider-cache. It does not mutate Supabase, Render
env vars, deployments, startup commands, or provider flags.

After the CLI reports ready, the SG service env must point the runtime reader at
the persistent-disk path before provider-cache and request-time lookups can see
the asset:

```text
ALPHAMISSENSE_HG38_RUNTIME_ASSET_PATH=/var/data/eamos/bio_assets/predictors/alphamissense/AlphaMissense_hg38.tsv.gz
ALPHAMISSENSE_HG38_RUNTIME_ASSET_MODE=local_path
```

Apply only those AlphaMissense env values, then use a deploy-only restart of the
current build so the web process reloads settings. Keep `LLM_PROVIDER=mock` and
do not change unrelated provider flags.

Verify after materialization:

```powershell
$pc = Invoke-RestMethod `
  -Uri "https://eamos-dev-sg.onrender.com/api/v1/health/provider-cache" `
  -Method Get `
  -TimeoutSec 60

$pc.providers.indexed_predictors.alphamissense | ConvertTo-Json -Depth 8
```

If provider-cache is stale after file readiness and env reload, use one further
deploy-only restart of the existing build.

## Supabase Cross-Check

Use Supabase as the durable source inventory, not as proof of Render runtime
readiness. For each asset lane, cross-check:

- Storage object exists in the private bucket.
- `eamos_private.source_asset_objects` has a release/provenance/checksum row.
- `eamos_private.source_asset_materializations` has the Render target row.
- Render disk file exists and matches expected size/checksum.
- Provider-cache reports ready without exposing paths or object URIs.

If the Supabase docs search connector asks for reauthentication, use the active
Supabase project tools for inventory and official Supabase web docs for current
documentation. Do not block source inventory on docs-search auth.
