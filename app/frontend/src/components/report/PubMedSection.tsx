import { Card } from '@/components/ui/Card'
import type { PubMedArticle } from '@/lib/backend'

interface PubMedSectionProps {
  articles: PubMedArticle[] | null | undefined
  number?: number
}

export function PubMedSection({ articles, number }: PubMedSectionProps) {
  if (!articles || articles.length === 0) return null

  return (
    <Card number={number} title="PubMed literature" meta={`${articles.length} ${articles.length === 1 ? 'article' : 'articles'}`}>
      <ul className="m-0 flex list-none flex-col gap-4 p-0">
        {articles.map((art) => (
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
              {[art.authors, art.journal, art.year].filter(Boolean).join(' · ')}
            </div>
            <div
              className="mt-0.5"
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 11,
                color: 'var(--ink-4)',
              }}
            >
              PMID {art.pmid}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  )
}
