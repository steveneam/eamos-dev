'use client'
import { useState } from 'react'
import Link from 'next/link'
import { Reveal } from '@/components/landing/Reveal'
import { CarouselDots } from '@/components/ui/CarouselDots'
import { PLANS, ENTERPRISE, formatAud, type Plan } from '@/lib/plans'

function PricingStyles() {
  return (
    <style>{`
      /* CTA buttons/links inside pricing cards */
      .pc-cta {
        transition:
          filter var(--dur-1) var(--ease-standard),
          box-shadow var(--dur-1) var(--ease-standard),
          transform var(--dur-1) var(--ease-standard);
        outline: none;
      }
      .pc-cta:hover { filter: brightness(0.88); }
      .pc-cta:active { transform: scale(0.97); }
      .pc-cta:focus-visible {
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--em) 28%, transparent);
      }

      /* Pricing card: focus-within ring for keyboard users tabbing to the CTA */
      .pricing-card:focus-within {
        outline: none;
      }

      /* AudienceToggle inactive option hover */
      .audience-opt {
        transition:
          background var(--dur-1) var(--ease-standard),
          color var(--dur-1) var(--ease-standard);
        outline: none;
      }
      .audience-opt:not([data-active]):hover {
        background: color-mix(in oklab, var(--em) 8%, transparent) !important;
        color: var(--hero-ink) !important;
      }
      .audience-opt:focus-visible {
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--em) 22%, transparent);
      }
    `}</style>
  )
}

type Audience = 'individual' | 'team'

// Single pricing surface. Plans derive from lib/plans.ts so they stay in sync with checkout.
export function Pricing() {
  const [audience, setAudience] = useState<Audience>('individual')

  return (
    <section id="pricing" className="py-28" style={{ background: 'var(--d-bg)' }}>
      <PricingStyles />
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
          <p
            className="mx-auto mt-4 text-[14px] leading-[1.6]"
            style={{ color: 'var(--hero-ink-2)', maxWidth: 480 }}
          >
            All prices in AUD, GST inclusive. Cancel anytime.
          </p>
        </header>

        <AudienceToggle value={audience} onChange={setAudience} />

        {audience === 'individual' ? (
          <>
            <div
              id="pricing-scroller"
              className="mt-12 -mx-8 flex snap-x snap-mandatory items-stretch gap-4 overflow-x-auto px-8 pb-4 md:mx-0 md:grid md:grid-cols-3 md:gap-5 md:overflow-visible md:px-0 md:pb-0"
            >
              {PLANS.map((tier, i) => (
                <Reveal
                  key={tier.id}
                  delay={i * 0.08}
                  className="h-full w-[80vw] max-w-[320px] shrink-0 snap-center md:w-auto md:max-w-none"
                >
                  <PlanCard plan={tier} rank={i} />
                </Reveal>
              ))}
            </div>
            <CarouselDots containerId="pricing-scroller" tone="dark" className="mt-5 md:hidden" />
          </>
        ) : (
          <Reveal className="mt-12 block">
            <EnterpriseCard />
          </Reveal>
        )}

        <p className="mt-10 text-center text-[12px]" style={{ color: 'var(--hero-ink-3)' }}>
          *Usage limits apply. Prices and plans are subject to change.
        </p>
        <p className="mt-2 text-center text-[11px]" style={{ color: 'var(--hero-ink-3)' }}>
          Sample pricing for the preview deployment — final tiers to be confirmed.
        </p>
      </div>
    </section>
  )
}

/**
 * Cards are structurally differentiated by tier rather than identical-card-grid:
 *   Free  (rank 0) — compact, plain, entry presentation
 *   Pro   (rank 1) — full-height featured card, teal border, larger price display
 *   Max   (rank 2) — compact, elevated, mono price
 * All lift via box-shadow on hover (--elev-2), no translateY bloom.
 */
function PlanCard({ plan, rank }: { plan: Plan; rank: number }) {
  const isFeatured = rank === 1
  const isFree = plan.id === 'free'
  const [hovered, setHovered] = useState(false)

  return (
    <div
      className="pricing-card relative flex h-full flex-col"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setHovered(true)}
      onBlur={() => setHovered(false)}
      style={{
        // Elevation lift via token; translateY suppressed via data attribute below.
        boxShadow: hovered ? 'var(--elev-2)' : 'var(--elev-1)',
        background: isFeatured ? 'rgba(16,185,129,0.06)' : 'var(--d-card)',
        border: `0.5px solid ${isFeatured ? 'rgba(52,211,153,0.4)' : 'var(--d-line)'}`,
        borderRadius: 16,
        // Featured card has tighter visual top padding and a teal accent rule
        padding: isFeatured ? '0 0 28px' : '28px 26px',
      }}
    >
      {isFeatured && (
        <div
          style={{
            height: 3,
            borderRadius: '16px 16px 0 0',
            background: 'linear-gradient(90deg, var(--teal) 0%, var(--em-bright) 100%)',
          }}
          aria-hidden
        />
      )}

      <div style={{ padding: isFeatured ? '26px 26px 0' : 0, flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div className="mb-1">
          <h3
            style={{
              fontFamily: 'var(--display)',
              fontWeight: isFeatured ? 600 : 400,
              fontSize: isFeatured ? 20 : 18,
              color: 'var(--hero-ink)',
              letterSpacing: '-0.01em',
              margin: 0,
            }}
          >
            {plan.name}
          </h3>
          <p className="mt-1 text-[12.5px]" style={{ color: 'var(--hero-ink-3)' }}>
            {plan.blurb}
          </p>
        </div>

        <div className="mt-7 flex items-baseline gap-1.5">
          <span
            style={{
              fontFamily: 'var(--mono)',
              fontWeight: 600,
              fontSize: isFeatured ? 40 : 32,
              color: 'var(--hero-ink)',
              letterSpacing: '-0.03em',
            }}
          >
            {isFree ? formatAud(0) : formatAud(plan.monthly)}
          </span>
          {!isFree && (
            <span className="text-[12.5px]" style={{ color: 'var(--hero-ink-3)' }}>
              / mo
            </span>
          )}
        </div>
        <p className="mt-1.5 text-[11.5px]" style={{ color: 'var(--hero-ink-3)', minHeight: 16 }}>
          {isFree ? 'Free forever' : 'Billed monthly · incl. GST'}
        </p>

        {isFree ? (
          <Link href="/account" style={ctaStyle(false)} className="pc-cta mt-6">
            Get started
          </Link>
        ) : (
          <Link href={`/checkout?plan=${plan.id}`} style={ctaStyle(isFeatured)} className="pc-cta mt-6">
            Choose {plan.name}
          </Link>
        )}

        <div
          className="mt-8 pt-6"
          style={{ borderTop: '0.5px solid var(--hero-line)', flex: 1 }}
        >
          <p
            className="mb-4 text-[11px] font-semibold uppercase tracking-[0.08em]"
            style={{ color: 'var(--hero-ink-3)' }}
          >
            {plan.featuresLead}
          </p>
          <ul
            className="flex flex-col gap-3"
            style={{ listStyle: 'none', margin: 0, padding: 0 }}
          >
            {plan.features.map((f) => (
              <li
                key={f}
                className="flex items-start gap-2.5 text-[13px]"
                style={{ color: 'var(--hero-ink-2)' }}
              >
                <CheckMark />
                {f}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}

function AudienceToggle({
  value,
  onChange,
}: {
  value: Audience
  onChange: (a: Audience) => void
}) {
  const options: [Audience, string][] = [
    ['individual', 'Individual'],
    ['team', 'Team and Enterprise'],
  ]
  return (
    <div className="flex items-center justify-center">
      <div
        className="inline-flex items-center gap-1"
        style={{
          padding: 4,
          borderRadius: 999,
          background: 'var(--hero-glass)',
          border: '0.5px solid var(--hero-line)',
        }}
      >
        {options.map(([key, label]) => {
          const active = value === key
          return (
            <button
              key={key}
              type="button"
              onClick={() => onChange(key)}
              data-active={active ? '' : undefined}
              className="audience-opt"
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
        <div className="mb-1">
          <h3
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 400,
              fontSize: 18,
              color: 'var(--hero-ink)',
              letterSpacing: '-0.01em',
              margin: 0,
            }}
          >
            {ENTERPRISE.name}
          </h3>
          <p className="mt-1 text-[12.5px]" style={{ color: 'var(--hero-ink-3)' }}>
            {ENTERPRISE.blurb}
          </p>
        </div>

        <div className="mt-7 flex items-baseline gap-1.5">
          <span
            style={{
              fontFamily: 'var(--mono)',
              fontWeight: 600,
              fontSize: 32,
              color: 'var(--hero-ink)',
              letterSpacing: '-0.03em',
            }}
          >
            Custom
          </span>
          <span className="text-[12.5px]" style={{ color: 'var(--hero-ink-3)' }}>
            pricing
          </span>
        </div>
        <p className="mt-1.5 text-[11.5px]" style={{ color: 'var(--hero-ink-3)' }}>
          Per-seat, tailored to your team
        </p>

        <a href={ENTERPRISE.contact} style={ctaStyle(true)} className="pc-cta mt-6">
          Contact sales
        </a>

        <div
          className="mt-8 pt-6"
          style={{ borderTop: '0.5px solid var(--hero-line)' }}
        >
          <p
            className="mb-4 text-[11px] font-semibold uppercase tracking-[0.08em]"
            style={{ color: 'var(--hero-ink-3)' }}
          >
            Includes:
          </p>
          <ul
            className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2"
            style={{ listStyle: 'none', margin: 0, padding: 0 }}
          >
            {ENTERPRISE.features.map((f) => (
              <li
                key={f}
                className="flex items-start gap-2.5 text-[13px]"
                style={{ color: 'var(--hero-ink-2)' }}
              >
                <CheckMark />
                {f}
              </li>
            ))}
          </ul>
        </div>
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
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--em-bright)"
      strokeWidth={2.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      style={{ marginTop: 2, flexShrink: 0 }}
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}
