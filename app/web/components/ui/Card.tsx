'use client'

import { useId, useState, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

export type Verdict =
  | 'Pathogenic'
  | 'Likely pathogenic'
  | 'VUS'
  | 'Likely benign'
  | 'Benign'

interface CardProps {
  number?: number
  title: string
  meta?: ReactNode
  /** Optional action slot rendered beside the disclosure control. */
  actions?: ReactNode
  children: ReactNode
  className?: string
  /** Start collapsed. Report chapters render open by default. */
  defaultOpen?: boolean
  /** Gives the clinical chapter index the matching ACMG-ramp treatment. */
  verdict?: Verdict | null
}

/** A numbered report chapter with a semantic heading and explicit disclosure. */
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
  const contentId = useId()
  const headingId = useId()
  const displayNumber = number === undefined ? null : String(number).padStart(2, '0')

  return (
    <article
      className={cn('report-chapter', className)}
      data-report-chapter={number ?? undefined}
      data-expanded={open}
      data-verdict={verdict ?? undefined}
    >
      <header className="report-chapter__header">
        {displayNumber && (
          <span className="report-chapter__index" aria-hidden="true">
            {displayNumber}
          </span>
        )}
        <div className="report-chapter__heading">
          <h2 id={headingId} className="report-chapter__title">
            {title}
          </h2>
          {meta && <div className="report-chapter__meta">{meta}</div>}
        </div>
        {actions && <div className="report-chapter__actions">{actions}</div>}
        <button
          type="button"
          className="report-chapter__toggle"
          aria-expanded={open}
          aria-controls={contentId}
          aria-label={`${open ? 'Hide' : 'Show'} ${title}`}
          onClick={() => setOpen((value) => !value)}
        >
          <span className="report-chapter__disclosure" aria-hidden="true">
            <span className="report-chapter__disclosure-label">{open ? 'Hide' : 'Show'}</span>
            <svg
              viewBox="0 0 24 24"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              strokeWidth={2.2}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </span>
        </button>
      </header>

      {open && (
        <div id={contentId} className="report-chapter__content">
          {children}
        </div>
      )}
    </article>
  )
}
