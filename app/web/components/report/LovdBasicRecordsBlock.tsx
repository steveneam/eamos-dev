import { EvidenceChip } from '@/components/ui/EvidenceChip'
import type { LovdBasicRecordsSection } from '@/lib/backend'
import {
  LOVD_PRESENCE_NOTICE,
  safeLovdBasicObservations,
} from '@/lib/lovd-basic-observation'

interface LovdBasicRecordsBlockProps {
  section?: LovdBasicRecordsSection | null
}

export function LovdBasicRecordsBlock({ section }: LovdBasicRecordsBlockProps) {
  const observations = safeLovdBasicObservations(section)
  if (observations.length === 0) return null

  return (
    <section
      aria-label="LOVD basic-record presence"
      style={{
        marginTop: 'var(--report-subpanel-gap)',
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-md)',
        background: 'var(--bg-soft)',
        padding: 'var(--report-subpanel-pad)',
        minWidth: 0,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 10,
          flexWrap: 'wrap',
        }}
      >
        <span className="eamos-kicker">LOVD basic-record presence</span>
        <span style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <EvidenceChip
            size="xs"
            tone={{ bg: 'var(--cls-na-bg)', border: 'var(--cls-na-bdr)', text: 'var(--cls-na-text)' }}
            title="This source-presence signal carries no classification or ACMG strength."
          >
            Presence only
          </EvidenceChip>
          <EvidenceChip
            size="xs"
            tone={{ bg: 'var(--bg)', border: 'var(--line)', text: 'var(--ink-4)' }}
            title="Assembly, versioned transcript, and coding HGVS all matched exactly."
          >
            Exact HGVS
          </EvidenceChip>
        </span>
      </div>

      <p style={{ margin: '10px 0 0', color: 'var(--ink-3)', fontSize: 12.5, lineHeight: 1.55 }}>
        {LOVD_PRESENCE_NOTICE}
      </p>

      <ol
        aria-label="Matching synthetic LOVD basic records"
        style={{ listStyle: 'none', display: 'grid', gap: 8, margin: '12px 0 0', padding: 0 }}
      >
        {observations.map((observation) => (
          <li
            key={observation.source_record_id}
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1fr) auto',
              gap: 12,
              alignItems: 'center',
              border: '0.5px solid var(--line)',
              borderRadius: 'var(--r-sm)',
              background: 'var(--bg)',
              padding: '10px 12px',
              minWidth: 0,
            }}
          >
            <div style={{ minWidth: 0 }}>
              <div
                style={{
                  color: 'var(--ink)',
                  fontSize: 13,
                  fontWeight: 600,
                  fontVariantNumeric: 'tabular-nums',
                  overflowWrap: 'anywhere',
                }}
              >
                {observation.transcript_accession}:{observation.hgvs_c}
              </div>
              <div style={{ marginTop: 3, color: 'var(--ink-4)', fontSize: 11.5, lineHeight: 1.45 }}>
                {observation.installation.display_name} · {observation.genome_build} · source edited{' '}
                {observation.source_edited_at.slice(0, 10)}
              </div>
            </div>
            <a
              href={observation.source_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: 'var(--teal-deep)',
                fontSize: 11.5,
                fontWeight: 600,
                textDecoration: 'none',
                borderBottom: '1px dotted var(--teal-bdr)',
                whiteSpace: 'nowrap',
              }}
            >
              Open record ↗
            </a>
          </li>
        ))}
      </ol>

      <p style={{ margin: '10px 0 0', color: 'var(--ink-4)', fontSize: 11, lineHeight: 1.45 }}>
        Synthetic fixture pilot. No live LOVD request, cache write, or classification field was used.
      </p>
    </section>
  )
}
