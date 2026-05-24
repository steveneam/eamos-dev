'use client'
import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { PageHeader } from '@/components/pricing/PageHeader'
import { useAuth } from '@/components/auth/AuthProvider'
import { getPlan, gstComponent, formatAud } from '@/lib/plans'

export function CheckoutClient() {
  const params = useSearchParams()
  const router = useRouter()
  const { user } = useAuth()

  const plan = getPlan(params.get('plan'))
  const [promo, setPromo] = useState('')
  const [busy, setBusy] = useState(false)

  const totals = useMemo(() => {
    if (!plan) return null
    const total = plan.monthly
    const gst = gstComponent(total)
    const subtotal = total - gst
    return { total, gst, subtotal }
  }, [plan])

  if (!plan || !totals) {
    return (
      <div style={{ background: 'var(--d-bg)', minHeight: '100vh' }}>
        <PageHeader />
        <main className="mx-auto px-6 py-28 text-center" style={{ maxWidth: 520 }}>
          <h1 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 24, color: 'var(--hero-ink)' }}>
            Choose a plan first
          </h1>
          <p className="mt-3 text-[14px]" style={{ color: 'var(--hero-ink-2)' }}>
            Pick a plan and we’ll bring you to checkout.
          </p>
          <Link href="/#pricing" className="mt-6 inline-flex" style={primaryLink}>
            View pricing
          </Link>
        </main>
      </div>
    )
  }

  // Mock-first: with no Stripe keys wired, "continue" routes to the success
  // receipt with a demo order id. When Stripe lands, this instead POSTs to the
  // backend to create a hosted Checkout Session and redirects to Stripe
  // (success_url → /checkout/success, reconciled by the Stripe webhook).
  const subscribe = () => {
    setBusy(true)
    const order = `EAM-${Date.now().toString(36).toUpperCase()}`
    const q = new URLSearchParams({
      plan: plan.id,
      amount: String(totals.total),
      order,
    })
    router.push(`/checkout/success?${q.toString()}`)
  }

  return (
    <div style={{ background: 'var(--d-bg)', minHeight: '100vh' }}>
      <PageHeader />

      <main className="mx-auto px-6 pb-28 pt-12" style={{ maxWidth: 1000 }}>
        <Link href="/#pricing" className="mb-6 inline-flex items-center gap-1.5 text-[13px] font-semibold" style={{ color: 'var(--hero-ink-2)', textDecoration: 'none' }}>
          ← Back to plans
        </Link>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1.15fr]">
          {/* LEFT — order summary (gradient emerald panel) */}
          <section
            style={{
              borderRadius: 18,
              padding: '28px 26px',
              background: 'linear-gradient(165deg, var(--hero-mid) 0%, var(--hero-bot) 100%)',
              border: '0.5px solid var(--hero-line)',
            }}
          >
            <h2 className="text-[12px] font-semibold uppercase tracking-[0.12em]" style={{ color: 'var(--em-bright)' }}>
              Order summary
            </h2>

            <div className="mt-5 flex items-start justify-between gap-3">
              <div>
                <p style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 19, color: 'var(--hero-ink)' }}>
                  {plan.name}
                </p>
                <p className="mt-0.5 text-[12.5px]" style={{ color: 'var(--hero-ink-3)' }}>{plan.blurb}</p>
              </div>
              <span
                className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.08em]"
                style={{ padding: '4px 9px', borderRadius: 100, background: 'var(--hero-glass2)', color: 'var(--hero-ink-2)' }}
              >
                Monthly
              </span>
            </div>

            {/* promo */}
            <div className="mt-4">
              <label className="text-[11.5px] font-semibold" style={{ color: 'var(--hero-ink-2)' }}>Promo code</label>
              <div className="mt-1.5 flex gap-2">
                <input
                  data-tone="dark"
                  value={promo}
                  onChange={(e) => setPromo(e.target.value)}
                  placeholder="Have a code?"
                  style={{ flex: 1, height: 38, padding: '0 12px', borderRadius: 9, background: 'var(--hero-glass)', border: '0.5px solid var(--hero-line)', color: 'var(--hero-ink)', fontSize: 13, outline: 'none' }}
                />
                <button type="button" style={{ height: 38, padding: '0 14px', borderRadius: 9, background: 'var(--hero-glass2)', border: '0.5px solid var(--hero-line)', color: 'var(--hero-ink-2)', fontSize: 12.5, fontWeight: 600, cursor: 'pointer' }}>
                  Apply
                </button>
              </div>
            </div>

            <div className="my-5" style={{ height: '0.5px', background: 'var(--hero-line)' }} />

            <Row label="Subtotal" value={formatAud(totals.subtotal)} />
            <Row label="GST (10%)" value={formatAud(totals.gst)} />
            <div className="mt-3 flex items-baseline justify-between">
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--hero-ink)' }}>Total due today</span>
              <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 24, color: 'var(--hero-ink)' }}>
                {formatAud(totals.total)}
              </span>
            </div>
            <p className="mt-2 text-[11px]" style={{ color: 'var(--hero-ink-3)' }}>
              Auto-renews monthly. Cancel anytime before renewal.
            </p>
          </section>

          {/* RIGHT — payment */}
          <section
            style={{ borderRadius: 18, padding: '28px 26px', background: 'var(--d-card)', border: '0.5px solid var(--d-line)' }}
          >
            <h2 className="text-[12px] font-semibold uppercase tracking-[0.12em]" style={{ color: 'var(--em-bright)' }}>
              Payment
            </h2>

            {!user && (
              <p className="mt-4" style={infoBox}>
                You’ll create or sign in to your account as part of checkout.
              </p>
            )}

            {/* Accepted methods (display) — entry happens on Stripe's hosted page */}
            <div className="mt-5 flex flex-wrap items-center gap-2">
              {['Card', 'Apple Pay', 'Google Pay', 'Link'].map((m) => (
                <span
                  key={m}
                  style={{
                    fontSize: 11.5,
                    fontWeight: 600,
                    padding: '6px 11px',
                    borderRadius: 100,
                    background: 'var(--hero-glass)',
                    border: '0.5px solid var(--hero-line)',
                    color: 'var(--hero-ink-2)',
                  }}
                >
                  {m}
                </span>
              ))}
            </div>

            {/* Hosted Stripe Checkout — we redirect; Stripe owns the card form */}
            <div
              className="mt-4"
              style={{ borderRadius: 12, border: '0.5px dashed var(--hero-line)', padding: '22px 18px', background: 'var(--hero-glass)' }}
            >
              <div className="flex items-center gap-2">
                <LockIcon />
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--hero-ink)' }}>Secure checkout by Stripe</span>
              </div>
              <p className="mt-2 text-[12.5px] leading-[1.55]" style={{ color: 'var(--hero-ink-2)' }}>
                You’ll be redirected to Stripe’s PCI-compliant hosted checkout to pay — card,
                Apple&nbsp;Pay, Google&nbsp;Pay and Link are all supported there.
              </p>
              <p className="mt-2 text-[11px]" style={{ color: 'var(--hero-ink-3)' }}>
                Preview build — no charge is made. “Continue” shows the confirmation receipt.
              </p>
            </div>

            <button
              type="button"
              onClick={subscribe}
              disabled={busy}
              className="mt-5 w-full"
              style={{ height: 48, borderRadius: 12, border: 'none', background: 'var(--em)', color: '#04140e', fontSize: 14, fontWeight: 700, cursor: 'pointer', opacity: busy ? 0.7 : 1 }}
            >
              {busy ? 'Redirecting…' : `Continue to checkout · ${formatAud(totals.total)}`}
            </button>
            <p className="mt-3 text-center text-[11px]" style={{ color: 'var(--hero-ink-3)' }}>
              By subscribing you agree to our{' '}
              <Link href="/terms" style={{ color: 'var(--em-bright)', textDecoration: 'none' }}>Terms</Link>.
            </p>
          </section>
        </div>
      </main>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span style={{ fontSize: 13, color: 'var(--hero-ink-2)' }}>{label}</span>
      <span style={{ fontSize: 13, color: 'var(--hero-ink)', fontFamily: 'var(--mono)' }}>{value}</span>
    </div>
  )
}

const primaryLink: React.CSSProperties = {
  height: 44,
  padding: '0 22px',
  borderRadius: 10,
  alignItems: 'center',
  justifyContent: 'center',
  background: 'var(--em)',
  color: '#04140e',
  fontSize: 13,
  fontWeight: 600,
  textDecoration: 'none',
  display: 'inline-flex',
}

const infoBox: React.CSSProperties = {
  margin: 0,
  padding: '9px 12px',
  borderRadius: 9,
  background: 'var(--hero-glass)',
  border: '0.5px solid var(--hero-line)',
  color: 'var(--hero-ink-2)',
  fontSize: 12.5,
  lineHeight: 1.5,
}

function LockIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--em-bright)" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  )
}
