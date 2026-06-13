# Backend Build Ledger Materialization Plan

Status: Current execution plan
Owner: Codex/backend
Last verified: 2026-06-14 01:47 +1000

## Purpose

This plan is the working checklist for moving build-ledger rows from "wired"
or "source ready" to actually usable on the SG Render backend. It complements
the local-first source rollout plan and the Render provider flip workflow:

- source and approval intent lives in
  `docs/local-first-data-source-strategy/source-asset-rollout.md`;
- runtime policy and ledger shape live in
  `docs/backend-build-ledger-runtime/design.md`;
- Render shell/provider flip steps live in
  `docs/deployment/render-provider-flip-workflows.md`.

Use this document when deciding what to materialize next. Do not use Workbench
or CRISPR off-target work as the default lane here; keep those separate unless
the user explicitly redirects.

## Current State

Live SG health was checked on 2026-06-14:

| Ledger lane | Live status | Meaning |
| --- | --- | --- |
| `hg38_2bit` | `ready` | Render disk has the verified hg38.2bit runtime asset. |
| `protein_pfam` | `available` | Pfam/HMMER is materialized and enabled on SG. |
| `coordinate_compact_index` | `ready` | Compact artifact is registered in Supabase, materialized on SG Render disk, schema-validated, and visible in provider-cache. |
| `gene_view` | `runtime_partial` | Asset blockers are cleared; deployed commit `550641d` still has the stale ledger blocker. Local `build_ledger.py` already fixes this and needs a coordinated code deploy. |
| `dbsnp_local_adapter` | `source_ready_for_materialization` | Fixture adapter exists; production object exists in Storage but metadata/runtime wiring is incomplete. |
| `phylop_conservation_reader` | `source_ready_for_materialization` | Reader proof exists; production object exists in Storage but metadata/runtime wiring is incomplete. |
| `clinvar_local_adapter` | `source_ready_for_materialization` | Fixture adapter exists; no durable production object was found in this pass. |
| `repeatmasker_local_adapter` | `source_ready_for_materialization` | Fixture adapter exists; no durable production object was found in this pass. |
| `local_evidence_orchestrator` | `disabled` | Correct until the full indexed-source batch is runtime-configured and verified. |
| `clinical_source_tables` | `import_ready` | Supabase tables are present but still fixture-scale. |

Supabase inventory checked on 2026-06-13:

| Area | Observed state | Required action |
| --- | --- | --- |
| `source_asset_objects` | Rows exist for hg38, Pfam, and the compact coordinate index artifact + manifest. | Register dbSNP, phyloP, ClinVar, and RepeatMasker objects before treating them as durable approved assets. |
| `source_asset_materializations` | hg38, Pfam, and compact coordinate index SG rows are `ready`. | Register remaining local-adapter materializations before runtime flips. |
| Storage prefix `transcripts/eamos_coordinate_index` | Compact index artifact and manifest uploaded, registered, and materialized on SG on 2026-06-14. | No repeat action; next blocker is deploying the local build-ledger Gene View fix. |
| Storage prefix `ncbi_dbsnp_gcf_000001405_40` | Six objects totaling about 29.6 GB exist. | Register metadata rows, then seed bgzip and `.tbi` onto Render. |
| Storage prefix `ucsc_phylop100way_hg38` | Four objects totaling about 9.9 GB exist. | Register metadata rows, then seed bigWig onto Render. |
| ClinVar / RepeatMasker prefixes | No durable objects observed. | Locate, upload, register, and verify before runtime work. |
| Clinical tables | MONDO/HPO/ClinGen/GenCC tables contain fixture-scale rows only. | Import release-pinned full tables separately from Render disk work. |

## Hard Gates

- Keep `LLM_PROVIDER=mock` until the AI-gateway release gate is intentionally
  crossed.
- Keep `CRISPR_OFFTARGET_PROVIDER=auto`; the full-index CRISPR lane belongs to
  the separate Workbench/off-target runbook.
- Do not enable coordinate or protein startup materialization.
- Do not point runtime at raw GFF scans.
- Do not use Render one-off jobs to seed the service persistent disk; they do
  not write to the mounted web-service disk.
- Do not enable `LOCAL_EVIDENCE_ENABLED=true` until dbSNP, ClinVar,
  RepeatMasker, phyloP, compact index, and hg38 are all production-path
  verified for the target flows.

## Sequence

### 1. Compact Coordinate Index

Goal: make `coordinate_compact_index=ready` and unblock Gene View.

2026-06-14 checkpoint:

- Built artifact:
  `.scratch/compact-coordinate-index/eamos-coordinate-index.latest.jsonl.gz`
- Uploaded object:
  `supabase://eamos-source-assets/transcripts/eamos_coordinate_index/eamos-coordinate-index.2026-06-14-transcript-gff-v1.jsonl.gz`
- Manifest object:
  `transcripts/eamos_coordinate_index/eamos-coordinate-index.2026-06-14-transcript-gff-v1.jsonl.gz.manifest.json`
- Artifact version: `2026-06-14-transcript-gff-v1`
- Size: `11597735`
- SHA256:
  `8b9e2b8c706d11823e92e25d2aaca23b2af978e086580667491ac141bfbf856e`
- Build contents: `130509` transcript rows, `20318` genes, `0` variant rows.
- Local proof passed: private Storage download, SHA256 verification, schema
  validation, and materialization through `eamos_compact_index_materialize`.
- Supabase metadata registration is done: source version, artifact object,
  manifest sidecar, and SG materialization row are present.
- Render Shell materialization is done. The committed CLI on live `550641d`
  still had the temp `.tmp` gzip validation bug, so a one-off Render Shell
  Python workaround staged the object under a `.jsonl.gz` name, verified size
  and SHA256, validated `eamos.coordinate_index.v1`, and atomically replaced the
  target file. A deploy-only restart cleared the web-process missing cache.
- Live SG now reports `source_assets.compact_coordinate_index.status=ready` and
  `build_ledger.items.coordinate_compact_index.status=ready`.
- Live SG still reports `build_ledger.items.gene_view.status=runtime_partial`
  because deployed commit `550641d` always appends the compact-index blocker in
  `_gene_view_item`. The local worktree already passes `coordinate_index_status`
  into `_gene_view_item`; deploy that code in the coordinated commit/deploy.

Steps:

1. Confirm whether a production compact index artifact already exists outside
   Render. **Done:** artifact did not exist before this run; a new artifact is
   now in private Storage.
2. If no artifact exists, run the offline builder that creates
   `eamos.coordinate_index.v1` JSONL.GZ from approved transcript inputs:

```bash
python -m app.cli.eamos_compact_index_build \
  --mane-gff <MANE.GRCh38.refseq_genomic.gff.gz> \
  --refseq-gff <GCF_000001405.40_GRCh38.p14_genomic.gff.gz> \
  --all-genes \
  --output <staging>/eamos-coordinate-index.latest.jsonl.gz \
  --require-ready \
  --compact
```

   Use `--gene` or `--gene-list` for pilot builds; `--all-genes` is required
   for the production transcript-model artifact.
3. Start with a transcript-model index if needed to unblock Gene View. Variant
   rows can be enriched later from curated ClinVar/dbSNP/catalog sources.
4. Validate locally with `CompactCoordinateIndex.inspection()`. **Done.**
5. Upload the artifact to private Supabase Storage and register a
   `source_asset_objects` row with checksum, size, approval, license, and
   materialization metadata. **Done.**
6. From the SG service runtime, run:

```bash
python -m app.cli.eamos_compact_index_materialize \
  --source-object-uri supabase://eamos-source-assets/transcripts/eamos_coordinate_index/eamos-coordinate-index.2026-06-14-transcript-gff-v1.jsonl.gz \
  --compact-index-path /var/data/eamos/bio_assets/transcripts/eamos-coordinate-index.latest.jsonl.gz \
  --expected-size-bytes 11597735 \
  --expected-sha256 8b9e2b8c706d11823e92e25d2aaca23b2af978e086580667491ac141bfbf856e \
  --require-ready \
  --compact
```

7. Verify `/api/v1/health/provider-cache`:
   - `source_assets.compact_coordinate_index.ready=true`
   - `build_ledger.items.coordinate_compact_index.status=ready`
   - `build_ledger.items.gene_view.status=ready` after the local build-ledger
     fix is deployed.

Current code note: the compact-index reader, builder, and materializer exist.
The local reader now validates gzip payloads by magic bytes as well as `.gz`
suffix so private-storage temp downloads schema-validate correctly. That fix is
not on live `550641d`; avoid repeating the Render Shell workaround after the
fix is deployed.

### 2. Metadata Reconciliation

Goal: make Supabase the durable source of truth before local adapter flips.

Steps:

1. **Done 2026-06-14 01:19 +1000:** reconciled the Pfam materialization row
   from `download_pending` to the live SG proof, preserving checksum, verified
   timestamp, persistent-disk path, and HMMER provider-cache readiness.
2. Register dbSNP Storage objects under `source_asset_objects`:
   - source id `ncbi_dbsnp_gcf_000001405_40`;
   - roles for bgzip VCF, tabix index, checksum/manifest objects;
   - approval and license status copied from the source rollout plan.
3. Register phyloP Storage objects under `source_asset_objects`:
   - source id `ucsc_phylop100way_hg38`;
   - roles for bigWig and checksum/manifest objects.
4. Locate or upload ClinVar GRCh38 VCF plus `.tbi` before any ClinVar runtime
   flip.
5. Locate or upload RepeatMasker official source plus the derived compact
   runtime interval index before any RepeatMasker runtime flip.

Prefer committed metadata CLIs/importers over manual SQL. If SQL is used for a
one-time reconciliation, capture the exact query in a follow-up runbook.

### 3. Runtime Path Wiring

Goal: make production local adapters configurable, not fixture-default.

The current local adapters are fixture-first and accept constructor paths, but
they are not yet fully exposed as production settings/runtime probes. Before
enabling local evidence, add or verify:

- dbSNP runtime path and index path settings;
- ClinVar runtime path and index path settings;
- RepeatMasker compact interval index path setting;
- phyloP bigWig path setting;
- sanitized provider-cache or preflight probes for each runtime file;
- tests proving fixture defaults are not used when production settings are
  configured.

### 4. Render Disk Seeding

Goal: place verified indexed artifacts on `/var/data/eamos` for the live web
service.

Batch order:

1. dbSNP bgzip VCF plus `.tbi`.
2. phyloP bigWig.
3. ClinVar bgzip VCF plus `.tbi`.
4. RepeatMasker compact interval index.

Use Render Shell, SSH/SCP, or a committed runtime CLI from the SG service
instance. Each seed must use temp-file download/copy, checksum verification,
and atomic rename. Health and preflight outputs must stay path-sanitized.

### 5. Local Evidence Gate

Goal: enable only the flows backed by verified production assets.

Only after the full batch is present and probes are green:

1. Set `LOCAL_EVIDENCE_ENABLED=true`.
2. Set `LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW` narrowly, starting with one or two
   flows such as `lookup,gene_viewer`.
3. Keep `LOCAL_EVIDENCE_REQUIRE_REAL_APIS=true`.
4. Verify provider-cache and targeted lookup/Gene View behavior.
5. Expand to `search` and `workbench` only after contract tests cover those
   surfaces.

## Immediate Next Tasks

1. Deploy the local build-ledger fix so Gene View stops reporting the stale
   compact-index blocker after the asset is ready.
2. Add production settings/probes for dbSNP, phyloP, ClinVar, and RepeatMasker
   runtime paths.
3. Register dbSNP and phyloP Storage objects in `source_asset_objects`.
4. Seed dbSNP and phyloP onto Render as the first local-adapter batch.

## Verification Commands

Run focused backend checks after code changes:

```bash
cd app/backend
python -m pytest tests/test_health_api.py tests/test_source_asset_preflight_cli.py tests/test_local_evidence_orchestrator.py -q
python -m ruff check app/services/build_ledger.py tests/test_health_api.py
python -m black --check --target-version py310 app/services/build_ledger.py tests/test_health_api.py
```

Run deployment checks after a Render materialization:

```bash
curl -fsS https://eamos-dev-sg.onrender.com/healthz
curl -fsS https://eamos-dev-sg.onrender.com/api/v1/health/provider-cache
```

The acceptance signal is the health JSON, not the presence of files alone.
