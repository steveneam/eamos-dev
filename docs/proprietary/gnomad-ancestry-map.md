# gnomAD Genetic Ancestry Map Anchors

Status: Active frontend prototype
Type: UI mapping algorithm
Owner: Codex
Added: 2026-05-24 01:56 +1000 - Codex
Last updated: 2026-05-24 03:38 +1000 - Codex

## What It Does

Maps gnomAD genetic ancestry group IDs to deterministic visual anchors on the
Variant Evidence Report Section 3 world map. The map uses source-reported gnomAD
group rows and a fixed anchor table to render relative allele-frequency markers
without implying patient ancestry, race, ethnicity, or exact geography.

## Why It Is Eamos-Original

The mapping is an Eamos-specific presentation layer for clinical/research
report readability. It pairs each gnomAD group ID with:

- a stable visual anchor on the report map,
- source-group context copy,
- a neutral fallback anchor for future or unmapped group IDs,
- explicit caveat text separating gnomAD source-group labels from patient
  ancestry or geographic certainty.

The source frequency values remain in `population_frequency_detail` and Section
3 row data; the anchor algorithm only controls marker placement and explanatory
context.

## Source Of Truth

- `app/frontend/src/components/report/gnomadAncestryMap.ts`
- `app/frontend/src/components/report/gnomadAncestryMap.test.ts`
- `app/web/components/report/gnomadAncestryMap.ts`
- `app/frontend/src/components/report/PopulationFrequencySection.tsx`
- `app/web/components/report/PopulationFrequencySection.tsx`
- `app/frontend/public/world.svg`
- `app/web/public/world.svg`
- `plans/variant-report-data-orchestration/plan.md` Task 15

## Caveats

- The basemap is `world.svg` from SimpleMaps; Eamos owns the gnomAD group anchor
  mapping and caveat logic, not the basemap artwork.
- Marker anchors are visual orientation points for source genetic ancestry
  groups, not exact geographic coordinates.
- The algorithm must not be used to infer patient ancestry, race, ethnicity,
  age, prevalence, survivorship, or per-country allele frequency.
- Future gnomAD group IDs should remain visible through the neutral fallback
  until a reviewed anchor is added.
- Population values must continue to come from source-backed gnomAD payload
  fields, not from the map layer.
