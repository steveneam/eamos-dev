import { EamosLogo } from '@/components/brand/EamosLogo'
import { SOURCES } from '@/lib/sources'

export function SiteFooter() {
  return (
    <footer
      className="py-16"
      style={{
        background: 'var(--hero-bot)',
        borderTop: '0.5px solid var(--hero-line)',
      }}
    >
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
                <FooterLink key={s.key} href={s.href} external>
                  {s.label}
                </FooterLink>
              ))}
            </FooterCol>
            <FooterCol title="Product">
              <FooterLink href="#how">How it works</FooterLink>
              <FooterLink href="#features">Features</FooterLink>
              <FooterLink href="#pricing">Pricing</FooterLink>
              <FooterLink href="#faq">FAQ</FooterLink>
            </FooterCol>
            <FooterCol title="More">
              <FooterLink href="/report?demo=1">Sample report</FooterLink>
              <FooterLink href="https://github.com/" external>
                GitHub
              </FooterLink>
              <FooterLink href="#contact">Contact</FooterLink>
            </FooterCol>
          </div>
        </div>

        <div
          className="mt-12 flex flex-col gap-2 pt-8 text-[11.5px] sm:flex-row sm:items-center sm:justify-between"
          style={{ borderTop: '0.5px solid var(--hero-line)', color: 'var(--hero-ink-3)' }}
        >
          <span>End-user software terms apply.</span>
          <span>© {new Date().getFullYear()} Eamos · Genomic intelligence platform</span>
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

function FooterLink({
  href,
  children,
  external,
}: {
  href: string
  children: React.ReactNode
  external?: boolean
}) {
  return (
    <a
      href={href}
      {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
      className="text-[12.5px] transition-colors hover:opacity-100"
      style={{ color: 'var(--hero-ink-2)', textDecoration: 'none', opacity: 0.85 }}
    >
      {children}
    </a>
  )
}
