'use client'
import { useState } from 'react'
import Link from 'next/link'
import { Reveal } from '@/components/landing/Reveal'
import { PLANS, ENTERPRISE, formatAud, type Plan } from '@/lib/plans'

type Audience = 'individual' | 'team'

// Single pricing surface (the dedicated /pricing page was removed 2026-05-25 —
// user wanted one funnel: prices here → click a plan → straight to /checkout).
// Numbers derive from lib/plans.ts so they never drift from checkout.
export function Pricing() {
  const [audience, setAudience] = useState<Audience>('individual')

  return (
    <section id="pricing" className="py-28" style={{ background: 'var(--d-bg)' }}>
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        <header className="mb-10 text-center">
          <p
            className="mb-3.5 text-[11px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: 'var(--em-bright)' }}
          >
            Pricing
          </p>
          <h2
            className="mx-auto text-[clamp(30px,3.5vw,42px)] font-semibold leading-[1.1] tracking-[-0.02em]"
            style={{ fontFamily: 'var(--display)', color: 'var(--hero-ink)', maxWidth: 640 }}
          >
            Start free. Scale to the whole lab.
          </h2>
          <p className="mx-auto mt-4 text-[14px] leading-[1.6]" style={{ color: 'var(--hero-ink-2)', maxWidth: 480 }}>
            All prices in AUD, GST inclusive. Cancel anytime.
          </p>
        </header>

        <AudienceToggle value={audience} onChange={setAudience} />

        {audience === 'individual' ? (
          <>
            {/* Mobile: edge-to-edge horizontal swipe carousel (peek next card).
                md+: 3-column grid. */}
            <div className="mt-12 -mx-8 flex snap-x snap-mandatory items-stretch gap-4 overflow-x-auto px-8 pb-4 md:mx-0 md:grid md:grid-cols-3 md:gap-5 md:overflow-visible md:px-0 md:pb-0">
              {PLANS.map((tier, i) => (
                <Reveal
                  key={tier.id}
                  delay={i * 0.08}
                  className="h-full w-[80vw] max-w-[320px] shrink-0 snap-center md:w-auto md:max-w-none"
                >
                  <PlanCard plan={tier} />
                </Reveal>
              ))}
            </div>
            <p className="mt-4 text-center text-[11px] md:hidden" style={{ color: 'var(--hero-ink-3)' }}>
              Swipe to compare plans →
            </p>
          </>
        ) : (
          <Reveal className="mt-12 block">
            <EnterpriseCard />
          </Reveal>
        )}

        <p className="mt-10 text-center text-[12px]" style={{ color: 'var(--hero-ink-3)' }}>
          *Usage limits apply. Prices and plans are subject to change at Eamos’s discretion.
        </p>
        <p className="mt-2 text-center text-[11px]" style={{ color: 'var(--hero-ink-3)' }}>
          Sample pricing for the preview deployment — final tiers and amounts to be confirmed.
        </p>
      </div>
    </section>
  )
}

function PlanCard({ plan }: { plan: Plan }) {
  const isFree = plan.id === 'free'

  return (
    <div
      className="pricing-card relative flex h-full flex-col"
      style={{
        background: plan.featured ? 'rgba(16,185,129,0.10)' : 'var(--d-card)',
        border: `0.5px solid ${plan.featured ? 'rgba(52,211,153,0.45)' : 'var(--d-line)'}`,
        borderRadius: 16,
        padding: '30px 28px',
      }}
    >
      {plan.featured && (
        <span
          className="absolute right-6 top-6 text-[10px] font-semibold uppercase tracking-[0.1em]"
          style={{ background: 'var(--em)', color: '#04140e', padding: '4px 9px', borderRadius: 100 }}
        >
          Most popular
        </span>
      )}

      <div className="mb-1 flex items-center gap-2">
        <TreeMark />
        <h3 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 18, color: 'var(--hero-ink)', letterSpacing: '-0.01em' }}>
          {plan.name}
        </h3>
      </div>
      <p className="text-[12.5px]" style={{ color: 'var(--hero-ink-3)' }}>{plan.blurb}</p>

      <div className="mt-7 flex items-baseline gap-1.5">
        <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 38, color: 'var(--hero-ink)', letterSpacing: '-0.02em' }}>
          {isFree ? formatAud(0) : formatAud(plan.monthly)}
        </span>
        {!isFree && <span className="text-[12.5px]" style={{ color: 'var(--hero-ink-3)' }}>/ month</span>}
      </div>
      <p className="mt-1.5 text-[11.5px]" style={{ color: 'var(--hero-ink-3)', minHeight: 16 }}>
        {isFree ? 'Free forever' : 'Billed monthly · incl. GST'}
      </p>

      {isFree ? (
        <Link href="/account" style={ctaStyle(false)} className="mt-6">
          Get started
        </Link>
      ) : (
        <Link href={`/checkout?plan=${plan.id}`} style={ctaStyle(!!plan.featured)} className="mt-6">
          Choose {plan.name}
        </Link>
      )}

      <p
        className="mt-8 pt-7 text-[11px] font-semibold uppercase tracking-[0.08em]"
        style={{ color: 'var(--hero-ink-3)', borderTop: '0.5px solid var(--hero-line)' }}
      >
        {plan.featuresLead}
      </p>
      <ul className="mt-4 flex flex-col gap-3" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {plan.features.map((f) => (
          <li key={f} className="flex items-start gap-2.5 text-[13px]" style={{ color: 'var(--hero-ink-2)' }}>
            <CheckMark />
            {f}
          </li>
        ))}
      </ul>
    </div>
  )
}

function AudienceToggle({ value, onChange }: { value: Audience; onChange: (a: Audience) => void }) {
  const options: [Audience, string][] = [
    ['individual', 'Individual'],
    ['team', 'Team & Enterprise'],
  ]
  return (
    <div className="flex items-center justify-center">
      <div
        className="inline-flex items-center gap-1"
        style={{ padding: 4, borderRadius: 999, background: 'var(--hero-glass)', border: '0.5px solid var(--hero-line)' }}
      >
        {options.map(([key, label]) => {
          const active = value === key
          return (
            <button
              key={key}
              type="button"
              onClick={() => onChange(key)}
              className="transition-colors"
              style={{
                padding: '8px 18px',
                borderRadius: 999,
                border: 'none',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 600,
                background: active ? 'var(--em)' : 'transparent',
                color: active ? '#04140e' : 'var(--hero-ink-2)',
              }}
            >
              {label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function EnterpriseCard() {
  return (
    <div className="flex justify-center">
      <div
        className="pricing-card flex w-full flex-col"
        style={{
          maxWidth: 560,
          background: 'var(--d-card)',
          border: '0.5px solid var(--d-line)',
          borderRadius: 16,
          padding: '30px 28px',
        }}
      >
        <div className="mb-1 flex items-center gap-2">
          <TreeMark />
          <h3 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 18, color: 'var(--hero-ink)', letterSpacing: '-0.01em' }}>
            {ENTERPRISE.name}
          </h3>
        </div>
        <p className="text-[12.5px]" style={{ color: 'var(--hero-ink-3)' }}>{ENTERPRISE.blurb}</p>

        <div className="mt-7 flex items-baseline gap-1.5">
          <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 38, color: 'var(--hero-ink)', letterSpacing: '-0.02em' }}>
            Custom
          </span>
          <span className="text-[12.5px]" style={{ color: 'var(--hero-ink-3)' }}>pricing</span>
        </div>
        <p className="mt-1.5 text-[11.5px]" style={{ color: 'var(--hero-ink-3)' }}>Per-seat — tailored to your team</p>

        <a href={ENTERPRISE.contact} style={ctaStyle(true)} className="mt-6">
          Contact sales
        </a>

        <p
          className="mt-8 pt-7 text-[11px] font-semibold uppercase tracking-[0.08em]"
          style={{ color: 'var(--hero-ink-3)', borderTop: '0.5px solid var(--hero-line)' }}
        >
          Includes:
        </p>
        <ul className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {ENTERPRISE.features.map((f) => (
            <li key={f} className="flex items-start gap-2.5 text-[13px]" style={{ color: 'var(--hero-ink-2)' }}>
              <CheckMark />
              {f}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function ctaStyle(featured: boolean): React.CSSProperties {
  return {
    height: 44,
    borderRadius: 10,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    textDecoration: 'none',
    fontSize: 13,
    fontWeight: 600,
    background: featured ? 'var(--em)' : 'var(--hero-glass2)',
    color: featured ? '#04140e' : 'var(--hero-ink)',
    border: `0.5px solid ${featured ? 'var(--em)' : 'var(--hero-line)'}`,
  }
}

function CheckMark() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--em-bright)" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" aria-hidden style={{ marginTop: 2, flexShrink: 0 }}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

function TreeMark() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--em-bright)" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 22V12" />
      <path d="M12 12 7 8" />
      <path d="m12 14 5-4" />
      <circle cx="12" cy="6" r="3" />
      <circle cx="6" cy="9" r="2" />
      <circle cx="18" cy="9" r="2" />
    </svg>
  )
}
