'use client'
// Root error boundary (App Router). Renders only when the root layout itself
// throws — a rare, catastrophic case. Reports to Sentry and shows a neutral
// fallback. NEW UI surface — flagged for design review.
import * as Sentry from '@sentry/nextjs'
import { useEffect } from 'react'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    Sentry.captureException(error)
  }, [error])

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#faf8f4',
          color: '#1c1a17',
          fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
        }}
      >
        <div style={{ maxWidth: 420, padding: '0 24px', textAlign: 'center' }}>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: '0 0 8px' }}>
            Something went wrong
          </h1>
          <p
            style={{
              fontSize: 14,
              lineHeight: 1.5,
              color: '#6b655c',
              margin: '0 0 20px',
            }}
          >
            An unexpected error interrupted the page. The issue has been logged.
          </p>
          <button
            onClick={() => reset()}
            style={{
              fontSize: 14,
              fontWeight: 500,
              padding: '8px 18px',
              borderRadius: 8,
              border: '1px solid #d8d2c7',
              background: '#fff',
              color: '#1c1a17',
              cursor: 'pointer',
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  )
}
