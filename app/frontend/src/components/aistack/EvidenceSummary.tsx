import type { ReportPayload } from '@/lib/backend'

interface EvidenceSummaryProps {
  payload: ReportPayload
}

function formatWarning(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

export function EvidenceSummary({ payload }: EvidenceSummaryProps) {
  const typedSummary = payload.report_profile?.interpretation_summary
  const hasTypedSummary = typedSummary != null
  const summary = hasTypedSummary
    ? typedSummary.text?.trim()
    : payload.ai_clinical_summary?.trim()
  const warnings = typedSummary?.warnings ?? []
  if (!summary && warnings.length === 0) return null
  const modeLabel =
    typedSummary?.mode === 'deterministic'
      ? 'deterministic'
      : typedSummary?.mode === 'llm_rewrite'
        ? 'AI rewrite'
        : hasTypedSummary
          ? 'unavailable'
          : 'synthesised'

  return (
    <div
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderTopLeftRadius: 14,
        borderTopRightRadius: 14,
        borderBottom: 'none',
        padding: '22px 26px',
      }}
    >
      <header
        className="mb-4 flex items-center gap-3 pb-4"
        style={{ borderBottom: '0.5px solid var(--line)' }}
      >
        <span
          className="inline-flex items-center justify-center text-white"
          style={{
            width: 24,
            height: 24,
            borderRadius: 999,
            background: 'var(--teal)',
            fontFamily: 'var(--mono)',
            fontSize: 11,
            fontWeight: 600,
          }}
        >
          1
        </span>
        <h2
          className="flex-1"
          style={{
            fontFamily: 'var(--display)',
            fontWeight: 600,
            fontSize: 18,
            letterSpacing: '-0.01em',
            color: 'var(--ink)',
            margin: 0,
          }}
        >
          AI evidence summary
        </h2>
        <span
          style={{
            fontSize: 11,
            color: 'var(--ink-4)',
            fontFamily: 'var(--mono)',
          }}
        >
          {modeLabel} | cited
        </span>
      </header>

      <div
        className="mb-4 flex items-center gap-2.5"
        style={{
          padding: '10px 12px',
          background: 'var(--teal-tint)',
          border: '0.5px solid #cbe3d8',
          borderRadius: 10,
          fontSize: 12,
          color: 'var(--teal-deep)',
        }}
      >
        <InfoIcon />
        <span>
          Synthesised from the source databases below. Every claim is anchored
          to a numbered source row.
        </span>
      </div>

      <div
        style={{
          fontSize: 15,
          lineHeight: 1.7,
          color: 'var(--ink-2)',
        }}
      >
        {summary ? (
          summary.split(/\n+/).map((para, i) => (
            <p key={i} style={{ margin: i === 0 ? 0 : '12px 0 0' }}>
              {para}
            </p>
          ))
        ) : (
          <p style={{ margin: 0, color: 'var(--ink-4)' }}>
            Interpretation summary unavailable for this lookup.
          </p>
        )}
      </div>

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
    </div>
  )
}

function InfoIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      style={{ flexShrink: 0 }}
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  )
}
