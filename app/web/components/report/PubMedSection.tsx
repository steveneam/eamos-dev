'use client'
import { useEffect, useState, type ReactNode } from 'react'
import { useSearchParams } from 'next/navigation'
import { Card } from '@/components/ui/Card'
import { PublicationTimelineChart } from '@/components/report/PublicationTimelineChart'
import { PublicationModal, usePublicationUrl } from '@/components/report/PublicationModal'
import { PublicationsCallout } from '@/components/report/PublicationsCallout'
import { lookupPublications } from '@/lib/api'
import type { PublicationSnippet, PubMedArticle, ReportPayload } from '@/lib/backend'

interface PubMedSectionProps {
  payload: ReportPayload
  number?: number
  /** Optional action slot (CopyButton) forwarded to the Card header. */
  actions?: ReactNode
}

const PAGE_SIZE = 5

const pubStyles = `
  .article-title-link:hover { color: var(--teal-deep) !important; text-decoration: underline; text-underline-offset: 3px; }
  .article-title-link:focus-visible { outline: none; box-shadow: 0 0 0 3px rgba(29,158,117,0.14); border-radius: 3px; }
`

function formatLabel(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

function articleDate(article: PubMedArticle): string {
  return article.publication_date || article.year || ''
}

export function PubMedSection({ payload, number, actions }: PubMedSectionProps) {
  const literature = payload.publications_literature ?? null
  const hasTypedLiterature = literature != null
  const initialArticles = hasTypedLiterature
    ? literature.articles ?? []
    : payload.pubmed_articles ?? []
  const warnings = literature?.warnings ?? []

  // Variant identity for the pagination request. Header is the authoritative
  // source (works for raw `q=` searches too). Per the live gotcha we OMIT the
  // transcript from the request body and always send species:'human'.
  const header = payload.report_profile?.header ?? null
  const gene = header?.gene ?? ''
  const cdna = header?.cdna ?? ''
  const proteinChange = header?.protein_change ?? null
  const canPaginate = hasTypedLiterature && Boolean(gene && cdna)

  const [extra, setExtra] = useState<PubMedArticle[]>([])
  const [total, setTotal] = useState<number>(literature?.total_count ?? initialArticles.length)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)
  const [openArticle, setOpenArticle] = useState<PubMedArticle | null>(null)
  const searchParams = useSearchParams()

  if (!hasTypedLiterature && initialArticles.length === 0) return null

  const articles = [...initialArticles, ...extra]

  // Hydrate openArticle from ?pub=PMID:N on mount + whenever articles change
  // (so newly-loaded "View more" rows are also URL-addressable). Inbound only —
  // user clicks drive the URL through usePublicationUrl below.
  useEffect(() => {
    const param = searchParams.get('pub')
    if (!param) {
      if (openArticle) setOpenArticle(null)
      return
    }
    const targetPmid = param.startsWith('PMID:') ? param.slice(5) : param
    if (openArticle?.pmid === targetPmid) return
    const match = articles.find((a) => a.pmid === targetPmid)
    if (match) setOpenArticle(match)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, articles.length])

  usePublicationUrl(openArticle, () => setOpenArticle(null))
  const shownCount = articles.length
  const meta = hasTypedLiterature
    ? `Showing ${shownCount} of ${total} publications`
    : `${articles.length} ${articles.length === 1 ? 'article' : 'articles'}`

  const canLoadMore = canPaginate && !failed && shownCount < total

  const timeline = literature?.publication_timeline ?? null
  const hasTimeline = timeline != null && (timeline.publications_by_year?.length ?? 0) > 0

  const pubmedSearchTerm = gene ? `${gene} ${proteinChange || cdna}`.trim() : ''
  const pubmedSearchUrl = pubmedSearchTerm
    ? `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(pubmedSearchTerm)}`
    : null

  const handleLoadMore = () => {
    if (loading) return
    setLoading(true)
    setFailed(false)
    lookupPublications({
      gene,
      cdna,
      protein_change: proteinChange,
      species: 'human',
      limit: PAGE_SIZE,
      offset: shownCount,
    })
      .then((page) => {
        const seen = new Set(articles.map((a) => a.pmid))
        const fresh = (page.articles ?? []).filter((a) => a.pmid && !seen.has(a.pmid))
        if (fresh.length === 0) {
          // Backend has no further distinct rows -- stop offering "View more".
          setTotal(shownCount)
          return
        }
        setExtra((prev) => [...prev, ...fresh])
        setTotal(page.total_count || shownCount + fresh.length)
      })
      .catch(() => setFailed(true))
      .finally(() => setLoading(false))
  }

  const moreCount = Math.min(PAGE_SIZE, total - shownCount)

  // Variant ↔ gene scope callout migrated up from old §4 so the scope toggle
  // lives with the publications section it actually controls. URL param
  // `?pubScope=variant|gene` continues to drive it; clicks on the toggle do
  // NOT push to URL (per M-001 scope).
  const calloutScopeCounts =
    payload.publications_callout?.scope_counts ??
    payload.publications_literature?.scope_counts ??
    null

  return (
    <Card number={number} title="Publication literature" meta={meta} actions={actions}>
      <style>{pubStyles}</style>
      <PublicationsCallout
        data={payload.publications_callout}
        scopeCounts={calloutScopeCounts}
        geneSymbol={gene || null}
      />
      {articles.length === 0 ? (
        <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: '14px 0 0' }}>
          No publication rows available for this lookup.
        </p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-4 p-0">
          {articles.map((art) => (
            <ArticleRow key={art.pmid} article={art} onOpen={() => setOpenArticle(art)} />
          ))}
        </ul>
      )}

      {(canLoadMore || failed || pubmedSearchUrl) && (
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
          {canLoadMore && (
            <button
              type="button"
              onClick={handleLoadMore}
              disabled={loading}
              aria-busy={loading}
              className="eamos-toggle-btn"
            >
              <span aria-hidden style={{ color: 'var(--ink-3)' }}>+</span>
              {loading ? 'Loading…' : `View ${moreCount} more`}
            </button>
          )}
          {failed && (
            <span role="alert" style={{ fontSize: 11.5, color: 'var(--ink-4)' }}>
              Could not load more here. Search the full set on PubMed.
            </span>
          )}
          {pubmedSearchUrl && (
            <a
              href={pubmedSearchUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: 'var(--teal-deep)',
                textDecoration: 'none',
              }}
            >
              Search all on PubMed ↗
            </a>
          )}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {warnings.slice(0, 3).map((warning) => (
            <span
              key={warning}
              style={{
                border: '0.5px solid var(--warn-bdr)',
                background: 'var(--warn-tint)',
                color: '#633806',
                borderRadius: 7,
                padding: '5px 8px',
                fontSize: 10.5,
                fontWeight: 600,
                overflowWrap: 'anywhere',
              }}
            >
              {formatLabel(warning)}
            </span>
          ))}
        </div>
      )}

      {hasTimeline && timeline && <PublicationTimelineChart timeline={timeline} />}
      <PublicationModal article={openArticle} onClose={() => setOpenArticle(null)} />
    </Card>
  )
}

function ArticleRow({ article, onOpen }: { article: PubMedArticle; onOpen: () => void }) {
  const snippets = article.snippets ?? []
  const sourceTags = article.source_tags ?? []

  // Title is button-like (opens the modal); the explicit "PubMed ↗" link in the
  // modal footer + the row's PMID metadata still give one-click PubMed access.
  return (
    <li className="m-0">
      <button
        type="button"
        onClick={onOpen}
        className="article-title-link"
        style={{
          display: 'block',
          width: '100%',
          textAlign: 'left',
          background: 'transparent',
          border: 'none',
          padding: 0,
          cursor: 'pointer',
          fontSize: 14,
          fontWeight: 600,
          color: 'var(--ink)',
          lineHeight: 1.4,
          textDecoration: 'none',
          transition: 'color var(--dur-1) var(--ease-standard)',
        }}
      >
        {article.title}
      </button>
      <div className="mt-1" style={{ fontSize: 12, color: 'var(--ink-3)' }}>
        {[article.authors, article.journal, articleDate(article)].filter(Boolean).join(' | ')}
      </div>
      <div
        className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1"
        style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-4)' }}
      >
        <span>PMID {article.pmid}</span>
        {article.pmcid && <span>PMC {article.pmcid}</span>}
        {article.doi && <span>DOI {article.doi}</span>}
        {sourceTags.map((tag) => (
          <span
            key={tag}
            style={{
              fontFamily: 'var(--body)',
              border: '0.5px solid var(--line)',
              borderRadius: 999,
              padding: '1px 6px',
              fontSize: 9.5,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: 'var(--ink-3)',
              background: 'var(--bg-soft)',
            }}
          >
            {tag}
          </span>
        ))}
      </div>

      {snippets.length > 0 ? (
        <div className="mt-2 flex flex-col gap-2">
          {snippets.map((snippet, i) => (
            <SnippetBlock key={i} snippet={snippet} />
          ))}
        </div>
      ) : (
        article.snippet_status && (
          <p
            className="mt-2"
            style={{ fontSize: 11.5, fontStyle: 'italic', color: 'var(--ink-4)', margin: '8px 0 0' }}
          >
            No exact-variant snippet. {formatLabel(article.snippet_status)}
          </p>
        )
      )}
    </li>
  )
}

function SnippetBlock({ snippet }: { snippet: PublicationSnippet }) {
  const detail = [snippet.section, snippet.source, snippet.confidence ? formatLabel(snippet.confidence) : null]
    .filter(Boolean)
    .join(' · ')

  return (
    <div style={{ background: 'var(--teal-tint)', border: '0.5px solid var(--line)', borderRadius: 6, padding: '8px 12px' }}>
      <p style={{ fontSize: 12.5, lineHeight: 1.55, color: 'var(--ink-3)', margin: 0 }}>
        {highlightTerms(snippet.text, snippet.matched_terms ?? [])}
      </p>
      {detail && (
        <div
          className="mt-1"
          style={{ fontSize: 10.5, color: 'var(--ink-4)', textTransform: 'lowercase' }}
        >
          {detail}
        </div>
      )}
    </div>
  )
}

// Wrap backend-provided matched terms in <mark>. No frontend snippet extraction --
// we only highlight terms the backend already flagged for this snippet.
function highlightTerms(text: string, terms: string[]): ReactNode {
  const clean = terms.filter((t) => t && t.trim().length > 0)
  if (clean.length === 0) return text
  const escaped = clean.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const re = new RegExp(`(${escaped.join('|')})`, 'gi')
  const lowered = clean.map((t) => t.toLowerCase())
  return text.split(re).map((part, i) =>
    lowered.includes(part.toLowerCase()) ? (
      <mark
        key={i}
        style={{ background: 'var(--teal-tint)', color: 'var(--teal-deep)', padding: '0 1px', borderRadius: 2 }}
      >
        {part}
      </mark>
    ) : (
      <span key={i}>{part}</span>
    ),
  )
}
