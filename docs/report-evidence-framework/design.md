# Report Evidence Framework Design

Status: Draft

## Summary

Eamos needs a gene- and variant-agnostic evidence framework for variant reports. The ABCA4 learning-gap work identified the right failure class: public evidence rows were being joined or displayed without a strong enough distinction between variant identity, source rationale, discovery search, and case-level ACMG requirements.

The recommended design is to introduce explicit evidence contracts for identity matching, trial discovery, case-context limitations, lazy section state, and report-wide section ranking. ABCA4 remains the proof case, but the code should operate on source-backed identifiers and typed match metadata rather than ABCA4-specific constants. The frontend should then render a progressive-disclosure dashboard from backend section signals instead of guessing which evidence matters.

## Context and Scope

This design covers the backend/frontend report path touched by the current dirty tree:

- ClinGen VCEP lookup: `app/backend/app/tools/clingen.py`
- ClinicalTrials.gov lookup: `app/backend/app/tools/clinical_trials.py`
- Evidence assembly: `app/backend/app/services/lookup_service.py`
- ACMG advisory scoring: `app/backend/app/services/acmg_points_engine.py`
- Gene-disease local cache: `app/backend/app/repos/supabase_local_model_cache_repo.py`
- Protein feature seeds: `app/backend/app/fixtures/protein_feature_seeds.json`
- Report frontend types/state: `app/web/lib/backend.ts`, `app/web/components/report/**`

It deliberately does not deploy, seed production, change Vercel/Render configuration, or decide commercialization filtering.

## Goals

- Prevent source assertions from being selected by narrative-only text mentions.
- Preserve ClinGen VCEP criteria only when source identity matches the requested variant.
- Discover clinical trials through reusable query lanes with clear match levels and provenance.
- Show honest PM3/PP4 limitations when public lookup lacks patient/case context.
- Normalize lazy publications/trials loading, empty, and error states.
- Keep protein architecture and variant localization source-backed and coordinate-backed.
- Add an Eamos-specific section signal model for priority, confidence, relevance, and default disclosure.
- Add tests that prove framework invariants beyond ABCA4.

## Non-Goals

- No production deploy.
- No role/auth/account plumbing for this work.
- No full clinical interpretation engine or patient eligibility matching.
- No fabricated case context from public literature or summary prose.
- No new LLM-backed semantic extraction pass for graphify.

## Proposed Design

### 1. Variant Identity Contract

Introduce a reusable identity-matching layer used by ClinGen and any future variant assertion source.

Match tiers:

1. Source assertion ID plus version, such as ClinGen ERepo UUID/version.
2. Stable variant identifiers: CAID, ClinVar Variation ID, VRS/SPDI where available.
3. Normalized genomic allele on explicit assembly.
4. Transcript HGVS with accession version.
5. Text-only candidate.

Only tiers 1-4 can attach source assertions automatically. Tier 5 can create a candidate/search hit with a warning, but it cannot populate VCEP criteria or source-asserted ACMG rows.

Narrative fields such as `summaryDesc`, rationale, abstracts, or evidence summaries are indexed as rationale/search text only. They are never identity fields.

### 2. Source Assertion Provenance

Every expert assertion should carry enough provenance to be audited later:

- source namespace and display name
- source URL/API endpoint
- assertion UUID/accession/version
- source version or release timestamp
- fetched/materialized timestamp
- approval and publication dates, when provided
- expert panel/affiliation/specification
- condition and inheritance context
- criteria met/not met
- raw payload hash where available
- identity match tier and matched identity field

This makes the exact ABCA4 ERepo UUID a normal assertion record, not special logic.

### 3. Clinical Trial Discovery Contract

Replace gene-specific discovery constants with query lanes built from report context and source-backed terminology rows.

Query lanes:

- `variant_exact`: quoted HGVS/rsID aliases and eligibility-focused searches
- `gene_in_eligibility`: gene symbol/aliases in eligibility or broad term fields
- `condition_intervention`: disease/condition aliases plus known intervention aliases
- `condition_only`: disease/condition aliases
- `intervention_only`: intervention aliases
- `gene_term`: broad gene term fallback

Each executed query is preserved in `query_executions`, including API params, source URL, status, result count, and fetched timestamp. Each trial row stores `matched_query_id`, `match_level`, `matched_terms`, `evidence_field`, and an optional short snippet.

Tinlarebant for Stargardt is then found because reusable terminology says Tinlarebant is an intervention associated with Stargardt/ABCA4 context, not because the tool code knows ABCA4.

### 4. Case-Context Limitation Contract

Replace flat ACMG warning strings with structured requirements.

Example shape:

```json
{
  "code": "PM3",
  "status": "not_scored",
  "reason": "missing_case_context",
  "missing_inputs": ["affected_status", "second_allele", "phase"],
  "applies_when": ["recessive_gene_disease"],
  "message": "PM3 requires affected case context, a second disease-causing allele, and phase evidence before Eamos can score it."
}
```

The backend owns the code and message. The frontend renders the message and can map severity/icon by `reason` or `code`, avoiding raw internal-string leakage.

### 5. Lazy Section Contract

Extend the existing `LookupSectionEnvelope` model to include trials:

- Add `therapies_trials` or `trials` to `LookupSectionId`.
- Add a `_trials_envelope()` alongside `_publications_envelope()`.
- Return `status`, `payload`, `freshness`, and `warnings` for both publications and trials.
- Render explicit idle/loading/empty/error states for both sections.

Publications and trials should use one component-level state vocabulary:

- idle: section not requested yet
- loading: request in flight
- available: rows or typed payload present
- empty: source responded but no rows matched
- partial: source responded with degraded/lower-scope rows
- error/fallback: source failed or payload could not be narrowed

### 6. Protein Architecture Contract

Protein feature seeds are acceptable only as source-backed fallback/augmentation rows. Each feature needs source accession, source release, feature coordinates, kind, lane, and label. Report localization must be computed by coordinate overlap between the variant protein position/range and source feature coordinates.

For ABCA4, Ile1745 overlaps or is near a transmembrane helix. The ATPase motif is a separate feature and must not be claimed for Ile1745.

### 7. Eamos Report Signal Contract

Add `report_profile.section_signals` as Eamos' own dashboard intelligence layer. This is not ACMG and not a clinical classification. It is an ordering and disclosure contract for the report UI.

Each signal carries:

- section ID and label
- priority from `0` to `100`
- confidence from `0.0` to `1.0`
- relevance scope such as exact variant, transcript/locus, protein region, gene-disease, gene discovery, or disease discovery
- source strength such as expert panel, curated, primary database, literature, Eamos computed, mixed source, inferred, or unavailable
- status: ready, limited, empty, error, or loading
- default-open boolean
- short headline, data notes, and source refs

The signal model lets Eamos behave like a modern clinical dashboard:

- exact expert assertions, ACMG ledger, gnomAD, calibrated predictors, and primary gene-disease context can open early when they are high-signal
- publications and trials stay open by default because they are expected report discovery surfaces, while molecular details, raw provenance, and future low-use sections can remain collapsed
- warnings stay near the section that owns them
- the frontend gets a stable data contract for ordering rather than hard-coded ABCA4/RPE65 heuristics
- Eamos confidence/ranking can be surfaced as Eamos dashboard signal, but never as ACMG or clinical classification

## Interfaces and Data

Proposed backend additions:

- `EvidenceIdentityMatch`: match tier, source field, requested term, matched value, normalized value, confidence.
- `SourceAssertionProvenance`: assertion ID/version/source/specification fields.
- `ClinicalTrialQueryExecution`: query ID, query lane, API params, source URL, result count, warnings.
- `TrialMatch`: add `matched_query_id`, `evidence_field`, `evidence_snippet`, `last_update_posted_at`.
- `EamosComputedClassification`: replace or supplement `warnings: list[str]` with `limitations: list[AcmgCaseContextLimitation]`.
- `LookupSectionId`: add `trials` or `therapies_trials`.
- `ReportSectionSignal`: section priority/confidence/relevance/status/default disclosure.
- `VariantReportProfile.section_signals`: sorted section signals for the dashboard.

Frontend additions:

- TypeScript mirrors for the structured limitation and trial query fields.
- A generic section state/placeholder renderer for lazy report sections.
- Dashboard disclosure that consumes `section_signals` instead of deriving importance from row counts alone.
- Display copy owned by backend where messages are source/clinical semantics.

## Alternatives Considered

1. Keep ABCA4 maps in `clinical_trials.py`.
   - Rejected because it fixes one trial and guarantees a repeat failure for the next disease/intervention.

2. Use broad full-text search everywhere and post-filter by text.
   - Rejected because narrative/rationale text creates false variant identity joins.

3. Hide PM3/PP4 when not scored.
   - Rejected because absence looks like a stalled/missing section rather than an honest limitation.

4. Keep trials eager and publications lazy.
   - Rejected because inconsistent loading/empty behavior is already making report sections look stuck.

## Tradeoffs

- More metadata is emitted, but report behavior becomes auditable.
- Some matches will downgrade from source-asserted to candidate/discovery rows; this is correct when identity is uncertain.
- Trial discovery may return more rows when condition/intervention lanes are added; match-level labels and per-row provenance must keep the UI honest.
- Structured ACMG limitations add contract work, but avoid fragile frontend string mapping.

## Rollout and Migration

1. Keep the current ABCA4 regression tests, but broaden them with non-ABCA4 controls.
2. Introduce structured identity/provenance helpers without changing frontend behavior.
3. Replace ABCA4 trial constants with a source-backed term registry and query execution provenance.
4. Add trials to the lazy section envelope and frontend lazy state renderer.
5. Add section signals to the report profile and start consuming them in a progressive-disclosure UI pass.
6. Convert ACMG warning strings to structured limitations while preserving `warnings` during a compatibility window.
7. Run targeted backend pytest, frontend lint, `git diff --check`, and `python -m graphify update .`.

## Open Questions

- Should the trial lazy section ID be `trials` for UI clarity or `therapies_trials` to mirror the backend profile field?
- Where should curated intervention/discovery aliases live initially: JSON fixture, local SQLite table, or Supabase-backed source table?
- Should `warnings` remain indefinitely as a compatibility alias after structured limitations land?
- Which non-ABCA4 gene should be the first cross-gene trial-discovery regression control?
- Should the Eamos confidence score be visible as a named score, or only used to order and collapse sections?
- Should dashboard ranking eventually support clinician and researcher modes?

## Decision

Proceed with the framework approach. Preserve the useful current dirty-tree changes, but do not ship ABCA4-specific trial constants as the final architecture. The next implementation should promote the current fixes into reusable identity, trial-discovery, case-context, lazy-section, and protein-overlap contracts.
