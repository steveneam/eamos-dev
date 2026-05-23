import { Reveal } from '@/components/landing/Reveal'

interface Tier {
  name: string
  price: string
  cadence: string
  blurb: string
  features: string[]
  featured?: boolean
}

const TIERS: Tier[] = [
  {
    name: 'Researcher',
    price: '$0',
    cadence: 'forever free',
    blurb: 'For individual research use.',
    features: ['Single variant search', 'Four-card master grid', 'ClinVar messenger', '10 queries / minute'],
  },
  {
    name: 'Professional',
    price: '$49',
    cadence: 'per user / month',
    blurb: 'For working clinicians and curators.',
    features: ['No speed throttling', 'Active alert queues', 'One-click PDF report export', 'Priority support'],
    featured: true,
  },
  {
    name: 'Clinical Lab',
    price: '$199',
    cadence: 'per team / month',
    blurb: 'For diagnostic labs and groups.',
    features: ['Shared collaborative workspace', 'Team-wide submission logs', 'Custom internal lab badges', 'Priority processing'],
  },
]

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
          {TIERS.map((tier, i) => (
            <Reveal key={tier.name} delay={i * 0.08} className="h-full">
              <div
                className="relative flex h-full flex-col"
                style={{
                  background: tier.featured ? 'rgba(16,185,129,0.10)' : 'var(--d-card)',
                  border: `0.5px solid ${tier.featured ? 'rgba(52,211,153,0.45)' : 'var(--d-line)'}`,
                  borderRadius: 16,
                  padding: '30px 28px',
                  boxShadow: tier.featured ? '0 28px 70px -34px rgba(16,185,129,0.55)' : 'none',
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
                    {tier.price}
                  </span>
                  <span className="text-[12.5px]" style={{ color: 'var(--hero-ink-3)' }}>
                    {tier.cadence}
                  </span>
                </div>

                <a
                  href="#"
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
                  {tier.price === '$0' ? 'Get started' : 'Choose plan'}
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
          ))}
        </div>
        <p className="mt-8 text-center text-[11px]" style={{ color: 'var(--hero-ink-3)' }}>
          Sample pricing — not final.
        </p>
      </div>
    </section>
  )
}
