'use client'

import { useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

export type Verdict =
  | 'Pathogenic'
  | 'Likely pathogenic'
  | 'VUS'
  | 'Likely benign'
  | 'Benign'

const VERDICT_DOT: Record<Verdict, string> = {
  'Pathogenic': 'var(--cls-path-dot)',
  'Likely pathogenic': 'var(--cls-lpath-dot)',
  'VUS': 'var(--cls-vus-dot)',
  'Likely benign': 'var(--cls-lben-dot)',
  'Benign': 'var(--cls-ben-dot)',
}

interface CardProps {
  number?: number
  title: string
  meta?: ReactNode
  /** Optional action slot rendered on the far right of the header — used for
   *  the CopyButton so users can grab the section data into Excel. Click
   *  events inside should call e.stopPropagation() so the Card header
   *  doesn't also toggle collapse. */
  actions?: ReactNode
  children: ReactNode
  className?: string
  /** Start collapsed. The report renders open by default — the chevron is the
   *  affordance, not the resting state. */
  defaultOpen?: boolean
  /** When provided, renders a 3px frozen-ramp accent on the left border. */
  verdict?: Verdict | null
}

/**
 * Section card on the variant report. The header is a collapse toggle —
 * left-aligned chevron (matches the workbench windows + side panel) →
 * optional numeric badge → display-serif title → meta on the right.
 *
 * Click anywhere on the header row to collapse or expand. Defaults open.
 */
export function Card({
  number,
  title,
  meta,
  actions,
  children,
  className,
  defaultOpen = true,
  verdict,
}: CardProps) {
  const [open, setOpen] = useState(defaultOpen)
  const accentColor = verdict ? VERDICT_DOT[verdict] : undefined

  return (
    <div
      className={cn(
        'rounded-[14px] bg-[var(--bg)] border border-[var(--line)] overflow-hidden',
        className,
      )}
      style={{
        borderWidth: '0.5px',
        boxShadow: 'var(--elev-1)',
        ...(accentColor && { borderLeftWidth: '3px', borderLeftColor: accentColor }),
      }}
    >
      <div
        // Using role="button" instead of <button> so the CopyButton in the
        // actions slot doesn't end up as a nested interactive control.
        role="button"
        tabIndex={0}
        className="text-left transition-colors select-none"
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          columnGap: 12,
          rowGap: 4,
          width: '100%',
          padding: '16px 24px',
          minWidth: 0,
          borderBottom: open ? '0.5px solid var(--line)' : 'none',
          background: 'transparent',
          cursor: 'pointer',
        }}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setOpen((o) => !o)
          }
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'var(--bg-soft)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent'
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            minWidth: 0,
            flex: '1 1 180px',
            overflow: 'hidden',
          }}
        >
          <span
            aria-hidden="true"
            className="inline-flex h-4 w-4 shrink-0 items-center justify-center"
            style={{
              color: 'var(--ink-3)',
              transition: 'transform .2s ease',
              transform: open ? 'rotate(0deg)' : 'rotate(-90deg)',
              flex: '0 0 auto',
            }}
          >
            <svg
              viewBox="0 0 24 24"
              width="12"
              height="12"
              fill="none"
              stroke="currentColor"
              strokeWidth={2.4}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </span>
          {number !== undefined && (
            <span
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold text-white"
              style={{ background: 'var(--teal)', fontFamily: 'var(--mono)', flex: '0 0 auto' }}
            >
              {number}
            </span>
          )}
          <h2
            className="text-[18px] font-normal tracking-[-0.01em]"
            style={{
              color: 'var(--ink)',
              fontFamily: 'var(--display)',
              overflowWrap: 'anywhere',
              minWidth: 0,
              flex: '1 1 auto',
            }}
          >
            {title}
          </h2>
        </div>
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            columnGap: 12,
            rowGap: 4,
            minWidth: 0,
            maxWidth: '100%',
          }}
        >
          {meta && (
            <span className="text-[12px]" style={{ color: 'var(--ink-4)', overflowWrap: 'anywhere' }}>
              {meta}
            </span>
          )}
          {actions && (
            <span
              className="inline-flex items-center"
              // Headers are click-to-toggle; without this the copy button
              // click would also bubble up and collapse the section.
              onClick={(e) => e.stopPropagation()}
            >
              {actions}
            </span>
          )}
        </div>
      </div>
      {open && <div className="px-6 py-5">{children}</div>}
    </div>
  )
}
