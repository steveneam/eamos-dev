# Report Evidence Framework Investigation

Status: Draft

This investigation captures why the current ABCA4 learning-gap fixes need to become a general evidence framework instead of staying as ABCA4-specific patches.

## Problem

The dirty tree already addresses the observed ABCA4 failures in several places:

- `app/backend/app/tools/clingen.py` adds a variant-identity guard so ClinGen rows are not selected because a requested variant appears only in narrative text.
- `app/backend/app/tools/clinical_trials.py` and `app/backend/app/services/lookup_service.py` add ABCA4/Stargardt/Tinlarebant discovery behavior.
- `app/backend/app/services/acmg_points_engine.py` adds PM3/PP4 case-context warnings.
- `app/backend/app/fixtures/protein_feature_seeds.json` adds source-backed ABCA4 protein architecture.
- `app/backend/app/repos/supabase_local_model_cache_repo.py` orders gene-disease rows by validity before choosing the primary condition.
- `app/web/components/report/EamosAcmgClassifier.tsx` displays ACMG warning strings.

The main risk is that some of this is framework-quality and some is still target-specific. If shipped as-is, the same class of failure will recur for the next gene, disease, intervention, or variant.

## Evidence Facts To Preserve

- Local ClinGen has ABCA4 VCEP affiliation `50140` data.
- The exact ClinGen Evidence Repository assertion for `ABCA4 c.5461-10T>C` is UUID `64d8e05f-18c1-4092-9ce7-8880f952e96e`.
- That assertion is Pathogenic, approved `2026-04-28`, published `2026-04-30`, and lists `PVS1_Strong`, `PM3_Very Strong`, `PS4`, and `PP4`.
- The record's identity fields include `NM_000350.3:c.5461-10T>C`, `NM_000350.3(ABCA4):c.5461-10T>C`, `NC_000001.11:g.94011395A>G`, CAID `CA220687`, and ClinVar Variation ID `92870`.
- Functional/publication evidence that should remain findable for `c.5461-10T>C` includes PMIDs `26976702`, `27775217`, `29461686`, `36910710`, and `41536809`.
- ClinicalTrials.gov trial `NCT06388083` is Tinlarebant in Stargardt disease and should be discoverable for ABCA4/Stargardt report context.
- `ABCA4 c.5234T>A` needs real case context before PM3 or PP4 can be scored. Do not infer phase, phenotype specificity, family history, affected status, or second-allele evidence from public lookup alone.
- Ile1745 is in or near an ABCA4 transmembrane helix, not the ATPase motif. Protein architecture must be feature-overlap/source-backed.

## Source Research

ClinGen Evidence Repository records are expert-panel assertions with structured identity fields, not generic text hits. The ABCA4 `c.5461-10T>C` ERepo page exposes the UUID, HGVS expressions, CAID, ClinVar Variation ID, condition, inheritance, approval/publication dates, classification, criteria, and expert panel. Source: https://erepo.clinicalgenome.org/evrepo/ui/classification/64d8e05f-18c1-4092-9ce7-8880f952e96e?version=1.0

ClinGen's Evidence Repository is described as an FDA-recognized human genetic variant database containing expert-curated assertions and supporting evidence summaries. Its advanced search exposes structured fields such as affiliation ID, CAID, ClinVar Variation ID, condition, gene, HGVS, classification, and expert panel. Source: https://erepo.clinicalgenome.org/evrepo/

ClinGen variant classification guidance explicitly includes PM3 and PP4-specific guidance, so PM3/PP4 should not be treated as generic text-mined assertions. Source: https://clinicalgenome.org/tools/clingen-variant-classification-guidance/

ClinGen PP1/BS4/PP4 guidance states that phenotype specificity is coupled with segregation/locus evidence and discusses a points-based evaluation for phenotype and co-segregation evidence. Source: https://clinicalgenome.org/docs/clingen-guidance-for-use-of-the-pp1-bs4-co-segregation-and-pp4-phenotype-specificity-criteria-for-sequence-variant/

ClinicalTrials.gov v2 should be treated as a discovery registry, not eligibility guidance. Use the v2 API, preserve query field provenance, and label rows as registry/discovery rows. Source: https://clinicaltrials.gov/data-api/api

ClinicalTrials.gov v2 search supports query fields such as `query.cond`, `query.intr`, `query.term`, and status filters. The live API version endpoint returned `apiVersion=2.0.5` and `dataTimestamp=2026-06-22T09:00:05` during this investigation.

`NCT06388083` was verified through the v2 API as `ACTIVE_NOT_RECRUITING`, Phase 2/3, conditions `STGD1; Stargardt Disease 1`, interventions `Tinlarebant; Placebo`, last update posted `2026-03-12`.

## Current Diff Review

### Robust Changes

- ClinGen variant identity guarding is directionally correct: it filters local/live records using identity fields rather than summary/rationale text.
- `EamosComputedClassification.warnings` is backward-compatible and gives the frontend a place to display honest limitations.
- Gene-disease validity ordering is gene-agnostic and prevents disputed relationships from winning primary condition selection over definitive relationships.
- Protein seed ingestion is already gene-agnostic; adding ABCA4 data exercises an existing framework.

### Remaining Spot-Fixes

- Clinical trial disease and discovery terms are hard-coded in `_GENE_TRIAL_DISEASE_TERMS` and `_GENE_TRIAL_DISCOVERY_TERMS`.
- Combined trial query provenance is lossy: multiple query lanes can contribute rows, but the summary still reports one selected query/source URL.
- ACMG warnings are flat strings, which makes structured frontend/export behavior brittle and can become noisy for public lookups with no submitted case context.
- ABCA4 protein seed data is source-backed, but the framework still needs a general overlap contract so reports do not imply that a variant is in a motif unless the coordinates prove it.
- Publications and trials do not share one lazy-section state model. Publications use `LookupSectionEnvelope`; trials are still eager through `report_profile.therapies_trials`.
- The same consistency problem applies outside the ABCA4-touched sections: population frequency, computational predictors, Eamos ACMG, gene-disease context, gene view, molecular context, publications, trials, and report narratives all need a shared scope/provenance/confidence/status vocabulary.

## Root Causes

1. Identity, evidence rationale, and report search text are not consistently separated.
2. Clinical trial discovery lacks a reusable query-plan/provenance model.
3. ACMG case-context limitations are represented as display strings instead of typed missing-input requirements.
4. Lazy report sections are not uniformly represented across publications, trials, and ClinGen.
5. Regression tests prove ABCA4 facts but not enough cross-gene invariants.
6. The frontend currently has to infer importance from section presence and row counts. That will not scale to a dashboard-style report because scientific priority depends on match scope, source strength, and confidence.

## Framework Requirements

1. Match variant evidence by structured identity tiers: source assertion ID/version, CAID/VRS/SPDI, normalized genomic allele with assembly, transcript HGVS with accession version, then text-only candidate. Text-only candidate matches must never auto-attach evidence.
2. Store source assertion provenance: namespace, source URL/API endpoint, UUID/accession, version, fetched timestamp, approval/publication dates, VCEP/assertion method, condition, inheritance, criteria met/not met, and raw payload hash when available.
3. Treat narrative text as rationale/search content only. A narrative mention can explain a source assertion but cannot establish that the assertion belongs to the current variant.
4. Model PM3/PP4 as case-context requirements. Missing phase, second allele, affected status, phenotype specificity, test scope, and alternative-cause exclusion must produce typed limitations, not score upgrades.
5. Build clinical trial rows from query lanes with per-row match details: query field, terms, evidence field/snippet, match level, source URL, and freshness.
6. Use reusable terminology/provenance tables for disease aliases, gene aliases, intervention aliases, and curated discovery terms. Avoid gene-specific constants in tool code.
7. Put publications and trials behind the same lazy-section envelope/status/freshness contract.
8. Keep protein architecture source-backed and coordinate-based. The report may say a variant overlaps a feature only when the feature coordinates and variant protein position overlap.
9. Emit report-wide `section_signals` so the frontend can rank and collapse sections consistently while keeping warnings and limitations near their owning section.

## Regression Controls

ABCA4 remains a regression suite, not a special case:

- `ABCA4 c.5461-10T>C` must resolve the exact ClinGen assertion UUID and criteria.
- `ABCA4 c.5461-10T>C` must show functional/publication evidence including the known PMID set where source data contains it.
- `ABCA4/Stargardt` must discover `NCT06388083` through source-backed disease/intervention query lanes.
- `ABCA4 c.5234T>A` must display PM3/PP4 missing-case-context limitations rather than inferred PM3/PP4.
- ABCA4 Ile1745 must be reported as overlapping/in-near a transmembrane helix, not an ATPase motif.
