'use client'
import { useCallback, useState, useSyncExternalStore, type ReactNode } from 'react'
import { IconChevron } from '@/components/icons/Icon'
import { readCollapsed, writeCollapsed } from '@/lib/work-rail-collapse'
import './work-rail.css'

/**
 * <WorkRail> — the shared controls-left / output-right shell used across the
 * product surfaces (/compare, /workbench, /report). The *output* (table,
 * canvas, report) is the stable anchor on the right; the rail on the left
 * carries the per-surface controls. One chrome, three surfaces.
 *
 * Responsive (DESIGN.md — never unmount, hide with transform/display):
 *   - ≥1200px  inline rail, expand (≈336px) ↔ collapse (48px icon rail).
 *   - <1200px  rail becomes an off-canvas drawer; output goes full-width; a
 *              floating trigger + scrim open it on demand. Content stays mounted.
 *
 * Collapse preference persists per surface in localStorage
 * (`eamos-rail-<surface>-collapsed`). Spec: docs/workspace-rail/spec.md §3.
 */

const BP_COMPACT = '(max-width: 1199px)'

/** Initial collapse pref — SSR returns expanded; client reads the persisted
 *  value, falling back to "collapsed on small screens". Lazy useState
 *  initializer (no setState-in-effect), mirroring WorkbenchShell. */
function initialCollapsed(surface: string): boolean {
  if (typeof window === 'undefined') return false
  const stored = readCollapsed(surface)
  if (stored !== null) return stored
  return window.matchMedia(BP_COMPACT).matches
}

/** matchMedia(<1200px) as an external store — SSR-safe via useSyncExternalStore
 *  (server snapshot is false), so no hydration mismatch and no effect. */
function subscribeCompact(onChange: () => void) {
  const mq = window.matchMedia(BP_COMPACT)
  mq.addEventListener('change', onChange)
  return () => mq.removeEventListener('change', onChange)
}
function getCompactSnapshot() {
  return window.matchMedia(BP_COMPACT).matches
}
function getServerCompactSnapshot() {
  return false
}

export interface WorkRailSectionProps {
  title: string
  /** Leading monochrome glyph (an <Icon*>) — the "what belongs to what" cue.
   *  Sits at the muted label tone; never carries the brand teal. */
  icon?: ReactNode
  meta?: ReactNode
  defaultOpen?: boolean
  children: ReactNode
  id?: string
}

/** A collapsible section inside the rail. Airy icon-led grammar (work-rail.css):
 *  a leading glyph anchors the row, the uppercase label and right-aligned meta
 *  follow, and the disclosure chevron sits quietly at the far right. Shared by
 *  every surface; the Workbench `.side-section` mirrors the same metrics. */
export function WorkRailSection({ title, icon, meta, defaultOpen = true, children, id }: WorkRailSectionProps) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className={`wr-section${open ? '' : ' is-collapsed'}`} id={id}>
      <button
        type="button"
        className="wr-section-head"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        {icon ? <span className="wr-section-icon" aria-hidden="true">{icon}</span> : null}
        <span className="wr-section-title">{title}</span>
        {meta ? <span className="wr-section-meta">{meta}</span> : null}
        <span className="wr-section-chev" aria-hidden="true">
          <IconChevron size={12} />
        </span>
      </button>
      {open && <div className="wr-section-body">{children}</div>}
    </div>
  )
}

export interface WorkRailProps {
  /** Persistence + a11y key. One of 'compare' | 'workbench' | 'report'. */
  surface: string
  /** Rail header label. */
  title: string
  /** Primary "new" action rendered at the top of the rail header. */
  action?: ReactNode
  /** The right-hand output pane (flex:1, fills the remainder). */
  output: ReactNode
  /** Rail body — typically <WorkRailSection> children. */
  children: ReactNode
  /** Optional pinned bottom region (account cluster, Ask launcher). Renders
   *  only when provided, so surfaces that don't opt in are unaffected. */
  foot?: ReactNode
  className?: string
}

export function WorkRail({ surface, title, action, output, children, foot, className }: WorkRailProps) {
  // Viewport <1200 → drawer mode (external store, SSR-safe). Collapse pref is
  // local + persisted. Drawer-open is only meaningful in drawer mode, so it's
  // derived (isOpen) rather than reset via an effect.
  const drawer = useSyncExternalStore(subscribeCompact, getCompactSnapshot, getServerCompactSnapshot)
  const [collapsed, setCollapsed] = useState(() => initialCollapsed(surface))
  const [drawerOpen, setDrawerOpen] = useState(false)
  const isOpen = drawer && drawerOpen

  const toggle = useCallback(() => {
    if (drawer) {
      setDrawerOpen((o) => !o)
      return
    }
    setCollapsed((c) => {
      const next = !c
      writeCollapsed(surface, next)
      return next
    })
  }, [drawer, surface])

  const expandFromIcon = useCallback(() => {
    setCollapsed(false)
    writeCollapsed(surface, false)
  }, [surface])

  const showIconRail = !drawer && collapsed
  const shellCls = [
    'work-shell',
    drawer ? 'mode-drawer' : 'mode-inline',
    showIconRail ? 'is-collapsed' : '',
    isOpen ? 'is-open' : '',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={shellCls}>
      {/* Drawer scrim — closes the overlay on <1200. */}
      {drawer && (
        <button
          type="button"
          className="work-rail-scrim"
          aria-label="Close panel"
          tabIndex={isOpen ? 0 : -1}
          onClick={() => setDrawerOpen(false)}
        />
      )}

      <aside className="work-rail" aria-label={`${title} controls`}>
        <div className="work-rail-head">
          <button
            type="button"
            className="work-rail-toggle"
            aria-expanded={drawer ? isOpen : !collapsed}
            aria-label={
              drawer
                ? isOpen
                  ? 'Close panel'
                  : 'Open panel'
                : collapsed
                  ? 'Expand panel'
                  : 'Collapse panel'
            }
            onClick={toggle}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width="13" height="13">
              <polyline points={!drawer && collapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6'} />
            </svg>
          </button>
          <span className="work-rail-title">{title}</span>
          {action ? <span className="work-rail-action">{action}</span> : null}
        </div>

        {/* Full body — the surface controls. Hidden (not unmounted) in icon-rail. */}
        <div className="work-rail-body">{children}</div>

        {/* Collapsed → a vertical title label; the toggle (above) or this stub expands it. */}
        {showIconRail && (
          <button
            type="button"
            className="work-rail-stub"
            aria-label={`Expand ${title} controls`}
            onClick={expandFromIcon}
          >
            <span>{title}</span>
          </button>
        )}

        {/* Pinned foot — account cluster + Ask launcher. Rides the rail's flex
            column (never unmounts), so it inherits collapse + drawer for free. */}
        {foot ? <div className="work-rail-foot">{foot}</div> : null}
      </aside>

      <div className="work-output">{output}</div>

      {/* Floating trigger to open the drawer on <1200 when it's closed. */}
      {drawer && !isOpen && (
        <button type="button" className="work-rail-fab" onClick={() => setDrawerOpen(true)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width="15" height="15">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
          <span>{title}</span>
        </button>
      )}
    </div>
  )
}
