import { Reveal } from '@/components/landing/Reveal'
import { LandingH2, LandingH3 } from '@/components/landing/ui/LandingHeading'
import { LandingEyebrow } from '@/components/landing/ui/LandingEyebrow'

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
      'Type a gene plus HGVS, rsID, or genomic coordinate. Eamos resolves supported formats into one reviewable query.',
    visual: { lines: ['> USH2A c.2276G>T', 'parsed: NM_206933.4', 'normalised: 1-216247118-C-A'] },
  },
  {
    num: 2,
    kicker: 'Evidence engine',
    title: 'Assemble the evidence stack',
    description:
      'Eamos checks the clinical sources and 11 in-silico predictors wired for the resolved variant, then evaluates returned evidence through a named, version-pinned ACMG/AMP rules layer. Missing results remain unavailable, not inferred.',
    visual: {
      lines: [
        'ClinVar · gnomAD · Ensembl',
        'REVEL · AlphaMissense · ESM1b',
        'SpliceAI · CI-SpliceAI · Pangolin',
        'CADD · CAPICE · GPN-MSA',
        'PrimateAI-3D · MetaLR · PubMed',
      ],
    },
  },
  {
    num: 3,
    kicker: 'Sourced report',
    title: 'Inspect the report',
    description:
      'Review clinical evidence, predictor scores, ACMG/AMP criteria, literature, and trial discovery links with provenance and release status attached, then carry the variant into Workbench or Batch.',
    visual: { lines: ['Scores: source-labelled', 'Criteria: version-pinned', 'Next: Workbench or Batch'] },
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
            <LandingH2>One query. A versioned evidence stack.</LandingH2>
          </div>
          <p
            className="md:max-w-[300px] md:text-right"
            style={{ fontSize: 12.5, color: 'var(--hero-ink-3)', letterSpacing: '0.01em' }}
          >
            Sources, predictors, and criteria stay inspectable from query to report.
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
                        color: isFeatured ? 'var(--em-ink)' : 'var(--em-bright)',
                        border: isFeatured ? 'none' : '0.5px solid var(--hero-line)',
                        fontFamily: 'var(--mono)',
                        fontSize: isFeatured ? 13 : 11,
                        fontWeight: 600,
                      }}
                    >
                      {String(step.num).padStart(2, '0')}
                    </span>
                    <LandingEyebrow style={{ color: 'var(--em-bright)' }}>
                      {step.kicker}
                    </LandingEyebrow>
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
                      background: isFeatured ? 'var(--page-bg-deep)' : 'var(--page-bg)',
                      border: '0.5px solid var(--hero-line)',
                      borderRadius: 10,
                      padding: isFeatured ? '16px 18px' : '12px 14px',
                      fontFamily: 'var(--mono)',
                      fontSize: isFeatured ? 12 : 11,
                      color: 'var(--hero-ink)',
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

        <div
          role="note"
          aria-label="How Eamos labels evidence status"
          className="mt-10 grid gap-3 py-5 md:grid-cols-[150px_minmax(0,1fr)] md:items-start"
          style={{
            borderTop: '0.5px solid var(--page-line)',
            borderBottom: '0.5px solid var(--page-line)',
          }}
        >
          <LandingEyebrow style={{ color: 'var(--em-bright)' }}>
            Source status
          </LandingEyebrow>
          <p
            style={{
              maxWidth: '75ch',
              margin: 0,
              fontSize: 12.5,
              lineHeight: 1.65,
              color: 'var(--hero-ink-2)',
            }}
          >
            <strong style={{ color: 'var(--hero-ink)' }}>Live</strong> was retrieved for this
            request. <strong style={{ color: 'var(--hero-ink)' }}>Cached</strong> was retrieved
            earlier with provenance retained. <strong style={{ color: 'var(--hero-ink)' }}>Bundled
            demo</strong> is a tracked fixture. <strong style={{ color: 'var(--hero-ink)' }}>Unavailable</strong>{' '}
            means no source-backed value returned. None of these states changes free access.
          </p>
        </div>
      </div>
    </section>
  )
}
