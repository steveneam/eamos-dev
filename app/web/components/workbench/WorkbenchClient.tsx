'use client'
import './workbench-shell.css'
import './workbench-viewer.css'
import './workbench-side-panel.css'
import './workbench-tools.css'
import './workbench-designers.css'
import { useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import type { WorkbenchTool } from '@/lib/backend'
import { EamosLogo } from '@/components/brand/EamosLogo'
import { EamosSearch } from '@/components/landing/EamosSearch'
import { ModePill } from '@/components/layout/ModePill'
import { ContextStrip } from './ContextStrip'
import { WorkbenchShell } from './WorkbenchShell'

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

  const [tool, setTool] = useState<WorkbenchTool>('viewer')

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

  return (
    <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
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
        onSelectTool={setTool}
      />

      <WorkbenchShell tool={tool} gene={gene} cdna={cdna} transcript={transcript} />
    </div>
  )
}
