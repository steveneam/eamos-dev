# Eamos v2 — Site-wide Bolder Redesign (impeccable)

> Status: PLAN, awaiting execution. Created 2026-05-26 (Claude). Frontend lane
> (`app/web/**`). Driven by the `impeccable` skill + 5 read-only surface audits.
> Locked creative direction: **The Reading Room, teal kept** (chosen by Steven
> 2026-05-26: serif + ruled-column structure; brand stays teal, no rebrand, no
> clinical color collision).
> Context briefs: `PRODUCT.md` (brand/tone/invariants), `DESIGN.md` (current v2 system).

---

## 0. TL;DR

Apply the `impeccable` methodology across the entire `app/web` site as a **full
bolder redesign**, unified under one design language (**The Reading Room**) so
the brand surfaces (landing/legal) and product surfaces (report/workbench/
account/checkout) read as one world, loud vs precise, instead of today's
"dramatic dark-emerald marketing site → plain SaaS-light app" split.

Scope: Landing+legal, Report, Workbench (Next), Account/Checkout/Auth.
Out of scope: `/runs` (frozen v1), `app/frontend` Vite (read-only reference),
`app/backend` (Codex lane). `/runs`, AlphaMissense display, and Franklin stay
as-is.

Foundation (token + type + primitives) lands **first and serially** because every
surface inherits it; surfaces then redesign in **parallel**; Workbench is gated
on finishing its pass-2 migration.

---

## 1. Goal & success criteria

- One coherent, distinctive, non-category-reflex design language site-wide.
- OKLCH token system; zero inline hex in components; zero impeccable "absolute
  ban" patterns remaining.
- Real type hierarchy (>=1.25 scale/weight steps), consistent spacing/alignment
  via shared tokens.
- Every PRODUCT.md invariant preserved (clinical trust, source links, DNA-primary,
  frozen semantic colors, hairlines, weight<=700, honest motion, density).
- The live clinical bug (ClassificationBadge Likely-Benign-renders-blue) fixed.
- Verified per surface in the browser on eamos-dev before sign-off.

Definition of done per surface: impeccable `audit` + `critique` pass clean,
`quality-reviewer` pass clean, browser-verified, no console errors, reduced-motion
and keyboard paths intact.

---

## 2. Locked creative direction — THE READING ROOM

**Thesis:** the interface is where clinicians read evidence and reach verdicts.
Typography is the architecture; the data is the decoration.

**Scene that forces the theme:** a genomics department's journal-reading room.
Desk-lamp warm cone light, Nature Genetics open on a standing desk, cool window
fill. Product surfaces feel like a *page*; the landing feels like a journal cover.

**Touchstone (cross-domain, not a competitor):** Nature Genetics / ft.com
editorial — serif authority, rust accent, dense-but-readable hierarchy.

### 2.1 Color — strategy: editorial, committed brand accent (target OKLCH; validate in Phase 0)

Neutrals are warm-tinted (hue ~40-75), never Tailwind slate, never pure #000/#fff.

```
/* Product surfaces (light) */
--bg        oklch(99.3% 0.004 75)   /* warm near-white "page" */
--bg-soft   oklch(97.5% 0.008 70)
--bg-soft2  oklch(95.5% 0.010 65)
--bg-tint   oklch(96.5% 0.014 165)  /* faint teal wash, functional only (<=4%) */
--ink       oklch(18% 0.020 40)     /* warm near-black (not blue, not #000) */
--ink-2     oklch(32% 0.035 40)
--ink-3     oklch(46% 0.030 45)
--ink-4     oklch(62% 0.024 50)
--ink-5     oklch(78% 0.014 55)
--line      oklch(90% 0.010 60)     /* hairline, must stay visible on warm white */
--line-2    oklch(83% 0.012 60)

/* Brand — TEAL (kept, hue ~163). Existing logo/domain color, now OKLCH-coherent.
   teal == brand AND Benign; disambiguate by role + lightness (see frozen note). */
--brand        oklch(59% 0.118 163)  /* = --teal; the brand anchor */
--brand-deep   oklch(49% 0.110 163)  /* pressed / = --teal-deep */
--brand-bright oklch(74% 0.130 165)  /* on-dark expression (landing) */
--brand-muted  oklch(59% 0.060 163)  /* desaturated borders/tints */
--brand-tint   oklch(96% 0.020 165)  /* near-white wash */

/* Landing dark editorial ground (warm brown-black, hue ~30-35) */
--d-bg     oklch(16% 0.025 35)
--d-bg-2   oklch(20% 0.030 35)
--d-ink    oklch(95% 0.010 75)      /* pale cream type */
--d-ink-2  oklch(80% 0.012 70)
--d-line   oklch(40% 0.020 40)
--d-card   /* cream at low alpha, e.g. color-mix or rgba(var) */
```

**Frozen, NOT recolored (clinical language — import as separate tokens):**
- Classification tiers (Pathogenic → Benign): keep DESIGN.md hex EXACTLY.
- Predictor score scales (SpliceAI/REVEL/AlphaMissense): keep.
- Sequence palette `--base-A/T/C/G` + amino-acid `--aa-*`: keep (muted, no rainbow).
- `--teal #1D9E75`: this IS the brand anchor (`--brand`) AND the Benign/functional
  semantic color. Disambiguate by role + lightness: brand-teal on CTAs / active nav
  / focus ring; benign-teal on badges / locus dots / verdicts. Never place an
  ambiguous teal CTA directly adjacent to a teal Benign signal.
- `--warn #BA7517` / `--err #B82B2B`: treat as FROZEN by default (embedded in the
  predictor/classification language). The audit's "equalize warn/err lightness"
  idea is an OPTIONAL, separately-reviewed micro-change, not assumed here.

**Focus ring** moves to the brand accent per invariant: `0 0 0 3px rgba(brand,.14)`.

### 2.2 Typography

```
--display : "Newsreader", Georgia, serif    /* editorial serif, DISPLAY-ONLY >=24px */
--body    : "Inter", system-ui, sans-serif  /* swap from Plus Jakarta for neutrality */
--mono    : "JetBrains Mono", ui-monospace, monospace   /* KEPT — HGVS identity */
```

- **Newsreader** is the recommended free default (Google, built for on-screen
  editorial, has italic + wide weights). Premium upgrade path: Canela / Tiempos
  (needs a license — see Open Decisions). The serif is **display-only**; if it
  leaks into 14-15px body/tables it degrades legibility — this is the #1 taste-risk
  of the direction and is a hard rule.
- Body: **Inter** recommended (cleaner against a characterful serif); fallback is
  keeping Plus Jakarta Sans (lower churn). Decide in Phase 0.
- Scale (>=1.25 steps; serif provides the leaps; sans/mono carry density):

| Role | Size | Face / weight |
| ---- | ---- | ------------- |
| Hero display (landing) | clamp 44–72px | serif 300–400 |
| Display L | 36–44px | serif 400 |
| Gene name / report running head | 28px | serif 400 |
| Section title | 18px | sans 600 |
| Body | 15px / 1.6 | sans 400–500 |
| Dense / secondary | 13px | sans 500 |
| Label / metadata | 11px uppercase, tracked | mono 500 |
| HGVS / scores / coords | per context | mono 500 |

No weight > 700 anywhere on product; brand surfaces may use serif 400 large (the
serif reads authoritative at low weight, so we rarely need bold).

### 2.3 Signature element — the ruled journal column

- Report main column carries a **0.5px full-height left rule** (`--line`); section
  numbers sit in the **margin gutter** outside the column, as in a journal article.
- Gene name renders as the article **running head** at the top of the column.
- Replaces SaaS section affordances: the teal numbered circle becomes a margin
  mono numeral against the rule. Kills nothing load-bearing; removes the dashboard
  read.
- Landing: the column rule **draws on scroll** (scroll-linked, honest, reduced-
  motion-safe). Workbench: the rule becomes the viewer's shared vertical axis/pin.

### 2.4 Motion

- Deliberate and legible: 240ms default (`--dur-2`/`--dur-3`), ease-out exponential
  only, no bounce/elastic, never animate layout props (transform/opacity/shadow/
  color only). Keep the global `prefers-reduced-motion` guard.
- One signature: the column-rule scroll-draw. No decorative loops; audit the
  existing `ls-drift`/`ls-shimmer` landing animations against "real state only"
  (likely retire or repurpose).

### 2.5 Register expression

- **Landing (brand, loud):** dark warm-brown ground, pale cream serif at large
  scale, teal accent, the search shell as "submit a query to the literature."
  Drop the dark-emerald tier and `hero-tree.webp`; the type + column do the drama.
- **Report/Workbench/Account (product, precise):** warm-white page, ruled column,
  serif only on the gene name / display headers, teal only on the primary CTA and
  active nav state, everything else ink-on-warm-white. Same world, turned to
  precision.

### 2.6 Color-safety notes (teal kept)

The rust↔pathogenic-red collision that the original rust accent carried is GONE:
teal (hue ~163) is far from err-red (~25), warn-amber (~63), and any classification
hue except Benign. Remaining items, milder:
1. **Teal is both brand and Benign.** Disambiguate by role + lightness: brand-teal
   on CTAs / active nav / focus ring; benign-teal on badges / locus dots / verdicts.
   Never adjacent-ambiguous. (Low stakes: Benign is the reassuring reading.)
2. **Phase 0 gate (warm-white):** the surfaces move from pure white to warm paper,
   which changes contrast ratios. Re-tune `--line` (hairlines must stay visible) and
   the ink scale, then verify WCAG AA on the new neutrals, plus a quick CVD sanity
   check on the frozen classification palette against the new background. Do not
   start surface work until this passes.

---

## 3. Invariants handed to every surface team (non-negotiable)

1. Semantic classification colors immutable; import as frozen tokens. (Fix the
   Likely-Benign-blue bug — see §4.)
2. OKLCH migration lives in the token layer only; components consume ~10 brand +
   semantic + frozen tokens. No inline hex.
3. `--teal` is both the brand anchor and the Benign/functional color; disambiguate
   by role + lightness (brand on CTA/nav/focus, benign on badges/dots), never
   adjacent-ambiguous. Brand color unchanged, so logo/domain equity is preserved.
4. Hairlines are infrastructure: 0.5px, never replaced by space or full borders;
   re-tune `--line` so it stays visible on warm-white.
5. The search shell is the product's interactive brand signature; focus glow uses
   the brand accent.
6. Motion stays honest (real state only); reduced-motion guard always shipped.
7. Weight cap 700 on product; brand may use serif at large sizes (low weight).
8. Nav = 60px, ContextStrip = 48px (fix the current 56px nav drift — load-bearing
   for Workbench layout math).
9. Source link on every data point; DNA notation primary / protein secondary;
   density preserved. No em dashes in copy.

---

## 4. Fix first, direction-independent — the live bug

`components/ui/ClassificationBadge.tsx` renders **Likely Benign in blue**
(`#eff6ff / #1e40af / #bfdbfe / #3b82f6`) and Pathogenic with drifted reds. Restore
DESIGN.md spec exactly (Likely Benign green `#EAF3DE / #3B6D11 / #C0DD97 / #639922`;
Pathogenic `#FCEBEB / #791F1F / #F7C1C1 / #E24B4A`). This corrupts clinical meaning
and ships today — do it before any redesign work, verify on a real report.

---

## 5. Execution architecture (impeccable + agent fan-out)

Coordination per `agent_handoff/README.md` (parallel-mode lanes, own-section-only,
no-delete/append+archive). All work is Claude's frontend lane; do not touch Codex's
dirty `PROGRESS.md`/`RISKS.md`/`plans/v2-backend.md`/its CURRENT.md section.

Each impeccable command maps to a step: `extract` (tokens/primitives), `typeset`
(type), `colorize` (color), `layout` (spacing/alignment), `animate` (motion),
`clarify` (copy), `onboard` (empty/first-run), `harden` (errors/edge cases),
`adapt` (responsive), `audit`+`critique`+`polish` (gates).

**Phase 0 — Foundation (SERIAL, the coherence gate). 1 developer agent + me.**
- §4 bug fix. OKLCH token migration in `globals.css` (`extract`). New type stack +
  scale (`typeset`). Re-tune hairlines/elevation/motion tokens. Build the ruled-
  column primitive + updated `Card`/badge/nav primitives. CVD validation gate
  (§2.6). Nav-height fix.
- Gate: `quality-reviewer` + impeccable `audit`; browser-verify a sample report +
  landing. **No surface work starts until this is merged and green.**

**Phase 1 — Surface redesigns (PARALLEL once Phase 0 locks). 3 agents.**
- Agent A: **Landing + legal** (drop emerald tier + hero image; serif hero; section
  rhythm; replace MetricBelt hero-metric template with a live report specimen;
  HowItWorks asymmetric editorial; legal pages on light surface + real nav).
- Agent B: **Report** (ruled column; ink/serif header; kill side-stripe bans in
  `.pred-disagree` + PubMed snippets; InSilico grid → comparison strip; section
  marks; elevation on cards; statement-style publications callout).
- Agent C: **Account/Checkout/Auth** (auth → route not popover; pricing cards as
  evidence objects not SaaS tiers; checkout manifest not gradient panel; receipt as
  document; plan-status header; trust band; fix dead promo button; error/empty/
  loading/success states; a11y focus management).
- Each agent: implement → impeccable `polish`/`audit` → `quality-reviewer` →
  browser-verify. Agents stay in their file sets; shared changes go back to
  Phase-0 token layer, not duplicated.

**Phase 2 — Workbench (GATED on pass-2 migration). Heaviest.**
- Close migration gaps first (viewer tracks + click-to-edit popover; the 4 tool
  panels; AskEamos pill; export panel-not-modal). Then redesign: spine signature,
  click-to-edit as the differentiator moment, conservation contour (not bar chart),
  minimap as ClinVar-density (not Benchling bar), ContextStrip classification badge.
- Same gate chain. Verify against the working Vite viewer as reference.

**Phase 3 — Cross-cutting close-out.**
- `adapt` (responsive breakpoints), `harden` (edge/error/i18n), `clarify` (copy
  sweep, no em dashes), full a11y + keyboard + reduced-motion pass, perf check
  (font loading, animation), integration checkpoint, `doc-sync` DESIGN.md +
  PRODUCT.md to the shipped reality.

---

## 6. Per-surface scope (from the audits — concrete backlog)

### Foundation / design system
OKLCH tokens; type stack+scale; hairline re-tune for warm-white; elevation tokens
re-based on new ink; consolidate the 3 color registers (kill the legacy
backward-compat bleed where unused by `/runs`); unify nav (60px; Workbench gets a
nav variant); fix `ClassificationBadge`; remove off-token motion (`CarouselDots`,
pricing hover raw shadow, etc.); Card radius 16→14.

### Landing + legal
Drop `--d-*`/`--hero-*` emerald + `hero-tree.webp`; serif hero with weight/scale
contrast (not color-tint emphasis); search-as-hero; alternating light/dark section
rhythm; replace MetricBelt (hero-metric ban) with live report specimen; HowItWorks
+ FeaturesGrid de-templated (asymmetric/editorial, not identical card grids);
mobile-nav blur cleanup; legal pages → light surface + composed nav + breadcrumb;
retire/repurpose `ls-drift`/`ls-shimmer`.

### Report
Ruled journal column + margin section numbers; serif gene name; **remove side-stripe
bans** (`.pred-disagree` line 356, PubMed snippet stripes ×many); InSilico 4-card
grid → analytical comparison strip; statement-style PublicationsCallout (kill the
mini hero-metric); apply `--elev-1` to cards + `--elev-2` interactive hover;
AskEamos gradient header → flat tint; on-token motion; preserve 3-layer disclosure,
source links, frozen colors, mono.

### Workbench (Phase 2, gated)
Finish pass-2 (viewer skeleton → real tracks + click-to-edit; tool panels; pill;
export non-modal); spine signature; conservation contour; ClinVar-density minimap;
ContextStrip classification badge; remove 2px side-stripes (`side-info`/`help-note`/
etc.); raw box-shadow → `--elev-*`; hardcoded durations → tokens; `.sv-splice-tag`
700→600; remove dev debug `<p>` + hardcoded "AI note" prose; keep muted base palette
+ click-to-edit differentiator + viewer-as-spine.

### Account / Checkout / Auth
Auth as `/auth` route (split page) + keep popover for in-product quick sign-in;
inline validation + human error copy (map Supabase errors); directed empty states;
honest loading (`aria-busy` + indicator); pricing cards as evidence objects (drop
"Most popular" + translateY bloom → elev lift); checkout order manifest (drop
gradient) + trust band (Stripe/ABN/refund) + GST clarity; receipt as document
(drop generic checkmark); `/account` plan-status header + manage-subscription;
fix dead promo "Apply" button; tokenize `#04140e`/`#fca5a5`/raw black shadows;
radii >14 → 14; focus management on popover open/close.

---

## 7. Sequencing & milestones

| # | Milestone | Verify |
| - | --------- | ------ |
| M0 | §4 badge fix | real report shows green Likely Benign |
| M1 | Phase 0 foundation + CVD gate | sample report + landing render on new tokens/type; CVD sim passes; reviewer green |
| M2 | Landing+legal (Agent A) | browser-verify landing + privacy/terms; no bans; reviewer green |
| M3 | Report (Agent B) | browser-verify report; bans gone; disclosure/source-links intact; reviewer green |
| M4 | Account/Checkout/Auth (Agent C) | flows work; states honest; trust band; reviewer green |
| M5 | Workbench pass-2 + redesign | viewer + tools real vs Vite ref; bans gone; reviewer green |
| M6 | Cross-cutting (adapt/harden/clarify/a11y/perf) + doc-sync | responsive + keyboard + reduced-motion verified; DESIGN/PRODUCT synced |

M1 blocks M2–M5. M2/M3/M4 run in parallel. M5 after its migration. Commit each
milestone with explicit Claude-lane pathspecs; never sweep Codex's dirty files.

---

## 8. Risks

1. **Serif leaking to body** — degrades clinical legibility/density. Hard rule:
   display-only >=24px. (Now the top risk.)
2. **Workbench scope** — pass-2 migration is weeks, not a polish; do not "redesign
   a bare frame." Gated as Phase 2.
3. **Warm-white contrast** — moving off pure white re-tunes ratios; `--line` must
   stay visible and text WCAG AA on warm paper (Phase 0 gate, §2.6).
4. **Token migration regressions** — `/runs` legacy + backward-compat tokens must
   stay intact; product surfaces must not import legacy tokens.
5. **Font licensing** — Newsreader (free) default avoids blocking; Canela/Tiempos
   need purchase (Open Decision).
6. **Teal brand/benign overlap** — mild; mitigated by role + lightness (§2.6). Not
   a safety risk (benign is the reassuring reading).

## 9. Open decisions (confirm in Phase 0)

- Display serif: Newsreader (free, default) vs Canela/Tiempos (paid). 
- Body face: Inter (recommended) vs keep Plus Jakarta Sans.
- Logo: stays teal (no refresh needed). Optional only: improve the spark mark's
  legibility at 18px nav scale (audit flagged it reads too thin).
- Whether to retire vs repurpose the Lifestream animation assets.
