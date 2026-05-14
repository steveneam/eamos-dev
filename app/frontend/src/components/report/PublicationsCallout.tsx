interface PublicationsCalloutProps {
  totalCount?: number
  scholarUrl?: string
  blurb?: string
  onAskSummary?: () => void
}

const DEFAULT_BLURB =
  'Across PubMed and Google Scholar for RPE65 + p.Asp87Gly. Ask Eamos for a synthesis of the top 5, or browse externally.'

export function PublicationsCallout({
  totalCount = 816,
  scholarUrl = 'https://scholar.google.com/scholar?q=RPE65+Asp87Gly',
  blurb = DEFAULT_BLURB,
  onAskSummary,
}: PublicationsCalloutProps) {
  return (
    <div className="pubs-strip">
      <div>
        <div className="pubs-n">{totalCount.toLocaleString()}</div>
        <div className="pubs-l">Relevant publications</div>
      </div>
      <div className="pubs-blurb">{blurb}</div>
      <div className="pubs-actions">
        <a
          className="pubs-action"
          href={scholarUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="7" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          Google Scholar
        </a>
        <button type="button" className="pubs-action" onClick={onAskSummary}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2 L13.5 8.5 L20 10 L13.5 11.5 L12 18 L10.5 11.5 L4 10 L10.5 8.5 Z" />
          </svg>
          AI summary
        </button>
      </div>
    </div>
  )
}
