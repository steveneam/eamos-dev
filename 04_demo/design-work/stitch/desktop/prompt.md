# Stitch prompt

Create a **desktop-only** page for a clinician-facing genomic batch review workspace.

Goal:
Show one complete review workflow in a single page: submit a batch of genomic reports, run the workflow, inspect the selected report in a large PDF preview, check supporting evidence, and complete clinician review with approve/drop actions.

Required structure:
- compact top bar with `HSIL demo`, batch status, and selected report status
- visible top batch intake area labeled `Submit reports` with queued reports and a clear `Run batch` action
- large central card labeled `Selected report` containing a strong PDF preview mockup
- nearby extracted metadata / parsed report details, but keep the PDF preview as the main visual focus
- right-side support rail containing `Evidence` and `Clinician review`
- clinician review area must visibly include notes plus both `Approve` and `Drop` actions

Responsive intent:
- This pass is desktop-only. Do not optimize for mobile or tablet.
- Keep the full workflow visible in one desktop composition.
- Do not add any page-switch hints or secondary app destinations.

Visual direction:
- light clinical palette: soft off-white background, white cards, muted teal or blue-green accent
- calm, credible, clean, high-whitespace composition
- subtle borders and soft shadows
- no dark theme, no neon, no dramatic gradients

Semantic lock:
- Required nouns: batch, report, evidence, clinician review
- Preferred discovery words: review required, VEP, ClinVar, SpliceAI, PDF preview
- Banned drift words: dashboard, analytics, patient portal, wizard, stepper, tabs, sidebar

Pre-approval lock:
- Page title: `Batch review workspace`
- Preserve exact labels for: `Submit reports`, `Selected report`, `Evidence`, `Clinician review`, `Run batch`, `Approve`, `Drop`

Use this copy:
- `Genomic referral support`
- `Batch review workspace`
- `Submit reports`
- `Run batch`
- `Selected report`
- `Evidence`
- `Clinician review`
- `Approve`
- `Drop`
- `Decision support only. Not a diagnosis. Clinician review required.`

Fix these issues:
- no sidebar
- no tabs
- no page-switch hints
- do not make evidence or queue bigger than the selected PDF preview
- batch intake must be visible without becoming a separate sectioned app shell

Do not introduce:
- KPI widgets
- analytics cards
- multi-page navigation
- patient-facing language
- autonomous diagnosis claims
