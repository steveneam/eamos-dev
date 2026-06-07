'use client'

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { CiteModal } from './CiteModal'

// Pinned monthly snapshot — bump when the report payload shape ships a breaking change.
const REPORT_VERSION = '2026.05'

// Collapsed-pref store for the bottom-left dock. useSyncExternalStore keeps it
// SSR-safe (server renders expanded) with no setState-in-effect — the user can
// tuck the dock away when the rail content reaches the bottom of the viewport.
const DOCK_KEY = 'eamos.cite-dock.collapsed'
const DOCK_EVENT = 'eamos:cite-dock'

function subscribeDock(onChange: () => void) {
  window.addEventListener('storage', onChange)
  window.addEventListener(DOCK_EVENT, onChange)
  return () => {
    window.removeEventListener('storage', onChange)
    window.removeEventListener(DOCK_EVENT, onChange)
  }
}
function getDockSnapshot(): boolean {
  try {
    return localStorage.getItem(DOCK_KEY) === '1'
  } catch {
    return false
  }
}
function getDockServerSnapshot(): boolean {
  return false
}

function formatDate(d: Date): string {
  // AU-style human date for citations (eg. "28 May 2026"). No locale dependency
  // for SSR safety: month name table is fixed.
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`
}

export function CiteChip() {
  const [citeOpen, setCiteOpen] = useState(false)
  // Ref is on the bottom-left Feedback chip wrapper now — the modal's
  // return-focus target lands on a stable on-screen element regardless of
  // viewport (the rail's Cite button is hidden < xl).
  const citeButtonRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  // Collapsed (hidden) preference — persisted, SSR-safe.
  const collapsed = useSyncExternalStore(subscribeDock, getDockSnapshot, getDockServerSnapshot)
  const setCollapsed = useCallback((next: boolean) => {
    try {
      localStorage.setItem(DOCK_KEY, next ? '1' : '0')
    } catch {
      /* private mode — ignore */
    }
    if (typeof window !== 'undefined') window.dispatchEvent(new Event(DOCK_EVENT))
  }, [])

  // {variant_display} resolves on /report routes from URL params; off-report → null.
  const variantDisplay = useMemo(() => {
    if (pathname !== '/report') return null
    const gene = searchParams.get('gene')?.trim()
    const cdna = searchParams.get('cdna')?.trim()
    const protein = searchParams.get('protein_change')?.trim()
    const q = searchParams.get('q')?.trim()
    const fixture = searchParams.get('fixture')?.trim()
    if (gene && cdna) return [gene, cdna, protein ? `(${protein})` : ''].filter(Boolean).join(' ').trim()
    if (q) return q
    if (fixture === 'rpe65-negative') return 'RPE65 c.260A>G'
    return 'USH2A c.2276G>T'
  }, [pathname, searchParams])

  // {date} resolved per-open so it reflects the actual access moment.
  const [date, setDate] = useState<string | null>(null)

  // Open on ?cite=1
  useEffect(() => {
    if (searchParams.get('cite') === '1') {
      let cancelled = false
      void Promise.resolve().then(() => {
        if (cancelled) return
        setCiteOpen(true)
        setDate(formatDate(new Date()))
      })
      return () => {
        cancelled = true
      }
    }
    return undefined
  }, [searchParams])

  const openCite = useCallback(() => {
    setCiteOpen(true)
    setDate(formatDate(new Date()))
  }, [])

  // Feedback intake — mailto to sales@eamos.com.au with the current report
  // URL + variant prefilled so the user only types the message body. Subject
  // includes the variant display (when on /report) so triage can route it.
  const openFeedback = useCallback(() => {
    const subjectVariant = variantDisplay ? ` — ${variantDisplay}` : ''
    const subject = `Eamos feedback${subjectVariant}`
    const url = typeof window !== 'undefined' ? window.location.href : ''
    const body = `\n\n--\nPage: ${url}${variantDisplay ? `\nVariant: ${variantDisplay}` : ''}\nReport version: ${REPORT_VERSION}`
    const href = `mailto:sales@eamos.com.au?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
    if (typeof window !== 'undefined') {
      window.location.href = href
    }
  }, [variantDisplay])

  const closeCite = useCallback(() => {
    setCiteOpen(false)
    // Optionally strip the param — best-effort; ignore if router not available
    try {
      const params = new URLSearchParams(window.location.search)
      if (params.has('cite')) {
        params.delete('cite')
        const newSearch = params.toString()
        router.replace(
          window.location.pathname + (newSearch ? `?${newSearch}` : ''),
          { scroll: false },
        )
      }
    } catch {
      // ignore navigation errors in non-browser contexts
    }
  }, [router])

  return (
    <>
      {/* Bottom-left fixed Feedback + Cite dock. Both actions live here now
          that the right-side TOC rail was removed — CiteChip owns the modal
          mount + the `?cite=1` URL-param listener so the Cite button and any
          deep link open the modal through the same path. Collapses to a small
          launcher so it never covers the bottom of the WorkRail. */}
      <div ref={citeButtonRef} style={dockWrapStyle}>
        {collapsed ? (
          <button
            type="button"
            onClick={() => setCollapsed(false)}
            aria-label="Show cite and feedback"
            title="Cite & feedback"
            style={launcherStyle}
          >
            <ChevronsRightIcon />
          </button>
        ) : (
          <div style={dockStyle}>
            <button
              type="button"
              onClick={openFeedback}
              aria-label="Send feedback to sales@eamos.com.au"
              style={chipBtnStyle}
            >
              <FeedbackIcon />
              Feedback
            </button>
            <span style={dockDividerStyle} />
            <button type="button" onClick={openCite} aria-label="Cite this report" style={chipBtnStyle}>
              <CiteIcon />
              Cite
            </button>
            <span style={dockDividerStyle} />
            <button
              type="button"
              onClick={() => setCollapsed(true)}
              aria-label="Hide cite and feedback"
              title="Hide"
              style={hideBtnStyle}
            >
              <ChevronsLeftIcon />
            </button>
          </div>
        )}
      </div>

      {/* Modal */}
      {citeOpen && (
        <CiteModal
          onClose={closeCite}
          returnFocusRef={citeButtonRef}
          variantDisplay={variantDisplay}
          date={date}
          reportVersion={REPORT_VERSION}
        />
      )}
    </>
  )
}

// ── Icon helpers (inline SVG, no dependency) ────────────────────────────────

function FeedbackIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}

function CiteIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 7V4h7" />
      <path d="M4 20v-3" />
      <path d="M17 4h3v3" />
      <path d="M20 20h-3" />
      <rect x="8" y="8" width="8" height="8" rx="1" />
    </svg>
  )
}

const chevronProps = {
  width: 13,
  height: 13,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
}

// «  — tuck the dock to the corner.
function ChevronsLeftIcon() {
  return (
    <svg {...chevronProps}>
      <polyline points="11 17 6 12 11 7" />
      <polyline points="18 17 13 12 18 7" />
    </svg>
  )
}

// »  — pull the dock back out.
function ChevronsRightIcon() {
  return (
    <svg {...chevronProps}>
      <polyline points="13 17 18 12 13 7" />
      <polyline points="6 17 11 12 6 7" />
    </svg>
  )
}

// ── Dock layout + chip button styles (compact register) ──

const dockWrapStyle: React.CSSProperties = {
  position: 'fixed',
  bottom: '16px',
  left: '16px',
  zIndex: 900,
}

const dockStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '2px',
  background: 'var(--bg)',
  border: '0.5px solid var(--line-2)',
  borderRadius: 'var(--r-md)',
  boxShadow: 'var(--elev-2)',
  padding: '2px',
}

const dockDividerStyle: React.CSSProperties = {
  width: '0.5px',
  alignSelf: 'stretch',
  background: 'var(--line-2)',
  margin: '2px 0',
}

const chipBtnStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '5px',
  padding: '5px 10px',
  background: 'transparent',
  color: 'var(--ink-2)',
  border: 'none',
  borderRadius: '8px',
  fontFamily: 'var(--body)',
  fontSize: '12px',
  fontWeight: 600,
  lineHeight: 1.2,
  cursor: 'pointer',
  transition: 'background 120ms ease, color 120ms ease',
}

// Icon-only "hide" affordance at the end of the dock.
const hideBtnStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '5px 7px',
  background: 'transparent',
  color: 'var(--ink-4)',
  border: 'none',
  borderRadius: '8px',
  cursor: 'pointer',
  transition: 'background 120ms ease, color 120ms ease',
}

// Collapsed launcher — a small rounded chip that restores the dock.
const launcherStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '30px',
  height: '30px',
  background: 'var(--bg)',
  color: 'var(--ink-3)',
  border: '0.5px solid var(--line-2)',
  borderRadius: 'var(--r-md)',
  boxShadow: 'var(--elev-2)',
  cursor: 'pointer',
}
