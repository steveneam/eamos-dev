'use client'
import Link from 'next/link'
import { EamosLogo } from '@/components/brand/EamosLogo'
import { AuthMenu } from '@/components/auth/AuthMenu'

/** Slim dark marketing header for the pricing/checkout routes. */
export function PageHeader() {
  return (
    <header
      className="sticky top-0 z-50"
      style={{ background: 'rgba(4,22,16,0.82)', borderBottom: '0.5px solid var(--hero-line)', backdropFilter: 'blur(8px)' }}
    >
      <div className="mx-auto flex items-center justify-between px-6" style={{ maxWidth: 1180, height: 56 }}>
        <Link href="/" aria-label="Eamos home" style={{ textDecoration: 'none' }}>
          <EamosLogo size={18} tone="dark" />
        </Link>
        <div className="flex items-center gap-5">
          <Link href="/#features" style={navLink}>Features</Link>
          <Link href="/#pricing" style={navLink}>Pricing</Link>
          <Link href="/#faq" style={navLink}>FAQ</Link>
          <AuthMenu tone="dark" />
        </div>
      </div>
    </header>
  )
}

const navLink: React.CSSProperties = {
  color: 'var(--hero-ink-2)',
  fontSize: 13.5,
  fontWeight: 600,
  textDecoration: 'none',
}
