# Free-public landing and product gallery

Status: implemented; verification and commit/push handoff in progress.
Stamped: 2026-07-16 12:18 +0000 · Codex.

## Outcome

Position Eamos as a free, research-use genomic evidence tool built for reach and
credibility. Remove the paid funnel. Replace generic feature marketing with
fresh browser captures of the actual report, Workbench, and multi-variant
comparison flows.

This is not a claim that every third-party predictor can be redistributed for
free. Product access and source licensing are separate boundaries.

## Frozen decisions

1. Eamos has no public paid tiers, upgrade path, or checkout funnel.
2. The landing page says access is free. It does not use a `$0` pricing card or
   preserve pricing language in another form.
3. REVEL, SpliceAI, and any other restricted source remain governed by their
   license/provenance/launch-gate metadata. Removing payment does not erase a
   source license.
4. Marketing names only sources Eamos can truthfully expose in the public
   experience. Restricted predictors are not promised in hero, FAQ, auth, or
   source-strip copy.
5. Feature imagery comes from Eamos itself, using safe demo variants and sample
   VCF data. No patient data, browser account identity, secrets, or production
   dashboards may appear.
6. Captures are reproducible from a checked-in, dependency-free headless Chrome
   script. Each image records a route, viewport, readiness condition, and crop.
7. The landing stays an expert instrument: the search remains the primary CTA;
   screenshots demonstrate provenance and workflow, not lifestyle marketing.
8. The hero's right-hand visual is a code-native interactive variant map, not
   stock imagery. It maps one bundled RPE65 change across genomic, transcript,
   protein, and public-evidence representations, with keyboard and
   reduced-motion behavior.

## Information architecture

1. **Hero:** free public access, one variant search, three concrete examples,
   and an interactive DNA locus that explains how one change maps across the
   evidence stack.
2. **Public-source strip:** only sources safe to claim as part of the public
   product.
3. **Real report specimen:** keep the existing evidence specimen as a fast
   glance, but remove synthetic claims about unavailable predictors.
4. **How it works:** query, public-source sweep, sourced report. No licensed
   score claims or fabricated instant timing.
5. **Product gallery:** three large, alternating browser captures:
   - variant report: public gnomAD population evidence and source status;
   - Workbench: sequence context and hands-on analysis;
   - Compare: safe sample-VCF cohort triage.
6. **Founder mission:** retain the personal reason the product exists.
7. **FAQ and footer:** explain public access, research-use scope, source
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
- Replace Terms billing copy with free-access/source-license language.
- Remove subscription-purpose wording from Privacy without touching Supabase
  authentication, RLS, saved variants, or evidence submission behavior.
- Keep backend payment/webhook code dormant. Deleting public UI is not a reason
  to casually weaken its server-side signature, auth, rate-limit, or idempotency
  controls.

### B. Make marketing license-honest

- Remove REVEL and SpliceAI promises from landing, auth marketing, metadata, and
  FAQ copy.
- Keep their report provenance and launch-gate metadata intact where the backend
  returns it.
- Replace product `Free`/`Pro` labels with `Public`/`License review`. Live rows
  defer to `public_serialization_allowed` and `launch_gate`; placeholders use a
  conservative catalog fallback rather than inventing access.

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
  HGVS, protein consequence, and safe public sources.
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
- No landing/auth/legal copy promises REVEL or SpliceAI availability.
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
- No licensed predictor download, redistribution, score fabrication, or license
  workaround.
- No backend predictor removal. Preserve provenance and launch gates.
- No Stripe/Supabase/Render/Vercel mutation or deploy command.
- No patient or private-account screenshot.
- No simultaneous web writers. The landing, shared navigation, legal copy, and
  screenshot gallery are coupled and run as one sequential lane.

## Follow-up after this slice

Archive or explicitly supersede historical pricing plans where they remain
useful only as history, so future agents cannot accidentally resurrect the paid
funnel. Re-capture the three product screens whenever those featured surfaces
change materially.

## Landing roadmap after this slice

### Pass 2: trust and comprehension

- Audit every number, source claim, demo label, and time-saving statement
  against a reproducible artifact. Never turn a fixture into a live-data claim.
- Tighten the hero-to-report narrative around three jobs: identify a variant,
  inspect provenance, and continue into Workbench or Batch.
- Keep the founder mission, but add third-party proof only when a real named
  user or publication can be cited. No invented testimonials or vanity counts.
- Explain source outages, cached fallbacks, and license-gated predictors in one
  compact trust note instead of scattering caveats.

### Pass 3: responsive, accessible, and fast

- Browser-test 360, 390, 768, 1024, 1440, and 1920 px widths, including the
  interactive hero, screenshot crops, sticky nav, and keyboard order.
- Add automated hero interaction coverage for mouse, keyboard, focus-visible,
  screen-reader names, and reduced motion.
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
licensed-score promises, or a client-side security boundary.
