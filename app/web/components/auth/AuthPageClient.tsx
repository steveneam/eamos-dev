'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { AuthPanel } from '@/components/auth/AuthPanel'
import { useAuth } from '@/components/auth/AuthProvider'
import { EamosLogo } from '@/components/brand/EamosLogo'

/**
 * Full-page /auth route — warm-white product register.
 * Split layout: editorial left panel + form right panel (desktop).
 * Single column (form only) on mobile.
 * Redirects to /account if already signed in.
 */
export function AuthPageClient() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && user) {
      router.replace('/account')
    }
  }, [user, loading, router])

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100dvh',
          background: 'var(--bg-soft)',
          display: 'grid',
          placeItems: 'center',
        }}
        aria-busy="true"
        aria-label="Loading"
      >
        <AuthSkeleton />
      </div>
    )
  }

  return (
    <div
      style={{
        minHeight: '100dvh',
        background: 'var(--bg-soft)',
        display: 'grid',
        gridTemplateColumns: '1fr',
      }}
      className="lg:grid-cols-[1fr_480px]"
    >
      {/* Left panel — editorial context strip (hidden on mobile) */}
      <aside
        className="hidden lg:flex lg:flex-col lg:justify-between"
        style={{
          background: 'var(--bg)',
          borderRight: '0.5px solid var(--line)',
          padding: '48px 56px',
        }}
      >
        <Link href="/" aria-label="Eamos home" style={{ textDecoration: 'none' }}>
          <EamosLogo size={18} tone="light" />
        </Link>

        <div style={{ maxWidth: 440 }}>
          <p
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 10.5,
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
              color: 'var(--teal)',
              marginBottom: 18,
            }}
          >
            Genomic Intelligence Platform
          </p>
          <h1
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 400,
              fontSize: 'clamp(28px, 3vw, 38px)',
              color: 'var(--ink)',
              lineHeight: 1.15,
              letterSpacing: '-0.02em',
              margin: 0,
            }}
          >
            One query.
            <br />
            Public evidence.
          </h1>
          <p
            style={{
              fontSize: 14.5,
              lineHeight: 1.65,
              color: 'var(--ink-3)',
              marginTop: 18,
              maxWidth: 380,
            }}
          >
            Public genomic evidence, aggregated into one structured report.
            Built for researchers who need a fast orientation and provenance
            they can inspect at every step.
          </p>

          <div
            style={{
              marginTop: 40,
              padding: '18px 20px',
              borderRadius: 'var(--r-lg)',
              background: 'var(--bg-soft)',
              border: '0.5px solid var(--line)',
            }}
          >
            <p
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 12,
                color: 'var(--ink)',
                margin: 0,
                letterSpacing: '-0.01em',
              }}
            >
              NM_000329.3:c.260A&gt;G
            </p>
            <p style={{ fontSize: 12.5, color: 'var(--ink-3)', margin: '4px 0 0' }}>
              RPE65 · p.Asp87Gly · chr1:68,444,869
            </p>
            <div
              className="mt-3 flex items-center gap-2"
              style={{ borderTop: '0.5px solid var(--line)', paddingTop: 12 }}
            >
              <span
                style={{
                  fontSize: 10.5,
                  fontWeight: 600,
                  padding: '2px 9px',
                  borderRadius: 4,
                  background: 'var(--cls-lpath-bg)',
                  color: 'var(--cls-lpath-text)',
                  border: '0.5px solid var(--cls-lpath-bdr)',
                }}
              >
                Likely Pathogenic
              </span>
              <span style={{ fontSize: 11.5, color: 'var(--ink-4)' }}>6 sources</span>
            </div>
          </div>
        </div>

        <p style={{ fontSize: 12, color: 'var(--ink-4)', margin: 0 }}>
          Research use only.{' '}
          <Link href="/terms" style={{ color: 'var(--ink-3)', textDecoration: 'none' }}>
            Terms
          </Link>{' '}
          ·{' '}
          <Link href="/privacy" style={{ color: 'var(--ink-3)', textDecoration: 'none' }}>
            Privacy
          </Link>
        </p>
      </aside>

      {/* Right panel — auth form */}
      <main
        style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '48px 32px',
          background: 'var(--bg-soft)',
        }}
      >
        {/* Mobile logo */}
        <div className="mb-8 lg:hidden">
          <Link href="/" aria-label="Eamos home" style={{ textDecoration: 'none' }}>
            <EamosLogo size={18} tone="light" />
          </Link>
        </div>

        <div style={{ maxWidth: 380, width: '100%', margin: '0 auto' }}>
          <div
            style={{
              background: 'var(--bg)',
              border: '0.5px solid var(--line)',
              borderRadius: 'var(--r-lg)',
              boxShadow: 'var(--elev-2)',
            }}
          >
            <AuthPanel
              onClose={() => router.push('/account')}
              tone="light"
              chromeless
            />
          </div>

          <p
            className="mt-5 text-center"
            style={{ fontSize: 12, color: 'var(--ink-4)' }}
          >
            <Link href="/" style={{ color: 'var(--ink-3)', textDecoration: 'none' }}>
              Back to Eamos
            </Link>
          </p>
        </div>
      </main>
    </div>
  )
}

function AuthSkeleton() {
  return (
    <div
      style={{
        width: 360,
        borderRadius: 'var(--r-lg)',
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        padding: '20px 22px 22px',
      }}
    >
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          style={{
            height: 40,
            borderRadius: 'var(--r-md)',
            background: 'var(--bg-soft2)',
            marginBottom: 12,
            opacity: 1 - i * 0.15,
          }}
        />
      ))}
    </div>
  )
}
