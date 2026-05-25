'use client'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { getPlan, gstComponent, formatAud } from '@/lib/plans'

/**
 * Checkout receipt — presented as a document, not a hero.
 * Warm-white surface, receipts live in the product register.
 */
export function CheckoutSuccessClient() {
  const params = useSearchParams()
  const { user } = useAuth()

  const plan = getPlan(params.get('plan'))
  const amount = Number(params.get('amount') ?? 0)
  const cycle = params.get('cycle') === 'yearly' ? 'yearly' : 'monthly'
  const order = params.get('order') ?? ''
  const methodKey = params.get('method') ?? 'card'
  const method =
    methodKey === 'apple'
      ? 'Apple Pay'
      : methodKey === 'google'
      ? 'Google Pay'
      : methodKey === 'paypal'
      ? 'PayPal'
      : 'Card'

  const gst = gstComponent(amount)
  const subtotal = amount - gst
  const now = new Date()
  const when = now.toLocaleString('en-AU', { dateStyle: 'medium', timeStyle: 'short' })

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg-soft)',
        display: 'grid',
        placeItems: 'center',
        padding: '48px 20px',
      }}
    >
      <article
        style={{
          width: '100%',
          maxWidth: 500,
        }}
      >
        {/* Document header */}
        <header className="mb-8 text-center">
          <Link
            href="/"
            aria-label="Eamos home"
            style={{
              fontFamily: 'var(--display)',
              fontSize: 20,
              fontWeight: 400,
              letterSpacing: '-0.01em',
              color: 'var(--ink)',
              textDecoration: 'none',
            }}
          >
            Eamos
          </Link>
          <p
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 10.5,
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
              color: 'var(--teal)',
              marginTop: 8,
            }}
          >
            Payment receipt
          </p>
        </header>

        <div
          style={{
            borderRadius: 'var(--r-lg)',
            background: 'var(--bg)',
            border: '0.5px solid var(--line)',
            boxShadow: 'var(--elev-1)',
            overflow: 'hidden',
          }}
        >
          {/* Plan confirmation strip */}
          <div
            style={{
              padding: '20px 28px',
              borderBottom: '0.5px solid var(--line)',
              background: 'var(--bg-tint)',
            }}
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <p
                  style={{
                    fontSize: 13.5,
                    fontWeight: 600,
                    color: 'var(--ink)',
                    margin: 0,
                  }}
                >
                  {plan ? `Eamos ${plan.name}` : 'Eamos plan'} is active.
                </p>
                <p style={{ fontSize: 13, color: 'var(--ink-3)', margin: '3px 0 0' }}>
                  Your subscription starts today.
                </p>
              </div>
              <span
                style={{
                  fontFamily: 'var(--mono)',
                  fontSize: 10.5,
                  fontWeight: 600,
                  padding: '3px 10px',
                  borderRadius: 100,
                  background: 'var(--teal-tint)',
                  color: 'var(--teal-deep)',
                  border: '0.5px solid var(--teal)',
                  whiteSpace: 'nowrap',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                Active
              </span>
            </div>
          </div>

          {/* Receipt details */}
          <div style={{ padding: '20px 28px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                <ReceiptRow label="Receipt" value={order || 'Preview'} mono />
                <ReceiptRow label="Date" value={when} />
                <ReceiptRow label="Payment method" value={method} />
                <ReceiptRow label="Account" value={user?.email ?? 'Guest'} mono />
                <ReceiptRow
                  label="Billing"
                  value={cycle === 'yearly' ? 'Yearly' : 'Monthly'}
                />
              </tbody>
            </table>
          </div>

          {/* Totals */}
          <div
            style={{
              padding: '16px 28px 20px',
              borderTop: '0.5px solid var(--line)',
              background: 'var(--bg-soft)',
            }}
          >
            <div className="flex items-center justify-between py-1.5">
              <span style={{ fontSize: 13, color: 'var(--ink-3)' }}>Amount (ex. GST)</span>
              <span style={{ fontSize: 13, fontFamily: 'var(--mono)', color: 'var(--ink)' }}>
                {formatAud(subtotal)}
              </span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span style={{ fontSize: 13, color: 'var(--ink-3)' }}>GST (10%)</span>
              <span style={{ fontSize: 13, fontFamily: 'var(--mono)', color: 'var(--ink)' }}>
                {formatAud(gst)}
              </span>
            </div>
            <div
              className="flex items-baseline justify-between"
              style={{ marginTop: 12, paddingTop: 12, borderTop: '0.5px solid var(--line)' }}
            >
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)' }}>
                Total charged
              </span>
              <span
                style={{
                  fontFamily: 'var(--mono)',
                  fontWeight: 600,
                  fontSize: 24,
                  color: 'var(--ink)',
                  letterSpacing: '-0.02em',
                }}
              >
                {formatAud(amount)}
              </span>
            </div>
          </div>

          {/* Actions */}
          <div
            style={{
              padding: '16px 28px',
              borderTop: '0.5px solid var(--line)',
              display: 'flex',
              gap: 10,
            }}
          >
            <Link
              href="/"
              style={{
                ...actionBtn,
                flex: 1,
                background: 'var(--bg-soft)',
                color: 'var(--ink-2)',
                border: '0.5px solid var(--line)',
              }}
            >
              Return home
            </Link>
            <Link
              href="/account"
              style={{
                ...actionBtn,
                flex: 1,
                background: 'var(--teal)',
                color: '#fff',
                border: '0.5px solid var(--teal)',
              }}
            >
              View account
            </Link>
          </div>
        </div>

        <p className="mt-5 text-center text-[11.5px]" style={{ color: 'var(--ink-4)' }}>
          Preview build — no real charge was made. For questions, contact{' '}
          <a
            href="mailto:support@eamos.com.au"
            style={{ color: 'var(--ink-3)', textDecoration: 'none' }}
          >
            support@eamos.com.au
          </a>
          .
        </p>
      </article>
    </div>
  )
}

function ReceiptRow({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <tr>
      <td
        style={{
          fontSize: 12.5,
          color: 'var(--ink-3)',
          paddingBottom: 8,
          width: '40%',
        }}
      >
        {label}
      </td>
      <td
        style={{
          fontSize: 12.5,
          color: 'var(--ink)',
          textAlign: 'right',
          fontFamily: mono ? 'var(--mono)' : 'var(--body)',
          paddingBottom: 8,
          maxWidth: 220,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {value}
      </td>
    </tr>
  )
}

const actionBtn: React.CSSProperties = {
  height: 42,
  borderRadius: 'var(--r-md)',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 13,
  fontWeight: 600,
  textDecoration: 'none',
}
