# Variant Report Data Orchestration Spec

Status: Draft for user review; gene-agnostic hardening and Section 3 gnomAD expansion implemented
Owner: Codex
Last updated: 2026-05-23 19:51 +1000 - Codex

## What

Build the backend architecture that uses the supercharged search bar as a
section-aware extraction planner for the full Variant Evidence Report layout:
header, four cards, AI interpretation summary, disease mechanism, molecular
context, computational deep dive, ACMG worksheet, publication grid, precision
therapies/trials, and provenance. The search bar must not only parse input; it
must determine the canonical variant identity, source-specific queries, and
which report sections can be populated at variant, gene, or disease level. The
change is backend-first and additive. It reuses the existing resolver, call
cards, gnomAD detail, EP-VLEx publication inventory, and functional-evidence
summary.

New 2026-05-23 requirement: add a Section 3 gnomAD expansion panel linked from
the Population Frequency card. Activating the card should scroll to Section 3
and expand the gnomAD panel. Section 2 remains disease mechanism/inheritance
only. Raw gnomAD metrics must not be repeated in the ACMG worksheet ledger.

The Section 3 expansion is protected by a gene-agnostic regression gate for
the existing report-profile sections. The goal is not full rich source coverage
for every gene yet; it is to prove that non-RPE65 lookups degrade to
empty/null/warning-labelled sections and never receive RPE65 fixture facts.

## Context

Relevant current files:

- `app/backend/app/services/search_input_resolver.py` resolves source-specific
  identifiers.
- `app/backend/app/services/lookup_service.py` assembles `ReportPayload`.
- `app/backend/app/services/report_call_cards.py` builds the four cards.
- `app/backend/app/services/publication_literature.py` implements EP-VLEx.
- `app/backend/app/services/functional_evidence.py` builds the separate
  functional-study summary.
- `app/backend/app/tools/{clinvar,gnomad,spliceai,pubmed,clinical_trials}.py`
  contain current source adapters.
- `app/backend/app/schemas/run.py` owns the `ReportPayload` contract.
- `app/backend/tests/test_frontend_contract.py` is the backend/frontend canary.
- `app/backend/app/services/report_call_cards.py` currently builds the
  Population Frequency card from `population_frequency_detail`.

User-provided layout files define the report order and required data. Existing
`plans/variant-report-layout/` covered the four cards and early source
strategy, but did not fully architect every section in the attached master
layout.

The supplied gnomAD expansion notes define a progressive-disclosure direction:
initial reports should keep the card payload compact, while the detailed panel
contains genetic ancestry group frequencies, age histograms, source/QC rows,
and future on-demand data-access hooks. The first Eamos slice should use the
current gnomAD adapter and fixture data; a local indexed ETL/database path is a
future production-scale task.

## Requirements

1. `POST /api/v1/lookup` must keep the existing response fields backward
   compatible.
2. Add one optional typed report-profile group to `ReportPayload` for
   section-specific data that is not already covered by existing fields.
3. Search interpretation must produce or feed a `ReportExtractionPlan` that
   maps the interpreted input to report sections and source queries.
4. The extraction plan must record whether each section is variant-level,
   gene-level, disease-level, or unavailable.
5. A variant-level section must not be populated from a gene-only search unless
   the section is warning-labeled and explicitly degraded.
6. The existing `call_cards`, `population_frequency_detail`,
   `functional_evidence`, and `publications_literature` groups remain canonical
   for those sections.
6a. The Population Frequency card must carry backend-provided navigation
   metadata for `scroll_and_expand` to the Section 3 gnomAD panel.
6b. Section 3 must own raw/source gnomAD metrics: AF, AC, AN, homozygote count,
   popmax, genetic ancestry rows, age histograms, source status, flags, and
   warnings.
6c. Section 2 disease mechanism must contain no gnomAD frequency, age, or
   genetic ancestry detail.
7. Every new section object must carry source provenance or row-level
   provenance sufficient to audit where the data came from.
8. Header data must come from normalized input, selected transcript,
   coordinates, source consensus, and source URLs.
9. The AI interpretation summary must be generated only from structured
   evidence already fetched for the report. It may not introduce uncited facts.
10. Disease mechanism must be populated from gene-disease/disease sources and
   must not invent penetrance values.
11. Molecular context must use transcript/consequence/exon/codon/domain and
   constraint sources, not prose scraped from websites.
12. Computational detail must distinguish SpliceAI, REVEL, CADD, PrimateAI-3D,
   conservation, and legacy predictors by true source/version.
13. AlphaMissense remains hidden/on hold even if a source contains a value.
14. ACMG ledger rows must separate source-asserted criteria from Eamos
   worksheet hints.
14a. ACMG ledger rows must not duplicate raw gnomAD AF/AC/AN/popmax,
   homozygote, genetic ancestry, or age-bin metrics in criterion rationale.
15. Final clinical classification must prefer ClinGen/VCEP, then ClinVar
   expert/aggregate classification. Eamos hints must not become final
   classification.
16. Publication inventory must include all PubMed publications related to the
   variant that EP-VLEx can identify, not only functional papers.
17. Functional-study count remains separate from publication inventory count.
18. ClinicalTrials.gov rows may be gene-level or disease-level when no
   variant-specific rows exist, but must carry an explicit `match_level`.
19. No trial or therapy row may imply patient eligibility.
20. Source failures must degrade to empty/null section data plus warnings, not
   a failed report.
21. Patient Report Pipeline (`/runs`) stays untouched.
22. Current gnomAD age data must be labelled as source-release sample age
    distribution. Do not present it as patient age, disease onset, penetrance,
    survivorship, or per-ancestry age distribution unless the source model
    explicitly provides that scope.
23. Report-profile fixtures must be variant/gene guarded. Disease,
    molecular-context, computational, clinical-consensus, functional,
    publication, trial, and population sections must not copy RPE65 fixture
    facts into other genes or variants.
24. The search/output path must be gene-agnostic across a regression matrix:
    RPE65 rich fixture, RPE65 splice/functional prior examples, USH2A,
    BRCA1 indel normalization, RPGRIP1 sparse/no-hit, and CFTR ambiguity.

## Design

### Components

Add these backend components:

- `app/backend/app/services/variant_report_orchestrator.py`
  - Builds the extraction plan and report profile from search interpretation,
    normalized variant identity, evidence map, raw source payloads, source
    statuses, existing detail groups, and settings.
- `app/backend/app/services/population_frequency_section.py`
  - Recommended Section 3 builder. Converts `population_frequency_detail` into
    a section-ready view model: visual scale, genetic ancestry group rows,
    global age histogram views, source/QC rows, warnings, provenance, and the
    stable section/panel IDs used by the Population Frequency card.
- `app/backend/app/services/report_extraction_plan.py`
  - Converts `SearchInputInterpretation` / `SearchInputResolution` into
    section-scoped source queries and match-level gates.
- `app/backend/app/services/report_provenance.py`
  - Normalizes source status, query identity, URLs, timestamps, versions, and
    warnings into consistent provenance records.
- `app/backend/app/tools/clingen.py`
  - First slice adapter for ClinGen ERepo summary classifications and future
    CSpec/LDH hooks.
- `app/backend/app/tools/gene_disease.py`
  - Aggregates ClinGen gene-disease validity, MedGen/Orphadata, and optional
    OMIM if configured.
- `app/backend/app/tools/computational_annotations.py`
  - Fetches dbNSFP/MyVariant/CADD/PrimateAI-3D style predictor rows behind one
    normalized contract.
- `app/backend/app/tools/therapies_trials.py`
  - Replaces text-only trial summary with structured therapy/trial rows.

Naming is illustrative; implementation should match local patterns and may
split files differently if the test boundaries stay clear.

### Data Flow

1. Accept structured or raw `search_text` lookup request.
2. Interpret through `SearchInputInterpreter` and `EamosSearchInputResolver`.
3. Build a section-aware `ReportExtractionPlan` with source queries and
   section match levels.
4. Run current baseline tools: VEP, VariantValidator, gnomAD, SpliceAI,
   ClinVar, PubMed, LitVar2.
5. Run new report-profile adapters with source-specific identifiers:
   ClinGen, gene-disease, computational annotations, structured trials.
6. Build existing detail groups first.
7. Build `call_cards`.
8. Build `report_profile`, embedding the extraction plan or a sanitized audit
   view of it.
9. Attach Section 3 population-frequency profile data from the canonical
   `population_frequency_detail`.
10. Return response with warnings and provenance.

### Additive Schemas

Add Pydantic models in `app/backend/app/schemas/run.py` or a dedicated schema
module imported from there:

```python
SourceStatus = Literal["live", "cache", "fixture", "fallback", "missing", "error"]
ReportMatchLevel = Literal["variant_level", "gene_level", "disease_level", "source_context"]
EvidenceAssertionLevel = Literal["source_asserted", "eamos_hint", "not_assessed"]

class SourceProvenance(BaseModel):
    source: str
    status: SourceStatus
    query: dict[str, str] = Field(default_factory=dict)
    source_url: str | None = None
    retrieved_at: datetime | None = None
    version: str | None = None
    warnings: list[str] = Field(default_factory=list)

class ReportExtractionSectionTarget(BaseModel):
    section_id: Literal[
        "header",
        "population_frequency",
        "rna_splicing",
        "lab_functional",
        "clinical_consensus",
        "interpretation_summary",
        "disease_mechanism",
        "molecular_context",
        "computational_deep_dive",
        "acmg_worksheet",
        "publications",
        "therapies_trials",
        "provenance",
    ]
    match_level: Literal["variant_level", "gene_level", "disease_level", "unavailable"]
    required_sources: list[str] = Field(default_factory=list)
    query_terms: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class ReportExtractionPlan(BaseModel):
    submitted_text: str
    mode: str
    canonical_identity: dict[str, str] = Field(default_factory=dict)
    source_query_bundle: dict[str, str | list[str] | None] = Field(default_factory=dict)
    section_targets: list[ReportExtractionSectionTarget] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)

class VariantReportHeader(BaseModel):
    display_name: str
    gene: str
    transcript: str | None = None
    cdna: str | None = None
    protein_change: str | None = None
    genomic_hg38: str | None = None
    classification: str | None = None
    classification_source: str | None = None
    verification_badges: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)

class InterpretationSummary(BaseModel):
    mode: Literal["deterministic", "llm_rewrite", "unavailable"] = "deterministic"
    text: str
    fact_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class DiseaseMechanismSection(BaseModel):
    primary_condition: str | None = None
    disease_ids: list[str] = Field(default_factory=list)
    inheritance: str | None = None
    penetrance: str | None = None
    gene_disease_validity: str | None = None
    mechanism: str | None = None
    provenance: list[SourceProvenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class MolecularContextSection(BaseModel):
    chromosome: str | None = None
    strand: str | None = None
    exon: str | None = None
    codon_change: str | None = None
    protein_position: str | None = None
    domain: str | None = None
    hotspot_flag: bool | None = None
    loeuf: float | None = None
    clingen_haploinsufficiency: str | None = None
    overlapping_cnvs: list[str] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)

class ComputationalPredictorRow(BaseModel):
    name: str
    score: str | float | None = None
    threshold: str | float | None = None
    interpretation: str | None = None
    source: str
    version: str | None = None
    source_url: str | None = None
    warnings: list[str] = Field(default_factory=list)

class ComputationalDeepDiveSection(BaseModel):
    predictors: list[ComputationalPredictorRow] = Field(default_factory=list)
    spliceai_max_delta: float | None = None
    spliceai_consequence: str | None = None
    conservation: list[ComputationalPredictorRow] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)

class AcmgWorksheetCriterion(BaseModel):
    code: str
    state: Literal["met", "not_met", "not_assessed", "conflicting"]
    strength: str | None = None
    assertion_level: EvidenceAssertionLevel
    rationale: str | None = None
    source: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class AcmgWorksheetLedger(BaseModel):
    classification: str | None = None
    classification_source: str | None = None
    criteria: list[AcmgWorksheetCriterion] = Field(default_factory=list)
    synthesis: str | None = None
    disclaimer: str = "Supporting evidence, not a clinical classification."

class TrialMatch(BaseModel):
    nct_id: str
    title: str
    status: str | None = None
    phase: str | None = None
    conditions: list[str] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    match_level: ReportMatchLevel
    matched_terms: list[str] = Field(default_factory=list)
    source_url: str
    warnings: list[str] = Field(default_factory=list)

class TherapiesTrialsSection(BaseModel):
    therapy_rows: list[TherapyMatch] = Field(default_factory=list)
    trial_rows: list[TrialMatch] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)

class ReportCallInteraction(BaseModel):
    action: Literal["none", "scroll", "scroll_and_expand"] = "none"
    target_section_id: str | None = None
    target_panel_id: str | None = None

class ReportCallCard(BaseModel):
    # existing fields unchanged
    interaction: ReportCallInteraction | None = None

class PopulationFrequencyVisualScale(BaseModel):
    basis: Literal["allele_frequency", "popmax_frequency"] = "allele_frequency"
    min_value: float = 0.0
    max_value: float | None = None
    max_group_id: str | None = None
    warnings: list[str] = Field(default_factory=list)

class PopulationFrequencyVisualGroup(BaseModel):
    id: str
    label: str
    allele_frequency: float | None = None
    allele_count: int | None = None
    allele_number: int | None = None
    homozygote_count: int | None = None
    is_popmax: bool = False
    data_state: Literal["observed", "zero_observed", "not_reported", "filtered"] = "observed"
    sort_order: int | None = None
    warnings: list[str] = Field(default_factory=list)

class PopulationAgeBin(BaseModel):
    label: str
    lower_bound: float | None = None
    upper_bound: float | None = None
    count: int

class PopulationAgeHistogramView(BaseModel):
    genotype: Literal["heterozygous_alternate", "homozygous_alternate"]
    scope: Literal["overall_release_samples", "genetic_ancestry_group"] = "overall_release_samples"
    group_id: str | None = None
    bins: list[PopulationAgeBin] = Field(default_factory=list)
    n_smaller: int | None = None
    n_larger: int | None = None
    warnings: list[str] = Field(default_factory=list)

class PopulationFrequencySourceRow(BaseModel):
    group_id: str
    label: str
    allele_frequency: float | None = None
    allele_count: int | None = None
    allele_number: int | None = None
    homozygote_count: int | None = None
    is_popmax: bool = False
    warnings: list[str] = Field(default_factory=list)

class PopulationFrequencyReportSection(BaseModel):
    section_number: int = 3
    section_id: str = "section-3-population-frequency"
    panel_id: str = "gnomad-expansion"
    title: str = "gnomAD Population Frequency Detail"
    detail_ref: Literal["population_frequency_detail"] = "population_frequency_detail"
    source_status: str = "missing"
    dataset: str = ""
    genome_build: str = "GRCh38"
    variant_id: str = ""
    sequencing_type: PopulationSequencingType = "unknown"
    visual_scale: PopulationFrequencyVisualScale | None = None
    visual_groups: list[PopulationFrequencyVisualGroup] = Field(default_factory=list)
    age_histograms: list[PopulationAgeHistogramView] = Field(default_factory=list)
    source_rows: list[PopulationFrequencySourceRow] = Field(default_factory=list)
    source_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)

class VariantReportProfile(BaseModel):
    extraction_plan: ReportExtractionPlan | None = None
    header: VariantReportHeader | None = None
    interpretation_summary: InterpretationSummary | None = None
    disease_mechanism: DiseaseMechanismSection | None = None
    population_frequency: PopulationFrequencyReportSection | None = None
    molecular_context: MolecularContextSection | None = None
    computational_deep_dive: ComputationalDeepDiveSection | None = None
    acmg_worksheet: AcmgWorksheetLedger | None = None
    therapies_trials: TherapiesTrialsSection | None = None
    provenance: list[SourceProvenance] = Field(default_factory=list)
```

`TherapyMatch` should be added when the first therapy source is implemented.
For ClinicalTrials.gov-only first slice, `therapy_rows` may be omitted or
implemented as an empty list.

Add:

```python
class ReportPayload(BaseModel):
    report_profile: VariantReportProfile | None = None
```

`ReportExtractionPlan` may initially be returned for audit/debugging. If the UI
does not need it directly, it can remain backend-internal while still being
covered by tests. Either way, the plan's section targets drive which sources
are called and how rows are labeled.

`ReportCallInteraction` and `PopulationFrequencyReportSection` are backend
contract hints only; the backend does not implement browser scroll behavior.
The frontend must mirror the optional fields in both TypeScript contract files
before rendering the Section 3 panel.

### Source Rules

ClinGen:

- Use ERepo for VCEP-curated classifications and source-asserted criteria when
  records exist.
- Use CSpec later for gene/disease-specific ACMG rule specifications.
- Use LDH/Allele Registry identifiers as normalization/linking aids, not as
  independent classification.

ClinVar:

- Prefer resolved NC genomic HGVS or ClinVar variation ID.
- Use esearch/esummary for aggregate classification and review status.
- Use VCV XML for submitter comments, cited PMIDs, and explicit criteria when
  available.
- Do not assume every ClinVar submission exposes ACMG criteria.

PubMed:

- Keep EP-VLEx broad: variant aliases, transcript HGVS, protein aliases, rsID,
  genomic aliases, and gene fallback.
- Pagination remains through `/api/v1/lookup/publications`.
- Snippets are evidence snippets only; do not scrape publisher pages.

ClinicalTrials.gov:

- Query `/api/v2/studies` with `query.term`.
- Search order: exact variant aliases, gene plus disease terms, gene alone.
- Extract NCT ID, title, status, phase, interventions, conditions, and
  locations from v2 study modules.
- Label `variant_level` only when record text explicitly includes submitted
  variant aliases.

Computational predictors:

- SpliceAI score comes from SpliceAI DS/DP output.
- REVEL, CADD, PrimateAI-3D, SIFT, PolyPhen, PhyloP, and GERP should come from
  dbNSFP/MyVariant/local files or direct CADD where appropriate.
- AlphaMissense values stay hidden while the project hold is active.
- Store source, version, genome build, and license caveat where relevant.

Disease and molecular context:

- HGNC normalizes approved symbols and aliases.
- ClinGen gene-disease validity is preferred for validity level.
- MedGen and Orphadata can provide disease identifiers, inheritance, and rare
  disease relationships.
- OMIM is optional and requires approved API/license configuration.
- gnomAD LOEUF/gene constraint should record release and use current
  interpretation guidance.

gnomAD population expansion:

- Use current `population_frequency_detail` as the source of truth for raw
  frequency detail.
- The report-profile Section 3 model may duplicate data only as a render-ready
  projection; it must keep `detail_ref="population_frequency_detail"` so the
  canonical source is clear.
- Current adapter data includes overall het/hom age distribution. Do not
  fabricate per-group age histograms from overall bins.
- Production-scale expansion should use official gnomAD browser
  tables/parquet/toolbox downloads and an indexed local data layer. The report
  endpoint should not perform heavy external-file scans at request time.

### Cache And Freshness

Use the existing variant cache for source fragments where possible. Cache keys
must include:

- normalized variant identity;
- source name;
- source query identity;
- genome build;
- source dataset/release/version;
- adapter version when parsing is non-trivial.

Do not cache unresolved or ambiguous variants as successful evidence.

## Decisions

- Decision: Add one typed `report_profile` group instead of many top-level
  fields.
  - Alternatives: add many optional top-level section fields.
  - Reason: keeps `ReportPayload` manageable while giving the UI typed nested
    sections.
  - Reversible: yes.

- Decision: Treat the search bar as a section-aware evidence planner.
  - Alternatives: parse input once, then let each report section independently
    decide what to query.
  - Reason: the product goal is accurate extraction into the right cards and
    sections. A shared extraction plan prevents source calls from drifting,
    broadening, or using the wrong identity level.
  - Reversible: no for the architecture; exact schema can evolve.

- Decision: ClinGen first, ClinVar second for clinical consensus and ACMG.
  - Alternatives: ClinVar first or Eamos-generated classification.
  - Reason: expert-panel curated evidence should outrank aggregate community
    records; automated hints should not become final classifications.
  - Reversible: source priority can be configured later, but this default
    should hold.

- Decision: PubMed publication inventory is broad.
  - Alternatives: only functional studies.
  - Reason: the user clarified the publication section is all variant-related
    literature; functional studies are a separate card/detail count.
  - Reversible: filters can be added but should not change the count meaning.

- Decision: Clinical trials are gene-level by default when variant-level is
  absent.
  - Alternatives: hide trials unless variant-specific.
  - Reason: most useful trial discovery is gene/disease/intervention oriented.
  - Reversible: stricter filters can be added.

- Decision: Use local/precomputed SpliceAI as the target path.
  - Alternatives: public SpliceAI lookup for production.
  - Reason: batch/repeated report generation needs stable, build-specific,
    cacheable output.
  - Reversible: public lookup remains a fallback.

- Assumption: First implementation can use fixture/mock source rows to land the
  schema, then add live adapters in separate tasks.

## Versions

- ClinicalTrials.gov API: v2 `/api/v2/studies`, with `query.term`.
- NCBI ClinVar/PubMed: E-utilities, respecting current NCBI rate-limit policy.
- gnomAD: existing code uses `gnomad_r4`; gnomAD v4.1.1 was released on
  2026-03-30 with updated constraint metrics and VEP annotations, so a
  compatibility upgrade should be a separate tested task.
- SpliceAI: Illumina CLI/package output fields
  `DS_AG`, `DS_AL`, `DS_DG`, `DS_DL`, `DP_AG`, `DP_AL`, `DP_DG`, `DP_DL`.
- Ensembl VEP: Ensembl REST current service.
- dbNSFP: v5.3.1 was released 2026-01-01 and includes CADD, REVEL, PrimateAI,
  AlphaMissense, conservation, and other predictors; licensing must be checked
  before distribution/use.

## Invariants

- The frontend must not infer clinical labels from raw evidence summaries.
- Source-asserted criteria and Eamos hints are separate.
- General publication count and functional-study count are separate.
- gnomAD data is population source data, not patient ancestry/age data.
- Section 2 disease mechanism contains no gnomAD metrics.
- Section 3 owns expanded gnomAD detail.
- ACMG worksheet rationale contains no raw gnomAD AC/AN/AF/popmax,
  homozygote, genetic ancestry, or age-bin values.
- Non-RPE65 lookups never inherit RPE65 disease, molecular, computational,
  ACMG, gnomAD, publication, functional, or trial facts.
- Interpretation summaries cite only facts actually present for the current
  variant/gene and source status.
- Clinical trial rows are discovery rows, not eligibility recommendations.
- Missing source data returns empty/null section data plus warnings.
- `/runs` and AlphaMissense remain untouched.

## Error Behavior

- Source timeout: section returns partial data with `status=fallback` or
  `status=error` and warnings.
- Identifier unresolved: strict genomic sources return stub/missing and do not
  attach unrelated fixtures.
- ClinGen no hit: fall back to ClinVar consensus and mark classification source.
- ClinVar no hit: display unavailable consensus and keep worksheet
  not-assessed.
- Predictor unavailable: show missing row warnings; do not copy values from
  another variant.
- ClinicalTrials.gov unavailable: empty `trial_rows`, warning, and source URL
  for manual search when possible.
- LLM summary unavailable: deterministic/extractive summary or unavailable
  state; exact source data remains returned.

## Testing Strategy

- Schema tests for all new Pydantic models.
- Contract canary pending-field coverage until Claude mirrors TypeScript.
- Unit tests for source-priority decisions:
  - ClinGen beats ClinVar.
  - ClinVar fills when ClinGen missing.
  - Eamos hints never overwrite final classification.
- Fixture tests for a complete report profile with all sections populated.
- Regression tests for no-hit/mismatched fixture behavior.
- Gene-agnostic report-profile regression matrix:
  - RPE65 `c.260A>G` rich fixture happy path.
  - RPE65 `c.11+5G>A` splice/functional-prior path.
  - USH2A `c.2276G>T` different-gene ClinVar/gnomAD-capable path.
  - BRCA1 `c.5266dup` indel normalization path.
  - RPGRIP1 `c.1997C>T` sparse/no-hit path.
  - CFTR Leu441 ambiguity path, which must return suggestions/confirmation
    rather than a report-runnable payload.
- ClinicalTrials.gov parser fixture tests for v2 JSON study modules.
- Computational annotation parser tests for SpliceAI DS/DP and dbNSFP-like
  predictor rows.
- Population-frequency expansion tests for card navigation metadata, Section 3
  assembly, heatmap/bar scale, age-bin conversion, source/QC rows, unsupported
  subgroup filtering, no per-group age fabrication, and no raw gnomAD metric
  leakage into Section 2 or ACMG ledger.
- Existing focused checks:

```bash
cd app/backend
python -m pytest tests/test_frontend_contract.py tests/test_variant_search_integration.py -q
python -m pytest tests/test_publication_literature.py tests/test_functional_evidence.py -q
python -m ruff check app tests
python -m black --check --target-version py310 app tests
```

Live smoke tests should be opt-in and source-specific.

## Out Of Scope

- Frontend TypeScript mirror and rendering.
- Patient Report Pipeline (`/runs`).
- AlphaMissense re-enable.
- Clinical eligibility matching.
- Paid/proprietary source ingestion without explicit license approval.
- Full local warehouse for all public datasets in the first slice.
