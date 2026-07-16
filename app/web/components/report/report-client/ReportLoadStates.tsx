import type { ReactNode } from 'react'
import Link from 'next/link'

export function CenteredMain({
  children,
  bleed = false,
}: {
  children: ReactNode
  bleed?: boolean
}) {
  return (
    <main
      className={bleed ? undefined : 'mx-auto'}
      style={
        bleed
          ? { width: '100%', maxWidth: 'none', padding: '32px 24px 80px' }
          : {
              width: '100%',
              maxWidth: 'var(--maxw-report-frame)',
              padding: '32px 32px 80px',
            }
      }
    >
      {children}
    </main>
  )
}

interface ErrorBlockProps {
  variant: 'generic' | 'offline' | 'unresolved'
  message?: string
  query: string
  onRetry: () => void
  backHref: string
  backLabel: string
  showDemo: boolean
}

export function ErrorBlock({
  variant,
  message,
  query,
  onRetry,
  backHref,
  backLabel,
  showDemo,
}: ErrorBlockProps) {
  const isOffline = variant === 'offline'
  const isUnresolved = variant === 'unresolved'
  const title = isOffline
    ? 'Backend offline'
    : isUnresolved
      ? 'Couldn’t resolve this variant'
      : 'Lookup failed'

  return (
    <section
      role="alert"
      style={{
        background: 'var(--warn-tint)',
        border: '0.5px solid var(--warn-bdr)',
        borderRadius: 14,
        padding: '24px 28px',
        color: 'var(--ink)',
      }}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="inline-flex shrink-0 items-center justify-center"
          style={{
            width: 28,
            height: 28,
            borderRadius: 999,
            background: 'var(--bg)',
            border: '0.5px solid var(--warn-bdr)',
            color: 'var(--warn)',
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </span>
        <div className="min-w-0 flex-1">
          <h2
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 600,
              fontSize: 16,
              letterSpacing: '-0.01em',
              color: 'var(--ink)',
              margin: 0,
            }}
          >
            {title}
          </h2>
          {query && (
            <div
              className="mt-1"
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 12.5,
                color: 'var(--ink-3)',
              }}
            >
              {query}
            </div>
          )}
          {isOffline ? (
            <p
              className="mt-2.5"
              style={{
                fontSize: 13.5,
                lineHeight: 1.6,
                color: 'var(--ink-2)',
                margin: '10px 0 0',
              }}
            >
              The Eamos service is temporarily unavailable — this can happen if the server is
              waking from idle. Please wait a few moments and try again.
            </p>
          ) : isUnresolved ? (
            <p
              className="mt-2.5"
              style={{
                fontSize: 13.5,
                lineHeight: 1.6,
                color: 'var(--ink-2)',
                margin: '10px 0 0',
              }}
            >
              We reached the databases, but none could resolve this query to genomic coordinates:
              Ensembl and VariantValidator didn’t recognise the gene/HGVS pair. This isn’t a
              network failure. Double-check the transcript and cDNA (or try the rsID), then retry.
            </p>
          ) : (
            <p
              className="mt-2.5"
              style={{
                fontSize: 13.5,
                lineHeight: 1.6,
                color: 'var(--ink-2)',
                margin: '10px 0 0',
                wordBreak: 'break-word',
              }}
            >
              {message}
            </p>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {isOffline && (
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex items-center gap-1.5 transition-colors"
                style={{
                  padding: '7px 14px',
                  borderRadius: 10,
                  border: '0.5px solid var(--ink-2)',
                  background: 'var(--ink-2)',
                  color: '#fff',
                  fontSize: 12.5,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Try again
              </button>
            )}
            <Link
              href={backHref}
              style={{
                padding: '7px 14px',
                borderRadius: 10,
                border: '0.5px solid var(--line-2)',
                background: 'var(--bg)',
                color: 'var(--ink-2)',
                fontSize: 12.5,
                fontWeight: 600,
                textDecoration: 'none',
              }}
            >
              {backLabel}
            </Link>
            {showDemo && !isOffline && (
              <Link
                href="/report?gene=USH2A&cdna=c.2276G%3ET"
                style={{
                  fontSize: 12,
                  color: 'var(--ink-3)',
                  textDecoration: 'underline',
                  textUnderlineOffset: 3,
                  marginLeft: 4,
                }}
              >
                View the USH2A sample report instead
              </Link>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

export function MalformedBlock({
  query,
  detail,
  backHref,
  backLabel,
  showDemo,
}: {
  query: string
  detail?: string
  backHref: string
  backLabel: string
  showDemo: boolean
}) {
  return (
    <section
      role="alert"
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '24px 28px',
        color: 'var(--ink)',
      }}
    >
      <h2
        style={{
          fontFamily: 'var(--display)',
          fontWeight: 600,
          fontSize: 16,
          letterSpacing: '-0.01em',
          margin: 0,
        }}
      >
        Not a recognised variant
      </h2>
      {query && (
        <div
          className="mt-1"
          style={{ fontFamily: 'var(--mono)', fontSize: 12.5, color: 'var(--ink-3)' }}
        >
          {query}
        </div>
      )}
      <p
        style={{
          fontSize: 13.5,
          lineHeight: 1.6,
          color: 'var(--ink-2)',
          margin: '10px 0 0',
        }}
      >
        {detail ?? 'Eamos couldn’t parse this as a variant. Try one of these formats:'}
      </p>
      <ul
        style={{
          margin: '10px 0 0',
          padding: 0,
          listStyle: 'none',
          display: 'flex',
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        {[
          ['Gene + cDNA', 'USH2A c.2276G>T'],
          ['Transcript HGVS', 'NM_206933.4:c.2276G>T'],
          ['Genomic hg38', '1-216247118-C-A'],
          ['dbSNP', 'rs80338902'],
        ].map(([label, example]) => (
          <li
            key={label}
            style={{
              padding: '6px 10px',
              background: 'var(--bg-soft)',
              border: '0.5px solid var(--line)',
              borderRadius: 8,
              fontSize: 12,
              color: 'var(--ink-3)',
            }}
          >
            <span style={{ color: 'var(--ink-4)' }}>{label}: </span>
            <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink-2)' }}>
              {example}
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Link
          href={backHref}
          style={{
            padding: '7px 14px',
            borderRadius: 10,
            border: '0.5px solid var(--ink-2)',
            background: 'var(--ink-2)',
            color: '#fff',
            fontSize: 12.5,
            fontWeight: 600,
            textDecoration: 'none',
          }}
        >
          {backLabel}
        </Link>
        {showDemo && (
          <Link
            href="/report?gene=USH2A&cdna=c.2276G%3ET"
            style={{
              fontSize: 12,
              color: 'var(--ink-3)',
              textDecoration: 'underline',
              textUnderlineOffset: 3,
              marginLeft: 4,
            }}
          >
            View the USH2A sample report instead
          </Link>
        )}
      </div>
    </section>
  )
}
