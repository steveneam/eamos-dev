'use client'
import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useAuth } from '@/components/auth/AuthProvider'
import { AuthPanel } from '@/components/auth/AuthPanel'

type OpenMode = 'auth' | 'account' | null

/**
 * Top-right account control. Signed out → "Sign in / Register" that expands an
 * anchored auth panel in place (not a route). Signed in → an avatar button that
 * drops a small account menu (Account, Sign out). Closes on outside-click / Esc.
 *
 * The open popover is driven by an explicit mode, NOT by `user`, so the auth
 * panel's "Account created — you're in" receipt stays visible after signup (when
 * `user` flips mid-flow) until the user clicks Continue.
 */
export function AuthMenu({ tone = 'dark' }: { tone?: 'dark' | 'light' }) {
  const { user, loading, signOut } = useAuth()
  const [open, setOpen] = useState<OpenMode>(null)
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(null)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(null)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const dark = tone === 'dark'
  const ink = dark ? 'var(--hero-ink-2)' : 'var(--ink-2)'

  return (
    <div ref={root} className="relative">
      {loading ? (
        <div style={{ width: 96, height: 30 }} aria-hidden />
      ) : user ? (
        <button
          type="button"
          onClick={() => setOpen((v) => (v === 'account' ? null : 'account'))}
          aria-haspopup="menu"
          aria-expanded={open === 'account'}
          className="inline-flex items-center gap-2 rounded-[10px] px-2 py-1 transition-colors"
          style={{ border: `0.5px solid ${dark ? 'var(--hero-line)' : 'var(--line)'}`, background: dark ? 'var(--hero-glass)' : 'var(--bg)', cursor: 'pointer' }}
        >
          <Avatar email={user.email ?? ''} />
          <span className="hidden max-w-[140px] truncate text-[12.5px] font-semibold sm:inline" style={{ color: ink }}>
            {user.email}
          </span>
          <Chevron color={ink} />
        </button>
      ) : (
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setOpen('auth')}
            className="hidden items-center rounded-[10px] px-3 py-1.5 text-[12.5px] font-semibold transition-colors sm:inline-flex"
            style={{ color: ink, background: 'transparent', border: 'none', cursor: 'pointer' }}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => setOpen('auth')}
            className="inline-flex shrink-0 items-center rounded-[10px] px-3.5 py-1.5 text-[12.5px] font-semibold transition-colors"
            style={{ color: '#fff', background: 'var(--em)', border: 'none', cursor: 'pointer' }}
          >
            Register
          </button>
        </div>
      )}

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.18, ease: [0.3, 0, 0, 1] }}
            role="dialog"
            aria-label={open === 'account' ? 'Account menu' : 'Sign in or register'}
            // The auth panel anchors to the Register button, which on mobile sits
            // left of the hamburger — so a button-anchored popover gets pushed
            // off-centre. On mobile it becomes a viewport-centred sheet (12px
            // gutters, below the 56px header); from sm+ it's the anchored popover.
            className={
              open === 'account'
                ? 'absolute right-0 z-[60] mt-2 w-[220px] max-w-[calc(100vw-24px)] origin-top-right'
                : 'fixed inset-x-3 top-16 z-[60] origin-top max-w-[calc(100vw-24px)] sm:absolute sm:inset-x-auto sm:right-0 sm:top-auto sm:mt-2 sm:w-[360px] sm:origin-top-right'
            }
            style={{
              borderRadius: 16,
              // Near-solid (was 0.92 + backdrop blur). The blur on a position:fixed
              // mobile sheet caused per-keystroke repaint jank → input lag while
              // typing on mobile. Dropping it (negligible visual change) fixes it.
              background: 'rgba(5,26,19,0.98)',
              border: '0.5px solid var(--hero-line)',
              boxShadow: '0 30px 80px -28px rgba(0,0,0,0.8)',
            }}
          >
            {open === 'account' && user ? (
              <div style={{ padding: 8 }}>
                <div style={{ padding: '8px 10px 10px' }}>
                  <p style={{ fontSize: 11, color: 'var(--hero-ink-3)', margin: 0 }}>Signed in as</p>
                  <p style={{ fontSize: 13, color: 'var(--hero-ink)', margin: '2px 0 0', wordBreak: 'break-all' }}>{user.email}</p>
                </div>
                <a href="/account" style={menuItem} onClick={() => setOpen(null)}>
                  My account
                </a>
                <button
                  type="button"
                  style={{ ...menuItem, width: '100%', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer' }}
                  onClick={async () => {
                    await signOut()
                    setOpen(null)
                  }}
                >
                  Sign out
                </button>
              </div>
            ) : (
              <AuthPanel onClose={() => setOpen(null)} />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

const menuItem: React.CSSProperties = {
  display: 'block',
  padding: '9px 10px',
  borderRadius: 9,
  fontSize: 13,
  fontWeight: 500,
  color: 'var(--hero-ink-2)',
  textDecoration: 'none',
}

function Avatar({ email }: { email: string }) {
  const letter = (email.trim()[0] || 'E').toUpperCase()
  return (
    <span
      aria-hidden
      style={{
        width: 24,
        height: 24,
        borderRadius: 999,
        display: 'grid',
        placeItems: 'center',
        background: 'var(--em)',
        color: '#04140e',
        fontSize: 12,
        fontWeight: 700,
      }}
    >
      {letter}
    </span>
  )
}

function Chevron({ color }: { color: string }) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  )
}
