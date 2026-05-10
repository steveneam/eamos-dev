# Narrowing Options (v1)

## How this shortlist was produced

We fanned out across **5 research lanes**:
- prior HSIL / winner-pattern signals
- current healthcare/news signals
- academic / arXiv signals
- GitHub / open-source feasibility signals
- team-fit signals

That produced **25 candidate ideas**.

This shortlist keeps the **5 strongest options** based on:
1. **Source strength** — official, academic, or strong OSS feasibility evidence
2. **Novelty** — not just a generic chatbot or broad "AI for healthcare" claim
3. **Hackathon buildability** — can be demoed with deterministic data and a tight workflow
4. **Judge fit** — clear health-system value, visible user, visible decision moment
5. **Team fit** — useful overlap with clinical, genomics, AI/data, nursing, and product/build skills

## Current recommendation

These are the **five best candidates to discuss seriously with the team**.

---

## Option 1 — Genomic ADR Guardrails for High-Risk Inpatient Prescribing

**Primary user:** ward nurses + pharmacists checking high-risk inpatient meds before administration

**Problem:** genotype-informed drug safety guidance rarely appears at the point where bedside med errors and preventable adverse drug events actually happen.

**Why it made the top 5:**
- Strong **team fit**: genomics + nursing + full-stack + explainable decision support
- Strong **novelty**: nurse-facing pharmacogenomic guardrails is more specific and more operational than generic prescriber CDS
- Strong **demo shape**: med list + genotype input -> alert + rationale + recommended next action

**Main caution:** keep the scope narrow to a small number of gene-drug pairs and one inpatient medication workflow.

**Short reason:** high safety value, unusually good fit for this team, and credible if kept narrow.

**Sources:**
- https://pmc.ncbi.nlm.nih.gov/articles/PMC5546947/
- https://github.com/PharmGKB/PharmCAT

---

## Option 2 — Planner-Auditor Discharge Safety Copilot

**Primary user:** discharge nurses and ward medical staff

**Problem:** discharge plans and summaries often miss critical follow-up actions, medication checks, or red-flag gaps.

**Why it made the top 5:**
- Strong **judge fit**: easy to explain as a patient-safety and workflow-reliability tool
- Strong **workflow clarity**: draft plan first, then deterministic audit before sign-off
- Strong **hackathon feasibility**: works well with mocked FHIR-like inputs and clear rule checks

**Main caution:** avoid drifting into a broad discharge-summary generator; keep it as a safety check + action-plan workflow.

**Short reason:** one of the cleanest high-value workflow ideas in the whole pool.

**Sources:**
- https://arxiv.org/abs/2601.21113
- https://arxiv.org/abs/2507.05319

---

## Option 3 — Prior Authorization TAT Monitor + Auto-Completeness Checker

**Primary user:** specialist office / clinic admin teams submitting prior authorization requests

**Problem:** treatment is delayed by fragmented prior-auth workflows, missing fields, and poor visibility on payer turnaround deadlines.

**Why it made the top 5:**
- Strong **source quality**: official CMS policy/timeline signals
- Strong **buildability**: easy to demo with forms, deadline logic, and escalation rules
- Strong **health-systems value**: directly tied to access, throughput, and compliance pressure

**Main caution:** less flashy than image/genomics ideas, so the pitch has to emphasize policy timing + workflow pain clearly.

**Short reason:** very concrete, official-source-backed, and hard to dismiss as vague AI theater.

**Sources:**
- https://www.cms.gov/newsroom/press-releases/cms-finalizes-rule-expand-access-health-information-and-improve-prior-authorization-process
- https://www.cms.gov/priorities/innovation/files/document/wiser-model-frequently-asked-questions

---

## Option 4 — PRS-Driven Glaucoma First-Responder Triage

**Primary user:** community optometry / ophthalmology clinics with limited specialist time

**Problem:** high-risk glaucoma patients can be referred too late while low-risk cases consume limited specialist capacity.

**Why it made the top 5:**
- Strong **team fit**: ophthalmology + genomics + AI/data is unusually relevant here
- Strong **novelty**: combines image/risk features into a triage-ready output instead of just a diagnostic model
- Strong **story potential**: clear user, clear urgency tier, clear referral workflow

**Main caution:** do not let the MVP turn into a full diagnostic model; keep it as triage support with simplified inputs and mocked/synthetic cases.

**Short reason:** best pure team-fit option from the whole brainstorm set.

**Sources:**
- https://pmc.ncbi.nlm.nih.gov/articles/PMC10462203/
- https://github.com/smilell/AG-CNN

---

## Option 5 — Imaging Delay Prioritizer for CT/MRI

**Primary user:** radiology triage coordinators / oncology pathway leads

**Problem:** scan bottlenecks delay diagnosis and downstream treatment, especially when urgent cases are not prioritized well enough.

**Why it made the top 5:**
- Strong **problem evidence**: backlog and delay data are concrete and recent
- Strong **system impact**: queue prioritization is easy for judges to understand as a health-systems intervention
- Strong **demoability**: intake rules + priority banding + escalation dashboard is straightforward to prototype

**Main caution:** operational queue tools can look dry, so the demo needs a clear patient-pathway consequence.

**Short reason:** one of the strongest data-backed operational options, with a clean before/after story.

**Sources:**
- https://www.rcr.ac.uk/news-policy/latest-updates/diagnostic-and-cancer-waiting-times-data-for-january-2024/
- https://www.rcr.ac.uk/news-policy/latest-updates/rcr-statement-on-nhs-england-s-may-2024-diagnostic-imaging-and-cancer-waiting-times/

---

## Why some ideas were not shortlisted

A few ideas were interesting but dropped because they were weaker on one of the key filters:
- **winner-pattern-only ideas** (good HSIL vibe, thinner external workflow evidence)
- **platform ideas** like synthetic FHIR environments (useful tooling, weaker end-user problem)
- **consumer tools** that felt less aligned with a sharp health-systems workflow
- **multimodal diagnostic ideas** that were exciting but too heavy for a tight hackathon MVP

## My current read

If the goal is **best overall shortlist**, the strongest discussion set is:
1. **Genomic ADR Guardrails**
2. **Planner-Auditor Discharge Safety Copilot**
3. **Prior Authorization TAT Monitor**
4. **PRS-Driven Glaucoma Triage**
5. **Imaging Delay Prioritizer**

If the goal is **best fit for this team specifically**, start discussion with:
1. **Genomic ADR Guardrails**
2. **PRS-Driven Glaucoma Triage**
3. **Planner-Auditor Discharge Safety Copilot**

## Next step

Turn these 5 into a comparison table with scoring columns:
- credibility
- novelty
- buildability
- judge appeal
- team fit
- data feasibility

Then choose the top 1–2 for deeper problem-definition work.
