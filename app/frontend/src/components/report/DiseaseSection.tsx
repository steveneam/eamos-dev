import { Card } from '@/components/ui/Card'
import { ClassificationBadge } from '@/components/ui/ClassificationBadge'
import type { ReportPayload } from '@/lib/backend'

interface DiseaseSectionProps {
  payload: ReportPayload
  number?: number
  embedded?: boolean
}

interface Field {
  label: string
  value: string | null | undefined
}

function deriveClassification(acmg: string | null | undefined): string | null {
  if (!acmg) return null
  const first = acmg.split(/[—\-:]/)[0]?.trim()
  return first || null
}

export function DiseaseSection({ payload, number, embedded }: DiseaseSectionProps) {
  const fields: Field[] = [
    { label: 'Associated disease', value: payload.clinical_phenotype },
    { label: 'Clinical integration', value: payload.clinical_integration },
    { label: 'Expected symptoms', value: payload.expected_symptoms },
    { label: 'Recommendations', value: payload.recommendations },
  ]

  const populated = fields.filter((f) => f.value?.trim())
  const classification = deriveClassification(payload.acmg_classification)

  if (populated.length === 0 && !classification) return null

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
            ACMG verdict
          </span>
          <ClassificationBadge classification={classification} />
          {payload.acmg_classification && (
            <span
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 11.5,
                color: 'var(--ink-3)',
              }}
            >
              {payload.acmg_classification}
            </span>
          )}
        </div>
      )}

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
    </>
  )

  if (embedded) return body
  return (
    <Card number={number} title="Disease, classification & recommendations">
      {body}
    </Card>
  )
}
