'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { CiteModal } from './CiteModal'

export function CiteChip() {
  const [citeOpen, setCiteOpen] = useState(false)
  const citeButtonRef = useRef<HTMLButtonElement>(null)
  const router = useRouter()
  const searchParams = useSearchParams()

  // Open on ?cite=1
  useEffect(() => {
    if (searchParams.get('cite') === '1') {
      setCiteOpen(true)
    }
  }, [searchParams])

  const openCite = useCallback(() => setCiteOpen(true), [])

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
      {/* Bottom-left fixed chip */}
      <div
        style={{
          position: 'fixed',
          bottom: '16px',
          left: '16px',
          zIndex: 900,
          display: 'inline-flex',
          alignItems: 'center',
          gap: '2px',
          background: 'var(--bg)',
          border: '0.5px solid var(--line-2)',
          borderRadius: 'var(--r-md)',
          boxShadow: 'var(--elev-2)',
          padding: '2px',
        }}
      >
        {/* Feedback */}
        <button
          onClick={() => console.log('TODO: feedback')}
          aria-label="Send feedback"
          style={chipBtnStyle}
        >
          <FeedbackIcon />
          Feedback
        </button>

        {/* Divider */}
        <div
          aria-hidden="true"
          style={{
            width: '0.5px',
            height: '18px',
            background: 'var(--line)',
            flexShrink: 0,
          }}
        />

        {/* Cite */}
        <button
          ref={citeButtonRef}
          onClick={openCite}
          aria-label="How to cite Eamos"
          style={chipBtnStyle}
        >
          <CiteIcon />
          Cite
        </button>
      </div>

      {/* Modal */}
      {citeOpen && (
        <CiteModal onClose={closeCite} returnFocusRef={citeButtonRef} />
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

// ── Chip button style (mirrors .eamos-toggle-btn register at compact scale) ──

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
