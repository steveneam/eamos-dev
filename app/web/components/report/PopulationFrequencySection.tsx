'use client'

import { useCallback, useMemo, useState, type CSSProperties } from 'react'

import type { PopulationFrequencyReportSection } from '@/lib/backend'

import { PopulationAgeDistribution } from './PopulationAgeDistribution'
import { AncestryFrequencyTab } from './population-frequency/PopulationFrequencyAncestry'
import { MapOverviewTab } from './population-frequency/PopulationFrequencyMap'
import {
  machineText,
  sourceStatusNeedsDisclosure,
  unavailableReasonCopy,
  uniqueWarnings,
  warningCopy,
} from './population-frequency/populationFrequencyModel'

interface PopulationFrequencySectionProps {
  section?: PopulationFrequencyReportSection | null
  unavailable?: PopulationFrequencyUnavailableState | null
}

interface PopulationFrequencyUnavailableState {
  sourceStatus?: string | null
  unavailableReason?: string | null
  warnings?: string[]
  variantId?: string | null
  dataset?: string | null
  genomeBuild?: string | null
  sequencingType?: string | null
}

type PopulationTab = 'map' | 'ancestry' | 'age'

export function PopulationFrequencySection({
  section,
  unavailable = null,
}: PopulationFrequencySectionProps) {
  const [activeTab, setActiveTab] = useState<PopulationTab>('map')
  const warnings = section?.warnings ?? []
  const groups = useMemo(
    () =>
      [...(section?.visual_groups ?? [])].sort(
        (a, b) => (a.sort_order ?? 99) - (b.sort_order ?? 99),
      ),
    [section?.visual_groups],
  )
  const [hoverGroupId, setHoverGroupId] = useState<string | null>(null)
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null)
  const handleSelectGroup = useCallback((id: string | null) => {
    setSelectedGroupId((current) => (current === id ? null : id))
  }, [])

  if (!section) {
    return <PopulationUnavailableStatePanel state={unavailable ?? { sourceStatus: 'missing' }} />
  }
  const disclosureWarnings = uniqueWarnings(warnings)
  const showStatusNote =
    Boolean(section.unavailable_reason) ||
    sourceStatusNeedsDisclosure(section.source_status) ||
    disclosureWarnings.some((warning) =>
      /unavailable|failed|failure|missing|gnomad_source_status/.test(warning),
    )

  return (
    <div id={section.section_id} className="scroll-mt-24" data-panel-id={section.panel_id}>
      <div
        className="flex flex-wrap items-center justify-between gap-3"
        style={{ marginBottom: 14 }}
      >
        <div
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 11.5,
            color: 'var(--ink-3)',
            overflowWrap: 'anywhere',
          }}
        >
          {section.variant_id || 'Variant ID unavailable'} · {section.sequencing_type}
        </div>
        <div className="inline-flex gap-1 rounded-lg border border-[var(--line)] bg-[var(--bg-soft)] p-1">
          <TabButton active={activeTab === 'map'} onClick={() => setActiveTab('map')}>
            World map
          </TabButton>
          <TabButton active={activeTab === 'ancestry'} onClick={() => setActiveTab('ancestry')}>
            Ancestry group frequencies
          </TabButton>
          <TabButton active={activeTab === 'age'} onClick={() => setActiveTab('age')}>
            Age distribution
          </TabButton>
        </div>
      </div>

      {showStatusNote && (
        <PopulationStatusNote
          sourceStatus={section.source_status}
          unavailableReason={section.unavailable_reason}
          warnings={disclosureWarnings}
        />
      )}

      <div id={section.panel_id}>
        <div>
          {activeTab === 'map' ? (
            <MapOverviewTab
              groups={groups}
              hoveredId={hoverGroupId}
              selectedId={selectedGroupId}
              onHoverGroup={setHoverGroupId}
              onSelectGroup={handleSelectGroup}
            />
          ) : activeTab === 'ancestry' ? (
            <AncestryFrequencyTab
              groups={groups}
              hoveredId={hoverGroupId}
              selectedId={selectedGroupId}
              overall={section.overall}
              sourceUrl={section.source_url}
              warnings={warnings}
              onHoverGroup={setHoverGroupId}
              onSelectGroup={handleSelectGroup}
            />
          ) : (
            <PopulationAgeDistribution histograms={section.age_histograms ?? []} />
          )}
        </div>
      </div>
    </div>
  )
}

function PopulationUnavailableStatePanel({
  state,
}: {
  state: PopulationFrequencyUnavailableState
}) {
  const warnings = uniqueWarnings(state.warnings ?? [])
  const reason = unavailableReasonCopy(state.unavailableReason)
  const status = machineText(state.sourceStatus) ?? 'missing'
  const meta = [
    state.variantId,
    state.dataset,
    state.genomeBuild,
    state.sequencingType,
  ]
    .filter(Boolean)
    .join(' | ')
  return (
    <div
      role="note"
      style={{
        border: '0.5px solid var(--warn-bdr)',
        borderRadius: 'var(--r-md)',
        background: 'var(--warn-tint)',
        color: 'var(--ink-2)',
        padding: '14px 16px',
        display: 'grid',
        gap: 8,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          gap: 10,
          flexWrap: 'wrap',
        }}
      >
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink)' }}>
            Frequency data unavailable
          </div>
          {meta && (
            <div
              style={{
                marginTop: 2,
                fontFamily: 'var(--mono)',
                fontSize: 11,
                color: 'var(--ink-3)',
                overflowWrap: 'anywhere',
              }}
            >
              {meta}
            </div>
          )}
        </div>
        <span style={statusChipStyle}>{status}</span>
      </div>
      <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.5, color: 'var(--ink-3)' }}>
        {reason ??
          'The backend did not return source-backed gnomAD frequency metrics for this variant.'}
      </p>
      {warnings.length > 0 && (
        <ul
          style={{
            margin: 0,
            paddingLeft: 17,
            display: 'grid',
            gap: 4,
            fontSize: 11.5,
            lineHeight: 1.45,
            color: 'var(--ink-3)',
          }}
        >
          {warnings.slice(0, 4).map((warning) => (
            <li key={warning}>{warningCopy(warning)}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function PopulationStatusNote({
  sourceStatus,
  unavailableReason,
  warnings,
}: {
  sourceStatus?: string | null
  unavailableReason?: string | null
  warnings: string[]
}) {
  const reason = unavailableReasonCopy(unavailableReason)
  const status = machineText(sourceStatus)
  const statusText =
    reason ??
    (warnings.map(warningCopy).slice(0, 2).join(' | ') ||
      'No live frequency result was returned.')
  return (
    <div
      role="note"
      style={{
        marginBottom: 14,
        border: '0.5px solid var(--warn-bdr)',
        borderRadius: 'var(--r-sm)',
        background: 'var(--warn-tint)',
        color: 'var(--ink-3)',
        padding: '8px 10px',
        fontSize: 11.5,
        lineHeight: 1.45,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 10,
        flexWrap: 'wrap',
      }}
    >
      <span style={{ minWidth: 0, overflowWrap: 'anywhere' }}>
        <strong style={{ color: 'var(--ink)', fontWeight: 700 }}>
          gnomAD source state:
        </strong>{' '}
        {statusText}
      </span>
      {status && <span style={statusChipStyle}>{status}</span>}
    </div>
  )
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean
  children: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      data-active={active}
      className="pop-tab-btn"
      style={{
        border: '0.5px solid',
        borderColor: active ? 'var(--teal)' : 'transparent',
        background: active ? 'var(--teal-tint)' : 'transparent',
        color: active ? 'var(--teal-deep)' : 'var(--ink-3)',
        borderRadius: 'var(--r-sm)',
        padding: '7px 10px',
        fontSize: 11.5,
        fontWeight: 700,
        cursor: 'pointer',
        maxWidth: 220,
        whiteSpace: 'normal',
        lineHeight: 1.2,
        transition:
          'background var(--dur-1) var(--ease-standard),' +
          'border-color var(--dur-1) var(--ease-standard),' +
          'color var(--dur-1) var(--ease-standard)',
      }}
    >
      <style>{`
        .pop-tab-btn[data-active="false"]:hover {
          background: var(--bg);
          color: var(--ink);
          border-color: var(--ink-5);
        }
        .pop-tab-btn:focus-visible {
          outline: none;
          box-shadow: 0 0 0 3px rgba(29, 158, 117, 0.18);
        }
        .pop-tab-btn:active {
          transform: translateY(0.5px);
          transition-duration: 80ms;
        }
      `}</style>
      {children}
    </button>
  )
}

const statusChipStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  border: '0.5px solid var(--warn-bdr)',
  borderRadius: 999,
  background: 'var(--bg)',
  color: 'var(--warn)',
  padding: '2px 7px',
  fontSize: 10.5,
  fontWeight: 700,
  whiteSpace: 'nowrap',
}
