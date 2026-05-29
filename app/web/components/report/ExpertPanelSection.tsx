'use client'

import { Card, type Verdict } from '@/components/ui/Card'
import { ClassificationBadge } from '@/components/ui/ClassificationBadge'
import type {
  ExpertPanelClassification,
  ExpertPanelCriterion,
  ExpertPanelData,
} from './expert-panel-sample'

interface ExpertPanelSectionProps {
  data?: ExpertPanelData | null
}

const CLASSIFICATION_DISPLAY: Record<ExpertPanelClassification, string> = {
  pathogenic: 'Pathogenic',
  likely_pathogenic: 'Likely pathogenic',
  vus: 'VUS',
  likely_benign: 'Likely benign',
  benign: 'Benign',
  conflicting: 'Conflicting',
  not_classified: 'Not classified',
}

const RAMP_TO_VERDICT: Record<ExpertPanelClassification, Verdict | null> = {
  pathogenic: 'Pathogenic',
  likely_pathogenic: 'Likely pathogenic',
  vus: 'VUS',
  likely_benign: 'Likely benign',
  benign: 'Benign',
  conflicting: null,
  not_classified: null,
}

const CRITERION_STATE_TINT: Record<ExpertPanelCriterion['state'], { bg: string; bd: string; ink: string }> = {
  met: { bg: 'var(--bg-soft)', bd: 'var(--line)', ink: 'var(--ink-1)' },
  not_met: { bg: 'var(--bg-soft)', bd: 'var(--line)', ink: 'var(--ink-4)' },
  not_assessed: { bg: 'transparent', bd: 'var(--line)', ink: 'var(--ink-4)' },
  conflicting: { bg: 'var(--warn-tint)', bd: 'var(--warn-bdr)', ink: 'var(--warn)' },
}

function formatFetchedAt(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toISOString().slice(0, 10)
}

function strengthSuffix(code: string, applied: string): string | null {
  const prefix = code + '_'
  if (!applied.startsWith(prefix)) return null
  return applied.slice(prefix.length)
}

function FreshnessChip({ data }: { data: ExpertPanelData }) {
  if (data.freshness === 'fresh') return null
  if (data.freshness === 'stale') {
    return (
      <span
        title={data.freshness_reason ?? 'stale'}
        style={{
          display: 'inline-block',
          padding: '1px 6px',
          borderRadius: 999,
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: '0.02em',
          color: 'var(--warn)',
          background: 'var(--warn-tint)',
          border: '0.5px solid var(--warn-bdr)',
          lineHeight: '16px',
          verticalAlign: 'middle',
        }}
      >
        Stale
      </span>
    )
  }
  return null
}

function CriterionChip({ criterion }: { criterion: ExpertPanelCriterion }) {
  const tint = CRITERION_STATE_TINT[criterion.state]
  const suffix = strengthSuffix(criterion.code, criterion.applied_strength)
  const isOverride = criterion.applied_strength !== criterion.default_strength
  const title =
    (criterion.rationale ?? '') +
    (isOverride
      ? `\n(VCEP override: default ${criterion.default_strength} → applied ${criterion.applied_strength})`
      : '')

  return (
    <span
      title={title.trim() || undefined}
      style={{
        display: 'inline-flex',
        alignItems: 'baseline',
        gap: 4,
        padding: '3px 8px',
        borderRadius: 'var(--r-sm)',
        background: tint.bg,
        border: `0.5px solid ${tint.bd}`,
        color: tint.ink,
        fontSize: 11.5,
        whiteSpace: 'nowrap',
      }}
    >
      <span style={{ fontFamily: 'var(--mono)', fontWeight: 700 }}>{criterion.code}</span>
      {suffix && (
        <span style={{ color: 'var(--ink-3)', fontSize: 10.5 }}>_{suffix}</span>
      )}
      {isOverride && (
        <span
          aria-label="VCEP strength override"
          style={{
            color: 'var(--teal-deep)',
            fontWeight: 700,
            fontSize: 10,
            marginLeft: 2,
          }}
        >
          §
        </span>
      )}
    </span>
  )
}

export function ExpertPanelSection({ data: dataProp }: ExpertPanelSectionProps) {
  // No fixture-fallback: M-007 trim ships `report_profile.expert_panel` as
  // null by default, so a fallback would paint RPE65 fixture data onto every
  // non-RPE65 query. Until the lazy clingen_vcep section is wired through
  // LazySection, callers that have no data render nothing.
  if (!dataProp) return null
  const data = dataProp
  const verdict = RAMP_TO_VERDICT[data.final_classification]
  const classificationText = CLASSIFICATION_DISPLAY[data.final_classification]

  return (
    <Card
      title="Expert Panel"
      meta={data.vcep.name}
      verdict={verdict}
      actions={<FreshnessChip data={data} />}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <ClassificationBadge classification={classificationText} />
          <span style={{ fontSize: 12, color: 'var(--ink-4)' }}>
            Curated {data.vcep.last_curated_date}
          </span>
          <a
            href={data.vcep.vcep_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontSize: 12,
              color: 'var(--teal-deep)',
              textDecoration: 'underline',
              textUnderlineOffset: 2,
            }}
          >
            View on ClinGen
          </a>
        </div>

        <p style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--ink-2)', margin: 0 }}>
          {data.narrative}
        </p>

        <div>
          <div
            style={{
              fontSize: 10.5,
              fontWeight: 700,
              color: 'var(--ink-4)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              marginBottom: 8,
            }}
          >
            ACMG criteria applied (VCEP-specific strengths)
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {data.criteria.map((c) => (
              <CriterionChip key={c.code} criterion={c} />
            ))}
          </div>
          <p style={{ fontSize: 10.5, color: 'var(--ink-4)', margin: '10px 0 0' }}>
            <span style={{ color: 'var(--teal-deep)', fontWeight: 700 }}>§</span> indicates a
            VCEP-specific strength override versus the default ACMG rule. Hover any chip for
            rationale.
          </p>
        </div>

        <div
          style={{
            fontSize: 11,
            color: 'var(--ink-4)',
            borderTop: '0.5px solid var(--line)',
            paddingTop: 10,
            display: 'flex',
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <span>{data.source_scope}</span>
          <span>·</span>
          <a
            href={data.provenance.source_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--ink-4)', textDecoration: 'underline', textUnderlineOffset: 2 }}
          >
            {data.provenance.source_version}
          </a>
          <span>·</span>
          <span>Fetched {formatFetchedAt(data.provenance.fetched_at)}</span>
        </div>
      </div>
    </Card>
  )
}
