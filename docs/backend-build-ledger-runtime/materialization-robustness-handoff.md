# Materialization Robustness Handoff — Claude → Codex

Author: Claude · Created: 2026-06-21 00:27 +1000 · Lane: backend materialization (Codex)

## Why this exists

Steven asked me (Claude) to help unblock the M1/M5/M6/M7/M8 materialization
batch while a mobile hotspot opened the egress the work needs. Before seeding I
verified the **live** SG service state over SSH and found the current
manual-seed path works but is fragile. Steven's decision: **switch the hotspot
off, have Codex build the robust tooling first, then re-initiate the hotspot
(or skip it entirely if the 443-path lands) and seed.** This doc is the
self-contained handoff for that build. It does not change any code, env,
provider, or Supabase state.

Companion docs (yours): `plan.md`, `materialization-plan.md`,
`docs/deployment/render-provider-flip-workflows.md`,
`docs/deployment/render-coordinate-assets.md`.

## Live state verified tonight (2026-06-20/21, SG `srv-d8ctvoh9rddc73a27nb0`)

Egress map (this workstation, on work wifi unless noted):

| Target | Port | Result | Consequence |
| --- | --- | --- | --- |
| Supabase pooler `aws-1-ap-southeast-2.pooler.supabase.com` | 5432 | blocked | M3 clinical import dies |
| Render SSH `ssh.singapore.render.com` | 22 | blocked (hotspot opens it) | disk seeds need hotspot |
| Supabase Storage S3 `…storage.supabase.co` | 443 | open | uploads work from here |
| Render dashboard / SG health API | 443 | open | read-only checks work |

Disk: `/var/data/eamos` = 59 GB, **6.0 GB used**, 53 GB free. Readers present:
`pysam=True`, `pyBigWig=True`. Memory: `memory.max=2048MiB`,
`memory.current≈211MiB` (seeding is disk/network bound, low OOM risk). Live
image already contains `app/cli/eamos_local_evidence_runtime_seed.py`. App root
on SG = `/app`; PID 1 = uvicorn.

### Six fragilities found (the reason for this handoff)

1. **Runtime-path env vars are UNSET on the service.** Pydantic defaults are
   relative `./data/bio_assets/...` (ephemeral `/app`), NOT `/var/data`. Seeding
   to `/var/data` would not flip provider-cache until these are set. Affected
   settings: `dbsnp_runtime_vcf_path`, `dbsnp_runtime_index_path`,
   `clinvar_runtime_vcf_path`, `clinvar_runtime_index_path`,
   `repeatmasker_runtime_index_path`, `phylop_runtime_bigwig_path`,
   `clingen_local_sqlite_path`, `clingen_local_manifest_path`.
2. **No `SUPABASE_STORAGE_S3_*` on the service.** So `--download-mode
   s3_multipart` fails on SG; only `rest` works today. REST is a single
   non-resumable stream — risky for the 29.55 GB dbSNP object.
3. **SSH sessions carry none of the service env** (Render injects into PID 1
   only). Tonight's workaround would be sourcing `/proc/1/environ`. A path that
   runs *inside* the web process avoids this entirely.
4. **The seed CLI does not reconcile Supabase metadata**
   (`supabase_metadata_mutation: not_used`). This is exactly the
   `materialization_metadata_missing` trap that bit the 2026-06-15 AlphaMissense
   run twice.
5. **The derived RepeatMasker compact index has no Storage object and no upload
   CLI.** `eamos_source_storage_upload` only knows the raw `rmsk.txt.gz`;
   `eamos_generated_artifact_upload` only knows
   `clingen_local/pubmed_local/literature_embeddings`. So M7's "Storage-backed"
   path was never implemented; only the `--source-artifact` local-file seed
   exists.
6. **The hotspot dependency itself.** Materialization currently requires an
   operator on a non-firewalled network. But 443 is open on work wifi, and the
   web service can reach both Storage and the pooler — so a 443-triggered,
   in-process materialization removes the hotspot need for *all* of it
   (including M3).

## Pinned materialization manifest (source of truth for the orchestrator)

All objects live in private bucket `eamos-source-assets`. Destinations are the
persistent-disk paths the env vars must point at.

| Role / artifact | Object key (under bucket) | Size (bytes) | MD5 | SHA256 | Disk destination | Env var |
| --- | --- | --- | --- | --- | --- | --- |
| clingen_local sqlite | `generated/eamos_clingen_local/clingen_local_sqlite/sha256-50e12d4c0caaefceeece8f1e04de654158c5197a03fb6def991728591028dd9b/clingen-local.sqlite` | 527925248 | 60997c2c9a6837bd8614f489e79021fb | 50e12d4c0caaefceeece8f1e04de654158c5197a03fb6def991728591028dd9b | `/var/data/eamos/bio_assets/clingen/clingen-local.sqlite` | `CLINGEN_LOCAL_SQLITE_PATH` |
| clingen_local manifest | (sidecar `.manifest.json`) | — | — | — | `/var/data/eamos/bio_assets/clingen/clingen-local.manifest.json` | `CLINGEN_LOCAL_MANIFEST_PATH` |
| clinvar_bgzip_vcf | `ncbi_clinvar_vcf/clinvar_grch38_vcf_gz/sha256-bd3cdbc07bf26aa5d136219e2db665b65c6e40edcbf15778b1096f5aba615302/clinvar.vcf.gz` | 191912185 | f56bc2236287e25e472fda9bda9d7551 | bd3cdbc07bf26aa5d136219e2db665b65c6e40edcbf15778b1096f5aba615302 | `/var/data/eamos/bio_assets/clinvar/clinvar.vcf.gz` | `CLINVAR_RUNTIME_VCF_PATH` |
| clinvar_tabix_index | `ncbi_clinvar_vcf/clinvar_grch38_vcf_tbi/sha256-8163ba8700e54c674784ab61fbd0816030d69778675c16f9e1a80694a85b13b7/clinvar.vcf.gz.tbi` | 609481 | 974654a1d7e19a2d3ae216560c0926e7 | 8163ba8700e54c674784ab61fbd0816030d69778675c16f9e1a80694a85b13b7 | `/var/data/eamos/bio_assets/clinvar/clinvar.vcf.gz.tbi` | `CLINVAR_RUNTIME_INDEX_PATH` |
| repeatmasker_compact_interval_index | **no Storage object yet** (see ask D); rebuilt locally | 701514606 | — | 6d7cd79c0f657dfb0549e71f64435ea35887a7dd797c52cfb655298690c32f98 | `/var/data/eamos/bio_assets/repeatmasker/repeatmasker.interval-index.jsonl` | `REPEATMASKER_RUNTIME_INDEX_PATH` |
| phylop_bigwig | `ucsc_phylop100way_hg38/ucsc_hg38_phylop100way_bw/sha256-445fa3473c94fc209a6854692143371a57c05a387241e3de55933032ac024973/hg38.phyloP100way.bw` | 9870053206 | 43858006bdf98145b6fd239490bd0478 | 445fa3473c94fc209a6854692143371a57c05a387241e3de55933032ac024973 | `/var/data/eamos/bio_assets/phylop/hg38.phyloP100way.bw` | `PHYLOP_RUNTIME_BIGWIG_PATH` |
| dbsnp_bgzip_vcf | `ncbi_dbsnp_gcf_000001405_40/dbsnp_grch38_vcf_gz/sha256-43bb897b69177555a8e9edeb7d8c8ea3e581dddaefadfafe29f36bed0d870574/GCF_000001405.40.gz` | 29552227779 | 6a6f313e92a39c337571174dad12cfe1 | 43bb897b69177555a8e9edeb7d8c8ea3e581dddaefadfafe29f36bed0d870574 | `/var/data/eamos/bio_assets/dbsnp/GCF_000001405.40.gz` | `DBSNP_RUNTIME_VCF_PATH` |
| dbsnp_tabix_index | `ncbi_dbsnp_gcf_000001405_40/dbsnp_grch38_vcf_tbi/sha256-d6c38c0b715e5fe16c715f2aaed04b3964ed7f38f00c5921e10afd3649b2b104/GCF_000001405.40.gz.tbi` | 3140346 | ba10bcbae4f0ad9b01244efdd564d6e2 | d6c38c0b715e5fe16c715f2aaed04b3964ed7f38f00c5921e10afd3649b2b104 | `/var/data/eamos/bio_assets/dbsnp/GCF_000001405.40.gz.tbi` | `DBSNP_RUNTIME_INDEX_PATH` |

Total new bytes ≈ 40.8 GB → disk lands ≈ 47 GB / 59 GB after seeding.

## The build asks (Codex)

A. **Declare runtime paths as code.** Put the 8 env vars above into a checked-in
   render blueprint (`render.yaml`) or make `Settings` RENDER-aware so it
   defaults to `/var/data/eamos/bio_assets/...` on the platform. Removes the
   silent-drift failure mode (#1).

B. **`eamos_materialize_all --manifest <pinned>` orchestrator.** One idempotent
   command: skip any role whose disk file already matches size+checksum; seed
   the rest; reconcile the Supabase `source_asset_materializations` row
   (download_pending→ready) after disk verification; emit one sanitized report.
   Prefer a **resumable** transport (add `SUPABASE_STORAGE_S3_*` to the SG env
   for s3_multipart, or make REST range-resumable) so a dropped 29 GB transfer
   resumes. This is also the **disaster-recovery** path: lose the disk → one
   command re-seeds everything.

C. **443-triggerable admin materialization path.** An authenticated, admin-only
   trigger (endpoint or release-phase command) that runs the orchestrator *in
   the web process* (env present, pooler + Storage reachable). Lets
   materialization — and M3's clinical import — run from anywhere over HTTPS with
   **no SSH and no hotspot**. Security: admin auth required, no secrets/paths in
   the response, idempotent, bounded.

D. **RepeatMasker derived-artifact lane.** Add an upload+register path for the
   compact interval index (extend `GENERATED_SOURCE_ARTIFACT_IDS` or
   `eamos_source_storage_upload`) so it lands in Storage like the others, OR
   formally bless the `--source-artifact` local-file seed as canonical. The
   rebuilt artifact is staged locally at
   `app/backend/.scratch/repeatmasker-compact-index/repeatmasker.interval-index.jsonl`
   — verified reproducible: 701,514,606 bytes, SHA256
   `6d7cd79c0f657dfb0549e71f64435ea35887a7dd797c52cfb655298690c32f98`,
   5,683,690 intervals, schema `eamos.repeatmasker.interval_index.v1`, built from
   the staged `rmsk.txt.gz` (SHA256 `db60e6aa…`). `.scratch` is ephemeral; treat
   the staged copy as transient.

E. **Hold the hard gates.** No `LOCAL_EVIDENCE_ENABLED` flip and no provider flip
   until every probe is `ready` (M9 stays last). Keep
   `LLM_PROVIDER=gateway` (current intended state) unchanged.

## Handoff protocol

1. Codex builds A–D (E is a standing gate).
2. When ready, Codex pings Steven; Steven relays to Claude.
3. Re-initiate the hotspot **only if** the 443-path (ask C) didn't land — if it
   did, materialization + M3 run over 443 with no hotspot.
4. Claude (or the 443-trigger) runs `eamos_materialize_all`, verifies each role
   `ready` in live provider-cache, confirms Supabase rows reconciled, leaves M9
   OFF.
5. Outstanding security item (separate from this build): the Supabase Storage S3
   secret was exposed in a tool transcript on 2026-06-20 and **must be rotated**;
   if ask B adds those creds to the SG env, set the rotated value.
