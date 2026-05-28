# Local-First Source Asset Rollout

Status: Draft for review
Owner: Codex/backend
Last updated: 2026-05-29 00:14 +1000 - Codex

Source plan: `docs/local-first-data-source-strategy/plan.md`

## Purpose

This plan turns the post-`hg38.2bit` source list into executable backend
tasks. The goal is the Eamos local-first evidence backbone, not Workbench UI:
identity, transcript model, clinical disease/gene tables, ClinVar/dbSNP,
conservation, and repeat context should land before deeper Workbench wiring.

## Shared Decisions

- `hg38.2bit` proof is the dependency, not the destination.
- Do these tasks before more Workbench UI work unless the user explicitly
  redirects.
- Default implementation is fixture-first and CI-small.
- No source file download is approved until exact official source URL, source
  version, checksum plan, storage target, and terms status are recorded.
- No Supabase bucket, migration, upload, policy, import, or env mutation is
  approved by this plan.
- Native reader verification is the gate before web-server/database wiring:
  finish the approved Linux/Render-style `pysam` + `pyBigWig` proof against
  tiny fixtures before connecting local source assets to request-time backend
  providers, object-storage range reads, Supabase-backed metadata flows, or
  production report/Workbench paths. Registry/manifest tests may continue on
  Windows, but runtime source serving waits for the native proof.
- Assets larger than 10 GB stage on `C:` before any object-storage promotion.
  User also directed dbSNP/GCF and phyloP to `C:` staging on 2026-05-27;
  reviewed smaller assets can stay on `E:` after safety/space checks.
- Restricted predictors remain out of scope: SpliceAI, CADD, REVEL,
  PrimateAI-3D, restricted dbNSFP fields, InterVar/ANNOVAR/OMIM production
  use, and runtime ML scoring.

## Sources Covered

- `clinvar.vcf.gz` + `.tbi`
- `GCF_000001405.40.gz` + `.tbi` for dbSNP
- UCSC `rmsk.txt.gz` as the official source table, with `rmsk.bb` derived only
  after the bigBed/conversion proof
- `hg38.phyloP100way.bw`
- `MANE.GRCh38.v1.4.ensembl_genomic.gtf.gz`, extracting MANE Select tagged
  rows
- `gencode.v45.annotation.gtf.gz`
- `mondo.json` / `mondo.tsv`
- `phenotype.hpoa` plus official HPO annotation tables; draft `hp.gpad` path is
  unverified
- `clingen_gene_validity.csv`
- `gencc-download.csv`

## Task 8 - Source Asset Manifest And Approval Pack

### Goal

Create a code-facing readiness checklist for each Day 1 source asset.

### Context

Runtime registry rows exist in `app/backend/app/data_sources/registry.py`, but
many intentionally have `source_url = None` and `download_approved = False`.
That is correct; the missing piece is an executable checklist that says what
must be filled before download/import/enablement.

### Relevant Files

- `app/backend/app/data_sources/registry.py`
- `app/backend/tests/test_data_source_registry.py`
- `plans/data-source-registry/source-registry.seed.json`
- `plans/data-source-registry/spec.md`

### Proposed Approach

Add a manifest/checklist helper under `app/backend/app/data_sources/` that
reports, per source: URL present, version present, checksum plan present,
storage target present, license/terms status, staging rule, reader dependency,
and approval status. The helper should fail closed and be testable without
network or data files.

### Acceptance Criteria

- The named sources are enumerated and all have runtime registry rows.
- Official source URL, source-version identity, checksum plan, and terms
  status are recorded for each named source.
- Missing approval fields are reported explicitly after metadata is recorded.
- `download_approved` remains false unless separately approved.
- Supabase-targeted rows are marked backend-owned, not frontend-readable.
- `dbSNP`, phyloP, SpliceAI, CADD, and any actual asset over 10 GB are flagged
  for `C:` staging.

### Verified Metadata Notes

Task 8 source identity checks completed 2026-05-27 without downloads:

- ClinVar GRCh38 VCF points at the NCBI `vcf_GRCh38` FTP listing, current file
  pair `clinvar.vcf.gz` / `.tbi`, with upstream MD5 sidecar plan.
- dbSNP points at NCBI `latest_release/VCF/GCF_000001405.40.gz` / `.tbi`,
  not a literal `.vcf.gz` filename; it is still a `C:` staging asset.
- UCSC RepeatMasker does not expose a verified direct `rmsk.bb` source in the
  reviewed listing; use official `rmsk.txt.gz` and derive/index after reader or
  conversion proof.
- UCSC phyloP is `hg38.phyloP100way.bw`, listed at 9.2 GB with `md5sum.txt`.
  It is now a `C:` staging asset by explicit user direction because it is
  still large, even though it is below the earlier automatic 10 GB threshold.
- MANE v1.4 official GTF is `MANE.GRCh38.v1.4.ensembl_genomic.gtf.gz`; MANE
  Select rows are selected by tags, not a separate `select_ensembl.gtf.gz`
  file.
- HPO readiness starts from the official HPO annotation docs
  (`phenotype.hpoa`, `genes_to_phenotype.txt`, `phenotype_to_genes.txt`,
  `genes_to_disease.txt`); the draft `hp.gpad` path did not resolve at the
  expected OBO PURL and should not be treated as verified.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_data_source_registry.py -q
python -m ruff check app/data_sources tests/test_data_source_registry.py
python -m black --check --target-version py310 app/data_sources tests/test_data_source_registry.py
```

### Out Of Scope

Downloads, installs, Supabase writes/resources, uploads, migrations, env
mutation, provider wiring, and frontend work.

## Task 9 - Indexed Reader Compatibility Proofs

Status: IMPLEMENTED to Windows-compatible boundary 2026-05-27 03:33 +1000 -
Codex. Native Linux VCF/bigWig proof attempted again 2026-05-27 18:26 +1000:
WSL is not installed, Docker Desktop local engine returned HTTP 500 on both
contexts after start/restart attempts, and user will seek IT approval for
Docker on 2026-05-28. No production assets were downloaded or imported.
Native proof retry 2026-05-28 01:24 +1000 with user approval is still blocked:
WSL remains uninstalled, Docker engines return HTTP 500, and starting the
Docker service is not permitted from this session. Hardening added shared
`NC_` RefSeq contig canonicalization plus duplicate alias-map coverage without
native readers. Update 2026-05-29: after the WSL RAM crash guardrail, this
proof must wait for Steven's explicit Linux/Render approval and must complete
before any web-server/database wiring for local indexed source serving.

### Goal

Prove tiny-file reader behavior before production ClinVar, dbSNP, phyloP, or
RepeatMasker assets are touched.

### Context

ClinVar and dbSNP need bgzip/tabix VCF reads. phyloP needs bigWig random
access. RepeatMasker needs either direct bigBed reading or deterministic
conversion into an indexed local table.

### Relevant Files

- `app/backend/requirements.txt`
- `app/backend/app/data_sources/registry.py`
- `app/backend/app/services/indexed_sources.py`
- `app/backend/app/fixtures/data_sources/`
- `app/backend/tests/test_indexed_source_readers.py`

### Proposed Approach

After explicit package approval, select current compatible packages:
`pysam` for VCF/tabix, `pyBigWig` for bigWig, and a reviewed bigBed reader or
conversion path for RepeatMasker. Tests use generated temporary fixtures or
tiny checked-in fixtures only. Current PyPI metadata for `pysam==0.24.0` and
`pyBigWig==0.3.25` has Linux/mac wheels but no Windows wheels, so native
reader tests are expected to skip on this Windows host and run on Linux/Render
or another environment with the native modules installed.

### Acceptance Criteria

- Tiny VCF + `.tbi` fixture can be queried by contig/position/range.
- `chr1`, `1`, and `NC_000001.11` aliases normalize where relevant.
- Missing index, malformed record, unknown contig, and out-of-range query fail
  closed with structured errors.
- Tiny bigWig proof can return a conservation score.
- RepeatMasker path decision is recorded: use deterministic `rmsk.txt` to
  indexed interval-table conversion first; derive bigBed only after a separate
  conversion proof.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_indexed_source_readers.py -q
python -m ruff check app/services/indexed_sources.py tests/test_indexed_source_readers.py
python -m black --check --target-version py310 app/services/indexed_sources.py tests/test_indexed_source_readers.py
```

### Out Of Scope

Production file downloads, Supabase Storage, provider wiring, and restricted
predictors.

## Task 10 - MANE And GENCODE Transcript Model Store

Status: DONE 2026-05-27 17:52 +1000 - Codex. Fixture-first store implemented;
coordinate-map helper added 2026-05-27 22:11 +1000. No production
MANE/GENCODE downloads/imports, runtime wiring, or API contract changes.

### Goal

Build the local transcript/exon/CDS model before deeper Workbench work.

### Context

MANE and GENCODE are the bridge between local reference sequence and product
features: transcript choice, exon/CDS geometry, codon windows, gene viewer,
primer targets, CRISPR context, and variant projection.

### Relevant Files

- `app/backend/app/services/transcript_model.py`
- `app/backend/app/fixtures/transcript_models/`
- `app/backend/tests/test_transcript_model_store.py`
- Later callers: `sequence_context.py`, `gene_viewer.py`,
  `sequence_window_model.py`, `workbench_design.py`

### Proposed Approach

Implement a fixture-first `TranscriptModelStore` with RPE65 plus one non-RPE65
control. Represent gene, transcript, exon, CDS, strand, genomic span, aliases,
coding length, and source provenance. Do not download MANE/GENCODE in this
task.

### Acceptance Criteria

- Done: RPE65 resolves to MANE Select `NM_000329.3` /
  `ENST00000262340.6`.
- Done: reverse-strand exon/CDS order is validated for RPE65.
- Done: store returns transcript span, exon/CDS intervals, coding length, and
  aliases.
- Done: missing gene/transcript returns structured unavailable state.
- Done: provenance includes MANE/GENCODE source IDs, fixture path, version, and
  checksum.
- Done: coordinate-map helper identifies exon/intron state with transcript-
  oriented CDS position for exon hits and flanking exon numbers for intron hits.

### Implementation Notes

- Added `app/backend/app/services/transcript_model.py`.
- Added `app/backend/app/fixtures/transcript_models/mane_gencode_tiny.json`
  with RPE65 and CFTR fixture controls.
- Added `app/backend/tests/test_transcript_model_store.py`.
- Added `TranscriptModelStore.map_coordinate()` for deterministic local
  coordinate checks: RPE65 reverse-strand exon hits, RPE65/CFTR intron hits,
  alias normalization, and structured fail-closed mismatch/outside states.
- This is not wired into `/api/v1/viewer`, Workbench tool contracts, source
  cache, or frontend/schema mirrors yet.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_transcript_model_store.py tests/test_sequence_window_model.py -q
python -m ruff check app/services/transcript_model.py tests/test_transcript_model_store.py
python -m black --check --target-version py310 app/services/transcript_model.py tests/test_transcript_model_store.py
```

### Out Of Scope

Full MANE/GENCODE downloads, frontend mirrors, and Workbench rendering.

## Task 11 - Small Clinical Source Table Parsers

Status: DONE 2026-05-27 18:26 +1000 - Codex. Fixture-first parsers
implemented; no Supabase import/migration, production downloads, or runtime
wiring.

### Goal

Build normalized local parsers for MONDO, HPOA, ClinGen gene validity, and
GenCC before any Supabase table import.

### Context

These small datasets are report evidence, not optional decoration:
disease labels/crossrefs, phenotype associations, gene-disease validity, and
gene-disease assertions.

### Relevant Files

- `app/backend/app/services/clinical_source_tables.py`
- `app/backend/app/fixtures/source_tables/`
- `app/backend/tests/test_clinical_source_tables.py`
- Future Supabase migrations only after explicit approval.

### Proposed Approach

Add fixture parsers for representative rows from `mondo.json` or `mondo.tsv`,
`phenotype.hpoa`, `hp.gpad`, `clingen_gene_validity.csv`, and
`gencc-download.csv`. Normalize IDs, names, dates, assertions, and provenance.

### Acceptance Criteria

- Done: MONDO fixture resolves disease ID/name/cross-references without importing
  OMIM-derived files.
- Done: HPOA fixture links disease/gene context to HPO IDs and labels.
- Done: ClinGen fixture returns validity classification and source date.
- Done: GenCC fixture returns assertion, submitter, disease, gene, and source date.
- Done: parser failures are structured and do not silently drop malformed rows.

### Implementation Notes

- Added `app/backend/app/services/clinical_source_tables.py`.
- Added tiny fixtures under `app/backend/app/fixtures/source_tables/` for
  MONDO JSON, HPO term labels, HPOA disease phenotype rows, HPO gene phenotype
  rows, ClinGen gene validity CSV, and GenCC CSV.
- Added `app/backend/tests/test_clinical_source_tables.py`.
- This is not wired into Supabase, source cache, report orchestration, provider
  replacement, frontend, or schema mirrors.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_clinical_source_tables.py -q
python -m ruff check app/services/clinical_source_tables.py tests/test_clinical_source_tables.py
python -m black --check --target-version py310 app/services/clinical_source_tables.py tests/test_clinical_source_tables.py
```

### Out Of Scope

Supabase migrations/imports/policies, OMIM/Orphanet imports, frontend display
changes, and live provider wiring.

## Task 12 - ClinVar VCF Local Adapter

Status: DONE 2026-05-27 20:19 +1000 - Codex. Hardening added 2026-05-28
01:24 +1000: duplicate INFO keys, duplicate variant identities, and duplicate
VCV/Variation ID identities now fail closed instead of silently overwriting
local fixture records. No production ClinVar download/import or runtime
provider replacement.

### Goal

Implement a fixture-first local ClinVar VCF adapter for classification,
review status, condition summary, Variation ID, and HGVS aliases.

### Context

ClinVar is a Day 1 non-restricted source and should become local-first before
repeated API calls. Production file is `clinvar.vcf.gz` plus `.tbi`; first
implementation uses tiny indexed fixtures.

### Relevant Files

- `app/backend/app/services/clinvar_local.py`
- `app/backend/app/tools/clinvar.py`
- `app/backend/app/fixtures/data_sources/clinvar_tiny.vcf`
- `app/backend/tests/test_clinvar_local_adapter.py`

### Proposed Approach

Use the indexed reader abstraction from Task 9. Normalize by chrom, position,
REF, ALT, and Variation ID where present. Keep the current HTTP ClinVar tool
intact until orchestration is explicitly changed.

### Acceptance Criteria

- Tiny fixture resolves RPE65 `1-68444869-T-C` to expected ClinVar fields.
- No-hit returns honest unavailable/no-record state.
- REF/ALT mismatch and contig alias mismatch fail closed.
- Provenance includes source ID, file version, checksum/path, and record ID.
- Existing ClinVar HTTP tests still pass.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_clinvar_local_adapter.py tests/test_clinical_consensus.py tests/test_functional_evidence.py -q
python -m ruff check app/services/clinvar_local.py tests/test_clinvar_local_adapter.py
python -m black --check --target-version py310 app/services/clinvar_local.py tests/test_clinvar_local_adapter.py
```

### Out Of Scope

Production ClinVar download/upload, Supabase Storage, and lookup-provider
replacement.

## Task 13 - dbSNP GCF Local Adapter

Status: DONE 2026-05-27 21:52 +1000 - Codex. Fixture-first adapter
implemented; no production GCF download/import, resolver rewiring, Supabase
upload/import, or source-cache wiring. Hardening added 2026-05-28 01:24
+1000: duplicate INFO keys and duplicate rsID identities now fail closed
instead of silently overwriting local fixture records.

### Goal

Implement fixture-first dbSNP rsID-to-GRCh38 identity lookup.

### Context

dbSNP is a Day 1 large identity source. It is expected to exceed 10 GB and
therefore needs `C:` staging and explicit approval before production download.

### Relevant Files

- `app/backend/app/services/dbsnp_local.py`
- `app/backend/app/services/search_input_resolver.py`
- `app/backend/app/fixtures/data_sources/dbsnp_tiny.vcf`
- `app/backend/tests/test_dbsnp_local_adapter.py`

### Proposed Approach

Use the Task 9 indexed VCF reader against a tiny dbSNP-style fixture. Resolve
rsIDs to normalized GRCh38 chrom/pos/ref/alt identities. Preserve upstream
`GCF_000001405.40` naming in provenance.

### Acceptance Criteria

- Done: known rsID rows resolve to normalized genomic identity.
- Done: multi-allelic rows are represented without guessing a single allele.
- Done: unknown rsID returns structured no-record state.
- Done: `NC_000001.11`, `1`, and `chr1` aliases normalize at adapter
  boundary.
- Done: no production dbSNP file is required by default tests.

### Implementation Notes

- Added `app/backend/app/services/dbsnp_local.py`.
- Added `app/backend/app/fixtures/data_sources/dbsnp_tiny.vcf` with
  `rs1645931040`, multiallelic `rs1801133`, and `rs61752871`.
- Added `app/backend/tests/test_dbsnp_local_adapter.py`.
- This is not wired into `search_input_resolver.py`, source cache, lookup
  orchestration, frontend, or schema mirrors yet.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_dbsnp_local_adapter.py tests/test_search_input_resolver.py tests/test_variant_search_integration.py -q
python -m ruff check app/services/dbsnp_local.py tests/test_dbsnp_local_adapter.py
python -m black --check --target-version py310 app/services/dbsnp_local.py tests/test_dbsnp_local_adapter.py
```

### Out Of Scope

Production GCF download, Supabase Storage upload, rsID merge archive, and
resolver rewiring beyond fixture-proof integration.

## Task 14 - RepeatMasker `rmsk.bb` Design Context Proof

Status: DONE 2026-05-27 21:52 +1000 - Codex. Deterministic `rmsk.txt` fixture
to indexed interval-table proof implemented; no bigBed download/conversion,
frontend warnings, primer/CRISPR rewiring, or Supabase Storage.

### Goal

Prove local repeat-overlap lookup for sequence windows.

### Context

RepeatMasker warnings affect primer/CRISPR design quality, but this should be
a backend source adapter before it becomes a Workbench UI feature.

### Relevant Files

- `app/backend/app/services/repeatmasker_local.py`
- `app/backend/app/fixtures/data_sources/repeatmasker_tiny.*`
- `app/backend/tests/test_repeatmasker_local_adapter.py`

### Proposed Approach

Choose direct bigBed reading or deterministic conversion into an indexed local
fixture/table. Query by genomic interval and return repeat class/family/name
plus provenance.

### Acceptance Criteria

- Done: tiny fixture returns repeat overlaps for a window and empty list for
  no-hit.
- Done: output includes repeat name, class/family, and interval coordinates.
- Done: unknown contig and invalid intervals fail closed.
- Done: chosen conversion path is recorded as deterministic `rmsk.txt` to
  indexed interval table.

### Implementation Notes

- Added `app/backend/app/services/repeatmasker_local.py`.
- Added `app/backend/app/fixtures/data_sources/repeatmasker_tiny.rmsk.txt`.
- Added `app/backend/tests/test_repeatmasker_local_adapter.py`.
- The official source remains `rmsk.txt.gz`; derive bigBed only after a
  separate approved conversion proof.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_repeatmasker_local_adapter.py -q
python -m ruff check app/services/repeatmasker_local.py tests/test_repeatmasker_local_adapter.py
python -m black --check --target-version py310 app/services/repeatmasker_local.py tests/test_repeatmasker_local_adapter.py
```

### Out Of Scope

Full `rmsk.bb` download, frontend warnings, primer/CRISPR rewiring, and
Supabase Storage.

## Task 15 - phyloP Conservation Reader Proof

Status: PLANNED / native proof blocked on this Windows host. Hardening pass
2026-05-27 23:57 +1000 added missing-bigWig fail-closed coverage before
`pyBigWig` import and a manifest gate proving phyloP remains
reader-proof/download-approval gated. No production phyloP download/upload or
native `pyBigWig` proof was performed.
Retry 2026-05-28 01:24 +1000 with user approval remains infrastructure-blocked:
WSL is not installed, Docker engines return HTTP 500, and starting the Docker
service is not permitted from this session.

### Goal

Prove local conservation-score lookup from a bigWig-style source.

### Context

`hg38.phyloP100way.bw` is listed as active Day 1 and should stage on `C:` by
explicit user direction. Actual size and checksum still must be verified before
download. Reader compatibility comes first.

### Relevant Files

- `app/backend/app/services/conservation_local.py`
- `app/backend/app/fixtures/data_sources/phylop_tiny.bw`
- `app/backend/tests/test_conservation_local_adapter.py`

### Proposed Approach

After explicit package approval, prove `pyBigWig` or an equivalent reader with
a tiny fixture. Return per-position and window-summary conservation values
with provenance.

### Acceptance Criteria

- Tiny fixture returns a conservation score for a position and summary for a
  window.
- Missing value, unknown contig, and out-of-range queries return structured
  unavailable state.
- Output carries source ID `ucsc_phylop100way_hg38`, source version, checksum,
  and path metadata.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_conservation_local_adapter.py -q
python -m ruff check app/services/conservation_local.py tests/test_conservation_local_adapter.py
python -m black --check --target-version py310 app/services/conservation_local.py tests/test_conservation_local_adapter.py
```

### Out Of Scope

Production phyloP download/upload, frontend conservation track rendering, and
licensed predictor scoring.

## Task 16 - Source-Backed Local Evidence Orchestration

Status: PARTIAL 2026-05-27 23:00 +1000 - Codex. Internal
no-contract-change local evidence composition slice and inert runtime
configuration gate implemented; not wired into public
lookup/search/gene-viewer/workbench routes, source cache, live providers, or
frontend mirrors.

### Goal

Make report/search/gene-view backend flows prefer proven local stores while
preserving external providers as fallback or freshness checks.

### Context

Local source assets matter only when orchestration uses them. This task should
wait until Tasks 10-15 have fixture-backed adapters and tests.

### Relevant Files

- `app/backend/app/services/search_input_resolver.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/sequence_context.py`
- `app/backend/app/services/gene_viewer.py`
- `app/backend/app/services/workbench_design.py`
- `app/backend/app/services/local_evidence_orchestrator.py`
- `app/backend/tests/test_local_evidence_orchestrator.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_gene_viewer.py`
- `app/backend/tests/test_workbench_api.py`
- `app/backend/tests/test_frontend_contract.py`

### Proposed Approach

Use local transcript/reference/dbSNP/ClinVar stores first when configured,
then source cache, then live providers. Preserve fixture determinism and
no-hit honesty. Add provenance that distinguishes local file, cache, and live
provider evidence.

### Acceptance Criteria

- Partial done: an internal helper resolves RPE65 `rs1645931040` through the
  local dbSNP fixture before any live fallback path is involved.
- Partial done: ClinVar classification/accession can come from the local
  fixture without HTTP inside the internal helper.
- Partial done: sequence context can combine transcript model output plus an
  injected reference-window reader.
- Partial done: no-hit local results do not fall through to unrelated fixtures.
- Partial done: runtime local-store preference now has an explicit
  disabled-by-default configuration gate that requires per-flow opt-in and, by
  default, `use_real_apis=True`.
- Pending: public search/report/gene-view runtime flows prefer local stores by
  explicit configuration.
- Existing fixture-mode lookup behavior remains deterministic.
- Contract tests remain green before any frontend mirror work.

### Implementation Notes

- Added `LocalEvidenceOrchestrator` as an internal backend-only composition
  helper using plain dataclasses, not public Pydantic schemas.
- The helper composes dbSNP local identity, ClinVar local lookup, transcript
  coordinate mapping, RepeatMasker local intervals, and optional
  `LocalSequenceWindowBuilder` output.
- Multiallelic dbSNP rows fail closed until a requested alternate allele is
  provided.
- Added disabled-by-default settings `local_evidence_enabled`,
  `local_evidence_allowed_flows_raw`, and
  `local_evidence_require_real_apis`, plus internal
  `LocalEvidenceRuntimeGate` / `LocalEvidenceRuntimeDecision` dataclasses for
  future runtime opt-in decisions.
- The gate allows only known runtime flows (`lookup`, `search`, `gene_viewer`,
  `workbench`), supports `all`, rejects unknown configured or requested flows
  fail-closed, and remains unused by current runtime services.
- Hardening pass added 2026-05-27 23:57 +1000: malformed local alleles now fail
  closed before dbSNP/ClinVar/transcript/RepeatMasker/sequence composition, and
  runtime-gate configured flow tokens are normalized/deduped under test.
- This is deliberately not wired into `/api/v1/lookup`, `/api/v1/viewer`,
  Workbench routes, source cache, live providers, or frontend schema mirrors.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_variant_search_integration.py tests/test_sequence_context.py tests/test_gene_viewer.py tests/test_workbench_api.py tests/test_frontend_contract.py -q
python -m pytest tests/test_local_evidence_orchestrator.py tests/test_dbsnp_local_adapter.py tests/test_clinvar_local_adapter.py tests/test_transcript_model_store.py tests/test_repeatmasker_local_adapter.py -q
python -m ruff check app/services tests
python -m black --check --target-version py310 app/services tests
```

### Out Of Scope

Frontend rendering, public API contract expansion unless explicitly approved,
production downloads, Supabase writes, restricted predictors, and runtime ML
scoring.
