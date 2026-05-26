'use client'
import Link from 'next/link'
import { EamosLogo } from '@/components/brand/EamosLogo'
import { AuthMenu } from '@/components/auth/AuthMenu'
import { TextLink, TextLinkStyles } from '@/components/landing/ui/TextLink'

/**
 * Shared brand-surface header for checkout, account, and other secondary
 * routes. Same geometry as LandingNav (logo left, links CENTERED in a flex-1
 * zone, AuthMenu right) so the nav reads as one system across the site.
 *
 *   tone="dark"  — dark editorial ground (original landing nav).
 *   tone="light" — warm-white product surface (checkout/account/legal flows).
 */
export function PageHeader({ tone = 'dark' }: { tone?: 'dark' | 'light' }) {
  const dark = tone === 'dark'

  return (
    <header
      className="sticky top-0 z-50"
      style={
        dark
          ? {
              // Opaque dark — backdrop-filter:blur on a sticky nav repaints on
              // every keystroke (mobile typing lag).
              background: 'rgb(4,22,16)',
              borderBottom: '0.5px solid var(--hero-line)',
              height: 'var(--nav-h)',
              display: 'flex',
              alignItems: 'center',
            }
          : {
              background: 'var(--nav-bg)',
              borderBottom: '0.5px solid var(--line)',
              height: 'var(--nav-h)',
              display: 'flex',
              alignItems: 'center',
            }
      }
    >
      <TextLinkStyles />
      <div
        className="relative mx-auto flex w-full items-center gap-3 px-4 sm:gap-4 sm:px-8"
        style={{ maxWidth: 1180 }}
      >
        <div className="flex items-center gap-2">
          <Link
            href="/"
            aria-label="Eamos home"
            className="flex shrink-0 items-center"
            style={{ textDecoration: 'none' }}
          >
            <EamosLogo size={18} tone={tone} />
          </Link>
        </div>
        <div className="relative flex min-w-0 flex-1 items-center justify-center">
          <nav className="hidden items-center gap-8 md:flex">
            <TextLink href="/#features" style={navLink(dark)}>Features</TextLink>
            <TextLink href="/#pricing" style={navLink(dark)}>Pricing</TextLink>
            <TextLink href="/#faq" style={navLink(dark)}>FAQ</TextLink>
          </nav>
        </div>
        <div className="flex items-center justify-end gap-2">
          <AuthMenu tone={tone} />
        </div>
      </div>
    </header>
  )
}

function navLink(dark: boolean): React.CSSProperties {
  return {
    color: dark ? 'var(--hero-ink-2)' : 'var(--ink-3)',
    fontSize: 13.5,
    fontWeight: 600,
  }
}
