'use client'

import { useId, useState, type ReactNode } from 'react'

interface DisclosureProps {
  /** Children render inside the expanding region. */
  children: ReactNode
  /** Verb shown alongside the chevron. Defaults: "Show details" / "Hide". */
  showLabel?: string
  hideLabel?: string
  /** Optional second slot on the right of the trigger (e.g. "9 met · 19 unmet"). */
  summary?: ReactNode
  /** Optional kicker line above the trigger, e.g. "ACMG criteria". */
  kicker?: string
  /** Start expanded. */
  defaultOpen?: boolean
  /** Stable id for aria-controls and deep-linking. */
  id?: string
  /** Fired after each open/close. */
  onToggle?: (open: boolean) => void
  /** Extra className applied to the wrapper section. */
  className?: string
  /** When true, hides the top hairline separator (used when the parent already provides one). */
  flush?: boolean
}

/**
 * Shared expand/collapse affordance for the variant report.
 *
 * Anchored to the bottom of a Card (place inside the Card body, after the
 * primary content). One trigger shape, one verbiage, one motion curve — so
 * the user never has to learn a new disclosure pattern per section.
 */
export function Disclosure({
  children,
  showLabel = 'Show details',
  hideLabel = 'Hide details',
  summary,
  kicker,
  defaultOpen = false,
  id,
  onToggle,
  className,
  flush = false,
}: DisclosureProps) {
  const [open, setOpen] = useState(defaultOpen)
  const fallbackId = useId()
  const panelId = id ? `${id}-panel` : `disclosure-${fallbackId}`

  const toggle = () => {
    setOpen((value) => {
      const next = !value
      onToggle?.(next)
      return next
    })
  }

  return (
    <section
      className={['eamos-disclosure', flush ? 'eamos-disclosure--flush' : '', className]
        .filter(Boolean)
        .join(' ')}
      data-open={open}
    >
      <button
        type="button"
        className="eamos-disclosure__trigger eamos-toggle-btn"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={toggle}
      >
        <span className="eamos-disclosure__chevron" aria-hidden>
          <svg viewBox="0 0 12 12" width="11" height="11" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 2 L8 6 L4 10" />
          </svg>
        </span>
        <span className="eamos-disclosure__label-stack">
          {kicker && <span className="eamos-disclosure__kicker">{kicker}</span>}
          <span className="eamos-disclosure__label">{open ? hideLabel : showLabel}</span>
        </span>
        {summary && <span className="eamos-disclosure__summary">{summary}</span>}
      </button>

      <div
        id={panelId}
        role="region"
        hidden={!open}
        aria-hidden={!open}
        className="eamos-disclosure__panel"
      >
        {open && <div className="eamos-disclosure__panel-inner">{children}</div>}
      </div>
    </section>
  )
}
