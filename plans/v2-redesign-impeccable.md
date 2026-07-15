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

2026-06-15 correction: `app/frontend` is now a stale frozen Vite reference for
report work. Active `/report` development is in `app/web`. Do not copy
`app/frontend` mock AlphaMissense/InSilicoGrid thresholds into live report code;
the live Section 2 path is `app/web/components/report/CalibratedInSilicoTable.tsx`
fed by `report_profile.computational_deep_dive`.

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
dirty `PROGRESS.md`/`docs/operations/risks-and-guardrails.md`/
`plans/v2-backend.md`/its CURRENT.md section.

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

---

## 10. Competitor steals — Varsome (added 2026-05-27, refined post-Codex)

> Source: full analysis in `docs/competitive/varsome.md`. This section maps
> the prioritised take-aways to existing milestones, calls out new ones,
> records anti-patterns we explicitly reject, and bakes in Codex's backend
> sizing + sequencing input (2026-05-27 cross-agent thread). Steven's prior
> likes (Cite chip, coloured ClinVar bars + stars, variant-vs-gene pub
> counts, publication modal with backdrop blur + PubMed/DOI/PDF, Region
> Browser depth) are all confirmed and slotted below.
>
> **Key resolutions (2026-05-27):**
> - **M7 = matrix-as-overture** above the ruled column (Reading Room kept).
> - **Cite chip** ships with software DOI placeholder + Steven's real ORCID
>   (`0009-0000-9745-8226`) + Scholar + PubMed; Zenodo DOI minted later.
> - **AlphaMissense** stays hidden in public display (2026-05-19 decision),
>   but **internal calibration policy + fixtures stay fresh** for M8;
>   conditional re-enable trigger: if SpliceAI / REVEL / CADD / Primate3D end
>   up Pro-gated, AM becomes the free-tier scorer.
> - **M10 split** into M10a (weeks, additive on EP-VLEx) and M10b (quarter,
>   net-new pipeline).
> - **M11 contract sketch is a prereq, not sequential** — section-fetch
>   shape must land before M7/M8/M9 FE harden, otherwise we build against the
>   monolith and rework hydration boundaries.

### 10.1 Goes inside an existing milestone (no new milestone)

| Steal | Milestone | Slot |
| ---- | --------- | ---- |
| **Bottom-left global Feedback + Cite chip** | M2 (Landing/legal) + cross-cutting | Add the chip primitive in Phase 0 so it ships on every surface from M2 onward. Cite modal contents (paper / DOI / BibTeX / RIS) decided when we have a draft Eamos paper or Zenodo DOI. |
| **Coloured pathogenicity left-edge accent on cards** | M3 (Report) | Component-level: `Card` gains an optional verdict prop that drives a 3px `border-left` in the frozen ramp. Tokens already exist. |
| **Inline ClinVar review-star glyph next to verdict** | M3 (Report) | Render in ClassificationBadge / call card header — 10–12px stars, tabular numerals nearby. |
| **Horizontal stacked-count bar with inline numerals** | M3 (Report) | New `StackedCountBar` primitive for ClinVar submitter splits + in-silico ensemble counts. Reuses frozen classification ramp; white numerals inside bar segments. |
| **ACMG criteria pills coloured by met/not-met** | M3 (Report) | Upgrade `AcmgCriteriaFold` chips: grey for not-met, frozen-ramp colour for met. Eliminates legend. |
| **Sticky variant ribbon with action cluster** | M3 (Report) | Pin HGVS + Copy / Share / Export / Save / Cite below the 60px nav. Mirrors the Workbench ContextStrip pattern. |
| **Premium-card pattern that shows what's behind the wall** (NOT the warning modal) | M4 (Account/Checkout/Auth) | When a paid surface lands: ungated row labels visible, scores/values replaced with Premium badge + one-line "what it adds." Explicit anti-pattern: do not ship the "results are incomplete unless you pay" warning modal. |
| **Publication-detail modal: PubMed + DOI + PDF + citation count + abstract + backdrop blur** | M3 (Report) | Upgrade existing publications list: click → modal with focus-trap, ESC, `aria-modal`, and a **shareable URL param** (`?pub=PMID:12345`) — fixing the bug Varsome shipped. |
| **Variant-vs-gene publication count toggle** | M3 (Report) | One boolean in the publications section header. Backend already returns `PublicationLiterature.total_count` for variant; needs gene-scoped counterpart (see §10.4 cross-agent ask). |

### 10.2 New milestones (sizing confirmed by Codex 2026-05-27)

| # | Description | FE | BE | Effort |
| - | ----------- | -- | -- | ------ |
| **M7** | **Card-matrix report header** above the ruled column (matrix-as-overture). 10–12 tiles, not Varsome's 24. Each tile = section preview (title + key value + mini-vis) + nav anchor. URL fragments / route segments so sections are linkable + back-button-friendly (fixes Varsome's client-only-state bug). Mobile: horizontal-scroll band, not stacked. **Tiles use cheap summary fields from the initial payload** (per Codex); detail panels lazy-load via the M11 section-fetch contract. | Lead | None — use current report fields unless a tile genuinely needs a new summary scalar | 1–2 wk |
| **M8** | **Calibrated in-silico verdict table.** Replace `InSilicoGrid` with composite verdict bar + per-engine table: **Engine · Calibrated label · Raw score · Version**. **Null-calibration UX (per Codex):** render the engine row, but the calibrated cell shows neutral *"No published calibration / Not calibrated"* with raw score + version still visible. Composite verdict bar aggregates only engines with an approved calibration policy. Frozen ramp colours on calibrated labels. AlphaMissense stays in internal calibration policy/fixtures but public display stays hidden until re-enable trigger fires. | Render-only | Additive: `calibrated_label`, `calibration_bucket`, `calibration_method`, `calibration_version` on existing predictor rows. Calibration policy is **backend-owned** (Pejaver/ClinGen SVI where valid, explicit null where not) | 2 wk |
| **M9** | **ClinGen VCEP narrative + criteria chips.** New report section: `ExpertPanel` attribution (e.g. TP53 VCEP), criteria-met / not-met chips, inheritance, MONDO link, "Evidence submitted by expert" narrative, source URL + version + provenance. **v1 scope (per Codex):** public **ClinGen Evidence Repository API / JSON-LD only** + public CSpec data if needed; **no SVI-gated / private feed.** | Render | Richer product contract on existing `ClingenTool` + `ClinicalConsensusBuilder`. **Cache key:** variant/provider identity oriented (CAID / ClinVar Variation ID / normalized HGVS + gene). **Cache record:** source URL, fetched_at, source_version/API version, raw JSON-LD, normalized summary, stale-on-failure behaviour. Fits **provider-backed source-cache** (not a big local asset; separate from small local ClinGen gene-validity tables) | 2–3 wk |
| **M10a** | **Gene-scoped publication count toggle** (variant-vs-gene). One boolean in the publications section header. | Render | Additive on EP-VLEx primitives (aliases, PMID dedupe, source tags, snippets/status, timeline already exist) — gene-scoped count is a small additive field | ~1 wk |
| **M10b** | **Publication index v2** *(net-new pipeline)*. PMC / Europe PMC ingestion; LLM entity extraction for tag-chip generation; "Linked by:" provenance (GDC / cBioPortal / community / Varsome AI–equivalent); citation counts; tag chips. Replaces Varsome's multi-year mining moat with one engineer-quarter to credible v1. | Render | Net-new pipeline; separate from EP-VLEx primitives | ~1 quarter |
| **M11** | **Mobile-first responsive sweep + section-fetch contract.** Horizontal-scroll for any multi-card surface. **Contract sketch is a prereq** for M7 / M8 / M9 FE harden (per Codex — building against the monolith and retrofitting hydration is the rework path). v1 lazy-fetch sections (per Codex): **publications, ClinGen VCEP narrative/criteria, computational expanded**. Publications already has `/lookup/publications`; M10a can extend it. ClinGen + computational can use a shared `lookup/sections` batch endpoint or dedicated endpoints. **Trials/therapies, disease mechanism, population detail wait for perf data.** M7 tiles do NOT make N tile calls — cheap summary fields in initial payload. | Lead | Section-fetch endpoints + `include=` selection on `/lookup` | 2 wk (sketch ~few days, full ship after M7/M8/M9 land) |
| **M12** | **Events emission primitive + (later) cleaner landing activity strip.** Deferred until organic volume justifies a user-facing feed. v1 (if pulled forward): **backend-only, privacy-safe event emission** with no-op/log sink — `lookup_completed`, `section_expanded`, `publication_opened`, `share_clicked`, `cite_clicked`. **Hard privacy guardrails (per Codex):** no PHI, no raw free-text query content, no public lab-affiliation feed, no Supabase migration until M12 is actually pulled forward. FE consumes later. | Lead (deferred) | BE-only primitive (deferred) | 1 wk events primitive; FE strip later |

### 10.3 Long-term / discuss

- **Proprietary ACMG classification engine** — long-term moat.
  `AcmgCriteriaFold` scaffolding is already there; building the rules engine
  is a strategic multi-quarter project, deferred until after M5 Workbench
  redesign lands.
- **Submit-to-ClinVar funnel** — future-roadmap only (per Codex). Needs
  classification governance, curator workflow, audit trail, source/licensing
  posture settled first.
- **SpliceVault top-4 mis-splice events** — needs SpliceVault license / data
  agreement; Codex backend lane.
- **3D Protein Viewer with variant overlay** (NGL Viewer or Mol\* + SwissModel
  / AlphaFold). High clinical signal; multi-MB WebGL bundle so must be lazy-
  loaded on expand. Slot after M5 (Workbench has the only existing viewer
  chassis worth extending).
- **Region Browser multi-track parity** (DNA letters / conservation histogram
  / amino-acid strip / UniProt regions / pathogenicity lane). Workbench
  viewer already has the spine.

### 10.4 Backend asks (cross-agent)

Will be opened in `agent_handoff/CURRENT.md` Cross-Agent Requests as
Claude→Codex CARs in this order:

1. **M11 minimal section-fetch contract sketch** *(opened at end of this
   session — prereq for M7/M8/M9 FE harden).*
2. **M8 calibrated-predictor fields** — `calibrated_label`,
   `calibration_bucket`, `calibration_method`, `calibration_version`;
   keep AM in internal calibration policy/fixtures.
3. **M9 ClinGen VCEP contract** — Evidence Repo public API/JSON-LD pull
   into a provider-backed source-cache slot, normalized summary + raw JSON-LD
   in the cache record, cache key on CAID / ClinVar VID / normalized HGVS +
   gene.
4. **M10a gene-scoped publication count** — additive field on EP-VLEx
   primitives.

CARs #2–4 open **when the relevant FE slice is about to start**, not all at
once; protocol stays per `agent_handoff/README.md`.

### 10.5 Anti-patterns Eamos explicitly rejects

1. Full-screen spinner with no skeleton.
2. "This website may not work correctly with your screen size" — mobile-first
   from the start.
3. "Viewed N times" / "Connect with past and future viewers" — wrong tone for
   a clinical decision tool.
4. Free-text user comments until we have a moderation budget.
5. Real-time activity strip until activity volume justifies it (cold start is
   brutal — Varsome's looks messy with full activity).
6. "Warning: results are incomplete unless you pay" upsell modal — erodes
   trust at decision time.
7. reCAPTCHA on shareable variant URLs.
8. Greying premium-gated and no-data tiles identically.
9. Serif on body / 14–15px content (already a §2.2 hard rule; Varsome
   sidesteps this by using sans everywhere, which we beat with Reading Room).

### 10.6 Sequencing — refined post-Codex

M0–M6 keep their current order and gates. The new milestones sequence as:

```
M3 (Report redesign)
   │
   ▼
M11 contract sketch     ← Codex defines section-fetch shape FIRST (~few days)
   │
   ├──► M7   (card matrix; cheap summary fields; FE-only)        ~1–2 wk
   ├──► M8   (calibrated in-silico; lazy detail panel)           ~2 wk
   ├──► M9   (ClinGen VCEP; lazy detail panel; source-cache)     ~2–3 wk
   └──► M10a (gene-scoped pub count; extends /lookup/publications) ~1 wk
              │
              ▼
M11 full ship (mobile + lazy section endpoints applied broadly)  ~2 wk
              │
              ▼
M10b (~1 quarter, net-new pipeline)
M12 (deferred — events primitive when pulled forward)
```

Component-level Tier-1 upgrades (Cite chip, left-edge accent, ClinVar stars
inline, stacked-count bar, ACMG met/not-met pills, publication modal with
backdrop blur) land **inside M2/M3** without scope creep — they're upgrades
on primitives Phase 0 already establishes. The Cite chip ships as the
bottom-left global chip in M2/M3 with the format in §10.7.

M5 Workbench redesign runs as a separate lane (already unblocked from
`fe9e3b4`). M10b and M12 are decoupled, scheduled when capacity allows.

### 10.7 Cite chip — format (ships in M2/M3)

Bottom-left global chip, two buttons (Feedback + Cite). Click Cite opens a
modal with:

```
How to cite Eamos
─────────────────
Software   Eamos team (2026). Eamos: clinical-grade variant interpretation.
           https://eamos.com.au · DOI: 10.5281/zenodo.XXXXX  (pending)

Author     Steven S. Eamegdool
           ORCID:    https://orcid.org/0009-0000-9745-8226
           Scholar:  https://scholar.google.com/citations?user=oNJ9_8YAAAAJ
           PubMed:   https://pubmed.ncbi.nlm.nih.gov/?term=Steven+S+Eamegdool

This report  {variant_display}. Accessed {date}. Report v{report_version}.

[Copy citation] [Copy BibTeX] [Copy RIS]
```

Ships at M2/M3 with the Zenodo DOI as `(pending)`; upgrade in-place when DOI
is minted. Modal closes on ESC, has focus-trap, has `aria-modal`, and is
shareable via `?cite=1` URL param (cf. M11 mobile responsiveness — must work
on small screens).

### 10.8 AlphaMissense — conditional re-enable trigger

Default: AlphaMissense stays hidden in public display per 2026-05-19
decision. Codex confirmed (2026-05-27): **AM stays in internal calibration
policy + fixtures for M8** — calibration data fresh, only public payload /
display hidden.

**Re-enable trigger:** if SpliceAI, REVEL, CADD, **and** Primate3D end up
Pro-gated in the free tier (i.e., the free-tier in-silico table would
otherwise be empty or sparse), AlphaMissense becomes the free-tier scorer
and re-enables in public display.

**Re-enable mechanic:** FE display-filter flip + BE fixture revert,
coordinated. No code changes required pre-trigger. Memory:
[[project_alphamissense_plan]].

### 10.9 Sequencing breakdown — persisted via /planner (2026-05-27 23:55 +1000)

> Source of truth for the executable sequence. Ran the `/planner` skill on the
> resolved post-Varsome spec (orchestrator + architect + 11 parallel
> quality-reviewer verifiers; 2 fix-iterations to PASS). Output: **21 decisions
> · 10 milestones · 5 waves · 30 code-intents · 1 dataflow diagram**. Ephemeral
> `plan.json` lives in tmp STATE_DIR; this section is the durable summary.
>
> **Mid-session correction:** Codex had already delivered the M11 minimal
> section-fetch contract sketch at 21:31 +1000 (files:
> `app/backend/app/api/routes/lookup.py`, `app/backend/app/schemas/lookup.py`,
> `app/backend/app/services/lookup_sections.py`,
> `app/backend/tests/test_lookup_section_fetch_contract.py` — covers M7 tile
> summary endpoint + section endpoint for `publications` +
> `computational_deep_dive` + partial `clingen_vcep` + per-section freshness
> fields + focused contract tests). Claude→Codex CAR #1 (22:55) is therefore
> already closed. **Wave 2 collapses to a Claude-side TS mirror only; Wave 3
> is immediately available.**

#### Waves

| Wave | Milestone | Lane | Effort | Blocking |
| ---- | --------- | ---- | ------ | -------- |
| 1 (in-flight) | M-001 / M3 Report redesign + 8 Tier-1 component upgrades inside M3 | FE-only (Claude) | active | none |
| 2 (collapsed) | M-002 / M11 minimal section-fetch contract sketch | BE done; Claude TS mirror only | hours-days for the mirror | Codex 21:31 release shipped; CAR #1 closed |
| 3 (parallel) | M-003 / M7 card-matrix overture | FE-only (Claude) | ~1–2 wk | M-002 mirror in `app/web/lib/backend.ts` |
| 3 (parallel) | M-004 / M8 calibrated in-silico table | FE + CAR #2 (calibrated_* fields) | **SHIPPED 2026-05-28 02:29 +1000 (`6049df1`)** — CAR #2 closed by Codex at 02:06; FE built `CalibratedInSilicoTable` + `CompositeVerdictBar`, mounted in `ReportClient` §2, ripped `InSilicoGrid` (DL-021 ship-then-rip). RPE65 validates: 1 LP + 2 VUS visible / 3 of 5 engines calibrated. AM still filtered at render. ⚠ CORRECTION 2026-06-06: component SHIPPED but renders EMPTY on a LIVE backend — `computational_deep_dive` is eager-excluded (`app/backend/app/api/routes/lookup.py:26-34`) and `CalibratedInSilicoTable`/`CompositeVerdictBar` are mounted EAGERLY (`ReportClient.tsx:737-738`), NOT via `<LazySection>` like publications, so it only populates on the offline RPE65 fixture. FE live-wiring (lazy-fetch `computational_deep_dive` from `/lookup/sections`) is OPEN. | M-002 mirror + CAR #2 |
| 3 (parallel) | M-005 / M9 ClinGen VCEP narrative + criteria chips | FE + CAR #3 (ClinGen Evidence Repo source-cache) | 🟡 PARTIAL (corrected 2026-06-06): `ExpertPanelSection` BUILT but renders null on a live backend (`expert_panel` eager-excluded `lookup.py:26-34` + mounted eagerly `ReportClient.tsx:775`, not `<LazySection>`); ClinGen Evidence-Repo source-cache NOT integrated; type drift local `ExpertPanelData` vs backend `ExpertPanelSection`. | M-002 mirror + CAR #3 |
| 3 (parallel) | M-006 / M10a gene-scoped publication count toggle | FE + CAR #4 (gene-scoped pub count field) | ~1 wk | M-002 mirror + CAR #4 |
| 4 | M-007 / M11 full ship — mobile-first sweep + LazySection broadly | FE-only (Claude) | ~2 wk | Wave 3 lands |
| 5 (deferred) | M-008 / M10b publication index v2 (PMC + LLM tags + provenance) | BE (~quarter); FE render-only later | ~1 quarter Codex | capacity / Steven scoping |
| 5 (deferred) | M-009 / M12 events emission primitive (BE-only) | BE (Codex); FE consumption later | ~1 wk Codex (when pulled forward) | organic volume justifying landing strip |
| 5 (deferred) | M-010 / AlphaMissense re-enable trigger monitoring | no-code (`docs/operations/risks-and-guardrails.md` watch entry) | minutes | trigger condition fires (no auto-flip — Steven approval required) |

#### Decision → milestone map (selected)

- **DL-001** (5-wave staged-parallel sequencing) and **DL-002** (per-slice
  CAR opening, not batched) shape every wave boundary and CAR cadence.
- **DL-004 + DL-005** (M7 = 10–12 tiles, cheap summary fields, URL
  fragments) drive `MatrixOverture` / `MatrixTile` (`CI-M-003-001/002/003`).
- **DL-006 + DL-007** (null-calibration neutral cell; composite verdict bar
  aggregates only approved-cal engines) drive M-004 `CalibratedInSilicoTable`
  + `CompositeVerdictBar` (`CI-M-004-001/002`).
- **DL-008** (AM internal-only display hidden + conditional re-enable trigger)
  drives M-010 RISKS watch entry (`CI-M-010-001`).
- **DL-009 + DL-010** (M9 v1 = public ClinGen Evidence Repository API/JSON-LD
  only; provider-backed source-cache keyed on CAID / ClinVar VID / normalized
  HGVS+gene; all 5 cache-record fields surfaced in provenance footer) drive
  M-005 `ExpertPanelSection` (`CI-M-005-001`).
- **DL-011** (M10 split into M10a additive vs M10b net-new pipeline) drives
  M-006 (Wave 3) vs M-008 (Wave 5).
- **DL-013** (M11 v1 lazy sections = publications + ClinGen + computational
  expanded; trials/disease/population stay eager) drives M-007 (`CI-M-007-001`).
- **DL-014** (M12 BE-only deferred + hard privacy guardrails — NO PHI, NO raw
  query text, NO public lab-affiliation, NO Supabase migration until pulled
  forward) drives M-009 placeholder.
- **DL-015** (Cite chip ships in M3 with real ORCID `0009-0000-9745-8226` +
  Scholar + PubMed; Zenodo DOI as `(pending)` upgrade-in-place) drives
  `CI-M-001-009`.
- **DL-016** (PublicationModal with `?pub=PMID:N` URL param + focus-trap +
  ESC + aria-modal + backdrop blur) drives `CI-M-001-012`.
- **DL-017** (premium-gated tiles use distinct visual treatment from no-data
  tiles — NEVER identical grey) drives `MatrixTile` rendering branches
  (`CI-M-003-002`).
- **DL-018** (M5 Workbench redesign stays decoupled separate lane) keeps M5
  out of this critical path.
- **DL-019** (every commit uses explicit `git add -- <paths>`, NEVER
  `git add -A` / `git add .`, to avoid sweeping Codex's uncommitted
  `app/backend/**` + `PROGRESS.md` + `plans/v2-backend.md` work into a
  Claude commit) is repeated as a commit-guard in every code-touching
  code-intent.
- **DL-021** (M3 InSilicoGrid ship-then-rip: M3 ships intermediate
  `StackedCountBar` ensemble strip, M-004/M8 fully replaces with
  `CalibratedInSilicoTable` once contract + calibration fields land) is
  the deliberate throwaway in `CI-M-001-004`.

#### CAR opening sequence (Cross-Agent Requests in `agent_handoff/CURRENT.md`)

| CAR | Status | Trigger | Scope |
| --- | ------ | ------- | ----- |
| **#1** Claude→Codex M11 minimal section-fetch contract sketch | **[DONE]** — closed by Codex's prior 21:31 +1000 release (cross-talk: my CAR opened at 22:55 after Codex shipped at 21:31) | open at Wave 2 start | summary endpoint + section endpoint for publications / computational_deep_dive / clingen_vcep + per-section freshness fields |
| **#2** Claude→Codex M8 calibrated-predictor fields | **[DONE]** opened 2026-05-28 01:31, closed by Codex 02:06, FE shipped 02:29 (`6049df1`) | M-004 / M8 FE slice start | additive `calibrated_label`, `calibration_bucket` (typed as `RampVerdict` 5-tier), `calibration_method`, `calibration_version` on each `ComputationalPredictorRow` in `ReportPayload.report_profile.computational_deep_dive.predictors`; calibration policy backend-owned (Pejaver/ClinGen SVI where valid, explicit null where not); AM stays in internal calibration policy/fixtures, public display hidden; full ask in `agent_handoff/CURRENT.md` Cross-Agent Requests |
| **#3** Claude→Codex M9 ClinGen VCEP source-cache | **OPEN** — opened 2026-05-28 03:18 +1000 (M-005 FE slice begins; full ask in `agent_handoff/CURRENT.md` Cross-Agent Requests) | M-005 / M9 FE slice start | public ClinGen Evidence Repository API/JSON-LD pull into provider-backed source-cache slot; cache key precedence CAID → ClinVar VID → normalized HGVS+gene; cache record = source URL + fetched_at + source_version + raw JSON-LD + normalized summary + stale-on-failure; response extends M11 `clingen_vcep` shape with `vcep`/`final_classification`/`narrative`/`criteria` (with VCEP-specific strength overrides)/`source_scope`/`provenance`; first consumer = new §3.5 Expert Panel disclosure block in /report, lazy-fetched via M11 section endpoint |
| **#4** Claude→Codex M10a gene-scoped pub count | NOT YET OPEN | open WHEN M10a FE slice begins | additive gene-scoped count field on EP-VLEx primitives (aliases / PMID dedupe / source tags / snippets / timeline already exist) |

CARs #2/#3/#4 open **per-slice**, NOT batched, per **DL-002**. This is the
Codex parallel-mode protocol preference (avoids stale specs and idle blocks).

#### What ships inside M3 without scope creep (Tier-1 component upgrades)

Per **DL-003**: upgrades on Phase-0 primitives, NOT a separate milestone.

1. **`CiteChip`** — bottom-left global chip (Feedback + Cite buttons); Cite
   modal per §10.7 format (Software block with real ORCID + Scholar + PubMed
   + Zenodo DOI `(pending)`); supports `?cite=1` URL param, ESC, focus-trap,
   aria-modal.
2. **`Card` verdict prop** — optional 3px frozen-ramp `border-left` accent
   driven by classification verdict.
3. **`ClassificationBadge` review-star slot** — inline 10–12px ClinVar
   review-star glyph + tabular numerals next to verdict.
4. **`StackedCountBar`** — new primitive used for ClinVar submitter splits
   and (intermediate) in-silico ensemble counts; frozen-ramp segments + inline
   white numerals.
5. **`AcmgCriteriaFold` met/not-met coloring** — met chips in frozen-ramp
   color, not-met chips in grey; legend removed (color alone now disambiguates).
6. **`StickyVariantRibbon`** — HGVS + Copy / Share / Export / Save / Cite
   cluster pinned below 60px nav on scroll; mirrors Workbench ContextStrip
   pattern; reduced-motion honors instant pin (no slide).
7. **`PublicationModal`** — modal-on-click with PubMed link + DOI + PDF +
   citation count + abstract + backdrop blur; `?pub=PMID:12345` shareable
   URL param; ESC + focus-trap + return-focus + aria-modal; coexists with
   `?cite=1` (independent params).
8. **`PublicationsCallout` toggle placeholder** — variant-vs-gene count
   toggle in section header; variant count wired to existing
   `PublicationLiterature.total_count`; gene count rendered as
   `Loading...` placeholder until M-006 lands; **honors inbound
   `?pubScope=variant|gene` URL param** so URLs shared during M3 hand off
   cleanly to M-006 when it wires the real fetcher.

#### Sub-agent / next-session runbook

1. **First action this session opens** — TS mirror Codex's M11 contract
   sketch. Read `app/backend/app/schemas/lookup.py` +
   `app/backend/app/api/routes/lookup.py` +
   `app/backend/app/services/lookup_sections.py`; mirror additive types into
   `app/web/lib/backend.ts`; add thin client helpers in `app/web/lib/api.ts`
   for the section-fetch endpoints. Backend-led; FE does not reshape. tsc
   clean on `app/web` only (Vite `app/frontend` out-of-scope).
2. **Wave 1 parallel** — implement M3 Tier-1 component upgrades inside M3
   per §10.9 list above. No backend dependency. Commit per file group with
   explicit `git add -- <paths>` (DL-019).
3. **Wave 3 starts when M-002 mirror lands** — M-003 first (FE-only, zero
   new CARs); M-004 opens CAR #2 at slice start; M-005 opens CAR #3 at slice
   start; M-006 opens CAR #4 at slice start.
4. **Wave 4 starts when M7/M8/M9/M10a all land** — apply LazySection +
   mobile sweep broadly. Trials / disease / population stay eager (DL-013).
5. **Wave 5 deferred** — M10b waits on capacity (~1 Codex quarter); M12
   waits on organic volume justifying landing strip (BE-only primitive when
   pulled forward, hard privacy guardrails); M-010 AM trigger watch criteria
   recorded in `docs/operations/risks-and-guardrails.md` when M-010 is actually touched
   (until then, this section is the canonical reference for the trigger).

#### Risks (mitigations baked into milestones)

- **R-001 / R-003** — Codex slip on a CAR keeps a Wave-3 slice blocked.
  Mitigation: own-tree-harden / mock-first per idle protocol; never block
  on gated milestones. (R-001 is moot now that CAR #1 is closed; pattern
  applies to CARs #2/#3/#4 when they open.)
- **R-002** — Codex's uncommitted Task 12 + Tasks 13-14 files
  (clinvar_local, dbsnp_local, repeatmasker_local + their fixtures and
  tests + supabase/migrations/0007 + PROGRESS.md + plans/v2-backend.md +
  Codex's M11 contract sketch backend files) swept into a Claude commit.
  Mitigation: DL-019 commit-guard in every code-touching code-intent;
  pre-commit checklist verifies staged file list does not contain any
  Codex-owned path.
- **R-004** — AlphaMissense auto-flip without Steven approval. Mitigation:
  M-010 explicitly no-code; constraints record carries MUST-NOT-auto-flip
  rule; trigger surfaces the question, never flips.
