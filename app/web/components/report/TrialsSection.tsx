import { Card } from '@/components/ui/Card'
import type { ReportPayload, TrialMatch } from '@/lib/backend'

interface TrialsSectionProps {
  payload: ReportPayload
  number?: number
}

export function TrialsSection({ payload, number }: TrialsSectionProps) {
  const typedTrials = payload.report_profile?.therapies_trials ?? null
  const trials = typedTrials?.trial_rows ?? []
  const warnings = typedTrials?.warnings ?? []
  if (trials.length === 0 && warnings.length === 0) return null

  return (
    <Card number={number} title="Active trials & approved therapies" meta="ClinicalTrials.gov">
      {trials.length > 0 && <TrialRows rows={trials} />}
      {typedTrials && trials.length === 0 && (
        <p
          style={{
            margin: 0,
            fontSize: 12.5,
            lineHeight: 1.6,
            color: 'var(--ink-4)',
          }}
        >
          No structured ClinicalTrials.gov rows are available for this lookup.
        </p>
      )}
      {warnings.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {warnings.slice(0, 2).map((warning) => (
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
    </Card>
  )
}

function TrialRows({ rows }: { rows: TrialMatch[] }) {
  return (
    <div className="mt-4" style={{ borderTop: '0.5px solid var(--line)' }}>
      <div
        className="py-2 uppercase"
        style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--ink-4)' }}
      >
        {rows.length} ClinicalTrials.gov record{rows.length === 1 ? '' : 's'}
      </div>
      <div className="flex flex-col">
        {rows.map((row) => (
          <TrialRow key={row.nct_id} row={row} />
        ))}
      </div>
    </div>
  )
}

function TrialRow({ row }: { row: TrialMatch }) {
  const detail = [
    row.status ? formatStatus(row.status) : null,
    row.phase,
    row.match_level ? formatWarning(row.match_level) : null,
  ].filter((item): item is string => Boolean(item))
  const condition = row.conditions?.[0]
  const intervention = row.interventions?.[0]
  const location = row.locations?.[0]

  return (
    <a
      href={row.source_url}
      target="_blank"
      rel="noreferrer"
      style={{
        display: 'block',
        borderTop: '0.5px solid var(--line)',
        padding: '10px 0',
        color: 'inherit',
        textDecoration: 'none',
      }}
    >
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-3)' }}>
          {row.nct_id}
        </span>
        {detail.map((item) => (
          <span
            key={item}
            style={{
              border: '0.5px solid var(--line)',
              borderRadius: 999,
              padding: '2px 7px',
              fontSize: 10.5,
              color: 'var(--ink-3)',
              background: 'var(--bg-soft)',
            }}
          >
            {item}
          </span>
        ))}
      </div>
      <div style={{ marginTop: 5, fontSize: 13, fontWeight: 700, color: 'var(--ink)' }}>
        {row.title}
      </div>
      {(condition || intervention || location) && (
        <div style={{ marginTop: 4, fontSize: 11.5, lineHeight: 1.55, color: 'var(--ink-4)' }}>
          {[condition, intervention, location].filter(Boolean).join(' | ')}
        </div>
      )}
    </a>
  )
}

function formatStatus(value: string): string {
  return value
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function formatWarning(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}
