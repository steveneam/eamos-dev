# Variant Evidence Report Layout Data Design

Status: Draft for user review
Owner: Codex
Last updated: 2026-05-20 19:25 +1000

## Summary

The Variant Evidence Report (`/report`) should be reorganized around an
above-the-fold four-card evidence grid, followed by detailed sections that
explain and audit the card outputs. The cards are intentionally compact:
primary label plus support badges only. Richer provenance, PMIDs, source rows,
snippets, warnings, and detailed metrics belong in the sections below the grid.

The backend should expose ready-to-render display metrics for each call card so
Claude can build the UI without deriving clinical meaning from raw source
payloads. The detailed payloads remain available for the expanded sections.

## Context And Current State

User source briefs:

- `Variant Report Page/Call cards/Ideal call card set up.txt`
- `Variant Report Page/Layout - VARIANT REPORT 1.txt`
- `Variant Report Page/Layout - VARIANT REPORT 2.txt`
- `Protein function in literature/Functional Card Display Logic & UI Layout Spec.txt`

Current frontend source:

- `app/frontend/src/pages/ReportPage.tsx` renders a header, AI stack, locus
  context, evidence-by-source block, gene context, decoder, trials, PubMed, and
  limitations.
- `VariantHeader.tsx` has a summary header and static sample stat cells for
  ClinVar, gnomAD AF, and REVEL.
- `InSilicoGrid.tsx`, `AcmgCriteriaFold.tsx`, `PublicationsCallout.tsx`, and
  `PubMedSection.tsx` already expose some data needed for the future layout.
- The page does not yet have the required four-card master grid:
  Population Frequency, Computational, Lab & Functional, Clinical Consensus.

Current backend source:

- `ReportPayload` already carries `in_silico_predictions`,
  `acmg_criteria_scaffold`, `publications_callout`, EP-VLEx
  `publications_literature`, and `functional_evidence`.
- The functional evidence backend now has enough structure to emit Card 3
  display metrics separately from the count of unique functional studies.

## Goals

- Make the four card outputs retrievable without frontend inference.
- Keep call cards compact: primary label plus support badges.
- Keep detailed evidence outside the cards in dedicated sections.
- Separate source-reported functional categorization from functional study
  count.
- Preserve current Variant Evidence Report behavior while adding fields
  additively.
- Keep Patient Report Pipeline (`/runs`) and AlphaMissense untouched.

## Non-Goals

- No frontend implementation in this backend planning slice.
- No Patient Report Pipeline work.
- No AlphaMissense re-enable.
- No final laboratory classification claim beyond source-reported consensus.
- No derivation of PS3/BS3 category from publication count.

## Proposed Design

Add an additive `ReportPayload.call_cards` group as the stable backend contract
for the four-card grid. Each card has the same minimal display surface:

- `card_id`
- `title`
- `primary_label`
- `support_badges`
- `ui_color_theme`
- `source_status`
- `provenance`

Each card also has an optional typed detail payload for section rendering. The
details are not required for the card itself.

### MVP Source Strategy

For an initial demo/MVP, use a hybrid retrieval strategy:

1. **MyVariant.info first for fast annotation fields.** It is appropriate as a
   single aggregator call for common variant annotations such as gnomAD,
   ClinVar, dbSNP, and dbNSFP-derived predictor fields when present.
2. **gnomAD Browser GraphQL for source population data.** Use
   `https://gnomad.broadinstitute.org/api` for interactive, single-variant
   Population Frequency card data after the variant has been normalized to
   `chr-pos-ref-alt` on GRCh38. Hydrate joint/exome/genome AC, AN, AF,
   homozygotes, `faf95` popmax, genetic ancestry group rows, and available age
   histograms. Treat the public GraphQL schema as rate-limited and subject to
   change, so cache successful responses and keep a fixture/cache fallback. For
   batch or production-scale reporting, prefer local indexed gnomAD release data
   or the official gnomAD toolbox path.
3. **Direct source APIs for evidence that needs provenance, freshness, or is not
   present in MyVariant.** This includes EP-VLEx PubMed rows/snippets,
   functional-study evidence from ClinGen/ClinVar/PubMed, ClinicalTrials.gov,
   and any source-native ClinGen evidence repository assertions.
4. **SpliceAI local/precomputed service for real use.** Use the Illumina
   SpliceAI package or a pinned container/service that accepts normalized VCF
   records plus the matching reference FASTA/annotation build and returns
   SpliceAI INFO fields. Store those results in our own database/cache.
5. **SpliceAI public lookup only as a temporary cached demo fallback.** It
   should not be the architecture for batch or repeated report generation.
6. **Local/direct engines later for production reliability.** For production or
   repeated demos, SpliceAI/Pangolin should be run locally or behind our own
   service, while MyVariant remains a useful fallback and annotation shortcut.

This avoids overbuilding the MVP while preventing the dashboard from depending
on brittle website scraping or unsupported batch usage.

### Card 1: Population Frequency

Source priority:

1. gnomAD Browser GraphQL live summary when available.
2. Cached gnomAD summary.
3. Fixture/sample fallback.

Card display:

- Primary label examples: `Absent`, `Rare (0.002% AF)`, `Common`.
- Support badge examples: `PM2`, `BS1`, `BA1`, or `None`.
- Details below card: max AF, allele count, allele number, genome build,
  source URL, genetic ancestry group frequencies, available heterozygote/
  homozygote age histograms, and warning if source degraded. Use gnomAD's
  "genetic ancestry group" language rather than "ethnicity" or patient
  ancestry inference.

### Card 2: Computational

Source priority:

1. Local/precomputed SpliceAI service for RNA splicing risk when available.
2. MyVariant/dbNSFP-derived REVEL or equivalent predictor fields when present.
3. Cached direct public SpliceAI lookup only for interactive MVP fallback.
4. Existing `in_silico_predictions` fixture/live bundle.

Card display:

- Primary label examples: `Damaging`, `Normal Splicing Predicted`,
  `Splicing Defect`, `Benign Predicted`, `Uncertain`.
- Support badge examples: `SpliceAI: 0.84`, `REVEL: 0.78`, `PP3`, `BP4`.
- Details below card: predictor rows, thresholds, score bars, per-source
  warnings.

### Card 3: Lab And Functional

Source priority:

1. ClinGen Evidence Repository asserted functional code, such as
   `PS3_Supporting` or `BS3_Supporting`.
2. ClinVar VCV comments or submitter text that explicitly reports PS3/BS3.
3. PubMed functional-study signals for count and review support only.

Card display:

- Primary label examples: `Functional Deficit`, `Normal Function`,
  `Conflicting Functional Data`, `Functional Evidence Found`,
  `No Functional Data Available`.
- Support badges: source-reported code badge, plus `X Unique`.
- The count badge is a volume metric only. It does not assign or upgrade the
  PS3/BS3 category.

Details below card:

- Unique studies, PMIDs/citations, source tags, snippets, source breakdown,
  warnings, and any source-reported asserted codes.

### Card 4: Clinical Consensus

Source priority:

1. ClinGen expert panel / VCEP classification when available.
2. ClinVar aggregate classification and review status.
3. Fixture/sample fallback.

Card display:

- Primary label examples: `Pathogenic`, `Likely Pathogenic`, `VUS`,
  `Conflicting`, `Likely Benign`, `Benign`.
- Support badge examples: `ClinGen Verified`, `ClinVar: 3 stars`,
  `14 submissions`.

Details below card:

- ClinVar accession, review status, submitter count, conflicting submissions,
  expert panel source, last evaluated date if available.

### Section 9: Precision Therapies And Clinical Trials

Clinical trials are useful even when not variant-specific. The backend should
query ClinicalTrials.gov at gene level first, using the gene symbol and disease
context where available. Results should be labeled as `gene_level` unless the
study record explicitly names the submitted variant or HGVS/protein alias.

Source:

- ClinicalTrials.gov API v2 `/api/v2/studies`, using `query.term` for general
  search expressions and the v2 JSON study structure.

Display:

- Trial ID, brief title, status, phase, intervention names, condition names,
  site/location summary, and source URL.
- Provenance badge: `Gene-level match` or `Variant-level match`.
- No claim that a patient is eligible; this is discovery/navigation only.

## Section Order

The target page order from the user briefs:

1. Variant header and action bar.
2. Four-card master grid.
3. Generative AI interpretation summary.
4. Disease mechanism and inheritance baseline.
5. Molecular context and structural overlap.
6. In silico and computational deep dive.
7. ACMG curation worksheet ledger.
8. Parallel aggregated publications data grid.
9. Precision therapies and active clinical trials, primarily gene-level when
   variant-level trial evidence is unavailable.
10. Limitations and source provenance.

## Interfaces And Data

Recommended additive backend contract:

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
    support_badges: list[ReportCallBadge]
    ui_color_theme: str
    source_status: str
    provenance: list[str] = Field(default_factory=list)

class VariantReportCallCards(BaseModel):
    cards: list[ReportCallCard]
```

Implemented first-slice population detail payload:

```python
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
    flags: list[str]
    warnings: list[str]
    source_url: str | None
```

Card-specific detail payloads can stay in the existing fields:

- population: `population_frequency_detail` plus the raw gnomAD evidence row
- computational: `in_silico_predictions`, SpliceAI evidence rows
- lab/functional: `functional_evidence`
- clinical consensus: `acmg_classification`, ClinVar evidence rows,
  `acmg_criteria_scaffold`

## Tradeoffs

- Generic call-card objects make frontend rendering simple and consistent.
- Existing detailed fields remain typed and source-specific.
- The generic card layer adds small backend duplication, but it prevents every
  frontend component from re-implementing source hierarchy and label logic.
- MyVariant reduces MVP integration work, but it is an aggregated snapshot. It
  should not replace source-native APIs where the report needs current rows,
  snippets, asserted functional codes, or trial provenance.
- gnomAD GraphQL is a good live source for interactive per-variant population
  frequency, ancestry-group rows, and age histograms, but it has the same
  operational caution as public SpliceAI lookups: cache it, preserve the source
  URL/dataset, and do not make unbounded batch report generation depend on the
  public browser API.
- Local SpliceAI requires reference-build discipline and operational setup, but
  it avoids throttling risk and lets the report serve repeat lookups from our
  own cache/database.

## Decision

Use a backend-generated four-card display contract for the above-the-fold grid,
and keep detailed section data in existing typed payload groups. Implement
additively so current clients remain compatible.

For the MVP, use source gnomAD Browser GraphQL for live single-variant
population frequency, ancestry, and age data, with cache/fixture fallback and
local indexed data as the production-scale path. Add MyVariant as an annotation
aggregator/fallback, not as the only source of truth. Use local/precomputed
SpliceAI as the target implementation for splicing scores, with public lookup
only as a cached fallback. Keep direct APIs for EP-VLEx, functional evidence,
ClinicalTrials.gov, and source-native ClinGen/ClinVar details.
