'use client'
import { useCallback, useState, useSyncExternalStore, type ReactNode } from 'react'
import { IconChevron, IconList, IconSparkle } from '@/components/icons/Icon'
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
 * AI mode (docs/ai-work-rail/spec.md): when `aiPanel` is supplied the rail head
 * carries a segmented Library ⇄ Ask-Eamos toggle. In AI mode the rail body shows
 * the assistant (the library sections stay mounted, just hidden, preserving their
 * state), the foot hides, and an expand-width button widens the rail to ~half the
 * page. Surfaces that pass no `aiPanel` are unchanged.
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
  /** Rail header label (and the Library segment label when `aiPanel` is set). */
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
  /** Optional Ask-Eamos surface. When set, the rail head gains the Library ⇄
   *  Ask-Eamos toggle and this renders in AI mode. */
  aiPanel?: ReactNode
  /** AI-segment label. Defaults to "Ask Eamos". */
  aiTitle?: string
  className?: string
}

export function WorkRail({ surface, title, action, output, children, foot, aiPanel, aiTitle = 'Ask Eamos', className }: WorkRailProps) {
  // Viewport <1200 → drawer mode (external store, SSR-safe). Collapse pref is
  // local + persisted. Drawer-open is only meaningful in drawer mode, so it's
  // derived (isOpen) rather than reset via an effect.
  const drawer = useSyncExternalStore(subscribeCompact, getCompactSnapshot, getServerCompactSnapshot)
  const [collapsed, setCollapsed] = useState(() => initialCollapsed(surface))
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [mode, setMode] = useState<'library' | 'ai'>('library')
  const [aiWide, setAiWide] = useState(false)
  const isOpen = drawer && drawerOpen
  const aiActive = !!aiPanel && mode === 'ai'

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

  // Collapsed-rail sparkle: expand straight into the assistant in one click.
  const openAiFromIcon = useCallback(() => {
    setCollapsed(false)
    writeCollapsed(surface, false)
    setMode('ai')
  }, [surface])

  const showIconRail = !drawer && collapsed
  const shellCls = [
    'work-shell',
    drawer ? 'mode-drawer' : 'mode-inline',
    showIconRail ? 'is-collapsed' : '',
    isOpen ? 'is-open' : '',
    aiActive ? 'is-ai' : '',
    aiActive && aiWide ? 'is-ai-wide' : '',
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

          {/* Head centre — segmented mode toggle when an AI panel is wired,
              else the static rail title. Hidden in the collapsed icon rail. */}
          {!showIconRail && aiPanel ? (
            <div className="wr-mode-toggle" data-mode={mode} role="tablist" aria-label="Rail mode">
              <span className="wr-mode-thumb" aria-hidden="true" />
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'library'}
                className="wr-mode-seg"
                onClick={() => setMode('library')}
              >
                <IconList size={13} />
                <span>{title}</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'ai'}
                className="wr-mode-seg wr-mode-seg-ai"
                onClick={() => setMode('ai')}
              >
                <IconSparkle size={13} />
                <span>{aiTitle}</span>
              </button>
            </div>
          ) : !showIconRail ? (
            <span className="work-rail-title">{title}</span>
          ) : null}

          {/* Head right — the expand-width control in AI mode, else the surface
              action. The collapsed icon rail gets a sparkle quick-open instead. */}
          {!showIconRail && aiActive ? (
            <button
              type="button"
              className="wr-ai-expand"
              aria-label={aiWide ? 'Collapse panel width' : 'Expand panel to half screen'}
              aria-pressed={aiWide}
              onClick={() => setAiWide((w) => !w)}
            >
              <ExpandWidthIcon wide={aiWide} />
            </button>
          ) : !showIconRail && action ? (
            <span className="work-rail-action">{action}</span>
          ) : showIconRail && aiPanel ? (
            <button
              type="button"
              className="wr-icon-ai"
              aria-label={`Open ${aiTitle}`}
              onClick={openAiFromIcon}
            >
              <IconSparkle size={16} />
            </button>
          ) : null}
        </div>

        {/* Full body — the surface controls + the AI panel. Both stay mounted
            (display-toggled by `.is-ai`) so Library state survives a mode flip.
            Hidden (not unmounted) in the icon rail. */}
        <div className="work-rail-body">
          <div className="wr-lib-body">{children}</div>
          {aiPanel ? <div className="wr-ai-body">{aiPanel}</div> : null}
        </div>

        {/* Collapsed → a vertical label of the active mode; the toggle (above) or
            this stub expands it. */}
        {showIconRail && (
          <button
            type="button"
            className="work-rail-stub"
            aria-label={`Expand ${aiActive ? aiTitle : title} controls`}
            onClick={expandFromIcon}
          >
            <span>{aiActive ? aiTitle : title}</span>
          </button>
        )}

        {/* Pinned foot — account cluster. Rides the rail's flex column (never
            unmounts), so it inherits collapse + drawer for free. Hidden in AI
            mode (the rail is dedicated to the assistant). */}
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

/** Double-chevron width control: `»` widen the rail, `«` narrow it back. */
function ExpandWidthIcon({ wide }: { wide: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width="14" height="14" aria-hidden="true">
      {wide ? (
        <>
          <polyline points="15 6 9 12 15 18" />
          <polyline points="21 6 15 12 21 18" />
        </>
      ) : (
        <>
          <polyline points="9 6 15 12 9 18" />
          <polyline points="3 6 9 12 3 18" />
        </>
      )}
    </svg>
  )
}
