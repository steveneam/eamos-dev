# Research Roadmap (v1)

## Purpose

The research track exists to answer two questions **before build starts**:

1. **What is the narrowest problem worth solving?**
2. **Can we defend and demo it credibly within the hackathon?**

This folder should reduce idea drift, not just collect articles.

---

## Current working hypothesis

The best current candidate is:

> A narrow clinician-facing decision-support workflow that helps flag likely RPE65-related referral candidates, explains the reasoning transparently, and prepares a reviewable output for clinician approval.

This is a **working hypothesis**, not a final locked statement.

---

## Research sequence

## Step 1 — Narrowing plan

### Objective
Choose the strongest concept framing before deeper research.

### Questions
- Are we solving a broad interpretation problem, or one narrow referral decision?
- Is the strongest user an ophthalmologist, genetics clinician, or another hospital-facing role?
- Which version is easiest to explain and defend in front of judges?

### Candidate option types to compare
- **Option A:** Broad inherited retinal disease interpretation assistant
- **Option B:** Narrow RPE65 referral-support / eligibility-flagging assistant
- **Option C:** Clinical report / referral draft assistant with lighter decision logic

### Decision criteria
- Clinical credibility
- Buildability in hackathon time
- Data feasibility
- Demo clarity
- Safety / low overclaim risk
- Distinctiveness vs generic AI copilot framing

### Deliverable
- `narrowing-options.md`

### Exit criteria
- One option is selected
- Rejected options have short written reasons

---

## Step 2 — Problem definition

### Objective
Describe the real-world workflow gap in concrete terms.

### Questions
- What happens in the current workflow today?
- Where is the friction?
- What is slow, fragmented, ambiguous, or error-prone?
- Why does this matter clinically and operationally?

### Deliverable
- `problem-definition.md`

### Exit criteria
- We can explain the problem in 3–5 plain-English bullets

---

## Step 3 — User + workflow mapping

### Objective
Map the exact user, inputs, decision point, and output.

### Questions
- Who is the primary user?
- What information do they already have at the moment they use this tool?
- What is the exact decision point?
- What output would actually help them move forward?

### Deliverable
- `user-workflow.md`

### Exit criteria
- One user journey is documented end-to-end

---

## Step 4 — Evidence pack

### Objective
Build the minimum evidence base needed to support the story.

### What to collect
- Disease/background references
- Workflow references
- Therapy / referral context references
- Clinical decision-support and explainability references
- Prior art / competitor examples
- Hackathon-relevant impact stats if available

### Target
- 8–10 useful references, not a giant bibliography

### Deliverable
- `evidence-pack.md`

### Exit criteria
- Each major claim in the pitch has at least one supporting reference

---

## Step 5 — Feasibility + data plan

### Objective
Decide what can be real, what should be mocked, and what must stay deterministic.

### Questions
- What inputs do we need for the MVP?
- What can be represented with static demo fixtures?
- Are there public references, APIs, or datasets we can safely use?
- What should stay rule-based instead of model-driven?
- Where would an LLM help, if at all?

### Deliverable
- `feasibility-data.md`

### Exit criteria
- We know the minimum data + logic needed for a reliable demo

---

## Step 6 — Safety boundary + claims control

### Objective
Prevent the project from drifting into unsafe or non-credible claims.

### Questions
- What must we explicitly avoid claiming?
- How do we describe the system as assistive, not autonomous?
- What human approval step must stay visible?
- How do we handle uncertainty, ambiguity, or missing inputs?

### Deliverable
- `safety-boundary.md`

### Exit criteria
- We have clean, judge-safe wording for README, pitch, and demo

---

## Step 7 — Demo scenario pack

### Objective
Turn the research output into a demo-ready set of cases.

### Minimum scenario set
- **Scenario 1:** likely eligible / strongest happy path
- **Scenario 2:** needs confirmation / uncertain branch
- **Optional Scenario 3:** not eligible / alternative next step

### Deliverable
- `demo-scenarios.md`

### Exit criteria
- Demo can show both value and restraint

---

## Suggested writing order

1. `narrowing-options.md`
2. `problem-definition.md`
3. `user-workflow.md`
4. `evidence-pack.md`
5. `feasibility-data.md`
6. `safety-boundary.md`
7. `demo-scenarios.md`

---

## What success looks like

By the end of research, we should be able to say:

- **who** the product is for,
- **what exact problem** it solves,
- **why this is the right narrow scope**,
- **what the MVP does and does not do**,
- and **why the demo is credible**.

If we cannot answer those cleanly, we are not ready to build.

---

## Immediate next move

Write `narrowing-options.md` first.

That is the decision gate for the rest of this folder.
