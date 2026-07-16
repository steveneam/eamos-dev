# Variant Report reading experience

Status: complete.

Stamped: 2026-07-16 15:44 +0000 · Codex.

## Outcome

Make `/report` read like one clinical evidence record. Preserve the four
evidence-axis cards Steven likes, remove the extra dashboard layer beneath
them, and begin the detailed read with Clinical evidence. Improve hierarchy,
source presentation, disclosure, state completeness, and visual rhythm across
every numbered section without changing the backend contract.

## Product scene and design register

A clinical geneticist is reading a resolved variant on a wide desktop in a
bright office or laboratory, often with several reference tabs open. They need
the verdict axes immediately, then a defensible source trail in clinical order.

This is a product-register surface. The color strategy stays restrained:
warm-light neutrals and brand teal for navigation and focus, with the frozen
ACMG ramp reserved for clinical meaning. Density remains a feature. The design
work follows `PRODUCT.md`, `DESIGN.md`, and the `impeccable` product reference.

## Locked decisions

1. Keep the four top cards: Computational, Clinical consensus, Population
   frequency, and Lab and functional.
2. The four cards are the only dashboard layer above the numbered evidence
   record.
3. Clinical evidence is section 1 and follows the cards directly.
4. Remove the backend-ranked `ReportSignalDashboard` from the page.
5. Remove the standalone `AdvisorySummaryStrip` from the page. The full
   Eamos-computed ACMG/AMP advisory remains in In-silico, where its points,
   gauge, plane, and waterfall can be audited.
6. Keep the seven-section registry and order:
   Clinical, In-silico, Population, Gene and locus, Disease, Publications,
   Trials.
7. Do not change Pydantic or TypeScript payload contracts in this slice.
8. Do not change call-card clinical semantics, source precedence, thresholds,
   the eleven-engine universal-free catalog, or backend operational metadata.
9. Do not touch `/runs`, providers, environment, migrations, cloud resources,
   deployments, or source materialization.

## Implementation

### Report hierarchy

- `ReportBody.tsx` now renders `CallCardsGrid` directly before
  `clinical_evidence`.
- The mini-card signal dashboard and evidence-fingerprint strip are unmounted.
- `scripts/eamos-web-boundary.mjs` asserts the Call cards → Clinical order and
  blocks either retired summary component from returning to the top flow.

### Numbered chapter presentation

- `Card.tsx` is a report-chapter primitive with a semantic level-two heading,
  dedicated native disclosure button, separate action slot, two-digit chapter
  index, title/source stack, explicit Hide/Show feedback, stable focus
  treatment, and responsive geometry.
- The Clinical chapter index uses the matching ACMG ramp color when a report
  verdict is available. Text still carries the classification meaning.
- Chapter bodies use one calm reading surface and deliberate spacing, allowing
  source-specific panels and visualizations to carry the evidence hierarchy.
- All seven sections, plus their lazy loading and empty/error wrappers, consume
  the same primitive.

### State and source presentation

- Loading, empty, partial, stale, and failed section states share one structured
  layout with status copy, optional detail/action, and honest loading skeletons.
- The VCEP fallback is a compact clinical source-scope note rather than a large
  warning banner. It still states exactly what is and is not source-backed.
- Motion uses the design tokens and remains covered by the global
  `prefers-reduced-motion` guard.

## Owned files

- `app/web/components/report/report-client/ReportBody.tsx`
- `app/web/components/report/report-client/ReportSectionPrimitives.tsx`
- `app/web/components/report/AdvisorySummaryStrip.tsx` (removed)
- `app/web/components/ui/Card.tsx`
- `app/web/app/globals.css`
- `scripts/eamos-web-boundary.mjs`
- `ROADMAP.md`
- `plans/README.md`
- `plans/variant-report-experience/plan.md`
- `PROGRESS.md`
- `agent_handoff/CURRENT.md`

The watcher-owned `agent_handoff/FROM-SWORDFISH.md` is explicitly excluded.

## Acceptance criteria

- Four call cards remain visually and semantically intact.
- Clinical evidence is the first UI beneath those cards.
- No evidence-signal mini-card grid or standalone fingerprint strip appears
  between the cards and Clinical.
- Every numbered section has clear chapter, source, action, and disclosure
  hierarchy.
- Collapse/expand is keyboard reachable, exposes `aria-expanded` and
  `aria-controls`, and never nests interactive elements.
- Section state copy is visible in text and does not rely on color.
- The report stays readable across supported desktop widths, with horizontal
  overflow contained for dense tables and visualizations.
- No backend/frontend contract, predictor access, source policy, or clinical
  threshold changes.

## Verification

- `npm run verify` passed in 155.2 seconds through repository guards, full
  frontend/backend lint and tests, TypeScript, and the production build.
- The frontend-contract canary passed independently. A local Next proxy ->
  FastAPI fixture-mode smoke returned the complete four-card report payload.
- Registry validation and report preflight passed at 1024, 1280, and 1440 px:
  seven required slots, no missing anchors, no horizontal overflow, and no
  fixable offenders.
- Browser fixture review at 1440 px passed for hierarchy, mouse and keyboard
  disclosure, accessible heading order, control names, focus, and console.
- Refined desktop Lighthouse scored Accessibility 94, Best Practices 100, and
  SEO 100. Older contrast debt inside dense evidence widgets remains explicitly
  queued for the accessibility follow-up.
- `git diff --check` and focused changed-file ESLint passed.

## Deliberate follow-up

After this presentation slice, use representative live variants to identify
real source-backed gaps. Do not infer missing backend work from an old plan.
Persistent assets, provider changes, cloud mutations, migrations, and deploys
remain separately gated.
