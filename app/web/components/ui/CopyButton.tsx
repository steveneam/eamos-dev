'use client'

import { useEffect, useRef, useState } from 'react'

interface CopyButtonProps {
  /** Plain text (or TSV) to copy. */
  text: string
  /** ARIA label / tooltip; defaults to "Copy". */
  label?: string
  /** Visual size: compact (header-right) vs inline (next to a value). */
  size?: 'compact' | 'inline'
  /** Stop click bubbling — useful when nested inside a clickable Card header. */
  stopPropagation?: boolean
}

/**
 * Two-square copy affordance. Lives in the top-right of section headers and
 * data boxes. Hover lifts the contrast; on click it copies the supplied
 * `text` (TSV-friendly per `lib/report-tsv`) and flips the label to a green
 * "Copied!" confirmation for ~1.5s before reverting.
 *
 * Use one button per logical chunk of data so the user can grab just the
 * piece they want — not the whole page — and paste it neatly into a
 * spreadsheet column-by-column.
 */
export function CopyButton({
  text,
  label = 'Copy',
  size = 'compact',
  stopPropagation = true,
}: CopyButtonProps) {
  const [copied, setCopied] = useState(false)
  const [hover, setHover] = useState(false)
  const timerRef = useRef<number | null>(null)

  useEffect(
    () => () => {
      if (timerRef.current != null) window.clearTimeout(timerRef.current)
    },
    [],
  )

  const handleClick = async (e: React.MouseEvent<HTMLButtonElement>) => {
    if (stopPropagation) e.stopPropagation()
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        // Fallback for non-secure contexts: hidden textarea + execCommand.
        const ta = document.createElement('textarea')
        ta.value = text
        ta.setAttribute('readonly', '')
        ta.style.position = 'absolute'
        ta.style.left = '-9999px'
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      }
      setCopied(true)
      if (timerRef.current != null) window.clearTimeout(timerRef.current)
      timerRef.current = window.setTimeout(() => setCopied(false), 1500)
    } catch {
      // Permission denied or no clipboard API — leave the button silent
      // rather than throwing in the user's face.
    }
  }

  const compact = size === 'compact'
  const greenText = '#0f6f3a'
  const greenBg = '#e6f4ec'
  const greenBorder = '#9bd0b3'

  return (
    <button
      type="button"
      aria-label={copied ? 'Copied to clipboard' : label}
      title={copied ? 'Copied' : label}
      onClick={handleClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: copied ? 5 : 0,
        padding: compact ? '4px 7px' : '3px 6px',
        height: compact ? 26 : 22,
        background: copied ? greenBg : hover ? 'var(--bg-soft)' : 'transparent',
        color: copied ? greenText : hover ? 'var(--ink)' : 'var(--ink-4)',
        border: '0.5px solid',
        borderColor: copied ? greenBorder : hover ? 'var(--line-2)' : 'var(--line)',
        borderRadius: 6,
        cursor: 'pointer',
        fontSize: 10.5,
        fontWeight: 600,
        fontFamily: 'var(--mono)',
        letterSpacing: copied ? '0.04em' : 0,
        textTransform: 'uppercase',
        transition:
          'background 140ms ease, color 140ms ease, border-color 140ms ease, transform 100ms ease',
        transform: hover && !copied ? 'translateY(-0.5px)' : 'translateY(0)',
      }}
    >
      <span aria-hidden="true" style={{ display: 'inline-flex' }}>
        {copied ? (
          // Check mark in green when confirmed.
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          // Two-square overlap (classic copy icon).
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="9" width="11" height="11" rx="2" />
            <path d="M5 15V6a2 2 0 0 1 2-2h9" />
          </svg>
        )}
      </span>
      {copied && <span>Copied</span>}
    </button>
  )
}
