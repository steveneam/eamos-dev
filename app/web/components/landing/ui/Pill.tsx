'use client'

/**
 * Landing interactive pill/chip — ONE shared primitive for:
 *   - "Try" example query chips (LandingClient)
 *   - "POWERED BY" source pills (SourceStrip)
 *   - Any future cross-DB/source chips on the landing
 *
 * Rest:   glass bg, hero-line border, hero-ink-2 text
 * Hover:  glass2 bg, em border, hero-ink text
 * Active: scale(0.97)
 * Focus-visible: 3px em-22% ring
 * All transitions on --dur-1 / --ease-standard.
 * Reduced-motion is handled by the global guard in globals.css.
 */

const TRANSITION = [
  'background var(--dur-1) var(--ease-standard)',
  'border-color var(--dur-1) var(--ease-standard)',
  'color var(--dur-1) var(--ease-standard)',
  'transform var(--dur-1) var(--ease-standard)',
].join(', ')

interface PillBaseProps {
  /** Leading teal dot accent (defaults to true) */
  dot?: boolean
  /** Font family override — defaults to var(--body); pass var(--mono) for HGVS chips */
  fontFamily?: string
  className?: string
  style?: React.CSSProperties
  children: React.ReactNode
  title?: string
}

interface PillButtonProps extends PillBaseProps {
  as?: 'button'
  onClick: () => void
  href?: never
  target?: never
  rel?: never
}

interface PillLinkProps extends PillBaseProps {
  as: 'a'
  href: string
  target?: string
  rel?: string
  onClick?: never
}

export type PillProps = PillButtonProps | PillLinkProps

export function Pill({ as, dot = true, fontFamily, children, className, style, title, ...rest }: PillProps) {
  const pillStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '5px 12px',
    background: 'var(--hero-glass)',
    border: '0.5px solid var(--hero-line)',
    borderRadius: 999,
    fontSize: 11.5,
    fontWeight: 500,
    color: 'var(--hero-ink-2)',
    textDecoration: 'none',
    cursor: 'pointer',
    transition: TRANSITION,
    outline: 'none',
    fontFamily: fontFamily ?? 'var(--body)',
    ...style,
  }

  const dotEl = dot ? (
    <span
      aria-hidden
      style={{ width: 5, height: 5, borderRadius: 999, background: 'var(--em-bright)', flexShrink: 0 }}
    />
  ) : null

  const shared = {
    'data-lp': 'pill',
    className: `eamos-pill${className ? ` ${className}` : ''}`,
    style: pillStyle,
    title,
  }

  if (as === 'a') {
    const { href, target, rel } = rest as PillLinkProps
    return (
      <a {...shared} href={href} target={target} rel={rel}>
        {dotEl}
        {children}
      </a>
    )
  }

  const { onClick } = rest as PillButtonProps
  return (
    <button {...shared} type="button" onClick={onClick}>
      {dotEl}
      {children}
    </button>
  )
}

/**
 * Mount once in the nearest layout or alongside a Pill consumer.
 * Injects the shared hover/focus/active CSS rules for .eamos-pill.
 */
export function PillStyles() {
  return (
    <style>{`
      .eamos-pill:hover {
        background: var(--hero-glass2) !important;
        border-color: var(--em) !important;
        color: var(--hero-ink) !important;
      }
      .eamos-pill:active {
        transform: scale(0.97) !important;
      }
      .eamos-pill:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--em) 22%, transparent);
      }
    `}</style>
  )
}
