import Image from 'next/image'
import Link from 'next/link'
import { Reveal } from '@/components/landing/Reveal'
import { LandingH2, LandingH3 } from '@/components/landing/ui/LandingHeading'
import { LandingEyebrow } from '@/components/landing/ui/LandingEyebrow'

const FEATURES = [
  {
    index: '01',
    eyebrow: 'Variant report',
    title: 'Evidence you can trace, not just a verdict',
    description:
      'Move from classification and population evidence to disease context, literature, and trials in one navigable report. Source status and provenance stay attached to the result.',
    src: '/features/report-demo.webp',
    alt: 'Eamos variant report for the bundled RPE65 demo, showing the real gnomAD population-frequency section and its provenance-aware evidence workspace.',
    route: '/report?fixture=rpe65-negative',
    href: '/report?fixture=rpe65-negative',
    action: 'Open the sample report',
  },
  {
    index: '02',
    eyebrow: 'Workbench',
    title: 'Sequence context beside the evidence',
    description:
      'Inspect genomic and transcript context, then move into primer, CRISPR, and alignment tools without rebuilding the variant by hand in another tab.',
    src: '/features/workbench-demo.webp',
    alt: 'Eamos Workbench running with the bundled RPE65 example and its sequence context visible.',
    route: '/workbench · RPE65',
    href: '/workbench?gene=RPE65&cdna=c.260A%3EG&transcript=NM_000329.3',
    action: 'Explore the Workbench',
  },
  {
    index: '03',
    eyebrow: 'Batch comparison',
    title: 'A cohort workflow with an explicit scope',
    description:
      'Import a VCF, review its variants in the browser, then choose when to generate a batch result. The screen below uses the bundled sample VCF.',
    src: '/features/compare-demo.webp',
    alt: 'Eamos batch comparison screen with the bundled sample VCF loaded and ready to generate.',
    route: '/compare · sample.vcf',
    href: '/compare',
    action: 'Open batch comparison',
  },
] as const

export function FeaturesGrid() {
  return (
    <section
      id="features"
      className="py-28"
      style={{
        background: 'var(--page-bg)',
        borderBottom: '0.5px solid var(--page-line)',
      }}
    >
      <div className="mx-auto px-6 sm:px-8" style={{ maxWidth: 1180 }}>
        <header className="mb-16 grid gap-6 md:grid-cols-[minmax(0,1fr)_330px] md:items-end">
          <div style={{ maxWidth: 720 }}>
            <LandingEyebrow className="mb-4" style={{ color: 'var(--em-bright)' }}>
              Inside Eamos
            </LandingEyebrow>
            <LandingH2>See the working product.</LandingH2>
          </div>
          <p
            style={{
              fontSize: 13.5,
              lineHeight: 1.65,
              color: 'var(--hero-ink-3)',
              margin: 0,
            }}
          >
            Current Eamos screens captured in a real browser from bundled demo data. No patient
            records and no concept mockups.
          </p>
        </header>

        <div>
          {FEATURES.map((feature, index) => {
            const imageFirst = index % 2 === 0
            return (
              <Reveal key={feature.index} as="article" delay={index * 0.05}>
                <div
                  className="grid gap-8 py-12 lg:grid-cols-12 lg:items-center lg:gap-12"
                  style={{ borderTop: '0.5px solid var(--page-line)' }}
                >
                  <div
                    className={`lg:col-span-4 ${imageFirst ? 'lg:order-2' : 'lg:order-1'}`}
                    style={{ maxWidth: 420 }}
                  >
                    <span
                      aria-hidden
                      style={{
                        display: 'block',
                        fontFamily: 'var(--mono)',
                        fontSize: 11,
                        color: 'var(--em-bright)',
                        marginBottom: 22,
                      }}
                    >
                      {feature.index} / 03
                    </span>
                    <LandingEyebrow className="mb-3" style={{ color: 'var(--hero-ink-3)' }}>
                      {feature.eyebrow}
                    </LandingEyebrow>
                    <LandingH3 className="mb-4">{feature.title}</LandingH3>
                    <p
                      style={{
                        fontSize: 14.5,
                        lineHeight: 1.65,
                        color: 'var(--hero-ink-2)',
                        margin: '0 0 22px',
                      }}
                    >
                      {feature.description}
                    </p>
                    <Link
                      href={feature.href}
                      className="feature-product-link"
                      style={{
                        color: 'var(--em-bright)',
                        fontSize: 13,
                        fontWeight: 600,
                        textDecoration: 'none',
                      }}
                    >
                      {feature.action} <span aria-hidden>→</span>
                    </Link>
                  </div>

                  <figure
                    className={`m-0 overflow-hidden lg:col-span-8 ${imageFirst ? 'lg:order-1' : 'lg:order-2'}`}
                    style={{
                      background: 'var(--page-bg-deep)',
                      border: '0.5px solid var(--page-line)',
                      borderRadius: 12,
                      boxShadow: 'var(--elev-2)',
                    }}
                  >
                    <div
                      className="flex items-center justify-between gap-4 px-4"
                      style={{
                        height: 34,
                        borderBottom: '0.5px solid var(--page-line)',
                        background: 'var(--page-card)',
                      }}
                    >
                      <span className="flex items-center gap-1.5" aria-hidden>
                        {[0, 1, 2].map((dot) => (
                          <span
                            key={dot}
                            style={{
                              width: 6,
                              height: 6,
                              borderRadius: 999,
                              background: dot === 0 ? 'var(--em)' : 'var(--line-2)',
                            }}
                          />
                        ))}
                      </span>
                      <span
                        style={{
                          fontFamily: 'var(--mono)',
                          fontSize: 9.5,
                          color: 'var(--hero-ink-3)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        Real browser capture · {feature.route}
                      </span>
                    </div>
                    <div className="relative" style={{ aspectRatio: '3 / 2' }}>
                      <Image
                        data-landing-feature-image={feature.index}
                        src={feature.src}
                        alt={feature.alt}
                        fill
                        unoptimized
                        priority={index === 0}
                        sizes="(max-width: 1024px) 100vw, 760px"
                        style={{ objectFit: 'cover', objectPosition: 'top center' }}
                      />
                    </div>
                  </figure>
                </div>
              </Reveal>
            )
          })}
        </div>
      </div>
      <style>{`
        .feature-product-link {
          text-decoration-line: underline;
          text-decoration-color: transparent;
          text-decoration-thickness: 1.5px;
          text-underline-offset: 5px;
          transition: text-decoration-color var(--dur-1) var(--ease-standard);
        }
        .feature-product-link:hover { text-decoration-color: currentColor; }
        .feature-product-link:focus-visible {
          outline: 2px solid color-mix(in oklab, var(--em) 55%, transparent);
          outline-offset: 5px;
          border-radius: 2px;
        }
      `}</style>
    </section>
  )
}
