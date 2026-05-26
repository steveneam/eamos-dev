'use client'

/**
 * Specimen strip — replaces the previous hero-metric belt (impeccable's
 * "hero-metric" ban). Instead of marketing counts (3M+ variants, 909M+ ...),
 * shows a fragment of an actual variant report: the call-card row a clinician
 * sees first. The cream landing is the journal cover; this inset is an open
 * page from inside.
 *
 * Static, mock-shape data hand-crafted to match the live `CallCardsGrid`
 * geometry (same min-height, type stack, badge tones). Real reports are loaded
 * via the backend; this is a proof, not a substitute.
 */

interface BadgeSpec {
  text: string
  tone: 'acmg' | 'metric' | 'source' | 'warning' | 'neutral'
}

interface CallSpec {
  title: string
  primary: string
  badges: BadgeSpec[]
  meta: string
}

// RPE65 c.260A>G — the demo variant Eamos uses everywhere (matches the auth-page
// specimen and the chip in the hero "Try" row).
const SPECIMEN: CallSpec[] = [
  {
    title: 'Clinical consensus',
    primary: 'Likely Pathogenic',
    badges: [
      { text: 'ACMG · PM1 PM2 PP3', tone: 'acmg' },
      { text: '6 submitters', tone: 'metric' },
    ],
    meta: 'ClinVar · Last reviewed Mar 2025',
  },
  {
    title: 'Population frequency',
    primary: 'Not observed',
    badges: [
      { text: 'gnomAD v4', tone: 'source' },
      { text: 'AC = 0', tone: 'metric' },
    ],
    meta: 'gnomAD genomes + exomes',
  },
  {
    title: 'Computational',
    primary: 'Damaging · consensus',
    badges: [
      { text: 'SpliceAI 0.94', tone: 'metric' },
      { text: 'REVEL 0.92', tone: 'metric' },
    ],
    meta: 'SpliceAI · REVEL · CADD',
  },
  {
    title: 'Functional',
    primary: 'PS3 supported',
    badges: [
      { text: 'ClinGen', tone: 'source' },
      { text: '4 studies', tone: 'metric' },
    ],
    meta: 'ClinGen · PubMed (4 PMIDs)',
  },
]

const BADGE_TONES = {
  acmg:    { bg: 'var(--teal-tint)',   border: '#cbe3d8', color: 'var(--teal-deep)' },
  metric:  { bg: 'var(--bg-soft)',     border: 'var(--line)', color: 'var(--ink-2)' },
  source:  { bg: '#eef6ff',            border: '#c9ddf5', color: '#1d4f7a' },
  warning: { bg: 'var(--warn-tint)',   border: 'var(--warn-bdr)', color: '#633806' },
  neutral: { bg: 'var(--bg-soft)',     border: 'var(--line)', color: 'var(--ink-3)' },
} as const

export function MetricBelt() {
  return (
    <section
      aria-label="A specimen of an Eamos variant report"
      className="py-24"
      style={{
        background: 'var(--d-bg)',
        borderTop: '0.5px solid var(--d-line)',
        borderBottom: '0.5px solid var(--d-line)',
      }}
    >
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        {/* Section eyebrow + headline */}
        <header className="mb-10 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div style={{ maxWidth: 560 }}>
            <p
              className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: 'var(--em-bright)' }}
            >
              A specimen
            </p>
            <h2
              className="text-[clamp(26px,3vw,36px)] leading-[1.1] tracking-[-0.02em]"
              style={{ fontFamily: 'var(--display)', fontWeight: 500, color: 'var(--hero-ink)' }}
            >
              How the evidence reads.
            </h2>
          </div>
          <p
            className="md:max-w-[380px] md:text-right"
            style={{ fontSize: 13.5, lineHeight: 1.55, color: 'var(--hero-ink-2)' }}
          >
            Four call cards at the top of every report — clinical consensus, population
            frequency, computational, functional — each citing the source it came from.
          </p>
        </header>

        {/* The "open page" — a warm-white inset, like opening a paper journal on a desk. */}
        <div
          className="overflow-hidden"
          style={{
            background: 'var(--bg)',
            border: '0.5px solid var(--line)',
            borderRadius: 14,
            boxShadow: '0 1px 0 rgba(0,0,0,0.02), 0 12px 32px -16px rgba(0,0,0,0.12)',
          }}
        >
          {/* Specimen variant header — same shape as VariantHeader, abbreviated. */}
          <div
            className="flex flex-wrap items-baseline gap-x-5 gap-y-1"
            style={{
              padding: '20px 24px 16px',
              borderBottom: '0.5px solid var(--line)',
            }}
          >
            <span
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 13,
                fontWeight: 500,
                letterSpacing: '0.01em',
                color: 'var(--ink-3)',
              }}
            >
              NM_000329.3:c.260A&gt;G
            </span>
            <span
              style={{
                fontFamily: 'var(--display)',
                fontSize: 19,
                fontWeight: 500,
                letterSpacing: '-0.01em',
                color: 'var(--ink)',
              }}
            >
              RPE65 <span style={{ color: 'var(--ink-3)', fontWeight: 400 }}>· p.Asp87Gly</span>
            </span>
            <span style={{ fontSize: 12, color: 'var(--ink-4)', fontFamily: 'var(--mono)' }}>
              chr1:68,894,505
            </span>
            <span className="ml-auto" style={{ fontSize: 11, color: 'var(--ink-4)' }}>
              Live demo · sourced
            </span>
          </div>

          {/* Four call cards — single grid; same min-height + tone as the live grid. */}
          <div className="grid grid-cols-1 gap-px sm:grid-cols-2 lg:grid-cols-4" style={{ background: 'var(--line)' }}>
            {SPECIMEN.map((card) => (
              <article
                key={card.title}
                style={{
                  background: 'var(--bg)',
                  padding: '18px 18px 20px',
                  minHeight: 168,
                }}
              >
                <div
                  className="uppercase"
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    letterSpacing: '0.08em',
                    color: 'var(--ink-4)',
                  }}
                >
                  {card.title}
                </div>
                <div
                  style={{
                    marginTop: 10,
                    fontFamily: 'var(--display)',
                    fontSize: 19,
                    fontWeight: 500,
                    lineHeight: 1.18,
                    letterSpacing: '-0.01em',
                    color: 'var(--ink)',
                  }}
                >
                  {card.primary}
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {card.badges.map((b) => {
                    const tone = BADGE_TONES[b.tone]
                    return (
                      <span
                        key={b.text}
                        style={{
                          border: `0.5px solid ${tone.border}`,
                          background: tone.bg,
                          color: tone.color,
                          borderRadius: 7,
                          padding: '4px 7px',
                          fontSize: 10.5,
                          fontWeight: 700,
                          lineHeight: 1.15,
                        }}
                      >
                        {b.text}
                      </span>
                    )
                  })}
                </div>
                <div
                  style={{
                    marginTop: 12,
                    fontSize: 10.5,
                    lineHeight: 1.4,
                    color: 'var(--ink-4)',
                  }}
                >
                  {card.meta}
                </div>
              </article>
            ))}
          </div>
        </div>

        <p className="mt-5 text-[11.5px]" style={{ color: 'var(--hero-ink-3)' }}>
          Specimen rendered from RPE65 c.260A&gt;G · every value links back to its source
          (ClinVar · gnomAD v4 · SpliceAI · ClinGen · PubMed).
        </p>
      </div>
    </section>
  )
}
