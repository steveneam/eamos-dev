'use client'

import { useEffect, useRef, useState } from 'react'
import { IconExport } from '@/components/icons/Icon'
import type { LookupResponse } from '@/lib/backend'
import { buildFullReportExport } from '@/lib/report-export'

interface ExportMenuProps {
  data: LookupResponse
  /** Trigger styling: `header` borrows the VariantHeader `v-tool` look; `ribbon`
   *  borrows the sticky-ribbon button look so the menu fits either host. */
  variant?: 'header' | 'ribbon'
}

const IconChevron = () => (
  <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M4 6l4 4 4-4" />
  </svg>
)

/**
 * Whole-report export dropdown. Lives in the sticky ribbon and the variant
 * header (the spec's "sticky-header button + dropdown"). Composes the existing
 * per-section serializers via `buildFullReportExport` — no new contract, reads
 * the `ReportPayload` already on screen.
 *
 *   - Copy full report  → rich (text/html + text/plain) clipboard write
 *   - Download (.tsv)    → tab-separated file (opens in Excel / Sheets)
 *   - Print / Save as PDF → window.print() (the existing PDF path, preserved)
 */
export function ExportMenu({ data, variant = 'ribbon' }: ExportMenuProps) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const rootRef = useRef<HTMLDivElement | null>(null)
  const copyTimer = useRef<number | null>(null)

  useEffect(
    () => () => {
      if (copyTimer.current != null) window.clearTimeout(copyTimer.current)
    },
    [],
  )

  useEffect(() => {
    if (!open) return
    const onPointerDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const flashCopied = () => {
    setCopied(true)
    if (copyTimer.current != null) window.clearTimeout(copyTimer.current)
    copyTimer.current = window.setTimeout(() => setCopied(false), 1600)
  }

  const handleCopyAll = async () => {
    setOpen(false)
    const { text, html } = buildFullReportExport(data)
    try {
      const ClipboardItemCtor: typeof ClipboardItem | undefined =
        typeof window !== 'undefined'
          ? (window as unknown as { ClipboardItem?: typeof ClipboardItem }).ClipboardItem
          : undefined
      if (navigator.clipboard?.write && ClipboardItemCtor) {
        await navigator.clipboard.write([
          new ClipboardItemCtor({
            'text/html': new Blob([html], { type: 'text/html' }),
            'text/plain': new Blob([text], { type: 'text/plain' }),
          }),
        ])
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
      }
      flashCopied()
    } catch {
      try {
        await navigator.clipboard?.writeText(text)
        flashCopied()
      } catch {
        // Clipboard API unavailable (patched out / permission denied) — no-op.
      }
    }
  }

  const handleDownload = () => {
    setOpen(false)
    const { text, filenameBase } = buildFullReportExport(data)
    const blob = new Blob([text], { type: 'text/tab-separated-values;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${filenameBase}.tsv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handlePrint = () => {
    setOpen(false)
    if (typeof window !== 'undefined') window.print()
  }

  const triggerLabel = copied ? 'Copied' : 'Export'

  return (
    <div ref={rootRef} style={{ position: 'relative', display: 'inline-flex' }}>
      {variant === 'header' ? (
        <button
          type="button"
          className="v-tool"
          aria-haspopup="menu"
          aria-expanded={open}
          aria-label="Export report"
          onClick={() => setOpen((v) => !v)}
        >
          <IconExport />
          <span>{triggerLabel}</span>
        </button>
      ) : (
        <button
          type="button"
          className="eamos-toggle-btn eamos-ribbon-btn"
          aria-haspopup="menu"
          aria-expanded={open}
          aria-label="Export report"
          onClick={() => setOpen((v) => !v)}
        >
          <IconExport size={13} />
          <span className="eamos-ribbon-btn-label">{triggerLabel}</span>
          <IconChevron />
        </button>
      )}

      {open && (
        <div
          role="menu"
          aria-label="Export report"
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            right: 0,
            zIndex: 60,
            minWidth: 216,
            background: 'var(--bg)',
            border: '0.5px solid var(--line)',
            borderRadius: 10,
            boxShadow: '0 8px 24px -6px rgba(11,26,43,0.18), 0 0 0 0.5px var(--line)',
            padding: 6,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          <MenuItem label="Copy full report" hint="Rich text + TSV" onClick={handleCopyAll} />
          <MenuItem label="Download (.tsv)" hint="Opens in Excel / Sheets" onClick={handleDownload} />
          <MenuItem label="Print / Save as PDF" hint="Browser print dialog" onClick={handlePrint} />
        </div>
      )}
    </div>
  )
}

interface MenuItemProps {
  label: string
  hint: string
  onClick: () => void
}

function MenuItem({ label, hint, onClick }: MenuItemProps) {
  const [hover, setHover] = useState(false)
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        gap: 1,
        width: '100%',
        textAlign: 'left',
        padding: '7px 10px',
        borderRadius: 7,
        border: 'none',
        background: hover ? 'var(--bg-soft)' : 'transparent',
        cursor: 'pointer',
        transition: 'background 120ms ease',
      }}
    >
      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>{label}</span>
      <span style={{ fontSize: 11, color: 'var(--ink-4)' }}>{hint}</span>
    </button>
  )
}
