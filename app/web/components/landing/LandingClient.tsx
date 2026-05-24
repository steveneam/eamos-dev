'use client'
import { useRouter } from 'next/navigation'
import { LandingNav } from '@/components/landing/LandingNav'
import { EamosSearch } from '@/components/landing/EamosSearch'
import { Lifestream } from '@/components/landing/Lifestream'
import { SourceStrip } from '@/components/landing/SourceStrip'
import { MetricBelt } from '@/components/landing/MetricBelt'
import { HowItWorks } from '@/components/landing/HowItWorks'
import { FeaturesGrid } from '@/components/landing/FeaturesGrid'
import { Testimonials } from '@/components/landing/Testimonials'
import { Pricing } from '@/components/landing/Pricing'
import { Faq } from '@/components/landing/Faq'
import { SiteFooter } from '@/components/landing/SiteFooter'

const VARIANT_LIKE = /^(c\.|p\.|g\.|m\.|n\.|rs\d|chr|\d+[-:])/i
const BARE_CDNA_LIKE = /^\d+(?:[+-]\d+)?(?:[ACGT]>[ACGT]|del(?:[ACGT]+)?|dup(?:[ACGT]+)?|ins[ACGT]+|delins[ACGT]+)$/i
const GENE_LIKE = /^[A-Za-z][A-Za-z0-9-]{1,15}$/

function cleanToken(token: string) {
  return token.trim().replace(/^[("'`]+|[)"'`,.;!?]+$/g, '')
}

function normaliseVariantToken(token: string) {
  const cleaned = cleanToken(token)
  if (!cleaned) return null
  if (VARIANT_LIKE.test(cleaned)) return cleaned
  if (BARE_CDNA_LIKE.test(cleaned)) return `c.${cleaned}`
  return null
}

function structuredVariantFromText(text: string) {
  const direct = text.match(/^([A-Za-z][A-Za-z0-9-]+)\s+(.+)$/)
  if (direct) {
    const variant = normaliseVariantToken(direct[2])
    if (variant) return { gene: direct[1].toUpperCase(), variant }
  }

  const tokens = text.split(/\s+/).map(cleanToken).filter(Boolean)
  for (let i = 1; i < tokens.length; i += 1) {
    const gene = tokens[i - 1]
    const variant = normaliseVariantToken(tokens[i])
    if (variant && GENE_LIKE.test(gene)) return { gene: gene.toUpperCase(), variant }
  }
  return null
}

export function LandingClient() {
  const router = useRouter()

  // One bar, freeform. Structured "GENE c.…/p.…/rs…" routes straight to the
  // lookup; anything else is sent as a raw query for the backend search-input
  // resolver to interpret (gene vs plain language).
  const handleSubmit = (raw: string) => {
    const text = raw.trim()
    if (!text) return
    const structured = structuredVariantFromText(text)
    if (structured) {
      const params = new URLSearchParams({ gene: structured.gene, cdna: structured.variant })
      router.push(`/report?${params.toString()}`)
    } else {
      const params = new URLSearchParams({ q: text })
      router.push(`/report?${params.toString()}`)
    }
  }

  return (
    <div style={{ background: 'var(--hero-top)', minHeight: '100vh' }}>
      <LandingNav onSubmit={handleSubmit} />

      {/* Hero — the deep emerald Lifestream */}
      <section
        id="hero"
        className="relative overflow-hidden"
        style={{
          background:
            'linear-gradient(180deg, var(--hero-top) 0%, var(--hero-mid) 48%, var(--hero-bot) 100%)',
          padding: '96px 24px 132px',
        }}
      >
        {/* Generated 8K emerald "lifestream tree" backdrop */}
        <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
          <img
            src="/hero-tree.webp"
            alt=""
            className="absolute inset-0 h-full w-full object-cover"
            style={{ objectPosition: '50% 30%', opacity: 0.95 }}
          />
          {/* darken the centre for headline legibility + blend edges into the page */}
          <div
            className="absolute inset-0"
            style={{
              background:
                'radial-gradient(74% 60% at 50% 38%, rgba(3,19,13,0.62) 0%, rgba(3,19,13,0.24) 58%, rgba(3,19,13,0) 82%)',
            }}
          />
          <div
            className="absolute inset-x-0 top-0"
            style={{ height: 130, background: 'linear-gradient(to bottom, var(--hero-top), rgba(2,17,12,0))' }}
          />
          <div
            className="absolute inset-x-0 bottom-0"
            style={{ height: 220, background: 'linear-gradient(to bottom, rgba(2,17,12,0), var(--hero-bot))' }}
          />
        </div>
        <Lifestream />
        <div className="relative z-10 mx-auto flex flex-col items-center text-center" style={{ maxWidth: 760 }}>
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
                boxShadow: '0 0 0 3px rgba(52,211,153,0.22)',
              }}
            />
            Genomic intelligence platform
          </span>

          <h1
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 600,
              fontSize: 'clamp(38px, 5.4vw, 66px)',
              lineHeight: 1.04,
              letterSpacing: '-0.025em',
              color: 'var(--hero-ink)',
              textWrap: 'balance',
              margin: '0 0 22px',
            }}
          >
            Instant, evidence-aggregated{' '}
            <span style={{ color: 'var(--em-bright)' }}>variant interpretation</span>.
          </h1>

          <p
            style={{
              fontSize: 18,
              lineHeight: 1.6,
              color: 'var(--hero-ink-2)',
              maxWidth: 560,
              margin: '0 0 40px',
            }}
          >
            One variant in, one structured report out. Eamos aggregates ClinVar, gnomAD, SpliceAI,
            Ensembl, PubMed, and ClinicalTrials.gov into a single clinician-readable report — so you
            stop opening six tabs per variant.
          </p>

          <div style={{ width: '100%', maxWidth: 620 }}>
            <EamosSearch size="hero" onSubmit={handleSubmit} />
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
            <span className="mr-1 text-[11px] font-medium uppercase tracking-[0.08em]" style={{ color: 'var(--hero-ink-3)' }}>
              Try
            </span>
            {[
              'RPE65 c.260A>G',
              'RPE65 c.11+5G>A',
              'USH2A c.2276G>T',
              'BRCA1 c.5266dupC',
            ].map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => handleSubmit(chip)}
                className="inline-flex items-center gap-1.5 rounded-full transition-colors"
                style={{
                  padding: '5px 11px',
                  background: 'var(--hero-glass)',
                  border: '0.5px solid var(--hero-line)',
                  fontFamily: 'var(--mono)',
                  fontSize: 11,
                  color: 'var(--hero-ink-2)',
                  cursor: 'pointer',
                }}
              >
                <span aria-hidden style={{ width: 4, height: 4, borderRadius: 999, background: 'var(--em-bright)' }} />
                {chip}
              </button>
            ))}
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
