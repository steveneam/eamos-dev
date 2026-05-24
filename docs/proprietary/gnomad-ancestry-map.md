# gnomAD Genetic Ancestry Map Regions

Status: Active frontend prototype
Type: UI mapping algorithm
Owner: Codex
Added: 2026-05-24 01:56 +1000 - Codex
Last updated: 2026-05-24 21:17 +1000 - Codex

## What It Does

Maps gnomAD genetic ancestry group IDs to deterministic visual regions on the
Variant Evidence Report Section 3 world map. The map uses source-reported
gnomAD group rows and a fixed Eamos region table to render relative
allele-frequency heat fills without implying patient ancestry, race, ethnicity,
or exact geography.

## Why It Is Eamos-Original

The mapping is an Eamos-specific presentation layer for clinical/research
report readability. It pairs each gnomAD group ID with:

- a stable visual anchor on the report map,
- an approximate region path for whole-region heat fill,
- source-group context copy,
- a neutral fallback anchor for future or unmapped group IDs,
- a land-silhouette mask that clips approximate region fills to the SimpleMaps
  basemap so fills read closer to country outlines instead of freeform blobs,
- hover/focus linkage between the map region and the matching ancestry row,
- explicit caveat text separating gnomAD source-group labels from patient
  ancestry or geographic certainty.

The source frequency values remain in `population_frequency_detail` and Section
3 row data; the map algorithm only controls visual placement, heat-region shape,
linked hover state, and explanatory context.

## Age Distribution Data

The Section 3 age chart uses exact gnomAD counts, not eyeballed bar heights.
Variant-carrier panels are built from the gnomAD variant GraphQL
`age_distribution` payload and are kept separate for exome and genome data.
The all-individual panels use the gnomAD v4 dataset metadata
`datasets/gnomad-v4/ageDistribution.json`, which is the same source pattern used
by the public gnomAD browser age-distribution component.

The rendered report intentionally shows four panels:

- exome variant carriers,
- exome all individuals,
- genome variant carriers,
- genome all individuals.

## Source Of Truth

- `app/frontend/src/components/report/gnomadAncestryMap.ts`
- `app/frontend/src/components/report/gnomadAncestryMap.test.ts`
- `app/web/components/report/gnomadAncestryMap.ts`
- `app/frontend/src/components/report/PopulationFrequencySection.tsx`
- `app/web/components/report/PopulationFrequencySection.tsx`
- `app/backend/app/tools/gnomad.py`
- `app/backend/app/services/population_frequency_section.py`
- `app/frontend/public/world.svg`
- `app/web/public/world.svg`
- `plans/variant-report-data-orchestration/plan.md` Task 15

## Caveats

- The basemap is `world.svg` from SimpleMaps; Eamos owns the gnomAD group anchor
  mapping and caveat logic, not the basemap artwork.
- Region paths are visual orientation zones for source genetic ancestry groups.
  They are clipped to land silhouettes for readability but are still not exact
  country/continent boundaries or geographic coordinates.
- The algorithm must not be used to infer patient ancestry, race, ethnicity,
  age, prevalence, survivorship, or per-country allele frequency.
- Future gnomAD group IDs should remain visible through the neutral fallback
  until a reviewed anchor is added.
- Population values must continue to come from source-backed gnomAD payload
  fields, not from the map layer.
- The all-individual age baseline is release-level gnomAD v4 metadata; it is not
  variant-specific and should be labelled separately from variant-carrier counts.
