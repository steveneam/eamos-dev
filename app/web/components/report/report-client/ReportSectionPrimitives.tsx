import type { ReactNode } from 'react'

import { Card } from '@/components/ui/Card'
import type { LookupSectionEnvelope, ReportSectionSignal } from '@/lib/backend'
import {
  REPORT_SECTION_BY_ID,
  REPORT_SIGNAL_ANCHORS,
  reportSectionStateCopy,
  reportSectionUiStateFromEnvelope,
  type ReportSectionId,
  type ReportSectionUiState,
} from '@/lib/report-section-registry'

export function ExpertPanelPartialNote() {
  return (
    <div
      role="note"
      data-report-section-state="partial"
      style={{
        marginTop: 18,
        padding: '12px 14px',
        background: 'var(--warn-tint)',
        border: '0.5px solid var(--warn-bdr)',
        borderRadius: 'var(--r-md)',
        fontSize: 12,
        lineHeight: 1.5,
        color: 'var(--ink-3)',
      }}
    >
      Expert-panel classification is derived from the current clinical-consensus snapshot, not the
      ClinGen Evidence Repository. Full VCEP attribution lands when the Evidence-Repository
      source-cache is integrated.
    </div>
  )
}

export function ReportSectionSlot({
  sectionId,
  children,
}: {
  sectionId: ReportSectionId
  children: ReactNode
}) {
  const section = REPORT_SECTION_BY_ID[sectionId]
  const required = section.requiredSlot ? 'true' : undefined
  const preflight = section.preflightRequired ? 'true' : undefined

  return (
    <section
      id={section.anchorId}
      className="scroll-mt-24"
      aria-label={section.label}
      data-report-section-slot={section.id}
      data-report-section-required={required}
      data-report-section-preflight={preflight}
    >
      {(section.aliasAnchors ?? []).map((anchorId) => (
        <div
          key={anchorId}
          id={anchorId}
          className="scroll-mt-24"
          data-report-section-alias={section.id}
        />
      ))}
      {children}
    </section>
  )
}

export function ReportSectionState({
  sectionId,
  state,
  detail,
  action,
}: {
  sectionId: ReportSectionId
  state: Exclude<ReportSectionUiState, 'ready'>
  detail?: string
  action?: ReactNode
}) {
  const section = REPORT_SECTION_BY_ID[sectionId]
  const copy = reportSectionStateCopy(section, state)
  const isWarningState = state === 'failed' || state === 'stale' || state === 'partial'

  return (
    <div
      role={state === 'failed' ? 'alert' : 'status'}
      data-report-section-state={state}
      style={{
        border: `0.5px solid ${isWarningState ? 'var(--warn-bdr)' : 'var(--line)'}`,
        borderRadius: 8,
        padding: '14px 16px',
        background: isWarningState ? 'var(--warn-tint)' : 'var(--bg-soft)',
        color: 'var(--ink-4)',
        fontSize: 12,
        lineHeight: 1.55,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 10,
        }}
      >
        <span>{copy}</span>
        {action && state === 'failed' && action}
      </div>
      {detail && <div style={{ marginTop: 6, overflowWrap: 'anywhere' }}>{detail}</div>}
    </div>
  )
}

export function ReportSectionSkeletonCard({ sectionId }: { sectionId: ReportSectionId }) {
  return <ReportSectionStateCard sectionId={sectionId} state="loading" />
}

export function ReportSectionEmptyCard({ sectionId }: { sectionId: ReportSectionId }) {
  return <ReportSectionStateCard sectionId={sectionId} state="empty" />
}

export function ReportSectionErrorCard({
  sectionId,
  message,
  action,
}: {
  sectionId: ReportSectionId
  message: string
  action: ReactNode
}) {
  return (
    <ReportSectionStateCard
      sectionId={sectionId}
      state="failed"
      detail={message}
      action={action}
    />
  )
}

export function ReportSectionStateCard({
  sectionId,
  state,
  detail,
  action,
}: {
  sectionId: ReportSectionId
  state: Exclude<ReportSectionUiState, 'ready'>
  detail?: string
  action?: ReactNode
}) {
  const section = REPORT_SECTION_BY_ID[sectionId]
  return (
    <Card number={section.number} title={section.title} meta={section.meta}>
      <ReportSectionState
        sectionId={sectionId}
        state={state}
        detail={detail}
        action={action}
      />
    </Card>
  )
}

export function stateFromEnvelope(
  envelope: LookupSectionEnvelope,
  fallback: Exclude<ReportSectionUiState, 'ready'> = 'partial',
): Exclude<ReportSectionUiState, 'ready'> {
  const state = reportSectionUiStateFromEnvelope(envelope)
  return state === 'ready' ? fallback : state
}

const SIGNAL_STATUS_LABEL: Record<ReportSectionSignal['status'], string> = {
  ready: 'Ready',
  limited: 'Limited',
  empty: 'Empty',
  error: 'Error',
  loading: 'Loading',
}

function signalStatusColor(status: ReportSectionSignal['status']): string {
  if (status === 'ready') return 'var(--teal-deep)'
  if (status === 'limited') return 'var(--warn)'
  if (status === 'error') return 'var(--err)'
  return 'var(--ink-4)'
}

export function ReportSignalDashboard({
  signals,
}: {
  signals?: ReportSectionSignal[] | null
}) {
  const rows = (signals ?? []).slice(0, 8)
  if (!rows.length) return null

  return (
    <div
      aria-label="Evidence signals"
      style={{
        display: 'grid',
        gap: 10,
        padding: '12px 14px',
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-md)',
        background: 'var(--bg)',
        boxShadow: 'var(--elev-1)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          gap: 10,
        }}
      >
        <div className="eamos-kicker">Evidence signals</div>
        <span style={{ fontSize: 11, color: 'var(--ink-4)' }}>Backend-ranked sections</span>
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(156px, 1fr))',
          gap: 8,
        }}
      >
        {rows.map((signal) => {
          const anchor = REPORT_SIGNAL_ANCHORS[signal.section_id]
          const content = (
            <>
              <span
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 8,
                  color: 'var(--ink)',
                  fontSize: 12,
                  fontWeight: 600,
                  lineHeight: 1.25,
                }}
              >
                <span>{signal.label}</span>
                <span
                  style={{ fontFamily: 'var(--mono)', color: 'var(--ink-4)', fontSize: 10 }}
                >
                  {signal.priority}
                </span>
              </span>
              <span
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 8,
                  marginTop: 5,
                  fontSize: 10.5,
                  color: 'var(--ink-4)',
                }}
              >
                <span style={{ color: signalStatusColor(signal.status), fontWeight: 600 }}>
                  {SIGNAL_STATUS_LABEL[signal.status]}
                </span>
                <span>{signal.default_open ? 'Open' : 'Collapsed'}</span>
              </span>
            </>
          )
          const title =
            [signal.headline, ...signal.data_notes].filter(Boolean).join(' | ') || signal.relevance
          const baseStyle = {
            display: 'block',
            minHeight: 58,
            padding: '8px 10px',
            border: '0.5px solid var(--line)',
            borderRadius: 'var(--r-sm)',
            background: signal.default_open ? 'var(--teal-tint)' : 'var(--bg-soft)',
            textDecoration: 'none',
          }
          return anchor ? (
            <a key={signal.section_id} href={`#${anchor}`} title={title} style={baseStyle}>
              {content}
            </a>
          ) : (
            <div key={signal.section_id} title={title} style={baseStyle}>
              {content}
            </div>
          )
        })}
      </div>
    </div>
  )
}
