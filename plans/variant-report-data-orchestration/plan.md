# Variant Report Data Orchestration Plan

Source: `plans/variant-report-data-orchestration/spec.md`

Status: In progress - Tasks 1-8 implemented and verified; Task 9 parser/helper slice complete; Task 11A gene-agnostic hardening + Task 12 Section 3 gnomAD expansion implemented and verified; Task 13 gene-context snapshot contract implemented and verified; Tasks 14-19 remain planned for snapshot UI, production gnomAD, ClinicalTrials.gov hardening, and final UI QA
Last updated: 2026-05-24 00:00 +1000 - Codex

Shared decisions:

- Use the existing search-input resolver as the front door.
- The supercharged search bar is the section-aware evidence planner, not just
  a parser.
- The backend should turn the interpreted input into a `ReportExtractionPlan`
  that maps source queries to report sections.
- Add one optional `ReportPayload.report_profile` group for the new typed
  report sections.
- ClinGen/VCEP source assertions outrank ClinVar aggregate evidence.
- ClinVar is the main fallback for clinical consensus and VCV details.
- Eamos-computed ACMG evidence remains worksheet hints, not final
  classification.
- Publications are all variant-related PubMed rows; functional studies stay a
  separate count.
- Clinical trials may be gene-level or disease-level, but must be labeled.
- Existing report-profile sections must be gene-agnostic before adding more
  visible gnomAD detail: non-RPE65 variants must degrade cleanly and never
  receive RPE65 fixture facts.
- Population Frequency card links to Section 3 and expands the gnomAD panel.
- Section 2 remains disease mechanism/inheritance only.
- Add a Section 2-adjacent expandable gene-context snapshot, but keep disease
  mechanism/inheritance fields semantically separate from locus/sequence
  visuals.
- The gene-context snapshot should reuse the Workbench gene-viewer data model,
  but render as a static report snapshot: no scrolling, zooming, editing, or
  manipulation.
- The gene-context snapshot has two stacked static views: a full transcript
  exon/intron overview with the variant pinned, then a zoomed variant
  neighborhood view in the exon/window style used by Workbench.
- The report snapshot should include an `Open in Workbench` deep link carrying
  `gene`, `cdna`, and `transcript`, so it acts as a product teaser without
  making the report itself interactive.
- Raw gnomAD metrics live in `population_frequency_detail` and Section 3, not
  in the ACMG ledger.
- No Patient Report Pipeline (`/runs`) or AlphaMissense work.

## Task 1 - Section-Aware Search Extraction Plan - DONE 2026-05-23

**Goal**

Make the search bar output drive accurate report population by creating a
section-aware extraction plan from the interpreted user input.

**Context**

The search bar is the product front door. It must extract the variant, gene,
disease context, aliases, and source-specific query bundle that decide what
data populates each report card and section.

**Relevant Files Or References**

- `app/backend/app/services/search_input_interpreter.py`
- `app/backend/app/services/search_input_resolver.py`
- `app/backend/app/services/search_candidate_resolver.py`
- future `app/backend/app/services/report_extraction_plan.py`
- `plans/search-bar-ai-input/spec.md`
- `plans/variant-report-data-orchestration/spec.md`

**Proposed Approach**

Add an internal `ReportExtractionPlan` builder that consumes
`SearchInputInterpretation` and `SearchInputResolution`. It emits canonical
identity, source-query bundle, and section targets with match levels:
variant-level, gene-level, disease-level, or unavailable. Use the plan to gate
source calls and section labels.

**Acceptance Criteria**

- Exact variant input produces variant-level targets for variant-specific
  sections.
- Gene/disease-only input cannot silently populate variant-level sections.
- ClinicalTrials.gov targets can degrade to gene-level with explicit labeling.
- Publication queries keep variant aliases distinct from gene fallback terms.
- Computational and ACMG sections require validated allele identity before
  showing variant-specific scores or criteria.

**Source Reference**

Spec sections "Requirements", "Data Flow", and "Additive Schemas".

**Verify**

```bash
cd app/backend
python -m pytest tests/test_variant_search_integration.py tests/test_search_input_resolver.py -q
```

**Out Of Scope**

Frontend rendering and new live source adapters.

**Implementation note:** Added
`app/backend/app/services/report_extraction_plan.py` with a
`ReportExtractionPlanBuilder` that consumes `SearchInputInterpretation` and
`SearchInputResolution`, emits canonical identity, source-query bundles, and
section targets, and gates variant-level sections when the input only reaches
gene/disease level or still requires confirmation. Publication variant aliases
and gene fallback terms are represented separately.

## Task 2 - Schema And Provenance Spine - DONE 2026-05-23

**Goal**

Add the additive schema surface for the full report layout without changing
existing clients.

**Context**

`ReportPayload` already has call cards, population detail, publications, and
functional evidence. The new layout needs typed sections for header, AI
summary, disease mechanism, molecular context, computational deep dive, ACMG
worksheet, therapies/trials, and provenance.

**Relevant Files Or References**

- `plans/variant-report-data-orchestration/spec.md`
- `app/backend/app/schemas/run.py`
- `app/backend/tests/test_frontend_contract.py`
- `app/backend/tests/test_variant_search_integration.py`

**Proposed Approach**

Add `SourceProvenance`, section models, and optional
`ReportPayload.report_profile`, including either `ReportExtractionPlan` or a
sanitized audit view of it. Add backend-only contract canary coverage like the
existing pending frontend mirror maps. Populate a fixture-mode profile with
minimal values from the existing RPE65 fixture stack.

**Acceptance Criteria**

- Existing `ReportPayload` fields remain unchanged.
- `/api/v1/lookup` returns `report_profile` in fixture mode.
- Every section has either typed data or null/empty state plus warnings.
- Contract canary records pending frontend mirror fields instead of failing
  before Claude mirrors TypeScript.

**Source Reference**

Spec sections "Additive Schemas" and "Invariants".

**Verify**

```bash
cd app/backend
python -m pytest tests/test_frontend_contract.py tests/test_variant_search_integration.py -q
```

**Out Of Scope**

Live source adapters and frontend rendering.

**Implementation note:** Added additive report-profile schemas in
`app/backend/app/schemas/run.py`, including `SourceProvenance`,
`ReportExtractionPlan`, typed report sections, `TherapiesTrialsSection`, and
optional `ReportPayload.report_profile`. The first slice omits `therapy_rows`
until an approved therapy source lands. Contract canary coverage records
`report_profile` as a pending frontend mirror field and verifies the backend
model fields.

## Task 3 - Report Orchestrator Service - DONE 2026-05-23

**Goal**

Centralize section assembly so `LookupService` does not become a long chain of
section-specific formatting logic.

**Context**

`LookupService` currently builds the baseline payload and attaches call cards.
The new sections need shared provenance, warning, and source-priority logic.

**Relevant Files Or References**

- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/report_call_cards.py`
- future `app/backend/app/services/variant_report_orchestrator.py`
- future `app/backend/app/services/report_provenance.py`

**Proposed Approach**

Add a `VariantReportDataOrchestrator` that accepts the extraction plan,
normalized variant, evidence map, raw source payloads, source statuses, and
existing detail groups. It returns `VariantReportProfile`. Keep source calls in
tools/adapters, not in the final formatting methods.

**Acceptance Criteria**

- `LookupService` delegates section profile construction to one service.
- Source status and warnings are represented consistently across sections.
- Missing evidence does not crash the report.
- Fixture lookup still includes four call cards and existing publication/
  functional groups.

**Source Reference**

Spec sections "Components", "Data Flow", and "Cache And Freshness".

**Verify**

```bash
cd app/backend
python -m pytest tests/test_variant_search_integration.py tests/test_frontend_contract.py -q
python -m ruff check app tests
python -m black --check --target-version py310 app tests
```

**Implementation note:** Added
`app/backend/app/services/report_provenance.py` and
`app/backend/app/services/variant_report_orchestrator.py`. `LookupService`
delegates `report_profile` assembly after existing call cards, population
detail, EP-VLEx, and functional evidence are built. The orchestrator produces
typed header, deterministic summary, disease mechanism, molecular context,
computational deep dive, ACMG worksheet, empty structured trials section with
explicit first-slice warnings, and normalized provenance.

**Verification:** `ruff check app tests`, `black --check --target-version
py310 app tests`, focused orchestration/contract/search/publication/functional/
cache suites, and full backend `python -m pytest -q` passed on 2026-05-23
(existing short test-JWT warnings only).

## Task 4 - ClinGen/ClinVar Clinical Consensus And ACMG Ledger - DONE 2026-05-23

**Goal**

Populate final consensus and worksheet criteria using the correct source
priority.

**Context**

The user expects ClinGen first for expert/ACMG evidence and ClinVar as the next
fallback. Current Card 4 is ClinVar fallback only.

**Relevant Files Or References**

- `app/backend/app/tools/clinvar.py`
- `app/backend/app/services/functional_evidence.py`
- `app/backend/app/tools/clingen.py`
- `app/backend/app/services/clinical_consensus.py`
- `app/backend/app/services/report_call_cards.py`
- `app/backend/app/schemas/run.py`

**Proposed Approach**

Add a ClinGen adapter for ERepo summary classifications. Parse source-asserted
met criteria where available. Extend ClinVar VCV parsing for criteria/comments
and cited PMIDs. Build `AcmgWorksheetLedger` with criterion rows marked
`source_asserted`, `eamos_hint`, or `not_assessed`.

**Acceptance Criteria**

- ClinGen/VCEP classification outranks ClinVar when both are present.
- ClinVar classification is used when ClinGen has no variant record.
- Criteria rows preserve assertion level and source.
- Eamos frequency/splice/computational/functional hints do not overwrite final
  classification.
- Card 4 provenance shows the source actually used.

**Source Reference**

Spec sections "Source Rules" and "Decisions".

**Verify**

```bash
cd app/backend
python -m pytest tests/test_variant_search_integration.py tests/test_functional_evidence.py tests/test_tool_invariants.py -q
```

**Out Of Scope**

Building a full ACMG classifier.

**Implementation note:** Added `ClingenTool` with fixture-backed and live
ERepo summary-classification lookup, plus `ClinicalConsensusBuilder` to choose
ClinGen/VCEP classification ahead of ClinVar and to merge source-asserted ACMG
criteria before Eamos worksheet hints. ClinVar VCV XML comments/attributes can
now contribute source-asserted criteria and PMID refs when available. Card 4,
the Variant Evidence Report header, deterministic interpretation summary, and
`report_profile.acmg_worksheet` now use the clinical-consensus summary; no new
frontend contract fields were added.

**Verification:** `ruff check app tests`, `black --check --target-version
py310 app tests`, focused clinical-consensus/search/functional/tool/contract/
orchestration suites, and full backend `python -m pytest -q` passed on
2026-05-23 (existing short test-JWT warnings only).

## Task 5 - Disease Mechanism And Inheritance Section - DONE 2026-05-23

**Goal**

Populate disease mechanism, inheritance, disease IDs, and validity level from
real gene-disease sources.

**Context**

The layout asks for disease mechanism and inheritance. Current
`associated_conditions` exists, but it is not enough for source-backed
inheritance, penetrance, and gene-disease validity.

**Relevant Files Or References**

- `app/backend/app/schemas/run.py`
- future `app/backend/app/tools/gene_disease.py`
- HGNC REST, ClinGen gene-disease validity, NCBI MedGen, Orphadata
- optional OMIM if licensed

**Proposed Approach**

Normalize gene through HGNC. Query ClinGen gene-disease validity when
available. Use MedGen and Orphadata for disease identifiers, inheritance, and
rare disease relationships. Treat OMIM as optional configuration requiring an
API key/license. Return null values when sources do not provide penetrance.

**Acceptance Criteria**

- Section can show primary condition and inheritance when source-backed.
- Disease identifiers include source prefixes such as MedGen, ORPHA, OMIM, or
  MONDO when available.
- Missing penetrance is null, not fabricated.
- Source provenance is returned per source.

**Source Reference**

Spec sections "Source Rules" and "Error Behavior".

**Verify**

```bash
cd app/backend
python -m pytest tests/test_variant_search_integration.py tests/test_frontend_contract.py -q
```

**Implementation note:** Added `GeneDiseaseTool` plus
`gene_disease_fixtures.json` for source-backed disease mechanism, inheritance,
disease IDs, gene-disease validity, and source provenance. `LookupService` now
runs the adapter during Variant Evidence Report lookup, and
`VariantReportDataOrchestrator` prefers the `gene_disease` evidence group for
`report_profile.disease_mechanism` while retaining a legacy
`associated_conditions` fallback. The RPE65 fixture records HGNC, ClinGen
Gene-Disease Validity, NCBI MedGen, and Orphadata provenance; missing penetrance
stays `null` with `penetrance_not_source_backed`.

**Verification:** focused orchestration/tool/search/contract suites, `ruff
check app tests`, `black --check --target-version py310 app tests`, and full
backend `python -m pytest -q` passed on 2026-05-23 (existing short test-JWT
warnings only).

## Task 6 - Molecular Context And Structural Overlap - DONE 2026-05-23

**Goal**

Populate exon/codon/protein-domain/constraint fields needed by the molecular
context section.

**Context**

The layout wants exon number, codon change, residue, domain, hotspot flag,
LOEUF, ClinGen haploinsufficiency, and overlapping CNV notes.

**Relevant Files Or References**

- `app/backend/app/tools/ensembl_vep.py`
- `app/backend/app/services/sequence_context.py`
- `app/backend/app/tools/gnomad.py`
- future ClinGen dosage adapter
- optional UniProt/AlphaFold/PDB mapping

**Proposed Approach**

Use VEP/MANE and existing sequence context for exon/codon/protein position.
Add gnomAD constraint/download or toolbox-backed LOEUF support behind a
versioned adapter. Add ClinGen dosage sensitivity as a source-backed field.
Keep structural domain mapping optional until a stable source is selected.

**Acceptance Criteria**

- The section returns transcript/exon/codon/protein-position details when
  resolvable.
- LOEUF and dosage fields include source release/version.
- No domain/hotspot value appears without source provenance.
- Reverse-strand variants are tested.

**Source Reference**

Spec section "Source Rules"; existing gene-viewer reverse-strand risks.

**Verify**

```bash
cd app/backend
python -m pytest tests/test_search_input_resolver.py tests/test_variant_search_integration.py -q
```

**Implementation note:** Added `MolecularContextTool` plus
`molecular_context_fixtures.json` for source-backed RPE65 gnomAD LOEUF and
ClinGen dosage sensitivity provenance. `LookupService` now runs the
`molecular_context` adapter and internally resolves existing sequence context
for codon/strand detail. `VariantReportDataOrchestrator` now populates
`report_profile.molecular_context` from source-prioritized VEP,
VariantValidator, sequence-context, and molecular-context evidence: exon 4,
reverse strand, `GAC>GGC`, protein position 87, LOEUF 1.0, and ClinGen
haploinsufficiency. Domain, hotspot, and structural CNV overlap remain empty
with explicit not-hydrated warnings.

**Verification:** focused orchestration/tool/search/contract suites, `ruff
check app tests`, `black --check --target-version py310 app tests`, and full
backend `python -m pytest -q` passed on 2026-05-23 (existing short test-JWT
warnings only).

## Task 7 - Computational Annotation Stack - DONE 2026-05-23

**Goal**

Populate the computational deep dive with source-labeled SpliceAI, REVEL, CADD,
PrimateAI-3D, conservation, and legacy predictor rows.

**Context**

The user noted that some public tools co-display multiple predictors. The
backend should store each metric under its true source and version. SpliceAI is
not the source of REVEL/CADD/PrimateAI-3D.

**Relevant Files Or References**

- `app/backend/app/tools/spliceai.py`
- future `app/backend/app/tools/computational_annotations.py`
- MyVariant.info docs
- dbNSFP docs
- CADD API docs
- Illumina SpliceAI docs

**Proposed Approach**

Implement a normalized computational annotation adapter. First slice can use
fixture/MyVariant/dbNSFP-like rows. Target path for SpliceAI is local or
precomputed VCF output. CADD can use direct small SNV API or local files.
PrimateAI-3D should be local/licensed data only. AlphaMissense values are
filtered while on hold.

**Acceptance Criteria**

- SpliceAI DS/DP rows show max delta and component scores.
- REVEL, CADD, and PrimateAI-3D rows include source/version.
- AlphaMissense is not surfaced.
- Missing scores are omitted or warning-labeled, never copied from fixtures for
  another variant.

**Source Reference**

Spec sections "Source Rules" and "Versions".

**Verify**

```bash
cd app/backend
python -m pytest tests/test_variant_search_integration.py tests/test_tool_invariants.py -q
```

**Implementation note:** Added `ComputationalAnnotationsTool` plus
`computational_annotations_fixtures.json` for a normalized, source-labeled
computational deep-dive slice. `LookupService` now runs the adapter during
Variant Evidence Report lookup, and `VariantReportDataOrchestrator` prefers the
new evidence over legacy in-silico cards. The RPE65 fixture returns SpliceAI
DS/DP component scores with max delta/consequence, REVEL, CADD PHRED,
PrimateAI-3D, MetaLR, and conservation rows with source/version labels.
AlphaMissense remains excluded/on hold. Missing variants return empty/missing
state without fixture bleed.

**Verification:** focused tool/orchestration/search/contract suites, `ruff
check app tests`, `black --check --target-version py310 app tests`, and full
backend `python -m pytest -q` passed on 2026-05-23 (existing short test-JWT
warnings only).

## Task 8 - Publications And Functional Evidence Integration Check - DONE 2026-05-23

**Goal**

Make the publication grid and functional card/detail semantics explicit in the
new report profile.

**Context**

EP-VLEx already implements the general publication inventory. Functional
evidence already implements a separate functional-study count.

**Relevant Files Or References**

- `app/backend/app/services/publication_literature.py`
- `app/backend/app/services/functional_evidence.py`
- `plans/variant-literature-extraction/plan.md`

**Proposed Approach**

Reference existing `publications_literature` and `functional_evidence` from the
report profile/provenance, without duplicating their row data. Add tests that
prove broad publication count and functional-study count can differ.

**Acceptance Criteria**

- General publication total remains EP-VLEx count.
- Functional evidence total remains functional-study count.
- The report profile labels both counts correctly.
- The first publication page remains capped and paginated.

**Source Reference**

User clarification in `plans/variant-literature-extraction/plan.md`.

**Verify**

```bash
cd app/backend
python -m pytest tests/test_publication_literature.py tests/test_functional_evidence.py tests/test_variant_search_integration.py -q
```

**Implementation note:** Added a focused integration test proving EP-VLEx
publication inventory and functional-study counts stay separate in the Variant
Evidence Report. The test verifies publication total `3`, functional-study
total `1`, the functional card `1 Unique` badge, report-profile section targets
for publications and lab-functional evidence, no duplicated article/study rows
inside `report_profile`, and `/api/v1/lookup/publications` pagination.

**Verification:** publication/functional integration focused suites, `ruff
check app tests`, `black --check --target-version py310 app tests`, and full
backend `python -m pytest -q` passed on 2026-05-23 (existing short test-JWT
warnings only).

## Task 9 - Structured Therapies And Clinical Trials - IN PROGRESS

**Goal**

Replace the text-only therapy/trial summary with structured rows suitable for
the Precision Therapies and Active Clinical Trials section.

**Context**

The current `ClinicalTrialsTool` returns a string summary. The layout needs
NCT ID, title, status, phase, interventions, conditions, sites, and match
level.

**Relevant Files Or References**

- `app/backend/app/tools/clinical_trials.py`
- future `app/backend/app/tools/therapies_trials.py`
- `app/backend/app/services/lookup_service.py`
- ClinicalTrials.gov API v2 docs
- optional CIViC, ClinPGx/PharmGKB, openFDA/FDA PGx table

**Proposed Approach**

Add structured ClinicalTrials.gov v2 parser and service. Query exact variant
aliases first, then gene plus disease terms, then gene alone. Add `match_level`
based on explicit term matches. Keep therapy rows empty or fixture-backed until
approved therapy sources are implemented. Consider CIViC only for oncology
contexts and PharmGKB/openFDA only as optional licensed/gated follow-ups.

**Acceptance Criteria**

- Trial rows include NCT URL and current recruitment status.
- Rows are labeled `variant_level`, `gene_level`, or `disease_level`.
- Gene-level rows appear when no variant-level rows exist.
- No row implies patient eligibility.
- Source failures return empty rows and warnings.

**Source Reference**

Spec section "ClinicalTrials.gov".

**Verify**

```bash
cd app/backend
python -m pytest tests/test_variant_search_integration.py tests/test_frontend_contract.py -q
```

Optional live smoke after approval:

```bash
cd app/backend
$env:USE_REAL_APIS='true'
python -m pytest tests/test_clinical_trials_tool.py -q
```

**Implementation note:** Parallel first slice added a backend-only
ClinicalTrials.gov v2 parser/helper in `clinical_trials.py`, with structured
query/match objects, NCT discovery links, status/phase/intervention/condition
extraction, `variant_level`/`gene_level`/`disease_level` labels, query fallback
ordering, and no-eligibility warnings. Integration into
`report_profile.therapies_trials.trial_rows` remains pending.

**Verification:** focused clinical-trials tests, `ruff check app tests`,
`black --check --target-version py310 app tests`, and full backend
`python -m pytest -q` passed on 2026-05-23 (existing short test-JWT warnings
only).

## Task 10 - Interpretation Summary Builder

**Goal**

Generate the AI interpretation summary from already-assembled source-backed
facts.

**Context**

The layout includes a summary paragraph. This should summarize the evidence
already in the report, not become an independent evidence source.

**Relevant Files Or References**

- `app/backend/app/agents/client.py`
- `app/backend/app/agents/prompts.py`
- future `VariantReportDataOrchestrator`
- `app/backend/app/schemas/run.py`

**Proposed Approach**

Implement deterministic summary templates first. If LLM mode is later enabled,
pass only the report fact bundle and require fact references in the structured
output. If the model is unavailable, keep deterministic summary or mark
summary unavailable.

**Acceptance Criteria**

- Summary references card/section facts only.
- It includes warnings when core sources are missing.
- LLM mode cannot add facts not present in the fact bundle.
- Mock mode is deterministic and CI-safe.

**Source Reference**

Spec sections "Requirements" and "Error Behavior".

**Verify**

```bash
cd app/backend
python -m pytest tests/test_variant_search_integration.py -q
```

## Task 11 - Verification, Docs, And Frontend Handoff

**Goal**

Prove the backend report profile is stable and give Claude the exact mirror and
rendering contract.

**Context**

Claude owns frontend mirror/search UX/report rendering by default. Contract
changes are backend-led but frontend mirror is a separate lane task.

**Relevant Files Or References**

- `app/backend/tests/test_frontend_contract.py`
- `agent_handoff/CURRENT.md`
- `plans/variant-report-data-orchestration/{design.md,spec.md,plan.md}`
- `app/frontend/src/lib/backend.ts`

**Proposed Approach**

Run focused backend tests and full backend tests after implementation. Update
pending frontend mirror field list. File a cross-agent request naming the new
models, section order, and invariants.

**Acceptance Criteria**

- Backend tests pass.
- Contract canary is either green or has explicit pending frontend mirror
  fields.
- Cross-agent request tells Claude exactly what to mirror/render.
- No frontend edits are made by Codex unless the user redirects ownership.

**Verify**

```bash
cd app/backend
python -m ruff check app tests
python -m black --check --target-version py310 app tests
python -m pytest -q
```

**Out Of Scope**

Frontend implementation, browser verification, commit, push, stash, reset, or
clean.

## Task 11A - Gene-Agnostic Report Profile Regression Gate - DONE 2026-05-23

**Goal**

Harden the existing Variant Evidence Report profile so search and output are
gene-agnostic before adding the more visible Section 3 gnomAD expansion.

**Context**

Tasks 1-8 proved the RPE65-rich report-profile path and added first-slice
adapters for clinical consensus, disease mechanism, molecular context,
computational annotations, publications/functional semantics, and
ClinicalTrials.gov parsing. The next risk is fixture bleed: a non-RPE65 lookup
must not receive RPE65 disease, molecular, computational, ACMG, gnomAD,
publication, functional, or trial facts.

The target is not full rich data for every gene yet. The target is safe,
gene-agnostic degradation: empty/null/warning-labelled sections when a source
or fixture does not match the current variant identity.

**Relevant Files Or References**

- `app/backend/app/services/search_input_resolver.py`
- `app/backend/app/services/report_extraction_plan.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/services/clinical_consensus.py`
- `app/backend/app/services/publication_literature.py`
- `app/backend/app/services/functional_evidence.py`
- `app/backend/app/tools/{gnomad,clinvar,variant_validator,ensembl_vep,computational_annotations,gene_disease,molecular_context,clinical_trials}.py`
- `app/backend/app/fixtures/tools/*.json`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_search_input_resolver.py`
- `app/backend/tests/test_gnomad_tool.py`
- `app/backend/tests/test_clinical_consensus.py`
- `app/backend/tests/test_publication_literature.py`
- `app/backend/tests/test_functional_evidence.py`
- `app/backend/tests/test_clinical_trials_tool.py`

**Proposed Approach**

Use a multi-gene regression matrix and then patch only the failing adapters or
orchestrator paths:

- RPE65 `c.260A>G`: rich fixture happy path remains populated.
- RPE65 `c.11+5G>A`: splice-adjacent/functional-prior path remains
  source-labelled.
- USH2A `c.2276G>T`: different-gene path does not inherit RPE65 report-profile
  facts.
- BRCA1 `c.5266dup`: indel normalization path does not inherit SNV/RPE65
  facts.
- RPGRIP1 `c.1997C>T`: sparse/no-hit path returns warning-labelled
  unavailable sections instead of unrelated fallback data.
- CFTR Leu441 ambiguity: returns suggestions/confirmation and does not build a
  report-runnable payload without a selected source-backed candidate.

**Parallel Next-Session Execution Model**

Codex orchestrator owns shared schema/contract changes and final integration
locally. Subagents can run in parallel on disjoint, read-heavy or focused
write scopes:

1. Fixture Bleed Audit Agent: inspect adapters/fixtures for identity guards and
   propose exact failing paths for non-RPE65 variants.
2. Multi-Gene Test Matrix Agent: add or plan focused regression cases for the
   six-variant matrix and report expected section states.
3. Clinical/ACMG Semantics Agent: verify PM2/BA1/BS1 and interpretation
   summary wording stay source-scoped and do not expose raw gnomAD metrics.
4. Section 3 gnomAD Worker: after Codex lands/controls shared schema shape,
   implement the gnomAD section builder/tests or a disjoint slice if assigned.

If subagents edit files, keep write sets disjoint. Codex should integrate and
run the final verification suite.

**Acceptance Criteria**

- RPE65 rich fixture report remains populated and current tests stay green.
- USH2A, BRCA1, and RPGRIP1 do not receive RPE65 disease mechanism,
  molecular-context, computational, ACMG, gnomAD, publication, functional, or
  trial facts.
- Gene-only/disease-only/ambiguous inputs keep variant-level sections
  unavailable or require confirmation.
- gnomAD no-hit and fallback mismatch do not attach fixture metrics.
- Interpretation summary cites only facts present for the current lookup.
- Publication inventory and functional evidence counts remain separate across
  non-RPE65 examples.
- Source failures degrade one section at a time and do not fail the whole
  lookup.

**Source Reference**

Spec requirements 20, 23, and 24; Invariants; Error Behavior.

**Verify**

```bash
cd app/backend
python -m pytest tests/test_variant_report_orchestration.py tests/test_variant_search_integration.py tests/test_search_input_resolver.py -q
python -m pytest tests/test_gnomad_tool.py tests/test_clinical_consensus.py tests/test_publication_literature.py tests/test_functional_evidence.py tests/test_clinical_trials_tool.py -q
python -m ruff check app tests
python -m black --check --target-version py310 app tests
python -m pytest -q
```

**Out Of Scope**

Frontend edits/rendering, browser verification, broad local data warehouse,
Patient Report Pipeline (`/runs`), AlphaMissense, commit, push, stash, reset,
or clean.

**Implementation note:** Added source-identity guards to fixture/fallback paths
for VariantValidator, VEP, SpliceAI, gnomAD, ClinVar, PubMed, and LitVar2 so a
nonmatching lookup returns empty/unavailable data instead of the RPE65 snapshot.
Added the six-variant regression matrix for RPE65 `c.260A>G`, RPE65
`c.11+5G>A`, USH2A `c.2276G>T`, BRCA1 `c.5266dup`, RPGRIP1 `c.1997C>T`, and
the CFTR Leu441 ambiguity path. Added a source-scoped ClinGen fixture for RPE65
`c.11+5G>A` so PS3/functional-prior behavior is proven without borrowing
`c.260A>G` facts. Sanitized ACMG rationale text and stopped call-card badges
from deriving PM2/BA1/BS1 directly from raw gnomAD metrics.

## Task 12 - Section 3 gnomAD Expansion Panel - DONE 2026-05-23

**Goal**

Add a backend/contract slice for a Section 3 gnomAD expansion panel linked
from the Population Frequency card.

**Context**

The user supplied gnomAD expansion briefs on 2026-05-23. The requested report
behavior is:

- Population Frequency card click scrolls to Section 3 and expands the gnomAD
  panel.
- Section 2 remains disease mechanism/inheritance only.
- The ACMG ledger stays clean and does not repeat raw gnomAD metrics.
- Codex owns backend/contract planning locally; Claude owns frontend rendering
  unless explicitly redirected.

Current backend state:

- `ReportPayload.population_frequency_detail` already carries the selected
  gnomAD summary: dataset, variant ID, sequencing type, AF, AC, AN,
  homozygotes, popmax, genetic ancestry group rows, age distribution, flags,
  warnings, and source URL.
- `ReportPayload.call_cards` already includes a compact Population Frequency
  card built from that detail.
- `VariantReportProfile.disease_mechanism` already owns Section 2-style disease
  mechanism/inheritance data.
- Task 11A should be run in the same next session before or alongside Task 12
  so non-RPE65 lookups are proven not to inherit RPE65 report-profile facts.

**Relevant Files Or References**

- `app/backend/app/schemas/run.py`
- `app/backend/app/services/report_call_cards.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- recommended new `app/backend/app/services/population_frequency_section.py`
- `app/backend/app/tools/gnomad.py`
- `app/backend/app/fixtures/tools/gnomad_fixtures.json`
- `app/backend/tests/test_gnomad_tool.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_frontend_contract.py`
- supplied docs:
  - `Population world heat map idea.txt`
  - `Technical Specification - Backend Component Architecture & Local Prototype.txt`

**Proposed Approach**

1. Add optional `ReportCallInteraction` and `ReportCallCard.interaction` in
   `run.py`. The Population Frequency card should emit:
   - `action="scroll_and_expand"`
   - `target_section_id="section-3-population-frequency"`
   - `target_panel_id="gnomad-expansion"`
2. Add a typed `VariantReportProfile.population_frequency` Section 3 model
   with section number/IDs, source status, dataset/build/variant ID, visual
   scale, genetic ancestry visual groups, overall age histogram views,
   source/QC rows, warnings, source URL, and provenance.
3. Keep `population_frequency_detail` as the canonical raw/source detail group.
   The Section 3 model is a render-ready projection with a clear
   `detail_ref="population_frequency_detail"`.
4. Add `population_frequency_section.py` to build the Section 3 model from the
   existing population detail. Do not query new external sources in this slice.
5. Extend `gnomad_fixtures.json` only enough to cover the existing core genetic
   ancestry groups and Section 3 visual states.
6. Keep current age distribution scope explicit as overall gnomAD release
   sample bins. Do not fabricate per-genetic-ancestry age histograms.
7. Keep ACMG PM2/BA1/BS1 rows source-asserted or Eamos-hint only, with no raw
   gnomAD metric text in ledger rationale.
8. Preserve Task 11A gene-agnostic invariants while implementing Section 3:
   non-RPE65 no-hit or sparse-source variants get unavailable/warning-labelled
   Section 3 state, not RPE65 gnomAD fixture detail.

**Acceptance Criteria**

- `/api/v1/lookup` returns the existing `population_frequency_detail` unchanged
  for existing clients.
- Population Frequency card has navigation metadata for Section 3 expansion.
- `report_profile.population_frequency.section_number == 3`.
- Section 3 exposes map/bar/table-ready gnomAD genetic ancestry rows using
  genetic ancestry group language.
- Section 3 exposes age histogram views only at their true source scope.
- Section 2 disease mechanism contains no gnomAD AF/AC/AN/popmax, genetic
  ancestry, or age fields.
- ACMG worksheet rationale contains no raw gnomAD AF/AC/AN/popmax,
  homozygote, genetic ancestry, or age-bin values.
- Gene-only/disease-only unresolved input does not populate variant-level
  gnomAD detail or frequency hints.
- Fallback fixture mismatch does not attach RPE65 gnomAD metrics to another
  variant.

**Source Reference**

Spec sections "Requirements", "Additive Schemas", "Source Rules", and
"Invariants"; supplied gnomAD progressive-disclosure and backend architecture
briefs.

**Verify**

```bash
cd app/backend
python -m pytest tests/test_variant_report_orchestration.py tests/test_report_call_cards.py tests/test_gnomad_tool.py -q
python -m pytest tests/test_variant_search_integration.py tests/test_clinical_consensus.py tests/test_frontend_contract.py -q
python -m pytest tests/test_tool_invariants.py -q
python -m ruff check app tests
python -m black --check --target-version py310 app tests
python -m pytest -q
```

**Out Of Scope**

Frontend rendering, browser verification, Patient Report Pipeline (`/runs`),
AlphaMissense, production gnomAD ETL/warehouse, per-hover API endpoint, local
DuckDB/parquet prototype, commit, push, stash, reset, or clean.

**Implementation note:** Added additive `ReportCallInteraction` plus
`ReportCallCard.interaction`, the `VariantReportProfile.population_frequency`
Section 3 schema group, and
`app/backend/app/services/population_frequency_section.py`. The builder projects
the existing canonical `population_frequency_detail` into Section 3 with
`detail_ref="population_frequency_detail"`, section ID
`section-3-population-frequency`, panel ID `gnomad-expansion`, genetic ancestry
group rows, overall release-sample age histogram scope, source/QC rows,
warnings, source URL, and provenance. Population Frequency cards now carry
`scroll_and_expand` metadata to Section 3.

**Verified 2026-05-23 19:51 +1000 - Codex:**

```bash
cd app/backend
python -m pytest tests/test_variant_report_orchestration.py tests/test_report_call_cards.py tests/test_gnomad_tool.py tests/test_clinical_consensus.py tests/test_variant_search_integration.py tests/test_search_input_resolver.py -q
python -m pytest tests/test_frontend_contract.py tests/test_tool_invariants.py tests/test_publication_literature.py tests/test_functional_evidence.py tests/test_clinical_trials_tool.py -q
python -m ruff check app tests
python -m black --check --target-version py310 app tests
python -m pytest -q
```

## Task 13 - Gene Context Snapshot Data Contract - DONE 2026-05-24 00:00 +1000 - Codex

**Goal**

Add the backend/report contract data needed for a static Section 2-adjacent
gene-context snapshot that is accurate for any supported gene and transcript.

**Context**

The report should show where the variant sits in the gene before the user
opens Workbench. The snapshot is intentionally static and report-safe, but it
must use the same source-backed gene-viewer architecture as Workbench. Do not
borrow the RPE65 sample scaffold for other genes.

The current Workbench live path can resolve coding cDNA SNVs through
VariantValidator and Ensembl sequence/region. The missing report-safe contract
piece is the full transcript exon/intron model needed for an all-exons overview
and a deterministic zoomed variant-neighborhood snapshot.

**Relevant Files Or References**

- `app/backend/app/schemas/gene_viewer.py`
- `app/backend/app/schemas/run.py`
- `app/backend/app/services/gene_viewer.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/tests/test_gene_viewer.py`
- `app/backend/tests/test_frontend_contract.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/frontend/src/lib/workbench/gene-viewer-adapter.ts`
- `plans/gene-viewer/{design.md,spec.md,plan.md}`
- `c:\Users\seamegdool\Desktop\Claude code and website tips\EAMOS Web Tool\variant-search-engine\Variant Report Page\Layout - VARIANT REPORT 2.txt`

**Proposed Approach**

Add an additive `gene_context_snapshot` model, either inside
`VariantReportProfile` or as a referenced report payload group. It should carry:

- canonical gene, transcript, genome build, chromosome, strand, and source
  provenance;
- full transcript exon/intron rows from Ensembl, with transcript-relative and
  genomic coordinates;
- variant projection on the transcript, including exon/intron membership,
  transcript offset, local sequence window, ref/alt, codon/protein fields when
  available, and warnings when any field is unavailable;
- render hints for a compressed full-transcript overview so very large genes do
  not make exons unreadable;
- a Workbench deep-link target with `gene`, `cdna`, and resolved transcript.

Use the existing `SourceBackedGeneViewerProvider` as the source path. If the
lookup is gene-only, ambiguous, or lacks a validated allele identity, return a
warning-labelled unavailable snapshot rather than a misleading picture.

**Acceptance Criteria**

- RPE65 fixture/current happy path returns a populated static snapshot contract.
- A non-RPE65 live/source-backed gene can return the full transcript model
  without importing the RPE65 scaffold.
- Large or many-exon genes use compressed intron rendering metadata and remain
  mappable.
- Ambiguous or unconfirmed inputs do not populate variant-specific snapshot
  coordinates.
- The contract includes enough data to render the two required static views:
  full transcript overview and zoomed variant neighborhood.
- Frontend contract canary records/mirrors the additive fields.
- `/runs` and AlphaMissense remain untouched.

**Source Reference**

User direction on 2026-05-23: add an expandable report image based on the
Workbench gene viewer, with a full gene/exon-intron context first and a zoomed
variant-in-exon image underneath; static only, and usable as a Workbench teaser.

**Verify**

```bash
cd app/backend
python -m pytest tests/test_gene_viewer.py tests/test_variant_report_orchestration.py tests/test_frontend_contract.py -q
python -m ruff check app tests/test_gene_viewer.py tests/test_variant_report_orchestration.py tests/test_frontend_contract.py
python -m black --check --target-version py310 app tests/test_gene_viewer.py tests/test_variant_report_orchestration.py tests/test_frontend_contract.py
```

**Out Of Scope**

Interactive report viewer controls, Workbench editing/scrolling behavior,
PDF-specific rendering, gnomAD ETL, ClinicalTrials.gov hardening, `/runs`, and
AlphaMissense.

**Implementation note:** Added additive `VariantReportProfile.gene_context_snapshot`
and nested snapshot models in `app/backend/app/schemas/run.py`, mirrored them
in both TypeScript contract files, and added `GeneContextSnapshotService` to
assemble the report-safe static snapshot through the existing gene-viewer source
path. The contract carries full transcript exon/intron rows, variant projection,
the reused Workbench zoom window/segments/sequences, compressed-render hints,
Workbench deep link, provenance, and warning-labelled unavailable states.
Fixture mode returns a populated RPE65 snapshot from the existing Workbench
fixture plus an explicit `transcript_model_from_rpe65_fixture_scaffold` warning;
non-RPE65 fixture lookups return missing/empty state rather than borrowing the
RPE65 scaffold. Source-backed tests prove a generic non-RPE65 transcript returns
its own exon/intron coordinates.

**Verified 2026-05-24 00:00 +1000 - Codex:**

```bash
cd app/backend
python -m pytest tests/test_gene_viewer.py tests/test_variant_report_orchestration.py tests/test_frontend_contract.py -q -x
python -m ruff check app tests/test_gene_viewer.py tests/test_variant_report_orchestration.py tests/test_frontend_contract.py
python -m black --check --target-version py310 app tests/test_gene_viewer.py tests/test_variant_report_orchestration.py tests/test_frontend_contract.py
python -m pytest tests/test_gene_viewer.py tests/test_variant_report_orchestration.py tests/test_frontend_contract.py -q
python -m pytest tests/test_variant_search_integration.py -q

cd ../frontend
npx tsc -b --pretty false

cd ../web
npx tsc --noEmit --pretty false
```

## Task 14 - Static Report Gene Context Snapshot UI - PLANNED 2026-05-23 23:27 +1000 - Codex

**Goal**

Render the report gene-context snapshot as an expandable static section in
Vite and Next, with two stacked images and a Workbench deep link.

**Context**

The report should stay readable and deterministic. The snapshot should feel
visually related to Workbench, but it must not embed a disabled interactive
canvas. Treat it as a report figure generated from the same data model.

**Relevant Files Or References**

- `app/frontend/src/pages/ReportPage.tsx`
- `app/frontend/src/components/report/*`
- `app/frontend/src/components/workbench/*`
- `app/frontend/src/lib/backend.ts`
- `app/frontend/src/lib/workbench/gene-viewer-adapter.ts`
- `app/web/components/report/*`
- `app/web/lib/backend.ts`
- `app/web/components/report/ReportClient.tsx`
- `plans/gene-viewer/{design.md,spec.md,plan.md}`
- `Layout - VARIANT REPORT 2.txt`

**Proposed Approach**

Add a `GeneContextSnapshotSection` in both report frontends. Place it as a
Section 2-adjacent expandable panel after disease mechanism/inheritance and
before the population-frequency Section 3. The panel should render:

1. A full transcript overview with exons, compressed introns, strand, transcript
   label, and a variant pin.
2. A zoomed static sequence/window image using the Workbench visual grammar:
   local exon/window, variant base, ref/alt, codon/protein labels when present,
   and source warnings.

Use SVG or structured HTML/CSS generated from the contract rather than a
pre-rendered raster asset so the result is responsive and future PDF/export
friendly. Add an `Open in Workbench` link to `/workbench?gene=...&cdna=...`
with `transcript` when available.

**Acceptance Criteria**

- The section is collapsed/expandable by default in the report flow without
  disrupting the existing Section 2 disease copy.
- The first snapshot shows the variant in all-exons/introns transcript context.
- The second snapshot shows a zoomed local variant neighborhood.
- The component has a useful empty/warning state for unsupported or ambiguous
  inputs.
- It uses stable dimensions so labels, pins, and sequence text do not resize or
  overlap on mobile or desktop.
- It does not add scrolling, dragging, editing, or zoom controls.
- The Workbench link preserves `gene`, `cdna`, and `transcript`.
- Vite and Next stay visually consistent.

**Source Reference**

User direction on 2026-05-23 and the existing Workbench gene viewer UI.

**Verify**

```bash
cd app/frontend
npx tsc -b --pretty false
npm run build

cd ../web
npx tsc --noEmit --pretty false
npm run build
```

Run browser verification on desktop and mobile for at least RPE65 and one
non-RPE65 source-backed example when the browser MCP or Playwright fallback is
available.

**Out Of Scope**

Backend contract shape decisions, Workbench interaction changes, live gnomAD
warehouse work, `/runs`, and AlphaMissense.

## Task 15 - gnomAD Ancestry Region Mapping Algorithm - PLANNED 2026-05-23 23:27 +1000 - Codex

**Goal**

Turn the current proprietary ancestry-to-map rendering logic into a documented,
testable algorithm that maps gnomAD genetic ancestry groups to report map
regions without implying patient ancestry or geographic certainty.

**Context**

Section 3 currently renders a first-slice gnomAD map/card from source genetic
ancestry groups. The next production step is to harden the group-to-region
mapping so it is auditable, deterministic, and safe for clinical/research
language.

**Relevant Files Or References**

- `app/backend/app/services/population_frequency_section.py`
- `app/backend/app/services/report_call_cards.py`
- `app/backend/app/tools/gnomad.py`
- `app/frontend/src/components/report/PopulationFrequencySection.tsx`
- `app/web/components/report/PopulationFrequencySection.tsx`
- `app/backend/tests/test_gnomad_tool.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `docs/proprietary/index.json`
- recommended new doc: `docs/proprietary/gnomad-ancestry-map.md`

**Proposed Approach**

Create a small, explicit mapping table for gnomAD group IDs (`afr`, `amr`,
`asj`, `eas`, `fin`, `mid`, `nfe`, `sas`, `ami`, `remaining`) to visual map
regions and labels. Document that this is source genetic-ancestry group
visualization, not patient ancestry inference. Keep unmapped or future gnomAD
groups visible as table rows with a neutral/unmapped map state rather than
dropped.

**Acceptance Criteria**

- Every current gnomAD fixture group maps to a deterministic visual state or a
  documented neutral fallback.
- Labels consistently use "genetic ancestry group" language.
- Tests prove unmapped groups do not crash the report and are not silently
  omitted.
- The proprietary index points to the algorithm doc.
- No patient ancestry/age inference is introduced.

**Source Reference**

Task 12 Section 3 gnomAD expansion and the user request to harden proprietary
ancestry-to-region mapping into a documented, testable algorithm.

**Verify**

```bash
cd app/backend
python -m pytest tests/test_gnomad_tool.py tests/test_variant_report_orchestration.py -q
python -m ruff check app tests/test_gnomad_tool.py tests/test_variant_report_orchestration.py
python -m black --check --target-version py310 app tests/test_gnomad_tool.py tests/test_variant_report_orchestration.py
```

**Out Of Scope**

Local gnomAD warehouse, per-hover detail endpoint, and frontend visual redesign
beyond labels/states needed by the algorithm.

## Task 16 - gnomAD Local Data Access Prototype - PLANNED 2026-05-23 23:27 +1000 - Codex

**Goal**

Prototype production-grade gnomAD data access using a local DuckDB/parquet or
warehouse-shaped adapter so hover/source-detail queries do not depend on
fixtures or broad live GraphQL calls.

**Context**

The current report can render gnomAD fixture/live summaries, but a production
experience needs reliable variant-level detail, source metadata, and fast
lookup for per-group hover/details. The prototype should validate data shape
and query patterns before a final infrastructure choice.

**Relevant Files Or References**

- `app/backend/app/tools/gnomad.py`
- `app/backend/app/services/population_frequency_section.py`
- `app/backend/app/schemas/run.py`
- `app/backend/tests/test_gnomad_tool.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- recommended prototype path: `app/backend/app/services/gnomad_local_store.py`
- recommended prototype tests: `app/backend/tests/test_gnomad_local_store.py`

**Proposed Approach**

Define an adapter interface that can be backed by DuckDB/parquet locally and by
a warehouse later. First slice should use a tiny checked-in or generated test
parquet/CSV fixture to prove:

- lookup by normalized GRCh38 variant ID;
- allele frequency/count/number by genetic ancestry group;
- popmax, homozygotes, quality flags, dataset/build, and source version;
- age histogram availability and scope;
- missing variant behavior.

Keep `GnomadTool` responsible for returning the same normalized summary shape
so existing report builders remain stable.

**Acceptance Criteria**

- Local adapter returns the same normalized summary shape as the current tool.
- Missing variants return a no-hit state without borrowing fixture data.
- Source version, dataset, and build are preserved in provenance.
- Tests cover at least one hit and one no-hit.
- The prototype can be swapped out for a warehouse without changing frontend
  contracts.

**Source Reference**

User next-step direction: productionize gnomAD data access via ETL/warehouse or
local DuckDB/parquet prototype, then per-hover/source-detail endpoint.

**Verify**

```bash
cd app/backend
python -m pytest tests/test_gnomad_tool.py tests/test_variant_report_orchestration.py tests/test_gnomad_local_store.py -q
python -m ruff check app tests
python -m black --check --target-version py310 app tests
```

**Out Of Scope**

Full public gnomAD ETL download, cloud warehouse deployment, frontend hover UI,
patient ancestry inference, `/runs`, and AlphaMissense.

## Task 17 - gnomAD Per-Hover Source Detail Endpoint - PLANNED 2026-05-23 23:27 +1000 - Codex

**Goal**

Add a lightweight endpoint and frontend data path for source-detail disclosure
when the user hovers/selects a gnomAD ancestry group or source row.

**Context**

Section 3 already has a visual map/card. The next UX step is progressive
disclosure: the top-level report stays compact, while hover/select exposes the
exact source values, dataset/build, warnings, and provenance for the selected
group.

**Relevant Files Or References**

- `app/backend/app/api/routes/lookup.py`
- `app/backend/app/tools/gnomad.py`
- `app/backend/app/services/population_frequency_section.py`
- `app/backend/app/schemas/run.py`
- `app/frontend/src/components/report/PopulationFrequencySection.tsx`
- `app/web/components/report/PopulationFrequencySection.tsx`
- `app/frontend/src/lib/backend.ts`
- `app/web/lib/backend.ts`

**Proposed Approach**

Add a small source-detail endpoint keyed by canonical variant identity and
gnomAD group ID, or embed enough detail in the existing payload if endpoint
latency/provenance does not justify a round trip. Use the local adapter from
Task 16 when available; otherwise fixture mode can return deterministic detail
for the current RPE65 example.

**Acceptance Criteria**

- Hover/select detail can show AF, AC, AN, homozygotes, data state, source URL,
  dataset/build, and warnings for one gnomAD group.
- Unknown group IDs return a structured 404/empty state, not a crash.
- Detail remains keyed to the current variant and cannot return RPE65 data for
  another variant.
- Frontend keeps keyboard/touch fallback for non-hover devices.
- Existing Section 3 render works without this endpoint if detail is
  unavailable.

**Source Reference**

Task 12 Section 3 gnomAD expansion and the production gnomAD data-access plan.

**Verify**

```bash
cd app/backend
python -m pytest tests/test_gnomad_tool.py tests/test_variant_report_orchestration.py -q

cd ../frontend
npx tsc -b --pretty false
npm run build

cd ../web
npx tsc --noEmit --pretty false
npm run build
```

**Out Of Scope**

Full gnomAD ETL, broad map redesign, patient ancestry inference, `/runs`, and
AlphaMissense.

## Task 18 - ClinicalTrials.gov Live Filtering And Provenance Hardening - PLANNED 2026-05-23 23:27 +1000 - Codex

**Goal**

Extend ClinicalTrials.gov from demo/report rows into robust live filtering,
match-level labeling, and provenance.

**Context**

Structured ClinicalTrials.gov rows now flow into the report profile in
controlled tests, but production behavior needs stronger live filtering and
source transparency. Trials may be variant-, gene-, disease-, therapy-, or
condition-level; the report must label that honestly.

**Relevant Files Or References**

- `app/backend/app/tools/clinical_trials.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/schemas/run.py`
- `app/backend/tests/test_clinical_trials_tool.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/frontend/src/components/report/TrialsSection.tsx`
- `app/web/components/report/TrialsSection.tsx`

**Proposed Approach**

Harden query construction, status filtering, deduplication, and match-level
classification. Capture query terms, source URL, API status, filters applied,
trial status, phase, conditions, interventions, locations, and warnings. Keep
gene-level and disease-level rows visible only when labelled as not
variant-specific.

**Acceptance Criteria**

- Live/filter tests cover recruiting/active status, completed status exclusion
  or labeling, gene-level fallback, and no-hit behavior.
- Every row has an NCT ID, source URL, status, match level, and matched terms.
- The report never implies a gene-level trial is variant-specific.
- Source failures degrade the trials section without failing the whole report.
- Frontend shows structured empty and warning states without relying on legacy
  paragraph copy.

**Source Reference**

Task 9 structured therapies/trials and the user request to extend
ClinicalTrials.gov from demo/report rows into robust live filtering and
provenance.

**Verify**

```bash
cd app/backend
python -m pytest tests/test_clinical_trials_tool.py tests/test_variant_report_orchestration.py -q
python -m ruff check app tests/test_clinical_trials_tool.py tests/test_variant_report_orchestration.py
python -m black --check --target-version py310 app tests/test_clinical_trials_tool.py tests/test_variant_report_orchestration.py
```

**Out Of Scope**

Approved-therapy database integration, eligibility parsing, patient matching,
`/runs`, and AlphaMissense.

## Task 19 - Report UI Review, Visual QA, And Continuation Checkpoint - PLANNED 2026-05-23 23:27 +1000 - Codex

**Goal**

Run a full report UI review after the gene-context snapshot and gnomAD/Trials
hardening land, then tune layout, responsive behavior, and source-state copy.

**Context**

The report now has the major data surfaces: header, call cards, deterministic
summary, disease mechanism, gnomAD Section 3, molecular/computational/ACMG,
publication rows, and ClinicalTrials.gov rows. The next session should treat
the page as a product surface and verify it visually across variants, not only
through unit tests.

**Relevant Files Or References**

- `app/frontend/src/pages/ReportPage.tsx`
- `app/frontend/src/components/report/*`
- `app/web/components/report/*`
- `app/web/components/report/ReportClient.tsx`
- `app/backend/tests/test_frontend_contract.py`
- `Layout - VARIANT REPORT 2.txt`

**Proposed Approach**

Use at least three report scenarios:

- RPE65 rich fixture happy path;
- non-RPE65 sparse/no-hit path;
- ambiguous/confirmation-required path.

Review desktop and mobile screenshots for text overlap, section order,
expand/collapse states, map/card readability, publication/trials empty states,
and Workbench teaser link behavior. Prefer small layout fixes over new feature
scope.

**Acceptance Criteria**

- Section order matches the report layout direction or an explicitly recorded
  deviation.
- Report cards and expansion panels do not overlap or resize unexpectedly on
  mobile or desktop.
- Empty/unavailable states are clear and do not imply missing data is benign.
- Workbench teaser link opens the right gene/cDNA/transcript when present.
- `/report` remains unaffected by landing-page-only styling changes.
- Browser verification artifacts or screenshots are captured when tooling is
  available.

**Source Reference**

User direction to visually review/tune the report UI and the 2026-05-23
layout reference document.

**Verify**

```bash
cd app/backend
python -m pytest tests/test_frontend_contract.py tests/test_variant_report_orchestration.py -q

cd ../frontend
npx tsc -b --pretty false
npm run build

cd ../web
npx tsc --noEmit --pretty false
npm run build
```

Then run browser verification on desktop and mobile using the in-app browser
MCP if available, or a Playwright fallback if the user approves that tool path.

**Out Of Scope**

New `/runs` work, AlphaMissense, unrelated landing redesign, broad color-system
changes, commit, push, stash, reset, or clean.
