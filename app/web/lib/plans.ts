// Pricing model for the landing #pricing section + /checkout. Amounts are AUD
// and GST-inclusive (Australian consumer convention). SAMPLE pricing for the
// test deployment — final tiers/amounts are a user decision (see
// plans/auth-pricing/requirements.md).

export type BillingCycle = 'monthly' | 'yearly'
export type PlanId = 'free' | 'pro' | 'max'

export interface Plan {
  id: PlanId
  name: string
  blurb: string
  /** AUD per month, GST-inclusive. */
  monthly: number
  /** AUD per year, GST-inclusive. */
  yearly: number
  featured?: boolean
  /** Heading shown above the feature list, e.g. "Everything in Free, plus:". */
  featuresLead: string
  features: string[]
}

export const GST_RATE = 0.1 // 10% — included in the displayed price

export const PLANS: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    blurb: 'For individual research use.',
    monthly: 0,
    yearly: 0,
    featuresLead: 'Includes:',
    features: [
      'Unlimited variant searches*',
      'Full variant evidence report',
      '3 AI queries / day',
      'Community support',
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    blurb: 'For working clinicians and curators.',
    monthly: 9.95,
    yearly: 95.5,
    featured: true,
    featuresLead: 'Everything in Free, plus:',
    features: [
      '10 AI queries / day',
      'ClinVar & evidence submissions',
      'VCF upload (batch variants)',
      'Workbench — 1 active project',
      'Reclassification alerts & PDF export',
    ],
  },
  {
    id: 'max',
    name: 'Max',
    blurb: 'For power users and heavy workflows.',
    monthly: 24.95,
    yearly: 239.5,
    featuresLead: 'Everything in Pro, plus:',
    features: [
      'Unlimited AI queries*',
      'Unlimited Workbench projects*',
      'Bulk VCF uploads*',
      'Priority support & evidence refresh',
    ],
  },
]

// "Lab / Enterprise" is a contact-sales tier (no self-serve price/checkout), so
// it lives outside PLANS and renders in the "Team & Enterprise" toggle view.
export const ENTERPRISE = {
  name: 'Lab / Enterprise',
  blurb: 'For diagnostic labs, teams and groups — per-seat licensing. Contact us for a quote.',
  contact: 'mailto:sales@eamos.com.au',
  features: [
    'Shared collaborative workspace',
    'Team-wide submission ledger',
    'Per-seat licensing & SSO',
    'Priority processing & support',
  ],
}

export function getPlan(id: string | null | undefined): Plan | undefined {
  return PLANS.find((p) => p.id === id)
}

// NOTE: the yearly cycle is intentionally NOT surfaced in the UI yet (user
// decision 2026-05-24 — monthly only for now). The `yearly` fields + the
// cycle-aware helpers below are retained so it can be re-enabled without
// reworking the model. Checkout/pricing currently use `plan.monthly` directly.

/** Price for a plan + cycle (AUD, GST-inclusive). */
export function priceFor(plan: Plan, cycle: BillingCycle): number {
  return cycle === 'yearly' ? plan.yearly : plan.monthly
}

/** Per-month equivalent for display (yearly / 12). */
export function perMonth(plan: Plan, cycle: BillingCycle): number {
  return cycle === 'yearly' ? plan.yearly / 12 : plan.monthly
}

/** Whole-percent saving of yearly vs 12× monthly. */
export function yearlySavingPct(plan: Plan): number {
  if (plan.monthly === 0) return 0
  return Math.round((1 - plan.yearly / (plan.monthly * 12)) * 100)
}

/** GST component already inside a GST-inclusive amount. */
export function gstComponent(inclusive: number): number {
  return inclusive - inclusive / (1 + GST_RATE)
}

export function formatAud(amount: number): string {
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    minimumFractionDigits: amount % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(amount)
}
