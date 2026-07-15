# Report Evidence Framework Spec

Status: Draft

## What

Build a gene- and variant-agnostic report evidence framework that turns the ABCA4 learning-gap fixes into reusable behavior across the whole variant report. The framework must attach expert assertions only through structured variant identity, discover clinical trials through source-backed query lanes, display honest ACMG case-context limitations, use consistent lazy section states, and expose Eamos section ranking metadata so the frontend can render a progressive-disclosure dashboard without hard-coded scientific heuristics.

## Context

The current dirty tree contains both good framework changes and ABCA4 spot-fixes. ClinGen identity guarding and gene-disease validity ordering are broadly useful. ABCA4-specific trial disease/discovery constants are not. ACMG PM3/PP4 warnings are useful but too unstructured. Publications already use the lazy section envelope; trials do not. Warning fields are already section-local across the report, so limitations should generally stay near the relevant section unless they change the top-line interpretation. Eamos also needs its own confidence/ranking layer, separate from ACMG, to decide which report sections open first and which remain collapsed.

Relevant files:

- `app/backend/app/tools/clingen.py`
- `app/backend/app/tools/clinical_trials.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/lookup_sections.py`
- `app/backend/app/services/acmg_points_engine.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/repos/supabase_local_model_cache_repo.py`
- `app/backend/app/fixtures/protein_feature_seeds.json`
- `app/backend/app/schemas/run.py`
- `app/backend/app/schemas/lookup.py`
- `app/web/lib/backend.ts`
- `app/web/components/report/LazySection.tsx`
- `app/web/components/report/PubMedSection.tsx`
- `app/web/components/report/TrialsSection.tsx`
- `app/web/components/report/EamosAcmgClassifier.tsx`

## Requirements

### Report-Wide Section Consistency

- Every report section must declare its evidence scope: exact variant, equivalent allele, transcript/locus, protein region, gene-disease, disease/intervention discovery, or summary.
- Every report section must expose source strength, status, confidence, display priority, default disclosure, and short data notes.
- Warnings and limitations should remain section-local by default.
- Top-level warnings should be reserved for query failure, report failure, or limitations that materially change the top-line interpretation.
- The frontend must not decide scientific priority from row counts alone.
- The backend must emit enough metadata for the frontend to rank and collapse sections consistently.

### Eamos Report Signal Model

- `VariantReportProfile` must expose `section_signals`.
- Each signal must include `section_id`, `label`, `priority`, `confidence`, `relevance`, `source_strength`, `status`, `default_open`, optional headline, data notes, and source refs.
- Eamos section confidence/ranking must be separate from ACMG classification and must not be presented as a clinical classification.
- Publications and trials should default open because users expect to see discovery evidence quickly; their lower-scope rows must be labeled by match level and data notes.
- Exact-variant, high-confidence, interpretation-changing sections should rank higher and open by default.
- Eamos confidence/ranking may be visible as an Eamos dashboard signal, but it must remain separate from ACMG and clinical classification.

### ClinGen and Variant Assertions

- The system must separate identity fields from rationale text.
- The system must never attach ClinGen VCEP rows based only on narrative/rationale/summary text.
- The system must record the identity match tier and matched source field for attached assertion rows.
- `ABCA4 c.5461-10T>C` must attach UUID `64d8e05f-18c1-4092-9ce7-8880f952e96e` when local ClinGen data contains that exact assertion.
- A neighboring or narrative-mentioned variant must be rejected with an explicit warning/status.

### ClinicalTrials.gov

- The system must build query lanes from structured report context and reusable terminology data, not hard-coded gene constants in tool code.
- The system must preserve every executed query and per-row matched query provenance.
- Rows must distinguish exact variant eligibility evidence from gene/disease/intervention discovery rows.
- `NCT06388083` must be discoverable for ABCA4/Stargardt/Tinlarebant through condition/intervention or source-backed intervention lanes.
- Trial rows must never imply patient eligibility.
- Trial rows should include status, phase, source URL, match level, evidence field/snippet when available, and last update date when provided by ClinicalTrials.gov.

### ACMG Case Context

- Public lookup must not score PM3 without case-level evidence for affected status, second allele, and phase/zygosity context.
- Public lookup must not score PP4 without phenotype specificity, test scope, and alternative-cause exclusion context.
- Missing PM3/PP4 inputs must be emitted as structured limitations.
- Source-asserted VCEP criteria may suppress limitations for that code only when the source assertion identity matches the variant.

### Lazy Report Sections

- Publications and trials must share a lazy-section envelope with `status`, `payload`, `freshness`, and `warnings`.
- The frontend must render clear idle/loading/empty/error/partial states for publications and trials.
- Empty source responses must not disappear silently.
- Fetch failures must render a retry path or explicit unavailable state.

### Protein Architecture

- Protein feature rows must remain source-backed with coordinates and provenance.
- Variant localization must be computed from protein coordinates and feature overlaps.
- ABCA4 Ile1745 must not be labeled as ATPase. It may be shown as in/near the transmembrane helix only if coordinates support that overlap.

## Design

### Data Types

Add or refine backend schema models:

```python
class EvidenceIdentityMatch(BaseModel):
    tier: Literal["assertion_id", "caid", "clinvar_variation_id", "vrs", "spdi", "genomic_hgvs", "transcript_hgvs", "candidate_text"]
    source_field: str
    requested: str
    matched: str
    normalized_requested: str
    normalized_matched: str
    auto_attach_allowed: bool

class ClinicalTrialQueryExecution(BaseModel):
    query_id: str
    lane: str
    params: dict[str, str]
    source_url: str
    status: str
    result_count: int
    warnings: list[str] = []

class AcmgCaseContextLimitation(BaseModel):
    code: str
    status: Literal["not_scored"]
    reason: str
    missing_inputs: list[str]
    applies_when: list[str] = []
    message: str

class ReportSectionSignal(BaseModel):
    section_id: str
    label: str
    priority: int
    confidence: float
    relevance: Literal[
        "exact_variant",
        "equivalent_allele",
        "protein_region",
        "transcript_locus",
        "gene_disease",
        "disease_discovery",
        "gene_discovery",
        "summary",
    ]
    source_strength: Literal[
        "expert_panel",
        "curated",
        "primary_db",
        "literature",
        "eamos_computed",
        "source_mixed",
        "inferred",
        "unavailable",
    ]
    status: Literal["ready", "limited", "empty", "error", "loading"]
    default_open: bool
    headline: str | None = None
    data_notes: list[str] = []
    source_refs: list[str] = []
```

Update existing models:

- `TrialMatch`: add query/evidence provenance fields.
- `TherapiesTrialsSection`: add `query_executions`, freshness-friendly provenance, and source status if absent.
- `EamosComputedClassification`: add `limitations`; keep `warnings` as compatibility until frontend/export are migrated.
- `LookupSectionId`: add a trials section ID.
- `VariantReportProfile`: add `section_signals` for report-wide ranking and progressive disclosure.

### ClinGen Flow

1. Build requested identity aliases from the resolved variant.
2. Query local/live ClinGen sources as today.
3. Extract identity values only from structured identity keys.
4. Match against request aliases with normalized identity matching.
5. Attach source assertion only if the match tier permits auto-attach.
6. Store identity match details in summary/provenance.
7. If candidates exist but fail identity guard, return missing/partial with `variant_identity_guard_rejected_candidate`.

### Trial Flow

1. Build variant aliases from resolved HGVS/rsID/genomic fields.
2. Build gene aliases from gene/transcript context.
3. Build disease aliases from gene-disease validity, MONDO/condition rows, and curated terminology.
4. Build intervention aliases from a source-backed discovery registry.
5. Execute query lanes independently.
6. Parse rows and locally confirm terms in specific fields.
7. Deduplicate by NCT ID while preserving all matched query executions.
8. Emit rows with match level and evidence field/snippet.
9. Surface lower-scope/discovery rows as partial/discovery, not exact matches.

### ACMG Flow

1. Compute source-asserted and Eamos-derived ACMG applications as today.
2. Build a case-context evidence object from patient/case inputs and source-asserted VCEP criteria.
3. For PM3/PP4, if no application exists, add structured limitations only when the gene/disease context makes the criterion relevant.
4. Do not add limitations for criteria that are source-asserted by an identity-matched VCEP row.
5. Frontend renders `limitations[].message`.

### Lazy Section Flow

1. Add trials to backend `LAZY_SECTION_ORDER`.
2. Add `_trials_envelope()` in `lookup_sections.py`.
3. Update frontend `LookupSectionId` and report rendering.
4. Use `LazySection` for trials and publications.
5. Add default placeholder/empty/error views so neither section returns `null` while a source fetch is pending or failed.

### Section Signal Flow

1. Build typed report sections as today.
2. Score each section by exactness, source strength, available rows, source status, and whether the section changes interpretation.
3. Emit section-local data notes from existing warning fields.
4. Sort by priority descending.
5. Keep publications and trials open by default while labeling their evidence scope. Lower-scope discovery rows should be visually honest, not hidden.

## Decisions

- Decision: Narrative text is rationale only. It can create candidates but cannot attach source-asserted evidence.
- Decision: ClinicalTrials.gov rows are discovery rows unless exact variant evidence is locally confirmed in a relevant field.
- Decision: Keep `warnings` during compatibility migration but introduce structured `limitations` for ACMG display and export.
- Decision: Use a JSON fixture/table for first-pass curated trial discovery terms, with provenance fields, before deciding on Supabase-backed storage.
- Decision: Add trials to the existing lazy-section framework instead of creating a parallel frontend fetch path.
- Decision: Add an Eamos section signal model now, but use it as advisory dashboard metadata until the frontend consumes it.

## Invariants

- No VCEP assertion without variant identity match.
- No PM3/PP4 scoring from public lookup-only context.
- No trial row without match level and query provenance.
- No publication/trial section silently disappears when source status is missing, empty, failed, or partial.
- No protein localization claim without coordinate overlap and source provenance.
- No frontend-only scientific ranking heuristic. Backend owns report priority/confidence.

## Error Behavior

- ClinGen candidate rejected: status `missing` or `partial`, warning `variant_identity_guard_rejected_candidate`, no criteria attached.
- ClinGen source unavailable: existing fallback behavior, but do not use stale/candidate rows unless identity tier is sufficient.
- ClinicalTrials.gov failure: section status `error`/`fallback`, warnings include the exception class, frontend displays unavailable state.
- ClinicalTrials.gov no rows: section status `missing` or `empty`, frontend displays "No ClinicalTrials.gov rows found for this lookup."
- Lazy payload cannot be narrowed: frontend displays a section error with retry.
- ACMG missing case context: structured limitations display; score remains unchanged.

## Testing Strategy

Backend pytest:

- ClinGen identity guard: exact HGVS, genomic-only, CAID/ClinVar ID, no identity fields, narrative-only false positive.
- Clinical trials: query lane generation, multiple query provenance, Tinlarebant `NCT06388083`, one non-ABCA4 condition/intervention control, exact variant downgrade when text confirmation fails.
- ACMG: AR no case context, AD no PM3 warning, phenotype-only no PP4 score, source-asserted PM3/PP4 suppresses limitations, second-allele/phase input when added.
- Lazy sections: trials envelope, missing/error/partial status, frontend contract.
- Protein seed: ABCA4 Ile1745 transmembrane overlap and not ATPase.
- Gene disease: definitive row wins over disputed row across at least ABCA4 and one non-ABCA4 fixture.
- Section signals: all major sections produce signal rows; high-confidence exact-variant sections outrank discovery sections; publications and trials are open by default with explicit scope/data notes.

Frontend:

- `npm --prefix app/web run lint`.
- Add focused component tests if the repo has a nearby test pattern for `LazySection` or report sections.
- Browser check on `http://localhost:3001` after implementation, not `127.0.0.1`, for ABCA4 `c.5461-10T>C` and `c.5234T>A`.

Repository:

- `git diff --check`.
- Structural boundary guards.

## Out of Scope

- Production deploy.
- Live SG verification before the code is reviewed and deployed later.
- Supabase migrations unless the term registry is explicitly moved out of fixtures.
- Patient eligibility recommendations.
- LLM-backed repository semantic extraction.
