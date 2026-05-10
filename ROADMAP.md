# HSIL-2026 Roadmap

## Core rule

**Research first. Build second. Pitch third.**

We do not start implementation until the team agrees on:
- one primary user,
- one narrow decision moment,
- one concrete output,
- and clear non-goals.

## Current working hypothesis

The strongest current direction is a **narrow clinician-facing decision-support tool** for inherited retinal disease cases, likely centered on **RPE65-related referral support**.

This is still a working hypothesis, not a locked final concept.

---

## Phase 0 — Team alignment + concept lock

### Goal
Get everyone describing the same project in the same words.

### Questions to answer
- What exact problem are we solving?
- Who is the primary user?
- What is the single clinical decision moment?
- What should the output look like?

### Outputs
- One-sentence problem statement
- One-sentence solution statement
- Initial non-goals list

### Exit criteria
- Team can explain the project consistently without drifting into different products

---

## Phase 1 — Narrowing research

### Goal
Compare a few candidate scopes and choose the one that is most:
- clinically credible,
- feasible in a hackathon,
- easy to explain,
- and strong in a live demo.

### What we will do
- List 2–3 viable concept framings
- Score them on scope, risk, demo clarity, and evidence support
- Reject anything too broad or too hard to defend

### Outputs
- Selected concept direction
- Short rejection notes for discarded options
- Clear statement of what we are **not** building

### Exit criteria
- One narrowed concept is chosen and defensible

---

## Phase 2 — Problem definition + evidence pack

### Goal
Prove that the chosen problem is real, meaningful, and worth solving.

### What we will do
- Describe the current workflow
- Identify where friction, delay, ambiguity, or risk appears
- Gather evidence and prior-art references
- Translate discussion into a concrete problem statement

### Outputs
- Problem brief
- Workflow summary
- Evidence/reference pack
- Prior-art / competitor notes

### Exit criteria
- We can justify the problem clearly to judges in plain English

---

## Phase 3 — MVP boundary + safety framing

### Goal
Define exactly what the prototype does and does not do.

### What we will do
- Lock the single happy-path workflow
- Define one uncertainty / edge branch
- Write the safety boundary and claims language
- Remove overclaiming from the concept

### Outputs
- MVP scope
- Non-goals / exclusions
- Safety boundary notes
- Judge-safe wording for deck and demo

### Exit criteria
- No ambiguity about whether this is assistive support vs autonomous diagnosis

---

## Phase 4 — Demo design + technical plan

### Goal
Turn the research decision into a buildable demo plan.

### What we will do
- Define the primary demo scenario
- Define 1–2 fallback / edge scenarios
- Choose the minimum data model and fixtures
- Sketch the architecture needed for the MVP

### Outputs
- Demo flow
- Screen / interaction plan
- Technical architecture note
- Fixture/data plan

### Exit criteria
- Demo can be described end-to-end before code starts

---

## Phase 5 — Build sprint

### Goal
Build the smallest working prototype that proves the concept.

### Build principles
- One primary workflow first
- Deterministic demo data before ambitious integrations
- Human review step must stay visible
- Prefer reliability over breadth

### Outputs
- Working prototype
- Demo-ready scenario
- Backup path if live integration fails

---

## Phase 6 — Pitch + submission polish

### Goal
Package the work into something judges can understand fast.

### What we will do
- Write the pitch storyline
- Prepare FAQ / challenge responses
- Align demo, wording, and claims
- Finalize required deliverables

### Outputs
- Pitch deck / speaking notes
- Demo script
- Final repo / deliverables checklist

---

## Immediate next steps

1. Rewrite and expand `02_research/ROADMAP.md`
2. Decide the narrowing candidates
3. Lock the first-pass problem statement
4. Build the evidence pack before solution drift starts

## Working reminder

If the idea cannot be explained as **one user + one decision + one output**, it is still too broad.
