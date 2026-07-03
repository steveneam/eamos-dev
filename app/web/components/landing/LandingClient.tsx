'use client'
import { useRouter } from 'next/navigation'
import { LandingNav } from '@/components/landing/LandingNav'
import { EamosSearch } from '@/components/landing/EamosSearch'
import { GenomicFlow } from '@/components/landing/GenomicFlow'
import { SourceStrip } from '@/components/landing/SourceStrip'
import { MetricBelt } from '@/components/landing/MetricBelt'
import { HowItWorks } from '@/components/landing/HowItWorks'
import { FeaturesGrid } from '@/components/landing/FeaturesGrid'
import { Testimonials } from '@/components/landing/Testimonials'
import { Pricing } from '@/components/landing/Pricing'
import { Faq } from '@/components/landing/Faq'
import { SiteFooter } from '@/components/landing/SiteFooter'
import { Pill, PillStyles } from '@/components/landing/ui/Pill'
import { searchHrefForQuery } from '@/lib/variant-search'
import { parseVariantFile, stashCompareVariants } from '@/lib/variant-file'
import { SAMPLE_VCF, SAMPLE_VCF_NAME } from '@/lib/sample-vcf'

export function LandingClient() {
  const router = useRouter()

  // One bar, freeform. Structured "GENE c.…/p.…/rs…" routes straight to the
  // lookup; anything else is sent as a raw query for the backend search-input
  // resolver to interpret (gene vs plain language). Shared with the report search.
  const handleSubmit = (raw: string) => {
    const href = searchHrefForQuery(raw)
    if (href) router.push(href)
  }

  return (
    <div style={{ background: 'var(--hero-top)', minHeight: '100vh' }}>
      <LandingNav onSubmit={handleSubmit} />

      {/* Hero — warm-brown editorial ground; evidence converges into the search */}
      <section
        id="hero"
        className="relative overflow-hidden"
        style={{
          background:
            'linear-gradient(180deg, var(--hero-top) 0%, var(--hero-mid) 52%, var(--hero-bot) 100%)',
          padding: '96px 0 112px',
        }}
      >
        <GenomicFlow />
        <div className="relative z-10 mx-auto flex flex-col items-start px-8 text-left" style={{ maxWidth: 1180 }}>
          <span
            className="mb-7 inline-flex items-center gap-2 rounded-full"
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
              color: 'var(--em-glow)',
              padding: '5px 12px',
              background: 'var(--hero-glass)',
              border: '0.5px solid var(--hero-line)',
            }}
          >
            <span
              aria-hidden
              style={{
                width: 6,
                height: 6,
                borderRadius: 999,
                background: 'var(--em-bright)',
                boxShadow: '0 0 0 3px color-mix(in oklab, var(--em) 22%, transparent)',
              }}
            />
            Genomics for everyone
          </span>

          <h1
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 400,
              fontSize: 'clamp(42px, 5.8vw, 68px)',
              lineHeight: 1.08,
              letterSpacing: '-0.02em',
              color: 'var(--hero-ink)',
              textWrap: 'balance',
              maxWidth: 820,
              margin: '0 0 22px',
            }}
          >
            Understand any genetic{' '}
            <span style={{ color: 'var(--em-bright)' }}>variant</span>
          </h1>

          <p
            style={{
              fontSize: 18,
              lineHeight: 1.6,
              color: 'var(--hero-ink-2)',
              maxWidth: 520,
              margin: '0 0 40px',
            }}
          >
            Search a gene, a variant, or ask in plain words. Eamos gathers the genomic evidence and
            returns one clear, sourced report.
          </p>

          <div style={{ width: '100%', maxWidth: 880 }}>
            <EamosSearch size="hero" tone="light" onSubmit={handleSubmit} />
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-2">
            <PillStyles />
            <span className="mr-1 text-[11px] font-medium uppercase tracking-[0.08em]" style={{ color: 'var(--hero-ink-3)' }}>
              Try
            </span>
            {[
              'USH2A c.2276G>T',
              'RPE65 c.11+5G>A',
              'BRCA1 c.5266dupC',
            ].map((chip) => (
              <Pill
                key={chip}
                as="button"
                onClick={() => handleSubmit(chip)}
                fontFamily="var(--mono)"
                style={{ fontSize: 11 }}
              >
                {chip}
              </Pill>
            ))}
            <span
              className="mx-1"
              style={{ display: 'inline-block', width: 1, height: 14, background: 'var(--hero-line)' }}
              aria-hidden
            />
            <Pill
              as="button"
              onClick={() => {
                const parsed = parseVariantFile(SAMPLE_VCF, SAMPLE_VCF_NAME)
                stashCompareVariants(parsed, SAMPLE_VCF_NAME)
                router.push('/compare?demo=1')
              }}
              style={{ fontSize: 11 }}
            >
              Sample VCF →
            </Pill>
          </div>
        </div>
      </section>

      <SourceStrip />
      <MetricBelt />
      <HowItWorks />
      <FeaturesGrid />
      <Testimonials />
      <Pricing />
      <Faq />
      <SiteFooter />
    </div>
  )
}
