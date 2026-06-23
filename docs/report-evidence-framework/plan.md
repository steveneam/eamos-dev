# Report Evidence Framework Plan

Status: Draft

## Task 0 - Report-Wide Section Consistency Audit

Goal: Prevent another spot-fix cycle by auditing every variant report section against the same evidence contract.

Context: ABCA4 exposed failures in ClinGen, trials, ACMG limitations, publications, and protein architecture, but the same architecture must cover population frequency, in silico predictors, Eamos ACMG, gene/disease context, gene view, molecular context, publications, trials, and narrative summaries.

Relevant files:

- `docs/report-evidence-framework/section-consistency-audit.md`
- `app/backend/app/schemas/run.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/web/lib/backend.ts`
- `app/web/components/report/**`

Proposed approach:

- Maintain a section matrix with scope, source strength, confidence, priority, disclosure, warnings/notes, ACMG contribution, and verification.
- Keep limitations/warnings section-local unless they change the top-line interpretation.
- Use the matrix as the acceptance checklist for all following tasks.

Acceptance criteria:

- Every major report section has a declared scope and source-strength rule.
- The plan distinguishes exact variant evidence from gene/disease discovery and transcript/protein context.
- Frontend progressive disclosure has a backend-owned signal contract.

Verify:

```powershell
git diff -- docs/report-evidence-framework/section-consistency-audit.md docs/report-evidence-framework/plan.md docs/report-evidence-framework/spec.md docs/report-evidence-framework/design.md
```

## Task 1 - Eamos Section Signal Model

Goal: Add Eamos' own report section priority/confidence model so the report can behave like a modern dashboard without frontend-only scientific heuristics.

Context: The frontend should know which sections to open, collapse, and order from backend metadata. This score is not ACMG and not a clinical classification.

Relevant files:

- `app/backend/app/schemas/run.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_frontend_contract.py`
- `app/web/lib/backend.ts`
- `app/frontend/src/lib/backend.ts`

Proposed approach:

- Add `ReportSectionSignal` and `VariantReportProfile.section_signals`.
- Compute deterministic first-pass signals from existing typed sections.
- Score by section scope, source strength, source status, row availability, and interpretation impact.
- Keep publications and trials open by default because users expect them in first-pass report review; rely on match-level labels and data notes rather than hiding them.
- Keep Eamos confidence/ranking separate from ACMG while allowing the UI to surface it as an Eamos dashboard signal.
- Mirror the contract into frontend types.

Acceptance criteria:

- Every typed report profile includes section signals for summary, expert panel, Eamos ACMG, population frequency, computational predictors, gene/disease context, gene view, molecular context, publications, and trials.
- High-confidence exact-variant sections outrank lower-scope discovery sections.
- Trials and publications are open by default, with lower-scope discovery rows clearly labeled.
- Existing report rendering remains compatible.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_variant_report_orchestration.py tests/test_frontend_contract.py -q
```

## Task 2 - ClinGen Identity Framework

Goal: Promote the current ClinGen guard into a reusable identity-match contract.

Context: The dirty `clingen.py` change correctly rejects narrative-only matches, but it should expose match tier/provenance and broaden test coverage.

Relevant files:

- `app/backend/app/tools/clingen.py`
- `app/backend/app/services/clingen_local.py`
- `app/backend/tests/test_clingen_local.py`
- `app/backend/tests/test_tool_invariants.py`

Proposed approach:

- Factor identity extraction/matching into a small helper module or local class.
- Treat `summaryDesc` and other rationale text as non-identity.
- Return identity match metadata in the ClinGen summary/provenance.
- Add warnings for rejected candidates.

Acceptance criteria:

- Exact ABCA4 `c.5461-10T>C` returns UUID `64d8e05f-18c1-4092-9ce7-8880f952e96e`.
- Neighbor/narrative-only rows are rejected.
- CAID/ClinVar Variation ID/genomic-only cases are covered.
- Records with no identity fields cannot auto-attach.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_clingen_local.py tests/test_tool_invariants.py -q
```

## Task 3 - Source-Backed Trial Discovery Registry

Goal: Replace ABCA4 hard-coded trial discovery maps with reusable terminology and query lanes.

Context: Current `_GENE_TRIAL_DISEASE_TERMS` and `_GENE_TRIAL_DISCOVERY_TERMS` find Tinlarebant but are not framework behavior.

Relevant files:

- `app/backend/app/tools/clinical_trials.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/tests/test_clinical_trials_tool.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- new fixture/table if needed

Proposed approach:

- Add a source-backed trial discovery registry with gene, disease alias, intervention alias, source URL, source release, and match policy.
- Build query lanes from variant aliases, gene aliases, disease terms, and intervention terms.
- Use ClinicalTrials.gov v2 field-specific params where possible (`query.cond`, `query.intr`, `query.term`, focused advanced filters later).
- Preserve every query execution and per-row matched query.

Acceptance criteria:

- Tinlarebant `NCT06388083` is found through disease/intervention lanes, not ABCA4 constants.
- Trial rows carry match level, matched terms, evidence field/snippet when available, and matched query ID.
- Multiple contributing queries preserve provenance.
- At least one non-ABCA4 fixture proves the query framework generalizes.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_clinical_trials_tool.py tests/test_variant_report_orchestration.py -q
```

## Task 4 - Lazy Trials Section and Report States

Goal: Make publications and trials share the same lazy loading, empty, partial, and error behavior.

Context: Publications already use `LookupSectionEnvelope`; trials are eager under `report_profile.therapies_trials`, so they can look absent or stalled.

Relevant files:

- `app/backend/app/services/lookup_sections.py`
- `app/backend/app/schemas/lookup.py`
- `app/backend/tests/test_lookup_section_fetch_contract.py`
- `app/web/lib/backend.ts`
- `app/web/components/report/LazySection.tsx`
- `app/web/components/report/ReportClient.tsx`
- `app/web/components/report/TrialsSection.tsx`
- `app/web/components/report/PubMedSection.tsx`

Proposed approach:

- Add a trials section ID to backend and frontend lookup-section contracts.
- Add `_trials_envelope()` with status/freshness/warnings.
- Use `LazySection` for trials.
- Add reusable placeholder/empty/error views for both publications and trials.

Acceptance criteria:

- Report sections do not silently disappear when publications/trials are loading, empty, failed, or partial.
- ABCA4 `c.5461-10T>C` can show publications and clinical trials.
- Empty/no-row states clearly distinguish no rows from source failure.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_lookup_section_fetch_contract.py tests/test_variant_report_orchestration.py -q
npm --prefix app/web run lint
```

## Task 5 - Structured ACMG Case-Context Limitations

Goal: Replace raw PM3/PP4 warning strings with structured limitations.

Context: Current warning plumbing is gene-agnostic but broad and display-string based.

Relevant files:

- `app/backend/app/schemas/run.py`
- `app/backend/app/services/acmg_points_engine.py`
- `app/backend/tests/test_acmg_points_engine.py`
- `app/web/lib/backend.ts`
- `app/web/components/report/EamosAcmgClassifier.tsx`

Proposed approach:

- Add `AcmgCaseContextLimitation` to backend schema.
- Emit limitations for PM3/PP4 missing case inputs.
- Keep `warnings` temporarily for compatibility.
- Render backend-provided messages in the frontend.

Acceptance criteria:

- `ABCA4 c.5234T>A` shows honest PM3/PP4 limitations without scoring those criteria from public lookup.
- Source-asserted PM3/PP4 criteria on exact VCEP rows suppress the corresponding limitation.
- Non-recessive or no-gene-disease contexts do not show noisy PM3 warnings.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_acmg_points_engine.py tests/test_frontend_contract.py -q
npm --prefix app/web run lint
```

## Task 6 - Protein Architecture Overlap Guard

Goal: Keep source-backed ABCA4 protein architecture while preventing unsupported localization claims.

Context: The ABCA4 seed is useful, but the report must compute overlap rather than imply motif membership from nearby feature labels.

Relevant files:

- `app/backend/app/fixtures/protein_feature_seeds.json`
- `app/backend/app/services/protein_annotation.py`
- `app/backend/tests/test_protein_annotation_service.py`

Proposed approach:

- Ensure seed features have coordinates, source accession, source release, and lane/kind.
- Add an overlap helper or test that proves variant position 1745 overlaps the transmembrane helix and not the ATPase region.
- Keep feature provenance visible.

Acceptance criteria:

- Ile1745 is shown as in/near a transmembrane helix, not ATPase.
- ATPase region remains present as a separate source feature if source-backed.
- Protein feature seed tests pass for ABCA4 and existing BRCA1/RPE65 controls.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_protein_annotation_service.py -q
```

## Task 7 - ABCA4 End-to-End Regression Review

Goal: Verify the two motivating ABCA4 report cases without hard-coding them in framework code.

Context: The target behaviors are scientific correctness and honest limitations.

Relevant files:

- Backend tests from Tasks 1-6
- Report frontend sections
- Current `.tmp-abca4-*` payloads may be read for comparison but should not be staged.

Acceptance criteria:

- `ABCA4 c.5461-10T>C` report sections include source-backed ClinGen, publications, and trial discovery rows.
- `ABCA4 c.5234T>A` report shows honest PM3/PP4 limitations and source-backed protein architecture.
- No claim says Ile1745 is ATPase-localized.

Verify:

```powershell
cd app/backend
python -m pytest tests/test_clingen_local.py tests/test_clinical_trials_tool.py tests/test_acmg_points_engine.py tests/test_variant_report_orchestration.py tests/test_protein_annotation_service.py tests/test_supabase_local_model_cache.py -q
npm --prefix app/web run lint
git diff --check
python -m graphify update .
```

Browser verification after implementation should use `http://localhost:3001`, not `http://127.0.0.1:3001`.

## Staging Constraints

- Use explicit pathspecs only.
- Do not deploy.
- Do not run `vercel` or `vc` from `app/web`.
- Keep root `.vercel` linked to `eamos-dev`.
- Keep `app/web/.vercel` absent.
- Do not stage held handoff/proprietary/report-launch files unless explicitly asked.
