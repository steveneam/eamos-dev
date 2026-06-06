# Render Coordinate Resolver Assets

Status: uploaded 2026-06-04. Eamos local coordinate resolution must use local
runtime files on Render, not VariantValidator/ClinVar as coordinate providers.

## Storage Decision

Use Supabase Storage as the private durable source for approved source assets.
Use Render persistent disk or private local cache only for preseeded runtime
artifacts. `hg38.2bit`, bgzip/tabix files, bigWig files, Pfam/HMMER indexes,
and compact immutable coordinate indexes need ordinary filesystem paths. Raw
MANE/RefSeq GFF files are offline build inputs, not production runtime scan
inputs.

Do not expose these objects to the frontend. Keep service-role/S3 credentials
backend-only and do not print them in logs.

## Supabase Bucket And Object Paths

Bucket:

- `eamos-source-assets`

Required objects:

- `transcripts/mane_refseq_gff/MANE.GRCh38.v1.5.refseq_genomic.gff.gz`
- `transcripts/refseq_grch38_p14_gff/GCF_000001405.40_GRCh38.p14_genomic.gff.gz`
- `transcripts/eamos_coordinate_index/eamos-coordinate-index.<version>.jsonl.gz`
- `genomes/ucsc_hg38_2bit/hg38.2bit`

Each object must have a neighboring checksum/size manifest in the same prefix:

- `<object>.manifest.json`

The manifest should include at least source/version, byte size, MD5 or SHA256,
upload status, approval status, and verification timestamp.

Uploaded 2026-06-04:

- `transcripts/mane_refseq_gff/MANE.GRCh38.v1.5.refseq_genomic.gff.gz`
  - size: `8,271,212`
  - manifest:
    `transcripts/mane_refseq_gff/MANE.GRCh38.v1.5.refseq_genomic.gff.gz.manifest.json`
- `transcripts/refseq_grch38_p14_gff/GCF_000001405.40_GRCh38.p14_genomic.gff.gz`
  - size: `56,923,273`
  - manifest:
    `transcripts/refseq_grch38_p14_gff/GCF_000001405.40_GRCh38.p14_genomic.gff.gz.manifest.json`
- `genomes/ucsc_hg38_2bit/hg38.2bit`
  - size: `835,393,456`
  - manifest: `genomes/ucsc_hg38_2bit/hg38.2bit.manifest.json`

## Render Runtime Paths

Materialize verified runtime artifacts into the Render persistent disk before
enabling Eamos-local coordinate resolution. The current raw GFF objects remain
approved offline inputs for the compact index builder:

- `/var/data/eamos/bio_assets/genomes/hg38.2bit`
- `/var/data/eamos/bio_assets/transcripts/eamos-coordinate-index.<version>.jsonl.gz`
- `/var/data/eamos/bio_assets/transcripts/eamos-coordinate-index.<version>.jsonl.gz.tbi`

Do not enable production lookup/search/report/viewer/batch paths that scan raw
GFF files. Use the compact immutable coordinate index after it has been built,
checksummed, and verified on the mounted disk.

## Render Environment

Set these values on the SG backend service:

- `COORDINATE_RESOLVER_ASSET_MATERIALIZATION_ENABLED=false`
- `COORDINATE_RESOLVER_COMPACT_INDEX_PATH=/var/data/eamos/bio_assets/transcripts/eamos-coordinate-index.<version>.jsonl.gz`
- `HG38_2BIT_RUNTIME_ASSET_PATH=/var/data/eamos/bio_assets/genomes/hg38.2bit`

Leave `COORDINATE_RESOLVER_HG38_2BIT_PATH` unset unless a coordinate-specific
reference override is needed. When unset, the coordinate resolver uses
`HG38_2BIT_RUNTIME_ASSET_PATH`.

Do not set `COORDINATE_RESOLVER_MANE_GFF_PATH` or
`COORDINATE_RESOLVER_REFSEQ_GFF_PATH` as runtime web-service dependencies.
Those raw GFF paths are offline build inputs for producing the compact index.
The runtime resolver built from `Settings` ignores raw GFF paths and reads the
compact index only, falling back according to the normal resolver policy when
the compact artifact is absent.

`COORDINATE_RESOLVER_ASSET_MATERIALIZATION_ENABLED=true` is a legacy unsafe
startup-materialization flag. Backend startup now fails closed if it is enabled.
Seed/materialize assets only through Render Shell or another explicit off-peak
process, verify manifests and checksums, then enable the runtime readers that
consume the already-present files.

## Verification

After materialization and redeploy, verify:

1. `/healthz` is green.
2. `/api/v1/health/provider-cache` reports `build_ledger.startup_downloads_allowed == false`.
3. `/api/v1/health/provider-cache` reports
   `source_assets.compact_coordinate_index.ready == true`.
4. `/api/v1/lookup/parse` with coordinate resolution returns
   `coordinate_resolution_audit.resolver_path == "eamos_local"`.
5. The same parse response provenance includes `eamos_local_coordinate_resolver`
   before any fallback provider.
6. No batch coordinate-resolution path depends on VariantValidator, ClinVar, or
   raw MANE/RefSeq/Gencode GFF scans.
