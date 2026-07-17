import { EvidenceChip } from '@/components/ui/EvidenceChip'
import type { FunctionalStudy } from '@/lib/backend'

const MAVE_TIP =
  'MAVE and deep mutational scanning assays measure the functional effects of many variants in one experiment.'
const UNCURATED_TIP =
  'These are source-reported measurements. No ACMG PS3 or BS3 strength has been asserted.'

interface MaveFunctionalBlockProps {
  gene?: string | null
  query?: string | null
  studies?: FunctionalStudy[]
}

export function MaveFunctionalBlock({
  gene,
  query,
  studies = [],
}: MaveFunctionalBlockProps) {
  const term = gene ?? query ?? ''
  const mavedbHref = `https://www.mavedb.org/#/search?search=${encodeURIComponent(term)}`
  const exactStudies = studies.filter((study) => study.source_tags.includes('mavedb'))

  return (
    <div
      style={{
        marginTop: 'var(--report-subpanel-gap)',
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-md)',
        background: 'var(--bg-soft)',
        padding: 'var(--report-subpanel-pad)',
        minWidth: 0,
        maxWidth: '100%',
        overflowX: 'hidden',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 10,
          flexWrap: 'wrap',
          minWidth: 0,
        }}
      >
        <span
          className="eamos-kicker"
          title={MAVE_TIP}
          style={{
            cursor: 'help',
            borderBottom: '1px dotted var(--ink-5)',
            overflowWrap: 'anywhere',
            minWidth: 0,
          }}
        >
          MAVE functional evidence · MaveDB
        </span>
        <span
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            flexWrap: 'wrap',
          }}
        >
          <EvidenceChip
            size="xs"
            uppercase
            tone={{
              bg: 'var(--cls-na-bg)',
              border: 'var(--cls-na-bdr)',
              text: 'var(--cls-na-text)',
            }}
            title={exactStudies.length > 0 ? UNCURATED_TIP : 'No exact local MaveDB match was returned.'}
            style={{ cursor: 'help' }}
          >
            {exactStudies.length > 0 ? 'Uncurated' : 'No match'}
          </EvidenceChip>
          <EvidenceChip
            size="xs"
            tone={{ bg: 'var(--bg)', border: 'var(--line)', text: 'var(--ink-4)' }}
            title="Each exact score-set match is displayed independently."
          >
            {exactStudies.length} exact {exactStudies.length === 1 ? 'measurement' : 'measurements'}
          </EvidenceChip>
        </span>
      </div>

      {exactStudies.length > 0 ? (
        <>
          <p
            style={{
              fontSize: 12.5,
              color: 'var(--ink-3)',
              margin: '10px 0 0',
              lineHeight: 1.55,
            }}
          >
            Raw source values are assay-specific and are not comparable across score sets.
            They are shown without aggregation, calibration, or an ACMG PS3/BS3 assignment.
          </p>
          <ol
            aria-label="Exact MaveDB measurements"
            style={{
              listStyle: 'none',
              display: 'grid',
              gap: 10,
              margin: '12px 0 0',
              padding: 0,
            }}
          >
            {exactStudies.map((study) => (
              <MaveMeasurement
                key={`${study.score_set_urn ?? study.source_accession ?? study.id}:${study.variant_urn ?? study.id}:${study.score_column ?? ''}`}
                study={study}
                fallbackHref={mavedbHref}
                gene={gene}
              />
            ))}
          </ol>
        </>
      ) : (
        <>
          <p
            style={{
              fontSize: 12.5,
              color: 'var(--ink-3)',
              margin: '10px 0 0',
              lineHeight: 1.55,
            }}
          >
            No exact, policy-approved local MaveDB CC0 measurement matched this variant.
          </p>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
              gap: 10,
              marginTop: 12,
            }}
          >
            <Metric label="Evidence status" value="Unavailable" hint="no exact MAVE match" />
            <Metric label="ACMG code" value="None" hint="PS3/BS3 not asserted" />
          </div>
        </>
      )}

      <div style={{ marginTop: 12, fontSize: 11 }}>
        <a
          href={mavedbHref}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: 'var(--teal-deep)',
            textDecoration: 'none',
            borderBottom: '1px dotted var(--teal-bdr)',
          }}
        >
          Search MaveDB for {gene ?? 'this gene'} ↗
        </a>
      </div>
    </div>
  )
}

function MaveMeasurement({
  study,
  fallbackHref,
  gene,
}: {
  study: FunctionalStudy
  fallbackHref: string
  gene?: string | null
}) {
  const accession = study.score_set_urn ?? study.source_accession ?? study.citation ?? study.id
  const scoreLabel = study.score_column ? `Raw ${study.score_column}` : 'Raw score'
  const score = rawScore(study)
  const sourceHref = study.url ?? fallbackHref
  const linkLabel = study.url ? 'Open MaveDB score set ↗' : `Search MaveDB for ${gene ?? 'this gene'} ↗`

  return (
    <li
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-sm)',
        background: 'var(--bg)',
        padding: '10px 12px',
        minWidth: 0,
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: 8,
        }}
      >
        <Metric label={scoreLabel} value={score} hint={study.score_unit ?? 'source reported'} />
        <Metric
          label="Match"
          value="Exact"
          hint={readableMatchLevel(study.match_level)}
        />
        <Metric label="Interpretation" value="Uncurated" hint="no ACMG strength" />
      </div>
      <div
        style={{
          marginTop: 10,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          flexWrap: 'wrap',
          fontSize: 11,
        }}
      >
        <span
          style={{
            fontFamily: 'var(--mono)',
            color: 'var(--ink-4)',
            overflowWrap: 'anywhere',
          }}
          title="MaveDB score-set accession"
        >
          {accession}
        </span>
        <a
          href={sourceHref}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: 'var(--teal-deep)',
            textDecoration: 'none',
            borderBottom: '1px dotted var(--teal-bdr)',
          }}
        >
          {linkLabel}
        </a>
      </div>
    </li>
  )
}

function rawScore(study: FunctionalStudy): string {
  const score = study.raw_score ?? study.functional_score
  if (score == null || String(score).trim() === '') return 'reported'
  return String(score)
}

function readableMatchLevel(matchLevel: string | null | undefined): string {
  if (!matchLevel) return 'identity verified'
  return matchLevel.replace(/^exact_/, '').replaceAll('_', ' ')
}

function Metric({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint?: string
}) {
  return (
    <div style={{ minWidth: 0 }}>
      <div className="eamos-kicker">{label}</div>
      <div
        style={{
          fontFamily: 'var(--mono)',
          fontSize: 16,
          fontWeight: 600,
          color: 'var(--ink)',
          marginTop: 3,
          lineHeight: 1.1,
          maxWidth: '100%',
          overflowWrap: 'anywhere',
          wordBreak: 'break-word',
        }}
      >
        {value}
      </div>
      {hint && <div style={{ fontSize: 10, color: 'var(--ink-4)', marginTop: 2 }}>{hint}</div>}
    </div>
  )
}
