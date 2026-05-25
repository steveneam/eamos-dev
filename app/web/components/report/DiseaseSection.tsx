import { Card } from '@/components/ui/Card'
import { ClassificationBadge } from '@/components/ui/ClassificationBadge'
import type { DiseaseMechanismSection, ReportExtractionSectionTarget, ReportPayload } from '@/lib/backend'

interface DiseaseSectionProps {
  payload: ReportPayload
  number?: number
  embedded?: boolean
  sectionTarget?: ReportExtractionSectionTarget | null
}

interface Field {
  label: string
  value: string | null | undefined
}

function deriveClassification(acmg: string | null | undefined): string | null {
  if (!acmg) return null
  const normalized = acmg.toLowerCase()
  if (normalized.includes('unavailable') || normalized.includes('not found') || normalized === 'none') return null
  const first = acmg.split(/[\u2014\-:]/)[0]?.trim()
  return first || null
}

function formatWarning(value: string): string {
  return value.replace(/_/g, ' ').replace(/:/g, ': ')
}

function typedFields(section: DiseaseMechanismSection): Field[] {
  return [
    { label: 'Primary condition', value: section.primary_condition },
    {
      label: 'Disease identifiers',
      value: (section.disease_ids ?? []).length > 0 ? section.disease_ids.join(' | ') : null,
    },
    { label: 'Mode of inheritance', value: section.inheritance },
    { label: 'Clinical penetrance', value: section.penetrance },
    { label: 'Gene-disease validity', value: section.gene_disease_validity },
    { label: 'Mechanism', value: section.mechanism },
  ]
}

export function DiseaseSection({ payload, number, embedded, sectionTarget }: DiseaseSectionProps) {
  const typedDisease = payload.report_profile?.disease_mechanism ?? null
  const fields: Field[] = typedDisease
    ? typedFields(typedDisease)
    : [
        { label: 'Associated disease', value: payload.clinical_phenotype },
        { label: 'Clinical integration', value: payload.clinical_integration },
        { label: 'Expected symptoms', value: payload.expected_symptoms },
        { label: 'Recommendations', value: payload.recommendations },
      ]

  const populated = fields.filter((f) => f.value?.trim())
  const warnings = typedDisease?.warnings ?? []
  const classification = typedDisease
    ? null
    : deriveClassification(
        payload.report_profile?.header?.classification ??
          payload.report_profile?.acmg_worksheet?.classification ??
          payload.acmg_classification,
      )
  const rawClassificationText =
    !typedDisease && payload.acmg_classification && deriveClassification(payload.acmg_classification)
      ? payload.acmg_classification
      : null

  if (populated.length === 0 && !classification && warnings.length === 0) return null

  const body = (
    <>
      {classification && (
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <span
            className="uppercase"
            style={{
              fontSize: 10.5,
              fontWeight: 600,
              letterSpacing: '0.08em',
              color: 'var(--ink-4)',
            }}
          >
            ACMG classification
          </span>
          <ClassificationBadge classification={classification} />
          {rawClassificationText && (
            <span
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 11.5,
                color: 'var(--ink-3)',
              }}
            >
              {rawClassificationText}
            </span>
          )}
        </div>
      )}

      {sectionTarget?.match_level && (
        <div className="mb-4 flex flex-wrap gap-2">
          <span
            style={{
              border: '0.5px solid var(--line)',
              borderRadius: 999,
              background: 'var(--bg-soft)',
              color: 'var(--ink-3)',
              padding: '3px 8px',
              fontSize: 10.5,
              fontWeight: 700,
            }}
          >
            {formatWarning(sectionTarget.match_level)}
          </span>
          {sectionTarget.warnings.slice(0, 2).map((warning) => (
            <span
              key={warning}
              style={{
                border: '0.5px solid var(--warn-bdr)',
                background: 'var(--warn-tint)',
                color: '#633806',
                borderRadius: 999,
                padding: '3px 8px',
                fontSize: 10.5,
                fontWeight: 700,
              }}
            >
              {formatWarning(warning)}
            </span>
          ))}
        </div>
      )}

      {populated.length > 0 ? (
        <div className="flex flex-col gap-3.5">
          {populated.map((field) => (
            <div key={field.label}>
              <div
                className="mb-1 uppercase"
                style={{
                  fontSize: 10.5,
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  color: 'var(--ink-4)',
                }}
              >
                {field.label}
              </div>
              <p
                style={{
                  margin: 0,
                  fontSize: 13.5,
                  lineHeight: 1.65,
                  color: 'var(--ink-2)',
                }}
              >
                {field.value}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: 0 }}>
          Disease mechanism details are not available for this lookup.
        </p>
      )}

      {warnings.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {warnings.slice(0, 3).map((warning) => (
            <span
              key={warning}
              style={{
                border: '0.5px solid var(--warn-bdr)',
                background: 'var(--warn-tint)',
                color: '#633806',
                borderRadius: 7,
                padding: '5px 8px',
                fontSize: 10.5,
                fontWeight: 600,
                overflowWrap: 'anywhere',
              }}
            >
              {formatWarning(warning)}
            </span>
          ))}
        </div>
      )}
    </>
  )

  if (embedded) return body
  return (
    <Card number={number} title="Disease mechanism & inheritance">
      {body}
    </Card>
  )
}
