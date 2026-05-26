'use client'

import { useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface CardProps {
  number?: number
  title: string
  meta?: ReactNode
  children: ReactNode
  className?: string
  /** Start collapsed. The report renders open by default — the chevron is the
   *  affordance, not the resting state. */
  defaultOpen?: boolean
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
  children,
  className,
  defaultOpen = true,
}: CardProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div
      className={cn(
        'rounded-[14px] bg-[var(--bg)] border border-[var(--line)] overflow-hidden',
        className,
      )}
      style={{ borderWidth: '0.5px', boxShadow: 'var(--elev-1)' }}
    >
      <button
        type="button"
        className="flex w-full items-center justify-between px-6 py-4 text-left transition-colors"
        style={{
          borderBottom: open ? '0.5px solid var(--line)' : 'none',
          background: 'transparent',
          cursor: 'pointer',
        }}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'var(--bg-soft)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent'
        }}
      >
        <div className="flex items-center gap-3">
          <span
            aria-hidden="true"
            className="inline-flex h-4 w-4 shrink-0 items-center justify-center"
            style={{
              color: 'var(--ink-3)',
              transition: 'transform .2s ease',
              transform: open ? 'rotate(0deg)' : 'rotate(-90deg)',
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
              style={{ background: 'var(--teal)', fontFamily: 'var(--mono)' }}
            >
              {number}
            </span>
          )}
          <h2
            className="text-[18px] font-normal tracking-[-0.01em]"
            style={{ color: 'var(--ink)', fontFamily: 'var(--display)' }}
          >
            {title}
          </h2>
        </div>
        {meta && (
          <span className="text-[12px]" style={{ color: 'var(--ink-4)' }}>
            {meta}
          </span>
        )}
      </button>
      {open && <div className="px-6 py-5">{children}</div>}
    </div>
  )
}
