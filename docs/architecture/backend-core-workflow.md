# Backend Core Workflow (Build-First)

## Goal

Design backend so others can continue research while we lock implementation around one core case-to-referral decision path.

The workflow should be:

1. Case intake
2. Variant processing
3. Evidence fetch
4. Decision-rule engine
5. Draft generation
6. Clinician review

---

## 1) Core Domain Entities

### Case
- case_id
- patient context (age/sex/setting)
- referral question
- variant list (gene, cDNA / hgvs / protein string when available)
- notes (referral/source text)

### Run
- workflow_run_id
- case_id
- status (`queued`, `running`, `needs-data`, `completed`, `failed`)
- active provider set
- timestamps and logs

### Evidence
- source (`vep`, `clinvar`, `local-knowledge`, `registry`)
- payload digest / relevance score
- timestamp / freshness

### Draft
- structured sections
- confidence / limitations
- suggested action
- risk flags

### Review
- reviewer
- edits
- finalization marker
- audit trail

---

## 2) Service Architecture

### A. API layer
- `POST /cases`  
  intake case
- `POST /cases/{id}/run`  
  trigger workflow run
- `GET /runs/{run_id}`  
  status + event log
- `GET /cases/{id}/draft`  
  latest draft + sections
- `POST /cases/{id}/review`  
  finalize clinician edits

### B. Workflow layer
- Stateful execution engine (LangGraph or explicit state machine)
- deterministic transition map:
  `ingest -> annotate -> evidence -> recommend -> render_draft -> review_queue`

### C. Provider abstraction
- `AnnotationProvider` (VEP first)
- `EvidenceProvider` (ClinVar/static evidence pack)
- `NormalizationProvider` (Allele Registry / local normalizer)
- `ModelProvider` (LLM or template renderer)

Each provider is optional and must degrade gracefully.

---

## 3) Refined MVP behavior (single-path)

### Input required for MVP
- Case basics + 1–3 variants
- referral intent context

### Output required for MVP
- structured draft
- one actionable recommendation
- at least one confidence flag
- at least one limitation note
- required-fields/coverage check summary

### Hard constraints
- one disease decision lane only for now
- one referral destination only in MVP
- no generic clinical diagnosis claim
- explicit clinician review required before final

---

## 4) Error/Failure policy

- If evidence provider times out: continue with reduced evidence + explicit warning.
- If annotation provider fails: continue with structured manual interpretation plus “missing evidence” banner.
- If model provider fails: use deterministic fallback templates.

---

## 5) Data strategy

- Start with deterministic fixtures (no PHI, no live dependency requirement).
- Add optional external lookup behind feature flags.
- Keep raw raw payload snapshots for audit/debug in `run_events`.

---

## 6) Build sequence (recommended)

1. **Phase 1:** Case schema + run orchestration + persistence + logs
2. **Phase 2:** Deterministic annotation/evidence stubs
3. **Phase 3:** Referral rule engine + draft renderer
4. **Phase 4:** Review endpoint + diff/audit
5. **Phase 5:** Optional external adapters (first VEP, then ClinVar)
6. **Phase 6:** Replace mocks with one small live endpoint (if feasible) + contract tests

---

## 7) Deliverable criteria for this build stage

- End-to-end local run works in one command with fixtures.
- One deterministic referral recommendation appears.
- Clinician review gate is required and logged.
- At least one fallback path is demonstrably tested and visible in UI/API.

---

## 8) Suggested next coding task set

- Add API adapters interfaces + dependency injection.
- Add `run` state machine with timeouts + graceful degradation.
- Add audit/log output for each workflow step.
- Add fixture-based tests for happy path + two failure modes.
- Produce one sample case for the chosen disease/referral lane.
