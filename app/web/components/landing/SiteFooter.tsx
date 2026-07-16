import { EamosLogo } from '@/components/brand/EamosLogo'
import { LANDING_SOURCES } from '@/lib/sources'
import { TextLink, TextLinkStyles } from '@/components/landing/ui/TextLink'
import { LandingEyebrow } from '@/components/landing/ui/LandingEyebrow'

export function SiteFooter() {
  return (
    <footer
      className="py-16"
      style={{
        background: 'var(--hero-bot)',
        borderTop: '0.5px solid var(--hero-line)',
      }}
    >
      <TextLinkStyles />
      <div className="mx-auto px-8" style={{ maxWidth: 1180 }}>
        <div className="flex flex-col gap-10 sm:flex-row sm:items-start sm:justify-between">
          <div style={{ maxWidth: 360 }}>
            <EamosLogo size={18} tone="dark" />
            <p className="mt-4 text-[12.5px] leading-[1.6]" style={{ color: 'var(--hero-ink-2)' }}>
              A free, independent genomic evidence workspace. Public-source results keep their
              citations and provenance, and source availability remains visible.
            </p>
          </div>

          <div className="flex flex-wrap gap-12">
            <FooterCol title="Sources">
              {LANDING_SOURCES.map((s) => (
                <TextLink key={s.key} href={s.href} target="_blank" rel="noopener noreferrer" className="text-[12.5px]">
                  {s.label}
                </TextLink>
              ))}
            </FooterCol>
            <FooterCol title="Product">
              <TextLink href="#how" className="text-[12.5px]">How it works</TextLink>
              <TextLink href="#features" className="text-[12.5px]">Features</TextLink>
              <TextLink href="/workbench" className="text-[12.5px]">Workbench</TextLink>
              <TextLink href="#faq" className="text-[12.5px]">FAQ</TextLink>
            </FooterCol>
            <FooterCol title="More">
              <TextLink href="/report?gene=USH2A&cdna=c.2276G%3ET" className="text-[12.5px]">Sample report</TextLink>
              <TextLink href="/account" className="text-[12.5px]">Submit evidence</TextLink>
              <TextLink href="mailto:hello@eamos.com.au" className="text-[12.5px]">Contact</TextLink>
            </FooterCol>
          </div>
        </div>

        <div
          className="mt-12 flex flex-col gap-2 pt-8 text-[11.5px] sm:flex-row sm:items-center sm:justify-between"
          style={{ borderTop: '0.5px solid var(--hero-line)' }}
        >
          <TextLink href="/terms" className="text-[11.5px]">Terms &amp; Conditions</TextLink>
          <TextLink href="/privacy" className="text-[11.5px]">Privacy Policy</TextLink>
          <span style={{ color: 'var(--hero-ink-3)' }}>Research use only. Not a medical device.</span>
          <span style={{ color: 'var(--hero-ink-3)' }}>© {new Date().getFullYear()} Eamos · Genomic intelligence platform</span>
        </div>
      </div>
    </footer>
  )
}

function FooterCol({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3">
      <LandingEyebrow style={{ color: 'var(--hero-ink-3)' }}>
        {title}
      </LandingEyebrow>
      {children}
    </div>
  )
}
