import { Reveal } from '@/components/landing/Reveal'
import { LandingH2, LandingH3 } from '@/components/landing/ui/LandingHeading'

interface Step {
  num: number
  kicker: string
  title: string
  description: string
  visual: { lines: string[] }
}

const STEPS: Step[] = [
  {
    num: 1,
    kicker: 'Single query',
    title: 'Enter a variant',
    description:
      'Type a gene plus HGVS, rsID, or genomic coordinate into the zero-trust search. Eamos normalises whatever you paste.',
    visual: { lines: ['> RPE65 c.260A>G', 'parsed: NM_000329.3', 'normalised: chr1:g.68894…'] },
  },
  {
    num: 2,
    kicker: 'Parallel sweep',
    title: 'Eamos queries every source at once',
    description:
      'ClinVar, gnomAD, VEP, SpliceAI, and PubMed, fanned out in parallel, aggregated and deduplicated, with the ACMG rules engine on top.',
    visual: {
      lines: [
        'ClinVar  … ok  (12 submissions)',
        'gnomAD   … ok  (v4, exomes+genomes)',
        'SpliceAI … ok  (Δ 0.94)',
        'VEP      … ok  (CADD 32, REVEL 0.92)',
        'PubMed   … ok  (4 citations matched)',
      ],
    },
  },
  {
    num: 3,
    kicker: 'Instant rendering',
    title: 'Read the report',
    description:
      'A clean four-card matrix with an AI-led summary, ACMG verdict, evidence table, and trials; every claim cited.',
    visual: { lines: ['Verdict: Likely path.', 'PM1, PM2, PP3', 'Trials: 3 recruiting'] },
  },
]

export function HowItWorks() {
  return (
    <section
      id="how"
      className="py-28"
      style={{
        background: 'var(--page-bg-deep)',
        borderBottom: '0.5px solid var(--page-line)',
      }}
    >
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        <header className="mb-14 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div style={{ maxWidth: 720 }}>
            <LandingH2>One variant in. One structured report out.</LandingH2>
          </div>
          <p
            className="md:max-w-[300px] md:text-right"
            style={{ fontSize: 12.5, color: 'var(--hero-ink-3)', letterSpacing: '0.01em' }}
          >
            Three stations. The middle one is where the work happens.
          </p>
        </header>

        {/* Asymmetric 3 / 6 / 3 — step 2 is the featured station, twice the width
            of the bookend steps. Stacks on small screens (step 2 still first by
            visual order, not source order — preserves narrative). */}
        <div className="grid grid-cols-1 gap-px lg:grid-cols-12" style={{ background: 'var(--page-line)' }}>
          {STEPS.map((step, i) => {
            const isFeatured = step.num === 2
            const colSpan = isFeatured ? 'lg:col-span-6' : 'lg:col-span-3'
            return (
              <Reveal
                key={step.num}
                as="article"
                delay={i * 0.08}
                className={`relative flex flex-col ${colSpan}`}
              >
                <div
                  className="flex h-full flex-col"
                  style={{
                    background: isFeatured ? 'var(--page-card)' : 'var(--page-bg-deep)',
                    padding: isFeatured ? '36px 32px' : '28px 24px',
                  }}
                >
                  <div className="mb-5 flex items-center gap-3">
                    <span
                      className="inline-flex items-center justify-center"
                      style={{
                        width: isFeatured ? 34 : 26,
                        height: isFeatured ? 34 : 26,
                        borderRadius: 999,
                        background: isFeatured ? 'var(--em)' : 'transparent',
                        color: isFeatured ? '#04140e' : 'var(--em-bright)',
                        border: isFeatured ? 'none' : '0.5px solid var(--hero-line)',
                        fontFamily: 'var(--mono)',
                        fontSize: isFeatured ? 13 : 11,
                        fontWeight: 600,
                      }}
                    >
                      {String(step.num).padStart(2, '0')}
                    </span>
                    <span
                      className="text-[10.5px] font-semibold uppercase tracking-[0.12em]"
                      style={{ color: 'var(--em-bright)' }}
                    >
                      {step.kicker}
                    </span>
                  </div>
                  <LandingH3 className="mb-3">{step.title}</LandingH3>
                  <p
                    style={{
                      fontSize: isFeatured ? 14.5 : 13,
                      color: 'var(--hero-ink-2)',
                      lineHeight: 1.6,
                      margin: `0 0 ${isFeatured ? 24 : 16}px`,
                    }}
                  >
                    {step.description}
                  </p>
                  <div
                    className="mt-auto flex flex-col justify-center gap-1 overflow-hidden"
                    style={{
                      background: isFeatured ? 'rgba(0,0,0,0.32)' : 'rgba(0,0,0,0.22)',
                      border: '0.5px solid var(--hero-line)',
                      borderRadius: 10,
                      padding: isFeatured ? '16px 18px' : '12px 14px',
                      fontFamily: 'var(--mono)',
                      fontSize: isFeatured ? 12 : 11,
                      color: 'var(--hero-ink-2)',
                      minHeight: isFeatured ? 132 : 70,
                    }}
                  >
                    {step.visual.lines.map((line, j) => (
                      <div
                        key={j}
                        style={{
                          color: j === step.visual.lines.length - 1 && !isFeatured ? 'var(--em-bright)' : undefined,
                          whiteSpace: 'pre',
                        }}
                      >
                        {line}
                      </div>
                    ))}
                  </div>
                </div>
              </Reveal>
            )
          })}
        </div>
      </div>
    </section>
  )
}
