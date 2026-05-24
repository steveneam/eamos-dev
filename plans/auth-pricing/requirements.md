# Auth + Pricing/Payment — UI Requirements

> Captured 2026-05-24 from user direction (Steven), for the NEXT session. Part of
> the post-deployment feature lane (PostHog + auth + Messenger + Stripe). The
> live test deployment is up (see `docs/deployment/README.md` +
> `agent_handoff/CURRENT.md`); these are the first real *features* on top of it.
> Supabase schema + browser client already exist
> (`supabase/migrations/0001_submission_ledger.sql`,
> `app/web/utils/supabase/client.ts`). Build on `app/web` (Next.js).

## A. Sign-up / Login — expandable panel (NOT a new page)

- **Trigger:** the "Sign in / Register" control at the **top-right of the landing page**.
- **Behavior:** **expands in place** (dropdown / popover / anchored panel) — does
  NOT navigate to a separate route. Closes on Cancel / outside-click / Esc.
- **OAuth "auto sign-in" row** at the **top** of the panel — icon buttons. User
  named Apple, Google, LinkedIn. Recommended set + additions: see "OAuth providers".
- **Email/password form:**
  - Email
  - Create password
  - Confirm password (must match)
  - Accept **Terms & Conditions** checkbox (required to enable Sign up) — needs a
    real Terms link/page.
  - Buttons: **Cancel** | **Sign up**
- **Login vs Sign-up:** the user described the *sign-up* shape. Add a small
  toggle/link ("Already have an account? Log in") so the same panel handles login
  (email + password + Sign in). Confirm with user. Include password-reset link.
- **Backend:** Supabase Auth. `profiles` row auto-creates on signup via the
  `handle_new_user` trigger (already in the migration). RLS already enabled.
  To make the tables usable post-login we must `GRANT` the `authenticated` role
  (SELECT/INSERT/DELETE per table) — currently anon AND authenticated have no
  grant (secure default). This is the deliberate "expose to logged-in users" step.

## B. Pricing / Payment — NEW page (route, e.g. `/pricing` → `/checkout`)

User: "should lead to a new page." Three reference layouts provided (screenshots
2026-05-24):

1. **Plan-comparison tier cards** (ref shot 2): two cards (e.g. Pro / Max) with
   the emerald tree/anchor icon, a **Monthly/Yearly toggle** (Save X%), price in
   **AUD + GST**, a prominent CTA button, and a feature checklist
   ("Everything in Free and:" / "Everything in Pro, plus:"). This is the `/pricing`
   landing layout — fits the existing emerald aesthetic.
2. **Order-summary / upgrade** (ref shot 1): selectable plan cards with a
   "Save 50%" badge + radio; an **Order details** panel (plan line, prorated
   adjustments, subtotal, GST, **total due today**); auto-renew notice; payment
   method row (saved card + edit pencil); T&C agreement checkbox; full-width
   "Upgrade to X" button.
3. **Split-panel checkout** (ref shot 3): LEFT = gradient summary panel (plan,
   **promo code**, subtotal, total due today); RIGHT = payment form (billing
   frequency toggle monthly/yearly + save %, **payment method tabs: Card / PayPal
   / Apple Pay / Google Pay**, card fields, billing address, country, full-width
   **Subscribe** button).
4. **Payment success / confirmation** (ref shot 4): a centered receipt card —
   green check icon, "Payment Successful" + thank-you line, a **receipt/order #**
   chip, a details list (Time/Date, Payment ID, Payment Method, Sender/account
   name), an amount block (Amount, GST, **Total**), and two buttons: **Return**
   (→ landing/account) | **More** (→ receipt detail / invoice / account billing).
   Shown after Stripe confirms payment (success-return route; ideally only show
   "paid" once a Stripe webhook has reconciled the charge).

**Synthesis for Eamos:**
- `/pricing`: tier cards (layout 1) in emerald, monthly/yearly toggle, AUD+GST.
- Choosing a paid plan → checkout (layout 2/3 hybrid): order summary + payment.
- **Payment = Stripe.** Strong recommendation: use **Stripe Checkout (hosted)**
  or the **Payment Element** rather than building the raw card form in shots 1/3.
  The Element/Checkout gives Card + Apple Pay + Google Pay (+ Link/PayPal) out of
  the box, is PCI-compliant, and is far less work than a custom card form. We can
  style the *surrounding* page (summary panel, plan cards) to match the refs while
  Stripe owns the actual card entry. RAISE the tradeoff with the user
  (pixel-custom card form vs Stripe-hosted security/speed) before building.

## OAuth providers (Claude recommendation — confirm with user)

User asked "Apple, Google, LinkedIn, anything else?". Recommendation for Eamos's
researcher/clinician audience:
- **Google** — essential; universal; Supabase-native. (Must.)
- **Microsoft / Entra ID** — ADD. Universities, hospitals, and enterprises run on
  Microsoft 365; for institutional users this beats Apple. Supabase-native (azure).
- **LinkedIn** — keep; professional/B2B fit (researchers, clinicians).
- **Apple** — optional polish; needs a paid Apple Developer account ($99/yr) and
  the most setup; most consumer-oriented. Lowest priority of the four.
- **ORCID** — the distinctive one: ORCID is the de-facto researcher identity
  (every academic has an iD). Great audience signal/differentiator, but it's NOT a
  Supabase-native provider — needs generic OIDC config (more setup). Flag as a
  phase-2 differentiator.
- **GitHub** — only if a bioinformatician/developer audience matters; Supabase-native.

Setup note: each provider = config in Supabase + the provider's dev console
(client id/secret + redirect URL). First cut: Google + email/password, then add
Microsoft + LinkedIn; Apple/ORCID later.

## Open decisions for next session
- Final OAuth provider set.
- Real pricing tiers + amounts. Deployment guide §5 said Free / Starter A$9.95 /
  Pro A$24.95; the reference screenshots show different numbers (reference only).
- Stripe Checkout-hosted vs Payment Element vs full custom card form (recommend
  hosted/Element).
- Login/Sign-up toggle + password reset within the panel.
- Terms & Conditions page content/link.

## Build order (dependencies)
1. **Auth** (Supabase Auth + expandable panel) + `GRANT authenticated` — unlocks
   the full RLS round-trip (sign-in → read/write own rows). Also the moment to
   verify RLS isolation end-to-end.
2. **Save-variant / "Messenger" submission UI** (uses `saved_variants` /
   `user_evidence_submissions`).
3. **Pricing page + Stripe checkout.**
- **PostHog** is independent + quick; can land any time (provider code in
  `docs/deployment/README.md` §8).

## Deploy reminder (so the features go live)
Both Vercel + Render are **auto-deploy OFF**. After building, commit + (user) push,
then **manual redeploy** each. New env vars (Supabase NEXT_PUBLIC_* for the live
site; Stripe keys) go in the Vercel dashboard (publishable client-side; secret
keys → Render/server only).
