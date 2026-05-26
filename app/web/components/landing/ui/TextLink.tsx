/**
 * Landing text/nav link — ONE shared primitive for:
 *   - Nav links (LandingNav)
 *   - Footer links (SiteFooter)
 *   - Any inline landing links
 *
 * Rest:   hero-ink-2
 * Hover:  hero-ink
 * Focus-visible: 3px em-22% ring, radius 3px
 * Transition: color --dur-1 / --ease-standard
 * Reduced-motion: handled by global guard.
 */
import type { CSSProperties } from 'react'

interface TextLinkProps {
  href: string
  target?: string
  rel?: string
  children: React.ReactNode
  /** Extra Tailwind/CSS classes */
  className?: string
  /** Style override — merges on top of the base link style */
  style?: CSSProperties
  onClick?: () => void
  'aria-label'?: string
}

export function TextLink({ href, target, rel, children, className, style, onClick, 'aria-label': ariaLabel }: TextLinkProps) {
  return (
    <a
      href={href}
      target={target}
      rel={rel}
      onClick={onClick}
      aria-label={ariaLabel}
      data-lp="text-link"
      className={`eamos-text-link${className ? ` ${className}` : ''}`}
      style={style}
    >
      {children}
    </a>
  )
}

/**
 * Mount once alongside TextLink consumers (e.g. in SiteFooter / LandingNav).
 * Injects the shared hover/focus CSS for .eamos-text-link.
 */
export function TextLinkStyles() {
  return (
    <style>{`
      /* Shares the landing's teal-accent hover signal with .lnav-link and
         .eamos-pill — every interactive surface hits the same teal axis. */
      .eamos-text-link {
        color: var(--hero-ink-2);
        text-decoration: underline;
        text-decoration-color: transparent;
        text-decoration-thickness: 1.5px;
        text-underline-offset: 5px;
        transition:
          color var(--dur-1) var(--ease-standard),
          text-decoration-color var(--dur-1) var(--ease-standard);
        border-radius: 3px;
        outline: none;
      }
      .eamos-text-link:hover {
        color: var(--hero-ink);
        text-decoration-color: var(--em-bright);
      }
      .eamos-text-link:focus-visible {
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--em) 22%, transparent);
      }
    `}</style>
  )
}
