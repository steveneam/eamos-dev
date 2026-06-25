'use client'
import { useState, type ReactNode } from 'react'
import { Card } from '@/components/ui/Card'
import type { ReportPayload, TherapiesTrialsSection, TrialMatch } from '@/lib/backend'

interface TrialsSectionProps {
  payload: ReportPayload
  section?: TherapiesTrialsSection | null
  number?: number
  /** Optional action slot (CopyButton) forwarded to the Card header. */
  actions?: ReactNode
}

const VISIBLE_TRIALS = 5

export function TrialsSection({ payload, section, number, actions }: TrialsSectionProps) {
  const typedTrials = section ?? payload.report_profile?.therapies_trials ?? null
  const trials = typedTrials?.trial_rows ?? []
  const warnings = typedTrials?.warnings ?? []
  if (typedTrials == null) return null

  return (
    <Card
      number={number}
      title="Active trials & approved therapies"
      meta="ClinicalTrials.gov"
      actions={actions}
    >
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
                color: 'var(--warn-text)',
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
  const [expanded, setExpanded] = useState(false)
  const hasOverflow = rows.length > VISIBLE_TRIALS
  const visible = expanded ? rows : rows.slice(0, VISIBLE_TRIALS)
  const hiddenCount = rows.length - VISIBLE_TRIALS

  return (
    <div className="mt-4" style={{ borderTop: '0.5px solid var(--line)' }}>
      <div
        className="py-2 uppercase"
        style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--ink-4)' }}
      >
        {hasOverflow && !expanded
          ? `Showing ${VISIBLE_TRIALS} of ${rows.length} ClinicalTrials.gov records`
          : `${rows.length} ClinicalTrials.gov record${rows.length === 1 ? '' : 's'}`}
      </div>
      <div className="flex flex-col">
        {visible.map((row) => (
          <TrialRow key={row.nct_id} row={row} />
        ))}
      </div>
      {hasOverflow && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="eamos-toggle-btn mt-3"
        >
          <span aria-hidden style={{ color: 'var(--ink-3)' }}>{expanded ? '−' : '+'}</span>
          {expanded ? 'Show fewer' : `View ${hiddenCount} more trial${hiddenCount === 1 ? '' : 's'}`}
        </button>
      )}
    </div>
  )
}

function TrialRow({ row }: { row: TrialMatch }) {
  const neutralPills = [
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
      className="trial-row-link"
      style={{
        display: 'block',
        borderTop: '0.5px solid var(--line)',
        padding: '10px 0',
        color: 'inherit',
        textDecoration: 'none',
        transition: `background var(--dur-1) var(--ease-standard)`,
        borderRadius: 4,
      }}
    >
      <style>{`
        .trial-row-link:hover { background: var(--bg-soft) !important; }
        .trial-row-link:focus-visible { outline: none; box-shadow: 0 0 0 3px rgba(29,158,117,0.14); }
      `}</style>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-3)' }}>
          {row.nct_id}
        </span>
        {row.status && <StatusPill status={row.status} />}
        {neutralPills.map((item) => (
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

// ClinicalTrials.gov recruitment-status colour coding (per Codex/Steven split):
// RECRUITING green · NOT_YET_RECRUITING yellow · ACTIVE_NOT_RECRUITING red ·
// everything else neutral. Phase + match_level stay neutral (above).
function StatusPill({ status }: { status: string }) {
  const tone = statusTone(status)
  return (
    <span
      style={{
        border: `0.5px solid ${tone.border}`,
        borderRadius: 999,
        padding: '2px 7px',
        fontSize: 10.5,
        fontWeight: 600,
        color: tone.fg,
        background: tone.bg,
      }}
    >
      {formatStatus(status)}
    </span>
  )
}

function statusTone(status: string): { bg: string; fg: string; border: string } {
  switch (status.toUpperCase()) {
    case 'RECRUITING':
      return { bg: 'var(--teal-tint)', fg: 'var(--teal-deep)', border: 'var(--teal-bdr)' }
    case 'NOT_YET_RECRUITING':
      return { bg: 'var(--warn-tint)', fg: 'var(--warn-text)', border: 'var(--warn-bdr)' }
    case 'ACTIVE_NOT_RECRUITING':
      return { bg: 'var(--err-tint)', fg: 'var(--err)', border: 'var(--cls-path-bdr)' }
    default:
      return { bg: 'var(--bg-soft)', fg: 'var(--ink-3)', border: 'var(--line)' }
  }
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
