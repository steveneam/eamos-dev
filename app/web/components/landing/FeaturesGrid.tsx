import Image from 'next/image'
import { Reveal } from '@/components/landing/Reveal'

interface Shot {
  src: string
  title: string
  caption: string
}

// Product snapshots captured from a live report. Rough first pass — replace with
// polished marketing shots later. The gnomAD world-map featured band below was
// captured from MTHFR c.665C>T (a gnomAD-present variant; the RPE65 demo isn't in gnomAD).
const SHOTS: Shot[] = [
  {
    src: '/feat-classification.webp',
    title: 'Classification at a glance',
    caption: 'ClinVar + UniProt distribution across LOF, missense, non-coding and synonymous.',
  },
  {
    src: '/feat-publications.webp',
    title: 'Cited literature, deduplicated',
    caption: 'Variant-level publication mining with snippets and a publications-over-time view.',
  },
  {
    src: '/feat-trials.webp',
    title: 'Active trials & therapies',
    caption: 'ClinicalTrials.gov discovery links, colour-coded by recruitment status.',
  },
]

export function FeaturesGrid() {
  return (
    <section id="features" className="py-28" style={{ background: 'var(--d-bg)' }}>
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        <header className="mb-14" style={{ maxWidth: 720 }}>
          <p
            className="mb-3.5 text-[11px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: 'var(--em-bright)' }}
          >
            What you get
          </p>
          <h2
            className="mb-4 text-[clamp(30px,3.5vw,42px)] font-semibold leading-[1.1] tracking-[-0.02em]"
            style={{ fontFamily: 'var(--display)', color: 'var(--hero-ink)' }}
          >
            One lookup. The whole evidence picture.
          </h2>
          <p className="text-[17px] leading-[1.55]" style={{ color: 'var(--hero-ink-2)', maxWidth: 620 }}>
            Every report folds the databases you already open into one structured, cited, ACMG-aware
            view — engineered for speed and clinical trust.
          </p>
        </header>

        {/* Featured: the four evidence call cards */}
        <Reveal as="article">
          <figure
            className="m-0 overflow-hidden"
            style={{ background: 'var(--d-card)', border: '0.5px solid var(--d-line)', borderRadius: 16 }}
          >
            <div
              className="relative"
              style={{ aspectRatio: '1280 / 300', overflow: 'hidden', background: 'var(--d-bg-2)' }}
            >
              <Image
                src="/feat-report-cards.webp"
                alt="Variant evidence report — four-card matrix: population, computational, functional and clinical consensus"
                fill
                sizes="(max-width: 1180px) 100vw, 1180px"
                style={{ objectFit: 'cover', objectPosition: 'top center' }}
              />
            </div>
            <figcaption style={{ padding: '20px 24px' }}>
              <h3 className="mb-1" style={feat.title}>
                Four-card evidence matrix
              </h3>
              <p style={feat.caption}>
                Population, computational, functional and clinical consensus — the four pillars, mapped
                above the fold with no nested tabs to dig through.
              </p>
            </figcaption>
          </figure>
        </Reveal>

        {/* Featured: gnomAD population-frequency world map (captured from MTHFR c.665C>T) */}
        <Reveal as="article">
          <figure
            className="m-0 overflow-hidden"
            style={{ marginTop: 20, background: 'var(--d-card)', border: '0.5px solid var(--d-line)', borderRadius: 16 }}
          >
            <div
              className="relative"
              style={{ aspectRatio: '7 / 3', overflow: 'hidden', background: 'var(--d-bg-2)' }}
            >
              <Image
                src="/feat-gnomad-map.webp"
                alt="gnomAD v4 allele frequencies across genetic ancestry groups, rendered on a land-clipped world map"
                fill
                sizes="(max-width: 1180px) 100vw, 1180px"
                style={{ objectFit: 'cover', objectPosition: 'center' }}
              />
            </div>
            <figcaption style={{ padding: '20px 24px' }}>
              <h3 className="mb-1" style={feat.title}>
                Population frequency, mapped
              </h3>
              <p style={feat.caption}>
                gnomAD v4 allele frequencies across every genetic ancestry group, on a land-clipped
                world map — source-group data, not patient ancestry or geography.
              </p>
            </figcaption>
          </figure>
        </Reveal>

        {/* Grid: the other product snapshots + the in-development Workbench */}
        <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {SHOTS.map((shot, i) => (
            <Reveal key={shot.src} as="article" delay={(i % 2) * 0.08}>
              <figure
                className="m-0 h-full overflow-hidden"
                style={{ background: 'var(--d-card)', border: '0.5px solid var(--d-line)', borderRadius: 14 }}
              >
                <div
                  className="relative"
                  style={{ aspectRatio: '16 / 11', overflow: 'hidden', background: 'var(--d-bg-2)' }}
                >
                  <Image
                    src={shot.src}
                    alt={shot.title}
                    fill
                    sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
                    style={{ objectFit: 'cover', objectPosition: 'top center' }}
                  />
                </div>
                <figcaption style={{ padding: '16px 18px' }}>
                  <h3 className="mb-1" style={feat.title}>
                    {shot.title}
                  </h3>
                  <p style={feat.caption}>{shot.caption}</p>
                </figcaption>
              </figure>
            </Reveal>
          ))}

          {/* Workbench — in development */}
          <Reveal as="article" delay={0.08}>
            <figure
              className="m-0 h-full overflow-hidden"
              style={{ background: 'var(--d-card)', border: '0.5px solid var(--d-line)', borderRadius: 14 }}
            >
              <div
                className="relative flex items-center justify-center"
                style={{
                  aspectRatio: '16 / 11',
                  overflow: 'hidden',
                  background:
                    'radial-gradient(120% 120% at 50% 0%, rgba(16,185,129,0.10), transparent 60%), var(--d-bg-2)',
                }}
              >
                <span
                  aria-hidden
                  className="text-center"
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 11,
                    lineHeight: 1.7,
                    letterSpacing: '0.04em',
                    color: 'var(--hero-ink-3)',
                    filter: 'grayscale(1)',
                    opacity: 0.7,
                  }}
                >
                  Sequence viewer
                  <br />
                  Primer · CRISPR design
                  <br />
                  Pairwise alignment
                </span>
                <span
                  className="absolute"
                  style={{
                    top: 12,
                    right: 12,
                    fontSize: 10,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    color: 'var(--em-bright)',
                    background: 'rgba(16,185,129,0.12)',
                    border: '0.5px solid var(--hero-line)',
                    borderRadius: 999,
                    padding: '4px 10px',
                  }}
                >
                  In development
                </span>
              </div>
              <figcaption style={{ padding: '16px 18px' }}>
                <h3 className="mb-1" style={feat.title}>
                  Workbench
                </h3>
                <p style={feat.caption}>
                  Sequence viewer, primer & CRISPR design, and alignment — in the works.
                </p>
              </figcaption>
            </figure>
          </Reveal>
        </div>
      </div>
    </section>
  )
}

const feat = {
  title: {
    fontFamily: 'var(--display)',
    fontWeight: 600,
    fontSize: 16,
    lineHeight: 1.25,
    letterSpacing: '-0.015em',
    color: 'var(--hero-ink)',
  } as const,
  caption: {
    fontSize: 13,
    color: 'var(--hero-ink-2)',
    lineHeight: 1.55,
    margin: 0,
  } as const,
}
