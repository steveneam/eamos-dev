# Variant Evidence Report Layout Data Plan

Source: `plans/variant-report-layout/spec.md`

Status: In progress - backend call-card contract and gnomAD population first slice implemented
Last updated: 2026-05-20 19:25 +1000 - Codex

Shared decisions:

- The four call cards are compact: primary label plus support badges only.
- Detailed evidence belongs in sections below the card grid.
- Functional category and functional-study count are independent.
- Clinical trials may be gene-level and must be labeled as such.
- MyVariant.info is an MVP annotation aggregator/fallback, not the sole source
  of truth.
- gnomAD Browser GraphQL is the live source for interactive single-variant
  population frequency, genetic ancestry group rows, and age histograms; cache
  responses and use local indexed release data/toolbox for production-scale
  batch work.
- SpliceAI target architecture is local/precomputed scores in our own
  service/database; public lookup is only a cached demo fallback.
- Frontend implementation is Claude-owned unless the user explicitly redirects.

## Task 0 - MVP Source Strategy And Annotation Adapter - IN PROGRESS

**Goal**

Define and implement the annotation-source split for the initial demo so report
cards can be populated quickly without building brittle website scrapers.

**Context**

The user's My Variant script can accelerate common annotation retrieval, but it
must not replace source-native evidence paths. SpliceAI should move toward a
local/precomputed implementation using the Illumina package or an equivalent
pinned service backed by our own cache/database.

**Relevant Files Or References**

- `plans/variant-report-layout/spec.md`
- local user file: `Variant Report Page/My Variant Script.txt`
- local user file: `Variant Report Page/Call cards/SpliceAI and REVEL implementation.txt`
- `app/backend/app/tools/spliceai.py`
- future `app/backend/app/tools/myvariant.py`
- future SpliceAI service/cache table

**Proposed Approach**

Add a MyVariant adapter for common annotation fields only after validating the
actual response field paths. Use it for ClinVar/dbSNP/dbNSFP REVEL when
available. Keep gnomAD population frequency on source gnomAD Browser GraphQL,
and keep EP-VLEx, functional evidence, ClinGen/ClinVar assertions, and
ClinicalTrials.gov on direct/source-native integrations.

For SpliceAI, normalize the queried variant into a build-specific VCF record,
run or query a local/precomputed SpliceAI service, parse DS/DP fields, and cache
the result with build/version provenance. Keep the current public lookup path
rate-limited and cached for interactive demo fallback only.

**Acceptance Criteria**

- Source fields used from MyVariant are verified against live/fixture response
  examples and marked with provenance.
- gnomAD live GraphQL responses are cached and expose ancestry/age detail as
  source data, not patient inference.
- No feature depends on scraping HTML pages.
- SpliceAI card data can come from local/precomputed output when configured.
- Public SpliceAI lookup is bounded by cache/backoff/rate limits.
- Missing aggregator fields degrade to direct APIs or neutral warnings.

**Verify**

Focused adapter/parser tests plus:

`cd app/backend && python -m pytest tests/test_variant_search_integration.py tests/test_tool_invariants.py -q`

## Task 1 - Backend Call-Card Contract - DONE 2026-05-20

**Goal**

Add the generic backend shape for the four Variant Evidence Report call cards.

**Context**

The current UI has summary stat cells in `VariantHeader.tsx`, but no stable
four-card payload. Claude should not derive card labels from raw evidence rows.

**Relevant Files Or References**

- `app/backend/app/schemas/run.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/tests/test_frontend_contract.py`
- `app/frontend/src/lib/backend.ts` (Claude mirror later)
- `plans/variant-report-layout/spec.md`

**Proposed Approach**

Add `ReportCallBadge`, `ReportCallCard`, `VariantReportCallCards`, and optional
`ReportPayload.call_cards`. Add a builder that assembles the four cards from
existing payload/evidence data.

**Acceptance Criteria**

- `/api/v1/lookup` returns four call cards in order.
- Each card has `card_id`, `title`, `primary_label`, `support_badges`,
  `ui_color_theme`, `source_status`, and `provenance`.
- Existing report fields remain unchanged.
- Frontend mirror fields are either mirrored by Claude or explicitly listed as
  pending in the contract canary.

**Verify**

`cd app/backend && python -m pytest tests/test_frontend_contract.py tests/test_variant_search_integration.py -q`

**Out Of Scope**

Frontend rendering and visual design.

**Implementation note:** Added `ReportCallBadge`, `ReportCallCard`,
`VariantReportCallCards`, and optional `ReportPayload.call_cards`. Added
`app/backend/app/services/report_call_cards.py` to assemble the four cards in
order from the live lookup payload. Frontend mirror fields remain pending for
Claude and are explicitly exempted in the backend contract canary.

## Task 2 - Population Frequency Card - DONE FIRST SLICE 2026-05-20

**Goal**

Build Card 1 from gnomAD/source frequency data and ACMG frequency badges.

**Context**

The desired card shows labels like `Rare (0.002% AF)` and badges like `PM2`.
The current page has a static gnomAD stat in `VariantHeader.tsx`. The source is
gnomAD Browser GraphQL (`https://gnomad.broadinstitute.org/api`) for
interactive single-variant live data.

**Relevant Files Or References**

- `app/backend/app/services/lookup_service.py`
- `app/backend/app/tools/gnomad.py`
- `app/backend/app/schemas/run.py`
- `app/backend/tests/test_variant_search_integration.py`

**Proposed Approach**

Normalize gnomAD summary fields into max AF, allele count, allele number,
subpopulation, and source status. Produce the card label and badge from
source-backed thresholds or existing ACMG scaffold values.
Hydrate `population_frequency_detail` with dataset, variant ID, sequencing
type, AC/AN/AF/homozygotes, popmax, genetic ancestry group rows, available age
histograms, warnings, and source URL.

**Acceptance Criteria**

- Absent/rare/common labels are deterministic.
- Badge is `PM2`, `BS1`, `BA1`, or `None`.
- Degraded gnomAD status appears in card provenance/warnings.
- Genetic ancestry group rows and age histograms are available for detailed
  section rendering.

**Verify**

`cd app/backend && python -m pytest tests/test_variant_search_integration.py tests/test_tool_invariants.py -q`

**Implementation note:** Existing `GnomadTool` now queries joint/exome/genome
AC/AN/homozygotes, `faf95`, genetic ancestry group rows, and age histograms in
real mode. The lookup payload now exposes `population_frequency_detail`, and
Card 1 is generated from that detail. Production-scale gnomAD storage/indexing
is still future work.

## Task 3 - Computational Card - FIRST CARD MAPPING DONE 2026-05-20

**Goal**

Build Card 2 from local/precomputed SpliceAI and protein-effect predictor data.

**Context**

The desired card shows labels like `Damaging` and badges like
`SpliceAI: 0.84`. Current data exists in `in_silico_predictions` and evidence
rows. REVEL can be sourced from MyVariant/dbNSFP when present. SpliceAI should
come from a local/precomputed service when available, with public lookup only as
a cached interactive fallback.

**Relevant Files Or References**

- `app/backend/app/schemas/run.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/tools/spliceai.py`
- future `app/backend/app/tools/myvariant.py`
- future SpliceAI local/precomputed service/cache
- `app/backend/app/fixtures/lookup_v2_modules.json`

**Proposed Approach**

Choose a primary label by priority: splicing defect, damaging protein
prediction, benign/normal prediction, uncertain/no data. Add support badges for
the strongest available predictor values. Parse SpliceAI DS/DP fields from the
local/precomputed path and preserve build/version provenance.

**Acceptance Criteria**

- SpliceAI high delta can produce `Splicing Defect`.
- Damaging protein predictors can produce `Damaging`.
- Missing predictors produce neutral `No Computational Data`.
- Public SpliceAI lookup is not required for batch report generation.
- AlphaMissense remains hidden/on hold unless explicitly approved.

**Verify**

`cd app/backend && python -m pytest tests/test_variant_search_integration.py tests/test_frontend_contract.py -q`

**Implementation note:** Card 2 is generated from existing
`in_silico_predictions` plus existing SpliceAI/ACMG scaffold fields. Local or
precomputed SpliceAI and MyVariant/dbNSFP REVEL retrieval remain separate source
implementation tasks.

## Task 4 - Lab And Functional Card - DONE 2026-05-20

**Goal**

Complete Card 3 as source-reported functional category plus unique functional
study count.

**Context**

The backend now returns `functional_evidence.display_metrics`, study rows, and
source counts. The UI card should show only primary label plus badges; detailed
study data is for the later section layout.

**Relevant Files Or References**

- `app/backend/app/schemas/run.py`
- `app/backend/app/services/functional_evidence.py`
- `app/backend/tests/test_functional_evidence.py`
- User functional-card layout spec

**Proposed Approach**

Map `functional_evidence.display_metrics` into the generic call-card contract.
Keep `functional_evidence` itself as the detailed payload for future section
rows.

**Acceptance Criteria**

- PS3 source-reported data displays `Functional Deficit` plus PS3 badge.
- BS3 source-reported data displays `Normal Function` plus BS3 badge.
- Study count badge displays `X Unique`.
- Count does not change the category or code badge.
- PubMed-only functional studies display `Functional Evidence Found` plus
  `Review Required`.

**Verify**

`cd app/backend && python -m pytest tests/test_functional_evidence.py tests/test_variant_search_integration.py -q`

**Implementation note:** Card 3 maps `functional_evidence.display_metrics` into
the generic call-card contract. The source-reported category badge and
`X Unique` count badge remain independent.

## Task 5 - Clinical Consensus Card - FIRST CLINVAR FALLBACK MAPPING DONE 2026-05-20

**Goal**

Build Card 4 from ClinGen/ClinVar clinical consensus.

**Context**

The desired card shows labels like `Likely Pathogenic` and badges like
`ClinGen Verified` or `ClinVar: 3 Stars`.

**Relevant Files Or References**

- `app/backend/app/tools/clinvar.py`
- future/available ClinGen source records
- `app/backend/app/services/lookup_service.py`
- `app/backend/tests/test_variant_search_integration.py`

**Proposed Approach**

Prefer ClinGen expert panel classification when available. Fall back to ClinVar
classification and review status. Include submitter count and conflict state
when source data provides it.

**Acceptance Criteria**

- ClinGen expert panel source produces `ClinGen Verified` badge.
- ClinVar review status maps to star/review badge.
- Conflicting classifications display a conflict label instead of hiding
  disagreement.

**Verify**

`cd app/backend && python -m pytest tests/test_variant_search_integration.py tests/test_tool_invariants.py -q`

**Implementation note:** Card 4 is generated from the current ClinVar aggregate
classification/review-status payload. ClinGen expert-panel/VCEP precedence and
richer conflict/submission detail remain a future source-integration slice.

## Task 6 - Section Payloads For Detailed Layout

**Goal**

Expose enough structured detail for the requested below-card sections without
forcing frontend components to parse generic evidence maps.

**Context**

The target layout includes AI summary, disease mechanism, molecular context,
computational deep dive, ACMG ledger, publications grid, therapies, trials, and
limitations.

**Relevant Files Or References**

- `app/backend/app/schemas/run.py`
- `app/backend/app/services/lookup_service.py`
- existing report components under `app/frontend/src/components/report/`

**Proposed Approach**

Add typed optional detail groups only where existing payloads are insufficient.
Reuse current fields where they already work: `associated_conditions`,
`locus_context`, `in_silico_predictions`, `acmg_criteria_scaffold`,
`publications_literature`, `functional_evidence`, and `pubmed_articles`.

**Acceptance Criteria**

- Each requested section has a clear source field.
- No section requires frontend parsing of raw `evidence.summary`.
- Missing source data degrades to empty lists/nulls plus warnings.

**Verify**

`cd app/backend && python -m pytest tests/test_frontend_contract.py tests/test_variant_search_integration.py -q`

## Task 7 - Gene-Level ClinicalTrials.gov Integration

**Goal**

Populate the therapies/trials section with gene-level clinical trial discovery.

**Context**

The user explicitly allows gene-level results when variant-specific trial
records are unavailable, e.g. RPE65 gene trials for an RPE65 variant.

**Relevant Files Or References**

- ClinicalTrials.gov API v2 `/api/v2/studies`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/tools/clinical_trials.py` or new service file
- `app/backend/tests/`

**Proposed Approach**

Query ClinicalTrials.gov with `query.term` using gene symbol plus disease terms
when available. Parse NCT ID, title, status, phase, interventions, conditions,
locations, and URL. Mark rows as `gene_level` unless the record includes the
variant alias.

**Acceptance Criteria**

- Gene-level RPE65 trial rows can be returned even when no trial names the
  exact variant.
- Rows include NCT URL and recruitment status.
- No row implies patient eligibility.
- Source failures return empty rows plus warning.

**Verify**

Focused fixture tests for parser and service. Optional approved live smoke:
`USE_REAL_APIS=true` lookup for an RPE65 variant and confirm ClinicalTrials.gov
rows are labeled `gene_level`.

## Task 8 - Claude Frontend Handoff

**Goal**

Give Claude a precise rendering contract for the four-card grid and detailed
sections.

**Context**

Claude owns frontend/product rendering and browser/pixel iteration. Codex owns
backend schema and source retrieval.

**Relevant Files Or References**

- `agent_handoff/CURRENT.md`
- `app/frontend/src/lib/backend.ts`
- `app/frontend/src/pages/ReportPage.tsx`
- `plans/variant-report-layout/design.md`
- `plans/variant-report-layout/spec.md`

**Proposed Approach**

File a cross-agent request once the backend contract lands. Include exact fields
to mirror, section order, and the invariant that functional category and count
are independent.

**Acceptance Criteria**

- `backend.ts` mirror includes all new fields.
- Variant Evidence Report renders the four cards above the fold.
- Detailed sections use typed payloads, not raw evidence parsing.
- Browser verification covers desktop and mobile.

**Verify**

Claude-owned frontend build, tests, and browser verification.
