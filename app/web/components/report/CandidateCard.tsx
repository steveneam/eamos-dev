import type { SearchInputCandidate } from '@/lib/backend'

// Shared source-backed candidate card. Extracted verbatim from
// SearchInterpretationPanel so the search interpretation flow and the
// paper → variants ambiguous-row chooser render the SAME card with the SAME
// fail-closed disabled state (`!(gene && cdna)` → "Needs source coordinates").
// Reuse, don't fork — see [[feedback_reuse_assets]].

export function formatToken(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

export function candidateSubtitle(candidate: SearchInputCandidate): string {
  return [
    candidate.transcript,
    candidate.cdna,
    candidate.protein_change,
    candidate.genomic_hg38 ?? candidate.genomic_hgvs,
  ]
    .filter(Boolean)
    .join(' | ')
}

interface CandidateCardProps {
  candidate: SearchInputCandidate
  onSelect: (candidate: SearchInputCandidate) => void
  /** Action label shown when the candidate is source-backed (gene && cdna).
   *  Defaults to the search panel's "Open report"; the paper chooser keeps it. */
  actionLabel?: string
}

export function CandidateCard({ candidate, onSelect, actionLabel = 'Open report' }: CandidateCardProps) {
  // Fail-closed: a candidate is only actionable when it carries source-backed
  // coordinates (gene + cDNA). Ambiguous/coordinate-less suggestions render
  // disabled — never as a clickable clinical action.
  const canOpen = Boolean(candidate.gene && candidate.cdna)
  return (
    <button
      type="button"
      disabled={!canOpen}
      onClick={() => onSelect(candidate)}
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
          {canOpen ? actionLabel : 'Needs source coordinates'}
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
}
