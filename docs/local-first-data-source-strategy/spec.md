# Local-First Data Source Strategy Spec

Status: Draft for user review
Owner: Codex/backend
Last updated: 2026-05-26 21:32 +1000 - Codex

## What

Implement the first backend foundation for local-first genomic source access:
a runtime data-source registry, a backend-enforced license/field policy, and a
fixture-first local reference genome store that inventories the existing local
`hg38.2bit` asset without downloading or moving it. This is the prerequisite
for later dbSNP, ClinVar, MyVariant gnomAD, Supabase Storage, and restricted
predictor work.

## Context

Approved design:

- `docs/local-first-data-source-strategy/design.md`

Planning inputs:

- `plans/data-source-registry/source-registry.seed.json`
- `plans/data-source-registry/spec.md`
- `plans/local-first-search-licensing-architecture.md`
- `plans/source-cache-architecture.md`

Existing backend surfaces:

- `app/backend/app/core/db.py`
- `app/backend/app/repos/source_cache_repo.py`
- `app/backend/app/services/source_cache.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/sequence_context.py`
- `app/backend/app/core/config.py`

Existing local asset:

- `app/backend/data/bio_assets/genomes/hg38.2bit`
- Size: `835,393,456` bytes
- MD5: `dcc3ea27079aa6dc3f9deccd7275e0f8`
- MD5 source: `app/backend/data/bio_assets/genomes/md5sum.txt`

This spec assumes "local model" means the local genomic data/reference model:
reference genome, transcript model, rsID/variant identity model, and source
adapter models. It does not introduce a local AI model.

## Requirements

1. Add a backend runtime source registry derived from the reviewed seed JSON.
2. Registry validation must fail if a source row is missing source identity,
   license status, allowed fields, restricted fields, storage target, checksum
   policy, or download-approval status.
3. Registry validation must enforce that `ucsc_hg38_2bit` is
   `p0_first_asset_proof`.
4. Registry validation must enforce that downloads are not approved unless a
   source URL, checksum policy, source version policy, storage target, and
   license status are present.
5. Add a backend license/field policy that can answer whether a source field
   may be requested, cached, normalized, or serialized in a public/prod path.
6. The policy must lock SpliceAI, CADD, REVEL, and PrimateAI-3D while their
   source rows remain unlicensed.
7. The policy must allow MyVariant only for `gnomad_genome` and
   `gnomad_exome`.
8. Add tests proving restricted predictors cannot leak through public/prod
   policy checks.
9. Inventory the existing local `hg38.2bit` read-only: path, size, MD5,
   source URL, and registry metadata.
10. Do not download, replace, move, upload, or commit `hg38.2bit`.
11. Add a fixture-first `ReferenceGenomeStore` interface with tests that do not
    require the full `hg38.2bit`.
12. The reference store must support sequence-window reads, chromosome alias
    normalization, reference-base validation, and metadata reporting.
13. The full local `hg38.2bit` can be used only in opt-in local tests or smoke
    checks that skip cleanly when the file is absent.
14. No Supabase writes, migrations, storage buckets, or environment mutations
    are part of this first spec.
15. No MyVariant adapter, dbSNP adapter, ClinVar adapter, InterVar integration,
    or restricted predictor enablement is part of this first spec.

## Design

### Runtime Registry

Add a backend package such as:

- `app/backend/app/data_sources/__init__.py`
- `app/backend/app/data_sources/registry.py`
- `app/backend/app/data_sources/policy.py`

The runtime registry can initially embed or load a curated JSON copy derived
from `plans/data-source-registry/source-registry.seed.json`. Keep runtime data
small and explicit; do not load arbitrary plan files at request time.

Core models:

- `DataSourceRecord`
- `DataSourceRegistry`
- `LicenseStatus`
- `ProductTier`
- `FieldPolicyDecision`

Minimum registry fields:

- `source_id`
- `priority`
- `tier`
- `files_or_api`
- `source_url`
- `expected_size`
- `actual_size_bytes_local`
- `checksum`
- `source_version`
- `storage_target`
- `current_local_path`
- `temporary_staging`
- `adapter`
- `license_status`
- `allowed_fields`
- `restricted_fields`
- `allowed_product_tiers`
- `download_approved`

### License And Field Policy

The policy should be a pure backend helper first, not request middleware.

Recommended API:

```python
policy = SourceFieldPolicy(registry)
policy.can_request(source_id, field_path, product_tier="public")
policy.can_cache(source_id, field_path, product_tier="public")
policy.can_serialize(source_id, field_path, product_tier="public")
policy.filter_payload(source_id, payload, product_tier="public")
```

Public/prod behavior:

- MyVariant allowlist: `gnomad_genome`, `gnomad_exome`.
- MyVariant denylist: `cadd`, `dbnsfp.revel`, `dbnsfp.primateai`,
  `spliceai`, `revel`, `primateai_3d`.
- Restricted predictors blocked while `license_status` is
  `restricted_unlicensed`.
- Internal fixture mode may retain restricted predictor examples only when
  explicitly labeled as fixture/internal.

The policy should be easy to call from future MyVariant/dbNSFP/local predictor
adapters before a request is made, before source-cache upsert, and before
serialization.

### ReferenceGenomeStore

Add a small interface, for example:

```python
class ReferenceGenomeStore:
    def metadata(self) -> ReferenceGenomeMetadata: ...
    def get_sequence(self, chrom: str, start: int, end: int) -> ReferenceWindow: ...
    def validate_reference_base(self, chrom: str, position: int, expected: str) -> ReferenceBaseCheck: ...
```

Coordinate convention:

- Inputs are 1-based inclusive genomic coordinates for callers.
- The reader adapter handles conversion to any 0-based half-open internal
  representation.
- Chromosome aliases normalize `1`, `chr1`, `NC_000001.11` where the store has
  an explicit mapping.

First implementation:

- Add a fixture-backed store with tiny deterministic sequence data.
- Add tests for window reads, aliases, boundaries, and reference-base checks.
- Add metadata support for source ID, source URL, checksum, local path, and
  source version.

Full `hg38.2bit` proof:

- Do not add a 2bit package in this spec unless the user explicitly approves
  the dependency proof.
- A later task should choose `twobitreader`, `py2bit`, or another maintained
  reader after compatibility testing.
- Opt-in smoke should read the known RPE65 region from the existing local
  asset and verify the reference base for GRCh38 `1:68444869` is `T` for
  `NM_000329.3:c.260A>G` / `1-68444869-T-C`.

### Supabase Boundary

This first spec does not create or mutate Supabase resources.

It should record policy only:

- Source-cache and source registry remain backend-only.
- Small source tables can later live in Supabase Postgres after reviewed
  migrations and RLS/private-schema decisions.
- Large files can later live in Supabase Storage only after reader behavior is
  proven and storage policies are reviewed.

## Decisions

- Decision: Start with runtime registry and policy before provider adapters.
  - Alternatives: start with MyVariant or dbSNP.
  - Why: adapters without policy can request or leak restricted fields, and
    large assets without registry checks can drift.
  - Reversible: yes, but this should remain the default foundation.

- Decision: `hg38.2bit` is first asset proof.
  - Alternatives: dbSNP first, MyVariant first, ClinVar first.
  - Why: reference windows underpin sequence context, gene viewer, primer,
    CRISPR, alignment, and normalization checks. It is also smaller and already
    present locally.
  - Reversible: not recommended.

- Decision: Fixture-backed reference store before a real 2bit reader.
  - Alternatives: install a reader and test against full `hg38.2bit` first.
  - Why: tests stay deterministic and the interface can settle before package
    selection.
  - Reversible: yes.

- Decision: No Supabase writes in the first slice.
  - Alternatives: create buckets/tables now.
  - Why: reader behavior and source ownership should be proven first.
  - Reversible: yes after review.

- Assumption: Public/prod restricted-field filtering is required even for Pro
  UI labels until licenses are actually enabled.

## Versions

- Python runtime: existing backend requirement is Python `>=3.10`.
- Existing dependencies: `httpx`, `primer3-py`, and `biopython` remain as-is.
- Candidate future reader dependencies are not pinned by this spec:
  `twobitreader` or `py2bit` for 2bit, `pysam` for tabix/VCF, `pyBigWig` for
  bigWig, and optionally `duckdb`/`pyarrow` for columnar local stores.
- Any new package must be selected in a separate compatibility proof using
  current official package metadata at that time.

## Invariants

- Default test suite must not require network, Supabase, or the full
  `hg38.2bit`.
- Existing `USE_REAL_APIS=false` fixture behavior must stay deterministic.
- Existing source-cache behavior must not be replaced.
- No restricted predictor fields may be requestable or serializable in
  public/prod while unlicensed.
- MyVariant may only request/return gnomAD fields.
- No source row may be marked `download_approved=true` without complete review
  metadata.
- The existing ignored `hg38.2bit` must not be moved, replaced, or committed.

## Error Behavior

- Missing registry source: return a policy denial or configuration error, not a
  permissive default.
- Missing required registry metadata: validation fails at startup/test time.
- Restricted field request: deny with a reason such as
  `restricted_unlicensed`.
- Unknown field path: deny by default unless explicitly allowlisted.
- Missing local reference asset in opt-in smoke: skip or return structured
  provider-unavailable status; default tests must still pass.
- Checksum mismatch: fail closed and do not use the asset.
- Reference-base mismatch: return a structured mismatch result and do not
  silently normalize the allele.
- Out-of-bounds or unknown chromosome: return structured invalid-input errors.

## Testing Strategy

Focused tests:

- `tests/test_data_source_registry.py`
  - validates registry rows and required fields;
  - enforces `ucsc_hg38_2bit` priority;
  - enforces no approved downloads without complete metadata;
  - enforces restricted predictor rows are unlicensed.

- `tests/test_source_field_policy.py`
  - MyVariant allows only `gnomad_genome` / `gnomad_exome`;
  - MyVariant denies CADD/dbNSFP/SpliceAI/REVEL/PrimateAI-3D paths;
  - public/prod denies restricted predictors;
  - fixture/internal mode can retain warning-labeled examples.

- `tests/test_reference_genome_store.py`
  - fixture-backed sequence windows;
  - chromosome alias normalization;
  - 1-based inclusive to reader-coordinate conversion;
  - reference-base validation;
  - out-of-bounds and unknown chromosome errors;
  - metadata/checksum reporting.

Opt-in local smoke:

- `tests/test_reference_genome_store_local_hg38.py`
  - skipped unless `EAMOS_VERIFY_LOCAL_HG38_2BIT=1`;
  - verifies file exists at `app/backend/data/bio_assets/genomes/hg38.2bit`;
  - verifies MD5 `dcc3ea27079aa6dc3f9deccd7275e0f8`;
  - after a reader is approved, verifies chr1 position `68444869` reference
    base is `T`.

General checks:

```powershell
cd app/backend
python -m pytest tests/test_data_source_registry.py tests/test_source_field_policy.py tests/test_reference_genome_store.py -q
python -m ruff check app tests
python -m black --check --target-version py310 app tests
```

## Out Of Scope

- Downloading or replacing `hg38.2bit`.
- Installing a 2bit reader package without explicit approval.
- Supabase Storage, Supabase Postgres, migrations, buckets, policies, or writes.
- MyVariant adapter implementation.
- dbSNP, ClinVar, MANE, GENCODE, Mondo, HPO, ClinGen, or GenCC ingestion.
- InterVar installation or production use.
- SpliceAI, CADD, REVEL, PrimateAI-3D unlock.
- Frontend contract or UI work.
- Patient Report Pipeline (`/runs`).
- AlphaMissense work.
