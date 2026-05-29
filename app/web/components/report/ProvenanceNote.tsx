// ProvenanceNote — a small per-section caveat that flags when a section's data
// is sample / fixture / not live-hydrated, instead of letting non-live data
// pass silently as real. Driven by the warning codes the payload (or an
// adapter) already emits. Renders nothing when there are no warnings, so a
// fully live section stays clean.

interface ProvenanceNoteProps {
  /** Raw warning codes (e.g. 'clinvar_track_not_live_hydrated'). */
  warnings: string[]
  /** 'warn' = amber, draws the eye to non-live data (default). 'muted' = quiet. */
  tone?: 'warn' | 'muted'
}

// Friendly text for the codes we know; everything else is humanised generically.
const FRIENDLY: Record<string, string> = {
  offline_fixture_not_live_source_backed: 'Offline sample, not live-sourced',
  clinvar_track_is_sample_bounded: 'ClinVar markers are sample-bounded',
  clinvar_track_not_live_hydrated: 'ClinVar track not live-hydrated',
  exon_intron_table_from_sample_scaffold: 'Exon/intron model from RPE65 sample scaffold',
  exon_intron_table_window_only: 'Exon/intron model is window-only (not whole-gene)',
  conservation_from_sample_scaffold: 'Conservation from RPE65 sample scaffold',
  conservation_unavailable: 'Conservation track unavailable',
}

function humanize(code: string): string {
  if (FRIENDLY[code]) return FRIENDLY[code]
  const spaced = code.replace(/_/g, ' ').trim()
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export function ProvenanceNote({ warnings, tone = 'warn' }: ProvenanceNoteProps) {
  const cleaned = Array.from(new Set(warnings.filter(Boolean)))
  if (cleaned.length === 0) return null

  const warn = tone === 'warn'
  return (
    <div
      role="note"
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 7,
        padding: '6px 10px',
        borderRadius: 'var(--r-sm)',
        background: warn ? 'var(--warn-tint)' : 'var(--bg-soft)',
        border: `0.5px solid ${warn ? 'var(--warn-bdr)' : 'var(--line)'}`,
        color: warn ? 'var(--warn-text)' : 'var(--ink-4)',
        fontSize: 10.5,
        lineHeight: 1.4,
        overflowWrap: 'anywhere',
      }}
    >
      <svg
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        style={{ flex: '0 0 auto', marginTop: 1 }}
      >
        <path d="M12 9v4M12 17h.01" />
        <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
      </svg>
      <span>
        <strong style={{ fontWeight: 700 }}>Sample data:</strong> {cleaned.map(humanize).join(' · ')}
      </span>
    </div>
  )
}
