import type { SearchInputCandidate, SearchInputInterpretation } from '@/lib/backend'

interface SearchInterpretationPanelProps {
  query: string
  interpretation: SearchInputInterpretation
  limitations?: string | null
  onSelectCandidate: (candidate: SearchInputCandidate) => void
}

function formatToken(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

function candidateSubtitle(candidate: SearchInputCandidate): string {
  return [
    candidate.transcript,
    candidate.cdna,
    candidate.protein_change,
    candidate.genomic_hg38 ?? candidate.genomic_hgvs,
  ]
    .filter(Boolean)
    .join(' | ')
}

export function SearchInterpretationPanel({
  query,
  interpretation,
  limitations,
  onSelectCandidate,
}: SearchInterpretationPanelProps) {
  const candidates = interpretation.candidates ?? []
  const prompt =
    interpretation.ui_prompt ??
    limitations ??
    'Review the source-backed interpretation before opening a report.'
  const warnings = [...(interpretation.assumptions ?? []), ...(interpretation.warnings ?? [])]

  return (
    <section
      role="status"
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '24px 28px',
        color: 'var(--ink)',
      }}
    >
      <div
        className="uppercase"
        style={{
          fontSize: 10.5,
          fontWeight: 700,
          letterSpacing: '0.08em',
          color: 'var(--ink-4)',
        }}
      >
        Search interpretation
      </div>
      <h2
        style={{
          fontFamily: 'var(--display)',
          fontSize: 18,
          fontWeight: 650,
          margin: '6px 0 0',
          color: 'var(--ink)',
        }}
      >
        {candidates.length > 0 ? 'Choose a source-backed match' : 'Search needs more detail'}
      </h2>
      <div
        className="mt-1"
        style={{
          fontFamily: 'var(--mono)',
          fontSize: 12.5,
          color: 'var(--ink-3)',
          overflowWrap: 'anywhere',
        }}
      >
        {query}
      </div>
      <p style={{ margin: '12px 0 0', fontSize: 13.5, lineHeight: 1.6, color: 'var(--ink-2)' }}>
        {prompt}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {[interpretation.mode, interpretation.confidence].filter(Boolean).map((item) => (
          <span
            key={item}
            style={{
              border: '0.5px solid var(--line)',
              borderRadius: 999,
              background: 'var(--bg-soft)',
              padding: '4px 8px',
              fontSize: 11,
              color: 'var(--ink-3)',
            }}
          >
            {formatToken(item)}
          </span>
        ))}
      </div>

      {candidates.length > 0 && (
        <div className="mt-5 flex flex-col gap-2">
          {candidates.map((candidate) => {
            const canOpen = Boolean(candidate.gene && candidate.cdna)
            return (
              <button
                key={candidate.candidate_id}
                type="button"
                disabled={!canOpen}
                onClick={() => onSelectCandidate(candidate)}
                style={{
                  border: '0.5px solid var(--line)',
                  borderRadius: 10,
                  background: canOpen ? 'var(--bg-soft)' : 'var(--bg)',
                  padding: '12px 14px',
                  textAlign: 'left',
                  cursor: canOpen ? 'pointer' : 'not-allowed',
                  opacity: canOpen ? 1 : 0.7,
                }}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--ink)' }}>
                    {candidate.display_label}
                  </span>
                  <span
                    style={{
                      fontSize: 10.5,
                      fontWeight: 700,
                      color: 'var(--teal-deep)',
                      textTransform: 'uppercase',
                    }}
                  >
                    {canOpen ? 'Open report' : 'Needs source coordinates'}
                  </span>
                </div>
                <div
                  className="mt-1"
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 11.5,
                    color: 'var(--ink-3)',
                    overflowWrap: 'anywhere',
                  }}
                >
                  {candidateSubtitle(candidate) || candidate.match_reason}
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {[candidate.match_reason, candidate.distance, ...candidate.source_support.slice(0, 3)]
                    .filter((item): item is string => Boolean(item))
                    .map((item) => (
                      <span
                        key={item}
                        style={{
                          border: '0.5px solid var(--line)',
                          borderRadius: 7,
                          background: 'var(--bg)',
                          padding: '3px 6px',
                          fontSize: 10.5,
                          color: 'var(--ink-4)',
                        }}
                      >
                        {formatToken(item)}
                      </span>
                    ))}
                </div>
              </button>
            )
          })}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {warnings.slice(0, 4).map((warning) => (
            <span
              key={warning}
              style={{
                border: '0.5px solid var(--warn-bdr)',
                borderRadius: 7,
                background: 'var(--warn-tint)',
                color: 'var(--warn-text)',
                padding: '5px 8px',
                fontSize: 10.5,
                fontWeight: 600,
                overflowWrap: 'anywhere',
              }}
            >
              {formatToken(warning)}
            </span>
          ))}
        </div>
      )}
    </section>
  )
}
