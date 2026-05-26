import type { Metadata } from 'next'
import Link from 'next/link'
import { EamosLogo } from '@/components/brand/EamosLogo'
import { AuthMenu } from '@/components/auth/AuthMenu'
import { TextLink, TextLinkStyles } from '@/components/landing/ui/TextLink'
import { LandingH3 } from '@/components/landing/ui/LandingHeading'

export const metadata: Metadata = {
  title: 'Terms & Conditions · Eamos',
  description: 'Terms of use for the Eamos genomic intelligence platform. Research use only.',
}

const SECTIONS: { h: string; p: string }[] = [
  {
    h: '1. Research use only',
    p: 'Eamos aggregates third-party genomic evidence (ClinVar, gnomAD, SpliceAI, Ensembl, PubMed and others) into a single report. It is provided for research and informational purposes only and is not a medical device. Output must not be used as the sole basis for any clinical or diagnostic decision.',
  },
  {
    h: '2. No warranty on aggregated evidence',
    p: 'Evidence is sourced live from external databases and may be incomplete, out of date, or revised by the upstream source at any time. Eamos makes no warranty as to the accuracy, completeness, or fitness of any aggregated result, and is not liable for decisions made in reliance on it.',
  },
  {
    h: '3. Your account',
    p: 'You are responsible for the security of your account credentials and for all activity under your account. You agree to provide accurate information and to use the platform in compliance with applicable laws and the terms of the underlying data sources.',
  },
  {
    h: '4. Variant submissions (Messenger)',
    p: 'Where you submit variant evidence for onward routing (e.g. to ClinVar), you confirm you have the right to share that data, that it contains no identifiable patient information unless you are authorised to share it, and that submissions are logged for audit.',
  },
  {
    h: '5. Subscriptions & billing',
    p: 'Paid plans are billed in advance via our payment processor (Stripe). Prices are shown in AUD and include GST where applicable. You may cancel at any time; access continues to the end of the current billing period. Sample pricing shown during this preview is not final.',
  },
  {
    h: '6. Changes to these terms',
    p: 'We may update these terms as the platform evolves. Material changes will be communicated through the platform. Continued use after a change constitutes acceptance.',
  },
]

export default function TermsPage() {
  return (
    <div style={{ background: 'var(--page-bg)', minHeight: '100vh' }}>
      <TextLinkStyles />

      {/* Composed nav: logo, anchor links into the landing, AuthMenu. Static, not
          sticky — legal pages are read-not-scroll-back-to-search surfaces. */}
      <header style={{ borderBottom: '0.5px solid var(--page-line)' }}>
        <div
          className="mx-auto flex items-center gap-6 px-6 sm:px-8"
          style={{ maxWidth: 1180, height: 'var(--nav-h)' }}
        >
          <Link href="/" aria-label="Eamos home" style={{ textDecoration: 'none' }}>
            <EamosLogo size={18} tone="dark" />
          </Link>
          <nav className="ml-auto hidden items-center gap-7 md:flex">
            <TextLink href="/#features" style={{ fontSize: 13.5, fontWeight: 600 }}>
              Features
            </TextLink>
            <TextLink href="/#pricing" style={{ fontSize: 13.5, fontWeight: 600 }}>
              Pricing
            </TextLink>
            <TextLink href="/#faq" style={{ fontSize: 13.5, fontWeight: 600 }}>
              FAQ
            </TextLink>
          </nav>
          <div className="ml-auto flex items-center md:ml-0">
            <AuthMenu tone="light" />
          </div>
        </div>
      </header>

      <main className="mx-auto px-6 pb-28 pt-10" style={{ maxWidth: 820 }}>
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="mb-8 text-[12px]" style={{ color: 'var(--hero-ink-3)' }}>
          <TextLink href="/" style={{ color: 'var(--hero-ink-3)' }}>Home</TextLink>
          <span aria-hidden style={{ margin: '0 8px' }}>·</span>
          <span aria-current="page" style={{ color: 'var(--hero-ink-2)' }}>Terms &amp; Conditions</span>
        </nav>

        <h1
          style={{
            fontFamily: 'var(--display)',
            fontWeight: 400,
            fontSize: 'clamp(34px, 4.4vw, 48px)',
            lineHeight: 1.06,
            letterSpacing: '-0.02em',
            color: 'var(--hero-ink)',
            margin: 0,
          }}
        >
          Terms &amp; Conditions
        </h1>
        <p className="mt-4 text-[14px]" style={{ color: 'var(--hero-ink-3)' }}>
          Preview draft, last updated 24 May 2026. Placeholder content for the test deployment; final
          terms will be reviewed before public launch.
        </p>

        <div className="mt-12 flex flex-col gap-9">
          {SECTIONS.map((s) => (
            <section key={s.h}>
              <LandingH3>{s.h}</LandingH3>
              <p className="mt-2.5 text-[14.5px] leading-[1.7]" style={{ color: 'var(--hero-ink-2)' }}>
                {s.p}
              </p>
            </section>
          ))}
        </div>
      </main>
    </div>
  )
}
