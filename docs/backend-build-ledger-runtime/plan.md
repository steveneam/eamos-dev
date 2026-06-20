# Backend Build Ledger Runtime Plan

1. Add the shared backend build ledger service.
   - Encode every build-ledger lane in one ordered contract.
   - Attach dynamic inspections for hg38, AlphaMissense, ESM1b, protein assets,
     local evidence gates, and source manifest readiness.
   - Keep serialization sanitized.

2. Wire all selected surfaces horizontally.
   - Add `build_ledger` to `/api/v1/health/provider-cache`.
   - Add `build_ledger` to `eamos_source_asset_preflight`.
   - Keep the existing narrower provider summaries in place for compatibility.

3. Enforce runtime asset policy.
   - Remove app-startup coordinate resolver downloads.
   - Fail closed if the legacy startup materialization flag is enabled.
   - Update deployment guidance to seed/materialize by explicit off-peak
     process only.

4. Harden the batch.
   - Add tests for required ledger rows and sanitization.
   - Add tests for preflight ledger output.
   - Add a startup policy test.

5. Compact coordinate index runtime pass.
   - Add the read-only compact index reader and fixture artifact.
   - Build runtime resolver instances from the compact index path with raw GFF
     paths disabled.
   - Wire lookup/search/report, Gene View, local evidence, and batch through
     the shared compact-index contract where those backend boundaries already
     exist.
   - Add explicit sanitized provider-cache and preflight readiness probes for
     the compact index.

6. Verify.
   - Run targeted backend pytest for health, preflight, runtime predictors,
     clinical source tables, literature, and startup policy.
   - Run lint/format checks where available.
   - Run `git diff --check`.

7. Continue materialization from the current execution checklist.
   - Use `docs/backend-build-ledger-runtime/materialization-plan.md` for the
     compact coordinate index and local-adapter runtime sequence.
   - Keep that checklist aligned with live SG health and Supabase inventory
     before provider flips.

## Agile Materialization Backlog

Use this section as the session-to-session pointer for remaining build-ledger
materialization work. Before starting any item, re-run the read-only baseline
checks because live SG, Supabase metadata, and local staging can move
independently:

```powershell
cd app/backend
python -m app.cli.eamos_source_asset_preflight --compact
python -m app.cli.eamos_clingen_local_preflight --compact
```

Also compare live SG provider-cache before any runtime decision. Do not flip
providers, env vars, or startup materialization from this backlog unless the
task explicitly reaches that acceptance gate.

### M0 - Ledger Baseline

Goal: capture the true current state from local preflight and live SG
provider-cache.

Acceptance criteria:

- Current ledger rows are grouped as ready, available, source-ready, disabled,
  missing, or gated.
- Local-ready versus live-ready differences are called out explicitly.
- No Storage, Supabase, Render, or env mutation is performed.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_source_asset_preflight --compact
```

Out of scope: downloads, uploads, Render disk writes, provider flips.

2026-06-19 checkpoint:

- Local preflight grouped `ready`: `clingen_local_adapter`, `hg38_2bit`.
  Local `source_ready_for_materialization`: `clinvar_local_adapter`,
  `dbsnp_local_adapter`, `phylop_conservation_reader`,
  `repeatmasker_local_adapter`. Local `disabled`: `local_evidence_orchestrator`.
  Local missing/gated rows include `coordinate_compact_index=missing`,
  `alphamissense=missing_source_file`, `esm1b=missing_source_file`,
  `ci_spliceai=score_cache_missing`, `capice=model_artifact_missing`,
  `literature_rag_embeddings=rag_disabled`, and
  `literature_engine=local_adapter_disabled`.
- Live SG differs from local for five rows: `coordinate_compact_index=ready`,
  `gene_view=ready`, `protein_pfam=available`, and `alphamissense=ready` on
  live; `clingen_local_adapter=local_adapter_disabled` on live while local is
  ready.
- Live SG `source_assets.clingen_local` remains `db_missing` with zero
  eRepo/CSpec counts. No Storage, Supabase metadata, Render, or env mutation
  was performed during the baseline.

### M1 - ClinGen/CSpec Generated SQLite Sync

Goal: move the already-built ClinGen eRepo/CSpec local SQLite artifact through
the generated-artifact lane, or prove that live SG already points at the same
ready artifact.

Context: local `eamos_clingen_local_preflight --compact` reports a ready
ClinGen eRepo/CSpec full snapshot (`eamos.clingen_local.v1`) with eRepo
classification rows and CSpec entities. This is distinct from the smaller
ClinGen gene-validity table import.

Relevant references:

- `docs/clingen-local-materialization/plan.md`
- `app/backend/app/services/clingen_local.py`
- `app/backend/app/services/generated_source_artifacts.py`
- `app/backend/app/cli/eamos_generated_artifact_upload.py`
- `app/backend/app/cli/eamos_generated_artifact_sync.py`

Acceptance criteria:

- The `clingen_local` generated artifact has a private Storage identity and
  checksum manifest, or live SG provider-cache proves the same runtime artifact
  is already ready.
- Runtime/preflight output remains sanitized: no local paths, object URIs,
  raw rows, or secrets.
- `build_ledger.items.clingen_local_adapter.status` is `ready` on the target
  runtime before relying on local-first ClinGen behavior.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_clingen_local_preflight --compact --require-ready
python -m app.cli.eamos_generated_artifact_upload --artifact clingen_local --compact
```

Out of scope: PubMed local, literature RAG, CSpec UI rendering.

2026-06-19 checkpoint:

- Local ClinGen preflight is ready for schema `eamos.clingen_local.v1`,
  source version `ClinGen eRepo/CSpec full snapshot 2026-06-11`, with 12,675
  eRepo classification rows, 77,799 CSpec entities, 25,762 CSpec links, and a
  verified checksum.
- The generated artifact upload plan is upload-eligible for private bucket
  `eamos-source-assets`: object
  `generated/eamos_clingen_local/clingen_local_sqlite/sha256-4b4a93b86116425f9949ea168df506b3ca17808d26db4e336ad833d1f73ada3d/clingen-local.sqlite`,
  size `463036416`, MD5 `7d6525308af1fbd64734491477adee06`, SHA256
  `4b4a93b86116425f9949ea168df506b3ca17808d26db4e336ad833d1f73ada3d`.
- Read-only S3 `head_object` proved both the artifact and manifest sidecar
  already exist in private Storage at that identity. No re-upload was needed.
- `eamos_generated_artifact_sync` now supports explicit
  `--download-mode s3_multipart`; a temp-destination sync from the private
  object downloaded, size/MD5/SHA256 verified, schema-validated, wrote the
  manifest sidecar, and emitted sanitized output. Live SG still needs an
  explicit runtime sync on the service disk before relying on local-first
  ClinGen behavior.

2026-06-20 update:

- The current local ClinGen artifact supersedes the 2026-06-11 private object:
  schema `eamos.clingen_local.v1`, source version
  `ClinGen eRepo/CSpec full snapshot 2026-06-19`, 12,690 eRepo rows, 77,801
  CSpec entities, and 25,772 CSpec links.
- Canonical M1 identity is now private Storage object
  `generated/eamos_clingen_local/clingen_local_sqlite/sha256-50e12d4c0caaefceeece8f1e04de654158c5197a03fb6def991728591028dd9b/clingen-local.sqlite`,
  size `527925248`, MD5 `60997c2c9a6837bd8614f489e79021fb`, SHA256
  `50e12d4c0caaefceeece8f1e04de654158c5197a03fb6def991728591028dd9b`.
  Codex uploaded the artifact and manifest to private Storage by S3 multipart;
  no Render seed, Supabase metadata write, provider flip, or env change was
  performed.
- Render Shell sync command, after confirming SG has the required private S3
  credentials:

```bash
python -m app.cli.eamos_generated_artifact_sync \
  --artifact clingen_local \
  --source-object-uri supabase://eamos-source-assets/generated/eamos_clingen_local/clingen_local_sqlite/sha256-50e12d4c0caaefceeece8f1e04de654158c5197a03fb6def991728591028dd9b/clingen-local.sqlite \
  --destination /var/data/eamos/bio_assets/clingen/clingen-local.sqlite \
  --manifest-destination /var/data/eamos/bio_assets/clingen/clingen-local.manifest.json \
  --download-mode s3_multipart \
  --expected-size-bytes 527925248 \
  --expected-md5 60997c2c9a6837bd8614f489e79021fb \
  --expected-sha256 50e12d4c0caaefceeece8f1e04de654158c5197a03fb6def991728591028dd9b \
  --require-ready \
  --compact
```

  If SG already has an older ClinGen runtime file and the command reports an
  existing-artifact mismatch, rerun the same command with `--force` after
  confirming the 2026-06-19 identity is still the intended target.

### M2 - Existing-Object Metadata Reconciliation

Goal: reconcile durable metadata for private Storage objects that already
exist, starting with dbSNP and phyloP.

Context: prior inventory found dbSNP and phyloP objects in private Storage, but
ledger rows still report `source_ready_for_materialization` because metadata
and runtime materialization rows are incomplete.

Acceptance criteria:

- `source_asset_objects` records exist for dbSNP and phyloP with role, size,
  checksum, license/provenance, and non-public access policy.
- Preflight no longer reports these sources as metadata-unknown.
- No Render disk seeding or local-evidence enablement happens in this task.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_source_asset_preflight --compact
```

Out of scope: ClinVar/RepeatMasker upload, runtime file placement.

2026-06-19 checkpoint:

- Added the committed `eamos_source_import --existing-object-set dbsnp_phylop`
  planning/apply path plus read-only Supabase S3 `head_object` verification for
  existing private Storage objects and manifest sidecars.
- S3 head verification passed for the dbSNP bgzip VCF, dbSNP tabix index,
  dbSNP upstream checksum, phyloP bigWig, and phyloP upstream checksum. The
  importer marks the metadata plan `verified` only after this proof.
- Supabase `eamos_private.source_asset_objects` now has five dbSNP/phyloP rows
  with `upload_status=verified`, `approval_status=approved`, private access
  flags false, role, size, SHA256, license/provenance metadata, and no frontend
  direct access.
- Supabase `eamos_private.source_asset_materializations` now has five matching
  SG rows for `sg-render` / `render_backend`; every row remains
  `materialization_status=not_materialized`, `verified_at=null`, and
  `fail_closed_reason=render_disk_seed_not_performed`.
- Local CLI apply remains gated by the app's configured materialization-store
  DB URL. In this session the committed importer generated and verified the
  registration payload, and the available Supabase connector path applied and
  read back the same rows. No Render disk seed, env/provider flip, local
  evidence enablement, PubMed/RAG work, or ESM1b work occurred.

### M3 - Small Clinical Table Imports

Goal: import release-pinned MONDO, HPO, ClinGen gene-validity, and GenCC tables
into private Supabase/Postgres.

Context: this is the `clinical_source_tables` ledger row, not the ClinGen
eRepo/CSpec SQLite artifact from M1.

Acceptance criteria:

- Fixture-scale clinical table data is replaced or augmented by release-pinned
  imports.
- Source versions and import timestamps are recorded.
- Existing public report/lookup contracts remain unchanged.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_clinical_source_tables.py tests/test_health_api.py -q
python -m app.cli.eamos_source_asset_preflight --compact
```

Out of scope: local-evidence gate, PubMed/RAG.

2026-06-19 checkpoint:

- Added a code-backed release-file import mode to `eamos_source_import`:
  `--clinical-release-files` reads the staged release-scale MONDO, HPO,
  ClinGen gene-validity, and GenCC files under `app/backend/data/source_assets`
  by default. The existing dev fixture import remains the default for tests and
  small local smoke runs.
- The release-file planner records explicit source-version overrides,
  SHA256-backed `local_source_versions`, release-file asset roles, row counts,
  and guardrails. It does not download, upload, seed Render, flip providers, or
  enable local evidence.
- Real staged-file planning passed with row counts:
  `clinical_mondo_diseases=31886`, `clinical_hpo_terms=19944`,
  `clinical_hpo_disease_phenotypes=281996`,
  `clinical_hpo_gene_phenotypes=329339`,
  `clinical_clingen_gene_validity=3596`, and
  `clinical_gencc_assertions=29845`.
- Live Supabase `eamos_private` currently remains fixture-scale by readback:
  MONDO 2, HPO terms 3, HPO disease phenotypes 2, HPO gene phenotypes 3,
  ClinGen validity 2, GenCC assertions 2. The private Postgres DB URL gate was
  added locally after this checkpoint, but the committed importer apply path
  timed out before writing rows because this workstation cannot open TCP
  connections to the Supabase pooler host (`aws-1-ap-southeast-2.pooler.supabase.com`)
  on port 5432. Connector SQL remains limited to readback/verification and is
  not the right path for streaming roughly 666k clinical rows.
- 2026-06-19 follow-up: the apply path now performs a fast sanitized TCP
  preflight before parsing/applying release files. On this workstation it fails
  in seconds with `supabase_import_database_unreachable` and host/port/timeout
  only; no secrets, release rows, writes, connector bulk SQL, or provider flips
  are involved.

### M4 - Local Evidence Runtime Probes

Goal: ensure dbSNP, ClinVar, RepeatMasker, and phyloP production runtime paths
are configurable and visible through sanitized health/preflight probes.

Acceptance criteria:

- Settings exist for each production runtime path/index path.
- Provider-cache or source preflight reports file readiness without leaking
  paths, object URIs, checksums that should stay private, or secrets.
- Tests prove fixture defaults are not mistaken for production configuration.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_source_asset_preflight_cli.py tests/test_health_api.py -q
```

Out of scope: Render seeding and `LOCAL_EVIDENCE_ENABLED=true`.

2026-06-19 checkpoint:

- Added production runtime path settings for dbSNP VCF/index, ClinVar
  VCF/index, RepeatMasker compact interval index, and phyloP bigWig.
- Added a sanitized `local_evidence_runtime_assets` probe to source-asset
  preflight and `/api/v1/health/provider-cache`. The probe reports ready/missing
  roles and byte sizes only; it emits no local paths, object URIs, secrets, raw
  rows, or private checksums, and it does not instantiate pysam/pyBigWig readers.
- Build-ledger rows for dbSNP, ClinVar, RepeatMasker, and phyloP stay
  `source_ready_for_materialization` with `seed_verified_render_disk_cache`
  blockers until configured production runtime files are present, then promote
  to `ready`.
- Focused tests cover missing-runtime and ready-runtime paths without leaking
  configured temp paths. No Render seed, local-evidence enablement, downloads,
  uploads, PubMed/RAG, ESM1b, or provider/env flips were performed.

### M5 - phyloP Runtime Seed

Goal: place the verified phyloP bigWig on the SG Render service disk.

Acceptance criteria:

- File is copied/downloaded through a temp path, size/checksum verified, and
  atomically renamed into the configured runtime path.
- Provider-cache reports phyloP ready for lookup/report use.
- No startup download path is introduced.

Verify: live SG provider-cache plus a targeted lookup/report conservation smoke.

Out of scope: local-evidence gate flip.

2026-06-19 code gate:

- Added `eamos_local_evidence_runtime_seed`, an explicit one-role-at-a-time
  runtime seed CLI for dbSNP, ClinVar, RepeatMasker, and phyloP roles.
- The M5 phyloP path is now covered for local operator files, Supabase private
  Storage REST downloads, and Supabase S3-compatible downloads. The S3 mode is
  the expected transport for the large production BigWig.
- The CLI verifies size plus MD5 and/or SHA256 before atomic rename, emits no
  local paths, object URIs, secrets, private checksums, or signed URLs, and does
  not mutate Supabase metadata, Render env/deploy state, providers, or
  `LOCAL_EVIDENCE_ENABLED`.
- Live SG is not seeded yet. The runtime command must be run from the approved
  Render Shell/operator context with the private source object URI and expected
  identity:

```powershell
python -m app.cli.eamos_local_evidence_runtime_seed `
  --role phylop_bigwig `
  --source-object-uri supabase://eamos-source-assets/ucsc_phylop100way_hg38/ucsc_hg38_phylop100way_bw/sha256-445fa3473c94fc209a6854692143371a57c05a387241e3de55933032ac024973/hg38.phyloP100way.bw `
  --destination /var/data/eamos/bio_assets/phylop/hg38.phyloP100way.bw `
  --download-mode s3_multipart `
  --expected-size-bytes 9870053206 `
  --expected-md5 43858006bdf98145b6fd239490bd0478 `
  --expected-sha256 445fa3473c94fc209a6854692143371a57c05a387241e3de55933032ac024973 `
  --require-ready `
  --compact
```

### M6 - ClinVar Runtime Seed

Goal: locate or upload ClinVar GRCh38 VCF plus `.tbi`, register metadata, and
seed the indexed runtime files.

Acceptance criteria:

- ClinVar local adapter reports ready from production runtime files.
- ACMG/local evidence paths can read ClinVar without live bulk downloads.
- Health/preflight output remains sanitized.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_clinvar_vcv.py tests/test_health_api.py -q
```

2026-06-20 update:

- Staged ClinVar GRCh38 files were uploaded to private `eamos-source-assets`
  by S3 multipart and verified by S3 head-object checks for each object plus
  manifest. Supabase metadata registration is complete for three
  `ncbi_clinvar_vcf` objects: `clinvar_bgzip_vcf`, `clinvar_tabix_index`, and
  `upstream_checksum`. The VCF and tabix rows are `verified`/`approved` and
  still fail closed as SG `not_materialized` with
  `render_disk_seed_not_performed`; the checksum row is registered as
  non-materializing metadata.
- The committed importer now supports the exact metadata plan/apply path:

```bash
python -m app.cli.eamos_source_import \
  --skip-clinical-fixtures \
  --storage-pilot none \
  --existing-object-set clinvar_vcf \
  --verify-storage-heads \
  --compact
```

- Upload command already run successfully:

```bash
python -m app.cli.eamos_source_storage_upload \
  --source ncbi_clinvar_vcf \
  --upload \
  --upload-mode s3_multipart \
  --compact
```

- Next gated step: seed both runtime roles from Render Shell:

```bash
python -m app.cli.eamos_local_evidence_runtime_seed \
  --role clinvar_bgzip_vcf \
  --source-object-uri supabase://eamos-source-assets/ncbi_clinvar_vcf/clinvar_grch38_vcf_gz/sha256-bd3cdbc07bf26aa5d136219e2db665b65c6e40edcbf15778b1096f5aba615302/clinvar.vcf.gz \
  --destination /var/data/eamos/bio_assets/clinvar/clinvar.vcf.gz \
  --download-mode s3_multipart \
  --expected-size-bytes 191912185 \
  --expected-md5 f56bc2236287e25e472fda9bda9d7551 \
  --expected-sha256 bd3cdbc07bf26aa5d136219e2db665b65c6e40edcbf15778b1096f5aba615302 \
  --require-ready \
  --compact

python -m app.cli.eamos_local_evidence_runtime_seed \
  --role clinvar_tabix_index \
  --source-object-uri supabase://eamos-source-assets/ncbi_clinvar_vcf/clinvar_grch38_vcf_tbi/sha256-8163ba8700e54c674784ab61fbd0816030d69778675c16f9e1a80694a85b13b7/clinvar.vcf.gz.tbi \
  --destination /var/data/eamos/bio_assets/clinvar/clinvar.vcf.gz.tbi \
  --download-mode s3_multipart \
  --expected-size-bytes 609481 \
  --expected-md5 974654a1d7e19a2d3ae216560c0926e7 \
  --expected-sha256 8163ba8700e54c674784ab61fbd0816030d69778675c16f9e1a80694a85b13b7 \
  --require-ready \
  --compact
```

### M7 - RepeatMasker Runtime Index

Goal: materialize the official RepeatMasker source into the compact runtime
interval index expected by the local adapter.

Acceptance criteria:

- Runtime uses the compact interval index, not raw source scans.
- RepeatMasker provider/preflight status is ready.
- Query tests cover bounded interval lookup.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_repeatmasker_local_adapter.py tests/test_indexed_source_readers.py tests/test_source_asset_preflight_cli.py -q
```

2026-06-19 code gate:

- Added the `eamos_repeatmasker_compact_index_build` build-time CLI and service
  helper for deriving a compact JSONL interval index from an approved UCSC
  `rmsk.txt` / `rmsk.txt.gz` source.
- `RepeatMaskerIndexedTable` now round-trips the compact
  `eamos.repeatmasker.interval_index.v1` JSONL schema and keeps bounded
  bisect-backed interval queries.
- `RepeatMaskerLocalStore` can load the compact interval index explicitly
  instead of reparsing raw UCSC source rows at runtime. Fixture defaults remain
  unchanged.
- The builder is build-time/operator-only: no download, Storage upload, Render
  seed, provider flip, `LOCAL_EVIDENCE_ENABLED` flip, startup materialization,
  PubMed/RAG, or ESM1b work occurred.
- Live SG is not seeded with the RepeatMasker compact index yet.

2026-06-19 production-build checkpoint:

- Built the production compact interval index locally from the approved staged
  UCSC source
  `app/backend/data/source_assets/repeatmasker_rmsk_bb/rmsk.txt.gz`.
- Source identity: size `155633856`, MD5
  `b2e108b535550ba9e3cf83c77417380f`, SHA256
  `db60e6aa7ac175f8f5465cd01b48b550e67e1fb0fd828608d8343481867bb276`.
- Derived compact artifact:
  `.scratch/repeatmasker-compact-index/repeatmasker.interval-index.jsonl`;
  schema `eamos.repeatmasker.interval_index.v1`; interval count `5683690`;
  size `701514606`; SHA256
  `6d7cd79c0f657dfb0549e71f64435ea35887a7dd797c52cfb655298690c32f98`.
- Local sanitized preflight with `REPEATMASKER_RUNTIME_INDEX_PATH` pointed at
  that artifact reports `repeatmasker_local_adapter.status=ready`,
  `fixture_default_used=false`, `source_runtime_scan_allowed=false`, and no path
  or secret emission.
- Focused verification passed:
  `python -m pytest tests\test_repeatmasker_local_adapter.py tests\test_indexed_source_readers.py tests\test_source_asset_preflight_cli.py -q`
  and
  `python -m pytest tests\test_health_api.py::test_provider_cache_health_reports_local_evidence_runtime_assets_without_paths -q`.
- No Storage upload, Supabase metadata write, Render seed, provider flip,
  `LOCAL_EVIDENCE_ENABLED` flip, startup materialization, PubMed/RAG, or ESM1b
  work occurred. Live SG remains unseeded until explicit upload/register/seed
  gates.

2026-06-20 update:

- The official staged `rmsk.txt.gz` source was uploaded to private
  `eamos-source-assets` by S3 multipart and verified by S3 head-object checks
  for the object plus manifest. Supabase metadata registration is complete for
  `repeatmasker_rmsk_bb` / `repeatmasker_source_table` with
  `upload_status=verified`, `approval_status=approved`,
  `materialization_required=false`, and SG `fail_closed_reason` set to
  `runtime_uses_derived_compact_index_not_source_table`.
- The committed importer now supports the exact metadata plan/apply path:

```bash
python -m app.cli.eamos_source_import \
  --skip-clinical-fixtures \
  --storage-pilot none \
  --existing-object-set repeatmasker_source \
  --verify-storage-heads \
  --compact
```

- Upload command already run successfully:

```bash
python -m app.cli.eamos_source_storage_upload \
  --source repeatmasker_rmsk_bb \
  --upload \
  --upload-mode s3_multipart \
  --compact
```

- Source object identity from the plan:
  `repeatmasker_rmsk_bb/ucsc_hg38_rmsk_txt_gz/sha256-db60e6aa7ac175f8f5465cd01b48b550e67e1fb0fd828608d8343481867bb276/rmsk.txt.gz`,
  size `155633856`, MD5 `b2e108b535550ba9e3cf83c77417380f`, SHA256
  `db60e6aa7ac175f8f5465cd01b48b550e67e1fb0fd828608d8343481867bb276`.
- The runtime seed target is still the derived compact interval index, not the
  source table. The compact artifact identity is size `701514606`, SHA256
  `6d7cd79c0f657dfb0549e71f64435ea35887a7dd797c52cfb655298690c32f98`.
  Upload/register of that derived compact artifact is still gated before a
  Storage-backed Render seed. If the compact artifact is placed on the SG
  instance by an approved operator channel instead, the seed command shape is:

```bash
python -m app.cli.eamos_local_evidence_runtime_seed \
  --role repeatmasker_compact_interval_index \
  --source-artifact /tmp/repeatmasker.interval-index.jsonl \
  --destination /var/data/eamos/bio_assets/repeatmasker/repeatmasker.interval-index.jsonl \
  --expected-size-bytes 701514606 \
  --expected-sha256 6d7cd79c0f657dfb0549e71f64435ea35887a7dd797c52cfb655298690c32f98 \
  --require-ready \
  --compact
```

### M8 - dbSNP Runtime Seed

Goal: seed the dbSNP bgzip VCF plus `.tbi` from private Storage onto SG Render
disk.

Context: this is operationally larger than phyloP/ClinVar/RepeatMasker because
the object set is about 29.6 GB.

Acceptance criteria:

- dbSNP local adapter reports ready from production runtime files.
- Allele identity lookup works from local indexed files.
- Runtime memory remains bounded during probe/query.

2026-06-20 prep:

- Approved private Storage object identities are registered in
  `source_asset_objects`; SG materialization rows remain
  `not_materialized` with `render_disk_seed_not_performed`.
- Render Shell seed commands:

```bash
python -m app.cli.eamos_local_evidence_runtime_seed \
  --role dbsnp_bgzip_vcf \
  --source-object-uri supabase://eamos-source-assets/ncbi_dbsnp_gcf_000001405_40/dbsnp_grch38_vcf_gz/sha256-43bb897b69177555a8e9edeb7d8c8ea3e581dddaefadfafe29f36bed0d870574/GCF_000001405.40.gz \
  --destination /var/data/eamos/bio_assets/dbsnp/GCF_000001405.40.gz \
  --download-mode s3_multipart \
  --expected-size-bytes 29552227779 \
  --expected-md5 6a6f313e92a39c337571174dad12cfe1 \
  --expected-sha256 43bb897b69177555a8e9edeb7d8c8ea3e581dddaefadfafe29f36bed0d870574 \
  --require-ready \
  --compact

python -m app.cli.eamos_local_evidence_runtime_seed \
  --role dbsnp_tabix_index \
  --source-object-uri supabase://eamos-source-assets/ncbi_dbsnp_gcf_000001405_40/dbsnp_grch38_vcf_tbi/sha256-d6c38c0b715e5fe16c715f2aaed04b3964ed7f38f00c5921e10afd3649b2b104/GCF_000001405.40.gz.tbi \
  --destination /var/data/eamos/bio_assets/dbsnp/GCF_000001405.40.gz.tbi \
  --download-mode s3_multipart \
  --expected-size-bytes 3140346 \
  --expected-md5 ba10bcbae4f0ad9b01244efdd564d6e2 \
  --expected-sha256 d6c38c0b715e5fe16c715f2aaed04b3964ed7f38f00c5921e10afd3649b2b104 \
  --require-ready \
  --compact
```

Verify: provider-cache plus targeted dbSNP/local-evidence tests.

### M9 - Local Evidence Gate

Goal: enable local evidence only after hg38, compact index, dbSNP, ClinVar,
RepeatMasker, and phyloP are production-path verified.

Acceptance criteria:

- `LOCAL_EVIDENCE_ENABLED=true` is paired with narrow
  `LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW`, initially `lookup,gene_viewer`.
- `LOCAL_EVIDENCE_REQUIRE_REAL_APIS=true` remains set.
- Lookup and Gene View smokes prove local evidence is active without broad
  fallback regressions.

Out of scope: search/workbench expansion until separate contract tests cover
those surfaces.

### M10 - MaveDB CC0 Import

Goal: materialize CC0 functional evidence after public-field review.

Acceptance criteria:

- MaveDB evidence is available to lookup/report surfaces.
- Public serialization policy is reviewed and enforced.
- No private/raw fields leak into public report payloads.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_mavedb_local.py tests/test_functional_evidence.py -q
```

2026-06-19 code gate:

- Added `eamos_mavedb_local_materialize`, an offline JSONL-to-SQLite
  materializer for CC0 MaveDB functional-score rows. It filters out non-CC0
  rows and score-missing rows, writes a sanitized manifest, computes a logical
  SHA256 over public runtime tables, and performs no network, Supabase, Render,
  provider/env, or startup-download action.
- Added local MaveDB runtime settings and sanitized provider-cache, source
  preflight, and build-ledger readiness. Missing assets report
  `cc0_import_not_materialized`; ready assets set `public_serialization_allowed`
  only after checksum/schema inspection.
- `FunctionalEvidenceExtractor` can read the local CC0 store when explicitly
  enabled and exposes MaveDB hits as uncurated functional studies with public
  score/accession fields. It does not assert PS3/BS3 or change ACMG verdict
  semantics.
- The report page now uses the existing MaveDB functional-evidence block for
  live local MaveDB hits and keeps the mock MAVE/OddsPath block only as the
  no-data fallback. The live branch is labeled uncurated.
- Focused backend, contract, health, preflight, variant-cache, and web
  TypeScript/ESLint checks passed locally. No M7 live upload/register/seed,
  M8 dbSNP seed, M9 local-evidence gate flip, PubMed/RAG, ESM1b, Storage,
  Supabase write, Render seed, or provider/env flip occurred.

### M11 - ESM1b MIT-Regenerated Scores

Goal: materialize the MIT-regenerated ESM1b hg38 bgzip/tabix artifact.

Blocker: operator must provide
`C:\EamosDataStaging\esm1b\esm1b-mit-regenerated-scores.csv` with `seq_id`
values matching the staged MANE protein FASTA IDs.

2026-06-19 status: code support remains present, but the operator score CSV is
not available in this workspace. M11 stays blocked until that private file and
MANE/reference checksum metadata are supplied.

Acceptance criteria:

- Runtime artifact and `.tbi` are generated from MIT-regenerated scores, not
  the non-commercial Hugging Face precomputed zip.
- Manifest records source, checksums, MANE/reference provenance, and
  `launch_gate: null` only for the clean regenerated path.
- Provider-cache/build-ledger report ESM1b ready after explicit runtime sync.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_tier2_predictor_artifact_upload --artifact esm1b_hg38_scores --compact
python -m pytest tests/test_esm1b_assembly.py tests/test_predictor_runtime.py -q
```

### M12 - CI-SpliceAI Runtime Artifact Set

Goal: materialize the complete CI-SpliceAI model/reference/score-cache set.

Acceptance criteria:

- Model, reference bundle, score cache, and score-cache index are all present.
- Partial artifact-set uploads remain blocked.
- Launch-gate/provenance metadata is preserved for commercialization filtering.

2026-06-19 status: current code treats CI-SpliceAI as a complete artifact-set
lane and wires the runtime score cache into the report path. When a local
complete model/reference/score-cache set is staged with valid sidecar manifests,
`ComputationalAnnotationsTool` reads the coordinate-keyed score cache and emits
a real gene-agnostic `CI-SpliceAI` `ComputationalPredictorRow` into
`computational_deep_dive`. The row preserves launch/provenance metadata for
later commercial filtering; launch gates do not hide the backend/internal row.
No local complete artifact set is staged, so runtime availability still remains
gated on operator artifacts. Bare files with a tabix index no longer report
`ready`.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_tier2_predictor_artifact_upload --artifact ci_spliceai --compact
python -m pytest tests/test_predictor_runtime.py -q
```

### M13 - CAPICE Runtime Artifact Set

Goal: materialize the complete CAPICE model and SpliceAI-derived feature cache.

Acceptance criteria:

- Model, feature cache, and feature-cache index are all present.
- Partial artifact-set uploads remain blocked.
- CAPICE scorer is connected only once artifacts pass preflight.

2026-06-19 status: current code treats CAPICE as a complete artifact-set lane
and wires the runtime feature/score cache into the report path. When a local
complete model/feature-cache set is staged with valid sidecar manifests,
`ComputationalAnnotationsTool` reads the coordinate-keyed feature cache and
emits a real gene-agnostic `CAPICE` `ComputationalPredictorRow` into
`computational_deep_dive`. The row preserves launch/provenance metadata for
later commercial filtering; launch gates do not hide the backend/internal row.
No local complete artifact set is staged, so runtime availability still remains
gated on operator artifacts. Bare files with a tabix index no longer report
`ready`.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_tier2_predictor_artifact_upload --artifact capice --compact
python -m pytest tests/test_predictor_runtime.py -q
```

### M14 - PubMed Local And Literature RAG

Goal: materialize PubMed local first, then literature RAG embeddings.

Status: deferred until Steven explicitly approves corpus logistics, storage
scope, staging, and cost.

Acceptance criteria:

- PubMed local SQLite is materialized from approved source packages and passes
  preflight.
- Literature embeddings are built offline from license-permitted rows, uploaded
  to private Storage, synced to Render disk, and never built/downloaded at
  startup.
- Chat/report retrieval uses the materialized store only after preflight is
  ready.

Verify:

```powershell
cd app/backend
python -m app.cli.eamos_pubmed_local_preflight --compact --require-ready
python -m app.cli.eamos_literature_embed_preflight --compact --require-ready
python -m pytest tests/test_pubmed_local.py tests/test_literature_retrieval.py -q
```

Out of scope until approval: full PubMed/RAG corpus build, embeddings spend,
provider/env flips.
