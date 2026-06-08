'use client'

import { useEffect, useState, useSyncExternalStore } from 'react'
import { SaveCurrentButton } from './VariantLibraryRail'
import { IconExport, IconShare } from '@/components/icons/Icon'
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

// Threshold (px) past which the ribbon pins; covers the variant header height.
const SCROLL_THRESHOLD = 200

// Reactive `prefers-reduced-motion` via useSyncExternalStore so the value is
// correct on first paint (no render-time ref read, no setState-in-effect).
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)'
function subscribeReducedMotion(onChange: () => void) {
  const mq = window.matchMedia(REDUCED_MOTION_QUERY)
  mq.addEventListener('change', onChange)
  return () => mq.removeEventListener('change', onChange)
}
const getReducedMotion = () => window.matchMedia(REDUCED_MOTION_QUERY).matches
const getReducedMotionServer = () => false

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
  const reducedMotion = useSyncExternalStore(
    subscribeReducedMotion,
    getReducedMotion,
    getReducedMotionServer,
  )

  useEffect(() => {
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

  // Variant identity, rendered to MIRROR the hero header: gene in Spectral
  // (display), the HGVS / coords in mono. The gene name must read in the same
  // font everywhere it appears (hero + this ribbon), so it is split out from the
  // mono HGVS run rather than baked into one mono string.
  const hgvsText = [
    transcript && hgvsC ? `${transcript}:${hgvsC}` : hgvsC,
    hgvsP ? `(${hgvsP})` : undefined,
  ]
    .filter(Boolean)
    .join(' ')

  const noMotion = reducedMotion

  return (
    <div
      role="toolbar"
      aria-label="Variant actions"
      className={className}
      style={{
        position: 'fixed',
        top: 60,
        left: 'var(--rail-live-w, 0px)',
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
          maxWidth: 'var(--maxw-report-frame, 1140px)',
          margin: '0 auto',
          padding: '0 24px',
          height: 44,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
        }}
      >
        {/* Left: variant identity — gene (Spectral) + HGVS (mono), mirroring the hero */}
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'baseline',
            gap: 8,
            flex: '1 1 0',
            minWidth: 0,
            overflow: 'hidden',
          }}
        >
          {gene && (
            <span
              style={{
                fontFamily: 'var(--display)',
                fontWeight: 500,
                fontSize: 16,
                lineHeight: 1,
                letterSpacing: '-0.01em',
                color: 'var(--ink)',
                flexShrink: 0,
              }}
            >
              {gene}
            </span>
          )}
          <span
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 12.5,
              fontWeight: 500,
              color: 'var(--ink-2)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              minWidth: 0,
            }}
          >
            {hgvsText}
          </span>
        </span>

        {/* Right: action cluster — Save · Export · Share, matching the hero. */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          {data && <SaveCurrentButton data={data} variant="ribbon" />}
          {exportSlot ?? <RibbonBtn label="Export" icon={<IconExport size={13} />} onClick={onExport} />}
          <RibbonBtn label="Share" icon={<IconShare size={13} />} onClick={onShare} />
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
