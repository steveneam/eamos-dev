# Local-First Search, Source Storage, and Licensed Predictor Plan

Date: 2026-05-26
Status: planning note
Owner: Codex/backend

Follow-up status: `plans/data-source-registry/spec.md` and
`plans/data-source-registry/source-registry.seed.json` now contain the first
reviewable registry/spec draft. No downloads, installs, Supabase writes, env
mutation, deploys, commits, or pushes were performed.

Priority correction: after registry review, `hg38.2bit` should be the first
asset proof. It is the common reference backbone for local sequence context,
gene viewer, primer design, CRISPR guide discovery, Sanger alignment context,
and variant normalization checks. An ignored local copy already exists at
`app/backend/data/bio_assets/genomes/hg38.2bit` from prior `isPcr` work and was
MD5 re-verified on 2026-05-26 as `dcc3ea27079aa6dc3f9deccd7275e0f8`. Inventory
and prove the 2bit reader, checksum, manifest, and storage/local-cache path
before dbSNP, ClinVar, MyVariant adapter work, or any restricted predictor
file.

## Purpose

This note preserves the architecture understanding from the 2026-05-26 review of the user-provided database and licensing documents. It is intended as durable context for the next session before implementation begins.

The reviewed documents were:

- `Data and sources 1.docx`
- `Data and sources 2.docx`
- `The Total Data Footprint 1.docx`
- `The Total Data Footprint 2.docx`
- `Licensing for SpliceAI-Primate3D-REVEL-CADD.docx`
- `Licensing for SpliceAI-Primate3D-REVEL-CADD 2.docx`

## Corrected Reading

The documents do not make MyVariant the answer for licensed predictor scores.

The intended MyVariant use is gnomAD population-frequency lookup, avoiding direct reliance on the gnomAD Browser API as the first or only path for frequency data. MyVariant may expose other annotation fields, but Eamos must not treat MyVariant as a licensing workaround for restricted predictors.

Implementation rule:

- MyVariant may be used for gnomAD frequency fields.
- MyVariant responses must be allowlisted by field.
- Restricted predictor fields from MyVariant, dbNSFP, or any other aggregator must be filtered or never requested unless Eamos has a commercial license or verified commercial redistribution rights.
- Restricted predictors include SpliceAI, CADD, REVEL, and PrimateAI-3D for current planning purposes.

This is especially important because MyVariant's own documentation notes that upstream data sources can have their own restrictions. Aggregation does not remove source licensing obligations.

## Reread Corrections And Exact DOCX Blueprint

The documents define a launch blueprint that is more specific than the first draft of this plan. Preserve these source rows when turning the plan into implementation tasks.

### Tier 1: Supabase Storage / Object Storage Assets

The DOCX files put these large indexed assets in Supabase Storage, with Render reading targeted ranges through `pysam`, `twobitreader`, or `pybigwig`:

- `hg38.2bit`, UCSC Genome Browser, about 800 MB, active Day 1.
- `GCF_000001405.40.vcf.gz` plus `.tbi`, NCBI dbSNP, about 15 GB, active Day 1.
- `clinvar.vcf.gz` plus `.tbi`, NCBI ClinVar FTP, about 60 MB, active Day 1.
- `rmsk.bb`, converted from RepeatMasker text / UCSC Table Browser, about 100 MB, active Day 1.
- `hg38.phyloP100way.bw`, UCSC PhyloP directory, about 10 GB, active Day 1.
- `spliceai_scores.masked.snv.hg38.vcf.gz` plus `.tbi`, Illumina BaseSpace, about 20 GB, Pro waitlist only.
- `primateai3d_scores.vcf.gz` plus `.tbi`, Illumina GitHub/BaseSpace, about 10 GB, Pro waitlist only.
- `cadd_scores.tsv.gz` plus `.tbi`, University of Washington, about 30 GB, Pro waitlist only.
- `revel_scores.tsv.gz` plus `.tbi`, Zenodo public repo, about 2 GB, Pro waitlist only.

Execution correction: until Supabase Storage is the approved target, any asset whose actual download size is greater than 10 GB is staged on the `C:` drive. This definitely includes dbSNP, SpliceAI, and CADD based on the document sizes. PhyloP and PrimateAI-3D are boundary cases at about 10 GB, so check actual size before download and stage on `C:` if they exceed 10 GB.

### Tier 2: Render Repo / App-Bundled Assets

The DOCX files put these small files in the Render app repository:

- `MANE.GRCh38.v1.4.select_ensembl.gtf.gz`, NCBI MANE FTP, about 25 MB, active Day 1.
- `gencode.v45.annotation.gtf.gz`, GENCODE Project, about 60 MB, active Day 1.
- InterVar pipeline configuration files, GitHub InterVar repo, about 10 MB, active Day 1 in the DOCX blueprint.

Execution correction: MANE and GENCODE can be evaluated as repo-bundled assets, but InterVar cannot be treated as automatically production-safe. The WGLab README says InterVar is free for non-commercial use and requires users to obtain OMIM/ANNOVAR licenses themselves. For a commercial launch, use an Eamos-owned ACMG rules/evidence engine unless InterVar, ANNOVAR, and OMIM rights are resolved.

### Tier 2.5: Python Engines

The DOCX files call out:

- `primer3-py` for thermodynamic primer calculations.
- `biopython` for DNA strings, reverse complements, CRISPR patterning, and alignment support.
- `pysam`, `twobitreader`, and `pybigwig` as streaming/indexed-data connectors.

Execution correction: `primer3-py` and `biopython` are already in backend requirements. `pysam`, a 2bit reader, and `pyBigWig` still need compatibility proof before adding them to the runtime.

### Tier 3: Supabase Postgres Tables

The DOCX files put these relational/small datasets in Supabase Postgres:

- `mondo.json` / `mondo.tsv`, Mondo Disease Ontology, about 40 MB, active Day 1.
- `phenotype.hpoa` / `hp.gpad`, Human Phenotype Ontology, about 5 MB, active Day 1.
- `clingen_gene_validity.csv`, ClinGen, about 2 MB, active Day 1.
- `gencc-download.csv`, GenCC, about 5 MB, active Day 1.

Execution correction: the document label says "OMIM & Orphanet Combined" for the Mondo row, but the actual files listed are Mondo files. Do not import OMIM-derived files unless their license is separately approved.

### Tier 4: Live APIs

The DOCX files define MyVariant as a zero-download live public cloud API:

- Active Day 1: MyVariant for live gnomAD v4 global and subpopulation frequencies.
- Pro waitlist filter: MyVariant may expose SpliceAI, CADD, REVEL, and PrimateAI-3D fields, but the backend must strip/filter those restricted data blocks until commercial agreements are signed.

Execution correction: implement this as a MyVariant gnomAD-only adapter with explicit field allowlisting. Do not request or return restricted predictor fields for public/commercial users.

### Product Surface From The DOCX Files

The target UI/report model is:

- Master header: genomic coordinate, dbSNP ID, transcript/gene mapping, calculated ACMG verdict.
- Clinical diagnostics: ClinVar consensus, ClinGen validity, Mondo disease cross-references, HPO symptom cloud.
- Population frequency: global AF, subpopulation extremes, homozygote count from gnomAD.
- Computational predictions: Day 1 consequence/codon/conservation, plus locked Pro predictors.
- Molecular workspace: sequence viewer, CRISPR NGG mapping, RepeatMasker warning, primer design.
- Transparency block: ACMG rule verification chain.

Backend planning should keep these product surfaces in view; the architecture is not only for the report endpoint but also for Workbench and gene-view use.

### Storage Footprint From The DOCX Files

The documents estimate:

- Day 1 object-storage assets: about 26 GB.
- Fully unlocked object-storage assets: about 88-94 GB depending on which rows are counted.
- Repo-bundled Tier 2 files: about 95 MB.
- Postgres Tier 3 source files: about 52 MB raw, potentially about 150 MB after indexing.

Execution correction: treat the Supabase 100 GB object storage and egress assumptions as targets to verify, not as proven runtime facts. Before relying on direct remote range reads, test the actual file readers against the planned storage path with fixtures and then one large non-restricted file.

## Main Findings

### 1. Search Should Be Local-First

The current product direction requires search to feel immediate. External API calls should not be the first gate before the app can identify a query, render a first result, or power Workbench features.

The target search flow should be:

1. Normalize user input locally.
2. Resolve variant identity locally where possible.
3. Query local stores and source cache.
4. Render the first response from local/cache/stale evidence.
5. Use external providers only for cache miss, freshness, background enrichment, or source-specific fallback.

This model supports both report search and Workbench because gene view, primer design, CRISPR guide design, and alignment all depend on reliable variant/gene/sequence context.

### 2. Existing Backend Already Has Part Of The Skeleton

Relevant existing surfaces:

- `app/backend/app/core/db.py` has `VariantCacheRecord`.
- `app/backend/app/core/db.py` has `SourceCacheRecord`.
- `app/backend/app/repos/source_cache_repo.py` already models fresh/stale source-cache reads and upserts.
- `app/backend/app/services/lookup_service.py` already has source-cache read-through behavior.
- `app/backend/app/services/lookup_service.py` currently generalizes arbitrary source-cache persistence mainly for `gnomad`.
- `plans/source-cache-architecture.md` already describes source-cache/local evidence direction.

The next architecture step should not invent a second cache system. It should extend this existing cache and provider pattern.

### 3. MyVariant Should Become A gnomAD Provider, Not A General Annotation Provider

Current backend has a direct gnomAD provider. The document direction suggests adding a MyVariant-backed gnomAD path because it can provide gnomAD fields without depending directly on the gnomAD Browser API.

The MyVariant adapter should:

- Request only allowlisted gnomAD fields.
- Normalize `gnomad_genome` and `gnomad_exome` into the existing Eamos frequency schema.
- Preserve source version/provenance where available.
- Cache by normalized variant identity, genome build, source field set, and adapter version.
- Never return CADD, REVEL, SpliceAI, PrimateAI-3D, or other restricted predictor values through this path.

Recommended provider order:

1. Source cache fresh hit.
2. Local gnomAD mini-store if/when implemented.
3. MyVariant gnomAD-only lookup.
4. Direct gnomAD API only as fallback if still permitted and useful.
5. Stale source-cache response if live providers fail.

### 4. Licensed Predictors Must Be Backend-Gated

SpliceAI, CADD, REVEL, and PrimateAI-3D should remain unavailable in public/commercial production until Eamos has explicit commercial rights.

Frontend blur or "Pro" labels are not sufficient. The backend must not return restricted scores to unlicensed clients.

Required backend concepts:

- A source license registry that marks each source as `public_allowed`, `commercial_allowed`, `restricted_unlicensed`, or `licensed_enabled`.
- A strict response filter that removes restricted scores before serialization.
- Tests proving restricted predictors are absent from public/prod payloads.
- A separate internal fixture mode for development and tests, with clear warnings.
- A future entitlement path only after contracts are signed.

The existing computational-annotations fixture already flags license-review risk. That warning should become an enforceable policy gate before public production use.

### 5. Local Source Storage Still Matters

MyVariant helps with gnomAD lookup, but it does not solve the bigger speed and control problem.

Priority local assets:

- Reference genome: `hg38.2bit` or equivalent indexed FASTA/2bit store.
- Transcript models: MANE plus GENCODE-derived transcript/exon/CDS model.
- dbSNP: rsID to GRCh38 variant identity.
- ClinVar: local variant classification and condition summary.
- Conservation: PhyloP/other conservation tracks, subject to license review.
- RepeatMasker: local masking and design blockers for Workbench.
- Optional local gnomAD mini-store: DuckDB/Parquet or indexed slice, not full SQL mirroring.

Large data should not be mirrored into ordinary application SQL tables. SQL should hold manifests, normalized cache rows, metadata, provenance, and curated small slices. Large static datasets should stay in indexed files, object storage, attached disk, or columnar stores.

### 6. Workbench Acceleration Comes From Local Sequence Context

Workbench primer, CRISPR, and alignment code already converge on sequence context. The fastest shared improvement is to localize sequence-context resolution.

Target change:

- Add a local `ReferenceGenomeStore` for sequence windows.
- Add a local `TranscriptModelStore` for exons, CDS, transcript boundaries, and gene models.
- Rewire `SequenceContextService` to use local stores first.
- Keep VariantValidator/Ensembl as fallback or validation providers, not as the first gate.
- Reuse the same local sequence context in gene viewer, primer design, CRISPR guide discovery, and Sanger alignment.

This avoids building separate lookup paths for each Workbench feature.

## Proposed Implementation Phases

## Download And Install Inventory

No production data download or package install should happen automatically from this plan. The first implementation step should be a registry/spec that confirms source, license, checksum, storage target, and runtime adapter before any large file is downloaded.

### Python packages likely needed

Already present in `app/backend/requirements.txt`:

- `httpx` for MyVariant and existing HTTP providers.
- `primer3-py` for primer design.
- `biopython` for sequence/alignment/trace support.

Likely additions for local-first data access:

- `pysam`: indexed VCF/BCF/TSV access through bgzip/tabix files, useful for dbSNP, ClinVar, and licensed predictor files if later enabled.
- `pyBigWig`: random access to conservation tracks such as PhyloP bigWig.
- `py2bit` or `twobitreader`: random access to `hg38.2bit` reference sequence. Pick one after a small Windows/Linux compatibility check.
- `duckdb`: local query engine for compact Parquet/columnar slices, especially a gnomAD mini-store if MyVariant/source-cache is not enough.
- `pyarrow`: only if Parquet ingestion/query paths require it alongside DuckDB.

Avoid adding heavy genomics tooling unless needed:

- Do not add Hail for request-time app serving.
- Do not add VEP/ANNOVAR-style stacks to the web runtime unless separately scoped.
- Do not add Bowtie/BWA/isPcr until genome-wide Workbench specificity is explicitly in scope.

### Day-1 candidate data assets

These are candidates, not approved downloads yet:

- `hg38.2bit`: local reference genome windows for sequence context, gene view, primer design, CRISPR, and alignment.
- dbSNP GRCh38 VCF plus `.tbi`: rsID to normalized genomic identity. The DOCX file name `GCF_000001405.40.vcf.gz` corresponds to the NCBI GRCh38.p14/dbSNP `GCF_000001405.40` VCF family; the upstream files are commonly published as `GCF_000001405.40.gz` and `GCF_000001405.40.gz.tbi`. Preserve the upstream file name in the registry even if a local alias uses `.vcf.gz`.
- ClinVar VCF plus `.tbi`: local clinical classification and condition summary.
- MANE transcript GTF/GFF: canonical transcript and exon/CDS model.
- GENCODE GTF/GFF: broader transcript model, likely stored outside Git if size/deploy impact is high.
- RepeatMasker `rmsk.bb` or equivalent: local masking/off-target blockers.
- PhyloP bigWig: conservation lookup, subject to source/license confirmation.
- Mondo/HPO/ClinGen/GenCC small clinical datasets: likely SQL/imported tables or compact JSON/CSV, after license/source registry review.

### MyVariant data use

MyVariant should not require a new package. Use the existing `httpx` dependency.

The MyVariant adapter should request only allowlisted gnomAD fields:

- `gnomad_genome`
- `gnomad_exome`

Do not request or return:

- `cadd`
- restricted `dbnsfp` predictor fields
- SpliceAI fields
- REVEL fields
- PrimateAI-3D fields

### Restricted or blocked data assets

Do not download or enable these for production/commercial use until commercial rights are confirmed:

- SpliceAI precomputed scores.
- CADD scores.
- REVEL tables, unless a verified commercial route is approved.
- PrimateAI-3D scores.
- Any dbNSFP branch/field whose commercial terms do not allow the intended Eamos use.
- InterVar software/config/database files for production commercial use unless commercial InterVar rights are confirmed.
- ANNOVAR or OMIM-derived files required by InterVar unless their licenses explicitly allow the intended Eamos use.

### Storage and runtime proof required before large downloads

Before downloading multi-GB files, prove the runtime path with small fixtures:

- Can `pysam` open a local VCF/TSV plus `.tbi` fixture on Windows and Linux?
- Can `pyBigWig` read a small bigWig fixture in the deployed runtime?
- Can the chosen 2bit reader read random windows in the deployed runtime?
- If using Supabase Storage or object storage, can the app perform the needed range/random reads efficiently, or must files be downloaded to local disk first?
- What are the checksum, version, and update strategy for each asset?

Temporary local storage rule:

- Any source asset larger than 10 GB should be downloaded to the `C:` drive, not the repo/workspace drive.
- Treat this as temporary local staging until the files are moved to Supabase Storage or another approved object-storage target.
- Before each large download, check free disk space on `C:`, write to a dedicated Eamos data-staging directory, and record the file path, checksum, source URL, source version, and intended Supabase destination in the data-source registry.
- Do not commit large downloaded assets to Git.
- `GCF_000001405.40.gz` / `GCF_000001405.40.gz.tbi` should follow this rule because the dbSNP VCF is expected to be larger than 10 GB.

dbSNP implementation notes:

- Use `pysam`/tabix for lookup, not full-file request-time scans.
- Normalize RefSeq `NC_...` contig identifiers to Eamos `chr1`/`chr2`/`chrX` style identities at the adapter boundary.
- Keep the `.tbi` sidecar beside the VCF in the same staging/storage prefix.
- Consider adding `RsMergeArch.bcp.gz` later if rsID merge/history resolution becomes a product requirement.

InterVar implementation notes:

- InterVar should not be assumed safe for commercial production just because the DOCX estimated its config size at about 10 MB.
- The current WGLab InterVar README states that InterVar is free for non-commercial use, that users need licenses such as OMIM and ANNOVAR themselves, and that authors should be contacted for commercial use.
- For Day 1 commercial-safe behavior, prefer an Eamos-owned ACMG evidence/rules engine using our own normalized evidence inputs instead of bundling InterVar/ANNOVAR.
- If InterVar compatibility is still desired, treat it as a licensed optional integration: no production install, bundled config, or runtime call until InterVar, ANNOVAR, and OMIM licensing are resolved.

### Phase 0: Data Source Registry

Create a durable registry document or config table covering:

- Source name
- Data files/API
- Expected size
- License/commercial status
- Allowed product tiers
- Storage mode
- Adapter owner
- Version/provenance fields
- Update frequency
- Cache policy

This registry should explicitly mark SpliceAI, CADD, REVEL, and PrimateAI-3D as restricted until licensed.

### Phase 1: Restricted Field Guard

Implement a backend allowlist/denylist for annotation fields.

Minimum behavior:

- Public/prod payloads do not include restricted predictor scores.
- MyVariant adapter can only request and return approved fields.
- Tests fail if CADD, REVEL, SpliceAI, or PrimateAI-3D appear in public payloads.

### Phase 2: MyVariant gnomAD-Only Adapter

Add a MyVariant provider for gnomAD frequency lookup.

Requirements:

- Input: normalized GRCh38 variant identity.
- Output: existing Eamos frequency model.
- Source fields: `gnomad_genome`, `gnomad_exome` only unless separately reviewed.
- Cache: source cache with source version and adapter version.
- Fallback: stale cache on provider failure.

### Phase 3: Local Identity Stores

Add local adapters for:

- dbSNP rsID resolution.
- ClinVar variant classification.
- Variant alias graph or normalized identity table.

This makes search fast for common query forms before any external provider is called.

### Phase 4: Local Sequence And Transcript Layer

Add:

- `ReferenceGenomeStore`
- `TranscriptModelStore`
- Asset manifest with checksums and source versions.
- Small test fixtures for deterministic CI.

Then update:

- `SequenceContextService`
- `GeneViewerService`
- Workbench primer/CRISPR/alignment context setup

### Phase 5: Local/Indexed Dataset Operations

Decide where large files live and prove random access behavior.

Open question:

- Supabase Storage may work for object storage, but random-access behavior for `.vcf.gz/.tbi`, `.bb`, `.bw`, and `.2bit` must be tested before committing to it as the runtime path.

Safer options:

- Startup download to local ephemeral disk with checksum validation.
- Attached persistent disk if host supports it.
- Object storage plus local cache.
- DuckDB/Parquet for compact queryable slices.

### Phase 6: Licensed Predictor Unlock

Only after commercial rights are obtained:

- Enable licensed source registry entries.
- Add entitlement checks.
- Add audit logging for restricted predictor access.
- Ingest licensed files.
- Add provider tests for each licensed source.
- Keep public/free payload filters active.

## Immediate Next Task

The next backend planning task should be a concrete implementation spec in this order:

1. Data-source registry seeded from the exact DOCX matrix above, including size, source URL, license status, storage target, checksum field, and whether `C:` staging applies.
2. Restricted annotation field allowlist and source-license policy.
3. Public/prod tests proving restricted predictors do not leak.
4. MyVariant gnomAD-only adapter.
5. Local-first search/provider order changes.
6. Local sequence-context architecture for Workbench acceleration.

Do not download large data assets or add new runtime packages until the registry/spec step is reviewed.

Do not auto-start the parked backend queue unless the user explicitly resumes it.

## Guardrails

Do not perform these actions unless explicitly requested:

- `/runs`
- AlphaMissense work
- destructive git operations
- stash/reset/clean
- push
- commit
- deploy
- environment mutation
- Supabase writes
