'use client'
import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { EamosLogo } from '@/components/brand/EamosLogo'
import { EamosSearch } from '@/components/landing/EamosSearch'
import { AuthMenu } from '@/components/auth/AuthMenu'

const NAV_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'FAQ', href: '#faq' },
]

export function LandingNav({ onSubmit }: { onSubmit: (query: string) => void }) {
  const root = useRef<HTMLDivElement>(null)
  const bgRef = useRef<HTMLDivElement>(null)
  const linksRef = useRef<HTMLDivElement>(null)
  const upRef = useRef<HTMLButtonElement>(null)
  const searchRef = useRef<HTMLDivElement>(null)
  const [expanded, setExpanded] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  // Mobile menu: close on outside-click / Esc. Links + the panel both carry
  // [data-mobile-menu] so a click on either keeps it open.
  useEffect(() => {
    if (!menuOpen) return
    const onDown = (e: MouseEvent) => {
      if (!(e.target as HTMLElement).closest('[data-mobile-menu]')) setMenuOpen(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setMenuOpen(false)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [menuOpen])

  useGSAP(
    () => {
      gsap.registerPlugin(ScrollTrigger)
      // Trigger off the hero (a normal-flow element) via a global query — not a
      // useGSAP-scoped selector string (which would look inside the nav) and not
      // the sticky nav itself (a sticky element misreports its position to
      // ScrollTrigger). One scrubbed timeline ties the whole nav handoff to
      // scroll position so it glides instead of snapping: the hero search
      // scrolls away while the bar solidifies, links fade out, and the compact
      // search fades in.
      const hero = document.querySelector('#hero')
      if (!hero) return
      const tl = gsap.timeline({
        scrollTrigger: { trigger: hero, start: 'top top', end: '+=440', scrub: 0.6 },
      })
      tl.to(bgRef.current, { opacity: 1, ease: 'none' }, 0)
        .to(linksRef.current, { opacity: 0, y: -6, pointerEvents: 'none', ease: 'none' }, 0)
        .fromTo(upRef.current, { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, ease: 'none' }, 0)
        // The compact search starts invisible AND pointer-inert — otherwise its
        // input sits on top of the nav links at scroll=0 and swallows mouse
        // clicks (the links work via keyboard/.click() but not by pointing).
        .fromTo(
          searchRef.current,
          { opacity: 0, scale: 0.96, yPercent: 8, pointerEvents: 'none' },
          { opacity: 1, scale: 1, yPercent: 0, pointerEvents: 'auto', ease: 'none' },
          0,
        )
    },
    { scope: root },
  )

  const scrollToTop = () =>
    window.scrollTo({
      top: 0,
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    })

  const sideTransition = 'max-width 460ms var(--ease-emphasized), opacity 300ms var(--ease-standard)'

  return (
    <>
      <LandingNavStyles />
      <div ref={root} className="sticky top-0 z-50">
        <div
          ref={bgRef}
          aria-hidden
          className="absolute inset-0"
          style={{
            opacity: 0,
            // Solid-ish, no blur. A sticky backdrop-filter:blur repaints on every
            // keystroke anywhere on the page — mobile typing lag. Warm near-white so
            // the scrolled nav reads as the cream cover firming up.
            background: 'rgba(252,249,243,0.96)',
            borderBottom: '0.5px solid var(--hero-line)',
          }}
        />

        <div
          className="relative mx-auto flex items-center gap-3 px-4 sm:gap-4 sm:px-8"
          style={{ maxWidth: 1180, height: 'var(--nav-h)' }}
        >
          {/* Left: logo + back-to-top (collapses away when the search expands) */}
          <div
            className="flex items-center gap-2"
            style={{
              maxWidth: expanded ? 0 : 240,
              opacity: expanded ? 0 : 1,
              overflow: 'hidden',
              transition: sideTransition,
              pointerEvents: expanded ? 'none' : 'auto',
            }}
          >
            <a href="/" aria-label="Eamos home" className="lnav-home-link flex shrink-0 items-center">
              <EamosLogo size={18} tone="light" />
            </a>
            <button
              ref={upRef}
              type="button"
              onClick={scrollToTop}
              aria-label="Back to top"
              className="lnav-icon-btn inline-flex shrink-0 items-center justify-center"
              style={{
                width: 30,
                height: 30,
                borderRadius: 999,
                background: 'var(--hero-glass)',
                border: '0.5px solid var(--hero-line)',
                color: 'var(--hero-ink-2)',
                cursor: 'pointer',
                opacity: 0,
              }}
            >
              <UpIcon />
            </button>
          </div>

          {/* Center: nav links (over the hero) cross-fading with the pinned search.
              On mobile this region instead holds the menu toggle, centered between
              the logo and the auth button. */}
          <div className="relative flex min-w-0 flex-1 items-center justify-center">
            <button
              data-mobile-menu
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={menuOpen}
              aria-controls="mobile-nav-menu"
              className="lnav-icon-btn inline-flex shrink-0 items-center justify-center md:hidden"
              style={{
                width: 34,
                height: 34,
                borderRadius: 10,
                background: 'var(--hero-glass)',
                border: '0.5px solid var(--hero-line)',
                color: 'var(--hero-ink)',
                cursor: 'pointer',
              }}
            >
              {menuOpen ? <CloseIcon /> : <MenuIcon />}
            </button>
            <div ref={linksRef} className="absolute hidden items-center gap-8 md:flex">
              {NAV_LINKS.map((l) => (
                <a
                  key={l.href}
                  href={l.href}
                  className="lnav-link"
                  style={{ fontSize: 13.5, fontWeight: 600 }}
                >
                  {l.label}
                </a>
              ))}
            </div>

            <div
              ref={searchRef}
              className="hidden min-w-0 md:block"
              onFocus={() => setExpanded(true)}
              onBlur={(e) => {
                if (!searchRef.current?.contains(e.relatedTarget as Node | null)) setExpanded(false)
              }}
              style={{
                opacity: 0,
                width: '100%',
                maxWidth: expanded ? 1180 : 400,
                marginLeft: 'auto',
                marginRight: 'auto',
                transition: 'max-width 460ms var(--ease-emphasized)',
              }}
            >
              <EamosSearch size="compact" tone="light" onSubmit={onSubmit} />
            </div>
          </div>

          {/* Right: auth + mobile menu toggle (collapses away when search expands) */}
          <div
            className="flex items-center justify-end gap-2"
            style={{
              maxWidth: expanded ? 0 : 260,
              opacity: expanded ? 0 : 1,
              overflow: 'visible',
              transition: sideTransition,
              pointerEvents: expanded ? 'none' : 'auto',
            }}
          >
            <AuthMenu tone="light" />
          </div>
        </div>

        {/* Mobile dropdown menu — the nav links, expanded on tap (md and below) */}
        <AnimatePresence>
          {menuOpen && (
            <motion.div
              data-mobile-menu
              id="mobile-nav-menu"
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18, ease: [0.3, 0, 0, 1] }}
              className="absolute left-0 right-0 md:hidden"
              style={{
                top: 56,
                // Opaque warm near-white — backdrop-filter:blur on a sticky
                // overlay repaints on every keystroke (mobile typing lag).
                background: 'rgb(250,246,239)',
                borderBottom: '0.5px solid var(--hero-line)',
                boxShadow: '0 8px 24px -16px rgba(40,28,12,0.18)',
              }}
            >
              <nav className="mx-auto flex flex-col px-4 py-1.5" style={{ maxWidth: 1180 }}>
                {NAV_LINKS.map((l, i) => (
                  <a
                    key={l.href}
                    href={l.href}
                    onClick={() => setMenuOpen(false)}
                    className="lnav-mobile-link"
                    style={{
                      padding: '13px 8px',
                      fontSize: 15,
                      fontWeight: 600,
                      borderTop: i === 0 ? 'none' : '0.5px solid var(--hero-line)',
                    }}
                  >
                    {l.label}
                  </a>
                ))}
              </nav>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  )
}

function LandingNavStyles() {
  return (
    <style>{`
      /* Nav text links (desktop) */
      .lnav-link {
        color: var(--hero-ink-2);
        text-decoration: none;
        transition: color var(--dur-1) var(--ease-standard);
        border-radius: 3px;
        outline: none;
      }
      .lnav-link:hover { color: var(--hero-ink); }
      .lnav-link:focus-visible {
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--em) 22%, transparent);
      }

      /* Mobile dropdown links */
      .lnav-mobile-link {
        display: block;
        color: var(--hero-ink-2);
        text-decoration: none;
        transition: color var(--dur-1) var(--ease-standard);
        border-radius: 4px;
        outline: none;
      }
      .lnav-mobile-link:hover { color: var(--hero-ink); }
      .lnav-mobile-link:focus-visible {
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--em) 22%, transparent);
      }

      /* Icon buttons: back-to-top + mobile menu toggle */
      .lnav-icon-btn {
        transition:
          background var(--dur-1) var(--ease-standard),
          border-color var(--dur-1) var(--ease-standard),
          color var(--dur-1) var(--ease-standard),
          transform var(--dur-1) var(--ease-standard);
        outline: none;
      }
      .lnav-icon-btn:hover {
        background: var(--hero-glass2) !important;
        border-color: var(--em) !important;
        color: var(--hero-ink) !important;
      }
      .lnav-icon-btn:active { transform: scale(0.95); }
      .lnav-icon-btn:focus-visible {
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--em) 22%, transparent);
      }

      /* Home logo link */
      .lnav-home-link {
        text-decoration: none;
        border-radius: 4px;
        outline: none;
        transition: opacity var(--dur-1) var(--ease-standard);
      }
      .lnav-home-link:hover { opacity: 0.8; }
      .lnav-home-link:focus-visible {
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--em) 22%, transparent);
      }
    `}</style>
  )
}

function UpIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <line x1="12" y1="19" x2="12" y2="5" />
      <polyline points="5 12 12 5 19 12" />
    </svg>
  )
}

function MenuIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden>
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden>
      <line x1="6" y1="6" x2="18" y2="18" />
      <line x1="6" y1="18" x2="18" y2="6" />
    </svg>
  )
}
