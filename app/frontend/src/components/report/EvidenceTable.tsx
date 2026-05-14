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

function renderSummaryValue(summary: Record<string, unknown>): string {
  const parts: string[] = []
  for (const [key, raw] of Object.entries(summary)) {
    if (raw === null || raw === undefined) continue
    if (typeof raw === 'object') {
      const flat = Object.entries(raw as Record<string, unknown>)
        .filter(([, v]) => v !== null && v !== undefined)
        .map(([k, v]) => `${k}=${v}`)
        .join(', ')
      if (flat) parts.push(`${key}: ${flat}`)
    } else {
      parts.push(`${key}: ${raw}`)
    }
  }
  return parts.join(' · ')
}

export function EvidenceTable({ evidence, number, embedded }: EvidenceTableProps) {
  if (evidence.length === 0) return null

  const table = (
    <table className="w-full" style={{ borderCollapse: 'collapse', fontSize: 13 }}>
        <tbody>
          {evidence.map((ev, i) => {
            const meta = getSourceMeta(ev.source)
            const dot = STATUS_DOT[ev.status] ?? 'var(--ink-4)'
            return (
              <tr
                key={i}
                style={{
                  borderBottom: i < evidence.length - 1 ? '0.5px solid var(--line)' : 'none',
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
  )

  if (embedded) return table
  return (
    <Card number={number} title="Evidence by source" meta={`${evidence.length} sources`}>
      {table}
    </Card>
  )
}
