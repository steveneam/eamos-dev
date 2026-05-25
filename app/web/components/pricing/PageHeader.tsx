'use client'
import Link from 'next/link'
import { EamosLogo } from '@/components/brand/EamosLogo'
import { AuthMenu } from '@/components/auth/AuthMenu'

/**
 * Shared header for pricing/checkout routes.
 * tone="dark"  — original dark emerald landing nav.
 * tone="light" — warm-white product nav for checkout/account flows.
 */
export function PageHeader({ tone = 'dark' }: { tone?: 'dark' | 'light' }) {
  const dark = tone === 'dark'

  return (
    <header
      className="sticky top-0 z-50"
      style={
        dark
          ? {
              background: 'rgba(4,22,16,0.92)',
              borderBottom: '0.5px solid var(--hero-line)',
              backdropFilter: 'blur(8px)',
              height: 'var(--nav-h)',
              display: 'flex',
              alignItems: 'center',
            }
          : {
              background: 'var(--bg)',
              borderBottom: '0.5px solid var(--line)',
              height: 'var(--nav-h)',
              display: 'flex',
              alignItems: 'center',
            }
      }
    >
      <div
        className="mx-auto flex items-center justify-between px-6"
        style={{ maxWidth: 1180, width: '100%' }}
      >
        <Link href="/" aria-label="Eamos home" style={{ textDecoration: 'none' }}>
          <EamosLogo size={18} tone={tone} />
        </Link>
        <div className="flex items-center gap-5">
          <Link href="/#features" style={navLink(dark)}>
            Features
          </Link>
          <Link href="/#pricing" style={navLink(dark)}>
            Pricing
          </Link>
          <Link href="/#faq" style={navLink(dark)}>
            FAQ
          </Link>
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
    textDecoration: 'none',
  }
}
