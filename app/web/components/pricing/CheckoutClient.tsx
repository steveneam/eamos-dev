'use client'
import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { PageHeader } from '@/components/pricing/PageHeader'
import { useAuth } from '@/components/auth/AuthProvider'
import { getPlan, gstComponent, formatAud } from '@/lib/plans'

function CheckoutStyles() {
  return (
    <style>{`
      .cc-promo-input {
        flex: 1;
        height: 38px;
        padding: 0 12px;
        border-radius: var(--r-md);
        background: var(--bg-soft);
        color: var(--ink);
        font-size: 13px;
        outline: none;
        transition: border-color var(--dur-1) var(--ease-standard),
                    box-shadow var(--dur-1) var(--ease-standard);
      }
      .cc-promo-input:focus-visible,
      .cc-promo-input:focus {
        border-color: var(--teal);
        box-shadow: 0 0 0 3px rgba(29,158,117,0.12);
        outline: none;
      }
      .cc-promo-input[data-invalid] {
        border-color: var(--err);
      }
      .cc-promo-input[data-invalid]:focus-visible,
      .cc-promo-input[data-invalid]:focus {
        border-color: var(--err);
        box-shadow: 0 0 0 3px rgba(184,43,43,0.10);
      }

      .cc-apply-btn {
        height: 38px;
        padding: 0 14px;
        border-radius: var(--r-md);
        background: var(--teal);
        border: none;
        color: #fff;
        font-size: 12.5px;
        font-weight: 600;
        cursor: pointer;
        transition: background var(--dur-1) var(--ease-standard),
                    opacity var(--dur-1) var(--ease-standard),
                    transform var(--dur-1) var(--ease-standard);
      }
      .cc-apply-btn:hover:not(:disabled) { background: var(--teal-deep); }
      .cc-apply-btn:active:not(:disabled) { transform: translateY(1px); }
      .cc-apply-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.25);
      }
      .cc-apply-btn:disabled { opacity: 0.45; cursor: not-allowed; }

      .cc-continue-btn {
        height: 48px;
        border-radius: var(--r-md);
        border: none;
        background: var(--teal);
        color: #fff;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: background var(--dur-1) var(--ease-standard),
                    box-shadow var(--dur-1) var(--ease-standard),
                    transform var(--dur-1) var(--ease-standard);
        width: 100%;
      }
      .cc-continue-btn:hover:not(:disabled) { background: var(--teal-deep); }
      .cc-continue-btn:active:not(:disabled) { transform: translateY(1px); }
      .cc-continue-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.25);
      }
      .cc-continue-btn:disabled { opacity: 0.65; cursor: not-allowed; }
    `}</style>
  )
}

// Mock promo codes for the preview build.
const PROMO_CODES: Record<string, number> = {
  LAUNCH10: 0.10,
  TRIAL20:  0.20,
}

export function CheckoutClient() {
  const params = useSearchParams()
  const router = useRouter()
  const { user } = useAuth()

  const plan = getPlan(params.get('plan'))
  const [promo, setPromo] = useState('')
  const [discount, setDiscount] = useState<number>(0)
  const [promoStatus, setPromoStatus] = useState<'idle' | 'valid' | 'invalid'>('idle')
  const [busy, setBusy] = useState(false)

  const totals = useMemo(() => {
    if (!plan) return null
    const base = plan.monthly
    const discountAmount = base * discount
    const total = base - discountAmount
    const gst = gstComponent(total)
    const subtotal = total - gst
    return { base, discountAmount, total, gst, subtotal }
  }, [plan, discount])

  const applyPromo = () => {
    const code = promo.trim().toUpperCase()
    const rate = PROMO_CODES[code]
    if (rate !== undefined) {
      setDiscount(rate)
      setPromoStatus('valid')
    } else {
      setDiscount(0)
      setPromoStatus('invalid')
    }
  }

  if (!plan || !totals) {
    return (
      <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
        <PageHeader tone="light" />
        <main
          className="mx-auto px-6 py-28 text-center"
          style={{ maxWidth: 520 }}
        >
          <h1
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 400,
              fontSize: 26,
              color: 'var(--ink)',
              letterSpacing: '-0.02em',
            }}
          >
            Choose a plan first
          </h1>
          <p className="mt-3" style={{ fontSize: 14, color: 'var(--ink-3)' }}>
            Pick a plan and we'll bring you to checkout.
          </p>
          <Link
            href="/#pricing"
            className="mt-6 inline-flex"
            style={primaryLink}
          >
            View pricing
          </Link>
        </main>
      </div>
    )
  }

  const subscribe = () => {
    if (busy) return
    setBusy(true)
    const order = `EAM-${Date.now().toString(36).toUpperCase()}`
    const q = new URLSearchParams({
      plan: plan.id,
      amount: String(totals.total),
      order,
    })
    // Reset busy if navigation is cancelled or fails
    router.push(`/checkout/success?${q.toString()}`)
    // Fallback reset so the button is not stuck if the user navigates back
    setTimeout(() => setBusy(false), 8000)
  }

  return (
    <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
      <CheckoutStyles />
      <PageHeader tone="light" />

      <main className="mx-auto px-6 pb-28 pt-12" style={{ maxWidth: 1000 }}>
        <Link
          href="/#pricing"
          className="mb-8 inline-flex items-center gap-1.5 text-[13px] font-semibold"
          style={{ color: 'var(--ink-3)', textDecoration: 'none' }}
        >
          Back to plans
        </Link>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1.15fr]">
          {/* LEFT — order manifest */}
          <section
            style={{
              borderRadius: 'var(--r-lg)',
              padding: '28px 26px',
              background: 'var(--bg)',
              border: '0.5px solid var(--line)',
              boxShadow: 'var(--elev-1)',
            }}
          >
            <h2
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 10.5,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.12em',
                color: 'var(--ink-4)',
                margin: 0,
              }}
            >
              Order summary
            </h2>

            <div className="mt-5">
              <p
                style={{
                  fontFamily: 'var(--display)',
                  fontWeight: 400,
                  fontSize: 20,
                  color: 'var(--ink)',
                  letterSpacing: '-0.01em',
                  margin: 0,
                }}
              >
                Eamos {plan.name}
              </p>
              <p className="mt-1 text-[12.5px]" style={{ color: 'var(--ink-3)' }}>
                {plan.blurb}
              </p>
              <span
                className="mt-2 inline-block text-[11px] font-semibold uppercase tracking-[0.08em]"
                style={{
                  padding: '3px 9px',
                  borderRadius: 100,
                  background: 'var(--bg-soft)',
                  color: 'var(--ink-3)',
                  border: '0.5px solid var(--line)',
                }}
              >
                Monthly
              </span>
            </div>

            {/* promo code — wired */}
            <div className="mt-6">
              <label
                htmlFor="promo-input"
                style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--ink-2)' }}
              >
                Promo code
              </label>
              <div className="mt-1.5 flex gap-2">
                <input
                  id="promo-input"
                  value={promo}
                  onChange={(e) => {
                    setPromo(e.target.value)
                    if (promoStatus !== 'idle') setPromoStatus('idle')
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && applyPromo()}
                  placeholder="Have a code?"
                  aria-label="Promo code"
                  aria-describedby="promo-status"
                  aria-invalid={promoStatus === 'invalid' ? true : undefined}
                  className="cc-promo-input"
                  data-invalid={promoStatus === 'invalid' ? '' : undefined}
                  style={{
                    border: `0.5px solid ${promoStatus === 'invalid' ? 'var(--err)' : 'var(--line-2)'}`,
                  }}
                />
                <button
                  type="button"
                  onClick={applyPromo}
                  disabled={!promo.trim()}
                  className="cc-apply-btn"
                >
                  Apply
                </button>
              </div>
              <div id="promo-status" aria-live="polite" aria-atomic="true">
                {promoStatus === 'valid' && (
                  <p style={{ fontSize: 12, color: 'var(--teal-deep)', marginTop: 6 }}>
                    Code applied — {Math.round(discount * 100)}% off.
                  </p>
                )}
                {promoStatus === 'invalid' && (
                  <p style={{ fontSize: 12, color: 'var(--err)', marginTop: 6 }}>
                    That code is not valid.
                  </p>
                )}
              </div>
            </div>

            <div className="my-5 hairline-b" />

            <ManifestRow label="Subtotal (ex. GST)" value={formatAud(totals.subtotal)} />
            {totals.discountAmount > 0 && (
              <ManifestRow
                label={`Promo (${Math.round(discount * 100)}%)`}
                value={`-${formatAud(totals.discountAmount)}`}
                highlight
              />
            )}
            <ManifestRow
              label="GST (10%)"
              value={formatAud(totals.gst)}
              hint="Included in the total below"
            />

            <div className="mt-4 flex items-baseline justify-between">
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)' }}>
                Total due today
              </span>
              <span
                style={{
                  fontFamily: 'var(--mono)',
                  fontWeight: 600,
                  fontSize: 26,
                  color: 'var(--ink)',
                  letterSpacing: '-0.02em',
                }}
              >
                {formatAud(totals.total)}
              </span>
            </div>
            <p className="mt-1.5 text-[11px]" style={{ color: 'var(--ink-4)' }}>
              Auto-renews monthly. Cancel anytime before renewal.
            </p>
          </section>

          {/* RIGHT — payment + trust */}
          <section
            style={{
              borderRadius: 'var(--r-lg)',
              padding: '28px 26px',
              background: 'var(--bg)',
              border: '0.5px solid var(--line)',
              boxShadow: 'var(--elev-1)',
            }}
          >
            <h2
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 10.5,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.12em',
                color: 'var(--ink-4)',
                margin: 0,
              }}
            >
              Payment
            </h2>

            {!user && (
              <p className="mt-4" style={infoBox}>
                You'll create or sign in to your account as part of checkout.
              </p>
            )}

            <div className="mt-5 flex flex-wrap items-center gap-2">
              {['Card', 'Apple Pay', 'Google Pay', 'Link'].map((m) => (
                <span
                  key={m}
                  style={{
                    fontSize: 11.5,
                    fontWeight: 600,
                    padding: '5px 10px',
                    borderRadius: 100,
                    background: 'var(--bg-soft)',
                    border: '0.5px solid var(--line)',
                    color: 'var(--ink-2)',
                  }}
                >
                  {m}
                </span>
              ))}
            </div>

            {/* Stripe redirect notice */}
            <div
              className="mt-4"
              style={{
                borderRadius: 'var(--r-md)',
                border: '0.5px solid var(--line)',
                padding: '18px 16px',
                background: 'var(--bg-soft)',
              }}
            >
              <div className="flex items-center gap-2">
                <LockIcon />
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>
                  Secure checkout by Stripe
                </span>
              </div>
              <p
                className="mt-2 text-[12.5px] leading-[1.55]"
                style={{ color: 'var(--ink-3)' }}
              >
                You'll be redirected to Stripe's PCI-compliant hosted checkout to pay.
                Card, Apple Pay, Google Pay and Link all supported.
              </p>
              <p className="mt-2 text-[11px]" style={{ color: 'var(--ink-4)' }}>
                Preview build — no charge is made. "Continue" shows the confirmation receipt.
              </p>
            </div>

            <button
              type="button"
              onClick={subscribe}
              disabled={busy}
              aria-busy={busy}
              className="cc-continue-btn mt-5"
            >
              {busy ? 'Redirecting…' : `Continue to checkout · ${formatAud(totals.total)}`}
            </button>
            <p className="mt-3 text-center text-[11px]" style={{ color: 'var(--ink-4)' }}>
              By subscribing you agree to our{' '}
              <Link href="/terms" style={{ color: 'var(--ink-3)', textDecoration: 'none' }}>
                Terms
              </Link>
              .
            </p>

            {/* Trust band */}
            <TrustBand />
          </section>
        </div>
      </main>
    </div>
  )
}

function TrustBand() {
  const items = [
    { icon: <LockIcon />, label: 'Stripe payments' },
    { icon: <AbnIcon />, label: 'ABN registered' },
    { icon: <RefundIcon />, label: '30-day refund' },
  ]
  return (
    <div
      className="mt-6 flex flex-wrap items-center justify-center gap-4"
      style={{
        borderTop: '0.5px solid var(--line)',
        paddingTop: 16,
      }}
    >
      {items.map((item) => (
        <div
          key={item.label}
          className="flex items-center gap-1.5"
          style={{ fontSize: 12, fontWeight: 500, color: 'var(--ink-3)' }}
        >
          {item.icon}
          {item.label}
        </div>
      ))}
    </div>
  )
}

function ManifestRow({
  label,
  value,
  hint,
  highlight,
}: {
  label: string
  value: string
  hint?: string
  highlight?: boolean
}) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <div>
        <span
          style={{
            fontSize: 13,
            color: highlight ? 'var(--teal-deep)' : 'var(--ink-3)',
          }}
        >
          {label}
        </span>
        {hint && (
          <span style={{ fontSize: 11, color: 'var(--ink-4)', display: 'block' }}>
            {hint}
          </span>
        )}
      </div>
      <span
        style={{
          fontSize: 13,
          color: highlight ? 'var(--teal-deep)' : 'var(--ink)',
          fontFamily: 'var(--mono)',
          fontWeight: highlight ? 600 : 400,
        }}
      >
        {value}
      </span>
    </div>
  )
}

const primaryLink: React.CSSProperties = {
  height: 44,
  padding: '0 22px',
  borderRadius: 'var(--r-md)',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'var(--teal)',
  color: '#fff',
  fontSize: 13,
  fontWeight: 600,
  textDecoration: 'none',
  display: 'inline-flex',
}

const infoBox: React.CSSProperties = {
  margin: 0,
  padding: '9px 12px',
  borderRadius: 'var(--r-md)',
  background: 'var(--bg-soft)',
  border: '0.5px solid var(--line)',
  color: 'var(--ink-3)',
  fontSize: 12.5,
  lineHeight: 1.5,
}

function LockIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--teal)"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  )
}

function AbnIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--teal)"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
    </svg>
  )
}

function RefundIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--teal)"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
    </svg>
  )
}
