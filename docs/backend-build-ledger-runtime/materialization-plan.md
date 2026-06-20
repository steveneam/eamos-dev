# Backend Build Ledger Materialization Plan

Status: Current execution plan
Owner: Codex/backend
Last verified: 2026-06-21 04:41 +1000

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

Live SG health was checked after the post-M3 lookup-stability deploy
`87af99b` on 2026-06-21:

| Ledger lane | Live status | Meaning |
| --- | --- | --- |
| `hg38_2bit` | `ready` | Render disk has the verified hg38.2bit runtime asset. |
| `protein_pfam` | `available` | Pfam/HMMER is materialized and enabled on SG. |
| `coordinate_compact_index` | `ready` | Compact artifact is registered in Supabase, materialized on SG Render disk, schema-validated, and visible in provider-cache. |
| `gene_view` | `ready` | Gene View blockers are cleared on live SG. |
| `dbsnp_local_adapter` | `ready` | Seeded runtime files are present on the SG service disk and provider-cache reports the role ready. |
| `phylop_conservation_reader` | `ready` | Seeded runtime bigWig is present on the SG service disk and provider-cache reports the role ready. |
| `clinvar_local_adapter` | `ready` | Seeded runtime VCF/index are present on the SG service disk. Full gene-wide distribution stays gated behind `LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW=lookup` until that request path is indexed/bounded. |
| `repeatmasker_local_adapter` | `ready` | Seeded compact interval index is present on the SG service disk and provider-cache reports the role ready. |
| `clingen_local_adapter` | `ready` | Generated ClinGen eRepo/CSpec SQLite is synced on SG. `CLINGEN_LOCAL_ENABLED` remains a separate gate and is still off in source-asset health. |
| `local_evidence_orchestrator` | `disabled` | Correct final gate state after M3: `LOCAL_EVIDENCE_ENABLED=false`; allowed flows were not flipped. |
| `clinical_source_tables` | `complete/live-run verified` | M3 release import completed against live Supabase and remains gate-off. The current build-ledger label may still read `import_ready` until that display label is reconciled. |

Supabase/runtime inventory checked on 2026-06-21:

| Area | Observed state | Required action |
| --- | --- | --- |
| `source_asset_objects` | Rows exist for hg38, Pfam, compact coordinate index, dbSNP, phyloP, ClinVar, RepeatMasker, and generated ClinGen artifacts. Seed assets are ready/private for the live runtime batch. | No repeat registration for M5-M8 seed assets unless a replacement source identity is approved. |
| `source_asset_materializations` | Live SG provider-cache reports `local_evidence_runtime_assets.ready_count=4` of `4` for dbSNP, phyloP, ClinVar, and RepeatMasker, plus ready hg38, compact index, Gene View, and ClinGen local runtime lanes. | Keep rows and runtime files gate-off until M9 is explicitly approved. Reconcile stale metadata labels separately if they still read `not_materialized`. |
| Storage/runtime seed assets | Compact coordinate index, dbSNP, phyloP, ClinVar, RepeatMasker compact index, hg38, and ClinGen generated SQLite have been seeded/synced for SG runtime use. | No startup materialization. Any refresh uses the explicit offline/private Storage/Render-disk seed path. |
| Clinical tables | M3 release import is complete and live-run verified with MONDO 31,886; HPO terms 19,944; HPO disease phenotypes 281,996; HPO gene phenotypes 329,339; ClinGen 3,596; GenCC 29,845. Total imported rows: 676,606. | Keep `ADMIN_MATERIALIZATION_ENABLED=false`; do not re-import unless Steven explicitly asks. `LOCAL_EVIDENCE_ENABLED` was not flipped. |

2026-06-21 post-import lookup checkpoint:

- Post-M3 RPE65 lookup instability was fixed in deploy `87af99b`.
- Live `/healthz` and `/api/v1/health/provider-cache` returned 200.
- Live `/api/v1/lookup/summary` for `RPE65:c.260A>G` returned 200 in about
  22.8 seconds with no Render restart.
- Sanitized live output scan passed: no local paths, object URIs, admin token,
  bearer token, database URL, service-role key, or secret-like values were
  emitted.
- Final gate state remains: `ADMIN_MATERIALIZATION_ENABLED=false`;
  `LOCAL_EVIDENCE_ENABLED=false`; `LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW` not
  flipped; `CLINGEN_LOCAL_ENABLED` not flipped.

## Hard Gates

- Keep `LLM_PROVIDER=mock` until the AI-gateway release gate is intentionally
  crossed.
- Keep `CRISPR_OFFTARGET_PROVIDER=auto`; the full-index CRISPR lane belongs to
  the separate Workbench/off-target runbook.
- Do not enable coordinate or protein startup materialization.
- Do not point runtime at raw GFF scans.
- Do not use Render one-off jobs to seed the service persistent disk; they do
  not write to the mounted web-service disk.
- Do not enable `LOCAL_EVIDENCE_ENABLED=true` without Steven's explicit M9
  approval. The production-path assets are ready, but the gate flip is a
  separate release action.
- Treat `CLINGEN_LOCAL_ENABLED=true` as a separate gate from M9 local evidence.
- Before enabling `lookup` local evidence, fix or keep excluded the current
  full-VCF ClinVar gene-distribution path; the post-M3 fix only prevents that
  expensive path while `LOCAL_EVIDENCE_ENABLED=false`.

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
- Superseding 2026-06-21 status: live SG now reports Gene View ready after the
  coordinated code deploys.

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
The reader validates gzip payloads by magic bytes as well as `.gz` suffix so
private-storage temp downloads schema-validate correctly. The old live
`550641d` workaround is superseded by the current deploys.

### 2. Metadata Reconciliation

Goal: make Supabase the durable source of truth before local adapter flips.

Steps:

1. **Done 2026-06-14 01:19 +1000:** reconciled the Pfam materialization row
   from `download_pending` to the live SG proof, preserving checksum, verified
   timestamp, persistent-disk path, and HMMER provider-cache readiness.
2. **Done 2026-06-19 02:02 +1000:** registered dbSNP Storage objects under
   `source_asset_objects`:
   - source id `ncbi_dbsnp_gcf_000001405_40`;
   - roles for bgzip VCF, tabix index, checksum/manifest objects;
   - approval and license status copied from the source rollout plan;
   - matching SG materialization rows were initially fail-closed as
     `not_materialized`; superseding 2026-06-21 live status reports dbSNP
     runtime ready on SG.
3. **Done 2026-06-19 02:02 +1000:** registered phyloP Storage objects under
   `source_asset_objects`:
   - source id `ucsc_phylop100way_hg38`;
   - roles for bigWig and checksum/manifest objects;
   - matching SG materialization rows were initially fail-closed as
     `not_materialized`; superseding 2026-06-21 live status reports phyloP
     runtime ready on SG.
4. **Done 2026-06-20 22:27 +1000:** uploaded and registered ClinVar GRCh38 VCF,
   `.tbi`, and upstream checksum objects as verified, approved, private
   metadata. Superseding 2026-06-21 live status reports ClinVar runtime ready
   on SG, with lookup distribution still gate-protected.
5. **Done 2026-06-20 22:27 +1000:** uploaded and registered the official
   RepeatMasker `rmsk.txt.gz` source as verified, approved, private,
   source-only metadata. Superseding 2026-06-21 live status reports the
   derived compact runtime interval index ready on SG.

Prefer committed metadata CLIs/importers over manual SQL. If SQL is used for a
one-time reconciliation, capture the exact query in a follow-up runbook.
M2 used the committed `eamos_source_import --existing-object-set dbsnp_phylop`
path for planning and S3 head verification; the local CLI database apply gate
remained unset, so the verified registration payload was applied through the
available Supabase connector and read back from `eamos_private`.

### 3. Runtime Path Wiring

Goal: make production local adapters configurable, not fixture-default.

The local adapters are fixture-first and accept constructor paths. Production
runtime settings and sanitized probes were added on 2026-06-19; the first live
seed batch is now present on SG as of 2026-06-21.
Before enabling local evidence, verify:

- dbSNP runtime path and index path settings exist and are pointed at the seeded
  bgzip VCF plus `.tbi`;
- ClinVar runtime path and index path settings exist and are pointed at the
  seeded bgzip VCF plus `.tbi`;
- RepeatMasker compact interval index path setting exists and points at the
  derived runtime index, not raw source scans;
- phyloP bigWig path setting exists and points at the seeded bigWig;
- `local_evidence_runtime_assets` in provider-cache/source preflight reports the
  expected roles as `ready`;
- health/preflight output remains sanitized: no local paths, object URIs,
  secrets, raw rows, or private checksums.

2026-06-21 checkpoint: M4 probe work is live and the M5-M8 seed batch is
present on SG. Provider-cache reports dbSNP, ClinVar, RepeatMasker, and phyloP
runtime roles as ready with sanitized status/size output only. No local paths,
object URIs, secrets, private checksums, or raw rows are emitted. The local
evidence orchestrator still reports disabled because `LOCAL_EVIDENCE_ENABLED`
remains false.

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

2026-06-19 M5 code gate: `eamos_local_evidence_runtime_seed` now provides the
committed runtime CLI for one local-evidence asset role at a time. It is
off-startup only, supports local operator files plus Supabase private Storage
REST/S3-compatible downloads, verifies expected size and MD5/SHA256 before
atomic rename, and emits only sanitized role/status/size output. It does not
mutate Supabase metadata, Render env/deploy state, provider settings, or
`LOCAL_EVIDENCE_ENABLED`.

The first live use was the phyloP BigWig seed from the SG service runtime:

```bash
python -m app.cli.eamos_local_evidence_runtime_seed \
  --role phylop_bigwig \
  --source-object-uri supabase://eamos-source-assets/ucsc_phylop100way_hg38/ucsc_hg38_phylop100way_bw/sha256-445fa3473c94fc209a6854692143371a57c05a387241e3de55933032ac024973/hg38.phyloP100way.bw \
  --destination /var/data/eamos/bio_assets/phylop/hg38.phyloP100way.bw \
  --download-mode s3_multipart \
  --expected-size-bytes 9870053206 \
  --expected-md5 43858006bdf98145b6fd239490bd0478 \
  --expected-sha256 445fa3473c94fc209a6854692143371a57c05a387241e3de55933032ac024973 \
  --require-ready \
  --compact
```

After the live seed, verify the SG provider-cache reports
`phylop_conservation_reader.status=ready`, then run a targeted lookup/report
conservation smoke. Do not flip the local-evidence gate during M5.

2026-06-21 checkpoint: the SG runtime seed batch is complete for the local
evidence asset roles. Live provider-cache reports
`source_assets.local_evidence_runtime_assets.ready_count=4` of `4`, and build
ledger rows for dbSNP, phyloP, ClinVar, and RepeatMasker are ready. This did
not flip `LOCAL_EVIDENCE_ENABLED`, `LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW`, or
`CLINGEN_LOCAL_ENABLED`.

2026-06-19 M7 code gate: RepeatMasker now has a build-time compact-index path
ready for the later runtime seed. `eamos_repeatmasker_compact_index_build`
converts an approved local `rmsk.txt` / `rmsk.txt.gz` source into
`eamos.repeatmasker.interval_index.v1` JSONL, and `RepeatMaskerLocalStore` can
load that compact index explicitly instead of reparsing raw UCSC rows at
runtime.

2026-06-19 production build: the approved staged UCSC source
`app/backend/data/source_assets/repeatmasker_rmsk_bb/rmsk.txt.gz` was converted
locally into `.scratch/repeatmasker-compact-index/repeatmasker.interval-index.jsonl`.
The source is size `155633856`, MD5 `b2e108b535550ba9e3cf83c77417380f`,
SHA256 `db60e6aa7ac175f8f5465cd01b48b550e67e1fb0fd828608d8343481867bb276`.
The derived compact artifact has schema `eamos.repeatmasker.interval_index.v1`,
`5683690` intervals, size `701514606`, and SHA256
`6d7cd79c0f657dfb0549e71f64435ea35887a7dd797c52cfb655298690c32f98`. Local
preflight with `REPEATMASKER_RUNTIME_INDEX_PATH` pointed at that artifact
reported the RepeatMasker runtime source ready without path or secret emission,
and focused RepeatMasker/source-preflight/health tests passed.

This did not upload Storage objects, mutate Supabase metadata, seed Render, flip
providers, enable local evidence, or add startup materialization. Superseding
2026-06-21 status: the derived RepeatMasker compact runtime artifact is now
present on the SG service disk and provider-cache reports the RepeatMasker
runtime role ready. Refreshes remain gated through the same explicit seed path.

Operator shape for a repeat build step:

```bash
python -m app.cli.eamos_repeatmasker_compact_index_build \
  --source-rmsk-path <approved-local-rmsk.txt.gz> \
  --output <staging>/repeatmasker.interval-index.jsonl \
  --require-ready \
  --compact
```

### 5. Local Evidence Gate

Goal: enable only the flows backed by verified production assets.

The full seed batch is present and the post-M3 lookup stability check is green,
so M9 can be proposed, but not flipped without Steven:

1. Set `LOCAL_EVIDENCE_ENABLED=true`.
2. Set `LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW=lookup,gene_viewer`.
3. Keep `LOCAL_EVIDENCE_REQUIRE_REAL_APIS=true`.
4. Keep `search` and `workbench` out.
5. Treat `CLINGEN_LOCAL_ENABLED=true` as a separate gate.
6. Before enabling `lookup`, handle the current ClinVar full-VCF distribution
   path so lookup does not parse the full seeded VCF on request. The deployed
   stabilization keeps that path disabled while local evidence is off; M9 must
   either make it indexed/gene-bounded or exclude it from the lookup gate.
7. Verify provider-cache and targeted lookup/Gene View behavior.
8. Expand to `search` and `workbench` only after contract tests cover those
   surfaces.

### 6. Tier 1 Generated SQLite Artifacts

Goal: move ClinGen local, PubMed local, and literature RAG embedding SQLite
artifacts through the same offline -> private Storage -> Render disk pattern
without startup downloads or provider flips.

The generated-asset lane is now code-backed:

```bash
python -m app.cli.eamos_generated_artifact_upload --compact
python -m app.cli.eamos_generated_artifact_upload --artifact pubmed_local --upload --upload-mode s3_multipart

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

python -m app.cli.eamos_generated_artifact_sync \
  --artifact pubmed_local \
  --source-object-uri supabase://eamos-source-assets/generated/eamos_pubmed_local/.../pubmed-local.sqlite \
  --force \
  --require-ready \
  --compact
```

Artifacts covered:

| Artifact id | Runtime path setting | Manifest setting | Source id |
| --- | --- | --- | --- |
| `clingen_local` | `CLINGEN_LOCAL_SQLITE_PATH` | `CLINGEN_LOCAL_MANIFEST_PATH` | `eamos_clingen_local` |
| `pubmed_local` | `PUBMED_LOCAL_SQLITE_PATH` | `PUBMED_LOCAL_MANIFEST_PATH` | `eamos_pubmed_local` |
| `literature_embeddings` | `RAG_SQLITE_PATH` | `RAG_MANIFEST_PATH` | `eamos_literature_embeddings` |

The upload CLI computes MD5/SHA256 and writes a private Storage identity
manifest for each generated SQLite artifact. The sync CLI downloads or copies
through a temp file, validates size/checksum and the artifact-specific SQLite
schema, writes the runtime manifest sidecar, and atomically replaces the runtime
file. It does not register `source_asset_objects`, mutate Render env, create
signed URLs, or set `LOCAL_EVIDENCE_ENABLED`.

2026-06-20 M1 note: Codex uploaded the current ClinGen generated SQLite object
and manifest to private Storage at the `sha256-50e12d4c...` identity above.
This supersedes the older `sha256-4b4a93b...` 2026-06-11 object for runtime
sync. No Render disk seed, Supabase metadata row, env change, provider flip, or
local-evidence gate flip was performed.

### 6.5. MaveDB CC0 Functional Scores

MaveDB now has a code-backed local materialization lane for public CC0
functional-score rows:

```bash
python -m app.cli.eamos_mavedb_local_materialize \
  --input-jsonl <approved-mavedb-export.jsonl> \
  --output data/bio_assets/mavedb/mavedb-local.sqlite \
  --manifest-path data/bio_assets/mavedb/mavedb-local.manifest.json \
  --source-version <reviewed-source-version> \
  --require-ready \
  --compact
```

The materializer filters to CC0 rows with a present score, writes a sanitized
manifest, and never downloads, uploads, seeds Render, writes Supabase metadata,
or flips providers. The lookup/report path treats MaveDB hits as uncurated
functional studies with public score/accession fields; it does not assert PS3 or
BS3 strength.

### 7. Tier 2 Predictor Artifact Sets

Goal: prepare ESM1b, CI-SpliceAI, and CAPICE runtime artifacts for the same
private Storage perimeter without pretending partial files are deployable.

The Tier 2 upload lane is code-backed and plan-only by default:

```bash
python -m app.cli.eamos_tier2_predictor_artifact_upload --compact
python -m app.cli.eamos_tier2_predictor_artifact_upload --artifact esm1b_hg38_scores --upload --upload-mode s3_multipart
```

Artifact sets covered:

| Artifact set | Required components | Runtime settings |
| --- | --- | --- |
| `esm1b_hg38_scores` | bgzip TSV plus `.tbi` | `ESM1B_HG38_RUNTIME_ASSET_PATH` |
| `ci_spliceai` | model, reference bundle, bgzip score cache plus `.tbi` | `CI_SPLICEAI_MODEL_PATH`, `CI_SPLICEAI_REFERENCE_PATH`, `CI_SPLICEAI_SCORE_CACHE_PATH` |
| `capice` | model, bgzip feature cache plus `.tbi` | `CAPICE_MODEL_PATH`, `CAPICE_FEATURE_CACHE_PATH` |

M12/M13 artifact-set design slice, 2026-06-19:

- CI-SpliceAI stays a self-hosted backend/admin lane: no hosted web-service
  dependency, no assumed genome-wide trusted precomputed score file, and no
  frontend direct artifact access.
- CAPICE stays launch-gated/display-safe until the SpliceAI-derived feature
  cache provenance is approved. The stock model path requires a model artifact,
  a bgzip feature cache, and the feature-cache tabix index as one complete set.
- Upload-planner manifests are private Storage identity manifests. Runtime
  readiness separately requires a local sidecar beside each runtime file:
  `<artifact path>.manifest.json`.
- Each local sidecar must match artifact/component/source/asset/role identity,
  match file byte size, carry MD5 or SHA256, preserve the expected launch gate,
  and assert the private runtime storage contract:
  `bucket_policy=private`, no frontend direct access, no signed URLs, no startup
  download, no request-time materialization, and `runtime_sync_required=true`.
- Provider-cache, source preflight, health, and build-ledger output may expose
  sanitized component readiness, manifest status, byte size, and launch gate,
  but must not emit local paths or unlock launch filtering.
- Runtime report wiring is local-file only. `ComputationalAnnotationsTool` reads
  CI-SpliceAI and CAPICE coordinate-keyed caches after the complete artifact-set
  gates pass, then emits real gene-agnostic `CI-SpliceAI` and `CAPICE`
  `ComputationalPredictorRow` values into `computational_deep_dive`.
- Commercial/launch gating remains metadata, not a backend/internal visibility
  filter: report rows, health, preflight, and build-ledger output keep the
  launch/provenance tags so public commercialization filtering can be decided
  later.

Current inventory, 2026-06-17: no approved local Tier 2 artifacts are present.
The default predictor root `app/backend/data/bio_assets/predictors/` is missing,
and the read-only upload plan reports `planned_count=0` with
`missing_local_file=9`.

ESM1b source gate checked 2026-06-17: the ntranoslab/esm-variants GitHub code is
MIT, but the Hugging Face Space that carries `ALL_hum_isoforms_ESM1b_LLR.zip`
declares `cc-by-nc-4.0` in its Space metadata and lists the zip as a 1.34 GB
file. Do not download or stage that precomputed score zip as a production
artifact unless Steven explicitly accepts an internal-only, non-commercial
source path. The commercial-safe path remains regeneration from the MIT model
with MANE/reference/source checksums recorded in the Eamos manifest.

Steven decision 2026-06-17: use the commercial-safe MIT regeneration path. The
runtime artifact launch gate is now manifest-driven:

- missing or legacy ESM1b artifacts report `esm1b_mit_regeneration_required`;
- manifests that identify the precomputed/non-commercial score zip stay gated;
- manifests written from MIT-regenerated scores carry `license_gate: null` and
  clear the ESM1b launch gate in provider-cache/build-ledger output.

After the operator-side MIT ESM1b scoring run produces a score CSV, run from
`app/backend` and materialize the Eamos runtime artifact without using the
Hugging Face score zip:

```bash
python -m app.cli.eamos_esm1b_regenerated_scores_materialize \
  --score-csv <staging>/esm1b-mit-regenerated-scores.csv \
  --codon-context-jsonl <staging>/esm1b-mane-codon-contexts.jsonl \
  --target-path data/bio_assets/predictors/esm1b/esm1b_hg38.tsv.gz \
  --mane-version <MANE release/version> \
  --grch38-reference-sha256 <hg38 reference SHA256> \
  --require-ready \
  --compact
```

Then rerun the read-only upload planner. The expected clean result is a complete
`esm1b_hg38_scores` plan with two components and `launch_gate: null`; Storage
upload, Supabase metadata registration, Render disk sync, and provider/env flips
remain separate approvals.

| Artifact set | Component | Expected default path | Current status |
| --- | --- | --- | --- |
| `esm1b_hg38_scores` | score cache | `app/backend/data/bio_assets/predictors/esm1b/esm1b_hg38.tsv.gz` | missing |
| `esm1b_hg38_scores` | score cache index | `app/backend/data/bio_assets/predictors/esm1b/esm1b_hg38.tsv.gz.tbi` | missing |
| `ci_spliceai` | model | `app/backend/data/bio_assets/predictors/ci_spliceai/ci_spliceai.keras` | missing |
| `ci_spliceai` | reference bundle | `app/backend/data/bio_assets/predictors/ci_spliceai/hg38_reference.json` | missing |
| `ci_spliceai` | score cache | `app/backend/data/bio_assets/predictors/ci_spliceai/ci_spliceai_hg38_scores.vcf.gz` | missing |
| `ci_spliceai` | score cache index | `app/backend/data/bio_assets/predictors/ci_spliceai/ci_spliceai_hg38_scores.vcf.gz.tbi` | missing |
| `capice` | model | `app/backend/data/bio_assets/predictors/capice/capice_model.json` | missing |
| `capice` | feature cache | `app/backend/data/bio_assets/predictors/capice/capice_hg38_features.tsv.gz` | missing |
| `capice` | feature cache index | `app/backend/data/bio_assets/predictors/capice/capice_hg38_features.tsv.gz.tbi` | missing |

The CLI blocks partial artifact-set uploads. For example, a CI-SpliceAI model
file is not upload-eligible unless the reference bundle, score cache, and score
cache index are also present. It writes private Storage identity manifests with
MD5/SHA256, component role, source id, and launch-gate metadata, but it does not
register Supabase metadata rows, mutate Render env, seed Render disk, create
signed URLs, flip providers, or unlock restricted predictor launch behavior.

## Immediate Next Tasks

1. Run the MaveDB CC0 materializer only after an approved public-field JSONL
   export is staged and reviewed; then verify health/preflight/report behavior
   before any live Storage or Render movement.
2. Keep PubMed full-corpus materialization paused until the corpus logistics
   spec is explicitly accepted for storage scope, staging, and costs.
3. Run the Tier 2 predictor artifact plan once local ESM1b, CI-SpliceAI, or
   CAPICE artifacts are staged; upload only complete artifact sets.
4. Run the Tier 1 generated-artifact upload/sync lane for ClinGen local and
   literature embeddings after the offline artifacts are built. Do not upload
   the 200-PMID PubMed proof as production PubMed-local.
5. Register the uploaded generated ClinGen artifact in `source_asset_objects` /
   `source_asset_materializations` once that generated-artifact identity is
   approved for source-asset metadata tracking.
6. Upload/register the derived RepeatMasker compact interval index artifact;
   the raw source object is already private and verified.
7. Seed phyloP, ClinVar, and dbSNP onto Render through explicit runtime gates,
   then verify provider-cache before any local-evidence enablement.

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
