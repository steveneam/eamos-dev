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

/** A four-point sparkle — the AI / natural-language affordance (✦). */
export function IconSparkle(p: IconProps) {
  return (
    <Icon {...p}>
      <path d="M12 3l1.8 7.2L21 12l-7.2 1.8L12 21l-1.8-7.2L3 12l7.2-1.8z" />
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

/* ─────────────────────────────────────────────────────────────────────────
   Rail section glyphs — the leading icon on every <WorkRail> section head.
   They sit at the muted label tone (monochrome, never the brand teal — they
   whisper "what belongs to what", they do not signal status). One pen, same
   1.75 weight as the family above. Spec: work-rail.css "airy icon-led" grammar.
   ───────────────────────────────────────────────────────────────────────── */

/** A plain folder (no move arrow) — the "Folders" group label. */
export function IconFolder(p: IconProps) {
  return (
    <Icon {...p}>
      <path d="M4 6h4l2 2h9a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1z" />
    </Icon>
  )
}

/** Three ruled lines with leading dots — the "On this page" jump index. */
export function IconList(p: IconProps) {
  return (
    <Icon {...p}>
      <line x1="4" y1="6" x2="4.4" y2="6" />
      <line x1="4" y1="12" x2="4.4" y2="12" />
      <line x1="4" y1="18" x2="4.4" y2="18" />
      <line x1="9" y1="6" x2="20" y2="6" />
      <line x1="9" y1="12" x2="20" y2="12" />
      <line x1="9" y1="18" x2="20" y2="18" />
    </Icon>
  )
}

/** A funnel — the "Add a filter" group on the Batch scope rail. */
export function IconFilter(p: IconProps) {
  return (
    <Icon {...p}>
      <path d="M3 5h18l-7 8v6l-4-2v-4z" />
    </Icon>
  )
}

/** A crosshair target — "Active scope" (Batch) / "Active variant" (Workbench).
 *  The locus the surface is aimed at. */
export function IconScope(p: IconProps) {
  return (
    <Icon {...p}>
      <circle cx="12" cy="12" r="7" />
      <line x1="12" y1="2.5" x2="12" y2="5" />
      <line x1="12" y1="19" x2="12" y2="21.5" />
      <line x1="2.5" y1="12" x2="5" y2="12" />
      <line x1="19" y1="12" x2="21.5" y2="12" />
      <circle cx="12" cy="12" r="1.4" />
    </Icon>
  )
}

/** Three linked nodes — the "Related variants" lanes. */
export function IconRelated(p: IconProps) {
  return (
    <Icon {...p}>
      <line x1="7.6" y1="8.4" x2="12" y2="15" />
      <line x1="16.4" y1="8" x2="14.4" y2="15.2" />
      <circle cx="6" cy="7" r="2.2" />
      <circle cx="18" cy="6.4" r="2.2" />
      <circle cx="13.4" cy="17" r="2.2" />
    </Icon>
  )
}

/** An intron line with two exon blocks — the Workbench "Transcript" section. */
export function IconGene(p: IconProps) {
  return (
    <Icon {...p}>
      <line x1="3" y1="12" x2="21" y2="12" />
      <rect x="6" y="8.5" width="4" height="7" rx="1" />
      <rect x="14" y="8.5" width="4" height="7" rx="1" />
    </Icon>
  )
}

/** A segmented domain bar — the Workbench "Protein features" section. */
export function IconProtein(p: IconProps) {
  return (
    <Icon {...p}>
      <rect x="3" y="9" width="18" height="6" rx="2" />
      <line x1="9" y1="9" x2="9" y2="15" />
      <line x1="14" y1="9" x2="14" y2="15" />
    </Icon>
  )
}

/** Scissors — the CRISPR "Editing strategy" section. */
export function IconScissors(p: IconProps) {
  return (
    <Icon {...p}>
      <circle cx="6" cy="6.5" r="2.3" />
      <circle cx="6" cy="17.5" r="2.3" />
      <line x1="8.1" y1="7.6" x2="20" y2="16" />
      <line x1="8.1" y1="16.4" x2="20" y2="8" />
    </Icon>
  )
}

/** Viewfinder corner brackets — the "Target window" sequence region. */
export function IconWindow(p: IconProps) {
  return (
    <Icon {...p}>
      <polyline points="8 5 5 5 5 8" />
      <polyline points="16 5 19 5 19 8" />
      <polyline points="8 19 5 19 5 16" />
      <polyline points="16 19 19 19 19 16" />
    </Icon>
  )
}

/** A flask — the Primer "Assay strategy" section. */
export function IconFlask(p: IconProps) {
  return (
    <Icon {...p}>
      <path d="M9 3h6" />
      <path d="M10 3v6l-4.5 8a1.6 1.6 0 0 0 1.4 2.4h10.2a1.6 1.6 0 0 0 1.4-2.4L14 9V3" />
      <line x1="7.5" y1="14" x2="16.5" y2="14" />
    </Icon>
  )
}

/* ─── Header / action glyphs — bring the report header chrome (hero + sticky
   ribbon) onto the one family. They replace ad-hoc inline SVGs that drifted
   across 1.5 / 2.0 / 2.2 stroke weights. ─── */

/** A tray with a down-arrow — the "Export" / download action. */
export function IconExport(p: IconProps) {
  return (
    <Icon {...p}>
      <path d="M12 3v11" />
      <polyline points="8 10 12 14 16 10" />
      <path d="M5 16v3a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3" />
    </Icon>
  )
}

/** Three linked nodes (1→2) — the "Share" action. */
export function IconShare(p: IconProps) {
  return (
    <Icon {...p}>
      <circle cx="6" cy="12" r="2.4" />
      <circle cx="17" cy="6" r="2.4" />
      <circle cx="17" cy="18" r="2.4" />
      <line x1="8.1" y1="10.9" x2="14.9" y2="7.1" />
      <line x1="8.1" y1="13.1" x2="14.9" y2="16.9" />
    </Icon>
  )
}

/** An eye — the "views" metric in the variant hero. */
export function IconEye(p: IconProps) {
  return (
    <Icon {...p}>
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
    </Icon>
  )
}

/** A calendar — the "updated" metric in the variant hero. */
export function IconCalendar(p: IconProps) {
  return (
    <Icon {...p}>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </Icon>
  )
}
