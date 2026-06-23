# Variant Report Section Consistency Audit

Status: Draft

## Purpose

The ABCA4 learning-gap fixes must become a report-wide framework, not a set of section-specific patches. Every report section that makes an evidence claim needs the same audit vocabulary so the frontend can present a modern dashboard without guessing which data matters.

The audit contract is deliberately small:

- scope: exact variant, equivalent allele, transcript/locus, protein region, gene-disease, disease/intervention discovery, or summary
- source: expert panel, curated source, primary database, literature, Eamos computed, mixed source, inferred, or unavailable
- confidence: numeric section confidence from `0.0` to `1.0`
- priority: numeric display priority from `0` to `100`
- state: ready, limited, empty, error, or loading
- default disclosure: open or collapsed by default
- notes: short section-local data notes, not global alarm banners unless they change the interpretation
- ACMG contribution: source asserted, Eamos hint, not assessed, or none
- verification: focused test proving the section does not overstate scope

## Section Matrix

| Section | Scope rule | Source strength | Default disclosure | ACMG contribution | Audit focus |
| --- | --- | --- | --- | --- | --- |
| Header and summary | Summary over current report facts | Mixed source | Open | None | Does not introduce claims absent from source sections |
| Expert panel / ClinGen | Exact variant or no attach | Expert panel | Open when matched | Source asserted | Identity-tier guard; narrative text is rationale only |
| Eamos ACMG | Exact variant evidence plus case context | Eamos computed | Open when criteria exist | Computed advisory | Missing PM3/PP4 case context stays as limitation, not score |
| Population frequency / gnomAD | Exact normalized allele | Primary database | Open when data exists | PM2/BA1/BS1 hints only | No frequency facts in unrelated sections; source unavailable vs not found |
| In silico predictors | Exact variant/protein substitution where supported | Primary database | Open when calibrated predictors exist | PP3/BP4 hints only | Model/version/calibration shown; unavailable predictors stay as notes |
| Gene-disease context | Gene-disease relationship | Curated source | Open when a primary condition exists | Context only unless VCEP/source says otherwise | Definitive/strong rows rank above disputed/limited rows |
| Gene view / locus context | Transcript/locus projection | Curated/local model | Open when coordinates render | None | Transcript/build/source visible; fixture/missing state explicit |
| Molecular/protein context | Protein region or transcript locus | Mixed source | Collapsed by default | Context only | Protein localization requires coordinate overlap |
| Publications | Exact variant when matched; gene fallback otherwise | Literature | Open by default | Source asserted only when source says so | Variant articles and gene-wide discovery are labeled separately |
| Clinical trials / therapies | Discovery unless exact eligibility text confirms variant | Primary registry | Open by default | None | Never implies patient eligibility; query lane provenance preserved |
| Gene viewer / workbench launch | Transcript/locus view over current identity | Local/workbench model | User-triggered | None | Same identity/build as report; warnings stay local to viewer |
| AI narrative / consensus text | Summary over cited source sections | Mixed source | Collapsed or secondary | None | Every sentence must map to source facts or limitations |

## Eamos Signal Model

The report should include `report_profile.section_signals`, a backend-generated ordering and disclosure contract. The frontend uses it to render a dashboard:

- High-priority exact-variant evidence opens first.
- Publications and trials stay open by default because they are user-expected discovery surfaces; their scope labels and data notes keep them honest.
- Data notes appear near the relevant section.
- Empty/error states remain visible enough to explain source status without dominating the page.
- ACMG scoring remains separate from Eamos confidence/ranking.

First-pass signal fields:

```json
{
  "section_id": "population_frequency",
  "label": "Population Frequency",
  "priority": 88,
  "confidence": 0.88,
  "relevance": "exact_variant",
  "source_strength": "primary_db",
  "status": "ready",
  "default_open": true,
  "headline": "Popmax group: nfe",
  "data_notes": [],
  "source_refs": ["gnomad"]
}
```

## Disclosure Rules

- Open by default: summary, exact expert assertion, Eamos ACMG when criteria exist, exact population frequency, calibrated predictors, primary gene-disease context, publications, and trials/therapies.
- Collapsed by default: molecular/protein details, AI narrative, raw provenance, and future low-use sections that do not answer the user's first-pass report questions.
- Empty but important: source-specific empty states should show compactly when the user expects the source, for example gnomAD not found or ClinGen no exact VCEP assertion.
- Error: source failure should render as a small unavailable state in the section, not a top-level report failure unless the report cannot answer the query.

## Implementation Notes

- Keep warnings and limitations section-local unless they change the top-line interpretation.
- Eamos ranking/confidence may be visible as Eamos dashboard signal, but it must not be presented as ACMG or clinical classification.
- Do not let frontend infer scientific importance from row counts alone. Backend owns priority and confidence because it knows match scope and source strength.
- Do not hide low-confidence rows completely. Collapse them and label their scope.

## Regression Questions

- Can every visible section state whether it is exact-variant, gene-level, disease-level, or discovery-only?
- Can the frontend order sections without hard-coded ABCA4 or RPE65 knowledge?
- Can a user see why a section is collapsed or limited without reading raw warning codes?
- Can tests prove that a section does not contribute ACMG points outside its allowed scope?
