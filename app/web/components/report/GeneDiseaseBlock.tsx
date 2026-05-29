'use client'

import type { EvidenceSourceSummary } from '@/lib/backend'

// GeneDiseaseBlock — ClinGen Gene-Disease Validity summary for §5
// Disease & curated variants.
//
// Reads the `gene_disease` evidence row's `summary`:
//   { approved_symbol, primary_condition, disease_ids[], inheritance,
//     gene_disease_validity, mechanism, conditions[] }
//
// Conditions[] is rendered as a compact list of names with their MONDO/OMIM/
// ORPHA chips so a clinician can scan the disease landscape at a glance —
// AssociatedConditions sitting next door is patient-summary text, this is the
// curated validity ledger.

interface GeneDiseaseBlockProps {
  evidence: EvidenceSourceSummary[]
}

interface GeneDiseaseCondition {
  name: string | null
  disease_ids: string[]
  inheritance: string | null
  validity: string | null
  mechanism: string | null
  source_urls: string[]
}

function readString(raw: unknown): string | null {
  return typeof raw === 'string' && raw.trim().length > 0 ? raw.trim() : null
}

function readStringArray(raw: unknown): string[] {
  if (!Array.isArray(raw)) return []
  const out: string[] = []
  for (const item of raw) {
    const s = readString(item)
    if (s) out.push(s)
  }
  return out
}

function readCondition(raw: unknown): GeneDiseaseCondition | null {
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) return null
  const obj = raw as Record<string, unknown>
  const name = readString(obj.name)
  if (!name) return null
  return {
    name,
    disease_ids: readStringArray(obj.disease_ids),
    inheritance: readString(obj.inheritance),
    validity: readString(obj.validity),
    mechanism: readString(obj.mechanism),
    source_urls: readStringArray(obj.source_urls),
  }
}

function validityTone(validity: string | null) {
  if (!validity) return { bg: 'var(--bg-soft)', bd: 'var(--line)', ink: 'var(--ink-3)' }
  const v = validity.toLowerCase()
  if (v.includes('definitive') || v.includes('strong'))
    return { bg: 'var(--teal-tint)', bd: 'var(--teal-deep)', ink: 'var(--teal-deep)' }
  if (v.includes('moderate') || v.includes('limited'))
    return { bg: 'var(--bg-soft)', bd: 'var(--line)', ink: 'var(--ink-2)' }
  if (v.includes('disputed') || v.includes('refuted'))
    return { bg: 'var(--warn-tint)', bd: 'var(--warn-bdr)', ink: 'var(--warn)' }
  return { bg: 'var(--bg-soft)', bd: 'var(--line)', ink: 'var(--ink-3)' }
}

export function GeneDiseaseBlock({ evidence }: GeneDiseaseBlockProps) {
  const row = evidence.find((e) => e.source?.toLowerCase() === 'gene_disease')
  if (!row || !row.summary) return null
  const summary = row.summary as Record<string, unknown>

  const approvedSymbol = readString(summary.approved_symbol)
  const primaryCondition = readString(summary.primary_condition)
  const inheritance = readString(summary.inheritance)
  const validity = readString(summary.gene_disease_validity)
  const mechanism = readString(summary.mechanism)
  const conditions: GeneDiseaseCondition[] = Array.isArray(summary.conditions)
    ? summary.conditions
        .map(readCondition)
        .filter((c): c is GeneDiseaseCondition => c !== null)
    : []

  if (!approvedSymbol && !primaryCondition && !mechanism && conditions.length === 0) {
    return null
  }

  const tone = validityTone(validity)

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
        gap: 12,
      }}
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="eamos-kicker">
          ClinGen gene-disease validity
        </span>
        {validity && (
          <span
            style={{
              padding: '2px 8px',
              borderRadius: 999,
              fontSize: 11,
              fontWeight: 600,
              background: tone.bg,
              border: `0.5px solid ${tone.bd}`,
              color: tone.ink,
              textTransform: 'capitalize',
            }}
          >
            {validity}
          </span>
        )}
      </div>

      {(approvedSymbol || primaryCondition || inheritance) && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'auto 1fr',
            columnGap: 12,
            rowGap: 4,
            fontSize: 12.5,
            color: 'var(--ink-2)',
            margin: 0,
          }}
        >
          {approvedSymbol && (
            <>
              <span style={{ color: 'var(--ink-4)' }}>Gene</span>
              <span style={{ fontFamily: 'var(--mono)', fontWeight: 600 }}>{approvedSymbol}</span>
            </>
          )}
          {primaryCondition && (
            <>
              <span style={{ color: 'var(--ink-4)' }}>Primary condition</span>
              <span>{primaryCondition}</span>
            </>
          )}
          {inheritance && (
            <>
              <span style={{ color: 'var(--ink-4)' }}>Inheritance</span>
              <span style={{ fontFamily: 'var(--mono)' }}>{inheritance}</span>
            </>
          )}
        </div>
      )}

      {mechanism && (
        <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.55, color: 'var(--ink-2)' }}>
          {mechanism}
        </p>
      )}

      {conditions.length > 0 && (
        <div>
          <div className="eamos-kicker" style={{ marginBottom: 6 }}>
            Curated conditions ({conditions.length})
          </div>
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {conditions.map((c, i) => {
              const condTone = validityTone(c.validity)
              return (
                <li
                  key={`${c.name}-${i}`}
                  style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    gap: 8,
                    flexWrap: 'wrap',
                    fontSize: 12,
                    color: 'var(--ink-2)',
                  }}
                >
                  <span style={{ fontWeight: 600 }}>{c.name}</span>
                  {c.inheritance && (
                    <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink-4)' }}>
                      {c.inheritance}
                    </span>
                  )}
                  {c.validity && (
                    <span
                      style={{
                        padding: '0 6px',
                        borderRadius: 999,
                        fontSize: 10.5,
                        fontWeight: 600,
                        background: condTone.bg,
                        border: `0.5px solid ${condTone.bd}`,
                        color: condTone.ink,
                        textTransform: 'capitalize',
                      }}
                    >
                      {c.validity}
                    </span>
                  )}
                  {c.disease_ids.slice(0, 3).map((id) => (
                    <span
                      key={id}
                      style={{
                        fontFamily: 'var(--mono)',
                        fontSize: 10.5,
                        color: 'var(--ink-4)',
                      }}
                    >
                      {id}
                    </span>
                  ))}
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {row.warnings && row.warnings.length > 0 && (
        <div style={{ fontSize: 11, color: 'var(--ink-4)' }}>
          {row.warnings.join(' · ')}
        </div>
      )}
    </div>
  )
}
