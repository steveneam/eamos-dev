'use client'
import { useRef, useState, type ReactNode } from 'react'

// The one info-affordance for the report. Replaces two drifted help marks — a
// hand-built italic-"i" span (AfThermometer) and a `ⓘ` unicode font glyph
// (PopulationFrequencySection). The font glyph renders inconsistently across
// platforms (DESIGN restricts iconography to the inline-SVG family), so both now
// share ONE inline-SVG circled-i mark drawn on the shared 1.75 pen. Two
// interaction modes are deliberately preserved (they are different affordances):
//   • <InfoHint>    hover / focus → native-title one-liner (dense inline help)
//   • <InfoPopover> click → a fixed, click-away panel for rich content
//                   (colour keys, method notes) — the panel UX is intact.

// Inline-SVG circled-"i" mark — currentColor, on the shared 1.75 stroke family.
function InfoMark({ size = 13 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0 }}
    >
      <circle cx="12" cy="12" r="9.5" fill="none" stroke="currentColor" strokeWidth="1.75" />
      <circle cx="12" cy="7.7" r="1.25" fill="currentColor" />
      <path d="M12 11v5.7" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

// Hover / focus help mark — a focusable circled-i carrying a native title
// one-liner. Drop-in for inline "what does this mean?" hints next to a label.
export function InfoHint({ tip, marginLeft = 5 }: { tip: string; marginLeft?: number }) {
  return (
    <span
      tabIndex={0}
      role="img"
      aria-label={tip}
      title={tip}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginLeft,
        color: 'var(--ink-4)',
        cursor: 'help',
        verticalAlign: 'middle',
        flex: '0 0 auto',
      }}
    >
      <InfoMark />
    </span>
  )
}

// Click-to-open popover — a pill trigger (same circled-i mark + label) toggling a
// fixed, click-away panel. position:fixed escapes any container overflow:hidden
// clip; both scrim + panel ride the shared --z-popover layer (info-popover-* CSS).
const INFO_POPOVER_WIDTH = 320

export function InfoPopover({
  label,
  triggerText = 'How to read this',
  children,
}: {
  label: string
  triggerText?: string
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  const toggle = () => {
    if (!open && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect()
      const left = Math.max(8, Math.min(rect.right - INFO_POPOVER_WIDTH, window.innerWidth - INFO_POPOVER_WIDTH - 8))
      setPos({ top: rect.bottom + 8, left })
    }
    setOpen((value) => !value)
  }

  return (
    <span style={{ display: 'inline-flex', flex: '0 0 auto' }}>
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={open}
        aria-label={label}
        onClick={toggle}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 5,
          border: '0.5px solid var(--line)',
          background: open ? 'var(--bg-soft)' : 'var(--bg)',
          color: 'var(--ink-3)',
          borderRadius: 999,
          padding: '3px 10px',
          fontSize: 10.5,
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        <InfoMark size={12} />
        {triggerText}
      </button>
      {open && pos && (
        <>
          <button
            type="button"
            aria-hidden
            tabIndex={-1}
            onClick={() => setOpen(false)}
            className="info-popover-scrim"
          />
          <div
            role="dialog"
            aria-label={label}
            className="info-popover-panel"
            style={{
              top: pos.top,
              left: pos.left,
              width: INFO_POPOVER_WIDTH,
              maxWidth: 'calc(100vw - 16px)',
              maxHeight: 'calc(100vh - 24px)',
              overflowY: 'auto',
              border: '0.5px solid var(--line)',
              background: 'var(--bg)',
              borderRadius: 10,
              padding: '12px 14px',
              boxShadow: 'var(--elev-3)',
              fontSize: 11,
              lineHeight: 1.5,
              color: 'var(--ink-3)',
              textAlign: 'left',
              whiteSpace: 'normal',
            }}
          >
            {children}
          </div>
        </>
      )}
    </span>
  )
}
