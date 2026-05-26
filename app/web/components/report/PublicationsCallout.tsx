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
    <div
      style={{
        background: 'var(--bg-soft)',
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-md)',
        padding: '14px 18px',
        marginTop: 14,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
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
              {data.total_count.toLocaleString()} publications
            </span>
            {data.blurb}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          <a
            href={data.scholar_url}
            target="_blank"
            rel="noopener noreferrer"
            className="eamos-toggle-btn"
            style={{ textDecoration: 'none' }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <circle cx="11" cy="11" r="7" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            Google Scholar ↗
          </a>
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
