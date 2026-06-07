'use client'

import { ClassificationBadge } from '@/components/ui/ClassificationBadge'
import { CuratorQuote } from './CuratorQuote'
import {
  StackedCountBar,
  type RampVerdict,
  type StackedCountSegment,
} from '@/components/ui/StackedCountBar'
import { reviewStatusToStars } from '@/lib/clinvar-review-status'
import { getSourceMeta } from '@/lib/sources'
import type { EvidenceSourceSummary } from '@/lib/backend'

// ClinVarBlock — focused ClinVar summary used inside §2 Evidence by source.
//
// Replaces the generic per-source EvidenceTable that previously listed every
// source row (variant_validator, gnomad, ensembl, spliceai, clingen,
// gene_disease, molecular_context, computational_annotations, pubmed, litvar2,
// clinical_trials, vep). Every one of those except ClinVar already has — or
// will have — a dedicated home elsewhere in the report; ClinVar is the only
// source without a section of its own, so it lives here.

interface ClinVarBlockProps {
  evidence: EvidenceSourceSummary[]
}

const SUBMITTER_VERDICTS: readonly RampVerdict[] = [
  'Pathogenic',
  'Likely pathogenic',
  'VUS',
  'Likely benign',
  'Benign',
]

function readSubmitterSegments(raw: unknown): StackedCountSegment[] {
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) return []
  const dict = raw as Record<string, unknown>
  const segments: StackedCountSegment[] = []
  for (const verdict of SUBMITTER_VERDICTS) {
    const v = dict[verdict]
    if (typeof v === 'number' && Number.isFinite(v) && v > 0) {
      segments.push({ verdict, count: v })
    }
  }
  return segments
}

function readString(raw: unknown): string | null {
  return typeof raw === 'string' && raw.trim().length > 0 ? raw.trim() : null
}

export function ClinVarBlock({ evidence }: ClinVarBlockProps) {
  const row = evidence.find((e) => e.source?.toLowerCase() === 'clinvar')
  if (!row || !row.summary || typeof row.summary !== 'object') return null
  const summary = row.summary as Record<string, unknown>

  const classification = readString(summary.classification)
  const reviewStatus = readString(summary.review_status)
  const conditions = readString(summary.conditions)
  const consequence = readString(summary.consequence)
  const submitterSegments = readSubmitterSegments(summary.submitter_counts)
  const submitterTotal = submitterSegments.reduce((sum, s) => sum + s.count, 0)
  const stars = reviewStatusToStars(reviewStatus)
  const meta = getSourceMeta(row.source)
  const link = row.source_url ?? null

  // Empty-state guard: if the row is here but has nothing to show, render
  // nothing rather than an empty card.
  if (!classification && !reviewStatus && !conditions && !consequence && submitterSegments.length === 0) {
    return null
  }

  return (
    <div
      style={{
        marginTop: 18,
        padding: '14px 16px',
        background: 'var(--bg-soft)',
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="eamos-kicker">
          {meta?.label ?? 'ClinVar'}
        </span>
        {link && (
          <a
            href={link}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontSize: 11.5,
              color: 'var(--teal-deep)',
              textDecoration: 'underline',
              textUnderlineOffset: 3,
            }}
          >
            View record ↗
          </a>
        )}
      </div>

      {(classification || reviewStatus) && (
        <div className="flex items-center gap-2 flex-wrap">
          {classification && (
            <ClassificationBadge classification={classification} reviewStars={stars} />
          )}
          {reviewStatus && (
            <span
              style={{ fontSize: 11.5, color: 'var(--ink-4)', borderBottom: '1px dotted var(--ink-5)', cursor: 'help' }}
              title="ClinVar review confidence (0–4 stars). More stars = more independent submitters agree, or an expert panel reviewed it."
            >
              {reviewStatus}
            </span>
          )}
        </div>
      )}

      {/* Same curator-quote grammar as ClinGen above; the submitter free-text
          interpretation is backend-gated, so the quote is mock-marked. */}
      <CuratorQuote mock />

      {submitterSegments.length > 0 && (
        <div className="flex flex-col gap-1">
          <div style={{ fontSize: 10.5, color: 'var(--ink-4)' }}>
            {submitterTotal} submitter{submitterTotal === 1 ? '' : 's'}
          </div>
          <StackedCountBar
            segments={submitterSegments}
            height={14}
            ariaLabel={`ClinVar submitter classifications: ${submitterSegments
              .map((s) => `${s.verdict} ${s.count}`)
              .join(', ')}`}
          />
        </div>
      )}

      {(conditions || consequence) && (
        <dl
          style={{
            margin: 0,
            display: 'grid',
            gridTemplateColumns: 'auto minmax(0, 1fr)',
            columnGap: 12,
            rowGap: 4,
            fontSize: 12.5,
            color: 'var(--ink-2)',
          }}
        >
          {conditions && (
            <>
              <dt style={{ color: 'var(--ink-4)' }}>Conditions</dt>
              <dd style={{ margin: 0, overflowWrap: 'anywhere' }}>{conditions}</dd>
            </>
          )}
          {consequence && (
            <>
              <dt style={{ color: 'var(--ink-4)' }}>Consequence</dt>
              <dd style={{ margin: 0, fontFamily: 'var(--mono)', overflowWrap: 'anywhere' }}>{consequence}</dd>
            </>
          )}
        </dl>
      )}

      {row.warnings && row.warnings.length > 0 && (
        <div
          style={{
            fontSize: 11,
            color: 'var(--warn)',
          }}
        >
          {row.warnings.join(' · ')}
        </div>
      )}
    </div>
  )
}
