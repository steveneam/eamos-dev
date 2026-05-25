import { Reveal } from '@/components/landing/Reveal'

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
      'ClinVar, gnomAD, VEP, SpliceAI, and PubMed in parallel, aggregated and deduplicated, with the ACMG rules engine on top.',
    visual: { lines: ['ClinVar … ok', 'gnomAD … ok', 'SpliceAI … ok', 'VEP … ok'] },
  },
  {
    num: 3,
    kicker: 'Instant rendering',
    title: 'Read the report',
    description:
      'A clean four-card matrix with an AI-led summary, ACMG verdict, evidence table, and trials, with every claim cited.',
    visual: { lines: ['Verdict: Likely path.', 'PM1, PM2, PP3', 'Trials: 3 recruiting'] },
  },
]

export function HowItWorks() {
  return (
    <section
      id="how"
      className="py-28"
      style={{
        background: 'var(--d-bg-2)',
        borderBottom: '0.5px solid var(--d-line)',
      }}
    >
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        <header className="mb-16" style={{ maxWidth: 720 }}>
          <p
            className="mb-3.5 text-[11px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: 'var(--em-bright)' }}
          >
            How it works
          </p>
          <h2
            className="text-[clamp(30px,3.5vw,42px)] font-semibold leading-[1.1] tracking-[-0.02em]"
            style={{ fontFamily: 'var(--display)', color: 'var(--hero-ink)' }}
          >
            One variant in. One structured report out.
          </h2>
        </header>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <Reveal key={step.num} as="article" delay={i * 0.1} className="relative flex flex-col">
              <div
                className="flex h-full flex-col"
                style={{
                  background: 'var(--d-card)',
                  border: '0.5px solid var(--d-line)',
                  borderRadius: 14,
                  padding: 28,
                }}
              >
                <div className="mb-4 flex items-center gap-3">
                  <span
                    className="inline-flex items-center justify-center"
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: 999,
                      background: step.num === 2 ? 'var(--em)' : 'var(--hero-glass2)',
                      color: step.num === 2 ? '#04140e' : 'var(--hero-ink)',
                      border: step.num === 2 ? 'none' : '0.5px solid var(--hero-line)',
                      fontFamily: 'var(--mono)',
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    {step.num}
                  </span>
                  <span
                    className="text-[10.5px] font-semibold uppercase tracking-[0.12em]"
                    style={{ color: 'var(--em-bright)' }}
                  >
                    {step.kicker}
                  </span>
                </div>
                <h3
                  className="mb-2"
                  style={{
                    fontFamily: 'var(--display)',
                    fontWeight: 600,
                    fontSize: 20,
                    lineHeight: 1.2,
                    letterSpacing: '-0.015em',
                    color: 'var(--hero-ink)',
                  }}
                >
                  {step.title}
                </h3>
                <p style={{ fontSize: 13.5, color: 'var(--hero-ink-2)', lineHeight: 1.6, margin: '0 0 18px' }}>
                  {step.description}
                </p>
                <div
                  className="mt-auto flex flex-col justify-center gap-1 overflow-hidden"
                  style={{
                    background: 'rgba(0,0,0,0.25)',
                    border: '0.5px solid var(--hero-line)',
                    borderRadius: 10,
                    padding: 14,
                    fontFamily: 'var(--mono)',
                    fontSize: 11.5,
                    color: 'var(--hero-ink-2)',
                    minHeight: 78,
                  }}
                >
                  {step.visual.lines.map((line, j) => (
                    <div
                      key={j}
                      style={{ color: j === step.visual.lines.length - 1 ? 'var(--em-bright)' : undefined }}
                    >
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
