import type { ReactNode } from 'react'

import { Card } from '@/components/ui/Card'
import type { LookupSectionEnvelope } from '@/lib/backend'
import {
  REPORT_SECTION_BY_ID,
  reportSectionStateCopy,
  reportSectionUiStateFromEnvelope,
  type ReportSectionId,
  type ReportSectionUiState,
} from '@/lib/report-section-registry'

export function ExpertPanelPartialNote() {
  return (
    <div role="note" className="report-source-note" data-report-section-state="partial">
      <span className="report-source-note__mark" aria-hidden="true">i</span>
      <span>
        <strong>Clinical source scope.</strong> Expert-panel classification currently follows the
        clinical-consensus snapshot. Full VCEP attribution appears when the ClinGen Evidence
        Repository source cache is available.
      </span>
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

  return (
    <div
      role={state === 'failed' ? 'alert' : 'status'}
      className={`report-section-state report-section-state--${state}`}
      data-report-section-state={state}
    >
      <span className="report-section-state__mark" aria-hidden="true" />
      <div className="report-section-state__copy">
        <div className="report-section-state__title">{copy}</div>
        {detail && <div className="report-section-state__detail">{detail}</div>}
        {state === 'loading' && (
          <span className="report-section-state__skeleton" aria-hidden="true">
            <span />
            <span />
          </span>
        )}
      </div>
      {action && state === 'failed' && action}
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
