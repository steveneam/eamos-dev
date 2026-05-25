'use client'
import { useState, type ReactNode } from 'react'
import { Card } from '@/components/ui/Card'
import { PublicationTimelineChart } from '@/components/report/PublicationTimelineChart'
import { lookupPublications } from '@/lib/api'
import type { PublicationSnippet, PubMedArticle, ReportPayload } from '@/lib/backend'

interface PubMedSectionProps {
  payload: ReportPayload
  number?: number
}

const PAGE_SIZE = 5

const pubStyles = `
  .article-title-link:hover { color: var(--teal-deep) !important; text-decoration: underline; text-underline-offset: 3px; }
  .article-title-link:focus-visible { outline: none; box-shadow: 0 0 0 3px rgba(29,158,117,0.14); border-radius: 3px; }
  .pub-more-btn:hover:not(:disabled) { background: var(--bg-soft) !important; border-color: var(--ink-5) !important; }
  .pub-more-btn:focus-visible { outline: none; box-shadow: 0 0 0 3px rgba(29,158,117,0.14); }
  .pub-more-btn:active:not(:disabled) { transform: translateY(1px); transition-duration: 80ms; }
`

function formatLabel(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

function articleDate(article: PubMedArticle): string {
  return article.publication_date || article.year || ''
}

export function PubMedSection({ payload, number }: PubMedSectionProps) {
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

  if (!hasTypedLiterature && initialArticles.length === 0) return null

  const articles = [...initialArticles, ...extra]
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

  return (
    <Card number={number} title="Publication literature" meta={meta}>
      <style>{pubStyles}</style>
      {hasTimeline && timeline && <PublicationTimelineChart timeline={timeline} />}
      {articles.length === 0 ? (
        <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: 0 }}>
          No publication rows available for this lookup.
        </p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-4 p-0">
          {articles.map((art) => (
            <ArticleRow key={art.pmid} article={art} />
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
              className="pub-more-btn"
              style={{
                padding: '7px 14px',
                borderRadius: 10,
                border: '0.5px solid var(--line-2)',
                background: 'var(--bg)',
                color: 'var(--ink-2)',
                fontSize: 12,
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
                transition: 'border-color var(--dur-1) var(--ease-standard), background var(--dur-1) var(--ease-standard)',
              }}
            >
              {loading ? 'Loading...' : ('View ' + String(moreCount) + ' more')}
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
              Search all on PubMed &#8599;
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
    </Card>
  )
}

function ArticleRow({ article }: { article: PubMedArticle }) {
  const snippets = article.snippets ?? []
  const sourceTags = article.source_tags ?? []

  return (
    <li className="m-0">
      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="article-title-link"
        style={{
          display: 'block',
          fontSize: 14,
          fontWeight: 600,
          color: 'var(--ink)',
          lineHeight: 1.4,
          textDecoration: 'none',
          transition: 'color var(--dur-1) var(--ease-standard)',
        }}
      >
        {article.title}
      </a>
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
