'use client'
import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useAuth } from '@/components/auth/AuthProvider'
import { AuthPanel } from '@/components/auth/AuthPanel'

type OpenMode = 'auth' | 'account' | null

/**
 * Top-right account control. Signed out: "Sign in / Register" that expands
 * an anchored auth popover (not a route). Signed in: avatar button with a
 * small account menu. Closes on outside-click or Esc.
 *
 * tone="dark"  — dark landing nav (hero-ink tokens, emerald Register button)
 * tone="light" — product nav (warm-white tokens, teal Register button)
 *
 * The open popover mode is driven explicitly so the auth receipt stays visible
 * after signup (user flips mid-flow) until Continue is clicked.
 */
export function AuthMenu({ tone = 'dark' }: { tone?: 'dark' | 'light' }) {
  const { user, loading, signOut } = useAuth()
  const [open, setOpen] = useState<OpenMode>(null)
  const root = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(null)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(null)
        triggerRef.current?.focus()
      }
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const dark = tone === 'dark'

  const ink = dark ? 'var(--hero-ink-2)' : 'var(--ink-2)'
  const borderColor = dark ? 'var(--hero-line)' : 'var(--line)'
  const bgSurface = dark ? 'var(--hero-glass)' : 'var(--bg)'

  return (
    <>
      <AuthMenuStyles />
      <div ref={root} className="relative">
        {loading ? (
          <div style={{ width: 96, height: 30 }} aria-hidden />
        ) : user ? (
          <button
            ref={triggerRef}
            type="button"
            onClick={() => setOpen((v) => (v === 'account' ? null : 'account'))}
            aria-haspopup="menu"
            aria-expanded={open === 'account'}
            className="am-avatar-btn"
            style={{
              border: `0.5px solid ${borderColor}`,
              background: bgSurface,
            }}
          >
            <Avatar email={user.email ?? ''} dark={dark} />
            <span
              className="hidden max-w-[140px] truncate text-[12.5px] font-semibold sm:inline"
              style={{ color: ink }}
            >
              {user.email}
            </span>
            <Chevron color={ink} open={open === 'account'} />
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <button
              ref={triggerRef}
              type="button"
              onClick={() => setOpen('auth')}
              className="am-signin-btn hidden sm:inline-flex"
              style={{ color: ink }}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => setOpen('auth')}
              className="am-register-btn"
              style={{
                color: dark ? 'var(--em-ink)' : '#fff',
                background: dark ? 'var(--em)' : 'var(--teal)',
              }}
            >
              Register
            </button>
          </div>
        )}

        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, y: -6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.98 }}
              transition={{ duration: 0.18, ease: [0.2, 0, 0, 1] }}
              role={open === 'account' ? 'menu' : 'dialog'}
              aria-label={open === 'account' ? 'Account menu' : 'Sign in or register'}
              className={
                open === 'account'
                  ? 'absolute right-0 z-[60] mt-2 w-[220px] max-w-[calc(100vw-24px)] origin-top-right'
                  : 'fixed inset-x-3 top-16 z-[60] origin-top max-w-[calc(100vw-24px)] sm:absolute sm:inset-x-auto sm:right-0 sm:top-auto sm:mt-2 sm:w-[360px] sm:origin-top-right'
              }
              style={{
                borderRadius: 'var(--r-lg)',
                background: dark ? 'rgba(5,26,19,0.98)' : 'var(--bg)',
                border: `0.5px solid ${dark ? 'var(--hero-line)' : 'var(--line)'}`,
                boxShadow: 'var(--elev-3)',
              }}
            >
              {open === 'account' && user ? (
                <AccountDropdown
                  email={user.email ?? ''}
                  dark={dark}
                  onClose={() => setOpen(null)}
                  onSignOut={async () => {
                    await signOut()
                    setOpen(null)
                  }}
                />
              ) : (
                <AuthPanel onClose={() => setOpen(null)} tone={tone} />
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  )
}

function AccountDropdown({
  email,
  dark,
  onClose,
  onSignOut,
}: {
  email: string
  dark: boolean
  onClose: () => void
  onSignOut: () => Promise<void>
}) {
  const [signingOut, setSigningOut] = useState(false)

  const handleSignOut = async () => {
    if (signingOut) return
    setSigningOut(true)
    await onSignOut()
    setSigningOut(false)
  }

  return (
    <div style={{ padding: 8 }}>
      <div style={{ padding: '8px 10px 10px' }}>
        <p
          style={{
            fontSize: 11,
            color: dark ? 'var(--hero-ink-3)' : 'var(--ink-4)',
            margin: 0,
          }}
        >
          Signed in as
        </p>
        <p
          style={{
            fontSize: 13,
            color: dark ? 'var(--hero-ink)' : 'var(--ink)',
            margin: '2px 0 0',
            wordBreak: 'break-all',
          }}
        >
          {email}
        </p>
      </div>
      <a
        href="/account"
        role="menuitem"
        className="am-menu-item"
        data-dark={dark ? '' : undefined}
        onClick={onClose}
      >
        My account
      </a>
      <button
        type="button"
        role="menuitem"
        className="am-menu-item am-menu-btn"
        data-dark={dark ? '' : undefined}
        disabled={signingOut}
        aria-busy={signingOut}
        onClick={handleSignOut}
      >
        {signingOut ? 'Signing out…' : 'Sign out'}
      </button>
    </div>
  )
}

// ── scoped styles ────────────────────────────────────────────────────────────
function AuthMenuStyles() {
  return (
    <style>{`
      .am-avatar-btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border-radius: 10px;
        padding: 4px 8px;
        cursor: pointer;
        transition: border-color var(--dur-1) var(--ease-standard),
                    box-shadow var(--dur-1) var(--ease-standard);
      }
      .am-avatar-btn:hover {
        box-shadow: var(--elev-1);
      }
      .am-avatar-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.15);
      }

      .am-signin-btn {
        align-items: center;
        border-radius: 10px;
        padding: 6px 12px;
        font-size: 12.5px;
        font-weight: 600;
        background: transparent;
        border: none;
        cursor: pointer;
        transition:
          background var(--dur-1) var(--ease-standard),
          color var(--dur-1) var(--ease-standard);
        outline: none;
      }
      /* tone="light" (landing) */
      .am-signin-btn:hover {
        background: color-mix(in oklab, var(--em) 8%, transparent);
        color: var(--hero-ink) !important;
      }
      .am-signin-btn:active { transform: scale(0.97); }
      .am-signin-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--em) 22%, transparent);
        border-radius: 10px;
      }

      .am-register-btn {
        display: inline-flex;
        align-items: center;
        border-radius: 10px;
        padding: 6px 14px;
        font-size: 12.5px;
        font-weight: 600;
        border: none;
        cursor: pointer;
        flex-shrink: 0;
        transition:
          background var(--dur-1) var(--ease-standard),
          transform var(--dur-1) var(--ease-standard),
          box-shadow var(--dur-1) var(--ease-standard);
        outline: none;
      }
      .am-register-btn:hover { filter: brightness(0.9); }
      .am-register-btn:active { transform: scale(0.97); }
      .am-register-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--em) 28%, transparent);
      }

      .am-menu-item {
        display: block;
        padding: 9px 10px;
        border-radius: 9px;
        font-size: 13px;
        font-weight: 500;
        color: var(--ink-2);
        text-decoration: none;
        transition: background var(--dur-1) var(--ease-standard),
                    color var(--dur-1) var(--ease-standard);
      }
      .am-menu-item[data-dark] { color: var(--hero-ink-2); }
      .am-menu-item:hover { background: var(--bg-soft2); color: var(--ink); }
      .am-menu-item[data-dark]:hover { background: rgba(255,255,255,0.06); color: var(--hero-ink); }
      .am-menu-item:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.12);
      }
      .am-menu-item:disabled { opacity: 0.6; cursor: not-allowed; }

      .am-menu-btn {
        width: 100%;
        text-align: left;
        background: none;
        border: none;
        cursor: pointer;
      }
      .am-menu-btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    `}</style>
  )
}

function Avatar({ email, dark }: { email: string; dark: boolean }) {
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
        background: dark ? 'var(--em)' : 'var(--teal)',
        color: dark ? 'var(--em-ink)' : '#fff',
        fontSize: 12,
        fontWeight: 700,
        flexShrink: 0,
      }}
    >
      {letter}
    </span>
  )
}

function Chevron({ color, open }: { color: string; open: boolean }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={2.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      style={{
        transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        transition: 'transform var(--dur-2) var(--ease-standard)',
      }}
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  )
}
