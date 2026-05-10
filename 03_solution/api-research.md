# API Research Plan (Backend-First)

## Scope

We are not building “everything.”
We are building a **single, narrow clinical workflow** with a small, reliable external dependency surface.

This plan is structured as:
1. must-have sources,
2. optional sources,
3. what we can defer,
4. implementation sequence for backend.

---

## I. Core workflow data model (priority)

For MVP we assume:
- case input (patient context + referral reason + one or more variant entries),
- deterministic report workflow,
- clinician review before final output.

### Stage A — Core case data (no external API required)
- Keep manual/fixture-based case payload schema in control.
- This guarantees stable demo behavior while we narrow disease + referral.

### Stage B — Evidence + interpretation APIs (controlled lookups)
- Add external sources only where they answer clear product questions.

---

## II. Must-have API surfaces (Tier 1)

### 1) Variant annotation / effect lookup
**Candidate:** Ensembl VEP REST (`/vep/.../region` or `/vep/.../id`)

**Why first:** gives deterministic, structured biology facts that can drive a referral-safe output.

**Use case:** map variant -> gene / consequence / impact hints.

**Risk note:** rate limits, response variability, model/plugin differences.

**Implementation shape:** adapter interface + cached responses for selected test variants.

---

### 2) Splice effect prediction
**Candidate:** SpliceAI public lookup API (Broad SpliceAI-lookup service or local self-hosted equivalent)

**Why second:** adds a focused signal for splice-region / intronic variants that VEP consequence labels alone may underspecify.

**Use case:** attach splice-gain / splice-loss evidence (`DS_*`, `DP_*`) when the workflow needs to know whether a variant may materially alter splicing.

**Risk note:** the public service is intended for interactive use, not batch traffic; rate limits and default-parameter drift are real. Always set `distance` and `mask` explicitly and keep fixture fallbacks.

**Implementation shape:** `splice_prediction_provider` adapter + cached responses for selected test variants.

---

### 3) Variant interpretation history / clinical assertions
**Candidate:** ClinVar-access pathways (via NCBI/available APIs and/or static references)

**Why third:** supports “what is known” claims and confidence context.

**Use case:** attach significance/condition evidence and confidence bands to draft.

**Risk note:** public APIs can be uneven; prefer controlled sample cache for hackathon demo reliability.

**Implementation shape:** evidence fetch adapter + local fallback fixtures.

---

### 4) Variant canonicalization / id normalization
**Candidate:** ClinGen Allele Registry (or equivalent canonicalization path if tokenized in current infra)

**Why fourth:** avoids noisy duplicate variant identities across sources.

**Use case:** stable keying by standard identifiers in internal stores + logs.

**Risk note:** availability/auth details vary; make this optional behind a feature flag.

---

### 5) Optional source-of-truth workflow benchmark
**Candidate:** Franklin/Genoox API (if access credentials are available)

**Why:** validates enterprise-style case/report workflow and informs endpoint shapes.

**Use case:** parity checks for case lifecycle and report lifecycle design.

**Risk note:** do not block MVP on this; this is optional until team has guaranteed access.

---

## III. Optional / post-MVP sources (Tier 2)

- Disease panel sources (e.g., PanelApp / curated panel APIs)
- Guideline engines (local policy files first, external APIs only if clean)
- EHR / referral scheduling APIs

These wait until disease + referral has been finalized.

---

## IV. API research outputs required before implementation

Before coding, collect and store:
- endpoint names,
- auth model (public key / bearer / none),
- sample request/response payload,
- quota/rate-limit behavior,
- offline fallback strategy for each endpoint.

Each endpoint we keep should have:
1) one source document,
2) one mock/fixture sample,
3) one schema adapter.

---

## V. Decision rule (important)

If an API fails during prototype, do one of:
- cached fixture fallback, or
- remove dependency + keep behavior via internal deterministic rules.

**No external API is allowed to be a hard blocker for demo.**

---

## VI. Immediate next actions

1. Confirm disease + referral lane (team finalization).
2. Build API adapter interfaces (no UI yet):
   - `annotation_provider`
   - `splice_prediction_provider`
   - `evidence_provider`
   - `normalization_provider`
3. Implement local fixtures for each interface.
4. Add smoke tests for adapter happy path + timeout/failure path.
