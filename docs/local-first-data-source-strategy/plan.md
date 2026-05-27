# Local-First Data Source Strategy Plan

Status: Draft for review
Owner: Codex/backend
Last updated: 2026-05-26 21:37 +1000 - Codex

Source spec: `docs/local-first-data-source-strategy/spec.md`

## Shared Decisions

- Build the runtime data-source registry and license/field policy before any
  provider adapter or source download.
- Treat `hg38.2bit` as `p0_first_asset_proof`.
- Use the existing ignored local asset at
  `app/backend/data/bio_assets/genomes/hg38.2bit`; do not download, replace,
  move, upload, or commit it.
- Commit code, registry metadata, checksum expectations, and loader behavior;
  do not commit the 835 MB binary to Git. Production must receive the file
  through an approved runtime asset path.
- The website/frontend never reads `hg38.2bit` directly. The FastAPI backend
  reads it from a local filesystem path or local cache and returns small
  sequence/context responses to the web app.
- Keep the first `ReferenceGenomeStore` fixture-backed. A real 2bit reader
  package is a separate gated dependency proof.
- No Supabase writes, migrations, buckets, storage policy changes, environment
  mutation, deploys, commits, pushes, `/runs`, AlphaMissense, InterVar,
  MyVariant adapter, dbSNP, ClinVar, or restricted predictor unlocks are part
  of this plan unless explicitly approved later.

## Task 1 - Runtime Data-Source Registry

### Goal

Add a backend runtime registry that validates source metadata and preserves the
reviewed DOCX matrix in code without loading plan files at request time.

### Context

The plan seed is in `plans/data-source-registry/source-registry.seed.json`.
The backend needs a small validated registry before downloads, adapters, or
license decisions can be enforced.

### Relevant Files

- `plans/data-source-registry/source-registry.seed.json`
- `app/backend/app/data_sources/__init__.py`
- `app/backend/app/data_sources/registry.py`
- `app/backend/tests/test_data_source_registry.py`

### Proposed Approach

Create a backend `data_sources` package with typed records and a curated
runtime registry derived from the seed. Validate required fields, license
status, allowed/restricted fields, storage target, checksum/source-version
policy, `download_approved`, and priority ordering.

### Acceptance Criteria

- Registry exposes lookup by `source_id`.
- `ucsc_hg38_2bit` is present and marked `p0_first_asset_proof`.
- `ncbi_dbsnp_gcf_000001405_40` is present as Day 1 and not download-approved.
- Restricted predictor source rows are present and unlicensed.
- Validation fails for missing license status, missing storage target, or
  approved download without complete review metadata.
- Runtime code does not import from `plans/`.

### Source Reference

- `docs/local-first-data-source-strategy/spec.md` Requirements 1-4.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_data_source_registry.py -q
python -m ruff check app/data_sources tests/test_data_source_registry.py
python -m black --check --target-version py310 app/data_sources tests/test_data_source_registry.py
```

### Out Of Scope

Downloads, installs, Supabase writes, adapter enablement, and source-cache
behavior changes.

## Task 2 - License And Field Policy

### Goal

Add a pure backend policy helper that denies restricted fields by default and
allows MyVariant only for gnomAD fields.

### Context

Frontend locks or "Pro" labels are not enough. The backend must decide whether
fields can be requested, cached, normalized, or serialized before any future
adapter is enabled.

### Relevant Files

- `app/backend/app/data_sources/registry.py`
- `app/backend/app/data_sources/policy.py`
- `app/backend/tests/test_source_field_policy.py`
- Future callers: `app/backend/app/tools/computational_annotations.py`,
  `app/backend/app/services/lookup_service.py`

### Proposed Approach

Implement `SourceFieldPolicy` over the runtime registry with methods for
request/cache/serialize decisions and payload filtering. Make unknown fields
deny by default. Keep the helper pure and unit-tested; do not wire it into live
providers in this task.

### Acceptance Criteria

- MyVariant allows only `gnomad_genome` and `gnomad_exome`.
- MyVariant denies CADD, dbNSFP restricted predictors, SpliceAI, REVEL, and
  PrimateAI-3D field paths.
- Public/prod policy denies SpliceAI, CADD, REVEL, and PrimateAI-3D while their
  rows are `restricted_unlicensed`.
- Unknown field paths are denied.
- Internal fixture mode can preserve warning-labeled restricted examples
  without making them public/prod serializable.

### Source Reference

- `docs/local-first-data-source-strategy/spec.md` Requirements 5-8.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_source_field_policy.py tests/test_data_source_registry.py -q
python -m ruff check app/data_sources tests/test_source_field_policy.py
python -m black --check --target-version py310 app/data_sources tests/test_source_field_policy.py
```

### Out Of Scope

MyVariant implementation, dbNSFP parsing changes, source-cache writes, and UI
entitlement logic.

## Task 3 - Existing `hg38.2bit` Inventory Proof

### Goal

Inventory and verify the existing ignored local `hg38.2bit` asset without
moving, replacing, downloading, uploading, or committing it.

### Context

The asset already exists at
`app/backend/data/bio_assets/genomes/hg38.2bit`. It was re-verified read-only:
835,393,456 bytes, MD5 `dcc3ea27079aa6dc3f9deccd7275e0f8`.

### Relevant Files

- `app/backend/app/data_sources/registry.py`
- `app/backend/tests/test_data_source_registry.py`
- `app/backend/tests/test_local_hg38_inventory.py`
- `app/backend/data/bio_assets/genomes/hg38.2bit` (read-only, ignored)
- `app/backend/data/bio_assets/genomes/md5sum.txt` (read-only, ignored)

### Proposed Approach

Add a read-only inventory helper or test utility that checks local path, size,
MD5, and registry metadata. The default test should skip cleanly if the ignored
asset is absent; a focused local verification can run where the asset exists.

### Acceptance Criteria

- Registry records the known UCSC URL, local path, size, and MD5.
- Local inventory test verifies size and MD5 when the file exists.
- Test skips cleanly when the ignored local asset is missing.
- No file write, move, download, upload, or environment mutation occurs.

### Source Reference

- `docs/local-first-data-source-strategy/spec.md` Requirements 9-10 and
  Testing Strategy opt-in local smoke.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_local_hg38_inventory.py tests/test_data_source_registry.py -q
```

### Out Of Scope

Reading sequence windows from the 2bit file, installing a 2bit reader, or
promoting the file to Supabase Storage.

## Task 4 - Fixture-Backed `ReferenceGenomeStore`

### Goal

Add the stable local reference genome interface using tiny deterministic
fixtures, without requiring the full `hg38.2bit` or a new package.

### Context

Workbench, gene viewer, primer, CRISPR, alignment, and variant normalization
need a shared reference-window abstraction. The interface should be tested
before a real 2bit reader is selected.

### Relevant Files

- `app/backend/app/services/reference_genome.py`
- `app/backend/app/fixtures/reference_genome/`
- `app/backend/tests/test_reference_genome_store.py`
- Later integration target: `app/backend/app/services/sequence_context.py`

### Proposed Approach

Implement a fixture-backed store with metadata, chromosome alias normalization,
1-based inclusive caller coordinates, sequence-window reads, and reference-base
validation. Keep the data tiny and checked into fixtures.

### Acceptance Criteria

- `get_sequence("1", start, end)` returns deterministic fixture windows.
- Aliases such as `1`, `chr1`, and configured `NC_...` names resolve when
  present in fixture metadata.
- Out-of-bounds windows and unknown chromosomes return structured errors.
- `validate_reference_base` succeeds and fails explicitly.
- Metadata reports source ID, source URL, checksum, path, and source version.
- Default tests do not require network, Supabase, or full `hg38.2bit`.

### Source Reference

- `docs/local-first-data-source-strategy/spec.md` Requirements 11-13.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_reference_genome_store.py -q
python -m ruff check app/services/reference_genome.py tests/test_reference_genome_store.py
python -m black --check --target-version py310 app/services/reference_genome.py tests/test_reference_genome_store.py
```

### Out Of Scope

Installing or selecting a real 2bit reader, reading the existing local
`hg38.2bit`, or rewiring `SequenceContextService`.

## Task 5 - Opt-In Local `hg38.2bit` Smoke Scaffold

### Goal

Prepare an opt-in smoke test that can verify the existing local asset and later
exercise a real 2bit reader, while staying skipped by default.

### Context

The full local asset exists, but dependency selection for a 2bit reader is a
separate approval. This task should create the smoke shape without authorizing
package installation.

### Relevant Files

- `app/backend/tests/test_reference_genome_store_local_hg38.py`
- `app/backend/app/data_sources/registry.py`
- `app/backend/app/services/reference_genome.py`

### Proposed Approach

Add a skipped-by-default test controlled by `EAMOS_VERIFY_LOCAL_HG38_2BIT=1`.
Initially it verifies file presence, size, and MD5. Leave the real sequence
read assertion marked pending/skipped until a reader package is approved.

### Acceptance Criteria

- Default pytest skips the local smoke.
- With `EAMOS_VERIFY_LOCAL_HG38_2BIT=1`, the test verifies path, size, and MD5.
- The future RPE65 reference-base check is documented:
  GRCh38 `1:68444869` should be `T`.
- The task installs no dependency and reads no sequence window unless a reader
  is already available through approved code.

### Source Reference

- `docs/local-first-data-source-strategy/spec.md` Testing Strategy.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_reference_genome_store_local_hg38.py -q
$env:EAMOS_VERIFY_LOCAL_HG38_2BIT = "1"
python -m pytest tests/test_reference_genome_store_local_hg38.py -q
Remove-Item Env:EAMOS_VERIFY_LOCAL_HG38_2BIT
```

### Out Of Scope

Reader package installation, Supabase Storage, and sequence-window reads from
the full asset unless already supported.

## Task 6 - Production `hg38.2bit` Runtime Asset Path

### Goal

Define and test how the deployed backend will access `hg38.2bit` quickly
without storing the binary in Git.

### Context

The file is only about 835 MB, so it is manageable as a runtime asset, but it
is still too large for ordinary Git/repo history. The backend needs a stable
local path for fast random reads; object storage can be the source of truth
only if the backend caches or mounts the file in a reader-compatible way.

### Relevant Files

- `app/backend/app/data_sources/registry.py`
- `app/backend/app/core/config.py`
- `app/backend/app/services/reference_genome.py`
- Future deployment docs or scripts under an approved path

### Proposed Approach

Record the production asset delivery mode before enabling real sequence reads.
Supported modes should be explicit:

- Local dev: existing ignored path under `app/backend/data/bio_assets/genomes/`.
- Hosted preferred: object storage source plus backend startup/local-cache
  materialization with checksum validation.
- Hosted alternative: persistent disk or mounted volume with checksum
  validation.

Do not implement Supabase upload, bucket creation, env mutation, or deployment
changes in this task unless the user explicitly approves that operation. The
plan should still make the runtime requirement clear: the backend reader needs
a local filesystem path or compatible mounted object.

### Acceptance Criteria

- Registry/config can describe where `hg38.2bit` should be found in local dev
  and hosted modes.
- Backend startup/health design can report missing asset, bad checksum, and
  ready states without crashing unrelated fixture mode.
- No Git-tracked binary is introduced.
- No Supabase write, bucket creation, env mutation, or deploy occurs without
  explicit approval.
- The chosen runtime path supports fast backend sequence reads before dbSNP,
  ClinVar, or MyVariant work depends on it.

### Source Reference

- User feedback on 2026-05-26: production tools need `hg38.2bit` highlighted
  and available for fast sequence analysis, while the file is not very large.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_data_source_registry.py tests/test_local_hg38_inventory.py -q
```

### Out Of Scope

Actual upload to Supabase Storage, deployment mutation, env mutation, or
persistent-disk provisioning unless separately approved.

## Task 7 - Gated 2bit Reader Compatibility Proof

### Goal

After explicit approval, choose and prove a real 2bit reader against the
fixture store and the existing local `hg38.2bit`.

### Context

This task is intentionally separate because it may require installing
`twobitreader`, `py2bit`, or another maintained package.

### Relevant Files

- `app/backend/requirements.txt`
- `app/backend/app/services/reference_genome.py`
- `app/backend/tests/test_reference_genome_store.py`
- `app/backend/tests/test_reference_genome_store_local_hg38.py`

### Proposed Approach

Check current package status from official package metadata, select the
smallest maintained reader that works on Windows and the deployed runtime, add
it to requirements only after approval, and implement a real reader adapter.

### Acceptance Criteria

- Reader dependency choice is recorded with version and rationale.
- Fixture tests still pass.
- Opt-in local smoke reads GRCh38 `1:68444869` and verifies reference base `T`.
- Missing file, checksum mismatch, unknown chromosome, and out-of-bounds reads
  fail closed.

### Source Reference

- `docs/local-first-data-source-strategy/spec.md` Versions and
  `ReferenceGenomeStore` design.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_reference_genome_store.py tests/test_reference_genome_store_local_hg38.py -q
python -m ruff check app/services/reference_genome.py tests/test_reference_genome_store*.py
python -m black --check --target-version py310 app/services/reference_genome.py tests/test_reference_genome_store*.py
```

### Out Of Scope

This task does not enable dbSNP, ClinVar, MyVariant, Supabase Storage, or
restricted predictors.

## Post-Reference Source Asset Rollout

The concrete post-`hg38.2bit` source-asset task plan now lives in
`docs/local-first-data-source-strategy/source-asset-rollout.md`.

That plan makes the next source work explicit before more Workbench UI:
source manifest/approval checklist, indexed reader proofs, MANE/GENCODE
transcript model store, MONDO/HPOA/ClinGen/GenCC local parsers, ClinVar VCF
local adapter, dbSNP/GCF local adapter, RepeatMasker context proof, phyloP
reader proof, and final source-backed orchestration.

## Deferred Follow-Up Tracks

These are not part of the first implementation unless separately approved:

- Supabase Storage proof for static assets after reader behavior is known and
  after the source-asset rollout records bucket/prefix/policy requirements.
- Supabase Postgres schema/import plan for Mondo, HPO, ClinGen, and GenCC
  after local parser behavior is verified.
- MyVariant gnomAD-only adapter after policy gates are wired.
- Production downloads/imports for dbSNP, ClinVar, MANE, GENCODE,
  RepeatMasker, phyloP, MONDO, HPOA, ClinGen, and GenCC after the
  source-asset rollout tasks prove fixtures/readers and approval fields.
- InterVar compatibility only after InterVar, ANNOVAR, and OMIM rights review.
- SpliceAI, CADD, REVEL, and PrimateAI-3D only after commercial license unlock,
  entitlement checks, and audit logging.
- Genomic LLM / Nucleotide Transformer scoring only after the local reference
  window and variant-window builder are proven. The notebooks at
  `C:\Users\seamegdool\Desktop\Claude code and website tips\EAMOS Web Tool\variant-search-engine\Sequence alignment\genomicLLM_Part1.ipynb`
  and
  `C:\Users\seamegdool\Desktop\Claude code and website tips\EAMOS Web Tool\variant-search-engine\Sequence alignment\genomicLLM_Part2.ipynb`
  are relevant as a future AI sequence-prior layer: Part 1 explains DNA
  k-mer/tokenisation and embeddings; Part 2 is directly relevant for
  zero-shot reference-vs-alternate scoring and per-token disruption profiles.
  Do not install `torch`/`transformers`, download the
  `InstaDeepAI/nucleotide-transformer-500m-human-ref` model, or add runtime ML
  scoring until separately approved. First prove deterministic GRCh38 windows,
  REF allele validation, ALT-applied windows, flank/token-map conventions, and
  provenance fields for model/tokenizer/window size. Treat any future score as
  research/triage evidence, not ACMG classification.
