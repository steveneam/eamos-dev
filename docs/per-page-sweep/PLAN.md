# Per-page sweep — orchestration plan

Synthesis of the 4 scout reports (`landing.md`, `auth-account.md`, `commerce.md`, `report-body.md`).
Scouts used `frontend-design` + `ui-ux-pro-max`. Claude = orchestrator + implementor.
Rule: durable/structural/marketing-visual changes need Steven's OK before shipping
([[feedback_subagent_recommendations_not_authorization]]). Everything below is FE-only, `app/web`, token-first.

Gates held all session: app/web **tsc 0-err**, **eslint 0-err / 3-warn** (pre-existing: CompareClient:61, VariantTable:112, PubMedSection:120).

---

## ✅ SHIPPED this session (uncommitted)

### A. Typography invariant change — HGVS identity off mono → Inter (Steven-approved)
The mono font was already JetBrains→IBM Plex (2026-06-03); "from jetbrains" = take HGVS variant
identity off the monospace family. Spectral is display-only so the proportional target is **Inter**
(+ `tabular-nums`). Coords / scores / sequences stay mono.
- Hero `.vh-cdna` / `.vh-prot` + breadcrumb → Inter (`VariantHeader.tsx`).
- Sticky ribbon: gene Spectral→**Inter 600** (delicate at 16px), HGVS mono→Inter (`StickyVariantRibbon.tsx`).
- Library saved cards `.lib-hgvs` / `.lib-hgvs-full` (`library.css`); related cards `.rel-gene` / `.rel-cdna` (`RelatedVariants.tsx`).
- Batch + variant table identity columns `r.hgvs_c` / `v.variant` → Inter+tabular-nums (`BatchResultsTable.tsx`, `VariantTable.tsx`). Index/AF/raw columns stay mono.
- **Kept mono (intentional):** search inputs (`SearchShell.tsx`) = "type a code here" entry affordance; the `v.raw` echo column.
- Purged stale "JetBrains" refs + updated the invariant in `DESIGN.md` + `globals.css` comments. (`layout.tsx:24` historical decision-note kept.)

### B. Report-body consistency pass (report-body.md Fixes 1,2,3,5,6)
- Mave inset `marginTop` 16→18 (kill §1 stutter); §3/§6 inset padding `14px 18px`→`14px 16px`.
- **Real bug:** undefined `--ink-1` (scale is `--ink`,`--ink-2..5`) → `--ink` in ExpertPanelSection + CalibratedInSilicoTable.
- DiseaseSection field-label → canonical `.eamos-kicker`. Legacy `--teal-faint`→`--teal-tint` (MolecularContext + ProteinTrack).
- Deferred: Fix 4 inner-gap collapse (most subjective, low value).

### C. Landing P0s (landing.md)
- Hero subhead terminal period (`LandingClient.tsx`).
- `scroll-padding-top: var(--nav-h)` + `scroll-behavior: smooth` on `html` (anchor links cleared the sticky nav).

---

## ✅ SHIPPED (cont.) — Steven steered: landing=all 3 systemic, pricing=keep neutral, auth=all 3 structural

### D. Landing (landing.md) — DONE + browser-verified
- F3 off-token colour → tokens: MetricBelt `--teal-bdr`/`--info-*`/`--warn-text`; new shared `--em-ink` token replaces raw `#04140e` ×4 (HowItWorks/Pricing×2/EamosSearch); FeaturesGrid emerald `rgba` → `color-mix(--em)`.
- F4 (approved) HowItWorks code-blocks near-black `rgba(0,0,0,.22–.32)` → warm `--page-bg`/`--page-bg-deep` + `--hero-ink`.
- F5 (approved) new `LandingEyebrow` primitive (`ui/LandingEyebrow.tsx`) unifies the 4 drifted micro-labels (SourceStrip/SiteFooter/HowItWorks/MetricBelt); colour stays per-ground.
- F6 (approved) rhythm tiers — short sections Faq + Testimonials `py-28`→`py-24`.
- F7 tabular metric badges; F9 pipe glyph → hairline; F12 hero measure 580→520. **Flagged (not shipped): F8 hero search-glow slate→elevation (noticeable hero change — wants OK); F10 specimen empty-Computational copy.**

### E. Commerce (commerce.md) — DONE + gated (**no "Most popular" pill — keep neutral**)
- F7 (P0 trust): `subscribe()` now sends explicit `cycle=monthly` (truthful) and **omits** `method`; receipt gates the "Payment method" row on a real param → no more false "Card/Monthly".
- F2 featured border `rgba(52,211,153,.55)` → `color-mix(--em 45%)`; F5 non-featured CTA border → `color-mix(--em 32%, --hero-line)`; F4 caption `--hero-ink-3`→`--hero-ink-2`; F8 payment pills → "Pay with" label + de-emphasised (informational); F11 tabular-nums on prices + receipt rows; F13 receipt email wraps (was truncated on mobile).

## 🟡 REMAINING — Auth / Account (auth-account.md) — Steven approved all 3 structural
- **Safe (no ask):** P0 `.ap-primary-btn` disabled affordance (`.45–.55` opacity); P0 placeholder-only labels → visible `<label>`; P0 sign-up double error channel → route length/mismatch to field, server errors to banner; password visibility toggle on shared `Field`; sub-44px Remove btn; grey "Forgot password?" → teal accent; unify drifted `.ap-*`/`.ac-*`/`.upw-*` field/btn bg + font-size.
- **Structural (approved):** labelled stacked OAuth row; chromeless full-page `/auth` + `/account` panel; refactor `update-password` onto shared `Field`.
- Heaviest surface (logic + structural) → own focused pass + browser-verify the sign-in/sign-up/account flows.

---

## 🟡 FLAGGED — Steven's call before I implement (durable / structural / marketing)

**Landing**
1. Vary the flat `py-28` section rhythm into tiers (durable spacing system).
2. `LandingEyebrow` primitive — unify the 4 near-identical micro-label specs into one.
3. Recolour the near-black `rgba(0,0,0,.22–.32)` HowItWorks code blocks → warm cream/teal (only near-black surfaces on the page).

**Commerce**
4. "Most popular" emphasis pill on a tier (which tier — marketing decision).
5. CTA-height unification across plan cards; real payment-method plumbing (touches checkout data flow — likely Codex-adjacent).

**Auth**
6. Labelled stacked OAuth button row; chromeless full-page auth panel; refactor `update-password` onto the shared `Field`.

**Report body**
7. Promote inset-panel geometry to a `--report-subpanel-*` token set; CallCardsGrid radius (10) vs §-Card (14); consolidate §3's duplicate cohort header.
