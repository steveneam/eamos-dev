# Free-access landing and product gallery

Status: Pass 2 trust/comprehension implemented and verified; broader Pass 3 pending.
Stamped: 2026-07-16 13:43 +0000 · Codex.

## Outcome

Position Eamos as a free, research-use genomic evidence tool built for reach and
credibility. Remove the paid funnel. Replace generic feature marketing with
fresh browser captures of the actual report, Workbench, and multi-variant
comparison flows.

Steven's 2026-07-16 decision makes the full wired predictor catalog part of the
same free product now. License/provenance/launch-gate fields remain in backend
rows, health, and preflight as informational metadata for a later keep/remove
decision; they do not create a product tier or hide a returned score.

## Frozen decisions

1. Eamos has no public paid tiers, upgrade path, or checkout funnel.
2. The landing page says access is free. It does not use a `$0` pricing card or
   preserve pricing language in another form.
3. REVEL, SpliceAI, AlphaMissense, ESM1b, PrimateAI-3D, MetaLR, CI-SpliceAI,
   Pangolin, CADD, GPN-MSA, and CAPICE are all included in the free catalog.
4. The product has no `Free`/`Pro`, `Public`/`License review`, or equivalent
   predictor-access split. A missing score is a runtime/data state, not an
   entitlement state.
5. Feature imagery comes from Eamos itself, using safe demo variants and sample
   VCF data. No patient data, browser account identity, secrets, or production
   dashboards may appear.
6. Captures are reproducible from a checked-in, dependency-free headless Chrome
   script. Each image records a route, viewport, readiness condition, and crop.
7. The landing stays an expert instrument: the search remains the primary CTA;
   screenshots demonstrate provenance and workflow, not lifestyle marketing.
8. The hero's right-hand visual is a code-native interactive variant map, not
   stock imagery. It maps one bundled RPE65 change across genomic, transcript,
   protein, and full-evidence-stack representations, with keyboard and
   reduced-motion behavior.

## Information architecture

1. **Hero:** free access, one variant search, three concrete examples,
   and an interactive DNA locus that explains how one change maps across the
   evidence stack.
2. **Evidence-source strip:** include the wired source set, including SpliceAI
   and REVEL.
3. **Real report specimen:** keep the existing evidence specimen as a fast
   glance, without fabricating scores the bundled artifact does not contain.
4. **How it works:** query, full evidence sweep, sourced report. Name the full
   predictor catalog and keep actual runtime state honest.
5. **Product gallery:** three large, alternating browser captures:
   - variant report: gnomAD population evidence and source status;
   - Workbench: sequence context and hands-on analysis;
   - Compare: safe sample-VCF cohort triage.
6. **Founder mission:** retain the personal reason the product exists.
7. **FAQ and footer:** explain free access, research-use scope, source
   availability, caching, and privacy.

The pricing climax disappears. The product gallery becomes the visual proof and
the mission section becomes the emotional close.

## Current implementation slice

### A. Remove monetization UI

- Remove `Pricing` from `LandingClient`, navigation, footer, legal nav, account
  menu, and account header.
- Remove the checkout route/components and the client pricing model.
- Move the shared secondary-page header out of `components/pricing` before
  deleting that package.
- Replace Terms billing copy with universal free-access language.
- Remove subscription-purpose wording from Privacy without touching Supabase
  authentication, RLS, saved variants, or evidence submission behavior.
- Keep backend payment/webhook code dormant. Deleting public UI is not a reason
  to casually weaken its server-side signature, auth, rate-limit, or idempotency
  controls.

### B. Make predictor access universal

- Restore REVEL, SpliceAI, and the complete predictor catalog to landing, auth,
  metadata, FAQ, and report copy.
- Remove predictor access pills and disease-source policy chips. Do not replace
  them with another universal `Free` badge on every row; one product-level free
  statement is enough.
- Ignore the retired `excluded_predictors` access-policy hint when constructing
  report-profile rows and computational call cards, so returned scores remain
  available across backend and frontend surfaces.
- Keep `public_serialization_allowed`, `launch_gate`, license, and provenance
  metadata intact in backend contracts, rows, health, and preflight. The UI does
  not use those fields as an entitlement filter.
- Keep missing scores honest: `Awaiting predictor data` or `Score unavailable`
  means no source-backed row was returned, never that an upgrade is required.

### C. Ship real feature captures

- Add `scripts/eamos-capture-landing-features.mjs` using native Chrome DevTools
  Protocol, with no browser automation dependency.
- Capture at 1440 × 960 CSS pixels, DPR 1 for crisp but bounded files.
- Use these safe flows:
  - `/report?fixture=rpe65-negative`, fully offline report fixture;
  - `/workbench?gene=RPE65&cdna=c.260A%3EG&transcript=NM_000329.3`, bundled
    viewer fallback if the local backend is absent;
  - `/compare`, with the checked-in sample VCF staged into session storage by
    the browser harness, then rendered without automatic network generation.
- Capture native quality-72 WebP from Chrome and keep each asset below 256 KiB.
- Replace the current collage and Workbench placeholder with three decisive
  product bands. Each image gets descriptive alt text, route CTA, intrinsic
  dimensions, responsive `sizes`, and a visible “Real browser capture” note.
- Preserve reduced-motion behavior. Screenshots are the baseline; a future
  short muted video must not autoplay for reduced-motion users and must stay
  inside an explicit performance budget.

### D. Make the hero visual earn its space

- Replace the ambient right-side strand decoration with an interactive RPE65
  variant map.
- Keep the actual query identity explicit: GRCh38 genomic change, transcript
  HGVS, protein consequence, and named evidence sources.
- Make the central locus and all four representation controls keyboard
  operable, with `aria-pressed`, an announced readout, visible focus, and a
  static reduced-motion state.
- Keep it desktop-only where the hero has a true right-hand column; preserve a
  compact, search-first mobile hero.

## Capture freshness contract

The checked-in assets are product documentation. Re-capture when a visible
featured surface changes materially. The capture script fails when its
readiness selector is missing; the asset check fails on route-contract,
dimension, size, byte-count, or hash drift. Browser output must be reviewed for
blank or error states before commit.

Suggested filenames:

```text
app/web/public/features/report-demo.webp
app/web/public/features/workbench-demo.webp
app/web/public/features/compare-demo.webp
app/web/public/features/capture-manifest.json
```

The manifest records the source commit, route, viewport, capture timestamp, and
SHA-256 for each asset. It contains no backend origin, credential, local path,
or user identifier.

## Verification

- `rg` finds no user-facing pricing, billing-plan, upgrade, checkout, or paid
  subscription language in active `app/web` surfaces.
- The free-access canary confirms all eleven predictor names remain in the
  report catalog, REVEL and SpliceAI remain in product copy, and no active
  access-tier or `License review` UI returns.
- `node scripts/eamos-capture-landing-features.mjs --check` validates asset
  presence, dimensions, hashes, and manifest routes without launching Chrome.
- Desktop and mobile landing browser smoke verifies image crops, no horizontal
  overflow, keyboard links, and reduced-motion behavior.
- Web boundary guard, Vitest, TypeScript, ESLint, production build, backend
  frontend-contract canary, and payment/auth regression tests stay green.
- Security review confirms no change to Supabase sessions/RLS and no client-side
  entitlement or payment decision was introduced.

## Deliberate non-goals

- No Supabase migration, policy, provider, auth, or cloud change.
- No new predictor asset download, redistribution, or score fabrication in this
  copy/UI slice.
- No backend predictor removal or metadata erasure. Preserve provenance and
  launch gates for the later founder decision, but do not turn them into access
  controls now.
- No Stripe/Supabase/Render/Vercel mutation or deploy command.
- No patient or private-account screenshot.
- No simultaneous web writers. The landing, shared navigation, legal copy, and
  screenshot gallery are coupled and run as one sequential lane.

## Follow-up after this slice

Archive or explicitly supersede historical pricing plans where they remain
useful only as history, so future agents cannot accidentally resurrect the paid
funnel. Re-capture the three product screens whenever those featured surfaces
change materially.

## Pass 2 implementation evidence

Verified: 2026-07-16 13:43 +0000 · Codex.

- Replaced the unbounded “any genetic variant” promise with the supported-input
  workflow: identify the variant, inspect provenance, continue into Workbench or
  Batch. Removed the founder quote's unmeasured time-saving and treatment-timing
  claims without weakening the Genomics for All mission.
- Corrected the USH2A specimen: its documented 0.182% maximum AF is now a raw
  gnomAD fact, not the contradicted “Low Frequency” verdict. Removed the
  unratcheted “3 Unique” count and made the snapshot date/static state visible.
- Consolidated live, cached, bundled-demo, and unavailable semantics into one
  compact trust note. Missing values remain source states, never access states.
- `scripts/eamos-web-boundary.mjs` now binds the RPE65 hero identity to the
  tracked backend coordinate fixture, keeps all eleven predictor names visible,
  and blocks the audited overclaims/specimen drift.
- `scripts/eamos-capture-landing-features.mjs --verify-hero` now exercises real
  mouse and keyboard activation, singular `aria-pressed`, the accessibility
  tree, atomic status announcements, focus-visible, reduced motion, and the
  compact mobile hide contract. Desktop 1440 × 960 and mobile 390 × 844 visual
  review passed. Featured report/Workbench/Compare surfaces did not change, so
  their checked-in captures remain current.
- `npm run verify` passed in 148.2 seconds: structural/capture/contract guards,
  frontend and backend lint/format, TypeScript, 18 Vitest files / 161 tests,
  full backend pytest, and the 17-route production build. No source, provider,
  auth, payment, Supabase, Render, Vercel, migration, or deploy mutation ran.

## Landing roadmap after this slice

### Pass 2: trust and comprehension (complete 2026-07-16)

- Audit every number, source claim, demo label, and time-saving statement
  against a reproducible artifact. Never turn a fixture into a live-data claim.
- Tighten the hero-to-report narrative around three jobs: identify a variant,
  inspect provenance, and continue into Workbench or Batch.
- Keep the founder mission, but add third-party proof only when a real named
  user or publication can be cited. No invented testimonials or vanity counts.
- Explain source outages, cached fallbacks, and unavailable scores in one compact
  trust note instead of scattering caveats.

### Pass 3: responsive, accessible, and fast

- Browser-test 360, 390, 768, 1024, 1440, and 1920 px widths, including the
  interactive hero, screenshot crops, sticky nav, and keyboard order.
- Keep the automated hero interaction contract green for mouse, keyboard,
  focus-visible, screen-reader names, reduced motion, and compact mobile layout.
- Establish a landing performance budget for LCP, CLS, total screenshot bytes,
  and shipped JavaScript. Keep the already-compressed screenshots unoptimized
  by Next because they are deterministic WebP documentation assets.
- Produce a real 1200 × 630 social card from the free-public positioning and
  verify metadata previews.

### Pass 4: free-product discovery loop

- Make sample reports and the sample VCF flow easy to share without exposing
  account identity or genomic query parameters to analytics.
- Add lightweight, privacy-safe events for example selection, report open,
  Workbench open, and Batch sample load. Do not capture variant content.
- Review search/FAQ copy using observed user questions, then improve the page
  around confusion actually seen rather than adding more sections by default.

Each pass ends with desktop/mobile browser evidence, the structural canaries,
and a measured before/after. None reintroduces billing, entitlement tiers,
predictor-access labels, or a client-side security boundary.
