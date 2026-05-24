import { Card } from '@/components/ui/Card'
import { PublicationTimelineChart } from '@/components/report/PublicationTimelineChart'
import type { PublicationSnippet, PubMedArticle, ReportPayload } from '@/lib/backend'

interface PubMedSectionProps {
  payload: ReportPayload
  number?: number
}

function formatWarning(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

function articleDate(article: PubMedArticle): string {
  return article.publication_date || article.year || ''
}

function firstSnippet(article: PubMedArticle): PublicationSnippet | null {
  return article.snippets?.[0] ?? null
}

export function PubMedSection({ payload, number }: PubMedSectionProps) {
  const literature = payload.publications_literature ?? null
  const hasTypedLiterature = literature != null
  const articles = hasTypedLiterature
    ? literature.articles ?? []
    : payload.pubmed_articles ?? []
  const warnings = literature?.warnings ?? []
  const totalCount = literature?.total_count ?? articles.length
  const shownCount = literature?.shown_count ?? articles.length

  if (!hasTypedLiterature && articles.length === 0) return null

  const meta = hasTypedLiterature
    ? `Showing ${shownCount} of ${totalCount} publications`
    : `${articles.length} ${articles.length === 1 ? 'article' : 'articles'}`

  const timeline = literature?.publication_timeline ?? null
  const hasTimeline = timeline != null && (timeline.publications_by_year?.length ?? 0) > 0

  return (
    <Card number={number} title="Publication literature" meta={meta}>
      {hasTimeline && timeline && <PublicationTimelineChart timeline={timeline} />}
      {articles.length === 0 ? (
        <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: 0 }}>
          No publication rows available for this lookup.
        </p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-4 p-0">
          {articles.map((art) => {
            const snippet = firstSnippet(art)
            return (
              <li key={art.pmid} className="m-0">
                <a
                  href={art.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'block',
                    fontSize: 14,
                    fontWeight: 600,
                    color: 'var(--ink)',
                    lineHeight: 1.4,
                    textDecoration: 'none',
                  }}
                >
                  {art.title}
                </a>
                <div
                  className="mt-1"
                  style={{
                    fontSize: 12,
                    color: 'var(--ink-3)',
                  }}
                >
                  {[art.authors, art.journal, articleDate(art)].filter(Boolean).join(' | ')}
                </div>
                <div
                  className="mt-0.5 flex flex-wrap gap-x-2 gap-y-1"
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 11,
                    color: 'var(--ink-4)',
                  }}
                >
                  <span>PMID {art.pmid}</span>
                  {art.pmcid && <span>PMC {art.pmcid}</span>}
                  {art.doi && <span>DOI {art.doi}</span>}
                </div>
                {snippet && (
                  <p
                    className="mt-2"
                    style={{
                      borderLeft: '2px solid var(--teal)',
                      paddingLeft: 10,
                      fontSize: 12.5,
                      lineHeight: 1.55,
                      color: 'var(--ink-3)',
                      marginBottom: 0,
                    }}
                  >
                    {snippet.text}
                  </p>
                )}
              </li>
            )
          })}
        </ul>
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
              {formatWarning(warning)}
            </span>
          ))}
        </div>
      )}
    </Card>
  )
}
