# Auth + Pricing Backend Contracts

Section edited: 2026-05-24 19:51 +1000 - Codex.

## Payment Host Decision

Use the existing FastAPI backend on Render for Stripe webhooks and checkout
session creation, not Vercel/serverless functions.

Reasons:

- Stripe secret keys and webhook secrets stay server-side with the backend env.
- The webhook can write subscription state through the same repository/database
  layer as the rest of the backend.
- Vercel remains a pure Next.js frontend plus `/api/*` proxy; Claude's `app/web`
  work only needs to call stable backend routes.
- A separate serverless webhook would create a second deployment surface and a
  second persistence path for the same subscription state.

## Evidence Submission Contract

`POST /api/v1/evidence-submissions`

Authentication: bearer token. The backend accepts existing Eamos test tokens and
can accept Supabase Auth JWTs when `SUPABASE_JWT_SECRET` is configured.

Request:

- `variant_hgvs`: accession-qualified HGVS such as `NM_000492.4:c.199C>T`.
- `submitted_pmid`: PubMed ID, digits only or `PMID:<digits>`.
- `curator_notes`: optional rationale text.
- Optional ClinVar functional-data fields: `condition_name`, `assay_type`,
  `collection_method`, `functional_effect`, `functional_consequence`, `method`,
  `result`, `evidence_codes`.

Response:

- `pubmed`: PubMed validation result. In `USE_REAL_APIS=false`, the backend
  records structural validation with `status: "unchecked"` and a warning.
- `clinvar_tracking_id`: internal tracking id, also used as the draft ClinVar
  submission name/local key.
- `clinvar_payload`: draft NCBI ClinVar `noClassificationSubmission` payload.
  `payload_status` is `ready_for_clinvar_dry_run` only when the required
  curator fields are present; otherwise it is `draft_needs_curator_fields`.
- `ledger_status: "recorded"` after the backend records the submission.

### Evidence Ledger Persistence

The accepted evidence-submission ledger is now Supabase-first when these
backend env vars are configured:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET` / `SUPABASE_JWT_ALGORITHM` for Supabase bearer-token
  authentication, already supported by the auth dependency.

Apply `supabase/migrations/0003_evidence_submission_payload.sql` after `0002`.
It adds one additive column:

- `submission_payload jsonb not null default '{}'::jsonb`

Existing frontend ledger reads keep using the stable columns
`variant_hgvs`, `submitted_pmid`, `curator_notes`, `clinvar_tracking_id`, and
`created_at`. The backend stores its richer generated fields in
`submission_payload`: PubMed validation, ClinVar draft, payload status,
submitted functional fields, evidence codes, and warnings.

If Supabase write-through env is absent, the backend keeps the local SQLite
repository fallback for offline tests/dev only. Tests cover the Supabase REST
boundary with a fake PostgREST client; no live Supabase secret is required.

## Payments Contract

`POST /api/v1/payments/checkout-session`

Request: `plan_key` (`pro` or `max`). Checkout is monthly-only; clients should
send `/checkout?plan=<id>` with no cycle. Free has no Stripe checkout path.

If Stripe is not configured, returns `mode: "mock"` so the UI can remain
mock-first. With `STRIPE_SECRET_KEY` and the matching monthly price env var, the
backend creates a hosted Stripe Checkout session:

- `STRIPE_PRICE_PRO_MONTHLY`
- `STRIPE_PRICE_MAX_MONTHLY`

The old `starter` id and `yearly` billing interval are retired. While Eamos is
in stealth mode, backend defaults use the Vercel dev frontend; `eamos.com.au` is
parked and should not be treated as the live browser origin:

- `https://eamos-dev.vercel.app/checkout/success?session_id={CHECKOUT_SESSION_ID}`
- `https://eamos-dev.vercel.app/checkout`

`GET /api/v1/payments/plan`

Returns the authenticated user's current plan. Missing subscription state maps to
`plan_key: "free"` and `status: "free"`. The response also includes the
canonical backend plan contract and limits:

| Plan | id | AUD monthly, GST incl. | AI queries/day | Evidence submissions | VCF uploads | Search rate-limit |
| --- | --- | ---: | ---: | --- | --- | --- |
| Free | `free` | $0.00 | 3 | Disabled | Disabled | Quiet Free search rate-limit |
| Pro | `pro` | $9.95 | 10 | Active subscription + identity verification required | Enabled; numeric cap pending product decision | Standard |
| Max | `max` | $24.95 | 100 fair-use | Active subscription + identity verification required | Bulk/fair-use | Standard |

The response field is `plan: { plan_key, display_name,
monthly_price_aud_cents, currency: "AUD", billing_interval: "monthly",
limits: {...} }`. VCF numeric caps stay explicit in the contract surface but
remain product-gated until Steven locks the exact Pro/Max cap values.

`POST /api/v1/payments/stripe/webhook`

Verifies `Stripe-Signature` using `STRIPE_WEBHOOK_SECRET` and records plan state
from:

- `checkout.session.completed`
- `customer.subscription.*`
- `invoice.paid`
- `invoice.payment_failed`

Webhook metadata should include `user_id` and `plan_key`. `billing_interval` may
be omitted; the backend records paid plans as monthly. Stripe price ids remain
environment-gated until the real Stripe products are known.
