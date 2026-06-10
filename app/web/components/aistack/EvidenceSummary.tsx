import type { ReportPayload } from '@/lib/backend'

interface EvidenceSummaryProps {
  payload: ReportPayload
}

function formatWarning(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

/**
 * The deterministic, source-anchored evidence synthesis — rendered as the opening
 * "Eamos" message of the Ask-Eamos chat thread (docs/ai-work-rail/spec.md): the
 * conversation starts already summarised, and scrolls up as the user chats. The
 * synthesis prose, then a slim provenance footnote, then any warning chips. The
 * "Eamos" role label is supplied by the surrounding chat message. Styling lives in
 * work-rail.css (`.wr-ai-*`).
 */
export function EvidenceSummary({ payload }: EvidenceSummaryProps) {
  const typedSummary = payload.report_profile?.interpretation_summary
  const hasTypedSummary = typedSummary != null
  const summary = hasTypedSummary
    ? typedSummary.text?.trim()
    : payload.ai_clinical_summary?.trim()
  const warnings = typedSummary?.warnings ?? []
  if (!summary && warnings.length === 0) return null

  return (
    <div className="wr-ai-summary">
      <div className="wr-ai-prose">
        {summary ? (
          summary.split(/\n+/).map((para, i) => <p key={i}>{para}</p>)
        ) : (
          <p className="wr-ai-prose-empty">
            Interpretation summary unavailable for this lookup.
          </p>
        )}
      </div>
      <p className="wr-ai-synth">
        <InfoIcon />
        <span>Synthesised from the cited evidence in this report.</span>
      </p>
      {warnings.length > 0 && (
        <div className="wr-ai-warnings">
          {warnings.slice(0, 3).map((warning) => (
            <span key={warning} className="wr-ai-warn">
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
      width="13"
      height="13"
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
