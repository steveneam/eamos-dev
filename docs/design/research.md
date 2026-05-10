# Research notes

## Project frame
- HSIL needs a **desktop-only design pass** for the demo phase.
- The page is a **single clinician workspace**, not a multi-page product shell.
- The workflow must cover: batch submission, run action, selected PDF preview, evidence, clinician review, and approve/drop outcome.
- The product remains clinician-facing referral support, not patient-facing reporting and not a generic genomics dashboard.

## Anchor references
- Reference 1: user-provided light clinical workspace screenshot with a large central work area and a narrower review rail.
  - Borrow: calm light palette, strong content hierarchy, wide primary canvas plus right-side decision/support rail.
  - Avoid: extra product-shell chrome, dashboard-feeling widgets, or navigation-heavy framing.
- Reference 2: user-provided workflow reference image showing a denser review layout.
  - Borrow: explicit workflow grouping, visible evidence and review decision area, strong operational clarity.
  - Avoid: over-dense enterprise clutter and generic admin-module repetition.
- Reference 3: user hand-drawn sketch.
  - Locked elements: `submit batch of reports`, `run button`, `report in PDF preview`, `clinician review + drop/approval`, `evidence`.
  - Strategic read: batch intake belongs near the top; PDF preview is the main canvas; evidence and clinician decision belong in the support rail.
- Reference 4: Genomics England PanelApp (`https://panelapp.genomicsengland.co.uk/`).
  - Borrow: evidence-first language and confidence/status cues.
  - Avoid: browser-style tables, dense technical exploration UI, or curator-tool complexity.

## Anti-references / drift families
- Anti-reference 1: generic admin dashboards with sidebars, tabs, KPIs, and analytics cards.
- Anti-reference 2: consumer genetics or patient-education report UIs.
- Anti-reference 3: dark AI cockpit styling with dramatic gradients and assistant-first framing.

## Public implementation references
- Repo or implementation 1: `https://panelapp.genomicsengland.co.uk/`
- Repo or implementation 2: `https://github.com/shadcn-ui/taxonomy`
- Repo or implementation 3: `https://github.com/TailAdmin/free-react-tailwind-admin-dashboard`

## Repeated structure cues
- Compact top bar with product label, batch status, and selected-report status.
- Wide main content area for the selected report preview.
- Batch queue / intake area should be visible without becoming a sidebar.
- Review rail should hold evidence, uncertainty, clinician notes, and final approve/drop controls.
- Strong section headings are enough; no tabs or page-switch hints are needed.

## Repeated visual cues
- Soft off-white background with white cards and pale neutral surfaces.
- Low-saturation teal / blue-green accents and restrained status colors.
- Generous whitespace and large readable blocks.
- Thin borders, subtle shadow, restrained radius.
- Avoid decorative medical motifs or flashy gradients.

## Prompt ingredients worth keeping
- desktop-first clinician workspace
- batch submission of reports
- run batch action
- selected PDF preview
- evidence panel
- clinician review
- approve / drop controls
- light clinical palette
- no sidebar
- no tabs
- no page-switch hints

## What to borrow
- Main canvas + support rail composition.
- Light, clean, clinical visual system.
- Evidence/status chips and concise trust language.
- One obvious operational CTA near intake/run.

## What to avoid
- Sidebars, tabs, breadcrumbs, stepper UI, or navigation chrome.
- Analytics cards and fake KPI panels.
- Consumer-facing language.
- Autonomous diagnosis or eligibility claims.
- Mobile-driven stacking logic in this phase.

## Open questions
- Whether the batch queue should be a horizontal strip or a compact left block inside the main area.
- Whether approve/drop belongs beside clinician notes or in a separate decision card.
- How much extracted metadata should sit below the PDF preview versus inside the right rail.
