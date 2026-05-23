'use client'
import { useRef, useState } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { EamosLogo } from '@/components/brand/EamosLogo'
import { EamosSearch } from '@/components/landing/EamosSearch'

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
        .fromTo(
          searchRef.current,
          { opacity: 0, scale: 0.96, yPercent: 8 },
          { opacity: 1, scale: 1, yPercent: 0, ease: 'none' },
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

  const sideTransition = 'max-width var(--dur-3) var(--ease-emphasized), opacity var(--dur-2) var(--ease-standard)'

  return (
    <div ref={root} className="sticky top-0 z-50">
      <div
        ref={bgRef}
        aria-hidden
        className="absolute inset-0"
        style={{
          opacity: 0,
          background: 'rgba(4,22,16,0.82)',
          borderBottom: '0.5px solid var(--hero-line)',
          backdropFilter: 'blur(8px)',
        }}
      />

      <div
        className="relative mx-auto flex items-center gap-3 px-4 sm:gap-4 sm:px-8"
        style={{ maxWidth: 1180, height: 56 }}
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
          <a href="/" aria-label="Eamos home" className="flex shrink-0 items-center" style={{ textDecoration: 'none' }}>
            <EamosLogo size={18} tone="dark" />
          </a>
          <button
            ref={upRef}
            type="button"
            onClick={scrollToTop}
            aria-label="Back to top"
            className="inline-flex shrink-0 items-center justify-center transition-colors"
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

        {/* Center: nav links (over the hero) cross-fading with the pinned search */}
        <div className="relative flex min-w-0 flex-1 items-center justify-center">
          <div ref={linksRef} className="absolute flex items-center gap-8">
            {NAV_LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="transition-colors"
                style={{ color: 'var(--hero-ink-2)', fontSize: 13.5, fontWeight: 600, textDecoration: 'none' }}
              >
                {l.label}
              </a>
            ))}
          </div>

          <div
            ref={searchRef}
            className="min-w-0"
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
              transition: 'max-width var(--dur-3) var(--ease-emphasized)',
            }}
          >
            <EamosSearch size="compact" onSubmit={onSubmit} />
          </div>
        </div>

        {/* Right: auth (collapses away when the search expands) */}
        <div
          className="flex items-center gap-2"
          style={{
            maxWidth: expanded ? 0 : 260,
            opacity: expanded ? 0 : 1,
            overflow: 'hidden',
            transition: sideTransition,
            pointerEvents: expanded ? 'none' : 'auto',
          }}
        >
          <a
            href="#"
            className="hidden items-center rounded-[10px] px-3 py-1.5 text-[12.5px] font-semibold transition-colors sm:inline-flex"
            style={{ color: 'var(--hero-ink-2)', textDecoration: 'none' }}
          >
            Sign in
          </a>
          <a
            href="#"
            className="inline-flex shrink-0 items-center rounded-[10px] px-3.5 py-1.5 text-[12.5px] font-semibold transition-colors"
            style={{ color: '#fff', background: 'var(--em)', textDecoration: 'none' }}
          >
            Register
          </a>
        </div>
      </div>
    </div>
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
