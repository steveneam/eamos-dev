# Local-First Data Source Strategy Design

Status: Draft
Owner: Codex/backend
Last updated: 2026-05-26 21:25 +1000 - Codex

## Summary

Eamos needs a local-first source architecture that separates three decisions
that were previously blurred together:

1. Local reference/model layer: how the backend resolves sequence, transcripts,
   rsIDs, and source-ready variant identity quickly and consistently.
2. Supabase/storage layer: where small tables, source-cache rows, object assets,
   and large indexed files live, and how the runtime reads them.
3. Licensing/policy layer: which data fields can be requested, cached, returned,
   or unlocked for commercial production.

The recommended direction is to make `hg38.2bit` the first asset proof, build a
runtime data-source registry plus license policy before any provider enablement,
and treat Supabase as metadata/cache/object storage rather than as a place to
mirror all large genomic data into ordinary SQL tables.

## Context And Scope

Current relevant artifacts:

- `plans/local-first-search-licensing-architecture.md`
- `plans/data-source-registry/spec.md`
- `plans/data-source-registry/source-registry.seed.json`
- `plans/source-cache-architecture.md`
- `app/backend/app/core/db.py`
- `app/backend/app/repos/source_cache_repo.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/sequence_context.py`

The backend already has source-cache infrastructure and source-specific lookup
plumbing. The next problem is not another cache. It is deciding the dependency
order and policy boundaries so downloads, installs, Supabase work, and provider
adapters do not happen in the wrong sequence.

This design covers backend architecture and sequencing only. It does not
approve new downloads, installs, Supabase writes, environment mutation,
deploys, or commercial use of restricted predictors.

Current local asset note: an ignored UCSC `hg38.2bit` already exists at
`app/backend/data/bio_assets/genomes/hg38.2bit` from the prior local `isPcr`
work. It is 835,393,456 bytes and MD5 re-verified on 2026-05-26 as
`dcc3ea27079aa6dc3f9deccd7275e0f8`, matching
`app/backend/data/bio_assets/genomes/md5sum.txt`. The next work is not a fresh
download; it is to inventory this asset into the registry and prove the reader
/ storage path cleanly.

Terminology: "local model" here means the local genomic data/reference model:
reference genome, transcript model, rsID/variant identity model, and source
adapter models. It does not mean a local LLM.

## Goals

- Make source lookup fast enough for report search and Workbench by resolving
  common identity and sequence context locally before external APIs.
- Put `hg38.2bit` first because it proves the shared reference-window path for
  sequence context, gene viewer, primer design, CRISPR guide discovery, Sanger
  alignment, and variant normalization checks.
- Keep Supabase responsibilities explicit: small relational source tables,
  source-cache rows, provenance metadata, and object-storage assets, not large
  unindexed SQL mirrors.
- Enforce licensing in backend code, not only in frontend copy or visual locks.
- Preserve the DOCX matrix exactly while making the implementation order safer.
- Keep fixture/offline mode deterministic.

## Non-Goals

- Downloading or replacing `hg38.2bit`, dbSNP, ClinVar, predictors, or any
  other asset.
- Installing `pysam`, `pyBigWig`, `twobitreader`, `py2bit`, `duckdb`, or
  `pyarrow`.
- Creating Supabase buckets, schemas, migrations, or storage policies.
- Enabling MyVariant, InterVar, SpliceAI, CADD, REVEL, or PrimateAI-3D in
  production paths.
- Changing frontend contracts or rendering.
- Touching `/runs` or AlphaMissense.

## Constraints

- MyVariant is Day 1 gnomAD lookup only. It must not be a path to restricted
  predictor fields.
- Restricted predictors include SpliceAI, CADD, REVEL, and PrimateAI-3D for
  current planning. They stay locked until commercial rights are recorded.
- InterVar is DOCX-intended but blocked for commercial production until
  InterVar, ANNOVAR, and OMIM rights are resolved.
- Assets whose actual download size is greater than 10 GB stage on `C:` until
  moved to Supabase Storage or another approved object-storage target.
- Supabase writes require explicit approval.
- Existing source-cache repository and lookup patterns should be extended, not
  replaced.
- Default tests must not require network or large assets.

## Proposed Design

### Track 1: Local Reference And Identity Model

Build this as the first technical track because it is the dependency for the
other two tracks.

Order:

1. Runtime data-source registry and license policy skeleton.
2. Inventory and re-verify the existing ignored `hg38.2bit` asset without
   moving it or mutating environment.
3. Tiny `ReferenceGenomeStore` fixture with stable tests.
4. 2bit reader compatibility proof against the tiny fixture, then against the
   existing local `hg38.2bit` path.
5. Replacement or fresh `hg38.2bit` download only after explicit source URL,
   checksum, storage, and download approval.
6. Local transcript model store from MANE/GENCODE fixtures.
7. Local dbSNP adapter for `GCF_000001405.40` after the reference path is
   proven.
8. Local ClinVar adapter and source-cache read-through.

The `ReferenceGenomeStore` should expose a small interface such as:

- `get_sequence(chrom, start, end, build) -> ReferenceWindow`
- `validate_reference_base(chrom, position, expected_base) -> result`
- `metadata() -> source version, checksum, storage path, reader`

The first implementation must use a tiny checked-in fixture or synthetic 2bit
fixture. It should not require the full `hg38.2bit` file.

### Track 2: Supabase And Storage Runtime

Use Supabase for:

- Small source tables: Mondo, HPO, ClinGen gene validity, GenCC.
- Source-cache rows and provenance metadata through backend-only service-role
  paths.
- Object storage for reviewed static assets after range/local-cache behavior is
  proven.

Do not use Supabase for:

- Large unindexed SQL mirrors of dbSNP, gnomAD, SpliceAI, CADD, or whole
  predictor tables.
- Direct frontend reads of source-cache or source-registry tables.
- Random access to object files until `.2bit`, `.vcf.gz/.tbi`, `.bw`, and
  `.bb` reader behavior is proven against the intended path.

The storage proof should answer:

- Does the reader require a local filesystem path?
- Can the runtime stream/range-read from object storage directly?
- If not, when and where does the backend download/cache the file locally?
- How are checksum, source version, and stale local cache handled?

### Track 3: Licensing And Field Policy

Add a backend policy gate before MyVariant or dbNSFP-like adapters can return
annotation blocks.

Policy components:

- Source registry rows with `license_status`, `allowed_fields`,
  `restricted_fields`, `allowed_product_tiers`, and `download_approved`.
- Request allowlists per adapter. MyVariant can request only `gnomad_genome`
  and `gnomad_exome`.
- Response filters before normalization, cache writes, and serialization.
- Tests that public/prod payloads do not include SpliceAI, CADD, REVEL, or
  PrimateAI-3D when unlicensed.
- Internal fixture mode may retain restricted examples only with explicit
  fixture/internal status and warnings.

## Architecture Views

Request-time lookup should flow like this:

```text
User query
  -> local parser / normalizer
  -> local reference + transcript + identity stores
  -> source cache / stale cache
  -> approved live providers or local indexed files
  -> license and field filter
  -> report / Workbench response
```

Asset lifecycle should flow like this:

```text
Registry row draft
  -> source URL + terms + checksum plan reviewed
  -> tiny fixture proof
  -> reader compatibility proof
  -> approved staging/download
  -> manifest entry
  -> runtime adapter enabled behind tests
```

## Interfaces And Data

The runtime registry can start as a backend JSON or Python module validated by
tests. It should be promoted from:

- `plans/data-source-registry/source-registry.seed.json`

Recommended runtime shape:

- `source_id`
- `priority`
- `tier`
- `files_or_api`
- `source_url`
- `expected_size`
- `actual_size`
- `checksum`
- `source_version`
- `storage_target`
- `temporary_staging`
- `adapter`
- `license_status`
- `allowed_fields`
- `restricted_fields`
- `allowed_product_tiers`
- `download_approved`

The first code-facing store interface should be the reference store, because it
is small and foundational. dbSNP, ClinVar, and predictor adapters should follow
only after the reference path is proven.

## Alternatives Considered

### Start With dbSNP

dbSNP is critical for rsID lookup, but it is about 15 GB and requires indexed
VCF/tabix reader behavior. Starting there tests too many risks at once:
large-file staging, reader install, object-storage behavior, contig
normalization, and rsID semantics.

### Start With MyVariant

MyVariant is useful for gnomAD frequencies, but it does not solve local
sequence context or Workbench acceleration. It also risks pulling in restricted
aggregator fields unless policy gates exist first.

### Start With Supabase Schema Work

Supabase tables are needed for small clinical datasets and source metadata, but
schema work before reader/storage proofs risks designing tables around
unverified runtime access patterns.

### Start With Restricted Predictor Files

This is blocked. It requires commercial license approval, entitlement policy,
and audit logging before production enablement.

## Tradeoffs

- Starting with `hg38.2bit` delays dbSNP and MyVariant briefly, but it proves a
  shared dependency that will reduce rework across report and Workbench code.
- A runtime registry adds up-front ceremony, but it prevents accidental
  downloads, unlicensed field leakage, and unclear storage ownership.
- Supabase object storage may still need local runtime caching if file readers
  require normal filesystem paths. The design keeps that option open.
- Fixture-first local stores add test scaffolding, but they keep CI small and
  deterministic.

## Cross-Cutting Concerns

Security:

- Keep source tables and source-cache rows backend-only.
- Do not expose service-role access or direct storage write paths to clients.
- If Supabase public schema is used for any source table, enable RLS and avoid
  broad `TO authenticated` access without row-level authorization.

Licensing:

- Treat license policy as an execution gate, not documentation.
- Do not request restricted fields from aggregators in public/prod mode.

Reliability:

- Serve stale cache only with explicit stale metadata.
- Fail closed on reference mismatch or missing local asset.

Performance:

- Prefer local reference and identity reads for request-time paths.
- Avoid request-time full-file scans.

Operations:

- Every downloaded asset needs source URL, checksum, source version, storage
  target, and update policy.
- Assets greater than 10 GB stage on `C:` first.

## Rollout And Migration

1. Review this design.
2. Write the implementation spec for the runtime registry and policy gate.
3. Write the plan with separate tasks for:
   - runtime registry validation;
   - restricted field policy tests;
   - inventory/reverification of the existing local `hg38.2bit`;
   - tiny `ReferenceGenomeStore` fixture;
   - 2bit reader compatibility proof against fixture and existing local asset;
   - approved `hg38.2bit` storage/promotion proof;
   - dbSNP adapter after reference proof;
   - Supabase storage/table plan after reader behavior is known.
4. Implement only the approved first task.

Rollback is simple for the first phases: remove the runtime registry module or
disable the reference store feature flag. No source data migration should exist
before explicit approval.

## Open Questions

- Which 2bit reader should Eamos use after Windows and deployed-runtime proof:
  `twobitreader`, `py2bit`, or another maintained package?
- Should full `hg38.2bit` runtime access be object-storage direct, startup
  local cache, attached disk, or explicit local path?
- What exact Supabase bucket/prefix and private policy shape should static
  source assets use?
- Which public/prod environment flag should drive restricted-field filtering:
  deployment mode, product tier, license registry state, or all three?
- Did "local model" mean only the local genomic data model, or also a local AI
  model? This design assumes the former.

## Decision

Adopt a three-track architecture:

- Local reference/model first, with `hg38.2bit` as `p0_first_asset_proof`.
- Supabase as backend-owned metadata/cache/object storage, not a large SQL
  genomic warehouse.
- Licensing as a backend-enforced policy gate before restricted fields are
  requested, cached, or serialized.

Human review is needed before writing the implementation spec and task plan.
