import { Card } from '@/components/ui/Card'
import { getSourceMeta } from '@/lib/sources'
import type { EvidenceSourceSummary } from '@/lib/backend'

interface EvidenceTableProps {
  evidence: EvidenceSourceSummary[]
  number?: number
  embedded?: boolean
}

const STATUS_DOT: Record<string, string> = {
  completed: 'var(--teal)',
  fallback: 'var(--warn)',
  degraded: 'var(--warn)',
  blocked: '#dc2626',
}

const DEGRADED_STATUSES = new Set(['fallback', 'fixture', 'missing', 'error', 'failed'])

function isFreshCache(ev: EvidenceSourceSummary): boolean {
  return ev.status === 'cache' || ev.cache_status === 'cache_hit'
}

function isStaleCache(ev: EvidenceSourceSummary): boolean {
  return ev.status === 'stale' || ev.cache_status === 'stale_on_failure'
}

function CachePill({ fresh, stale }: { fresh: boolean; stale: boolean }) {
  if (fresh) {
    return (
      <span
        style={{
          display: 'inline-block',
          padding: '1px 6px',
          borderRadius: 999,
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: '0.02em',
          color: 'var(--teal-deep)',
          background: 'var(--teal-tint)',
          border: '0.5px solid var(--teal)',
          lineHeight: '16px',
          verticalAlign: 'middle',
        }}
      >
        Cached
      </span>
    )
  }
  if (stale) {
    return (
      <span
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
        Stale cache
      </span>
    )
  }
  return null
}

// Flatten a summary value to a readable string. Recurses one structural
// level so nested objects render their `k=v` pairs instead of the previous
// `[object Object]`; arrays of objects (e.g. PubMed / litvar2 `articles`)
// are too deep to inline usefully and collapse to a count, while arrays of
// scalars join.
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (Array.isArray(value)) {
    const allScalar = value.every((v) => typeof v !== 'object' || v === null)
    return allScalar
      ? value.filter((v) => v !== null && v !== undefined).join(', ')
      : `${value.length} item${value.length === 1 ? '' : 's'}`
  }
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .filter(([, v]) => v !== null && v !== undefined)
      .map(([k, v]) => `${k}=${formatValue(v)}`)
      .join(', ')
  }
  return String(value)
}

function renderSummaryValue(summary: Record<string, unknown>): string {
  const parts: string[] = []
  for (const [key, raw] of Object.entries(summary)) {
    if (raw === null || raw === undefined) continue
    const formatted = formatValue(raw)
    if (formatted) parts.push(`${key}: ${formatted}`)
  }
  return parts.join(' · ')
}

export function EvidenceTable({ evidence, number, embedded }: EvidenceTableProps) {
  // AlphaMissense is on hold per user decision (2026-05-19) — filtered from the
  // evidence table; the source row stays in the payload/sample assets so this
  // is a one-line revert once re-approved. See agent_handoff DECISIONS.
  const rows = evidence.filter((ev) => ev.source?.toLowerCase() !== 'alphamissense')
  if (rows.length === 0) return null

  const degradedRows = rows.filter((ev) => DEGRADED_STATUSES.has(ev.status))

  const table = (
    <>
      <div
        style={{
          fontSize: 10.5,
          fontWeight: 700,
          color: 'var(--ink-4)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          marginTop: 18,
          marginBottom: 10,
        }}
      >
        Per-source detail
      </div>
      <table className="w-full" style={{ borderCollapse: 'collapse', fontSize: 13 }}>
        <tbody>
          {rows.map((ev, i) => {
            const meta = getSourceMeta(ev.source)
            const dot = STATUS_DOT[ev.status] ?? 'var(--ink-4)'
            const fresh = isFreshCache(ev)
            const stale = isStaleCache(ev)
            return (
              <tr
                key={i}
                style={{
                  borderBottom: i < rows.length - 1 ? '0.5px solid var(--line)' : 'none',
                }}
              >
                <td
                  style={{
                    padding: '12px 14px 12px 0',
                    width: '32%',
                    color: 'var(--ink-3)',
                    verticalAlign: 'top',
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span
                      aria-hidden
                      style={{
                        width: 7,
                        height: 7,
                        borderRadius: 999,
                        background: dot,
                        flexShrink: 0,
                      }}
                    />
                    {ev.source_url ? (
                      <a
                        href={ev.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          color: 'var(--ink-3)',
                          textDecoration: 'underline',
                          textDecorationStyle: 'dotted',
                          textUnderlineOffset: 3,
                        }}
                      >
                        {meta?.label ?? ev.source} ↗
                      </a>
                    ) : (
                      <span>{meta?.label ?? ev.source}</span>
                    )}
                    {(fresh || stale) && <CachePill fresh={fresh} stale={stale} />}
                  </div>
                  <div
                    className="mt-0.5"
                    style={{ fontSize: 11, color: 'var(--ink-4)' }}
                  >
                    {ev.status}
                  </div>
                </td>
                <td
                  style={{
                    padding: '12px 0',
                    fontFamily: 'var(--mono)',
                    fontSize: 12.5,
                    color: 'var(--ink)',
                    verticalAlign: 'top',
                  }}
                >
                  {renderSummaryValue(ev.summary) || '—'}
                  {ev.warnings.length > 0 && (
                    <div
                      className="mt-1"
                      style={{
                        fontFamily: 'var(--body)',
                        fontSize: 11,
                        color: 'var(--warn)',
                      }}
                    >
                      {ev.warnings.join(' · ')}
                    </div>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </>
  )

  const degradedBanner = degradedRows.length > 0 ? (
    <div
      style={{
        marginTop: 10,
        padding: '7px 10px',
        borderRadius: 6,
        background: 'var(--warn-tint)',
        border: '0.5px solid var(--warn-bdr)',
        fontSize: 11,
        color: 'var(--warn)',
      }}
    >
      Degraded sources:{' '}
      {degradedRows
        .map((ev) => getSourceMeta(ev.source)?.label ?? ev.source)
        .join(', ')}
    </div>
  ) : null

  if (embedded) return <>{table}{degradedBanner}</>
  return (
    <Card number={number} title="Evidence by source" meta={`${rows.length} sources`}>
      {table}
      {degradedBanner}
    </Card>
  )
}
