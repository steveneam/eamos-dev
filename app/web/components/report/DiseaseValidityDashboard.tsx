'use client'

import { useMemo, useState, type CSSProperties } from 'react'
import { CuratedVariantsGrid } from '@/components/report/CuratedVariantsGrid'
import type {
  AssociatedCondition,
  CuratedVariantsDistribution,
  EvidenceSourceSummary,
  ReportExtractionSectionTarget,
  ReportPayload,
  SourceProvenance,
} from '@/lib/backend'

interface DiseaseValidityDashboardProps {
  payload: ReportPayload
  evidence: EvidenceSourceSummary[]
  sectionTarget?: ReportExtractionSectionTarget | null
}

interface DiseaseCondition {
  name: string
  diseaseIds: string[]
  inheritance: string | null
  validity: string | null
  mechanism: string | null
  sourceUrls: string[]
  caseCount: number | null
  sourceList: string | null
  sourceKind: 'gene_disease' | 'legacy_report'
}

interface SourceRow {
  label: string
  status: string
  version?: string | null
  href?: string | null
  policy: 'FREE' | 'PRO' | 'GATED'
  note?: string | null
}

const VALIDITY_STEPS = ['Limited', 'Moderate', 'Strong', 'Definitive']

function readString(raw: unknown): string | null {
  return typeof raw === 'string' && raw.trim().length > 0 ? raw.trim() : null
}

function readNumber(raw: unknown): number | null {
  return typeof raw === 'number' && Number.isFinite(raw) ? raw : null
}

function readStringArray(raw: unknown): string[] {
  if (!Array.isArray(raw)) return []
  return raw.map(readString).filter((value): value is string => value != null)
}

function readCondition(raw: unknown): DiseaseCondition | null {
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) return null
  const obj = raw as Record<string, unknown>
  const name = readString(obj.name)
  if (!name) return null
  return {
    name,
    diseaseIds: readStringArray(obj.disease_ids),
    inheritance: readString(obj.inheritance),
    validity: readString(obj.validity),
    mechanism: readString(obj.mechanism),
    sourceUrls: readStringArray(obj.source_urls),
    caseCount: null,
    sourceList: null,
    sourceKind: 'gene_disease',
  }
}

function legacyCondition(condition: AssociatedCondition): DiseaseCondition {
  return {
    name: condition.name,
    diseaseIds: legacyDiseaseIds(condition),
    inheritance: condition.inheritance,
    validity: condition.evidence_level,
    mechanism: null,
    sourceUrls: [],
    caseCount: condition.case_count,
    sourceList: condition.source_list ?? condition.source,
    sourceKind: 'legacy_report',
  }
}

function legacyDiseaseIds(condition: AssociatedCondition): string[] {
  const candidates = [condition.source, condition.db_tag].filter(
    (value): value is string => typeof value === 'string' && value.trim().length > 0,
  )
  const ids: string[] = []
  for (const value of candidates) {
    const trimmed = value.trim()
    const curie = /^(MONDO|OMIM|ORPHA|MedGen|MedGenUID):[A-Za-z0-9_.-]+$/i.exec(trimmed)
    if (curie) {
      ids.push(trimmed)
      continue
    }
    const omimHash = /^OMIM\s+#?(\d+)$/i.exec(trimmed)
    if (omimHash) {
      ids.push(`OMIM:${omimHash[1]}`)
      continue
    }
    const orphanet = /^Orphanet\s+ORPHA:(\d+)$/i.exec(trimmed)
    if (orphanet) {
      ids.push(`ORPHA:${orphanet[1]}`)
    }
  }
  return Array.from(new Set(ids))
}

function normalizeConditionName(value: string): string {
  return value
    .toLowerCase()
    .replace(/\([^)]*\)/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

function conditionNamesOverlap(a: string, b: string): boolean {
  const left = normalizeConditionName(a)
  const right = normalizeConditionName(b)
  return left === right || left.includes(right) || right.includes(left)
}

function formatWarning(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

function titleCase(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function normalizeValidity(value: string | null): string | null {
  if (!value) return null
  const normalized = value.toLowerCase()
  if (normalized.includes('definitive')) return 'Definitive'
  if (normalized.includes('strong')) return 'Strong'
  if (normalized.includes('moderate')) return 'Moderate'
  if (normalized.includes('limited')) return 'Limited'
  if (normalized.includes('disputed')) return 'Disputed'
  if (normalized.includes('refuted')) return 'Refuted'
  if (normalized.includes('no known')) return 'No known disease relationship'
  return titleCase(value)
}

function diseaseIdLink(id: string): string | null {
  const idx = id.indexOf(':')
  if (idx < 0) return null
  const prefix = id.slice(0, idx).toUpperCase()
  const acc = id.slice(idx + 1).trim()
  if (!acc) return null
  switch (prefix) {
    case 'MONDO':
      return `https://monarchinitiative.org/MONDO:${acc}`
    case 'OMIM':
      return `https://omim.org/entry/${acc}`
    case 'ORPHA':
      return `https://www.orpha.net/en/disease/detail/${acc}`
    case 'MEDGEN':
      return `https://www.ncbi.nlm.nih.gov/medgen/?term=${encodeURIComponent(acc)}`
    case 'MEDGENUID':
      return `https://www.ncbi.nlm.nih.gov/medgen/${acc}`
    default:
      return null
  }
}

function sourceLabelFromId(id: string): string | null {
  const prefix = id.split(':')[0]?.toUpperCase()
  if (prefix === 'MONDO') return 'MONDO'
  if (prefix === 'OMIM') return 'OMIM'
  if (prefix === 'ORPHA') return 'Orphanet'
  if (prefix === 'MEDGEN' || prefix === 'MEDGENUID') return 'NCBI MedGen'
  if (prefix === 'HP' || prefix === 'HPO') return 'Human Phenotype Ontology'
  return null
}

function sourceLabelFromUrl(url: string): string | null {
  const lower = url.toLowerCase()
  if (lower.includes('gencc')) return 'GenCC'
  if (lower.includes('clingen')) return 'ClinGen Gene-Disease Validity'
  if (lower.includes('medgen')) return 'NCBI MedGen'
  if (lower.includes('orpha')) return 'Orphanet'
  if (lower.includes('omim')) return 'OMIM'
  if (lower.includes('monarch')) return 'MONDO'
  return null
}

function sourcePolicy(label: string): SourceRow['policy'] {
  const normalized = label.toLowerCase()
  if (normalized.includes('omim')) return 'PRO'
  if (normalized.includes('restricted')) return 'GATED'
  return 'FREE'
}

function rowFromProvenance(item: SourceProvenance): SourceRow {
  const label = item.source === 'Orphadata' ? 'Orphanet' : item.source
  return {
    label,
    status: item.status,
    version: item.version,
    href: item.source_url,
    policy: sourcePolicy(label),
  }
}

function addSourceRow(rows: Map<string, SourceRow>, row: SourceRow) {
  const key = row.label.toLowerCase()
  const existing = rows.get(key)
  if (!existing) {
    rows.set(key, row)
    return
  }
  rows.set(key, {
    ...existing,
    status: existing.status === 'missing' ? row.status : existing.status,
    version: existing.version ?? row.version,
    href: existing.href ?? row.href,
    note: existing.note ?? row.note,
  })
}

function buildSourceRows(
  geneDiseaseRow: EvidenceSourceSummary | undefined,
  conditions: DiseaseCondition[],
  ids: string[],
  curated: CuratedVariantsDistribution | null | undefined,
): SourceRow[] {
  const rows = new Map<string, SourceRow>()
  const provenance = Array.isArray(geneDiseaseRow?.summary?.provenance)
    ? (geneDiseaseRow.summary.provenance as SourceProvenance[])
    : []
  for (const item of provenance) addSourceRow(rows, rowFromProvenance(item))

  for (const id of ids) {
    const label = sourceLabelFromId(id)
    if (label) {
      addSourceRow(rows, {
        label,
        status: geneDiseaseRow?.status ?? 'missing',
        href: diseaseIdLink(id),
        policy: sourcePolicy(label),
        note: label === 'OMIM' ? 'Launch-gated identifier source' : null,
      })
    }
  }

  for (const condition of conditions) {
    for (const id of condition.diseaseIds) {
      const label = sourceLabelFromId(id)
      if (label) {
        addSourceRow(rows, {
          label,
          status: condition.sourceKind === 'gene_disease' ? geneDiseaseRow?.status ?? 'missing' : 'legacy',
          href: diseaseIdLink(id),
          policy: sourcePolicy(label),
          note: condition.sourceKind === 'legacy_report' ? 'Legacy condition payload' : null,
        })
      }
    }
    for (const url of condition.sourceUrls) {
      const label = sourceLabelFromUrl(url)
      if (label) {
        addSourceRow(rows, {
          label,
          status: geneDiseaseRow?.status ?? 'missing',
          href: url,
          policy: sourcePolicy(label),
        })
      }
    }
    for (const token of (condition.sourceList ?? '').split(/\s*(?:[|,]|\u00b7)\s*/)) {
      const label = token.trim()
      if (!label) continue
      if (/^(OMIM|MONDO|GenCC|ClinGen|DECIPHER|Orphanet|PubMed)$/i.test(label)) {
        addSourceRow(rows, {
          label,
          status: 'legacy',
          policy: sourcePolicy(label),
          note: 'Legacy associated-condition source label',
        })
      }
    }
  }

  if (curated) {
    const sourceStatus = curated.source_status ?? 'legacy'
    const hasClinVarSource = curated.source_id === 'ncbi_clinvar_vcf'
    addSourceRow(rows, {
      label: 'ClinVar',
      status: sourceStatus,
      version: curated.source_version,
      href: curated.source_url,
      policy: curated.public_serialization_allowed === false ? 'GATED' : 'FREE',
      note: hasClinVarSource
        ? sourceStatus === 'fixture'
          ? 'Fixture aggregate from installed ClinVar rows'
          : 'Local full-source gene aggregate'
        : 'Distribution payload without ClinVar source identity',
    })
    if (curated.subtitle?.toLowerCase().includes('uniprot')) {
      addSourceRow(rows, {
        label: 'UniProt',
        status: 'legacy',
        policy: 'FREE',
        note: 'Distribution payload, pending source-row contract',
      })
    }
  }

  const priority = (row: SourceRow) => {
    if (row.policy === 'PRO') return 20
    if (row.status === 'legacy') return 15
    if (row.status === 'fixture' || row.status === 'fallback') return 10
    return 0
  }
  return [...rows.values()].sort((a, b) => priority(a) - priority(b) || a.label.localeCompare(b.label))
}

function curatedSourceLabel(curated: CuratedVariantsDistribution | null | undefined): string {
  if (!curated) return 'No curated variant distribution'
  if (curated.source_id !== 'ncbi_clinvar_vcf') return 'Source metadata unavailable'
  const status = (curated.source_status ?? 'legacy').toLowerCase()
  if (status === 'fixture') return 'ClinVar fixture aggregate'
  if (['ready', 'local', 'live', 'available'].includes(status)) return 'ClinVar local full-source aggregate'
  if (status === 'legacy') return 'Legacy distribution payload'
  return `ClinVar ${formatWarning(status)}`
}

function primaryIds(
  selected: DiseaseCondition | null,
  summary: Record<string, unknown>,
  payload: ReportPayload,
): string[] {
  const selectedIds = selected?.diseaseIds ?? []
  if (selectedIds.length > 0) return selectedIds
  const summaryIds = readStringArray(summary.disease_ids)
  if (summaryIds.length > 0) return summaryIds
  return payload.report_profile?.disease_mechanism?.disease_ids ?? []
}

function sourceBackedConditions(summary: Record<string, unknown>): DiseaseCondition[] {
  return Array.isArray(summary.conditions)
    ? summary.conditions.map(readCondition).filter((condition): condition is DiseaseCondition => condition !== null)
    : []
}

function mergedConditions(summary: Record<string, unknown>, legacy: AssociatedCondition[] | undefined): DiseaseCondition[] {
  const sourceRows = sourceBackedConditions(summary)
  const rows = [...sourceRows]
  for (const row of legacy ?? []) {
    if (sourceRows.some((sourceRow) => conditionNamesOverlap(sourceRow.name, row.name))) continue
    rows.push(legacyCondition(row))
  }
  return rows
}

function StatusChip({ label }: { label: string }) {
  const normalized = label.toLowerCase()
  const warning = ['fixture', 'fallback', 'legacy', 'missing', 'error', 'failed'].includes(normalized)
  return (
    <span
      style={{
        ...chipStyle,
        background: warning ? 'var(--warn-tint)' : 'var(--teal-tint)',
        borderColor: warning ? 'var(--warn-bdr)' : 'var(--teal-bdr)',
        color: warning ? 'var(--warn)' : 'var(--teal-deep)',
      }}
    >
      {formatWarning(label)}
    </span>
  )
}

function PolicyChip({ policy }: { policy: SourceRow['policy'] }) {
  const pro = policy !== 'FREE'
  return (
    <span
      style={{
        ...chipStyle,
        background: pro ? 'var(--cls-vus-bg)' : 'var(--bg)',
        borderColor: pro ? 'var(--cls-vus-bdr)' : 'var(--line)',
        color: pro ? 'var(--cls-vus-text)' : 'var(--ink-3)',
      }}
      title={pro ? 'Source requires launch-time visibility or license handling.' : 'Source can render in public mode when row metadata allows it.'}
    >
      {policy}
    </span>
  )
}

function ValidityScale({ value }: { value: string | null }) {
  const normalized = normalizeValidity(value)
  const activeIndex = normalized ? VALIDITY_STEPS.findIndex((step) => step === normalized) : -1
  const exceptional = normalized === 'Disputed' || normalized === 'Refuted'
  return (
    <div style={validityScaleStyle} aria-label="Gene-disease validity scale">
      {VALIDITY_STEPS.map((step, index) => {
        const active = index <= activeIndex && !exceptional
        const current = index === activeIndex && !exceptional
        return (
          <div key={step} style={validityStepStyle}>
            <div
              style={{
                ...validityBarStyle,
                background: active ? 'var(--teal)' : 'var(--bg-soft2)',
                borderColor: current ? 'var(--teal-deep)' : 'var(--line)',
              }}
            />
            <span style={{ color: current ? 'var(--ink)' : 'var(--ink-4)' }}>{step}</span>
          </div>
        )
      })}
      {exceptional && (
        <span style={{ ...chipStyle, background: 'var(--err-tint)', borderColor: 'var(--err)', color: 'var(--err)' }}>
          {normalized}
        </span>
      )}
    </div>
  )
}

function Fact({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div style={factStyle}>
      <span style={factLabelStyle}>{label}</span>
      <span style={factValueStyle}>{value || 'Unavailable'}</span>
    </div>
  )
}

export function DiseaseValidityDashboard({
  payload,
  evidence,
  sectionTarget,
}: DiseaseValidityDashboardProps) {
  const geneDiseaseRow = useMemo(
    () => evidence.find((row) => row.source?.toLowerCase() === 'gene_disease'),
    [evidence],
  )
  const summary = useMemo(
    () => (geneDiseaseRow?.summary ?? {}) as Record<string, unknown>,
    [geneDiseaseRow],
  )
  const conditions = useMemo(
    () => mergedConditions(summary, payload.associated_conditions),
    [payload.associated_conditions, summary],
  )
  const [selectedIndex, setSelectedIndex] = useState(0)
  const selected = conditions[selectedIndex] ?? conditions[0] ?? null

  const typedDisease = payload.report_profile?.disease_mechanism ?? null
  const diseaseIds = primaryIds(selected, summary, payload)
  const primaryCondition =
    selected?.name ??
    readString(summary.primary_condition) ??
    typedDisease?.primary_condition ??
    payload.associated_conditions?.[0]?.name ??
    null
  const gene =
    readString(summary.approved_symbol) ??
    readString(summary.gene) ??
    payload.report_profile?.header?.gene ??
    payload.variant_summary_rows[0]?.gene ??
    null
  const inheritance = selected?.inheritance ?? readString(summary.inheritance) ?? typedDisease?.inheritance ?? null
  const validity = selected?.validity ?? readString(summary.gene_disease_validity) ?? typedDisease?.gene_disease_validity ?? null
  const mechanism =
    selected?.sourceKind === 'legacy_report'
      ? null
      : selected?.mechanism ?? readString(summary.mechanism) ?? typedDisease?.mechanism ?? null
  const genccCount = readNumber(summary.gencc_assertion_count)
  const warnings = [
    ...(geneDiseaseRow?.warnings ?? []),
    ...readStringArray(summary.warnings),
    ...(typedDisease?.warnings ?? []),
    ...(payload.curated_variants_distribution?.warnings ?? []),
  ]
  const sourceRows = buildSourceRows(geneDiseaseRow, conditions, diseaseIds, payload.curated_variants_distribution)
  const curated = payload.curated_variants_distribution
  const curatedSourceStatus = curated?.source_status ?? (curated ? 'legacy' : null)
  const curatedIsClinVar = curated?.source_id === 'ncbi_clinvar_vcf'
  const curatedIsFixture = curatedIsClinVar && curatedSourceStatus === 'fixture'
  const curatedSourceBacked = curatedIsClinVar && curatedSourceStatus !== 'legacy'
  const proSourceCount = sourceRows.filter((row) => row.policy !== 'FREE').length
  const nonReadySourceCount = sourceRows.filter((row) =>
    ['fixture', 'fallback', 'legacy', 'missing', 'error', 'failed'].includes(row.status.toLowerCase()),
  ).length
  const sourceState = geneDiseaseRow?.status ?? typedDisease?.provenance?.[0]?.status ?? 'missing'
  const sourceBacked = !['fixture', 'fallback', 'legacy', 'missing', 'error', 'failed'].includes(sourceState)

  return (
    <div style={dashboardStyle}>
      <section style={heroStyle} aria-label="Gene-disease validity summary">
        <div style={heroMainStyle}>
          <span style={kickerStyle}>Gene-disease validity</span>
          <h3 style={heroTitleStyle}>
            {gene || 'Gene'} <span style={{ color: 'var(--ink-4)' }}>-&gt;</span> {primaryCondition || 'condition unavailable'}
          </h3>
          <div style={chipRowStyle}>
            <StatusChip label={sourceState} />
            {validity && <span style={validityChipStyle}>{normalizeValidity(validity)}</span>}
            {genccCount !== null && <span style={chipStyle}>GenCC {genccCount} assertion{genccCount === 1 ? '' : 's'}</span>}
            {sectionTarget?.match_level && <span style={chipStyle}>{formatWarning(sectionTarget.match_level)}</span>}
          </div>
        </div>
        <div style={factsGridStyle}>
          <Fact label="Inheritance" value={inheritance} />
          <Fact label="Validity" value={normalizeValidity(validity)} />
          <Fact label="Source state" value={sourceBacked ? 'source-backed' : 'not launch-ready'} />
        </div>
      </section>

      <ValidityScale value={validity} />

      {mechanism && (
        <p style={mechanismStyle}>
          {mechanism}
        </p>
      )}

      {diseaseIds.length > 0 && (
        <div style={idStripStyle}>
          <span style={kickerStyle}>Disease identifiers</span>
          <div style={chipRowStyle}>
            {diseaseIds.map((id) => {
              const href = diseaseIdLink(id)
              const label = sourceLabelFromId(id)
              return href ? (
                <a key={id} href={href} target="_blank" rel="noopener noreferrer" style={idChipStyle} title={label ?? id}>
                  {id}
                </a>
              ) : (
                <span key={id} style={idChipStyle}>{id}</span>
              )
            })}
          </div>
        </div>
      )}

      {conditions.length > 0 && (
        <section style={panelStyle} aria-label="Associated condition navigator">
          <div style={panelHeadStyle}>
            <div>
              <span style={kickerStyle}>Condition navigator</span>
              <div style={panelTitleStyle}>{conditions.length} condition{conditions.length === 1 ? '' : 's'}</div>
            </div>
            <span style={panelNoteStyle}>Sorted source rows first, legacy report rows second</span>
          </div>
          <div style={conditionListStyle}>
            {conditions.map((condition, index) => {
              const active = index === selectedIndex
              return (
                <button
                  key={`${condition.name}-${index}`}
                  type="button"
                  style={{
                    ...conditionButtonStyle,
                    borderColor: active ? 'var(--teal)' : 'var(--line)',
                    background: active ? 'var(--teal-tint)' : 'var(--bg)',
                  }}
                  onClick={() => setSelectedIndex(index)}
                >
                  <span style={conditionNameStyle}>{condition.name}</span>
                  <span style={conditionMetaStyle}>
                    {condition.inheritance ?? 'inheritance unavailable'}
                    {condition.validity ? ` | ${normalizeValidity(condition.validity)}` : ''}
                    {condition.caseCount !== null ? ` | ${condition.caseCount.toLocaleString()} cases` : ''}
                  </span>
                  <span style={chipRowStyle}>
                    <StatusChip label={condition.sourceKind === 'gene_disease' ? sourceState : 'legacy'} />
                    {condition.diseaseIds.slice(0, 3).map((id) => (
                      <span key={id} style={miniIdStyle}>{id}</span>
                    ))}
                  </span>
                </button>
              )
            })}
          </div>
        </section>
      )}

      <details style={sourceDetailsStyle}>
        <summary style={sourceSummaryStyle}>
          <span>
            <span style={kickerStyle}>Source ledger</span>
            <span style={sourceSummaryTitleStyle}>Audit drawer</span>
          </span>
          <span style={sourceSummaryMetaStyle}>
            <span style={chipStyle}>{sourceRows.length} sources</span>
            {proSourceCount > 0 && <PolicyChip policy="PRO" />}
            {nonReadySourceCount > 0 && <StatusChip label={`${nonReadySourceCount} not launch-ready`} />}
          </span>
        </summary>
        <div style={sourceDrawerBodyStyle}>
          <p style={sourceDrawerNoteStyle}>
            Source IDs, source versions, and launch gates live here so Section 5 can stay readable while still remaining audit-grade.
          </p>
          <div style={sourceTableStyle}>
            {sourceRows.map((row) => (
              <div key={row.label} style={sourceRowStyle}>
                <div style={{ minWidth: 0 }}>
                  {row.href ? (
                    <a href={row.href} target="_blank" rel="noopener noreferrer" style={sourceLinkStyle}>
                      {row.label}
                    </a>
                  ) : (
                    <span style={sourceNameStyle}>{row.label}</span>
                  )}
                  {row.version && <div style={sourceVersionStyle}>{row.version}</div>}
                  {row.note && <div style={sourceVersionStyle}>{row.note}</div>}
                </div>
                <div style={sourceMetaStyle}>
                  <PolicyChip policy={row.policy} />
                  <StatusChip label={row.status} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </details>

      <section style={panelStyle} aria-label="Curated variant landscape">
        <div style={panelHeadStyle}>
          <div>
            <span style={kickerStyle}>Variant landscape</span>
            <div style={panelTitleStyle}>Curated variant distribution</div>
          </div>
          <span style={panelNoteStyle}>
            {curatedSourceLabel(curated)}
          </span>
        </div>
        {curated ? (
          <>
            <div style={chipRowStyle}>
              <StatusChip label={curatedSourceStatus ?? 'missing'} />
              {curated.source_id && <span style={chipStyle}>{curated.source_id}</span>}
              {curated.source_version && (
                <span style={sourceVersionChipStyle}>{curated.source_version}</span>
              )}
            </div>
            {!curatedSourceBacked && (
              <div style={warningBandStyle}>
                Distribution counts are missing ClinVar local source metadata.
              </div>
            )}
            {curatedIsFixture && (
              <div style={warningBandStyle}>
                Fixture aggregate: installed sample rows only, not all RPE65 ClinVar records.
              </div>
            )}
            <CuratedVariantsGrid data={curated} />
          </>
        ) : (
          <p style={emptyTextStyle}>No curated variant distribution is available for this gene.</p>
        )}
      </section>

      {warnings.length > 0 && (
        <div style={warningListStyle}>
          {Array.from(new Set(warnings)).slice(0, 5).map((warning) => (
            <span key={warning} style={warningChipStyle}>{formatWarning(warning)}</span>
          ))}
        </div>
      )}
    </div>
  )
}

const dashboardStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
}

const heroStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 230px), 1fr))',
  gap: 14,
  alignItems: 'stretch',
  border: '0.5px solid var(--line)',
  borderRadius: 'var(--r-md)',
  background: 'var(--bg-soft)',
  padding: 14,
}

const heroMainStyle: CSSProperties = {
  minWidth: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const heroTitleStyle: CSSProperties = {
  margin: 0,
  fontSize: 18,
  lineHeight: 1.25,
  fontWeight: 650,
  color: 'var(--ink)',
  overflowWrap: 'anywhere',
  minWidth: 0,
}

const kickerStyle: CSSProperties = {
  fontSize: 10.5,
  fontWeight: 700,
  color: 'var(--ink-4)',
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
}

const chipRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  flexWrap: 'wrap',
  minWidth: 0,
}

const chipStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
  border: '0.5px solid var(--line)',
  borderRadius: 999,
  background: 'var(--bg)',
  color: 'var(--ink-3)',
  padding: '2px 7px',
  fontSize: 10.5,
  fontWeight: 700,
  whiteSpace: 'nowrap',
}

const sourceVersionChipStyle: CSSProperties = {
  ...chipStyle,
  maxWidth: '100%',
  whiteSpace: 'normal',
  overflowWrap: 'anywhere',
}

const validityChipStyle: CSSProperties = {
  ...chipStyle,
  background: 'var(--teal-tint)',
  borderColor: 'var(--teal-bdr)',
  color: 'var(--teal-deep)',
}

const factsGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr',
  gap: 8,
}

const factStyle: CSSProperties = {
  border: '0.5px solid var(--line)',
  borderRadius: 'var(--r-sm)',
  background: 'var(--bg)',
  padding: '8px 10px',
  minWidth: 0,
}

const factLabelStyle: CSSProperties = {
  display: 'block',
  fontSize: 10,
  color: 'var(--ink-4)',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  fontWeight: 700,
}

const factValueStyle: CSSProperties = {
  display: 'block',
  marginTop: 2,
  fontSize: 12.5,
  color: 'var(--ink-2)',
  fontWeight: 650,
  maxWidth: '100%',
  overflowWrap: 'anywhere',
  wordBreak: 'break-word',
}

const validityScaleStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(92px, 1fr))',
  alignItems: 'center',
  gap: 8,
}

const validityStepStyle: CSSProperties = {
  minWidth: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  fontSize: 10.5,
  fontWeight: 650,
}

const validityBarStyle: CSSProperties = {
  height: 7,
  border: '0.5px solid var(--line)',
  borderRadius: 999,
}

const mechanismStyle: CSSProperties = {
  margin: 0,
  fontSize: 13,
  lineHeight: 1.6,
  color: 'var(--ink-2)',
}

const idStripStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  flexWrap: 'wrap',
}

const idChipStyle: CSSProperties = {
  ...chipStyle,
  fontFamily: 'var(--mono)',
  color: 'var(--ink-3)',
  textDecoration: 'none',
}

const panelStyle: CSSProperties = {
  borderTop: '0.5px solid var(--line)',
  paddingTop: 14,
}

const panelHeadStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'baseline',
  gap: 12,
  flexWrap: 'wrap',
  marginBottom: 10,
}

const panelTitleStyle: CSSProperties = {
  marginTop: 2,
  fontSize: 13.5,
  color: 'var(--ink)',
  fontWeight: 650,
}

const panelNoteStyle: CSSProperties = {
  fontSize: 11,
  color: 'var(--ink-4)',
}

const conditionListStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 250px), 1fr))',
  gap: 8,
}

const conditionButtonStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'flex-start',
  gap: 6,
  width: '100%',
  border: '0.5px solid var(--line)',
  borderRadius: 'var(--r-sm)',
  padding: 10,
  cursor: 'pointer',
  textAlign: 'left',
  transition: 'border-color var(--dur-1) var(--ease-standard), background var(--dur-1) var(--ease-standard)',
}

const conditionNameStyle: CSSProperties = {
  fontSize: 12.5,
  color: 'var(--ink)',
  fontWeight: 650,
}

const conditionMetaStyle: CSSProperties = {
  fontSize: 11.5,
  color: 'var(--ink-4)',
}

const miniIdStyle: CSSProperties = {
  fontFamily: 'var(--mono)',
  fontSize: 10,
  color: 'var(--ink-4)',
}

const sourceTableStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr',
  border: '0.5px solid var(--line)',
  borderRadius: 'var(--r-md)',
  overflow: 'hidden',
}

const sourceDetailsStyle: CSSProperties = {
  borderTop: '0.5px solid var(--line)',
  paddingTop: 12,
}

const sourceSummaryStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 12,
  cursor: 'pointer',
  border: '0.5px solid var(--line)',
  borderRadius: 'var(--r-md)',
  background: 'var(--bg-soft)',
  padding: '9px 11px',
}

const sourceSummaryTitleStyle: CSSProperties = {
  display: 'block',
  marginTop: 2,
  fontSize: 12.5,
  color: 'var(--ink)',
  fontWeight: 650,
}

const sourceSummaryMetaStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  gap: 6,
  flexWrap: 'wrap',
}

const sourceDrawerBodyStyle: CSSProperties = {
  marginTop: 10,
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const sourceDrawerNoteStyle: CSSProperties = {
  margin: 0,
  fontSize: 11.5,
  color: 'var(--ink-4)',
}

const sourceRowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) auto',
  gap: 10,
  alignItems: 'center',
  padding: '9px 11px',
  borderBottom: '0.5px solid var(--line)',
  background: 'var(--bg)',
}

const sourceNameStyle: CSSProperties = {
  fontSize: 12.5,
  color: 'var(--ink)',
  fontWeight: 650,
}

const sourceLinkStyle: CSSProperties = {
  ...sourceNameStyle,
  color: 'var(--teal-deep)',
  textDecoration: 'none',
}

const sourceVersionStyle: CSSProperties = {
  marginTop: 2,
  fontSize: 10.5,
  color: 'var(--ink-4)',
}

const sourceMetaStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  gap: 6,
  flexWrap: 'wrap',
}

const warningBandStyle: CSSProperties = {
  border: '0.5px solid var(--warn-bdr)',
  borderRadius: 'var(--r-sm)',
  background: 'var(--warn-tint)',
  color: 'var(--warn)',
  padding: '8px 10px',
  fontSize: 11.5,
  fontWeight: 650,
}

const warningListStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 6,
}

const warningChipStyle: CSSProperties = {
  ...chipStyle,
  background: 'var(--warn-tint)',
  borderColor: 'var(--warn-bdr)',
  color: 'var(--warn)',
}

const emptyTextStyle: CSSProperties = {
  margin: 0,
  fontSize: 12.5,
  color: 'var(--ink-4)',
}
