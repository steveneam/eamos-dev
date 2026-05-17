import type { PublicationsCallout as PublicationsCalloutData } from '@/lib/backend'

interface PublicationsCalloutProps {
  data?: PublicationsCalloutData | null
  onAskSummary?: () => void
}

export function PublicationsCallout({ data, onAskSummary }: PublicationsCalloutProps) {
  if (!data) {
    return (
      <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: '14px 0 0' }}>
        No publication summary available for this variant.
      </p>
    )
  }

  return (
    <div className="pubs-strip">
      <div>
        <div className="pubs-n">{data.total_count.toLocaleString()}</div>
        <div className="pubs-l">Relevant publications</div>
      </div>
      <div className="pubs-blurb">{data.blurb}</div>
      <div className="pubs-actions">
        <a
          className="pubs-action"
          href={data.scholar_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="7" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          Google Scholar
        </a>
        {onAskSummary && (
          <button type="button" className="pubs-action" onClick={onAskSummary}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2 L13.5 8.5 L20 10 L13.5 11.5 L12 18 L10.5 11.5 L4 10 L10.5 8.5 Z" />
            </svg>
            AI summary
          </button>
        )}
      </div>
    </div>
  )
}
