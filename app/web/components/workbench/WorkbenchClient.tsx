'use client'
import './workbench-shell.css'
import './workbench-viewer.css'
import './workbench-side-panel.css'
import './workbench-tools.css'
import './workbench-designers.css'
import { useCallback, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import type { WorkbenchTool } from '@/lib/backend'
import { EamosLogo } from '@/components/brand/EamosLogo'
import { EamosSearch } from '@/components/landing/EamosSearch'
import { ModePill } from '@/components/layout/ModePill'
import { captureWorkbenchOpen } from '@/lib/product-analytics'
import { ContextStrip } from './ContextStrip'
import { WorkbenchShell } from './WorkbenchShell'
import {
  readWorkbenchWorkspace,
  workbenchIdentity,
} from '@/lib/workbench/workspace'
import type { ViewerMode } from './CanvasHeader'

const DEFAULT_GENE = 'RPE65'
const DEFAULT_CDNA = 'c.260A>G'

function parseQuery(raw: string): { gene: string; cdna: string; transcript?: string } | null {
  const s = raw.trim()
  if (!s) return null
  const m = s.match(
    /^([A-Za-z0-9]+)[\s:]+(?:(N[MR]_\d+(?:\.\d+)?|ENST\d+(?:\.\d+)?)[\s:]+)?(.+)$/i,
  )
  if (!m) return null
  return {
    gene: m[1].toUpperCase(),
    transcript: m[2],
    cdna: m[3].trim(),
  }
}

function cleanParam(value: string | null): string | undefined {
  const clean = value?.trim()
  return clean || undefined
}

export function WorkbenchClient() {
  const params = useSearchParams()
  const router = useRouter()

  const gene = cleanParam(params.get('gene'))?.toUpperCase() ?? DEFAULT_GENE
  const cdna = cleanParam(params.get('cdna')) ?? DEFAULT_CDNA
  const transcript = cleanParam(params.get('transcript'))

  const toolParam = params.get('tool')
  const legacyCompare = toolParam === 'compare'
  const tool: WorkbenchTool = toolParam === 'primer' || toolParam === 'crispr' || toolParam === 'align'
    ? toolParam
    : 'viewer'
  const view: ViewerMode = params.get('view') === 'locus' ? 'locus' : 'window'
  const contextId = /^[A-Za-z0-9_-]{1,100}$/.test(params.get('context_id') ?? '')
    ? params.get('context_id') ?? undefined
    : undefined
  const lastOpenedIdentity = useRef<string | null>(null)

  const workbenchHref = useCallback((
    nextTool: WorkbenchTool,
    nextView: ViewerMode,
    nextTranscript = transcript,
  ) => {
    const next = new URLSearchParams({ gene, cdna, tool: nextTool, view: nextView })
    if (nextTranscript) next.set('transcript', nextTranscript)
    if (contextId) next.set('context_id', contextId)
    return `/workbench?${next.toString()}`
  }, [cdna, contextId, gene, transcript])

  useEffect(() => {
    if (!legacyCompare) return
    router.replace('/compare?view=compare&notice=workbench_compare_moved', { scroll: false })
  }, [legacyCompare, router])

  useEffect(() => {
    if (legacyCompare || params.has('tool') || params.has('view')) return
    const restored = readWorkbenchWorkspace(workbenchIdentity(gene, cdna, transcript))
    if (!restored) return
    router.replace(workbenchHref(restored.active_tool, restored.view), { scroll: false })
  }, [cdna, gene, legacyCompare, params, router, transcript, workbenchHref])

  useEffect(() => {
    const identity = `${gene}\u0000${cdna}\u0000${transcript ?? ''}`
    if (lastOpenedIdentity.current === identity) return
    lastOpenedIdentity.current = identity
    captureWorkbenchOpen()
  }, [cdna, gene, transcript])

  // A gene/variant lookup stays on the workbench (loads the new sequence); a
  // free-text or unparseable query hands off to the report search resolver.
  const handleLookup = (query: string) => {
    const parsed = parseQuery(query)
    if (parsed) {
      const next = new URLSearchParams({
        gene: parsed.gene,
        cdna: parsed.cdna,
      })
      if (parsed.transcript) next.set('transcript', parsed.transcript)
      router.push(`/workbench?${next.toString()}`)
    } else if (query.trim()) {
      router.push(`/report?q=${encodeURIComponent(query.trim())}`)
    }
  }

  if (legacyCompare) {
    return <div className="wb-redirect" role="status">Opening Batch comparison…</div>
  }

  return (
    <div className="wb-page" style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
      {/* ── Nav — shared chrome, identical to Report / Batch ── */}
      <div className="nav-wrap">
        <div className="wrap-wide nav">
          <Link href="/" className="wb-logo" aria-label="Eamos home">
            <EamosLogo size={18} />
          </Link>
          <div className="wb-nav-search">
            <EamosSearch size="compact" tone="light" onSubmit={handleLookup} />
          </div>
          <ModePill current="workbench" />
        </div>
      </div>

      <ContextStrip
        gene={gene}
        variant={cdna}
        tool={tool}
        onSelectTool={(nextTool) => router.push(workbenchHref(nextTool, view), { scroll: false })}
      />

      {gene === DEFAULT_GENE && cdna === DEFAULT_CDNA && !params.has('gene') && !params.has('cdna') ? (
        <div className="wb-example-note" role="note">
          Example workspace: RPE65 c.260A&gt;G. Search for a gene and variant above to replace it with your target.
        </div>
      ) : null}

      <WorkbenchShell
        tool={tool}
        gene={gene}
        cdna={cdna}
        transcript={transcript}
        initialView={view}
        onViewChange={(nextView) => router.replace(workbenchHref(tool, nextView), { scroll: false })}
        onTranscriptChange={(nextTranscript) => router.push(
          workbenchHref(tool, view, nextTranscript),
          { scroll: false },
        )}
      />
    </div>
  )
}
