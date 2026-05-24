'use client'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { getPlan, gstComponent, formatAud } from '@/lib/plans'

export function CheckoutSuccessClient() {
  const params = useSearchParams()
  const { user } = useAuth()

  const plan = getPlan(params.get('plan'))
  const amount = Number(params.get('amount') ?? 0)
  const cycle = params.get('cycle') === 'yearly' ? 'yearly' : 'monthly'
  const order = params.get('order') ?? '—'
  const methodKey = params.get('method') ?? 'card'
  const method =
    methodKey === 'apple' ? 'Apple Pay' : methodKey === 'google' ? 'Google Pay' : methodKey === 'paypal' ? 'PayPal' : 'Card'

  const gst = gstComponent(amount)
  const subtotal = amount - gst
  const now = new Date()
  const when = now.toLocaleString('en-AU', { dateStyle: 'medium', timeStyle: 'short' })

  return (
    <div style={{ background: 'var(--d-bg)', minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '48px 20px' }}>
      <div
        style={{
          width: '100%',
          maxWidth: 460,
          borderRadius: 20,
          background: 'var(--d-card)',
          border: '0.5px solid var(--d-line)',
          padding: '34px 30px',
          textAlign: 'center',
          boxShadow: '0 40px 100px -40px rgba(0,0,0,0.7)',
        }}
      >
        <div
          style={{
            width: 58,
            height: 58,
            margin: '0 auto 18px',
            borderRadius: 999,
            background: 'rgba(16,185,129,0.16)',
            border: '0.5px solid rgba(52,211,153,0.5)',
            display: 'grid',
            placeItems: 'center',
          }}
        >
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="var(--em-bright)" strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>

        <h1 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 23, color: 'var(--hero-ink)', margin: 0 }}>
          Payment successful
        </h1>
        <p className="mt-2 text-[14px]" style={{ color: 'var(--hero-ink-2)' }}>
          Thank you{plan ? ` — your ${plan.name} plan is active.` : '.'}
        </p>

        <span
          className="mt-4 inline-flex items-center gap-2"
          style={{ padding: '6px 12px', borderRadius: 100, background: 'var(--hero-glass)', border: '0.5px solid var(--hero-line)', fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--hero-ink-2)' }}
        >
          Receipt #{order}
        </span>

        <div className="mt-6 text-left" style={{ borderTop: '0.5px solid var(--hero-line)', paddingTop: 16 }}>
          <Detail label="Date" value={when} />
          <Detail label="Payment ID" value={order} mono />
          <Detail label="Payment method" value={method} />
          <Detail label="Account" value={user?.email ?? 'Guest checkout'} mono />
          <Detail label="Billing" value={cycle === 'yearly' ? 'Yearly' : 'Monthly'} />
        </div>

        <div className="mt-4" style={{ borderTop: '0.5px solid var(--hero-line)', paddingTop: 16 }}>
          <Detail label="Amount" value={formatAud(subtotal)} mono />
          <Detail label="GST (10%)" value={formatAud(gst)} mono />
          <div className="mt-2 flex items-baseline justify-between">
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--hero-ink)' }}>Total</span>
            <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 22, color: 'var(--hero-ink)' }}>
              {formatAud(amount)}
            </span>
          </div>
        </div>

        <div className="mt-7 flex items-center gap-3">
          <Link href="/" style={{ ...btn, flex: 1, background: 'var(--hero-glass)', color: 'var(--hero-ink)', border: '0.5px solid var(--hero-line)' }}>
            Return home
          </Link>
          <Link href="/account" style={{ ...btn, flex: 1, background: 'var(--em)', color: '#04140e', border: '0.5px solid var(--em)' }}>
            View account
          </Link>
        </div>
        <p className="mt-4 text-[11px]" style={{ color: 'var(--hero-ink-3)' }}>
          Preview build — no real charge was made.
        </p>
      </div>
    </div>
  )
}

function Detail({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span style={{ fontSize: 12.5, color: 'var(--hero-ink-3)' }}>{label}</span>
      <span
        className="truncate text-right"
        style={{ fontSize: 12.5, color: 'var(--hero-ink)', fontFamily: mono ? 'var(--mono)' : 'var(--body)', maxWidth: '60%' }}
      >
        {value}
      </span>
    </div>
  )
}

const btn: React.CSSProperties = {
  height: 44,
  borderRadius: 10,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 13,
  fontWeight: 600,
  textDecoration: 'none',
}
