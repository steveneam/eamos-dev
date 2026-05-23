import { type ReactNode } from 'react'
import { Reveal } from '@/components/landing/Reveal'

interface Feature {
  icon: ReactNode
  title: string
  description: string
}

const FEATURES: Feature[] = [
  {
    icon: <GridIcon />,
    title: 'Four-card evidence matrix',
    description:
      'Population, splicing, functional, and consensus — the four pillars of evidence mapped cleanly above the fold, no nested tabs to dig through.',
  },
  {
    icon: <SparkIcon />,
    title: 'Cognitive summary generator',
    description:
      'An immediate, conversational AI paragraph explains the biological verdict right below the matrix — with inline citations to every source.',
  },
  {
    icon: <ShieldIcon />,
    title: 'Zero-trust aggregation',
    description:
      'Records are pulled live, per query, over secure requests. No identifiable patient sequence files are ever stored on the platform.',
  },
  {
    icon: <SendIcon />,
    title: 'Pass-through ClinVar messenger',
    description:
      'Found a new functional assay? Wire it straight to ClinVar from your dashboard — no wrestling with complex federal submission forms.',
  },
]

export function FeaturesGrid() {
  return (
    <section id="features" className="py-28" style={{ background: 'var(--d-bg)' }}>
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        <header className="mb-16" style={{ maxWidth: 720 }}>
          <p
            className="mb-3.5 text-[11px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: 'var(--em-bright)' }}
          >
            Why Eamos
          </p>
          <h2
            className="mb-4 text-[clamp(30px,3.5vw,42px)] font-semibold leading-[1.1] tracking-[-0.02em]"
            style={{ fontFamily: 'var(--display)', color: 'var(--hero-ink)' }}
          >
            Built for the actual variant-interpretation workflow.
          </h2>
          <p className="text-[17px] leading-[1.55]" style={{ color: 'var(--hero-ink-2)', maxWidth: 620 }}>
            Eamos folds the databases you already open into one structured, cited, ACMG-aware report —
            engineered for speed and clinical trust.
          </p>
        </header>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          {FEATURES.map((feat, i) => (
            <Reveal key={feat.title} as="article" delay={(i % 2) * 0.1}>
              <div
                className="flex h-full gap-4 transition-colors"
                style={{
                  background: 'var(--d-card)',
                  border: '0.5px solid var(--d-line)',
                  borderRadius: 14,
                  padding: '28px 30px',
                }}
              >
                <span
                  className="inline-flex shrink-0 items-center justify-center"
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 11,
                    background: 'rgba(16,185,129,0.12)',
                    border: '0.5px solid var(--hero-line)',
                    color: 'var(--em-bright)',
                  }}
                >
                  {feat.icon}
                </span>
                <div>
                  <h3
                    className="mb-1.5"
                    style={{
                      fontFamily: 'var(--display)',
                      fontWeight: 600,
                      fontSize: 18,
                      lineHeight: 1.25,
                      letterSpacing: '-0.015em',
                      color: 'var(--hero-ink)',
                    }}
                  >
                    {feat.title}
                  </h3>
                  <p style={{ fontSize: 13.5, color: 'var(--hero-ink-2)', lineHeight: 1.6, margin: 0 }}>
                    {feat.description}
                  </p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function iconProps() {
  return {
    width: 19,
    height: 19,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
  }
}

function GridIcon() {
  return (
    <svg {...iconProps()}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  )
}

function SparkIcon() {
  return (
    <svg {...iconProps()}>
      <path d="M12 2 L13.5 8.5 L20 10 L13.5 11.5 L12 18 L10.5 11.5 L4 10 L10.5 8.5 Z" />
    </svg>
  )
}

function ShieldIcon() {
  return (
    <svg {...iconProps()}>
      <path d="M12 3 L20 6 V11 C20 16 16.5 19.5 12 21 C7.5 19.5 4 16 4 11 V6 Z" />
      <path d="M9 12 l2 2 l4 -4" />
    </svg>
  )
}

function SendIcon() {
  return (
    <svg {...iconProps()}>
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  )
}
