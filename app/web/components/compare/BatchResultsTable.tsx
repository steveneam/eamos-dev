'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { reportHrefForQuery } from '@/lib/variant-search'
import { CopyButton } from '@/components/ui/CopyButton'
import type { BatchResult } from '@/lib/backend'
import { sortByActionable, summarizeCohort } from '@/lib/batch-summary'
import { CohortSummary } from './CohortSummary'

/**
 * Server-computed batch results dashboard. Rendered once a real /batch job
 * completes and returns BatchResult[]. Adds the cohort summary (spec §5.5b)
 * above an actionable-first table: P/LP pinned to top, a post-lookup gnomAD-AF
 * filter, and a TSV export. Distinct from the client-side scope preview
 * (VariantTable) that stands in offline / mock.
 */

const AF_OPTIONS: { label: string; value: number | null }[] = [
  { label: 'All', value: null },
  { label: '≤ 5%', value: 0.05 },
  { label: '≤ 1%', value: 0.01 },
  { label: '≤ 0.1%', value: 0.001 },
]

function verdictColor(v?: string | null): string {
  const s = (v ?? '').toLowerCase()
  if (!s) return 'var(--ink-4)'
  if (/pathogenic/.test(s) && !/benign/.test(s)) return 'var(--err)'
  if (/benign/.test(s)) return 'var(--teal-deep)'
  return 'var(--ink-3)' // VUS / uncertain / conflicting
}

function reportLink(r: BatchResult): string | null {
  if (r.gene && r.hgvs_c) return reportHrefForQuery(`${r.gene} ${r.hgvs_c}`)
  return reportHrefForQuery(r.variant_key)
}

function fmtAf(af?: number | null): string {
  if (af == null) return '—'
  if (af === 0) return '0'
  if (af < 0.0001) return af.toExponential(1)
  return af.toFixed(4)
}

function escHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function copyPayload(results: BatchResult[]): { html: string; text: string } {
  const headers = ['Gene', 'HGVS (c.)', 'HGVS (p.)', 'ClinVar', 'ACMG', 'gnomAD AF', 'Variant key']
  const cells = results.map((r) => [
    r.gene ?? '',
    r.hgvs_c ?? r.variant_key,
    r.hgvs_p ?? '',
    r.clinvar_verdict ?? '',
    r.acmg_classification ?? '',
    r.gnomad_af == null ? '' : String(r.gnomad_af),
    r.variant_key,
  ])
  const text = [headers, ...cells].map((row) => row.join('\t')).join('\n')
  const thead = `<tr>${headers.map((h) => `<th>${escHtml(h)}</th>`).join('')}</tr>`
  const tbody = cells.map((row) => `<tr>${row.map((c) => `<td>${escHtml(c)}</td>`).join('')}</tr>`).join('')
  return { html: `<table><thead>${thead}</thead><tbody>${tbody}</tbody></table>`, text }
}

function downloadTsv(results: BatchResult[]): void {
  const { text } = copyPayload(results)
  const blob = new Blob([text], { type: 'text/tab-separated-values;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `eamos-batch-${results.length}-variants.tsv`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export function BatchResultsTable({
  results,
  panelGenes,
  panelLabel,
}: {
  results: BatchResult[]
  /** Active panel gene symbols (union, any case) → panel-coverage card. */
  panelGenes?: string[]
  panelLabel?: string
}) {
  const [afMax, setAfMax] = useState<number | null>(null)

  const summary = useMemo(() => summarizeCohort(results, panelGenes), [results, panelGenes])
  const sorted = useMemo(() => sortByActionable(results), [results])
  const visible = useMemo(
    () => (afMax == null ? sorted : sorted.filter((r) => r.gnomad_af == null || r.gnomad_af <= afMax)),
    [sorted, afMax],
  )
  const hidden = sorted.length - visible.length
  const payload = useMemo(() => copyPayload(visible), [visible])

  return (
    <div>
      <CohortSummary summary={summary} panelLabel={panelLabel} />

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap',
          marginBottom: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-4)' }}>
            {hidden > 0 ? `${visible.length} of ${sorted.length}` : `${sorted.length}`} annotated · server-computed
          </span>
          <span aria-hidden style={{ color: 'var(--line-2)' }}>·</span>
          <span style={{ fontSize: 11, color: 'var(--ink-4)' }}>gnomAD AF</span>
          <div role="group" aria-label="Filter by gnomAD allele frequency" style={{ display: 'inline-flex', gap: 4 }}>
            {AF_OPTIONS.map((opt) => {
              const active = afMax === opt.value
              return (
                <button
                  key={opt.label}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setAfMax(opt.value)}
                  style={{
                    padding: '3px 9px',
                    borderRadius: 7,
                    border: `0.5px solid ${active ? 'var(--teal-bdr)' : 'var(--line-2)'}`,
                    background: active ? 'var(--teal-tint)' : 'var(--bg)',
                    color: active ? 'var(--teal-deep)' : 'var(--ink-3)',
                    fontSize: 11,
                    fontWeight: 600,
                    fontFamily: 'var(--mono)',
                    cursor: 'pointer',
                  }}
                >
                  {opt.label}
                </button>
              )
            })}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <CopyButton text={payload} label="Copy results for spreadsheet" />
          <button
            type="button"
            onClick={() => downloadTsv(visible)}
            disabled={visible.length === 0}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '5px 11px',
              borderRadius: 8,
              border: '0.5px solid var(--line-2)',
              background: 'var(--bg)',
              color: 'var(--ink-2)',
              fontSize: 11.5,
              fontWeight: 600,
              cursor: visible.length === 0 ? 'not-allowed' : 'pointer',
              opacity: visible.length === 0 ? 0.5 : 1,
            }}
          >
            <span aria-hidden>↓</span> Download TSV
          </button>
        </div>
      </div>

      <div style={{ maxHeight: 560, overflow: 'auto', border: '0.5px solid var(--line)', borderRadius: 14 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              <Th style={{ width: 44, textAlign: 'right' }}>#</Th>
              <Th>Gene</Th>
              <Th>HGVS</Th>
              <Th>ClinVar</Th>
              <Th>ACMG</Th>
              <Th style={{ textAlign: 'right' }}>gnomAD AF</Th>
              <Th style={{ textAlign: 'right' }}>Report</Th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r, i) => {
              const href = reportLink(r)
              return (
                <tr key={`${r.variant_key}-${i}`} style={{ borderTop: '0.5px solid var(--line)' }}>
                  <Td style={{ textAlign: 'right', color: 'var(--ink-4)', fontFamily: 'var(--mono)' }}>{i + 1}</Td>
                  <Td style={{ fontWeight: 600, color: 'var(--ink)' }}>{r.gene ?? '—'}</Td>
                  <Td style={{ fontFamily: 'var(--body)', fontVariantNumeric: 'tabular-nums', color: 'var(--ink-2)' }}>
                    {r.hgvs_c ?? r.variant_key}
                    {r.hgvs_p ? <span style={{ color: 'var(--ink-4)' }}> · {r.hgvs_p}</span> : null}
                  </Td>
                  <Td style={{ color: verdictColor(r.clinvar_verdict), fontWeight: 500 }}>{r.clinvar_verdict ?? '—'}</Td>
                  <Td style={{ color: verdictColor(r.acmg_classification) }}>{r.acmg_classification ?? '—'}</Td>
                  <Td style={{ textAlign: 'right', fontFamily: 'var(--mono)', color: 'var(--ink-3)' }}>{fmtAf(r.gnomad_af)}</Td>
                  <Td style={{ textAlign: 'right' }}>
                    {href ? (
                      <Link href={href} style={{ fontSize: 12, fontWeight: 600, color: 'var(--teal-deep)', textDecoration: 'none' }}>
                        Open report →
                      </Link>
                    ) : (
                      <span style={{ fontSize: 12, color: 'var(--ink-5)' }}>—</span>
                    )}
                  </Td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Th({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <th
      scope="col"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 1,
        textAlign: 'left',
        padding: '10px 14px',
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        color: 'var(--ink-4)',
        background: 'var(--bg-soft)',
        ...style,
      }}
    >
      {children}
    </th>
  )
}

function Td({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <td style={{ padding: '10px 14px', verticalAlign: 'top', ...style }}>{children}</td>
}
