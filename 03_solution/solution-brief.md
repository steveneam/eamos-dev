# Solution Brief

## Current position

We are keeping the **genomics workflow** because the workflow itself is real and clinically grounded.

What we are **not** building is a generic genomic report generator.

What we **are** building is a **narrow clinician-facing decision-support workflow** that takes a genomic case plus patient context, grounds it in structured evidence, and produces a **referral-support draft** or **next-step recommendation** that must be reviewed by a clinician before use.

In short:

> **Input:** genomic case + clinical context  
> **Process:** annotation + evidence + narrow decision logic  
> **Output:** clinician-review draft for one specific referral / next-step decision

---

## Current narrowing status

The team has **not yet locked the final disease and referral pathway**.

That is the active narrowing question.

However, the product shape is now stable enough to build the backend around one repeatable pattern:
- one disease lane,
- one referral destination,
- one recommendation output,
- one clinician review gate.

The disease/referral choice can change without forcing a full backend redesign if the workflow remains the same.

---

## Problem statement

Clinicians and genomic teams often need to combine:
- a reported variant or case report,
- patient context,
- and supporting evidence,

into a **clear, reviewable next-step decision**.

This process is often fragmented across notes, reports, knowledge sources, and clinician memory.

The problem we want to solve is **not interpretation in the abstract**.
It is the narrower operational problem of:

> turning a genomic case into a **clear, grounded, clinician-reviewable referral or action recommendation**.

---

## Proposed solution

Build a backend-first workflow that:

1. ingests a genomic case,
2. normalizes and annotates the variant(s),
3. retrieves supporting evidence,
4. applies narrow disease/referral decision logic,
5. drafts a structured recommendation,
6. and requires clinician review before final output.

The draft can be rendered as a report, but the **report is an artifact of the workflow**, not the core product.

The core product is the **decision-support step**.

---

## Primary user

Current working user:
- clinician / reviewer / coordinator handling genomic case review and referral decision-making

This may ultimately narrow to a more specific role depending on disease selection, for example:
- specialist clinic reviewer,
- genetics service reviewer,
- referral coordinator,
- or disease-specific clinician team.

For now, the brief should stay **clinician-facing**, not consumer-facing.

---

## MVP definition

The MVP must support **one narrow case-to-referral workflow** only.

### MVP inputs
- basic patient context
- referral question / clinical question
- 1–3 variants
- short note or source report text

### MVP processing
- variant normalization
- annotation lookup
- clinical evidence lookup
- disease/referral rule application
- structured draft generation

### MVP outputs
- one recommendation / referral-support result
- one confidence or uncertainty indicator
- one limitations section
- one clinician review/edit step
- one audit trail for how the draft was produced

---

## Example output shape

A successful MVP output should look like:
- **summary of case relevance**
- **supporting evidence bullets**
- **recommended next step / referral direction**
- **confidence caveat**
- **missing information / review points**

Examples of recommendation language:
- supports referral to specialist review
- likely relevant, needs confirmation
- insufficient evidence for automated recommendation

This keeps the product clearly assistive rather than autonomous.

---

## Technical strategy

### Build posture
- backend first
- fixture first
- deterministic first
- external APIs only where they clearly improve the workflow

### Core workflow
1. Case intake
2. Variant processing
3. Evidence fetch
4. Decision-rule engine
5. Draft generation
6. Clinician review

### External dependency posture
- external APIs must be optional or cacheable
- no live API should be a hard blocker for the demo
- every provider should have a local fallback

### API priority order
1. variant annotation
2. clinical significance / evidence
3. variant normalization
4. optional enterprise workflow benchmark APIs
5. disease-specific evidence sources after narrowing is finalized

### LLM role
The LLM should help with:
- explanation,
- structured draft wording,
- and limited reasoning over already-grounded evidence.

The LLM should **not** be treated as the primary source of truth.

---

## Non-goals

We are not building:
- a general-purpose genomic interpretation platform
- a Franklin/Genoox clone
- a consumer genetics / wellness / allergy report product
- autonomous diagnosis
- a broad multi-disease recommendation engine in the MVP
- a system that gives final clinical advice without review

---

## Risk controls

- keep the scope to one disease + one referral lane
- preserve uncertainty and missing-data warnings
- require clinician review before final output
- log the workflow steps and evidence sources
- prefer deterministic fallback behavior over fragile live integrations
- do not overclaim clinical certainty in pitch or UI

---

## Current open decisions

These still need to be finalized by the team:
- which disease to focus on
- which referral destination / next-step action to support
- which evidence sources are required for that lane
- what sample cases best demonstrate the workflow

Possible lane examples under discussion:
- inherited retinal disease / RPE65-related referral support
- hereditary cancer referral support
- cardiogenetics referral support

---

## Immediate next steps

1. lock the disease + referral lane
2. define the first 2–3 synthetic demo cases
3. build backend adapters and fixture responses
4. implement the case -> evidence -> recommendation -> review workflow
5. only then add disease-specific polish and pitch wording

---

## Working reminder

If the product starts to sound like **"AI generates a genomic report"**, it has drifted too broad again.

The intended product is:

> **a narrow, clinician-facing genomic decision-support workflow for one specific referral / next-step decision**.
