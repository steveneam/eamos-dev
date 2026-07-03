'use client'

import { Component, type ErrorInfo, type ReactNode } from 'react'

/**
 * GeneViewerErrorBoundary — isolates the §4 genomic track (ReportGeneViewer)
 * from the rest of the report.
 *
 * ReportGeneViewer renders an 85KB canvas/SVG track from computed genomic
 * coordinates; a throw during render (bad coords, missing track data) would
 * otherwise white-screen the whole report. This boundary catches that throw
 * and degrades to an on-brand fallback with a retry, so the surrounding
 * report sections stay usable. Sentry's global handler picks up the
 * console.error automatically — no Sentry import needed here.
 */

interface GeneViewerErrorBoundaryProps {
  children: ReactNode
  gene?: string
  cdna?: string
}

interface GeneViewerErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class GeneViewerErrorBoundary extends Component<
  GeneViewerErrorBoundaryProps,
  GeneViewerErrorBoundaryState
> {
  state: GeneViewerErrorBoundaryState = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): GeneViewerErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[GeneViewerErrorBoundary]', error, info)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      const { gene, cdna } = this.props
      const label = [gene, cdna].filter(Boolean).join(' ')

      return (
        <section
          style={{
            border: '0.5px solid var(--line)',
            borderRadius: 14,
            padding: '32px 32px 28px',
            background: 'var(--bg)',
          }}
        >
          <span
            className="uppercase"
            style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: '0.12em', color: 'var(--ink-4)' }}
          >
            Gene viewer unavailable
          </span>
          <p style={{ fontSize: 14, color: 'var(--ink-3)', margin: '10px 0 18px', lineHeight: 1.5 }}>
            The genomic track could not be rendered{label ? ` for ${label}` : ''}. The rest of the
            report is unaffected.
          </p>
          <button
            type="button"
            onClick={this.handleRetry}
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: 'var(--teal-deep)',
              background: 'transparent',
              border: '0.5px solid var(--teal)',
              borderRadius: 8,
              padding: '8px 16px',
              cursor: 'pointer',
              transition: 'background-color var(--dur-1, 120ms) var(--ease-standard, ease)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--teal)'
              e.currentTarget.style.color = 'var(--bg)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent'
              e.currentTarget.style.color = 'var(--teal-deep)'
            }}
            onFocus={(e) => {
              e.currentTarget.style.outline = '2px solid var(--teal)'
              e.currentTarget.style.outlineOffset = '2px'
            }}
            onBlur={(e) => {
              e.currentTarget.style.outline = 'none'
            }}
          >
            Try again
          </button>
        </section>
      )
    }

    return this.props.children
  }
}
