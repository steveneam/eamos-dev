import type {
  AssociatedCondition as AssociatedConditionData,
  EvidenceLevel,
} from '@/lib/backend'

type EvLevel = 'def' | 'strong' | 'mod' | 'lim'

interface AssociatedConditionsProps {
  data?: AssociatedConditionData[] | null
}

const EV_ABBREV: Record<EvidenceLevel, EvLevel> = {
  definitive: 'def',
  strong: 'strong',
  moderate: 'mod',
  limited: 'lim',
}

const EV_LABEL: Record<EvidenceLevel, string> = {
  definitive: 'Definitive',
  strong: 'Strong',
  moderate: 'Moderate',
  limited: 'Limited',
}

export function AssociatedConditions({ data }: AssociatedConditionsProps) {
  if (!data || data.length === 0) {
    return (
      <div style={{ marginTop: 22 }}>
        <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: 0 }}>
          No associated conditions recorded for this gene.
        </p>
      </div>
    )
  }

  const sub = `${data.length} conditions · OMIM + GenCC + ClinGen + MONDO`

  return (
    <div style={{ marginTop: 22 }}>
      <div className="vardist-title" style={{ marginBottom: 4 }}>
        Associated conditions
        <span className="vardist-sub">{sub}</span>
      </div>
      <div className="conds">
        {data.map((c, i) => (
          <div key={i} className="cond">
            <div className="cond-cases">
              <span className="n">{c.case_count}</span>
              <span className="l">cases</span>
            </div>
            <div className="cond-main">
              <div className="name">{c.name}</div>
              <div className="meta">
                <span className="meta-tag">
                  {c.db_tag_bold && <b>{c.db_tag_bold}</b>}
                  {c.db_tag_bold ? ` ${c.db_tag}` : c.db_tag || c.source}
                </span>
                <span className="ev-level">
                  <span className={`ev-bars ${EV_ABBREV[c.evidence_level]}`}>
                    <span /><span /><span />
                  </span>
                  {EV_LABEL[c.evidence_level]}
                </span>
                <span className="src">{c.source_list}</span>
              </div>
            </div>
            <div className="cond-inherit">{c.inheritance}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
