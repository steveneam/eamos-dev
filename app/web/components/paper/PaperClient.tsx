'use client'

import { useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
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
import { stashCompareVariants, type ParsedVariant } from '@/lib/variant-file'
import { extractPaperVariants, isMockResponse } from '@/lib/paperVariants'
import type { PaperChatScope } from '@/lib/chat'
import type {
  PaperPdfMeta,
  PaperSourceMetadata,
  PaperVariantsResponse,
  SearchInputCandidate,
  ValidatedPaperVariant,
} from '@/lib/backend'

type Phase = 'idle' | 'loading' | 'ready' | 'error'
type ResultView = 'merged' | 'by-paper'

const MOCK_TIP =
  'Mock extraction — the paper → variants endpoint is not yet wired to live data. The fail-closed gating, dedup, provenance and actions are real.'

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
  if (!c.gene || !c.cdna) return null
  const p = new URLSearchParams({ gene: c.gene, cdna: c.cdna })
  if (c.transcript) p.set('transcript', c.transcript)
  if (c.protein_change) p.set('protein_change', c.protein_change)
  return `/report?${p.toString()}`
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
    const p = new URLSearchParams({ gene: v.gene, cdna })
    if (m) p.set('transcript', m[1])
    if (v.protein_change) p.set('protein_change', v.protein_change)
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

      {(showOpen || showSave) && !hasRecommendations && (
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
              return (
                <div key={c.candidate_id} className="flex flex-col gap-1.5">
                  <CandidateCard
                    candidate={c}
                    onSelect={(picked) => {
                      const href = candidateReportHref(picked)
                      if (href) router.push(href)
                    }}
                  />
                  {candidateToParsed(c) && (
                    <button
                      type="button"
                      disabled={cSaved}
                      onClick={() => onAddCandidate(c)}
                      style={{ ...ghostBtn(), alignSelf: 'flex-start', padding: '5px 11px', fontSize: 11.5 }}
                    >
                      {cSaved ? 'In library ✓' : '+ Library'}
                    </button>
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
  const [text, setText] = useState('')
  const [attachments, setAttachments] = useState<AttachedSource[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ExtractResult | null>(null)
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

  const totalSources = attachments.length + (text.trim() ? 1 : 0)
  const canExtract = phase !== 'loading' && totalSources > 0

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
    setAttachments((prev) => [...prev, ...next])
  }
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files?.length) void addFiles(e.dataTransfer.files)
  }
  const removeAttachment = (id: string) => setAttachments((prev) => prev.filter((a) => a.id !== id))

  const run = async () => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setPhase('loading')
    setError(null)

    const sources: AttachedSource[] = []
    if (text.trim()) sources.push({ id: 'paste', name: 'Pasted text', kind: 'text', text })
    sources.push(...attachments)

    try {
      const tagged: Array<{ source: string; v: ValidatedPaperVariant }> = []
      const bySource: SourceGroup[] = []
      const warnings: string[] = []
      const provenance = new Set<string>()
      let mock = false

      for (const src of sources) {
        const res: PaperVariantsResponse =
          src.kind === 'pdf'
            ? await extractPaperVariants({ pdf: src.file, sourceName: src.name }, { signal: controller.signal })
            : await extractPaperVariants({ text: src.text ?? '', sourceName: src.name }, { signal: controller.signal })
        if (isMockResponse(res)) mock = true
        res.variants.forEach((v) => tagged.push({ source: src.name, v }))
        res.warnings.forEach((w) => warnings.push(`${src.name}: ${w}`))
        res.provenance.forEach((p) => provenance.add(p))
        bySource.push({
          name: src.name,
          kind: src.kind,
          pdf: res.pdf,
          metadata: res.source_metadata,
          variants: res.variants,
        })
      }

      setResult({ tagged, bySource, warnings, provenance: [...provenance], mock })
      setSavedKeys(new Set())
      setPhase('ready')
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setError(err instanceof Error ? err.message : 'Extraction failed')
      setPhase('error')
    }
  }

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
          onChange={(e) => setText(e.target.value)}
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
          <span className="eamos-mock" title={MOCK_TIP}>
            Mock extraction
          </span>
          <div className="flex items-center gap-3">
            {totalSources > 0 && (
              <span style={{ fontSize: 12, color: 'var(--ink-4)' }}>
                {totalSources} source{totalSources === 1 ? '' : 's'} ready
              </span>
            )}
            <button type="button" disabled={!canExtract} onClick={run} style={primaryBtn(canExtract)}>
              {phase === 'loading' ? 'Extracting…' : 'Extract →'}
            </button>
          </div>
        </div>
      </section>

      {phase === 'error' && (
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
      {result && counts && phase === 'ready' && (
        <section className="mt-6">
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
                <span className="eamos-mock" title={MOCK_TIP}>
                  Mock
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
                  Guardrails — patient data not used · raw paper text blocked · secrets blocked. Only the short
                  evidence quote per candidate is surfaced, never the full paper.
                </div>
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
