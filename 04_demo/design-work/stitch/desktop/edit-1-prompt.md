# Stitch edit prompt

Keep the current desktop structure and light clinical styling.

Preserve:
- the overall one-page layout
- top batch-intake strip
- large central selected PDF preview
- right-side Evidence rail
- right-side Clinician review rail
- exact labels: `Batch review workspace`, `Submit reports`, `Selected report`, `Evidence`, `Clinician review`, `Run batch`, `Approve`, `Drop`

Improve:
- remove the extra top-framing actions `Export CSV` and `Sign-off Batch`
- do not add any other top-right actions that feel like separate workflow destinations
- keep only quiet status information plus the main `Run batch` action
- rewrite the selected report content away from epilepsy / SCN1A / POLG language
- make the selected report and evidence feel aligned to genomic referral support, preferably inherited retinal disease / RPE65 lane context
- keep the center panel feeling like a PDF preview rather than an app sub-page
- keep evidence concise and source-like, not dashboard-like

Semantic lock:
- keep required nouns: batch, report, evidence, clinician review
- preferred language: genomic referral support, review required, VEP, ClinVar, SpliceAI, RPE65
- do not use: dashboard, analytics, patient portal, Export CSV, Sign-off Batch, epilepsy, SCN1A, POLG

Pre-approval lock:
- page title must stay `Batch review workspace`
- section headings must stay exactly the same
- keep both final decision buttons visible: `Approve` and `Drop`

Do not introduce:
- tabs
- sidebars
- breadcrumbs
- wizard/stepper UI
- KPI or analytics cards
