import type { Metadata } from 'next'
import Link from 'next/link'
import { EamosLogo } from '@/components/brand/EamosLogo'

export const metadata: Metadata = {
  title: 'Privacy Policy — Eamos',
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
    p: 'We collect the following categories of personal information: (a) Account identity — your name, email address, and OAuth profile information provided when you sign in via Google, Microsoft, or LinkedIn, or when you register with an email address directly. This is managed through Supabase Auth. (b) Saved variants and evidence submissions — any variant records you choose to save in your account, and any evidence submissions you make through the Messenger feature. (c) Usage analytics — page-visit and interaction events collected by PostHog to help us understand how the platform is used and improve it.',
  },
  {
    h: '4. How genomic queries are de-identified in analytics',
    p: 'When you search for a variant, PostHog is configured to capture the route path only — the gene name, cDNA notation, and any query-string parameters are scrubbed before the event is sent. Users are identified in analytics by an opaque Supabase UUID, not by email address. As a result, your specific genomic queries are not linked to your identity in our analytics system.',
  },
  {
    h: '5. Reference genomic data is not your personal data',
    p: 'Evidence shown in variant reports (from ClinVar, gnomAD, Ensembl/VEP, ClinicalTrials.gov, PubMed, and other public sources) is fetched live from those public databases and is reference data about variants, not personal data belonging to you. No patient sequence files are stored by Eamos.',
  },
  {
    h: '6. How we use your information',
    p: 'Your account identity is used solely to authenticate you, manage your subscription, and associate saved data with your account. Saved variants and Messenger submissions are stored so you can retrieve and manage them. Usage analytics are used in aggregate to improve platform features and reliability. We do not sell your personal information, use it for targeted advertising, or share it for purposes unrelated to operating Eamos.',
  },
  {
    h: '7. Third-party processors',
    p: 'We share personal information with the following processors only to the extent necessary to operate the platform: Supabase (authentication and database, Sydney region, Australia) for account data and saved records; PostHog (analytics, United States) for usage events — only de-identified data as described in section 4; Google, Microsoft, and LinkedIn (OAuth providers) when you choose to sign in via those services — subject to their own privacy policies; Vercel (application hosting) and Render (backend hosting) as infrastructure processors. We do not authorise processors to use your data for their own purposes beyond service delivery.',
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
      <header
        className="mx-auto flex items-center justify-between px-6"
        style={{ maxWidth: 820, height: 64 }}
      >
        <Link href="/" aria-label="Eamos home" style={{ textDecoration: 'none' }}>
          <EamosLogo size={18} tone="dark" />
        </Link>
        <Link href="/" style={{ color: 'var(--hero-ink-2)', fontSize: 13, fontWeight: 600, textDecoration: 'none' }}>
          ← Back to home
        </Link>
      </header>

      <main className="mx-auto px-6 pb-28 pt-10" style={{ maxWidth: 820 }}>
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em]" style={{ color: 'var(--em-bright)' }}>
          Legal
        </p>
        <h1
          className="text-[clamp(30px,4vw,44px)] font-semibold leading-[1.08] tracking-[-0.02em]"
          style={{ fontFamily: 'var(--display)', color: 'var(--hero-ink)' }}
        >
          Privacy Policy
        </h1>
        <p className="mt-4 text-[14px]" style={{ color: 'var(--hero-ink-3)' }}>
          Preview draft — last updated 25 May 2026. Written to comply with the Australian Privacy Act 1988 (Cth) and the Australian Privacy Principles (APPs).
        </p>

        <div className="mt-12 flex flex-col gap-9">
          {SECTIONS.map((s) => (
            <section key={s.h}>
              <h2 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 18, color: 'var(--hero-ink)', margin: 0 }}>
                {s.h}
              </h2>
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
