import { EamosLogo } from '@/components/brand/EamosLogo'
import { SOURCES } from '@/lib/sources'
import { TextLink, TextLinkStyles } from '@/components/landing/ui/TextLink'

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
              Built independently for genomic medicine. Evidence is aggregated live from public
              databases — no patient sequence files are stored.
            </p>
          </div>

          <div className="flex flex-wrap gap-12">
            <FooterCol title="Sources">
              {SOURCES.map((s) => (
                <TextLink key={s.key} href={s.href} target="_blank" rel="noopener noreferrer" className="text-[12.5px]">
                  {s.label}
                </TextLink>
              ))}
            </FooterCol>
            <FooterCol title="Product">
              <TextLink href="#how" className="text-[12.5px]">How it works</TextLink>
              <TextLink href="#features" className="text-[12.5px]">Features</TextLink>
              <TextLink href="/#pricing" className="text-[12.5px]">Pricing</TextLink>
              <TextLink href="#faq" className="text-[12.5px]">FAQ</TextLink>
            </FooterCol>
            <FooterCol title="More">
              <TextLink href="/report?demo=1" className="text-[12.5px]">Sample report</TextLink>
              <TextLink href="#contact" className="text-[12.5px]">Contact</TextLink>
            </FooterCol>
          </div>
        </div>

        <div
          className="mt-12 flex flex-col gap-2 pt-8 text-[11.5px] sm:flex-row sm:items-center sm:justify-between"
          style={{ borderTop: '0.5px solid var(--hero-line)' }}
        >
          <TextLink href="/terms" className="text-[11.5px]">Terms &amp; Conditions</TextLink>
          <TextLink href="/privacy" className="text-[11.5px]">Privacy Policy</TextLink>
          <span style={{ color: 'var(--hero-ink-3)' }}>Research use only — not a medical device.</span>
          <span style={{ color: 'var(--hero-ink-3)' }}>© {new Date().getFullYear()} Eamos · Genomic intelligence platform</span>
        </div>
      </div>
    </footer>
  )
}

function FooterCol({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3">
      <span
        className="text-[10.5px] font-semibold uppercase tracking-[0.14em]"
        style={{ color: 'var(--hero-ink-3)' }}
      >
        {title}
      </span>
      {children}
    </div>
  )
}
