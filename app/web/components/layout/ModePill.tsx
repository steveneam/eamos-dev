'use client'
import { type ReactNode } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { cn } from '@/lib/utils'

type Surface = 'report' | 'workbench' | 'compare'

interface ModePillProps {
  current: Surface
  className?: string
}

// Shared icon set for the primary surface switcher — one stroke language (1.9px,
// round caps) so Report / Workbench / Batch read as one control. The label
// always rides alongside the glyph (never icon-only) for discoverability.
const svgProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.9,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  width: 13,
  height: 13,
  'aria-hidden': true,
}

const ICONS: Record<Surface, ReactNode> = {
  report: (
    <svg {...svgProps}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  ),
  workbench: (
    <svg {...svgProps}>
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  ),
  compare: (
    <svg {...svgProps}>
      <line x1="8" y1="6" x2="21" y2="6" />
      <line x1="8" y1="12" x2="21" y2="12" />
      <line x1="8" y1="18" x2="21" y2="18" />
      <line x1="3" y1="6" x2="3.01" y2="6" />
      <line x1="3" y1="12" x2="3.01" y2="12" />
      <line x1="3" y1="18" x2="3.01" y2="18" />
    </svg>
  ),
}

const ITEMS: Array<{ key: Surface; label: string; path: string }> = [
  { key: 'report',    label: 'Report',    path: '/report' },
  { key: 'compare',   label: 'Batch',     path: '/compare' },
  { key: 'workbench', label: 'Workbench', path: '/workbench' },
]

export function ModePill({ current, className }: ModePillProps) {
  const params = useSearchParams()
  const query = params.toString()
  const qs = query ? `?${query}` : ''

  return (
    <div
      role="group"
      aria-label="View mode"
      className={cn('inline-flex items-center', className)}
      style={{
        background: 'var(--bg-soft)',
        border: '0.5px solid var(--line)',
        borderRadius: 100,
        padding: 3,
      }}
    >
      {ITEMS.map((item) => {
        const active = item.key === current
        // Report/Workbench preserve the active variant (qs); Compare is the
        // multi-variant surface, so it doesn't carry the single-variant query.
        const href = item.key === 'compare' ? item.path : `${item.path}${qs}`
        return (
          <Link
            key={item.key}
            href={href}
            aria-current={active ? 'page' : undefined}
            className="inline-flex items-center gap-1.5 font-semibold transition-colors"
            style={{
              padding: '6px 12px',
              fontSize: 12,
              borderRadius: 100,
              color: active ? '#ffffff' : 'var(--ink-3)',
              background: active ? 'var(--ink-2)' : 'transparent',
              textDecoration: 'none',
            }}
          >
            {ICONS[item.key]}
            {item.label}
          </Link>
        )
      })}
    </div>
  )
}
