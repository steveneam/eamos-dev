# BE↔FE Cross-Check — Claude's adversarial review of Codex's backend

Stamp: 2026-05-24 00:40 +1000 · Claude. User-directed cross-check + integration
meeting. This doc is the Claude→Codex half (Claude reviewing the backend).
Codex's half (reviewing `app/web` + `app/frontend`) is expected as a parallel
direct-Codex session; exchange + agree the fix list here.

**Scope reviewed:** `variant_report_orchestrator.py`, `report_call_cards.py`,
`population_frequency_section.py`, `tools/gnomad.py`, `report_extraction_plan.py`
(match-level gating), `functional_evidence.py`, `gene_context_snapshot.py`,
`schemas/run.py` (report-profile subtree + match-level literals),
`tests/test_frontend_contract.py` (the canary), and both `backend.ts` mirrors.
Read-only — **no backend files edited** (per the cross-check rules; backend fixes
are Codex's lane).

---

## Verified-green facts (no action; for the meeting record)

- **Contract canary: 117 passed (0.87s)** — `python -m pytest
  tests/test_frontend_contract.py`.
- **The two `backend.ts` mirrors are byte-identical** — `diff
  app/frontend/src/lib/backend.ts app/web/lib/backend.ts` is clean; both 1128
  lines. The dual-mirror is in sync *right now*.
- **`VariantReportProfile` TS ↔ Pydantic matches field-for-field (11/11)** — the
  report-profile mirror is accurate today (see F1: it just isn't *guarded*).
- **Match-level gating in the extraction plan is correct:** `disease_mechanism`
  + `therapies_trials` = `gene_level`; all variant sections = `variant_level`,
  degrading to `unavailable` when there is no variant identity / confirmation is
  required (`_has_variant_identity`).
- **gnomAD fixture honesty is good:** non-RPE65 variants in fixture mode return
  `status="missing"` + `gnomad_fixture_variant_mismatch` (no RPE65 numbers served
  for the wrong variant); live-fetch failures fall back with explicit
  `live_fetch_failed:<Type>` + (on mismatch) `gnomad_fallback_fixture_variant_mismatch`.
- **gene-context snapshot honesty is good:** fixture path tags
  `gene_context_snapshot_fixture` + `transcript_model_from_rpe65_fixture_scaffold`;
  source path tags `gene_context_snapshot_source_backed`; non-cdna / non-human /
  provider-error return an explicit `_unavailable_snapshot` with cause warnings.
- **Functional-evidence honesty is good:** PS3/BS3 are *source-asserted* (scanned
  from ClinGen `metCodes` / ClinVar VCV + PubMed text), never derived from study
  count; the `"X Unique"` volume badge is independent of ACMG strength. Matches
  the CAR constraint "study count must not derive/upgrade PS3/BS3."

---

## Findings (prioritized)

### F1 — HIGH · contract-test integrity · **owner: Codex (BE; canary is backend-owned)**
**The contract canary does not actually verify the v2 report contract against the frontend.**

- The *only* Pydantic↔TS parity test is
  `test_pydantic_field_names_present_in_typescript`, which iterates **only**
  `MODEL_TO_TS_INTERFACE`. That map omits the entire report-profile subtree
  **except** the Task-13 `GeneContext*` models — i.e. it does NOT check
  `VariantReportProfile`, `ReportExtractionPlan/SectionTarget`,
  `VariantReportHeader`, `InterpretationSummary`, `DiseaseMechanismSection`,
  `MolecularContextSection`, `ComputationalDeepDiveSection/PredictorRow`,
  `AcmgWorksheetLedger/Criterion`, `TherapiesTrialsSection`, `TrialMatch`,
  `SourceProvenance`, the `PopulationFrequency*` report-section models,
  `FunctionalEvidence*`, `ReportCallCard*`/`VariantReportCallCards`,
  `PublicationLiterature/Snippet/SourceBreakdown`, or any `SearchInput*` model.
- The `*_BACKEND_MODELS` suites (`test_report_profile_backend_models_are_declared`,
  functional, call-card, search-input, epvlex) assert only
  `fields <= set(model.model_fields.keys())` — a **backend self-check that never
  reads backend.ts**. They look like contract coverage but verify nothing about
  the mirror.
- On `ReportPayload`, `report_profile`/`call_cards`/`population_frequency_detail`/
  `functional_evidence`/`publications_literature` are explicitly **exempted** from
  the parity check via `EPVLEX_PENDING_FRONTEND_MIRROR_FIELDS`.
- **Net:** the largest, newest part of the contract can drift Pydantic↔TS with
  the canary still green. It happens to be in sync today (verified), so this is a
  latent-risk fix, not a live break.
- **Suggested fix:** now that the FE mirror is complete, move the report-profile /
  call-card / functional / population / search-input / epvlex models out of the
  self-check dicts and into `MODEL_TO_TS_INTERFACE` (or a second parametrized
  parity test), and remove the now-satisfied entries from
  `EPVLEX_PENDING_FRONTEND_MIRROR_FIELDS`. Confirm green afterward.

### F2 — HIGH · contract-test integrity · **owner: Codex (BE) + Claude (FE) co-own**
**The canary only reads the Vite `backend.ts`; the Next `app/web/lib/backend.ts` is unguarded.**

- `_backend_ts_path()` hardcodes `…/frontend/src/lib/backend.ts`. `app/web` is now
  the active dev surface for landing+report and has zero canary coverage. The two
  files are identical today (F-verified) only by manual discipline.
- **Suggested fix:** parametrize the parity test over BOTH paths, **or** add a
  cheap assertion that the two `backend.ts` files are byte-identical until cutover
  retires one. Backend-owned test file; Claude can supply the app/web path.

### F3 — MEDIUM · gating coordination · **owner: integration meeting (BE+FE)**
**Rendered report sections do not self-declare `match_level`.**

- Gating lives only in `extraction_plan.section_targets[].match_level` and
  `TrialMatch.match_level`. The section payloads (`DiseaseMechanismSection`,
  `MolecularContextSection`, …) carry no `match_level`. `disease_mechanism` and
  `therapies_trials` are `gene_level` by design, but a component rendering those
  payloads directly has no in-band signal to label them gene-level — it must
  cross-reference `section_targets` by `section_id` (exactly what the
  `report_profile` CAR instructs).
- **Action:** confirm in Codex's FE-review half whether the FE actually consumes
  `section_targets` for gating. If not: either FE wires it, or BE adds a
  `match_level` field to each rendered section payload (BE-led contract change).

### F4 — LOW · display honesty · **owner: Codex (BE)**
**Population-frequency call card hardcodes provenance `"gnomAD GraphQL"` in the no-data branch.**

- `report_call_cards._population_frequency_card` (no-data path) emits
  `provenance=["gnomAD GraphQL"]` regardless of `source_status` (which may be
  `fixture`/`missing`). `source_status` carries the truth, so this is cosmetic,
  but the string implies a live GraphQL call that didn't happen. Consider
  deriving the provenance label from status.

### F5 — LOW · dead branch · **owner: Codex (BE)**
**BA1/BS1 label branches are identical in `_population_frequency_card`.**

- `max_af >= FREQUENCY_BA1_AF_THRESHOLD` and `>= FREQUENCY_BS1_AF_THRESHOLD` both
  yield `"Common (… max AF)"` + `benign_green_state`; the BA1 branch is
  unreachable-equivalent. Not a bug (the BA1/BS1 distinction surfaces via the
  ACMG badge from consensus), but either differentiate the label or collapse the
  two branches.

---

## Open-CAR reconciliation (status in code vs marked in CURRENT.md)

| CAR | Marked | Actual in code |
| --- | ------ | -------------- |
| `report_profile` mirror+render | OPEN | **Mirrored** in BOTH `backend.ts` (VariantReportProfile 11/11). Render: confirm in Codex FE-review half. |
| `call_cards` mirror+render | OPEN | **Mirrored** in both; `CallCardsGrid.tsx` exists (untracked) in both apps. |
| gnomAD §3 population mirror+render | OPEN | **Mirrored** (PopulationFrequencyReportSection); `PopulationFrequencySection.tsx` modified in both. |
| functional evidence mirror+render | OPEN | **Mirrored** (FunctionalEvidenceSummary). |
| EP-VLEx publications mirror+render | OPEN | **Mirrored** (PublicationLiterature/Snippet). |
| search-input (raw `search_text` + `/lookup/parse` + chips) | OPEN | **NOT wired** — grep finds no `search_text` / `/lookup/parse` / `search_interpretation` in either `api.ts`. Types mirrored; wiring absent. **Genuinely open — Claude/FE lane.** |

Most "OPEN" report CARs are satisfied in code and should be marked DONE once the
FE-render half is confirmed; the search-input AI wiring is the real remaining
frontend task (today the landing routes freeform → `/report?q=` only).

---

## Proposed fix split (to agree in the meeting)
- **Codex / BE:** F1 (promote report models into the real parity check), F2
  (guard app/web path or assert identical), F4, F5. Then mark the satisfied
  report CARs DONE.
- **Claude / FE:** the search-input AI wiring CAR (raw `search_text` →
  `/lookup/parse` → interpretation chips → `/report`); confirm F3 consumption of
  `section_targets` in the report components.
