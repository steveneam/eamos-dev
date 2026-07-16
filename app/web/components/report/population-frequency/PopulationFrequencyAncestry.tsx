'use client'

import { Fragment, useMemo, useState } from 'react'

import type {
  PopulationFrequencyOverall,
  PopulationFrequencySexCell,
  PopulationFrequencyVisualGroup,
} from '@/lib/backend'
import { CopyButton } from '@/components/ui/CopyButton'
import { InfoPopover } from '@/components/ui/InfoHint'

import { PopulationUnavailablePanel } from './PopulationUnavailablePanel'
import { WorldFrequencyMap } from './PopulationFrequencyMap'
import {
  GEOGRAPHIC_GROUP_IDS,
  applyDatasetToGroup,
  applyDatasetToOverall,
  bandFill,
  buildAncestryFrequencyTsv,
  buildReadoutTsv,
  compactLabel,
  formatFrequency,
  formatInteger,
  groupContext,
  hasOverall,
  warningCopy,
} from './populationFrequencyModel'

export function AncestryFrequencyTab({
  groups,
  hoveredId,
  selectedId,
  overall,
  sourceUrl,
  warnings,
  onHoverGroup,
  onSelectGroup,
}: {
  groups: PopulationFrequencyVisualGroup[]
  hoveredId: string | null
  selectedId: string | null
  overall?: PopulationFrequencyOverall | null
  sourceUrl?: string | null
  warnings: string[]
  onHoverGroup: (id: string | null) => void
  onSelectGroup: (id: string | null) => void
}) {
  const [includeExome, setIncludeExome] = useState(true)
  const [includeGenome, setIncludeGenome] = useState(true)
  const displayGroups = useMemo(
    () => groups.map((group) => applyDatasetToGroup(group, includeExome, includeGenome)),
    [groups, includeExome, includeGenome],
  )

  if (groups.length === 0) {
    return <PopulationUnavailablePanel title="Genetic ancestry group frequencies unavailable" />
  }

  const toggleExome = () => setIncludeExome((value) => (value && !includeGenome ? value : !value))
  const toggleGenome = () => setIncludeGenome((value) => (value && !includeExome ? value : !value))
  const selectedDisplayGroup = selectedId
    ? displayGroups.find((group) => group.id === selectedId) ?? null
    : null
  const displayOverall = applyDatasetToOverall(overall, includeExome, includeGenome)
  const geographicGroups = displayGroups.filter((group) => GEOGRAPHIC_GROUP_IDS.has(group.id))
  const offMapGroups = displayGroups.filter((group) => !GEOGRAPHIC_GROUP_IDS.has(group.id))
  const chartMax = Math.max(0, ...displayGroups.map((group) => group.allele_frequency ?? 0))

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'stretch', gap: 16 }}>
      <div
        style={{
          flex: '1.2 1 360px',
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <div
          style={{
            border: '0.5px solid var(--line)',
            borderRadius: 8,
            background: 'linear-gradient(180deg, #f8fbfd 0%, #f1f6f8 100%)',
            overflow: 'hidden',
          }}
        >
          <WorldFrequencyMap
            groups={displayGroups}
            hoveredId={hoveredId}
            selectedId={selectedId}
            layout="side"
            showOffMap={false}
            onHoverGroup={onHoverGroup}
            onSelectGroup={onSelectGroup}
          />
        </div>

        <SelectedGroupInspector group={selectedDisplayGroup} />
        {hasOverall(displayOverall) && <CohortOverallReadout overall={displayOverall} />}
      </div>

      <aside
        style={{
          flex: '0.9 1 250px',
          minWidth: 0,
          border: '0.5px solid var(--line)',
          borderRadius: 8,
          background: 'var(--bg)',
          padding: 12,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <style>{`
          .pop-ancestry-bar[data-selected="true"] { transform: scale(1.015); }
          .pop-ancestry-bar[data-selected="false"]:active { transform: translateY(0.5px); transition-duration: 80ms; }
          .pop-ancestry-bar:focus-visible { outline: none; box-shadow: 0 0 0 3px rgba(29, 158, 117, 0.18); }
          @media (prefers-reduced-motion: reduce) { .pop-ancestry-bar { transition: none !important; } }
        `}</style>
        <div className="flex items-start justify-between gap-3">
          <div className="eamos-kicker">Allele frequency by gnomAD group</div>
          <CopyButton
            text={buildAncestryFrequencyTsv(displayGroups, displayOverall)}
            label="Copy allele frequency table"
          />
        </div>
        <DatasetIncludeControl
          includeExome={includeExome}
          includeGenome={includeGenome}
          onToggleExome={toggleExome}
          onToggleGenome={toggleGenome}
        />
        <div className="mt-3 flex flex-col gap-1.5">
          {geographicGroups.map((group) => (
            <AncestryBar
              key={group.id}
              group={group}
              chartMax={chartMax}
              isHovered={hoveredId === group.id}
              isSelected={selectedId === group.id}
              onHoverGroup={onHoverGroup}
              onSelectGroup={onSelectGroup}
            />
          ))}
        </div>
        {offMapGroups.length > 0 && (
          <div
            style={{
              marginTop: 12,
              padding: 10,
              borderRadius: 8,
              border: '0.5px solid var(--line)',
              background: 'var(--bg-soft)',
            }}
          >
            <div className="eamos-kicker">Non-geographic cohorts</div>
            <div
              style={{
                marginTop: 3,
                fontSize: 10,
                color: 'var(--ink-4)',
                lineHeight: 1.4,
              }}
            >
              Defined by genetic similarity, not geography — shown off the map.
            </div>
            <div className="mt-2 flex flex-col gap-1.5">
              {offMapGroups.map((group) => (
                <AncestryBar
                  key={group.id}
                  group={group}
                  chartMax={chartMax}
                  isHovered={hoveredId === group.id}
                  isSelected={selectedId === group.id}
                  onHoverGroup={onHoverGroup}
                  onSelectGroup={onSelectGroup}
                />
              ))}
            </div>
          </div>
        )}
        <div
          style={{
            marginTop: 'auto',
            paddingTop: 12,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          <DataNotesPopover warnings={warnings} />
          {sourceUrl && (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex"
              style={{ fontSize: 10.5, color: 'var(--ink-3)', textUnderlineOffset: 3 }}
            >
              Open source record
            </a>
          )}
        </div>
      </aside>
    </div>
  )
}

function DataNotesPopover({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null
  return (
    <InfoPopover
      label="gnomAD section data notes"
      triggerText={`Data notes (${warnings.length})`}
    >
      <div
        style={{ fontWeight: 700, color: 'var(--ink)', fontSize: 11.5, marginBottom: 6 }}
      >
        Data notes
      </div>
      <ul
        style={{
          margin: 0,
          paddingLeft: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 5,
        }}
      >
        {warnings.slice(0, 6).map((warning) => (
          <li key={warning} style={{ lineHeight: 1.45 }}>
            {warningCopy(warning)}
          </li>
        ))}
      </ul>
    </InfoPopover>
  )
}

function DatasetIncludeControl({
  includeExome,
  includeGenome,
  onToggleExome,
  onToggleGenome,
}: {
  includeExome: boolean
  includeGenome: boolean
  onToggleExome: () => void
  onToggleGenome: () => void
}) {
  return (
    <div className="mt-2 flex flex-wrap items-center" style={{ gap: 8 }}>
      <span
        style={{
          fontSize: 9.5,
          fontWeight: 700,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: 'var(--ink-4)',
        }}
      >
        Include
      </span>
      <DatasetCheckbox label="Exomes" checked={includeExome} onChange={onToggleExome} />
      <DatasetCheckbox label="Genomes" checked={includeGenome} onChange={onToggleGenome} />
    </div>
  )
}

function DatasetCheckbox({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: () => void
}) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      onClick={onChange}
      className="pop-dataset-chk"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        border: '0.5px solid',
        borderColor: checked ? 'var(--teal-bdr)' : 'var(--line)',
        background: checked ? 'var(--teal-tint)' : 'var(--bg)',
        color: checked ? 'var(--teal-deep)' : 'var(--ink-3)',
        borderRadius: 'var(--r-sm)',
        padding: '3px 9px',
        fontSize: 11,
        fontWeight: 600,
        cursor: 'pointer',
        transition:
          'background var(--dur-1) var(--ease-standard),' +
          'border-color var(--dur-1) var(--ease-standard),' +
          'color var(--dur-1) var(--ease-standard)',
      }}
    >
      <style>{`
        .pop-dataset-chk:focus-visible { outline: none; box-shadow: 0 0 0 3px rgba(29, 158, 117, 0.18); }
      `}</style>
      <span
        aria-hidden
        style={{
          width: 13,
          height: 13,
          borderRadius: 3,
          border: '1.5px solid',
          borderColor: checked ? 'var(--teal)' : 'var(--ink-5)',
          background: checked ? 'var(--teal)' : 'transparent',
          color: '#fff',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 9,
          lineHeight: 1,
          flex: '0 0 auto',
        }}
      >
        {checked ? '✓' : ''}
      </span>
      {label}
    </button>
  )
}

const INSPECTOR_BOX_STYLE = {
  minHeight: 192,
  boxSizing: 'border-box' as const,
  border: '0.5px solid var(--line)',
  borderRadius: 8,
  padding: 12,
  background: 'var(--bg-soft)',
}

function SelectedGroupInspector({ group }: { group: PopulationFrequencyVisualGroup | null }) {
  if (!group) {
    return (
      <div
        style={{
          ...INSPECTOR_BOX_STYLE,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <span
          style={{
            fontSize: 11.5,
            color: 'var(--ink-4)',
            textAlign: 'center',
            lineHeight: 1.45,
          }}
        >
          Click a group on the map or in the list for its breakdown.
        </span>
      </div>
    )
  }
  const rows: Array<{ label: string; cell: PopulationFrequencySexCell }> = [
    { label: 'Overall', cell: group },
    ...(group.xx ? [{ label: 'XX', cell: group.xx }] : []),
    ...(group.xy ? [{ label: 'XY', cell: group.xy }] : []),
  ]
  return (
    <InspectorReadout
      title={compactLabel(group.label)}
      rows={rows}
      note={groupContext(group)}
      copyable
    />
  )
}

function CohortOverallReadout({ overall }: { overall?: PopulationFrequencyOverall | null }) {
  const rows: Array<{ label: string; cell: PopulationFrequencySexCell }> = [
    ...(overall?.total ? [{ label: 'Total', cell: overall.total }] : []),
    ...(overall?.xx ? [{ label: 'XX', cell: overall.xx }] : []),
    ...(overall?.xy ? [{ label: 'XY', cell: overall.xy }] : []),
  ]
  if (rows.length === 0) return null
  return (
    <InspectorReadout
      kicker="All gnomAD samples"
      title="Whole-variant totals"
      rows={rows}
      note="Across all gnomAD ancestry groups."
      copyable
    />
  )
}

function InspectorReadout({
  kicker,
  title,
  rows,
  note,
  copyable = false,
}: {
  kicker?: string
  title: string
  rows: Array<{ label: string; cell: PopulationFrequencySexCell }>
  note: string
  copyable?: boolean
}) {
  return (
    <div style={INSPECTOR_BOX_STYLE}>
      <div className="flex items-start justify-between gap-3">
        <div style={{ minWidth: 0, flex: 1 }}>
          {kicker && <div className="eamos-kicker">{kicker}</div>}
          <div
            style={{
              marginTop: kicker ? 8 : 0,
              fontSize: 13.5,
              fontWeight: 700,
              color: 'var(--ink)',
              lineHeight: 1.25,
              height: 34,
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {title}
          </div>
        </div>
        {copyable && <CopyButton text={buildReadoutTsv(title, rows)} label={`Copy ${title}`} />}
      </div>
      <div
        className="mt-3"
        style={{
          display: 'grid',
          gridTemplateColumns: '58px repeat(4, minmax(0, 1fr))',
          columnGap: 12,
          rowGap: 6,
          alignItems: 'end',
        }}
      >
        <span />
        <StatHead>Allele frequency</StatHead>
        <StatHead>Allele count</StatHead>
        <StatHead>Allele number</StatHead>
        <StatHead>Homozygotes</StatHead>
        {rows.map((row) => (
          <Fragment key={row.label}>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--ink-2)' }}>
              {row.label}
            </span>
            <StatCell>{formatFrequency(row.cell.allele_frequency)}</StatCell>
            <StatCell>{formatInteger(row.cell.allele_count)}</StatCell>
            <StatCell>{formatInteger(row.cell.allele_number)}</StatCell>
            <StatCell>{formatInteger(row.cell.homozygote_count)}</StatCell>
          </Fragment>
        ))}
      </div>
      <div
        style={{
          marginTop: 8,
          height: 16,
          fontSize: 11,
          color: 'var(--ink-4)',
          lineHeight: 1.45,
          display: '-webkit-box',
          WebkitLineClamp: 1,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }}
      >
        {note}
      </div>
    </div>
  )
}

function StatHead({ children }: { children: string }) {
  return (
    <span
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-end',
        height: 24,
        overflow: 'hidden',
        fontSize: 9.5,
        color: 'var(--ink-4)',
        textAlign: 'right',
        lineHeight: 1.25,
      }}
    >
      {children}
    </span>
  )
}

function StatCell({ children }: { children: string }) {
  return (
    <span
      style={{
        fontFamily: 'var(--body)',
        fontVariantNumeric: 'tabular-nums',
        fontSize: 11,
        color: 'var(--ink-2)',
        textAlign: 'right',
      }}
    >
      {children}
    </span>
  )
}

function AncestryBar({
  group,
  chartMax,
  isHovered,
  isSelected,
  onHoverGroup,
  onSelectGroup,
}: {
  group: PopulationFrequencyVisualGroup
  chartMax: number
  isHovered: boolean
  isSelected: boolean
  onHoverGroup: (id: string | null) => void
  onSelectGroup: (id: string | null) => void
}) {
  const value = group.allele_frequency ?? 0
  const width = chartMax > 0 && value > 0 ? Math.max(2, (value / chartMax) * 100) : 0
  const barColor = bandFill(group.allele_frequency, group.data_state)
  const emphasized = isSelected || isHovered
  return (
    <button
      type="button"
      data-gnomad-row={group.id}
      aria-pressed={isSelected}
      className="pop-ancestry-bar"
      data-selected={isSelected ? 'true' : 'false'}
      title={`${group.label}; allele number ${formatInteger(group.allele_number)}; ${groupContext(group)}`}
      onMouseEnter={() => onHoverGroup(group.id)}
      onMouseLeave={() => onHoverGroup(null)}
      onFocus={() => onHoverGroup(group.id)}
      onBlur={() => onHoverGroup(null)}
      onClick={() => onSelectGroup(group.id)}
      style={{
        border: '0.5px solid',
        borderColor: emphasized ? '#fde047' : 'var(--line)',
        background: emphasized ? 'rgba(254, 249, 195, 0.72)' : 'var(--bg)',
        borderRadius: 'var(--r-sm)',
        padding: '7px 8px',
        textAlign: 'left',
        cursor: 'pointer',
        boxShadow: isSelected
          ? `0 0 0 2.5px rgba(253, 224, 71, 0.9), 0 6px 16px ${barColor}40`
          : isHovered
            ? `0 0 16px ${barColor}55`
            : 'none',
        transition:
          'border-color 140ms ease, background 140ms ease,' +
          'box-shadow 160ms var(--ease-standard), transform 180ms var(--ease-standard)',
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span
          style={{
            fontSize: 10.8,
            fontWeight: 700,
            color: emphasized ? 'var(--ink)' : 'var(--ink-2)',
            textShadow: isSelected ? `0 0 11px ${barColor}99` : 'none',
          }}
        >
          {compactLabel(group.label)}
        </span>
        <span
          style={{
            fontFamily: 'var(--body)',
            fontVariantNumeric: 'tabular-nums',
            fontSize: 10.4,
            color: 'var(--ink-3)',
          }}
        >
          {formatFrequency(group.allele_frequency)}
        </span>
      </div>
      <div
        className="mt-2"
        aria-hidden
        style={{
          height: 5,
          borderRadius: 999,
          background: 'var(--bg-soft2)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${width}%`,
            height: '100%',
            borderRadius: 999,
            background: barColor,
          }}
        />
      </div>
    </button>
  )
}
