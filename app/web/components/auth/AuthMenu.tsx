'use client'
import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import Link from 'next/link'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useAuth } from '@/components/auth/AuthProvider'
import { AuthPanel } from '@/components/auth/AuthPanel'
import { buildFeedbackMailto } from '@/lib/report-feedback'

type OpenMode = 'auth' | 'account' | null
type Placement = 'nav' | 'rail-foot'

// Client-mounted flag via useSyncExternalStore — false on the server + first
// hydration render, true thereafter. SSR-safe with no setState-in-effect, so the
// portal only reaches document.body on the client.
const emptySubscribe = () => () => {}

/**
 * Account control. Two placements, one menu:
 *
 *  - `nav` (default): top-right of a TopNav/landing bar. Signed out → "Sign in
 *    / Register" expands an anchored auth popover; signed in → avatar button +
 *    account menu, both anchored top-right.
 *  - `rail-foot`: a full-width row pinned in the <WorkRail> foot. The popover
 *    opens UPWARD and PORTALS to <body> so the rail's `overflow:hidden` +
 *    sticky stacking context can't clip it (docs/workbench-task-a STEP 2).
 *
 * Closes on outside-click (root or portalled popover) or Esc.
 *
 * tone="dark"  — dark landing nav (hero-ink tokens, emerald Register button)
 * tone="light" — product nav (warm-white tokens, teal Register button)
 */
export function AuthMenu({
  tone = 'dark',
  placement = 'nav',
}: {
  tone?: 'dark' | 'light'
  placement?: Placement
}) {
  const { user, loading, signOut } = useAuth()
  const [open, setOpen] = useState<OpenMode>(null)
  const root = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const popRef = useRef<HTMLDivElement>(null)
  const railFoot = placement === 'rail-foot'

  // Portals touch `document` — only render after mount so SSR (and the first
  // client render, which must match it) never reaches document.body.
  const mounted = useSyncExternalStore(emptySubscribe, () => true, () => false)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node
      // Portalled popover lives outside `root`, so check it explicitly.
      if (!root.current?.contains(t) && !popRef.current?.contains(t)) setOpen(null)
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

  // Rail-foot popover position — fixed coords measured off the trigger, opening
  // upward. Recomputed on open + on scroll/resize while open.
  const [pos, setPos] = useState<{ left: number; bottom: number; minWidth: number } | null>(null)
  useEffect(() => {
    if (!railFoot || !open) return
    const measure = () => {
      const r = triggerRef.current?.getBoundingClientRect()
      if (!r) return
      setPos({ left: r.left, bottom: window.innerHeight - r.top + 8, minWidth: r.width })
    }
    measure()
    window.addEventListener('resize', measure)
    window.addEventListener('scroll', measure, true)
    return () => {
      window.removeEventListener('resize', measure)
      window.removeEventListener('scroll', measure, true)
    }
  }, [railFoot, open])

  const dark = tone === 'dark'

  const ink = dark ? 'var(--hero-ink-2)' : 'var(--ink-2)'
  const borderColor = dark ? 'var(--hero-line)' : 'var(--line)'
  const bgSurface = dark ? 'var(--hero-glass)' : 'var(--bg)'

  const popoverInner =
    open === 'account' && user ? (
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
    )

  const popoverChrome = {
    borderRadius: 'var(--r-lg)',
    background: dark ? 'rgba(5,26,19,0.98)' : 'var(--bg)',
    border: `0.5px solid ${dark ? 'var(--hero-line)' : 'var(--line)'}`,
    boxShadow: 'var(--elev-3)',
  } as const

  return (
    <>
      <AuthMenuStyles />
      <div ref={root} className={railFoot ? 'wr-foot-am' : 'relative'}>
        {loading ? (
          railFoot ? (
            <div className="wr-foot-row" aria-hidden style={{ height: 36 }} />
          ) : (
            <div style={{ width: 96, height: 30 }} aria-hidden />
          )
        ) : user ? (
          railFoot ? (
            <button
              ref={triggerRef}
              type="button"
              onClick={() => setOpen((v) => (v === 'account' ? null : 'account'))}
              aria-haspopup="menu"
              aria-expanded={open === 'account'}
              className="wr-foot-row wr-foot-account"
              title={user.email ?? 'Account'}
            >
              <Avatar email={user.email ?? ''} dark={false} />
              <span className="wr-foot-email">{user.email}</span>
              <ChevronUp open={open === 'account'} />
            </button>
          ) : (
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
          )
        ) : railFoot ? (
          <button
            ref={triggerRef}
            type="button"
            onClick={() => setOpen('auth')}
            aria-haspopup="dialog"
            aria-expanded={open === 'auth'}
            className="wr-foot-row wr-foot-signin"
            title="Sign in or register"
          >
            <SignInGlyph />
            <span className="wr-foot-signin-label">Sign in / Register</span>
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

        {/* Nav popover — anchored within the relative parent. */}
        {!railFoot && (
          <AnimatePresence>
            {open && (
              <motion.div
                ref={popRef}
                initial={{ opacity: 0, y: -6, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -6, scale: 0.98 }}
                transition={{ duration: 0.18, ease: [0.2, 0, 0, 1] }}
                role={open === 'account' ? 'menu' : 'dialog'}
                aria-label={open === 'account' ? 'Account menu' : 'Sign in or register'}
                className={
                  open === 'account'
                    ? 'absolute right-0 mt-2 w-[220px] max-w-[calc(100vw-24px)] origin-top-right'
                    : 'fixed inset-x-3 top-16 origin-top max-w-[calc(100vw-24px)] sm:absolute sm:inset-x-auto sm:right-0 sm:top-auto sm:mt-2 sm:w-[360px] sm:origin-top-right'
                }
                style={{ zIndex: 'var(--z-popover)', ...popoverChrome }}
              >
                {popoverInner}
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </div>

      {/* Rail-foot popover — PORTAL wraps AnimatePresence (a portal can't be an
          AnimatePresence child), so it escapes the rail's overflow:hidden and
          opens upward off the trigger rect. */}
      {railFoot &&
        mounted &&
        createPortal(
          <AnimatePresence>
            {open && (
              <motion.div
                ref={popRef}
                initial={{ opacity: 0, y: 6, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 6, scale: 0.98 }}
                transition={{ duration: 0.18, ease: [0.2, 0, 0, 1] }}
                role={open === 'account' ? 'menu' : 'dialog'}
                aria-label={open === 'account' ? 'Account menu' : 'Sign in or register'}
                style={{
                  position: 'fixed',
                  left: pos?.left ?? 16,
                  bottom: pos?.bottom ?? 16,
                  width: open === 'account' ? 220 : 360,
                  maxWidth: 'calc(100vw - 24px)',
                  maxHeight: 'calc(100vh - 120px)',
                  overflowY: 'auto',
                  transformOrigin: 'bottom left',
                  zIndex: 'var(--z-popover)',
                  ...popoverChrome,
                }}
              >
                {popoverInner}
              </motion.div>
            )}
          </AnimatePresence>,
          document.body,
        )}
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
      <Link
        href="/#pricing"
        role="menuitem"
        className="am-menu-item"
        data-dark={dark ? '' : undefined}
        onClick={onClose}
      >
        Billing &amp; plans
      </Link>
      <button
        type="button"
        role="menuitem"
        className="am-menu-item am-menu-btn"
        data-dark={dark ? '' : undefined}
        onClick={() => {
          window.location.href = buildFeedbackMailto()
          onClose()
        }}
      >
        Send feedback
      </button>
      <span className="am-menu-sep" data-dark={dark ? '' : undefined} aria-hidden="true" />
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

      .am-menu-sep {
        display: block;
        height: 0.5px;
        margin: 4px 6px;
        background: var(--line);
      }
      .am-menu-sep[data-dark] { background: var(--hero-line); }
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

/** Rail-foot account chevron — points up (menu opens upward), flips down when open. */
function ChevronUp({ open }: { open: boolean }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className="wr-foot-chev"
      style={{
        transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        transition: 'transform var(--dur-2) var(--ease-standard)',
      }}
    >
      <polyline points="18 15 12 9 6 15" />
    </svg>
  )
}

/** Sign-in door glyph for the signed-out rail-foot row. */
function SignInGlyph() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className="wr-foot-signin-ico"
    >
      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
      <polyline points="10 17 15 12 10 7" />
      <line x1="15" y1="12" x2="3" y2="12" />
    </svg>
  )
}
