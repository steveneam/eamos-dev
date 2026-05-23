# Variant Report Data Orchestration Design

Status: Draft for user review; Section 3 gnomAD expansion planned
Owner: Codex
Last updated: 2026-05-23 19:14 +1000 - Codex

## Summary

The Variant Evidence Report needs a backend data-orchestration layer where the
supercharged search bar is the first step in data extraction, not just an input
parser. The backend should interpret the user's single search string into a
canonical variant/gene/disease context, produce a section-aware evidence plan,
call the exact source adapters needed for each card and section, and return
typed section payloads. The existing resolver, call cards, gnomAD detail,
EP-VLEx publication inventory, and functional-evidence summary should remain.
This design adds a report-profile assembly layer for the header, AI summary,
disease mechanism, molecular context, computational deep dive, ACMG ledger,
therapies/trials, and provenance.

New direction added 2026-05-23: the Population Frequency call card should link
to a Section 3 gnomAD expansion panel. The click target should scroll to
Section 3 and expand the gnomAD panel. Section 2 remains disease mechanism and
inheritance only. Raw gnomAD metrics belong in the card detail/Section 3 source
panel, not repeated in the ACMG worksheet ledger.

## Context And Scope

The current backend already has important pieces:

- `EamosSearchInputResolver` resolves raw user input into source-specific
  identifiers for VariantValidator, VEP, gnomAD, SpliceAI, ClinVar, and
  literature.
- `ReportPayload.call_cards`, `population_frequency_detail`,
  `functional_evidence`, and `publications_literature` support the first
  four-card and publication slices.
- `ClinicalTrialsTool` currently returns a text summary; the layout needs
  structured rows.
- `population_frequency_detail` currently carries the selected gnomAD summary
  with AC/AN/AF, popmax, genetic ancestry groups, and overall age distribution.
  It should become the canonical source for the Section 3 gnomAD expansion,
  while staying backward-compatible for the current compact card.

The attached layout briefs require the report to be populated in this order:
header, four call cards, AI interpretation summary, disease mechanism,
molecular context, computational deep dive, ACMG worksheet, publication grid,
precision therapies/trials, and provenance.

This design covers backend architecture and source strategy only. Frontend
rendering remains Claude-owned unless the user redirects Codex. Patient Report
Pipeline (`/runs`) and AlphaMissense remain on hold.

## Goals

- Populate every requested report section from real source-backed data where
  available.
- Preserve source identity, query identity, retrieval status, version/build,
  warnings, and source URLs for audit.
- Make the Population Frequency card navigable to the Section 3 gnomAD
  expansion without requiring the frontend to infer target IDs.
- Make section data typed so frontend components do not parse raw evidence
  maps or prose.
- Prefer curated clinical sources for clinical classification and ACMG
  assertions.
- Keep general publication inventory separate from functional-study evidence.
- Keep clinical trials useful by returning gene-level rows when
  variant-specific rows do not exist, clearly labeled.
- Avoid website scraping and unsupported public-page batch usage.

## Non-Goals

- No frontend implementation in this planning slice.
- No Patient Report Pipeline (`/runs`) work.
- No AlphaMissense display or re-enable.
- No final patient-specific medical recommendation or eligibility claim.
- No automatic final ACMG classification from Eamos-computed hints.
- No broad local warehouse build in the first implementation slice.

## Constraints

- Existing clients must keep working; all contract changes are additive.
- Exact source semantics matter: gnomAD ancestry rows are genetic ancestry
  groups, not patient ancestry; ClinicalTrials.gov rows are discovery links,
  not eligibility.
- gnomAD age bins describe observed source-release sample distributions. They
  must not be presented as patient age, disease onset, penetrance, survivorship,
  or per-ancestry histograms unless the source data actually supports that
  scope.
- NCBI E-utilities need rate limiting, registered tool/email values for
  sustained use, and API-key support.
- gnomAD Browser GraphQL is useful for interactive lookup but should be cached;
  production batch use should move toward local indexed data or official
  gnomAD toolbox/download paths.
- SpliceAI target path is local/precomputed scoring with reference-build
  discipline. Public lookup is a cached demo fallback only.
- dbNSFP, CADD, REVEL, and PrimateAI-3D have licensing/version constraints;
  the backend must record the source and must not imply those scores came from
  SpliceAI.

## Proposed Design

Add a `VariantReportDataOrchestrator` service that starts from the
`SearchInputInterpretation` and builds a `ReportExtractionPlan`. The plan is an
internal/auditable map from the interpreted variant to report sections,
source-specific queries, and minimum evidence needed to populate each section.
The orchestrator then gathers source fragments and assembles one optional
`ReportPayload.report_profile` object plus the existing detailed groups.

High-level flow:

```text
search_text
  -> SearchInputInterpreter / EamosSearchInputResolver
  -> canonical variant identity + disease/gene context
  -> ReportExtractionPlan by card/section
  -> section-scoped source adapters and cache
  -> normalized evidence fragments
  -> VariantReportDataOrchestrator
  -> ReportPayload.call_cards + report_profile + existing detail groups
```

The orchestrator should not be another fixture loader. It should accept source
fragments from adapters and emit typed, provenance-rich section objects. A
section is considered populated only when its required identity level is met:
variant-level sections require a validated variant identity; gene-level
sections may use gene/disease context; trial rows may fall back to gene-level
only with explicit labels.

### Section-Aware Extraction Plan

The search-bar backend should emit these internal facts before source calls:

- `canonical_identity`: gene, transcript, cDNA, protein, rsID, GRCh38 VCF ID,
  genomic HGVS, ClinVar VCV/variation ID when known.
- `context_identity`: disease terms, inheritance hints, phenotype terms, and
  user-provided aliases.
- `source_query_bundle`: source-specific inputs for VariantValidator, VEP,
  gnomAD, SpliceAI, ClinVar, ClinGen, PubMed, LitVar2, ClinicalTrials.gov,
  HGNC, and gene-disease sources.
- `section_targets`: which report sections can be populated at variant level,
  gene level, disease level, or not yet.
- `confidence_and_gates`: whether lookup can run, whether candidate selection
  is required, and which sections must be warning-labeled because the search
  did not resolve enough detail.

This is the core point of the search bar: accurate extraction of relevant
source queries and report-section intent from one user input. It prevents a
variant-specific publication query from becoming a broad gene literature count,
prevents gene-level trials from being mislabeled as variant-specific, and
prevents computational or ACMG sections from using scores for the wrong allele.

## Source Matrix

Required MVP sources:

| Need | Primary source | Fallback/source notes |
| --- | --- | --- |
| Input normalization | Eamos resolver, VariantValidator, Ensembl VEP/MANE | Cache successful mappings; never send one raw string to every source. |
| Clinical consensus | ClinGen ERepo/VCEP when available | ClinVar aggregate classification and review status next. |
| ACMG criteria | ClinGen ERepo/CSpec source-asserted criteria | ClinVar VCV submitter details as fallback; Eamos hints stay separate. |
| Population frequency | gnomAD Browser GraphQL, currently `gnomad_r4` in code | Cache; plan a separate compatibility pass for newer gnomAD releases. |
| Splice impact | Local/precomputed Illumina SpliceAI output | Public lookup only as cached demo fallback. |
| REVEL/CADD/PrimateAI-3D | dbNSFP local file or MyVariant/dbNSFP fields where verified | CADD API for small SNV lookups; license/version recorded. |
| Publications | PubMed E-utilities plus LitVar2/ClinVar PMIDs via EP-VLEx | All variant-related PubMed rows, not only functional rows. |
| Functional studies | ClinGen, ClinVar VCV text, PubMed functional signals | Count is volume only; does not assign PS3/BS3. |
| Trials | ClinicalTrials.gov API v2 `/api/v2/studies` | Gene-level by default; variant-level only on explicit alias match. |

Additional sources the user did not list but the layout needs:

| Need | Source to add or gate |
| --- | --- |
| Gene symbols and aliases | HGNC REST API or downloaded HGNC complete set. |
| Disease/inheritance | ClinGen gene-disease validity, NCBI MedGen, Orphadata; OMIM only with an approved API/license key. |
| Gene dosage/fragility | ClinGen Dosage Sensitivity and gnomAD constraint downloads/toolbox. |
| Structural/domain context | Ensembl protein features, UniProt/AlphaFold/PDB where licensing and identifiers are clear. |
| Oncology precision therapy | CIViC for cancer molecular-profile evidence; optional and clearly oncology-scoped. |
| Pharmacogenomics/drug labels | ClinPGx/PharmGKB, FDA pharmacogenomic biomarker table/openFDA labels; optional and license-gated where needed. |
| Proprietary clinical databases | HGMD, commercial panels, or paid APIs only after explicit licensing approval. |

## Section Ownership

### Header

Source from the normalized query, selected transcript, VEP/VariantValidator
coordinates, ClinGen/ClinVar consensus, and source URLs. Bookmark/account state
is frontend/user-account state and should not block report data.

### Four Cards

Keep using `ReportPayload.call_cards`. Card logic remains backend-generated so
the UI does not derive clinical labels. Card 4 should prefer ClinGen/VCEP once
available; current ClinVar fallback remains valid.

The Population Frequency card remains compact: overall frequency state,
source/PM2-BA1-BS1 badge, and a few summary badges only. It should carry
optional navigation metadata that says the action is `scroll_and_expand`, the
target section is Section 3, and the target panel is the gnomAD expansion
panel. The frontend owns the actual scroll/focus behavior.

### Section 3 gnomAD Population Frequency Detail

Section 3 should own the expanded gnomAD detail panel. It should be assembled
from `population_frequency_detail` rather than from the ACMG ledger or disease
mechanism section.

The first backend slice should expose map/bar/table-ready data from the
existing gnomAD summary:

- Source header: dataset/release, genome build, query variant ID, sequencing
  type, source status, source URL, flags, warnings, and retrieval/version
  provenance where available.
- Metric strip: selected AF, AC/AN, homozygote count, popmax frequency and
  popmax genetic ancestry group.
- Genetic ancestry heatmap and sorted bar-chart rows from gnomAD genetic
  ancestry groups. Labels must use gnomAD genetic ancestry terminology, not
  race, ethnicity, patient ancestry, or world-population language.
- Age histograms from the source age distribution. Current gnomAD adapter data
  is overall het/hom age distribution, not per-genetic-ancestry histograms, so
  the backend must mark the scope explicitly and avoid fabricating per-group
  age arrays.
- Source/QC table rows for raw group metrics and visible warnings. Tooltips may
  help UI users, but every metric must also be present in visible text/table
  fields.

Future production-scale expansion can add an offline gnomAD ETL and indexed
local/warehouse data access layer for heavier sub-metrics. The live report API
should not query external websites or unindexed multi-gigabyte files for hover
interactions.

### AI Interpretation Summary

Generate after cards and sections are built. Default mode should be
deterministic/extractive from structured facts. Optional LLM mode can rewrite
for readability, but it may only use provided evidence fragments and must
return cited fact references. It cannot introduce new facts.

### Disease Mechanism And Inheritance

Build from gene-disease validity, disease identifiers, mode of inheritance, and
penetrance fields where source-backed. Do not synthesize penetrance percentages
unless a source provides them.

### Molecular Context And Structural Overlap

Build from VEP/MANE transcript consequence, exon/codon context, gnomAD LOEUF
or constraint source, ClinGen dosage, and optional protein-domain mappings.

### Computational Deep Dive

Use true-source predictor rows: SpliceAI for splice DS/DP, dbNSFP/MyVariant or
direct CADD for protein/pathogenicity scores, and conservation metrics where
available. AlphaMissense remains filtered while on hold.

### ACMG Ledger

Represent each criterion with one of:

- `source_asserted`: explicitly asserted by ClinGen or a trusted source record.
- `eamos_hint`: computed from source data and requiring reviewer validation.
- `not_assessed`: not available.

The final classification should prefer ClinGen VCEP, then ClinVar expert panel
or aggregate. Eamos hints are displayed as worksheet support, not a final
classification engine.

PM2, BA1, and BS1 may appear in the worksheet only as source-asserted criteria
or reviewer-facing Eamos hints with caveats. Do not duplicate raw gnomAD AF,
AC, AN, popmax, homozygote, genetic ancestry, or age-bin values in the ledger
rationale. Those raw values live in `population_frequency_detail` and the
Section 3 gnomAD panel.

### Publications

Reuse EP-VLEx as the general variant-publication inventory. Return all
variant-related PubMed publications the backend can identify, shown paginated,
with functional-only studies kept in `functional_evidence`.

### Therapies And Trials

Return structured therapy/trial rows. Query by variant aliases first, then
gene plus disease terms. If no variant-specific record is found, return
gene-level/disease-level results with explicit `match_level`.

### Provenance

Every section and row should carry source name, retrieval status, query identity,
source URL, retrieved timestamp, version/build where known, and warnings.

## Interfaces And Data

Recommended additive shape:

```python
class ReportExtractionSectionTarget(BaseModel):
    section_id: str
    match_level: Literal["variant_level", "gene_level", "disease_level", "unavailable"]
    required_sources: list[str] = Field(default_factory=list)
    query_terms: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class ReportExtractionPlan(BaseModel):
    submitted_text: str
    canonical_identity: dict[str, str] = Field(default_factory=dict)
    source_query_bundle: dict[str, list[str] | str | None] = Field(default_factory=dict)
    section_targets: list[ReportExtractionSectionTarget] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)

class SourceProvenance(BaseModel):
    source: str
    status: Literal["live", "cache", "fixture", "fallback", "missing", "error"]
    query: dict[str, str] = Field(default_factory=dict)
    source_url: str | None = None
    retrieved_at: datetime | None = None
    version: str | None = None
    warnings: list[str] = Field(default_factory=list)

class VariantReportProfile(BaseModel):
    extraction_plan: ReportExtractionPlan | None = None
    header: VariantReportHeader | None = None
    interpretation_summary: InterpretationSummary | None = None
    disease_mechanism: DiseaseMechanismSection | None = None
    molecular_context: MolecularContextSection | None = None
    computational_deep_dive: ComputationalDeepDiveSection | None = None
    acmg_worksheet: AcmgWorksheetLedger | None = None
    therapies_trials: TherapiesTrialsSection | None = None
    provenance: list[SourceProvenance] = Field(default_factory=list)

class ReportPayload(BaseModel):
    # existing fields unchanged
    report_profile: VariantReportProfile | None = None
```

Existing fields remain canonical for details already implemented:
`call_cards`, `population_frequency_detail`, `functional_evidence`,
`publications_literature`, `pubmed_articles`, `in_silico_predictions`, and
`acmg_criteria_scaffold`.

The gnomAD expansion should be additive to the existing population models. The
recommended first-slice additions are optional card navigation metadata and a
typed population-frequency report section nested under `report_profile`, while
keeping the current top-level `population_frequency_detail` as the canonical
raw/source detail group.

## Alternatives Considered

- **Frontend derives sections from `evidence.summary`.** Rejected because it
  duplicates clinical/source hierarchy logic and makes provenance brittle.
- **One giant generic list of sections.** Rejected for core evidence because
  the frontend needs typed data for cards, grids, and warnings.
- **MyVariant-only backend.** Rejected because the report needs source-native
  freshness, citations, clinical assertions, and ClinicalTrials.gov rows.
- **Local warehouse first.** Rejected for MVP speed; selected architecture can
  add local datasets behind the same adapter contracts.

## Tradeoffs

The proposed design adds a typed orchestration layer, which is more code than
directly appending text to `therapeutic_landscape` and `ai_clinical_summary`.
The gain is that each report section becomes auditable, cacheable, testable,
and frontend-ready. The largest risk is source drift, especially gnomAD
GraphQL, ClinicalTrials.gov fields, and ClinGen API shapes; adapter tests and
fixture snapshots are required.

## Cross-Cutting Concerns

- **Clinical safety:** display source-reported assertions separately from
  Eamos-computed hints.
- **Privacy:** report generation uses variant/gene inputs only; do not send
  patient identifiers to public sources.
- **Reliability:** bounded timeouts, per-source fallbacks, cache, and source
  warnings.
- **Observability:** record source status and query identity for each section.
- **Cost and licensing:** CADD, dbNSFP branches, PrimateAI-3D, PharmGKB, OMIM,
  HGMD, and commercial sources need explicit license review.

## Rollout

1. Add schema/provenance spine and fixture-backed report profile.
2. Convert ClinicalTrials.gov from text summary to structured rows.
3. Add ClinGen/ClinVar clinical-consensus and ACMG ledger source precedence.
4. Add disease/molecular/computational detail adapters behind cache.
5. Add optional live smokes per source; keep CI fixture/mock-first.
6. File a Claude handoff for TypeScript mirror and section rendering.

## Open Questions

- Should OMIM be configured as an approved licensed source now, or should the
  first slice use MedGen/Orphadata/ClinGen disease data only?
- Do we want oncology-specific sources like CIViC visible for all genes, or
  only when cancer/disease context is detected?
- Should gnomAD stay pinned to `gnomad_r4` for report stability, or should a
  separate task upgrade to the latest browser/download release after fixture
  compatibility tests?
- Do we want to land the Section 3 panel from current GraphQL/fixture fields
  first, or start with a local mini-parquet/DuckDB prototype for per-group age
  and heavier expansion metrics?

## Decision

Build a backend `VariantReportDataOrchestrator` that assembles a typed
`report_profile` from source adapters and existing report fields. Use ClinGen
first for curated clinical/ACMG assertions, ClinVar next, and Eamos-computed
criteria only as worksheet hints. Use PubMed for all variant-related
publications, not only functional literature. Use ClinicalTrials.gov at
gene/disease level when variant-level trials are absent, with explicit match
labels and no eligibility claims.

## References

- ClinVar programmatic access: https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/
- NCBI E-utilities policy and API keys: https://www.ncbi.nlm.nih.gov/books/NBK25497/
- ClinicalTrials.gov API v2: https://clinicaltrials.gov/data-api/about-api/api-migration
- Illumina SpliceAI: https://github.com/Illumina/SpliceAI
- Ensembl REST/VEP: https://rest.ensembl.org/
- MyVariant.info docs: https://docs.myvariant.info/
- gnomAD toolbox and release notes: https://gnomad.broadinstitute.org/news/2025-01-gnomad-toolbox/
- ClinGen LDH/ERepo/API overview: https://ldh.clinicalgenome.org/ldh/ui/api-docs
- ClinGen ACMG/AMP guidance: https://www.clinicalgenome.org/tools/clingen-variant-classification-guidance/
- dbNSFP: https://www.dbnsfp.org/home
- CADD API: https://cadd.gs.washington.edu/api
- HGNC REST API: https://www.genenames.org/help/rest/
- NCBI MedGen: https://www.ncbi.nlm.nih.gov/medgen/docs/overview/
- Orphadata API: https://www.orphadata.com/_orphadata-api/
- CIViC API: https://griffithlab.github.io/civic-api-docs/
- ClinPGx/PharmGKB API: https://api.pharmgkb.org/
