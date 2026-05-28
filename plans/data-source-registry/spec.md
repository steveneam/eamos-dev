# Data Source Registry And Licensed Predictor Spec

Status: Draft for user review
Owner: Codex/backend
Last updated: 2026-05-29 00:14 +1000 - Codex

## What

Create the backend-owned source registry and license policy that must exist
before any production data downloads, package installs, Supabase Storage moves,
or provider enablement. This spec is a planning artifact only. It does not
download assets, install packages, mutate env, write to Supabase, deploy, or
change runtime code.

The seeded registry lives in:

- `plans/data-source-registry/source-registry.seed.json`

After review, the implementation can promote the reviewed rows into a runtime
backend registry such as `app/backend/app/data_sources/registry.py` or a
validated JSON asset loaded by backend services.

## Non-Negotiable DOCX Corrections

- MyVariant is for gnomAD Day 1 lookup only. It is not a workaround for
  licensed predictor scores.
- MyVariant requests and responses must be allowlisted to gnomAD fields.
- Restricted predictor fields are filtered or locked in backend code. This
  includes SpliceAI, CADD, REVEL, and PrimateAI-3D for current planning.
- dbSNP `GCF_000001405.40.vcf.gz` plus `.tbi` is a Day 1 large asset.
- InterVar is DOCX-intended for Day 1, but commercial production requires
  license review before bundling config, installing it, or calling it.
- Any source asset whose actual download size is greater than 10 GB stages on
  the `C:` drive until moved to Supabase Storage or another approved object
  storage target.
- Large assets are never committed to Git.

## Registry Schema

Every registry row must carry these fields before download or enablement:

- `source_id`: stable backend identifier.
- `display_name`: human-readable source name.
- `priority`: implementation priority. `p0_first_asset_proof` is reserved for
  the first file/reader/storage proof that unblocks later source work.
- `tier`: object storage, repo asset, python engine, postgres table, or live
  API.
- `day1_status`: active Day 1, Pro waitlist, or blocked.
- `files_or_api`: exact file names, sidecars, or API field set.
- `upstream_source`: source organization and distribution channel.
- `source_url`: exact source URL. It may be `null` in this draft, but a row is
  not download-approved until this is filled from the reviewed source.
- `expected_size`: DOCX expected size.
- `storage_target`: Supabase Storage, Render repo, Supabase Postgres, live API,
  or package/runtime dependency.
- `temporary_staging`: whether `C:` staging is required, not required, or must
  be decided by checking actual size.
- `adapter`: planned runtime adapter or reader.
- `license_status`: current commercial-readiness status.
- `allowed_product_tiers`: public/free, Pro waitlist, internal fixture, or
  licensed-only.
- `allowed_fields`: fields the backend may request/return.
- `restricted_fields`: fields the backend must not request/return without a
  reviewed license gate.
- `checksum_required`: true for every downloaded file.
- `source_version_required`: true for every file/table/API adapter.
- `cache_policy`: source-cache/local-store behavior.
- `download_approved`: must remain false until the source URL, license, size,
  checksum plan, and storage target are reviewed.

## Exact DOCX Matrix

## Priority Decision: `hg38.2bit` First

`hg38.2bit` is the first asset proof after registry approval.

Rationale:

- It is the shared reference backbone for local sequence context, gene viewer,
  primer design, CRISPR guide discovery, Sanger alignment context, and variant
  normalization checks.
- It is much smaller than dbSNP, SpliceAI, CADD, and the other multi-GB assets,
  so it can prove the checksum, manifest, object-storage/local-cache, and
  random-access reader path with lower operational risk.
- Proving the 2bit reader and storage path first clarifies how later indexed
  assets should be staged, cached locally, and opened by the backend.
- It does not unlock restricted predictor fields or create commercial license
  exposure.

An ignored local copy already exists from the prior `isPcr` work:
`app/backend/data/bio_assets/genomes/hg38.2bit`. It is 835,393,456 bytes and
was MD5 re-verified on 2026-05-26 as
`dcc3ea27079aa6dc3f9deccd7275e0f8`, matching the local `md5sum.txt`.

The first implementation after review should inventory and re-verify that
existing asset, then add a tiny `ReferenceGenomeStore` fixture plus 2bit
reader/storage proof. A fresh or replacement download still requires explicit
approval and a filled source URL/checksum plan in the registry.

### Tier 1: Supabase Storage / Object Storage Assets

| Asset | Upstream | Size | Day 1 status | Storage target | Adapter | Staging |
| --- | --- | ---: | --- | --- | --- | --- |
| `hg38.2bit` | UCSC Genome Browser | about 800 MB | active Day 1 | Supabase Storage / object storage | `twobitreader` or `py2bit` after proof | no `C:` staging expected |
| `GCF_000001405.40.vcf.gz` + `.tbi` | NCBI dbSNP | about 15 GB | active Day 1 | Supabase Storage / object storage | `pysam` / tabix | stage on `C:` |
| `clinvar.vcf.gz` + `.tbi` | NCBI ClinVar FTP | about 60 MB | active Day 1 | Supabase Storage / object storage | `pysam` / tabix | no `C:` staging expected |
| `rmsk.bb` | RepeatMasker text / UCSC Table Browser conversion | about 100 MB | active Day 1 | Supabase Storage / object storage | bigBed reader or conversion path | no `C:` staging expected |
| `hg38.phyloP100way.bw` | UCSC PhyloP directory | about 10 GB | active Day 1 | Supabase Storage / object storage | `pyBigWig` | check actual size; stage on `C:` if greater than 10 GB |
| `spliceai_scores.masked.snv.hg38.vcf.gz` + `.tbi` | Illumina BaseSpace | about 20 GB | Pro waitlist only | Supabase Storage after license approval | `pysam` / tabix | stage on `C:` |
| `primateai3d_scores.vcf.gz` + `.tbi` | Illumina GitHub/BaseSpace | about 10 GB | Pro waitlist only | Supabase Storage after license approval | `pysam` / tabix | check actual size; stage on `C:` if greater than 10 GB |
| `cadd_scores.tsv.gz` + `.tbi` | University of Washington | about 30 GB | Pro waitlist only | Supabase Storage after license approval | `pysam` / tabix | stage on `C:` |
| `revel_scores.tsv.gz` + `.tbi` | Zenodo public repo | about 2 GB | Pro waitlist only | Supabase Storage after license approval | `pysam` / tabix | no `C:` staging expected |

dbSNP implementation notes:

- Preserve the upstream `GCF_000001405.40` naming in the registry even if a
  local alias adds `.vcf.gz`.
- Keep the `.tbi` sidecar in the same storage prefix as the VCF.
- Normalize RefSeq `NC_...` contigs to the Eamos `chr1` / `chrX` style at the
  adapter boundary.
- Consider `RsMergeArch.bcp.gz` later only if rsID merge/history becomes a
  product requirement.

### Tier 2: Render Repo / App-Bundled Assets

| Asset | Upstream | Size | Day 1 status | Storage target | Adapter | License gate |
| --- | --- | ---: | --- | --- | --- | --- |
| `MANE.GRCh38.v1.4.select_ensembl.gtf.gz` | NCBI MANE FTP | about 25 MB | active Day 1 | Render repo candidate | transcript model parser | source terms record required |
| `gencode.v45.annotation.gtf.gz` | GENCODE Project | about 60 MB | active Day 1 | Render repo candidate | transcript model parser | source terms record required |
| InterVar pipeline configuration files | GitHub InterVar repo | about 10 MB | DOCX-intended Day 1 | not production-enabled until review | optional licensed integration | InterVar, ANNOVAR, and OMIM rights required |

InterVar implementation notes:

- Do not treat InterVar as automatically production-safe.
- For Day 1 commercial-safe behavior, prefer an Eamos-owned ACMG evidence and
  worksheet engine using normalized evidence inputs.
- If InterVar compatibility is still desired, implement it as an optional
  licensed integration after InterVar, ANNOVAR, and OMIM rights are resolved.

### Tier 2.5: Python Engines

| Engine | Current status | Use | Gate |
| --- | --- | --- | --- |
| `primer3-py` | already in backend requirements | thermodynamic primer calculations | existing license risk remains tracked |
| `biopython` | already in backend requirements | DNA strings, reverse complements, CRISPR patterning, alignment | existing runtime dependency |
| `pysam` | not installed by this spec | indexed VCF/BCF/TSV access | prove Windows/Linux compatibility before adding |
| `twobitreader` / `py2bit` | not installed by this spec | random access to `hg38.2bit` | choose after compatibility proof |
| `pyBigWig` | not installed by this spec | random access to PhyloP bigWig | prove deployed runtime compatibility before adding |
| `duckdb` / `pyarrow` | not installed by this spec | optional local gnomAD/columnar slices | add only after store design is approved |

### Tier 3: Supabase Postgres Tables

| Dataset | Upstream | Size | Day 1 status | Storage target | Notes |
| --- | --- | ---: | --- | --- | --- |
| `mondo.json` / `mondo.tsv` | Mondo Disease Ontology | about 40 MB | active Day 1 | Supabase Postgres | DOCX label says OMIM and Orphanet combined, but files are Mondo; do not import OMIM-derived data without license approval |
| `phenotype.hpoa` / `hp.gpad` | Human Phenotype Ontology | about 5 MB | active Day 1 | Supabase Postgres | symptom / phenotype mapping |
| `clingen_gene_validity.csv` | ClinGen | about 2 MB | active Day 1 | Supabase Postgres | gene-disease validity |
| `gencc-download.csv` | GenCC | about 5 MB | active Day 1 | Supabase Postgres | gene-disease assertions |

Supabase posture:

- These are backend-owned source tables, not direct frontend tables.
- Prefer private schemas or backend-only access. If an exposed schema is used,
  enable RLS and avoid broad `TO authenticated` policies.
- Do not expose `source_cache` or source registry rows directly through anon or
  authenticated client access.

### Tier 4: Live APIs

| API | Day 1 status | Allowed fields | Restricted fields |
| --- | --- | --- | --- |
| MyVariant | active Day 1 for gnomAD lookup | `gnomad_genome`, `gnomad_exome` | CADD, dbNSFP restricted predictors, SpliceAI, REVEL, PrimateAI-3D |

The MyVariant adapter must request only the allowed gnomAD fields and normalize
them into the existing Eamos frequency schema. MyVariant responses must be
filtered before caching and before serialization.

## Restricted Field Guard

The backend needs a source-license policy before MyVariant, dbNSFP-like blocks,
or local predictor files are enabled for production paths.

Minimum policy behavior:

- Public/prod payloads do not include SpliceAI, CADD, REVEL, or PrimateAI-3D
  scores unless the registry row is `licensed_enabled`.
- MyVariant can only request and return the gnomAD allowlist.
- Aggregator payloads are filtered by field path before normalization.
- Existing internal fixtures may keep restricted predictor examples only under
  fixture/internal-test status with visible license warnings.
- Tests fail if restricted predictor names or source blocks appear in
  public/prod serialized payloads.

Suggested policy values:

- `public_allowed`: usable for public/commercial output after terms review.
- `commercial_allowed`: usable for commercial output with recorded terms.
- `restricted_unlicensed`: not requestable or serializable in public/prod.
- `licensed_enabled`: enabled only after commercial rights and entitlement
  policy are recorded.
- `internal_fixture_only`: usable in deterministic tests, not public/prod.

## Source Order

Recommended population-frequency provider order after review:

1. Fresh source-cache hit.
2. Local gnomAD mini-store if implemented.
3. MyVariant gnomAD-only lookup.
4. Direct gnomAD API fallback if still permitted and useful.
5. Stale source-cache response if live providers fail.

Recommended search identity order after local stores land:

1. Local parser and normalized identity.
2. Local dbSNP `GCF_000001405.40` rsID lookup.
3. Local transcript/reference stores.
4. Source cache.
5. External providers for cache miss, freshness, or validation.

## Runtime Wiring Gate

Do not wire local indexed assets into request-time web-server paths or
database/object-storage runtime flows until the native reader proof passes in
an explicitly approved Linux/Render-style environment.

The gate covers:

- `pysam` opening and querying tiny bgzip/tabix VCF fixtures for ClinVar/dbSNP
  style records.
- `pyBigWig` opening and querying a tiny bigWig fixture for phyloP-style
  conservation reads.
- Structured fail-closed behavior for missing indexes, malformed records,
  unknown contigs, out-of-range intervals, and contig alias normalization.
- Confirmation that the target runtime can install/import the selected native
  packages before they are used by backend providers.

Registry rows, manifest readiness checks, and Windows-compatible parser tests
may continue before this gate. Actual local source serving from the web server,
Supabase/object-storage range reads, startup local-cache downloads, and
production report/Workbench provider wiring wait until this gate is complete.

## Implementation Phases

### Phase 0: Registry And Policy Skeleton

- Promote the reviewed seed registry to a runtime backend module or validated
  JSON asset.
- Add schema validation for required fields, checksum/source URL gates, storage
  target, staging policy, and license state.
- Add tests that every source row has a license state and that no row is
  `download_approved` without URL, checksum plan, source version, and storage
  target.

### Phase 0A: `hg38.2bit` Reference Proof

- Implement a small `ReferenceGenomeStore` interface using a tiny 2bit fixture
  or equivalent test fixture first.
- Choose `twobitreader` or `py2bit` only after a small Windows/Linux
  compatibility proof.
- Prove checksum validation, source-version recording, random window reads, and
  adapter error behavior before using the full `hg38.2bit`.
- Test the same reader path against the existing ignored local `hg38.2bit`
  asset without moving it or mutating env.
- After explicit approval, promote, copy, or redownload `hg38.2bit` only as
  needed for the approved storage target.
- Keep dbSNP, ClinVar, MyVariant, InterVar, and restricted predictor work
  deferred until this reference proof is reviewable.

### Phase 1: Restricted Annotation Field Filter

- Add a backend allowlist/denylist layer for provider field paths and
  serialized predictor names.
- Add tests proving public/prod payloads do not leak SpliceAI, CADD, REVEL, or
  PrimateAI-3D when unlicensed.
- Keep internal fixture mode explicit and warning-labeled.

### Phase 2: MyVariant gnomAD-Only Adapter

- Use existing `httpx`.
- Request only `gnomad_genome` and `gnomad_exome`.
- Normalize into the existing population-frequency model.
- Cache by normalized GRCh38 variant identity, adapter version, field set, and
  source version where available.
- Serve stale source-cache data on provider failure.

### Phase 3: Local Identity Stores

- Add dbSNP, ClinVar, and variant-alias local adapters with tiny fixtures first.
- Use `pysam` only after a compatibility proof and explicit package approval.
- Keep no-hit/missing results honest and never fall through to unrelated
  fixtures.

### Phase 4: Local Sequence And Transcript Layer

- Add `ReferenceGenomeStore` and `TranscriptModelStore` behind small fixtures.
- Rewire `SequenceContextService`, gene viewer, primer, CRISPR, and alignment
  context setup to prefer local stores once assets are available.
- Keep VariantValidator/Ensembl as fallback or validation providers.

### Phase 5: Object-Storage Runtime Proof

- Prove random/range access for `.vcf.gz/.tbi`, `.bb`, `.bw`, and `.2bit`
  against the intended storage path with fixtures first.
- Only then test one large non-restricted file.
- If object storage is too slow for random access, use local startup download
  with checksum validation, attached disk, or object storage plus local cache.

### Phase 6: Licensed Predictor Unlock

- Only after commercial rights are obtained, update registry rows to
  `licensed_enabled`.
- Add entitlement checks and audit logging before serving restricted predictor
  scores.
- Keep public/free filters active.

## Acceptance Criteria For This Spec

- The registry seed preserves the DOCX matrix exactly enough for review.
- `hg38.2bit` is marked as `p0_first_asset_proof`, ahead of dbSNP/ClinVar and
  before restricted predictors or MyVariant adapter work.
- MyVariant is represented only as a gnomAD Day 1 API path.
- dbSNP `GCF_000001405.40` is represented as a Day 1 large asset.
- Restricted predictor assets and fields are locked behind license review.
- InterVar is represented as DOCX-intended but blocked for commercial
  production until license review.
- `C:` staging is required for assets greater than 10 GB and called out for
  dbSNP, SpliceAI, and CADD; PhyloP and PrimateAI-3D require actual-size
  checks.
- No downloads, installs, Supabase writes, env mutation, deploys, commits,
  pushes, `/runs`, or AlphaMissense work are performed by this spec pass.

## Verification

Planning artifact checks only:

```powershell
git diff --check -- plans\data-source-registry\spec.md plans\data-source-registry\source-registry.seed.json
Get-Content -Raw plans\data-source-registry\source-registry.seed.json | ConvertFrom-Json | Out-Null
```

Runtime tests are intentionally deferred until the reviewed registry is
implemented in backend code.

## Review Gate

Review this spec and registry seed before any:

- large data download;
- dependency install;
- Supabase Storage bucket/prefix creation;
- Supabase Postgres import/migration;
- MyVariant adapter enablement;
- restricted predictor field handling change;
- InterVar install or production call.
