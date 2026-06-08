'use client'
import type {
  PublicationsCallout as PublicationsCalloutData,
  PublicationScopeCounts,
} from '@/lib/backend'

type PubScope = 'variant' | 'gene'

interface PublicationsCalloutProps {
  data?: PublicationsCalloutData | null
  scopeCounts?: PublicationScopeCounts | null
  geneSymbol?: string | null
  onAskSummary?: () => void
  /** Controlled scope — the parent (§6) owns it so the same toggle also steers
   *  the publication timeline. URL `?pubScope=` is read by the parent. */
  scope: PubScope
  onScopeChange: (scope: PubScope) => void
}

export function PublicationsCallout({
  data,
  scopeCounts,
  geneSymbol,
  onAskSummary,
  scope,
  onScopeChange,
}: PublicationsCalloutProps) {
  const setScope = onScopeChange

  if (!data && !scopeCounts) {
    return (
      <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: '14px 0 0' }}>
        No publication summary available for this variant.
      </p>
    )
  }

  const variantCount = scopeCounts?.variant?.total_count ?? data?.total_count ?? null
  const geneScope = scopeCounts?.gene ?? null
  const geneCount = geneScope?.total_count ?? null
  const geneQuery = geneScope?.query ?? null
  const genePubMedUrl = geneQuery
    ? `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(geneQuery)}`
    : geneSymbol
      ? `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(geneSymbol)}%5BGene+Name%5D`
      : null
  const geneLabel = geneSymbol ? `the ${geneSymbol} gene` : 'this gene'
  // Variant-scope outbound link → PubMed (was Google Scholar). Prefer the
  // backend's variant PubMed query; else fall back to a gene-name search.
  const variantQuery = scopeCounts?.variant?.query ?? null
  const variantPubMedUrl = variantQuery
    ? `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(variantQuery)}`
    : geneSymbol
      ? `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(geneSymbol)}%5BGene+Name%5D`
      : null

  return (
    <div
      style={{
        background: 'var(--bg-soft)',
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-md)',
        padding: 'var(--report-subpanel-pad)',
        marginTop: 14,
      }}
    >
      {/* Scope toggle — inbound-only: URL param sets initial state; clicking does NOT push to URL (M-001 scope) */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
        <button
          type="button"
          onClick={() => setScope('variant')}
          className="eamos-toggle-btn"
          title="Show publications that cite this specific variant"
          style={scope === 'variant' ? { background: 'var(--bg-soft2)', borderColor: 'var(--ink-4)', color: 'var(--ink)' } : undefined}
        >
          Variant
        </button>
        <button
          type="button"
          onClick={() => setScope('gene')}
          className="eamos-toggle-btn"
          title="Show publications about the whole gene, not just this variant"
          style={scope === 'gene' ? { background: 'var(--bg-soft2)', borderColor: 'var(--ink-4)', color: 'var(--ink)' } : undefined}
        >
          Gene
        </button>
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 200px', minWidth: 0 }}>
          {scope === 'variant' ? (
            <p
              style={{
                margin: 0,
                fontSize: 13.5,
                lineHeight: 1.55,
                color: 'var(--ink-2)',
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--mono)',
                  fontWeight: 600,
                  color: 'var(--ink)',
                  marginRight: 6,
                }}
              >
                {variantCount != null ? `${variantCount.toLocaleString()} publications` : '— publications'}
              </span>
              {data?.blurb}
            </p>
          ) : geneCount != null ? (
            <p
              style={{
                margin: 0,
                fontSize: 13.5,
                lineHeight: 1.55,
                color: 'var(--ink-2)',
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--mono)',
                  fontWeight: 600,
                  color: 'var(--ink)',
                  marginRight: 6,
                }}
              >
                {geneCount.toLocaleString()} publications
              </span>
              across {geneLabel} (PubMed source count).
            </p>
          ) : (
            <p
              style={{
                margin: 0,
                fontSize: 13.5,
                lineHeight: 1.55,
                color: 'var(--ink-3)',
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--mono)',
                  fontWeight: 600,
                  color: 'var(--ink-4)',
                  marginRight: 6,
                }}
                aria-label="Not available"
              >
                —
              </span>
              Gene-wide publication count not available right now.
            </p>
          )}
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          {scope === 'variant' && variantPubMedUrl && (
            <a
              href={variantPubMedUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="eamos-toggle-btn"
              style={{ textDecoration: 'none' }}
              title="Open this variant's publications in PubMed"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <circle cx="11" cy="11" r="7" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              PubMed ↗
            </a>
          )}
          {scope === 'gene' && genePubMedUrl && (
            <a
              href={genePubMedUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="eamos-toggle-btn"
              style={{ textDecoration: 'none' }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <circle cx="11" cy="11" r="7" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              PubMed (gene) ↗
            </a>
          )}
          {onAskSummary && (
            <button
              type="button"
              onClick={onAskSummary}
              className="eamos-toggle-btn"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M12 2 L13.5 8.5 L20 10 L13.5 11.5 L12 18 L10.5 11.5 L4 10 L10.5 8.5 Z" />
              </svg>
              AI summary
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
