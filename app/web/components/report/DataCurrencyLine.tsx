// DataCurrencyLine — a small, honest "clinical data current as of" line under
// the variant header. Trust-building data-currency disclosure (Varsome/Franklin
// both do this). It is sourced, in priority order, from:
//   1. the per-asset freshness block (backend Phase 0.1 — `materialized_at` +
//      `status`), when present, or
//   2. the real per-source `fetched_at` timestamps already carried on each
//      evidence row (no fabricated dates).
// It renders nothing when there is no real date to show, so it never invents
// currency it cannot prove.

import type { LookupResponse, ReportDataCurrency, SourceFreshness } from '@/lib/backend'

interface DataCurrencyLineProps {
  data: LookupResponse
  /** Backend Phase 0.1 per-asset freshness block. May be absent on older payloads. */
  freshness?: ReportDataCurrency | null
}

// The clinical sources we surface, in display order. Keys match the lowercased
// `source` on evidence rows and the `source` on a freshness entry.
const CLINICAL_SOURCES: { key: string; label: string }[] = [
  { key: 'clinvar', label: 'ClinVar' },
  { key: 'clingen', label: 'ClinGen' },
]

const STATUS_COLOR: Record<string, string> = {
  fresh: 'var(--ok, #2f9e6f)',
  stale: 'var(--warn-text)',
  overdue: 'var(--bad, #c2453d)',
  unknown: 'var(--ink-5)',
}

function formatDate(value: string): string | null {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
}

// Latest real `fetched_at` across the evidence rows for a given source key.
function latestFetchForSource(data: LookupResponse, key: string): string | null {
  const dates = (data.evidence ?? [])
    .filter((row) => (row.source ?? '').toLowerCase() === key)
    .map((row) => row.fetched_at)
    .filter((v): v is string => typeof v === 'string' && v.length > 0)
    .sort()
  return dates.at(-1) ?? null
}

interface ResolvedSource {
  label: string
  date: string
  status?: string | null
  detail: string
}

function resolveSource(
  data: LookupResponse,
  freshness: ReportDataCurrency | null | undefined,
  key: string,
  label: string,
): ResolvedSource | null {
  const live: SourceFreshness | undefined = freshness?.sources?.find(
    (s) => (s.source ?? '').toLowerCase() === key,
  )
  // Prefer the materialized "as of" from the freshness block; fall back to the
  // real fetched_at on evidence rows.
  const rawDate = live?.materialized_at ?? live?.upstream_released_at ?? latestFetchForSource(data, key)
  if (!rawDate) return null
  const date = formatDate(rawDate)
  if (!date) return null
  const status = live?.status ?? null
  const detailBits = [`${label} ${date}`]
  if (live?.tier) detailBits.push(`${live.tier} tier`)
  if (status) detailBits.push(status)
  if (typeof live?.staleness_days === 'number') detailBits.push(`${live.staleness_days}d since refresh`)
  return { label, date, status, detail: detailBits.join(' · ') }
}

export function DataCurrencyLine({ data, freshness }: DataCurrencyLineProps) {
  const resolved = CLINICAL_SOURCES.map(({ key, label }) =>
    resolveSource(data, freshness, key, label),
  ).filter((s): s is ResolvedSource => s !== null)

  if (resolved.length === 0) return null

  const title = `Clinical data currency — ${resolved.map((s) => s.detail).join(' · ')}`

  return (
    <div
      role="note"
      title={title}
      aria-label={title}
      style={{
        display: 'flex',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '4px 8px',
        fontSize: 10.5,
        lineHeight: 1.4,
        color: 'var(--ink-4)',
      }}
    >
      <svg
        width="11"
        height="11"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        style={{ flex: '0 0 auto' }}
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </svg>
      <span style={{ color: 'var(--ink-3)', fontWeight: 600 }}>Clinical data current as of</span>
      {resolved.map((s, i) => (
        <span key={s.label} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          {s.status && (
            <span
              aria-hidden="true"
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: STATUS_COLOR[s.status] ?? 'var(--ink-5)',
                flex: '0 0 auto',
              }}
            />
          )}
          <span>
            {s.label} <span style={{ color: 'var(--ink-3)' }}>{s.date}</span>
          </span>
          {i < resolved.length - 1 && <span style={{ color: 'var(--ink-5)' }}>·</span>}
        </span>
      ))}
    </div>
  )
}
