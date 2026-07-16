'use client'
import Link from 'next/link'
import { EamosLogo } from '@/components/brand/EamosLogo'
import { AuthMenu } from '@/components/auth/AuthMenu'
import { TextLink, TextLinkStyles } from '@/components/landing/ui/TextLink'

/** Shared brand-surface header for account and other secondary routes. */
export function PageHeader({ tone = 'dark' }: { tone?: 'dark' | 'light' }) {
  const dark = tone === 'dark'

  return (
    <header
      className="sticky top-0 z-50"
      style={{
        background: dark ? 'rgb(4,22,16)' : 'var(--nav-bg)',
        borderBottom: `0.5px solid ${dark ? 'var(--hero-line)' : 'var(--line)'}`,
        height: 'var(--nav-h)',
        display: 'flex',
        alignItems: 'center',
      }}
    >
      <TextLinkStyles />
      <div
        className="relative mx-auto flex w-full items-center gap-3 px-4 sm:gap-4 sm:px-8"
        style={{ maxWidth: 1180 }}
      >
        <Link
          href="/"
          aria-label="Eamos home"
          className="brand-home-link flex shrink-0 items-center"
        >
          <EamosLogo size={18} tone={tone} />
        </Link>
        <div className="relative flex min-w-0 flex-1 items-center justify-center">
          <nav className="hidden items-center gap-8 md:flex">
            <TextLink href="/#features" style={navLink(dark)}>Features</TextLink>
            <TextLink href="/#how" style={navLink(dark)}>How it works</TextLink>
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
