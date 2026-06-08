# Commerce surface sweep — pricing → checkout → receipt

Assessment only. Scope: the paid funnel — plan tiers (landing `#pricing`), `/checkout`, `/checkout/success`.
Design system: `D:\eamos\DESIGN.md` + the token block in `D:\eamos\app\web\app\globals.css`.
Skills consulted: `frontend-design`, `ui-ux-pro-max` (`--domain ux/style/typography/product/web`).

Quality bar reminder (DESIGN.md): brand surfaces (landing/checkout) sit on warm-paper, hover signal is the
teal axis (border/underline swap — **never** translateY lift, **never** shadow swap on pricing cards,
user-mandated 2026-05-26). Color encodes meaning; restraint is the house style. The funnel's job is
**clarity + trust**, so most findings are about hierarchy and legibility, not decoration.

---

## 1. Surface map

| File | Role |
| ---- | ---- |
| `D:\eamos\app\web\components\landing\Pricing.tsx` | **Where pricing lives.** Landing `#pricing` section. `PLANS.map` → `<PlanCard>` ×3 (Free/Pro/Max), `<AudienceToggle>` (Individual / Team & Enterprise), `<EnterpriseCard>`, mobile snap-carousel + `<CarouselDots>`. CTAs link to `/checkout?plan=<id>`. |
| `D:\eamos\app\web\lib\plans.ts` | Pricing model — `PLANS` array, `ENTERPRISE`, `getPlan`, `gstComponent`, `formatAud`. Single source of truth shared by landing + checkout. Yearly fields present but intentionally not surfaced. |
| `D:\eamos\app\web\app\checkout\page.tsx` | Route shell — `<Suspense>` → `<CheckoutClient>`. |
| `D:\eamos\app\web\components\pricing\CheckoutClient.tsx` | Checkout — 2-col: LEFT order summary (plan, promo input, manifest rows, total), RIGHT payment (method pills, Stripe redirect notice, Continue CTA, `<TrustBand>`). |
| `D:\eamos\app\web\app\checkout\success\page.tsx` | Route shell → `<CheckoutSuccessClient>`. |
| `D:\eamos\app\web\components\pricing\CheckoutSuccessClient.tsx` | Receipt — document-style card: plan-active strip, receipt rows, totals, Return-home / View-account actions. |
| `D:\eamos\app\web\components\pricing\PageHeader.tsx` | Shared brand nav for checkout/account (`tone="light"`). |

Funnel flow: landing `#pricing` → `Choose Pro` → `/checkout?plan=pro` → `Continue` → `/checkout/success?plan&amount&order`.

---

## 2. Findings

Severity: **P0** broken/trust-or-conversion-damaging · **P1** clear inconsistency or hierarchy miss · **P2** polish.

### Pricing cards (`Pricing.tsx`)

**F1 · `Pricing.tsx:126-140` · No "Most popular / Recommended" label on the featured tier · P1**
The Pro card is the intended hero (`featured: true` in `plans.ts`, semi-teal rest border + filled CTA), but the
**only** signal is a faint border tint and CTA fill. There is no badge, no label, no copy telling the user Pro
is the recommended pick. ui-ux-pro-max (Navigation/Active-State, and the universal pricing pattern) — the
recommended tier must be *unmistakably* indicated; here the eye gets no anchor and all three cards read as
equal rank. This is the single highest-leverage conversion fix on the surface. (Geometry is deliberately
identical per the card comment — so the emphasis must come from a label, not size.)

**F2 · `Pricing.tsx:136` · Featured border uses a raw `rgba(52,211,153,0.55)` literal, off-token · P1**
`border: 0.5px solid ${isFeatured ? 'rgba(52,211,153,0.55)' : 'var(--page-line)'}`. `rgba(52,211,153)` is
emerald-500, **not** an Eamos token — the brand teal is `--em` / `--teal` (`#1D9E75`). The hover correctly
swaps to `var(--em)`, so at rest the featured card is a *different green* than on hover and than every other
teal accent on the page. DESIGN.md "No colours outside the palette"; consume the teal axis via token. Use a
`color-mix` of `--em` so rest and hover are the same hue.

**F3 · `Pricing.tsx:159,287` · Price number is `--mono` (JetBrains Mono), inconsistent with checkout's `--mono` total but worth a deliberate call · P2**
Prices render in `--mono` at 32px 600. That is internally consistent with the checkout total (also `--mono`),
and DESIGN.md sanctions mono for "scores/coords/dense numerics", with prices explicitly "may use tabular-nums
Inter — check what's idiomatic." Mono is defensible here (it reads as a precise figure). No change needed, but
see F11 — mono prices should carry `font-variant-numeric: tabular-nums` so digits don't shift. Logged as
don't-touch + a one-line polish.

**F4 · `Pricing.tsx:167-169` · "Free forever" vs "Billed monthly · incl. GST" caption sits in `--hero-ink-3` (hint) · P2**
The price sub-caption is the faintest ink rank. On the cream `--page-bg-deep` ground at 11.5px this is the
billing-cadence line — borderline legibility, and billing cadence is trust-relevant copy on a pricing surface.
Bump one rank to `--hero-ink-2` (still secondary, but readable).

**F5 · `Pricing.tsx:343-351` · Non-featured CTA (`Get started`, `Choose Max`) is a low-contrast glass fill · P1**
`ctaStyle(false)` = `background: var(--hero-glass2)`, `color: var(--hero-ink)`, hairline border. On the Free and
Max cards the CTA is a near-invisible ghost on cream — it barely reads as a button. DESIGN.md affordance
cheat-sheet: a CTA is the heaviest element in its region and "clickable looks clickable". The two non-featured
CTAs currently recede below the feature list in visual weight. Acceptable to keep Pro as the only *filled* teal
CTA (intentional rank), but Free/Max need a clearer button affordance (stronger border or ink, see spec).

### Checkout (`CheckoutClient.tsx`)

**F6 · `CheckoutClient.tsx:222-235` · `Continue` button has no honest pending/redirect state beyond a label, and an 8s magic reset · P1**
`subscribe()` sets `busy`, pushes the route, and `setTimeout(() => setBusy(false), 8000)`. The label flips to
"Redirecting…" (good) but there's no spinner/visual pending token, and the 8000ms fallback is a magic number
that can leave the CTA disabled for 8s if navigation is interrupted. DESIGN.md principle #4 "feedback immediate
and honest" — a single synchronous nav should show one honest pending state. Low risk in preview, but flag the
hardcoded timeout. (Functional, not visual — see flagged §4 for the route-data gap that compounds this.)

**F7 · `CheckoutClient.tsx:469-477` + `subscribe()` · Receipt loses payment method + billing cycle · P0 (trust/correctness)**
`subscribe()` builds the success URL with only `plan`, `amount`, `order`. But `CheckoutSuccessClient` reads
`method` (→ defaults "Card") and `cycle` (→ defaults "monthly") from params. So the receipt **always** says
"Card" / "Monthly" regardless of what the buyer did, and the order summary's promo discount is folded into
`amount` with no line item on the receipt. On a payment confirmation this is a correctness/trust defect: the
document misrepresents the transaction. (In preview no real method is chosen, but the receipt still asserts a
specific method as fact.) Fix: pass the real values, or drop the "Payment method" row until a method is actually
selected. P0 because it's a receipt stating something false.

**F8 · `CheckoutClient.tsx:422-438` · Payment-method pills are decorative but read as selectable · P1**
`['Card','Apple Pay','Google Pay','Link']` render as pill chips identical in shape to interactive pills
elsewhere on brand surfaces, but they're static `<span>`s with no selected state and no role. ui-ux-pro-max
(Affordance / Active-State): a control that looks like a choice but isn't is a guess-trap. They're meant as
"these are supported" badges — make them visually read as informational (lighter, no pill-button look) or label
the group ("Pay with"). Also note: `'Link'` (Stripe Link) is opaque jargon to a clinician buyer.

**F9 · `CheckoutClient.tsx:314-331` · Promo input border is set both via inline `style` and the `.cc-promo-input` class · P2**
The invalid border color is applied twice (inline `style={{ border: ... var(--err) ... }}` and the
`[data-invalid]` CSS rule). Redundant; the inline style also hardcodes the rest border to `--line-2` which the
class doesn't set, so the rest border lives inline while hover/focus/invalid live in CSS — split-brain styling
that's easy to break. Consolidate into the class.

**F10 · `CheckoutClient.tsx:357,365` · GST row says "GST (10%)" with hint "Included in the total below", but subtotal is labelled "Subtotal (ex. GST)" · P2**
The manifest shows Subtotal (ex GST) + GST (10%) as if they add up to the total, but GST is *already inside* the
displayed price (`gstComponent` extracts it from the inclusive amount). A scanning buyer may read it as additive
tax. The hint mitigates but the row order (subtotal, then GST, then total) implies summation. Minor copy/clarity
— consider "of which GST" framing. Low severity; logged for the copy pass.

### Receipt (`CheckoutSuccessClient.tsx`)

**F11 · `CheckoutSuccessClient.tsx:218-228` + `CheckoutClient.tsx:375-385` · Currency figures lack `tabular-nums` · P2**
All the `--mono` price/total spans (and the manifest values) omit `font-variant-numeric: tabular-nums`. Mono
fonts are *usually* tabular but JetBrains Mono's currency glyphs + the `$` from `Intl.NumberFormat` can still
cause baseline/width drift across rows in the manifest and receipt tables. ui-ux-pro-max typography: align
numeric columns. Add `font-variant-numeric: tabular-nums` to the price/manifest/receipt numeric spans.

**F12 · `CheckoutSuccessClient.tsx:177-188` · Receipt rows use a `<table>` but the manifest on checkout uses flex divs · P2**
Two different layout primitives for the same "label · value" pattern across the two screens (checkout manifest =
flex rows; receipt = table). Both work; it's an internal inconsistency that makes future edits diverge. Not
worth a refactor now — logged as a consistency note.

**F13 · `CheckoutSuccessClient.tsx:282-319` (ReceiptRow) value cell · truncates with ellipsis at `maxWidth: 220` · P1 (mobile)**
The value cell is `whiteSpace: nowrap` + `overflow: hidden` + `textOverflow: ellipsis` + `maxWidth: 220`. A long
account email (the `Account` row, `user?.email`) will silently truncate — on the receipt the buyer can't see
their own billing email in full. On a 390px viewport the 500px card already shrinks; truncating the email on the
*receipt they keep* is a real loss. Allow the email row to wrap (it's the one row where the full value matters).

**F14 · `CheckoutSuccessClient.tsx` · No print affordance on a receipt · P2**
This is the one document a buyer is most likely to print/save, but there's no "Print / Save PDF" action — only
Return-home and View-account. ui-ux-pro-max (product/receipt): receipts should be savable. Low effort
(`window.print()` + a print stylesheet), but it's net-new behavior → logged in flagged §4, not auto-applied.

### Cross-surface

**F15 · `Pricing.tsx:343-351` vs `CheckoutClient.tsx:84-105` vs `CheckoutSuccessClient.tsx:322-331` · Three near-identical CTA button definitions, three radius/height specs · P2**
Pricing CTA: 44px / radius 10. Checkout primary-link: 44px / `--r-md`. Receipt actionBtn: 42px / `--r-md`.
Continue button: 48px / `--r-md`. Four different button heights across one funnel (42/44/48). Minor, but the
funnel would feel more crafted with a consistent CTA height. Logged as polish.

**F16 · `CheckoutClient.tsx:192-219` (empty state) · "Choose a plan first" empty state is solid, but its CTA height (44) differs and there's no nav back into the funnel beyond "View pricing" · P2**
Good that the no-plan case is handled. Minor: the empty state is fine; just noting it's the only well-handled
edge case (no loading/error states elsewhere, which is acceptable for a mock preview).

---

## 3. Implementation spec (P0/P1, directly applicable)

All values use existing tokens. No new hex.

### F1 — add a "Most popular" label to the featured (Pro) card  *(P1)*
`Pricing.tsx` `PlanCard`, when `isFeatured`. Inside the card's top region (above or beside `<LandingH3>`), add a
small pill. Reuse the existing eyebrow idiom already used elsewhere in this file (11px uppercase tracked):
```tsx
{isFeatured && (
  <span
    className="mb-3 inline-block text-[10.5px] font-semibold uppercase tracking-[0.08em]"
    style={{
      padding: '3px 10px',
      borderRadius: 999,
      background: 'color-mix(in oklab, var(--em) 12%, transparent)',
      color: 'var(--em-deep)',
      border: '0.5px solid color-mix(in oklab, var(--em) 40%, transparent)',
    }}
  >
    Most popular
  </span>
)}
```
Place it as the first child of the inner `<div style={{ flex: 1 ... }}>` (before the `mb-1` name block), or
absolutely-positioned top-right of the card (`.relative` is already on the card root). Keeps geometry identical
across cards (label only), satisfies the "lead the rank" intent the border was trying and failing to carry alone.

### F2 — featured rest border on-token  *(P1)*
`Pricing.tsx:136`
```diff
- border: `0.5px solid ${isFeatured ? 'rgba(52,211,153,0.55)' : 'var(--page-line)'}`,
+ border: `0.5px solid ${isFeatured ? 'color-mix(in oklab, var(--em) 45%, transparent)' : 'var(--page-line)'}`,
```
Now rest and the `:hover { border-color: var(--em) }` are the same hue, brand-correct.

### F5 — strengthen non-featured CTA affordance  *(P1)*
`Pricing.tsx` `ctaStyle(false)` (lines 347-351). Keep Pro as the only *filled* teal CTA, but give Free/Max a real
button read — deepen the border to the teal axis and the text to full ink:
```diff
  background: featured ? 'var(--em)' : 'var(--hero-glass2)',
  color: featured ? '#04140e' : 'var(--hero-ink)',
- border: `0.5px solid ${featured ? 'var(--em)' : 'var(--hero-line)'}`,
+ border: `0.5px solid ${featured ? 'var(--em)' : 'color-mix(in oklab, var(--em) 32%, var(--hero-line))'}`,
```
(`--hero-ink` text is already correct; the border is what was disappearing.) The existing `.pc-cta:hover`
brightness step still applies. If stronger is wanted, that's a structural call → §4.

### F7 — receipt must reflect the real transaction  *(P0)*
`CheckoutClient.tsx` `subscribe()` (lines 222-235). Pass the values the receipt reads, instead of letting it
default to "Card"/"Monthly":
```diff
  const q = new URLSearchParams({
    plan: plan.id,
    amount: String(totals.total),
    order,
+   cycle: 'monthly',           // explicit; the only cycle currently surfaced
+   method: 'card',             // until a real method is selected
  })
```
AND on the receipt, since no method is actually *chosen* in the preview, prefer dropping the assertion over
stating a false one. `CheckoutSuccessClient.tsx:181`:
```diff
- <ReceiptRow label="Payment method" value={method} />
+ {params.get('method') ? <ReceiptRow label="Payment method" value={method} /> : null}
```
Net: the receipt only claims a method when one was passed. (If Steven prefers always showing "Card" as the
preview default, the `cycle`/`method` params above make it truthful-by-construction instead of defaulted.)

### F8 — payment-method pills read as informational, not selectable  *(P1)*
`CheckoutClient.tsx:422-438`. Add a group label and de-emphasize the chips so they don't impersonate a choice:
```diff
+ <p className="mt-4 text-[11.5px] font-semibold" style={{ color: 'var(--ink-2)' }}>Pay with</p>
- <div className="mt-5 flex flex-wrap items-center gap-2">
+ <div className="mt-1.5 flex flex-wrap items-center gap-2">
    {['Card', 'Apple Pay', 'Google Pay', 'Link'].map((m) => (
      <span ... style={{
-       background: 'var(--bg-soft)',
-       color: 'var(--ink-2)',
+       background: 'transparent',
+       color: 'var(--ink-3)',
        border: '0.5px solid var(--line)',
      }}>
```
Rename `'Link'` → keep, but the group label "Pay with" now frames all four as supported rails, not buttons.

### F4 — billing-cadence caption one rank brighter  *(P2→do with F1)*
`Pricing.tsx:167`
```diff
- <p className="mt-1.5 text-[11.5px]" style={{ color: 'var(--hero-ink-3)', minHeight: 16 }}>
+ <p className="mt-1.5 text-[11.5px]" style={{ color: 'var(--hero-ink-2)', minHeight: 16 }}>
```

### F11 — tabular figures on all currency spans  *(P2, trivial, do it)*
Add `fontVariantNumeric: 'tabular-nums'` to the mono price spans:
- `Pricing.tsx:150-158` (card price) and `:285-294` (enterprise "Custom").
- `CheckoutClient.tsx:375-385` (Total due) and `ManifestRow` value span (`:551-559`).
- `CheckoutSuccessClient.tsx:200-208,218-228` (Amount/GST/Total) and `ReceiptRow` value cell.
Example: `style={{ ..., fontVariantNumeric: 'tabular-nums' }}`.

### F13 — let the receipt email wrap  *(P1, mobile)*
`CheckoutSuccessClient.tsx` `ReceiptRow` value cell (lines 303-318). The truncation is fine for short values but
wrong for the email. Either drop the nowrap globally, or add an opt-in `wrap` prop and pass it on the Account row:
```diff
  function ReceiptRow({ label, value, mono }: {...}) {
```
Simplest surgical fix — remove the nowrap/ellipsis (values are short except email; wrapping is harmless):
```diff
-       maxWidth: 220,
-       overflow: 'hidden',
-       textOverflow: 'ellipsis',
-       whiteSpace: 'nowrap',
+       wordBreak: 'break-word',
```

### F9 — consolidate promo-input border into the class  *(P2)*
`CheckoutClient.tsx`. Add a rest border to `.cc-promo-input` and drop the inline `style` border:
```diff
  .cc-promo-input {
    flex: 1; height: 38px; ...
+   border: 0.5px solid var(--line-2);
  }
```
and remove the inline `style={{ border: ... }}` on the `<input>` (the `[data-invalid]` rule already handles the
error border).

---

## 4. Flagged — needs Steven approval (durable / structural / net-new)

- **F6 / F7 follow-through — real method+cycle plumbing.** Truly fixing the receipt's method/cycle means deciding
  the preview's intended behavior (always "Card monthly"? or carry a selected method?). The §3 fix makes it
  *truthful*, but a real method selector is a structural addition — confirm direction.
- **F14 — Print / Save-PDF action on the receipt.** Net-new behavior + a print stylesheet. Standard for receipts,
  but it's an added control on a brand surface → wants the OK before shipping.
- **F5 escalation — if Free/Max CTAs should become *filled* secondary buttons** (vs the border-only bump in §3),
  that changes the deliberate "Pro is the only filled CTA" rank decision. Structural rank change → approve first.
- **F8 — if the method pills should become a real selectable control** (radio group) rather than informational
  badges, that's a feature, not polish.
- **F15 — unifying CTA button height (42/44/48 → one value) across the funnel.** Touches three files' shared
  button idiom; low-risk but it's a cross-surface normalization → confirm the canonical height (recommend 44).

---

## 5. Don't-touch (intentional-but-odd)

- **Mono prices (F3).** `--mono` for price figures is internally consistent (landing + checkout + receipt all use
  it) and DESIGN.md explicitly permits mono for dense numerics. Reads as a precise figure; keep. (Only add
  tabular-nums per F11.)
- **`borderRadius: 16` on pricing/enterprise cards** (`Pricing.tsx:137,272`). Above `--r-lg` (14px) but it
  deliberately matches `FeaturesGrid.tsx:54` — the landing-card radius is a chosen 16px. Consistent within the
  landing register; leave.
- **Yearly pricing fields unused** (`plans.ts` `yearly`, `perMonth`, `yearlySavingPct`). Intentionally retained,
  not surfaced (user decision 2026-05-24, monthly-only). Not dead code to remove.
- **"Preview build — no charge" copy** on checkout + receipt. Deliberate test-deployment honesty. Keep until
  launch.
- **No `type="email"` / real card fields on checkout.** By design — checkout redirects to Stripe hosted checkout;
  there are no card fields to harden here. The ui-ux-pro-max "input types" guideline doesn't apply.
- **Raw `borderRadius: 999/100/10`** throughout. Project-wide idiom for pills / `--r-md`; not a commerce-specific
  defect.
- **Audience toggle `#04140e` active text** (`Pricing.tsx:251`, and `ctaStyle` featured text). A near-black ink on
  the bright `--em` fill for contrast — used consistently for teal-on-CTA text across the brand surface. Leave.

---

## Summary

The commerce funnel is solid, on-system, and accessibility-aware (labels, `aria-live`, focus rings, reduced-motion
inherited globally). The gaps are **hierarchy and trust**, not decoration. The two highest-value fixes: **F1** —
the featured Pro tier has no "Most popular" label, so the recommended plan has no anchor (pure conversion loss);
and **F7** — the receipt asserts a payment method/cycle the checkout never sent, so the confirmation document can
state something false (a trust defect on the one page a buyer keeps). Quick wins alongside them: on-token featured
border (F2, currently emerald-500, off-palette), a readable non-featured CTA (F5), informational-not-selectable
payment pills (F8), email-wrap on the receipt (F13), and tabular currency figures (F11). Larger calls — real
method plumbing, a Print/Save action, and CTA-height unification — are flagged for approval in §4.

File written: `D:\eamos\docs\per-page-sweep\commerce.md`
