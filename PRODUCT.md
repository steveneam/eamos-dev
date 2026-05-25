# Eamos — Product Brief

> Brand/tone/strategy context for design work. Drafted from `README.md` + `DESIGN.md`
> (2026-05-26). `DESIGN.md` owns tokens/components; this file owns *why* and *for whom*.

register: product

Eamos is a **dual-register** product. Most surfaces are **product** register
(design serves the work): `/report`, `/workbench`, `/account`, `/checkout`. The
marketing surfaces are **brand** register (design is the product): `/` landing,
`/privacy`, `/terms`. Pick the register from the surface in focus; this field is
only the fallback.

## Users

- **Clinical geneticists & genetic counsellors** — interpreting a specific
  patient variant under time pressure. Need a verdict fast, then audit-grade
  evidence they can defend. Will not trust a number they cannot click through to
  its source.
- **Research scientists (molecular / translational genetics)** — exploring a
  gene/variant, designing primers and gRNAs, comparing variants. Live in the
  Workbench. Value density and keyboard speed over hand-holding.
- **Lab directors / PIs (buyers)** — evaluate on credibility and rigor, not
  flash. The interface itself is part of the trust argument.

Context of use: desktop, bright office/lab lighting, often many tabs open,
frequently mid-task and impatient. Not a phone-first consumer audience.

## Product purpose

Collapse "open six database tabs to interpret one variant" into a single
structured, sourced report, plus a sequence Workbench for hands-on design work.
The search bar IS the homepage. DNA coding notation (`c.260A>G`) is the primary
identity everywhere; protein change is derived and secondary.

## Brand

- **Clinical, professional, premium — not consumer, not corporate.** Dense but
  scannable. The polish comes from hierarchy, restraint, and motion, never
  ornament. "Premium, not decorated."
- **Trust is the brand.** Every score/classification/frequency links to its
  source. The look must read as *instrument*, not *marketing site*.
- Brand teal `#1D9E75` on warm-white (product) / warm-brown (landing) surfaces.
  Display **Spectral** (editorial serif, heading-role only), body **Inter**, mono
  **JetBrains Mono**. The editorial register is justified by the journal/evidence
  reading context; fonts are deliberate non-reflex picks (avoid the editorial
  serif + mono-label + ruled-column template fingerprint).
- AU-first company (eamos.com.au, has ABN); code stays domain-agnostic.

## Tone (copy)

- Active voice, clinical register, **no hedging**. Lead with the gene, variant,
  or finding. Never open with "This report…", "Based on…", "Please note…".
- Numbers carry units and references ("Scotopic b-wave ~18 µV, ref >150 µV"),
  never vague ("reduced responses").
- No em dashes. Every word earns its place.

## Anti-references (do NOT look like these)

- **Benchling rainbow** sequence colors. Eamos uses a muted ~25%-chroma base
  palette, never saturated ATCG rainbow.
- **Franklin / Genoox** — direct competitor. No Franklin chip, no link, no
  visual echo.
- **Consumer DNA brands** (23andMe / Ancestry style): cutesy helixes, pastel
  gradients, lifestyle photography, emoji. Eamos is an instrument for experts.
- **Generic SaaS slop**: gradient hero text, identical icon-card grids, the
  hero-metric template, glassmorphism-by-default, purple/indigo "AI" gradients.
- **Dark-neon "biotech" cliché**: neon-green-on-black helix, sci-fi HUD chrome.
  This is the first category reflex for genomics and must be actively avoided.

## Strategic principles (the invariants a redesign must not break)

1. **Every interaction gets a response (the lynchpin).** When the user does
   anything, the interface answers. Buttons carry default, hover, pressed/active,
   disabled, and loading states; inputs carry focus, error (a real message, not a
   bare red border), and where useful warning states; data fetches show loading,
   completed actions show success, meaningful state changes are acknowledged. The
   response must be **honest** (reflects real state, never fabricated progress),
   **accessible** (error and status in text + ARIA, not color alone; focus always
   visible and keyboard-reachable), **calm** (skeletons for content regions,
   spinners for inline/button waits; a response can be instant, not always an
   animation), and **reduced-motion-safe**. A dead click is a bug. This composes
   with impeccable's product-register state completeness, not against it.
2. **Verifiability over flash.** Source link on every data point stays. If a
   bolder treatment hides or weakens provenance, it is wrong.
3. **DNA notation is primary**, protein secondary, always.
4. **Semantic classification colors are a clinical language** (Pathogenic→Benign
   tiers, predictor score scales): one ordered ramp, changed only by explicit
   owner decision, never an incidental palette choice.
5. **Clinical core is non-negotiable**: 0.5px hairlines are load-bearing, no
   font weight > 700, no decorative gradients (only ≤4% functional washes),
   motion reflects real state only, always ship the reduced-motion guard.
6. **Density is a feature.** Don't trade scannability for whitespace drama.
7. **`/runs` (Layer 2) is frozen** on the v1 system. Out of scope for redesign.

## Where boldness is allowed to live

The brand surfaces (landing/legal) carry the expressive load. On product
surfaces, "bolder" means sharper hierarchy, a more confident signature element,
better motion and typographic rhythm, and a more distinctive-yet-clinical color
strategy, not ornament that competes with the data.
