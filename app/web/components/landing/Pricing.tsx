import { Reveal } from '@/components/landing/Reveal'
import { PLANS, formatAud } from '@/lib/plans'

// Landing teaser — derives from the same lib/plans.ts source as /pricing so the
// numbers never drift. Full toggle/checkout lives on /pricing.
export function Pricing() {
  return (
    <section id="pricing" className="py-28" style={{ background: 'var(--d-bg)' }}>
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        <header className="mb-14 text-center">
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
        </header>

        <div className="grid grid-cols-1 items-stretch gap-5 md:grid-cols-3">
          {PLANS.map((tier, i) => {
            const isFree = tier.monthly === 0
            return (
              <Reveal key={tier.id} delay={i * 0.08} className="h-full">
                <div
                  className="pricing-card relative flex h-full flex-col"
                  style={{
                    background: tier.featured ? 'rgba(16,185,129,0.10)' : 'var(--d-card)',
                    border: `0.5px solid ${tier.featured ? 'rgba(52,211,153,0.45)' : 'var(--d-line)'}`,
                    borderRadius: 16,
                    padding: '30px 28px',
                  }}
                >
                  {tier.featured && (
                    <span
                      className="absolute right-6 top-6 text-[10px] font-semibold uppercase tracking-[0.1em]"
                      style={{ background: 'var(--em)', color: '#04140e', padding: '4px 9px', borderRadius: 100 }}
                    >
                      Most popular
                    </span>
                  )}
                  <h3
                    style={{
                      fontFamily: 'var(--display)',
                      fontWeight: 600,
                      fontSize: 18,
                      color: 'var(--hero-ink)',
                      letterSpacing: '-0.01em',
                    }}
                  >
                    {tier.name}
                  </h3>
                  <p className="mt-1 text-[12.5px]" style={{ color: 'var(--hero-ink-3)' }}>
                    {tier.blurb}
                  </p>
                  <div className="mt-5 flex items-baseline gap-1.5">
                    <span
                      style={{
                        fontFamily: 'var(--display)',
                        fontWeight: 700,
                        fontSize: 36,
                        color: 'var(--hero-ink)',
                        letterSpacing: '-0.02em',
                      }}
                    >
                      {formatAud(tier.monthly)}
                    </span>
                    <span className="text-[12.5px]" style={{ color: 'var(--hero-ink-3)' }}>
                      {isFree ? 'forever free' : 'per month'}
                    </span>
                  </div>

                  <a
                    href="/pricing"
                    className="mt-6 inline-flex items-center justify-center text-[13px] font-semibold transition-colors"
                    style={{
                      height: 42,
                      borderRadius: 10,
                      textDecoration: 'none',
                      background: tier.featured ? 'var(--em)' : 'var(--hero-glass2)',
                      color: tier.featured ? '#04140e' : 'var(--hero-ink)',
                      border: `0.5px solid ${tier.featured ? 'var(--em)' : 'var(--hero-line)'}`,
                    }}
                  >
                    {isFree ? 'Get started' : 'Choose plan'}
                  </a>

                  <ul className="mt-7 flex flex-col gap-3" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                    {tier.features.map((f) => (
                      <li key={f} className="flex items-start gap-2.5 text-[13px]" style={{ color: 'var(--hero-ink-2)' }}>
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
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              </Reveal>
            )
          })}
        </div>
        <p className="mt-8 text-center text-[11px]" style={{ color: 'var(--hero-ink-3)' }}>
          *Usage limits apply. Sample pricing — not final.
        </p>
      </div>
    </section>
  )
}
