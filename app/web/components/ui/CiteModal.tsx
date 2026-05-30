'use client'

import { useEffect, useRef, useState, type RefObject } from 'react'

interface CiteModalProps {
  onClose: () => void
  returnFocusRef: RefObject<HTMLElement | null>
  /** Resolved by parent on /report routes; falls back to template tokens off-report. */
  variantDisplay?: string | null
  date?: string | null
  reportVersion?: string | null
}

const ORCID_URL = 'https://orcid.org/0009-0000-9745-8226'
const SCHOLAR_URL = 'https://scholar.google.com/citations?user=oNJ9_8YAAAAJ'
const PUBMED_URL = 'https://pubmed.ncbi.nlm.nih.gov/?term=Steven+S+Eamegdool'
const EAMOS_URL = 'https://eamos.com.au'

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])'

export function CiteModal({
  onClose,
  returnFocusRef,
  variantDisplay,
  date,
  reportVersion,
}: CiteModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const titleId = 'cite-modal-title'

  const [copied, setCopied] = useState(false)
  const copyTimerRef = useRef<number | null>(null)
  useEffect(
    () => () => {
      if (copyTimerRef.current != null) window.clearTimeout(copyTimerRef.current)
    },
    [],
  )

  // Focus-trap + ESC
  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    // Focus first focusable element on mount
    const focusables = () =>
      Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE))

    const first = focusables()[0]
    first?.focus()

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }

      if (e.key !== 'Tab') return

      const els = focusables()
      if (els.length === 0) return
      const firstEl = els[0]
      const lastEl = els[els.length - 1]

      if (e.shiftKey) {
        if (document.activeElement === firstEl) {
          e.preventDefault()
          lastEl.focus()
        }
      } else {
        if (document.activeElement === lastEl) {
          e.preventDefault()
          firstEl.focus()
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  // Return focus on unmount. Capture the node when the effect runs so cleanup
  // doesn't read a ref that may have changed by the time the modal unmounts.
  useEffect(() => {
    const returnTarget = returnFocusRef.current
    return () => {
      returnTarget?.focus()
    }
  }, [returnFocusRef])

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onClose()
  }

  // Plain-text citation built from the same fields the modal renders. No
  // placeholder DOI — it stays pending until a real one is minted.
  function buildCitation() {
    let cite = 'Eamegdool, S. S. (2026). Eamos: clinical-grade variant interpretation. https://eamos.com.au'
    if (variantDisplay) {
      cite += ` Variant: ${variantDisplay}.`
      if (date) cite += ` Accessed ${date}.`
      if (reportVersion) cite += ` Report v${reportVersion}.`
    }
    return cite
  }

  async function handleCopyCitation() {
    const cite = buildCitation()
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(cite)
      } else {
        // Legacy fallback for insecure contexts (mirrors CopyButton).
        const ta = document.createElement('textarea')
        ta.value = cite
        ta.setAttribute('readonly', '')
        ta.style.position = 'absolute'
        ta.style.left = '-9999px'
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      }
      setCopied(true)
      if (copyTimerRef.current != null) window.clearTimeout(copyTimerRef.current)
      copyTimerRef.current = window.setTimeout(() => setCopied(false), 1500)
    } catch {
      // Clipboard blocked (permission denied / patched API). Leave the label
      // unchanged rather than fake a success — honest per the lynchpin.
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        background: 'rgba(11,26,43,0.45)',
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
      }}
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        style={{
          background: 'var(--bg)',
          border: '0.5px solid var(--line)',
          borderRadius: '16px',
          boxShadow: 'var(--elev-3)',
          width: '100%',
          maxWidth: '540px',
          maxHeight: 'calc(100vh - 32px)',
          overflowY: 'auto',
          padding: '28px 32px 24px',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            marginBottom: '20px',
          }}
        >
          <h2
            id={titleId}
            style={{
              fontFamily: 'var(--display)',
              fontSize: '22px',
              fontWeight: 400,
              color: 'var(--ink)',
              margin: 0,
              lineHeight: 1.2,
            }}
          >
            How to cite Eamos
          </h2>
          <button
            onClick={onClose}
            aria-label="Close citation modal"
            style={{
              background: 'transparent',
              border: '0.5px solid var(--line)',
              borderRadius: '8px',
              padding: '4px 8px',
              cursor: 'pointer',
              color: 'var(--ink-3)',
              fontSize: '18px',
              lineHeight: 1,
              marginTop: '2px',
              flexShrink: 0,
            }}
          >
            ×
          </button>
        </div>

        {/* Hairline */}
        <div
          style={{
            borderTop: '0.5px solid var(--line)',
            marginBottom: '20px',
          }}
        />

        {/* Citation rows */}
        <dl
          style={{
            margin: 0,
            display: 'grid',
            gridTemplateColumns: 'max-content 1fr',
            columnGap: '20px',
            rowGap: '16px',
          }}
        >
          {/* Software */}
          <dt style={labelStyle}>Software</dt>
          <dd style={valueStyle}>
            Eamos team (2026).{' '}
            <em style={{ fontStyle: 'italic', color: 'var(--ink)' }}>
              Eamos: clinical-grade variant interpretation.
            </em>{' '}
            <a href={EAMOS_URL} target="_blank" rel="noopener noreferrer" style={linkStyle}>
              https://eamos.com.au
            </a>
            {' · '}
            DOI:{' '}
            <span style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--ink-3)' }}>
              10.5281/zenodo.XXXXX
            </span>{' '}
            <span style={{ color: 'var(--ink-4)', fontSize: '11px' }}>(pending)</span>
          </dd>

          {/* Author */}
          <dt style={labelStyle}>Author</dt>
          <dd style={{ ...valueStyle, display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontWeight: 600, color: 'var(--ink)' }}>Steven S. Eamegdool</span>
            <span>
              <span style={metaLabelStyle}>ORCID</span>{' '}
              <a href={ORCID_URL} target="_blank" rel="noopener noreferrer" style={linkStyle}>
                {ORCID_URL}
              </a>
            </span>
            <span>
              <span style={metaLabelStyle}>Scholar</span>{' '}
              <a href={SCHOLAR_URL} target="_blank" rel="noopener noreferrer" style={linkStyle}>
                {SCHOLAR_URL}
              </a>
            </span>
            <span>
              <span style={metaLabelStyle}>PubMed</span>{' '}
              <a href={PUBMED_URL} target="_blank" rel="noopener noreferrer" style={linkStyle}>
                {PUBMED_URL}
              </a>
            </span>
          </dd>

          {/* This report — off-report routes hide the row (no variant to cite). */}
          {variantDisplay && (
            <>
              <dt style={labelStyle}>This report</dt>
              <dd style={valueStyle}>
                <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink)' }}>{variantDisplay}</span>
                {date ? <>{'. Accessed '}<span style={{ color: 'var(--ink-2)' }}>{date}</span></> : null}
                {reportVersion ? <>{'. Report v'}<span style={{ fontFamily: 'var(--mono)', color: 'var(--ink-2)' }}>{reportVersion}</span></> : null}
                {'.'}
              </dd>
            </>
          )}
        </dl>

        {/* Hairline */}
        <div style={{ borderTop: '0.5px solid var(--line)', margin: '20px 0' }} />

        {/* Copy buttons — plain-text citation copies for real; the structured
            BibTeX/RIS exports are honestly disabled until they are built. */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          <button
            type="button"
            onClick={handleCopyCitation}
            aria-label={copied ? 'Citation copied to clipboard' : 'Copy citation'}
            style={copied ? { ...copyBtnStyle, ...copiedBtnStyle } : copyBtnStyle}
          >
            {copied ? 'Copied' : 'Copy citation'}
          </button>
          <button type="button" disabled aria-disabled="true" style={disabledBtnStyle}>
            Copy BibTeX
          </button>
          <button type="button" disabled aria-disabled="true" style={disabledBtnStyle}>
            Copy RIS
          </button>
        </div>
        <p
          style={{
            margin: '10px 0 0',
            fontSize: '11px',
            color: 'var(--ink-4)',
          }}
        >
          Structured BibTeX and RIS export are coming soon.
        </p>
      </div>
    </div>
  )
}

// ── Shared style objects ────────────────────────────────────────────────────

const labelStyle: React.CSSProperties = {
  fontFamily: 'var(--mono)',
  fontSize: '11px',
  fontWeight: 600,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  color: 'var(--ink-4)',
  paddingTop: '2px',
  whiteSpace: 'nowrap',
}

const valueStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '13px',
  lineHeight: 1.55,
  color: 'var(--ink-2)',
}

const metaLabelStyle: React.CSSProperties = {
  fontFamily: 'var(--mono)',
  fontSize: '10.5px',
  fontWeight: 600,
  color: 'var(--ink-4)',
  display: 'inline-block',
  width: '52px',
}

const linkStyle: React.CSSProperties = {
  color: 'var(--teal-deep)',
  textDecoration: 'underline',
  textDecorationColor: 'transparent',
  textUnderlineOffset: '3px',
  wordBreak: 'break-all',
  transition: 'color 120ms ease, text-decoration-color 120ms ease',
}

const copyBtnStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  padding: '7px 14px',
  background: 'var(--bg)',
  color: 'var(--ink-2)',
  border: '0.5px solid var(--line-2)',
  borderRadius: 'var(--r-md)',
  fontFamily: 'var(--body)',
  fontSize: '12.5px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: 'var(--elev-1)',
  transition: 'background 120ms ease, border-color 120ms ease, box-shadow 200ms ease',
}

// Confirmation state for the citation button — teal tint reads as success
// while staying on-token (no new hard-coded greens).
const copiedBtnStyle: React.CSSProperties = {
  background: 'var(--teal-tint)',
  color: 'var(--teal-deep)',
  borderColor: 'var(--teal)',
}

// Honest non-interactive state for the unbuilt structured exports.
const disabledBtnStyle: React.CSSProperties = {
  ...copyBtnStyle,
  opacity: 0.5,
  cursor: 'not-allowed',
  boxShadow: 'none',
}
