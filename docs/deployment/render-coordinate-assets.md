# Render Coordinate Resolver Assets

Status: uploaded 2026-06-04. Eamos local coordinate resolution must use local
runtime files on Render, not VariantValidator/ClinVar as coordinate providers.

## Storage Decision

Use Supabase Storage as the private durable source for approved source assets.
Use Render persistent disk or private local cache as the runtime source of
truth because the resolver needs ordinary filesystem paths for GFF parsing and
`hg38.2bit` random access.

Do not expose these objects to the frontend. Keep service-role/S3 credentials
backend-only and do not print them in logs.

## Supabase Bucket And Object Paths

Bucket:

- `eamos-source-assets`

Required objects:

- `transcripts/mane_refseq_gff/MANE.GRCh38.v1.5.refseq_genomic.gff.gz`
- `transcripts/refseq_grch38_p14_gff/GCF_000001405.40_GRCh38.p14_genomic.gff.gz`
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

Materialize the objects into the Render persistent disk before enabling
Eamos-local coordinate resolution:

- `/var/data/eamos/bio_assets/transcripts/MANE.GRCh38.v1.5.refseq_genomic.gff.gz`
- `/var/data/eamos/bio_assets/transcripts/GCF_000001405.40_GRCh38.p14_genomic.gff.gz`
- `/var/data/eamos/bio_assets/genomes/hg38.2bit`

## Render Environment

Set these values on the SG backend service:

- `COORDINATE_RESOLVER_ASSET_MATERIALIZATION_ENABLED=true`
- `COORDINATE_RESOLVER_MANE_GFF_PATH=/var/data/eamos/bio_assets/transcripts/MANE.GRCh38.v1.5.refseq_genomic.gff.gz`
- `COORDINATE_RESOLVER_REFSEQ_GFF_PATH=/var/data/eamos/bio_assets/transcripts/GCF_000001405.40_GRCh38.p14_genomic.gff.gz`
- `HG38_2BIT_RUNTIME_ASSET_PATH=/var/data/eamos/bio_assets/genomes/hg38.2bit`

Leave `COORDINATE_RESOLVER_HG38_2BIT_PATH` unset unless a coordinate-specific
reference override is needed. When unset, the coordinate resolver uses
`HG38_2BIT_RUNTIME_ASSET_PATH`.

When `COORDINATE_RESOLVER_ASSET_MATERIALIZATION_ENABLED=true`, backend startup
downloads the three private Storage objects to the configured runtime paths,
verifies each object against its sidecar manifest, atomically places verified
files on the persistent disk, and skips already verified files on subsequent
deploys. Startup fails closed if any enabled materialization check fails.

## Verification

After redeploy, verify:

1. `/api/v1/health` is green.
2. `/api/v1/lookup/parse` with coordinate resolution returns
   `coordinate_resolution_audit.resolver_path == "eamos_local"`.
3. The same parse response provenance includes `eamos_local_coordinate_resolver`
   before any fallback provider.
4. No batch coordinate-resolution path depends on VariantValidator or ClinVar.
