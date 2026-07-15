'use client'

import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import type {
  PopulationFrequencyDatasetCell,
  PopulationFrequencyOverall,
  PopulationFrequencyReportSection,
  PopulationFrequencyOverallTotalCell,
  PopulationFrequencySexCell,
  PopulationFrequencyVisualGroup,
} from '@/lib/backend'
import {
  GNOMAD_ANCESTRY_MAP_VERSION,
  gnomadMapAnchor,
} from './gnomadAncestryMap'
import {
  GNOMAD_AF_BANDS,
  GNOMAD_MAP_HOVER,
  GNOMAD_MAP_SURFACE,
  type GnomadAfBand,
} from './gnomadMapTheme'
import {
  GNOMAD_MAP_LAND,
  GNOMAD_MAP_REGIONS,
  GNOMAD_MAP_VIEW_BOX,
} from './gnomadMapGeometry.generated'
import { CopyButton } from '@/components/ui/CopyButton'
import { InfoPopover } from '@/components/ui/InfoHint'
import { PopulationAgeDistribution } from './PopulationAgeDistribution'

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

function formatInteger(value: number | null | undefined): string {
  return value == null ? 'Not reported' : new Intl.NumberFormat('en-US').format(value)
}

function formatFrequency(value: number | null | undefined): string {
  if (value == null) return 'Not reported'
  if (value === 0) return '0%'
  const pct = value * 100
  if (pct < 0.001) return `${pct.toExponential(2)}%`
  if (pct < 0.1) return `${pct.toPrecision(2)}%`
  return `${pct.toFixed(2)}%`
}

function compactLabel(label: string): string {
  return label.replace(' genetic ancestry', '')
}

// Plain-language copy for the gnomAD section data-note keys, so the DATA NOTES strip
// reads as guidance rather than raw backend flags. `key:value` warnings match on the
// key prefix; anything unmapped falls back to a prettified version of the raw key.
const WARNING_COPY: Record<string, string> = {
  low_allele_number_cohorts:
    'Some ancestry groups have few sampled alleles (small sample size), so their frequencies are less precise.',
  allele_number_unavailable: 'Allele number (sample size) is not reported for one or more groups.',
  genetic_ancestry_groups_unavailable: 'Per-ancestry-group frequencies are unavailable for this variant.',
  age_distribution_unavailable: 'Age distribution is not available for this variant.',
  age_distribution_scope: 'Age distribution covers all gnomAD release samples, not only this variant’s carriers.',
  per_genetic_ancestry_age_distribution_not_available: 'Age distribution is not broken down by ancestry group.',
  allele_frequency_unavailable: 'Overall allele frequency is unavailable for this variant.',
  population_frequency_detail_unavailable: 'Detailed population frequency data is unavailable.',
  gnomad_source_status: 'gnomAD did not return a live frequency result for this lookup.',
  source_status: 'gnomAD source status is not live for this lookup.',
}

const UNAVAILABLE_REASON_COPY: Record<string, string> = {
  detail_unavailable: 'Detailed gnomAD population frequency data is unavailable.',
  frequency_metrics_unavailable: 'gnomAD returned the variant but did not provide usable frequency metrics.',
  variant_not_found: 'gnomAD has no record for this variant.',
  source_failure: 'gnomAD could not be reached for this lookup.',
  source_unavailable: 'gnomAD is unavailable for this lookup.',
}

function warningCopy(warning: string): string {
  const key = warning.split(':', 1)[0]
  return WARNING_COPY[warning] ?? WARNING_COPY[key] ?? warning.replace(/_/g, ' ').replace(/:/g, ': ')
}

function machineText(value: string | null | undefined): string | null {
  if (!value) return null
  return value.replace(/_/g, ' ').replace(/:/g, ': ').trim()
}

function unavailableReasonCopy(reason: string | null | undefined): string | null {
  if (!reason) return null
  return UNAVAILABLE_REASON_COPY[reason] ?? machineText(reason)
}

function sourceStatusNeedsDisclosure(status: string | null | undefined): boolean {
  if (!status) return false
  return !['live', 'local', 'cache', 'fixture'].includes(status.toLowerCase())
}

function uniqueWarnings(warnings: string[]): string[] {
  return Array.from(new Set(warnings.filter(Boolean)))
}

function groupContext(group: PopulationFrequencyVisualGroup): string {
  return gnomadMapAnchor(group.id).context
}

// Threshold-anchored absolute-AF color model (T5). Color comes from fixed
// cutoffs (GNOMAD_AF_BANDS) — the same yardstick for every variant — not relative
// scaling against popmax/visual_scale.max. Bands are consulted ONLY for an
// observed AF > 0; not observed (or explicit zero_observed) → neutral noData grey,
// never red.
function bandForAf(
  value: number | null | undefined,
  dataState?: string,
): GnomadAfBand | null {
  if (dataState === 'zero_observed' || value == null || value <= 0) return null
  return GNOMAD_AF_BANDS.find((band) => value >= band.min) ?? null
}

function bandFill(value: number | null | undefined, dataState?: string): string {
  return bandForAf(value, dataState)?.color ?? GNOMAD_MAP_SURFACE.noData
}

// Geographic groups that own a dissolved map region; every other group (ASJ, AMI,
// Remaining) is a non-geographic cohort shown as an off-map chip (T8).
const GEOGRAPHIC_GROUP_IDS = new Set<string>(GNOMAD_MAP_REGIONS.map((region) => region.group))

// Ancestral-origin copy for an off-map cohort chip: the cohort description from the
// anchor layer, minus the now-obsolete "oriented over <place>" map-orientation clause.
function offMapOriginCopy(groupId: string): string {
  return (
    OFFMAP_SHORT_DESC[groupId] ??
    gnomadMapAnchor(groupId)
      .context.split(/,?\s*oriented/i)[0]
      .replace(/^gnomAD\s+\w+:\s*/i, '')
      .replace(/[;,]\s*$/, '')
      .trim()
  )
}

// Concise chip descriptions (override the longer anchor copy for verbose cohorts).
const OFFMAP_SHORT_DESC: Record<string, string> = {
  remaining: 'Individuals not assigned gnomAD labels',
}

// Uniform footer-chip box so the Total/XX/XY and non-geographic cohort chips read
// as one aligned set: identical width + min height, descriptions clamped to 2 lines.
const FOOTER_CHIP_WIDTH = 140
const FOOTER_CHIP_MIN_HEIGHT = 46
const FOOTER_CHIP_DESC_STYLE = {
  marginTop: 2,
  fontSize: 9.2,
  color: 'var(--ink-4)',
  lineHeight: 1.3,
  display: '-webkit-box',
  WebkitLineClamp: 2,
  WebkitBoxOrient: 'vertical' as const,
  overflow: 'hidden',
}

// ── Exome / Genome "Include" dataset filter ──────────────────────────────────
// gnomAD lets you recompute every group's AC/AN/AF/homozygotes for exomes only,
// genomes only, or both combined ("joint"). Backed by the shared contract
// (`@/lib/backend`): a group and the cohort total each carry the flat joint fields
// plus optional `exome` / `genome` dataset cells. The FE derives the displayed cell
// from the checkbox state — both → joint, one → that dataset.
const EMPTY_DATASET_CELL: PopulationFrequencyDatasetCell = {
  allele_frequency: null,
  allele_count: null,
  allele_number: null,
  homozygote_count: null,
}

// `base` is a group or the cohort total; both share the flat-joint + optional
// exome/genome shape of PopulationFrequencyOverallTotalCell (a group is structurally
// assignable to it).
function selectDatasetCell(
  base: PopulationFrequencyOverallTotalCell,
  includeExome: boolean,
  includeGenome: boolean,
): PopulationFrequencyDatasetCell {
  if (includeExome && includeGenome) {
    return {
      allele_frequency: base.allele_frequency,
      allele_count: base.allele_count,
      allele_number: base.allele_number,
      homozygote_count: base.homozygote_count,
    }
  }
  if (includeExome) return base.exome ?? EMPTY_DATASET_CELL
  if (includeGenome) return base.genome ?? EMPTY_DATASET_CELL
  return EMPTY_DATASET_CELL
}

function applyDatasetToGroup(
  group: PopulationFrequencyVisualGroup,
  includeExome: boolean,
  includeGenome: boolean,
): PopulationFrequencyVisualGroup {
  const cell = selectDatasetCell(group, includeExome, includeGenome)
  const observed = cell.allele_frequency != null && cell.allele_frequency > 0
  return {
    ...group,
    allele_frequency: cell.allele_frequency,
    allele_count: cell.allele_count,
    allele_number: cell.allele_number,
    homozygote_count: cell.homozygote_count,
    // Recompute observed/zero so the map colours the selected dataset honestly (a
    // group seen jointly but absent from one dataset reads grey "not observed").
    data_state: observed ? 'observed' : 'zero_observed',
  }
}

function applyDatasetToOverall(
  overall: PopulationFrequencyOverall | null | undefined,
  includeExome: boolean,
  includeGenome: boolean,
): PopulationFrequencyOverall | null {
  if (!overall) return null
  const total = overall.total
    ? { ...overall.total, ...selectDatasetCell(overall.total, includeExome, includeGenome) }
    : overall.total
  // XX / XY stay joint: the contract carries no per-dataset sex split (a follow-up).
  // Total recomputes, which is the headline gnomAD behaviour.
  return { ...overall, total }
}

// Tab-separated group table (paste-ready for a spreadsheet). Reflects the current
// Exome/Genome dataset selection, and exports raw allele frequencies (not the rounded
// on-screen %) so the numbers stay analysable.
function buildAncestryFrequencyTsv(
  groups: PopulationFrequencyVisualGroup[],
  overall: PopulationFrequencyOverall | null,
): string {
  const num = (value: number | null | undefined) => (value == null ? '' : String(value))
  const row = (label: string, cell: PopulationFrequencySexCell) =>
    [label, num(cell.allele_frequency), num(cell.allele_count), num(cell.allele_number), num(cell.homozygote_count)].join('\t')
  const header = ['Genetic ancestry group', 'Allele frequency', 'Allele count', 'Allele number', 'Homozygotes'].join('\t')
  const groupRows = groups.map((group) => row(compactLabel(group.label), group))
  const overallRows: string[] = []
  if (overall?.total) overallRows.push(row('Total', overall.total))
  if (overall?.xx) overallRows.push(row('XX', overall.xx))
  if (overall?.xy) overallRows.push(row('XY', overall.xy))
  return [header, ...groupRows, ...overallRows].join('\n')
}

export function PopulationFrequencySection({ section, unavailable = null }: PopulationFrequencySectionProps) {
  const [activeTab, setActiveTab] = useState<PopulationTab>('map')
  const warnings = section?.warnings ?? []
  const groups = useMemo(
    () => [...(section?.visual_groups ?? [])].sort((a, b) => (a.sort_order ?? 99) - (b.sort_order ?? 99)),
    [section?.visual_groups],
  )
  // Hover and selection are SEPARATE. Hovering a bar or region only highlights it
  // (transient, cleared on mouse-leave/blur). Clicking PINS the selection that drives
  // the selected-group inspector and the map standout. The inspector's contents change
  // only when a different group is clicked; hovering never disturbs it.
  const [hoverGroupId, setHoverGroupId] = useState<string | null>(null)
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null)
  // Click toggles the pin: clicking the already-selected group clears it (route back to
  // the prompt); clicking a different group replaces the selection.
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
    disclosureWarnings.some((warning) => /unavailable|failed|failure|missing|gnomad_source_status/.test(warning))

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
        <div>{/* tab content begins */}
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

function PopulationUnavailableStatePanel({ state }: { state: PopulationFrequencyUnavailableState }) {
  const warnings = uniqueWarnings(state.warnings ?? [])
  const reason = unavailableReasonCopy(state.unavailableReason)
  const status = machineText(state.sourceStatus) ?? 'missing'
  const meta = [
    state.variantId,
    state.dataset,
    state.genomeBuild,
    state.sequencingType,
  ].filter(Boolean).join(' | ')
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
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink)' }}>
            Frequency data unavailable
          </div>
          {meta && (
            <div style={{ marginTop: 2, fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-3)', overflowWrap: 'anywhere' }}>
              {meta}
            </div>
          )}
        </div>
        <span style={statusChipStyle}>{status}</span>
      </div>
      <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.5, color: 'var(--ink-3)' }}>
        {reason ?? 'The backend did not return source-backed gnomAD frequency metrics for this variant.'}
      </p>
      {warnings.length > 0 && (
        <ul style={{ margin: 0, paddingLeft: 17, display: 'grid', gap: 4, fontSize: 11.5, lineHeight: 1.45, color: 'var(--ink-3)' }}>
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
  const statusText = reason ?? (warnings.map(warningCopy).slice(0, 2).join(' | ') || 'No live frequency result was returned.')
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
        <strong style={{ color: 'var(--ink)', fontWeight: 700 }}>gnomAD source state:</strong>{' '}
        {statusText}
      </span>
      {status && <span style={statusChipStyle}>{status}</span>}
    </div>
  )
}

// Data notes as an "ⓘ" popover (same affordance as the map's "How to read this"),
// rather than an inline expandable. Lives in the Ancestry tab's right-rail footer.
function DataNotesPopover({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null
  return (
    <InfoPopover label="gnomAD section data notes" triggerText={`Data notes (${warnings.length})`}>
      <div style={{ fontWeight: 700, color: 'var(--ink)', fontSize: 11.5, marginBottom: 6 }}>Data notes</div>
      <ul style={{ margin: 0, paddingLeft: 16, display: 'flex', flexDirection: 'column', gap: 5 }}>
        {warnings.slice(0, 6).map((warning) => (
          <li key={warning} style={{ lineHeight: 1.45 }}>{warningCopy(warning)}</li>
        ))}
      </ul>
    </InfoPopover>
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

function MapOverviewTab({
  groups,
  hoveredId,
  selectedId,
  onHoverGroup,
  onSelectGroup,
}: {
  groups: PopulationFrequencyVisualGroup[]
  hoveredId: string | null
  selectedId: string | null
  onHoverGroup: (id: string | null) => void
  onSelectGroup: (id: string | null) => void
}) {
  if (groups.length === 0) {
    return <UnavailablePanel title="Genetic ancestry group frequencies unavailable" />
  }

  return (
    <div
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 8,
        background: 'var(--bg-soft)',
        overflow: 'hidden',
      }}
    >
      <WorldFrequencyMap
        groups={groups}
        hoveredId={hoveredId}
        selectedId={selectedId}
        layout="full"
        onHoverGroup={onHoverGroup}
        onSelectGroup={onSelectGroup}
      />
    </div>
  )
}

function AncestryFrequencyTab({
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
  // gnomAD "Include: Exomes / Genomes" filter: recomputes every group's AF/AC/AN/hom
  // for the selected dataset(s). At least one stays on. Hooks run before the early
  // return below so the rules of hooks hold when there are no groups.
  const [includeExome, setIncludeExome] = useState(true)
  const [includeGenome, setIncludeGenome] = useState(true)
  const displayGroups = useMemo(
    () => groups.map((group) => applyDatasetToGroup(group, includeExome, includeGenome)),
    [groups, includeExome, includeGenome],
  )

  if (groups.length === 0) {
    return <UnavailablePanel title="Genetic ancestry group frequencies unavailable" />
  }

  // Toggling never leaves both unchecked (gnomAD shows at least one dataset).
  const toggleExome = () => setIncludeExome((value) => (value && !includeGenome ? value : !value))
  const toggleGenome = () => setIncludeGenome((value) => (value && !includeExome ? value : !value))
  // The inspector is driven by the CLICKED group only; the map/bars highlight hover
  // and selection separately. Both read the dataset-derived list, not raw groups.
  const selectedDisplayGroup = selectedId ? displayGroups.find((group) => group.id === selectedId) ?? null : null
  const displayOverall = applyDatasetToOverall(overall, includeExome, includeGenome)

  // Every group is a horizontal bar in one list; the no-region cohorts
  // (ASJ/AMI/Remaining) are grouped at the bottom inside their own outlined box
  // rather than split out into a separate chip section.
  const geographicGroups = displayGroups.filter((group) => GEOGRAPHIC_GROUP_IDS.has(group.id))
  const offMapGroups = displayGroups.filter((group) => !GEOGRAPHIC_GROUP_IDS.has(group.id))
  // Bar LENGTH is a relative comparison across all groups, scaled to a local max
  // (not the backend visual_scale.max). Bar COLOR is absolute (bandFill).
  const chartMax = Math.max(0, ...displayGroups.map((group) => group.allele_frequency ?? 0))

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        // Stretch so the two columns are the same height: the taller column (usually the
        // left, with the responsive map) sets the height and the right rail grows to it,
        // its pinned footer dropping to the bottom so the two feet line up exactly. When
        // the layout wraps to a single column (mobile), each row has one item so stretch
        // is a no-op.
        alignItems: 'stretch',
        gap: 16,
      }}
    >
      {/* Left column: map on top, compact selected-group inspector below it,
          occupying the space that was empty under the map. */}
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
          /* Selected bars scale up via a transition (not a one-shot keyframe) so
             selecting AND de-selecting animate symmetrically — de-select is the exact
             reverse. Ease-out, no bounce. */
          .pop-ancestry-bar[data-selected="true"] { transform: scale(1.015); }
          .pop-ancestry-bar[data-selected="false"]:active { transform: translateY(0.5px); transition-duration: 80ms; }
          .pop-ancestry-bar:focus-visible { outline: none; box-shadow: 0 0 0 3px rgba(29, 158, 117, 0.18); }
          @media (prefers-reduced-motion: reduce) { .pop-ancestry-bar { transition: none !important; } }
        `}</style>
        <div className="flex items-start justify-between gap-3">
          <div className="eamos-kicker">Allele frequency by gnomAD group</div>
          <CopyButton text={buildAncestryFrequencyTsv(displayGroups, displayOverall)} label="Copy allele frequency table" />
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
            <div style={{ marginTop: 3, fontSize: 10, color: 'var(--ink-4)', lineHeight: 1.4 }}>
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
        {/* Footer pinned to the bottom of the rail: data notes fill the dead space
            under the bars, keeping the Ancestry layout square and aligned. */}
        <div style={{ marginTop: 'auto', paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
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

// gnomAD-style "Include: Exomes / Genomes" dataset filter. Two checkbox chips that
// recompute every group's frequency for the chosen dataset(s); at least one stays on.
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

// Bottom-left readout. Three states:
//  • a group is hovered/selected → that group's Overall + XX/XY (gnomAD per-group
//    expansion);
//  • nothing active → the whole-cohort Total + XX/XY (gnomAD's bottom Total rows);
//  • neither available → a prompt.
// XX/XY rows render only once the backend surfaces the sex cells (Codex contract);
// per-group Overall and (when present) the cohort total work from existing data.
// Min-height equals the tallest populated readout (measured ~209px: fixed two-line
// title slot + fixed two-line header row + Overall/XX/XY rows + fixed two-line note,
// identical for every group) so the resting prompt and any hovered group render at
// exactly the same height — hovering in/out never resizes the box or shoves the readout
// below it (no jitter), at any viewport width: long names that wrap and column headers
// that wrap as the columns narrow are both absorbed by their fixed-height slots.
const INSPECTOR_BOX_STYLE = {
  // Equals the populated readout height (~191px) so the box does not change height
  // between the resting prompt and a selected group — clicking to select or de-select
  // never jumps the layout. The right rail stretches (alignItems: stretch) to keep the
  // two column feet aligned despite this height.
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
      <div style={{ ...INSPECTOR_BOX_STYLE, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: 11.5, color: 'var(--ink-4)', textAlign: 'center', lineHeight: 1.45 }}>
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

// Always-on whole-cohort readout, shown beneath the inspector on the Ancestry tab so
// the variant's Total / XX / XY stay visible regardless of what (if anything) is hovered.
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

// One-readout TSV (title line + header + rows) for the per-box copy buttons.
function buildReadoutTsv(title: string, rows: Array<{ label: string; cell: PopulationFrequencySexCell }>): string {
  const num = (value: number | null | undefined) => (value == null ? '' : String(value))
  const lines = [title, ['', 'Allele frequency', 'Allele count', 'Allele number', 'Homozygotes'].join('\t')]
  rows.forEach((row) =>
    lines.push([row.label, num(row.cell.allele_frequency), num(row.cell.allele_count), num(row.cell.allele_number), num(row.cell.homozygote_count)].join('\t')),
  )
  return lines.join('\n')
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
              // Fixed two-line slot: a long name that wraps must not change the box
              // height. The box only changes contents on a deliberate click now.
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
          // Fixed label column (not auto): the inspector and the cohort readout share
          // one column geometry so their stat columns line up vertically even though
          // their row labels differ ("Overall" vs "Total").
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
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--ink-2)' }}>{row.label}</span>
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
          // Single fixed line: keeps both boxes short (so the left column foot lines up
          // with the right rail) and a constant height (the box only changes on click).
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

// Fixed two-line, bottom-aligned slot: these headers wrap from one to two lines as the
// columns narrow, which would change the readout height and reintroduce hover jitter.
// Reserving two lines keeps the header row a constant height at every viewport width.
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
    <span style={{ fontFamily: 'var(--body)', fontVariantNumeric: 'tabular-nums', fontSize: 11, color: 'var(--ink-2)', textAlign: 'right' }}>
      {children}
    </span>
  )
}

// One frequency row: label + AF readout + a bar whose LENGTH is relative (scaled to
// chartMax) and whose COLOR is the absolute AF band. Shared by the geographic list
// and the non-geographic outlined box so both stay visually identical.
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
  // Hover = subtle highlight (just a hint); selection = strong pinned state that drives
  // the inspector. The press (:active, in the shared style block) is the click feel.
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
        // Hover and selection both use the yellow highlight (the lively look retained).
        // Selection is told apart by MORE: a crisp ring + a scale-up + the inspector
        // populating, while hover is just the tint + a soft band-colour glow.
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
        <span style={{ fontFamily: 'var(--body)', fontVariantNumeric: 'tabular-nums', fontSize: 10.4, color: 'var(--ink-3)' }}>
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

function WorldFrequencyMap({
  groups,
  hoveredId,
  selectedId,
  layout = 'side',
  showOffMap = true,
  onHoverGroup,
  onSelectGroup,
}: {
  groups: PopulationFrequencyVisualGroup[]
  hoveredId: string | null
  selectedId: string | null
  layout?: 'full' | 'side'
  showOffMap?: boolean
  onHoverGroup: (id: string | null) => void
  onSelectGroup: (id: string | null) => void
}) {
  const isFull = layout === 'full'
  const { width, height } = GNOMAD_MAP_VIEW_BOX
  const byGroup = new Map(groups.map((group) => [group.id, group]))
  const offMapGroups = groups.filter((group) => !GEOGRAPHIC_GROUP_IDS.has(group.id))
  // Dim the rest of the map only when the SELECTED group is itself a region (so there
  // is something to stand out). Selecting an off-map cohort leaves the map undimmed.
  const selectedOnMap = selectedId != null && GNOMAD_MAP_REGIONS.some((region) => region.group === selectedId)
  // World-map tab only (no inspector there): a small popover anchored near the selected
  // region showing its joint allele frequency (default exome+genome, no XX/XY split).
  const popoverRegion = isFull && selectedId ? GNOMAD_MAP_REGIONS.find((region) => region.group === selectedId) ?? null : null
  const popoverGroup = popoverRegion ? byGroup.get(popoverRegion.group) ?? null : null
  const labelSize = isFull ? 22 : 18
  const rootRef = useRef<HTMLDivElement>(null)
  // World-map tab: clicking outside the map (page background, chrome) clears the
  // selection, like clicking empty ocean does. Scoped to the full layout so it never
  // fights the Ancestry tab's bar/inspector selection. Off-map cohort chips and the
  // legend live inside rootRef, so clicking those is not treated as a click-away.
  useEffect(() => {
    if (!isFull || selectedId == null) return
    const handlePointerDown = (event: PointerEvent) => {
      const root = rootRef.current
      if (root && event.target instanceof Node && !root.contains(event.target)) {
        onSelectGroup(null)
      }
    }
    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [isFull, selectedId, onSelectGroup])

  return (
    <div ref={rootRef} style={{ position: 'relative' }}>
      <style>{`
        .gnomad-region { transition: fill 160ms var(--ease-standard), fill-opacity 160ms var(--ease-standard); }
        .gnomad-region-g { transition: opacity 160ms var(--ease-standard); }
        /* No default focus box around the region — focusing it triggers the yellow halo
           (onFocus -> hover), which is the visible focus indicator for keyboard users. */
        .gnomad-region-g:focus { outline: none; }
        .gnomad-halo { transition: stroke-opacity 200ms var(--ease-standard); }
        @keyframes gnomadPopIn { from { opacity: 0; } to { opacity: 1; } }
        .gnomad-map-pop { animation: gnomadPopIn 160ms var(--ease-standard); }
        @media (prefers-reduced-motion: reduce) { .gnomad-region, .gnomad-region-g, .gnomad-halo { transition: none; } .gnomad-map-pop { animation: none; } }
      `}</style>
      <div style={{ position: 'relative' }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="World map of gnomAD genetic ancestry group allele frequencies"
        style={{ width: '100%', aspectRatio: `${width} / ${height}`, display: 'block' }}
      >
        <rect x="0" y="0" width={width} height={height} fill={GNOMAD_MAP_SURFACE.ocean} onClick={() => onSelectGroup(null)} />
        {/* Neutral base land — untracked countries show through here (D5 tier 2).
            Clicking it (empty / untracked space) clears the selection, like the ocean. */}
        <path d={GNOMAD_MAP_LAND} fill={GNOMAD_MAP_SURFACE.baseLand} stroke="none" onClick={() => onSelectGroup(null)} />
        {GNOMAD_MAP_REGIONS.map((region) => {
          const group = byGroup.get(region.group)
          const interactive = Boolean(group)
          const isSelected = selectedId === region.group
          const isHovered = hoveredId === region.group
          const emphasized = isSelected || isHovered
          // When a region is selected, the others fade back so it stands out. A hovered
          // region is never dimmed (the hover stays full-strength on top of the fade).
          const dimmed = selectedOnMap && !isSelected && !isHovered
          // A tracked region with no backend group, or no observed AF, reads neutral
          // grey (D5 tier 3 — "we cover this cohort, no signal"), never a low band.
          const fill = group
            ? bandFill(group.allele_frequency, group.data_state)
            : GNOMAD_MAP_SURFACE.noData
          const code = region.group.toUpperCase()
          return (
            <g
              key={region.group}
              className="gnomad-region-g"
              tabIndex={interactive ? 0 : undefined}
              role={interactive ? 'button' : undefined}
              data-gnomad-region={region.group}
              aria-label={
                group
                  ? `${group.label}: ${formatFrequency(group.allele_frequency)}, allele number ${formatInteger(group.allele_number)}. ${groupContext(group)}`
                  : `${code}: not reported in this cohort`
              }
              onMouseEnter={interactive ? () => onHoverGroup(region.group) : undefined}
              onMouseLeave={interactive ? () => onHoverGroup(null) : undefined}
              onFocus={interactive ? () => onHoverGroup(region.group) : undefined}
              onBlur={interactive ? () => onHoverGroup(null) : undefined}
              onClick={interactive ? () => onSelectGroup(region.group) : undefined}
              style={{ cursor: interactive ? 'pointer' : 'default', opacity: dimmed ? 0.45 : 1 }}
            >
              <path
                className="gnomad-region"
                d={region.d}
                data-active={emphasized ? 'true' : 'false'}
                fill={fill}
                fillOpacity={emphasized ? 1 : 0.92}
                stroke={GNOMAD_MAP_SURFACE.regionStroke}
                strokeWidth={0.6}
                strokeLinejoin="round"
              />
              <text
                x={region.labelX}
                y={region.labelY}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={labelSize}
                fontFamily="var(--mono)"
                fontWeight={emphasized ? 700 : 600}
                fill={GNOMAD_MAP_SURFACE.label}
                paintOrder="stroke"
                stroke={GNOMAD_MAP_SURFACE.regionStroke}
                strokeWidth={3}
                strokeLinejoin="round"
                style={{ pointerEvents: 'none' }}
              >
                {code}
              </text>
            </g>
          )
        })}
        {/* The double-stroke yellow halo (dark outer + bright inner) on hover AND
            selection — the lively highlight retained. Drawn in a separate non-interactive
            layer ABOVE every region fill so the emphasized halo is never covered by a
            neighbour, and so the interactive fills can stay in STABLE order. Reordering the
            fills on hover/select is what made selecting a new region take two clicks
            (the moved DOM node dropped the click); only the array's last region was
            unaffected. Halos fade via stroke-opacity so hover and select/de-select animate
            symmetrically; selection is told apart by the dim of the rest of the map. */}
        <g style={{ pointerEvents: 'none' }}>
          {GNOMAD_MAP_REGIONS.map((region) => {
            const emphasized = region.group === selectedId || region.group === hoveredId
            return (
              <g key={`halo-${region.group}`}>
                <path className="gnomad-halo" d={region.d} fill="none" stroke={GNOMAD_MAP_HOVER.haloDark} strokeWidth={6} strokeLinejoin="round" style={{ strokeOpacity: emphasized ? 1 : 0 }} />
                <path className="gnomad-halo" d={region.d} fill="none" stroke={GNOMAD_MAP_HOVER.haloLight} strokeWidth={2.75} strokeLinejoin="round" style={{ strokeOpacity: emphasized ? 1 : 0 }} />
              </g>
            )
          })}
        </g>
      </svg>
        {popoverRegion && popoverGroup && (
          <MapSelectionPopover region={popoverRegion} group={popoverGroup} viewWidth={width} viewHeight={height} />
        )}
      </div>

      <MapLegendFooter />

      {showOffMap && offMapGroups.length > 0 && (
        <OffMapCohorts
          groups={offMapGroups}
          hoveredId={hoveredId}
          selectedId={selectedId}
          onHoverGroup={onHoverGroup}
          onSelectGroup={onSelectGroup}
        />
      )}
    </div>
  )
}

// Per-region anchor in OCEAN / empty space (viewBox coords) so the popover lands clear
// of the selected region and its neighbours rather than on top of land. Centred on the
// anchor. Falls back to the region label if a group has no anchor.
const POPOVER_ANCHORS: Record<string, { x: number; y: number }> = {
  afr: { x: 1300, y: 615 }, // Indian Ocean, SE of Africa
  amr: { x: 300, y: 560 }, // SE Pacific, west of South America
  eas: { x: 1600, y: 505 }, // W Pacific, SE of East Asia
  fin: { x: 775, y: 180 }, // North Atlantic / Norwegian Sea, west of Scandinavia
  mid: { x: 1235, y: 495 }, // Arabian Sea, south of the Middle East
  nfe: { x: 800, y: 255 }, // North Atlantic, west of Europe
  sas: { x: 1390, y: 565 }, // Indian Ocean / Bay of Bengal, south of South Asia
}

// World-map-tab popover: floats in nearby ocean/empty space (not over the region) and
// names the group in full with its joint allele frequency (default exome+genome; no
// XX/XY split). Centred on a hand-picked ocean anchor, in % of the SVG box.
function MapSelectionPopover({
  region,
  group,
  viewWidth,
  viewHeight,
}: {
  region: (typeof GNOMAD_MAP_REGIONS)[number]
  group: PopulationFrequencyVisualGroup
  viewWidth: number
  viewHeight: number
}) {
  const anchor = POPOVER_ANCHORS[region.group] ?? { x: region.labelX, y: region.labelY }
  const leftPct = (anchor.x / viewWidth) * 100
  const topPct = (anchor.y / viewHeight) * 100
  const dot = bandFill(group.allele_frequency, group.data_state)
  return (
    <div
      className="gnomad-map-pop"
      role="status"
      style={{
        position: 'absolute',
        left: `${leftPct}%`,
        top: `${topPct}%`,
        transform: 'translate(-50%, -50%)',
        width: 190,
        maxWidth: '70%',
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 9,
        boxShadow: '0 8px 22px rgba(0,0,0,0.18)',
        padding: '8px 11px',
        pointerEvents: 'none',
        zIndex: 5,
      }}
    >
      <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--ink)', lineHeight: 1.25 }}>
        {compactLabel(group.label)}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 7, marginTop: 4 }}>
        <span
          aria-hidden
          style={{ width: 9, height: 9, borderRadius: 3, background: dot, border: '0.5px solid rgba(0,0,0,0.12)', flex: '0 0 auto', transform: 'translateY(1px)' }}
        />
        <span style={{ fontFamily: 'var(--body)', fontVariantNumeric: 'tabular-nums', fontSize: 16, fontWeight: 700, color: 'var(--ink)' }}>
          {formatFrequency(group.allele_frequency)}
        </span>
        <span style={{ fontSize: 9.5, color: 'var(--ink-4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          allele freq
        </span>
      </div>
    </div>
  )
}

// Off-map diaspora / founder cohorts (D6): ASJ, AMI, Remaining — genetic-similarity
// groups with no honest geography, so they are never placed on the map. Cross-linked
// with the ancestry list via the shared active group.
function hasOverall(overall?: PopulationFrequencyOverall | null): boolean {
  return Boolean(overall && (overall.total || overall.xx || overall.xy))
}

function OffMapCohorts({
  groups,
  hoveredId,
  selectedId,
  onHoverGroup,
  onSelectGroup,
}: {
  groups: PopulationFrequencyVisualGroup[]
  hoveredId: string | null
  selectedId: string | null
  onHoverGroup: (id: string | null) => void
  onSelectGroup: (id: string | null) => void
}) {
  return (
    <div style={{ borderTop: '0.5px solid var(--line)', background: 'var(--bg-soft)', padding: '10px 12px' }}>
      <div>
        {groups.length > 0 && (
          <div style={{ minWidth: 0 }}>
            <div className="eamos-kicker">Non-geographic cohorts</div>
            <div style={{ marginTop: 3, fontSize: 10.5, color: 'var(--ink-4)', lineHeight: 1.4 }}>
              Defined by genetic similarity rather than geography, so they are shown off the map.
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {groups.map((group) => {
                const isSelected = selectedId === group.id
                const isHovered = hoveredId === group.id
                const emphasized = isSelected || isHovered
                const dot = bandFill(group.allele_frequency, group.data_state)
                return (
                  <button
                    key={group.id}
                    type="button"
                    data-gnomad-offmap={group.id}
                    aria-pressed={isSelected}
                    title={`${group.label}; ${groupContext(group)}`}
                    onMouseEnter={() => onHoverGroup(group.id)}
                    onMouseLeave={() => onHoverGroup(null)}
                    onFocus={() => onHoverGroup(group.id)}
                    onBlur={() => onHoverGroup(null)}
                    onClick={() => onSelectGroup(group.id)}
                    style={{
                      border: '0.5px solid',
                      // Hover = yellow tint (lively, retained); selected = tint + a crisp
                      // ring so the pinned chip reads as more than a hover.
                      borderColor: emphasized ? '#fde047' : 'var(--line)',
                      background: emphasized ? 'rgba(254, 249, 195, 0.72)' : 'var(--bg)',
                      boxShadow: isSelected ? '0 0 0 2px rgba(253, 224, 71, 0.9)' : 'none',
                      borderRadius: 'var(--r-sm)',
                      padding: '4px 8px',
                      textAlign: 'left',
                      cursor: 'pointer',
                      width: FOOTER_CHIP_WIDTH,
                      minHeight: FOOTER_CHIP_MIN_HEIGHT,
                      boxSizing: 'border-box',
                      transition: 'border-color 140ms ease, background 140ms ease, box-shadow 160ms var(--ease-standard)',
                    }}
                  >
                    <div style={{ display: 'flex', gap: 6, alignItems: 'flex-start' }}>
                      <span
                        aria-hidden
                        style={{ width: 8, height: 8, borderRadius: 3, background: dot, border: '0.5px solid rgba(0,0,0,0.12)', flex: '0 0 auto', marginTop: 3 }}
                      />
                      <div style={{ minWidth: 0 }}>
                        <div className="flex items-baseline gap-1.5">
                          <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, fontWeight: 700, color: 'var(--ink-2)' }}>
                            {group.id.toUpperCase()}
                          </span>
                          <span style={{ fontFamily: 'var(--body)', fontVariantNumeric: 'tabular-nums', fontSize: 9.6, color: 'var(--ink-3)' }}>
                            {formatFrequency(group.allele_frequency)}
                          </span>
                        </div>
                        <div style={FOOTER_CHIP_DESC_STYLE}>
                          {offMapOriginCopy(group.id)}
                        </div>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Banded legend + framing copy (T9). Discrete absolute-AF bands (with the ACMG
// anchors) plus the neutral not-observed grey; the genetic-similarity framing is
// preserved and the basemap attribution is Natural Earth (public domain).
function MapLegendFooter() {
  return (
    <div style={{ borderTop: '0.5px solid var(--line)', background: 'var(--bg)', padding: '9px 12px', fontSize: 11, color: 'var(--ink-3)' }}>
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1" aria-label="Allele frequency bands">
          {GNOMAD_AF_BANDS.map((band) => (
            <LegendSwatch
              key={band.id}
              color={band.color}
              label={band.label}
              tag={band.acmg ?? (band.id === 'uncommon' ? 'Intermediate' : null)}
            />
          ))}
          <LegendSwatch color={GNOMAD_MAP_SURFACE.noData} label="Not observed" tag={null} />
        </div>
        <InfoPopover label="How to read this map">
          <div style={{ fontWeight: 700, color: 'var(--ink)', fontSize: 11.5, marginBottom: 6 }}>Reading the colours</div>
          <div>
            Colour is the variant’s <strong>absolute allele frequency</strong> in each gnomAD group, against
            fixed ACMG-style cutoffs:
          </div>
          <ul style={{ margin: '6px 0 10px', paddingLeft: 16, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <li><strong>BA1 / BS1</strong> (green) — common; supports a benign call.</li>
            <li><strong>Intermediate</strong> (amber) — frequency gives no evidence either way.</li>
            <li><strong>PM2</strong> (red) — very rare or absent; supports a pathogenic call.</li>
            <li><strong>Not observed</strong> (grey) — cohort is covered, variant not seen.</li>
          </ul>
          <div style={{ fontWeight: 700, color: 'var(--ink)', fontSize: 11.5, marginBottom: 6 }}>Method &amp; sources</div>
          <div>
            Basemap from Natural Earth (public domain); regions are dissolved from member countries and
            land-clipped. gnomAD groups describe genetic-similarity cohorts — not race, ethnicity, patient
            ancestry, or exact geography. Algorithm {GNOMAD_ANCESTRY_MAP_VERSION}.
          </div>
        </InfoPopover>
      </div>
    </div>
  )
}

// Plain-language meaning of each band tag, surfaced on hover (tooltip) and in the
// info popover so the benign (BA1/BS1), intermediate, and pathogenic (PM2) ends all
// read clearly. The amber middle band is "Intermediate" — frequency-uninformative —
// not literally a VUS (VUS is the overall classification, not a frequency criterion).
const BAND_TAG_MEANING: Record<string, string> = {
  BA1: 'ACMG BA1 — stand-alone benign evidence (allele frequency ≥ 5%)',
  BS1: 'ACMG BS1 — strong benign evidence (more common than the disorder)',
  PM2: 'ACMG PM2 — supporting pathogenic evidence (absent or extremely rare)',
  Intermediate:
    'Intermediate — too rare to call benign (below BS1), too common for PM2; allele frequency gives no ACMG evidence either way.',
}

function LegendSwatch({ color, label, tag }: { color: string; label: string; tag: string | null }) {
  return (
    <span className="inline-flex items-center gap-1.5" style={{ fontSize: 10.5 }}>
      <span
        aria-hidden
        style={{ width: 12, height: 12, borderRadius: 3, background: color, border: '0.5px solid rgba(0,0,0,0.12)', flex: '0 0 auto' }}
      />
      <span style={{ color: 'var(--ink-2)' }}>{label}</span>
      {tag && (
        <span
          title={BAND_TAG_MEANING[tag] ?? tag}
          style={{ fontFamily: 'var(--mono)', fontSize: 9, fontWeight: 700, color: 'var(--ink-4)', border: '0.5px solid var(--line)', borderRadius: 4, padding: '0 3px', cursor: 'help' }}
        >
          {tag}
        </span>
      )}
    </span>
  )
}

function UnavailablePanel({ title, compact = false }: { title: string; compact?: boolean }) {
  return (
    <div
      style={{
        minHeight: compact ? 118 : 180,
        border: '0.5px dashed var(--line-2)',
        borderRadius: 8,
        background: 'var(--bg-soft)',
        color: 'var(--ink-4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: 14,
        fontSize: 12,
      }}
    >
      {title}
    </div>
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
