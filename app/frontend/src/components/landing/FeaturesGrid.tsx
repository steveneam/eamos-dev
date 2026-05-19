interface Feature {
  name: string
  type: string
  title: string
  description: string
  metaKey?: string
  metaValue?: string
}

const FEATURES: Feature[] = [
  {
    name: 'aggregate',
    type: 'core',
    title: 'One search, five databases',
    description: 'Aggregates ClinVar, gnomAD, VEP, SpliceAI, and PubMed in a single structured report.',
    metaKey: 'Sources',
    metaValue: '5 live',
  },
  {
    name: 'classify',
    type: 'rules',
    title: 'ACMG-aligned classification',
    description: 'Applies PM1, PM2, PP3 and friends — every criterion shown with its underlying evidence.',
    metaKey: 'Criteria',
    metaValue: 'ACMG/AMP',
  },
  {
    name: 'summarise',
    type: 'AI',
    title: 'AI narrative summary',
    description: 'Synthesises sources into a plain-language clinical summary, with inline citations to each source.',
    metaKey: 'Model',
    metaValue: 'claude-sonnet-4',
  },
  {
    name: 'decode',
    type: 'parser',
    title: 'Variant decoder',
    description: 'Translates HGVS into the amino-acid change, codon, and protein-domain context.',
    metaKey: 'Input',
    metaValue: 'HGVS · rsID',
  },
  {
    name: 'trials',
    type: 'feed',
    title: 'Trial & therapy finder',
    description: 'Pulls active ClinicalTrials.gov studies and FDA-approved therapies for the gene under review.',
    metaKey: 'Source',
    metaValue: 'CT.gov',
  },
  {
    name: 'cite',
    type: 'audit',
    title: 'Cite-as-you-go',
    description: 'Every claim is anchored to its source row — never wonder where a number came from.',
    metaKey: 'Trace',
    metaValue: '100%',
  },
]

export function FeaturesGrid() {
  return (
    <section id="features" className="py-24">
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        <header className="mb-14" style={{ maxWidth: 720 }}>
          <p
            className="mb-3.5 text-[11px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: 'var(--teal-deep)' }}
          >
            Features
          </p>
          <h2
            className="mb-4 text-[clamp(30px,3.5vw,42px)] font-semibold leading-[1.1] tracking-[-0.02em]"
            style={{ fontFamily: 'var(--display)', color: 'var(--ink)' }}
          >
            Built for the actual variant-interpretation workflow.
          </h2>
          <p
            className="text-[17px] leading-[1.55]"
            style={{ color: 'var(--ink-3)', maxWidth: 620 }}
          >
            Eamos folds the five databases you already open into one structured, cited, ACMG-aware report.
          </p>
        </header>

        <div
          className="grid grid-cols-1 overflow-hidden md:grid-cols-2 lg:grid-cols-3"
          style={{
            gap: '1px',
            background: 'var(--line)',
            border: '0.5px solid var(--line)',
            borderRadius: 14,
          }}
        >
          {FEATURES.map((feat) => (
            <article
              key={feat.name}
              className="flex flex-col gap-3.5 transition-colors hover:bg-[var(--bg-soft)]"
              style={{ background: 'var(--bg)', padding: '32px 28px' }}
            >
              <div className="flex items-center justify-between">
                <span
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 14,
                    fontWeight: 600,
                    color: 'var(--ink)',
                    letterSpacing: '-0.01em',
                  }}
                >
                  {feat.name}
                </span>
                <span
                  className="uppercase"
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    color: 'var(--ink-4)',
                    letterSpacing: '0.1em',
                    padding: '3px 8px',
                    background: 'var(--bg-soft)',
                    border: '0.5px solid var(--line)',
                    borderRadius: 4,
                  }}
                >
                  {feat.type}
                </span>
              </div>
              <h3
                className="mt-1"
                style={{
                  fontFamily: 'var(--display)',
                  fontWeight: 600,
                  fontSize: 19,
                  lineHeight: 1.25,
                  letterSpacing: '-0.015em',
                  color: 'var(--ink)',
                }}
              >
                {feat.title}
              </h3>
              <p
                style={{
                  fontSize: 13.5,
                  color: 'var(--ink-3)',
                  lineHeight: 1.6,
                  margin: 0,
                }}
              >
                {feat.description}
              </p>
              {feat.metaKey && (
                <div
                  className="mt-auto flex flex-col gap-1 pt-3.5"
                  style={{ borderTop: '0.5px solid var(--line)' }}
                >
                  <div
                    className="flex justify-between"
                    style={{ fontSize: 11, color: 'var(--ink-4)' }}
                  >
                    <span>{feat.metaKey}</span>
                    <span
                      style={{
                        color: 'var(--ink-2)',
                        fontFamily: 'var(--mono)',
                        fontWeight: 500,
                      }}
                    >
                      {feat.metaValue}
                    </span>
                  </div>
                </div>
              )}
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
