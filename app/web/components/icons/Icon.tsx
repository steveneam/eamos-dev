import type { ReactNode, SVGProps } from 'react'

/**
 * The one clean line-icon family — the unbuilt Illustrae "asset-style restraint"
 * steal (spec §6). Illustrae ships a deliberately tiny, single-source asset set;
 * Eamos was violating that with 7 ad-hoc Unicode glyphs (⇄ ✕ ⌬ ▾ ⤓ ✎ →) living
 * beside clean SVGs. This module is the clinical answer: clean line-work from one
 * pen, never hand-drawn. Sibling to ToolIcon.tsx (same idiom, weight stepped
 * 2 → 1.75 because these render smaller — "icons whisper, text speaks").
 * Design: docs/workspace-rail/illustrae-complement-design.md §2.
 *
 * Accessibility (one rule, no exceptions): every SVG is decorative
 * (`aria-hidden`); meaning lives on the host control's aria-label / aria-pressed
 * / aria-expanded. The icons can never leak a confusing accessible name.
 */
export interface IconProps extends Omit<SVGProps<SVGSVGElement>, 'width' | 'height'> {
  size?: number
}

const iconBase = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.75,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
} as const

function Icon({ size = 16, children, ...rest }: IconProps & { children: ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" {...iconBase} {...rest}>
      {children}
    </svg>
  )
}

/** Two opposed horizontal arrows — "pin / line these up to compare" (⇄). */
export function IconPin(p: IconProps) {
  return (
    <Icon {...p}>
      <line x1="4" y1="9" x2="18" y2="9" />
      <polyline points="14 6 18 9 14 12" />
      <line x1="20" y1="15" x2="6" y2="15" />
      <polyline points="10 12 6 15 10 18" />
    </Icon>
  )
}

/** A clean X — remove / clear / delete / unpin (✕). */
export function IconRemove(p: IconProps) {
  return (
    <Icon {...p}>
      <line x1="6" y1="6" x2="18" y2="18" />
      <line x1="18" y1="6" x2="6" y2="18" />
    </Icon>
  )
}

/** A bookmark ribbon — the Save register (empty-state, save-to-library). */
export function IconBookmark(p: IconProps) {
  return (
    <Icon {...p}>
      <path d="M6 4h12v16l-6-4-6 4z" />
    </Icon>
  )
}

/** A folder outline — carries the "into a folder" meaning the bare ▾ never did. */
export function IconFolderMove(p: IconProps) {
  return (
    <Icon {...p}>
      <path d="M3 7a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" />
    </Icon>
  )
}

/** A down-arrow landing into an open tray — "drop here" (⤓), folder drag-over. */
export function IconDropInto(p: IconProps) {
  return (
    <Icon {...p}>
      <line x1="12" y1="3" x2="12" y2="14" />
      <polyline points="8 10 12 14 16 10" />
      <path d="M5 16v3h14v-3" />
    </Icon>
  )
}

/** A pencil at 45° — rename (✎). */
export function IconRename(p: IconProps) {
  return (
    <Icon {...p}>
      <path d="M4 20l1.2-4.2L15.8 5.2a1.9 1.9 0 0 1 2.7 2.7L8.2 18.5 4 20z" />
      <line x1="14" y1="7" x2="17" y2="10" />
    </Icon>
  )
}

/** A thin right arrow — "Import VCF →", "Open in Compare →" (→). */
export function IconArrowRight(p: IconProps) {
  return (
    <Icon {...p}>
      <line x1="5" y1="12" x2="18" y2="12" />
      <polyline points="13 7 18 12 13 17" />
    </Icon>
  )
}

/** A plus — "+ New folder", "+ Save", lane add (+). */
export function IconPlus(p: IconProps) {
  return (
    <Icon {...p}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </Icon>
  )
}

/** A checkmark — the "✓ Saved" confirmed state (✓). */
export function IconCheck(p: IconProps) {
  return (
    <Icon {...p}>
      <polyline points="5 13 10 17 19 7" />
    </Icon>
  )
}

/** A single down-chevron — disclosure for sections / lanes / folders / the row
 *  caret (folds in the old <Chevron>/<Caret>). Rotated via CSS per open state.
 *  A lone polyline needs more presence than the multi-stroke glyphs, so it keeps
 *  the 2.4 weight the old chevrons used. */
export function IconChevron(p: IconProps) {
  return (
    <Icon strokeWidth={2.4} {...p}>
      <polyline points="6 9 12 15 18 9" />
    </Icon>
  )
}
