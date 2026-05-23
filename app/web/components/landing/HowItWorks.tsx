interface Step {
  num: number
  title: string
  description: string
  visual: { dim?: string; accent?: string; lines: string[] }
}

const STEPS: Step[] = [
  {
    num: 1,
    title: 'Enter a variant',
    description: 'Type a gene plus HGVS, rsID, or genomic coordinate. Eamos normalises whatever you paste.',
    visual: {
      lines: ['> RPE65 c.260A>G', 'parsed: NM_000329.3', 'normalised: chr1:g.68894…'],
    },
  },
  {
    num: 2,
    title: 'Eamos queries five databases',
    description: 'In parallel: ClinVar, gnomAD, VEP, SpliceAI, PubMed. ACMG rules engine runs on top.',
    visual: {
      lines: ['ClinVar … ok', 'gnomAD … ok', 'SpliceAI … ok', 'VEP … ok'],
    },
  },
  {
    num: 3,
    title: 'Read the report',
    description: 'AI summary, ACMG verdict, evidence table, trials, and PubMed — every claim cited.',
    visual: {
      lines: ['Verdict: Likely path.', 'PM1, PM2, PP3', 'Trials: 3 recruiting'],
    },
  },
]

export function HowItWorks() {
  return (
    <section
      id="how"
      className="py-24"
      style={{
        background: 'var(--bg-soft)',
        borderTop: '0.5px solid var(--line)',
        borderBottom: '0.5px solid var(--line)',
      }}
    >
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        <header className="mb-14" style={{ maxWidth: 720 }}>
          <p
            className="mb-3.5 text-[11px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: 'var(--teal-deep)' }}
          >
            How it works
          </p>
          <h2
            className="mb-4 text-[clamp(30px,3.5vw,42px)] font-semibold leading-[1.1] tracking-[-0.02em]"
            style={{ fontFamily: 'var(--display)', color: 'var(--ink)' }}
          >
            One variant in. One structured report out.
          </h2>
        </header>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {STEPS.map((step) => (
            <article
              key={step.num}
              className="relative"
              style={{
                background: 'var(--bg)',
                border: '0.5px solid var(--line)',
                borderRadius: 14,
                padding: 28,
              }}
            >
              <span
                className="mb-4 inline-flex items-center justify-center text-white"
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 999,
                  background: step.num === 2 ? 'var(--teal)' : 'var(--ink-2)',
                  fontFamily: 'var(--mono)',
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                {step.num}
              </span>
              <h3
                className="mb-2"
                style={{
                  fontFamily: 'var(--display)',
                  fontWeight: 600,
                  fontSize: 20,
                  lineHeight: 1.2,
                  letterSpacing: '-0.015em',
                  color: 'var(--ink)',
                }}
              >
                {step.title}
              </h3>
              <p
                className="mb-4"
                style={{
                  fontSize: 13.5,
                  color: 'var(--ink-3)',
                  lineHeight: 1.6,
                  margin: '0 0 18px',
                }}
              >
                {step.description}
              </p>
              <div
                className="flex flex-col justify-center gap-1 overflow-hidden"
                style={{
                  background: 'var(--bg-soft)',
                  border: '0.5px solid var(--line)',
                  borderRadius: 10,
                  padding: 14,
                  fontFamily: 'var(--mono)',
                  fontSize: 11.5,
                  color: 'var(--ink-2)',
                  minHeight: 78,
                }}
              >
                {step.visual.lines.map((line, i) => (
                  <div
                    key={i}
                    style={{
                      color: i === step.visual.lines.length - 1 ? 'var(--teal-deep)' : undefined,
                    }}
                  >
                    {line}
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
