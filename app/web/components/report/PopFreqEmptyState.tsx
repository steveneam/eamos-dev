// PopFreqEmptyState — no-data state for the report's Population Frequency
// section.
//
// Rendered when a variant has no population-frequency observation: a novel
// variant, or a reference dataset with no coverage at this locus. A blank or
// broken-looking section would read as a data-pipeline failure, and a bare
// "not found" would read as evidence against pathogenicity — neither is
// correct. This state names the situation plainly and makes the clinical
// caveat explicit: for a rare-disease candidate, absence from population
// databases is expected and is not evidence against pathogenicity.
//
// Pure presentational component — no hooks, no client boundary required.

interface PopFreqEmptyStateProps {
  variantId?: string | null
  /** e.g. "gnomAD v4" */
  dataset?: string | null
  /** e.g. "GRCh38" */
  genomeBuild?: string | null
  /** Optional backend-supplied reason for the absence. */
  reason?: string | null
}

export function PopFreqEmptyState({ variantId, dataset, genomeBuild, reason }: PopFreqEmptyStateProps) {
  const headline = dataset ? `Not observed in ${dataset}` : 'No population frequency data'
  const hasMeta = Boolean(variantId || genomeBuild)

  return (
    <div
      role="status"
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '28px 28px 24px',
      }}
    >
      <div className="flex items-start gap-4">
        {/* Empty-reading glyph: a flat baseline with faint, dashed near-zero
            bars — a histogram that recorded nothing, not a cutesy icon. */}
        <svg
          width="36"
          height="36"
          viewBox="0 0 36 36"
          fill="none"
          aria-hidden="true"
          style={{ flex: '0 0 auto', marginTop: 2 }}
        >
          <line x1="4" y1="29" x2="32" y2="29" stroke="var(--ink-4)" strokeWidth="1" />
          <rect x="8" y="25" width="5" height="4" rx="1" stroke="var(--ink-4)" strokeWidth="1" strokeDasharray="1.5 2" />
          <rect x="15.5" y="23" width="5" height="6" rx="1" stroke="var(--ink-4)" strokeWidth="1" strokeDasharray="1.5 2" />
          <rect x="23" y="25" width="5" height="4" rx="1" stroke="var(--ink-4)" strokeWidth="1" strokeDasharray="1.5 2" />
        </svg>

        <div className="flex-1">
          <div
            style={{
              fontFamily: 'var(--display)',
              fontSize: 17,
              fontWeight: 500,
              letterSpacing: '-0.01em',
              color: 'var(--ink)',
            }}
          >
            {headline}
          </div>

          <p style={{ marginTop: 6, fontSize: 13, lineHeight: 1.55, color: 'var(--ink-2)', maxWidth: '58ch' }}>
            For a rare-disease candidate, absence from population reference databases is expected and is not
            evidence against pathogenicity. Absence of evidence is not evidence of absence.
          </p>

          {reason ? <p style={{ marginTop: 8, fontSize: 12, color: 'var(--ink-3)' }}>{reason}</p> : null}

          {hasMeta ? (
            <div className="flex flex-wrap items-center gap-2" style={{ marginTop: 12 }}>
              {variantId ? (
                <span
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 11,
                    color: 'var(--ink-4)',
                    border: '0.5px solid var(--line)',
                    borderRadius: 999,
                    padding: '2px 8px',
                  }}
                >
                  {variantId}
                </span>
              ) : null}
              {genomeBuild ? (
                <span
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 11,
                    color: 'var(--ink-4)',
                    border: '0.5px solid var(--line)',
                    borderRadius: 999,
                    padding: '2px 8px',
                  }}
                >
                  {genomeBuild}
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
