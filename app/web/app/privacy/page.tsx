import type { Metadata } from 'next'
import Link from 'next/link'
import { EamosLogo } from '@/components/brand/EamosLogo'
import { AuthMenu } from '@/components/auth/AuthMenu'
import { TextLink, TextLinkStyles } from '@/components/landing/ui/TextLink'
import { LandingH3 } from '@/components/landing/ui/LandingHeading'

export const metadata: Metadata = {
  title: 'Privacy Policy · Eamos',
  description: 'Privacy policy for the Eamos genomic intelligence platform. How we collect, use, and protect your information under the Australian Privacy Principles.',
}

const SECTIONS: { h: string; p: string }[] = [
  {
    h: '1. Research use only',
    p: 'Eamos is a research-use-only (RUO) genomic variant intelligence tool. It aggregates publicly available reference data for informational and research purposes. It is not a medical device and output must not be used as the sole basis for any clinical decision.',
  },
  {
    h: '2. Who we are',
    p: 'Eamos is an Australian-based platform hosted at eamos.com.au. This policy is written to comply with the Australian Privacy Act 1988 (Cth) and the Australian Privacy Principles (APPs), in particular APP 1 (open and transparent management of personal information). Questions or requests may be directed to privacy@eamos.com.au.',
  },
  {
    h: '3. What personal information we collect',
    p: 'We collect the following categories of personal information: (a) Account identity, being your name, email address, and OAuth profile information provided when you sign in via Google, Microsoft, or LinkedIn, or when you register with an email address directly. This is managed through Supabase Auth. (b) Saved variants and evidence submissions, being any variant records you choose to save in your account, and any evidence submissions you make through the Messenger feature. (c) Usage analytics, being page-visit and interaction events collected by PostHog to help us understand how the platform is used and improve it.',
  },
  {
    h: '4. How genomic queries are de-identified in analytics',
    p: 'When you search for a variant, PostHog is configured to capture the route path only; the gene name, cDNA notation, and any query-string parameters are scrubbed before the event is sent. Users are identified in analytics by an opaque Supabase UUID, not by email address. As a result, your specific genomic queries are not linked to your identity in our analytics system.',
  },
  {
    h: '5. Reference genomic data is not your personal data',
    p: 'Evidence shown in variant reports (from ClinVar, gnomAD, Ensembl, ClinicalTrials.gov, PubMed, and other public sources) is fetched live from those public databases and is reference data about variants, not personal data belonging to you. No patient sequence files are stored by Eamos.',
  },
  {
    h: '6. How we use your information',
    p: 'Your account identity is used solely to authenticate you, manage your subscription, and associate saved data with your account. Saved variants and Messenger submissions are stored so you can retrieve and manage them. Usage analytics are used in aggregate to improve platform features and reliability. We do not sell your personal information, use it for targeted advertising, or share it for purposes unrelated to operating Eamos.',
  },
  {
    h: '7. Third-party processors',
    p: 'We share personal information with the following processors only to the extent necessary to operate the platform: Supabase (authentication and database, Sydney region, Australia) for account data and saved records; PostHog (analytics, United States) for usage events (only de-identified data as described in section 4); Google, Microsoft, and LinkedIn (OAuth providers) when you choose to sign in via those services, subject to their own privacy policies; Vercel (application hosting) and Render (backend hosting) as infrastructure processors. We do not authorise processors to use your data for their own purposes beyond service delivery.',
  },
  {
    h: '8. Data retention',
    p: 'Account data and saved records are retained for as long as your account is active. If you delete your account, your personal information will be removed from our active systems within 30 days, subject to any retention obligations under applicable law. Analytics data retained by PostHog is subject to PostHog\'s own retention settings.',
  },
  {
    h: '9. Your rights (APP 12 & APP 13)',
    p: 'Under the Australian Privacy Act you have the right to access the personal information we hold about you and to request correction of information that is inaccurate, out of date, incomplete, or misleading. You also have the right to request deletion of your account and associated personal data. To exercise any of these rights, contact us at privacy@eamos.com.au. We will respond within 30 days.',
  },
  {
    h: '10. Security',
    p: 'We use industry-standard security measures including TLS encryption in transit and access controls on our database. Authentication is delegated to Supabase, which implements secure credential handling. We promptly investigate suspected breaches and will notify affected users and the Office of the Australian Information Commissioner (OAIC) as required by the Notifiable Data Breaches scheme.',
  },
  {
    h: '11. Changes to this policy',
    p: 'We may update this policy as the platform evolves. Material changes will be communicated through the platform. Continued use after a change constitutes acceptance of the updated policy. The current version is always available at eamos.com.au/privacy.',
  },
  {
    h: '12. Contact',
    p: 'For privacy enquiries, access requests, correction requests, or complaints, contact us at privacy@eamos.com.au. If you are not satisfied with our response, you may lodge a complaint with the Office of the Australian Information Commissioner (OAIC) at oaic.gov.au.',
  },
]

export default function PrivacyPage() {
  return (
    <div style={{ background: 'var(--page-bg)', minHeight: '100vh' }}>
      <TextLinkStyles />

      {/* Composed nav — same geometry as LandingNav: logo left, links
          centered in a flex-1 zone, AuthMenu right. Static (not sticky) since
          legal pages don't have a hero search to fold into. */}
      <header style={{ borderBottom: '0.5px solid var(--page-line)' }}>
        <div
          className="relative mx-auto flex items-center gap-3 px-4 sm:gap-4 sm:px-8"
          style={{ maxWidth: 1180, height: 'var(--nav-h)' }}
        >
          <div className="flex items-center gap-2">
            <Link href="/" aria-label="Eamos home" className="brand-home-link flex shrink-0 items-center">
              <EamosLogo size={18} tone="dark" />
            </Link>
          </div>
          <div className="relative flex min-w-0 flex-1 items-center justify-center">
            <nav className="hidden items-center gap-8 md:flex">
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
          </div>
          <div className="flex items-center justify-end gap-2">
            <AuthMenu tone="light" />
          </div>
        </div>
      </header>

      <main className="mx-auto px-6 pb-28 pt-10" style={{ maxWidth: 820 }}>
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="mb-8 text-[12px]" style={{ color: 'var(--hero-ink-3)' }}>
          <TextLink href="/" style={{ color: 'var(--hero-ink-3)' }}>Home</TextLink>
          <span aria-hidden style={{ margin: '0 8px' }}>·</span>
          <span aria-current="page" style={{ color: 'var(--hero-ink-2)' }}>Privacy Policy</span>
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
          Privacy Policy
        </h1>
        <p className="mt-4 text-[14px]" style={{ color: 'var(--hero-ink-3)' }}>
          Preview draft, last updated 25 May 2026. Written to comply with the Australian Privacy Act 1988 (Cth) and the Australian Privacy Principles (APPs).
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
