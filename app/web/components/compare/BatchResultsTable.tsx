'use client'

import { useMemo } from 'react'
import Link from 'next/link'
import { reportHrefForQuery } from '@/lib/variant-search'
import { CopyButton } from '@/components/ui/CopyButton'
import type { BatchResult } from '@/lib/backend'

/**
 * Server-computed batch results table. Rendered once a real /batch job completes
 * and returns BatchResult[] (gene · HGVS · ClinVar · ACMG · gnomAD AF · report
 * link) — distinct from the client-side scope preview (VariantTable), which
 * stands in offline / mock. Spec: Phase 1b live wiring.
 */

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
  const headers = ['Gene', 'HGVS (c.)', 'HGVS (p.)', 'ClinVar', 'ACMG', 'gnomAD AF']
  const cells = results.map((r) => [
    r.gene ?? '',
    r.hgvs_c ?? r.variant_key,
    r.hgvs_p ?? '',
    r.clinvar_verdict ?? '',
    r.acmg_classification ?? '',
    r.gnomad_af == null ? '' : String(r.gnomad_af),
  ])
  const text = [headers, ...cells].map((row) => row.join('\t')).join('\n')
  const thead = `<tr>${headers.map((h) => `<th>${escHtml(h)}</th>`).join('')}</tr>`
  const tbody = cells.map((row) => `<tr>${row.map((c) => `<td>${escHtml(c)}</td>`).join('')}</tr>`).join('')
  return { html: `<table><thead>${thead}</thead><tbody>${tbody}</tbody></table>`, text }
}

export function BatchResultsTable({ results }: { results: BatchResult[] }) {
  const payload = useMemo(() => copyPayload(results), [results])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-4)' }}>
          {results.length} annotated · server-computed
        </span>
        <CopyButton text={payload} label="Copy results for spreadsheet" />
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
            {results.map((r, i) => {
              const href = reportLink(r)
              return (
                <tr key={`${r.variant_key}-${i}`} style={{ borderTop: '0.5px solid var(--line)' }}>
                  <Td style={{ textAlign: 'right', color: 'var(--ink-4)', fontFamily: 'var(--mono)' }}>{i + 1}</Td>
                  <Td style={{ fontWeight: 600, color: 'var(--ink)' }}>{r.gene ?? '—'}</Td>
                  <Td style={{ fontFamily: 'var(--mono)', color: 'var(--ink-2)' }}>
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
