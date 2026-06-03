# Local-First Source Model Workflows

Status: Active backend prototype
Type: Source-model workflow / local adapter pattern
Owner: Codex backend
Added: 2026-05-27 22:11 +1000 - Codex
Last updated: 2026-06-04 02:53 +1000 - Codex

## What It Does

This entry tracks the Eamos local-first evidence backbone built around small,
deterministic source-model proofs before production ingestion. The workflow
turns large or regulated biomedical sources into narrow backend-owned adapters
that can be tested with tiny fixtures, provenance, and fail-closed states before
any download, Supabase import, frontend mirror, or source-cache rewiring.

Current first-slice adapters and workflows include:

- Reference and sequence window model over a local `hg38.2bit` reader path.
- MANE/GENCODE transcript model store with exon/CDS geometry.
- Eamos Local Coordinate Resolver over local MANE/RefSeq transcript geometry and
  local hg38 reference sequence.
- Transcript coordinate map helper for exon/intron checks.
- ClinVar local VCF adapter.
- dbSNP GCF local rsID identity adapter.
- RepeatMasker deterministic `rmsk.txt` to interval-table proof.
- Small MONDO/HPO/ClinGen/GenCC clinical source-table parsers.
- Indexed-reader proof boundaries for VCF/tabix, bigWig, and RepeatMasker.
- Internal local evidence orchestrator that composes local source-model outputs
  without changing public API contracts.
- Disabled-by-default runtime gate for future local-store preference decisions.

The coordinate resolver is the shared coordinate identity layer. Workbench
fixtures, report normalization, search-bar resolution, and batch VCF input
normalization should depend on this resolver rather than each keeping a separate
coordinate script. Existing Workbench fixtures are validation/render fixtures,
not an alternate source of truth.

## Why It Is Eamos-Original

The individual building blocks are known bioinformatics ideas: indexed VCF,
GTF/GFF-derived feature models, interval tables, and provenance records are not
unique by themselves. The project-original part is the Eamos workflow and
contract discipline:

- Fixture-first proof for every source before production ingestion.
- A runtime source registry and approval checklist before any download/import.
- Backend-only source ownership: frontend never reads raw source assets,
  Supabase source tables, object storage paths, or source-cache internals.
- Fail-closed lookup states instead of silent fallbacks or unrelated fixtures.
- Per-record provenance with source ID, version, checksum/path, and record ID
  where applicable.
- Alias normalization at adapter boundaries (`chr`, bare chromosome, RefSeq
  `NC_` aliases, VCV/Variation ID, rsID).
- Explicit separation between public Day 1 sources, local fixtures, source
  cache, live providers, and restricted predictors.
- Hydration-boundary planning for report sections so frontend summary views do
  not depend on monolithic heavy source payloads.

This should be treated as Eamos implementation IP. Avoid claiming it is globally
novel unless a separate prior-art review is performed.

## Source Of Truth

- Source rollout plan:
  `docs/local-first-data-source-strategy/source-asset-rollout.md`
- Data-source registry and readiness:
  - `app/backend/app/data_sources/registry.py`
  - `app/backend/app/data_sources/source_manifest.py`
  - `app/backend/tests/test_data_source_registry.py`
  - `app/backend/tests/test_source_asset_manifest.py`
- Indexed reader and conversion proof:
  - `app/backend/app/services/indexed_sources.py`
  - `app/backend/tests/test_indexed_source_readers.py`
- Reference and sequence-window layer:
  - `app/backend/app/services/reference_genome.py`
  - `app/backend/app/services/sequence_window_model.py`
  - `app/backend/tests/test_reference_genome_store.py`
  - `app/backend/tests/test_sequence_window_model.py`
- Eamos local coordinate resolver:
  - `app/backend/app/services/eamos_coordinate_resolver.py`
  - `app/backend/app/services/search_input_resolver.py`
  - `app/backend/scripts/validate_project_100_coordinates.py`
  - `app/backend/tests/test_eamos_coordinate_resolver.py`
- Transcript/source model layer:
  - `app/backend/app/services/transcript_model.py`
  - `app/backend/app/fixtures/transcript_models/mane_gencode_tiny.json`
  - `app/backend/tests/test_transcript_model_store.py`
- Clinical source-table parsers:
  - `app/backend/app/services/clinical_source_tables.py`
  - `app/backend/app/fixtures/source_tables/`
  - `app/backend/tests/test_clinical_source_tables.py`
- ClinVar local adapter:
  - `app/backend/app/services/clinvar_local.py`
  - `app/backend/app/fixtures/data_sources/clinvar_tiny.vcf`
  - `app/backend/tests/test_clinvar_local_adapter.py`
- dbSNP local adapter:
  - `app/backend/app/services/dbsnp_local.py`
  - `app/backend/app/fixtures/data_sources/dbsnp_tiny.vcf`
  - `app/backend/tests/test_dbsnp_local_adapter.py`
- RepeatMasker local adapter:
  - `app/backend/app/services/repeatmasker_local.py`
  - `app/backend/app/fixtures/data_sources/repeatmasker_tiny.rmsk.txt`
  - `app/backend/tests/test_repeatmasker_local_adapter.py`
- Lookup section-fetch sketch using the same provenance/freshness discipline:
  - `app/backend/app/services/lookup_sections.py`
  - `app/backend/tests/test_lookup_section_fetch_contract.py`
- Internal source-model orchestration layer:
  - `app/backend/app/services/local_evidence_orchestrator.py`
  - `app/backend/tests/test_local_evidence_orchestrator.py`
  - `app/backend/app/core/config.py`

## Current Examples

- RPE65 coordinate map:
  `NC_000001.11:g.68444869` maps to RPE65 `NM_000329.3` exon 4, CDS position
  260, using reverse-strand transcript math.
- Local evidence orchestration:
  `rs1645931040` resolves through local dbSNP to `1-68444869-T-C`, local
  ClinVar `VCV001421454`, transcript exon 4/CDS position 260, a RepeatMasker
  no-hit state, and an injectable reference-window context without HTTP or
  public schema changes.
- Local evidence runtime gate:
  local-store preference is disabled by default, requires explicit flow opt-in
  for `lookup`, `search`, `gene_viewer`, or `workbench`, and by default also
  requires `use_real_apis=True` before a runtime path can prefer local stores.
- Local evidence hardening:
  malformed local alleles fail closed before source-model composition, runtime
  gate flow tokens normalize/dedupe before decisions, ClinVar RefSeq contigs
  canonicalize to gnomAD-style chromosome IDs, and local source fixtures now
  have edge-case coverage for parser failures, provenance, alias boundaries, and
  no-public-contract behavior. ClinVar and dbSNP VCF fixture parsing also fails
  closed on duplicate INFO keys and duplicate source identities instead of
  silently overwriting local records.
- Local coordinate resolution:
  Project-100 now resolves 100/100 rows locally from MANE/RefSeq GFF plus
  `hg38.2bit` and validates 100/100 against ClinVar/SPDI and VariantValidator in
  the oracle harness. External providers are validators/debug fallbacks, not
  batch runtime coordinate dependencies.
- dbSNP:
  `rs1645931040` resolves to `1-68444869-T-C`; multiallelic `rs1801133`
  returns both allele identities instead of choosing one.
- ClinVar:
  `1-68444869-T-C` resolves to `VCV001421454` in the tiny local fixture with
  classification, review status, condition summary, and HGVS aliases.
- RepeatMasker:
  UCSC-style `rmsk.txt` rows are converted into a deterministic interval table
  for overlap/no-hit queries without downloading or deriving a production
  bigBed.

## Current Verification

Focused verification passed on 2026-05-27:

- Transcript model, sequence-window, and gene-viewer tests.
- Local evidence orchestration tests, including no-public-contract-surface
  checks.
- ClinVar, dbSNP, RepeatMasker, indexed-reader, search-resolver, and
  variant-search integration tests.
- Local-first hardening tests for reference duplicate aliases, transcript
  boundary mapping, clinical parser edge cases, ClinVar `NC_` normalization,
  ClinVar/dbSNP duplicate local identities, dbSNP/RepeatMasker fail-closed
  boundaries, phyloP proof/approval gates, and runtime-gate flow normalization.
- Ruff and Black checks for the touched backend services and tests.

Native `pysam` VCF/tabix and `pyBigWig` proofs remain Windows-host blocked and
must run in an approved Linux/Docker/WSL environment.

## Caveats

- This is not a production ingestion pipeline yet. Large source downloads,
  Supabase storage/imports, and production indexed assets still require
  explicit URL, version, checksum, storage, terms, and approval gates.
- No restricted predictors are enabled by this workflow.
- Production runtime should materialize a compact Eamos transcript projection
  index from MANE/RefSeq GFF plus checksums. Cold parsing the full RefSeq GFF is
  acceptable for validation but not the final request-path shape.
- Do not wire frontend or tool runtime behavior directly to these adapters until
  the backend API contract and source orchestration task explicitly approve it.
