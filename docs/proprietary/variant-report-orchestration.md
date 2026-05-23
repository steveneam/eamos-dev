# Variant Report Data Orchestrator

Status: Active first-slice backend prototype
Type: Orchestration layer
Owner: Codex
Added: 2026-05-23 12:10 +1000 - Codex
Last updated: 2026-05-23 19:51 +1000 - Codex

## What It Does

Builds the typed `ReportPayload.report_profile` group for the Variant Evidence
Report. It turns the interpreted search input and normalized source identities
into a section-aware extraction plan, consistent provenance records, and typed
layout sections for the header, interpretation summary, disease mechanism,
molecular context, population frequency, computational deep dive, ACMG
worksheet, therapies/trials, and provenance.

## Why It Is Eamos-Original

The orchestration is Eamos-specific: it gates report sections by match level,
keeps variant-level claims separate from gene-level and disease-level fallbacks,
preserves source query identity for audit, gates fixture/fallback outputs by
current lookup identity, and assembles existing Eamos evidence groups without
making the frontend infer clinical or source hierarchy from raw tool summaries.

## Source Of Truth

- `app/backend/app/services/report_extraction_plan.py`
- `app/backend/app/services/report_provenance.py`
- `app/backend/app/services/population_frequency_section.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/services/clinical_consensus.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/tools/clingen.py`
- `app/backend/app/tools/clinvar.py`
- `app/backend/app/tools/ensembl_vep.py`
- `app/backend/app/tools/gene_disease.py`
- `app/backend/app/tools/gnomad.py`
- `app/backend/app/tools/litvar2.py`
- `app/backend/app/tools/molecular_context.py`
- `app/backend/app/tools/pubmed.py`
- `app/backend/app/tools/spliceai.py`
- `app/backend/app/tools/variant_validator.py`
- `app/backend/app/tools/computational_annotations.py`
- `app/backend/app/schemas/run.py`
- `app/backend/tests/test_clinical_consensus.py`
- `app/backend/tests/test_clinical_trials_tool.py`
- `app/backend/tests/test_gnomad_tool.py`
- `app/backend/tests/test_report_call_cards.py`
- `app/backend/tests/test_search_input_resolver.py`
- `app/backend/tests/test_tool_invariants.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_variant_report_publication_functional_integration.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_frontend_contract.py`
- `plans/variant-report-data-orchestration/`

## Caveats

- First slice is fixture/mock-first for several sections.
- ClinGen/VCEP clinical consensus is implemented as a fixture-backed/live
  source-priority slice; broader CSpec remains later.
- Disease mechanism/inheritance now has a first-slice `gene_disease` adapter
  with curated HGNC, ClinGen Gene-Disease Validity, NCBI MedGen, and Orphadata
  provenance; broader ontology ingestion and licensed OMIM API work remain
  later.
- Molecular context now has a first-slice `molecular_context` adapter with
  curated gnomAD LOEUF and ClinGen dosage provenance, plus sequence-context
  reverse-strand codon detail. Domain/hotspot mapping and full structural CNV
  overlap remain later tasks and are warning-labeled when absent.
- Computational annotation now has a first-slice
  `computational_annotations` adapter with source-labeled SpliceAI, REVEL,
  CADD, PrimateAI-3D, MetaLR, and conservation rows. Live MyVariant/dbNSFP/CADD
  integration, local/precomputed SpliceAI service implementation, and licensed
  PrimateAI-3D ingestion remain later tasks.
- Section 3 population frequency is a render-ready projection from the
  canonical `population_frequency_detail` group. It adds card navigation
  metadata and labels current gnomAD age histograms as overall release-sample
  scope, not per-genetic-ancestry or patient-age inference.
- Fixture/fallback adapters now guard their outputs by variant or gene identity
  so non-RPE65 lookups degrade to unavailable/empty sections instead of
  inheriting the single RPE65 source snapshot.
- ACMG worksheet rationales are sanitized for raw population-frequency metrics,
  and call-card PM2/BA1/BS1 badges come only from source-asserted or explicit
  Eamos-hint rows, not direct AF/AC/popmax threshold derivation.
- ClinicalTrials.gov now has a backend-only structured parser/helper first
  slice. Integration into `report_profile.therapies_trials.trial_rows` remains
  pending.
- `TherapiesTrialsSection` intentionally exposes structured trial rows only;
  therapy rows stay omitted until an approved therapy source lands.
- AlphaMissense remains on hold and is filtered from the computational deep
  dive.
