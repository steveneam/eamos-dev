import { Disclosure } from '@/components/ui/Disclosure'
import type { AcmgCriteriaScaffold } from '@/lib/backend'
import { AcmgGrid } from './AcmgGrid'

interface AcmgCriteriaFoldProps {
  data?: AcmgCriteriaScaffold | null
}

export function AcmgCriteriaFold({ data }: AcmgCriteriaFoldProps) {
  if (!data) {
    return (
      <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: 0 }}>
        No ACMG criteria scaffold available for this variant.
      </p>
    )
  }

  const intro = data.intro
  const note = data.note

  const met = data.criteria.filter((c) => c.verdict === 'met').length
  const unmet = data.criteria.length - met

  return (
    <Disclosure
      kicker="ACMG criteria"
      showLabel="Show all 28 criteria"
      hideLabel="Hide criteria"
      summary={`${met} met · ${unmet} unmet · ACMG 2015 + 2022 PP3/BP4`}
    >
      {intro && (
        <p
          style={{
            margin: '0 0 14px',
            fontSize: 12.5,
            lineHeight: 1.6,
            color: 'var(--ink-3)',
          }}
        >
          {intro.split(/\b(This is supporting evidence, not a classification\.)\b/).map((part, i) =>
            part === 'This is supporting evidence, not a classification.' ? (
              <strong key={i} style={{ color: 'var(--ink)' }}>{part}</strong>
            ) : (
              part
            ),
          )}
        </p>
      )}

      <AcmgGrid criteria={data.criteria} />

      {note && (
        <div className="acmg-note">
          <strong>Note:</strong> {note}
        </div>
      )}
    </Disclosure>
  )
}
