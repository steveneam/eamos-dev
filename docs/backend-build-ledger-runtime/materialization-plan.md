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
| `dbsnp_local_adapter` | `source_ready_for_materialization` | Fixture adapter exists; production object metadata is verified/private in Supabase, but SG runtime files are not seeded. |
| `phylop_conservation_reader` | `source_ready_for_materialization` | Reader proof exists; production object metadata is verified/private in Supabase, but SG runtime files are not seeded. |
| `clinvar_local_adapter` | `source_ready_for_materialization` | Fixture adapter exists; no durable production object was found in this pass. |
| `repeatmasker_local_adapter` | `source_ready_for_materialization` | Fixture adapter exists; no durable production object was found in this pass. |
| `local_evidence_orchestrator` | `disabled` | Correct until the full indexed-source batch is runtime-configured and verified. |
| `clinical_source_tables` | `import_ready` | Supabase tables are present but still fixture-scale. |

Supabase inventory checked on 2026-06-19:

| Area | Observed state | Required action |
| --- | --- | --- |
| `source_asset_objects` | Rows exist for hg38, Pfam, compact coordinate index artifact + manifest, and five dbSNP/phyloP existing-object rows. The dbSNP/phyloP rows are `verified`, `approved`, and private. | Register ClinVar and RepeatMasker objects before treating them as durable approved assets. |
| `source_asset_materializations` | hg38, Pfam, and compact coordinate index SG rows are `ready`. Five dbSNP/phyloP SG rows exist and are intentionally `not_materialized` with `render_disk_seed_not_performed`. | Register ClinVar/RepeatMasker materializations, then seed dbSNP/phyloP/ClinVar/RepeatMasker only through explicit runtime gates. |
| Storage prefix `transcripts/eamos_coordinate_index` | Compact index artifact and manifest uploaded, registered, and materialized on SG on 2026-06-14. | No repeat action; next blocker is deploying the local build-ledger Gene View fix. |
| Storage prefix `ncbi_dbsnp_gcf_000001405_40` | Objects and manifest sidecars were proved by S3 `head_object`; registered metadata covers bgzip VCF, tabix index, and upstream checksum. | Seed bgzip and `.tbi` onto Render only after the explicit runtime gate. |
| Storage prefix `ucsc_phylop100way_hg38` | Objects and manifest sidecars were proved by S3 `head_object`; registered metadata covers bigWig and upstream checksum. | Seed bigWig onto Render only after the explicit runtime gate. |
| ClinVar / RepeatMasker prefixes | No durable objects observed. | Locate, upload, register, and verify before runtime work. |
| Clinical tables | MONDO/HPO/ClinGen/GenCC tables contain fixture-scale rows only. Release-file importer now plans the staged full tables: MONDO 31,886; HPO terms 19,944; HPO disease phenotypes 281,996; HPO gene phenotypes 329,339; ClinGen 3,596; GenCC 29,845. | Apply through the committed importer from a host that can reach the Supabase Postgres pooler; the local DB URL gate is configured, but this workstation timed out to the pooler before writes. No Render disk work is involved. |

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
2. **Done 2026-06-19 02:02 +1000:** registered dbSNP Storage objects under
   `source_asset_objects`:
   - source id `ncbi_dbsnp_gcf_000001405_40`;
   - roles for bgzip VCF, tabix index, checksum/manifest objects;
   - approval and license status copied from the source rollout plan;
   - matching SG materialization rows remain fail-closed as
     `not_materialized`.
3. **Done 2026-06-19 02:02 +1000:** registered phyloP Storage objects under
   `source_asset_objects`:
   - source id `ucsc_phylop100way_hg38`;
   - roles for bigWig and checksum/manifest objects;
   - matching SG materialization rows remain fail-closed as
     `not_materialized`.
4. Locate or upload ClinVar GRCh38 VCF plus `.tbi` before any ClinVar runtime
   flip.
5. Locate or upload RepeatMasker official source plus the derived compact
   runtime interval index before any RepeatMasker runtime flip.

Prefer committed metadata CLIs/importers over manual SQL. If SQL is used for a
one-time reconciliation, capture the exact query in a follow-up runbook.
M2 used the committed `eamos_source_import --existing-object-set dbsnp_phylop`
path for planning and S3 head verification; the local CLI database apply gate
remained unset, so the verified registration payload was applied through the
available Supabase connector and read back from `eamos_private`.

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

### 6. Tier 1 Generated SQLite Artifacts

Goal: move ClinGen local, PubMed local, and literature RAG embedding SQLite
artifacts through the same offline -> private Storage -> Render disk pattern
without startup downloads or provider flips.

The generated-asset lane is now code-backed:

```bash
python -m app.cli.eamos_generated_artifact_upload --compact
python -m app.cli.eamos_generated_artifact_upload --artifact pubmed_local --upload --upload-mode s3_multipart

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

1. Keep PubMed full-corpus materialization paused until the corpus logistics
   spec is explicitly accepted for storage scope, staging, and costs.
2. Run the Tier 2 predictor artifact plan once local ESM1b, CI-SpliceAI, or
   CAPICE artifacts are staged; upload only complete artifact sets.
3. Run the Tier 1 generated-artifact upload/sync lane for ClinGen local and
   literature embeddings after the offline artifacts are built. Do not upload
   the 200-PMID PubMed proof as production PubMed-local.
4. Register the uploaded generated artifacts in `source_asset_objects` /
   `source_asset_materializations` once the Storage object identities are
   approved.
5. Add production settings/probes for dbSNP, phyloP, ClinVar, and RepeatMasker
   runtime paths.
6. Register dbSNP and phyloP Storage objects in `source_asset_objects`.
7. Seed dbSNP and phyloP onto Render as the first heavy local-adapter batch.

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
