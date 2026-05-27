'use client'

import { useEffect, useRef, useState } from 'react'

interface CopyButtonProps {
  /**
   * What to copy. Either:
   *   - a plain string (legacy TSV-only callers), or
   *   - `{ html, text }` so the clipboard carries both `text/html` (Excel,
   *     Sheets paste with borders/wrap/zebra) and `text/plain` (Notion,
   *     editors, AI chat) and each target reads the format it understands.
   */
  text: string | { html: string; text: string }
  /** ARIA label / tooltip; defaults to "Copy". */
  label?: string
  /** Visual size: compact (header-right) vs inline (next to a value). */
  size?: 'compact' | 'inline'
  /** Stop click bubbling — useful when nested inside a clickable Card header. */
  stopPropagation?: boolean
}

/**
 * Two-square copy affordance. Lives in the top-right of section headers and
 * data boxes. Hover lifts the contrast; on click it writes the payload to
 * the clipboard (rich HTML + plain TSV when both are supplied, plain text
 * otherwise) and flips the label to a green "Copied!" confirmation for
 * ~1.5s.
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
    const payload =
      typeof text === 'string' ? { html: null, text } : { html: text.html, text: text.text }

    try {
      // 1. Rich path: write both text/html and text/plain so Excel/Sheets
      //    paste formatted (borders, wrap, header fill) while plain-text
      //    targets get the TSV.
      const ClipboardItemCtor: typeof ClipboardItem | undefined =
        typeof window !== 'undefined' ? (window as unknown as { ClipboardItem?: typeof ClipboardItem }).ClipboardItem : undefined
      if (payload.html && navigator.clipboard?.write && ClipboardItemCtor) {
        const item = new ClipboardItemCtor({
          'text/html': new Blob([payload.html], { type: 'text/html' }),
          'text/plain': new Blob([payload.text], { type: 'text/plain' }),
        })
        await navigator.clipboard.write([item])
      } else if (navigator.clipboard?.writeText) {
        // 2. Plain path: secure-context clipboard, text only.
        await navigator.clipboard.writeText(payload.text)
      } else {
        // 3. Legacy fallback for insecure contexts.
        const ta = document.createElement('textarea')
        ta.value = payload.text
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
      // Rich write can fail on permission/MIME issues — degrade to plain.
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(typeof text === 'string' ? text : text.text)
          setCopied(true)
          if (timerRef.current != null) window.clearTimeout(timerRef.current)
          timerRef.current = window.setTimeout(() => setCopied(false), 1500)
        }
      } catch {
        // Give up silently — better than a thrown error in the user's face.
      }
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
