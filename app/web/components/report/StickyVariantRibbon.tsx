'use client'

import { useEffect, useRef, useState } from 'react'
import { SaveCurrentButton } from './VariantLibraryRail'
import type { LookupResponse } from '@/lib/backend'

export interface StickyVariantRibbonProps {
  hgvsC?: string
  hgvsP?: string
  transcript?: string
  gene?: string
  /** Threaded so the ribbon's Save reuses the one library save path (matches the hero). */
  data?: LookupResponse
  onShare?: () => void
  onExport?: () => void
  /** When provided, replaces the plain Export button (e.g. the ExportMenu dropdown). */
  exportSlot?: React.ReactNode
  className?: string
}

// Inline SVGs — Lucide-style, 16×16 viewBox, 1.5px stroke
const IconShare = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="12" cy="3" r="1.5" />
    <circle cx="4" cy="8" r="1.5" />
    <circle cx="12" cy="13" r="1.5" />
    <path d="M5.5 7.25l5 -3M5.5 8.75l5 3" />
  </svg>
)
const IconExport = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M8 2v8M5 7l3 3 3-3" />
    <path d="M3 11v2a1 1 0 001 1h8a1 1 0 001-1v-2" />
  </svg>
)

// Threshold (px) past which the ribbon pins; covers the variant header height.
const SCROLL_THRESHOLD = 200

export function StickyVariantRibbon({
  hgvsC,
  hgvsP,
  transcript,
  gene,
  data,
  onShare,
  onExport,
  exportSlot,
  className,
}: StickyVariantRibbonProps) {
  const [pinned, setPinned] = useState(false)
  const reducedMotion = useRef(false)

  useEffect(() => {
    reducedMotion.current =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const handleScroll = () => {
      setPinned(window.scrollY > SCROLL_THRESHOLD)
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    // Sync on mount in case page loaded mid-scroll
    handleScroll()

    return () => {
      window.removeEventListener('scroll', handleScroll)
    }
  }, [])

  // If no HGVS notation, render nothing
  if (!hgvsC) return null

  // Label: "RPE65 NM_000329.3:c.260A>G (p.Tyr87Cys)" or whatever subset is present
  const label = [
    gene,
    transcript && hgvsC ? `${transcript}:${hgvsC}` : hgvsC,
    hgvsP ? `(${hgvsP})` : undefined,
  ]
    .filter(Boolean)
    .join(' ')

  const noMotion = reducedMotion.current

  return (
    <div
      role="toolbar"
      aria-label="Variant actions"
      className={className}
      style={{
        position: 'fixed',
        top: 60,
        left: 0,
        right: 0,
        zIndex: 40,
        background: 'var(--bg)',
        borderBottom: '0.5px solid var(--line)',
        boxShadow: pinned
          ? '0 2px 8px -2px rgba(11,26,43,0.12), 0 0 0 0.5px var(--line)'
          : 'none',
        // Visibility: hidden when not pinned to keep it out of tab order
        opacity: pinned ? 1 : 0,
        pointerEvents: pinned ? 'auto' : 'none',
        transform: pinned
          ? 'translateY(0)'
          : noMotion
          ? 'translateY(0)'
          : 'translateY(-6px)',
        transition: noMotion
          ? 'opacity 0ms'
          : 'opacity 150ms ease, transform 150ms ease, box-shadow 150ms ease',
        visibility: pinned ? 'visible' : 'hidden',
      }}
    >
      <div
        style={{
          maxWidth: 'var(--maxw-report, 860px)',
          margin: '0 auto',
          padding: '0 24px',
          height: 44,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
        }}
      >
        {/* Left: HGVS label */}
        <span
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 13,
            fontWeight: 500,
            color: 'var(--ink)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flex: '1 1 0',
            minWidth: 0,
          }}
        >
          {label}
        </span>

        {/* Right: action cluster — Save · Export · Share, matching the hero. */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          {data && <SaveCurrentButton data={data} variant="hero" />}
          {exportSlot ?? <RibbonBtn label="Export" icon={<IconExport />} onClick={onExport} />}
          <RibbonBtn label="Share" icon={<IconShare />} onClick={onShare} />
        </div>
      </div>
    </div>
  )
}

interface RibbonBtnProps {
  label: string
  icon: React.ReactNode
  onClick?: () => void
}

function RibbonBtn({ label, icon, onClick }: RibbonBtnProps) {
  return (
    <button
      className="eamos-toggle-btn eamos-ribbon-btn"
      style={{ padding: '5px 10px', gap: 5, fontSize: 12 }}
      onClick={onClick}
      disabled={!onClick}
      aria-label={label}
      title={label}
    >
      {icon}
      <span className="eamos-ribbon-btn-label">{label}</span>
    </button>
  )
}
