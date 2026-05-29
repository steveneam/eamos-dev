# Private Source Storage Design

Status: Draft

## Summary

Eamos should use Supabase as the durable source-of-truth perimeter for approved source assets, but only through backend-owned paths. Large genomic/protein/source files belong in private immutable object storage with Postgres metadata and checksums; small relational sources belong in private Postgres tables; frontend/Vercel should only call backend APIs that return bounded, serialized slices.

This deliberately differs from the source DOCX where it suggests frontend SQL over source tables. Direct browser access to source/cache tables is not part of the safe design.

## Context and Scope

The current backend has local/fixture parsers and caches for the source matrix: hg38, dbSNP, ClinVar, RepeatMasker, phyloP, MANE, GENCODE, MONDO, HPO, ClinGen, GenCC, MyVariant gnomAD paths, and local protein annotation. Supabase dev now has an `eamos_private` schema for source versions, cache entries, jobs, protein annotation metadata/cache, and private clinical source tables.

This design covers the production/dev shape for the DOCX Tier 1 and Tier 2 assets, plus how Tier 3 tables and cache rows fit around them. It does not approve any production source downloads, object uploads, deploy/env changes, or licensed/restricted source use.

## Goals

- Keep source files, local-model caches, and derived clinical/genomic rows backend-only.
- Make every source import traceable by release, checksum, object path, row count, warning state, and provenance.
- Avoid startup downloads on Render and avoid Vercel/frontend access to private data.
- Support local indexed readers by materializing object-storage assets into verified local cache files before use.
- Let Claude and Codex share one operational map for database/webserver decisions without exposing secrets.

## Non-Goals

- No public genomic buckets.
- No frontend direct SQL over source/cache tables.
- No Vercel-hosted large source assets.
- No unrestricted user uploads.
- No InterVar/ANNOVAR/OMIM production execution or restricted predictor unlocks until separate license/product gates are approved.
- No live third-party protein API fallback or startup protein downloads.

## Constraints

- Supabase Storage buckets are private by default and private downloads require RLS-authorized access or signed URLs. Trusted backend clients may use service-role credentials, which must never reach the browser.
- Supabase recommends treating the `storage` schema as read-only; object writes/deletes should go through the Storage API, not direct SQL against storage metadata.
- Current backend indexed readers (`pysam`, `pyBigWig`, `twobitreader`, RepeatMasker readers) generally need local filesystem paths, not arbitrary HTTPS URLs.
- Render filesystem/runtime behavior means source assets must be pre-materialized or fetched into a durable/verified local cache path before reader use. No request-time cold downloads.
- The current dev Supabase project is `eamos-dev` (`cpdjxsgasaesysvxkpmi`); env/deploy wiring still requires explicit approval.

## Proposed Design

Use four layers:

1. Source metadata in private Postgres.
   `eamos_private.local_source_versions` is the manifest gate for all source assets, including file assets and relational imports. A source is usable only if its expected release/checksum/size and import state are recorded.

2. Private immutable Storage objects for large assets.
   Create a private bucket, recommended name `eamos-source-assets`, with immutable object paths:
   `source_id/release/checksum/file-name`.
   Examples:
   - `ucsc_hg38_2bit/hg38-2020-12/md5-.../hg38.2bit`
   - `ncbi_dbsnp_gcf/GCF_000001405.40/sha256-.../GCF_000001405.40.gz`
   - `ncbi_dbsnp_gcf/GCF_000001405.40/sha256-.../GCF_000001405.40.gz.tbi`
   - `ncbi_clinvar_vcf/clinvar_20260523/sha256-.../clinvar.vcf.gz`
   - `ucsc_phylop_100way/hg38/sha256-.../hg38.phyloP100way.bw`

3. Backend local materialization cache.
   Backend startup may validate configured local paths, but it must not cold-download production assets. A separate backend admin/import job may download from private Storage to an ignored local cache directory, verify checksum and size, then atomically mark the local asset ready. Reader services only open files after this ready marker exists.

4. Derived private tables/cache rows.
   Small sources and derived indexes go into private tables or `local_model_cache_entries`:
   - Tier 2 MANE/GENCODE derived transcript, exon/CDS, alias, canonical/MANE rows.
   - Tier 3 MONDO/HPO/ClinGen/GenCC rows.
   - Gene viewer full-locus and local evidence cache payloads.
   - Protein annotation jobs/results keyed by protein sequence SHA256 plus source release/checksum.

## Tier Mapping

Tier 1 large binary/indexed assets:
- Store object metadata now in `local_source_versions`.
- Upload to private Storage only after explicit approval.
- Backend readers use local verified cache files, not browser URLs.
- DB stores object URI, checksum, size, release, source URL, license/terms status, and materialization status.

Tier 2 repo/local files:
- MANE and GENCODE should not be browser assets. Full source files can be private Storage objects; derived transcript models belong in private DB/cache rows.
- InterVar config remains metadata-only and disabled by policy until approval. Do not execute or serialize InterVar-derived classifications yet.
- Tiny fixtures may stay in repo for tests, but production-sized files should not be committed.

Tier 3 relational sources:
- Import to private Postgres tables in `eamos_private`.
- Tables already scaffolded for MONDO, HPO terms, HPO disease/gene phenotypes, ClinGen gene validity, and GenCC assertions.
- Frontend receives only backend API responses shaped for report/viewer needs.

Tier 4 live APIs:
- MyVariant/gnomAD remains backend-mediated.
- Cache summaries in private cache tables with source status, freshness, raw warnings, and restricted-field stripping.

## Runtime Flow

```text
Admin/import job
  -> verify source approval and license status
  -> upload or register private Storage object
  -> write local_source_versions row
  -> materialize derived DB/cache rows
  -> run advisor checks and smoke queries

Backend request
  -> resolve source/cache key
  -> read private DB cache or verified local asset
  -> if source unavailable, fail closed or stale-on-failure
  -> return bounded public API payload

Frontend/Vercel
  -> calls Eamos backend API only
  -> never receives Supabase service role, private object URL, or table access
```

## Interfaces and Data

Scaffolded metadata tables:

- `eamos_private.source_asset_objects`
  Tracks bucket, object path, byte size, checksum, content type, release, source version FK, upload status, and materialization policy.

- `eamos_private.source_asset_materializations`
  Tracks backend host/environment, local path hash, materialized checksum, ready marker, last verification, failure reason, and stale status.

These tables are metadata-only. They do not create a bucket, upload an object, grant browser access, or make a source reader ready by themselves.

- Backend admin/import CLI:
  `python -m app.cli.eamos_source_import --source <id> --release <release> --register-metadata-only`

- Backend smoke CLI:
  `python -m app.cli.eamos_source_smoke --source <id> --case rpe65`

No frontend contract should expose these private table names. Claude-facing frontend contracts should use existing or new backend endpoints only.

## Alternatives Considered

Public Supabase Storage buckets:
Rejected. They are simpler and more CDN-friendly, but raw genomic/protein/source files and indexes should not be publicly listable or directly readable.

Frontend direct Supabase SQL:
Rejected. RLS can protect rows, but source/cache schema visibility and direct query coupling create avoidable security and product risks.

Commit production source files to repo:
Rejected for large files and licensed/restricted data. It bloats git, complicates deploys, and makes policy separation harder.

Render startup downloads:
Rejected. Cold starts and deploys become fragile, slow, and dependent on third-party availability.

Supabase Storage direct reader URLs:
Rejected for most indexed readers. The current Python readers need local paths and sidecar indexes; materialization is the safer runtime boundary.

## Tradeoffs

The design adds an import/materialization step, but it makes runtime behavior deterministic and testable. It postpones raw object uploads until approval, but the metadata/import schema can be verified now. Private buckets and backend APIs are less convenient than public URLs, but they prevent accidental data exposure and keep Vercel lightweight.

## Cross-Cutting Concerns

Security:
- Service-role keys are backend-only.
- Browser roles get no grants on private source/cache tables.
- Storage bucket remains private.
- No signed URL should be sent to the frontend for raw source assets unless a future reviewed feature explicitly requires it.

Reliability:
- All source use is gated on checksum verification.
- Stale-on-failure is allowed for cache summaries only when provenance and warning state are preserved.
- Large asset readers fail closed if the local materialization marker is missing or checksum mismatches.

Performance:
- Indexed readers operate on local files.
- Derived DB tables should carry query-specific indexes before runtime use.
- Supabase advisor INFO-level unused-index warnings are expected immediately after creating empty/new tables.

Cost:
- Supabase Storage is suitable for durable private assets, but large files such as dbSNP, phyloP, SpliceAI, CADD, and PrimateAI-3D can create storage and egress costs. Only approved Day 1 sources should be uploaded.

Operations:
- Every import job writes row counts and warnings.
- Every DDL/import pass ends with security advisors, performance advisors, and smoke queries.
- Rollbacks should delete derived rows by source_version_id, not mutate raw history in place.

## Rollout and Migration

1. Keep metadata-only rows for all known sources.
2. Import Tier 3 small clinical source rows into private tables.
3. Add `source_asset_objects` and `source_asset_materializations` after review.
4. Register, but do not upload, Tier 1/Tier 2 large objects until approval.
5. Upload one approved pilot object, likely `hg38.2bit`, to private Storage.
6. Prove backend materialization to local cache and checksum verification.
7. Enable one bounded backend read path with stale/fail-closed tests.
8. Repeat source by source.

## Claude Handoff Notes

- Treat Supabase source/cache tables as backend-only. Do not build frontend SQL clients for them.
- Vercel should not host or fetch raw Tier 1/Tier 2 source files.
- Build UI against backend API payloads and status fields, not table schemas or object paths.
- If a report or Workbench screen needs source data, request a backend endpoint or lazy section.
- Respect stale/fail-closed warning strings; do not hide source unavailability as empty evidence.
- Do not introduce public buckets, signed raw-source URLs, or `NEXT_PUBLIC_*` service-role values.

## Open Questions

- Which bucket name and retention policy should be approved for large source assets?
- Should dev and production use separate buckets or separate object prefixes under different Supabase projects?
- Which source is the first private Storage pilot: `hg38.2bit` or ClinVar VCF?
- What maximum local materialization cache size should Render use?
- Should restricted/pro-tier predictors have separate buckets or a policy column on source metadata?

## Decision

Recommended decision: approve a backend-only private source-storage lane. Start with metadata and Tier 3 relational imports now. Hold raw Tier 1/Tier 2 object uploads until explicit approval of bucket name, object path convention, and materialization job behavior. Frontend/Vercel integration remains API-only.

References:
- Supabase private bucket behavior and signed URL options: https://supabase.com/docs/guides/storage/buckets/fundamentals
- Supabase Storage RLS/access control and service-key caveat: https://supabase.com/docs/guides/storage/security/access-control
- Supabase storage schema should be treated as read-only for object operations: https://supabase.com/docs/guides/storage/schema/design
