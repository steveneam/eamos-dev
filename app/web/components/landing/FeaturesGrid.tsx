import Image from 'next/image'
import { Reveal } from '@/components/landing/Reveal'
import { LandingH2, LandingH3 } from '@/components/landing/ui/LandingHeading'

interface Shot {
  src: string
  title: string
  caption: string
}

// Product snapshots captured from a live report. Rough first pass — replace with
// polished marketing shots later. The gnomAD world-map featured band below was
// captured from MTHFR c.665C>T (a gnomAD-present variant; the RPE65 demo isn't in gnomAD).
//
// The four-card "evidence matrix" specimen lives in MetricBelt above; this grid
// shows the *other* layers of the report (classification, publications, trials,
// gnomAD map, Workbench).
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
    <section id="features" className="py-28" style={{ background: 'var(--page-bg)' }}>
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        <header className="mb-14" style={{ maxWidth: 720 }}>
          <LandingH2 className="mb-4">One lookup. The whole evidence picture.</LandingH2>
          <p className="text-[17px] leading-[1.55]" style={{ color: 'var(--hero-ink-2)', maxWidth: 620 }}>
            Every report folds the databases you already open into one structured, cited, ACMG-aware
            view, engineered for speed and clinical trust.
          </p>
        </header>

        {/* Featured: gnomAD population-frequency world map (captured from MTHFR c.665C>T).
            The four-call-card specimen lives in MetricBelt above — re-showing it here would
            duplicate the page; this section opens with the gnomAD map as the next layer. */}
        <Reveal as="article">
          <figure
            className="m-0 overflow-hidden"
            style={{ background: 'var(--page-card)', border: '0.5px solid var(--page-line)', borderRadius: 16 }}
          >
            <div
              className="relative"
              style={{ aspectRatio: '7 / 3', overflow: 'hidden', background: 'var(--page-bg-deep)' }}
            >
              <Image
                src="/feat-gnomad-map.webp"
                alt="gnomAD v4 allele frequencies across genetic ancestry groups, rendered on a land-clipped world map"
                fill
                priority
                sizes="(max-width: 1180px) 100vw, 1180px"
                style={{ objectFit: 'cover', objectPosition: 'center' }}
              />
            </div>
            <figcaption style={{ padding: '20px 24px' }}>
              <LandingH3 className="mb-1">
                Population frequency, mapped
              </LandingH3>
              <p style={feat.caption}>
                gnomAD v4 allele frequencies across every genetic ancestry group, on a land-clipped
                world map. Source-group data, not patient ancestry or geography.
              </p>
            </figcaption>
          </figure>
        </Reveal>

        {/* Asymmetric: a wide "Classification" feature, then two narrower
            shots stacked, then a wide "Workbench" in-development tile. Reads as
            magazine column-spans, not a 4-up template. Stacks on mobile. */}
        <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-6">
          {/* SHOT 0 — wide */}
          <Reveal as="article" className="lg:col-span-4" delay={0}>
            <figure
              className="m-0 h-full overflow-hidden"
              style={{ background: 'var(--page-card)', border: '0.5px solid var(--page-line)', borderRadius: 14 }}
            >
              <div
                className="relative"
                style={{ aspectRatio: '16 / 8', overflow: 'hidden', background: 'var(--page-bg-deep)' }}
              >
                <Image
                  src={SHOTS[0].src}
                  alt={SHOTS[0].title}
                  fill
                  priority
                  sizes="(max-width: 1024px) 100vw, 66vw"
                  style={{ objectFit: 'cover', objectPosition: 'top center' }}
                />
              </div>
              <figcaption style={{ padding: '18px 22px' }}>
                <LandingH3 className="mb-1">
                  {SHOTS[0].title}
                </LandingH3>
                <p style={feat.caption}>{SHOTS[0].caption}</p>
              </figcaption>
            </figure>
          </Reveal>

          {/* SHOTS 1-2 — narrow, stacked into one column on lg+ */}
          <div className="grid grid-cols-1 gap-5 lg:col-span-2">
            {[SHOTS[1], SHOTS[2]].map((shot, i) => (
              <Reveal key={shot.src} as="article" delay={0.06 + i * 0.04}>
                <figure
                  className="m-0 h-full overflow-hidden"
                  style={{ background: 'var(--page-card)', border: '0.5px solid var(--page-line)', borderRadius: 14 }}
                >
                  <div
                    className="relative"
                    style={{ aspectRatio: '16 / 9', overflow: 'hidden', background: 'var(--page-bg-deep)' }}
                  >
                    <Image
                      src={shot.src}
                      alt={shot.title}
                      fill
                      sizes="(max-width: 1024px) 100vw, 33vw"
                      style={{ objectFit: 'cover', objectPosition: 'top center' }}
                    />
                  </div>
                  <figcaption style={{ padding: '14px 18px' }}>
                    <LandingH3 className="mb-1">
                      {shot.title}
                    </LandingH3>
                    <p style={feat.caption}>{shot.caption}</p>
                  </figcaption>
                </figure>
              </Reveal>
            ))}
          </div>

          {/* Workbench — wide, in development. Spans full width on lg+ so it
              reads as a milestone, not a peer. */}
          <Reveal as="article" className="lg:col-span-6" delay={0.18}>
            <figure
              className="m-0 h-full overflow-hidden"
              style={{ background: 'var(--page-card)', border: '0.5px solid var(--page-line)', borderRadius: 14 }}
            >
              <div
                className="relative flex items-center justify-center"
                style={{
                  aspectRatio: '32 / 9',
                  overflow: 'hidden',
                  background:
                    'radial-gradient(120% 120% at 50% 0%, rgba(16,185,129,0.10), transparent 60%), var(--page-bg-deep)',
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
                <LandingH3 className="mb-1">
                  Workbench
                </LandingH3>
                <p style={feat.caption}>
                  Sequence viewer, primer & CRISPR design, and alignment; in the works.
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
  caption: {
    fontSize: 13,
    color: 'var(--hero-ink-2)',
    lineHeight: 1.55,
    margin: 0,
  } as const,
}
