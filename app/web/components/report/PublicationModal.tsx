'use client'

/**
 * PublicationModal — M-001 #7
 *
 * Renders a rich publication detail modal for a PubMedArticle.
 *
 * URL param: ?pub=PMID:{pmid}
 *   - Pushed when an article is open; cleared on close.
 *   - Preserves all other search params (e.g. ?cite=1) — only `pub` is touched.
 *
 * Integration note: the parent component (wired in a later slice) should:
 *   1. Hold `article: PubMedArticle | null` state.
 *   2. Call `usePublicationUrl(article, onClose)` (exported below) to drive the
 *      URL param round-trip.
 *   3. Pass `article` and `onClose` to <PublicationModal />.
 *
 * Example parent snippet:
 *   const [article, setArticle] = useState<PubMedArticle | null>(null)
 *   usePublicationUrl(article, () => setArticle(null))
 *   // On card click: setArticle(selectedArticle)
 *   // On URL load: read ?pub=PMID:N, find in articles[], call setArticle(match)
 */

import { useCallback, useEffect, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import type { PubMedArticle, PublicationSnippet, PublicationSourceTag } from '@/lib/backend'

// ---------------------------------------------------------------------------
// URL param round-trip hook
// ---------------------------------------------------------------------------

/**
 * Syncs the ?pub=PMID:{pmid} URL param with the open article state.
 * Call this hook in the component that owns the article state.
 * Only touches the `pub` param — other params (e.g. ?cite=1) are preserved.
 */
export function usePublicationUrl(
  article: PubMedArticle | null,
  onClose: () => void,
): void {
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    const params = new URLSearchParams(searchParams.toString())

    if (article) {
      params.set('pub', `PMID:${article.pmid}`)
    } else {
      params.delete('pub')
    }

    const newSearch = params.toString()
    const newUrl = newSearch ? `?${newSearch}` : window.location.pathname
    router.replace(newUrl, { scroll: false })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [article?.pmid])

  // On mount, if ?pub=PMID:N is present, the parent should read it and open
  // the matching article. That wiring lives in the integration slice.
  void onClose // referenced so the dependency is visible to parent tooling
}

// ---------------------------------------------------------------------------
// Focus-trap helpers
// ---------------------------------------------------------------------------

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

function trapFocus(container: HTMLElement, e: KeyboardEvent): void {
  const focusable = Array.from(
    container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
  ).filter((el) => !el.closest('[inert]'))

  if (focusable.length === 0) return

  const first = focusable[0]
  const last = focusable[focusable.length - 1]

  if (e.shiftKey) {
    if (document.activeElement === first) {
      e.preventDefault()
      last.focus()
    }
  } else {
    if (document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }
}

// ---------------------------------------------------------------------------
// Source-tag label map
// ---------------------------------------------------------------------------

const SOURCE_TAG_LABEL: Record<PublicationSourceTag, string> = {
  litvar2: 'LitVar2',
  pubmed: 'PubMed',
  clinvar: 'ClinVar',
  clingen: 'ClinGen',
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface PublicationModalProps {
  article: PubMedArticle | null
  onClose: () => void
}

export function PublicationModal({ article, onClose }: PublicationModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  // Capture focused element on open; return focus on close
  useEffect(() => {
    if (article) {
      previousFocusRef.current = document.activeElement as HTMLElement
      // Move focus into the dialog on next tick so the element is rendered
      requestAnimationFrame(() => {
        const first = dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)
        first?.focus()
      })
    } else {
      previousFocusRef.current?.focus()
    }
  }, [article])

  // ESC to close + focus-trap
  useEffect(() => {
    if (!article) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }
      if (e.key === 'Tab' && dialogRef.current) {
        trapFocus(dialogRef.current, e)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [article, onClose])

  // Scroll-lock on body while open
  useEffect(() => {
    if (article) {
      document.body.style.overflow = 'hidden'
      return () => { document.body.style.overflow = '' }
    }
  }, [article])

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) onClose()
    },
    [onClose],
  )

  if (!article) return null

  // Derived values
  const pmcPdfUrl = article.pmcid
    ? `https://www.ncbi.nlm.nih.gov/pmc/articles/${article.pmcid}/pdf/`
    : null

  const doiUrl = article.doi
    ? `https://doi.org/${article.doi}`
    : null

  const titleId = `pub-modal-title-${article.pmid}`

  return (
    /* Backdrop overlay */
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto px-4 py-10 sm:py-16"
      style={{ background: 'rgba(11, 26, 43, 0.45)' }}
      onClick={handleBackdropClick}
      aria-hidden="false"
    >
      {/* Dialog panel */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative w-full max-w-2xl rounded-[var(--r-lg)] flex flex-col"
        style={{
          background: 'var(--bg)',
          boxShadow: 'var(--elev-3)',
          border: '0.5px solid var(--line)',
          maxHeight: 'calc(100vh - 5rem)',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-start justify-between gap-3 px-6 pt-6 pb-4"
          style={{ borderBottom: '0.5px solid var(--line)' }}
        >
          <div className="flex-1 min-w-0">
            <h2
              id={titleId}
              className="leading-snug"
              style={{
                fontFamily: 'var(--display)',
                fontWeight: 400,
                fontSize: '18px',
                color: 'var(--ink)',
              }}
            >
              {article.title}
            </h2>

            {/* Journal · year */}
            <p
              className="mt-1 text-sm truncate"
              style={{ color: 'var(--ink-3)' }}
            >
              {article.journal}
              {article.year ? ` · ${article.year}` : ''}
              {article.authors ? ` · ${article.authors}` : ''}
            </p>
          </div>

          {/* Close button */}
          <button
            type="button"
            onClick={onClose}
            aria-label="Close publication"
            className="shrink-0 flex items-center justify-center w-8 h-8 rounded-[var(--r-sm)] transition-colors"
            style={{
              color: 'var(--ink-4)',
              border: '0.5px solid var(--line)',
              background: 'transparent',
            }}
            onMouseEnter={(e) => {
              ;(e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--ink-3)'
              ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--ink-2)'
            }}
            onMouseLeave={(e) => {
              ;(e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--line)'
              ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--ink-4)'
            }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Citation count badge — citation_count is not in PubMedArticle schema */}
          <div className="flex items-center gap-2">
            <span
              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
              style={{
                background: 'var(--bg-soft)',
                color: 'var(--ink-3)',
                border: '0.5px solid var(--line)',
              }}
            >
              Citations: —
            </span>

            {/* Source-tag badges */}
            {article.source_tags && article.source_tags.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {article.source_tags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                    style={{
                      background: 'var(--bg-tint)',
                      color: 'var(--ink-3)',
                      border: '0.5px solid var(--line)',
                    }}
                  >
                    {SOURCE_TAG_LABEL[tag] ?? tag}
                  </span>
                ))}
              </div>
            ) : null}
          </div>

          {/* Abstract */}
          <section>
            <h3
              className="mb-1.5 text-xs font-semibold uppercase tracking-wide"
              style={{ color: 'var(--ink-4)' }}
            >
              Abstract
            </h3>
            {article.abstract ? (
              <p className="text-sm leading-relaxed" style={{ color: 'var(--ink-2)' }}>
                {article.abstract}
              </p>
            ) : (
              <p className="text-sm italic" style={{ color: 'var(--ink-4)' }}>
                No abstract available.
              </p>
            )}
          </section>

          {/* Snippets */}
          {article.snippets && article.snippets.length > 0 && (
            <section>
              <h3
                className="mb-2 text-xs font-semibold uppercase tracking-wide"
                style={{ color: 'var(--ink-4)' }}
              >
                Matched passages
              </h3>
              <div className="space-y-2">
                {article.snippets.map((snippet: PublicationSnippet, i: number) => (
                  <SnippetBlock key={i} snippet={snippet} />
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Footer */}
        <div
          className="px-6 py-4 flex flex-wrap items-center gap-3"
          style={{ borderTop: '0.5px solid var(--line)', background: 'var(--bg-soft)' }}
        >
          <FooterLink href={article.url} label="PubMed ↗" />
          {doiUrl && <FooterLink href={doiUrl} label="DOI ↗" />}
          {pmcPdfUrl && <FooterLink href={pmcPdfUrl} label="PDF ↗" />}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function FooterLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-sm font-medium transition-colors"
      style={{ color: 'var(--ink-3)' }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLAnchorElement).style.color = 'var(--ink)' }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLAnchorElement).style.color = 'var(--ink-3)' }}
    >
      {label}
    </a>
  )
}

function SnippetBlock({ snippet }: { snippet: PublicationSnippet }) {
  return (
    <div
      className="rounded-[var(--r-sm)] px-3 py-2.5 text-sm"
      style={{
        background: 'var(--bg-soft)',
        border: '0.5px solid var(--line)',
        color: 'var(--ink-2)',
      }}
    >
      <p className="leading-relaxed">{snippet.text}</p>
      {snippet.matched_terms.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {snippet.matched_terms.map((term) => (
            <span
              key={term}
              className="inline-block px-1.5 py-0 rounded text-xs font-medium"
              style={{
                background: 'var(--bg-tint)',
                color: 'var(--ink-3)',
              }}
            >
              {term}
            </span>
          ))}
        </div>
      )}
      <p
        className="mt-1 text-xs"
        style={{ color: 'var(--ink-4)' }}
      >
        {snippet.section} · {snippet.source} · {snippet.confidence.replace(/_/g, ' ')}
      </p>
    </div>
  )
}
