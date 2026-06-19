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

// ClinGen Gene-Disease Validity — full 8-tier scale, mapped onto the shared
// classification ramp so confidence reads at a glance: high (green/teal) →
// low (yellow) → contradicting (orange/red) → neutral (grey/blue).
function validityTone(validity: string | null) {
  const neutral = { bg: 'var(--cls-na-bg)', bd: 'var(--cls-na-bdr)', ink: 'var(--cls-na-text)' }
  if (!validity) return neutral
  const v = validity.toLowerCase()
  if (v.includes('definitive'))
    return { bg: 'var(--teal-tint)', bd: 'var(--teal-bdr)', ink: 'var(--teal-deep)' }
  if (v.includes('strong'))
    return { bg: 'var(--cls-ben-bg)', bd: 'var(--cls-ben-bdr)', ink: 'var(--cls-ben-text)' }
  if (v.includes('moderate'))
    return { bg: 'var(--cls-lben-bg)', bd: 'var(--cls-lben-bdr)', ink: 'var(--cls-lben-text)' }
  if (v.includes('limited'))
    return { bg: 'var(--cls-vus-bg)', bd: 'var(--cls-vus-bdr)', ink: 'var(--cls-vus-text)' }
  if (v.includes('disputed'))
    return { bg: 'var(--cls-lpath-bg)', bd: 'var(--cls-lpath-bdr)', ink: 'var(--cls-lpath-text)' }
  if (v.includes('refuted'))
    return { bg: 'var(--cls-path-bg)', bd: 'var(--cls-path-bdr)', ink: 'var(--cls-path-text)' }
  if (v.includes('animal'))
    return { bg: 'var(--info-bg)', bd: 'var(--info-bdr)', ink: 'var(--info-text)' }
  // "No Known Disease Relationship" and anything unrecognised → neutral grey.
  return neutral
}

// Resolve a CURIE-style disease id (MONDO:0008765, OMIM:204100, ORPHA:65,
// MedGen:C1859844, MedGenUID:348473) to its canonical ontology page.
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

// MONDO leads (cross-ontology anchor), then OMIM/ORPHA/MedGen.
function orderDiseaseIds(ids: string[]): string[] {
  const rank = (id: string) => {
    const p = id.split(':')[0].toUpperCase()
    return p === 'MONDO' ? 0 : p === 'OMIM' ? 1 : p === 'ORPHA' ? 2 : p === 'MEDGEN' ? 3 : 4
  }
  // de-dupe while preserving the ranked order
  const seen = new Set<string>()
  return [...ids]
    .filter((id) => (seen.has(id) ? false : (seen.add(id), true)))
    .sort((a, b) => rank(a) - rank(b))
}

function titleCase(value: string): string {
  return value.replace(/\b\w/g, (c) => c.toUpperCase())
}

const GENCC_TIP =
  'GenCC aggregates gene–disease validity assertions from member submitters (ClinGen, Genomics England PanelApp, Orphanet, Invitae, and others). Consensus = the agreed classification across them.'
const MONDO_TIP =
  'MONDO — the cross-ontology disease identifier that unifies OMIM, Orphanet and MedGen. Opens the Monarch Initiative page.'

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
  const orderedIds = orderDiseaseIds(readStringArray(summary.disease_ids))
  const genccAssertions = readStringArray(summary.gencc_assertions)
  const genccSubmitters = readStringArray(summary.gencc_submitters)
  const genccCount =
    typeof summary.gencc_assertion_count === 'number' && Number.isFinite(summary.gencc_assertion_count)
      ? summary.gencc_assertion_count
      : genccAssertions.length
  const genccConsensus = genccAssertions[0] ?? null

  return (
    <div
      style={{
        marginTop: 'var(--report-subpanel-gap)',
        padding: 'var(--report-subpanel-pad)',
        background: 'var(--bg-soft)',
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="eamos-kicker">Gene-disease validity</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {validity && (
            <span
              title="ClinGen Gene-Disease Validity classification (8-tier confidence scale)."
              style={{
                padding: '2px 8px',
                borderRadius: 999,
                fontSize: 11,
                fontWeight: 600,
                background: tone.bg,
                border: `0.5px solid ${tone.bd}`,
                color: tone.ink,
                textTransform: 'capitalize',
                cursor: 'help',
              }}
            >
              ClinGen · {validity}
            </span>
          )}
          <span
            title={GENCC_TIP}
            style={{
              padding: '2px 8px',
              borderRadius: 999,
              fontSize: 11,
              fontWeight: 600,
              background: 'var(--bg)',
              border: `0.5px solid ${genccConsensus ? tone.bd : 'var(--line)'}`,
              color: genccConsensus ? tone.ink : 'var(--ink-4)',
              cursor: 'help',
            }}
          >
            {genccConsensus
              ? `GenCC · ${titleCase(genccConsensus)} · ${genccCount} assertion${genccCount === 1 ? '' : 's'}`
              : 'GenCC · unavailable'}
          </span>
        </span>
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

      {orderedIds.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 6 }}>
          <span className="eamos-kicker" style={{ marginRight: 2 }}>Disease IDs</span>
          {orderedIds.map((id) => {
            const href = diseaseIdLink(id)
            const isMondo = id.toUpperCase().startsWith('MONDO')
            const chipStyle: React.CSSProperties = {
              fontFamily: 'var(--mono)',
              fontSize: 10.5,
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: 999,
              border: `0.5px solid ${isMondo ? 'var(--teal-bdr)' : 'var(--line)'}`,
              background: isMondo ? 'var(--teal-tint)' : 'var(--bg)',
              color: isMondo ? 'var(--teal-deep)' : 'var(--ink-3)',
              textDecoration: 'none',
              whiteSpace: 'nowrap',
            }
            return href ? (
              <a
                key={id}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                style={chipStyle}
                title={isMondo ? MONDO_TIP : `Open ${id}`}
              >
                {id} ↗
              </a>
            ) : (
              <span key={id} style={chipStyle}>
                {id}
              </span>
            )
          })}
        </div>
      )}

      {mechanism && (
        <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.55, color: 'var(--ink-2)' }}>
          {mechanism}
        </p>
      )}

      {genccSubmitters.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
          <span className="eamos-kicker">GenCC submitters</span>
          {genccSubmitters.slice(0, 6).map((submitter) => (
            <span
              key={submitter}
              style={{
                fontSize: 10.5,
                color: 'var(--ink-3)',
                border: '0.5px solid var(--line)',
                borderRadius: 999,
                padding: '2px 8px',
                background: 'var(--bg)',
              }}
            >
              {submitter}
            </span>
          ))}
        </div>
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
