'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { openAuthMenu } from '@/components/auth/AuthMenu'
import { TopNav } from '@/components/layout/TopNav'
import { ModePill } from '@/components/layout/ModePill'
import { WorkRail } from '@/components/layout/WorkRail'
import { RailFoot } from '@/components/layout/RailFoot'
import { LibrarySection } from '@/components/library/LibrarySection'
import { EamosSearch } from '@/components/landing/EamosSearch'
import { CandidateCard, formatToken } from '@/components/report/CandidateCard'
import { PaperAiPanel } from './PaperAiPanel'
import { saveVariant } from '@/lib/variant-library'
import { reportHrefForQuery } from '@/lib/variant-search'
import { clearPaperTarget, readPaperTarget } from '@/lib/report-workflow'
import { stashCompareVariants, type ParsedVariant } from '@/lib/variant-file'
import {
  cancelPaperRun,
  deletePaperRun,
  extractPaperVariants,
  getPaperProcessingDisclosure,
  getPaperRun,
  getPaperRunResult,
  isMockResponse,
  PaperRequestError,
  type PaperInputClass,
} from '@/lib/paperVariants'
import type { PaperChatScope } from '@/lib/chat'
import { buildReportHrefV1, buildWorkbenchHrefV1 } from '@/lib/backend'
import type {
  CanonicalVariantRefV1,
  PaperPdfMeta,
  PaperSourceMetadata,
  PaperVariantsResponse,
  ProcessingDisclosureV1,
  SearchInputCandidate,
  ValidatedPaperVariant,
  WorkflowAsyncStateV1,
  WorkflowActiveToolV1,
  WorkflowRunV1,
} from '@/lib/backend'

type Phase = WorkflowAsyncStateV1
type ResultView = 'merged' | 'by-paper'

const FRONTEND_FIXTURE_TIP =
  'Frontend fixture. It demonstrates fail-closed review states and is not source-backed extraction.'
const PAPER_CONCURRENCY = 2

function waitForPaperPoll(signal: AbortSignal, milliseconds: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const onAbort = () => {
      window.clearTimeout(timer)
      reject(new DOMException('Aborted', 'AbortError'))
    }
    const timer = window.setTimeout(() => {
      signal.removeEventListener('abort', onAbort)
      resolve()
    }, milliseconds)
    signal.addEventListener('abort', onAbort, { once: true })
  })
}

// ─── input model ────────────────────────────────────────────────────────
// Each dropped/attached file is a source; a non-empty paste box is also a
// source. Extraction runs once per source and the results are merged.
interface AttachedSource {
  id: string
  name: string
  kind: 'text' | 'pdf'
  text?: string
  file?: File
  charCount?: number
}

type SourceRunState = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

interface SourceRunRecord {
  source: AttachedSource
  state: SourceRunState
  response?: PaperVariantsResponse
  error?: string
  runId?: string
  disclosure?: ProcessingDisclosureV1
}

// ─── merge model ────────────────────────────────────────────────────────
// A variant seen across several papers collapses to one row that aggregates
// every source's evidence quote + source_support, so cross-paper corroboration
// is visible (and counts as evidence) rather than duplicated.
interface SourceMention {
  source: string
  quote: string | null
}
interface MergedVariant {
  key: string
  rep: ValidatedPaperVariant
  mentions: SourceMention[]
  sources: string[]
  sourceSupport: string[]
}
interface SourceGroup {
  name: string
  kind: 'text' | 'pdf'
  pdf: PaperPdfMeta | null
  metadata: PaperSourceMetadata | null
  variants: ValidatedPaperVariant[]
  runId: string | null
  disclosure: ProcessingDisclosureV1 | null
}

// A paper is identified by its citation, not its filename. Use backend
// bibliographic metadata when present; otherwise fall back to a filename-derived
// "Author · Year" (common export naming) with the raw filename as a subtitle.
function citation(meta: PaperSourceMetadata): string {
  const authors = meta.authors.length
    ? meta.authors.length > 1
      ? `${meta.authors[0]} et al.`
      : meta.authors[0]
    : null
  const lead = [authors, meta.year].filter(Boolean).join(' · ')
  return [lead || null, meta.title].filter(Boolean).join(' — ') || 'Untitled source'
}
function filenameHeading(name: string): string {
  const base = name.replace(/\.[^.]+$/, '')
  const m = base.match(/^([A-Za-z][A-Za-z'-]+)[ _-]?(\d{4})\b/)
  return m ? `${m[1]} · ${m[2]}` : base
}

interface SourceHeading {
  /** Compact label for the per-source strip. */
  short: string
  /** Group title for the By-paper header (paper title, or author·year citation). */
  primary: string
  /** Authors · year · journal line, when the primary is the title. */
  byline: string | null
  pmid: string | null
  doi: string | null
  /** Raw filename, shown as a small reference under the citation. */
  filename: string | null
}
function sourceHeading(group: SourceGroup): SourceHeading {
  if (group.name === 'Pasted text') {
    return { short: 'Pasted text', primary: 'Pasted text', byline: null, pmid: null, doi: null, filename: null }
  }
  const m = group.metadata
  if (m && (m.title || m.authors.length)) {
    const firstAuthor = m.authors[0] ? m.authors[0].split(/[ ,]/)[0] : null
    const authorsFull = m.authors.length
      ? m.authors.length > 2
        ? `${m.authors[0]} et al.`
        : m.authors.join(', ')
      : null
    return {
      short: [firstAuthor, m.year].filter(Boolean).join(' · ') || filenameHeading(group.name),
      primary: m.title ?? citation(m),
      byline: m.title ? [authorsFull, m.year, m.journal].filter(Boolean).join(' · ') || null : null,
      pmid: m.pmid,
      doi: m.doi,
      filename: group.name,
    }
  }
  const fh = filenameHeading(group.name)
  return { short: fh, primary: fh, byline: null, pmid: null, doi: null, filename: group.name }
}
interface ExtractResult {
  tagged: Array<{ source: string; v: ValidatedPaperVariant }>
  bySource: SourceGroup[]
  warnings: string[]
  provenance: string[]
  mock: boolean
}

function sourceInputClass(source: AttachedSource): PaperInputClass {
  return source.kind === 'pdf' ? 'pdf' : 'paper_text'
}

function processingKey(disclosures: ProcessingDisclosureV1[]): string {
  return disclosures
    .map((item) =>
      [
        item.provider_id,
        item.execution,
        item.retention,
        item.consent_required ? 'consent' : 'direct',
        [...item.input_classes].sort().join(','),
      ].join(':'),
    )
    .sort()
    .join('|')
}

function resultFromRuns(runs: SourceRunRecord[]): ExtractResult | null {
  const completed = runs.filter(
    (run): run is SourceRunRecord & { response: PaperVariantsResponse } => Boolean(run.response),
  )
  if (completed.length === 0) return null
  const tagged: Array<{ source: string; v: ValidatedPaperVariant }> = []
  const bySource: SourceGroup[] = []
  const warnings: string[] = []
  const provenance = new Set<string>()
  let mock = false
  for (const run of completed) {
    const response = run.response
    if (isMockResponse(response)) mock = true
    response.variants.forEach((variant) => tagged.push({ source: run.source.name, v: variant }))
    response.warnings.forEach((warning) => warnings.push(`${run.source.name}: ${warning}`))
    response.provenance.forEach((item) => provenance.add(item))
    bySource.push({
      name: run.source.name,
      kind: run.source.kind,
      pdf: response.pdf,
      metadata: response.source_metadata,
      variants: response.variants,
      runId: run.runId ?? null,
      disclosure: run.disclosure ?? null,
    })
  }
  return { tagged, bySource, warnings, provenance: [...provenance], mock }
}

function safePaperError(error: unknown): string {
  if (error instanceof PaperRequestError) return error.message
  return 'Paper extraction failed. Retry this source.'
}

function dedupKey(v: ValidatedPaperVariant): string {
  if (v.validated && v.variant_id) return `id:${v.variant_id.toLowerCase()}`
  if (v.genomic_hgvs) return `g:${v.genomic_hgvs.toLowerCase()}`
  const ident = (v.transcript_hgvs || v.protein_hgvs || v.protein_change || '').toLowerCase()
  return `v:${(v.gene || '').toLowerCase()}|${v.level}|${ident}`
}

function mergeVariants(tagged: Array<{ source: string; v: ValidatedPaperVariant }>): MergedVariant[] {
  const groups = new Map<string, Array<{ source: string; v: ValidatedPaperVariant }>>()
  for (const item of tagged) {
    const key = dedupKey(item.v)
    const arr = groups.get(key)
    if (arr) arr.push(item)
    else groups.set(key, [item])
  }
  const merged: MergedVariant[] = []
  for (const [key, arr] of groups) {
    // Representative: prefer a validated mention, else the one with the most
    // source support, else the first seen.
    const rep =
      arr.find((x) => x.v.validated)?.v ??
      [...arr].sort((a, b) => b.v.source_support.length - a.v.source_support.length)[0].v
    const seen = new Set<string>()
    const mentions: SourceMention[] = []
    const sources: string[] = []
    const support = new Set<string>(rep.source_support)
    for (const { source, v } of arr) {
      v.source_support.forEach((s) => support.add(s))
      if (!seen.has(source)) {
        seen.add(source)
        sources.push(source)
      }
      mentions.push({ source, quote: v.evidence_quote })
    }
    merged.push({ key, rep, mentions, sources, sourceSupport: [...support] })
  }
  return merged.sort((a, b) => {
    if (a.rep.validated !== b.rep.validated) return a.rep.validated ? -1 : 1
    if (b.sources.length !== a.sources.length) return b.sources.length - a.sources.length
    return (a.rep.gene || '').localeCompare(b.rep.gene || '')
  })
}

// ─── fail-closed gating (safety-critical) ───────────────────────────────
// A row exposes clinical actions ONLY when its representative is a validated,
// source-backed clinical allele. Ambiguous suggestions and experimental
// constructs are shown but never actionable — mirrors the backend semantics so
// the UI can never present an unresolved/experimental mention as clinical.
function isClinicalActionable(v: ValidatedPaperVariant): boolean {
  return v.validated && v.context === 'clinical_allele'
}
function isAmbiguous(v: ValidatedPaperVariant): boolean {
  // Clinical chooser only. An experimental construct that gains recommended cDNAs
  // (Codex's protein→cDNA backend, coming soon) must NOT render as a clinical
  // match-picker — it stays non-clinical reference (see the recommended-cDNA block).
  return !v.validated && v.candidates.length > 0 && v.context !== 'experimental_construct'
}
function statusGlyph(v: ValidatedPaperVariant): { glyph: string; label: string; tone: string } {
  if (v.validated) return { glyph: '✓', label: 'Validated', tone: 'var(--teal-deep)' }
  if (isAmbiguous(v)) return { glyph: '⚠', label: 'Ambiguous', tone: 'var(--warn-text)' }
  if (v.context === 'experimental_construct')
    return { glyph: '⌀', label: 'Experimental', tone: 'var(--ink-4)' }
  return { glyph: '⊘', label: 'Held', tone: 'var(--ink-4)' }
}
function bestHgvs(v: ValidatedPaperVariant): string {
  return v.transcript_hgvs || v.protein_hgvs || v.protein_change || v.gene || '—'
}

// Build the report query for a source-backed candidate — mirrors
// ReportClient.handleSelectCandidate so a paper candidate opens the same report.
function candidateReportHref(c: SearchInputCandidate): string | null {
  const canonical = canonicalCandidate(c)
  return canonical ? buildReportHrefV1(canonical, 'paper') : null
}
function variantReportHref(v: ValidatedPaperVariant): string | null {
  const resolved =
    v.candidates.find((c) => c.candidate_id === v.resolved_candidate_id && c.gene && c.cdna) ??
    v.candidates.find((c) => c.gene && c.cdna)
  if (resolved) return candidateReportHref(resolved)
  if (v.gene && v.transcript_hgvs) {
    const m = v.transcript_hgvs.match(/^(.+?):(c\..+)$/)
    const cdna = m ? m[2] : v.transcript_hgvs.startsWith('c.') ? v.transcript_hgvs : null
    if (!cdna) return null
    const p = new URLSearchParams({ gene: v.gene, cdna, from: 'paper' })
    if (m) p.set('transcript', m[1])
    return `/report?${p.toString()}`
  }
  return null
}
function variantToParsed(v: ValidatedPaperVariant): ParsedVariant | null {
  const resolved =
    v.candidates.find((c) => c.candidate_id === v.resolved_candidate_id && c.gene && c.cdna) ??
    v.candidates.find((c) => c.gene && c.cdna)
  const gene = resolved?.gene ?? v.gene
  let cdna = resolved?.cdna ?? null
  if (!cdna && v.transcript_hgvs) {
    const m = v.transcript_hgvs.match(/^(.+?):(c\..+)$/)
    cdna = m ? m[2] : v.transcript_hgvs.startsWith('c.') ? v.transcript_hgvs : null
  }
  if (!gene || !cdna) return null
  return { raw: v.transcript_hgvs ?? `${gene} ${cdna}`, gene, variant: cdna, query: `${gene} ${cdna}` }
}
// Saving is a bookmark, not a clinical claim — available on any row that resolves
// to a gene+variant query (validated OR held), but not experimental constructs
// (nothing coordinate-resolvable to save). Open report stays gated to validated.
function canSaveVariant(v: ValidatedPaperVariant): boolean {
  return v.context !== 'experimental_construct' && variantToParsed(v) !== null
}
function variantKey(v: ValidatedPaperVariant): string {
  const p = variantToParsed(v)
  return p ? p.query.toLowerCase() : ''
}
function candidateToParsed(c: SearchInputCandidate): ParsedVariant | null {
  if (!c.gene || !c.cdna) return null
  return {
    raw: c.transcript ? `${c.transcript}:${c.cdna}` : `${c.gene} ${c.cdna}`,
    gene: c.gene,
    variant: c.cdna,
    query: `${c.gene} ${c.cdna}`,
  }
}
function candidateKey(c: SearchInputCandidate): string {
  const p = candidateToParsed(c)
  return p ? p.query.toLowerCase() : ''
}

function canonicalCandidate(c: SearchInputCandidate): CanonicalVariantRefV1 | null {
  if (!c.gene || !c.cdna || !c.candidate_id) return null
  return {
    schema_version: 'canonical_variant_ref.v1',
    gene: c.gene.toUpperCase(),
    cdna: c.cdna,
    transcript: c.transcript ?? null,
    protein_hgvs: c.protein_change ?? null,
    genomic_hg38: c.genomic_hg38 ?? null,
    variant_key: c.candidate_id,
    species: 'human',
    genome_build: 'GRCh38',
    resolution_status: c.genomic_hg38 && c.transcript ? 'resolved' : c.genomic_hg38 ? 'ambiguous' : 'unresolved',
    source_support: c.source_support,
    warnings: c.warnings,
  }
}

function canonicalPaperVariant(v: ValidatedPaperVariant): CanonicalVariantRefV1 | null {
  const candidate =
    v.candidates.find((item) => item.candidate_id === v.resolved_candidate_id) ??
    v.candidates.find((item) => item.gene && item.cdna)
  if (candidate) return canonicalCandidate(candidate)
  const parsed = variantToParsed(v)
  const key = v.variant_id ?? v.resolved_candidate_id
  if (!v.validated || !parsed?.gene || !parsed.variant || !key) return null
  const transcriptMatch = v.transcript_hgvs?.match(/^(.+?):c\./)
  return {
    schema_version: 'canonical_variant_ref.v1',
    gene: parsed.gene.toUpperCase(),
    cdna: parsed.variant,
    transcript: transcriptMatch?.[1] ?? null,
    protein_hgvs: v.protein_hgvs ?? v.protein_change,
    genomic_hg38: v.variant_id,
    variant_key: key,
    species: 'human',
    genome_build: 'GRCh38',
    resolution_status:
      v.variant_id && transcriptMatch?.[1]
        ? 'resolved'
        : v.variant_id
          ? 'ambiguous'
          : 'unresolved',
    source_support: v.source_support,
    warnings: v.resolver_warnings,
  }
}

function paperWorkbenchHref(
  variant: CanonicalVariantRefV1 | null,
  tool: WorkflowActiveToolV1 = 'viewer',
): string | null {
  if (!variant) return null
  try {
    return buildWorkbenchHrefV1(variant, { tool, view: 'window' })
  } catch {
    return null
  }
}

// ─── TSV export of the merged table ─────────────────────────────────────
function tsvCell(s: string): string {
  return s.replace(/[\t\r\n]+/g, ' ')
}
function mergedToTsv(rows: MergedVariant[]): string {
  const header = [
    'gene',
    'level',
    'context',
    'status',
    'hgvs',
    'genomic_hgvs',
    'variant_id',
    'papers_seen_in',
    'sources',
    'source_support',
    'validated',
    'evidence',
  ]
  const lines = [header.join('\t')]
  for (const m of rows) {
    const v = m.rep
    lines.push(
      [
        v.gene ?? '',
        v.level,
        v.context,
        v.validation_status,
        bestHgvs(v),
        v.genomic_hgvs ?? '',
        v.variant_id ?? '',
        String(m.sources.length),
        m.sources.join('; '),
        m.sourceSupport.join('; '),
        v.validated ? 'yes' : 'no',
        m.mentions.find((x) => x.quote)?.quote ?? '',
      ]
        .map(tsvCell)
        .join('\t'),
    )
  }
  return lines.join('\n')
}
function downloadTextFile(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function Badge({ children, tone = 'var(--ink-3)' }: { children: React.ReactNode; tone?: string }) {
  return (
    <span
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 999,
        background: 'var(--bg-soft)',
        padding: '3px 8px',
        fontSize: 10.5,
        fontWeight: 600,
        color: tone,
        textTransform: 'uppercase',
        letterSpacing: '0.04em',
      }}
    >
      {children}
    </span>
  )
}
function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 7,
        background: 'var(--bg)',
        padding: '3px 6px',
        fontSize: 10.5,
        color: 'var(--ink-4)',
      }}
    >
      {children}
    </span>
  )
}
function primaryBtn(enabled: boolean): React.CSSProperties {
  return {
    minHeight: 44,
    padding: '7px 14px',
    borderRadius: 9,
    fontSize: 12.5,
    fontWeight: 600,
    color: enabled ? '#ffffff' : 'var(--ink-4)',
    background: enabled ? 'var(--ink-2)' : 'var(--bg-soft)',
    border: '0.5px solid var(--line)',
    cursor: enabled ? 'pointer' : 'not-allowed',
  }
}
function ghostBtn(): React.CSSProperties {
  return {
    minHeight: 44,
    padding: '7px 14px',
    borderRadius: 9,
    fontSize: 12.5,
    fontWeight: 600,
    color: 'var(--ink-2)',
    background: 'var(--bg)',
    border: '0.5px solid var(--line-2, var(--line))',
    cursor: 'pointer',
  }
}

function disclosureExecutionLabel(item: ProcessingDisclosureV1): string {
  if (item.execution === 'browser') return 'Browser only'
  if (item.execution === 'eamos_backend') return 'Eamos backend'
  return 'External provider'
}

function disclosureRetentionLabel(item: ProcessingDisclosureV1): string {
  if (item.retention === 'none') return 'No retention'
  if (item.retention === 'request_lifetime') return 'Request lifetime only'
  if (item.retention === 'ttl') return item.expires_at ? `Expires ${item.expires_at}` : 'Time limited'
  return 'Saved to account'
}

function ProcessingDisclosurePanel({
  disclosures,
  onAccept,
}: {
  disclosures: ProcessingDisclosureV1[]
  onAccept: () => void
}) {
  return (
    <section
      className="mt-4"
      aria-labelledby="paper-processing-title"
      style={{
        border: '0.5px solid var(--warn-bdr)',
        borderRadius: 12,
        background: 'var(--warn-tint)',
        padding: '16px 18px',
      }}
    >
      <h2 id="paper-processing-title" style={{ margin: 0, fontSize: 14, fontWeight: 650, color: 'var(--ink)' }}>
        Review processing before upload
      </h2>
      <p style={{ margin: '6px 0 12px', maxWidth: '70ch', fontSize: 12.5, lineHeight: 1.55, color: 'var(--ink-2)' }}>
        Publications can contain case or person language. Eamos does not ask you to upload patient records. Review the named processing path before sending this text or PDF.
      </p>
      <div className="flex flex-col gap-2">
        {disclosures.map((item) => (
          <div
            key={`${item.provider_id}-${item.input_classes.join('-')}`}
            style={{
              border: '0.5px solid var(--warn-bdr)',
              borderRadius: 9,
              background: 'var(--bg)',
              padding: '10px 12px',
            }}
          >
            <div className="flex flex-wrap items-center gap-2">
              <strong style={{ fontSize: 12.5, color: 'var(--ink)' }}>{item.provider_label}</strong>
              <Badge tone="var(--warn-text)">{disclosureExecutionLabel(item)}</Badge>
              {item.input_classes.map((inputClass) => (
                <Chip key={inputClass}>{formatToken(inputClass)}</Chip>
              ))}
            </div>
            <p style={{ margin: '6px 0 0', fontSize: 11.5, lineHeight: 1.5, color: 'var(--ink-3)' }}>
              {item.raw_input_persisted ? 'Raw input is persisted.' : 'Raw input is not persisted.'}{' '}
              {disclosureRetentionLabel(item)}. {item.user_deletable ? 'You can delete the saved run.' : 'No raw input is retained for later deletion.'}
            </p>
            {item.warnings.length > 0 && (
              <ul style={{ margin: '7px 0 0', paddingLeft: 18, fontSize: 11.5, color: 'var(--warn-text)' }}>
                {item.warnings.map((warning) => <li key={warning}>{warning}</li>)}
              </ul>
            )}
          </div>
        ))}
      </div>
      <p style={{ margin: '10px 0 0', maxWidth: '74ch', fontSize: 11.5, lineHeight: 1.5, color: 'var(--ink-3)' }}>
        You can cancel this Eamos run while it is queued or running. Cancellation cannot recall input already received by an external provider.
      </p>
      <button type="button" onClick={onAccept} style={{ ...primaryBtn(true), marginTop: 13 }}>
        I understand, send these sources
      </button>
    </section>
  )
}

function SourceRunStatusList({
  runs,
  onRetry,
  onRemove,
}: {
  runs: SourceRunRecord[]
  onRetry: () => void
  onRemove: (run: SourceRunRecord) => void
}) {
  if (runs.length === 0) return null
  const canRetry = runs.some((run) => run.state === 'failed' || run.state === 'cancelled')
  return (
    <section className="mt-4" aria-labelledby="paper-source-status-title">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="paper-source-status-title" style={{ margin: 0, fontSize: 12.5, fontWeight: 650, color: 'var(--ink-2)' }}>
          Source status
        </h2>
        {canRetry && <button type="button" onClick={onRetry} style={ghostBtn()}>Retry failed sources</button>}
      </div>
      <ul className="mt-2 flex flex-col gap-1.5" style={{ padding: 0 }}>
        {runs.map((run) => {
          const tone = run.state === 'failed'
            ? 'var(--err)'
            : run.state === 'cancelled'
              ? 'var(--warn-text)'
              : run.state === 'completed'
                ? 'var(--teal-deep)'
                : 'var(--ink-3)'
          return (
            <li
              key={run.source.id}
              className="flex flex-wrap items-center justify-between gap-2"
              style={{
                listStyle: 'none',
                border: '0.5px solid var(--line)',
                borderRadius: 9,
                background: 'var(--bg)',
                padding: '8px 10px',
              }}
            >
              <span style={{ minWidth: 0, fontSize: 12, color: 'var(--ink-2)', overflowWrap: 'anywhere' }}>
                {run.source.name}
                {run.error ? <span style={{ display: 'block', marginTop: 2, fontSize: 11, color: tone }}>{run.error}</span> : null}
              </span>
              <span className="flex flex-wrap items-center gap-1.5">
                {run.disclosure && <Chip>{run.disclosure.provider_label}</Chip>}
                <Badge tone={tone}>{run.state}</Badge>
                {(run.state === 'completed' || run.state === 'failed' || run.state === 'cancelled') && (
                  <button
                    type="button"
                    onClick={() => onRemove(run)}
                    aria-label={`Remove ${run.source.name} from this extraction`}
                    style={{ ...ghostBtn(), padding: '4px 8px', fontSize: 11 }}
                  >
                    Remove
                  </button>
                )}
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

const citationLink: React.CSSProperties = {
  fontSize: 10.5,
  fontWeight: 600,
  color: 'var(--teal-deep)',
  border: '0.5px solid var(--line)',
  borderRadius: 7,
  background: 'var(--bg-soft)',
  padding: '3px 7px',
  textDecoration: 'none',
}

function PaperCandidateRow({
  merged,
  savedKeys,
  onOpenReport,
  onAddVariant,
  onAddCandidate,
}: {
  merged: MergedVariant
  savedKeys: Set<string>
  onOpenReport: (v: ValidatedPaperVariant) => void
  onAddVariant: (v: ValidatedPaperVariant) => void
  onAddCandidate: (c: SearchInputCandidate) => void
}) {
  const router = useRouter()
  const [showProvenance, setShowProvenance] = useState(false)
  const variant = merged.rep
  const status = statusGlyph(variant)
  // Any non-validated row with source-backed candidates shows a chooser: a
  // clinical ambiguous match (pick the transcript) OR an experimental
  // construct's same-residue cDNA recommendations (research context). Both are
  // user-selected and never auto-validated — opening one runs the authoritative
  // report lookup, saving one is a bookmark — so this stays fail-closed.
  const hasRecommendations = !variant.validated && variant.candidates.length > 0
  const isResearchContext = variant.context === 'experimental_construct'
  // Open report on the rep = the clinical action → validated only. Save = a
  // bookmark → any resolvable row.
  const showOpen = isClinicalActionable(variant) && Boolean(variantReportHref(variant))
  const showSave = canSaveVariant(variant)
  const repSaved = savedKeys.has(variantKey(variant))
  const repParsed = variantToParsed(variant)
  const batchParsed = isClinicalActionable(variant) ? repParsed : null
  const workbenchHref = paperWorkbenchHref(canonicalPaperVariant(variant))
  const multiPaper = merged.sources.length > 1
  const resolverNotes = [...variant.resolver_warnings, ...variant.resolver_provenance]
  // Saveable rows are draggable straight into the WorkRail library box.
  const dragParsed = showSave ? variantToParsed(variant) : null

  return (
    <li
      draggable={Boolean(dragParsed)}
      onDragStart={(e) => {
        if (!dragParsed) return
        e.dataTransfer.setData(
          'text/plain',
          JSON.stringify({ eamosSave: dragParsed, hgvs_full: variant.transcript_hgvs ?? null }),
        )
        e.dataTransfer.effectAllowed = 'copy'
      }}
      title={dragParsed ? 'Drag to the library to save' : undefined}
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 12,
        background: 'var(--bg)',
        padding: '16px 18px',
        listStyle: 'none',
        cursor: dragParsed ? 'grab' : 'default',
      }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span aria-hidden style={{ fontSize: 15, color: status.tone, fontWeight: 700 }}>
          {status.glyph}
        </span>
        <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)' }}>
          {variant.gene ?? 'Unknown gene'}
        </span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 12.5, color: 'var(--ink-2)', overflowWrap: 'anywhere' }}>
          {bestHgvs(variant)}
        </span>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
        <Badge>{variant.level}</Badge>
        <Badge tone={variant.context === 'experimental_construct' ? 'var(--ink-4)' : 'var(--ink-3)'}>
          {formatToken(variant.context)}
        </Badge>
        <Badge tone={status.tone}>{status.label}</Badge>
        {multiPaper && <Badge tone="var(--teal-deep)">Seen in {merged.sources.length} papers</Badge>}
        {merged.sourceSupport.slice(0, 3).map((s) => (
          <Chip key={s}>{s}</Chip>
        ))}
      </div>

      {merged.mentions.some((m) => m.quote) && (
        <div className="mt-3 flex flex-col gap-2">
          {merged.mentions
            .filter((m) => m.quote)
            .map((m, i) => (
              <blockquote
                key={`${m.source}-${i}`}
                style={{
                  margin: 0,
                  paddingLeft: 12,
                  borderLeft: '2px solid var(--line-2, var(--line))',
                  fontSize: 13,
                  lineHeight: 1.6,
                  color: 'var(--ink-2)',
                }}
              >
                {multiPaper && (
                  <span
                    style={{
                      display: 'block',
                      fontSize: 10.5,
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      color: 'var(--ink-4)',
                      marginBottom: 2,
                    }}
                  >
                    {m.source}
                  </span>
                )}
                <span style={{ fontStyle: 'italic' }}>“{m.quote}”</span>
              </blockquote>
            ))}
        </div>
      )}

      {variant.validated && variant.genomic_hgvs && (
        <div
          className="mt-2.5"
          style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-3)', overflowWrap: 'anywhere' }}
        >
          {variant.genomic_hgvs}
          {variant.variant_id ? `  ·  ${variant.variant_id}` : ''}
        </div>
      )}

      {(showOpen || showSave || workbenchHref || batchParsed) && !hasRecommendations && (
        <div className="mt-3.5 flex flex-wrap gap-2">
          {showOpen && (
            <button type="button" onClick={() => onOpenReport(variant)} style={primaryBtn(true)}>
              Open report
            </button>
          )}
          {showSave && (
            <button type="button" disabled={repSaved} onClick={() => onAddVariant(variant)} style={ghostBtn()}>
              {repSaved ? 'In library ✓' : '+ Library'}
            </button>
          )}
          {workbenchHref && (
            <button type="button" onClick={() => router.push(workbenchHref)} style={ghostBtn()}>
              Open Workbench
            </button>
          )}
          {batchParsed && (
            <button
              type="button"
              onClick={() => {
                stashCompareVariants([batchParsed], `Paper · ${variant.gene ?? 'variant'}`)
                router.push('/compare')
              }}
              style={ghostBtn()}
            >
              Add to Batch
            </button>
          )}
        </div>
      )}

      {hasRecommendations && (
        <div className="mt-3.5">
          <div
            style={{
              fontSize: 11.5,
              fontWeight: 600,
              color: isResearchContext ? 'var(--ink-4)' : 'var(--warn-text)',
              marginBottom: 8,
            }}
          >
            {isResearchContext
              ? 'Recommended cDNA · same residue, source-backed (research) — open or save any'
              : `${variant.candidates.length} candidate${variant.candidates.length === 1 ? '' : 's'} — pick a source-backed match to open it; save any to the library to keep it`}
          </div>
          <div className="flex flex-col gap-2.5">
            {variant.candidates.map((c) => {
              const cSaved = savedKeys.has(candidateKey(c))
              const parsedCandidate = candidateToParsed(c)
              const candidateWorkbenchHref = isResearchContext
                ? null
                : paperWorkbenchHref(canonicalCandidate(c))
              return (
                <div key={c.candidate_id} className="flex flex-col gap-1.5">
                  <CandidateCard
                    candidate={c}
                    onSelect={(picked) => {
                      const href = candidateReportHref(picked)
                      if (href) router.push(href)
                    }}
                  />
                  {parsedCandidate && (
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={cSaved}
                        onClick={() => onAddCandidate(c)}
                        style={{ ...ghostBtn(), padding: '5px 11px', fontSize: 11.5 }}
                      >
                        {cSaved ? 'In library ✓' : '+ Library'}
                      </button>
                      {!isResearchContext && (
                        <button
                          type="button"
                          onClick={() => {
                            stashCompareVariants([parsedCandidate], `Paper · ${c.gene}`)
                            router.push('/compare')
                          }}
                          style={{ ...ghostBtn(), padding: '5px 11px', fontSize: 11.5 }}
                        >
                          Add to Batch
                        </button>
                      )}
                      {candidateWorkbenchHref && (
                        <button
                          type="button"
                          onClick={() => router.push(candidateWorkbenchHref)}
                          style={{ ...ghostBtn(), padding: '5px 11px', fontSize: 11.5 }}
                        >
                          Open Workbench
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {!showOpen && !showSave && !hasRecommendations && (
        <div className="mt-3" style={{ fontSize: 12, color: 'var(--ink-4)' }}>
          {variant.context === 'experimental_construct'
            ? 'Experimental construct — shown for context, not a clinical variant.'
            : 'Held — could not resolve to a gene + variant. No clinical action.'}
        </div>
      )}

      {resolverNotes.length > 0 && (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setShowProvenance((s) => !s)}
            style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink-4)', background: 'transparent', border: 'none', cursor: 'pointer', padding: 0 }}
          >
            {showProvenance ? 'Hide' : 'Show'} resolver provenance ▾
          </button>
          {showProvenance && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {variant.resolver_warnings.map((w) => (
                <span
                  key={w}
                  style={{
                    border: '0.5px solid var(--warn-bdr)',
                    borderRadius: 7,
                    background: 'var(--warn-tint)',
                    color: 'var(--warn-text)',
                    padding: '3px 7px',
                    fontSize: 10.5,
                    fontWeight: 600,
                  }}
                >
                  {formatToken(w)}
                </span>
              ))}
              {variant.resolver_provenance.map((p) => (
                <Chip key={p}>{formatToken(p)}</Chip>
              ))}
            </div>
          )}
        </div>
      )}
    </li>
  )
}

export function PaperClient() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const requestedRunId = searchParams.get('run_id')
  const { user, loading: authLoading, getAccessToken } = useAuth()
  const [text, setText] = useState('')
  const [attachments, setAttachments] = useState<AttachedSource[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [sourceRuns, setSourceRuns] = useState<SourceRunRecord[]>([])
  const [disclosures, setDisclosures] = useState<ProcessingDisclosureV1[]>([])
  const [acceptedProcessingKey, setAcceptedProcessingKey] = useState<string | null>(null)
  const [pendingSources, setPendingSources] = useState<AttachedSource[]>([])
  const [pendingPreserve, setPendingPreserve] = useState(false)
  const [resumeAfterAuth, setResumeAfterAuth] = useState(false)
  const [activeRun, setActiveRun] = useState<WorkflowRunV1 | null>(null)
  const [confirmDeleteRun, setConfirmDeleteRun] = useState(false)
  const [paperTarget, setPaperTarget] = useState(() => readPaperTarget())
  const [view, setView] = useState<ResultView>('merged')
  const [savedKeys, setSavedKeys] = useState<Set<string>>(new Set())
  const [collapsedPapers, setCollapsedPapers] = useState<Set<string>>(() => new Set())
  const togglePaper = (name: string) =>
    setCollapsedPapers((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  const [toast, setToast] = useState<string | null>(null)
  const [showMeta, setShowMeta] = useState(false)
  const [searchFocused, setSearchFocused] = useState(false)
  const idRef = useRef(0)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const runSeq = useRef(0)
  const resumedRunRef = useRef<string | null>(null)

  const currentSources = useMemo(() => {
    const sources: AttachedSource[] = []
    if (text.trim()) sources.push({ id: 'paste', name: 'Pasted text', kind: 'text', text })
    sources.push(...attachments)
    return sources
  }, [attachments, text])
  const totalSources = currentSources.length
  const busy = phase === 'validating' || phase === 'queued' || phase === 'running'
  const canExtract = !busy && !authLoading && totalSources > 0
  const result = useMemo(() => resultFromRuns(sourceRuns), [sourceRuns])

  const flash = (msg: string) => {
    setToast(msg)
    window.setTimeout(() => setToast(null), 2400)
  }

  // Top-nav variant search → report, mirroring /report and /compare so the search
  // bar behaves identically across surfaces.
  const handleSearch = (raw: string) => {
    const href = reportHrefForQuery(raw)
    if (href) router.push(href)
  }

  const addFiles = async (files: FileList | File[]) => {
    const next: AttachedSource[] = []
    for (const file of Array.from(files)) {
      const isPdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name)
      idRef.current += 1
      const id = `src-${idRef.current}`
      if (isPdf) {
        next.push({ id, name: file.name, kind: 'pdf', file })
      } else {
        const content = await file.text()
        next.push({ id, name: file.name, kind: 'text', text: content, charCount: content.length })
      }
    }
    setAcceptedProcessingKey(null)
    setAttachments((prev) => [...prev, ...next])
  }
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files?.length) void addFiles(e.dataTransfer.files)
  }
  const removeAttachment = (id: string) => {
    setAcceptedProcessingKey(null)
    setAttachments((prev) => prev.filter((attachment) => attachment.id !== id))
    setSourceRuns((prev) => prev.filter((run) => run.source.id !== id))
  }

  const executeSources = useCallback(async (
    sources: AttachedSource[],
    token: string,
    processingConsent: boolean,
    runDisclosures: ProcessingDisclosureV1[],
    preserve: boolean,
  ) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    const sequence = runSeq.current + 1
    runSeq.current = sequence
    const targetIds = new Set(sources.map((source) => source.id))
    const baseRuns = preserve
      ? sourceRuns.filter((record) => !targetIds.has(record.source.id))
      : []
    const queued = sources.map<SourceRunRecord>((source) => ({ source, state: 'queued' }))
    setSourceRuns([...baseRuns, ...queued])
    setPhase('queued')
    setError(null)

    const outcomes = new Map<string, SourceRunRecord>()
    let cursor = 0
    const updateRecord = (id: string, patch: Partial<SourceRunRecord>) => {
      setSourceRuns((prev) =>
        prev.map((record) => (record.source.id === id ? { ...record, ...patch } : record)),
      )
    }
    const worker = async () => {
      while (cursor < sources.length && !controller.signal.aborted) {
        const source = sources[cursor]
        cursor += 1
        const disclosure =
          runDisclosures.find((item) => item.input_classes.includes(sourceInputClass(source))) ?? null
        updateRecord(source.id, { state: 'running', disclosure: disclosure ?? undefined })
        setPhase('running')
        let workflowRunId: string | undefined
        try {
          const response = await extractPaperVariants(
            source.kind === 'pdf'
              ? { pdf: source.file, sourceName: source.name }
              : { text: source.text ?? '', sourceName: source.name },
            {
              signal: controller.signal,
              accessToken: token,
              processingConsent,
              onWorkflowRunId: (runId) => {
                workflowRunId = runId
              },
            },
          )
          const completed: SourceRunRecord = {
            source,
            state: 'completed',
            response,
            runId: workflowRunId,
            disclosure: disclosure ?? undefined,
          }
          outcomes.set(source.id, completed)
          updateRecord(source.id, completed)
        } catch (caught) {
          if (caught instanceof DOMException && caught.name === 'AbortError') {
            const cancelled: SourceRunRecord = { source, state: 'cancelled' }
            outcomes.set(source.id, cancelled)
            updateRecord(source.id, cancelled)
            continue
          }
          const failed: SourceRunRecord = {
            source,
            state: 'failed',
            error: safePaperError(caught),
            disclosure: disclosure ?? undefined,
          }
          outcomes.set(source.id, failed)
          updateRecord(source.id, failed)
        }
      }
    }
    await Promise.all(
      Array.from({ length: Math.min(PAPER_CONCURRENCY, sources.length) }, () => worker()),
    )
    if (runSeq.current !== sequence) return

    for (const source of sources) {
      if (!outcomes.has(source.id)) {
        outcomes.set(source.id, { source, state: 'cancelled' })
      }
    }
    const combined = [
      ...baseRuns,
      ...sources.map((source) => outcomes.get(source.id) ?? { source, state: 'cancelled' as const }),
    ]
    setSourceRuns(combined)
    if (controller.signal.aborted) {
      setPhase('cancelled')
      return
    }
    const completedCount = combined.filter((record) => record.state === 'completed').length
    const failedCount = combined.filter((record) => record.state === 'failed').length
    setSavedKeys(new Set())
    if (completedCount === 0) {
      setError(combined.find((record) => record.error)?.error ?? 'Paper extraction failed.')
      setPhase('failed')
    } else if (failedCount > 0) {
      setPhase('partial')
    } else {
      const hasCandidates = combined.some((record) => (record.response?.variants.length ?? 0) > 0)
      setPhase(hasCandidates ? 'completed' : 'empty')
    }
  }, [sourceRuns])

  const beginRun = useCallback(async (
    sources: AttachedSource[] = currentSources,
    preserve = false,
  ) => {
    if (sources.length === 0) return
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setPhase('validating')
    setError(null)
    setPendingSources(sources)
    setPendingPreserve(preserve)
    const token = await getAccessToken()
    if (!token) {
      setResumeAfterAuth(true)
      setPhase('auth_required')
      openAuthMenu()
      return
    }
    setResumeAfterAuth(false)
    try {
      const inputClasses = [...new Set(sources.map(sourceInputClass))]
      const nextDisclosures = await Promise.all(
        inputClasses.map((inputClass) =>
          getPaperProcessingDisclosure(inputClass, {
            accessToken: token,
            signal: controller.signal,
          }),
        ),
      )
      setDisclosures(nextDisclosures)
      const key = processingKey(nextDisclosures)
      const consentRequired = nextDisclosures.some((item) => item.consent_required)
      if (consentRequired && acceptedProcessingKey !== key) {
        setPhase('consent_required')
        return
      }
      await executeSources(sources, token, consentRequired, nextDisclosures, preserve)
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === 'AbortError') return
      const message = safePaperError(caught)
      setError(message)
      if (
        caught instanceof PaperRequestError &&
        (caught.code === 'auth_required' || caught.code === 'auth_expired')
      ) {
        setResumeAfterAuth(true)
        setPhase('auth_required')
        openAuthMenu()
      } else {
        setPhase('failed')
      }
    }
  }, [acceptedProcessingKey, currentSources, executeSources, getAccessToken])

  useEffect(() => {
    if (!resumeAfterAuth || !user || phase !== 'auth_required' || pendingSources.length === 0) return
    window.queueMicrotask(() => void beginRun(pendingSources, pendingPreserve))
  }, [beginRun, pendingPreserve, pendingSources, phase, resumeAfterAuth, user])

  const acceptAndContinue = async () => {
    const key = processingKey(disclosures)
    setAcceptedProcessingKey(key)
    const token = await getAccessToken()
    if (!token) {
      setResumeAfterAuth(true)
      setPhase('auth_required')
      openAuthMenu()
      return
    }
    await executeSources(pendingSources, token, true, disclosures, pendingPreserve)
  }

  const cancelCurrentRun = () => {
    runSeq.current += 1
    abortRef.current?.abort()
    setSourceRuns((prev) =>
      prev.map((record) =>
        record.state === 'queued' || record.state === 'running'
          ? { ...record, state: 'cancelled' }
          : record,
      ),
    )
    setPhase('cancelled')
  }

  const retryFailedSources = () => {
    const failed = sourceRuns
      .filter((record) => record.state === 'failed' || record.state === 'cancelled')
      .map((record) => record.source)
    void beginRun(failed, true)
  }

  const removeSourceRun = async (record: SourceRunRecord) => {
    if (record.runId) {
      const token = await getAccessToken()
      if (!token) {
        setPhase('auth_required')
        openAuthMenu()
        return
      }
      try {
        await deletePaperRun(record.runId, { accessToken: token })
      } catch (caught) {
        setError(safePaperError(caught))
        setPhase('failed')
        return
      }
    }
    setSourceRuns((prev) => prev.filter((run) => run.source.id !== record.source.id))
    if (record.source.id === 'paste') setText('')
    else setAttachments((prev) => prev.filter((source) => source.id !== record.source.id))
    if (sourceRuns.every((run) => run.source.id === record.source.id)) {
      setActiveRun(null)
      setConfirmDeleteRun(false)
      setError(null)
      setPhase('idle')
    }
  }

  useEffect(() => {
    if (!requestedRunId || authLoading || resumedRunRef.current === requestedRunId) return
    if (!user) {
      window.queueMicrotask(() => {
        setPhase('auth_required')
        setResumeAfterAuth(false)
        openAuthMenu()
      })
      return
    }
    resumedRunRef.current = requestedRunId
    const controller = new AbortController()
    abortRef.current = controller
    void (async () => {
      await Promise.resolve()
      if (controller.signal.aborted) return
      setPhase('validating')
      const token = await getAccessToken()
      if (!token) throw new PaperRequestError('Sign in to resume this Paper run.', { code: 'auth_required' })
      let run = await getPaperRun(requestedRunId, { accessToken: token, signal: controller.signal })
      setActiveRun(run)
      while (run.status === 'queued' || run.status === 'running') {
        setPhase(run.status)
        await waitForPaperPoll(controller.signal, 1800)
        run = await getPaperRun(requestedRunId, { accessToken: token, signal: controller.signal })
        setActiveRun(run)
      }
      if (run.status === 'cancelled' || run.status === 'expired' || run.status === 'failed') {
        setPhase(run.status)
        return
      }
      const response = await getPaperRunResult(requestedRunId, {
        accessToken: token,
        signal: controller.signal,
      })
      const source: AttachedSource = {
        id: `run-${run.run_id}`,
        name: response.source_metadata?.title ?? 'Saved Paper extraction',
        kind: response.pdf ? 'pdf' : 'text',
      }
      setDisclosures(run.processing_disclosure ? [run.processing_disclosure] : [])
      setSourceRuns([
        {
          source,
          state: 'completed',
          response,
          runId: run.run_id,
          disclosure: run.processing_disclosure ?? undefined,
        },
      ])
      setPhase(run.status === 'partial' ? 'partial' : response.variants.length ? 'completed' : 'empty')
    })().catch((caught: unknown) => {
      if (caught instanceof DOMException && caught.name === 'AbortError') return
      resumedRunRef.current = null
      const message = safePaperError(caught)
      setError(message)
      if (
        caught instanceof PaperRequestError &&
        (caught.code === 'auth_required' || caught.code === 'auth_expired')
      ) {
        setPhase('auth_required')
        openAuthMenu()
      } else {
        setPhase('failed')
      }
    })
    return () => controller.abort()
  }, [authLoading, getAccessToken, requestedRunId, user])

  const merged = useMemo(() => (result ? mergeVariants(result.tagged) : []), [result])
  const counts = useMemo(() => {
    if (!result) return null
    return {
      papers: result.bySource.length,
      mentions: result.tagged.length,
      distinct: merged.length,
      validated: merged.filter((m) => m.rep.validated).length,
    }
  }, [result, merged])
  const saveableRows = useMemo(() => merged.filter((m) => canSaveVariant(m.rep)), [merged])

  // Ask-Eamos paper scope — this run's merged candidates + source provenance,
  // bounded/sanitized to mirror the backend PaperContext (short evidence quote
  // only, never the full paper body). Null until an extraction produces
  // candidates, so the rail's chat stays idle until there's something to ground in.
  const paperScope = useMemo<PaperChatScope | null>(() => {
    if (!result || merged.length === 0) return null
    return {
      candidates: merged.slice(0, 50).map((m) => ({
        gene: m.rep.gene,
        hgvs: bestHgvs(m.rep),
        level: m.rep.level,
        context: m.rep.context,
        validation_status: m.rep.validation_status,
        validated: m.rep.validated,
        evidence_quote: m.mentions.find((x) => x.quote)?.quote ?? null,
        source_support: m.sourceSupport.slice(0, 12),
        papers: m.sources.slice(0, 12),
      })),
      source_count: result.bySource.length,
      sources: result.bySource.map((s) => sourceHeading(s).short).slice(0, 24),
    }
  }, [result, merged])

  const openReport = (v: ValidatedPaperVariant) => {
    const href = variantReportHref(v)
    if (href) router.push(href)
  }
  const addVariant = (v: ValidatedPaperVariant) => {
    const parsed = variantToParsed(v)
    if (!parsed) return
    const added = saveVariant(parsed, { hgvs_full: v.transcript_hgvs ?? undefined })
    setSavedKeys((prev) => new Set(prev).add(parsed.query.toLowerCase()))
    flash(added ? `Saved ${parsed.query} to library` : `${parsed.query} already in library`)
  }
  const addCandidate = (c: SearchInputCandidate) => {
    const parsed = candidateToParsed(c)
    if (!parsed) return
    const added = saveVariant(parsed, {
      hgvs_full: c.transcript ? `${c.transcript}:${c.cdna}` : undefined,
    })
    setSavedKeys((prev) => new Set(prev).add(parsed.query.toLowerCase()))
    flash(added ? `Saved ${parsed.query} to library` : `${parsed.query} already in library`)
  }
  const addAllSaveable = () => {
    let added = 0
    for (const m of saveableRows) {
      const parsed = variantToParsed(m.rep)
      if (!parsed) continue
      if (saveVariant(parsed, { hgvs_full: m.rep.transcript_hgvs ?? undefined })) added += 1
      setSavedKeys((prev) => new Set(prev).add(parsed.query.toLowerCase()))
    }
    flash(added ? `Saved ${added} variant${added === 1 ? '' : 's'} to library` : 'Those variants are already in your library')
  }
  const addAllToBatch = () => {
    const parsed = saveableRows
      .map((m) => variantToParsed(m.rep))
      .filter((p): p is ParsedVariant => Boolean(p))
    if (parsed.length === 0) return
    stashCompareVariants(parsed, 'Paper extraction')
    router.push('/compare')
  }
  const cancelSavedRun = async () => {
    if (!activeRun) return
    const token = await getAccessToken()
    if (!token) {
      setPhase('auth_required')
      openAuthMenu()
      return
    }
    try {
      const cancelled = await cancelPaperRun(activeRun.run_id, { accessToken: token })
      setActiveRun(cancelled)
      setPhase('cancelled')
    } catch (caught) {
      setError(safePaperError(caught))
      setPhase('failed')
    }
  }
  const deleteSavedRun = async () => {
    if (!activeRun) return
    const token = await getAccessToken()
    if (!token) {
      setPhase('auth_required')
      openAuthMenu()
      return
    }
    try {
      await deletePaperRun(activeRun.run_id, { accessToken: token })
      setActiveRun(null)
      setConfirmDeleteRun(false)
      setSourceRuns([])
      setDisclosures([])
      setPhase('idle')
      router.replace('/paper')
      flash('Paper run deleted')
    } catch (caught) {
      setError(safePaperError(caught))
      setPhase('failed')
    }
  }
  const exportTsv = () => {
    if (!merged.length) return
    downloadTextFile('paper-variants.tsv', mergedToTsv(merged), 'text/tab-separated-values')
  }

  // ─── output pane ──────────────────────────────────────────────────────
  // Centered reading column, same idiom as /report's CenteredMain: mx-auto +
  // --maxw-report-frame so the content sits centered in the pane right of the
  // rail rather than jammed left with a void on the right.
  const output = (
    <main className="mx-auto" style={{ width: '100%', maxWidth: 'var(--maxw-report-frame)', padding: '24px 32px 80px' }}>
      <header>
        <h1 style={{ fontFamily: 'var(--display)', fontSize: 26, fontWeight: 650, margin: 0, color: 'var(--ink)' }}>
          Paper → Variants
        </h1>
        <p style={{ margin: '8px 0 0', fontSize: 14, lineHeight: 1.6, color: 'var(--ink-2)' }}>
          Drop one or more publications, then resolve each variant mention through Eamos source-backed candidate
          resolution. Variants seen across papers are merged; only a single high-confidence, source-backed clinical
          allele becomes a clinical action. Save any to the library on the left to open in a report later.
        </p>
      </header>

      {paperTarget && (
        <section
          className="mt-4 flex flex-wrap items-center justify-between gap-3"
          aria-label="Paper variant target"
          style={{
            border: '0.5px solid var(--teal-bdr)',
            borderRadius: 10,
            background: 'var(--teal-tint)',
            padding: '10px 12px',
          }}
        >
          <span style={{ fontSize: 12, color: 'var(--ink-2)' }}>
            Finding mentions of <strong>{paperTarget.variant.gene} {paperTarget.variant.cdna}</strong>
            <span style={{ display: 'block', marginTop: 3, color: 'var(--ink-4)' }}>
              Target carried from another surface. No publication text was prefilled.
            </span>
          </span>
          <button
            type="button"
            onClick={() => {
              clearPaperTarget()
              setPaperTarget(null)
            }}
            style={ghostBtn()}
          >
            Discard target
          </button>
        </section>
      )}

      {activeRun && (
        <section
          className="mt-4 flex flex-wrap items-center justify-between gap-3"
          aria-label="Saved Paper run"
          style={{
            border: '0.5px solid var(--line)',
            borderRadius: 10,
            background: 'var(--bg)',
            padding: '10px 12px',
          }}
        >
          <span style={{ fontSize: 12, color: 'var(--ink-3)' }}>
            Saved run · <strong style={{ color: 'var(--ink-2)' }}>{formatToken(activeRun.status)}</strong>
            {' · '}{new Date(activeRun.updated_at).toLocaleString()}
          </span>
          <span className="flex flex-wrap items-center gap-2">
            {(activeRun.status === 'queued' || activeRun.status === 'running') && (
              <button type="button" onClick={() => void cancelSavedRun()} style={ghostBtn()}>
                Cancel run
              </button>
            )}
            {confirmDeleteRun ? (
              <>
                <button type="button" onClick={() => setConfirmDeleteRun(false)} style={ghostBtn()}>
                  Keep run
                </button>
                <button type="button" onClick={() => void deleteSavedRun()} style={ghostBtn()}>
                  Confirm delete
                </button>
              </>
            ) : (
              <button type="button" onClick={() => setConfirmDeleteRun(true)} style={ghostBtn()}>
                Delete run
              </button>
            )}
          </span>
        </section>
      )}

      {/* Input zone */}
      <section
        className="mt-6"
        style={{ background: 'var(--bg)', border: '0.5px solid var(--line)', borderRadius: 14, padding: '20px 22px' }}
      >
        <div
          onDragEnter={(e) => {
            e.preventDefault()
            setDragActive(true)
          }}
          onDragOver={(e) => e.preventDefault()}
          onDragLeave={(e) => {
            e.preventDefault()
            if (e.currentTarget === e.target) setDragActive(false)
          }}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          aria-label="Drag papers here or browse to attach"
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              fileInputRef.current?.click()
            }
          }}
          style={{
            border: `1.5px dashed ${dragActive ? 'var(--teal-deep)' : 'var(--line-2, var(--line))'}`,
            borderRadius: 12,
            background: dragActive ? 'color-mix(in oklab, var(--teal-deep) 6%, var(--bg-soft))' : 'var(--bg-soft)',
            padding: '22px 18px',
            textAlign: 'center',
            cursor: 'pointer',
            transition: 'background 120ms, border-color 120ms',
          }}
        >
          <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-2)' }}>
            Drag papers here — <span style={{ color: 'var(--teal-deep)' }}>or browse</span>
          </div>
          <div style={{ fontSize: 11.5, color: 'var(--ink-4)', marginTop: 4 }}>.txt or PDF · multiple files supported</div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,text/plain,application/pdf,.pdf"
            multiple
            hidden
            onChange={(e) => {
              if (e.target.files?.length) void addFiles(e.target.files)
              e.target.value = ''
            }}
          />
        </div>

        {attachments.length > 0 && (
          <ul className="mt-3 flex flex-col gap-1.5" style={{ padding: 0, margin: 0 }}>
            {attachments.map((a) => (
              <li
                key={a.id}
                className="flex items-center justify-between gap-3"
                style={{
                  border: '0.5px solid var(--line)',
                  borderRadius: 9,
                  background: 'var(--bg-soft)',
                  padding: '8px 12px',
                  listStyle: 'none',
                }}
              >
                <span className="flex items-center gap-2 min-w-0">
                  <Badge tone={a.kind === 'pdf' ? 'var(--warn-text)' : 'var(--ink-3)'}>{a.kind}</Badge>
                  <span style={{ fontSize: 12.5, color: 'var(--ink-2)', overflowWrap: 'anywhere' }}>{a.name}</span>
                  {a.charCount != null && (
                    <span style={{ fontSize: 11, color: 'var(--ink-4)' }}>{a.charCount.toLocaleString()} chars</span>
                  )}
                </span>
                <button
                  type="button"
                  aria-label={`Remove ${a.name}`}
                  onClick={() => removeAttachment(a.id)}
                  style={{ fontSize: 13, color: 'var(--ink-4)', background: 'transparent', border: 'none', cursor: 'pointer', padding: '0 4px' }}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}

        <textarea
          value={text}
          onChange={(e) => {
            setAcceptedProcessingKey(null)
            setText(e.target.value)
          }}
          placeholder="…or paste publication text here (abstract, results, methods)"
          aria-label="Paste publication text"
          rows={5}
          className="mt-3"
          style={{
            width: '100%',
            resize: 'vertical',
            fontFamily: 'var(--mono)',
            fontSize: 12.5,
            lineHeight: 1.6,
            color: 'var(--ink)',
            background: 'var(--bg-soft)',
            border: '0.5px solid var(--line)',
            borderRadius: 10,
            padding: '12px 14px',
          }}
        />

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5">
            {disclosures.length > 0 ? (
              disclosures.map((item) => (
                <Badge
                  key={`${item.provider_id}-${item.input_classes.join('-')}`}
                  tone={item.execution === 'external_provider' ? 'var(--warn-text)' : 'var(--teal-deep)'}
                >
                  {disclosureExecutionLabel(item)} · {item.provider_label}
                </Badge>
              ))
            ) : (
              <span style={{ fontSize: 11.5, color: 'var(--ink-4)' }}>
                Auth and processing details are checked before upload
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {totalSources > 0 && (
              <span style={{ fontSize: 12, color: 'var(--ink-4)' }}>
                {totalSources} source{totalSources === 1 ? '' : 's'} ready
              </span>
            )}
            {busy && (
              <button type="button" onClick={cancelCurrentRun} style={ghostBtn()}>
                Cancel
              </button>
            )}
            <button type="button" disabled={!canExtract} onClick={() => void beginRun()} style={primaryBtn(canExtract)}>
              {phase === 'validating'
                ? 'Checking…'
                : phase === 'queued' || phase === 'running'
                  ? 'Extracting…'
                  : 'Extract →'}
            </button>
          </div>
        </div>
      </section>

      {phase === 'auth_required' && (
        <section
          className="mt-4"
          role="status"
          style={{
            fontSize: 13,
            color: 'var(--ink-2)',
            background: 'var(--warn-tint)',
            border: '0.5px solid var(--warn-bdr)',
            borderRadius: 10,
            padding: '14px 16px',
          }}
        >
          <strong style={{ display: 'block', color: 'var(--ink)' }}>Sign in before processing</strong>
          <span style={{ display: 'block', marginTop: 4 }}>
            Your attached sources remain staged in this tab. Extraction resumes after sign-in.
          </span>
          <button type="button" onClick={openAuthMenu} style={{ ...primaryBtn(true), marginTop: 10 }}>
            Sign in
          </button>
        </section>
      )}

      {phase === 'consent_required' && disclosures.length > 0 && (
        <ProcessingDisclosurePanel disclosures={disclosures} onAccept={() => void acceptAndContinue()} />
      )}

      <SourceRunStatusList
        runs={sourceRuns}
        onRetry={retryFailedSources}
        onRemove={(record) => void removeSourceRun(record)}
      />

      {phase === 'cancelled' && (
        <p
          className="mt-4"
          role="status"
          style={{
            fontSize: 13,
            color: 'var(--warn-text)',
            background: 'var(--warn-tint)',
            border: '0.5px solid var(--warn-bdr)',
            borderRadius: 10,
            padding: '12px 14px',
          }}
        >
          Extraction cancelled. Staged sources remain available to retry.
        </p>
      )}

      {phase === 'expired' && (
        <p
          className="mt-4"
          role="alert"
          style={{
            fontSize: 13,
            color: 'var(--ink-3)',
            background: 'var(--bg-soft)',
            border: '0.5px solid var(--line-2)',
            borderRadius: 10,
            padding: '12px 14px',
          }}
        >
          This saved Paper run expired. Its result is no longer available; attach the source again to create a new run.
        </p>
      )}

      {phase === 'failed' && error && (
        <p
          className="mt-4"
          role="alert"
          style={{
            fontSize: 13,
            color: 'var(--warn-text)',
            background: 'var(--warn-tint)',
            border: '0.5px solid var(--warn-bdr)',
            borderRadius: 10,
            padding: '12px 14px',
          }}
        >
          {error}
        </p>
      )}

      {/* Results */}
      {result && counts && (phase === 'completed' || phase === 'partial' || phase === 'empty') && (
        <section className="mt-6">
          {phase === 'partial' && (
            <p
              role="status"
              style={{
                margin: '0 0 12px',
                padding: '10px 12px',
                borderRadius: 9,
                border: '0.5px solid var(--warn-bdr)',
                background: 'var(--warn-tint)',
                color: 'var(--warn-text)',
                fontSize: 12.5,
              }}
            >
              Partial result. Completed sources are preserved; retry only the failed sources above.
            </p>
          )}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <h2 style={{ fontFamily: 'var(--display)', fontSize: 18, fontWeight: 650, margin: 0, color: 'var(--ink)' }}>
                Candidates
              </h2>
              <span style={{ fontSize: 12.5, color: 'var(--ink-3)' }}>
                {counts.papers} paper{counts.papers === 1 ? '' : 's'} · {counts.mentions} mention
                {counts.mentions === 1 ? '' : 's'} · {counts.distinct} distinct · {counts.validated} validated
              </span>
              {result.mock && (
                <span className="eamos-mock" title={FRONTEND_FIXTURE_TIP}>
                  Frontend fixture
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {merged.length > 0 && (
                <button type="button" onClick={exportTsv} style={ghostBtn()}>
                  Export TSV
                </button>
              )}
              {saveableRows.length > 0 && (
                <>
                  <button type="button" onClick={addAllSaveable} style={ghostBtn()}>
                    + All to Library
                  </button>
                  <button type="button" onClick={addAllToBatch} style={ghostBtn()}>
                    → Batch
                  </button>
                </>
              )}
            </div>
          </div>

          {/* View toggle (always shown) + per-source strip */}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <div
              role="tablist"
              aria-label="Result view"
              className="inline-flex items-center"
              style={{ background: 'var(--bg-soft)', border: '0.5px solid var(--line)', borderRadius: 100, padding: 3 }}
            >
              {(
                [
                  ['merged', 'Merged'],
                  ['by-paper', 'By paper'],
                ] as Array<[ResultView, string]>
              ).map(([key, label]) => {
                const active = view === key
                return (
                  <button
                    key={key}
                    role="tab"
                    aria-selected={active}
                    type="button"
                    onClick={() => setView(key)}
                    style={{
                      padding: '5px 12px',
                      fontSize: 11.5,
                      fontWeight: 600,
                      borderRadius: 100,
                      border: 'none',
                      cursor: 'pointer',
                      color: active ? '#ffffff' : 'var(--ink-3)',
                      background: active ? 'var(--ink-2)' : 'transparent',
                    }}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {result.bySource.map((s) => (
                <span
                  key={s.name}
                  title={s.name}
                  style={{
                    border: '0.5px solid var(--line)',
                    borderRadius: 8,
                    background: 'var(--bg)',
                    padding: '4px 9px',
                    fontSize: 11,
                    color: 'var(--ink-3)',
                  }}
                >
                  {sourceHeading(s).short} · {s.variants.length} mention{s.variants.length === 1 ? '' : 's'}
                </span>
              ))}
            </div>
          </div>

          {/* Merged view */}
          {view === 'merged' &&
            (merged.length === 0 ? (
              <p className="mt-4" style={{ fontSize: 13, color: 'var(--ink-3)' }}>
                No variant mentions found across the supplied sources.
              </p>
            ) : (
              <ul className="mt-4 flex flex-col gap-3" style={{ padding: 0, margin: 0 }}>
                {merged.map((m) => (
                  <PaperCandidateRow
                    key={m.key}
                    merged={m}
                    savedKeys={savedKeys}
                    onOpenReport={openReport}
                    onAddVariant={addVariant}
                    onAddCandidate={addCandidate}
                  />
                ))}
              </ul>
            ))}

          {/* By-paper grouped view */}
          {view === 'by-paper' && (
            <div className="mt-4 flex flex-col gap-6">
              {result.bySource.map((s) => {
                const rows = mergeVariants(s.variants.map((v) => ({ source: s.name, v })))
                const heading = sourceHeading(s)
                const collapsed = collapsedPapers.has(s.name)
                return (
                  <div key={s.name}>
                    {/* Paper title leads as the group header (chevron collapses
                        the section); its variants nest below. */}
                    <div style={{ borderBottom: '1px solid var(--line)', paddingBottom: 11, marginBottom: collapsed ? 0 : 14 }}>
                      <div className="flex items-start gap-2">
                        <button
                          type="button"
                          aria-expanded={!collapsed}
                          aria-label={`${collapsed ? 'Expand' : 'Collapse'} ${heading.primary}`}
                          onClick={() => togglePaper(s.name)}
                          style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '3px 2px 0 0', color: 'var(--ink-4)', fontSize: 13, lineHeight: 1 }}
                        >
                          <span style={{ display: 'inline-block', transform: collapsed ? 'rotate(-90deg)' : 'none', transition: 'transform 120ms' }}>
                            ▾
                          </span>
                        </button>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div className="flex flex-wrap items-baseline gap-2">
                            <h3
                              style={{
                                fontFamily: 'var(--display)',
                                fontSize: 18,
                                fontWeight: 650,
                                color: 'var(--ink)',
                                margin: 0,
                                lineHeight: 1.3,
                              }}
                            >
                              {heading.primary}
                            </h3>
                            <Badge tone={s.kind === 'pdf' ? 'var(--warn-text)' : 'var(--ink-3)'}>{s.kind}</Badge>
                          </div>
                          {heading.byline && (
                            <div style={{ fontSize: 12.5, color: 'var(--ink-3)', marginTop: 3 }}>{heading.byline}</div>
                          )}
                          {!s.metadata && (
                            <div style={{ fontSize: 11.5, color: 'var(--ink-4)', marginTop: 3 }}>
                              Bibliographic metadata unavailable; filename shown.
                            </div>
                          )}
                          <div className="flex flex-wrap items-center gap-2" style={{ marginTop: 5 }}>
                            {heading.pmid && (
                              <a
                                href={`https://pubmed.ncbi.nlm.nih.gov/${heading.pmid}/`}
                                target="_blank"
                                rel="noreferrer"
                                style={citationLink}
                              >
                                PMID: {heading.pmid}
                              </a>
                            )}
                            {heading.doi && (
                              <a href={`https://doi.org/${heading.doi}`} target="_blank" rel="noreferrer" style={citationLink}>
                                DOI
                              </a>
                            )}
                            {heading.filename && (
                              <span style={{ fontSize: 11, color: 'var(--ink-4)' }}>{heading.filename}</span>
                            )}
                            <span style={{ fontSize: 11, color: 'var(--ink-4)' }}>
                              · {rows.length} variant{rows.length === 1 ? '' : 's'} mentioned
                              {s.pdf ? ` · ${s.pdf.page_count}p ${s.pdf.engine}` : ''}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                    {!collapsed &&
                      (rows.length === 0 ? (
                        <p style={{ fontSize: 12.5, color: 'var(--ink-4)' }}>No variant mentions in this source.</p>
                      ) : (
                        <ul className="flex flex-col gap-3" style={{ padding: 0, margin: 0 }}>
                          {rows.map((m) => (
                            <PaperCandidateRow
                              key={`${s.name}-${m.key}`}
                              merged={m}
                              savedKeys={savedKeys}
                              onOpenReport={openReport}
                              onAddVariant={addVariant}
                              onAddCandidate={addCandidate}
                            />
                          ))}
                        </ul>
                      ))}
                  </div>
                )
              })}
            </div>
          )}

          {/* Warnings / provenance / guardrails */}
          <div className="mt-5">
            <button
              type="button"
              onClick={() => setShowMeta((s) => !s)}
              style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--ink-4)', background: 'transparent', border: 'none', cursor: 'pointer', padding: 0 }}
            >
              {showMeta ? 'Hide' : 'Show'} warnings & provenance ▾
            </button>
            {showMeta && (
              <div
                className="mt-3"
                style={{ border: '0.5px solid var(--line)', borderRadius: 10, background: 'var(--bg)', padding: '14px 16px', fontSize: 12, color: 'var(--ink-3)' }}
              >
                {result.warnings.length > 0 && (
                  <div className="mb-2 flex flex-wrap gap-1.5">
                    {result.warnings.map((w) => (
                      <span
                        key={w}
                        style={{
                          border: '0.5px solid var(--warn-bdr)',
                          borderRadius: 7,
                          background: 'var(--warn-tint)',
                          color: 'var(--warn-text)',
                          padding: '3px 7px',
                          fontSize: 10.5,
                          fontWeight: 600,
                        }}
                      >
                        {formatToken(w)}
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex flex-wrap gap-1.5">
                  {result.provenance.map((p) => (
                    <Chip key={p}>{formatToken(p)}</Chip>
                  ))}
                </div>
                <div className="mt-3" style={{ fontSize: 11, color: 'var(--ink-4)', lineHeight: 1.6 }}>
                  Eamos does not ask for patient records, but publications can contain case or person language.
                  Only the short evidence quote per candidate is returned to this view, never the full paper body.
                </div>
                {disclosures.map((item) => (
                  <div
                    key={`${item.provider_id}-${item.input_classes.join('-')}`}
                    className="mt-2"
                    style={{ fontSize: 11, color: 'var(--ink-4)', lineHeight: 1.6 }}
                  >
                    {item.provider_label}: {disclosureExecutionLabel(item).toLowerCase()} ·{' '}
                    {item.raw_input_persisted ? 'raw input persisted' : 'raw input not persisted'} ·{' '}
                    {disclosureRetentionLabel(item).toLowerCase()}.
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      )}
    </main>
  )

  return (
    <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
      <TopNav right={<ModePill current="paper" />}>
        {/* Compact variant search, same as /report: expands on focus, routes to
            the report. Keeps the search bar consistent across every surface. */}
        <div
          className="mx-auto"
          onFocus={() => setSearchFocused(true)}
          onBlur={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setSearchFocused(false)
          }}
          style={{
            width: '100%',
            maxWidth: searchFocused ? 760 : 640,
            transition: 'max-width 460ms var(--ease-emphasized)',
          }}
        >
          <EamosSearch size="compact" tone="light" onSubmit={handleSearch} />
        </div>
      </TopNav>
      {/* WorkRail rendered directly (like /report) — no padded wrapper, so the
          sticky rail reaches the viewport bottom instead of stopping short. The
          output pane owns its own bottom spacing. */}
      <WorkRail
        surface="paper"
        title="Library"
        aiTitle="Ask Eamos"
        aiPanel={<PaperAiPanel paper={paperScope} />}
        foot={<RailFoot />}
        output={output}
      >
        <LibrarySection openLabel="Open report" />
      </WorkRail>

      {toast && (
        <div
          role="status"
          style={{
            position: 'fixed',
            bottom: 24,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'var(--ink-2)',
            color: '#ffffff',
            padding: '10px 18px',
            borderRadius: 999,
            fontSize: 12.5,
            fontWeight: 600,
            boxShadow: '0 6px 24px rgba(0,0,0,0.18)',
            zIndex: 60,
          }}
        >
          {toast}
        </div>
      )}
    </div>
  )
}
