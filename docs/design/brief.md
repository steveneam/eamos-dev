# Project brief

## Product summary
A desktop-first HSIL demo workspace for clinician-facing genomic report batch review. The page must show one coherent workflow: submit a batch of reports, run the workflow, inspect the selected report in a large PDF preview, review supporting evidence, and make a clinician approve/drop decision.

## Target user
Clinician reviewer, genetics reviewer, referral coordinator, or specialist team member reviewing batched genomic reports.

## Primary goal
Make the demo instantly legible as a real clinical review workflow with one page only and no navigation detours.

## Core screens and pages
- One page only: desktop batch-review workspace.
- No sidebar destinations.
- No tabs.
- No page-switch hints or multi-step wizard chrome.

## Information hierarchy
1. Top bar with product label, batch state, and selected report status.
2. Batch submission / queue area with visible run action.
3. Large selected PDF preview as the main focal region.
4. Supporting extracted details / metadata under or beside the preview.
5. Right-side rail for evidence, uncertainty, clinician review, and approve/drop controls.

## Reference cues
- Use the user-provided light workspace screenshots as structural and visual anchors.
- Use the user sketch as the locked module list.
- Use evidence/status density from genomics review tools, but keep the UI much cleaner.

## Visual tone
- Light, clinical, calm, credible.
- Off-white / pale neutral background.
- White cards with subtle borders and soft shadows.
- Muted teal / blue-green accent.
- Clear typography and generous whitespace.

## Constraints
- Desktop-first only.
- No mobile/tablet layout work in this pass.
- One-page workflow only.
- No sidebar.
- No tabs.
- No page-switch hints.
- Must include batch submission, run button, PDF preview, evidence, clinician review, and approve/drop actions.
- Must remain clinician-facing and review-required.
- Must not imply autonomous diagnosis.

## Responsive priority
- Source of truth breakpoint: desktop-only for this phase
- Required mobile modules: not in scope
- Tablet expansion rules: not in scope
- Desktop expansion rules: use a large central preview canvas with a supporting right rail and visible batch intake area
- Copy that must stay locked across breakpoints: `Batch review workspace`, `Submit reports`, `Run batch`, `Selected report`, `Evidence`, `Clinician review`, `Approve`, `Drop`
- Probe failure signals to watch for: sidebar drift, tab drift, dashboard/KPI drift, consumer-report drift, or loss of the PDF-preview-first hierarchy

## Success criteria
- The page reads as a real clinician workflow in one glance.
- The selected PDF preview is clearly the main focal area.
- Evidence and clinician decision controls are visible and credible.
- The batch submission area is present without becoming a separate page.
- The design looks implementation-ready for the later build phase.

## Open questions
- Whether the queue is best shown as a compact table, stacked cards, or pill list.
- Whether approve/drop should include a short decision reason field by default.
- Whether extracted metadata should be a separate lower band or inside the main preview card.

## Approval status
- State: approved
- Notes: Leo explicitly asked to rerun the design with Stitch and use the skill-like workflow without mobile/tablet layout.
