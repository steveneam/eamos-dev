# Variant Evidence Report Layout Data Spec

Status: Draft for user review
Owner: Codex
Last updated: 2026-05-20 19:25 +1000

## What

Add backend data contracts and retrieval responsibilities for the minimum
Variant Evidence Report layout: top header, four-card evidence grid, AI
summary, disease mechanism, molecular context, computational deep dive, ACMG
worksheet, publication grids, therapies, clinical trials, and provenance. This
spec is backend-first and additive; frontend implementation remains Claude's
lane unless explicitly redirected.

## Context

The current `/report` UI already renders useful pieces, but the data is not
organized around the requested four-card evidence grid and section order.

Current pieces already present:

- Header: `VariantHeader.tsx`
- In-silico grid: `InSilicoGrid.tsx`
- ACMG scaffold: `AcmgCriteriaFold.tsx`
- Associated conditions: `AssociatedConditions.tsx`
- Publications callout and PubMed list: `PublicationsCallout.tsx`,
  `PubMedSection.tsx`
- Backend EP-VLEx and functional evidence: `publications_literature`,
  `functional_evidence`

Missing or incomplete:

- A generic call-card contract for all four above-the-fold cards.
- Dynamic population frequency card output from gnomAD.
- Dynamic clinical-consensus card output from ClinGen/ClinVar source hierarchy.
- A dedicated functional call-card display object that keeps category separate
  from study count. This is now partly implemented in `functional_evidence`.
- A gene-level ClinicalTrials.gov retrieval shape.
- Section payloads that allow Claude to render the requested layout without
  scraping `evidence` rows directly.

## Requirements

1. The Variant Evidence Report payload must expose four call cards:
   Population Frequency, Computational, Lab & Functional, Clinical Consensus.
2. Each call card must provide a primary label and support badges. Richer data
   must remain in detail fields below the grid.
3. Card 3 must display source-reported functional categorization separately
   from the unique functional-study count.
4. Functional-study count must not determine or upgrade PS3/BS3 category.
5. ClinicalTrials.gov results may be gene-level. They must be labeled as
   gene-level unless the trial record explicitly names the queried variant.
6. The backend must preserve existing `ReportPayload` fields and add new fields
   additively.
7. The frontend contract canary must allow pending mirrors only when the
   cross-agent request states exactly what Claude must mirror.
8. AlphaMissense and Patient Report Pipeline (`/runs`) remain out of scope.
9. MVP annotation retrieval should use MyVariant.info as an aggregator/fallback
   only where the returned field is actually present and source-labeled.
10. SpliceAI should be implemented as a local/precomputed service for repeated
   report generation; public lookup may be used only as a cached demo fallback.
11. Population Frequency must use source gnomAD Browser GraphQL live data for
    interactive single-variant lookups when genomic coordinates are available.
12. gnomAD ancestry rows must be labeled as genetic ancestry groups, and age
    histograms must be displayed as source population detail, not patient-age
    or patient-ancestry inference.

## Design

### MVP Retrieval Strategy

Do not scrape source websites. Use APIs, local tools, or our own indexed
database.

Use MyVariant.info for fast MVP annotation fields such as gnomAD, ClinVar,
dbSNP, and dbNSFP-derived REVEL when a live response confirms the field exists.
Treat fields from the local My Variant script as assumptions until verified
against a real MyVariant response and metadata.

Use source gnomAD Browser GraphQL for the Population Frequency card. The
official browser API at `https://gnomad.broadinstitute.org/api` exposes
`variant(variantId, dataset)` and can return joint/exome/genome AC, AN, AF,
homozygotes, `faf95`, genetic ancestry group rows, and available age
histograms. The GraphQL resource is public, rate-limited, and its schema is
documented as subject to change, so cache successful responses, keep fixture
fallbacks, and prefer local indexed release data or the official gnomAD toolbox
path for batch/production-scale reporting.

Use direct/source-native integrations where provenance and freshness matter:

- EP-VLEx publication rows/snippets from PubMed/PMC-style APIs.
- Functional evidence from ClinGen/ClinVar/PubMed extractors.
- Source-reported ClinGen/ClinVar assertions.
- ClinicalTrials.gov v2 records.

For SpliceAI, the target architecture is local/precomputed:

- Normalize the variant to a build-specific VCF record.
- Run/pin Illumina SpliceAI with the matching reference FASTA and annotation
  build, or query our own database of precomputed SpliceAI scores.
- Parse `DS_AG`, `DS_AL`, `DS_DG`, `DS_DL`, `DP_AG`, `DP_AL`, `DP_DG`, and
  `DP_DL`.
- Cache/store the result with genome build, SpliceAI version, annotation build,
  and score mode.
- Keep the current public lookup path only as a rate-limited, cached fallback
  for interactive demo lookups.

### Additive Payload Groups

Add:

```python
class ReportCallBadge(BaseModel):
    text: str
    kind: Literal["acmg", "metric", "source", "warning", "neutral"]

class ReportCallCard(BaseModel):
    card_id: Literal[
        "population_frequency",
        "computational",
        "lab_functional",
        "clinical_consensus",
    ]
    title: str
    primary_label: str
    support_badges: list[ReportCallBadge] = Field(default_factory=list)
    ui_color_theme: str
    source_status: str
    provenance: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class VariantReportCallCards(BaseModel):
    cards: list[ReportCallCard] = Field(default_factory=list)

class PopulationFrequencyDetail(BaseModel):
    source: str = "gnomAD"
    dataset: str
    variant_id: str
    sequencing_type: Literal["joint", "exome", "genome", "unknown"]
    allele_frequency: float | None
    allele_count: int | None
    allele_number: int | None
    homozygote_count: int | None
    popmax_frequency: float | None
    popmax_population: str | None
    genetic_ancestry_groups: list[PopulationFrequencyAncestryGroup]
    age_distribution: PopulationAgeDistribution | None
    flags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_url: str | None = None
```

Add optional `ReportPayload.call_cards: VariantReportCallCards | None`.

Add optional `ReportPayload.population_frequency_detail:
PopulationFrequencyDetail | None`.

Card-specific details stay in existing or planned fields:

- `population_frequency_detail`
- `in_silico_predictions`
- `functional_evidence`
- `clinical_consensus_detail`
- `therapies_trials`
- `publications_literature`

### Card 1: Population Frequency

Inputs:

- gnomAD summary from the existing tool, sourced from live GraphQL in real mode
  and fixture/cache fallback otherwise.
- ACMG scaffold if PM2, BS1, or BA1 is already present.

Output logic:

- `Absent` when allele count is zero or source explicitly reports absent.
- `Rare (<AF> AF)` when max AF is below the configured rare threshold.
- `Common (<AF> AF)` when max AF crosses benign-frequency thresholds.
- Support badge uses source-backed ACMG code when available: `PM2`, `BS1`,
  `BA1`, or `None`.
- Details include dataset, variant ID, sequencing type, AC/AN/AF/homozygotes,
  popmax, genetic ancestry group rows, available age histograms, flags,
  warnings, and the gnomAD source URL.

### Card 2: Computational

Inputs:

- `in_silico_predictions.cards`
- SpliceAI evidence summary from local/precomputed service where available.
- MyVariant/dbNSFP REVEL or equivalent predictor fields when present.

Output logic:

- Prefer the highest clinical action signal:
  splicing defect, damaging protein prediction, benign/normal prediction,
  uncertain.
- Support badge examples: `SpliceAI: 0.84`, `REVEL: 0.78`, `PP3`, `BP4`.

### Card 3: Lab And Functional

Inputs:

- `functional_evidence.display_metrics`
- `functional_evidence.source_asserted_codes`
- `functional_evidence.total_count`

Output logic:

- Use source-reported PS3/BS3 asserted codes when present.
- Support badges: `[PS3]` or `[PS3_Supporting]` plus `[X Unique]`.
- If PubMed-only functional studies exist without source-reported PS3/BS3,
  show `Functional Evidence Found` + `Review Required` + `[X Unique]`.
- If both PS3 and BS3 are source-reported, show `Conflicting Functional Data`
  + `Review Required` + `[X Unique]`.

### Card 4: Clinical Consensus

Inputs:

- ClinGen expert panel records when available.
- ClinVar classification, review status, and submitter count.
- Existing `acmg_classification` fallback.

Output logic:

- Primary label is the clinical consensus classification text.
- Support badge examples: `ClinGen Verified`, `ClinVar: 3 stars`,
  `14 submissions`, `Conflicting`.

### Section 7: Precision Therapies And Clinical Trials

Inputs:

- Existing therapy text and clinical trial summary.
- Future ClinicalTrials.gov API v2 search.

Retrieval:

- Query ClinicalTrials.gov `/api/v2/studies`.
- Use `query.term` for the gene symbol plus disease terms when known.
- Extract NCT ID, brief title, status, phase, interventions, conditions,
  locations, and study URL.
- Label each row `gene_level` unless the study explicitly includes the queried
  variant alias.

ClinicalTrials.gov notes:

- The official API migration guide says the v2 `/api/v2/studies` endpoint
  replaces classic full study queries and accepts search expressions through
  `query.term`.
- The study data structure docs define retrievable JSON fields and nested study
  modules.

## Decisions

- Decision: Use backend-generated call-card display metrics.
  - Alternative: frontend derives labels from raw evidence rows.
  - Reason: prevents duplicated clinical/source hierarchy logic in UI.
  - Reversible: yes, but not recommended.

- Decision: Functional category and study count are independent.
  - Alternative: derive PS3 strength from count.
  - Reason: user explicitly wants display of category plus count, not count as
    classification logic.
  - Reversible: no, this is a product invariant.

- Decision: Clinical trials are gene-level by default.
  - Alternative: require variant-specific trials only.
  - Reason: most trials are condition/gene/intervention oriented, and gene-level
    discovery is still useful to clinicians.
  - Reversible: yes, can add stricter filters later.

## Invariants

- Existing `ReportPayload` fields must remain backward compatible.
- `publications_literature.total_count` remains the general publication count.
- `functional_evidence.total_count` remains unique functional-study volume.
- `functional_evidence.display_metrics.acmg_badge_text` must not be derived
  from study count.
- Patient Report Pipeline (`/runs`) stays untouched.
- AlphaMissense stays on hold.

## Error Behavior

- Missing source data produces neutral labels and source warnings, not crashes.
- Failed ClinicalTrials.gov calls produce an empty trials list plus warning.
- Gene-level trial rows must be clearly labeled as gene-level.
- Variant-level trial rows require explicit variant alias match in the record.

## Testing Strategy

- Backend unit tests for each call card builder.
- Fixture lookup test for all four cards present.
- gnomAD tool parser test for live GraphQL population rows and age histograms.
- Contract canary for new Pydantic models once Claude mirrors them.
- ClinicalTrials.gov parser tests using fixture JSON.
- Live ClinicalTrials.gov smoke only when explicitly approved or as a documented
  optional verification step.
- Frontend browser verification belongs to Claude after implementation.

## Out Of Scope

- Frontend implementation.
- Pixel/layout iteration.
- Patient Report Pipeline (`/runs`).
- AlphaMissense re-enable.
- Clinical eligibility matching.
- Final laboratory classification beyond source-reported consensus display.
